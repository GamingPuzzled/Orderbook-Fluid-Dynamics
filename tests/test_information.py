"""Tests for the post-sweep drift (information) analysis."""

from __future__ import annotations

import numpy as np
import polars as pl

from lobflow.information import tercile, vwap_at


def test_vwap_window_and_missing() -> None:
    ts = np.array([0, 500_000, 1_000_000, 4_000_000], dtype=np.int64)
    px = np.array([100.0, 102.0, 104.0, 200.0])
    sz = np.array([1.0, 1.0, 2.0, 1.0])
    out = vwap_at(np.array([1_000_000, 10_000_000], dtype=np.int64), ts, px, sz)
    # [0 s, 2 s] holds the first three trades: (100 + 102 + 2·104) / 4
    assert abs(out[0] - 102.5) < 1e-12
    assert np.isnan(out[1])


def test_tercile_within_day() -> None:
    df = pl.DataFrame({"day": ["a"] * 6 + ["b"] * 3, "x": [1, 2, 3, 4, 5, 6, 30, 10, 20]})
    q = df.with_columns(tercile("x").alias("q"))["q"].to_list()
    assert q == [0, 0, 1, 1, 2, 2, 2, 0, 1]
