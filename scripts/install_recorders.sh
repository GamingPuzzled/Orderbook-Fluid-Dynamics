#!/bin/zsh
# Install (or remove) macOS launchd agents that keep the Bitstamp L3 recorders running.
#
#   scripts/install_recorders.sh install [pair ...]   # default pairs: btcusd ethusd
#   scripts/install_recorders.sh uninstall [pair ...]
#   scripts/install_recorders.sh status
#
# Each agent starts at login, restarts the recorder if it exits (KeepAlive, 30 s throttle) and
# wraps it in `caffeinate -i`, which prevents idle sleep while recording (the Mac can still sleep
# when the lid is closed). Logs: logs/record_bitstamp_<pair>.log
set -eu
ROOT="${0:A:h:h}"
UV="$(command -v uv || echo /opt/homebrew/bin/uv)"
AGENTS="$HOME/Library/LaunchAgents"
ACTION="${1:-status}"
shift || true
if [[ $# -eq 0 ]]; then PAIRS=(btcusd ethusd); else PAIRS=("$@"); fi

label() { echo "com.lobflow.record-bitstamp-$1"; }

install_one() {
  local pair=$1 lbl plist
  lbl=$(label "$pair")
  plist="$AGENTS/$lbl.plist"
  mkdir -p "$AGENTS" "$ROOT/logs"
  # stop a manually started recorder for this pair (two writers would corrupt the gzip files)
  local pidf="$ROOT/logs/record_bitstamp_$pair.pid" pid i
  if [[ -f "$pidf" ]]; then
    pid=$(cat "$pidf")
    # INT then TERM (current recorders close their gzip file on both; a nohup'd process may
    # ignore INT); wait until it is really gone before starting the agent
    kill -INT "$pid" 2>/dev/null || true
    sleep 2
    kill -TERM "$pid" 2>/dev/null || true
    for i in {1..20}; do kill -0 "$pid" 2>/dev/null || break; sleep 0.5; done
    if kill -0 "$pid" 2>/dev/null; then kill -KILL "$pid"; sleep 1; fi
  fi
  cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$lbl</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/caffeinate</string><string>-i</string>
    <string>$UV</string><string>run</string><string>python</string>
    <string>scripts/record_bitstamp.py</string><string>--pair</string><string>$pair</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>30</integer>
  <key>StandardOutPath</key><string>$ROOT/logs/record_bitstamp_$pair.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/record_bitstamp_$pair.log</string>
  <key>EnvironmentVariables</key>
  <dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string></dict>
</dict>
</plist>
EOF
  launchctl bootout "gui/$UID/$lbl" 2>/dev/null || true
  launchctl bootstrap "gui/$UID" "$plist"
  echo "installed $lbl"
}

uninstall_one() {
  local lbl
  lbl=$(label "$1")
  launchctl bootout "gui/$UID/$lbl" 2>/dev/null || true
  rm -f "$AGENTS/$lbl.plist"
  echo "removed $lbl"
}

case "$ACTION" in
  install) for p in "${PAIRS[@]}"; do install_one "$p"; done ;;
  uninstall) for p in "${PAIRS[@]}"; do uninstall_one "$p"; done ;;
  status) launchctl list | grep -E "PID|com.lobflow" || echo "no lobflow agents loaded" ;;
  *) echo "usage: $0 install|uninstall|status [pair ...]"; exit 2 ;;
esac
