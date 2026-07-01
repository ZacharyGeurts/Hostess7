#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-filesystem-update.py" ]]
  [[ -f "${ROOT}/data/field-filesystem-doctrine.json" ]]
  grep -q 'field_filesystem' "${ROOT}/lib/field-panel-parallel.py"
  grep -q '/api/field-filesystem' "${ROOT}/lib/threat-panel-http.py"
  grep -q '"destroyed"' "${ROOT}/data/field-filesystem-doctrine.json"
  grep -q 'enrich_catalog_row' "${ROOT}/lib/nexus-file-catalog.py"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-filesystem-update.py" json 2>/dev/null || true); grep -q 'field-filesystem-update/v1'
out=$("$PY" "${ROOT}/lib/field-filesystem-update.py" mark /tmp/fs-test-listed.txt 2>/dev/null || true); grep -q '"deleted": true'
out=$("$PY" "${ROOT}/lib/field-filesystem-update.py" plan 2>/dev/null || true); grep -q 'overwrite_pending_mb'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    "$PY" -c "
import importlib.util, json
from pathlib import Path
p = Path('${ROOT}/lib/field-filesystem-update.py')
spec = importlib.util.spec_from_file_location('fsu', p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
row = mod.enrich_catalog_row({'path': 'lib/test.py', 'size': 1})
mod._set_overlay('lib/test.py', {'destroyed': True, 'destroyed_at': '2026-06-27T00:00:00Z', 'destroyed_date': '2026-06-27'})
row2 = mod.enrich_catalog_row({'path': 'lib/test.py', 'size': 1})
assert row2.get('destroyed') is True and row2.get('destroyed_date') == '2026-06-27'
print('destroyed_field_ok')
" | grep -q 'destroyed_field_ok'
