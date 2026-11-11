import numpy as np
import polars as pl
import pytest

from lobflow.convert import infer_tick_size
from lobflow.events import PanelParams, build_event_panel
from lobflow.sweeps import SweepParams, detect_sweeps
from lobflow.tardis import DatasetSpec, first_days

TICK = 0.5


def _trades() -> pl.DataFrame:
    rows = [
        # small single-level buys
        (1_000_000, 1_000_100, "buy", 100.5, 1.0),
        (1_100_000, 1_100_100, "buy", 100.5, 1.0),
        # big buy sweep at t=2.0s through 100.5..101.5 (3 levels)
        (2_000_000, 2_000_100, "buy", 100.5, 2.0),
        (2_000_000, 2_000_100, "buy", 101.0, 3.0),
        (2_000_000, 2_000_100, "buy", 101.5, 4.0),
        # small 3-level sell sweep 200 ms later (candidate, not large)
        (2_200_000, 2_200_100, "sell", 100.0, 0.1),
        (2_200_000, 2_200_100, "sell", 99.5, 0.1),
        (2_200_000, 2_200_100, "sell", 99.0, 0.1),
    ]
    ts, lts, side, px, amt = zip(*rows, strict=True)
    return pl.DataFrame(
        {"timestamp": ts, "local_timestamp": lts, "side": side, "price": px, "amount": amt}
    )


def test_detect_sweeps_filters() -> None:
    runs = detect_sweeps(_trades(), TICK, SweepParams(min_levels=3, size_quantile=0.5))
    sel = runs.filter(pl.col("selected"))
    assert sel.height == 1
    r = sel.row(0, named=True)
    assert r["side"] == "buy" and r["n_levels"] == 3 and r["ticks_spanned"] == 2
    assert r["volume"] == pytest.approx(9.0)
    # sell sweep is a candidate but fails size filter and isolation
    sell = runs.filter(pl.col("side") == "sell").row(0, named=True)
    assert sell["is_candidate"] and not sell["isolated"] and not sell["selected"]


def _book_arrays() -> dict[str, np.ndarray]:
    # pre: bids 100.0, 99.5 ; asks 100.5..103.0 each size 1
    rows: list[tuple[int, bool, bool, float, float]] = []
    rows += [(0, True, True, 100.0, 5.0), (0, True, True, 99.5, 5.0)]
    rows += [(0, True, False, 100.5 + 0.5 * k, 1.0) for k in range(6)]
    # sweep arrives on book feed at 2.000050s: asks 100.5,101.0,101.5 cleared
    rows += [(2_000_050, False, False, p, 0.0) for p in (100.5, 101.0, 101.5)]
    # +30 ms: maker posts at old touch 100.5 (source-like refill at j=1)
    rows += [(2_030_100, False, False, 100.5, 0.7)]
    ts, snap, bid, px, amt = zip(*rows, strict=True)
    return {
        "ts": np.array(ts, dtype=np.int64),
        "is_snapshot": np.array(snap),
        "is_bid": np.array(bid),
        "price": np.array(px),
        "amount": np.array(amt),
    }


def test_event_panel_geometry_and_refill() -> None:
    sweeps = detect_sweeps(_trades(), TICK, SweepParams(size_quantile=0.5)).filter(
        pl.col("selected")
    )
    events, panel = build_event_panel(
        _book_arrays(), sweeps, TICK, PanelParams(taus_ms=(20, 40), margin_ticks=2, n_levels=10)
    )
    ev = events.row(0, named=True)
    assert ev["L_gap"] == 3 and ev["cleared_frac"] == pytest.approx(1.0)
    assert ev["mid_pre"] == pytest.approx(100.25)
    # j grid: -1..5 ; j=1 is price 100.5
    pre = panel.filter(pl.col("tau_ms") == -1).sort("j")
    assert pre["j"].to_list() == [-1, 0, 1, 2, 3, 4, 5]
    assert pre.filter(pl.col("j") == 1)["price"][0] == pytest.approx(100.5)
    # inside-spread grid points are 0, not NaN
    assert pre.filter(pl.col("j") == 0)["depth"][0] == 0.0
    # opposite side (bids) on the same grid: 99.5 and 100.0 hold 5 each; above best bid -> 0
    assert pre.filter(pl.col("j") <= 0)["depth_opp"].to_list() == [5.0, 5.0]
    assert pre.filter(pl.col("j") == 2)["depth_opp"][0] == 0.0
    assert pre.filter(pl.col("j") == 5)["depth"][0] == 1.0  # 102.5 within sampled range
    t20 = panel.filter(pl.col("tau_ms") == 20).sort("j")
    assert t20.filter(pl.col("in_gap"))["depth"].to_list() == [0.0, 0.0, 0.0]
    t40 = panel.filter(pl.col("tau_ms") == 40).sort("j")
    assert t40.filter(pl.col("j") == 1)["depth"][0] == pytest.approx(0.7)
    assert t40.filter(pl.col("j") == 4)["depth"][0] == pytest.approx(1.0)


