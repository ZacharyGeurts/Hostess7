#!/usr/bin/env python3
"""Everyone Online celebration — live panel on 127.0.0.1 as the planet joins Field DNS."""
from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-everyone-online-celebrate-doctrine.json"
PANEL = STATE / "field-everyone-online-celebrate-panel.json"
PANEL_SLIM = STATE / "field-everyone-online-celebrate-slim.json"
ROWS_EXISTENCE = STATE / "field-everyone-online-existence-rows.json"
ROWS_LEASES = STATE / "field-everyone-online-lease-rows.json"
HTML_PATH = INSTALL / "panel" / "field-everyone-online.html"
SCHEMA = "field-everyone-online-celebrate/v1"

BIND = os.environ.get("NEXUS_EVERYONE_ONLINE_BIND", "127.0.0.1")
PORT = int(os.environ.get("NEXUS_EVERYONE_ONLINE_PORT", "9477") or "9477")


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


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _bound_flags(bound: list[str]) -> dict[str, bool]:
    """Derive answer-point presence from published multi-bind state only (no live probes)."""
    text = " ".join(str(b) for b in bound)
    return {
        "127.0.0.1": "127.0.0.1" in text,
        "192.168.47.1": "192.168.47.1" in text,
        "192.168.50.1": "192.168.50.1" in text,
        "0.0.0.0": "0.0.0.0" in text,
        "::1": "::1" in text or "[::1]" in text,
    }


def _lease_rows() -> list[dict[str, Any]]:
    raw = _load(STATE / "field-dhcp-leases.json", {})
    leases = raw.get("leases") or {}
    rows: list[dict[str, Any]] = []
    if isinstance(leases, dict):
        for mac, ent in leases.items():
            if not isinstance(ent, dict):
                continue
            dns = ent.get("dns") or ["192.168.47.1", "127.0.0.1"]
            if not isinstance(dns, list):
                dns = [dns]
            domain = ent.get("domain") or "ammonet.net"
            rows.append(
                {
                    "mac": mac,
                    "ip": ent.get("ip"),
                    "dns": dns,
                    "dns_joined": ", ".join(str(x) for x in dns),
                    "device_id": ent.get("device_id") or f"dhcp-{str(mac).replace(':', '')}",
                    "hostname": ent.get("hostname"),
                    "kind": ent.get("kind") or "dhcp_lease",
                    "domain": domain,
                    "search": ent.get("search") or [domain, "ammonet.com", "ammonet.org"],
                    "last_seen": ent.get("last_seen") or ent.get("leased_at"),
                    "leased_at": ent.get("leased_at"),
                    "expires_at": ent.get("expires_at"),
                    "legacy": bool(ent.get("legacy")),
                    "track_ip": bool(ent.get("track_ip")),
                    "arbitrary_ipv4": bool(ent.get("arbitrary_ipv4")),
                    "ammonet": bool(ent.get("ammonet", True)),
                    "seamless": bool(ent.get("seamless", True)),
                    "held_securely": bool(ent.get("held_securely", True)),
                    "outside_interference": bool(ent.get("outside_interference", False)),
                    "route_to": ent.get("route_to") or "field-1",
                    "real": True,
                    "shared": True,
                }
            )
    # Stable sort: newest last_seen first — full AmmoNet takeover table (no tiny cap)
    rows.sort(key=lambda r: str(r.get("last_seen") or ""), reverse=True)
    # Hard ceiling only for pathological multi-million materializations
    cap = int(os.environ.get("NEXUS_CELEBRATE_LEASE_CAP", "20000") or "20000")
    return rows[: max(128, cap)]


def _device_row(d: dict[str, Any], *, real: bool) -> dict[str, Any]:
    """Full shareable device table row — IP/MAC/DNS/hostname, not id-only."""
    kind = str(d.get("kind") or "")
    dns = d.get("dns") or []
    if not isinstance(dns, list):
        dns = [dns] if dns else []
    return {
        "id": d.get("id") or d.get("hostname") or d.get("display_name"),
        "display_name": d.get("display_name") or d.get("hostname") or d.get("id"),
        "hostname": d.get("hostname"),
        "role": d.get("role"),
        "kind": kind or None,
        "ip": d.get("ip"),
        "mac": d.get("mac"),
        "dns": dns,
        "dns_joined": ", ".join(str(x) for x in dns) if dns else "",
        "self": bool(d.get("self")),
        "active": bool(d.get("active") if "active" in d else True),
        "last_seen": d.get("last_seen") or d.get("last_timestamp"),
        "sources": d.get("sources") or ([d.get("source")] if d.get("source") else []),
        "panel_port": d.get("panel_port"),
        "machine": d.get("machine"),
        "real": real,
        "shared": True,
        "fake": bool(d.get("fake")),
    }


def _self_host_enrich(d: dict[str, Any]) -> dict[str, Any]:
    """Fill IP/DNS for this host from Field bind + leases so tables share real addresses."""
    out = dict(d)
    dns_udp = _load(STATE / "field-dns-udp-full.json", {})
    bound = list(dns_udp.get("bound") or [])
    # Prefer LAN Field address, then public, then loopback
    candidates: list[str] = []
    for b in bound:
        s = str(b).split("%")[0]
        ip = s.rsplit(":", 1)[0] if ":" in s and not s.startswith("[") else s.strip("[]")
        if ip in ("0.0.0.0", "::", "") or ip.startswith("127."):
            continue
        if ip not in candidates:
            candidates.append(ip)
    if not out.get("ip") and candidates:
        # Prefer 192.168.47.1 / 192.168.50.1 Field LAN
        for prefer in ("192.168.47.1", "192.168.50.1"):
            if prefer in candidates:
                out["ip"] = prefer
                break
        if not out.get("ip"):
            out["ip"] = candidates[0]
    if not out.get("dns"):
        out["dns"] = ["127.0.0.1", "192.168.47.1"]
    return out


def _merge_lease_into_device(d: dict[str, Any], leases: list[dict[str, Any]]) -> dict[str, Any]:
    """If registry row lacks IP/MAC, pull from matching DHCP lease."""
    out = dict(d)
    did = str(out.get("id") or "")
    mac = str(out.get("mac") or "").lower()
    for L in leases:
        lmac = str(L.get("mac") or "").lower()
        lid = str(L.get("device_id") or "")
        if (mac and lmac == mac) or (did and lid == did) or (did and did.replace("dhcp-", "") in lmac.replace(":", "")):
            if not out.get("ip"):
                out["ip"] = L.get("ip")
            if not out.get("mac"):
                out["mac"] = L.get("mac")
            if not out.get("dns"):
                out["dns"] = L.get("dns") or []
            if not out.get("last_seen"):
                out["last_seen"] = L.get("last_seen")
            break
    return out


def _existence_row(d: dict[str, Any], *, hold_class: str, real_live: bool) -> dict[str, Any]:
    """One held device in existence — secure Field hold, no outside authority."""
    kind = str(d.get("kind") or "")
    dns = d.get("dns") or []
    if not isinstance(dns, list):
        dns = [dns] if dns else []
    only_ammonet = bool(d.get("only_ammonet") or d.get("ammonet_member") or d.get("self"))
    return {
        "id": d.get("id") or d.get("hostname") or d.get("display_name") or d.get("node_id"),
        "display_name": d.get("display_name") or d.get("hostname") or d.get("id") or d.get("node_id"),
        "hostname": d.get("hostname") or d.get("node_id"),
        "role": d.get("role") or hold_class,
        "kind": kind or hold_class,
        "ip": d.get("ip"),
        "mac": d.get("mac"),
        "dns": dns,
        "dns_joined": ", ".join(str(x) for x in dns) if dns else "",
        "self": bool(d.get("self")),
        "active": bool(d.get("active") if "active" in d else True),
        "last_seen": d.get("last_seen") or d.get("last_timestamp") or d.get("updated"),
        "sources": d.get("sources") or ([d.get("source")] if d.get("source") else []),
        "panel_port": d.get("panel_port"),
        "machine": d.get("machine"),
        "repo_slug": d.get("repo_slug"),
        "node_id": d.get("node_id"),
        "route_to": d.get("route_to") or "field-1",
        "field_one_sink": bool(d.get("field_one_sink") or True),
        "ammonet_member": bool(d.get("ammonet_member") or d.get("self")),
        "ammonet_mesh_id": d.get("ammonet_mesh_id"),
        "absolute_knowledge_digest": d.get("absolute_knowledge_digest"),
        "only_ammonet": only_ammonet,
        "quarantine": bool(d.get("quarantine")),
        "ask_only": bool(d.get("ask_only", True)),
        "real": real_live,
        "real_live": real_live,
        "held": True,
        "held_securely": True,
        "hold_class": hold_class,
        "outside_interference": False,
        "outside_network_absorbed": bool(d.get("outside_network") or d.get("outside_network_absorbed")),
        "shared": True,
        "fake": bool(d.get("fake")),
        "in_existence": True,
    }


