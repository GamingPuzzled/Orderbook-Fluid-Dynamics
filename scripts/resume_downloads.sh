#!/bin/zsh
# Resume rate-limited Tardis downloads in phases (run from cron; idempotent: finished days skip).
#   resume_downloads.sh bybit    -> SOL, XRP, LINK (Bybit), then analyze each
#   resume_downloads.sh binance  -> Binance futures BTCUSDT, 12 quarterly days, then analyze
#   resume_downloads.sh okx      -> OKX BTC-USDT-SWAP (tick-by-tick book), 12 quarterly days
# After each symbol: fine-grid flows, three-component model, robustness, size matching, PDE fit,
# follow-up execution cost.
# Removes its own crontab line after running so each phase fires once.
set -u
EDGES=0,20,40,60,80,100,140,200,300,450,650,1000

post() {  # post <exchange> <symbol> <max push ms>: fine flows -> model -> robustness
  local P="--max-push-ms $3"
  $UV run lobflow flows --exchange "$1" --symbol "$2" --tag flowsfine --edges $EDGES \
    --workers 1 ${=P} >> "$LOG" 2>&1
  $UV run lobflow model --exchange "$1" --symbol "$2" --n-boot 300 ${=P} > /dev/null 2>> "$LOG"
  $UV run lobflow robustness --exchange "$1" --symbol "$2" ${=P} > /dev/null 2>> "$LOG"
  $UV run lobflow moves --exchange "$1" --symbol "$2" --workers 2 ${=P} > /dev/null 2>> "$LOG"
  $UV run lobflow pde --exchange "$1" --symbol "$2" ${=P} > /dev/null 2>> "$LOG"
  $UV run lobflow execution --exchange "$1" --symbol "$2" ${=P} > /dev/null 2>> "$LOG"
  $UV run lobflow fitmodels --exchange "$1" --symbol "$2" ${=P} > /dev/null 2>> "$LOG"
  $UV run lobflow information --exchange "$1" --symbol "$2" ${=P} > /dev/null 2>> "$LOG"
  $UV run lobflow zonewidth --exchange "$1" --symbol "$2" ${=P} > /dev/null 2>> "$LOG"
  echo "$2 post exit $?" >> "$LOG"
}
PHASE="$1"
ROOT="/Users/joelpulikkan/Orderbook Fluid Dynamics"
UV=/opt/homebrew/bin/uv
cd "$ROOT" || exit 1
LOG="logs/resume_${PHASE}_$(date +%Y%m%d_%H%M).log"
echo "start $(date)" >> "$LOG"

case "$PHASE" in
  bybit)
    for SYM in SOLUSDT XRPUSDT LINKUSDT; do
      $UV run lobflow batch --exchange bybit --symbol $SYM --start 2023-05-01 --end 2026-11-01 \
        --prune-raw --workers 2 >> "$LOG" 2>&1
      $UV run lobflow analyze --exchange bybit --symbol $SYM > /dev/null 2>> "$LOG"
      echo "$SYM exit $?" >> "$LOG"
      post bybit $SYM 20
    done
    ;;
  okx)
    D=2023-11-01,2024-02-01,2024-05-01,2024-08-01,2024-11-01,2025-02-01,2025-05-01,2025-08-01,2025-11-01,2026-02-01,2026-05-01,2026-08-01
    $UV run lobflow batch --exchange okex-swap --symbol BTC-USDT-SWAP --start 2023-11-01 \
      --end 2026-08-01 --days $D --prune-raw --workers 1 >> "$LOG" 2>&1
    # OKX books channel pushes every 100 ms: relax the feed filter as for Binance (52 ms -> 60)
    $UV run lobflow analyze --exchange okex-swap --symbol BTC-USDT-SWAP --max-push-ms 110 \
      > /dev/null 2>> "$LOG"
    echo "okx exit $?" >> "$LOG"
    post okex-swap BTC-USDT-SWAP 110
    ;;
  binance)
    D=2023-11-01,2024-02-01,2024-05-01,2024-08-01,2024-11-01,2025-02-01,2025-05-01,2025-08-01,2025-11-01,2026-02-01,2026-05-01,2026-08-01
    $UV run lobflow batch --exchange binance-futures --symbol BTCUSDT --start 2023-11-01 \
      --end 2026-08-01 --days $D --prune-raw --workers 1 >> "$LOG" 2>&1
    $UV run lobflow analyze --exchange binance-futures --symbol BTCUSDT --max-push-ms 60 \
      > /dev/null 2>> "$LOG"
    echo "binance exit $?" >> "$LOG"
    post binance-futures BTCUSDT 60
    ;;
  *)
    echo "unknown phase $PHASE" >> "$LOG"; exit 2
    ;;
esac

# regenerate paper tables / figures (cross-asset ones pick up every processed symbol)
$UV run python scripts/tables.py >> "$LOG" 2>&1
$UV run python scripts/figures.py >> "$LOG" 2>&1
$UV run python scripts/crossasset.py >> "$LOG" 2>&1
(cd paper && rm -f ../paper_overleaf.zip && zip -qr ../paper_overleaf.zip main.tex references.bib \
  tables figures) >> "$LOG" 2>&1

crontab -l 2>/dev/null | grep -v "resume_downloads.sh\" $PHASE" | crontab -
echo "done $(date)" >> "$LOG"
