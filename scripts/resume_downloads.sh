#!/bin/zsh
# Resume rate-limited Tardis downloads in phases (run from cron; idempotent: finished days skip).
#   resume_downloads.sh bybit    -> SOL, XRP, LINK (Bybit), then analyze each
#   resume_downloads.sh binance  -> Binance futures BTCUSDT, 12 quarterly days, then analyze
# Removes its own crontab line after running so each phase fires once.
set -u
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
    done
    ;;
  binance)
    D=2023-11-01,2024-02-01,2024-05-01,2024-08-01,2024-11-01,2025-02-01,2025-05-01,2025-08-01,2025-11-01,2026-02-01,2026-05-01,2026-08-01
    $UV run lobflow batch --exchange binance-futures --symbol BTCUSDT --start 2023-11-01 \
      --end 2026-08-01 --days $D --prune-raw --workers 1 >> "$LOG" 2>&1
    $UV run lobflow analyze --exchange binance-futures --symbol BTCUSDT --max-push-ms 30 \
      > /dev/null 2>> "$LOG"
    echo "binance exit $?" >> "$LOG"
    ;;
  *)
    echo "unknown phase $PHASE" >> "$LOG"; exit 2
    ;;
esac

crontab -l 2>/dev/null | grep -v "resume_downloads.sh\" $PHASE" | crontab -
echo "done $(date)" >> "$LOG"
