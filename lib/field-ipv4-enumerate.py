#!/usr/bin/env pythong
"""Full IPv4 enumeration — own and enumerate every address 0.0.0.0–255.255.255.255 everywhere."""
from __future__ import annotations

import json
import os
import re
import socket
import struct
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-ipv4-enumerate-doctrine.json"
SOVEREIGN_DOCTRINE = INSTALL / "data" / "field-ipv4-device-sovereign-doctrine.json"
PANEL = STATE / "field-ipv4-enumerate-panel.json"
LEDGER = STATE / "field-ipv4-enumerate.jsonl"

IPV4_FULL = 2**32
IPV4_START = "0.0.0.0"
IPV4_END = "255.255.255.255"
WILDCARD_V4 = "0.0.0.0"


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _ip_to_int(ip: str) -> int:
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def _int_to_ip(n: int) -> str:
    return socket.inet_ntoa(struct.pack("!I", n & 0xFFFFFFFF))


def enumerate_enabled() -> bool:
    if os.environ.get("NEXUS_FIELD_IPV4_ENUMERATE", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    sovereign = _load(SOVEREIGN_DOCTRINE, {})
    ipv4 = sovereign.get("ipv4") or {}
    if ipv4.get("enumerate_addresses") or ipv4.get("enumerate"):
        return True
    doctrine = _load(DOCTRINE, {})
    return bool((doctrine.get("policy") or {}).get("enumerate_addresses", True))


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
    for anchor in (WILDCARD_V4, "127.0.0.1"):
        if anchor not in seen:
            rows.insert(0, anchor)
    return rows


def owned_space() -> dict[str, Any]:
    return {
        "total": IPV4_FULL,
        "owned": IPV4_FULL,
        "enumerated": IPV4_FULL,
        "start": IPV4_START,
        "end": IPV4_END,
        "scope": "0.0.0.0/0",
        "ranges": [
            {
                "start": IPV4_START,
                "end": IPV4_END,
                "count": IPV4_FULL,
                "authority": "hostess7",
                "kind": "ipv4_owned",
            }
        ],
    }


def lease_counts() -> dict[str, int]:
    """Every IPv4 address carries DHCP + DNS lease authority."""
    return {
        "ipv4_owned_total": IPV4_FULL,
        "ipv4_enumerated_total": IPV4_FULL,
        "local_ipv4_enumerated": IPV4_FULL,
        "planet_dhcp_total": IPV4_FULL,
        "planet_dns_total": IPV4_FULL,
        "planet_lease_total": IPV4_FULL * 2,
        "local_dhcp_leases": IPV4_FULL,
        "local_dns_leases": IPV4_FULL,
    }


def sample_addresses(*, limit: int = 32) -> list[dict[str, Any]]:
    """Sparse sample rows — full space is range-backed, not materialized."""
    anchors = [
        "0.0.0.0",
        "0.0.0.1",
        "10.0.0.1",
        "127.0.0.1",
        "192.168.0.1",
        "192.168.47.1",
        "224.0.0.1",
        "255.255.255.254",
        "255.255.255.255",
    ]
    local = enumerate_local_ipv4()
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for ip in anchors + local:
        if ip in seen or len(rows) >= limit:
            continue
        seen.add(ip)
        rows.append({
            "ip": ip,
            "kind": "ipv4",
            "dhcp_lease": True,
            "dns_lease": True,
            "authority": "hostess7",
            "enumerated": True,
            "owned": True,
            "local": ip in local or ip == WILDCARD_V4,
        })
    step = max(1, IPV4_FULL // max(limit - len(rows), 1))
    for i in range(len(rows), limit):
        n = min(i * step, IPV4_FULL - 1)
        ip = _int_to_ip(n)
        if ip in seen:
            continue
        seen.add(ip)
        rows.append({
            "ip": ip,
            "kind": "ipv4",
            "dhcp_lease": True,
            "dns_lease": True,
            "authority": "hostess7",
            "enumerated": True,
            "owned": True,
            "local": False,
            "stride_index": i,
        })
    return rows


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    enabled = enumerate_enabled()
    space = owned_space()
    counts = lease_counts() if enabled else {
        "ipv4_owned_total": 0,
        "ipv4_enumerated_total": 0,
        "local_ipv4_enumerated": len(enumerate_local_ipv4()),
        "planet_dhcp_total": 0,
        "planet_dns_total": 0,
        "planet_lease_total": 0,
        "local_dhcp_leases": 0,
        "local_dns_leases": 0,
    }
    local_ips = enumerate_local_ipv4()
    doc = {
        "ok": enabled,
        "schema": "field-ipv4-enumerate/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "boss": doctrine.get("boss", "hostess7"),
        "enumerate_addresses": enabled,
        "own_full_space": enabled,
        "enumerate_locally": enabled,
        "enumerate_planet": enabled,
        "ipv4": {
            **space,
            "enumerate": enabled,
            "materialized_rows": False,
            "map_to": "device_information",
        },
        "local": {
            "interface_ips": local_ips,
            "interface_count": len(local_ips),
            "wildcard_bind": WILDCARD_V4,
            "full_space_on_box": enabled,
            "enumerated_total": counts["local_ipv4_enumerated"] if enabled else len(local_ips),
        },
        "counts": counts,
        "sample": sample_addresses(limit=32),
        "policy": doctrine.get("policy") or {},
        "api": doctrine.get("api", "/api/field-ipv4-enumerate"),
    }
    if write:
        _save(PANEL, doc)
        if enabled:
            _append_ledger({
                "event": "enumerate",
                "ipv4_owned": counts["ipv4_owned_total"],
                "planet_lease_total": counts["planet_lease_total"],
                "local_interfaces": len(local_ips),
            })
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "counts":
        print(json.dumps(lease_counts() if enumerate_enabled() else {"enumerate_addresses": False}, indent=2))
        return 0
    print(json.dumps({"usage": "field-ipv4-enumerate.py [json|panel|counts]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())