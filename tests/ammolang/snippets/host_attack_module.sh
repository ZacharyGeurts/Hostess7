#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/host-attack-map.py" ]]
  [[ -f "${ROOT}/lib/host-attack.sh" ]]
  grep -q 'nexus_host_attacks_panel_json' "${ROOT}/lib/host-attack.sh"
  grep -q 'host_attacks' "${ROOT}/lib/threat-panel.sh"
  grep -q '_clamp_coords' "${ROOT}/lib/host-attack-map.py"
  grep -q '_monitor_snapshot' "${ROOT}/lib/host-attack-map.py"
  grep -q 'is_monitor_target' "${ROOT}/lib/host-attack-map.py"
  grep -q 'globe_pin' "${ROOT}/lib/host-attack-map.py"
  grep -q 'return None' "${ROOT}/lib/host-attack-map.py"
out=$("$PY" "${ROOT}/lib/host-attack-map.py" build-fast 2>/dev/null || true); grep -q 'point_count'
out=$("$PY" "${ROOT}/lib/host-attack-map.py" json-panel 2>/dev/null || true); grep -q 'points'
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" - <<'PY'
import importlib.util
from pathlib import Path
root = Path(__import__("os").environ["NEXUS_INSTALL_ROOT"])
spec = importlib.util.spec_from_file_location("ham", root / "lib" / "host-attack-map.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod._clamp_coords(40.7, -74.0) == (40.7, -74.0)
assert mod._clamp_coords(0, 200) == (0.0, -160.0)
assert mod._clamp_coords("bad", 10) is None
assert mod._resolve_coords("1.2.3.4", {"lat": 51.5, "lon": -0.1}) == (51.5, -0.1, "GeoIP")
assert mod._resolve_coords("1.2.3.4", {"country_code": "US"}) is not None
assert mod._resolve_coords("1.2.3.4", {}) is None
PY
