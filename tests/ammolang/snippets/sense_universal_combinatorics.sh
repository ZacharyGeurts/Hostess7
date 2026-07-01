#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'sense_universal_slice' "${ROOT}/lib/field-sense-package-meld.py"
  grep -q 'universal_lock' "${ROOT}/data/field-sense-package-doctrine.json"
  grep -q 'universal_lock' "${ROOT}/data/eye-ear-plate-doctrine.json"
  grep -q 'sense_stack' "${ROOT}/data/universal-protector-doctrine.json"
  grep -q 'sense_universal' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/data/g16-field-combinatorics-doctrine.json"
  grep -q '_sense_universal_slice' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'universal_lock' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'field_ellie_fier' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'sense_universal' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q '_universal_lock_gate' "${ROOT}/lib/eye-ear-plate.py"
  grep -q 'universal_lock' "${ROOT}/lib/universal-protector.py"
  tmp_state="$(mktemp -d)"
  sense_out="$(mktemp)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-sense-package-meld.py" slice >"$sense_out" 2>/dev/null || true
  grep -q 'field-sense-universal-slice' "$sense_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    python3 "$sg/Grok16/lib/field_combinatorics.py" publish >"$sense_out" 2>/dev/null
  grep -q 'sense_universal' "$sense_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-plate-combinatorics-bridge.py" build >"$sense_out" 2>/dev/null || true
  grep -q 'sense_universal_lock' "$sense_out"
  rm -f "$sense_out"
