#!/usr/bin/env pythong
"""US local network — learn from existing NEXUS tables; show LAN on US field."""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_CACHE = STATE / "us-local-network.json"

PRIVATE_IP = re.compile(
    r"^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|169\.254\.)"
)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _run(cmd: list[str], timeout: int = 6) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
        return (proc.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _parse_neigh_table() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = _run(["ip", "-j", "neigh", "show"])
    if text:
        try:
            for ent in json.loads(text):
                ip = str(ent.get("dst") or "")
                if not ip or ip.startswith("127.") or not PRIVATE_IP.match(ip):
                    continue
                rows.append({
                    "ip": ip,
                    "mac": str(ent.get("lladdr") or ""),
                    "iface": str(ent.get("dev") or ""),
                    "state": str(ent.get("state") or ""),
                    "source": "arp_neigh",
                })
            return rows
        except json.JSONDecodeError:
            pass
    for line in _run(["ip", "neigh", "show"]).splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        ip, _, _, state = parts[0], parts[1], parts[2], parts[3]
        mac = parts[5] if len(parts) > 5 and parts[4] == "lladdr" else ""
        if not PRIVATE_IP.match(ip):
            continue
        rows.append({"ip": ip, "mac": mac, "iface": parts[2] if len(parts) > 2 else "", "state": state, "source": "arp_neigh"})
    snap = STATE / "arp.snapshot"
    if snap.is_file():
        for line in snap.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.search(r"(\d+\.\d+\.\d+\.\d+).*?([0-9a-f:]{11,17})", line, re.I)
            if m and PRIVATE_IP.match(m.group(1)):
                ip = m.group(1)
                if not any(r["ip"] == ip for r in rows):
                    rows.append({"ip": ip, "mac": m.group(2), "state": "snapshot", "source": "arp_snapshot"})
    return rows


def _dhcp_leases() -> list[dict[str, Any]]:
    leases_doc = _load_json(STATE / "field-dhcp-leases.json", {"leases": {}})
    pool = leases_doc.get("leases") or {}
    rows: list[dict[str, Any]] = []
    if isinstance(pool, dict):
        for mac, info in pool.items():
            if isinstance(info, dict):
                rows.append({
                    "ip": info.get("ip"),
                    "mac": mac,
                    "dns": info.get("dns") or ["127.0.0.1"],
                    "leased_at": info.get("leased_at"),
                    "source": "dhcp_lease",
                    "role": "dhcp-client",
                })
    dhcp_panel = _load_json(STATE / "field-dhcp-panel.json", {})
    for item in dhcp_panel.get("leases") or []:
        if isinstance(item, (list, tuple)) and len(item) == 2:
            mac, info = item[0], item[1]
            if isinstance(info, dict) and info.get("ip"):
                rows.append({
                    "ip": info["ip"],
                    "mac": mac,
                    "source": "dhcp_panel",
                    "role": "dhcp-client",
                })
    return rows


def _home_protector_lan() -> list[dict[str, Any]]:
    doc = _load_json(STATE / "home-protector-panel.json", {})
    rows: list[dict[str, Any]] = []
    for ent in doc.get("entities") or doc.get("table") or []:
        kind = str(ent.get("kind") or "")
        if kind not in ("lan", "arp", "wifi"):
            continue
        rows.append({
            "ip": ent.get("ip"),
            "mac": ent.get("mac") or ent.get("bssid"),
            "label": ent.get("label"),
            "kind": kind,
            "permission": ent.get("permission"),
            "unauthorized": ent.get("unauthorized"),
            "signal": ent.get("signal"),
            "source": "home_protector",
            "role": kind,
        })
    return rows


def _equipment_room_peers() -> list[dict[str, Any]]:
    doc = _load_json(STATE / "equipment-room-panel.json", {})
    rows: list[dict[str, Any]] = []
    for peer in doc.get("field_dns_peers") or []:
        host = peer.get("host") or peer.get("ip")
        if not host or str(host).startswith("127."):
            continue
        rows.append({
            "ip": host,
            "mac": peer.get("mac"),
            "label": peer.get("stack") or peer.get("role"),
            "port": peer.get("port"),
            "role": peer.get("role") or "dns-peer",
            "running": peer.get("running"),
            "source": "equipment_room",
        })
    return rows


def _gatekeeper_lan() -> list[dict[str, Any]]:
    doc = _load_json(STATE / "connection-intent.json", {})
    rows: list[dict[str, Any]] = []
    for conn in doc.get("connections") or []:
        rip = str(conn.get("remote_ip") or conn.get("remote") or "").split(":")[0].strip("[]")
        if not rip or not PRIVATE_IP.match(rip):
            continue
        rows.append({
            "ip": rip,
            "label": conn.get("process"),
            "verdict": conn.get("verdict"),
            "source": "gatekeeper",
            "role": "live-flow",
        })
    return rows


def _dns_servers() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dns = _load_json(STATE / "field-dns-panel.json", {})
    srv = dns.get("servers") or {}
    dns_srv = srv.get("dns") or {}
    if dns_srv:
        rows.append({
            "ip": "127.0.0.1",
            "label": "NEXUS Truth Resolver",
            "port": dns_srv.get("port") or 53,
            "running": dns_srv.get("running"),
            "role": "dns-server",
            "source": "field_dns",
        })
    dhcp_srv = srv.get("dhcp") or _load_json(STATE / "field-dhcp-panel.json", {})
    if dhcp_srv.get("running") or dhcp_srv.get("bind"):
        rows.append({
            "ip": str(dhcp_srv.get("bind") or "0.0.0.0:67").split(":")[0],
            "label": "NEXUS Field DHCP",
            "port": 67,
            "running": dhcp_srv.get("running"),
            "lease_count": dhcp_srv.get("lease_count", 0),
            "role": "dhcp-server",
            "source": "field_dhcp",
        })
    return rows


def _merge_devices(sources: list[tuple[str, list[dict[str, Any]]]]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for table_name, rows in sources:
        for row in rows:
            ip = str(row.get("ip") or "").strip()
            mac = str(row.get("mac") or "").strip().lower()
            key = ip or mac or f"{table_name}:{row.get('label', '')}"
            if key not in by_key:
                by_key[key] = {
                    "id": key,
                    "ip": ip or None,
                    "mac": mac or None,
                    "label": row.get("label") or row.get("role") or "",
                    "role": row.get("role") or row.get("kind") or "device",
                    "sources": [],
                    "tables": [],
                }
            ent = by_key[key]
            if ip and not ent.get("ip"):
                ent["ip"] = ip
            if mac and not ent.get("mac"):
                ent["mac"] = mac
            if row.get("label") and not ent.get("label"):
                ent["label"] = row["label"]
            src = row.get("source") or table_name
            if src not in ent["sources"]:
                ent["sources"].append(src)
            if table_name not in ent["tables"]:
                ent["tables"].append(table_name)
            for field in (
                "iface", "state", "permission", "unauthorized", "verdict",
                "signal", "port", "running", "dns", "leased_at", "lease_count",
            ):
                if row.get(field) is not None and ent.get(field) is None:
                    ent[field] = row[field]
    devices = sorted(by_key.values(), key=lambda d: (d.get("ip") or "zzz", d.get("mac") or ""))
    return devices


def _subnets(interfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    subnets: list[dict[str, Any]] = []
    for iface in interfaces:
        name = iface.get("name") or ""
        for addr in iface.get("addresses") or []:
            if addr.get("family") not in ("inet", None) and str(addr.get("family")) != "inet":
                continue
            local = addr.get("local")
            plen = addr.get("prefixlen")
            if local and plen and PRIVATE_IP.match(str(local)):
                subnets.append({
                    "iface": name,
                    "cidr": f"{local}/{plen}",
                    "host_ip": local,
                    "scope": addr.get("scope") or "global",
                })
    return subnets


def build_local_network(*, interfaces: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if interfaces is None:
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("field_us_intel", INSTALL / "lib" / "field-us-intel.py")
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                interfaces = mod._interfaces()
        except Exception:
            interfaces = []

    tables = {
        "arp_neigh": _parse_neigh_table(),
        "dhcp_leases": _dhcp_leases(),
        "home_protector": _home_protector_lan(),
        "equipment_room": _equipment_room_peers(),
        "gatekeeper": _gatekeeper_lan(),
        "dns_dhcp_servers": _dns_servers(),
    }
    sources = [(name, rows) for name, rows in tables.items()]
    devices = _merge_devices(sources)
    table_stats = {name: len(rows) for name, rows in tables.items()}
    hostname = socket.gethostname()
    doc = {
        "schema": "us-local-network/v1",
        "updated": _now(),
        "title": "Local network",
        "motto": "Learned from ARP, DHCP, home protector, equipment room, gatekeeper — your LAN on US.",
        "hostname": hostname,
        "device_count": len(devices),
        "subnets": _subnets(interfaces or []),
        "devices": devices,
        "tables_learned": table_stats,
        "tables_total_rows": sum(table_stats.values()),
        "sources": list(tables.keys()),
    }
    tmp = PANEL_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL_CACHE)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL_CACHE.is_file():
        try:
            return json.loads(PANEL_CACHE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return build_local_network()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_local_network(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: us-local-network.py [json|build]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())