#!/usr/bin/env bash
# Cool operation — lower CPU/bandwidth while keeping local war stack alive.
set -euo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-$ROOT}"
export NEXUS_STATE_DIR="$STATE"
export SG_ROOT="${SG_ROOT:-$(cd "$ROOT/.." && pwd)}"

MODE="${1:-on}"
COOL_FLAG="$STATE/cool-operation.json"
COOL_ENV="$STATE/cool-operation.env"

log() { printf '[cool-op] %s\n' "$*"; }

_write_flag() {
  /usr/bin/mkdir -p "$STATE"
  printf '%s\n' "NEXUS_COOL_OPERATION=1" >"$COOL_ENV"
  printf '%s\n' "NEXUS_AWAIT_SIMPLE=1" >>"$COOL_ENV"
  printf '%s\n' "NEXUS_FIELD_THERMAL_TIGHTEN=0.6" >>"$COOL_ENV"
  printf '%s\n' "NEXUS_H7_IDLE_INTERVAL=900" >>"$COOL_ENV"
  printf '%s\n' "HOSTESS7_LOW_POWER=1" >>"$COOL_ENV"
  printf '%s\n' "GROK_LAB_RSYNC_BWLIMIT=8000" >>"$COOL_ENV"
  python3 -c "
import json, datetime
from pathlib import Path
p = Path('$COOL_FLAG')
p.write_text(json.dumps({
  'schema': 'cool-operation/v1',
  'active': True,
  'updated': datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'note': 'Reduced CPU/bandwidth — local stack stays up',
}, indent=2) + '\n')
"
}

_cool_on() {
  log "engaging cool operation"
  _write_flag

  # Stop background brain burners
  if [[ -f "$ROOT/lib/hostess7-idle-grow.py" ]]; then
    python3 "$ROOT/lib/hostess7-idle-grow.py" stop 2>/dev/null || true
  fi
  if [[ -f "$ROOT/Hostess7/Hostess7.sh" ]]; then
    AML_BUILD=0 HOSTESS7_LOW_POWER=1 bash "$ROOT/Hostess7/Hostess7.sh" off 2>/dev/null || true
  fi

  # Kill stuck Grok16 tool wrappers (awk/cp/mkdir spin when Grok16 precedes /usr/bin on PATH)
  for pat in 'Grok16/bin/g16-awk' 'Grok16/bin/awk' 'Grok16/bin/g16-cp' 'Grok16/bin/cp' \
             'Grok16/bin/g16-mkdir' 'Grok16/bin/mkdir' 'Grok16/bin/g16-rm' 'Grok16/bin/rm'; do
    while IFS= read -r pid; do
      [[ -n "$pid" && "$pid" != "$$" ]] && kill -9 "$pid" 2>/dev/null || true
    done < <(pgrep -f "$pat" 2>/dev/null || true)
  done
  # Pause bandwidth-heavy VM deploy/rsync while cool
  for pat in 'world-node-deploy-remaining' 'world-node-quick-deploy' 'world-node-hostess7-deploy'; do
    while IFS= read -r pid; do
      [[ -n "$pid" && "$pid" != "$$" ]] && kill -TERM "$pid" 2>/dev/null || true
    done < <(pgrep -f "$pat" 2>/dev/null || true)
  done
  # Restart single panel-tray watchdog (patched loop uses sleep, not recursive inotify)
  if [[ -f "$ROOT/lib/panel-tray.sh" ]]; then
    # shellcheck source=/dev/null
    source "$ROOT/lib/nexus-common.sh" 2>/dev/null || true
    # shellcheck source=/dev/null
    source "$ROOT/lib/panel-tray.sh" 2>/dev/null || true
    nexus_panel_tray_stop 2>/dev/null || true
    nexus_panel_tray_watchdog_start 2>/dev/null || true
  fi

  # Suspend idle QEMU VMs (keep operational pair 2222/2223)
  if [[ -f "$ROOT/GrokLab/deploy/qemu-world-cool.sh" ]]; then
    bash "$ROOT/GrokLab/deploy/qemu-world-cool.sh" suspend-idle 2>/dev/null || true
  fi

  # Thermal tighten
  if [[ -f "$ROOT/lib/field-thermal-guard.py" ]]; then
    NEXUS_COOL_OPERATION=1 python3 "$ROOT/lib/field-thermal-guard.py" gatekeeper 2>/dev/null || true
  fi

  log "cool operation ON — local :9477/:9481/:8080 unchanged"
  log "flag: $COOL_FLAG"
}

_cool_off() {
  log "disengaging cool operation"
  rm -f "$COOL_FLAG" "$COOL_ENV" 2>/dev/null || true
  if [[ -f "$ROOT/GrokLab/deploy/qemu-world-cool.sh" ]]; then
    bash "$ROOT/GrokLab/deploy/qemu-world-cool.sh" resume-all 2>/dev/null || true
  fi
  log "cool operation OFF"
}

_cool_status() {
  if [[ -f "$COOL_FLAG" ]]; then
    cat "$COOL_FLAG"
  else
    echo '{"active":false}'
  fi
  echo "--- processes ---"
  pgrep -af 'hostess7-idle-grow|field_agents7.py daemon|qemu-system-x86' 2>/dev/null | head -12 || true
}

case "$MODE" in
  on|engage|cool) _cool_on ;;
  off|resume|warm) _cool_off ;;
  status|json) _cool_status ;;
  *)
    echo "usage: $0 [on|off|status]" >&2
    exit 1
    ;;
esac