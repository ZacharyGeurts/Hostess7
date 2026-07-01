#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/Queen/data/queen-localhost-bookmarks.json" ]]
  [[ -f "${ROOT}/Queen/lib/queen-browser-settings.py" ]]
  [[ -f "${ROOT}/Queen/lib/queen-bookmark-tree.py" ]]
  [[ -f "${ROOT}/Queen/lib/queen-bookmark-tooltips.py" ]]
  [[ -f "${ROOT}/Queen/world/queen-bookmarks-bar.js" ]]
  [[ -f "${ROOT}/Queen/world/queen-browser-settings.html" ]]
  grep -q 'localhost_flyout' "${ROOT}/Queen/lib/queen-browser.py"
  grep -q 'bookmark_trees' "${ROOT}/Queen/lib/queen-browser.py"
  grep -q 'qb-bookmarks-search' "${ROOT}/Queen/world/browser.html"
  grep -q '/api/queen-browser-settings' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'tooltips_enabled' "${ROOT}/Queen/data/queen-browser-settings-doctrine.json"
  grep -q 'security_locked_keys' "${ROOT}/Queen/data/queen-browser-settings-doctrine.json"
  grep -q '_secure_compat_profile' "${ROOT}/Queen/lib/queen-browser.py"
  "$PY" -c "import json; d=json.load(open('${ROOT}/Queen/data/queen-browser-settings-doctrine.json')); assert 'tooltips_fetch_meta' not in (d.get('defaults') or {}), d"
  ! [[ -f "${ROOT}/Queen/world/queen-browser.js" ]]
  grep -q '_extract_gecko_tree' "${ROOT}/Queen/lib/queen-browser-import.py"
out=$("$PY" "${ROOT}/Queen/lib/queen-browser-settings.py" posture 2>/dev/null || true); grep -q '"security_locked": true'
