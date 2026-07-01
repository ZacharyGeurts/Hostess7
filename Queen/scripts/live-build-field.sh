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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/live-build-field.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# Full native field live build — latest g16 + ZOCR hangup watch (~10s).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/../.." && pwd)"
export SG_ROOT="${SG_ROOT:-${SG}}"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${ROOT}}"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-state}"
export QUEEN_ROOT="${ROOT}"
export GROK16_ROOT="${GROK16_ROOT:-${SG}/Grok16}"
export ZOCR_ROOT="${ZOCR_ROOT:-${SG}/ZOCR}"
export FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-${SG}/Final_Eye}"
export FINAL_EAR_ROOT="${FINAL_EAR_ROOT:-${SG}/Final_Ear}"
export QUEEN_WATCH_INTERVAL="${QUEEN_WATCH_INTERVAL:-10}"
export QUEEN_WATCH_OCR="${QUEEN_WATCH_OCR:-1}"
export QUEEN_FULL_FIELD="${QUEEN_FULL_FIELD:-1}"
export G16_RELEASE_PROFILE="${G16_RELEASE_PROFILE:-1}"
export G16_FIELD_SPEED="${G16_FIELD_SPEED:-1}"
export QUEEN_WORLD_PORT="${QUEEN_WORLD_PORT:-9481}"
export PATH="${SG}/GrokPy/bin:${SG}/PythonG/bin:${ROOT}/bin:${PATH}"

LOG="${ROOT}/.queen-forge.log"
echo "Queen live native field build"
echo "  log: ${LOG}"
echo "  g16: ${GROK16_ROOT}"
echo "  ZOCR: ${ZOCR_ROOT}"
echo "  Final_Eye: ${FINAL_EYE_ROOT}"
echo "  Final_Ear: ${FINAL_EAR_ROOT} (tri-sense hangup poll every ${QUEEN_WATCH_INTERVAL}s)"
echo "  full field: ${QUEEN_FULL_FIELD}"

exec pythong "${ROOT}/lib/queen-forge.py" run live_build_field 2>&1 | tee -a "${LOG}"