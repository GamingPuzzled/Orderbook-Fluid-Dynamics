"""Per-day processing: sweeps → fixed-frame panel, moving-frame profiles, placebo profiles."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import polars as pl

from lobflow.convert import infer_tick_size
from lobflow.events import DEFAULT_TAUS_MS, PanelParams, build_event_panel, load_book_arrays
from lobflow.flows import DEFAULT_EDGES_MS, flow_panel
from lobflow.profiles import placebo_times, profile_panel
from lobflow.state import state_covariates
from lobflow.sweeps import SweepParams, detect_sweeps

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class FeedStats:
    """Feed-quality diagnostics for one book file (exchange clock)."""

    n_updates: int
    n_messages: int
    n_snapshot_resets: int
    snapshot_levels_bid: int
    snapshot_levels_ask: int
    push_interval_ms_p50: float
    push_interval_ms_p90: float
    latency_ms_p50: float
    latency_ms_p99: float


def feed_stats(book: pl.DataFrame) -> FeedStats:
    msg = book.group_by("local_timestamp", maintain_order=True).agg(
        pl.col("timestamp").first(), pl.col("is_snapshot").first()
    )
    snaps = msg["is_snapshot"].to_numpy()
    resets = int(np.sum(snaps[1:] & ~snaps[:-1]) + int(snaps[0])) if snaps.size else 0
    first_snap_ts = book.filter(pl.col("is_snapshot"))["local_timestamp"].head(1)
    lv = (
        book.filter(pl.col("is_snapshot") & (pl.col("local_timestamp") == first_snap_ts[0]))
        .group_by("side")
        .len()
        if first_snap_ts.len()
        else pl.DataFrame({"side": [], "len": []})
    )
    levels = dict(zip(lv["side"].to_list(), lv["len"].to_list(), strict=True))
    dt = np.diff(msg["timestamp"].to_numpy()) / 1000.0
    lat = (book["local_timestamp"] - book["timestamp"]).to_numpy() / 1000.0
    return FeedStats(
        n_updates=book.height,
        n_messages=msg.height,
        n_snapshot_resets=resets,
        snapshot_levels_bid=int(levels.get("bid", 0)),
        snapshot_levels_ask=int(levels.get("ask", 0)),
        push_interval_ms_p50=float(np.percentile(dt, 50)) if dt.size else float("nan"),
        push_interval_ms_p90=float(np.percentile(dt, 90)) if dt.size else float("nan"),
        latency_ms_p50=float(np.percentile(lat, 50)),
        latency_ms_p99=float(np.percentile(lat, 99)),
    )


def placebo_design(
    runs: pl.DataFrame, book_ts: np.ndarray, n_placebo: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """Placebo times (≥ 2 s from any large candidate run) and random sides; deterministic."""
    big = runs.filter(pl.col("is_candidate") & (pl.col("volume") >= pl.col("size_threshold")))
    t_pl = placebo_times(
        int(book_ts[0]) + 5_000_000,
        int(book_ts[-1]) - 5_000_000,
        n_placebo,
        big["timestamp"].to_numpy().astype(np.int64),
        seed=seed,
    )
    rng = np.random.default_rng(seed + 1)
    pl_buy = np.asarray(rng.random(t_pl.shape[0]) < 0.5, dtype=np.bool_)
    return t_pl, pl_buy


def process_flows_day(
    parquet_root: Path,
    out_root: Path,
    exchange: str,
    symbol: str,
    day: str,
    *,
    edges_ms: tuple[int, ...] = DEFAULT_EDGES_MS,
    n_placebo: int = 2000,
    seed: int = 0,
    tag: str = "flows",
    coarsen_us: int = 0,
) -> dict[str, int]:
    """Gross-flow (mass balance) outputs for a day already run through ``process_day``.

    Reuses the stored events (``t0``, side) and regenerates the identical placebo design.
    Writes ``{day}_{tag}.parquet``, ``{day}_{tag}_info.parquet`` and the ``_placebo``
    counterparts (``tag`` lets alternative window grids coexist with the default).
    """
    out = out_root / exchange / symbol
    meta = json.loads((out / f"{day}_meta.json").read_text())
    ev_path = out / f"{day}_events.parquet"
    if not ev_path.exists():
        return {"n_events": 0, "n_placebo": 0}
    root = parquet_root / exchange
    book = pl.read_parquet(root / "incremental_book_L2" / symbol / f"{day}.parquet")
    trades = pl.read_parquet(root / "trades" / symbol / f"{day}.parquet").sort(
        "timestamp", maintain_order=True
    )
    tk = float(meta["tick"])
    arrays = load_book_arrays(book, "exchange")
    sp = SweepParams(**meta["sweep_params"])
    runs = detect_sweeps(trades, tk, sp)
    ev = pl.read_parquet(ev_path).sort("event_id")
    n_pl = _write_flows(
        out, day, arrays, trades, runs, ev, tk, edges_ms, n_placebo, seed, tag, coarsen_us
    )
    log.info("%s %s %s: flows for %d events, %d placebo", exchange, symbol, day, ev.height, n_pl)
    return {"n_events": ev.height, "n_placebo": n_pl}


def _write_flows(
    out: Path,
    day: str,
    arrays: dict[str, np.ndarray],
    trades: pl.DataFrame,
    runs: pl.DataFrame,
    ev: pl.DataFrame,
    tk: float,
    edges_ms: tuple[int, ...],
    n_placebo: int,
    seed: int,
    tag: str = "flows",
    coarsen_us: int = 0,
) -> int:
    """Write sweep and placebo gross-flow tables; ``trades`` sorted, ``ev`` sorted by id."""
    tr = (
        trades["timestamp"].to_numpy().astype(np.int64),
        trades["price"].to_numpy(),
        trades["amount"].to_numpy(),
        (trades["side"] == "buy").to_numpy(),
    )
    t_pl, pl_buy = placebo_design(runs, arrays["ts"], n_placebo, seed)
    sets = {
        tag: (ev["t0"].to_numpy().astype(np.int64), (ev["side"] == "buy").to_numpy()),
        f"{tag}_placebo": (t_pl, pl_buy),
    }
    for name, (t0, is_buy) in sets.items():
        flows, info = flow_panel(
            arrays, *tr, t0, is_buy, tk, edges_ms=edges_ms, coarsen_us=coarsen_us
        )
        flows.write_parquet(out / f"{day}_{name}.parquet")
        info.with_columns(pl.Series("is_buy", is_buy)).write_parquet(
            out / f"{day}_{name}_info.parquet"
        )
    return int(t_pl.size)


def process_moves_day(
    parquet_root: Path,
    out_root: Path,
    exchange: str,
    symbol: str,
    day: str,
    *,
    n_placebo: int = 2000,
    seed: int = 0,
    lag_ms: int = 100,
) -> dict[str, int]:
    """Exact-size matching statistics (:mod:`lobflow.moves`) for sweeps and the identical
    placebo design; writes ``{day}_moves.parquet`` (column ``set``: sweep / placebo)."""
    from lobflow.moves import LogRow, common_sizes, log_frame, lot_size, move_stats

    out = out_root / exchange / symbol
    meta = json.loads((out / f"{day}_meta.json").read_text())
    ev_path = out / f"{day}_events.parquet"
    if not ev_path.exists():
        return {"n_events": 0, "n_placebo": 0}
    root = parquet_root / exchange
    book = pl.read_parquet(root / "incremental_book_L2" / symbol / f"{day}.parquet")
    trades = pl.read_parquet(root / "trades" / symbol / f"{day}.parquet").sort(
        "timestamp", maintain_order=True
    )
    tk = float(meta["tick"])
    arrays = load_book_arrays(book, "exchange")
    runs = detect_sweeps(trades, tk, SweepParams(**meta["sweep_params"]))
    ev = pl.read_parquet(ev_path).sort("event_id")
    tr = (
        trades["timestamp"].to_numpy().astype(np.int64),
        trades["price"].to_numpy(),
        trades["amount"].to_numpy(),
        (trades["side"] == "buy").to_numpy(),
    )
    t_pl, pl_buy = placebo_design(runs, arrays["ts"], n_placebo, seed)
    sets = {
        "sweep": (ev["t0"].to_numpy().astype(np.int64), (ev["side"] == "buy").to_numpy()),
        "placebo": (t_pl, pl_buy),
    }
    logs = {}
    for name, (t0, is_buy) in sets.items():
        raw: list[LogRow] = []
        flow_panel(arrays, *tr, t0, is_buy, tk, edges_ms=(0, 1000), log=raw)
        logs[name] = log_frame(raw)
    common = common_sizes(list(logs.values()))
    lot = lot_size(list(logs.values()))
    stats = pl.concat(
        [
            move_stats(lg, common, lot, lag_ms=lag_ms).with_columns(pl.lit(name).alias("set"))
            for name, lg in logs.items()
        ]
    )
    stats.write_parquet(out / f"{day}_moves.parquet")
    log.info(
        "%s %s %s: moves for %d events, %d placebo", exchange, symbol, day, ev.height, t_pl.size
    )
    return {"n_events": ev.height, "n_placebo": int(t_pl.size)}


def process_state_day(
    parquet_root: Path,
    out_root: Path,
    exchange: str,
    symbol: str,
    day: str,
    *,
    n_placebo: int = 2000,
    seed: int = 0,
) -> int:
    """Write ``{day}_state.parquet``: pre-event covariates for sweeps and placebo times.

    Columns: set ("sweep" | "placebo"), event_id, t0, vol_10s, rv_60s, n_10s. Placebo ids
    and times match ``process_day`` / ``process_flows_day`` (same deterministic design).
    """
    out = out_root / exchange / symbol
    ev_path = out / f"{day}_events.parquet"
    if not ev_path.exists():
        return 0
    meta = json.loads((out / f"{day}_meta.json").read_text())
    root = parquet_root / exchange
    trades = pl.read_parquet(root / "trades" / symbol / f"{day}.parquet").sort(
        "timestamp", maintain_order=True
    )
    ts_range = (
        pl.scan_parquet(root / "incremental_book_L2" / symbol / f"{day}.parquet")
        .select(pl.col("timestamp").min().alias("lo"), pl.col("timestamp").max().alias("hi"))
        .collect()
        .row(0)
    )
    runs = detect_sweeps(trades, float(meta["tick"]), SweepParams(**meta["sweep_params"]))
    t_pl, _ = placebo_design(runs, np.array(ts_range, dtype=np.int64), n_placebo, seed)
    ev = pl.read_parquet(ev_path).sort("event_id")
    _write_state(out, day, trades, runs, ev, np.array(ts_range, dtype=np.int64), n_placebo, seed)
    return ev.height


def _write_state(
    out: Path,
    day: str,
    trades: pl.DataFrame,
    runs: pl.DataFrame,
    ev: pl.DataFrame,
    book_ts: np.ndarray,
    n_placebo: int,
    seed: int,
) -> None:
    """Write pre-event state covariates for sweeps and placebo (``trades`` sorted by time)."""
    t_pl, _ = placebo_design(runs, book_ts, n_placebo, seed)
    tt = trades["timestamp"].to_numpy().astype(np.int64)
    tp, ta = trades["price"].to_numpy(), trades["amount"].to_numpy()
    parts = []
    for name, t0 in (("sweep", ev["t0"].to_numpy().astype(np.int64)), ("placebo", t_pl)):
        cov = state_covariates(tt, tp, ta, t0)
        parts.append(
            cov.with_columns(
                pl.lit(name).alias("set"),
                pl.Series("event_id", np.arange(t0.shape[0], dtype=np.int64)),
                pl.Series("t0", t0),
            )
        )
    pl.concat(parts).write_parquet(out / f"{day}_state.parquet")


def process_day(
    parquet_root: Path,
    out_root: Path,
    exchange: str,
    symbol: str,
    day: str,
    *,
    tick: float | None = None,
    sweep_params: SweepParams | None = None,
    taus_ms: tuple[int, ...] = DEFAULT_TAUS_MS,
    max_d: int = 50,
    n_placebo: int = 2000,
    seed: int = 0,
    extras: bool = True,
) -> dict[str, object]:
    """Run the full per-day pipeline and write outputs to ``out_root/exchange/symbol``.

    Files: ``{day}_events.parquet``, ``{day}_panel.parquet`` (fixed frame),
    ``{day}_moving.parquet`` (sweep profiles), ``{day}_placebo.parquet`` (placebo profiles),
    ``{day}_meta.json`` (feed stats, parameters, counts). With ``extras`` (default) also the
    gross-flow and state-covariate files (as ``process_flows_day`` / ``process_state_day``),
    reusing the in-memory book.
    """
    root = parquet_root / exchange
    book = pl.read_parquet(root / "incremental_book_L2" / symbol / f"{day}.parquet")
    trades = pl.read_parquet(root / "trades" / symbol / f"{day}.parquet")
    tk = tick or infer_tick_size(book["price"].head(2_000_000).to_numpy())
    fs = feed_stats(book)
    sp = sweep_params or SweepParams()

    runs = detect_sweeps(trades, tk, sp)
    sweeps = runs.filter(pl.col("selected"))
    out = out_root / exchange / symbol
    out.mkdir(parents=True, exist_ok=True)
    meta: dict[str, object] = {
        "exchange": exchange,
        "symbol": symbol,
        "day": day,
        "tick": tk,
        "feed": asdict(fs),
        "sweep_params": asdict(sp),
        "taus_ms": list(taus_ms),
        "n_runs": runs.height,
        "n_candidates": int(runs["is_candidate"].sum()),
        "n_selected": sweeps.height,
    }
    if sweeps.height == 0:
        (out / f"{day}_meta.json").write_text(json.dumps(meta, indent=2))
        return meta

    arrays = load_book_arrays(book, "exchange")
    pp = PanelParams(taus_ms=taus_ms, confirm_tau_ms=taus_ms[0])
    events, panel = build_event_panel(arrays, sweeps, tk, pp)
    events = events.with_columns(pl.lit(tk).alias("tick"), pl.lit(day).alias("day"))

    sw_sorted = sweeps.sort("timestamp")
    t0 = sw_sorted["timestamp"].to_numpy().astype(np.int64)
    is_buy = (sw_sorted["side"] == "buy").to_numpy()
    moving = profile_panel(arrays, t0, is_buy, tk, taus_ms, max_d=max_d)

    t_pl, pl_buy = placebo_design(runs, arrays["ts"], n_placebo, seed)
    placebo = profile_panel(arrays, t_pl, pl_buy, tk, taus_ms, max_d=max_d).with_columns(
        pl.Series("is_buy", np.repeat(pl_buy, (len(taus_ms) + 1) * max_d))
    )

    events.write_parquet(out / f"{day}_events.parquet")
    panel.write_parquet(out / f"{day}_panel.parquet")
    moving.write_parquet(out / f"{day}_moving.parquet")
    placebo.write_parquet(out / f"{day}_placebo.parquet")
    meta["n_events"] = events.height
    meta["n_placebo"] = int(t_pl.shape[0])
    if extras:
        tr_sorted = trades.sort("timestamp", maintain_order=True)
        ev_sorted = events.sort("event_id")
        _write_flows(
            out, day, arrays, tr_sorted, runs, ev_sorted, tk, DEFAULT_EDGES_MS, n_placebo, seed
        )
        _write_state(out, day, tr_sorted, runs, ev_sorted, arrays["ts"], n_placebo, seed)
    (out / f"{day}_meta.json").write_text(json.dumps(meta, indent=2))
    log.info("%s %s %s: %d events, %d placebo", exchange, symbol, day, events.height, t_pl.size)
    return meta