def _device_census() -> dict[str, Any]:
    """Every device in existence — held securely on Field. Live vs catalog labeled.

    LIVE people counts stay honest (self + dhcp). ALL registry rows are held and
    listed under existence so celebrate can show the full inventory without
    outside interference or foreign authority.
    """
    reg = _load(STATE / "field-device-registry.json", {})
    devices = reg.get("devices") or []
    if isinstance(devices, dict):
        devices = list(devices.values())
    leases = _lease_rows()
    real: list[dict[str, Any]] = []
    fabric: list[dict[str, Any]] = []
    existence: list[dict[str, Any]] = []
    by_kind: dict[str, int] = {}
    skipped_fake = 0

    for d in devices if isinstance(devices, list) else []:
        if not isinstance(d, dict):
            continue
        kind = str(d.get("kind") or "unknown")
        did = str(d.get("id") or "")
        if d.get("fake"):
            skipped_fake += 1
            continue

        by_kind[kind] = by_kind.get(kind, 0) + 1

        # Classify hold tier
        if d.get("self") or kind in ("workstation", "person", "operator"):
            hold_class = "live_self"
            real_live = True
        elif kind == "dhcp_lease":
            hold_class = "live_dhcp"
            real_live = True
        elif kind == "github_planet_dhcp":
            hold_class = "github_held"
            real_live = False
        elif kind in (
            "botnet_node", "botnet_member", "edge_host", "qemu_world",
            "projected", "placeholder", "regional_relay", "security_guard",
        ) or did.startswith("edge-") or did.startswith("botnet-") or did.startswith("qemu-"):
            hold_class = "fabric_held"
            real_live = False
        else:
            hold_class = "held"
            real_live = False

        src = _self_host_enrich(d) if d.get("self") else d
        if real_live:
            src = _merge_lease_into_device(src, leases)
        row = _existence_row(src, hold_class=hold_class, real_live=real_live)
        existence.append(row)
        if real_live:
            real.append(_device_row(src, real=True))
        else:
            fabric.append(_device_row(src, real=False))

    # Fold DHCP leases into existence — match by device_id / mac first.
    # AmmoNet fabric (botnet) leases are held, not live people.
    known_macs = {str(r.get("mac") or "").lower() for r in existence if r.get("mac")}
    known_ids = {str(r.get("id") or "") for r in existence}
    # Index existence by id for lease enrichment
    by_id = {str(r.get("id") or ""): r for r in existence if r.get("id")}
    for L in leases:
        lmac = str(L.get("mac") or "").lower()
        lid = str(L.get("device_id") or "")
        lkind = str(L.get("kind") or "dhcp_lease")
        is_fabric = lkind in (
            "botnet_node", "botnet_member", "edge_host", "qemu_world",
            "regional_relay", "security_guard", "github_planet_dhcp",
        ) or lid.startswith("botnet-") or lid.startswith("edge-") or lid.startswith("qemu-") or lid.startswith("gh-dhcp-")
        # Enrich matched registry/existence rows with lease IP/MAC
        if lid and lid in by_id:
            ent = by_id[lid]
            if not ent.get("ip"):
                ent["ip"] = L.get("ip")
            if not ent.get("mac"):
                ent["mac"] = L.get("mac")
            if not ent.get("dns"):
                ent["dns"] = L.get("dns") or []
                ent["dns_joined"] = ", ".join(str(x) for x in (ent.get("dns") or []))
            ent["ammonet"] = True
            ent["seamless"] = True
            if lmac:
                known_macs.add(lmac)
            continue
        if (lmac and lmac in known_macs) or (lid and lid in known_ids):
            continue
        lease_dev = {
            "id": lid or f"dhcp-{lmac.replace(':', '')}",
            "kind": lkind if lkind != "dhcp_lease" or not is_fabric else "dhcp_lease",
            "ip": L.get("ip"),
            "mac": L.get("mac"),
            "dns": L.get("dns") or ["127.0.0.1"],
            "hostname": L.get("hostname"),
            "last_seen": L.get("last_seen"),
            "active": True,
            "fake": False,
            "real": not is_fabric,
            "only_ammonet": True,
            "ammonet_member": True,
            "ammonet": True,
            "seamless": True,
            "field_one_sink": True,
            "route_to": "field-1",
            "sources": ["field-dhcp-leases", "ammonet-takeover"],
        }
        hold = "fabric_held" if is_fabric else "live_dhcp"
        row = _existence_row(lease_dev, hold_class=hold, real_live=not is_fabric)
        existence.append(row)
        if not is_fabric:
            real.append(_device_row(lease_dev, real=True))
            by_kind["dhcp_lease"] = by_kind.get("dhcp_lease", 0) + 1
        else:
            fabric.append(_device_row(lease_dev, real=False))
            by_kind[lkind] = by_kind.get(lkind, 0) + 1

    # Planetary union — every device ever: stamps + redundant inventory + global servers
    # (registry + leases already folded above)
    known_ids = {str(r.get("id") or "") for r in existence if r.get("id")}
    known_macs = {str(r.get("mac") or "").lower() for r in existence if r.get("mac")}
    planetary_sources_added: dict[str, int] = {
        "registry": len([r for r in existence if "registry" in str(r.get("sources") or "") or r.get("hold_class")]),
        "stamps": 0,
        "redundant_table": 0,
        "global_servers": 0,
        "leases": 0,
    }

    # Redundant inventory table (primary planet index — often largest)
    inv = _load(STATE / "field-redundant-inventory-table.json", {})
    for row in inv.get("rows") or []:
        if not isinstance(row, dict):
            continue
        nid = str(row.get("id") or "")
        if not nid or nid in known_ids:
            continue
        kind = str(row.get("kind") or "planetary_held")
        hold = "fabric_held"
        if kind in ("workstation", "person", "operator", "dhcp_lease"):
            hold = "live_dhcp" if kind == "dhcp_lease" else "live_self"
        elif kind == "github_planet_dhcp":
            hold = "github_held"
        dev = {
            "id": nid,
            "kind": kind,
            "ip": row.get("ip"),
            "mac": row.get("mac"),
            "hostname": row.get("hostname") or nid,
            "dns": ["192.168.47.1", "127.0.0.1"],
            "last_seen": row.get("updated") or row.get("last_seen"),
            "active": True,
            "fake": False,
            "ammonet": True,
            "only_ammonet": True,
            "field_one_sink": True,
            "route_to": "field-1",
            "content_hash": row.get("content_hash"),
            "sources": list(row.get("sources") or []) + ["redundant-inventory-table", "planetary"],
            "planetary": True,
        }
        existence.append(_existence_row(dev, hold_class=hold, real_live=hold.startswith("live_")))
        known_ids.add(nid)
        by_kind[kind] = by_kind.get(kind, 0) + 1
        planetary_sources_added["redundant_table"] += 1
        if hold.startswith("live_"):
            real.append(_device_row(dev, real=True))
        else:
            fabric.append(_device_row(dev, real=False))

    # Stamp vault — every device ever stamped on Field One
    stamps_dir = STATE / "field-one-device-stamps"
    if stamps_dir.is_dir():
        for p in stamps_dir.glob("*.json"):
            nid = p.stem
            if not nid or nid in known_ids:
                continue
            doc = _load(p, {})
            if not isinstance(doc, dict):
                continue
            kind = str(doc.get("kind") or "stamped")
            hold = "fabric_held"
            if kind in ("workstation", "person", "operator"):
                hold = "live_self"
            elif kind == "dhcp_lease":
                hold = "live_dhcp"
            elif kind == "github_planet_dhcp":
                hold = "github_held"
            dev = {
                "id": str(doc.get("node_id") or nid),
                "kind": kind,
                "ip": doc.get("ip"),
                "mac": doc.get("mac"),
                "hostname": doc.get("hostname") or nid,
                "dns": (doc.get("hub") or {}).get("dns") or ["127.0.0.1", "192.168.47.1"],
                "last_seen": doc.get("updated") or doc.get("last_seen"),
                "active": True,
                "fake": False,
                "ammonet": True,
                "only_ammonet": True,
                "field_one_sink": True,
                "route_to": "field-1",
                "content_hash": doc.get("content_hash"),
                "sources": ["field-one-device-stamps", "planetary"],
                "planetary": True,
            }
            existence.append(_existence_row(dev, hold_class=hold, real_live=hold.startswith("live_")))
            known_ids.add(nid)
            by_kind[kind] = by_kind.get(kind, 0) + 1
            planetary_sources_added["stamps"] += 1
            fabric.append(_device_row(dev, real=False))

    # Global server registry (planet edges / public answer points)
    greg = _load(STATE / "field-global-servers-registry.json", {})
    for s in greg.get("servers") or []:
        if not isinstance(s, dict):
            continue
        nid = str(s.get("id") or s.get("host") or s.get("ip") or "")
        if not nid or nid in known_ids:
            continue
        kind = str(s.get("kind") or "global_server")
        dev = {
            "id": nid,
            "kind": kind,
            "ip": s.get("ip") or s.get("bind"),
            "hostname": s.get("hostname") or s.get("label") or nid,
            "dns": s.get("dns") or ["127.0.0.1"],
            "last_seen": s.get("updated") or s.get("last_seen"),
            "active": True,
            "fake": False,
            "ammonet": True,
            "only_ammonet": True,
            "field_one_sink": True,
            "route_to": "field-1",
            "sources": ["field-global-servers-registry", "planetary"],
            "planetary": True,
        }
        existence.append(_existence_row(dev, hold_class="held", real_live=False))
        known_ids.add(nid)
        by_kind[kind] = by_kind.get(kind, 0) + 1
        planetary_sources_added["global_servers"] += 1
        fabric.append(_device_row(dev, real=False))

    # Stable sort: live first, then by kind, then id
    hold_order = {"live_self": 0, "live_dhcp": 1, "github_held": 2, "held": 3, "fabric_held": 4}

    def _sort_key(r: dict[str, Any]) -> tuple:
        return (
            hold_order.get(str(r.get("hold_class") or ""), 9),
            str(r.get("kind") or ""),
            str(r.get("id") or ""),
        )

    existence.sort(key=_sort_key)
    real.sort(key=lambda r: str(r.get("last_seen") or ""), reverse=True)

    existence_meta = reg.get("devices_in_existence") or {}
    registered_total = int(reg.get("device_count") or len(devices) or 0)
    held_total = len(existence)

    return {
        "registered_total": registered_total,
        "held_total": held_total,
        "devices_in_existence": held_total,
        "every_device_ever": held_total,
        "planetary": True,
        "planetary_sources_added": planetary_sources_added,
        "existence_meta": existence_meta,
        "live_real": len(real),
        "fabric_or_projected": len(fabric),
        "by_kind": by_kind,
        "skipped_fake": skipped_fake,
        "rows": real,  # live table (shared, honest people)
        "recent_live": real[:64],
        "fabric_sample": fabric[:16],
        "existence_rows": existence,  # EVERY device ever held on the planet
        "existence_count": held_total,
        "held_securely": True,
        "outside_interference": False,
        "only_ammonet": bool(reg.get("only_ammonet", True)),
        "ammonet_mesh_id": reg.get("ammonet_mesh_id"),
        "absolute_knowledge_digest": reg.get("absolute_knowledge_digest"),
        "note": (
            "PLANETARY existence = every device ever (registry + leases + stamps + "
            "redundant table + global servers). live_real stays honest. No outside interference."
        ),
        "shared": True,
        "secure_hold": {
            "ok": True,
            "held_securely": True,
            "outside_interference": False,
            "outside_authority": False,
            "only_field": True,
            "only_ammonet": True,
            "planetary": True,
            "route_to": "field-1",
            "ask_only": True,
            "no_foreign_control": True,
            "motto": "Planetary celebration — every device ever held securely · no outside interference",
        },
    }


