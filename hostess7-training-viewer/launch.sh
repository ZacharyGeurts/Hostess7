#!/usr/bin/env bash
# AmmoLang subfolder route — AML_BUILD=1 (default)
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
export PATH="${GROK16_ROOT}/bin:${NEXUS_INSTALL_ROOT}/PythonG/bin:/usr/bin:/bin:${PATH:-}"
export H7_TRAINING_VIEWER_PORT="${H7_TRAINING_VIEWER_PORT:-9488}"
export QUEEN_ROOT="${QUEEN_ROOT:-${NEXUS_INSTALL_ROOT}/Queen}"

PY="${PY:-pythong}"
if ! command -v "$PY" >/dev/null 2>&1; then
  PY=python3
fi

URL="http://127.0.0.1:${H7_TRAINING_VIEWER_PORT}/"
PID_FILE="${VIEWER_ROOT}/.viewer.pid"
LOG="${VIEWER_ROOT}/viewer.log"
OPENER="${NEXUS_INSTALL_ROOT}/lib/queen-panel-open.py"

mkdir -p "${NEXUS_STATE_DIR}"

_running() {
  [[ -f "$PID_FILE" ]] || return 1
  local pid
  pid="$(cat "$PID_FILE" 2>/dev/null)" || return 1
  kill -0 "$pid" 2>/dev/null
}

if ! _running; then
  : >"$LOG"
  nohup "$PY" "${VIEWER_ROOT}/serve.py" >>"$LOG" 2>&1 &
  echo $! >"$PID_FILE"
  for _ in $(seq 1 30); do
    if curl -sf "${URL}api/health" >/dev/null 2>&1; then
      break
    fi
    sleep 0.2
  done
fi

_open() {
  local url="$1"
  if [[ -f "$OPENER" ]]; then
    NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT}" NEXUS_STATE_DIR="${NEXUS_STATE_DIR}" \
      QUEEN_ROOT="${QUEEN_ROOT}" "$PY" "$OPENER" url "$url" && return
  fi
  echo "Open in Queen browser: $url"
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
    _open "$URL"
    echo "Training viewer: $URL"
    ;;
  *)
    echo "Usage: $0 [open|stop|url]" >&2
    exit 1
    ;;
esac
