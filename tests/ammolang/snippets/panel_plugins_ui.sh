#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'nexus-plugin-runtime.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-plugins-dock' "${ROOT}/panel/threat-panel.html"
  grep -q 'NexusPlugins.render' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-plugin-manager' "${ROOT}/panel/threat-panel.html"
  grep -q 'tab-beacon.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'summary-plugins' "${ROOT}/panel/threat-panel.html"
