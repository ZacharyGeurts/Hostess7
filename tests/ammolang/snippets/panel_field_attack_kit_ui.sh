#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'Field Attack Kit' "${ROOT}/panel/threat-panel.html"
  grep -q 'ak-crush-hot' "${ROOT}/panel/threat-panel.html"
  grep -q 'attack-kit/kill' "${ROOT}/panel/threat-panel.html"
  grep -q 'KILL' "${ROOT}/panel/threat-panel.html"
  grep -q 'FRIENDLY' "${ROOT}/panel/threat-panel.html"
  grep -q 'friendly_refused' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'NEXUS_ATTACK_KIT_AUTO_CRUSH' "${ROOT}/panel/threat-panel.html"
  grep -q 'Auto-kill hostile targets' "${ROOT}/panel/threat-panel.html"
  grep -q 'God Bless' "${ROOT}/panel/threat-panel.html"
  grep -q 'ha-strike-badge' "${ROOT}/panel/threat-panel.html"
  grep -q 'Trust Strike' "${ROOT}/panel/threat-panel.html"
  grep -q 'ak-strike-corpus' "${ROOT}/panel/threat-panel.html"
  grep -q 'field-toolkit-panel' "${ROOT}/panel/threat-panel.html"
  grep -q 'ft-attack-select' "${ROOT}/panel/threat-panel.html"
  grep -q 'update-busy' "${ROOT}/panel/threat-panel.html"
  grep -qE 'v3\.8\.2' "${ROOT}/panel/threat-panel.html"
  grep -q 'lastPanelUpdated' "${ROOT}/panel/threat-panel.html"
  grep -q 'consumer_collateral' "${ROOT}/panel/threat-panel.html"
  grep -q 'PINPOINT' "${ROOT}/panel/threat-panel.html"
  grep -q 'HARDWARE DESTROY' "${ROOT}/panel/threat-panel.html"
  grep -q 'strike-destroy' "${ROOT}/panel/threat-panel.html"
  grep -q 'old-man' "${ROOT}/panel/threat-panel.html"
  grep -q 'Comfort reading' "${ROOT}/panel/threat-panel.html"
  grep -q 'set-old-man' "${ROOT}/panel/threat-panel.html"
  grep -q 'v6.0.0' "${ROOT}/panel/threat-panel.html"
  ! grep -q 'Grandmas' "${ROOT}/panel/threat-panel.html"
