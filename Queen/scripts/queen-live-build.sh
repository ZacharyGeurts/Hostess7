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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/queen-live-build.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Queen live build — g16 compile watcher + full field build with tri-sense hangup poll.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/../.." && pwd)"
export SG_ROOT="${SG_ROOT:-${SG}}"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${ROOT}}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export QUEEN_ROOT="${ROOT}"
export GROK16_ROOT="${GROK16_ROOT:-${SG}/Grok16}"
export G16_PREFIX="${G16_PREFIX:-${GROK16_ROOT}}"
export ZOCR_ROOT="${ZOCR_ROOT:-${SG}/ZOCR}"
export FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-${SG}/Final_Eye}"
export FINAL_EAR_ROOT="${FINAL_EAR_ROOT:-${SG}/Final_Ear}"
export QUEEN_WATCH_INTERVAL="${QUEEN_WATCH_INTERVAL:-10}"
export QUEEN_WATCH_OCR="${QUEEN_WATCH_OCR:-1}"
export QUEEN_FULL_FIELD="${QUEEN_FULL_FIELD:-0}"
export G16_RELEASE_PROFILE="${G16_RELEASE_PROFILE:-1}"
export G16_FIELD_SPEED="${G16_FIELD_SPEED:-1}"
export PATH="${GROK16_ROOT}/bin:${SG}/PythonG/bin:${ROOT}/bin:${PATH}"

WATCH_SRC="${ROOT}/tools/queen-live-watch.c"
WATCH_BIN="${ROOT}/bin/queen-live-watch"
LOG="${ROOT}/.queen-forge.log"
DASH="file://${ROOT}/gui/queen-live-build.html"

mkdir -p "${ROOT}/bin" "${ROOT}/data"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Queen Live Build — g16 + Ninja + hangup watch               ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo "  Queen:     ${ROOT}"
echo "  g16:       $(command -v g16 2>/dev/null || echo missing)"
echo "  g++16:     $(command -v g++16 2>/dev/null || echo missing)"
echo "  Log:       ${LOG}"
echo "  Dashboard: ${DASH}"
echo ""

if [[ -f "${WATCH_SRC}" ]]; then
  need_compile=1
  if [[ -x "${WATCH_BIN}" && "${WATCH_BIN}" -nt "${WATCH_SRC}" ]]; then
    need_compile=0
  fi
  if [[ "${need_compile}" -eq 1 ]]; then
    echo "=== field-compile queen-live-watch (g16) ==="
    g16 -O2 -pipe -Wall -Wextra -o "${WATCH_BIN}" "${WATCH_SRC}"
    echo "  → ${WATCH_BIN}"
  fi
fi

WATCH_PID=""
cleanup() {
  [[ -n "${WATCH_PID}" ]] && kill "${WATCH_PID}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

if [[ -x "${WATCH_BIN}" ]]; then
  echo "=== starting queen-live-watch (C, 5s poll) ==="
  "${WATCH_BIN}" "${LOG}" 5 &
  WATCH_PID=$!
fi

echo ""
echo "=== starting live_build_field (forge + ZOCR tri-sense every ${QUEEN_WATCH_INTERVAL}s) ==="
echo "  Open dashboard in browser: ${DASH}"
echo "  Tail log: tail -f ${LOG}"
echo ""

exec "${ROOT}/scripts/live-build-field.sh" "$@"