#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-combinatronic-spider-wire.py" ]]
  [[ -f "${ROOT}/data/field-combinatronic-spider-wire-doctrine.json" ]]
  grep -q 'spider_wire' "${ROOT}/lib/g16-combinatronic-rebalance.py"
  grep -q 'ironclad_outward' "${ROOT}/lib/field-combinatronic-spider-wire.py"
  grep -q '/api/combinatronic/spider-wire' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/combinatronic/spider-wire' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'qcc-spider-wire' "${ROOT}/Queen/world/queen-chips-cores.html"
  grep -q 'combinatronic_spider_wire' "${ROOT}/Hostess7/data/hostess7-neural-stack.json"
  tmp_state="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-g16-universal-combinatronic.py" combinatronic --refresh >/dev/null 2>&1 || true
  wire_out="$(mktemp)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-combinatronic-spider-wire.py" build >"$wire_out" 2>/dev/null
  grep -m1 -q 'field-combinatronic-spider-wire' "$wire_out"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" \
    aml_py "g16-combinatronic-rebalance.py" spider_wire >"$wire_out" 2>/dev/null
  grep -m1 -q '"action": "spider_wire"' "$wire_out"
  rm -f "$wire_out"
