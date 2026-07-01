#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/packet-field.py" ]]
  grep -q 'nexus_packet_field_capture' "${ROOT}/lib/packet-oracle.sh"
  grep -q 'packet_field' "${ROOT}/lib/threat-panel.sh"
  grep -q 'renderPacketField' "${ROOT}/panel/threat-panel.html"
  grep -q 'packet-field-wrap' "${ROOT}/panel/threat-panel.html"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    aml_py "packet-field.py" parse-line \
    "1748012345.123456 IP 127.0.0.1.54321 > 104.18.29.234.443: Flags [P.], seq 1, ack 1, win 512, length 100" \
    | grep -q '"direction": "TX"'
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    aml_py "packet-field.py" parse-line \
    "1748012345.123456 IP 104.18.29.234.443 > 127.0.0.1.54321: Flags [P.], seq 1, ack 1, win 512, length 200" \
    | grep -q '"direction": "RX"'
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" - <<'PY'
import importlib.util
from pathlib import Path
root = Path(__import__("os").environ["NEXUS_INSTALL_ROOT"])
spec = importlib.util.spec_from_file_location("pf", root / "lib" / "packet-field.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
assert mod._port_service(443) == "HTTPS"
assert "TX" in mod._english_summary({"direction": "TX", "process": "firefox", "protocol": "tcp", "src_port": 54321, "dst_ip": "1.2.3.4", "dst_port": 443, "port_service": "HTTPS", "length": 100, "flags": "P."})
= {"10.0.0.1"}
assert mod._classify_direction("10.0.0.1", "8.8.8.8", local, "Out") == "TX"
assert mod._classify_direction("8.8.8.8", "10.0.0.1", local, "In") == "RX"
line = "1782249257.017925 enp10s0 Out IP 10.0.0.1.36444 > 1.1.1.1.443: Flags [.], ack 1, win 566, length 0"
rec = mod.parse_tcpdump_line(line, local, {})
assert rec and rec["direction"] == "TX"
PY
