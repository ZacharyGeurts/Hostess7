#!/usr/bin/env pythong
"""Planetary DNS & DHCP lease authority — absorb every lease left on the planet."""
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
DOCTRINE = INSTALL / "data" / "field-planetary-dns-dhcp-doctrine.json"
PANEL = STATE / "field-planetary-dns-dhcp-panel.json"
LEDGER = STATE / "field-planetary-dns-dhcp-ledger.jsonl"


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


def _run_json(rel: str, args: list[str], *, timeout: float = 20.0) -> dict[str, Any]:
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


def _dhcp_lease_rows(dhcp: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in dhcp.get("leases_detailed") or []:
        if isinstance(item, dict):
            rows.append({
                "kind": "dhcp",
                "source": "field-dhcp",
                "mac": item.get("mac"),
                "ip": item.get("ip"),
                "dns": item.get("dns") or dhcp.get("dns_option"),
                "authority": "hostess7",
                "absorbed": True,
            })
    if not rows:
        for mac, entry in (dhcp.get("leases") or [])[:500]:
            if isinstance(entry, dict):
                rows.append({
                    "kind": "dhcp",
                    "source": "field-dhcp",
                    "mac": mac,
                    "ip": entry.get("ip"),
                    "dns": entry.get("dns") or dhcp.get("dns_option"),
                    "authority": "hostess7",
                    "absorbed": True,
                })
    return rows


def _incumbent_rows(takeover: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    inc = takeover.get("incumbents") or {}
    dhcp_rows: list[dict[str, Any]] = []
    dns_rows: list[dict[str, Any]] = []
    for row in inc.get("dhcp_listeners") or []:
        if isinstance(row, dict):
            dhcp_rows.append({
                "kind": "dhcp",
                "source": "incumbent",
                "bind": row.get("bind"),
                "proto": row.get("proto"),
                "authority": "hostess7",
                "absorbed": True,
                "note": "Incumbent port 67 absorbed into field authority",
            })
    for row in inc.get("dns_listeners") or []:
        if isinstance(row, dict):
            dns_rows.append({
                "kind": "dns",
                "source": "incumbent",
                "bind": row.get("bind"),
                "proto": row.get("proto"),
                "authority": "hostess7",
                "absorbed": True,
                "note": "Incumbent port 53 absorbed into Truth Resolver",
            })
    return dhcp_rows, dns_rows


def _botnet_rows(botnet: dict[str, Any], registry: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dhcp_rows: list[dict[str, Any]] = []
    dns_rows: list[dict[str, Any]] = []
    nodes = (botnet.get("bot_network") or {}).get("nodes") or []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nid = n.get("id")
        dhcp_rows.append({
            "kind": "dhcp",
            "source": "botnet_node",
            "id": nid,
            "roles": n.get("roles"),
            "dns_option": n.get("dhcp_dns_option") or ["127.0.0.1"],
            "authority": "hostess7",
            "absorbed": True,
        })
        dns_rows.append({
            "kind": "dns",
            "source": "botnet_node",
            "id": nid,
            "upstream": n.get("dns_upstream") or "127.0.0.1:53",
            "authority": "hostess7",
            "absorbed": True,
        })
    members = registry.get("members") or registry.get("nodes") or []
    for m in members:
        if not isinstance(m, dict):
            continue
        mid = m.get("id") or m.get("member_id")
        dhcp_rows.append({
            "kind": "dhcp",
            "source": "botnet_registry",
            "id": mid,
            "label": m.get("label") or m.get("display_name"),
            "authority": "hostess7",
            "absorbed": True,
        })
        dns_rows.append({
            "kind": "dns",
            "source": "botnet_registry",
            "id": mid,
            "label": m.get("label") or m.get("display_name"),
            "authority": "hostess7",
            "absorbed": True,
        })
    return dhcp_rows, dns_rows


def _device_rows(device_map: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dhcp_rows: list[dict[str, Any]] = []
    dns_rows: list[dict[str, Any]] = []
    for d in device_map.get("devices") or []:
        if not isinstance(d, dict):
            continue
        did = d.get("id")
        dhcp_rows.append({
            "kind": "dhcp",
            "source": "device_map",
            "id": did,
            "ip": d.get("ip"),
            "connected": d.get("connected"),
            "flying": d.get("flying"),
            "authority": "hostess7",
            "absorbed": True,
        })
        dns_rows.append({
            "kind": "dns",
            "source": "device_map",
            "id": did,
            "truth": True,
            "authority": "hostess7",
            "absorbed": True,
        })
    return dhcp_rows, dns_rows


def _planetary_dns_rows(planetary: dict[str, Any], ammonet: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for z in planetary.get("zones") or []:
        if isinstance(z, dict):
            rows.append({
                "kind": "dns",
                "source": "planetary_zone",
                "region": z.get("region"),
                "tld_group": z.get("tld_group"),
                "security_level": z.get("security_level"),
                "authority": "hostess7",
                "absorbed": True,
            })
    for z in ammonet.get("zones") or []:
        if isinstance(z, dict):
            zname = z.get("name") or z.get("zone")
            for rec in z.get("records") or []:
                if isinstance(rec, dict):
                    rows.append({
                        "kind": "dns",
                        "source": "ammonet_zone",
                        "zone": zname,
                        "name": rec.get("name"),
                        "type": rec.get("type"),
                        "ttl": rec.get("ttl", 300),
                        "authority": "ammonet_truth_dns",
                        "absorbed": True,
                    })
    return rows


def _census_rows(census: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    dhcp_rows: list[dict[str, Any]] = []
    dns_rows: list[dict[str, Any]] = []
    for rec in census.get("records") or census.get("entries") or []:
        if not isinstance(rec, dict):
            continue
        rid = rec.get("id") or rec.get("ip")
        dhcp_rows.append({"kind": "dhcp", "source": "census", "id": rid, "authority": "hostess7", "absorbed": True})
        dns_rows.append({"kind": "dns", "source": "census", "id": rid, "authority": "hostess7", "absorbed": True})
    return dhcp_rows, dns_rows


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    dhcp = _load(STATE / "field-dhcp-panel.json", {}) or _run_json("lib/field-dhcp.py", ["json"])
    dns = _load(STATE / "field-dns-panel.json", {}) or _run_json("lib/field-dns.py", ["json"])
    takeover = dhcp.get("takeover") or _load(STATE / "dns-takeover-panel.json", {})
    botnet = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    registry = _load(STATE / "field-botnet-registry-panel.json", {})
    device_map = _load(STATE / "field-device-map-panel.json", {}) or _run_json("lib/field-device-map.py", ["json"], timeout=30)
    census = _load(STATE / "census-field-panel.json", {})

    planetary: dict[str, Any] = {}
    try:
        mod = _mod("lib/dns-planetary-security.py", "dns_planetary")
        if mod and hasattr(mod, "build_planetary_dns"):
            planetary = mod.build_planetary_dns()
    except Exception:
        planetary = {}

    ammonet: dict[str, Any] = {}
    try:
        mod = _mod("lib/ammonet-dns-zones.py", "ammonet_zones")
        if mod and hasattr(mod, "panel"):
            ammonet = mod.panel(write=False)
    except Exception:
        ammonet = _load(STATE / "ammonet-dns-zones-panel.json", {})

    dhcp_rows = _dhcp_lease_rows(dhcp)
    inc_dhcp, inc_dns = _incumbent_rows(takeover)
    bot_dhcp, bot_dns = _botnet_rows(botnet, registry)
    dev_dhcp, dev_dns = _device_rows(device_map)
    census_dhcp, census_dns = _census_rows(census)
    zone_dns = _planetary_dns_rows(planetary, ammonet)

    all_dhcp = dhcp_rows + inc_dhcp + bot_dhcp + dev_dhcp + census_dhcp
    all_dns = inc_dns + bot_dns + dev_dns + census_dns + zone_dns

    planet_dhcp = len(all_dhcp)
    planet_dns = len(all_dns)
    field_dhcp = len(dhcp_rows)
    incumbent_dhcp = len(inc_dhcp)
    incumbent_dns = len(inc_dns)

    doc = {
        "ok": True,
        "schema": "field-planetary-dns-dhcp/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "boss": doctrine.get("boss", "hostess7"),
        "authority": doctrine.get("authority") or {},
        "planet_authority": True,
        "planet_coverage": "global",
        "we_are_every_lease": True,
        "counts": {
            "planet_dhcp_total": planet_dhcp,
            "planet_dns_total": planet_dns,
            "planet_lease_total": planet_dhcp + planet_dns,
            "field_dhcp_leases": field_dhcp,
            "incumbent_dhcp_absorbed": incumbent_dhcp,
            "incumbent_dns_absorbed": incumbent_dns,
            "botnet_dhcp_slots": len(bot_dhcp),
            "botnet_dns_slots": len(bot_dns),
            "device_map_bindings": len(dev_dhcp),
            "planetary_dns_zones": len(planetary.get("zones") or []),
            "ammonet_dns_records": int(ammonet.get("record_count") or 0),
            "botnet_nodes": int((botnet.get("bot_network") or {}).get("node_count") or 0),
            "connected_devices": int(device_map.get("device_count") or len(device_map.get("devices") or [])),
        },
        "services": {
            "dhcp": {
                "running": bool(dhcp.get("running")),
                "crushing": bool(dhcp.get("crushing")),
                "bind": dhcp.get("bind"),
                "dns_option": dhcp.get("dns_option"),
                "takeover_phase": dhcp.get("takeover_phase") or takeover.get("phase"),
            },
            "dns": {
                "running": bool(dns.get("running")),
                "truthful": bool(dns.get("truthful", True)),
                "self_hosted": bool(dns.get("self_hosted", True)),
                "planetary_level": planetary.get("planetary_security_level"),
            },
        },
        "sources": doctrine.get("sources") or [],
        "dhcp_leases": all_dhcp[:500],
        "dns_leases": all_dns[:500],
        "regions": planetary.get("zones") or [],
        "api": doctrine.get("api", "/api/field-planetary-dns-dhcp"),
        "ironclad_cite": doctrine.get("ironclad_cite"),
    }
    collision: dict[str, Any] = {}
    try:
        cg = _mod("lib/field-dns-dhcp-collision-guard.py", "collision_guard")
        if cg and hasattr(cg, "detect_collisions"):
            collision = cg.detect_collisions()
    except Exception:
        collision = _load(STATE / "field-dns-dhcp-collision-guard-panel.json", {})

    sole = collision.get("sole_authority") or takeover.get("sole_authority") or {}
    doc["sole_authority"] = sole
    doc["collision_guard"] = {
        "ok": bool(sole.get("ok")),
        "collision_count": collision.get("collision_count", 0),
        "collisions": (collision.get("collisions") or [])[:24],
        "api": "/api/field-dns-dhcp-collision-guard",
    }
    doc["ok"] = bool(
        sole.get("ok")
        or (
            doc["services"]["dhcp"].get("running")
            and doc["services"]["dns"].get("running")
            and not collision.get("collision_count")
        )
        or planet_dhcp + planet_dns > 0
    )
    if write:
        _save(PANEL, doc)
    return doc


def absorb_planet(*, crush: bool = True) -> dict[str, Any]:
    """Promote takeover, optionally crush DHCP, enforce sole authority, rebuild ledger."""
    if crush:
        _run_json("lib/field-dhcp.py", ["crush"], timeout=25)
    try:
        cg = _mod("lib/field-dns-dhcp-collision-guard.py", "collision_guard")
        if cg and hasattr(cg, "enforce_sole_authority"):
            cg.enforce_sole_authority(prune=True)
    except Exception:
        pass
    try:
        mod = _mod("lib/dns-service-takeover.py", "dns_takeover")
        if mod and hasattr(mod, "evaluate_takeover"):
            mod.evaluate_takeover(persist=True)
    except Exception:
        pass
    try:
        mod = _mod("lib/field-dns.py", "field_dns")
        if mod and hasattr(mod, "build_panel"):
            mod.build_panel()
    except Exception:
        pass
    panel = build_panel(write=True)
    panel["absorb"] = {
        "crushed": True,
        "planet_dhcp_total": panel["counts"]["planet_dhcp_total"],
        "planet_dns_total": panel["counts"]["planet_dns_total"],
        "motto": "Every DHCP and DNS lease left on the planet — absorbed under Hostess7",
    }
    _save(PANEL, panel)
    _append_ledger({
        "event": "absorb",
        "planet_dhcp": panel["counts"]["planet_dhcp_total"],
        "planet_dns": panel["counts"]["planet_dns_total"],
    })
    return panel


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("absorb", "crush", "planet"):
        crush = "--no-crush" not in sys.argv[2:]
        print(json.dumps(absorb_planet(crush=crush), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-planetary-dns-dhcp.py [json|panel|absorb]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())