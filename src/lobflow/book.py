"""Level-2 order book replay from Tardis ``incremental_book_L2`` updates.

Semantics (Tardis docs): each row sets the absolute size at (side, price); ``amount == 0``
deletes the level. A run of ``is_snapshot == True`` rows following non-snapshot rows marks a
fresh snapshot: the book is reset before applying it.

Clock: rows are ordered by ``local_timestamp`` (receive time). All book queries use the same
clock so book and trade feeds recorded on one machine are comparable.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

import numba as nb
import numpy as np
import numpy.typing as npt
import polars as pl

F64 = npt.NDArray[np.float64]
I64 = npt.NDArray[np.int64]
B = npt.NDArray[np.bool_]


@dataclass(frozen=True)
class BookSamples:
    """Top-``n_levels`` book states at query times. Arrays are (n_queries, n_levels), NaN-padded.

    ``last_update_ts`` is the local timestamp of the last update applied before each query
    (staleness diagnostic); ``resets`` counts snapshot resets seen before each query.
    """

    query_ts: I64
    bid_px: F64
    bid_sz: F64
    ask_px: F64
    ask_sz: F64
    last_update_ts: I64
    resets: I64

    @property
    def mid(self) -> F64:
        return 0.5 * (self.bid_px[:, 0] + self.ask_px[:, 0])

    @property
    def crossed(self) -> B:
        return self.bid_px[:, 0] >= self.ask_px[:, 0]


def sample_book_reference(
    local_ts: I64,
    is_snapshot: B,
    is_bid: B,
    price: F64,
    amount: F64,
    query_ts: I64,
    n_levels: int = 50,
) -> BookSamples:
    """Pure-Python reference implementation of :func:`sample_book` (slow; used in tests).

    Replay updates and record the top ``n_levels`` per side as of each query time.

    State at query time ``t`` includes every update with ``local_ts <= t``.
    ``local_ts`` must be non-decreasing; ``query_ts`` is sorted internally and results are
    returned in the caller's original order.
    """
    n = local_ts.shape[0]
    if not (is_snapshot.shape[0] == is_bid.shape[0] == price.shape[0] == amount.shape[0] == n):
        raise ValueError("update arrays must have equal length")
    if n and np.any(np.diff(local_ts) < 0):
        raise ValueError("local_ts must be non-decreasing")

    order = np.argsort(query_ts, kind="stable")
    q_sorted = query_ts[order]
    nq = q_sorted.shape[0]

    bid_px = np.full((nq, n_levels), np.nan)
    bid_sz = np.full((nq, n_levels), np.nan)
    ask_px = np.full((nq, n_levels), np.nan)
    ask_sz = np.full((nq, n_levels), np.nan)
    last_ts = np.full(nq, -1, dtype=np.int64)
    resets_out = np.zeros(nq, dtype=np.int64)

    bids: dict[float, float] = {}
    asks: dict[float, float] = {}
    prev_snap = False
    resets = 0
    last = -1

    def emit(k: int) -> None:
        top_b = heapq.nlargest(n_levels, bids)
        top_a = heapq.nsmallest(n_levels, asks)
        nb, na = len(top_b), len(top_a)
        if nb:
            bid_px[k, :nb] = top_b
            bid_sz[k, :nb] = [bids[p] for p in top_b]
        if na:
            ask_px[k, :na] = top_a
            ask_sz[k, :na] = [asks[p] for p in top_a]
        last_ts[k] = last
        resets_out[k] = resets

    ts_l = local_ts.tolist()
    snap_l = is_snapshot.tolist()
    bid_l = is_bid.tolist()
    px_l = price.tolist()
    amt_l = amount.tolist()

    q = 0
    for i in range(n):
        t = ts_l[i]
        while q < nq and q_sorted[q] < t:
            emit(q)
            q += 1
        if q >= nq:
            break
        snap = snap_l[i]
        if snap and not prev_snap:
            bids.clear()
            asks.clear()
            resets += 1
        prev_snap = snap
        book = bids if bid_l[i] else asks
        a = amt_l[i]
        if a == 0.0:
            book.pop(px_l[i], None)
        else:
            book[px_l[i]] = a
        last = t
    while q < nq:
        emit(q)
        q += 1

    inv = np.empty_like(order)
    inv[order] = np.arange(nq)
    return BookSamples(
        query_ts=query_ts.copy(),
        bid_px=bid_px[inv],
        bid_sz=bid_sz[inv],
        ask_px=ask_px[inv],
        ask_sz=ask_sz[inv],
        last_update_ts=last_ts[inv],
        resets=resets_out[inv],
    )


def sample_book(
    local_ts: I64,
    is_snapshot: B,
    is_bid: B,
    price: F64,
    amount: F64,
    query_ts: I64,
    n_levels: int = 50,
    *,
    price_index: tuple[F64, I64] | None = None,
) -> BookSamples:
    """Replay updates and record the top ``n_levels`` per side as of each query time.

    ``price_index``: optional precomputed (sorted distinct prices, index of each row's price),
    see :func:`price_index`; computing it is the dominant cost, so reuse it across calls.

    State at query time ``t`` includes every update with ``local_ts <= t``. ``local_ts`` must
    be non-decreasing; results are returned in the caller's query order. Same semantics as
    :func:`sample_book_reference`, compiled with numba over a dense index of the distinct
    prices (exact float keys preserved).
    """
    n = local_ts.shape[0]
    if not (is_snapshot.shape[0] == is_bid.shape[0] == price.shape[0] == amount.shape[0] == n):
        raise ValueError("update arrays must have equal length")
    if n and np.any(np.diff(local_ts) < 0):
        raise ValueError("local_ts must be non-decreasing")
    order = np.argsort(query_ts, kind="stable")
    q_sorted = np.ascontiguousarray(query_ts[order], dtype=np.int64)
    levels, k_idx = price_index if price_index is not None else build_price_index(price)
    bid_px, bid_sz, ask_px, ask_sz, last_ts, resets = _replay_kernel(
        np.ascontiguousarray(local_ts, dtype=np.int64),
        np.ascontiguousarray(is_snapshot, dtype=np.bool_),
        np.ascontiguousarray(is_bid, dtype=np.bool_),
        np.ascontiguousarray(k_idx, dtype=np.int64),
        np.ascontiguousarray(amount, dtype=np.float64),
        np.ascontiguousarray(levels, dtype=np.float64),
        q_sorted,
        n_levels,
    )
    inv = np.empty_like(order)
    inv[order] = np.arange(q_sorted.shape[0])
    return BookSamples(
        query_ts=query_ts.copy(),
        bid_px=bid_px[inv],
        bid_sz=bid_sz[inv],
        ask_px=ask_px[inv],
        ask_sz=ask_sz[inv],
        last_update_ts=last_ts[inv],
        resets=resets[inv],
    )


def build_price_index(price: F64) -> tuple[F64, I64]:
    """Sorted distinct prices and each row's index into them (multithreaded via polars)."""
    if price.shape[0] == 0:
        return np.zeros(0), np.zeros(0, dtype=np.int64)
    sr = pl.Series("p", price)
    k_idx = (sr.rank("dense") - 1).to_numpy().astype(np.int64)
    levels = sr.unique().sort().to_numpy().astype(np.float64)
    return levels, k_idx


def sample_arrays(
    book_arrays: dict[str, np.ndarray], query_ts: I64, n_levels: int = 50
) -> BookSamples:
    """:func:`sample_book` on a replay-array dict (see ``events.load_book_arrays``).

    Caches the price index in the dict under ``levels`` / ``k_idx`` on first use.
    """
    if "k_idx" not in book_arrays:
        book_arrays["levels"], book_arrays["k_idx"] = build_price_index(book_arrays["price"])
    return sample_book(
        book_arrays["ts"],
        book_arrays["is_snapshot"],
        book_arrays["is_bid"],
        book_arrays["price"],
        book_arrays["amount"],
        query_ts,
        n_levels,
        price_index=(book_arrays["levels"], book_arrays["k_idx"]),
    )


@nb.njit(cache=True)
def _replay_kernel(
    ts: I64,
    snap: B,
    is_bid: B,
    k_idx: I64,
    amount: F64,
    levels: F64,
    q: I64,
    n_levels: int,
) -> tuple[F64, F64, F64, F64, I64, I64]:  # pragma: no cover - compiled
    n = ts.shape[0]
    u = levels.shape[0]
    nq = q.shape[0]
    bid_px = np.full((nq, n_levels), np.nan)
    bid_sz = np.full((nq, n_levels), np.nan)
    ask_px = np.full((nq, n_levels), np.nan)
    ask_sz = np.full((nq, n_levels), np.nan)
    last_out = np.full(nq, -1, dtype=np.int64)
    resets_out = np.zeros(nq, dtype=np.int64)
    bids = np.zeros(u)
    asks = np.zeros(u)
    best_bid = -1  # highest index with bid size > 0
    best_ask = u  # lowest index with ask size > 0
    prev_snap = False
    resets = 0
    last = -1
    j = 0
    for i in range(n + 1):
        t = ts[i] if i < n else np.iinfo(np.int64).max
        while j < nq and (q[j] < t or i == n):
            c = 0
            k = best_bid
            while k >= 0 and c < n_levels:
                if bids[k] > 0.0:
                    bid_px[j, c] = levels[k]
                    bid_sz[j, c] = bids[k]
                    c += 1
                k -= 1
            c = 0
            k = best_ask
            while k < u and c < n_levels:
                if asks[k] > 0.0:
                    ask_px[j, c] = levels[k]
                    ask_sz[j, c] = asks[k]
                    c += 1
                k += 1
            last_out[j] = last
            resets_out[j] = resets
            j += 1
        if i == n or j >= nq:
            break
        if snap[i] and not prev_snap:
            bids[:] = 0.0
            asks[:] = 0.0
            best_bid = -1
            best_ask = u
            resets += 1
        prev_snap = snap[i]
        k = k_idx[i]
        a = amount[i]
        if is_bid[i]:
            bids[k] = a
            if a > 0.0:
                if k > best_bid:
                    best_bid = k
            elif k == best_bid:
                while best_bid >= 0 and bids[best_bid] <= 0.0:
                    best_bid -= 1
        else:
            asks[k] = a
            if a > 0.0:
                if k < best_ask:
                    best_ask = k
            elif k == best_ask:
                while best_ask < u and asks[best_ask] <= 0.0:
                    best_ask += 1
        last = t
    return bid_px, bid_sz, ask_px, ask_sz, last_out, resets_out
