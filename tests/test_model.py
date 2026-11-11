import numpy as np
import pytest

from lobflow.model import Pulse, fit_pulse, split_components, summarize, window_edges


def test_window_edges_sorted() -> None:
    e = window_edges(["40-100", "20-40", "100-250"])
    assert e.tolist() == [20.0, 40.0, 100.0, 250.0]


def test_fit_pulse_recovers_parameters() -> None:
    true = Pulse(0.3, 3.0, 40.0)
    edges = np.array([20, 40, 60, 80, 100, 140, 200, 300, 450, 650, 1000, 3000], dtype=float)
    fit = fit_pulse(edges, np.diff(true.cdf(edges)))
    assert fit.mass == pytest.approx(0.3, rel=0.05)
    assert fit.mean_ms == pytest.approx(120.0, rel=0.05)


def test_summarize_switch_time() -> None:
    early, late = Pulse(1.0, 2.0, 20.0), Pulse(1.0, 4.0, 150.0)
    s = summarize(early, late, Pulse(0.5, 2.0, 30.0))
    assert 100.0 < s["t_switch_ms"] < 400.0
    assert s["transport_share_250ms"] > 0.8


def test_split_components() -> None:
    n = np.array([0.05, 0.03, 0.04])
    j = np.array([0.14, 0.03, -0.01])
    t, w, s = split_components(n, j)
    np.testing.assert_allclose(t, [0.05, 0.03, 0.0])
    np.testing.assert_allclose(w, [0.09, 0.0, 0.0])
    np.testing.assert_allclose(s, [0.0, 0.0, 0.04])


def test_day_window_sums_zone_cut() -> None:
    """Widening the near zone moves a zone's net flow from deep depletion to near build-up."""
    import polars as pl

    from lobflow.model import day_window_sums

    flows = pl.DataFrame(
        {
            "event_id": [0, 0, 0],
            "window": ["0-20"] * 3,
            "side": ["swept"] * 3,
            "zone": ["1-5", "6-10", "51+"],
            "metric": ["add", "cancel", "cancel"],
            "value": [2.0, 1.0, 4.0],
            "day": ["d"] * 3,
        }
    )
    info = pl.DataFrame({"event_id": [0], "valid": [True], "depth_pre_swept": [10.0], "day": ["d"]})
    narrow = day_window_sums(flows, info, None)
    wide = day_window_sums(flows, info, None, ("51+",), ("1-5", "6-10"))
    assert narrow.select("near", "deep").row(0) == (2.0, 5.0)
    assert wide.select("near", "deep").row(0) == (1.0, 4.0)
