#!/usr/bin/env bash
# Hostess7 embed installer — user service + boot + optional daemon
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
START_ONLY=0
SKIP_DAEMON=0

for arg in "$@"; do
  case "$arg" in
    --start-only) START_ONLY=1 ;;
    --no-daemon) SKIP_DAEMON=1 ;;
  esac
done

export HOSTESS7_ROOT="$ROOT"
export HOSTESS7_BRAIN_STATE="${HOSTESS7_BRAIN_STATE:-$ROOT/brain/state}"
export NEXUS_STATE_DIR="$HOSTESS7_BRAIN_STATE"
mkdir -p "$HOSTESS7_BRAIN_STATE/snapshots"

PY="${PYTHONG:-pythong}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python3
fi

echo "=== Hostess7 embed install (1.0.7h) ==="
echo "  root:  $ROOT"
echo "  state: $HOSTESS7_BRAIN_STATE"

"$PY" -m pip install -q -e "$ROOT" 2>/dev/null \
  || "$PY" -m pip install -q --user -e "$ROOT" 2>/dev/null \
  || "$PY" -m pip install -q --break-system-packages -e "$ROOT"

if [[ "$START_ONLY" -eq 0 ]]; then
  UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  mkdir -p "$UNIT_DIR"
  sed "s|%h/Hostess7|$ROOT|g; s|%i|$USER|g" "$ROOT/deploy/hostess7.service" >"$UNIT_DIR/hostess7.service"
  systemctl --user daemon-reload 2>/dev/null || true
  systemctl --user enable hostess7.service 2>/dev/null || true
  echo "  systemd: $UNIT_DIR/hostess7.service"
fi

bash "$ROOT/Hostess7.sh" boot --no-stack-learn 2>/dev/null \
  || bash "$ROOT/Hostess7.sh" boot \
  || true

if [[ "$SKIP_DAEMON" -eq 0 ]]; then
  LOG="$HOSTESS7_BRAIN_STATE/hostess7-daemon.log"
  PIDF="$HOSTESS7_BRAIN_STATE/hostess7-daemon.pid"
  if [[ -f "$PIDF" ]] && kill -0 "$(cat "$PIDF")" 2>/dev/null; then
    echo "  daemon: already running pid $(cat "$PIDF")"
  else
    nohup env PYTHONPATH="$ROOT/src" "$PY" -m hostess7.daemon >>"$LOG" 2>&1 &
    echo $! >"$PIDF"
    echo "  daemon: started pid $(cat "$PIDF")"
  fi
fi

PORT="${HOSTESS7_WEB_PORT:-8080}"
echo "=== Hostess7 embed ready → http://127.0.0.1:${PORT}/ ==="
echo "  core:   hostess7-core status"
echo "  brain:  curl -s http://127.0.0.1:${PORT}/api/brain | head"