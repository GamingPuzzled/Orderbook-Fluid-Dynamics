"""Order-level (L3) analysis of Bitstamp's public feed (``scripts/record_bitstamp.py``).

Unlike the 20 ms level-2 Bybit feed, every order create / change / delete arrives as its own
event with an order ID, so a 'move' (cancel deep, re-post near the touch) is visible as an
individual delete followed by a create of the *same amount* at a price closer to the touch.
Bitstamp issues a new ID on every re-post (``order_changed`` is a partial fill), so the
same-order test matches on exact amount (satoshi precision) and price, with two coincidence
controls.

Pipeline
--------
1. ``parse_file``: raw gzip JSONL -> event frame (cached as parquet per hour).
2. ``replay``: rebuild the book from the REST snapshot of each connection segment; record
   best bid/ask *before* every event, and depth / state covariates at anchor times.
3. ``find_sweeps``: taker orders filling at >= ``min_levels`` distinct prices.
4. ``window_flows``: swept-side adds / cancels / fills by distance from the opposite best quote
   and time since the anchor (sweep end, or placebo time).
5. ``move_flags``: for each near-touch add, is there a delete of an identical amount at a
   strictly deeper price within ``lag_ms``? Controls: amount ± 1 satoshi; same rule with the
   delete pool shifted by ``shift_ms`` in time.
"""

from __future__ import annotations

import glob
import gzip
import heapq
import json
import zlib
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl

I64 = npt.NDArray[np.int64]
F64 = npt.NDArray[np.float64]

EV_CREATE, EV_CHANGE, EV_DELETE, EV_TRADE, EV_SUB = 0, 1, 2, 3, 4
SAT = 100_000_000  # amount key: integer satoshis
CENT = 100  # price key: integer cents
BINS_MS: tuple[int, ...] = (0, 20, 40, 60, 100, 250, 500, 1000)

SCHEMA = {
    "seq": pl.Int64,
    "recv_us": pl.Int64,
    "t_us": pl.Int64,
    "ev": pl.Int8,
    "id": pl.Int64,
    "side": pl.Int8,  # orders: 0 bid / 1 ask; trades: taker side 0 buy / 1 sell
    "px": pl.Int64,  # cents
    "amt": pl.Int64,  # satoshis
    "maker_id": pl.Int64,
}


# ---------------------------------------------------------------- parsing


def _lines(path: Path) -> Iterator[str]:
    """Lines of a (possibly still-growing or truncated) gzip file."""
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            yield from fh
    except (EOFError, zlib.error, OSError):
        return


def _key(s: str, scale: int) -> int:
    """Exact integer key for a decimal string (no float rounding)."""
    whole, _, frac = s.partition(".")
    digits = len(str(scale)) - 1
    frac = (frac + "0" * digits)[:digits]
    sign = -1 if whole.startswith("-") else 1
    return sign * (abs(int(whole or "0")) * scale + int(frac or "0"))


def parse_file(path: Path) -> pl.DataFrame:
    """Raw hourly file -> event frame (``SCHEMA``). Unparseable lines are skipped."""
    rows: list[tuple[int, ...]] = []
    for seq, line in enumerate(_lines(path)):
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        m = rec["msg"]
        ev = m.get("event")
        d = m.get("data") or {}
        recv = int(rec["recv_us"])
        if ev == "bts:subscription_succeeded":
            if str(m.get("channel", "")).startswith("live_orders"):
                rows.append((seq, recv, recv, EV_SUB, 0, -1, 0, 0, 0))
            continue
        if ev in ("order_created", "order_changed", "order_deleted"):
            code = {"order_created": EV_CREATE, "order_changed": EV_CHANGE}.get(ev, EV_DELETE)
            rows.append(
                (
                    seq,
                    recv,
                    int(d["microtimestamp"]),
                    code,
                    int(d["id"]),
                    int(d["order_type"]),
                    _key(d["price_str"], CENT),
                    _key(d["amount_str"], SAT),
                    0,
                )
            )
        elif ev == "trade":
            buy = int(d["type"]) == 0
            taker, maker = (
                (d["buy_order_id"], d["sell_order_id"])
                if buy
                else (d["sell_order_id"], d["buy_order_id"])
            )
            rows.append(
                (
                    seq,
                    recv,
                    int(d["microtimestamp"]),
                    EV_TRADE,
                    int(taker),
                    int(d["type"]),
                    _key(d["price_str"], CENT),
                    _key(d["amount_str"], SAT),
                    int(maker),
                )
            )
    return pl.DataFrame(rows, schema=SCHEMA, orient="row")


@dataclass(frozen=True)
class Snapshot:
    recv_us: int
    t_us: int
    bids: list[tuple[int, int, int]]  # (id, px cents, amt sat)
    asks: list[tuple[int, int, int]]


