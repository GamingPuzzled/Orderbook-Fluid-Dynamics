"""Gross order flows by distance after shocks: additions, cancellations, fills (mass balance).

Purpose: decide whether post-sweep refill conserves liquidity (cancel deep, repost near the
touch: non-local *transport*) or injects it (additions exceed cancellations: *source*).

For each event, replay every L2 message in ``[t0, t0 + edges_ms[-1])`` starting from the book
strictly before ``t0`` and classify each level change on both sides:

- ``add``      size increase inside the tracked window;
- ``fill``     size decrease matched to traded volume at that price (aggressor hitting this
               side, trade time ≤ message time + ``fill_tol_us``, not older than
               ``fill_expiry_us``; matchable volume capped at the displayed size, since
               trades beyond it hit hidden or not-yet-pushed liquidity);
- ``cancel``   remaining size decrease inside the window;
- ``edge_in``  new level appearing beyond the side's deepest tracked price (top-N window
               refilling after levels are consumed; not an order arrival);
- ``edge_out`` level deleted beyond the side's new deepest price while a new level was
               inserted inside the window in the same message (pushed out of the top-N
               window; ambiguous with cancel-deepest + post, assigned here → cancellations
               are a lower bound; ``edge_out`` is their upper-bound complement).

Identity per side and window (all prices): Δdepth = add + edge_in − cancel − fill − edge_out.

Zones: distance ``d`` in ticks from the *opposite* side's best quote just before the message
(moving frame, same as ``profiles``). Feed caveat: each message is a net change per price over
one push interval (20 ms on Bybit ``orderbook.50``), so a cancel and an add at one price
within one push cancel out; gross flows are lower bounds.

Full-depth feeds (snapshot deeper than 2 × ``n_levels``, e.g. Binance with ~1000 levels) are
seen through a top-``n_levels`` window: the full book is replayed, but only changes of the
visible top levels are classified, exactly as on a top-N feed. Deep levels of such feeds go
stale (no removal message once they drift out of the published range), which otherwise
shows up as spurious additions at placebo times.
"""

from __future__ import annotations

import heapq
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
import polars as pl

from lobflow.book import sample_arrays

I64 = npt.NDArray[np.int64]
F64 = npt.NDArray[np.float64]

DEFAULT_EDGES_MS: tuple[int, ...] = (0, 20, 40, 100, 250, 1000)
ZONES: tuple[tuple[int, int], ...] = ((1, 5), (6, 10), (11, 20), (21, 50), (51, 10**9))
METRICS: tuple[str, ...] = ("add", "cancel", "fill", "edge_in", "edge_out", "add_cofar")
NEAR_MAX_D = 5  # near zone: d <= 5
FAR_MIN_D = 11  # far zone: d >= 11
SIDES: tuple[str, ...] = ("swept", "opp")


def snapshot_depth(is_snapshot: npt.NDArray[np.bool_], is_bid: npt.NDArray[np.bool_]) -> int:
    """Levels per side in the largest snapshot (max over runs of snapshot rows and sides)."""
    if not is_snapshot.any():
        return 0
    snap = is_snapshot.astype(np.int8)
    starts = np.flatnonzero(np.diff(np.concatenate([[0], snap])) == 1)
    ends = np.flatnonzero(np.diff(np.concatenate([snap, [0]])) == -1) + 1
    best = 0
    for a, b in zip(starts, ends, strict=True):
        n_bid = int(is_bid[a:b].sum())
        best = max(best, n_bid, int(b - a) - n_bid)
    return best


def zone_labels() -> list[str]:
    return [f"{lo}-{hi}" if hi < 10**9 else f"{lo}+" for lo, hi in ZONES]


def _zone_index(d: int) -> int:
    for k, (lo, hi) in enumerate(ZONES):
        if lo <= d <= hi:
            return k
    return 0  # d <= 0 (crossed/locked transient): count with the touch zone