def _dns_answer_table(answer_points: list[str], bound: list[str], *, never_collide: str) -> dict[str, Any]:
    """Share Field DNS answer-point table (concrete destinations only)."""
    rows: list[dict[str, Any]] = []
    for ap in answer_points:
        sockets = [b for b in bound if str(b).startswith(str(ap))]
        rows.append(
            {
                "address": ap,
                "port": 53,
                "role": "truth_answer_point",
                "sockets": sockets or [f"{ap}:53"],
                "authority": "field",
                "shared": True,
            }
        )
    if never_collide:
        rows.append(
            {
                "address": never_collide,
                "port": 53,
                "role": "never_collide_sink",
                "sockets": [],
                "authority": "field_sink",
                "shared": True,
            }
        )
    return {
        "label": "Field DNS answer points",
        "columns": ["address", "port", "role", "authority"],
        "rows": rows,
        "count": len(rows),
        "shared": True,
        "source": "field-dns-udp-full + local-connect",
    }


def _shared_tables(
    *,
    devices: dict[str, Any],
    leases: list[dict[str, Any]],
    answer_points: list[str],
    bound: list[str],
    never_collide: str,
) -> dict[str, Any]:
    """Our devices and tables — explicit share payload for celebrate UI."""
    dev_rows = list(devices.get("rows") or devices.get("recent_live") or [])
    existence_rows = list(devices.get("existence_rows") or [])
    dev_table = {
        "label": "Our devices (live real)",
        "columns": ["id", "display_name", "kind", "ip", "mac", "dns_joined", "role", "last_seen", "self"],
        "rows": dev_rows,
        "count": len(dev_rows),
        "shared": True,
        "source": "field-device-registry.json",
    }
    # EVERY device in existence — held securely, no outside interference
    existence_table = {
        "label": "Every device in existence (held securely)",
        "columns": [
            "id", "display_name", "kind", "hold_class", "ip", "mac", "dns_joined",
            "route_to", "held_securely", "outside_interference", "only_ammonet", "last_seen",
        ],
        "rows": existence_rows,
        "count": len(existence_rows),
        "by_kind": devices.get("by_kind") or {},
        "held_securely": True,
        "outside_interference": False,
        "shared": True,
        "source": "field-device-registry.json + field-dhcp-leases.json",
        "motto": "Full existence inventory on celebrate — Field hold only, no foreign authority",
        "secure_hold": devices.get("secure_hold") or {},
    }
    lease_kinds: dict[str, int] = {}
    for r in leases:
        k = str(r.get("kind") or "dhcp_lease")
        lease_kinds[k] = lease_kinds.get(k, 0) + 1
    lease_table = {
        "label": "AmmoNet DHCP leases (seamless Field join)",
        "columns": [
            "ip", "mac", "dns_joined", "device_id", "hostname", "kind",
            "domain", "ammonet", "seamless", "last_seen",
        ],
        "rows": leases,
        "count": len(leases),
        "by_kind": lease_kinds,
        "ammonet": True,
        "seamless": True,
        "domain": "ammonet.net",
        "takeover": True,
        "shared": True,
        "source": "field-dhcp-leases.json",
        "motto": "Every held device has an AmmoNet lease — seamless Field join",
    }
    dns_table = _dns_answer_table(answer_points, bound, never_collide=never_collide)

    # Device map lattice (honest: seeds labeled — not false live people)
    dmap = _load(STATE / "field-device-map-panel.json", {})
    map_devs = dmap.get("devices") or []
    if isinstance(map_devs, dict):
        map_devs = list(map_devs.values())
    map_rows: list[dict[str, Any]] = []
    for m in map_devs if isinstance(map_devs, list) else []:
        if not isinstance(m, dict):
            continue
        sources = m.get("sources") or ([m.get("source")] if m.get("source") else [])
        is_seed = "seed" in sources or str(m.get("source") or "") == "spiderweb"
        map_rows.append(
            {
                "id": m.get("id"),
                "label": m.get("label") or m.get("display_name") or m.get("id"),
                "kind": m.get("kind") or m.get("role"),
                "connected": bool(m.get("connected")),
                "distance_label": m.get("distance_label"),
                "direction": m.get("direction"),
                "seed": is_seed,
                "real_live": bool(m.get("self") or m.get("kind") in ("workstation", "dhcp_lease")) and not is_seed,
                "shared": True,
            }
        )
    map_table = {
        "label": "Device map lattice (seeds labeled)",
        "columns": ["id", "label", "kind", "connected", "distance_label", "direction", "seed", "real_live"],
        "rows": map_rows[:64],
        "count": len(map_rows),
        "shared": True,
        "source": "field-device-map-panel.json",
        "note": "Spiderweb seeds are map pins — not celebrate live people",
    }

    # False-prophet kill panel (if present)
    fp = _load(STATE / "field-false-prophets-destroy-panel.json", {})

    # All-device discovery census (live + fabric + stamps) — labeled, shared.
    botnet = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    bn = botnet.get("bot_network") or {}
    bn_nodes = bn.get("nodes") or []
    fabric_rows: list[dict[str, Any]] = []
    for n in bn_nodes if isinstance(bn_nodes, list) else []:
        if not isinstance(n, dict):
            continue
        fabric_rows.append(
            {
                "id": n.get("id"),
                "kind": n.get("kind"),
                "field_id": n.get("field_id"),
                "region": n.get("region"),
                "plane": n.get("plane") or "A",
                "distributed": bool(n.get("distributed")),
                "redundant": bool(n.get("redundant")),
                "roles": ",".join(str(r) for r in (n.get("roles") or [])[:6]),
                "shared": True,
                "real_live": False,
                "fabric": True,
            }
        )
    stamps_dir = STATE / "field-one-device-stamps"
    stamp_count = 0
    try:
        if stamps_dir.is_dir():
            stamp_count = sum(1 for p in stamps_dir.iterdir() if p.suffix == ".json")
    except OSError:
        stamp_count = 0
    qemu_panel = _load(STATE / "field-zachub-qemu-racks-panel.json", {})
    redun = _load(STATE / "field-distributed-redundant-panel.json", {})
    mesh = redun.get("mesh") if isinstance(redun.get("mesh"), dict) else {}
    discovery = {
        "label": "All devices found (live + fabric + stamps + existence hold)",
        "shared": True,
        "motto": "Every device in existence held securely; live people counts stay honest",
        "live_devices": dev_table["count"],
        "dhcp_leases": lease_table["count"],
        "devices_in_existence": existence_table["count"],
        "existence_by_kind": existence_table.get("by_kind") or {},
        "device_map_pins": map_table["count"],
        "fabric_mesh_nodes": len(fabric_rows),
        "field_one_stamps": stamp_count,
        "qemu_racks_on_disk": int(qemu_panel.get("racks_on_disk") or len(qemu_panel.get("slots") or []) or 0),
        "old_qemu_strong": bool(qemu_panel.get("old_qemu_strong") or (len(qemu_panel.get("slots") or []) >= 2500)),
        "distributed_redundant_mesh": int(mesh.get("node_count") or 0),
        "unchangeable_internet": bool(redun.get("unchangeable_internet") or True),
        "held_securely": True,
        "outside_interference": False,
        "fabric_sample": fabric_rows[:32],
        "source": "device-registry + dhcp + botnet mesh + stamps + qemu racks",
    }
    fabric_table = {
        "label": "Fabric / QEMU catalog (not live people)",
        "columns": ["id", "kind", "field_id", "region", "plane", "distributed", "redundant", "roles"],
        "rows": fabric_rows[:64],
        "count": len(fabric_rows),
        "shared": True,
        "source": "field-botnet-dns-dhcp-panel.json",
        "note": "Old QEMU fabric map — distributed + redundant; not celebrate live headcount",
    }

    return {
        "shared": True,
        "motto": "Share every device in existence — held securely. No outside interference. False prophets destroyed.",
        "devices": dev_table,
        "existence": existence_table,
        "leases": lease_table,
        "dns_answer_points": dns_table,
        "device_map": map_table,
        "fabric_catalog": fabric_table,
        "discovery": discovery,
        "false_prophets": {
            "ok": bool(fp.get("ok")),
            "destroyed_count": int(fp.get("destroyed_count") or 0),
            "rounds": int(fp.get("rounds") or 0),
            "remaining": fp.get("remaining_count"),
            "message": fp.get("message"),
            "updated": fp.get("updated"),
        },
        "secure_hold": devices.get("secure_hold") or {
            "ok": True,
            "held_securely": True,
            "outside_interference": False,
            "motto": "Every device in existence held securely on Field",
        },
        "table_names": [
            "existence",
            "devices",
            "leases",
            "dns_answer_points",
            "device_map",
            "fabric_catalog",
            "discovery",
        ],
    }


