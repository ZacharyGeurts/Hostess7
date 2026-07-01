#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  grep -q 'view-host-attack' "${ROOT}/panel/threat-panel.html"
  grep -q 'Host Attack' "${ROOT}/panel/threat-panel.html"
  grep -q 'renderHostAttackMap' "${ROOT}/panel/threat-panel.html"
  grep -q 'host-earth-map' "${ROOT}/panel/threat-panel.html"
  grep -q 'leaflet.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'createGlobeLayer' "${ROOT}/panel/threat-panel.html"
  grep -q 'SDF Wireframe' "${ROOT}/panel/threat-panel.html"
  grep -q 'trashHostPin' "${ROOT}/panel/threat-panel.html"
  grep -q 'host-map-trash' "${ROOT}/panel/threat-panel.html"
  grep -q 'Zachary Geurts' "${ROOT}/panel/threat-panel.html"
  grep -q 'normalizeGeo' "${ROOT}/panel/threat-panel.html"
  grep -q 'warmHostEarthMap' "${ROOT}/panel/threat-panel.html"
  grep -q 'attackKitKill' "${ROOT}/panel/threat-panel.html"
  grep -q 'haBleedLine' "${ROOT}/panel/threat-panel.html"
  grep -q 'selectHostTarget' "${ROOT}/panel/threat-panel.html"
  grep -q 'host-kill-dossier' "${ROOT}/panel/threat-panel.html"
  grep -q 'haTooltipText' "${ROOT}/panel/threat-panel.html"
  grep -q 'target_os' "${ROOT}/panel/threat-panel.html"
  grep -q 'sdf-render.js' "${ROOT}/panel/threat-panel.html"
  grep -q 'NexusSdf' "${ROOT}/panel/threat-panel.html"
  grep -q 'hydrateHostSdfMarkers' "${ROOT}/panel/threat-panel.html"
  grep -q 'formatGps' "${ROOT}/panel/threat-panel.html"
  grep -q 'HA_SDF_PIN_ANCHOR' "${ROOT}/panel/threat-panel.html"
  [[ -f "${ROOT}/panel/assets/sdf/manifest.json" ]]
  [[ -f "${ROOT}/panel/assets/sdf/pin-hostile.sdf.png" ]]
  [[ -f "${ROOT}/panel/assets/sdf/globe-world.sdf.png" ]]
  [[ -f "${ROOT}/panel/assets/sdf/globe-wireframe.sdf.png" ]]
  grep -q 'globe-wireframe' "${ROOT}/panel/assets/sdf/manifest.json"
  grep -q 'attackKitCheckOnline' "${ROOT}/panel/threat-panel.html"
  grep -q 'attackKitRekill' "${ROOT}/panel/threat-panel.html"
  grep -q 'attackKitNokill' "${ROOT}/panel/threat-panel.html"
  grep -q 'haOnlineBadgeHtml' "${ROOT}/panel/threat-panel.html"
  grep -q 'ha-online-badge' "${ROOT}/panel/threat-panel.html"
  grep -q 'NO-KILL' "${ROOT}/panel/threat-panel.html"
  grep -q 'Check Online' "${ROOT}/panel/threat-panel.html"
  grep -q 'RE-KILL' "${ROOT}/panel/threat-panel.html"
  grep -q 'same-host validation' "${ROOT}/panel/threat-panel.html"
  grep -q 'checkNexusUpdate' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-version-btn' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-upgrade-btn' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-restart-btn' "${ROOT}/panel/threat-panel.html"
  grep -q 'distance_label' "${ROOT}/panel/threat-panel.html"
  grep -qE 'v[4-7]\.[0-9]+\.[0-9]+' "${ROOT}/panel/threat-panel.html"
