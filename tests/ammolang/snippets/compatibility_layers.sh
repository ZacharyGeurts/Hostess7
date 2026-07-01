#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/field-compatibility-layers.py" ]]
  [[ -f "${ROOT}/data/field-compatibility-layers-doctrine.json" ]]
  [[ -f "${ROOT}/panel/compatibility-layers.html" ]]
  [[ -f "${ROOT}/panel/assets/compatibility-layers.js" ]]
  grep -q '/api/compatibility' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'compatibility_layers' "${ROOT}/lib/field-panel-parallel.py"
  grep -q 'compatibility-layers-card' "${ROOT}/panel/threat-panel.html"
  grep -q 'nexus-compatibility' "${ROOT}/data/field-host-desktop-doctrine.json"
  grep -q 'nexus_c2_tree' "${ROOT}/data/field-host-desktop-doctrine.json"
  grep -q 'nexus-calc' "${ROOT}/data/field-host-desktop-doctrine.json"
  grep -q 'startbar_auto_hide_default": false' "${ROOT}/data/field-host-desktop-doctrine.json"
  [[ -f "${ROOT}/panel/nexus-calc.html" ]]
  [[ -f "${ROOT}/panel/nexus-calendar.html" ]]
  grep -q 'nexus-calc' "${ROOT}/lib/threat-panel-http.py"
  grep -q '_refresh_compatibility_layers' "${ROOT}/lib/field-plate-meld.py"
  tmp_state="$(mktemp -d)"
out=$("$PY" "${ROOT}/lib/field-compatibility-layers.py" json 2>/dev/null || true); grep -q 'field-compatibility-layers/v1'
out=$("$PY" "${ROOT}/lib/field-compatibility-layers.py" stack 2>/dev/null || true); grep -q '"layers"'
  grep -q 'launch_seal_state' "${ROOT}/Queen/lib/queen-launch-chamber.py"
  grep -q 'launch_refresh_allowed' "${ROOT}/Queen/lib/queen-launch-chamber.py"
  grep -q 'launch_seal_generation' "${ROOT}/Queen/lib/queen-file-browser.py"
  grep -q 'fast_cycle' "${SG_ROOT:-$(cd "${ROOT}/.." && pwd)}/Grok16/lib/field_combinatorics.py"
  grep -q 'fast_cycle_default' "${ROOT}/data/field-compatibility-layers-doctrine.json"
  grep -q 'engine_fingerprint' "${sg}/Grok16/lib/field_combinatorics.py"
  grep -q 'combinatorics_engine_lock' "${ROOT}/data/field-compatibility-layers-doctrine.json"
  grep -q 'reject_attempt' "${sg}/Grok16/lib/field_combinatorics.py"
  grep -q 'operator_running' "${sg}/Grok16/lib/field_combinatorics.py"
  grep -q 'combinatorics_never_update_on_running_operator' "${ROOT}/data/field-compatibility-layers-doctrine.json"
  grep -q 'combinatorics_never_break_on_mismatch' "${ROOT}/data/field-compatibility-layers-doctrine.json"
  grep -q '/api/combinatorics-threat' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/combinatorics/comb' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/combinatorics/brain-try' "${ROOT}/lib/threat-panel-http.py"
  [[ -f "${ROOT}/lib/field-combinatorics-comb.py" ]]
out=$("$PY" "${ROOT}/lib/field-compatibility-layers.py" refresh 2>/dev/null || true); grep -q 'launch_seal_generation'
  chamber="$(mktemp -d)"
  echo 'print("ok")' > "$chamber/main.py"
  NEXUS_INSTALL_ROOT="$ROOT" NEXUS_STATE_DIR="$tmp_state" QUEEN_ROOT="$ROOT/Queen" \
    "$PY" -c "
import importlib.util, json, sys
from pathlib import Path
p = Path('${ROOT}/Queen/lib/queen-launch-chamber.py')
spec = importlib.util.spec_from_file_location('ch', p)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
root = Path('${chamber}')
first = mod.write_launch_file(root)
assert first.get('ok') and first.get('secured'), first
second = mod.write_launch_file(root, refresh=False)
assert second.get('error') == 'launch_locked', second
seal = int(json.loads(open('${tmp_state}/field-compatibility-layers-panel.json').read()).get('launch_seal',{}).get('generation',1))
bad = mod.write_launch_file(root, refresh=True, seal_generation=0)
assert bad.get('error') == 'launch_seal_stale_sync_compatibility_layers_first', bad
good = mod.write_launch_file(root, refresh=True, seal_generation=seal)
assert good.get('ok') and good.get('refreshed'), good
print('launch_seal_ok')
" | grep -q 'launch_seal_ok'
