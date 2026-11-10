import numpy as np
import polars as pl
import pytest

from lobflow.flows import flow_panel

TICK = 0.5


def _arrays(rows: list[tuple[int, bool, bool, float, float]]) -> dict[str, np.ndarray]:
    ts, snap, bid, px, amt = zip(*rows, strict=True)
    return {
        "ts": np.array(ts, dtype=np.int64),
        "is_snapshot": np.array(snap),
        "is_bid": np.array(bid),
        "price": np.array(px, dtype=np.float64),
        "amount": np.array(amt, dtype=np.float64),
    }


def _scenario() -> tuple[dict[str, np.ndarray], tuple[np.ndarray, ...]]:
    # top-4 window per side. bids 100.0, 99.5; asks 100.5..102.0 (d = 1..4 from bid 100.0)
    rows = [(0, True, True, 100.0, 5.0), (0, True, True, 99.5, 5.0)]
    rows += [(0, True, False, 100.5 + 0.5 * k, 1.0) for k in range(4)]
    t0 = 1_000_000
    # t0: buy sweep fills 100.5 and 101.0; window refills with 102.5, 103.0 (edge_in)
    rows += [(t0, False, False, 100.5, 0.0), (t0, False, False, 101.0, 0.0)]
    rows += [(t0, False, False, 102.5, 1.0), (t0, False, False, 103.0, 1.0)]
    # t0+25ms: far ask 103.0 cancelled (d = 6 from bid 100.0); window refills 103.5 (edge_in)
    rows += [(t0 + 25_000, False, False, 103.0, 0.0), (t0 + 25_000, False, False, 103.5, 1.0)]
    # t0+30ms: touch add at new price 101.0 (d = 2) pushes 103.5 out (edge_out)
    rows += [(t0 + 30_000, False, False, 101.0, 0.7), (t0 + 30_000, False, False, 103.5, 0.0)]
    # t0+50ms: add at 100.5 pushes deepest 102.5 out of the 4-level window (edge_out)
    rows += [(t0 + 50_000, False, False, 100.5, 0.3), (t0 + 50_000, False, False, 102.5, 0.0)]
    trades = (
        np.array([t0, t0], dtype=np.int64),
        np.array([100.5, 101.0]),
        np.array([1.0, 1.0]),
        np.array([True, True]),
    )
    return _arrays(rows), trades


def _run(**kw: object) -> tuple[pl.DataFrame, pl.DataFrame]:
    arrays, (tts, tpx, tam, tbuy) = _scenario()
    return flow_panel(
        arrays,
        tts,
        tpx,
        tam,
        tbuy,
        np.array([1_000_000], dtype=np.int64),
        np.array([True]),
        TICK,
        edges_ms=(0, 20, 40, 100),
        n_levels=4,
        **kw,  # type: ignore[arg-type]
    )


def _get(flows: pl.DataFrame, **f: str) -> float:
    q = flows
    for k, v in f.items():
        q = q.filter(pl.col(k) == v)
    return float(q["value"].sum())


def test_classification() -> None:
    flows, info = _run()
    sw = {"side": "swept"}
    assert _get(flows, window="0-20", metric="fill", **sw) == pytest.approx(2.0)
    assert _get(flows, window="0-20", metric="edge_in", **sw) == pytest.approx(2.0)
    assert _get(flows, window="20-40", metric="cancel", zone="6-10", **sw) == pytest.approx(1.0)
    assert _get(flows, window="20-40", metric="add", zone="1-5", **sw) == pytest.approx(0.7)
    assert _get(flows, window="20-40", metric="add_cofar", **sw) == 0.0  # far = d >= 11
    assert _get(flows, window="20-40", metric="edge_in", **sw) == pytest.approx(1.0)
    assert _get(flows, window="20-40", metric="edge_out", **sw) == pytest.approx(1.0)
    assert _get(flows, window="40-100", metric="edge_out", **sw) == pytest.approx(1.0)
    assert _get(flows, window="40-100", metric="add", **sw) == pytest.approx(0.3)
    assert _get(flows, metric="cancel", window="0-20", **sw) == 0.0
    r = info.row(0, named=True)
    assert r["valid"] and r["depth_pre_swept"] == pytest.approx(4.0)
    assert r["traded_swept_0-20"] == pytest.approx(2.0)
    assert r["filled_swept_0-20"] == pytest.approx(2.0)


def test_mass_balance_identity() -> None:
    flows, info = _run()
    s = flows.filter(pl.col("side") == "swept")
    tot = {m: _get(s, metric=m) for m in ("add", "cancel", "fill", "edge_in", "edge_out")}
    net = tot["add"] + tot["edge_in"] - tot["cancel"] - tot["fill"] - tot["edge_out"]
    # final asks: 100.5 (0.3), 101.0 (0.7), 101.5, 102.0 (1 each) = 3.0; pre = 4.0
    assert net == pytest.approx(3.0 - info["depth_pre_swept"][0])


def test_unmatched_removal_is_cancel_without_trades() -> None:
    arrays, _ = _scenario()
    empty = np.array([], dtype=np.int64)
    flows, _ = flow_panel(
        arrays,
        empty,
        np.array([]),
        np.array([]),
        np.array([], dtype=bool),
        np.array([1_000_000], dtype=np.int64),
        np.array([True]),
        TICK,
        edges_ms=(0, 20),
        n_levels=4,
    )
    assert _get(flows, metric="fill") == 0.0
    assert _get(flows, metric="cancel", side="swept") == pytest.approx(2.0)


def test_snapshot_in_window_invalidates() -> None:
    arrays, (tts, tpx, tam, tbuy) = _scenario()
    arrays["is_snapshot"][-1] = True
    _, info = flow_panel(
        arrays,
        tts,
        tpx,
        tam,
        tbuy,
        np.array([1_000_000], dtype=np.int64),
        np.array([True]),
        TICK,
        edges_ms=(0, 20, 40, 100),
        n_levels=4,
    )
    assert not info["valid"][0]


def test_hidden_trade_volume_does_not_absorb_later_cancel() -> None:
    # bid 100 (5); ask 100.5 (1). Buy trade of 3 at 100.5 (2 hidden). At 30 ms ask 100.5 is
    # re-posted (0.8) and at 60 ms cancelled: must count as cancel, not fill.
    rows = [(0, True, True, 100.0, 5.0), (0, True, False, 100.5, 1.0), (0, True, False, 101.0, 1.0)]
    rows += [(1000, False, False, 100.5, 0.0), (30_000, False, False, 100.5, 0.8)]
    rows += [(60_000, False, False, 100.5, 0.0)]
    flows, _ = flow_panel(
        _arrays(rows),
        np.array([1000], dtype=np.int64),
        np.array([100.5]),
        np.array([3.0]),
        np.array([True]),
        np.array([1000], dtype=np.int64),
        np.array([True]),
        TICK,
        edges_ms=(0, 20, 100),
        n_levels=10,
    )
    assert _get(flows, metric="fill", side="swept") == pytest.approx(1.0)
    assert _get(flows, metric="cancel", side="swept") == pytest.approx(0.8)
