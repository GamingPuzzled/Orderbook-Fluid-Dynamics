"""Pre-event market-state covariates and placebo reweighting (state-matched placebo).

Covariates at time t (trades only, strictly before t):

- ``vol_10s``  traded volume in [t − 10 s, t);
- ``rv_60s``   realised variation: Σ |Δ log last-trade price| on a 1 s grid over [t − 60 s, t);
- ``n_10s``    number of trades in [t − 10 s, t).

Combined with ``depth_pre_swept`` (from ``flows``), these define strata; placebo events are
reweighted so their stratum distribution matches the sweeps' (coarsened exact matching
weights). Because all statistics are ratios of sums, a weight w scales an event's flows and
its pre-shock depth alike.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
import polars as pl

I64 = npt.NDArray[np.int64]
F64 = npt.NDArray[np.float64]

COVARIATES: tuple[str, ...] = ("vol_10s", "rv_60s", "n_10s")


def state_covariates(trades_ts: I64, trades_px: F64, trades_amt: F64, t: I64) -> pl.DataFrame:
    """Covariates for each time in ``t`` (trades must be sorted by time)."""
    if np.any(np.diff(trades_ts) < 0):
        raise ValueError("trades_ts must be non-decreasing")
    cum_vol = np.concatenate([[0.0], np.cumsum(trades_amt)])
    lo = np.searchsorted(trades_ts, t - 10_000_000, side="left")
    hi = np.searchsorted(trades_ts, t, side="left")
    vol = cum_vol[hi] - cum_vol[lo]
    n = (hi - lo).astype(np.int64)
    grid = t[:, None] - np.arange(60, -1, -1, dtype=np.int64)[None, :] * 1_000_000
    idx = np.searchsorted(trades_ts, grid, side="left") - 1  # last trade strictly before
    px = np.where(idx >= 0, trades_px[np.clip(idx, 0, None)], np.nan)
    rv = np.nansum(np.abs(np.diff(np.log(px), axis=1)), axis=1)
    return pl.DataFrame({"vol_10s": vol, "rv_60s": rv, "n_10s": n})


def matching_weights(
    sweep_cov: pl.DataFrame,
    placebo_cov: pl.DataFrame,
    *,
    columns: Sequence[str] = ("vol_10s", "rv_60s", "depth_pre_swept"),
    n_bins: int = 4,
) -> pl.DataFrame:
    """Coarsened-exact-matching weights for placebo rows.

    Bins: quantiles of the *sweep* distribution per column (``n_bins`` each). Placebo weight
    in cell c = (sweep share of c) / (placebo share of c); placebo rows in cells without
    sweeps get 0. Returns ``placebo_cov`` with ``cell`` and ``w`` columns (mean weight 1 over
    matched rows). Also reports coverage: share of sweeps whose cell has placebo support,
    as column ``sweep_coverage`` (constant).
    """

    def cells(df: pl.DataFrame) -> pl.Series:
        code = pl.lit(0, dtype=pl.Int64)
        for col in columns:
            qs = np.quantile(sweep_cov[col].to_numpy(), np.linspace(0, 1, n_bins + 1)[1:-1])
            b = np.searchsorted(qs, df[col].to_numpy(), side="right")
            code = code * n_bins + pl.Series(b.astype(np.int64))
        return pl.select(code.alias("cell")).to_series()

    s_cell = cells(sweep_cov)
    p_cell = cells(placebo_cov)
    s_share = s_cell.value_counts(normalize=True, name="s")
    p_share = p_cell.value_counts(normalize=True, name="p")
    ratio = s_share.join(p_share, on="cell", how="inner").with_columns(
        (pl.col("s") / pl.col("p")).alias("w")
    )
    coverage = float(ratio["s"].sum())
    out = (
        placebo_cov.with_columns(p_cell.alias("cell"))
        .join(ratio.select("cell", "w"), on="cell", how="left")
        .with_columns(pl.col("w").fill_null(0.0))
    )
    mean_w = out.filter(pl.col("w") > 0)["w"].mean()
    scale = 1.0 / float(mean_w) if isinstance(mean_w, (int, float)) and mean_w > 0 else 1.0
    return out.with_columns(pl.col("w") * scale, pl.lit(coverage).alias("sweep_coverage"))
