#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${sg}/Grok16/data/g16-always-optimal-doctrine.json" ]]
  [[ -f "${sg}/Grok16/lib/field-always-optimal.py" ]]
  grep -q 'always_optimal' "${sg}/Grok16/scripts/grok16-integrate.sh"
  grep -q 'ideal_profile' "${sg}/NewLatest/lib/field-plate-combinatorics-bridge.py"
  grep -q '_run_always_optimal' "${ROOT}/lib/field-compatibility-layers.py"
  grep -q 'nexus_boot_impl_always_optimal' "${ROOT}/lib/nexus-boot-impl.sh"
  grep -q 'auto_on_panel_boot' "${sg}/Grok16/data/g16-always-optimal-doctrine.json"
  grep -q '/api/always-optimal' "${ROOT}/lib/threat-panel-http.py"
  GROK16_SG_ROOT="$sg" SG_ROOT="$sg" NEXUS_STATE_DIR="${NEXUS_STATE_DIR:-${ROOT}/.nexus-field-drive/nexus-field/state}" \
    python3 "${sg}/Grok16/lib/field-always-optimal.py" apply --no-layers | grep -q '"always_optimal": true'
  [[ -f "${sg}/Grok16/data/g16-always-optimal-panel.json" ]]
  grep -q 'G16_BELT_PROFILE' "${sg}/Grok16/data/grok16-integrate.env"
