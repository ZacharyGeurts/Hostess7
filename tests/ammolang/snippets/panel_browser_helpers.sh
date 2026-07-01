#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/panel-browser.sh" ]]
  [[ -f "${ROOT}/panel/field.html" ]]
  [[ -f "${ROOT}/panel/assets/field-foundation.js" ]]
  grep -q '/api/field' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'panel_ready' "${ROOT}/lib/threat-panel.sh"
  grep -q 'function paintPanel' "${ROOT}/panel/threat-panel.html"
  grep -q 'No client cache' "${ROOT}/panel/assets/field-foundation.js"
  grep -q '/api/status' "${ROOT}/panel/assets/field-foundation.js"
  grep -q 'field-live' "${ROOT}/panel/threat-panel.html"
  grep -q 'select, select option' "${ROOT}/panel/threat-panel.html"
  ! grep -q '_inject_field_bootstrap' "${ROOT}/lib/threat-panel-http.py"
  [[ -f "${ROOT}/lib/hostess7-field.sh" ]]
  [[ -f "${ROOT}/lib/hostess7-operator.sh" ]]
  nexus_panel_url | grep -q '127.0.0.1'
  nexus_panel_url | grep -q '/field'
  nexus_panel_app_url | grep -q '/app'
