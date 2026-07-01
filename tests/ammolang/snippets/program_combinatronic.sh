#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-program-combinatronic.py" ]]
  [[ -f "${ROOT}/data/field-program-combinatronic-seed.json" ]]
  [[ -f "${ROOT}/data/field-program-combinatronic-doctrine.json" ]]
  grep -q 'program_combinatronic' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/data/g16-field-combinatorics-doctrine.json"
  grep -q '_program_combinatronic_slice' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'program_combinatronic' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q 'program_combinatronic' "${ROOT}/lib/field-combinatorics-comb.py"
  grep -q '/api/program/combinatronic' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'boil_command' "${ROOT}/lib/field-program-combinatronic.py"
  tmp_state="$(mktemp -d)"
  prog_out="$(mktemp)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-program-combinatronic.py" combinatronic >"$prog_out" 2>/dev/null || true
  grep -q 'field-program-combinatronic/v1' "$prog_out"
  aml_py "field-program-combinatronic.py" boil python def >"$prog_out" 2>/dev/null || true
  grep -q '"canonical": "declare"' "$prog_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    python3 "$sg/Grok16/lib/field_combinatorics.py" publish >"$prog_out" 2>/dev/null
  grep -q 'program_combinatronic' "$prog_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-program-combinatronic.py" combinatronic >"$prog_out" 2>/dev/null || true
  grep -q '"boil_complete": true' "$prog_out"
  rm -f "$prog_out"
