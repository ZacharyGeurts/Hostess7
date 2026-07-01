#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-steel-neural-plates.py" ]]
  [[ -f "${ROOT}/data/field-steel-neural-plates-doctrine.json" ]]
  grep -q 'steel_neural_plates' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'steel_neural_plates' "${ROOT}/lib/g16-combinatronic-rebalance.py"
  grep -q 'steel_plates' "${ROOT}/data/field-combinatronic-balance-doctrine.json"
  grep -q '/api/steel-neural-plates' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/steel-neural-plates' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'combinatoric_entry' "${ROOT}/lib/field-steel-neural-plates.py"
  grep -q 'deep_paths' "${ROOT}/lib/field-steel-neural-plates.py"
  tmp_state="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-chip-battery.py" publish >/dev/null
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-program-combinatronic.py" publish >/dev/null
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-g16-universal-combinatronic.py" publish >/dev/null
out=$("$PY" "${ROOT}/lib/field-steel-neural-plates.py" build 2>/dev/null || true); grep -q 'field-steel-neural-plates/v1' <<<"$out"
out=$("$PY" "${ROOT}/lib/field-steel-neural-plates.py" verify 2>/dev/null || true); grep -q '"ok": true' <<<"$out"
out=$("$PY" "${ROOT}/lib/g16-combinatronic-rebalance.py" steel_plates 2>/dev/null || true); grep -q '"action": "steel_neural_plates"' <<<"$out"
