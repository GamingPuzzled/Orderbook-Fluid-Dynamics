"""Tests for follow-up execution costs."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from lobflow.execution import costs, walk_cost


def test_walk_cost_fills_levels_in_order_and_charges_shortfall() -> None:
    depth = np.array([[1.0, 2.0, 0.0], [0.0, 0.0, 0.5]])
    dbar, short = walk_cost(depth, 2.0)
    # row 0: 1 @ d=1 + 1 @ d=2 -> 1.5 ; row 1: 0.5 @ d=3 + 1.5 @ d=4 (beyond) -> 3.75
    np.testing.assert_allclose(dbar, [1.5, 3.75])
    np.testing.assert_allclose(short, [0.0, 0.75])
    with pytest.raises(ValueError):
        walk_cost(depth, 0.0)


def test_costs_relative_to_mid_in_bps() -> None:
    mat = pl.DataFrame(
        {
            "event_id": [0],
            "tau_ms": [20],
            "depth": [[1.0] + [0.0] * 49],
            "spread_ticks": [1.0],
            "mid": [100.0],
            "day": ["d"],
        }
    )
    out = costs(mat, {"d": 0.01}, [1.0])
    # fill at d = 1 tick from the opposite quote = 0.5 tick from the mid = 0.005 / 100 = 0.5 bp
    assert out["cost_bps_q0"][0] == pytest.approx(0.5)
    assert out["short_q0"][0] == 0.0
