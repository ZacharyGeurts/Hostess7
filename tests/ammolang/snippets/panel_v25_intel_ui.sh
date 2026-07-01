#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'renderIntelBanner' "${ROOT}/panel/threat-panel.html"
  grep -q 'Remove pest' "${ROOT}/panel/threat-panel.html"
  grep -qE 'v2\.(5\.0|6\.0|7\.0)' "${ROOT}/panel/threat-panel.html"
  grep -q '/api/pest/eradicate' "${ROOT}/lib/threat-panel-http.py"
