"""Tests for the queue-reactive benchmark."""

from __future__ import annotations

import numpy as np
import polars as pl

from lobflow.queuereactive import Intensity, _state_at


def test_state_interpolates_between_profile_grid() -> None:
    prof = pl.DataFrame(
        {
            "event_id": [1, 1, 1],
            "tau_ms": [-1, 60, 100],
            "near": [9.0, 1.0, 3.0],
            "deep": [9.0, 4.0, 0.0],
        }
    )
    st = _state_at(prof, [60.0, 80.0, 100.0]).sort("t_start")
    assert st["near_q"].to_list() == [1.0, 2.0, 3.0]
    assert st["deep_q"].to_list() == [4.0, 2.0, 0.0]


def test_intensity_cells_and_fallback() -> None:
    rng = np.random.default_rng(0)
    qn = np.concatenate([np.full(100, 0.01), np.full(100, 1.2)])
    qd = np.full(200, 1.2)
    rn = np.where(qn < 0.5, 2.0, 0.5) + rng.normal(0, 0.01, 200)
    rows = pl.DataFrame({"qn": qn, "qd": qd, "rn": rn, "rd": np.zeros(200), "wt": np.ones(200)})
    it = Intensity(min_obs=30).fit(rows)
    r_low, _ = it.rates(np.array([0.01]), np.array([1.2]))
    r_high, _ = it.rates(np.array([1.2]), np.array([1.2]))
    assert abs(r_low[0] - 2.0) < 0.05 and abs(r_high[0] - 0.5) < 0.05
    # unseen deep bin: falls back to the near-only marginal
    r_fb, _ = it.rates(np.array([0.01]), np.array([0.01]))
    assert abs(r_fb[0] - 2.0) < 0.05
