#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/signals-field.py" ]]
  [[ -f "${ROOT}/lib/fcc-signal-lookup.py" ]]
  grep -q 'signals_field' "${ROOT}/lib/threat-panel.sh"
  grep -q '/api/signals-field' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'view-signals' "${ROOT}/panel/threat-panel.html"
  grep -q 'frequency_registry' "${ROOT}/lib/signals-field.py"
  grep -q '_build_frequency_registry' "${ROOT}/lib/field-rf-sentinel.py"
  grep -q 'signals-freq-registry' "${ROOT}/panel/threat-panel.html"
  grep -q 'drawRipplingFieldSheet' "${ROOT}/panel/assets/signals-field.js"
out=$("$PY" "${ROOT}/lib/signals-field.py" json 2>/dev/null || true); grep -q 'signals-field/v1'
out=$("$PY" "${ROOT}/lib/signals-field.py" json 2>/dev/null || true); grep -q 'frequency_registry'
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" -c "
import importlib.util, os, json
from pathlib import Path
ROOT = Path('${ROOT}')
spec = importlib.util.spec_from_file_location('rf', ROOT / 'lib' / 'field-rf-sentinel.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
reg = mod._build_frequency_registry([])
assert reg.get('schema') == 'frequency-registry/v1'
assert reg.get('total_slots', 0) > 0
assert reg.get('silent_slots') == reg.get('total_slots')
reg2 = mod._build_frequency_registry([{'channel': 6, 'freq_mhz': '2437', 'band': '2.4GHz', 'signal_dbm': 72, 'ssid': 'test', 'bssid': 'aa:bb:cc:dd:ee:ff'}])
assert reg2.get('recognized_slots', 0) >= 1
"
