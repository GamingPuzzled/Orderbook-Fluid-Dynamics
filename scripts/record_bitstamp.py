"""Record Bitstamp's public order-level (L3) feed: every order create / change / delete with
order IDs, plus trades. Free, no account. Used to test directly whether post-sweep refill
moves the *same* orders (the level-2 data cannot show this).

Output: data/raw/bitstamp_l3/<pair>/<YYYY-MM-DD>/<HH>.jsonl.gz, one JSON object per line:
    {"recv_us": <local receive time, µs>, "msg": <raw websocket message>}
plus a REST order-book snapshot (with order IDs) at every (re)connect and every 15 minutes:
    .../snapshot_<recv_us>.json.gz

Usage (runs until stopped; reconnects with backoff):
    uv run python scripts/record_bitstamp.py --pair btcusd
Stop: kill the process (PID in logs/record_bitstamp_<pair>.pid).
"""

from __future__ import annotations

import argparse
import asyncio
import gzip
import json
import logging
import os
import signal
import time
import urllib.request
from pathlib import Path
from typing import IO

import websockets

WS_URL = "wss://ws.bitstamp.net"
BOOK_URL = "https://www.bitstamp.net/api/v2/order_book/{pair}/?group=2"  # group=2: order IDs
USER_AGENT = "lobflow-research-recorder/0.1"
log = logging.getLogger("record_bitstamp")


class HourlyWriter:
    """Append lines to an hourly-rotated gzip file."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.key = ""
        self.fh: IO[str] | None = None

    def write(self, line: str, now: float) -> None:
        key = time.strftime("%Y-%m-%d/%H", time.gmtime(now))
        if key != self.key:
            self.close()
            path = self.root / f"{key}.jsonl.gz"
            path.parent.mkdir(parents=True, exist_ok=True)
            self.fh = gzip.open(path, "at", encoding="utf-8")  # noqa: SIM115 (kept open)
            self.key = key
        assert self.fh is not None
        self.fh.write(line + "\n")

    def close(self) -> None:
        if self.fh is not None:
            self.fh.close()
            self.fh = None
        self.key = ""  # force reopen on next write (same hour after a reconnect)


def snapshot(pair: str, root: Path) -> None:
    """Save the REST order book (with order IDs) so the L3 stream can be replayed."""
    recv_us = time.time_ns() // 1000
    req = urllib.request.Request(BOOK_URL.format(pair=pair), headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310 (fixed https URL)
        body = r.read()
    day = time.strftime("%Y-%m-%d", time.gmtime(recv_us / 1e6))
    path = root / day / f"snapshot_{recv_us}.json.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb") as fh:
        fh.write(body)
    log.info("snapshot saved: %s (%d bytes)", path.name, len(body))


SNAPSHOT_EVERY_S = 900.0  # periodic resync points for replay after feed gaps


async def periodic_snapshots(pair: str, root: Path) -> None:
    """Save a REST snapshot every ``SNAPSHOT_EVERY_S`` while connected (errors are logged)."""
    while True:
        await asyncio.sleep(SNAPSHOT_EVERY_S)
        try:
            await asyncio.to_thread(snapshot, pair, root)
        except OSError as exc:
            log.warning("periodic snapshot failed: %s", exc)


async def consume(ws: websockets.ClientConnection, writer: HourlyWriter) -> None:
    """Write every message with its local receive time until the server asks to reconnect."""
    n = 0
    async for msg in ws:
        now = time.time()
        writer.write(json.dumps({"recv_us": int(now * 1e6), "msg": json.loads(msg)}), now)
        n += 1
        if n % 100_000 == 0:
            log.info("%d messages", n)
        if '"bts:request_reconnect"' in str(msg):
            log.info("server requested reconnect")
            return


async def record(pair: str, root: Path) -> None:
    # SIGTERM (launchd stop, kill) cancels this task so the gzip file is closed cleanly
    task = asyncio.current_task()
    if task is not None:
        asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    writer = HourlyWriter(root)
    backoff = 1.0
    channels = [f"live_orders_{pair}", f"live_trades_{pair}"]
    try:
        while True:
            try:
                async with websockets.connect(
                    WS_URL, open_timeout=15, ping_interval=20, max_size=2**22
                ) as ws:
                    for ch in channels:
                        await ws.send(
                            json.dumps({"event": "bts:subscribe", "data": {"channel": ch}})
                        )
                    # snapshot after subscribing, so no gap between book and stream
                    await asyncio.to_thread(snapshot, pair, root)
                    backoff = 1.0
                    resync = asyncio.create_task(periodic_snapshots(pair, root))
                    try:
                        await consume(ws, writer)
                    finally:
                        resync.cancel()
            except (OSError, websockets.WebSocketException, TimeoutError) as exc:
                log.warning("connection lost: %s; retry in %.0f s", exc, backoff)
                writer.close()
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 300.0)
    finally:
        writer.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="btcusd")
    ap.add_argument("--out", default="data/raw/bitstamp_l3")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Path("logs").mkdir(exist_ok=True)
    Path(f"logs/record_bitstamp_{a.pair}.pid").write_text(str(os.getpid()))
    try:
        asyncio.run(record(a.pair, Path(a.out) / a.pair))
    except (KeyboardInterrupt, asyncio.CancelledError):
        log.info("stopped")


if __name__ == "__main__":
    main()
