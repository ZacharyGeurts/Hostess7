#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'settings-profile-card' "${ROOT}/panel/threat-panel.html"
  grep -q 'setting-state-badge' "${ROOT}/panel/threat-panel.html"
  grep -q 'applySettingRowVisual' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderSettingsProfile' "${ROOT}/panel/threat-panel.html"
  grep -q 'summary-protection' "${ROOT}/panel/threat-panel.html"
  grep -qE 'v[2-7]\.[0-9]+\.[0-9]+' "${ROOT}/panel/threat-panel.html"
