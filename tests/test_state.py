import numpy as np
import polars as pl
import pytest

from lobflow.state import matching_weights, nn_weights, state_covariates


def test_state_covariates_windows() -> None:
    s = 1_000_000
    ts = np.array([0, 55 * s, 58 * s, 59 * s, 61 * s], dtype=np.int64)
    px = np.array([100.0, 101.0, 100.0, 100.0, 105.0])
    amt = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    cov = state_covariates(ts, px, amt, np.array([60 * s], dtype=np.int64)).row(0, named=True)
    assert cov["vol_10s"] == pytest.approx(9.0)  # trades at 55, 58, 59 s; 61 s excluded
    assert cov["n_10s"] == 3
    # 1 s grid on [0, 60): price path 100 -> 101 (55 s) -> 100 (58 s)
    assert cov["rv_60s"] == pytest.approx(2 * abs(np.log(101 / 100)))


def test_matching_weights_reproduce_sweep_mix() -> None:
    # bins at sweep median (4.5): sweeps split 50/50; placebo 2 low / 8 high -> reweighted 50/50
    sweep = pl.DataFrame({"x": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]})
    placebo = pl.DataFrame({"x": [1.0, 2.0] + [9.0] * 8})
    w = matching_weights(sweep, placebo, columns=("x",), n_bins=2)
    lo = w.filter(pl.col("x") < 4.5)["w"].sum()
    hi = w.filter(pl.col("x") > 4.5)["w"].sum()
    assert lo / (lo + hi) == pytest.approx(0.5)
    assert w["w"].mean() == pytest.approx(1.0)
    assert w["sweep_coverage"][0] == pytest.approx(1.0)


def test_nn_weights_track_upper_tail() -> None:
    # sweeps all high; placebo mostly low with a few high rows -> weight lands on high rows
    sweep = pl.DataFrame({"x": [10.0, 11.0, 12.0, 13.0]})
    placebo = pl.DataFrame({"x": [0.0] * 20 + [10.5, 12.5]})
    w = nn_weights(sweep, placebo, columns=("x",), k=1)
    assert w.filter(pl.col("x") == 0.0)["w"].sum() == 0.0
    matched = (w["x"] * w["w"]).sum() / w["w"].sum()
    assert matched == pytest.approx(11.5)
    assert w.filter(pl.col("w") > 0)["w"].mean() == pytest.approx(1.0)