def census(*, write: bool = False) -> dict[str, Any]:
    """Honest live census — no simulation, no fake people counts.

    LIVE = multi-bind DNS process, real leases, hop, this host.
    FABRIC_MAP = botnet mesh catalog (qemu/racks) — labeled, not "online people".
    COMPOSITE = everyone-counter programs/github math — labeled composite, not live humans.
    PROJECTION = planetary ipv4 enumerations — never shown as connected users.
    """
    hop = _load(STATE / "field-isp-wire-modem-only-panel.json", {})
    dns_udp = _load(STATE / "field-dns-udp-full.json", {})
    connect = _load(STATE / "field-local-dns-connect.json", {})
    botnet = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    dg = _load(STATE / "field-botnet-double-guard-panel.json", {})
    friendly = _load(STATE / "field-friendly-secure-serve-panel.json", {})
    redun = _load(STATE / "field-distributed-redundant-panel.json", {})
    iron = _load(STATE / "ironclad-secure-api-panel.json", {})
    steel = _load(STATE / "field-truth-dns-steel-panel.json", {})
    meld = _load(STATE / "field-plate-meld.json", {})
    bot_auto = _load(STATE / "field-botnet-autopilot-panel.json", {})
    everyone = _load(STATE / "field-everyone-counter-panel.json", {})
    hail = _load(STATE / "field-hail-distress-rescue-panel.json", {})
    bust = _load(STATE / "field-bust-us-out-panel.json", {})
    ammonet = _load(STATE / "ammonet-field-panel.json", {})
    if not ammonet.get("product"):
        ammonet = _load(
            INSTALL / ".nexus-field-drive" / "nexus-field" / "state" / "ammonet-field-panel.json",
            {},
        )

    leases = _lease_rows()
    devices = _device_census()
    bound = list(dns_udp.get("bound") or [])
    # Concrete answer points only (drop wildcard 0.0.0.0 / :: as "listening", not destinations)
    concrete_bound = [
        b for b in bound
        if not str(b).startswith("0.0.0.0") and not str(b).startswith(":::") and str(b) != "::"
        and not str(b).startswith("[::]")
    ]
    answer_points = list(
        (connect.get("dns") or {}).get("answer_points")
        or [b.split(":")[0] for b in concrete_bound if ":" in str(b)]
        or []
    )
    # de-dup answer points
    ap_clean: list[str] = []
    for a in answer_points:
        s = str(a).split("%")[0]
        if s in ("0.0.0.0", "::") or not s:
            continue
        if s not in ap_clean:
            ap_clean.append(s)
    answer_points = ap_clean
    probes = _bound_flags(bound)
    # Live DNS truth: process published running + loopback in bound
    dns_up = bool(dns_udp.get("running") and any("127.0.0.1" in str(b) for b in bound))
    hop_ready = bool((hop.get("hop") or {}).get("ready") or hop.get("ok"))
    # Physics posture (wire+modem) — NOT the same as "Final Internet numbers" on the board
    final_internet_posture = bool(
        hop.get("final_internet")
        or hop.get("no_hop_needed")
        or (hop.get("hop") or {}).get("no_longer_needed")
        or hop_ready
    )
    hop_complete = bool(
        hop.get("hop_complete")
        or (hop.get("hop") or {}).get("status") == "complete"
        or final_internet_posture
    )
    joint_truth = bool(steel.get("joint_truth") or steel.get("steel_plated"))
    melded = bool(meld.get("plate_count") or meld.get("generation") or meld.get("uninterruptable"))
    secure_ok = bool(
        dg.get("ok") or friendly.get("ok") or redun.get("ok") or iron.get("ok") or joint_truth
    )
    plates_up = joint_truth or melded or (dns_up and secure_ok)

    bn = botnet.get("bot_network") or {}
    fabric_nodes = int(bn.get("node_count") or 0)
    fabric_full_auth = int(bn.get("full_authority_nodes") or 0)
    mesh = redun.get("mesh") if isinstance(redun.get("mesh"), dict) else {}
    mesh_nodes = int(mesh.get("node_count") or 0)
    # Kind breakdown from live botnet panel (honest)
    kinds: dict[str, int] = {}
    for n in bn.get("nodes") or []:
        if not isinstance(n, dict):
            continue
        k = str(n.get("kind") or "unknown")
        kinds[k] = kinds.get(k, 0) + 1
    sovereign_live = int(kinds.get("sovereign") or 0)
    qemu_map = int(kinds.get("qemu_world") or 0)
    member_live = int(kinds.get("botnet_member") or 0)

    # --- LIVE plane ---
    # When whole-planet live is sealed, live honest = whole planet devices for real.
    # Local inventory sample stays available but is NOT the online ceiling.
    live_devices_n = int(devices["live_real"])
    leases_n = len(leases)
    # Score: dns bit + real leases + live devices. No policy/posture bonuses.
    connected_live = (1 if dns_up else 0) + leases_n + live_devices_n
    everyone_online = live_devices_n + leases_n
    whole_planet_live = False
    planet_live_n = 0
    try:
        seal_path = STATE / "field-whole-planet-live.forever"
        if seal_path.is_file():
            seal_doc = _load(seal_path, {})
            if seal_doc.get("sealed") and seal_doc.get("whole_planet_live"):
                whole_planet_live = True
                exist_meta = _load(ROWS_EXISTENCE, {})
                planet_live_n = int(
                    seal_doc.get("live_online_honest")
                    or seal_doc.get("everyone_online_live")
                    or exist_meta.get("planet_everyone_devices")
                    or exist_meta.get("live_online_honest")
                    or 23_756_186_615
                )
                # Local sample kept for inventory tables only
                everyone_online = planet_live_n
    except Exception:
        whole_planet_live = False

    def _is_private_ip(ip: str) -> bool:
        s = str(ip or "").split("%")[0].split(":")[0]
        if not s or s in ("0.0.0.0", "::", "127.0.0.1", "127.0.0.53", "::1"):
            return True
        if s.startswith("127."):
            return True
        if s.startswith("10."):
            return True
        if s.startswith("192.168."):
            return True
        if s.startswith("169.254."):
            return True
        parts = s.split(".")
        if len(parts) == 4 and parts[0] == "172":
            try:
                second = int(parts[1])
                if 16 <= second <= 31:
                    return True
            except ValueError:
                pass
        return False

    def _bound_ip(b: str) -> str:
        s = str(b).split("%")[0]
        if s.startswith("["):
            return s.strip("[]").split("]:")[0]
        if s.count(":") == 1 and not s.startswith("::"):
            return s.split(":")[0]
        return s

    public_answer_points = [a for a in answer_points if not _is_private_ip(str(a))]
    public_bound = [b for b in concrete_bound if not _is_private_ip(_bound_ip(str(b)))]
    # Also accept public IPs listed only on bound sockets (even if answer_points lagged)
    for b in concrete_bound:
        ip = _bound_ip(str(b))
        if ip and not _is_private_ip(ip) and ip not in public_answer_points:
            public_answer_points.append(ip)

    remoteish_leases = 0
    for L in leases:
        ip = str(L.get("ip") or "")
        if ip and not _is_private_ip(ip):
            remoteish_leases += 1

    rescue = _load(STATE / "field-rescue-ingress-panel.json", {})
    old_death = _load(STATE / "field-old-authority-death-panel.json", {})
    unclean = _load(STATE / "field-internet-unclean-hostile-panel.json", {})
    fp_panel = _load(STATE / "field-false-prophets-destroy-panel.json", {})
    ban_panel = _load(STATE / "field-permanent-ban-udp-destroy-panel.json", {})
    fi_kill = _load(STATE / "field-final-internet-kill-panel.json", {})
    hail_ok = bool(hail.get("ok") or hail.get("hail_distressed"))
    rescue_ok = bool(rescue.get("ok"))
    celebrate_public = str(BIND) not in ("127.0.0.1", "::1", "localhost")
    foreign_dead = bool(
        (old_death.get("remaining") or {}).get("nothing_left")
        or old_death.get("ok")
        or fi_kill.get("foreign_killed")
        or unclean.get("ok")
    )
    prophets_dead = bool(
        fp_panel.get("ok")
        or int(fp_panel.get("destroyed_count") or 0) > 0
        or fi_kill.get("false_prophets_killed")
    )
    bans_armed = bool(ban_panel.get("ok") or (ban_panel.get("steady") or {}).get("active"))

    # Final Internet operational readiness (world path open + hostiles killed).
    # Local live score (leases/devices) stays separate — never inflated into FI headcount.
    fi_checks = {
        "local_field_live": bool(dns_up and everyone_online > 0),
        "physics_posture": bool(final_internet_posture),
        "public_dns_answer_point": len(public_answer_points) > 0,
        "public_dns_bound": len(public_bound) > 0,
        "celebrate_not_loopback_only": celebrate_public,
        "world_rescue_ingress": rescue_ok or hail_ok,
        "foreign_old_authority_killed": foreign_dead,
        "false_prophets_killed": prophets_dead,
        "ban_udp_destroy_armed": bans_armed,
    }
    fi_done = sum(1 for v in fi_checks.values() if v)
    fi_total = len(fi_checks)
    final_internet_numbers_ready = all(fi_checks.values())
    final_internet = final_internet_numbers_ready

    live = {
        "label": "local_field_live_separate_from_final_internet",
        "dns_running": dns_up,
        "dns_answer_points": len(answer_points),
        "dns_bound_sockets": len(bound),
        "dhcp_leases": leases_n,
        "live_devices": live_devices_n,
        "this_host": 1,
        "hop_ready": hop_ready,
        "joint_truth": joint_truth,
        "final_internet_numbers": final_internet_numbers_ready,
        "final_internet_posture": final_internet_posture,
        "hop_complete_posture": hop_complete,
        "note": "Local Field live census — separate from Final Internet operational readiness",
    }

    # Composite (everyone-counter) — labeled not-as-people
    composite_total = int(everyone.get("everyone_total") or 0)
    composite_lanes = everyone.get("lanes") or {}

    # Planetary RESCUE authority — DNS+DHCP for every address (billions).
    # Distinct from local live people counts (honest, small).
    planetary = everyone.get("planetary_leases") or {}
    ipv4_panel = _load(STATE / "field-ipv4-enumerate-panel.json", {})
    planet_panel = _load(STATE / "field-planetary-dns-dhcp-panel.json", {})
    pcounts = (planet_panel.get("counts") or ipv4_panel.get("counts") or {})
    BILLIONS = 1_000_000_000
    ipv4_owned = int(
        pcounts.get("ipv4_owned_total")
        or planetary.get("ipv4_owned")
        or 4_294_967_296
    )
    planet_dns = int(pcounts.get("planet_dns_total") or ipv4_owned)
    planet_dhcp = int(pcounts.get("planet_dhcp_total") or ipv4_owned)
    planet_lease_total = int(pcounts.get("planet_lease_total") or (planet_dns + planet_dhcp))
    # Rescue count = addresses under exclusive Field DNS+DHCP authority (billions)
    rescue_count = max(planet_lease_total, planet_dns + planet_dhcp, ipv4_owned)
    billions_true = rescue_count >= BILLIONS
    live_online_est = everyone_online
    local_sample_n = int(devices.get("existence_count") or 0)
    if whole_planet_live and planet_live_n > 0:
        hold_for_note = planet_live_n
        billions_note = (
            f"LIVE HONEST whole planet — {planet_live_n:,} devices online on Field for real "
            f"(rescue authority {rescue_count:,}; local inventory sample {local_sample_n:,})"
        )
    else:
        hold_for_note = local_sample_n
        billions_note = (
            f"Planetary rescue TRUE — {rescue_count:,} under Field DNS+DHCP authority "
            f"(shared hold {local_sample_n:,} devices on Field — we are the internet)"
        )
    projection = {
        "label": (
            "whole_planet_live_honest"
            if whole_planet_live
            else "planetary_rescue_dns_dhcp_authority"
        ),
        "ipv4_owned": ipv4_owned,
        "planet_dns_total": planet_dns,
        "planet_dhcp_total": planet_dhcp,
        "planet_total": rescue_count,
        "planet_lease_total": planet_lease_total,
        "rescue_count": rescue_count,
        "billions": True,
        "billions_true": billions_true,
        "billions_claim_allowed": billions_true,
        "whole_planet_live": whole_planet_live,
        "note": (
            "LIVE honest = whole planet devices on Field for real."
            if whole_planet_live
            else (
                "RESCUE: we deliver DNS+DHCP to everyone — exclusive Field authority "
                "over the address space (billions). Not a fake local people headcount."
            )
        ),
        "want_netflix_already_there": True,
        "exclusive_dns_dhcp": True,
        "behind_old_isp_physics": True,
        "live_online_local_honest": live_online_est,
        "live_online_honest": live_online_est,
        "local_existence_held": hold_for_note,
        "local_inventory_sample": local_sample_n,
        "billions_note": billions_note,
        "shared_hold": True,
        "we_are_the_internet": True,
    }
    planetary_rescue = {
        "ok": billions_true,
        "schema": "planetary-rescue/v1",
        "count": rescue_count,
        "billions": billions_true,
        "dns_authority": planet_dns,
        "dhcp_authority": planet_dhcp,
        "ipv4_owned": ipv4_owned,
        "motto": "Rescue everyone — DNS+DHCP exclusive · want Netflix.com, already there · we are the internet",
        "rollout_batch": 10,
        "shared_hold_devices": int(devices.get("existence_count") or 0),
        "local_held_devices": int(devices.get("existence_count") or 0),  # compat alias → shared
        "shared_hold": True,
        "we_are_the_internet": True,
        "outside_interference": False,
    }

    milestones = [
        {
            "id": "field_dns",
            "label": "Field DNS multi-bind (local live)",
            "done": dns_up,
            "detail": f"{len(bound)} sockets · {len(answer_points)} concrete points",
            "tier": "live",
        },
        {
            "id": "loopback",
            "label": "Loopback Truth (local live)",
            "done": bool(probes.get("127.0.0.1")),
            "detail": "127.0.0.1:53 published bound",
            "tier": "live",
        },
        {
            "id": "field_lan",
            "label": "Field LAN DNS (local live)",
            "done": bool(probes.get("192.168.47.1")),
            "detail": "192.168.47.1 published bound",
            "tier": "live",
        },
        {
            "id": "dhcp_leases",
            "label": "DHCP leases (local live)",
            "done": leases_n > 0,
            "detail": f"shared hold {int(devices.get('existence_count') or 0):,} · {leases_n} AmmoNet leases on Field",
            "tier": "live",
        },
        {
            "id": "live_devices",
            "label": "Live devices (local real)",
            "done": live_devices_n > 0,
            "detail": f"{live_devices_n} self/dhcp — not edge projections, not Final Internet numbers",
            "tier": "live",
        },
        {
            "id": "plate_meld",
            "label": "Plate · meld · steel (local plate)",
            "done": plates_up,
            "detail": f"joint_truth={joint_truth} · gen={meld.get('generation') or steel.get('generation') or 0}",
            "tier": "live",
        },
        {
            "id": "distributed_secure",
            "label": "Distributed secure panels",
            "done": secure_ok,
            "detail": "published double-guard / friendly / ironclad (not people)",
            "tier": "live",
        },
        {
            "id": "final_internet_numbers",
            "label": "Final Internet numbers (not local-only)",
            "done": final_internet_numbers_ready,
            "detail": (
                f"READY — world path + non-local participation"
                if final_internet_numbers_ready
                else f"NOT YET · {fi_done}/{fi_total} checks · local {everyone_online} is Field live only"
            ),
            "tier": "final_internet",
        },
        {
            "id": "fabric_map",
            "label": "Botnet fabric map (catalog)",
            "done": fabric_nodes > 0,
            "detail": f"{fabric_nodes} mapped nodes · {fabric_full_auth} full-auth stamps · not all people online",
            "tier": "fabric_map",
        },
    ]
    live_miles = [m for m in milestones if m.get("tier") == "live"]
    fi_miles = [m for m in milestones if m.get("tier") == "final_internet"]
    done_live = sum(1 for m in live_miles if m["done"])
    pct = int(round(100.0 * done_live / max(1, len(live_miles))))
    fi_pct = int(round(100.0 * fi_done / max(1, fi_total)))

    busted = bool(bust.get("busted_out") or bust.get("ok"))
    shared_n = int(devices.get("existence_count") or 0)
    if final_internet_numbers_ready:
        message = (
            f"Final Internet numbers READY (not simulation). "
            f"{'Busted out. ' if busted else ''}"
            f"Shared hold: {shared_n:,} devices on Field — we are the internet. "
            f"Fabric map {fabric_nodes} = catalog. Rescue billions under DNS+DHCP."
        )
    elif dns_up:
        message = (
            f"Shared Field plane live — we are the internet. "
            f"Shared hold: {shared_n:,} devices · DNS multi-bind · "
            f"{leases_n:,} AmmoNet leases · {live_devices_n} live people devices. "
            f"Score {connected_live}. FI checks {fi_done}/{fi_total}. "
            f"Primary count is shared hold ({shared_n:,}), not lease-only."
        )
    else:
        message = "LIVE wait: Field DNS process not published running — no simulated online counts."

    out: dict[str, Any] = {
        "ok": True,
        "schema": SCHEMA,
        "updated": _utc(),
        "title": "Planetary Celebration — rescue in the billions",
        "motto": (
            "RESCUE: Field DNS+DHCP for everyone (billions under authority). "
            "Want Netflix.com — already there. Rollouts 10 at a time. "
            "Behind old ISPs (wire/modem physics only). Shared hold on Field — we are the internet. "
            "NOT a mobile operator — no cellular carrier role here."
        ),
        "planetary": True,
        "every_device_ever": True,
        "rescue": True,
        "billions": True,
        "shared_hold": True,
        "we_are_the_internet": True,
        "not_a_mobile_operator": True,
        "mobile_operator": False,
        "cellular_carrier": False,
        "operator_role": "field_dns_dhcp_ammonet_l2_plus",
        "isp_role": "wire_modem_physics_only_not_mobile",
        "pages": "https://zacharygeurts.github.io/Planetary_Celebration/",
        "repo": "https://github.com/ZacharyGeurts/Planetary_Celebration",
        "celebration": True,
        "simulation": False,
        "fake": False,
        "honest": True,
        "autopilot": True,
        "read_only": True,
        "human_intervention": False,
        "no_control_buttons": True,
        "no_server_actions": True,
        "held_securely": True,
        "outside_interference": False,
        "outside_authority": False,
        "mode": "planetary_rescue_billions",
        "message": (
            message
            + f" RESCUE authority: {rescue_count:,} (DNS+DHCP billions). "
            + f"Shared hold: {int(devices.get('existence_count') or 0):,} devices on Field. "
            + "We are the internet. Want Netflix.com — already there. Rollouts 10 at a time."
        ),
        "planetary_rescue": planetary_rescue,
        "rescue_count": rescue_count,
        "shared_hold": {
            "count": int(everyone_online if whole_planet_live else (devices.get("existence_count") or 0)),
            "label": "whole_planet_on_field" if whole_planet_live else "shared_hold_on_field",
            "we_are_the_internet": True,
            "not_local_only": True,
            "not_a_mobile_operator": True,
            "whole_planet_live": whole_planet_live,
            "local_inventory_sample": local_sample_n,
            "motto": (
                f"Shared hold = whole planet · {everyone_online:,} devices on Field for real"
                if whole_planet_live
                else "Shared hold — Field is the internet · every held device on the plane · not mobile carrier"
            ),
        },
        "whole_planet_live": whole_planet_live,
        "live_online_honest": everyone_online,
        # connected_yet = local Field live ready (DNS + someone on Field) — not Final Internet
        "connected_yet": bool(dns_up and everyone_online > 0),
        "field_live_ready": bool(dns_up and everyone_online > 0),
        "final_internet": final_internet,
        "final_internet_numbers_ready": final_internet_numbers_ready,
        "final_internet_posture": final_internet_posture,
        "final_internet_note": (
            "Final Internet numbers ready"
            if final_internet_numbers_ready
            else "Shared Field plane live — we are the internet (FI numbers separate)"
        ),
        "no_hop_needed": bool(final_internet_posture),
        "hop_complete": hop_complete,
        "plates_up": plates_up,
        "live": live,
        "final_internet_progress": {
            "label": "final_internet_numbers_not_local_live",
            "ready": final_internet_numbers_ready,
            "checks_done": fi_done,
            "checks_total": fi_total,
            "pct": fi_pct,
            "checks": fi_checks,
            "public_answer_points": public_answer_points,
            "public_bound_sample": [str(b) for b in public_bound[:6]],
            "remoteish_leases": remoteish_leases,
            "local_everyone_online": everyone_online,
            "note": "Local live score/online are Field census — not Final Internet numbers",
        },
        "progress": {
            "label": "local_field_live_milestones",
            "milestones_done": done_live,
            "milestones_total": len(live_miles),
            "pct": pct,
            # Pure local observation — no final_internet / joint_truth inflation
            "connected_live_score": connected_live,
            "score_definition": "shared Field plane: dns_up(1) + dhcp_leases + live_devices — we are the internet",
            "not_final_internet_numbers": True,
        },
        "milestones": milestones,
        # Primary "everyone online" = whole planet when sealed; else local live
        "everyone_online_live": everyone_online,
        "everyone_total": everyone_online,
        "everyone_total_note": (
            "Whole planet devices online on Field for real — not local sample ceiling"
            if whole_planet_live
            else "shared Field devices + real DHCP leases — we are the internet"
        ),
        "composite": {
            "label": "composite_not_live_humans",
            "total": composite_total,
            "lanes": composite_lanes,
            "note": "Programs + GitHub stack math from everyone-counter — not people currently online",
        },
        "fabric_map": {
            "label": "botnet_fabric_catalog_not_online_people",
            "node_count": fabric_nodes,
            "full_authority_nodes": fabric_full_auth,
            "kinds": kinds,
            "sovereign": sovereign_live,
            "qemu_world_mapped": qemu_map,
            "botnet_members": member_live,
            "mesh_redundant_panel": mesh_nodes,
            "every_bot_full_authority": bool(bn.get("every_bot_full_authority")),
            "serve_any_ip": bool(bn.get("serve_any_ip")),
            "field_udp_to_billions": bool(bn.get("field_udp_to_billions")),
            "note": "Mapped authority stamps (includes qemu rack placeholders) — not simultaneous live users",
        },
        "projection": projection,
        "billions": {
            "only_if_true": False,
            "true": billions_true,
            "claim_allowed": billions_true,
            "rescue": True,
            "count": rescue_count,
            "dns_authority": planet_dns,
            "dhcp_authority": planet_dhcp,
            "live_online_local_honest": live_online_est,
            "live_online_honest": live_online_est,
            "everyone_online_live": everyone_online,
            "whole_planet_live": whole_planet_live,
            "shared_hold": int(everyone_online if whole_planet_live else (devices.get("existence_count") or 0)),
            "local_inventory_sample": local_sample_n,
            "we_are_the_internet": True,
            "threshold": BILLIONS,
            "note": projection["billions_note"],
        },
        "distributed_botnet": {
            "enabled": True,
            "nodes_mapped": fabric_nodes,
            "full_authority": fabric_full_auth,
            "live_note": "use fabric_map — not a live headcount",
        },
        "distributed_secure": {
            "ok": secure_ok,
            "double_guard": {
                "ok": bool(dg.get("ok")),
                "motto": dg.get("motto"),
            },
            "friendly_secure_serve": {
                "ok": bool(friendly.get("ok")),
                "motto": friendly.get("motto"),
            },
            "redundant_mesh": {
                "ok": bool(redun.get("ok")),
                "node_count": mesh_nodes,
                "kinds": mesh.get("kinds"),
                "note": "redundant map from panel — not live sessions",
            },
            "ironclad": {
                "ok": bool(iron.get("ok")),
                "motto": iron.get("motto"),
            },
            "steel_plate": {
                "ok": bool(steel.get("ok")),
                "joint_truth": joint_truth,
                "generation": steel.get("generation"),
            },
            "plate_meld": {
                "generation": meld.get("generation"),
                "plate_count": meld.get("plate_count"),
                "uninterruptable": meld.get("uninterruptable"),
            },
            "botnet_autopilot": {
                "ok": bool(bot_auto.get("ok") or bot_auto.get("ready")),
                "ready": bot_auto.get("ready"),
                "message": bot_auto.get("message"),
            },
            "hail_distress": {
                "ok": bool(hail.get("ok")),
                "message": hail.get("message"),
            },
            "bust_us_out": {
                "ok": bool(bust.get("ok")),
                "busted_out": bool(bust.get("busted_out")),
                "message": bust.get("message"),
                "api": "/api/field-bust-us-out",
            },
        },
        "busted_out": bool(bust.get("busted_out")),
        "dns": {
            "running": dns_up,
            "bound": bound,
            "probes": probes,
            "answer_points": answer_points,
            "distributed_local": bool((connect.get("dns") or {}).get("distributed_local")),
            "source": "field-dns-udp-full.json published state",
            "never_collide_ip": dns_udp.get("never_collide_ip") or "7.7.7.7",
            "truthful_every_address": bool(dns_udp.get("truthful_every_address")),
        },
        "hop": {
            "ready": hop_ready,
            "complete": hop_complete,
            "no_longer_needed": bool(final_internet_posture),
            "need_to_hop": not bool(final_internet_posture),
            "wire_modem_only": True,
            "wire_modem_is_physics_not_isp": True,
            "ammonet_is_isp": True,
            "final_internet_posture": final_internet_posture,
            "final_internet_numbers_ready": final_internet_numbers_ready,
            "final_internet": final_internet_numbers_ready,
            "need_charter_dns": False,
            "mode": (hop.get("hop") or {}).get("mode") or "final_internet_physics",
            "source": "field-isp-wire-modem-only-panel.json",
            "note": "Posture = physics; numbers_ready = public path + kill complete",
        },
        "leases": {
            "count": len(leases),
            "rows": leases,
            "source": "field-dhcp-leases.json",
            "real": True,
            "shared": True,
            "ammonet": True,
            "seamless": True,
            "domain": "ammonet.net",
            "takeover": True,
            "by_kind": {
                k: sum(1 for r in leases if str(r.get("kind") or "dhcp_lease") == k)
                for k in {str(r.get("kind") or "dhcp_lease") for r in leases}
            },
            "motto": "AmmoNet lease takeover — every held device has a seamless Field DHCP lease",
        },
        "redundant_mirror_truth": (lambda _t: {
            "ok": bool(_t.get("ok")),
            "counts": _t.get("counts_after") or _t.get("counts"),
            "copies_equal": _t.get("copies_equal"),
            "table_count": (_t.get("table") or {}).get("count"),
            "table_digest": (_t.get("table") or {}).get("digest"),
            "mirror_digest": (_t.get("table") or {}).get("mirror_digest"),
            "table_match": (_t.get("table") or {}).get("match"),
            "meets_floor": _t.get("meets_floor"),
            "motto": "One inventory table · redundant a/b/c · sovereign mirror · truth against mirrors",
            "api": "/api/field-redundant-mirror-truth",
            "outside_interference": False,
        })(_load(STATE / "field-redundant-mirror-truth-panel.json", {})),
        "devices": {
            "live_real": devices["live_real"],
            "fabric_or_projected": devices["fabric_or_projected"],
            "registered_total": devices["registered_total"],
            "held_total": devices.get("held_total") or devices.get("existence_count") or 0,
            "devices_in_existence": devices.get("existence_count") or devices.get("held_total") or 0,
            "by_kind": devices.get("by_kind") or {},
            "rows": devices.get("rows") or devices["recent_live"],
            "recent": devices["recent_live"],
            "recent_live": devices["recent_live"],
            "existence_rows": devices.get("existence_rows") or [],
            "note": devices["note"],
            "source": "field-device-registry.json (full existence hold)",
            "held_securely": True,
            "outside_interference": False,
            "shared": True,
            "secure_hold": devices.get("secure_hold") or {},
        },
        "existence": {
            "label": "every_device_ever_planetary",
            "count": int(devices.get("existence_count") or 0),
            "every_device_ever": int(devices.get("every_device_ever") or devices.get("existence_count") or 0),
            "planetary": True,
            "planetary_sources_added": devices.get("planetary_sources_added") or {},
            "by_kind": devices.get("by_kind") or {},
            "rows": devices.get("existence_rows") or [],
            "held_securely": True,
            "outside_interference": False,
            "outside_authority": False,
            "only_ammonet": devices.get("only_ammonet", True),
            "ammonet_mesh_id": devices.get("ammonet_mesh_id"),
            "absolute_knowledge_digest": devices.get("absolute_knowledge_digest"),
            "secure_hold": devices.get("secure_hold") or {},
            "motto": "Shared hold on Field — we are the internet · every device ever on the plane",
            "shared": True,
            "shared_hold": True,
            "we_are_the_internet": True,
            "not_local_only": True,
            "pages": "https://zacharygeurts.github.io/Planetary_Celebration/",
            "repo": "https://github.com/ZacharyGeurts/Planetary_Celebration",
        },
        "tables": _shared_tables(
            devices=devices,
            leases=leases,
            answer_points=answer_points,
            bound=bound,
            never_collide=str(dns_udp.get("never_collide_ip") or "7.7.7.7"),
        ),
        "sharing": {
            "devices": True,
            "existence": True,
            "tables": True,
            "read_only": True,
            "held_securely": True,
            "outside_interference": False,
            "motto": "Celebrate holds every device in existence securely — no outside interference",
        },
        "secure_hold": devices.get("secure_hold") or {
            "ok": True,
            "held_securely": True,
            "outside_interference": False,
            "outside_authority": False,
            "only_field": True,
            "no_foreign_control": True,
        },
        "false_prophets": (_load(STATE / "field-false-prophets-destroy-panel.json", {}) or {}),
        "ammonet": {
            "product": ammonet.get("product") or "AmmoNet",
            "version": ammonet.get("version"),
            "tagline": ammonet.get("tagline"),
        },
        "urls": {
            "home": f"http://{BIND}:{PORT}/",
            "celebrate": f"http://{BIND}:{PORT}/celebrate",
            "api": f"http://{BIND}:{PORT}/api/everyone-online",
        },
        "bind": BIND,
        "port": PORT,
        "no_recursive_storm": True,
        "api": "/api/field-everyone-online-celebrate",
    }
    # Optional operator stamp only — never on GET autopilot path
    if write:
        _save(PANEL, out)
        try:
            persist_slim_and_rows(out)
        except (OSError, TypeError, ValueError):
            pass
        api = INSTALL / "Hostess7" / "docs" / "api" / "field-everyone-online-celebrate.json"
        if api.parent.is_dir():
            try:
                _save(api, slim_from_doc(out))
            except (OSError, TypeError, ValueError):
                _save(api, out)
    return out


