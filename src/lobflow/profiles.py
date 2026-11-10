"""Moving-frame depth profiles around shocks (sweeps) and placebo times.

Frame: swept-side depth at integer distance ``d`` (ticks) from the *current* opposite best
quote. For a buy sweep (asks consumed) at time t:

    d = (ask_price - best_bid(t)) / tick,   d = 1, 2, ..., max_d

``d = 1`` is the tightest possible quote; a fully recovered one-tick-spread book has depth at
``d = 1``. Unlike the fixed (pre-shock) frame, this frame follows the price, so a permanent
price move does not masquerade as refill order.

Transport-vs-source reading: if depth rebuilds at small ``d`` first, liquidity is posted at
the touch (non-local source); if large ``d`` recovers first and the recovered region creeps
toward ``d = 1``, refill propagates from surviving deep liquidity (local transport).
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt
import polars as pl

from lobflow.book import sample_arrays

I64 = npt.NDArray[np.int64]


def profile_panel(
    book_arrays: dict[str, np.ndarray],
    t0: I64,
    is_buy: npt.NDArray[np.bool_],
    tick: float,
    taus_ms: Sequence[int],
    *,
    max_d: int = 50,
    n_levels: int = 50,
    pre_offset_us: int = 1,
) -> pl.DataFrame:
    """Long table (event_id, tau_ms, d, depth, observed, surv_ub, spread_ticks, mid).

    ``surv_ub``: upper bound on depth that was already resting at the same price pre-shock
    (see ``_surviving_upper_bound``); ``depth - surv_ub`` lower-bounds newly posted depth.

    ``tau_ms == -1`` is the pre-shock state (book strictly before ``t0``). ``observed`` is
    False where ``d`` lies beyond the deepest sampled level of the top-N feed (depth unknown).
    """
    n_ev = t0.shape[0]
    if is_buy.shape[0] != n_ev:
        raise ValueError("t0 and is_buy must have equal length")
    offsets = np.array([-pre_offset_us, *(1000 * t for t in taus_ms)], dtype=np.int64)
    labels = np.array([-1, *taus_ms], dtype=np.int64)
    n_off = offsets.shape[0]
    q = (t0[:, None] + offsets[None, :]).ravel()
    s = sample_arrays(book_arrays, q, n_levels=n_levels)
    buy_rows = np.repeat(is_buy, n_off)
    # Swept side and its opposite best, per query row.
    px = np.where(buy_rows[:, None], s.ask_px, s.bid_px)
    sz = np.where(buy_rows[:, None], s.ask_sz, s.bid_sz)
    opp_best = np.where(buy_rows, s.bid_px[:, 0], s.ask_px[:, 0])
    sign = np.where(buy_rows, 1.0, -1.0)

    n_rows = q.shape[0]
    depth = np.zeros((n_rows, max_d))
    d_idx = np.rint((px - opp_best[:, None]) * sign[:, None] / tick).astype(np.float64)
    valid = np.isfinite(px) & np.isfinite(d_idx) & (d_idx >= 1) & (d_idx <= max_d)
    r, c = np.nonzero(valid)
    np.add.at(depth, (r, d_idx[r, c].astype(np.int64) - 1), sz[r, c])
    deepest = np.nanmax(np.where(np.isfinite(px), d_idx, np.nan), axis=1)
    d_grid = np.arange(1, max_d + 1)
    observed = d_grid[None, :] <= np.nan_to_num(deepest, nan=0.0)[:, None]
    ok_row = np.isfinite(opp_best)
    observed &= ok_row[:, None]
    depth[~observed] = np.nan

    surv_ub = _surviving_upper_bound(px, sz, depth, opp_best, sign, tick, n_off, max_d)

    spread = (s.ask_px[:, 0] - s.bid_px[:, 0]) / tick
    ev = np.repeat(np.arange(n_ev, dtype=np.int64), n_off)
    tau = np.tile(labels, n_ev)
    return pl.DataFrame(
        {
            "event_id": np.repeat(ev, max_d),
            "tau_ms": np.repeat(tau, max_d),
            "d": np.tile(d_grid, n_rows).astype(np.int64),
            "depth": depth.ravel(),
            "observed": observed.ravel(),
            "surv_ub": surv_ub.ravel(),
            "spread_ticks": np.repeat(spread, max_d),
            "mid": np.repeat(s.mid, max_d),
        }
    )


def _surviving_upper_bound(
    px: npt.NDArray[np.float64],
    sz: npt.NDArray[np.float64],
    depth: npt.NDArray[np.float64],
    opp_best: npt.NDArray[np.float64],
    sign: npt.NDArray[np.float64],
    tick: float,
    n_off: int,
    max_d: int,
) -> npt.NDArray[np.float64]:
    """Upper bound on pre-shock depth still resting at each (row, d), from L2 data.

    For each absolute price, take the running minimum of swept-side depth from the event's
    pre-shock book (row ``event * n_off``) through the current sample. Depth above that
    running minimum must have been added after the shock, so

        surviving ≤ surv_ub,   new ≥ depth − surv_ub.

    Prices beyond the deepest pre-shock sampled level are unknown (NaN). Prices inside the
    pre-shock observed range but empty, or on the near side of the pre-shock best quote,
    start at 0 (any later depth there is new).
    """
    n_rows = px.shape[0]
    out = np.full((n_rows, max_d), np.nan)
    k_px = np.rint(px / tick)
    d_grid = np.arange(1, max_d + 1)
    for e0 in range(0, n_rows, n_off):
        kp, sp = k_px[e0], sz[e0]
        ok = np.isfinite(kp)
        if not ok.any():
            continue
        kp_i = kp[ok].astype(np.int64)
        sgn = sign[e0]
        deepest = int(kp_i.max() if sgn > 0 else kp_i.min())
        runmin: dict[int, float] = dict(zip(kp_i.tolist(), sp[ok].tolist(), strict=True))
        for r in range(e0, e0 + n_off):
            if not np.isfinite(opp_best[r]):
                continue
            k0 = int(np.rint(opp_best[r] / tick))
            for c in range(max_d):
                k = k0 + int(sgn * d_grid[c])
                if (k > deepest) if sgn > 0 else (k < deepest):
                    continue  # unknown pre-shock depth
                cur = runmin.get(k, 0.0)
                v = depth[r, c]
                if np.isfinite(v):
                    cur = min(cur, v)
                    runmin[k] = cur
                    out[r, c] = cur
    return out


def placebo_times(
    t_start: int,
    t_end: int,
    n: int,
    exclude: I64,
    *,
    exclude_window_us: int = 2_000_000,
    seed: int = 0,
) -> I64:
    """Uniform random times in [t_start, t_end] at least ``exclude_window_us`` from any
    excluded time (e.g. all candidate sweeps). Returns sorted int64 array of length <= n."""
    rng = np.random.default_rng(seed)
    ex = np.sort(exclude.astype(np.int64))
    out: list[int] = []
    for _ in range(50):
        cand = rng.integers(t_start, t_end, size=4 * n, dtype=np.int64)
        if ex.size:
            pos = np.searchsorted(ex, cand)
            left = np.abs(cand - ex[np.clip(pos - 1, 0, ex.size - 1)])
            right = np.abs(ex[np.clip(pos, 0, ex.size - 1)] - cand)
            cand = cand[np.minimum(left, right) > exclude_window_us]
        out.extend(cand.tolist())
        if len(out) >= n:
            break
    return np.sort(np.array(out[:n], dtype=np.int64))