def test_sell_side_geometry() -> None:
    trades = pl.DataFrame(
        {
            "timestamp": [5_000_000] * 3,
            "local_timestamp": [5_000_100] * 3,
            "side": ["sell"] * 3,
            "price": [100.0, 99.5, 99.0],
            "amount": [1.0, 1.0, 1.0],
        }
    )
    rows = [(0, True, True, 100.0 - 0.5 * k, 1.0) for k in range(6)]
    rows += [(0, True, False, 100.5, 1.0)]
    ts, snap, bid, px, amt = zip(*rows, strict=True)
    arrays = {
        "ts": np.array(ts, dtype=np.int64),
        "is_snapshot": np.array(snap),
        "is_bid": np.array(bid),
        "price": np.array(px),
        "amount": np.array(amt),
    }
    sweeps = detect_sweeps(trades, TICK, SweepParams(size_quantile=0.0)).filter(pl.col("selected"))
    events, panel = build_event_panel(
        arrays, sweeps, TICK, PanelParams(taus_ms=(20,), margin_ticks=1)
    )
    assert events["L_gap"][0] == 3
    pre = panel.filter(pl.col("tau_ms") == -1).sort("j")
    assert pre["price"].to_list() == [100.5, 100.0, 99.5, 99.0, 98.5]
    assert pre["x_fixed"][1] == pytest.approx(-0.5)


def test_infer_tick_and_first_days() -> None:
    assert infer_tick_size(np.array([100.0, 100.1, 100.3, 99.9])) == pytest.approx(0.1)
    from datetime import date

    assert first_days(date(2025, 11, 15), date(2026, 2, 1)) == [
        date(2025, 12, 1),
        date(2026, 1, 1),
        date(2026, 2, 1),
    ]
    with pytest.raises(ValueError):
        DatasetSpec("bybit", "trades", date(2026, 1, 2), "BTCUSDT")


def test_truncated_feed_marks_unobserved_as_nan() -> None:
    sweeps = detect_sweeps(_trades(), TICK, SweepParams(size_quantile=0.5)).filter(
        pl.col("selected")
    )
    # only 4 ask levels sampled: deepest observed pre-shock ask is 102.0
    _, panel = build_event_panel(
        _book_arrays(), sweeps, TICK, PanelParams(taus_ms=(20,), margin_ticks=2, n_levels=4)
    )
    pre = panel.filter(pl.col("tau_ms") == -1).sort("j")
    assert pre.filter(pl.col("j") == 4)["depth"][0] == 1.0  # 102.0 observed
    assert np.isnan(pre.filter(pl.col("j") == 5)["depth"][0])  # 102.5 beyond top-4


def test_infer_tick_ignores_rare_off_grid_prices() -> None:
    from lobflow.convert import infer_tick_size

    rng = np.random.default_rng(0)
    on_grid = np.round(43_000 + rng.integers(0, 5000, 100_000) * 0.1, 1)
    stray = np.array([43_000.01, 43_123.47])  # two updates one cent off the 0.1 grid
    assert infer_tick_size(np.concatenate([on_grid, stray])) == pytest.approx(0.1)
    assert infer_tick_size(np.round(20_000 + rng.integers(0, 4000, 50_000) * 0.5, 1)) == 0.5
