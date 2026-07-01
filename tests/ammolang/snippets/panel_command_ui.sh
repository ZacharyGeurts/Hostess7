#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'view-command' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderCommandCenter' "${ROOT}/panel/threat-panel.html"
  grep -q 'TAB_GROUPS' "${ROOT}/panel/threat-panel.html"
  grep -q 'data-view="command"' "${ROOT}/panel/threat-panel.html"
  grep -q 'data-view="packets"' "${ROOT}/panel/threat-panel.html"
  grep -q 'data-view="threats"' "${ROOT}/panel/threat-panel.html"
  grep -q 'data-view="intel"' "${ROOT}/panel/threat-panel.html"
  grep -q 'data-view="system"' "${ROOT}/panel/threat-panel.html"
  grep -q 'panel-subnav' "${ROOT}/panel/threat-panel.html"
  grep -q 'Good Guy' "${ROOT}/panel/threat-panel.html"
  grep -qE 'v7\.0\.0|v5\.(0|8\.4)' "${ROOT}/panel/threat-panel.html"