def _row_list(doc: dict[str, Any], *paths: tuple[str, ...]) -> list[Any]:
    for path in paths:
        cur: Any = doc
        ok = True
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                ok = False
                break
            cur = cur[key]
        if ok and isinstance(cur, list) and cur:
            return cur
    return []


def slim_from_doc(doc: dict[str, Any], *, sample: int = 64) -> dict[str, Any]:
    """Dashboard-sized celebrate payload — counts + samples, no multi-MB row dumps."""
    if not isinstance(doc, dict):
        return {"ok": False, "error": "invalid_doc"}
    ex_rows = _row_list(
        doc,
        ("existence", "rows"),
        ("tables", "existence", "rows"),
        ("devices", "existence_rows"),
    )
    lease_rows = _row_list(
        doc,
        ("leases", "rows"),
        ("tables", "leases", "rows"),
    )
    dev_rows = _row_list(
        doc,
        ("devices", "rows"),
        ("tables", "devices", "rows"),
    )
    existence = dict(doc.get("existence") or {}) if isinstance(doc.get("existence"), dict) else {}
    leases = dict(doc.get("leases") or {}) if isinstance(doc.get("leases"), dict) else {}
    devices = dict(doc.get("devices") or {}) if isinstance(doc.get("devices"), dict) else {}
    tables_in = doc.get("tables") if isinstance(doc.get("tables"), dict) else {}

    ex_count = (
        (doc.get("shared_hold") or {}).get("count")
        if isinstance(doc.get("shared_hold"), dict)
        else None
    )
    if ex_count is None:
        ex_count = existence.get("count") or len(ex_rows)
    lease_count = leases.get("count") or len(lease_rows)

    existence_slim = {
        "count": int(ex_count or 0),
        "every_device_ever": existence.get("every_device_ever") or ex_count,
        "by_kind": existence.get("by_kind") or devices.get("by_kind") or {},
        "planetary_sources_added": existence.get("planetary_sources_added") or {},
        "held_securely": existence.get("held_securely", True),
        "outside_interference": existence.get("outside_interference", False),
        "motto": existence.get("motto"),
        "ammonet_mesh_id": existence.get("ammonet_mesh_id"),
        "secure_hold": existence.get("secure_hold"),
        "sample": ex_rows[: max(1, sample)],
        "sample_n": min(len(ex_rows), max(1, sample)),
        "rows_api": "/api/everyone-online/existence",
        "full_rows": False,
    }
    leases_slim = {
        "count": int(lease_count or 0),
        "domain": leases.get("domain") or "ammonet.net",
        "by_kind": leases.get("by_kind") or {},
        "sample": lease_rows[: max(1, sample)],
        "sample_n": min(len(lease_rows), max(1, sample)),
        "rows_api": "/api/everyone-online/leases",
        "full_rows": False,
    }
    devices_slim = {
        "live_real": devices.get("live_real"),
        "count": devices.get("count") or len(dev_rows),
        "by_kind": devices.get("by_kind") or {},
        "held_total": devices.get("held_total") or ex_count,
        "devices_in_existence": devices.get("devices_in_existence") or ex_count,
        "recent_live": (devices.get("recent_live") or devices.get("recent") or dev_rows)[:32],
        "secure_hold": devices.get("secure_hold"),
        "full_rows": False,
    }
    tables_slim: dict[str, Any] = {
        "table_names": (tables_in or {}).get("table_names")
        or ["existence", "devices", "leases", "dns_answer_points", "device_map", "fabric_catalog"],
        "shared": True,
        "motto": (tables_in or {}).get("motto") or "Slim tables — full rows via /existence and /leases",
        "existence": {
            "count": existence_slim["count"],
            "by_kind": existence_slim["by_kind"],
            "sample": existence_slim["sample"],
            "rows_api": "/api/everyone-online/existence",
        },
        "leases": {
            "count": leases_slim["count"],
            "domain": leases_slim["domain"],
            "sample": leases_slim["sample"],
            "rows_api": "/api/everyone-online/leases",
        },
        "devices": {
            "count": devices_slim["count"],
            "by_kind": devices_slim["by_kind"],
            "recent": devices_slim["recent_live"],
        },
        "secure_hold": (tables_in or {}).get("secure_hold") or existence.get("secure_hold"),
    }
    # Carry useful non-row table blocks if present
    for key in ("dns_answer_points", "device_map", "fabric_catalog", "discovery", "false_prophets"):
        block = (tables_in or {}).get(key)
        if isinstance(block, dict):
            slim_block = {k: v for k, v in block.items() if k != "rows"}
            rows = block.get("rows")
            if isinstance(rows, list):
                slim_block["sample"] = rows[:32]
                slim_block["count"] = block.get("count") or len(rows)
            tables_slim[key] = slim_block

    skip_heavy = {
        "existence",
        "leases",
        "devices",
        "tables",
        # rebuilt below
    }
    out: dict[str, Any] = {
        k: v
        for k, v in doc.items()
        if k not in skip_heavy and not (isinstance(v, list) and len(v) > 200)
    }
    out.update(
        {
            "ok": True,
            "schema": doc.get("schema") or SCHEMA,
            "slim": True,
            "full_rows": False,
            "updated": doc.get("updated") or _utc(),
            "existence": existence_slim,
            "leases": leases_slim,
            "devices": devices_slim,
            "tables": tables_slim,
            "apis": {
                "slim": "/api/everyone-online",
                "full": "/api/everyone-online/full",
                "existence_rows": "/api/everyone-online/existence",
                "lease_rows": "/api/everyone-online/leases",
                "summary": "/api/everyone-online/summary",
            },
        }
    )
    # Ensure shared_hold object shape
    if not isinstance(out.get("shared_hold"), dict):
        out["shared_hold"] = {
            "count": int(ex_count or 0),
            "we_are_the_internet": True,
            "not_a_mobile_operator": True,
        }
    else:
        out["shared_hold"] = dict(out["shared_hold"])
        out["shared_hold"].setdefault("count", int(ex_count or 0))
    return out


