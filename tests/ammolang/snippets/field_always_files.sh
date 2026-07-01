#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-always-files.py" ]]
  [[ -f "${ROOT}/data/field-always-files-doctrine.json" ]]
  [[ -f "${ROOT}/data/field-vfs-ai-contract.json" ]]
  grep -q 'history_for_path' "${ROOT}/lib/field-drive-indexer.py"
  grep -q 'enrich_entry' "${ROOT}/lib/field-always-files.py"
  grep -q 'properties_menu' "${ROOT}/lib/field-always-files.py"
  grep -q 'system_security' "${ROOT}/lib/field-always-files.py"
  grep -q 'system_security' "${ROOT}/data/field-always-files-doctrine.json"
  grep -q 'password_required' "${ROOT}/data/field-always-files-doctrine.json"
  grep -q '_maybe_enrich_row' "${ROOT}/Queen/lib/queen-file-browser.py"
  grep -q 'always_properties' "${ROOT}/Queen/lib/queen-file-browser.py"
  grep -q '/api/field-vfs' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/field-timeshift' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'always_files' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'alwaysKnowsBadge' "${ROOT}/Queen/world/queen-files.js"
  grep -q 'showProperties' "${ROOT}/Queen/world/queen-files.js"
  grep -q 'renderPropertiesFlyout' "${ROOT}/Queen/world/queen-files.js"
  grep -q 'qf-props-flyout' "${ROOT}/Queen/world/queen-files.html"
  grep -q 'qf-props-menu' "${ROOT}/Queen/world/queen-files.html"
  grep -q 'QueenIconEngine' "${ROOT}/Queen/world/queen-icon-engine.js"
  grep -q 'file-folder-32.png' "${ROOT}/Queen/data/queen-icon-battery.json"
  grep -q 'QueenIconEngine' "${ROOT}/panel/assets/field-startbar.js"
  grep -q 'folderIconEl' "${ROOT}/panel/assets/field-startbar.js"
  grep -q 'qf-sec-banner' "${ROOT}/Queen/world/queen-files.css"
  grep -q 'qf-fly-pane' "${ROOT}/Queen/world/queen-viewer.css"
  [[ -f "${ROOT}/Queen/world/assets/icons/file-folder-32.png" ]]
  [[ -f "${ROOT}/panel/assets/queen-icon-engine.js" ]]
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-always-files.py" sync 2>/dev/null || true); grep -q 'field-always-files-plate/v1'
out=$("$PY" "${ROOT}/lib/field-always-files.py" ai 2>/dev/null || true); grep -q 'field-vfs-ai-context/v1'
out=$("$PY" "${ROOT}/lib/field-always-files.py" resolve lib/field-always-files.py 2>/dev/null || true); grep -q 'field-always-file/v1'
out=$("$PY" "${ROOT}/lib/field-always-files.py" properties lib/field-always-files.py 2>/dev/null || true); grep -q 'field-always-properties/v1'
out=$("$PY" "${ROOT}/lib/field-always-files.py" properties lib/field-always-files.py 2>/dev/null || true); grep -q 'password_required'
