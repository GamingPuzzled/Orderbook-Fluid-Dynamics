"""Download Tardis.dev free sample datasets (first day of each month, no API key).

Files are gzip CSVs served from ``https://datasets.tardis.dev/v1/{exchange}/{data_type}/
{YYYY}/{MM}/{DD}/{SYMBOL}.csv.gz``. Only day 1 of each month is available without a key.
"""

from __future__ import annotations

import logging
import shutil
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

log = logging.getLogger(__name__)

BASE_URL = "https://datasets.tardis.dev/v1"
DATA_TYPES = ("incremental_book_L2", "trades", "liquidations")
USER_AGENT = "lobflow-research/0.1"
RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
MAX_WAIT_S = 600.0


def _retry_wait(retry_after: str | None, attempt: int, backoff_s: float) -> float:
    """Seconds to wait before the next attempt."""
    if retry_after is not None:
        try:
            return min(max(float(retry_after), 1.0), MAX_WAIT_S)
        except ValueError:
            pass
    return float(min(backoff_s * 2.0**attempt, MAX_WAIT_S))


class TardisError(RuntimeError):
    """Raised when a Tardis dataset cannot be fetched."""


@dataclass(frozen=True)
class DatasetSpec:
    """One Tardis daily file."""

    exchange: str
    data_type: str
    day: date
    symbol: str

    def __post_init__(self) -> None:
        if self.day.day != 1:
            raise ValueError(f"free Tardis samples are first-of-month only, got {self.day}")
        if self.data_type not in DATA_TYPES:
            raise ValueError(f"unknown data_type {self.data_type!r}; expected one of {DATA_TYPES}")

    @property
    def url(self) -> str:
        d = self.day
        return (
            f"{BASE_URL}/{self.exchange}/{self.data_type}/"
            f"{d.year:04d}/{d.month:02d}/{d.day:02d}/{self.symbol}.csv.gz"
        )

    def local_path(self, root: Path) -> Path:
        return (
            root / self.exchange / self.data_type / self.symbol / f"{self.day.isoformat()}.csv.gz"
        )


def first_days(start: date, end: date) -> list[date]:
    """All first-of-month dates in [start, end]."""
    out: list[date] = []
    y, m = start.year, start.month
    if start.day != 1:
        m += 1
        if m == 13:
            y, m = y + 1, 1
    while date(y, m, 1) <= end:
        out.append(date(y, m, 1))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def download(
    spec: DatasetSpec,
    root: Path,
    *,
    overwrite: bool = False,
    timeout: float = 120.0,
    max_retries: int = 6,
    backoff_s: float = 30.0,
) -> Path:
    """Download one dataset to ``root``; skip if present. Writes atomically via a .part file.

    Rate limits (HTTP 429) and transient server/network errors are retried with exponential
    backoff (``backoff_s · 2^attempt``, capped at 10 min), honouring ``Retry-After``.
    """
    dest = spec.local_path(root)
    if dest.exists() and not overwrite:
        log.info("skip (exists) %s", dest)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(max_retries + 1):
        req = urllib.request.Request(spec.url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp, tmp.open("wb") as fh:
                shutil.copyfileobj(resp, fh, length=1 << 20)
            break
        except urllib.error.HTTPError as exc:
            tmp.unlink(missing_ok=True)
            if exc.code in RETRY_STATUS and attempt < max_retries:
                wait = _retry_wait(exc.headers.get("Retry-After"), attempt, backoff_s)
                log.warning("HTTP %d for %s; retry in %.0f s", exc.code, spec.url, wait)
                time.sleep(wait)
                continue
            raise TardisError(f"HTTP {exc.code} for {spec.url}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            tmp.unlink(missing_ok=True)
            if attempt < max_retries:
                wait = _retry_wait(None, attempt, backoff_s)
                log.warning("network error for %s (%s); retry in %.0f s", spec.url, exc, wait)
                time.sleep(wait)
                continue
            raise TardisError(f"network error for {spec.url}: {exc}") from exc
    tmp.replace(dest)
    log.info("downloaded %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
    return dest
