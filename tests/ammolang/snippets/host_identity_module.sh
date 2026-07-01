#!/bin/bash
set -euo pipefail
set +o pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_harness.sh
source "${SCRIPT_DIR}/_harness.sh"

# shellcheck source=_harness.sh
# shellcheck source=_harness.sh
  [[ -f "${ROOT}/lib/host-identity.py" ]]
  grep -q 'validate_same_host' "${ROOT}/lib/host-identity.py"
  grep -q 'check_target_online' "${ROOT}/lib/host-identity.py"
  grep -q 'identity_fingerprint' "${ROOT}/lib/host-attack-map.py"
  NEXUS_STATE_DIR="$NEXUS_STATE_DIR" NEXUS_INSTALL_ROOT="$ROOT" \
    "$PY" - <<'PY'
import importlib.util
from pathlib import Path
root = Path(__import__("os").environ["NEXUS_INSTALL_ROOT"])
spec = importlib.util.spec_from_file_location("hi", root / "lib" / "host-identity.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
archived = {
    "ip": "203.0.113.50",
    "identity_hash": "abc",
    "markers": {
        "asn": "as12345 example isp",
        "tls_subject": "cn=target.example.com",
        "ptr_hostname": "target.example.com",
    },
}
live = {
    "ip": "203.0.113.50",
    "asn": "as12345 example isp",
    "tls_subject": "cn=target.example.com",
    "ptr_hostname": "target.example.com",
    "online": True,
}
val = mod.validate_same_host(archived, live)
assert val["same_host"] is True
assert val["required_ip_match"] is True
assert val["score"] >= 40
bad = mod.validate_same_host(archived, {"ip": "203.0.113.51", "asn": "as12345 example isp"})
assert bad["same_host"] is False
assert bad["reason"] == "ip_mismatch"
fp = mod.extract_identity_fingerprint({
    "ip": "203.0.113.50",
    "asn": "AS12345",
    "ptr_hostname": "Target.Example.COM.",
    "target_tls_subject": "CN=Target.Example.com",
})
assert fp["ip"] == "203.0.113.50"
assert fp["markers"]["asn"] == "as12345"
assert fp["markers"]["ptr_hostname"] == "target.example.com"
assert fp["identity_hash"]
priv = mod.check_target_online("127.0.0.1")
assert priv.get("ok") is False
PY
