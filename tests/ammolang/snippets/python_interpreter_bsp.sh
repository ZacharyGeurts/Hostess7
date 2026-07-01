#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${sg}/Grok16/lib/field_python_interpreter.py" ]]
  grep -q '_resolve_bsp_python' "${ROOT}/Queen/lib/queen-launch-chamber.py"
  grep -q 'interpreter_bsp' "${ROOT}/Queen/lib/queen-launch-chamber.py"
  python3 "${sg}/Grok16/tests/test_field_python_interpreter.py"
  py_chamber="$(mktemp -d)"
  cp "${sg}/Grok16/examples/speed-demo/speed_demo.py" "$py_chamber/main.py"
  GROK16_ROOT="$sg/Grok16" SG_ROOT="$sg" QUEEN_ROOT="$ROOT/Queen" NEXUS_INSTALL_ROOT="$ROOT" \
    QUEEN_LAUNCH_IRON_EXEC=0 "$PY" -c "
import importlib.util, json
from pathlib import Path
spec = importlib.util.spec_from_file_location('ch', Path('${ROOT}/Queen/lib/queen-launch-chamber.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
root = Path('${py_chamber}')
plane = mod.resolve_organized_runner(root, 'main.py', mod.build_manifest(root), {})
assert plane.get('ok'), plane
assert plane.get('toolchain') == 'python_gpy', plane
assert plane.get('interpreter'), plane
print('python_interpreter_bsp_ok')
" | grep -q 'python_interpreter_bsp_ok'
