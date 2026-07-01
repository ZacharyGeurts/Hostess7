#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-chips-plate-stack.py" ]]
  [[ -f "${ROOT}/data/field-chips-iron-steel-plate-doctrine.json" ]]
  grep -q 'chips_plate_stack' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'chips_plate_stack' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'chips_plate_stack' "${ROOT}/data/field-plate-meld-doctrine.json"
  grep -q 'sovereign_time_only' "${ROOT}/data/field-chips-iron-steel-plate-doctrine.json"
  grep -q 'steel_rewrite' "${ROOT}/data/field-chips-iron-steel-plate-doctrine.json"
  grep -q 'steel_family' "${ROOT}/lib/field-chips-plate-stack.py"
  grep -q 'field-steel-plate-optimal' "${ROOT}/data/field-chips-iron-steel-plate-doctrine.json"
  [[ -f "${ROOT}/lib/field-steel-plate-optimal.py" ]]
  grep -q 'direct_neural_calculator' "${ROOT}/lib/field-chips-plate-stack.py"
  grep -q 'organize_chip_paths' "${ROOT}/lib/iron-plate-organize.py"
  grep -q '/api/chips/plate-stack' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/chips/plate-stack' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'chips_plate_stack' "${ROOT}/lib/g16-combinatronic-rebalance.py"
  grep -q 'plate_stack' "${ROOT}/data/field-ironclad-chips-combinatorics-doctrine.json"
  [[ -f "${ROOT}/lib/field-chips-core.py" ]]
  [[ -f "${ROOT}/data/field-chips-core-doctrine.json" ]]
  grep -q 'chips_core' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'chips_core' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'condense_after_ironclad' "${ROOT}/lib/field-chips-core.py"
  grep -q '/api/chips/core' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/chips/core' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'chips_core' "${ROOT}/lib/g16-combinatronic-rebalance.py"
  grep -q 'qcc-chips-core' "${ROOT}/Queen/world/queen-chips-cores.html"
  tmp_state="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-ironclad-chips-combinatorics.py" publish >/dev/null
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-steel-neural-plates.py" build >/dev/null
out=$("$PY" "${ROOT}/lib/field-chips-plate-stack.py" build 2>/dev/null || true); grep -q 'field-chips-plate-stack/v1' <<<"$out"
out=$("$PY" "${ROOT}/lib/field-chips-plate-stack.py" verify 2>/dev/null || true); grep -q '"ok": true' <<<"$out"
out=$("$PY" "${ROOT}/lib/field-chips-plate-stack.py" wire 2>/dev/null || true); grep -q 'sovereign_linear_ns' <<<"$out"
  grep -q 'field-plate-rebalance-derivatives' "${ROOT}/lib/field-chips-plate-stack.py"
  grep -q 'plate_rebalance_derivatives' "${ROOT}/lib/g16-combinatronic-rebalance.py"
out=$("$PY" "${ROOT}/lib/field-plate-rebalance-derivatives.py" verify 2>/dev/null || true); grep -q '"ok": true' <<<"$out"
out=$("$PY" "${ROOT}/lib/g16-combinatronic-rebalance.py" plate_derivatives 2>/dev/null || true); grep -q 'central_difference' <<<"$out"
out=$("$PY" "${ROOT}/lib/field-chips-core.py" build 2>/dev/null || true); grep -q 'field-chips-core/v1' <<<"$out"
out=$("$PY" "${ROOT}/lib/field-chips-core.py" verify 2>/dev/null || true); grep -q '"ok": true' <<<"$out"