def flow_panel(
    book_arrays: dict[str, np.ndarray],
    trades_ts: I64,
    trades_px: F64,
    trades_amt: F64,
    trades_buy: npt.NDArray[np.bool_],
    t0: I64,
    is_buy: npt.NDArray[np.bool_],
    tick: float,
    *,
    edges_ms: Sequence[int] = DEFAULT_EDGES_MS,
    n_levels: int = 50,
    fill_tol_us: int = 5_000,
    fill_expiry_us: int = 100_000,
    log: list[tuple[int, int, int, int, float, int]] | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Return (flows, info).

    If ``log`` is given, every swept-side ``add`` and pure ``cancel`` (no fill part) is
    appended as ``(event, t_us since t0, d, +1 add / -1 cancel, size, depth_px)`` with
    ``depth_px`` = price in ticks, signed so larger = deeper on that side, for order-level tests
    (:mod:`lobflow.moves`).

    ``flows``: long table (event_id, window, side, zone, metric, value) of summed sizes.
    ``add_cofar`` is swept-side addition volume in messages that also contain a far-zone
    (d ≥ 11) swept-side cancellation (co-occurrence for the repositioning test).

    ``info``: per event (event_id, depth_pre_swept, depth_pre_opp, traded_swept_<w>,
    filled_swept_<w>, valid). ``valid`` is False if a snapshot reset falls in the window or
    either side is empty pre-shock.
    """
    n_ev = t0.shape[0]
    if is_buy.shape[0] != n_ev:
        raise ValueError("t0 and is_buy must have equal length")
    if np.any(np.diff(trades_ts) < 0):
        raise ValueError("trades_ts must be non-decreasing")
    edges_us = np.asarray(edges_ms, dtype=np.int64) * 1000
    n_win = edges_us.shape[0] - 1
    horizon = int(edges_us[-1])
    ts = book_arrays["ts"]
    snap = book_arrays["is_snapshot"]
    is_bid = book_arrays["is_bid"]
    price = book_arrays["price"]
    amount = book_arrays["amount"]

    # pre-shock book deep enough to hold every published level: otherwise a size change at a
    # level beyond the sampled depth (full-depth feeds such as Binance) looks like a new
    # level of full size, and its later removal is lost
    published = snapshot_depth(snap, is_bid)
    pre_levels = max(4 * n_levels, 2 * published)
    pre = sample_arrays(book_arrays, t0 - 1, n_levels=pre_levels)
    # full-depth feed: classify changes of the top-n_levels view only, as on a top-N feed
    # (deep levels of a full-depth feed go stale without removal messages)
    emulate = published > 2 * n_levels
    acc = np.zeros((n_ev, n_win, 2, len(ZONES), len(METRICS)))
    traded = np.zeros((n_ev, n_win))
    filled = np.zeros((n_ev, n_win))
    depth_pre = np.zeros((n_ev, 2))
    valid = np.ones(n_ev, dtype=bool)
    m_add, m_can, m_fill, m_ein, m_eout, m_cof = range(len(METRICS))

    for e in range(n_ev):
        start = int(t0[e])
        i0 = int(np.searchsorted(ts, start, side="left"))
        i1 = int(np.searchsorted(ts, start + horizon, side="left"))
        if snap[i0:i1].any():
            valid[e] = False
            continue
        bids = _side_dict(pre.bid_px[e], pre.bid_sz[e])
        asks = _side_dict(pre.ask_px[e], pre.ask_sz[e])
        if not bids or not asks:
            valid[e] = False
            continue
        buy = bool(is_buy[e])
        # side 0 = swept (asks for a buy sweep), side 1 = opposite
        full = (asks, bids) if buy else (bids, asks)
        # sign: +1 if deeper = higher price on that side (asks), -1 for bids
        sgn = (1, -1) if buy else (-1, 1)
        books = tuple(_top(full[s], n_levels, sgn[s]) for s in (0, 1)) if emulate else full
        depth_pre[e] = [sum(books[0].values()), sum(books[1].values())]

        j0 = int(np.searchsorted(trades_ts, start, side="left"))
        j1 = int(np.searchsorted(trades_ts, start + horizon + fill_tol_us, side="left"))
        tj = j0
        # fill pools per side: price -> [unmatched traded size, last trade ts]
        pools: tuple[dict[float, list[float]], dict[float, list[float]]] = ({}, {})

        i = i0
        while i < i1:
            m_ts = int(ts[i])
            k = i
            while k < i1 and ts[k] == m_ts:
                k += 1
            w = int(np.searchsorted(edges_us, m_ts - start, side="right")) - 1
            w = min(max(w, 0), n_win - 1)
            # load trades up to message time + tolerance into pools
            while tj < j1 and trades_ts[tj] <= m_ts + fill_tol_us:
                hits_swept = bool(trades_buy[tj]) == buy
                s_idx = 0 if hits_swept else 1
                tpx_f = float(trades_px[tj])
                tpool = pools[s_idx].setdefault(tpx_f, [0.0, 0.0])
                # cap at displayed size: volume beyond it (hidden/iceberg, or posted after
                # the last push) cannot appear as a removal and must not absorb later cancels
                tpool[0] = min(tpool[0] + float(trades_amt[tj]), books[s_idx].get(tpx_f, 0.0))
                tpool[1] = float(trades_ts[tj])
                if hits_swept:
                    tw = int(np.searchsorted(edges_us, trades_ts[tj] - start, side="right")) - 1
                    traded[e, min(max(tw, 0), n_win - 1)] += float(trades_amt[tj])
                tj += 1
            # state before this message
            deep_before = [_deepest(books[s], sgn[s]) for s in (0, 1)]
            full_before = [len(books[s]) >= n_levels for s in (0, 1)]
            best_before = [_best(books[s], sgn[s]) for s in (0, 1)]
            changes: list[tuple[int, float, float, float]] = []  # (side, px, old, new)
            touched = set()
            for r in range(i, k):
                s = 0 if (bool(is_bid[r]) != buy) else 1
                px, new = float(price[r]), float(amount[r])
                old = full[s].get(px, 0.0)
                if new == 0.0:
                    full[s].pop(px, None)
                else:
                    full[s][px] = new
                if emulate:
                    touched.add(s)
                elif new != old:
                    changes.append((s, px, old, new))
            for s in sorted(touched):
                vis = _top(full[s], n_levels, sgn[s])
                for px in vis.keys() | books[s].keys():
                    old, new = books[s].get(px, 0.0), vis.get(px, 0.0)
                    if new != old:
                        changes.append((s, px, old, new))
                books[s].clear()
                books[s].update(vis)
            deep_after = [_deepest(books[s], sgn[s]) for s in (0, 1)]
            push_budget = _push_budget(changes, deep_before, deep_after, sgn)
            far_cancel = False
            near_adds: list[tuple[int, float]] = []
            for s, px, old, new in changes:
                ref = best_before[1 - s]
                d = int(round((px - ref) * sgn[s] / tick)) if np.isfinite(ref) else 0
                z = _zone_index(d)
                delta = new - old
                cell = acc[e, w, s, z]
                if delta > 0:
                    beyond = np.isfinite(deep_before[s]) and (px - deep_before[s]) * sgn[s] > 0
                    if old == 0.0 and beyond and full_before[s]:
                        cell[m_ein] += delta
                    else:
                        cell[m_add] += delta
                        if s == 0:
                            near_adds.append((z, delta))
                            if log is not None:
                                log.append((e, m_ts - start, d, 1, delta, _dpx(px, sgn[s], tick)))
                    continue
                rem = -delta
                pool = pools[s].get(px)
                had_fill = False
                if pool is not None and pool[0] > 0 and m_ts - pool[1] <= fill_expiry_us:
                    f = min(rem, pool[0])
                    pool[0] -= f
                    rem -= f
                    cell[m_fill] += f
                    had_fill = f > 0
                    if s == 0:
                        filled[e, w] += f
                if rem <= 0:
                    continue
                if (s, px) in push_budget:
                    cell[m_eout] += rem
                else:
                    cell[m_can] += rem
                    if s == 0 and log is not None and not had_fill:
                        log.append((e, m_ts - start, d, -1, rem, _dpx(px, sgn[s], tick)))
                    if s == 0 and d >= FAR_MIN_D:
                        far_cancel = True
            if far_cancel:
                for z, v in near_adds:
                    acc[e, w, 0, z, m_cof] += v
            i = k

    return _to_long(acc, edges_ms), _info(depth_pre, traded, filled, valid, edges_ms)


def _push_budget(
    changes: list[tuple[int, float, float, float]],
    deep_before: list[float],
    deep_after: list[float],
    sgn: tuple[int, int],
) -> set[tuple[int, float]]:
    """Deletions treated as top-N window push-outs (``edge_out``).

    A deleted level beyond the side's new deepest price counts as pushed out only while new
    price levels were inserted *inside* the window in the same message (one push-out per
    insertion, deepest first); otherwise it is a cancellation. L2 cannot separate "cancel
    deepest + post new level" from a push-out, so this assigns the ambiguous case to
    ``edge_out`` (conservative: understates cancellations).
    """
    out: set[tuple[int, float]] = set()
    for s in (0, 1):
        db, da = deep_before[s], deep_after[s]
        n_ins = sum(
            1
            for side, px, old, new in changes
            if side == s and old == 0.0 and new > 0.0 and not (px - db) * sgn[s] > 0
        )
        cands = sorted(
            (
                px
                for side, px, _, new in changes
                if side == s and new == 0.0 and np.isfinite(da) and (px - da) * sgn[s] > 0
            ),
            key=lambda p: -p * sgn[s],
        )
        out.update((s, px) for px in cands[:n_ins])
    return out


def _dpx(px: float, sgn: int, tick: float) -> int:
    return int(round(px * sgn / tick))


def _side_dict(px: F64, sz: F64) -> dict[float, float]:
    ok = np.isfinite(px) & np.isfinite(sz)
    return dict(zip(px[ok].tolist(), sz[ok].tolist(), strict=True))


def _deepest(book: dict[float, float], sgn: int) -> float:
    if not book:
        return float("nan")
    return max(book) if sgn > 0 else min(book)


def _top(book: dict[float, float], n: int, sgn: int) -> dict[float, float]:
    """The ``n`` best levels (lowest asks for sgn > 0, highest bids for sgn < 0)."""
    pick = heapq.nsmallest if sgn > 0 else heapq.nlargest
    return {px: book[px] for px in pick(n, book)}


def _best(book: dict[float, float], sgn: int) -> float:
    if not book:
        return float("nan")
    return min(book) if sgn > 0 else max(book)


def _window_labels(edges_ms: Sequence[int]) -> list[str]:
    return [f"{a}-{b}" for a, b in zip(edges_ms[:-1], edges_ms[1:], strict=True)]


def _to_long(acc: npt.NDArray[np.float64], edges_ms: Sequence[int]) -> pl.DataFrame:
    n_ev, n_win, n_side, n_zone, n_met = acc.shape
    idx = np.indices(acc.shape).reshape(5, -1)
    vals = acc.ravel()
    keep = vals != 0.0
    wl, zl = _window_labels(edges_ms), zone_labels()
    return pl.DataFrame(
        {
            "event_id": idx[0][keep].astype(np.int64),
            "window": np.array(wl)[idx[1][keep]],
            "side": np.array(SIDES)[idx[2][keep]],
            "zone": np.array(zl)[idx[3][keep]],
            "metric": np.array(METRICS)[idx[4][keep]],
            "value": vals[keep],
        },
        schema={
            "event_id": pl.Int64,
            "window": pl.Utf8,
            "side": pl.Utf8,
            "zone": pl.Utf8,
            "metric": pl.Utf8,
            "value": pl.Float64,
        },
    )


def _info(
    depth_pre: F64,
    traded: F64,
    filled: F64,
    valid: npt.NDArray[np.bool_],
    edges_ms: Sequence[int],
) -> pl.DataFrame:
    cols: dict[str, object] = {
        "event_id": np.arange(depth_pre.shape[0], dtype=np.int64),
        "depth_pre_swept": depth_pre[:, 0],
        "depth_pre_opp": depth_pre[:, 1],
        "valid": valid,
    }
    for k, lab in enumerate(_window_labels(edges_ms)):
        cols[f"traded_swept_{lab}"] = traded[:, k]
        cols[f"filled_swept_{lab}"] = filled[:, k]
    return pl.DataFrame(cols)
