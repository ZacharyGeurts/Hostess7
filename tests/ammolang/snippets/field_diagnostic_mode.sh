#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-diagnostic-mode.py" ]]
  [[ -f "${ROOT}/data/field-diagnostic-mode-doctrine.json" ]]
  grep -q 'field_diagnostic' "${ROOT}/lib/field-panel-parallel.py"
  grep -q '/api/diagnostic-mode' "${ROOT}/lib/threat-panel-http.py"
  grep -q '_refresh_if_allowed' "${ROOT}/lib/field-plate-meld.py"
  grep -q 'diagnostic-mode-card' "${ROOT}/panel/threat-panel.html"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-diagnostic-mode.py" json 2>/dev/null || true); grep -q 'field-diagnostic-mode/v1'
out=$("$PY" "${ROOT}/lib/field-diagnostic-mode.py" detect 2>/dev/null || true); grep -q 'fault_count'
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" \
    "$PY" -c "
import importlib.util, json
from pathlib import Path
p = Path('${ROOT}/lib/field-diagnostic-mode.py')
spec = importlib.util.spec_from_file_location('diag', p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod.slice_allowed('gatekeeper') or not mod.active()
assert mod.refresh_allowed('g1id_baselines') or not mod.active()
locked = mod.filter_field_slices({'gatekeeper': ('x', []), 'field_command': ('y', [])})
assert 'field_command' not in locked or not mod.active()
print('diagnostic_filter_ok')
" | grep -q 'diagnostic_filter_ok'
  echo '{"ok":false,"required_ok":false}' > "$tmp_state/g1id-baseline-panel.json"
out=$("$PY" "${ROOT}/lib/field-diagnostic-mode.py" engage 2>/dev/null || true); grep -q '"engaged": true'
out=$("$PY" "${ROOT}/lib/field-diagnostic-mode.py" json 2>/dev/null || true); grep -q 'locked_slices'
