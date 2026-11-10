import numpy as np
import polars as pl
import pytest

from lobflow.profiles import placebo_times, profile_panel

TICK = 0.5


def _arrays(rows: list[tuple[int, bool, bool, float, float]]) -> dict[str, np.ndarray]:
    ts, snap, bid, px, amt = zip(*rows, strict=True)
    return {
        "ts": np.array(ts, dtype=np.int64),
        "is_snapshot": np.array(snap),
        "is_bid": np.array(bid),
        "price": np.array(px),
        "amount": np.array(amt),
    }


def _book() -> dict[str, np.ndarray]:
    rows = [(0, True, True, 100.0, 5.0), (0, True, True, 99.5, 5.0)]
    rows += [(0, True, False, 100.5 + 0.5 * k, 1.0) for k in range(6)]  # asks d=1..6
    # t=1000us: buy sweep clears 100.5..101.5; bids move up to 101.0
    rows += [(1000, False, False, p, 0.0) for p in (100.5, 101.0, 101.5)]
    rows += [(1000, False, True, 101.0, 2.0)]
    # t=30ms: new ask posted at 101.5 (d=1 relative to new best bid 101.0)
    rows += [(30_000, False, False, 101.5, 0.4)]
    return _arrays(rows)


def test_buy_profile_moves_with_price() -> None:
    panel = profile_panel(
        _book(), np.array([1000], dtype=np.int64), np.array([True]), TICK, (20, 40), max_d=8
    )
    pre = panel.filter(pl.col("tau_ms") == -1).sort("d")
    assert pre["depth"].to_list()[:6] == [1.0] * 6
    assert pre["observed"].to_list()[6:] == [False, False]
    assert pre["spread_ticks"][0] == pytest.approx(1.0)
    # τ=20ms: best bid 101.0; remaining asks 102.0..103.0 at d = 2, 3, 4; d=1 empty
    p20 = panel.filter(pl.col("tau_ms") == 20).sort("d")
    assert p20["depth"].to_list()[:4] == [0.0, 1.0, 1.0, 1.0]
    assert p20["spread_ticks"][0] == pytest.approx(2.0)
    # τ=40ms: touch refilled at d=1
    p40 = panel.filter(pl.col("tau_ms") == 40).sort("d")
    assert p40["depth"][0] == pytest.approx(0.4)


def test_sell_profile_symmetry() -> None:
    rows = [(0, True, False, 100.5, 5.0)]
    rows += [(0, True, True, 100.0 - 0.5 * k, 2.0) for k in range(4)]  # bids d=1..4
    panel = profile_panel(
        _arrays(rows), np.array([10], dtype=np.int64), np.array([False]), TICK, (20,), max_d=5
    )
    pre = panel.filter(pl.col("tau_ms") == -1).sort("d")
    assert pre["depth"].to_list()[:4] == [2.0] * 4
    assert not pre["observed"][4]


def test_placebo_excludes_window() -> None:
    ex = np.array([5_000_000, 9_000_000], dtype=np.int64)
    t = placebo_times(0, 20_000_000, 200, ex, exclude_window_us=1_000_000, seed=1)
    assert t.size == 200
    assert np.all(np.min(np.abs(t[:, None] - ex[None, :]), axis=1) > 1_000_000)


def test_surviving_bound_running_min() -> None:
    panel = profile_panel(
        _book(), np.array([1000], dtype=np.int64), np.array([True]), TICK, (20, 40), max_d=8
    )
    get = {
        (t, d): (dep, s)
        for t, d, dep, s in panel.select("tau_ms", "d", "depth", "surv_ub").iter_rows()
    }
    # τ=20: asks 102.0..103.0 (d=2..4) untouched since pre -> fully surviving
    assert get[(20, 2)] == (1.0, 1.0)
    # τ=40: 101.5 (d=1) was swept to 0 at τ=20, now 0.4 -> surviving bound 0, all new
    assert get[(40, 1)] == (pytest.approx(0.4), 0.0)
    # beyond pre-shock deepest ask (103.0): d=6 at τ=40 is price 104.0 -> unknown
    assert np.isnan(get[(40, 6)][1])
