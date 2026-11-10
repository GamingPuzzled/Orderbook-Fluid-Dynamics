"""Command-line entry point: ``lobflow {download,convert,events,batch,analyze,flows}``."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from datetime import date
from pathlib import Path
from typing import Any

import polars as pl

from lobflow.convert import csv_gz_to_parquet
from lobflow.pipeline import process_day
from lobflow.sweeps import SweepParams
from lobflow.tardis import DatasetSpec, TardisError, download, first_days

log = logging.getLogger("lobflow")


def _cmd_download(a: argparse.Namespace) -> int:
    days = first_days(date.fromisoformat(a.start), date.fromisoformat(a.end))
    failures = 0
    for d in days:
        for dt in a.data_types:
            try:
                download(DatasetSpec(a.exchange, dt, d, a.symbol), Path(a.raw))
            except TardisError as exc:
                log.error("%s", exc)
                failures += 1
    return 1 if failures else 0


def _cmd_convert(a: argparse.Namespace) -> int:
    raw, out = Path(a.raw), Path(a.out)
    for src in sorted(raw.rglob("*.csv.gz")):
        rel = src.relative_to(raw)
        data_type = rel.parts[1]
        dest = out / rel.with_suffix("").with_suffix(".parquet")
        if dest.exists() and not a.overwrite:
            continue
        rows = csv_gz_to_parquet(src, dest, data_type)
        log.info("converted %s -> %s (%d rows)", src, dest, rows)
    return 0


def _cmd_events(a: argparse.Namespace) -> int:
    process_day(
        Path(a.parquet),
        Path(a.out),
        a.exchange,
        a.symbol,
        a.day,
        tick=a.tick,
        sweep_params=SweepParams(a.min_levels, a.size_quantile, a.isolation_ms * 1000),
    )
    return 0


def _init_worker(level: int) -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(message)s")


def _run_days(fn: Callable[..., int], jobs: list[tuple[Any, ...]], workers: int) -> int:
    """Run ``fn(*job)`` for each job, in parallel processes if ``workers > 1``.

    ``fn`` returns the number of failures for its day; the total is returned.
    """
    if workers <= 1:
        return sum(fn(*j) for j in jobs)
    level = logging.getLogger().getEffectiveLevel()
    with ProcessPoolExecutor(workers, initializer=_init_worker, initargs=(level,)) as ex:
        return sum(f.result() for f in [ex.submit(fn, *j) for j in jobs])


def _batch_day(
    exchange: str,
    symbol: str,
    day: str,
    raw: Path,
    pq_root: Path,
    out: Path,
    tick: float | None,
    prune_raw: bool,
) -> int:
    d = date.fromisoformat(day)
    try:
        for dt in ("incremental_book_L2", "trades"):
            spec = DatasetSpec(exchange, dt, d, symbol)
            src = download(spec, raw)
            dest = pq_root / exchange / dt / symbol / f"{day}.parquet"
            if not dest.exists():
                csv_gz_to_parquet(src, dest, dt)
            if prune_raw:
                src.unlink(missing_ok=True)
        process_day(pq_root, out, exchange, symbol, day, tick=tick)
    except (TardisError, OSError, ValueError, pl.exceptions.PolarsError) as exc:
        log.error("day %s failed: %s", day, exc)
        return 1
    return 0


def _cmd_batch(a: argparse.Namespace) -> int:
    """Download → convert → process each first-of-month day; optionally prune raw files."""
    raw, pq_root, out = Path(a.raw), Path(a.parquet), Path(a.out)
    days = first_days(date.fromisoformat(a.start), date.fromisoformat(a.end))
    if a.days:
        wanted = set(a.days.split(","))
        days = [d for d in days if d.isoformat() in wanted]
    jobs = []
    for d in days:
        day = d.isoformat()
        if (out / a.exchange / a.symbol / f"{day}_meta.json").exists() and not a.overwrite:
            log.info("skip %s (done)", day)
            continue
        jobs.append((a.exchange, a.symbol, day, raw, pq_root, out, a.tick, a.prune_raw))
    failures = _run_days(_batch_day, jobs, a.workers)
    log.info("batch done: %d days, %d failures", len(days), failures)
    return 1 if failures else 0


def _cmd_analyze(a: argparse.Namespace) -> int:
    from lobflow.analysis import run

    out = Path(a.events) / a.exchange / a.symbol
    print(run(out, Path(a.results) / a.exchange / a.symbol, max_push_ms=a.max_push_ms))
    return 0


def _flows_day(
    parquet: Path,
    events: Path,
    exchange: str,
    symbol: str,
    day: str,
    state_only: bool,
    tag: str = "flows",
    edges_ms: tuple[int, ...] | None = None,
) -> int:
    from lobflow.flows import DEFAULT_EDGES_MS
    from lobflow.pipeline import process_flows_day, process_state_day

    try:
        if not state_only:
            edges = edges_ms or DEFAULT_EDGES_MS
            process_flows_day(parquet, events, exchange, symbol, day, edges_ms=edges, tag=tag)
        if tag == "flows":
            process_state_day(parquet, events, exchange, symbol, day)
    except Exception as exc:  # report and continue with other days
        log.error("flows %s failed: %s", day, exc)
        return 1
    return 0


def _cmd_flows(a: argparse.Namespace) -> int:
    """Gross-flow outputs for every processed main-sample day (push ≤ --max-push-ms, ≥ 50
    levels)."""
    import json

    out = Path(a.events) / a.exchange / a.symbol
    only = set(a.days.split(",")) if a.days else None
    jobs = []
    for f in sorted(out.glob("*_meta.json")):
        m = json.loads(f.read_text())
        fd = m["feed"]
        main = fd["push_interval_ms_p50"] <= a.max_push_ms and (
            min(fd["snapshot_levels_bid"], fd["snapshot_levels_ask"]) >= 50
        )
        day = m["day"]
        done = "state" if a.state_only else f"{a.tag}_info"
        if not main or (only is not None and day not in only):
            continue
        if not a.overwrite and (out / f"{day}_{done}.parquet").exists():
            continue
        edges = tuple(int(x) for x in a.edges.split(",")) if a.edges else None
        jobs.append(
            (Path(a.parquet), Path(a.events), a.exchange, a.symbol, day, a.state_only, a.tag, edges)
        )
    return 1 if _run_days(_flows_day, jobs, a.workers) else 0


def _moves_day(parquet: Path, events: Path, exchange: str, symbol: str, day: str) -> int:
    from lobflow.pipeline import process_moves_day

    try:
        process_moves_day(parquet, events, exchange, symbol, day)
        return 0
    except Exception:
        log.exception("moves failed for %s %s %s", exchange, symbol, day)
        return 1


def _main_days(out: Path, max_push_ms: float) -> list[str]:
    """Processed days whose feed meets the main-sample spec."""
    import json

    days = []
    for f in sorted(out.glob("*_meta.json")):
        m = json.loads(f.read_text())
        fd = m["feed"]
        if (
            fd["push_interval_ms_p50"] <= max_push_ms
            and (min(fd["snapshot_levels_bid"], fd["snapshot_levels_ask"]) >= 50)
            and (out / f"{m['day']}_events.parquet").exists()
        ):
            days.append(m["day"])
    return days


def _cmd_moves(a: argparse.Namespace) -> int:
    from lobflow.moves import run_moves

    out = Path(a.events) / a.exchange / a.symbol
    days = _main_days(out, a.max_push_ms)
    todo = [d for d in days if a.overwrite or not (out / f"{d}_moves.parquet").exists()]
    jobs = [(Path(a.parquet), Path(a.events), a.exchange, a.symbol, d) for d in todo]
    failed = _run_days(_moves_day, jobs, a.workers)
    res = Path(a.results) / a.exchange / a.symbol
    print(run_moves(out, res, max_push_ms=a.max_push_ms))
    return 1 if failed else 0


def _cmd_pde(a: argparse.Namespace) -> int:
    from lobflow.pde import run_pde

    out = Path(a.events) / a.exchange / a.symbol
    res = Path(a.results) / a.exchange / a.symbol
    print(run_pde(out, res, max_push_ms=a.max_push_ms, n_folds=a.folds))
    return 0


def _cmd_execution(a: argparse.Namespace) -> int:
    from lobflow.execution import run_execution

    out = Path(a.events) / a.exchange / a.symbol
    res = Path(a.results) / a.exchange / a.symbol
    print(run_execution(out, res, max_push_ms=a.max_push_ms, n_boot=a.n_boot))
    return 0


def _cmd_l3(a: argparse.Namespace) -> int:
    from lobflow.l3 import run_l3

    text = run_l3(
        Path(a.raw) / a.pair,
        Path(a.cache) / a.pair,
        Path(a.results) / "bitstamp" / a.pair,
        min_levels=a.min_levels,
        min_bps=a.min_bps,
        near_bps=a.near_bps,
        n_boot=a.n_boot,
    )
    print(text)
    return 0


def _cmd_model(a: argparse.Namespace) -> int:
    from lobflow.model import run_model

    out = Path(a.events) / a.exchange / a.symbol
    res = Path(a.results) / a.exchange / a.symbol
    print(run_model(out, res, tag=a.tag, n_boot=a.n_boot, max_push_ms=a.max_push_ms))
    return 0


def _cmd_robustness(a: argparse.Namespace) -> int:
    from lobflow.robustness import run_robustness

    out = Path(a.events) / a.exchange / a.symbol
    res = Path(a.results) / a.exchange / a.symbol
    print(run_robustness(out, res, tag=a.tag, n_boot=a.n_boot, k=a.k, max_push_ms=a.max_push_ms))
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="lobflow")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download", help="fetch Tardis free first-of-month files")
    d.add_argument("--exchange", required=True, help="e.g. bybit, binance-futures")
    d.add_argument("--symbol", required=True, help="e.g. BTCUSDT")
    d.add_argument("--start", required=True, help="YYYY-MM-DD")
    d.add_argument("--end", required=True, help="YYYY-MM-DD")
    d.add_argument("--data-types", nargs="+", default=["incremental_book_L2", "trades"])
    d.add_argument("--raw", default="data/raw")
    d.set_defaults(fn=_cmd_download)

    c = sub.add_parser("convert", help="csv.gz -> parquet")
    c.add_argument("--raw", default="data/raw")
    c.add_argument("--out", default="data/parquet")
    c.add_argument("--overwrite", action="store_true")
    c.set_defaults(fn=_cmd_convert)

    e = sub.add_parser("events", help="detect sweeps and build event panel for one day")
    e.add_argument("--exchange", required=True)
    e.add_argument("--symbol", required=True)
    e.add_argument("--day", required=True, help="YYYY-MM-DD")
    e.add_argument("--parquet", default="data/parquet")
    e.add_argument("--out", default="data/events")
    e.add_argument("--tick", type=float, default=None, help="override inferred tick size")
    e.add_argument("--min-levels", type=int, default=3)
    e.add_argument("--size-quantile", type=float, default=0.95)
    e.add_argument("--isolation-ms", type=int, default=500)
    e.set_defaults(fn=_cmd_events)

    b = sub.add_parser("batch", help="download+convert+process a range of free days")
    b.add_argument("--exchange", required=True)
    b.add_argument("--symbol", required=True)
    b.add_argument("--start", required=True)
    b.add_argument("--end", required=True)
    b.add_argument("--raw", default="data/raw")
    b.add_argument("--parquet", default="data/parquet")
    b.add_argument("--out", default="data/events")
    b.add_argument("--tick", type=float, default=None)
    b.add_argument("--prune-raw", action="store_true", help="delete csv.gz after conversion")
    b.add_argument("--overwrite", action="store_true")
    b.add_argument("--workers", type=int, default=1, help="days processed in parallel")
    b.add_argument("--days", default=None, help="comma-separated subset of days in range")
    b.set_defaults(fn=_cmd_batch)

    z = sub.add_parser("analyze", help="pool processed days and write results/summary.md")
    z.add_argument("--exchange", required=True)
    z.add_argument("--symbol", required=True)
    z.add_argument("--events", default="data/events")
    z.add_argument("--results", default="results")
    z.add_argument(
        "--max-push-ms", type=float, default=20.0, help="feed filter: median push interval"
    )
    z.set_defaults(fn=_cmd_analyze)

    fl = sub.add_parser("flows", help="gross add/cancel/fill flows for processed main-sample days")
    fl.add_argument("--exchange", required=True)
    fl.add_argument("--symbol", required=True)
    fl.add_argument("--parquet", default="data/parquet")
    fl.add_argument("--events", default="data/events")
    fl.add_argument("--overwrite", action="store_true")
    fl.add_argument("--workers", type=int, default=1, help="days processed in parallel")
    fl.add_argument("--days", default=None, help="comma-separated subset of days")
    fl.add_argument("--tag", default="flows", help="output file tag (alternative grids)")
    fl.add_argument("--edges", default=None, help="window edges in ms, e.g. 0,20,40,100")
    fl.add_argument(
        "--state-only", action="store_true", help="only write pre-event state covariates"
    )
    fl.add_argument("--max-push-ms", type=float, default=20.0, help="main-sample feed filter")
    fl.set_defaults(fn=_cmd_flows)

    mo = sub.add_parser("model", help="fit the two-phase (transport + source) refill model")
    mo.add_argument("--exchange", required=True)
    mo.add_argument("--symbol", required=True)
    mo.add_argument("--events", default="data/events")
    mo.add_argument("--results", default="results")
    mo.add_argument("--tag", default="flowsfine")
    mo.add_argument("--n-boot", type=int, default=200)
    mo.add_argument("--max-push-ms", type=float, default=20.0, help="main-sample feed filter")
    mo.set_defaults(fn=_cmd_model)

    mv = sub.add_parser("moves", help="exact-size matching test for order repositioning")
    mv.add_argument("--exchange", required=True)
    mv.add_argument("--symbol", required=True)
    mv.add_argument("--parquet", default="data/parquet")
    mv.add_argument("--events", default="data/events")
    mv.add_argument("--results", default="results")
    mv.add_argument("--workers", type=int, default=1)
    mv.add_argument("--overwrite", action="store_true")
    mv.add_argument("--max-push-ms", type=float, default=20.0, help="main-sample feed filter")
    mv.set_defaults(fn=_cmd_moves)

    pd_ = sub.add_parser("pde", help="out-of-sample local vs non-local continuum model fit")
    pd_.add_argument("--exchange", required=True)
    pd_.add_argument("--symbol", required=True)
    pd_.add_argument("--events", default="data/events")
    pd_.add_argument("--results", default="results")
    pd_.add_argument("--folds", type=int, default=5)
    pd_.add_argument("--max-push-ms", type=float, default=20.0, help="main-sample feed filter")
    pd_.set_defaults(fn=_cmd_pde)

    ex = sub.add_parser("execution", help="cost of a follow-up market order after sweeps")
    ex.add_argument("--exchange", required=True)
    ex.add_argument("--symbol", required=True)
    ex.add_argument("--events", default="data/events")
    ex.add_argument("--results", default="results")
    ex.add_argument("--n-boot", type=int, default=200)
    ex.add_argument("--max-push-ms", type=float, default=20.0, help="main-sample feed filter")
    ex.set_defaults(fn=_cmd_execution)

    l3p = sub.add_parser("l3", help="Bitstamp order-level (L3) replication and move test")
    l3p.add_argument("--pair", default="btcusd")
    l3p.add_argument("--raw", default="data/raw/bitstamp_l3")
    l3p.add_argument("--cache", default="data/processed/bitstamp_l3")
    l3p.add_argument("--results", default="results")
    l3p.add_argument("--min-levels", type=int, default=3)
    l3p.add_argument("--min-bps", type=float, default=0.5)
    l3p.add_argument("--near-bps", type=float, default=1.0)
    l3p.add_argument("--n-boot", type=int, default=500)
    l3p.set_defaults(fn=_cmd_l3)

    ro = sub.add_parser("robustness", help="matching comparison and subset robustness table")
    ro.add_argument("--exchange", required=True)
    ro.add_argument("--symbol", required=True)
    ro.add_argument("--events", default="data/events")
    ro.add_argument("--results", default="results")
    ro.add_argument("--tag", default="flowsfine")
    ro.add_argument("--n-boot", type=int, default=100)
    ro.add_argument("--k", type=int, default=5, help="nearest placebo times per sweep")
    ro.add_argument("--max-push-ms", type=float, default=20.0, help="main-sample feed filter")
    ro.set_defaults(fn=_cmd_robustness)
    return ap


def main(argv: list[str] | None = None) -> int:
    a = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if a.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    return int(a.fn(a))


if __name__ == "__main__":
    sys.exit(main())
