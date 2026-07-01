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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/impl/restart-field-stack.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# Restart NewLatest field stack (panel + Queen + Final_Eye).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SG="$(cd "${ROOT}/.." && pwd)"
QUEEN="${QUEEN_ROOT:-${ROOT}/Queen}"
PANEL_PORT="${NEXUS_THREAT_PANEL_PORT:-9477}"
WORLD_PORT="${QUEEN_WORLD_PORT:-9481}"
EYE_PORT="${ZOCR_PORT:-${FINAL_EYE_PORT:-9479}}"

export SG_ROOT="${SG}"
export NEXUS_INSTALL_ROOT="${ROOT}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-field-drive/nexus-field/state}"
export TDIR="${TDIR:-${HOME}/.grok/projects/home-default-Desktop-SG/terminals}"
export NEXUS_FIELD_STANDALONE=1
export NEXUS_ZNETWORK="${NEXUS_ZNETWORK:-1}"
export NEXUS_ZNETWORK_PROMPT=0
export NEXUS_BOOT_IMPL="${NEXUS_BOOT_IMPL:-0}"
export NEXUS_FIELD_LAUNCH_BROWSER="${NEXUS_FIELD_LAUNCH_BROWSER:-1}"
export NEXUS_KEYBOARD_SOVEREIGN=1
export NEXUS_C2_DESKTOP_LAUNCH=0
export NEXUS_BOOT_C2_ONLY=0
export NEXUS_AUTO_LAUNCH_QUEEN_BROWSER=0
export NEXUS_C2_KIOSK=0
export AMMOOS_DESKTOP_URL="http://127.0.0.1:${PANEL_PORT}/field"
export NEXUS_C2_LAUNCH_URL="${AMMOOS_DESKTOP_URL}"
export AMMOOS_SHOW_DESKTOP_ICONS=1
export QUEEN_ROOT="${QUEEN}"
export DISPLAY="${DISPLAY:-:0}"
mkdir -p "$TDIR" "$NEXUS_STATE_DIR"

echo "=== Stopping integrated stack ==="
pkill -f "${QUEEN}/build/rtx/bin/Linux/queen-browser" 2>/dev/null || true
pkill -9 -f 'threat-panel-http\.py' 2>/dev/null || true
pkill -f "${QUEEN}/lib/queen-world.py" 2>/dev/null || true
if command -v fuser >/dev/null 2>&1; then
  fuser -k "${PANEL_PORT}/tcp" "${WORLD_PORT}/tcp" 2>/dev/null || true
fi
sleep 0.6

echo "=== Starting integrated stack (fast: panel + Queen) ==="
echo "  Full stack: bash ${ROOT}/scripts/stack.sh start"
AML_IMPL=1 bash "${ROOT}/scripts/impl/ammoos-direct-start.sh"

if ! curl -sf "http://127.0.0.1:${EYE_PORT}/api/health" >/dev/null 2>&1; then
  echo "=== Starting Final_Eye :${EYE_PORT} ==="
  FINAL_EYE="${FINAL_EYE_ROOT:-${SG}/Final_Eye}"
  if [[ -f "${FINAL_EYE}/start.sh" ]]; then
    ZOCR_PORT="${EYE_PORT}" bash "${FINAL_EYE}/start.sh" --no-open >/dev/null 2>&1 || true
  fi
fi

if [[ "${NEXUS_FIELD_LAUNCH_BROWSER}" == "1" ]]; then
  echo "NEXUS C2 desktop — fullscreen kiosk at /field"
fi

echo ""
echo "URLs:"
echo "  NEXUS C2     http://127.0.0.1:${PANEL_PORT}/field"
echo "  Final_Eye    http://127.0.0.1:${EYE_PORT}/ops"
