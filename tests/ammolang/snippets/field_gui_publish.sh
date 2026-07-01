#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-gui-publish.sh" ]]
  grep -q 'nexus_field_gui_publish_all' "${ROOT}/lib/threat-panel.sh"
  grep -q 'field_hardware' "${ROOT}/lib/threat-panel.sh"
  grep -q 'field_hazard_onset' "${ROOT}/lib/threat-panel.sh"
  grep -q 'lethal_enforcement' "${ROOT}/lib/threat-panel.sh"
  grep -q '/api/field' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'renderHardware(doc)' "${ROOT}/panel/assets/signals-field.js"
  grep -q 'fetch("/api/status"' "${ROOT}/panel/threat-panel.html"
  grep -q 'FIELD_PARALLEL_SLICES' "${ROOT}/panel/threat-panel.html"
  grep -q 'PANEL_PARALLEL_KEYS' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'max_workers: int = 25' "${ROOT}/lib/field-panel-parallel.py"
  ! grep -q 'nexus_hostess7_nexus_update_plan' "${ROOT}/lib/hostess7-operator.sh"
  grep -q 'NEXUS_VERSION="g16-1.0"' "${ROOT}/lib/nexus-common.sh"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" bash -c '
    source "${NEXUS_INSTALL_ROOT}/lib/nexus-common.sh"
    nexus_init_runtime_paths
    source "${NEXUS_INSTALL_ROOT}/lib/field-gui-publish.sh"
    nexus_field_gui_publish_all
    [[ -s "$NEXUS_STATE_DIR/field-hardware-panel.json" ]] || nexus_field_hardware_json | grep -q field-hardware
  '
