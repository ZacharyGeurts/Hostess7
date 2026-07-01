#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/safe-signal-touch.py" ]]
  grep -q 'human_touch' "${ROOT}/lib/connection-gatekeeper.py"
  grep -q 'animals are different' "${ROOT}/lib/safe-signal-touch.py"
  grep -q 'conn-silent-summary' "${ROOT}/panel/threat-panel.html"
  grep -q 'music-touch-badge' "${ROOT}/panel/threat-panel.html"
  grep -q 'traffic-touch-badge' "${ROOT}/panel/threat-panel.html"
  grep -q 'animal-touch-badge' "${ROOT}/panel/threat-panel.html"
  grep -q 'train-touch-badge' "${ROOT}/panel/threat-panel.html"
  grep -q 'Train are different' "${ROOT}/lib/safe-signal-touch.py"
out=$("$PY" "${ROOT}/lib/connection-gatekeeper.py" --stdin <<'EOF' 2>/dev/null || true); grep -q 'touch_policy'
tcp ESTAB 0 0 10.0.0.5:52444 172.217.14.206:443 users:(("firefox",pid=1,fd=3))
EOF
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    aml_py "safe-signal-touch.py" 2>/dev/null || \
    "$PY" -c "
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location('st', '${ROOT}/lib/safe-signal-touch.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
assert m.felt_safe_kind(proc='waze', host='waze.com') == 'traffic'
assert m.felt_safe_kind(proc='amtrak', host='') == 'train'
assert m.lifeform_touch('pet') == 'animal'
print('ok')
"
