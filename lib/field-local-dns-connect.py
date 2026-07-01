#!/usr/bin/env pythong
"""AmmoOS local DNS/DHCP connect — steer to our Truth Resolver and Field DHCP when they start."""
from __future__ import annotations

import json
import os
import socket
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SCHEMA = "field-local-dns-connect/v1"
CONNECT_STATE = STATE / "field-local-dns-connect.json"
RESOLV_STUB = STATE / "resolv.conf.nexus-stub"
DNS_IPV4 = os.environ.get("NEXUS_FIELD_DNS_IPV4", "127.0.0.1")
DNS_IPV6 = os.environ.get("NEXUS_FIELD_DNS_IPV6", "::1")
DNS_PORT = int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53") or "53")


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _pid_alive(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        pid = int(path.read_text(encoding="utf-8").strip().split()[0])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _dns_running() -> bool:
    return _pid_alive(STATE / "field-dns.pid")


def _dhcp_running() -> bool:
    return _pid_alive(STATE / "field-dhcp.pid")


def _encode_name(name: str) -> bytes:
    out = bytearray()
    for label in name.rstrip(".").split("."):
        raw = label.encode("ascii")[:63]
        out.append(len(raw))
        out.extend(raw)
    out.append(0)
    return bytes(out)


def _dns_probe(host: str = DNS_IPV4, qname: str = "example.com") -> bool:
    txn = struct.pack("!H", int(time.time()) & 0xFFFF)
    header = txn + struct.pack("!HHHHH", 0x0100, 1, 0, 0, 0)
    packet = header + _encode_name(qname) + struct.pack("!HH", 1, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    try:
        sock.sendto(packet, (host, DNS_PORT))
        data, _ = sock.recvfrom(4096)
        return len(data) >= 12
    except OSError:
        return False
    finally:
        sock.close()


def _primary_iface() -> str:
    try:
        proc = subprocess.run(
            ["ip", "-4", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        for line in (proc.stdout or "").splitlines():
            parts = line.split()
            if "dev" in parts:
                return parts[parts.index("dev") + 1]
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    return os.environ.get("NEXUS_FIELD_DHCP_BIND_IF", "")


def _local_mac(iface: str) -> str:
    if not iface:
        return ""
    path = Path(f"/sys/class/net/{iface}/address")
    try:
        return path.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return ""


def _dhcp_lease_for_mac(mac: str) -> dict[str, Any] | None:
    if not mac:
        return None
    leases = _load_json(STATE / "field-dhcp-leases.json", {"leases": {}})
    entry = (leases.get("leases") or {}).get(mac)
    return entry if isinstance(entry, dict) else None


def _write_resolv_stub() -> Path:
    port = DNS_PORT
    text = (
        "# AmmoOS Truth DNS — local connect (RFC 1035)\n"
        "# Steer all resolver traffic to our loopback Truth Resolver\n"
        f"nameserver {DNS_IPV4}\n"
        f"nameserver {DNS_IPV6}\n"
        "options edns0 trust-ad single-request-reopen\n"
        f"# NEXUS_FIELD_DNS_PORT={port}\n"
        "# NEXUS_FIELD_LOCAL_DNS_CONNECT=1\n"
    )
    RESOLV_STUB.write_text(text, encoding="utf-8")
    return RESOLV_STUB


def _enforce_system_resolv() -> bool:
    sh = INSTALL / "lib" / "field-dns.sh"
    if not sh.is_file():
        return False
    try:
        proc = subprocess.run(
            ["bash", "-c", f'source "{sh}" && nexus_field_dns_enforce_resolv'],
            capture_output=True,
            text=True,
            timeout=12,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _request_dhcp(iface: str) -> dict[str, Any]:
    if not iface:
        return {"ok": False, "skipped": True, "reason": "no_iface"}
    for cmd in (
        ["dhclient", "-1", "-v", iface],
        ["dhcpcd", "-n", iface],
    ):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if proc.returncode == 0:
                return {"ok": True, "method": cmd[0], "iface": iface}
        except (OSError, subprocess.TimeoutExpired):
            continue
    return {"ok": False, "iface": iface, "reason": "no_dhcp_client"}


def connect(*, persist: bool = True) -> dict[str, Any]:
    dns_up = _dns_running()
    dhcp_up = _dhcp_running()
    dns_healthy = dns_up and _dns_probe()
    iface = _primary_iface()
    mac = _local_mac(iface)
    lease = _dhcp_lease_for_mac(mac) if dhcp_up else None

    dns_connected = False
    dhcp_connected = False
    resolv_path = ""
    system_resolv = False

    if dns_up and (dns_healthy or os.environ.get("NEXUS_FIELD_DNS_CONNECT_WITHOUT_PROBE", "0") == "1"):
        stub = _write_resolv_stub()
        resolv_path = str(stub)
        dns_connected = True
        if os.environ.get("NEXUS_FIELD_DNS_ENFORCE_RESOLV", "1") == "1":
            system_resolv = _enforce_system_resolv()

    dhcp_result: dict[str, Any] = {"ok": False, "skipped": True}
    if dhcp_up:
        if lease:
            dhcp_connected = True
            dhcp_result = {"ok": True, "method": "lease_table", "ip": lease.get("ip"), "iface": iface}
        elif iface and os.environ.get("NEXUS_FIELD_DHCP_CLIENT_CONNECT", "1") == "1":
            dhcp_result = _request_dhcp(iface)
            dhcp_connected = bool(dhcp_result.get("ok"))

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "ok": dns_connected or dhcp_connected,
        "ts": _now(),
        "motto": "Use our local Truth DNS and Field DHCP — connect when either starts.",
        "dns": {
            "running": dns_up,
            "healthy": dns_healthy,
            "connected": dns_connected,
            "resolver": DNS_IPV4,
            "port": DNS_PORT,
            "resolv_stub": resolv_path,
            "system_resolv_enforced": system_resolv,
        },
        "dhcp": {
            "running": dhcp_up,
            "connected": dhcp_connected,
            "iface": iface or None,
            "mac": mac or None,
            "lease": lease,
            "client": dhcp_result,
        },
        "env_hint": {
            "RESOLV_CONF": resolv_path,
            "NEXUS_FIELD_DNS_IPV4": DNS_IPV4,
        },
    }
    if persist:
        _save_json(CONNECT_STATE, doc)
    return doc


def posture() -> dict[str, Any]:
    cached = _load_json(CONNECT_STATE, {})
    live = connect(persist=False)
    if cached.get("ts"):
        live["last_connect"] = cached
    return live


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "connect":
        print(json.dumps(connect(), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-local-dns-connect.py [json|connect]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())