"""Does refill depend on how informative the sweep was? (adverse-selection test)

If liquidity providers pull and reposition because a sweep may carry information, refill
should differ between sweeps after which the price keeps moving in the sweep's direction
(informative) and sweeps after which it reverts (uninformative).

Post-sweep drift: signed price change, in ticks, from the mid quote 1 s after the sweep to the
volume-weighted trade price in [h − 1 s, h + 1 s] (default h = 5 s), positive when the price
continues in the sweep's direction. It is measured strictly after the 0–1 s window in which
flows are measured, so it does not contain the sweep's own mechanical price impact. It is
not exogenous: a book that stays thin can itself let the price drift, so differences across
drift groups are evidence of association, not of a causal effect of information.

Sweeps are split into within-day terciles of drift (reversal / flat / continuation). For each
tercile, placebo times are re-matched (nearest neighbour, within day, on volume, volatility and
depth) from (a) all placebo times, and (b) placebo times in the same within-day tercile of
their own drift (signed by their pseudo-direction), which removes the generic link between
price moves and cancellations. Statistics are those of :mod:`lobflow.robustness`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl

from lobflow.robustness import (
    STATS,
    _fmt,
    match_within_day,
    prepare_subsets,
    subset_point_fn,
    subset_stats,
)

F64 = npt.NDArray[np.float64]
US = 1_000_000
REF_TAU_MS = 1000
TERCILES = ("reversal", "flat", "continuation")
DIFF_STATS = ("kappa_20-40", "withdrawal_<250ms", "transport_<250ms", "source_>250ms")


def vwap_at(
    times_us: npt.NDArray[np.int64],
    trade_ts: npt.NDArray[np.int64],
    trade_px: F64,
    trade_sz: F64,
    *,
    half_width_us: int = US,
) -> F64:
    """Volume-weighted trade price in [t − half_width, t + half_width] per time; NaN if no
    trade. ``trade_ts`` must be sorted."""
    cum_v = np.concatenate([[0.0], np.cumsum(trade_sz)])
    cum_pv = np.concatenate([[0.0], np.cumsum(trade_px * trade_sz)])
    lo = np.searchsorted(trade_ts, times_us - half_width_us, side="left")
    hi = np.searchsorted(trade_ts, times_us + half_width_us, side="right")
    v = cum_v[hi] - cum_v[lo]
    with np.errstate(invalid="ignore", divide="ignore"):
        out = (cum_pv[hi] - cum_pv[lo]) / v
    return np.where(v > 0, out, np.nan)


def _ref_mid(out_dir: Path, days: Sequence[str], kind: str) -> pl.DataFrame:
    """Mid quote at τ = 1 s per event (renumbered ids, as ``robustness.load_tag``)."""
    parts = []
    for k, day in enumerate(days):
        df = pl.read_parquet(
            out_dir / f"{day}_{kind}.parquet", columns=["event_id", "tau_ms", "mid"]
        )
        parts.append(
            df.filter(pl.col("tau_ms") == REF_TAU_MS)
            .group_by("event_id")
            .agg(pl.col("mid").first().alias("mid_ref"))
            .with_columns((pl.col("event_id") + k * 1_000_000).alias("event_id"))
        )
    return pl.concat(parts)


def drift_ticks(times: pl.DataFrame, trades_dir: Path, *, horizon_s: float = 5.0) -> pl.DataFrame:
    """``times``: event_id, day, t0 (µs), sign (+1/−1), mid_ref, tick. Adds ``drift`` (ticks)."""
    parts = []
    for day in times["day"].unique().sort().to_list():
        t = times.filter(pl.col("day") == day)
        tr = pl.read_parquet(
            trades_dir / f"{day}.parquet", columns=["timestamp", "price", "amount"]
        ).sort("timestamp")
        px = vwap_at(
            (t["t0"].to_numpy() + int(horizon_s * US)).astype(np.int64),
            tr["timestamp"].to_numpy().astype(np.int64),
            tr["price"].to_numpy().astype(np.float64),
            tr["amount"].to_numpy().astype(np.float64),
        )
        d = t["sign"].to_numpy() * (px - t["mid_ref"].to_numpy()) / t["tick"].to_numpy()
        parts.append(t.with_columns(pl.Series("drift", d)))
    return pl.concat(parts)


def tercile(col: str) -> pl.Expr:
    """Within-day tercile (0, 1, 2) of ``col``."""
    r = pl.col(col).rank("average").over("day") / pl.len().over("day")
    return (r * 3).ceil().clip(1, 3).cast(pl.Int64).sub(1)


def run_information(
    out_dir: Path,
    results_dir: Path,
    trades_dir: Path,
    *,
    tag: str = "flowsfine",
    horizon_s: float = 5.0,
    n_boot: int = 100,
    k: int = 5,
    max_push_ms: float = 20.0,
    seed: int = 0,
) -> str:
    """Three-phase statistics by post-sweep drift tercile; writes ``information.md`` and
    ``information.parquet``."""
    si = prepare_subsets(out_dir, tag=tag, max_push_ms=max_push_ms)
    tick = si.events.select("event_id", "tick")

    s_times = (
        si.s_cov.select("event_id", "day", "t0", "side")
        .join(_ref_mid(out_dir, si.days, "moving"), on="event_id")
        .join(tick, on="event_id")
        .with_columns(pl.when(pl.col("side") == "buy").then(1.0).otherwise(-1.0).alias("sign"))
    )
    day_tick = (
        tick.join(si.events.select("event_id", "day"), on="event_id")
        .group_by("day")
        .agg(pl.col("tick").first())
    )
    p_times = (
        si.p_cov.select("event_id", "day", "t0", "is_buy")
        .join(_ref_mid(out_dir, si.days, "placebo"), on="event_id")
        .join(day_tick, on="day")
        .with_columns(pl.when(pl.col("is_buy")).then(1.0).otherwise(-1.0).alias("sign"))
    )
    s_dr = drift_ticks(s_times, trades_dir, horizon_s=horizon_s).drop_nans("drift")
    p_dr = drift_ticks(p_times, trades_dir, horizon_s=horizon_s).drop_nans("drift")
    s_dr = s_dr.with_columns(tercile("drift").alias("dq"))
    p_dr = p_dr.with_columns(tercile("drift").alias("dq"))

    s_cov = si.s_cov.join(s_dr.select("event_id", "drift", "dq"), on="event_id")
    p_cov = si.p_cov.join(p_dr.select("event_id", "drift", "dq"), on="event_id")
    s_info = si.s_info.join(s_dr.select("event_id", "drift", "dq"), on="event_id")

    rows: list[dict[str, object]] = []
    fns: dict[tuple[int, str], tuple[Callable[[Sequence[str]], dict[str, float]], list[str]]] = {}
    for q, name in enumerate(TERCILES):
        sub_cov = s_cov.filter(pl.col("dq") == q)
        sub_info = s_info.filter(pl.col("dq") == q)
        drift = sub_cov["drift"].to_numpy()
        for pool_name, pool in (
            ("all placebo times", p_cov),
            ("placebo, same drift tercile", p_cov.filter(pl.col("dq") == q)),
        ):
            w = match_within_day(sub_cov, pool, method="nn", k=k)
            fns[(q, pool_name)] = subset_point_fn(
                si.s_flows, sub_info, si.p_flows, si.p_info, w, si.windows
            )
            st = subset_stats(
                si.s_flows, sub_info, si.p_flows, si.p_info, w, si.windows, n_boot=n_boot
            )
            pd_ = pool.join(w, on="event_id")
            rows.append(
                {
                    "tercile": name,
                    "placebo_pool": pool_name,
                    "drift_median": float(np.median(drift)),
                    "placebo_drift_median": float(np.median(pd_["drift"].to_numpy()))
                    if pd_.height
                    else float("nan"),
                    **st,
                }
            )

    # paired day bootstrap: continuation − reversal, same resampled days for both
    diffs: list[dict[str, object]] = []
    rng = np.random.default_rng(seed)
    for pool_name in ("all placebo times", "placebo, same drift tercile"):
        (f_hi, d_hi), (f_lo, d_lo) = fns[(2, pool_name)], fns[(0, pool_name)]
        days = sorted(set(d_hi) & set(d_lo))
        point_hi, point_lo = f_hi(days), f_lo(days)
        draws = []
        for _ in range(n_boot):
            ds = rng.choice(days, size=len(days)).tolist()
            a, b = f_hi(ds), f_lo(ds)
            draws.append({stat: a[stat] - b[stat] for stat in DIFF_STATS})
        for stat in DIFF_STATS:
            dd = np.array([x[stat] for x in draws], dtype=float)
            diffs.append(
                {
                    "placebo_pool": pool_name,
                    "stat": stat,
                    "diff": point_hi[stat] - point_lo[stat],
                    "lo": float(np.nanpercentile(dd, 2.5)),
                    "hi": float(np.nanpercentile(dd, 97.5)),
                }
            )

    results_dir.mkdir(parents=True, exist_ok=True)
    table = pl.DataFrame(rows)
    table.write_parquet(results_dir / "information.parquet")
    diff_table = pl.DataFrame(diffs)
    diff_table.write_parquet(results_dir / "information_diff.parquet")
    lines = [
        "# Refill by post-sweep price drift (information content of the sweep)",
        "",
        f"Drift: signed price change (ticks) from the mid 1 s after the sweep to the VWAP of "
        f"trades in [{horizon_s - 1:g} s, {horizon_s + 1:g} s], positive = continuation in the "
        "sweep's direction. Within-day terciles. Placebo re-matched per tercile (NN, within "
        "day); pool (b) restricts placebo times to the same tercile of their own drift. "
        "95% day-cluster bootstrap CIs; masses are fractions of pre-shock swept depth.",
        "",
        "| drift tercile | placebo pool | sweeps | median drift (ticks) | κ 20–40 | κ 40–100 | "
        "κ 250–1000 | withdrawal <250 | repositioning <250 | new liq. >250 | repos. share "
        "<250 | switch (ms) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in table.iter_rows(named=True):
        lines.append(
            f"| {r['tercile']} | {r['placebo_pool']} | {int(r['n_sweeps'])} | "
            f"{r['drift_median']:+.1f} | "
            + " | ".join(
                _fmt(r, s, 0 if s == "t_switch_ms" else (2 if s.startswith("kappa") else 3))
                for s in STATS
            )
            + " |"
        )
    lines += [
        "",
        "## Continuation − reversal (paired day bootstrap, 95% CI)",
        "",
        "| placebo pool | statistic | difference | 95% CI |",
        "|---|---|---|---|",
        *[
            f"| {r['placebo_pool']} | {r['stat']} | {r['diff']:+.3f} | "
            f"[{r['lo']:+.3f}, {r['hi']:+.3f}] |"
            for r in diff_table.iter_rows(named=True)
        ],
    ]
    text = "\n".join(lines) + "\n"
    (results_dir / "information.md").write_text(text)
    return text
