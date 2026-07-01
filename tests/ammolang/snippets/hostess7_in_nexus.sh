#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -d "${ROOT}/Hostess7" ]]
  [[ -x "${ROOT}/Hostess7/Hostess7.sh" ]]
  grep -q 'NewLatest/Hostess7' "${ROOT}/data/sg-canonical.json"
  NEXUS_INSTALL_ROOT="$ROOT" "$PY" -c "
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('sg_paths', Path('${ROOT}') / 'lib' / 'sg_paths.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert str(mod.hostess7_root()).endswith('NewLatest/Hostess7'), mod.hostess7_root()
"
