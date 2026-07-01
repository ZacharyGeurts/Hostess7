#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'view-precision-map' "${ROOT}/panel/threat-panel.html"
  grep -q 'view-precision-web' "${ROOT}/panel/threat-panel.html"
  grep -q 'precision-map.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'precision-spiderweb.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-map.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-theme.css' "${ROOT}/panel/threat-panel.html"
  [[ -f "${ROOT}/panel/assets/nexus-map.js" ]]
  [[ -f "${ROOT}/panel/assets/nexus-theme.css" ]]
  grep -q 'NexusMap' "${ROOT}/panel/assets/precision-map.js"
  grep -q 'us-dashboard' "${ROOT}/panel/threat-panel.html"
  grep -q 'us-hero' "${ROOT}/panel/threat-panel.html"
  grep -q 'map-viewport' "${ROOT}/panel/threat-panel.html"
  grep -q 'primeMapPanel' "${ROOT}/panel/assets/nexus-map.js"
  grep -q 'resolveAnchor' "${ROOT}/panel/assets/precision-map.js"
  grep -q 'renderPrecisionMap' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderPrecisionSpiderweb' "${ROOT}/panel/threat-panel.html"
  grep -q 'Precision · Map' "${ROOT}/panel/threat-panel.html"
  grep -q 'Precision · Web' "${ROOT}/panel/threat-panel.html"
  grep -q 'precision-place-toggle' "${ROOT}/panel/threat-panel.html"
  grep -q 'precision-web-canvas' "${ROOT}/panel/threat-panel.html"
