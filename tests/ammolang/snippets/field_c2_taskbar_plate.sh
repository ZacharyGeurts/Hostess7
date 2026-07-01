#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-c2-taskbar-plate.py" ]]
  [[ -f "${ROOT}/data/field-c2-taskbar-doctrine.json" ]]
  grep -q 'c2_taskbar' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'c2_taskbar' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'c2_taskbar' "${ROOT}/lib/field-plate-combinatorics-bridge.py"
  grep -q '/api/field-c2-taskbar' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'c2_taskbar' "${ROOT}/data/ironclad-meld-extensions.json"
  grep -q 'field-c2-taskbar-plate' "${ROOT}/lib/field-code-bugfinder.py"
  grep -q 'c2_taskbar' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'comb-quint-strip' "${ROOT}/panel/combinatorics-studio.html"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-c2-taskbar-plate.py" json 2>/dev/null || true); grep -q 'field-c2-taskbar-plate/v1'
out=$("$PY" "${ROOT}/lib/field-c2-taskbar-plate.py" bsp 2>/dev/null || true); grep -q 'case_id'
out=$("$PY" "${ROOT}/lib/field-plate-combinatorics-bridge.py" build 2>/dev/null || true); grep -q 'c2_quint_live'
