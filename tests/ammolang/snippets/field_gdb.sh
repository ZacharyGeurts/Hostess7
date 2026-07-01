#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-gdb.py" ]]
  [[ -f "${sg}/GDB-Field/data/field-gdb-doctrine.json" ]]
  grep -q '/api/field-gdb' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'ai_decode' "${ROOT}/lib/field-gdb.py"
  grep -q 'graph_call_stack' "${ROOT}/lib/field-gdb.py"
out=$("$PY" "${ROOT}/lib/field-gdb.py" json 2>/dev/null || true); grep -q 'field-gdb-panel/v1'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$(mktemp -d)" SG_ROOT="$sg" GROK16_ROOT="$sg/Grok16" GDB_FIELD_ROOT="$sg/GDB-Field" HOSTESS7_ROOT="$ROOT/Hostess7" \
    "$PY" -c "
import importlib.util, json
from pathlib import Path
spec = importlib.util.spec_from_file_location('fg', Path('${ROOT}/lib/field-gdb.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
hl = mod.highlight_asm_line('  401000:       55                    push   %rbp')
assert hl.get('ansi') and 'push' in hl.get('ansi','')
g = mod.graph_call_stack([{'depth':0,'function':'main','file':'a.c','line':1,'pc':'0x1'}])
assert g.get('chart') and g['chart'].get('datasets')
print('field_gdb_ok')
" | grep -q 'field_gdb_ok'
  if [[ -x "${sg}/Grok16/bin/gpy-16" ]]; then
out=$("$PY" "${ROOT}/lib/field-gdb.py" decode "${sg}/Grok16/bin/gpy-16" 2>/dev/null || true); grep -q 'field-gdb-decode/v1'