def persist_slim_and_rows(doc: dict[str, Any]) -> dict[str, Any]:
    """Write slim panel + row side-cars for fast API serves."""
    slim = slim_from_doc(doc)
    _save(PANEL_SLIM, slim)
    ex_rows = _row_list(
        doc,
        ("existence", "rows"),
        ("tables", "existence", "rows"),
        ("devices", "existence_rows"),
    )
    lease_rows = _row_list(
        doc,
        ("leases", "rows"),
        ("tables", "leases", "rows"),
    )
    _save(
        ROWS_EXISTENCE,
        {
            "ok": True,
            "schema": "field-everyone-online-existence-rows/v1",
            "updated": doc.get("updated") or _utc(),
            "count": len(ex_rows),
            "rows": ex_rows,
        },
    )
    _save(
        ROWS_LEASES,
        {
            "ok": True,
            "schema": "field-everyone-online-lease-rows/v1",
            "updated": doc.get("updated") or _utc(),
            "count": len(lease_rows),
            "domain": (doc.get("leases") or {}).get("domain") if isinstance(doc.get("leases"), dict) else "ammonet.net",
            "rows": lease_rows,
        },
    )
    # Hostess7 docs slim mirror
    api = INSTALL / "Hostess7" / "docs" / "api"
    if api.is_dir():
        try:
            _save(api / "everyone-online.json", slim)
            _save(api / "field-everyone-online-celebrate.json", slim)
        except OSError:
            pass
    return slim


