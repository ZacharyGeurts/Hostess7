#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-cpu-library.py" ]]
  [[ -f "${ROOT}/data/field-cpu-library-seed.json" ]]
  [[ -f "${ROOT}/lib/field-font-kit.py" ]]
  [[ -f "${ROOT}/data/field-font-doctrine.json" ]]
  grep -q 'cpu_library' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'cpu_library' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'field_font' "${ROOT}/lib/field-panel-parallel.py"
  grep -q '/api/cpu-library' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/field-font' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/field-font-editor' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/cpu-library' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'field-cpu-library' "${ROOT}/data/field-host-desktop-doctrine.json"
  grep -q 'field-font-editor' "${ROOT}/data/field-host-desktop-doctrine.json"
  grep -q 'desktop' "${ROOT}/data/field-host-desktop-doctrine.json"
  grep -q 'clipboard_master' "${ROOT}/data/field-clipboard-doctrine.json"
  grep -q 'historic_ring' "${ROOT}/data/field-clipboard-doctrine.json"
  grep -q 'history-paste' "${ROOT}/lib/field-clipboard-wire.py"
  [[ -f "${ROOT}/Queen/world/queen-cpu-library.html" ]]
  [[ -f "${ROOT}/panel/field-font-editor.html" ]]
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-cpu-library.py" verify 2>/dev/null || true); grep -q '"ok": true'
out=$("$PY" "${ROOT}/lib/field-cpu-library.py" search arm 2>/dev/null || true); grep -q '"hits"'
out=$("$PY" "${ROOT}/lib/field-font-kit.py" build 2>/dev/null || true); grep -q '"ok": true'
out=$("$PY" "${ROOT}/lib/field-font-kit.py" panel 2>/dev/null || true); grep -q 'field-font-panel/v1'
out=$("$PY" "${ROOT}/lib/field-clipboard-wire.py" history 2>/dev/null || true); grep -q 'field-clipboard-history/v1'
  [[ -f "${ROOT}/panel/assets/fonts/amouranth-bold-sdf.png" ]]
