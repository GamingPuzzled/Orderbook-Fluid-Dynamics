"""Tests for the Bitstamp order-level (L3) analysis."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import polars as pl

from lobflow import l3


def test_key_exact_decimal() -> None:
    assert l3._key("74539.05", l3.CENT) == 7453905
    assert l3._key("0.00031831", l3.SAT) == 31831
    assert l3._key("1.5", l3.SAT) == 150_000_000
    assert l3._key("12", l3.CENT) == 1200


def test_book_best_and_prune_stale_snapshot_orders() -> None:
    b = l3.Book()
    b.add(1, 0, 100, 5)  # bid 1.00
    b.add(2, 1, 102, 5)  # ask 1.02 (stale snapshot order)
    b.add(3, 1, 104, 5)
    b.stale_candidates = {1, 2, 3}
    assert (b.best(0), b.best(1)) == (100, 102)
    b.add(10, 0, 103, 1)  # stream bid crosses the stale ask
    b.stale_candidates.discard(10)
    b.prune_crossed()
    assert (b.best(0), b.best(1)) == (103, 104)
    assert b.n_pruned == 1 and 2 not in b.orders
    b.remove(10)
    assert b.best(0) == 100
    # a crossing between stream-seen orders is left alone (transient marketable order)
    b.stale_candidates.discard(3)
    b.add(11, 0, 105, 1)
    b.prune_crossed()
    assert b.best(0) == 105 and 3 in b.orders


def _write_raw(path: Path, msgs: list[dict[str, object]], recv0: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        for i, m in enumerate(msgs):
            fh.write(json.dumps({"recv_us": recv0 + i, "msg": m}) + "\n")
        fh.write('{"recv_us": 1, "msg": {"trunc')  # truncated tail is skipped


def _order(ev: str, oid: int, side: int, px: str, amt: str, t_us: int) -> dict[str, object]:
    return {
        "event": ev,
        "channel": "live_orders_btcusd",
        "data": {
            "id": oid,
            "order_type": side,
            "price_str": px,
            "amount_str": amt,
            "microtimestamp": str(t_us),
        },
    }


def test_parse_replay_and_segments(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    t0 = 1_000_000_000
    msgs: list[dict[str, object]] = [
        {"event": "bts:subscription_succeeded", "channel": "live_orders_btcusd", "data": {}},
        _order("order_created", 20, 1, "101.00", "0.5", t0 + 1000),
        _order("order_deleted", 2, 1, "102.00", "1", t0 + 2000),
        {
            "event": "trade",
            "channel": "live_trades_btcusd",
            "data": {
                "type": 0,
                "price_str": "101.00",
                "amount_str": "0.5",
                "microtimestamp": str(t0 + 3000),
                "buy_order_id": 99,
                "sell_order_id": 20,
            },
        },
        _order("order_deleted", 20, 1, "101.00", "0", t0 + 3000),
    ]
    _write_raw(raw / "2026-01-01" / "00.jsonl.gz", msgs, recv0=t0)
    _write_raw(raw / "2026-01-01" / "01.jsonl.gz", [], recv0=t0 + 10**10)  # "latest"
    snap = {
        "microtimestamp": str(t0),
        "bids": [["100.00", "1", "1"]],
        "asks": [["102.00", "1", "2"], ["103.00", "1", "3"]],
    }
    with gzip.open(raw / "2026-01-01" / f"snapshot_{t0 - 5}.json.gz", "wt") as fh:
        json.dump(snap, fh)

    ev = l3.load_events(raw, tmp_path / "cache")
    assert ev["ev"].to_list() == [l3.EV_SUB, l3.EV_CREATE, l3.EV_DELETE, l3.EV_TRADE, l3.EV_DELETE]
    snaps = l3.load_snapshots(raw)
    segs = l3.segments(ev, snaps)
    assert len(segs) == 1 and segs[0][2].t_us == t0
    rep, _ = l3.replay(ev, snaps)
    orders = rep.filter(pl.col("ev") != l3.EV_TRADE)
    # best quotes *before* each event
    assert orders.select("bid", "ask").rows() == [(10000, 10200), (10000, 10100), (10000, 10100)]
    flows = l3.window_flows(
        rep,
        pl.DataFrame({"aid": [0], "t_end": [t0], "book_side": [1]}),
        window_ms=(0, 10),
        max_bps=1000.0,
    )
    assert flows["kind"].to_list() == ["add", "cancel", "fill"]


def test_find_sweeps_and_isolation() -> None:
    tr = pl.DataFrame(
        {
            "id": [1, 1, 1, 2, 2, 2, 3],
            "side": [0, 0, 0, 1, 1, 1, 0],
            "t_us": [0, 1, 2, 500_000, 500_001, 500_002, 3_000_000],
            "px": [10000, 10001, 10002, 9999, 9998, 9997, 10000],
            "amt": [1, 1, 1, 1, 1, 1, 1],
        },
        schema_overrides={"side": pl.Int8},
    )
    sw = l3.find_sweeps(tr, min_levels=3)
    assert sw["id"].to_list() == [1]  # 2 is within 1 s of 1; 3 has one level
    assert sw["book_side"].to_list() == [1]


def test_move_flags_exact_lot_and_time_controls() -> None:
    def row(t_ms: float, kind: str, px: int, amt: int) -> dict[str, object]:
        return {
            "aid": 0,
            "side": 1,
            "t_us": int(t_ms * 1000),
            "dt_ms": t_ms,
            "kind": kind,
            "px": px,
            "amt": amt,
            "dist_bps": 0.1 if kind == "add" else 5.0,
        }

    flows = pl.DataFrame(
        [
            row(10, "add", 100, 777),  # moved from 105 (same amount, deeper)
            row(5, "cancel", 105, 777),
            row(30, "add", 100, 555),  # cancel at the same price: not a move
            row(31, "cancel", 100, 555),
            row(50, "add", 100, 999),  # matched only by the ±1 satoshi control
            row(52, "cancel", 106, 1000),
            row(70, "add", 100, 333),  # matched only 2 s later (time control)
            row(2070, "cancel", 107, 333),
        ]
    )
    m = l3.move_flags(flows, near_bps=1.0, lag_ms=100.0, shift_ms=2000.0).sort("t_us")
    assert m["exact"].to_list() == [True, False, False, False]
    assert m["ctrl_lot"].to_list() == [0.0, 0.0, 0.5, 0.0]
    assert m["ctrl_time"].to_list() == [False, False, False, True]
