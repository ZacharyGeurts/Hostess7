#!/usr/bin/env bash
# Training viewer open is lightweight — default AML_BUILD=0 (full field_vm_boot is separate).
export AML_BUILD="${AML_BUILD:-0}"
# AmmoLang subfolder route — opt-in with AML_BUILD=1
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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:hostess7-training-viewer/launch.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

# Hostess 7 Training Viewer — opens in Queen browser tab.
set -euo pipefail

VIEWER_ROOT="$(cd "$(dirname "$0")" && pwd)"
NEXUS_TREE="$(cd "${VIEWER_ROOT}/.." && pwd)"

export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${NEXUS_TREE}}"
export SG_ROOT="${SG_ROOT:-${NEXUS_INSTALL_ROOT}}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${NEXUS_INSTALL_ROOT}/.nexus-state}"
export HOSTESS7_ROOT="${HOSTESS7_ROOT:-${NEXUS_INSTALL_ROOT}/Hostess7}"
export GROK16_ROOT="${GROK16_ROOT:-${NEXUS_INSTALL_ROOT}/Grok16}"
export G16_PREFIX="${G16_PREFIX:-$GROK16_ROOT}"
export GPY16_ROOT="${GPY16_ROOT:-$GROK16_ROOT/python}"
export PATH="/usr/bin:/bin:${GROK16_ROOT}/bin:${NEXUS_INSTALL_ROOT}/PythonG/bin:${PATH:-}"
export H7_TRAINING_VIEWER_PORT="${H7_TRAINING_VIEWER_PORT:-9488}"
export QUEEN_ROOT="${QUEEN_ROOT:-${NEXUS_INSTALL_ROOT}/Queen}"

PY=python3
OPEN_PY=python3

URL="http://127.0.0.1:${H7_TRAINING_VIEWER_PORT}/"
PROGRAM_ID="${H7_TRAINING_LAUNCH_ID:-hostess7-training-viewer}"
DESKTOP_URL="http://127.0.0.1:${NEXUS_THREAT_PANEL_PORT:-9477}/field?launch=${PROGRAM_ID}"
PID_FILE="${VIEWER_ROOT}/.viewer.pid"
LOG="${VIEWER_ROOT}/viewer.log"
OPENER="${NEXUS_INSTALL_ROOT}/lib/queen-panel-open.py"

/usr/bin/mkdir -p "${NEXUS_STATE_DIR}"

_running() {
  curl -sf --connect-timeout 1 --max-time 2 "${URL}api/health" >/dev/null 2>&1
}

if ! _running; then
  if [[ -f "$PID_FILE" ]]; then
    pid="$(cat "$PID_FILE" 2>/dev/null || true)"
    [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
    rm -f "$PID_FILE"
  fi
  : >"$LOG"
  nohup "$PY" "${VIEWER_ROOT}/serve.py" >>"$LOG" 2>&1 &
  echo $! >"$PID_FILE"
  for _ in $(seq 1 30); do
    if curl -sf --connect-timeout 1 --max-time 2 "${URL}api/health" >/dev/null 2>&1; then
      break
    fi
    sleep 0.2
  done
fi

_open() {
  if [[ -f "$OPENER" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      QUEEN_ROOT="${QUEEN_ROOT}" \
      "$OPEN_PY" "$OPENER" program "${PROGRAM_ID}" >/dev/null 2>&1 || true
    return 0
  fi
  echo "Open AmmoOS desktop: ${DESKTOP_URL}"
}

case "${1:-open}" in
  stop)
    if _running; then
      kill "$(cat "$PID_FILE")" 2>/dev/null || true
      rm -f "$PID_FILE"
      echo "Training viewer stopped."
    else
      echo "Training viewer not running."
    fi
    ;;
  url)
    echo "$URL"
    ;;
  open|start|"")
    _open
    echo "AmmoOS desktop → Training Viewer (${PROGRAM_ID})"
    echo "  desktop: ${DESKTOP_URL}"
    echo "  viewer:  ${URL}"
    ;;
  *)
    echo "Usage: $0 [open|stop|url]" >&2
    exit 1
    ;;
esac
