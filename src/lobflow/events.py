"""Build the post-sweep event panel: depth on a fixed tick grid around the cleared gap.

Coordinates (per event, swept side only):
- ``j`` — gap index. ``j = 1`` is the pre-shock touch on the swept side (nearest the mid),
  ``j = L`` the deepest consumed level. ``j <= 0`` lies inside the pre-shock spread;
  ``j > L`` is surviving liquidity beyond the void. Transport from surviving liquidity predicts
  refill starting near ``j = L``; posting at the new touch predicts refill near ``j = 1``.
- ``x_fixed`` — signed distance from the pre-shock mid in ticks (fixed frame).

Clock: by default book and trades are aligned on the **exchange** clock (matching-engine
timestamps), which removes the differing latencies of the separate book and trade streams.
``t0`` is the sweep's exchange timestamp; the pre-shock state is the book as of
``t0 - pre_offset_us`` (strictly before the sweep). ``clock="local"`` uses receive times
instead (needs a larger ``pre_offset_us``, e.g. 20 ms). Clearing is confirmed at
``confirm_tau_ms`` (≥ one book push interval after ``t0``).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
import polars as pl

from lobflow.book import BookSamples, sample_arrays

# 20 ms = Bybit orderbook.50 push interval; shorter offsets only repeat the pre-shock state.
DEFAULT_TAUS_MS: tuple[int, ...] = (20, 40, 60, 100, 250, 500, 1000)


@dataclass(frozen=True)
class PanelParams:
    taus_ms: Sequence[int] = DEFAULT_TAUS_MS
    clock: Literal["exchange", "local"] = "exchange"
    pre_offset_us: int = 1
    confirm_tau_ms: int = 20  # must be in taus_ms
    margin_ticks: int = 5  # grid extension on each side of the gap
    n_levels: int = 50  # levels sampled per side; must cover gap + margin
    empty_frac: float = 0.05  # traded level counts as cleared if depth < frac * pre depth


CLOCK_COLUMNS: dict[str, tuple[str, str]] = {
    # clock -> (book/trade column, sweep-run column)
    "exchange": ("timestamp", "timestamp"),
    "local": ("local_timestamp", "local_ts"),
}


def load_book_arrays(
    book: pl.DataFrame, clock: Literal["exchange", "local"] = "exchange"
) -> dict[str, np.ndarray]:
    """Extract replay arrays, ordered (stably) by the chosen clock."""
    col = CLOCK_COLUMNS[clock][0]
    b = book.sort(col, maintain_order=True)
    return {
        "ts": b[col].to_numpy(),
        "is_snapshot": b["is_snapshot"].to_numpy(),
        "is_bid": (b["side"] == "bid").to_numpy(),
        "price": b["price"].to_numpy(),
        "amount": b["amount"].to_numpy(),
    }


def _depth_on_grid(
    px_row: np.ndarray, sz_row: np.ndarray, grid: np.ndarray, tick: float, ask_side: bool
) -> np.ndarray:
    """Depth of one book side at each grid price.

    Returns 0 where the side has no order but the price is observed (inside its sampled range,
    or on the far side of its best quote, toward/past the mid); NaN beyond the deepest sampled
    level, where absence cannot be distinguished from truncation of the top-N feed.
    """
    out = np.zeros(grid.shape[0])
    valid = np.isfinite(px_row)
    px, sz = px_row[valid], sz_row[valid]
    if px.size == 0:
        return np.full(grid.shape[0], np.nan)
    step = grid[1] - grid[0] if grid.shape[0] > 1 else tick
    idx = np.rint((px - grid[0]) / step).astype(np.int64)
    inside = (idx >= 0) & (idx < grid.shape[0])
    out[idx[inside]] = sz[inside]
    lo, hi = px.min(), px.max()
    # Asks: truncation is above the deepest ask. Bids: truncation is below the deepest bid.
    unobserved = grid > hi + tick / 2 if ask_side else grid < lo - tick / 2
    out[unobserved] = np.nan
    return out


def build_event_panel(
    book_arrays: dict[str, np.ndarray],
    sweeps: pl.DataFrame,
    tick: float,
    params: PanelParams | None = None,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Return (events, panel).

    ``events``: one row per sweep with pre-shock state and a ``cleared_frac`` confirmation.
    ``panel``: long table (event_id, tau_ms, j, in_gap, x_fixed, price, depth, depth_opp, mid,
    depth_pre). ``depth`` is the swept side, ``depth_opp`` the opposite side on the same grid
    (e.g. bids moving into a gap cleared by a buy sweep). ``tau_ms == -1`` is pre-shock.
    """
    p = params or PanelParams()
    if p.confirm_tau_ms not in p.taus_ms:
        raise ValueError("confirm_tau_ms must be one of taus_ms")
    t_col = CLOCK_COLUMNS[p.clock][1]
    sw = sweeps.sort(t_col)
    n_ev = sw.height
    if n_ev == 0:
        raise ValueError("no sweeps supplied")
    t0 = sw[t_col].to_numpy().astype(np.int64)
    offsets_us = np.array([-p.pre_offset_us, *(1000 * t for t in p.taus_ms)], dtype=np.int64)
    confirm_k = 1 + list(p.taus_ms).index(p.confirm_tau_ms)
    n_off = offsets_us.shape[0]
    q = (t0[:, None] + offsets_us[None, :]).ravel()

    s: BookSamples = sample_arrays(book_arrays, q, n_levels=p.n_levels)

    sides = sw["side"].to_list()
    p_min = sw["p_min"].to_numpy()
    p_max = sw["p_max"].to_numpy()
    ev_rows: list[dict[str, object]] = []
    panel_parts: list[pl.DataFrame] = []
    for e in range(n_ev):
        base = e * n_off
        pre = base
        buy = sides[e] == "buy"  # buy aggressor consumes asks
        px_pre = s.ask_px[pre] if buy else s.bid_px[pre]
        sz_pre = s.ask_sz[pre] if buy else s.bid_sz[pre]
        touch = px_pre[0]
        deep = p_max[e] if buy else p_min[e]
        mid_pre = float(s.mid[pre])
        if not np.isfinite(touch) or not np.isfinite(mid_pre):
            continue
        direction = 1.0 if buy else -1.0
        gap_len = int(round((deep - touch) / tick * direction)) + 1
        if gap_len < 1:
            continue
        j = np.arange(1 - p.margin_ticks, gap_len + p.margin_ticks + 1)
        grid = touch + direction * (j - 1) * tick
        depth_pre = _depth_on_grid(px_pre, sz_pre, grid, tick, ask_side=buy)

        in_gap = (j >= 1) & (j <= gap_len)
        first_post = base + confirm_k
        px_fp = s.ask_px[first_post] if buy else s.bid_px[first_post]
        sz_fp = s.ask_sz[first_post] if buy else s.bid_sz[first_post]
        depth_fp = _depth_on_grid(px_fp, sz_fp, grid, tick, ask_side=buy)
        had = in_gap & (np.nan_to_num(depth_pre) > 0)
        cleared = had & (np.nan_to_num(depth_fp) < p.empty_frac * np.nan_to_num(depth_pre))
        cleared_frac = float(cleared.sum() / had.sum()) if had.any() else float("nan")

        ev_rows.append(
            {
                "event_id": e,
                "timestamp": int(sw["timestamp"][e]),
                "t0": int(t0[e]),
                "local_ts": int(sw["local_ts"][e]),
                "side": sides[e],
                "L_gap": gap_len,
                "touch_pre": float(touch),
                "mid_pre": mid_pre,
                "spread_pre_ticks": float((s.ask_px[pre, 0] - s.bid_px[pre, 0]) / tick),
                "gap_depth_pre": float(np.nansum(depth_pre[in_gap])),
                "volume": float(sw["volume"][e]),
                "cleared_frac": cleared_frac,
                "pre_staleness_us": int(q[pre] - s.last_update_ts[pre])
                if s.last_update_ts[pre] >= 0
                else -1,
                "crossed_pre": bool(s.crossed[pre]),
                "resets_in_window": int(s.resets[base + n_off - 1] - s.resets[pre]),
            }
        )
        for k in range(n_off):
            row = base + k
            px = s.ask_px[row] if buy else s.bid_px[row]
            sz = s.ask_sz[row] if buy else s.bid_sz[row]
            opx = s.bid_px[row] if buy else s.ask_px[row]
            osz = s.bid_sz[row] if buy else s.ask_sz[row]
            panel_parts.append(
                pl.DataFrame(
                    {
                        "event_id": np.full(j.shape[0], e, dtype=np.int64),
                        "tau_ms": np.full(
                            j.shape[0], -1 if k == 0 else p.taus_ms[k - 1], dtype=np.int64
                        ),
                        "j": j.astype(np.int64),
                        "in_gap": in_gap,
                        "x_fixed": (grid - mid_pre) / tick,
                        "price": grid,
                        "depth": _depth_on_grid(px, sz, grid, tick, ask_side=buy),
                        "depth_opp": _depth_on_grid(opx, osz, grid, tick, ask_side=not buy),
                        "mid": np.full(j.shape[0], s.mid[row]),
                        "depth_pre": depth_pre,
                    }
                )
            )
    events = pl.DataFrame(ev_rows)
    panel = pl.concat(panel_parts) if panel_parts else pl.DataFrame()
    return events, panel
