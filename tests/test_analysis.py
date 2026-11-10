import numpy as np
import polars as pl
import pytest

from lobflow.analysis import (
    bucket_recovery,
    half_recovery_order,
    order_summary,
    spread_decomposition,
)

FINE = tuple((k, k) for k in range(1, 4))


def _prof(rows: list[tuple[int, int, int, float]]) -> pl.DataFrame:
    """rows: (event_id, tau_ms, d, depth); all observed, mid/spread constant."""
    e, t, d, dep = zip(*rows, strict=True)
    n = len(rows)
    return pl.DataFrame(
        {
            "event_id": e,
            "tau_ms": t,
            "d": d,
            "depth": dep,
            "observed": [True] * n,
            "spread_ticks": [1.0] * n,
            "mid": [100.0] * n,
        }
    )


def _touch_first() -> pl.DataFrame:
    # pre depth 1 at d=1..3; at τ=20 all empty; d=1 recovers at 40, d=3 at 100, d=2 never
    rows = [(0, -1, d, 1.0) for d in (1, 2, 3)]
    rows += [(0, 20, d, 0.0) for d in (1, 2, 3)]
    rows += [(0, 40, 1, 1.0), (0, 40, 2, 0.0), (0, 40, 3, 0.0)]
    rows += [(0, 100, 1, 1.0), (0, 100, 2, 0.2), (0, 100, 3, 0.8)]
    return _prof(rows)


def test_bucket_recovery_ratio_of_sums() -> None:
    r = bucket_recovery(_touch_first(), n_boot=10, buckets=FINE)
    v = {(b, t): x for b, t, x in r.select("bucket", "tau_ms", "R").iter_rows()}
    assert v[("1", 20)] == 0.0 and v[("1", 40)] == 1.0
    assert v[("3", 100)] == pytest.approx(0.8)


def test_half_recovery_and_order() -> None:
    h = half_recovery_order(_touch_first(), buckets=FINE, censor_ms=2000)
    t = dict(h.select("bucket", "t_half").iter_rows())
    assert t == {"1": 40, "2": 2000, "3": 100}
    s = order_summary(h, "1", "3")
    assert s["n"] == 1 and s["p_shallow_first"] == 1.0


def test_undepleted_bucket_excluded() -> None:
    rows = [(0, -1, 1, 1.0), (0, -1, 2, 1.0), (0, 20, 1, 0.0), (0, 20, 2, 1.0), (0, 40, 1, 1.0)]
    rows += [(0, 40, 2, 1.0)]
    h = half_recovery_order(_prof(rows), buckets=FINE)
    assert h["bucket"].to_list() == ["1"]


def test_spread_decomposition_buy() -> None:
    # pre: bid 100, ask 100.5 (mid 100.25, spread 1); τ=20: bid 102, ask 103 (mid 102.5, spread 2)
    prof = pl.DataFrame(
        {
            "event_id": [0, 0],
            "tau_ms": [-1, 20],
            "d": [1, 1],
            "mid": [100.25, 102.5],
            "spread_ticks": [1.0, 2.0],
        }
    )
    info = pl.DataFrame({"event_id": [0], "is_buy": [True], "tick": [0.5]})
    out = spread_decomposition(prof, info).row(0, named=True)
    assert out["opp_adv"] == pytest.approx(4.0)  # bid 100 -> 102
    assert out["swept_disp"] == pytest.approx(5.0)  # ask 100.5 -> 103
    assert out["d_spread"] == pytest.approx(1.0)
    assert np.isfinite(out["spread_ticks"])


def test_composition_recovery_splits_new_and_surviving() -> None:
    from lobflow.analysis import composition_recovery

    # one event, d=1: pre depth 2; τ=20 depth 3 of which surviving bound 1 -> new 2
    prof = pl.DataFrame(
        {
            "event_id": [0, 0],
            "tau_ms": [-1, 20],
            "d": [1, 1],
            "depth": [2.0, 3.0],
            "observed": [True, True],
            "surv_ub": [2.0, 1.0],
            "spread_ticks": [1.0, 1.0],
            "mid": [100.0, 100.0],
        }
    )
    r = composition_recovery(prof, buckets=((1, 1),)).row(0, named=True)
    assert r["R_surv"] == pytest.approx(0.5)
    assert r["R_new"] == pytest.approx(1.0)
    assert r["R_known"] == pytest.approx(1.5)
    assert r["known_share"] == pytest.approx(1.0)


def _flows(rows: list[tuple[int, str, str, str, float]], day: str) -> pl.DataFrame:
    e, w, z, m, v = zip(*rows, strict=True)
    n = len(rows)
    return pl.DataFrame(
        {
            "event_id": e,
            "window": w,
            "side": ["swept"] * n,
            "zone": z,
            "metric": m,
            "value": v,
            "day": [day] * n,
        }
    )


def test_transport_test_repositioning_covers_near_build() -> None:
    from lobflow.analysis import transport_test

    # sweeps: near add 3, far cancel 3 -> conserved repositioning; placebo: tiny symmetric churn
    sw = pl.concat(
        [
            _flows([(k, "20-40", "1-5", "add", 3.0), (k, "20-40", "11-20", "cancel", 3.0)], d)
            for k, d in ((0, "a"), (1, "b"))
        ]
    )
    pb = pl.concat(
        [
            _flows([(k, "20-40", "1-5", "add", 0.1), (k, "20-40", "1-5", "cancel", 0.1)], d)
            for k, d in ((0, "a"), (1, "b"))
        ]
    )
    info = pl.DataFrame(
        {
            "event_id": [0, 1],
            "valid": [True, True],
            "depth_pre_swept": [10.0, 10.0],
            "day": ["a", "b"],
        }
    )
    r = transport_test((sw, info), (pb, info), windows=("20-40",), n_boot=20).row(0, named=True)
    assert r["kappa"] == pytest.approx(1.0)
    assert r["x_near_net"] == pytest.approx(0.3)
    assert r["x_far_net"] == pytest.approx(0.3)
    assert r["cover"] == pytest.approx(1.0)
