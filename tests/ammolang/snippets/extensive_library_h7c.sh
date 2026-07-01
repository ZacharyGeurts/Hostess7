#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-extensive-library.py" ]]
  [[ -f "${ROOT}/lib/field-h7c-compression.py" ]]
  [[ -f "${ROOT}/lib/field-device-visuals.py" ]]
  [[ -f "${ROOT}/data/field-extensive-library-seed.json" ]]
  [[ -f "${ROOT}/data/field-h7c-doctrine.json" ]]
  [[ -f "${ROOT}/data/field-extensive-library-doctrine.json" ]]
  grep -q '_extensive_library_entries' "${ROOT}/lib/h7-library-bridge.py"
  grep -q '/api/extensive-library' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/h7c' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/device-visuals' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/extensive-library' "${ROOT}/Queen/lib/queen-world.py"
  grep -q 'extensive_library' "${ROOT}/lib/field-panel-parallel.py"
  tmp_state="$(mktemp -d)"
  grep -q 'small_optimizer' "${ROOT}/lib/field-h7c-compression.py"
  grep -q 'build_universal_rapid' "${ROOT}/lib/field-h7c-compression.py"
  grep -q 'universal_rapid' "${ROOT}/data/field-h7c-doctrine.json"
  grep -q 'h7c/2' "${ROOT}/data/field-h7c-doctrine.json"
  grep -q 'lossless' "${ROOT}/data/field-h7c-doctrine.json"
out=$("$PY" "${ROOT}/lib/field-g16-universal-combinatronic.py" publish 2>/dev/null || true); grep -q '"ok": true'
out=$("$PY" "${ROOT}/lib/field-h7c-compression.py" panel 2>/dev/null || true); grep -q 'field-h7c-panel'
out=$("$PY" "${ROOT}/lib/field-h7c-compression.py" panel 2>/dev/null || true); grep -q 'universal_rapid'
out=$("$PY" "${ROOT}/lib/field-h7c-compression.py" verify 2>/dev/null || true); grep -q '"lossless": true'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    "$PY" -c "
import importlib.util, json, os
from pathlib import Path
root = Path('${ROOT}')
state = Path('${tmp_state}')
spec = importlib.util.spec_from_file_location('h7c', root / 'lib/field-h7c-compression.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
text = '# Universal rapid\\n\\nProse band.\\n\`\`\`py\\nprint(42)\\n\`\`\`\\n'
packed = mod.pack_h7c(text, {'test': 'universal_rapid'})
header, out, stats = mod.decompress_h7c(packed, verify=True)
assert out == text, 'lossless roundtrip'
assert header.get('universal_rapid'), 'header universal_rapid'
assert stats.get('universal_rapid', {}).get('present'), 'stats universal present'
print(json.dumps({'ok': True, 'universal_rapid': header.get('universal_rapid')}))
" | grep -q '"ok": true'
out=$("$PY" "${ROOT}/lib/field-h7c-compression.py" optimize "${ROOT}/data/field-h7c-doctrine.json" 2>/dev/null || true); grep -q 'h7c-small-optimizer'
out=$("$PY" "${ROOT}/lib/field-extensive-library.py" verify 2>/dev/null || true); grep -q '"ok": true'
out=$("$PY" "${ROOT}/lib/field-extensive-library.py" search mario 2>/dev/null || true); grep -q '"hits"'
out=$("$PY" "${ROOT}/lib/field-device-visuals.py" generate 2>/dev/null || true); grep -q 'field-device-visuals-panel'
out=$("$PY" "${ROOT}/lib/field-extensive-library.py" build 2>/dev/null || true); grep -q '"ok": true'
