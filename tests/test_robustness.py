import polars as pl
import pytest

from lobflow.robustness import kappa_day_sums


def test_kappa_day_sums_groups_fine_windows() -> None:
    rows = [
        # (event, window, metric, value)
        (0, "20-40", "add", 1.0),
        (0, "20-40", "cancel", 2.0),
        (0, "40-60", "add", 3.0),
        (0, "60-100", "cancel", 4.0),
        (1, "40-60", "add", 100.0),  # invalid event, excluded
    ]
    flows = pl.DataFrame(
        {
            "event_id": [r[0] for r in rows],
            "window": [r[1] for r in rows],
            "metric": [r[2] for r in rows],
            "value": [r[3] for r in rows],
            "side": ["swept"] * len(rows),
            "day": ["d"] * len(rows),
        }
    )
    info = pl.DataFrame({"event_id": [0, 1], "valid": [True, False]})
    out = kappa_day_sums(flows, info)
    m = {(r["group"], r["metric"]): r["value"] for r in out.iter_rows(named=True)}
    assert m[("20-40", "add")] == pytest.approx(1.0)
    assert m[("40-100", "add")] == pytest.approx(3.0)
    assert m[("40-100", "cancel")] == pytest.approx(4.0)
