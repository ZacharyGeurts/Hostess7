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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:Queen/scripts/watch-build.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/usr/bin/env bash
# ZOCR + Final_Eye + Final_Ear forge watch — catch hangups every ~10s while build runs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SG="$(cd "${ROOT}/../.." && pwd)"
export SG_ROOT="${SG_ROOT:-${SG}}"
export NEXUS_INSTALL_ROOT="${NEXUS_INSTALL_ROOT:-${ROOT}}"
export QUEEN_ROOT="${ROOT}"
export ZOCR_ROOT="${ZOCR_ROOT:-${SG}/ZOCR}"
export FINAL_EYE_ROOT="${FINAL_EYE_ROOT:-${SG}/Final_Eye}"
export FINAL_EAR_ROOT="${FINAL_EAR_ROOT:-${SG}/Final_Ear}"
export GROK16_ROOT="${GROK16_ROOT:-${SG}/Grok16}"
export QUEEN_WATCH_INTERVAL="${1:-10}"
export QUEEN_WATCH_OCR="${QUEEN_WATCH_OCR:-1}"
export QUEEN_WATCH_LOOP=1
exec pythong "${ROOT}/lib/queen-forge.py" run forge_watch