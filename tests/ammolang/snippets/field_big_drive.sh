#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-big-drive.py" ]]
  [[ -f "${ROOT}/data/field-big-drive-doctrine.json" ]]
  [[ -f "${ROOT}/panel/field-big-drive.html" ]]
  [[ -f "${ROOT}/panel/assets/field-big-drive.js" ]]
  grep -q '/api/field-big-drive' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/field-big-drive' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'field-big-drive' "${ROOT}/data/field-host-desktop-doctrine.json"
  grep -q 'Open in Big Drive' "${ROOT}/Queen/world/queen-files.js"
  grep -q '_storage_formats' "${ROOT}/lib/field-file-formats.py"
  grep -q 'field_on_field_forbidden' "${ROOT}/data/field-big-drive-doctrine.json"
  grep -q 'bd-stabilizer-bar' "${ROOT}/panel/field-big-drive.html"
  grep -q 'stabilizer_progress' "${ROOT}/lib/field-big-drive.py"
  grep -q 'stabilize_drive' "${ROOT}/lib/field-big-drive.py"
py="python3"
  SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$py" "${ROOT}/lib/field-big-drive.py" json | grep -q 'field-big-drive/v1'
tmp_iso="$NEXUS_STATE_DIR/big-drive-test.iso"
  printf 'plain iso payload' >"$tmp_iso"
  stab_out=$(SG_ROOT="${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}" NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$py" "${ROOT}/lib/field-big-drive.py" dispatch <<EOF
{"action":"stabilize","path":"${tmp_iso}","device_id":"usb_stick"}
EOF
)
  echo "$stab_out" | grep -q '"ok": true'
  echo "$stab_out" | grep -q 'universal_2d'
