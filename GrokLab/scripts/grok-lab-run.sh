# AmmoLang boundary route — AML_BUILD=1 universal boundary
_aml_find_root() {
  local d="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  while [[ "$d" != "/" ]]; do
    [[ -f "$d/lib/ammolang-run.sh" ]] && echo "$d" && return 0
    d="$(dirname "$d")"
  done
  return 1
}
if [[ "${AML_BUILD:-1}" != "0" ]] && [[ -z "${AML_BOUNDARY_ACTIVE:-}" ]]; then
  _AML_ROOT="$(_aml_find_root 2>/dev/null || true)"
  if [[ -n "$_AML_ROOT" ]]; then
    export AML_BOUNDARY_ACTIVE=1
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:GrokLab/scripts/grok-lab-run.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Grok AI Lab — Final Eye live + KILROY protection battery. Forever war with terror; resolute.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NL="${NEXUS_INSTALL_ROOT:-$(cd "$ROOT/.." && pwd)}"
export NEXUS_INSTALL_ROOT="$NL"
export KILROY_ROOT="${KILROY_ROOT:-$NL/KILROY}"
export GROK_LAB_ROOT="$ROOT"
export GROK_LAB_STATE="${GROK_LAB_STATE:-$ROOT/.lab-state}"
export FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-$NL/Final_Eye}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$NL/.nexus-state}"
PY="${GROK_LAB_PY:-python3}"
export GROK_LAB_PY="$PY"

mkdir -p "$GROK_LAB_STATE"

log() { printf '[grok-lab] %s\n' "$*"; }

case "${1:-battery}" in
  start)    log "Starting Final Eye (headless)…"; exec "$PY" "$NL/lib/grok-ai-lab.py" start ;;
  stop)     log "Stopping Final Eye…"; exec "$PY" "$NL/lib/grok-ai-lab.py" stop ;;
  boot|protect|boot-rekill)
    log "Boot protection — revalidate kill list + RE-KILL at boot…"
    exec "$PY" "$NL/lib/grok-ai-lab.py" boot
    ;;
  revalidate)
    exec "$PY" "$NL/lib/field-attack-kit.py" revalidate-kill-list
    ;;
  arm)      log "Lab arm — boot protection (set GROK_LAB_RELEASE_EYE=1 to release vision kills)…"; exec "$PY" "$NL/lib/grok-ai-lab.py" arm ;;
  status)   exec "$PY" "$NL/lib/grok-ai-lab.py" status ;;
  live)     log "Live loop — Final Eye + OCR brain + sanctuary…"; exec "$PY" "$NL/lib/grok-ai-lab.py" live "${2:-3}" ;;
  protect|battery|test)
    log "=== Grok AI Lab protection battery ==="
    log "home=127.0.0.1 perimeter=the_world coexist=1 kill_evil=1 new_internet=every_home"
    exec "$PY" "$NL/lib/grok-ai-lab.py" battery
    ;;
  *)
    echo "usage: grok-lab-run.sh [start|stop|arm|status|battery|live [loops]]" >&2
    exit 1
    ;;
esac