#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/scripts/wire-stack.sh" ]]
  [[ -x "${ROOT}/scripts/wire-stack.sh" ]]
  grep -q 'wire-stack.sh' "${ROOT}/data/sg-canonical.json"
  grep -q 'NewLatest/Grok16' "${ROOT}/data/sg-canonical.json"
  [[ -L "${ROOT}/Grok16" || -d "${ROOT}/Grok16" ]]
  [[ -L "${ROOT}/KILROY" || -d "${ROOT}/KILROY" ]]
  [[ -d "${ROOT}/hostess7-training-viewer" ]]
  NEXUS_INSTALL_ROOT="$ROOT" "$PY" -c "
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('sg_paths', Path('${ROOT}') / 'lib' / 'sg_paths.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.sg_root() == Path('${ROOT}').resolve(), mod.sg_root()
assert mod.grok16_root().name == 'Grok16', mod.grok16_root()
assert mod.kilroy_root().name == 'KILROY', mod.kilroy_root()
"
