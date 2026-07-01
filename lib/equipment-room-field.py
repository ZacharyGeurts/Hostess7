#!/usr/bin/env pythong
"""Network equipment room field — MDF/IDF reporting, legacy DNS gear, field server peers."""
from __future__ import annotations

import json
import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "dns-admin-seed.json"
PANEL_CACHE = STATE / "equipment-room-panel.json"
REPORTS = STATE / "equipment-room-reports.jsonl"
PEERS_FILE = STATE / "field-dns-peers.json"


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


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _local_ips() -> list[str]:
    ips: list[str] = []
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips or ["127.0.0.1"]


def _dns_server_status() -> dict[str, Any]:
    py = INSTALL / "lib" / "field-dns.py"
    if not py.is_file():
        return {"running": False, "schema": "field-dns/v2"}
    try:
        proc = subprocess.run(
            [os.environ.get("PYTHON", "pythong"), str(py), "status"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
            env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        pass
    cache = STATE / "field-dns.json"
    return _load_json(cache, {"running": False})


def _discover_lan_dns() -> list[dict[str, Any]]:
    """Best-effort: hosts on LAN that answer UDP/53 (old gear / field servers)."""
    found: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            ["ip", "-4", "neigh", "show"],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        for line in (proc.stdout or "").splitlines():
            parts = line.split()
            if len(parts) < 1:
                continue
            ip = parts[0]
            if ip.startswith("127.") or ip.startswith("169.254."):
                continue
            mac = parts[4] if len(parts) > 4 and parts[3] == "lladdr" else ""
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.35)
            try:
                sock.sendto(b"\x00" * 12 + b"\x01\x00\x00\x01" + b"\x03www\x07example\x03com\x00\x00\x01\x00\x01", (ip, 53))
                sock.recvfrom(512)
                found.append({
                    "ip": ip,
                    "mac": mac,
                    "port": 53,
                    "role": "lan-responder",
                    "stack": "legacy/unknown",
                    "note": "UDP/53 responder — document in equipment room; prefer Truth Resolver upstream",
                })
            except OSError:
                pass
            finally:
                sock.close()
    except OSError:
        pass
    return found[:24]


def _field_dns_peers(seed: dict[str, Any], dns_status: dict[str, Any]) -> list[dict[str, Any]]:
    peers = list(_load_json(PEERS_FILE, seed.get("field_dns_peers_seed") or []))
    local_port = int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53"))
    local = {
        "id": "nexus-truth-local",
        "role": "primary",
        "host": "127.0.0.1",
        "port": local_port,
        "stack": "NEXUS Truth Resolver",
        "rfc": "RFC 1034 §3.6 trace",
        "running": bool(dns_status.get("running")),
        "ipv6": "::1",
        "field_server_port_hint": 777,
    }
    if not any(p.get("id") == "nexus-truth-local" for p in peers):
        peers.insert(0, local)
    else:
        for p in peers:
            if p.get("id") == "nexus-truth-local":
                p.update(local)
    for ip in _local_ips():
        if ip != "127.0.0.1":
            peers.append({
                "id": f"lan-{ip.replace('.', '-')}",
                "role": "field-node",
                "host": ip,
                "port": local_port,
                "stack": "NEXUS field host",
                "rfc": "RFC 1035",
                "note": "Same-host LAN — Truth Resolver loopback preferred",
            })
    peer_doc = _load_json(PEERS_FILE, {})
    configured = peer_doc.get("extra_peers") if isinstance(peer_doc, dict) else None
    if isinstance(configured, list):
        for ep in configured:
            if isinstance(ep, dict) and ep.get("host"):
                peers.append(ep)
    discovered = _discover_lan_dns()
    for d in discovered:
        if not any(p.get("host") == d["ip"] for p in peers):
            peers.append({
                "id": f"discovered-{d['ip'].replace('.', '-')}",
                "role": "legacy-peer",
                "host": d["ip"],
                "port": d["port"],
                "stack": d.get("stack", "legacy"),
                "mac": d.get("mac", ""),
                "note": d.get("note", ""),
            })
    return peers


def append_report(report: dict[str, Any]) -> dict[str, Any]:
    doc = {
        "schema": "equipment-room-report/v1",
        "ts": _now(),
        **report,
    }
    REPORTS.parent.mkdir(parents=True, exist_ok=True)
    with REPORTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
    return doc


def build_panel(*, equipment_room_enabled: bool | None = None) -> dict[str, Any]:
    seed = _load_json(SEED, {})
    dns_status = _dns_server_status()
    enabled = equipment_room_enabled
    if enabled is None:
        enabled = bool(seed.get("equipment_room_default_enabled", True))
    reports: list[dict[str, Any]] = []
    if REPORTS.is_file():
        try:
            for line in REPORTS.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]:
                if line.strip():
                    reports.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    doc: dict[str, Any] = {
        "schema": "equipment-room/v1",
        "updated": _now(),
        "title": "Network Equipment Room · DNS Field",
        "equipment_room_enabled": enabled,
        "equipment_room_prompt": seed.get("equipment_room_prompt"),
        "mdf_idf_checklist": seed.get("mdf_idf_checklist") or [],
        "legacy_dns_equipment": seed.get("legacy_dns_equipment") or [],
        "field_dns_peers": _field_dns_peers(seed, dns_status),
        "dns_server": dns_status,
        "reports_count": len(reports),
        "recent_reports": reports[-8:],
        "identity": {
            "hostname": socket.gethostname(),
            "fqdn": socket.getfqdn(),
            "lan_ips": _local_ips(),
        },
        "interop_notes": [
            "Old BIND / Windows DNS: set forwarders to 127.0.0.1 Truth Resolver — RFC 1035 delegation preserved.",
            "Field servers on Hostess 7 port family (7, 77, 777): admin portal read-only; resolver stays on :53 loopback.",
            "ISP modem DNS: document only — foreign resolver policy blocks egress.",
            "More field servers: add to field-dns-peers.json extra_peers — no remote push from this portal.",
        ],
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
    return build_panel()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "report" and len(sys.argv) > 2:
        try:
            payload = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            print(json.dumps({"error": "invalid json"}))
            return 1
        print(json.dumps(append_report(payload), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: equipment-room-field.py [json|build|report <json>]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())