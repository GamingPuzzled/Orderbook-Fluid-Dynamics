# lobflow — spatial refill of swept order books

Research pipeline for studying how crypto perpetual order books refill after aggressive multi-level sweeps. See [`docs/research_design.md`](docs/research_design.md) and [`docs/literature_review.md`](docs/literature_review.md).

## Setup

```bash
uv sync
```

## Pipeline

```bash
# 1. Download Tardis.dev free first-of-month samples (no API key)
uv run lobflow download --exchange bybit --symbol BTCUSDT --start 2026-01-01 --end 2026-10-01

# 2. csv.gz -> typed Parquet (streaming)
uv run lobflow convert

# 3. Detect isolated sweeps and build the event panel for one day
uv run lobflow events --exchange bybit --symbol BTCUSDT --day 2026-10-01
```

Outputs in `data/events/{exchange}/{symbol}/`:
- `{day}_events.parquet`: one row per sweep (side, gap length, pre-shock mid/spread, cleared fraction, staleness).
- `{day}_panel.parquet`: depth of the swept side (`depth`) and the opposite side (`depth_opp`) on a fixed tick grid around the gap, at τ ∈ {20, 40, 60, 100, 250, 500, 1000} ms (`tau_ms = -1` is pre-shock).

## Modules

| Module | Purpose |
|---|---|
| `tardis.py` | Free-sample downloader (atomic writes, skip existing) |
| `convert.py` | Streaming CSV→Parquet, tick-size inference |
| `book.py` | L2 replay with snapshot resets; top-N state at query times |
| `sweeps.py` | Aggressor-run sweep detection, size and isolation filters |
| `events.py` | Event panel on exchange clock; clearing confirmation |

## Checks

```bash
uv run pytest && uv run ruff check src tests && uv run mypy src
```
