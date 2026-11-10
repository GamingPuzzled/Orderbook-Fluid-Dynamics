"""Robustness of the three-phase refill result across matching methods and event subsets.

For each subset of sweeps (sweep size, buy vs sell, time of day, sweep volume), placebo
times are re-matched within day on (10 s volume, 60 s realised variation, pre-shock depth),
with buy/sell and time-of-day subsets drawing placebo times from the same side / hours only.
Statistics per subset (95% day-cluster bootstrap CIs):

- ``kappa_<window>``: added ÷ cancelled swept-side depth (all zones), sweeps only;
- ``withdrawal_<250ms``, ``transport_<250ms``, ``source_>250ms``, ``transport_share_<250ms``,
  ``t_switch_ms``: three-component split of excess (sweep − matched placebo) flows, as in
  :mod:`lobflow.model` (deep zones d > 5).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from lobflow.model import (
    DEEP,
    day_window_sums,
    excess_masses,
    observed_summary,
    split_components,
    window_edges,
)
from lobflow.state import matching_weights, nn_weights

COVS = ("vol_10s", "rv_60s", "depth_pre_swept")
KAPPA_GROUPS: dict[str, tuple[float, float]] = {
    "20-40": (20, 40),
    "40-100": (40, 100),
    "100-250": (100, 250),
    "250-1000": (250, 1000),
}
STATS = (
    "kappa_20-40",
    "kappa_40-100",
    "kappa_250-1000",
    "withdrawal_<250ms",
    "transport_<250ms",
    "source_>250ms",
    "transport_share_<250ms",
    "t_switch_ms",
)
US_PER_HOUR = 3_600_000_000


def load_tag(out_dir: Path, days: Sequence[str], kind: str) -> pl.DataFrame:
    """Per-day ``{day}_{kind}.parquet`` with globally unique ids (same scheme as
    :func:`lobflow.analysis.load_outputs`)."""
    parts = [
        pl.read_parquet(out_dir / f"{d}_{kind}.parquet").with_columns(
            (pl.col("event_id") + k * 1_000_000).alias("event_id"), pl.lit(d).alias("day")
        )
        for k, d in enumerate(days)
    ]
    return pl.concat(parts, how="diagonal_relaxed")


def match_within_day(
    s_cov: pl.DataFrame, p_cov: pl.DataFrame, *, method: str = "nn", k: int = 5, min_n: int = 3
) -> pl.DataFrame:
    """Placebo weights (event_id, w) matched day by day; days with < ``min_n`` sweeps or no
    placebo are dropped."""
    parts = []
    for day in s_cov["day"].unique().sort().to_list():
        sd, pd_ = s_cov.filter(pl.col("day") == day), p_cov.filter(pl.col("day") == day)
        if sd.height < min_n or pd_.height == 0:
            continue
        if method == "nn":
            parts.append(nn_weights(sd, pd_, columns=COVS, k=k))
        else:
            parts.append(matching_weights(sd, pd_, columns=COVS))
    if not parts:
        return pl.DataFrame(schema={"event_id": pl.Int64, "w": pl.Float64})
    return pl.concat(parts, how="diagonal_relaxed").select("event_id", "w")


def balance_table(s_cov: pl.DataFrame, p_cov: pl.DataFrame, w: pl.DataFrame) -> pl.DataFrame:
    """Mean covariates: sweeps, raw placebo, matched placebo, and standardised difference
    (matched − sweep) / sweep std."""
    pw = p_cov.join(w, on="event_id", how="inner")
    rows = []
    for c in (*COVS, "n_10s"):
        s = s_cov[c].cast(pl.Float64).to_numpy()
        p = p_cov[c].cast(pl.Float64).to_numpy()
        m = float(np.average(pw[c].cast(pl.Float64).to_numpy(), weights=pw["w"].to_numpy()))
        sd = float(s.std(ddof=1)) if s.size > 1 else 1.0
        rows.append(
            {
                "covariate": c,
                "sweep": float(s.mean()),
                "placebo_raw": float(p.mean()),
                "placebo_matched": m,
                "std_diff": (m - float(s.mean())) / (sd or 1.0),
            }
        )
    return pl.DataFrame(rows)


def kappa_day_sums(flows: pl.DataFrame, info: pl.DataFrame) -> pl.DataFrame:
    """Per day × kappa group: swept-side add and cancel sums (all zones)."""
    edges = {w: tuple(float(x) for x in w.split("-")) for w in flows["window"].unique()}
    group = {
        w: g
        for w, (a, b) in edges.items()
        for g, (lo, hi) in KAPPA_GROUPS.items()
        if a >= lo and b <= hi
    }
    ok = info.filter(pl.col("valid"))["event_id"].implode()
    return (
        flows.filter(
            pl.col("side") == "swept",
            pl.col("metric").is_in(["add", "cancel"]),
            pl.col("event_id").is_in(ok),
            pl.col("window").is_in(list(group)),
        )
        .with_columns(pl.col("window").replace_strict(group).alias("group"))
        .group_by("day", "group", "metric")
        .agg(pl.col("value").sum())
    )


def subset_point_fn(
    s_flows: pl.DataFrame,
    s_info: pl.DataFrame,
    p_flows: pl.DataFrame,
    p_info: pl.DataFrame,
    w: pl.DataFrame,
    windows: Sequence[str],
) -> tuple[Callable[[Sequence[str]], dict[str, float]], list[str]]:
    """(statistics for a list of days (repeats allowed), the subset's usable days)."""
    days = sorted(set(s_info["day"].unique()) & set(p_info.join(w, on="event_id")["day"]))
    s_info = s_info.filter(pl.col("day").is_in(days))
    s_sums = day_window_sums(s_flows, s_info, None, DEEP)
    p_sums = day_window_sums(p_flows, p_info, w, DEEP)
    k_sums = kappa_day_sums(s_flows, s_info)
    edges = window_edges(windows)

    def one(ds: Sequence[str]) -> dict[str, float]:
        n, j = excess_masses(s_sums, p_sums, windows, ds)
        out = observed_summary(edges, *split_components(n, j))
        counts = pl.DataFrame({"day": list(ds)}).group_by("day").len()
        tot = (
            k_sums.join(counts, on="day")
            .group_by("group", "metric")
            .agg((pl.col("value") * pl.col("len")).sum())
        )
        m = {(r["group"], r["metric"]): r["value"] for r in tot.iter_rows(named=True)}
        for g in KAPPA_GROUPS:
            c = m.get((g, "cancel"), 0.0)
            out[f"kappa_{g}"] = m.get((g, "add"), 0.0) / c if c else float("nan")
        return out

    return one, days


def subset_stats(
    s_flows: pl.DataFrame,
    s_info: pl.DataFrame,
    p_flows: pl.DataFrame,
    p_info: pl.DataFrame,
    w: pl.DataFrame,
    windows: Sequence[str],
    *,
    n_boot: int = 100,
    seed: int = 0,
) -> dict[str, float]:
    """Point estimates and bootstrap CIs (``<stat>_lo``/``_hi``) for one subset."""
    one, days = subset_point_fn(s_flows, s_info, p_flows, p_info, w, windows)
    point = one(days)
    rng = np.random.default_rng(seed)
    boots = [one(rng.choice(days, size=len(days)).tolist()) for _ in range(n_boot)]
    res: dict[str, float] = {
        "n_sweeps": float(s_info.filter(pl.col("day").is_in(days), pl.col("valid")).height)
    }
    res["n_days"] = float(len(days))
    for st in STATS:
        b = np.array([x[st] for x in boots], dtype=float)
        res[st] = point[st]
        res[f"{st}_lo"] = float(np.nanpercentile(b, 2.5))
        res[f"{st}_hi"] = float(np.nanpercentile(b, 97.5))
    return res


Subset = tuple[str, str, pl.Expr, Callable[[pl.DataFrame], pl.DataFrame] | None]


def subsets() -> list[Subset]:
    """(group, label, sweep filter, placebo-pool filter or None)."""

    def side(is_buy: bool) -> Callable[[pl.DataFrame], pl.DataFrame]:
        return lambda p: p.filter(pl.col("is_buy") == is_buy)

    def hours(lo: int, hi: int) -> Callable[[pl.DataFrame], pl.DataFrame]:
        return lambda p: p.filter(pl.col("hour").is_between(lo, hi - 1))

    return [
        ("all", "all sweeps", pl.lit(True), None),
        ("levels cleared (day tercile)", "smallest third", pl.col("gap_q") == 0, None),
        ("levels cleared (day tercile)", "middle third", pl.col("gap_q") == 1, None),
        ("levels cleared (day tercile)", "largest third", pl.col("gap_q") == 2, None),
        ("sweep volume", "below day median", pl.col("vol_rel") < 1.0, None),
        ("sweep volume", "above day median", pl.col("vol_rel") >= 1.0, None),
        ("side", "buy sweeps (ask side)", pl.col("side") == "buy", side(True)),
        ("side", "sell sweeps (bid side)", pl.col("side") == "sell", side(False)),
        ("time of day (UTC)", "00-08", pl.col("hour").is_between(0, 7), hours(0, 8)),
        ("time of day (UTC)", "08-16", pl.col("hour").is_between(8, 15), hours(8, 16)),
        ("time of day (UTC)", "16-24", pl.col("hour").is_between(16, 23), hours(16, 24)),
    ]


def _fmt(r: dict[str, object], st: str, digits: int) -> str:
    v, lo, hi = (float(r[f"{st}{s}"]) for s in ("", "_lo", "_hi"))  # type: ignore[arg-type]
    if not np.isfinite(v):
        return "–"
    return f"{v:.{digits}f} [{lo:.{digits}f}, {hi:.{digits}f}]"


@dataclass(frozen=True)
class SubsetInputs:
    """Everything subset analyses need: flows, info joined with sweep covariates, and the
    matching covariates of sweeps and placebo times."""

    s_flows: pl.DataFrame
    s_info: pl.DataFrame
    p_flows: pl.DataFrame
    p_info: pl.DataFrame
    s_cov: pl.DataFrame
    p_cov: pl.DataFrame
    windows: list[str]
    days: list[str]
    events: pl.DataFrame  # sweeps (≥ 95% of gap cleared), all columns


def prepare_subsets(
    out_dir: Path, *, tag: str = "flowsfine", max_push_ms: float = 20.0
) -> SubsetInputs:
    from lobflow.analysis import load_outputs

    data = load_outputs(out_dir, max_push_ms=max_push_ms)
    days = data["meta"].filter(pl.col("ok"))["day"].sort().to_list()
    events = data["events"].filter(pl.col("cleared_frac") >= 0.95)
    s_flows, s_info = load_tag(out_dir, days, tag), load_tag(out_dir, days, f"{tag}_info")
    p_flows, p_info = (
        load_tag(out_dir, days, f"{tag}_placebo"),
        load_tag(out_dir, days, f"{tag}_placebo_info"),
    )
    hour = ((pl.col("t0") // US_PER_HOUR) % 24).cast(pl.Int64).alias("hour")
    gap_rank = pl.col("L_gap").rank("average").over("day") / pl.len().over("day")
    ev = events.with_columns(
        hour,
        (pl.col("volume") / pl.col("volume").median().over("day")).alias("vol_rel"),
        (gap_rank * 3).ceil().clip(1, 3).cast(pl.Int64).sub(1).alias("gap_q"),
    ).select("event_id", "side", "L_gap", "gap_q", "vol_rel", "hour")
    s_info = s_info.drop("is_buy", strict=False).join(ev, on="event_id", how="inner")
    state = data["state"].with_columns(hour)
    s_cov = state.filter(pl.col("set") == "sweep").join(
        s_info.filter(pl.col("valid")).select("event_id", *COVS[2:], "side", "gap_q", "vol_rel"),
        on="event_id",
    )
    p_cov = state.filter(pl.col("set") == "placebo").join(
        p_info.filter(pl.col("valid")).select("event_id", *COVS[2:], "is_buy"), on="event_id"
    )
    labels = s_flows["window"].unique().to_list()
    edges = window_edges(labels)
    windows = [f"{int(a)}-{int(b)}" for a, b in zip(edges[:-1], edges[1:], strict=True) if a > 0]
    return SubsetInputs(s_flows, s_info, p_flows, p_info, s_cov, p_cov, windows, days, events)


def run_robustness(
    out_dir: Path,
    results_dir: Path,
    *,
    tag: str = "flowsfine",
    n_boot: int = 100,
    k: int = 5,
    max_push_ms: float = 20.0,
) -> str:
    """Matching comparison (CEM vs nearest neighbour) and subset table; writes
    ``robustness.md``, ``robustness.parquet`` and ``matching_balance.parquet``."""
    si = prepare_subsets(out_dir, tag=tag, max_push_ms=max_push_ms)
    s_flows, s_info, p_flows, p_info = si.s_flows, si.s_info, si.p_flows, si.p_info
    s_cov, p_cov, windows = si.s_cov, si.p_cov, si.windows

    rows: list[dict[str, object]] = []
    balances = []
    for method in ("cem", "nn"):
        w = match_within_day(s_cov, p_cov, method=method, k=k, min_n=8)
        balances.append(balance_table(s_cov, p_cov, w).with_columns(pl.lit(method).alias("method")))
        st = subset_stats(s_flows, s_info, p_flows, p_info, w, windows, n_boot=n_boot)
        rows.append({"group": "matching", "subset": method.upper(), **st})
    for group, label, s_filter, p_filter in subsets()[1:]:
        sub_cov = s_cov.filter(s_filter)
        pool = p_filter(p_cov) if p_filter is not None else p_cov
        w = match_within_day(sub_cov, pool, method="nn", k=k)
        st = subset_stats(
            s_flows, s_info.filter(s_filter), p_flows, p_info, w, windows, n_boot=n_boot
        )
        rows.append({"group": group, "subset": label, **st})

    results_dir.mkdir(parents=True, exist_ok=True)
    table = pl.DataFrame(rows)
    table.write_parquet(results_dir / "robustness.parquet")
    bal = pl.concat(balances)
    bal.write_parquet(results_dir / "matching_balance.parquet")
    lines = [
        "# Robustness of the three-phase refill",
        "",
        "Matching: within-day, on 10 s volume, 60 s RV and pre-shock swept depth. CEM = "
        "quartile strata; NN = 5 nearest placebo times per sweep in standardised log "
        "covariates. Subsets below use NN, re-matched per subset (side and time-of-day subsets "
        "draw placebo times from the same side / hours). 95% day-cluster bootstrap CIs; "
        "masses are fractions of pre-shock swept-side depth.",
        "",
        "## Covariate balance (std_diff = (matched − sweep) / sweep sd)",
        "",
        "| method | covariate | sweep | placebo raw | placebo matched | std diff |",
        "|---|---|---|---|---|---|",
        *[
            f"| {r['method']} | {r['covariate']} | {r['sweep']:.4g} | {r['placebo_raw']:.4g} | "
            f"{r['placebo_matched']:.4g} | {r['std_diff']:+.3f} |"
            for r in bal.iter_rows(named=True)
        ],
        "",
        "## Subsets",
        "",
        "| group | subset | sweeps | κ 20–40 | κ 40–100 | κ 250–1000 | withdrawal <250 | "
        "repositioning <250 | new liq. >250 | repos. share <250 | switch (ms) |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in table.iter_rows(named=True):
        lines.append(
            f"| {r['group']} | {r['subset']} | {int(r['n_sweeps'])} | "
            + " | ".join(
                _fmt(r, s, 0 if s == "t_switch_ms" else (2 if s.startswith("kappa") else 3))
                for s in STATS
            )
            + " |"
        )
    text = "\n".join(lines) + "\n"
    (results_dir / "robustness.md").write_text(text)
    return text
