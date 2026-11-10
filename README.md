# lobflow — how crypto order books refill after liquidity sweeps

Code for the paper *Pulled, moved, then made: how crypto order books refill after liquidity
sweeps* (Joel Pulikkan, draft in [`paper/main.tex`](paper/main.tex)).

After an aggressive order sweeps several price levels, the swept side of the book refills in
three ordered phases: **withdrawal** (deep orders cancelled, ~50–110 ms), **repositioning**
(depth cancelled deep is posted near the new best quote, ~130–360 ms) and **new liquidity**
(additions exceed cancellations, ~0.4–0.5 s). Local diffusion adds no out-of-sample predictive
power for the depth profile.

Design notes and running log of results: [`docs/research_design.md`](docs/research_design.md);
literature review: [`docs/literature_review.md`](docs/literature_review.md).

## Data

- **Bybit / Binance / OKX perpetuals (level 2):** Tardis.dev publishes the first day of every
  month free of charge, with no API key. Raw files are *not* redistributed here; the pipeline
  downloads them. Tardis rate-limits free downloads (HTTP 429 with `retry-after`), so large
  batches are resumed in phases (`scripts/resume_downloads.sh`).
- **Bitstamp BTC/USD, ETH/USD (order level):** recorded live from Bitstamp's public websocket
  (`live_orders_*`, `live_trades_*`) plus REST snapshots with order IDs, by
  `scripts/record_bitstamp.py`. No account is needed.

Everything under `data/` and `logs/` is git-ignored. `results/` holds the derived tables the
paper uses.

## Setup

```bash
uv sync                      # Python ≥ 3.12; installs the `lobflow` CLI
uv run lobflow --help
```

## Reproducing the paper

Per symbol (main sample: Bybit `BTCUSDT`, `ETHUSDT`, free days 2023-05-01 onward with the 20 ms /
50-level feed):

```bash
EX=bybit; SYM=BTCUSDT
EDGES=0,20,40,60,80,100,140,200,300,450,650,1000
uv run lobflow batch --exchange $EX --symbol $SYM --start 2023-05-01 --end 2026-11-01 --workers 2
uv run lobflow analyze    --exchange $EX --symbol $SYM          # recovery, κ, sample table
uv run lobflow flows      --exchange $EX --symbol $SYM --tag flowsfine --edges $EDGES
uv run lobflow model      --exchange $EX --symbol $SYM --n-boot 300   # three phases
uv run lobflow robustness --exchange $EX --symbol $SYM          # NN matching, subsets
uv run lobflow moves      --exchange $EX --symbol $SYM          # exact-size matching (L2)
uv run lobflow pde        --exchange $EX --symbol $SYM          # local vs non-local fits
uv run lobflow execution  --exchange $EX --symbol $SYM          # follow-up order cost
```

Bitstamp order-level replication (frozen sample used in the paper):

```bash
uv run lobflow l3 --pair btcusd --n-boot 300 --until 2026-11-10T16:00
```

Paper tables and figures (written to `paper/tables/`, `figures/` and `paper/figures/`):

```bash
uv run python scripts/tables.py       # Tables: robustness, execution
uv run python scripts/figures.py      # Figures 1, 2, 3, 5
uv run python scripts/crossasset.py   # Table: cross-asset summary; Figure 4 (all processed symbols)
```

| Paper item | Source file | Produced by |
|---|---|---|
| Sample table | `results/<ex>/<sym>/summary.md` | `analyze` |
| Recovery heatmap (Fig. 3) | `bucket_recovery.parquet` | `analyze` → `figures.py` |
| κ table, mass-balance figure (Fig. 2) | `transport_test_matched.parquet` | `analyze` → `figures.py` |
| Three-phase table, Fig. 1 | `model_summary_*.parquet`, `model_windows_*.parquet` | `model` → `figures.py` |
| Same-order test (L2) | `moves.md` | `moves` |
| Bitstamp results | `results/bitstamp/btcusd/l3.md` | `l3` |
| Execution table, Fig. 5 | `execution.parquet` | `execution` → `tables.py`, `figures.py` |
| PDE table | `pde.md` (copied into `main.tex` by hand) | `pde` |
| Robustness table | `robustness.parquet` | `robustness` → `tables.py` |
| Cross-asset table / Fig. 4 | all of the above | `crossasset.py` |

Bootstrap seeds are fixed, so reruns on the same days reproduce the numbers exactly.

## Recording the Bitstamp feed

```bash
zsh scripts/install_recorders.sh install      # launchd agents for btcusd + ethusd (macOS)
zsh scripts/install_recorders.sh status
zsh scripts/install_recorders.sh uninstall
```

Agents start at login, restart on exit, and keep the Mac from idle-sleeping while recording
(`caffeinate -i`). Output: `data/raw/bitstamp_l3/<pair>/<YYYY-MM-DD>/<HH>.jsonl.gz` (~300 MB/day
for BTC/USD), plus a REST snapshot at each connect and every 15 minutes.

## Modules (`src/lobflow/`)

| Module | Purpose |
|---|---|
| `tardis.py` | Free-sample downloader (atomic writes, skip existing) |
| `convert.py` | Streaming CSV → Parquet, tick-size inference |
| `book.py` | Level-2 replay with snapshot resets (numba) |
| `sweeps.py` | Aggressor runs, sweep detection, size and isolation filters |
| `events.py` | Event panel on the exchange clock; clearing confirmation |
| `profiles.py` | Moving-frame depth profiles; placebo times |
| `flows.py` | Gross-flow decomposition (add / cancel / fill / window edges) |
| `state.py` | State covariates; CEM and nearest-neighbour placebo weights |
| `pipeline.py` | Per-day processing (events, profiles, flows, state, moves) |
| `analysis.py` | Recovery, κ, transport tests, summary tables |
| `model.py` | Three-component decomposition (withdrawal / repositioning / source) |
| `robustness.py` | Matching comparison and subset robustness |
| `moves.py` | Exact-size matching of near-touch adds to deeper cancels (L2) |
| `pde.py` | Out-of-sample local vs non-local continuum model fits |
| `execution.py` | Cost of a follow-up market order after sweeps |
| `l3.py` | Bitstamp order-level replay, sweeps, flows and move tests |
| `cli.py` | `lobflow` command-line interface |

## Checks

```bash
uv run pytest && uv run ruff check src tests scripts && uv run mypy src
```

## Licence

Not yet chosen.