def load_snapshot(path: Path) -> Snapshot:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        b = json.load(fh)
    recv = int(path.name.split("_")[1].split(".")[0])

    def side(rows: list[list[str]]) -> list[tuple[int, int, int]]:
        return [(int(r[2]), _key(r[0], CENT), _key(r[1], SAT)) for r in rows]

    return Snapshot(recv, int(b["microtimestamp"]), side(b["bids"]), side(b["asks"]))


def load_events(raw_root: Path, cache_root: Path, *, skip_latest: bool = True) -> pl.DataFrame:
    """All hourly files under ``raw_root`` (cached per file as parquet), sorted by receive
    order. The newest file is skipped by default (it is still being written)."""
    files = sorted(Path(p) for p in glob.glob(str(raw_root / "*" / "[0-9]*.jsonl.gz")))
    if skip_latest and files:
        files = files[:-1]
    parts = []
    for f in files:
        c = cache_root / f.parent.name / f"{f.name.split('.')[0]}.parquet"
        if not c.exists() or c.stat().st_mtime < f.stat().st_mtime:
            c.parent.mkdir(parents=True, exist_ok=True)
            parse_file(f).write_parquet(c)
        parts.append(pl.read_parquet(c).with_columns(pl.lit(str(c)).alias("file")))
    if not parts:
        return pl.DataFrame(schema=SCHEMA)
    return pl.concat(parts).sort("recv_us", "seq", maintain_order=True).drop("file")


def load_snapshots(raw_root: Path) -> list[Snapshot]:
    files = sorted(Path(p) for p in glob.glob(str(raw_root / "*" / "snapshot_*.json.gz")))
    return sorted((load_snapshot(f) for f in files), key=lambda s: s.recv_us)


# ---------------------------------------------------------------- book replay


class Book:
    """Order-level book with lazy-deletion heaps for the best quotes."""

    def __init__(self) -> None:
        self.orders: dict[int, tuple[int, int, int]] = {}  # id -> (side, px, amt)
        self.levels: tuple[dict[int, int], dict[int, int]] = ({}, {})
        self.heaps: tuple[list[int], list[int]] = ([], [])  # bids: -px, asks: px
        self.at: tuple[dict[int, set[int]], dict[int, set[int]]] = ({}, {})  # px -> ids
        self.stale_candidates: set[int] = set()  # snapshot orders not yet seen in the stream
        self.n_pruned = 0

    def _level_add(self, side: int, px: int, amt: int) -> None:
        lv = self.levels[side]
        new = lv.get(px, 0) + amt
        if new > 0:
            if px not in lv:
                heapq.heappush(self.heaps[side], -px if side == 0 else px)
            lv[px] = new
        else:
            lv.pop(px, None)

    def add(self, oid: int, side: int, px: int, amt: int) -> None:
        self.remove(oid)
        if amt > 0:
            self.orders[oid] = (side, px, amt)
            self._level_add(side, px, amt)
            self.at[side].setdefault(px, set()).add(oid)

    def remove(self, oid: int) -> None:
        self.stale_candidates.discard(oid)
        o = self.orders.pop(oid, None)
        if o is not None:
            self._level_add(o[0], o[1], -o[2])
            ids = self.at[o[0]].get(o[1])
            if ids is not None:
                ids.discard(oid)
                if not ids:
                    del self.at[o[0]][o[1]]

    def prune_crossed(self) -> None:
        """While the book is crossed, drop snapshot orders at the crossing best levels: the
        REST snapshot can contain orders already deleted before the stream started, whose
        delete therefore never arrives. Stream-born orders are never dropped (a crossing
        between them is a transient marketable order)."""
        while True:
            b, a = self.best(0), self.best(1)
            if not (b and a and b >= a):
                return
            stale = [
                o
                for side, px in ((0, b), (1, a))
                for o in self.at[side].get(px, ())
                if o in self.stale_candidates
            ]
            if not stale:
                return
            for o in stale:
                self.remove(o)
                self.n_pruned += 1

    def best(self, side: int) -> int:
        """Best price (cents) on ``side``; 0 if empty."""
        h, lv = self.heaps[side], self.levels[side]
        while h:
            px = -h[0] if side == 0 else h[0]
            if px in lv:
                return px
            heapq.heappop(h)
        return 0

    def depth_within(self, side: int, bps: float) -> float:
        """BTC resting on ``side`` within ``bps`` of the *opposite* best quote."""
        ref = self.best(1 - side)
        if ref == 0:
            return 0.0
        lim = ref * (1 - bps / 1e4) if side == 0 else ref * (1 + bps / 1e4)
        lv = self.levels[side]
        tot = sum(a for p, a in lv.items() if (p >= lim if side == 0 else p <= lim))
        return tot / SAT


