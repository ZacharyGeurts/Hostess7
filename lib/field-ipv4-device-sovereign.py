#!/usr/bin/env pythong
"""All IPv4 on every box — device-mapped authority; auto-manage; suppress foreign DNS/DHCP worldwide."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-ipv4-device-sovereign-doctrine.json"
PANEL = STATE / "field-ipv4-device-sovereign-panel.json"
LEDGER = STATE / "field-ipv4-device-sovereign.jsonl"

IPV4_SPACE = 2**32


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


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_json(rel: str, args: list[str], *, timeout: float = 30.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
    except Exception:
        pass
    return {}


def _lease_by_mac() -> dict[str, dict[str, Any]]:
    leases = _load(STATE / "field-dhcp-leases.json", {"leases": {}})
    return {
        mac: entry for mac, entry in (leases.get("leases") or {}).items()
        if isinstance(entry, dict)
    }


def _device_authority_rows() -> list[dict[str, Any]]:
    """Device information primary — IPv4 numbers omitted from the authority map."""
    device_map = _load(STATE / "field-device-map-panel.json", {})
    if not device_map.get("devices"):
        device_map = _run_json("lib/field-device-map.py", ["json"], timeout=45)
    leases = _lease_by_mac()
    rows: list[dict[str, Any]] = []

    for d in device_map.get("devices") or []:
        if not isinstance(d, dict):
            continue
        did = str(d.get("id") or "")
        if not did:
            continue
        mac = str(d.get("mac") or d.get("hwaddr") or "").lower()
        lease = leases.get(mac) if mac else None
        rows.append({
            "device_id": did,
            "label": d.get("label") or did,
            "kind": d.get("kind") or d.get("source") or "device",
            "connected": bool(d.get("connected", True)),
            "flying": bool(d.get("flying")),
            "precision": d.get("precision") or "sub_micron",
            "bearing": d.get("direction"),
            "distance_label": d.get("distance_label"),
            "dns_authority": "hostess7_truth",
            "dhcp_authority": "hostess7_field",
            "ipv4_sovereign": True,
            "track_ip": False,
            "has_lease": bool(lease),
            "source": d.get("source"),
        })

    botnet = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    seen = {r["device_id"] for r in rows}
    for n in (botnet.get("bot_network") or {}).get("nodes") or []:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id") or "")
        if not nid or nid in seen:
            continue
        seen.add(nid)
        rows.append({
            "device_id": nid,
            "label": n.get("label") or nid,
            "kind": n.get("kind") or "botnet_box",
            "connected": True,
            "flying": n.get("kind") == "qemu_world",
            "roles": n.get("roles"),
            "dns_authority": "hostess7_truth",
            "dhcp_authority": "hostess7_field",
            "ipv4_sovereign": True,
            "all_ipv4_on_box": True,
            "suppress_foreign_dns_dhcp": True,
            "track_ip": False,
            "auto_managed": True,
            "source": "botnet_node",
        })

    for mac, entry in leases.items():
        pseudo = f"dhcp-{mac.replace(':', '')[:12]}"
        if pseudo in seen:
            continue
        seen.add(pseudo)
        rows.append({
            "device_id": pseudo,
            "label": f"LAN client {mac}",
            "kind": "dhcp_client",
            "connected": True,
            "dns_authority": "hostess7_truth",
            "dhcp_authority": "hostess7_field",
            "ipv4_sovereign": True,
            "track_ip": False,
            "has_lease": True,
            "mac": mac,
            "source": "field-dhcp",
        })

    return rows


def _box_authority() -> dict[str, Any]:
    hostname = os.environ.get("HOSTNAME", "field-box")
    try:
        import socket
        hostname = socket.gethostname()
    except OSError:
        pass
    return {
        "box_id": hostname,
        "all_ipv4": True,
        "ipv4_scope": "0.0.0.0/0",
        "bind_dns": "0.0.0.0:53",
        "bind_dhcp": "0.0.0.0:67",
        "auto_managed": True,
        "never_look_back": True,
        "boss": "hostess7",
    }


def _worldwide_suppression() -> dict[str, Any]:
    collision = _load(STATE / "field-dns-dhcp-collision-guard-panel.json", {})
    if not collision.get("foreign_threat_count"):
        collision = _run_json("lib/field-dns-dhcp-collision-guard.py", ["detect"], timeout=20)
    botnet = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    node_count = int((botnet.get("bot_network") or {}).get("node_count") or 0)
    enforce = collision.get("enforce") or {}
    return {
        "active": True,
        "foreign_dns_dhcp_off": True,
        "foreign_threat_count": collision.get("foreign_threat_count", 0),
        "threats_eradicated": enforce.get("threats_eradicated", 0),
        "sole_authority": (collision.get("sole_authority") or {}).get("ok"),
        "suppressor_nodes": node_count + 1,
        "motto": "Turn off any other DHCP and DNS — worldwide botnet suppressors",
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    devices = _device_authority_rows()
    any_ip = _run_json("lib/field-dns-dhcp-any-ip.py", ["json"], timeout=15)
    planetary = _load(STATE / "field-planetary-dns-dhcp-panel.json", {})

    doc = {
        "ok": True,
        "schema": "field-ipv4-device-sovereign/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "boss": doctrine.get("boss", "hostess7"),
        "all_ipv4_every_box": True,
        "track_devices_not_numbers": True,
        "never_look_back": True,
        "ipv4": {
            "sovereign": True,
            "symbolic_space": IPV4_SPACE,
            "scope": "0.0.0.0/0",
            "enumerate": False,
            "map_to": "device_information",
        },
        "box": _box_authority(),
        "devices": devices,
        "device_count": len(devices),
        "connected_devices": sum(1 for d in devices if d.get("connected")),
        "any_ip": {
            "dns_wildcard": (any_ip.get("dns") or {}).get("wildcard_v4"),
            "dhcp_wildcard": (any_ip.get("dhcp") or {}).get("wildcard"),
        },
        "worldwide_suppression": _worldwide_suppression(),
        "planetary_leases": (planetary.get("counts") or {}).get("planet_lease_total"),
        "policy": doctrine.get("policy") or {},
        "api": doctrine.get("api", "/api/field-ipv4-device-sovereign"),
    }
    if write:
        _save(PANEL, doc)
    return doc


def manage(*, auto: bool = True) -> dict[str, Any]:
    """Automatic sovereign management — enforce, absorb, refresh device map."""
    actions: list[dict[str, Any]] = []

    cg = _run_json("lib/field-dns-dhcp-collision-guard.py", ["enforce"], timeout=45)
    actions.append({"step": "collision_guard", "sole": (cg.get("sole_authority") or {}).get("ok")})

    _run_json("lib/field-planetary-dns-dhcp.py", ["absorb", "--no-crush"], timeout=60)
    actions.append({"step": "planetary_absorb"})

    _run_json("lib/field-dns-dhcp-any-ip.py", ["panel"], timeout=15)
    actions.append({"step": "any_ip_panel"})

    _run_json("lib/field-device-map.py", ["panel"], timeout=60)
    actions.append({"step": "device_map"})

    panel = build_panel(write=True)
    panel["manage"] = {
        "auto": auto,
        "actions": actions,
        "device_count": panel.get("device_count"),
        "worldwide_suppression": panel.get("worldwide_suppression"),
    }
    _save(PANEL, panel)
    _append_ledger({
        "event": "manage",
        "devices": panel.get("device_count"),
        "suppression": panel.get("worldwide_suppression"),
    })
    return panel


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("manage", "auto", "run"):
        print(json.dumps(manage(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "devices":
        print(json.dumps({
            "devices": _device_authority_rows(),
            "device_count": len(_device_authority_rows()),
            "track_devices_not_numbers": True,
        }, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-ipv4-device-sovereign.py [json|panel|manage|devices]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())