#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/panel/assets/dusty-midnight.css" ]]
  [[ -f "${ROOT}/panel/assets/us-dashboard.js" ]]
  grep -q 'dusty-midnight' "${ROOT}/panel/threat-panel.html"
  grep -q 'dusty-midnight.css' "${ROOT}/panel/threat-panel.html"
  grep -q 'us-dashboard.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'us-host-machine' "${ROOT}/panel/threat-panel.html"
  grep -q 'us-traffic-canvas' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderUSDashboard' "${ROOT}/panel/assets/us-dashboard.js"
  grep -q 'nexus-military-v8' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-military-v82' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-v82' "${ROOT}/panel/threat-panel.html"
  grep -q 'v8.2.0' "${ROOT}/panel/threat-panel.html"
  grep -q '_panel_slice' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'prefetchTabSlices' "${ROOT}/panel/threat-panel.html"
  grep -q 'field_brain' "${ROOT}/lib/field-panel-parallel.py"
  grep -q '/api/field-brain' "${ROOT}/lib/threat-panel-http.py"
  [[ -f "${ROOT}/lib/field-brain-panel.py" ]]
  [[ -d "${ROOT}/library/dewey" ]]
