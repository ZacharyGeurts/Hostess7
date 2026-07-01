#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/target-bleed.py" ]]
  grep -q 'host_endpoint_context' "${ROOT}/lib/target-bleed.py"
  grep -q 'bleed_target' "${ROOT}/lib/target-bleed.py"
  grep -q 'target_bleed' "${ROOT}/lib/host-attack-map.py"
  grep -q 'target_os' "${ROOT}/lib/host-attack-map.py"
out=$("$PY" "${ROOT}/lib/target-bleed.py" bleed 127.0.0.1 2>/dev/null 2>/dev/null || true); grep -q '"skipped": "private"'
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" - <<'PY'
import importlib.util
from pathlib import Path
root = Path(__import__("os").environ["NEXUS_INSTALL_ROOT"])
spec = importlib.util.spec_from_file_location("tb", root / "lib" / "target-bleed.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
hc = mod.host_endpoint_context()
assert hc.get("os")
assert hc.get("hostname")
guess = mod.ttl_os_guess("127.0.0.1")
assert guess.get("skipped") == "private"
PY
