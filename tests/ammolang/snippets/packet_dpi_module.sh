#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/packet-dpi.py" ]]
  grep -q 'ALERT_MIN_CONFIDENCE' "${ROOT}/lib/packet-dpi.py"
  grep -q 'translate_deep' "${ROOT}/lib/packet-dpi.py"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" - <<'PY'
import importlib.util
from pathlib import Path
root = Path(__import__("os").environ["NEXUS_INSTALL_ROOT"])
spec = importlib.util.spec_from_file_location("dpi", root / "lib" / "packet-dpi.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
pkt = {"direction": "TX", "process": "firefox", "protocol": "tcp", "src_ip": "10.0.0.1", "src_port": 50000, "dst_ip": "1.1.1.1", "dst_port": 443, "length": 200, "flags": "P."}
r = mod.analyze_packet(pkt)
assert not r.get("alert")
assert r.get("verdict") in ("benign_trusted_app", "clean", "low_noise", "sacred_excluded")
PY