def segments(
    events: pl.DataFrame, snaps: Sequence[Snapshot], *, silence_us: int = 5_000_000
) -> list[tuple[int, int, Snapshot]]:
    """(start_row, end_row, snapshot) per websocket connection: rows from one subscription
    marker to the next, paired with the snapshot requested closest to the marker (the
    recorder requests it right after subscribing, so it can precede the logged marker),
    within ``max_gap`` = 60 s. A segment is cut at the first receive gap > ``silence_us``
    (a dropped connection whose reconnect marker may be missing): later rows have no valid
    book until the next marker."""
    max_gap = 60_000_000
    ev = events["ev"].to_numpy()
    recv = events["recv_us"].to_numpy()
    starts = list(np.flatnonzero(ev == EV_SUB)) + [len(events)]
    gaps = np.flatnonzero(np.diff(recv) > silence_us) + 1  # first row after each gap
    out = []
    for a, b in zip(starts[:-1], starts[1:], strict=True):
        snap = min(snaps, key=lambda s: abs(s.recv_us - recv[a]), default=None)
        if snap is not None and abs(snap.recv_us - recv[a]) <= max_gap:
            g = gaps[(gaps > a + 2) & (gaps < b)]  # ignore the subscribe/snapshot pause
            out.append((int(a), int(g[0]) if len(g) else int(b), snap))
    return out


