#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'view-spiderweb' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderTerrorSpiderweb' "${ROOT}/panel/threat-panel.html"
  grep -q 'terror-spiderweb.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'spiderweb-map' "${ROOT}/panel/threat-panel.html"
  grep -q 'spiderweb-registry-map' "${ROOT}/panel/threat-panel.html"
  grep -q 'spiderweb-mobile-map' "${ROOT}/panel/threat-panel.html"
  grep -q 'Terror · Spiderweb' "${ROOT}/panel/threat-panel.html"
  grep -q 'spiderweb-registry-tables' "${ROOT}/panel/threat-panel.html"
  grep -q 'spiderweb-universal-banner' "${ROOT}/panel/threat-panel.html"
  grep -q 'spiderweb-existence-table' "${ROOT}/panel/threat-panel.html"
  grep -q 'Persistent existence identity' "${ROOT}/panel/threat-panel.html"