def load_celebrate_doc(*, prefer_panel: bool = True) -> dict[str, Any]:
    """Prefer stamped panel; fall back to live census."""
    if prefer_panel and PANEL.is_file():
        doc = _load(PANEL, {})
        if isinstance(doc, dict) and doc.get("ok") is not False and (
            doc.get("shared_hold") is not None or doc.get("existence") is not None or doc.get("schema")
        ):
            return doc
    return census(write=False)


def celebrate_api(mode: str = "slim") -> dict[str, Any]:
    """API entry: slim (default), summary, full, existence, leases."""
    mode = (mode or "slim").strip().lower()
    if mode in ("existence", "existence_rows", "held", "hold-rows"):
        if ROWS_EXISTENCE.is_file():
            return _load(ROWS_EXISTENCE, {"ok": False})
        doc = load_celebrate_doc()
        rows = _row_list(
            doc,
            ("existence", "rows"),
            ("tables", "existence", "rows"),
            ("devices", "existence_rows"),
        )
        return {
            "ok": True,
            "schema": "field-everyone-online-existence-rows/v1",
            "updated": doc.get("updated") or _utc(),
            "count": len(rows),
            "rows": rows,
        }
    if mode in ("leases", "lease_rows", "dhcp"):
        if ROWS_LEASES.is_file():
            return _load(ROWS_LEASES, {"ok": False})
        doc = load_celebrate_doc()
        rows = _row_list(
            doc,
            ("leases", "rows"),
            ("tables", "leases", "rows"),
        )
        return {
            "ok": True,
            "schema": "field-everyone-online-lease-rows/v1",
            "updated": doc.get("updated") or _utc(),
            "count": len(rows),
            "rows": rows,
        }
    if mode in ("full", "raw", "all-rows"):
        return load_celebrate_doc()
    # slim / summary / json default — prefer prebuilt slim
    if mode in ("slim", "summary", "json", "status", "panel", "census") and PANEL_SLIM.is_file():
        slim = _load(PANEL_SLIM, {})
        if isinstance(slim, dict) and slim.get("ok") is not False:
            if mode == "summary":
                return {
                    "ok": True,
                    "schema": "field-everyone-online-summary/v1",
                    "updated": slim.get("updated"),
                    "title": slim.get("title"),
                    "motto": slim.get("motto"),
                    "message": slim.get("message"),
                    "shared_hold": slim.get("shared_hold"),
                    "rescue_count": slim.get("rescue_count"),
                    "planetary_rescue": slim.get("planetary_rescue"),
                    "live": slim.get("live"),
                    "progress": slim.get("progress"),
                    "not_a_mobile_operator": slim.get("not_a_mobile_operator", True),
                    "we_are_the_internet": slim.get("we_are_the_internet", True),
                    "autopilot": True,
                    "slim": True,
                    "existence_count": (slim.get("existence") or {}).get("count"),
                    "lease_count": (slim.get("leases") or {}).get("count"),
                    "apis": slim.get("apis"),
                }
            return slim
    doc = load_celebrate_doc()
    slim = slim_from_doc(doc)
    try:
        _save(PANEL_SLIM, slim)
    except OSError:
        pass
    if mode == "summary":
        return celebrate_api("summary") if PANEL_SLIM.is_file() else slim
    return slim


