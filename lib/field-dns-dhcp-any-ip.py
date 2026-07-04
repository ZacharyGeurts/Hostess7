#!/usr/bin/env pythong
"""Answer DNS and DHCP on any IP — wildcard bind + enumerate every local address."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-dns-dhcp-any-ip-doctrine.json"
PANEL = STATE / "field-dns-dhcp-any-ip-panel.json"

WILDCARD_V4 = "0.0.0.0"
WILDCARD_V6 = "::"
QUEEN = os.environ.get("NEXUS_QUEEN_LAN_DNS", os.environ.get("NEXUS_FIELD_DHCP_BIND", "192.168.47.1"))
SOVEREIGN_DOCTRINE = INSTALL / "data" / "field-ipv4-device-sovereign-doctrine.json"


def _device_sovereign_mode() -> bool:
    if os.environ.get("NEXUS_FIELD_IPV4_DEVICE_SOVEREIGN", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    try:
        doctrine = json.loads(SOVEREIGN_DOCTRINE.read_text(encoding="utf-8"))
        return bool((doctrine.get("policy") or {}).get("track_devices_not_numbers", True))
    except (OSError, json.JSONDecodeError):
        return True


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _enabled(flag: str, default: str = "1") -> bool:
    return os.environ.get(flag, default).strip().lower() not in ("0", "false", "no", "off")


def _run_ip(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["ip", *args],
            capture_output=True,
            text=True,
            timeout=4,
            errors="replace",
        )
        return proc.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def enumerate_local_ipv4() -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for line in _run_ip(["-4", "addr", "show"]).splitlines():
        m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/", line)
        if not m:
            continue
        ip = m.group(1)
        if ip not in seen:
            seen.add(ip)
            rows.append(ip)
    if WILDCARD_V4 not in seen:
        rows.insert(0, WILDCARD_V4)
    return rows


def enumerate_local_ipv6() -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for line in _run_ip(["-6", "addr", "show"]).splitlines():
        m = re.search(r"inet6 ([0-9a-f:]+)/", line, re.I)
        if not m:
            continue
        ip = m.group(1).split("%")[0]
        if ip == "::1" or ip.startswith("fe80:"):
            pass
        if ip not in seen:
            seen.add(ip)
            rows.append(ip)
    if "::1" not in seen:
        rows.append("::1")
    if WILDCARD_V6 not in seen:
        rows.insert(0, WILDCARD_V6)
    return rows


def dns_bind_hosts_v4() -> list[str]:
    if not _enabled("NEXUS_FIELD_DNS_ANY_IP"):
        raw = os.environ.get("NEXUS_FIELD_DNS_BINDS_IPV4", "127.0.0.1")
        return [h.strip() for h in raw.split(",") if h.strip()] or ["127.0.0.1"]
    # Wildcard — answers DNS queries sent to any local IPv4 address.
    return [WILDCARD_V4]


def dns_bind_hosts_v6() -> list[str]:
    if not _enabled("NEXUS_FIELD_DNS_ANY_IP"):
        raw = os.environ.get("NEXUS_FIELD_DNS_BINDS_IPV6", "::1")
        return [h.strip() for h in raw.split(",") if h.strip()] or ["::1"]
    return [WILDCARD_V6]


def dhcp_bind_host() -> str:
    if _enabled("NEXUS_FIELD_DHCP_ANY_IP"):
        return WILDCARD_V4
    raw = os.environ.get("NEXUS_FIELD_DHCP_BIND", "").strip()
    if raw:
        return raw
    return QUEEN if QUEEN in enumerate_local_ipv4() else WILDCARD_V4


def dhcp_server_id(fallback: str | None = None) -> str:
    """Server identifier for DHCP option 54 — prefer Queen LAN, else fallback."""
    fb = fallback or dhcp_bind_host()
    if fb == WILDCARD_V4:
        return QUEEN if QUEEN in enumerate_local_ipv4() else "127.0.0.1"
    return fb


def answer_points(*, device_sovereign: bool | None = None) -> list[dict[str, Any]]:
    sovereign = _device_sovereign_mode() if device_sovereign is None else device_sovereign
    if sovereign:
        return [
            {
                "address": WILDCARD_V4,
                "family": "ipv4",
                "dns": True,
                "dhcp": True,
                "wildcard": True,
                "device_mapped": True,
                "note": "All IPv4 on box — map to device information, not numbers",
            },
            {
                "address": WILDCARD_V6,
                "family": "ipv6",
                "dns": True,
                "dhcp": False,
                "wildcard": True,
                "device_mapped": True,
                "note": "DNS wildcard — device authority primary",
            },
        ]
    points: list[dict[str, Any]] = []
    for ip in enumerate_local_ipv4():
        if ip == WILDCARD_V4:
            points.append({
                "address": ip,
                "family": "ipv4",
                "dns": True,
                "dhcp": True,
                "wildcard": True,
                "note": "Answers DNS/DHCP on every IPv4 assigned to this host",
            })
        else:
            points.append({
                "address": ip,
                "family": "ipv4",
                "dns": True,
                "dhcp": True,
                "wildcard": False,
            })
    for ip in enumerate_local_ipv6():
        if ip == WILDCARD_V6:
            points.append({
                "address": ip,
                "family": "ipv6",
                "dns": True,
                "dhcp": False,
                "wildcard": True,
                "note": "Answers DNS on every IPv6 assigned to this host",
            })
        else:
            points.append({
                "address": ip,
                "family": "ipv6",
                "dns": True,
                "dhcp": False,
                "wildcard": False,
            })
    return points


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = {}
    try:
        doctrine = json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    sovereign = _device_sovereign_mode()
    v4 = enumerate_local_ipv4()
    v6 = enumerate_local_ipv6()
    points = answer_points(device_sovereign=sovereign)
    enum_panel: dict[str, Any] = {}
    try:
        enum_py = INSTALL / "lib" / "field-ipv4-enumerate.py"
        if enum_py.is_file():
            proc = subprocess.run(
                [sys.executable, str(enum_py), "json"],
                cwd=str(INSTALL),
                capture_output=True,
                text=True,
                timeout=12,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            raw = (proc.stdout or "").strip()
            if raw.startswith("{"):
                enum_panel = json.loads(raw)
    except Exception:
        enum_panel = {}
    enum_counts = enum_panel.get("counts") or {}
    enumerate_all = bool(enum_panel.get("enumerate_addresses") or enum_counts.get("ipv4_enumerated_total"))
    doc = {
        "ok": True,
        "schema": "field-dns-dhcp-any-ip/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "any_ip": True,
        "answer_any_ip": True,
        "device_sovereign": sovereign,
        "track_devices_not_numbers": sovereign,
        "arbitrary_ipv4_worldwide": sovereign,
        "it_just_works": sovereign,
        "dns": {
            "binds_v4": dns_bind_hosts_v4(),
            "binds_v6": dns_bind_hosts_v6(),
            "wildcard_v4": WILDCARD_V4,
            "wildcard_v6": WILDCARD_V6,
            "port": int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53")),
        },
        "dhcp": {
            "bind": dhcp_bind_host(),
            "server_id": dhcp_server_id(),
            "port": 67,
            "wildcard": dhcp_bind_host() == WILDCARD_V4,
        },
        "local_ipv4": v4,
        "local_ipv6": [] if sovereign else [ip for ip in v6 if ip not in (WILDCARD_V6,)],
        "enumerate_addresses": enumerate_all or not sovereign,
        "ipv4_enumeration": {
            "enabled": enumerate_all,
            "owned_total": enum_counts.get("ipv4_owned_total"),
            "enumerated_total": enum_counts.get("ipv4_enumerated_total"),
            "local_enumerated": enum_counts.get("local_ipv4_enumerated"),
            "scope": "0.0.0.0/0",
        },
        "map_to": "device_information" if sovereign else "local_addresses",
        "answer_points": points,
        "answer_point_count": len(points),
        "policy": doctrine.get("policy") or {},
        "api": doctrine.get("api", "/api/field-dns-dhcp-any-ip"),
    }
    if write:
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        tmp = PANEL.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dns-binds":
        print(json.dumps({
            "v4": dns_bind_hosts_v4(),
            "v6": dns_bind_hosts_v6(),
        }, ensure_ascii=False))
        return 0
    if cmd == "dhcp-bind":
        print(json.dumps({"bind": dhcp_bind_host(), "server_id": dhcp_server_id()}, ensure_ascii=False))
        return 0
    print(json.dumps({"usage": "field-dns-dhcp-any-ip.py [json|panel|dns-binds|dhcp-bind]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())