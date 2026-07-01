#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-dewey-library.py" ]]
  [[ -f "${ROOT}/data/field-dewey-library-doctrine.json" ]]
  grep -q 'glob_books' "${ROOT}/lib/h7-library-bridge.py"
  grep -q 'field-dewey-library' "${ROOT}/lib/h7-library-bridge.py"
  grep -q 'ensure_h7c_path' "${ROOT}/lib/field-dewey-library.py"
  grep -q 'auto_convert_on_open' "${ROOT}/data/field-dewey-library-doctrine.json"
  grep -q 'open_h7_path' "${ROOT}/lib/field-h7c-compression.py"
  grep -q 'maybe_rebalance_on_open' "${ROOT}/lib/field-h7c-compression.py"
  grep -q 'benchmark_neural_pipeline' "${ROOT}/lib/field-h7c-compression.py"
  grep -q 'steel_neural_plates' "${ROOT}/data/field-h7c-doctrine.json"
  grep -q '/api/dewey-library' "${ROOT}/lib/threat-panel-http.py"
  grep -q '_pack_entry_h7c' "${ROOT}/lib/field-extensive-library.py"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-dewey-library.py" migrate 2>/dev/null || true); grep -q '"ok": true'
out=$("$PY" "${ROOT}/lib/field-dewey-library.py" tree 2>/dev/null || true); grep -q 'field-dewey-library-tree'
out=$("$PY" "${ROOT}/lib/field-dewey-library.py" verify 2>/dev/null || true); grep -q '"ok": true'
  [[ ! -f "${ROOT}/library/dewey/004-computers/nes/nes.h7" ]]
  [[ -f "${ROOT}/library/dewey/004-computers/nes/nes.h7c" ]]
  tmp_h7_dir="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" \
    "$PY" -c "
import importlib.util, json, sys
from pathlib import Path
sg = Path('${sg}')
root = Path('${ROOT}')
tmp = Path('${tmp_h7_dir}')
sys.path.insert(0, str(sg / 'Hostess7/scripts'))
from field_h7_book import write_h7
h7 = tmp / 'auto_convert_test.h7'
write_h7(h7, '# Auto convert on open\\n', {'id': 'auto_convert_test', 'title': 'Auto Convert Test'})
assert h7.is_file(), 'fixture h7 missing'
spec = importlib.util.spec_from_file_location('dewey', root / 'lib/field-dewey-library.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
out = mod.ensure_h7c_path(h7)
assert out.suffix == '.h7c' and out.is_file(), 'h7c not created'
assert not h7.is_file(), 'legacy h7 still on disk'
header, text, stats = mod._h7c_mod().decompress_h7c(out.read_bytes(), verify=True)
assert 'Auto convert' in text, 'lossless text'
print(json.dumps({'ok': True, 'converted': True, 'chars': len(text)}))
" | grep -q '"converted": true'
  h7_open="${tmp_h7_dir}/open_cli_test.h7"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" SG_ROOT="$sg" \
    "$PY" -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path('${sg}') / 'Hostess7/scripts'))
from field_h7_book import write_h7
write_h7(Path('${h7_open}'), '# Open CLI\\n', {'id': 'open_cli_test', 'title': 'Open CLI'})
"
out=$("$PY" "${ROOT}/lib/field-dewey-library.py" open "${h7_open}" 2>/dev/null || true); grep -q '"converted": true'
  [[ ! -f "${h7_open}" ]]
  [[ -f "${tmp_h7_dir}/open_cli_test.h7c" ]]
  rm -rf "${tmp_h7_dir}"
