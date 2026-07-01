#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-h7c-correct.py" ]]
  grep -q '"corrects"' "${ROOT}/data/field-h7c-doctrine.json"
  mkdir -p "${ROOT}/.nexus-state"
  tmp_state="$(mktemp -d)"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    aml_py "field-h7c-correct.py" one \
    "${ROOT}/library/dewey/700-arts/games/nes/nes_contra/nes_contra.h7c" --apply | grep -q '"ok": true'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    "$PY" -c "
import importlib.util
from pathlib import Path
root = Path('${ROOT}')
spec = importlib.util.spec_from_file_location('h7c', root / 'lib/field-h7c-compression.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
blob = (root / 'library/dewey/700-arts/games/nes/nes_contra/nes_contra.h7c').read_bytes()
_, text, stats = mod.decompress_h7c(blob, verify=True)
assert stats.get('block_wrapper') is True
if '## Corrects' in text:
    assert 'H7c/4' in text or 'ironclad block' in text.lower()
print('ok')
"
