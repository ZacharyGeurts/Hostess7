#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'Fair Ad Guardian' "${ROOT}/panel/threat-panel.html"
  grep -q 'policy-pick' "${ROOT}/panel/threat-panel.html"
  grep -q 'guardian-feed' "${ROOT}/panel/threat-panel.html"
  grep -q '/api/adblock/policy' "${ROOT}/lib/threat-panel-http.py"
  grep -qE 'v7\.[0-9]+\.[0-9]+|v2\.(7\.0|8\.0|9\.0)|v3\.(0\.(0|1)|[12]\.(0|1))' "${ROOT}/panel/threat-panel.html"