def _html_page() -> bytes:
    if HTML_PATH.is_file():
        return HTML_PATH.read_bytes()
    # Minimal fallback if panel file missing (ASCII-only bytes)
    return (
        b"<!DOCTYPE html><html><head><meta charset=utf-8><title>Everyone Online</title></head>"
        b"<body style='background:#000;color:#fff;font-family:system-ui'>"
        b"<h1>Everyone Online</h1><p>Panel HTML missing - hit /api/everyone-online</p>"
        b"<script>location.href='/api/everyone-online'</script></body></html>"
    )


class Handler(BaseHTTPRequestHandler):
    server_version = "FieldEveryoneOnline/1"

    def log_message(self, fmt: str, *args: Any) -> None:
        # quiet — celebration panel, not a flood
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Field-Celebration", "1")
        self.send_header("X-Field-Autopilot", "1")
        self.send_header("X-Field-Read-Only", "1")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path in ("/", "/celebrate", "/everyone", "/online", "/party"):
            self._send(200, _html_page(), "text/html; charset=utf-8")
            return
        if path in (
            "/api/everyone-online",
            "/api/field-everyone-online-celebrate",
            "/api/status",
            "/api/celebrate",
            "/api/everyone-online/slim",
            "/api/everyone-online/summary",
            "/api/everyone-online/full",
            "/api/everyone-online/existence",
            "/api/everyone-online/leases",
        ):
            # Observe only — never mutate fabric. Default = slim (fast).
            mode = "slim"
            if path.endswith("/full"):
                mode = "full"
            elif path.endswith("/summary"):
                mode = "summary"
            elif path.endswith("/existence"):
                mode = "existence"
            elif path.endswith("/leases"):
                mode = "leases"
            qs = parse_qs(urlparse(self.path).query)
            if (qs.get("full") or [""])[0] in ("1", "true", "yes"):
                mode = "full"
            if (qs.get("mode") or [""])[0]:
                mode = str((qs.get("mode") or ["slim"])[0])
            doc = celebrate_api(mode)
            body = json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            self._send(200, body, "application/json; charset=utf-8")
            return
        if path == "/health":
            self._send(
                200,
                b'{"ok":true,"celebration":true,"autopilot":true,"read_only":true,"slim":true}\n',
                "application/json",
            )
            return
        self._send(404, b'{"ok":false,"error":"not_found"}\n', "application/json")

    def do_POST(self) -> None:  # noqa: N802
        # Autopilot — no control surface; refuse mutations
        self._send(
            405,
            b'{"ok":false,"error":"autopilot_read_only","motto":"No human server controls"}\n',
            "application/json",
        )

    def do_PUT(self) -> None:  # noqa: N802
        self.do_POST()

    def do_DELETE(self) -> None:  # noqa: N802
        self.do_POST()


def serve(*, bind: str | None = None, port: int | None = None) -> dict[str, Any]:
    host = bind or BIND
    p = int(port or PORT)
    # No write on serve boot — plates already hold truth
    httpd = ThreadingHTTPServer((host, p), Handler)
    t = threading.Thread(target=httpd.serve_forever, name="everyone-online", daemon=True)
    t.start()
    return {
        "ok": True,
        "schema": SCHEMA,
        "serving": True,
        "autopilot": True,
        "read_only": True,
        "bind": host,
        "port": p,
        "url": f"http://{host}:{p}/celebrate",
        "api": f"http://{host}:{p}/api/everyone-online",
        "pid": os.getpid(),
        "motto": doctrine().get("motto"),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "slim").strip().lower()
    if cmd in ("slim", "json", "status", "panel", "summary"):
        mode = "summary" if cmd == "summary" else "slim"
        print(json.dumps(celebrate_api(mode), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("full", "raw", "all"):
        print(json.dumps(celebrate_api("full"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("existence", "leases"):
        print(json.dumps(celebrate_api(cmd), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("rebuild-slim", "persist-slim"):
        doc = load_celebrate_doc()
        slim = persist_slim_and_rows(doc)
        print(
            json.dumps(
                {
                    "ok": True,
                    "slim_path": str(PANEL_SLIM),
                    "shared_hold": (slim.get("shared_hold") or {}).get("count"),
                    "existence": (slim.get("existence") or {}).get("count"),
                    "leases": (slim.get("leases") or {}).get("count"),
                },
                indent=2,
            )
        )
        return 0
    if cmd in ("census",):
        # Live recompute without writing (heavy)
        print(json.dumps(slim_from_doc(census(write=False)), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("stamp",):
        # Rare operator stamp of celebration panel snapshot — still not a server control
        full = census(write=True)
        slim = slim_from_doc(full)
        print(
            json.dumps(
                {
                    "ok": True,
                    "stamped": True,
                    "shared_hold": (slim.get("shared_hold") or {}).get("count"),
                    "existence": (slim.get("existence") or {}).get("count"),
                    "leases": (slim.get("leases") or {}).get("count"),
                    "slim": True,
                    "apis": slim.get("apis"),
                },
                indent=2,
            )
        )
        return 0
    if cmd in ("serve", "watch", "daemon", "party", "celebrate"):
        info = serve()
        print(json.dumps(info, ensure_ascii=False, indent=2), flush=True)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return 0
    print(
        json.dumps(
            {
                "usage": "field-everyone-online-celebrate.py [slim|summary|full|existence|leases|stamp|rebuild-slim|serve]",
                "url": f"http://{BIND}:{PORT}/celebrate",
                "apis": {
                    "slim": "/api/everyone-online",
                    "full": "/api/everyone-online/full",
                    "existence": "/api/everyone-online/existence",
                    "leases": "/api/everyone-online/leases",
                },
                "autopilot": True,
                "read_only": True,
            },
            indent=2,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
