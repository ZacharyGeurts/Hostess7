#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'view-field-rf' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderFieldRF' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderPoliceAgency' "${ROOT}/panel/threat-panel.html"
  grep -q 'police-agency-select' "${ROOT}/panel/threat-panel.html"
  grep -q 'police-category-filter' "${ROOT}/panel/threat-panel.html"
  grep -q 'police-import-file' "${ROOT}/panel/threat-panel.html"
  grep -q 'police-import-images' "${ROOT}/panel/threat-panel.html"
  grep -q 'gov-merge-banner' "${ROOT}/panel/threat-panel.html"
  grep -q 'intelligence databases' "${ROOT}/panel/threat-panel.html"
  grep -q 'program-tag-select' "${ROOT}/panel/threat-panel.html"
  grep -q 'Obscure programs' "${ROOT}/panel/threat-panel.html"
  grep -q 'program-tag-desc' "${ROOT}/panel/threat-panel.html"
  grep -q 'location.reload' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-rf-shield-enabled' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-rf-lawful-kick' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-rf-shoot-to-kill' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-rf-unpermitted' "${ROOT}/panel/threat-panel.html"
  grep -q 'view-field-rf' "${ROOT}/panel/threat-panel.html"
  grep -q 'SHOOT TO KILL' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-material.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-rf-material-map' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderMaterialField' "${ROOT}/panel/threat-panel.html"
  grep -q 'disabled forever' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-rf-pollution' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-rf-operations' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-rf-antenna-fields' "${ROOT}/panel/threat-panel.html"
  grep -q 'resolution_score' "${ROOT}/panel/threat-panel.html"
  grep -q 'NEAR-INFINITE' "${ROOT}/panel/threat-panel.html"
  grep -q 'Permitted spectrum' "${ROOT}/panel/threat-panel.html"
  grep -q 'WIFI_THREAT' "${ROOT}/panel/threat-panel.html" || grep -q 'Lawful kick' "${ROOT}/panel/threat-panel.html"
