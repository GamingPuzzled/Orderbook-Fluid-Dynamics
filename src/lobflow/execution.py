"""Execution cost of a follow-up market order after a sweep.

For a market order of size Q on the swept side at post-sweep delay τ, walk the stored
moving-frame profile (depth at d = 1..50 ticks from the opposite best quote) and compute the
liquidity cost relative to the mid at τ:

    cost_bps(Q, τ) = (d̄(Q, τ) − spread_ticks(τ)/2) · tick / mid(τ) · 1e4,

where d̄ is the fill-weighted mean distance (volume beyond d = 50 is charged at d = 51, a lower
bound; its incidence is reported). Sweeps are compared with state-matched placebo times
(within-day nearest-neighbour weights on 10 s volume, 60 s realised variation and pre-shock
swept-side depth), with day-cluster bootstrap CIs.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl

F64 = npt.NDArray[np.float64]

D_MAX = 50
Q_MULTS: tuple[float, ...] = (0.05, 0.1, 0.25)


def walk_cost(depth: F64, q: float) -> tuple[F64, F64]:
    """Fill-weighted mean distance (ticks) for size ``q`` on each row of ``depth`` (n × D),
    and the unfilled share charged at d = D + 1."""
    if q <= 0:
        raise ValueError("q must be positive")
    d = np.arange(1, depth.shape[1] + 1, dtype=np.float64)
    before = np.concatenate([np.zeros((depth.shape[0], 1)), np.cumsum(depth, axis=1)[:, :-1]], 1)
    fill = np.clip(q - before, 0.0, depth)
    left = np.clip(q - fill.sum(axis=1), 0.0, None)
    dbar = (fill @ d + left * (depth.shape[1] + 1)) / q
    return dbar, left / q


def profile_matrix(prof: pl.DataFrame) -> pl.DataFrame:
    """Long profiles (event_id, tau_ms, d, depth, spread_ticks, mid) -> one row per
    (event_id, tau_ms) with ``depth`` as a list ordered by d = 1..D_MAX."""
    return (
        prof.filter(pl.col("d") <= D_MAX)
        .sort("event_id", "tau_ms", "d")
        .group_by("event_id", "tau_ms", maintain_order=True)
        .agg(
            pl.col("depth"),
            pl.col("spread_ticks").first(),
            pl.col("mid").first(),
            pl.col("day").first(),
        )
        .filter(pl.col("depth").list.len() == D_MAX)
    )


def costs(mat: pl.DataFrame, tick: dict[str, float], qs: Sequence[float]) -> pl.DataFrame:
    """Add ``cost_bps_q{i}`` and ``short_q{i}`` columns for each size in ``qs``."""
    depth = np.vstack(mat["depth"].to_list()).astype(np.float64)
    tk = np.array([tick[d] for d in mat["day"].to_list()])
    half = mat["spread_ticks"].to_numpy() / 2
    mid = mat["mid"].to_numpy()
    cols = []
    for i, q in enumerate(qs):
        dbar, short = walk_cost(depth, q)
        cols += [
            pl.Series(f"cost_bps_q{i}", (dbar - half) * tk / mid * 1e4),
            pl.Series(f"short_q{i}", short),
        ]
    return mat.drop("depth").with_columns(cols)


def _boot_days(
    s: pl.DataFrame, p: pl.DataFrame, col: str, taus: Sequence[int], n_boot: int, seed: int
) -> tuple[F64, F64, F64]:
    """Per τ: sweep mean, weighted placebo mean and (n_boot × τ × 2) day-bootstrap draws."""
    days = sorted(set(s["day"].to_list()))
    rng = np.random.default_rng(seed)

    def agg(df: pl.DataFrame) -> dict[tuple[str, int], tuple[float, float]]:
        g = df.group_by("day", "tau_ms").agg(
            (pl.col(col) * pl.col("w")).sum().alias("num"), pl.col("w").sum().alias("den")
        )
        return {(d, t): (n, m) for d, t, n, m in g.iter_rows()}

    sa, pa = agg(s.with_columns(pl.lit(1.0).alias("w"))), agg(p)

    def mean(tab: dict[tuple[str, int], tuple[float, float]], ds: Sequence[str]) -> F64:
        out = np.empty(len(taus))
        for j, t in enumerate(taus):
            num = sum(tab.get((d, t), (0.0, 0.0))[0] for d in ds)
            den = sum(tab.get((d, t), (0.0, 0.0))[1] for d in ds)
            out[j] = num / den if den > 0 else np.nan
        return out

    draws = np.empty((n_boot, len(taus), 2))
    for b in range(n_boot):
        ds = [days[i] for i in rng.integers(0, len(days), len(days))]
        draws[b, :, 0], draws[b, :, 1] = mean(sa, ds), mean(pa, ds)
    return mean(sa, days), mean(pa, days), draws


def run_execution(
    out_dir: Path,
    results_dir: Path,
    *,
    max_push_ms: float = 20.0,
    n_boot: int = 200,
    q_mults: Sequence[float] = Q_MULTS,
) -> str:
    """Follow-up execution cost table for one symbol; writes ``execution.md`` / ``.parquet``."""
    from lobflow.analysis import load_outputs, placebo_weights

    data = load_outputs(out_dir, max_push_ms=max_push_ms)
    ev = data["events"].filter(pl.col("cleared_frac") >= 0.95)
    if "state" not in data or "flows_info" not in data:
        raise ValueError(f"state / flows outputs missing in {out_dir}")
    w, _ = placebo_weights(
        data["state"], data["flows_info"], data["flows_placebo_info"], method="nn"
    )
    s_ids = data["flows_info"].filter(pl.col("valid"))["event_id"]
    ev = ev.filter(pl.col("event_id").is_in(s_ids.implode()))
    # size unit: median placebo depth within D_MAX ticks just before the placebo time
    base = (
        data["placebo"]
        .filter((pl.col("tau_ms") == -1) & (pl.col("d") <= D_MAX))
        .group_by("event_id")
        .agg(pl.col("depth").sum())["depth"]
    )
    q_med = float(base.median())  # type: ignore[arg-type]
    qs = [m * q_med for m in q_mults]
    tick = {d: float(t) for d, t in ev.group_by("day").agg(pl.col("tick").first()).iter_rows()}

    s_prof = data["moving"].filter(pl.col("event_id").is_in(ev["event_id"].implode()))
    p_prof = data["placebo"].join(w.select("event_id", "w"), on="event_id", how="inner")
    p_prof = p_prof.filter(pl.col("w") > 0)
    s = costs(profile_matrix(s_prof), tick, qs)
    p = costs(profile_matrix(p_prof), tick, qs).join(
        w.select("event_id", "w"), on="event_id", how="inner"
    )
    s = s.filter(pl.col("day").is_in(p["day"].unique().implode()))  # days with a match
    taus = sorted(s["tau_ms"].unique().to_list())

    rows = []
    for i, (m, q) in enumerate(zip(q_mults, qs, strict=True)):
        for stat in ("cost_bps", "short"):
            col = f"{stat}_q{i}"
            sm, pm, dr = _boot_days(s, p, col, taus, n_boot, seed=i)
            diff = dr[:, :, 0] - dr[:, :, 1]
            for j, t in enumerate(taus):
                rows.append(
                    {
                        "q_mult": m,
                        "q": q,
                        "stat": stat,
                        "tau_ms": t,
                        "sweep": float(sm[j]),
                        "placebo": float(pm[j]),
                        "diff": float(sm[j] - pm[j]),
                        "diff_lo": float(np.nanpercentile(diff[:, j], 2.5)),
                        "diff_hi": float(np.nanpercentile(diff[:, j], 97.5)),
                    }
                )
    tab = pl.DataFrame(rows)
    results_dir.mkdir(parents=True, exist_ok=True)
    tab.write_parquet(results_dir / "execution.parquet")

    lines = [
        "# Cost of a follow-up market order on the swept side",
        "",
        f"Sweeps: {s['event_id'].n_unique():,} (cleared ≥ 95%), placebo times with NN weight > 0:"
        f" {p['event_id'].n_unique():,}; days: {s['day'].n_unique()}. Q in multiples of the "
        f"median placebo depth within {D_MAX} ticks ({q_med:.3f}). Cost = fill-weighted "
        "distance from the mid at τ, in bps (τ = −1: just before the sweep). "
        "95% day-bootstrap CIs for sweep − placebo. "
        "`short` = share of Q beyond 50 ticks (charged at 51; costs are lower bounds).",
        "",
    ]
    for m in q_mults:
        sub = tab.filter((pl.col("q_mult") == m) & (pl.col("stat") == "cost_bps"))
        sh = tab.filter((pl.col("q_mult") == m) & (pl.col("stat") == "short"))
        lines += [
            f"## Q = {m:g} × median depth",
            "",
            "| τ (ms) | sweep | placebo | sweep − placebo | excess / excess at 20 ms | "
            "short (sweep) |",
            "|---|---|---|---|---|---|",
        ]
        ex20 = float(sub.filter(pl.col("tau_ms") == 20)["diff"][0])
        for r, sr in zip(sub.iter_rows(named=True), sh.iter_rows(named=True), strict=True):
            rel = "" if r["tau_ms"] < 0 or ex20 == 0 else f"{r['diff'] / ex20:.2f}"
            lines.append(
                f"| {r['tau_ms']} | {r['sweep']:.3f} | {r['placebo']:.3f} | {r['diff']:+.3f} "
                f"[{r['diff_lo']:+.3f}, {r['diff_hi']:+.3f}] | {rel} | {sr['sweep']:.3f} |"
            )
        lines.append("")
    text = "\n".join(lines)
    (results_dir / "execution.md").write_text(text)
    return text
