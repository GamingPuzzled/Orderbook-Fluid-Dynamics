"""Does repositioning depend on the relative tick size within an asset? (tick-size test)

Across assets, repositioning is large on the small-tick BTC and ETH books and near zero on
the large-tick SOL, XRP and LINK books, but assets also differ in depth and participants.
Within an asset, the tick relative to price varies from day to day with the price level (and
with exchange tick changes), so a within-asset regression separates the tick from the asset.

Per asset and day: three-component statistics of excess (sweep − NN-matched placebo) flows,
as in :mod:`lobflow.robustness`, with the near zone at d ≤ 5 ticks; the median tick in basis
points of the pre-sweep mid; and the median pre-sweep swept-side depth in quote currency.
Regression (weighted by sweeps per day): statistic on log10 tick (bp) with asset fixed
effects, optionally controlling for log10 depth. Standard errors: heteroskedasticity-robust
(HC1) and a day bootstrap stratified by asset.

The price level moves with time, so the tick effect is not separated from slow changes in
market structure; the tick changes (BTC 0.5 → 0.1, SOL 0.01 → 0.001) are the cleanest
within-asset variation.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl

from lobflow.robustness import match_within_day, prepare_subsets, subset_point_fn

F64 = npt.NDArray[np.float64]
Y_STATS = ("transport_<250ms", "withdrawal_<250ms", "source_>250ms", "kappa_20-40")
MIN_SWEEPS = 10
SMALL_TICK = ("BTCUSDT", "ETHUSDT")  # where repositioning is large enough to vary


def day_panel(out_dir: Path, asset: str, *, max_push_ms: float = 20.0, k: int = 5) -> pl.DataFrame:
    """One row per usable day: statistics, tick (bp), tick (price units), depth, sweeps."""
    si = prepare_subsets(out_dir, max_push_ms=max_push_ms)
    w = match_within_day(si.s_cov, si.p_cov, method="nn", k=k)
    one, days = subset_point_fn(si.s_flows, si.s_info, si.p_flows, si.p_info, w, si.windows)
    ev = (
        si.events.join(
            si.s_info.filter(pl.col("valid")).select("event_id", "depth_pre_swept"),
            on="event_id",
        )
        .group_by("day")
        .agg(
            (pl.col("tick") / pl.col("mid_pre") * 1e4).median().alias("tick_bp"),
            pl.col("tick").first().alias("tick"),
            (pl.col("depth_pre_swept") * pl.col("mid_pre")).median().alias("depth_quote"),
            pl.len().alias("n_sweeps"),
        )
    )
    rows = [{"day": d, **{s: one([d])[s] for s in Y_STATS}} for d in days]
    return (
        pl.DataFrame(rows)
        .join(ev, on="day")
        .filter(pl.col("n_sweeps") >= MIN_SWEEPS)
        .with_columns(pl.lit(asset).alias("asset"))
    )


@dataclass(frozen=True)
class Fit:
    beta: float  # coefficient on log10 tick
    se_hc1: float
    lo: float  # bootstrap 95% interval
    hi: float
    n_days: int


def _design(panel: pl.DataFrame, controls: Sequence[str]) -> F64:
    assets = sorted(panel["asset"].unique().to_list())
    cols = [np.log10(panel["tick_bp"].to_numpy())]
    cols += [np.log10(panel[c].to_numpy()) for c in controls]
    cols += [(panel["asset"] == a).to_numpy().astype(float) for a in assets]
    return np.column_stack(cols)


def wls(x: F64, y: F64, wt: F64) -> tuple[F64, F64]:
    """Weighted least squares; (coefficients, HC1 standard errors)."""
    sw = np.sqrt(wt)
    xw, yw = x * sw[:, None], y * sw
    beta, *_ = np.linalg.lstsq(xw, yw, rcond=None)
    resid = yw - xw @ beta
    bread = np.linalg.pinv(xw.T @ xw)
    meat = (xw * resid[:, None] ** 2).T @ xw
    n, p = x.shape
    cov = bread @ meat @ bread * n / max(n - p, 1)
    return beta, np.sqrt(np.diag(cov))


def fit(
    panel: pl.DataFrame,
    stat: str,
    *,
    controls: Sequence[str] = (),
    n_boot: int = 500,
    seed: int = 0,
) -> Fit:
    """Within-asset slope of ``stat`` on log10 tick (bp), weighted by sweeps per day."""
    p = panel.filter(pl.col(stat).is_finite())
    x, y, wt = _design(p, controls), p[stat].to_numpy(), p["n_sweeps"].to_numpy().astype(float)
    beta, se = wls(x, y, wt)
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero((p["asset"] == a).to_numpy()) for a in p["asset"].unique()]
    draws = []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(g, size=len(g)) for g in groups])
        b, _ = wls(x[idx], y[idx], wt[idx])
        draws.append(b[0])
    lo, hi = np.percentile(draws, [2.5, 97.5])
    return Fit(float(beta[0]), float(se[0]), float(lo), float(hi), p.height)


def run_ticksize(
    events_root: Path,
    results_dir: Path,
    assets: Sequence[tuple[str, str]],
    *,
    max_push_ms: float = 20.0,
    n_boot: int = 500,
) -> str:
    """Pool day panels for ``assets`` ((exchange, symbol) pairs); writes ``ticksize.md``,
    ``ticksize_panel.parquet`` and ``ticksize.parquet`` to ``results_dir``."""
    panel = pl.concat(
        [day_panel(events_root / e / s, s, max_push_ms=max_push_ms) for e, s in assets]
    )
    samples = {"all assets": panel}
    small = panel.filter(pl.col("asset").is_in(list(SMALL_TICK)))
    if small["asset"].n_unique() > 0 and small.height < panel.height:
        samples["BTC + ETH"] = small
    rows = []
    for sample, sub in samples.items():
        for stat in Y_STATS:
            for label, controls in (("asset FE", ()), ("asset FE + depth", ("depth_quote",))):
                f = fit(sub, stat, controls=controls, n_boot=n_boot)
                rows.append({"sample": sample, "stat": stat, "spec": label, **f.__dict__})
    results_dir.mkdir(parents=True, exist_ok=True)
    panel.write_parquet(results_dir / "ticksize_panel.parquet")
    table = pl.DataFrame(rows)
    table.write_parquet(results_dir / "ticksize.parquet")

    by_tick = (
        panel.group_by("asset", "tick")
        .agg(
            pl.len().alias("days"),
            pl.col("tick_bp").median(),
            (
                (pl.col("transport_<250ms") * pl.col("n_sweeps")).sum() / pl.col("n_sweeps").sum()
            ).alias("transport"),
        )
        .sort("asset", "tick")
    )
    lines = [
        "# Repositioning and the relative tick size within assets",
        "",
        "Day-level excess statistics (NN placebo, near zone d ≤ 5 ticks) regressed on log10 "
        f"median tick (bp of mid), with asset fixed effects; days with ≥ {MIN_SWEEPS} sweeps, "
        "weighted by sweeps. β = change per tenfold increase in the relative tick. HC1 SE and "
        "95% day bootstrap (stratified by asset).",
        "",
        f"Assets: {', '.join(s for _, s in assets)}; days: {panel.height}.",
        "",
        "| sample | statistic | specification | β (per 10× tick) | HC1 SE | 95% bootstrap | days |",
        "|---|---|---|---|---|---|---|",
        *[
            f"| {r['sample']} | {r['stat']} | {r['spec']} | {r['beta']:+.3f} | {r['se_hc1']:.3f} | "
            f"[{r['lo']:+.3f}, {r['hi']:+.3f}] | {r['n_days']} |"
            for r in table.iter_rows(named=True)
        ],
        "",
        "## By exchange tick (sweep-weighted repositioning < 250 ms)",
        "",
        "| asset | tick | days | median tick (bp) | repositioning |",
        "|---|---|---|---|---|",
        *[
            f"| {r['asset']} | {r['tick']:g} | {r['days']} | {r['tick_bp']:.3f} | "
            f"{r['transport']:.3f} |"
            for r in by_tick.iter_rows(named=True)
        ],
    ]
    text = "\n".join(lines) + "\n"
    (results_dir / "ticksize.md").write_text(text)
    return text
