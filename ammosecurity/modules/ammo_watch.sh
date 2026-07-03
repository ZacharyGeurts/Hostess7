#!/usr/bin/env bash
# ammo_watch — 30s re-enforcement + drift detection (stealth heartbeat)
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/../lib/common.sh"

M="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INTERVAL="${AMMO_WATCH_INTERVAL:-30}"
PID_FILE="${AMMO_STATE_DIR}/ammo_watch.pid"
WATCH_LOG="${AMMO_STATE_DIR}/watch.log"

_watch_once() {
  local drift=0
  bash "$M/sg_net_harden.sh" drift || drift=1
  bash "$M/sg_service_cleaner.sh" drift || drift=1
  if [[ -f /var/lib/ammo/ingress-clasp.lock ]] || [[ -f "${AMMO_STATE_DIR}/ingress-clasp.lock" ]]; then
    bash "$M/sg_ingress_clasp.sh" status >/dev/null 2>&1 || true
  fi
  if [[ "$drift" -eq 1 ]]; then
    ammo_log 'drift detected — re-applying mandatory baseline'
    bash "$M/sg_net_harden.sh" apply 2>/dev/null || true
    bash "$M/sg_service_cleaner.sh" 2>/dev/null || true
    ammo_violation 'watch re-applied mandatory baseline after drift'
  else
    ammo_health_note 'watch tick ok'
  fi
  return 0
}

cmd_start() {
  ammo_ensure_state
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    ammo_log "ammo_watch already running pid $(cat "$PID_FILE")"
    return 0
  fi
  (
    trap 'rm -f "$PID_FILE"; exit 0' INT TERM
    echo $$ >"$PID_FILE"
    while true; do
      _watch_once >>"$WATCH_LOG" 2>&1 || true
      sleep "$INTERVAL"
    done
  ) &
  disown 2>/dev/null || true
  sleep 0.2
  ammo_log "ammo_watch started (interval ${INTERVAL}s) pid $(cat "$PID_FILE" 2>/dev/null || echo '?')"
}

cmd_stop() {
  if [[ -f "$PID_FILE" ]]; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    rm -f "$PID_FILE"
    ammo_log 'ammo_watch stopped'
  else
    ammo_log 'ammo_watch not running'
  fi
}

cmd_status() {
  ammo_log '=== ammo_watch status ==='
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "running pid $(cat "$PID_FILE") interval ${INTERVAL}s"
  else
    echo 'not running'
  fi
  [[ -f "$WATCH_LOG" ]] && tail -5 "$WATCH_LOG" 2>/dev/null || true
  [[ -f "$AMMO_VIOLATIONS_LOG" ]] && echo "--- violations (tail) ---" && tail -3 "$AMMO_VIOLATIONS_LOG" 2>/dev/null || true
}

cmd_once() {
  ammo_ensure_state
  _watch_once
}

main() {
  case "${1:-status}" in
    start) cmd_start ;;
    stop) cmd_stop ;;
    once|tick) cmd_once ;;
    status) cmd_status ;;
    *) cmd_status ;;
  esac
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi