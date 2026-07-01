#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-clean-juice.py" ]]
  [[ -f "${ROOT}/data/field-clean-juice-doctrine.json" ]]
  grep -q 'field_clean_juice' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'grid_talk' "${ROOT}/data/field-power-doctrine.json"
  grep -q 'double_voltage_on_present_rail' "${ROOT}/data/field-voltage-regulation-doctrine.json"
  grep -q 'no_double_voltage' "${ROOT}/lib/field-clean-juice.py"
  grep -q 'bsp_octree' "${ROOT}/lib/field-clean-juice.py"
  grep -q '_clean_juice' "${ROOT}/lib/field-power-ledger.py"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-clean-juice.py" json 2>/dev/null 2>/dev/null || true); grep -q 'field-clean-juice/v1'
out=$("$PY" "${ROOT}/lib/field-clean-juice.py" json 2>/dev/null 2>/dev/null || true); grep -q '"grid_talk": false'
  rm -rf "$tmp_state"
