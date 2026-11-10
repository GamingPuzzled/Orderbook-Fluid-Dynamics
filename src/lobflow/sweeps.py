"""Detect aggressive multi-level sweeps from trade prints.

An *aggressor run* is the set of trades sharing (exchange timestamp, aggressor side). On
matching engines that stamp all fills of one taker order with the same timestamp this
recovers individual sweeping orders without fixed time buckets (which split sweeps at bucket
edges). Distinct taker orders in the same millisecond on the same side are merged; this is a
known, documented limitation.
"""

from __future__ import annotations

from dataclasses import dataclass

import polars as pl


@dataclass(frozen=True)
class SweepParams:
    min_levels: int = 3  # distinct price levels consumed
    size_quantile: float = 0.95  # volume quantile among candidate sweeps in the sample
    isolation_us: int = 500_000  # no other candidate sweep within this window before t0


def aggressor_runs(trades: pl.DataFrame, tick: float) -> pl.DataFrame:
    """Collapse trades into aggressor runs keyed by (timestamp, side)."""
    if tick <= 0:
        raise ValueError("tick must be positive")
    return (
        trades.filter(pl.col("side").is_in(["buy", "sell"]))
        .group_by(["timestamp", "side"], maintain_order=True)
        .agg(
            pl.col("local_timestamp").min().alias("local_ts"),
            pl.col("price").min().alias("p_min"),
            pl.col("price").max().alias("p_max"),
            pl.col("price").first().alias("p_first"),
            pl.col("price").last().alias("p_last"),
            pl.col("price").n_unique().alias("n_levels"),
            pl.col("amount").sum().alias("volume"),
            (pl.col("price") * pl.col("amount")).sum().alias("notional"),
            pl.len().alias("n_trades"),
        )
        .with_columns(
            ((pl.col("p_max") - pl.col("p_min")) / tick)
            .round(0)
            .cast(pl.Int64)
            .alias("ticks_spanned"),
            (pl.col("notional") / pl.col("volume")).alias("vwap"),
        )
        .sort("timestamp")
    )


def detect_sweeps(
    trades: pl.DataFrame, tick: float, params: SweepParams | None = None
) -> pl.DataFrame:
    """Return isolated, large multi-level sweeps with diagnostic columns.

    Columns added: ``is_candidate``, ``size_threshold``, ``gap_prev_us``, ``isolated``,
    ``selected``. The full run table is returned so filters can be audited; use
    ``.filter(pl.col("selected"))`` for the event list.
    """
    p = params or SweepParams()
    runs = aggressor_runs(trades, tick)
    runs = runs.with_columns((pl.col("n_levels") >= p.min_levels).alias("is_candidate"))
    cand = runs.filter(pl.col("is_candidate"))
    if cand.height == 0:
        return runs.with_columns(
            pl.lit(None, dtype=pl.Float64).alias("size_threshold"),
            pl.lit(None, dtype=pl.Int64).alias("gap_prev_us"),
            pl.lit(False).alias("isolated"),
            pl.lit(False).alias("selected"),
        )
    thr = float(cand["volume"].quantile(p.size_quantile, interpolation="linear") or 0.0)
    # Gap to previous candidate (any size) on the exchange clock.
    cand = cand.with_columns(pl.col("timestamp").diff().alias("gap_prev_us"))
    runs = runs.join(
        cand.select("timestamp", "side", "gap_prev_us"), on=["timestamp", "side"], how="left"
    )
    return runs.with_columns(
        pl.lit(thr).alias("size_threshold"),
        (pl.col("gap_prev_us").is_null() | (pl.col("gap_prev_us") > p.isolation_us)).alias(
            "isolated"
        ),
    ).with_columns(
        (pl.col("is_candidate") & (pl.col("volume") >= thr) & pl.col("isolated")).alias("selected")
    )
