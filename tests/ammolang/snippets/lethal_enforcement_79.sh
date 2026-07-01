#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/lethal-enforcement.py" ]]
  [[ -f "${ROOT}/lib/hostess7-lethal-insight.py" ]]
  [[ -f "${ROOT}/lib/spatial-target-geometry.py" ]]
  [[ -f "${ROOT}/data/lethal-enforcement-policy.json" ]]
  grep -q '/api/lethal-enforcement' "${ROOT}/lib/threat-panel-http.py"
  grep -q '/api/hostess7-lethal-insight' "${ROOT}/lib/threat-panel-http.py"
  grep -q 'lethal-status' "${ROOT}/panel/threat-panel.html"
  grep -q 'kill_tier = "lethal"' "${ROOT}/lib/connection-gatekeeper.py"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    aml_py "spatial-target-geometry.py" classify '{"lat":45.85,"lon":-87.05,"kind":"terror"}' \
    | grep -q 'spatial-target-geometry'
out=$("$PY" "${ROOT}/lib/lethal-enforcement.py" status 2>/dev/null || true); grep -q 'lethal'
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" - <<'PY'
import importlib.util, json
from pathlib import Path
root = Path(__import__("os").environ["NEXUS_INSTALL_ROOT"])
spec = importlib.util.spec_from_file_location("lethal", root / "lib" / "lethal-enforcement.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
heaven = mod.classify_removal({"verdict": "USER_OK", "trust_rank": 1, "remote_ip": "1.2.3.4"})
assert heaven["removal_level"] == "pass", heaven
hell = mod.classify_removal({"verdict": "HARM_CANDIDATE", "hell_chosen": True, "kind": "terror", "remote_ip": "6.6.6.6", "lat": 45.85, "lon": -87.05})
assert hell["removal_level"] in ("lethal", "total_removal", "strike"), hell
print(json.dumps({"heaven": heaven["removal_level"], "hell": hell["removal_level"]}))
PY