def replay(
    events: pl.DataFrame,
    snaps: Sequence[Snapshot],
    anchors: pl.DataFrame | None = None,
    *,
    depth_bps: float = 10.0,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Replay each connection segment from its snapshot.

    Returns (events with ``seg``, ``bid``, ``ask`` = best quotes *before* each event, restricted
    to replayed rows; anchors with ``depth_pre`` = swept-side depth within ``depth_bps`` of the
    opposite best at ``t_pre`` and the anchor's ``seg``). Anchors need columns ``aid``,
    ``t_pre`` (µs) and ``book_side``. Events time-stamped before the snapshot are skipped
    (already reflected); later ones are applied idempotently.
    """
    n = len(events)
    bid = np.zeros(n, dtype=np.int64)
    ask = np.zeros(n, dtype=np.int64)
    seg_id = np.full(n, -1, dtype=np.int64)
    t = events["t_us"].to_numpy()
    evc = events["ev"].to_numpy()
    oid = events["id"].to_numpy()
    side = events["side"].to_numpy()
    px = events["px"].to_numpy()
    amt = events["amt"].to_numpy()
    if anchors is None:
        anchors = pl.DataFrame(schema={"aid": pl.Int64, "t_pre": pl.Int64, "book_side": pl.Int8})
    a_sorted = anchors.sort("t_pre")
    a_t = a_sorted["t_pre"].to_numpy()
    a_side = a_sorted["book_side"].to_numpy()
    a_depth = np.full(len(a_sorted), np.nan)
    a_seg = np.full(len(a_sorted), -1, dtype=np.int64)
    for k, (lo, hi, snap) in enumerate(segments(events, snaps)):
        book = Book()
        for s, rows in ((0, snap.bids), (1, snap.asks)):
            for o, p, q in rows:
                book.add(o, s, p, q)
        book.stale_candidates = set(book.orders)
        t_end = t[hi - 1] if hi > lo else snap.t_us
        ai = int(np.searchsorted(a_t, snap.t_us, side="left"))
        for i in range(lo, hi):
            if evc[i] in (EV_SUB, EV_TRADE) or t[i] < snap.t_us:
                continue
            while ai < len(a_t) and a_t[ai] <= t[i] and a_t[ai] <= t_end:
                a_depth[ai] = book.depth_within(int(a_side[ai]), depth_bps)
                a_seg[ai] = k
                ai += 1
            bid[i], ask[i], seg_id[i] = book.best(0), book.best(1), k
            if evc[i] == EV_DELETE:
                book.remove(int(oid[i]))
            else:
                book.stale_candidates.discard(int(oid[i]))
                book.add(int(oid[i]), int(side[i]), int(px[i]), int(amt[i]))
            book.prune_crossed()
    out = events.with_columns(
        pl.Series("seg", seg_id), pl.Series("bid", bid), pl.Series("ask", ask)
    ).filter((pl.col("seg") >= 0) | (pl.col("ev") == EV_TRADE))
    anc = a_sorted.with_columns(pl.Series("depth_pre", a_depth), pl.Series("seg", a_seg))
    return out, anc


# ---------------------------------------------------------------- sweeps and placebo


def find_sweeps(
    trades: pl.DataFrame, *, min_levels: int = 3, min_bps: float = 0.0, isolate_ms: int = 1000
) -> pl.DataFrame:
    """Taker orders that fill at >= ``min_levels`` distinct prices spanning >= ``min_bps``.

    ``book_side`` is the swept side (1 = asks for a buy taker). Isolated: no other qualifying
    sweep ended within ``isolate_ms`` before this one started.
    """
    g = (
        trades.group_by("id")
        .agg(
            pl.col("side").first(),
            pl.col("t_us").min().alias("t_first"),
            pl.col("t_us").max().alias("t_end"),
            pl.col("px").n_unique().alias("n_levels"),
            pl.col("px").min().alias("px_min"),
            pl.col("px").max().alias("px_max"),
            (pl.col("amt").sum() / SAT).alias("volume"),
        )
        .with_columns(
            ((pl.col("px_max") - pl.col("px_min")) / pl.col("px_min") * 1e4).alias("span_bps"),
            (1 - pl.col("side")).cast(pl.Int8).alias("book_side"),
        )
        .filter((pl.col("n_levels") >= min_levels) & (pl.col("span_bps") >= min_bps))
        .sort("t_first")
    )
    prev_end = g["t_end"].shift(1).fill_null(-(10**18))
    return g.filter(g["t_first"] - prev_end.cum_max() > isolate_ms * 1000)


def placebo_times(
    events: pl.DataFrame,
    sweeps: pl.DataFrame,
    *,
    n: int,
    seed: int = 0,
    guard_ms: int = 2000,
) -> pl.DataFrame:
    """Uniform random (time, side) draws inside replayed segments, at least ``guard_ms`` from
    every taker in ``sweeps`` (pass all multi-level takers) and from segment edges."""
    rng = np.random.default_rng(seed)
    seg = (
        events.filter(pl.col("seg") >= 0)
        .group_by("seg")
        .agg(pl.col("t_us").min().alias("a"), pl.col("t_us").max().alias("b"))
    )
    g = guard_ms * 1000
    spans = [(a + g, b - g - 1_000_000) for a, b in seg.select("a", "b").iter_rows()]
    spans = [(a, b) for a, b in spans if b > a]
    lens = np.array([b - a for a, b in spans], dtype=np.float64)
    sw = sweeps.sort("t_first")
    b_start = sw["t_first"].to_numpy()
    b_end = np.maximum.accumulate(sw["t_end"].to_numpy()) if len(sw) else b_start
    out_t: list[int] = []
    tries = 0
    while len(out_t) < n and spans and tries < 50 * n:
        tries += 1
        a, b = spans[int(rng.choice(len(spans), p=lens / lens.sum()))]
        tt = int(rng.integers(a, b))
        # blocked if some taker starts before tt + 1 s + guard and ends after tt − guard
        j = int(np.searchsorted(b_start, tt + 1_000_000 + g, side="left"))
        if j == 0 or b_end[j - 1] < tt - g:
            out_t.append(tt)
    t = np.array(out_t, dtype=np.int64)
    return pl.DataFrame(
        {
            "t_first": t,
            "t_end": t,
            "book_side": rng.integers(0, 2, size=len(t)).astype(np.int8),
        }
    )


def anchor_covariates(trades: pl.DataFrame, anchors: pl.DataFrame) -> pl.DataFrame:
    """vol_10s, rv_60s, n_10s before each anchor's ``t_first`` (reuses ``state``)."""
    from lobflow.state import state_covariates

    tr = trades.sort("t_us")
    cov = state_covariates(
        tr["t_us"].to_numpy(),
        tr["px"].to_numpy() / CENT,
        tr["amt"].to_numpy() / SAT,
        anchors["t_first"].to_numpy() - 1000,
    )
    return pl.concat([anchors, cov], how="horizontal")


# ---------------------------------------------------------------- flows around anchors


def window_flows(
    ev: pl.DataFrame,
    anchors: pl.DataFrame,
    *,
    window_ms: tuple[int, int] = (-200, 1200),
    max_bps: float = 10.0,
) -> pl.DataFrame:
    """Swept-side order events within ``window_ms`` of each anchor's ``t_end``.

    Columns: aid, side, dt_ms (from t_end), kind ('add' | 'cancel' | 'fill' | 'change' |
    'move' = same order ID re-priced in place, ``prev_px`` = its previous price), px, amt,
    dist_bps (from the opposite best quote before the event; positive = away from it).
    A delete is a fill if the order traded as maker within 20 ms before it. Events while the
    book is crossed (transient marketable orders, ~1% of time) are dropped.
    """
    orders = ev.filter(pl.col("ev").is_in([EV_CREATE, EV_CHANGE, EV_DELETE]))
    last_fill = (
        ev.filter(pl.col("ev") == EV_TRADE)
        .group_by("maker_id")
        .agg(pl.col("t_us").max().alias("t_fill"))
        .rename({"maker_id": "id"})
    )
    # previous price of the same order: an order_changed with a new price is an in-place move,
    # unless the order is a taker (its price field follows its successive fills)
    takers = ev.filter(pl.col("ev") == EV_TRADE)["id"].unique()
    orders = orders.with_columns(
        pl.when(pl.col("id").is_in(takers.implode()))
        .then(None)
        .otherwise(pl.col("px").shift(1).over("id"))
        .alias("prev_px")
    )
    orders = orders.join(last_fill, on="id", how="left").with_columns(
        pl.when(pl.col("ev") == EV_CREATE)
        .then(pl.lit("add"))
        .when(
            (pl.col("ev") == EV_CHANGE)
            & pl.col("prev_px").is_not_null()
            & (pl.col("px") != pl.col("prev_px"))
        )
        .then(pl.lit("move"))
        .when(pl.col("ev") == EV_CHANGE)
        .then(pl.lit("change"))
        .when(pl.col("t_fill").is_not_null() & (pl.col("t_us") - pl.col("t_fill") <= 20_000))
        .then(pl.lit("fill"))
        .otherwise(pl.lit("cancel"))
        .alias("kind"),
        pl.when(pl.col("side") == 1)
        .then((pl.col("px") - pl.col("bid")) / pl.col("bid") * 1e4)
        .otherwise((pl.col("ask") - pl.col("px")) / pl.col("ask") * 1e4)
        .alias("dist_bps"),
    )
    orders = orders.filter(
        (pl.col("bid") > 0) & (pl.col("ask") > pl.col("bid"))  # skip transient crossed books
    ).sort("t_us")
    t = orders["t_us"].to_numpy()
    s = orders["side"].to_numpy()
    lo_us, hi_us = window_ms[0] * 1000, window_ms[1] * 1000
    idx_parts, aid_parts, dt_parts = [], [], []
    for aid, t_end, side in anchors.select("aid", "t_end", "book_side").iter_rows():
        a = int(np.searchsorted(t, t_end + lo_us, side="left"))
        b = int(np.searchsorted(t, t_end + hi_us, side="right"))
        sel = np.arange(a, b)[s[a:b] == side]
        idx_parts.append(sel)
        aid_parts.append(np.full(len(sel), aid, dtype=np.int64))
        dt_parts.append((t[sel] - t_end) / 1000.0)
    if not idx_parts:
        return pl.DataFrame()
    idx = np.concatenate(idx_parts)
    return (
        orders[idx]
        .select("t_us", "id", "side", "kind", "px", "prev_px", "amt", "dist_bps")
        .with_columns(
            pl.Series("aid", np.concatenate(aid_parts)),
            pl.Series("dt_ms", np.concatenate(dt_parts)),
        )
        .filter(pl.col("dist_bps") <= max_bps)
    )


def move_flags(
    flows: pl.DataFrame,
    *,
    near_bps: float = 1.0,
    lag_ms: float = 100.0,
    shift_ms: float = 2000.0,
    pool: pl.DataFrame | None = None,
) -> pl.DataFrame:
    """Near-touch adds (dist <= ``near_bps``, dt >= 0) with linkage flags:

    - ``exact``: a cancel of the identical amount at a strictly deeper *price* (higher for
      asks, lower for bids; prices, not distances, so a re-post at the same price after the
      quote moved never counts) within ±``lag_ms``;
    - ``ctrl_lot``: same, amount ± 1 satoshi (averaged over the two shifts);
    - ``ctrl_time``: same as exact but against cancels ``shift_ms`` later (pool = ``pool`` or
      ``flows``; the shifted pool must cover the shifted window).
    """
    adds = flows.filter(
        (pl.col("kind") == "add") & (pl.col("dist_bps") <= near_bps) & (pl.col("dt_ms") >= 0)
    ).with_row_index("rid")
    src_all = pool if pool is not None else flows
    cancels = src_all.filter(pl.col("kind") == "cancel").select(
        "aid",
        pl.col("t_us").alias("ts"),
        pl.col("px").alias("spx"),
        pl.col("amt").alias("samt"),
    )

    def flag(shift_amt: int, shift_us: int) -> pl.Series:
        j = adds.join(
            cancels.with_columns(
                (pl.col("samt") - shift_amt).alias("samt"), (pl.col("ts") - shift_us).alias("ts")
            ),
            left_on=["aid", "amt"],
            right_on=["aid", "samt"],
            how="inner",
        ).filter(
            ((pl.col("ts") - pl.col("t_us")).abs() <= lag_ms * 1000)
            & pl.when(pl.col("side") == 1)
            .then(pl.col("spx") > pl.col("px"))
            .otherwise(pl.col("spx") < pl.col("px"))
        )
        hit = set(j["rid"].to_list())
        return pl.Series([r in hit for r in adds["rid"].to_list()], dtype=pl.Boolean)

    sh = int(shift_ms * 1000)
    return adds.with_columns(
        flag(0, 0).alias("exact"),
        ((flag(1, 0).cast(pl.Float64) + flag(-1, 0).cast(pl.Float64)) / 2).alias("ctrl_lot"),
        flag(0, sh).alias("ctrl_time"),
    )


def bin_label(dt: pl.Expr, bins: Sequence[int] = BINS_MS) -> pl.Expr:
    expr = pl.lit(None, dtype=pl.Utf8)
    for a, b in zip(bins[:-1], bins[1:], strict=True):
        expr = pl.when((dt >= a) & (dt < b)).then(pl.lit(f"{a}-{b}")).otherwise(expr)
    return expr


# ---------------------------------------------------------------- report

KAPPA_BINS: tuple[int, ...] = (0, 20, 40, 60, 100, 250, 500, 1000)
MOVE_BINS: tuple[int, ...] = (0, 20, 100, 250, 1000)


def _per_anchor(df: pl.DataFrame, value: pl.Expr, bins: Sequence[int], aids: pl.Series) -> F64:
    """(n_anchors × n_bins) sums of ``value`` per anchor and time bin (anchors in ``aids``
    order, zeros where empty)."""
    labels = [f"{a}-{b}" for a, b in zip(bins[:-1], bins[1:], strict=True)]
    g = (
        df.with_columns(bin_label(pl.col("dt_ms"), bins).alias("bin"))
        .filter(pl.col("bin").is_not_null())
        .group_by("aid", "bin")
        .agg(value.sum().alias("v"))
    )
    out = np.zeros((len(aids), len(labels)))
    pos = {a: i for i, a in enumerate(aids.to_list())}
    col = {b: j for j, b in enumerate(labels)}
    for a, b, v in g.iter_rows():
        if a in pos:
            out[pos[a], col[b]] = v
    return out


def _boot_ratio(
    num: F64, den: F64, w: F64, n_boot: int, rng: np.random.Generator
) -> tuple[F64, F64]:
    """Point estimate Σw·num/Σw·den per column and (n_boot × cols) anchor-bootstrap draws."""
    est = (w @ num) / np.where(w @ den > 0, w @ den, np.nan)
    draws = np.empty((n_boot, num.shape[1]))
    for b in range(n_boot):
        i = rng.integers(0, len(w), len(w))
        d = w[i] @ den[i]
        draws[b] = (w[i] @ num[i]) / np.where(d > 0, d, np.nan)
    return est, draws


def _ci(draws: F64) -> tuple[F64, F64]:
    return np.nanpercentile(draws, 2.5, axis=0), np.nanpercentile(draws, 97.5, axis=0)


def run_l3(
    raw_root: Path,
    cache_root: Path,
    results_dir: Path,
    *,
    min_levels: int = 3,
    min_bps: float = 0.5,
    placebo_per_sweep: int = 20,
    near_bps: float = 1.0,
    lag_ms: float = 100.0,
    n_boot: int = 500,
    seed: int = 0,
) -> str:
    """Full Bitstamp L3 analysis; writes ``l3.md`` and ``l3_*.parquet`` to ``results_dir``."""
    from lobflow.state import nn_weights

    rng = np.random.default_rng(seed)
    ev = load_events(raw_root, cache_root)
    snaps = load_snapshots(raw_root)
    trades = ev.filter(pl.col("ev") == EV_TRADE)
    sweeps = find_sweeps(trades, min_levels=min_levels, min_bps=min_bps)
    takers = find_sweeps(trades, min_levels=2, isolate_ms=0)
    r0, _ = replay(ev, snaps)
    plac = placebo_times(r0, takers, n=placebo_per_sweep * len(sweeps), seed=seed)
    anchors = (
        pl.concat(
            [
                sweeps.select("t_first", "t_end", "book_side").with_columns(
                    pl.lit(1, dtype=pl.Int8).alias("is_sweep")
                ),
                plac.with_columns(pl.lit(0, dtype=pl.Int8).alias("is_sweep")),
            ]
        )
        .with_row_index("aid")
        .with_columns(pl.col("aid").cast(pl.Int64), (pl.col("t_first") - 1000).alias("t_pre"))
    )
    rep, anc = replay(ev, snaps, anchors)
    anc = anc.filter((pl.col("seg") >= 0) & pl.col("depth_pre").is_not_nan()).sort("aid")
    anc = anchor_covariates(trades, anc).rename({"depth_pre": "depth_pre_swept"})
    s_cov, p_cov = anc.filter(pl.col("is_sweep") == 1), anc.filter(pl.col("is_sweep") == 0)
    p_cov = nn_weights(s_cov, p_cov, k=5)
    anc = pl.concat(
        [s_cov.with_columns(pl.lit(1.0).alias("w")), p_cov.drop("sweep_coverage")],
        how="diagonal_relaxed",
    ).sort("aid")
    flows = window_flows(rep, anc, window_ms=(-200, 3400))
    early = flows.filter(pl.col("dt_ms") < 1000)
    moves = move_flags(early, near_bps=near_bps, lag_ms=lag_ms, pool=flows)

    results_dir.mkdir(parents=True, exist_ok=True)
    anc.write_parquet(results_dir / "l3_anchors.parquet")
    moves.write_parquet(results_dir / "l3_moves.parquet")

    groups = {g: anc.filter(pl.col("is_sweep") == g) for g in (1, 0)}
    vol = pl.col("amt").cast(pl.Float64) / SAT
    f_pos = early.filter(pl.col("dist_bps") >= 0)

    # κ = adds / cancels per bin
    kap: dict[int, tuple[F64, F64]] = {}
    for g, a in groups.items():
        fa = f_pos.filter(pl.col("aid").is_in(a["aid"].implode()))
        num = _per_anchor(fa.filter(pl.col("kind") == "add"), vol, KAPPA_BINS, a["aid"])
        den = _per_anchor(fa.filter(pl.col("kind") == "cancel"), vol, KAPPA_BINS, a["aid"])
        kap[g] = _boot_ratio(num, den, a["w"].to_numpy(), n_boot, rng)

    # move shares (volume-weighted) per bin, plus pooled 20-250 and 0-1000
    mbins = MOVE_BINS
    pooled = {"20-250": (1, 3), "0-1000": (0, 4)}
    share: dict[int, dict[str, tuple[F64, F64]]] = {}
    for g, a in groups.items():
        ma = moves.filter(pl.col("aid").is_in(a["aid"].implode()))
        tot = _per_anchor(ma, vol, mbins, a["aid"])
        cols = {
            "exact": _per_anchor(ma, vol * pl.col("exact").cast(pl.Float64), mbins, a["aid"]),
            "time": _per_anchor(ma, vol * pl.col("ctrl_time").cast(pl.Float64), mbins, a["aid"]),
            "lot": _per_anchor(ma, vol * pl.col("ctrl_lot"), mbins, a["aid"]),
        }
        cols["beyond"] = cols["exact"] - cols["time"]
        ext = {
            k: np.column_stack([v] + [v[:, i:j].sum(1) for i, j in pooled.values()])
            for k, v in cols.items()
        }
        tot_ext = np.column_stack([tot] + [tot[:, i:j].sum(1) for i, j in pooled.values()])
        sub = np.random.default_rng(seed + 1 + g)  # same draws across statistics
        share[g] = {}
        for k, v in ext.items():
            share[g][k] = _boot_ratio(v, tot_ext, a["w"].to_numpy(), n_boot, sub)

    # same-ID in-place moves into the touch: share of near-touch inflow (adds + moves in)
    toward = (
        pl.when(pl.col("side") == 1)
        .then(pl.col("px") < pl.col("prev_px"))
        .otherwise(pl.col("px") > pl.col("prev_px"))
    )
    near_in = early.filter(
        (pl.col("dt_ms") >= 0)
        & (pl.col("dist_bps") <= near_bps)
        & ((pl.col("kind") == "add") | ((pl.col("kind") == "move") & toward))
    )
    n_inplace = {
        g: int(
            near_in.filter(pl.col("kind") == "move", pl.col("aid").is_in(a["aid"].implode())).height
        )
        for g, a in groups.items()
    }
    for g, a in groups.items():
        na = near_in.filter(pl.col("aid").is_in(a["aid"].implode()))
        num = _per_anchor(na.filter(pl.col("kind") == "move"), vol, mbins, a["aid"])
        den = _per_anchor(na, vol, mbins, a["aid"])
        num = np.column_stack([num] + [num[:, i:j].sum(1) for i, j in pooled.values()])
        den = np.column_stack([den] + [den[:, i:j].sum(1) for i, j in pooled.values()])
        share[g]["inplace"] = _boot_ratio(
            num, den, a["w"].to_numpy(), n_boot, np.random.default_rng(seed + 10 + g)
        )

    # balance (weighted standardised differences)
    def sdiff(c: str) -> float:
        xs = np.log1p(groups[1][c].to_numpy())
        xp = np.log1p(groups[0][c].to_numpy())
        wp = groups[0]["w"].to_numpy()
        return float((xs.mean() - np.average(xp, weights=wp)) / (xs.std() or 1.0))

    def fmt(v: float) -> str:
        return f"{v:.3f}"

    def ci(e: F64, d: F64, j: int) -> str:
        lo, hi = _ci(d)
        return f"{fmt(e[j])} [{fmt(lo[j])}, {fmt(hi[j])}]"

    hours = (ev["t_us"].max() - ev["t_us"].min()) / 3.6e9  # type: ignore[operator]
    n_ord = int(ev.filter(pl.col("ev") != EV_TRADE).height)
    kl = [f"{a}-{b}" for a, b in zip(KAPPA_BINS[:-1], KAPPA_BINS[1:], strict=True)]
    ml = [f"{a}-{b}" for a, b in zip(mbins[:-1], mbins[1:], strict=True)] + list(pooled)
    lines = [
        "# Bitstamp BTC/USD order-level (L3) replication",
        "",
        f"Sample: {hours:.1f} h, {n_ord:,} order events, {trades.height:,} trades; "
        f"{groups[1].height} isolated sweeps (taker filling at ≥{min_levels} prices spanning "
        f"≥{min_bps} bps), {groups[0].height} placebo times (NN-matched, k=5, on vol_10s, "
        "rv_60s, swept-side depth within 10 bps). 95% anchor-bootstrap CIs "
        f"({n_boot} draws). Swept side, within 10 bps of the opposite best quote.",
        "",
        "Balance (standardised difference, log1p): "
        + ", ".join(f"{c} {sdiff(c):+.2f}" for c in ("vol_10s", "rv_60s", "depth_pre_swept")),
        "",
        "## κ = added / cancelled volume",
        "",
        "| window (ms) | sweep | placebo |",
        "|---|---|---|",
        *[f"| {lab} | {ci(*kap[1], j)} | {ci(*kap[0], j)} |" for j, lab in enumerate(kl)],
        "",
        f"## Exact-amount moves into the touch (adds within {near_bps} bps)",
        "",
        "Share of near-touch added volume that has a cancel of the identical amount (satoshi) "
        f"at a strictly deeper price within ±{lag_ms:.0f} ms. Controls: amount ±1 satoshi "
        "(`lot`); same rule against cancels 2 s later (`time`, captures repeated quote "
        "sizes). `beyond` = exact − time.",
        "",
        "| window (ms) | sweep exact | sweep lot | sweep time | sweep beyond | "
        "placebo exact | placebo time | placebo beyond |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for j, lab in enumerate(ml):
        s1, s0 = share[1], share[0]
        lines.append(
            f"| {lab} | {fmt(s1['exact'][0][j])} | {fmt(s1['lot'][0][j])} | "
            f"{fmt(s1['time'][0][j])} | {ci(*s1['beyond'], j)} | {fmt(s0['exact'][0][j])} | "
            f"{fmt(s0['time'][0][j])} | {ci(*s0['beyond'], j)} |"
        )
    lines += [
        "",
        "## Same-ID in-place moves into the touch",
        "",
        "Resting orders re-priced in place (``order_changed`` with a new price and the same ID; "
        "taker orders, whose price field follows their fills, excluded). "
        f"Share of near-touch inflow volume (adds + in-place moves toward the touch, within "
        f"{near_bps} bps) that is an in-place move. Events: sweeps {n_inplace[1]}, placebo "
        f"{n_inplace[0]}.",
        "",
        "| window (ms) | sweep | placebo |",
        "|---|---|---|",
        *[
            f"| {lab} | {ci(*share[1]['inplace'], j)} | {ci(*share[0]['inplace'], j)} |"
            for j, lab in enumerate(ml)
        ],
    ]
    text = "\n".join(lines) + "\n"
    (results_dir / "l3.md").write_text(text)
    rows = []
    for g in (1, 0):
        for j, lab in enumerate(kl):
            rows.append(
                {
                    "set": g,
                    "stat": "kappa",
                    "bin": lab,
                    "est": float(kap[g][0][j]),
                    "lo": float(_ci(kap[g][1])[0][j]),
                    "hi": float(_ci(kap[g][1])[1][j]),
                }
            )
        for k, (e, d) in share[g].items():
            for j, lab in enumerate(ml):
                rows.append(
                    {
                        "set": g,
                        "stat": k,
                        "bin": lab,
                        "est": float(e[j]),
                        "lo": float(_ci(d)[0][j]),
                        "hi": float(_ci(d)[1][j]),
                    }
                )
    pl.DataFrame(rows).write_parquet(results_dir / "l3_summary.parquet")
    return text
