#!/usr/bin/env pythong
"""IPv4 completely arbitrary worldwide — any pick works; map to device, not numbers."""
from __future__ import annotations

import hashlib
import json
import os
import socket
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-ipv4-arbitrary-doctrine.json"
SOVEREIGN_DOCTRINE = INSTALL / "data" / "field-ipv4-device-sovereign-doctrine.json"
PANEL = STATE / "field-ipv4-arbitrary-panel.json"

UNICAST_MIN = 0x01000000
UNICAST_MAX = 0xDFFFFFFF


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _ip_to_int(ip: str) -> int:
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def _int_to_ip(n: int) -> str:
    return socket.inet_ntoa(struct.pack("!I", n & 0xFFFFFFFF))


def arbitrary_ipv4_enabled() -> bool:
    if os.environ.get("NEXUS_FIELD_IPV4_ARBITRARY", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    sovereign = _load(SOVEREIGN_DOCTRINE, {})
    if (sovereign.get("policy") or {}).get("arbitrary_ipv4_worldwide"):
        return True
    doctrine = _load(DOCTRINE, {})
    return bool((doctrine.get("policy") or {}).get("arbitrary_ipv4_worldwide", True))


def valid_arbitrary_ip(ip: str) -> bool:
    """Any unicast IPv4 the client may pick — worldwide arbitrary."""
    if not ip or ip in ("0.0.0.0", "255.255.255.255"):
        return False
    try:
        n = _ip_to_int(ip)
    except OSError:
        return False
    if n >= 0xE0000000:
        return False
    return True


def mac_to_arbitrary_ip(mac: str) -> str:
    digest = hashlib.sha256(mac.lower().encode()).digest()
    span = UNICAST_MAX - UNICAST_MIN
    n = UNICAST_MIN + (int.from_bytes(digest[:4], "big") % span)
    return _int_to_ip(n)


def resolve_lease_ip(
    mac: str,
    *,
    requested: str | None = None,
    ciaddr: str | None = None,
    dest_ip: str | None = None,
    existing: str | None = None,
) -> str:
    """Honor client pick → renew address → dest IP → stable MAC hash."""
    for candidate in (requested, ciaddr, existing, dest_ip):
        if candidate and valid_arbitrary_ip(candidate):
            return candidate
    return mac_to_arbitrary_ip(mac)


def skip_ping_probe() -> bool:
    if not arbitrary_ipv4_enabled():
        return False
    if os.environ.get("NEXUS_FIELD_DHCP_PING_PROBE", "").strip().lower() in ("1", "true", "yes", "on"):
        return False
    doctrine = _load(DOCTRINE, {})
    return bool((doctrine.get("policy") or {}).get("skip_ping_probe", True))


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    enabled = arbitrary_ipv4_enabled()
    doc = {
        "ok": True,
        "schema": "field-ipv4-arbitrary/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "boss": doctrine.get("boss", "hostess7"),
        "arbitrary_ipv4": enabled,
        "arbitrary_ipv4_worldwide": enabled,
        "it_just_works": enabled,
        "track_devices_not_numbers": True,
        "internet": {
            "anywhere": True,
            "any_pick": enabled,
            "scope": "0.0.0.0/0",
            "dns_bind": "0.0.0.0:53",
            "dhcp_bind": "0.0.0.0:67",
            "note": "Connect anywhere — pick any IPv4, we answer and map to device",
        },
        "lease_policy": {
            "honor_requested_ip": True,
            "honor_ciaddr": True,
            "honor_dest_ip": True,
            "skip_ping_probe": skip_ping_probe(),
            "map_to": "device_information",
        },
        "policy": doctrine.get("policy") or {},
        "api": doctrine.get("api", "/api/field-ipv4-arbitrary"),
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "enabled":
        print(json.dumps({"arbitrary_ipv4": arbitrary_ipv4_enabled()}, ensure_ascii=False))
        return 0
    print(json.dumps({"usage": "field-ipv4-arbitrary.py [json|panel|enabled]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())