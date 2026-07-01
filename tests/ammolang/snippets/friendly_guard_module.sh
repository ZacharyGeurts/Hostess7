#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/friendly-guard.py" ]]
  [[ -f "${ROOT}/lib/friendly-guard.sh" ]]
  grep -q 'IMMUTABLE' "${ROOT}/lib/friendly-guard.py"
  grep -q 'KILL_REFUSED_IMMUTABLE' "${ROOT}/lib/friendly-guard.sh"
  grep -q 'nexus_friendly_guard_refuse_kill' "${ROOT}/lib/field-attack-kit.sh"
out=$("$PY" "${ROOT}/lib/friendly-guard.py" check 127.0.0.1 2>/dev/null || true); grep -q '"refuse": true'
out=$("$PY" "${ROOT}/lib/friendly-guard.py" check 185.199.108.153 2>/dev/null || true); grep -q '"refuse": false'
  grep -q '|| true' "${ROOT}/lib/friendly-guard.sh"
  nexus_friendly_guard_refuse_kill "147.93.191.75" && exit 1 || true
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" - <<'PY'
import importlib.util
from pathlib import Path
root = Path(__import__("os").environ["NEXUS_INSTALL_ROOT"])
spec = importlib.util.spec_from_file_location("fg", root / "lib" / "friendly-guard.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
refuse, reason = mod.refuse_kill("8.8.8.8")
assert refuse and reason == "sacred_infrastructure"
refuse, reason = mod.refuse_kill("185.199.108.155", {"verdict": "USER_OK", "trust_rank": 0})
assert refuse and reason.startswith("friendly")
refuse, _ = mod.refuse_kill("185.199.108.154", {"verdict": "HARM_CANDIDATE", "trust_rank": 4})
assert not refuse
PY
