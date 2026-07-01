#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/library/dewey/355-military-science/future_war/future_war.h7c" ]]
  [[ -f "${ROOT}/library/dewey/355-military-science/future_war/future_war.md" ]]
  grep -q 'format_v4' "${ROOT}/data/field-h7c-doctrine.json"
  grep -q 'wrap_h7c_block' "${ROOT}/lib/field-h7c-compression.py"
  grep -q 'field-layer-sweep' "${ROOT}/lib/field-h7-corpus-sync.py"
  [[ -f "${ROOT}/lib/field-layer-sweep.py" ]]
  tmp_state="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    aml_py "field-h7c-compression.py" unpack \
    "${ROOT}/library/dewey/355-military-science/future_war/future_war.h7c" | grep -q '"block_wrapper": true'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    "$PY" -c "
from pathlib import Path
import importlib.util, sys
root = Path('${ROOT}')
spec = importlib.util.spec_from_file_location('h7c', root / 'lib/field-h7c-compression.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
raw = (root / 'library/dewey/355-military-science/future_war/future_war.md').read_text(encoding='utf-8')
blob = (root / 'library/dewey/355-military-science/future_war/future_war.h7c').read_bytes()
_, text, stats = mod.decompress_h7c(blob, verify=True)
assert text == raw
assert stats.get('field_layer') == 1
print('ok')
"
  ! grep -rq '"layer": 0' "${ROOT}/data/field-combinatronic-spider-wire-doctrine.json" \
    "${ROOT}/data/field-chips-iron-steel-plate-doctrine.json" 2>/dev/null
