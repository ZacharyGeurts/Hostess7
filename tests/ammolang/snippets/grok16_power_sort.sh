#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${sg}/Grok16/data/g16-power-sort-doctrine.json" ]]
  [[ -f "${sg}/Grok16/lib/field-power-sort.py" ]]
  [[ -f "${sg}/Grok16/lib/g16-power-sort-plate.py" ]]
  grep -q 'plate_not_wire' "${sg}/Grok16/data/g16-power-sort-doctrine.json"
  grep -q 'g16_power_sort' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'power_sort' "${sg}/Grok16/lib/field-always-optimal.py"
  grep -q '_power_sort_mod' "${ROOT}/Queen/lib/queen-file-browser.py"
  grep -q 'sections' "${ROOT}/Queen/lib/queen-file-browser.py"
  grep -q '/api/power-sort' "${ROOT}/lib/threat-panel-http.py"
  grep -q '"id": "power_sort"' "${ROOT}/data/ironclad-meld-extensions.json"
  grep -q 'field-physics-witness' "${ROOT}/lib/field-plate-meld.py"
  grep -q '/api/physics-witness' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'locational_sitrep' "${ROOT}/lib/field-plate-meld.py"
  grep -q '/api/locational-sitrep' "${ROOT}/lib/threat-panel-http.py"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-field-drive/nexus-field/state}" \
    aml_py "field-locational-sitrep-plate.py" cycle | grep -q '"plate_not_wire": true'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-field-drive/nexus-field/state}" GROK16_ROOT="$sg/Grok16" \
    aml_py "field-physics-witness.py" cycle | grep -q 'We all need to know thermals'
  GROK16_SG_ROOT="$sg" SG_ROOT="$sg" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-field-drive/nexus-field/state}" \
    python3 "${sg}/Grok16/lib/field-power-sort.py" apply | grep -q '"always_best_sort": true'
  GROK16_SG_ROOT="$sg" SG_ROOT="$sg" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-field-drive/nexus-field/state}" \
    python3 "${sg}/Grok16/lib/g16-power-sort-plate.py" cycle | grep -q '"plate_not_wire": true'
  grep -q 'line_safety' "${sg}/Grok16/data/g16-power-sort-doctrine.json"
  grep -q 'narrow_band_width' "${sg}/Grok16/lib/field-power-sort.py"
  GROK16_SG_ROOT="$sg" SG_ROOT="$sg" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-field-drive/nexus-field/state}" \
    python3 "${sg}/Grok16/lib/g16-power-sort-plate.py" cycle | grep -q '"narrow_band_width": 16'
  [[ -f "${sg}/Grok16/data/g16-power-sort-panel.json" ]]
  [[ -f "${sg}/Grok16/data/g16-power-sort-bench.json" ]]
  [[ -x "${sg}/Grok16/scripts/grok16-test-gate.sh" ]]
