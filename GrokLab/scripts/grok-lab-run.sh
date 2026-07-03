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

# Hostess 7 runs the lab — share in, no share out
export HOSTESS7_LAB_SOVEREIGN="${HOSTESS7_LAB_SOVEREIGN:-1}"
export HOSTESS7_LAB_EGRESS="${HOSTESS7_LAB_EGRESS:-0}"

log() { printf '[grok-lab] %s\n' "$*"; }

_h7_lab_gate() {
  if [[ "${HOSTESS7_LAB_SOVEREIGN:-1}" == "0" ]]; then
    return 0
  fi
  local py="${GROK_LAB_PY:-python3}"
  local sovereign="${NL}/lib/hostess7-lab-sovereign.py"
  if [[ -f "$sovereign" ]]; then
    if ! "$py" "$sovereign" secure 2>/dev/null | grep -q '"ok": true'; then
      log "Hostess 7 lab gate — securing connection (share in · no share out)…"
      "$py" "$sovereign" connect >/dev/null 2>&1 || true
    fi
  fi
}

case "${1:-battery}" in
  start)
    _h7_lab_gate
    log "Starting Final Eye (headless) — Hostess 7 sovereign…"
    exec "$PY" "$NL/lib/grok-ai-lab.py" start
    ;;
  stop)     log "Stopping Final Eye…"; exec "$PY" "$NL/lib/grok-ai-lab.py" stop ;;
  boot|protect|boot-rekill)
    _h7_lab_gate
    log "Boot protection — Hostess 7 sovereign · RE-KILL at boot…"
    exec "$PY" "$NL/lib/grok-ai-lab.py" boot
    ;;
  revalidate)
    exec "$PY" "$NL/lib/field-attack-kit.py" revalidate-kill-list
    ;;
  arm)
    _h7_lab_gate
    log "Lab arm — Hostess 7 boss (set GROK_LAB_RELEASE_EYE=1 to release vision kills)…"
    exec "$PY" "$NL/lib/grok-ai-lab.py" arm
    ;;
  status)
    _h7_lab_gate
    exec "$PY" "$NL/lib/grok-ai-lab.py" status
    ;;
  live)
    _h7_lab_gate
    log "Live loop — Final Eye + OCR brain + sanctuary (share in only)…"
    exec "$PY" "$NL/lib/grok-ai-lab.py" live "${2:-3}"
    ;;
  protect|battery|test)
    _h7_lab_gate
    log "=== Grok AI Lab protection battery — Hostess 7 sovereign ==="
    log "home=127.0.0.1 share_in=1 share_out=0 boss=hostess7"
    exec "$PY" "$NL/lib/grok-ai-lab.py" battery
    ;;
  *)
    echo "usage: grok-lab-run.sh [start|stop|arm|status|battery|live [loops]]" >&2
    exit 1
    ;;
esac