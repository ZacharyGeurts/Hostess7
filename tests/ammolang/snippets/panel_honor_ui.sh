#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'view-honor' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderHonorability' "${ROOT}/panel/threat-panel.html"
  grep -q 'honorStarsHtml' "${ROOT}/panel/threat-panel.html"
  grep -q 'honor-pending-banner' "${ROOT}/panel/threat-panel.html"
  grep -q 'honor-loc-wireless' "${ROOT}/panel/threat-panel.html"
  grep -q 'data-view-jump="intel/trust"' "${ROOT}/panel/threat-panel.html"
  grep -q 'distance from you' "${ROOT}/panel/threat-panel.html"
