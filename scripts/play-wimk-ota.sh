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
    exec bash "${_AML_ROOT}/lib/ammolang-run.sh" exec "script:scripts/play-wimk-ota.sh" "$@"
  fi
fi
unset -f _aml_find_root 2>/dev/null || true

#!/bin/bash
# 93.1 WIMK — 3-field antenna catches OTA and plays station program.
set -euo pipefail
ROOT="${NEXUS_INSTALL_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
export NEXUS_INSTALL_ROOT="$ROOT"
export NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-$ROOT/.nexus-state}"
export NEXUS_FIELD_CATCH_MHZ="${NEXUS_FIELD_CATCH_MHZ:-93.1}"
export NEXUS_ANTENNA_MAX_ATTEMPTS="${NEXUS_ANTENNA_MAX_ATTEMPTS:-8}"

echo "=== 93.1 WIMK — 3-field antenna → play station ==="
pythong "$ROOT/lib/field-antenna-catch.py" catch \
  '{"freq_mhz":93.1,"station_id":"wimk-931","call_sign":"WIMK","play":true,"seconds":30}'