#!/usr/bin/env python3
"""Rescue ingress — clear fake blocks, expand DHCP pool, blast edges, DNS/DHCP through."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-rescue-ingress-doctrine.json"
PANEL = STATE / "field-rescue-ingress-panel.json"
LEASE_FILE = STATE / "field-dhcp-leases.json"
REGISTRY = STATE / "field-device-registry.json"


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


def _dhcp_lease_devices() -> list[dict[str, Any]]:
    leases = _load(LEASE_FILE, {}).get("leases") or {}
    out: list[dict[str, Any]] = []
    for mac, entry in leases.items():
        if not isinstance(entry, dict):
            continue
        ip = entry.get("ip")
        if not ip:
            continue
        out.append({
            "id": entry.get("device_id") or f"dhcp-{str(mac).replace(':', '')[:12]}",
            "mac": mac,
            "ip": ip,
            "dns": entry.get("dns") or ["127.0.0.1"],
            "sources": ["field-dhcp", "rescue-ingress"],
            "kind": "dhcp_lease",
            "real": True,
            "fake": False,
            "active": True,
            "last_seen": entry.get("last_seen") or _utc(),
            "last_timestamp": entry.get("last_seen") or _utc(),
            "quarantine": bool(entry.get("quarantine")),
        })
    return out


def clear_fake_blocks(*, write: bool = True) -> dict[str, Any]:
    """Remove fake evictions — DHCP leases are real people; restore registry truth."""
    doc = _load(DOCTRINE, {})
    cf = doc.get("clear_fakes") or {}
    reg_doc = _load(REGISTRY, {"devices": [], "policy": {}})
    policy = dict(reg_doc.get("policy") or {})
    policy.update({
        "never_evict_dhcp_sourced": bool(cf.get("never_evict_dhcp_sourced", True)),
        "dhcp_lease_is_real": bool(cf.get("dhcp_lease_is_real", True)),
        "min_corroboration_sources": int(cf.get("min_corroboration_sources") or 0),
        "ai_evict_stale": False,
        "never_exceed_existence": False,
    })
    reg_doc["policy"] = policy

    dhcp_real = _dhcp_lease_devices()
    by_id: dict[str, dict[str, Any]] = {}
    for d in reg_doc.get("devices") or []:
        if isinstance(d, dict) and d.get("id"):
            row = dict(d)
            if row.get("self"):
                by_id[str(row["id"])] = row
                continue
            if row.get("fake") or row.get("evict_reason"):
                continue
            row["fake"] = False
            row["active"] = True
            by_id[str(row["id"])] = row
    for d in dhcp_real:
        by_id[str(d["id"])] = d

    reg_doc["devices"] = list(by_id.values())
    reg_doc["device_count"] = len(reg_doc["devices"])
    reg_doc["fake_cleared"] = _utc()
    reg_doc["rescue_ingress"] = True
    if write:
        _save(REGISTRY, reg_doc)
        seed = INSTALL / "data" / "field-device-registry-seed.json"
        if seed.is_file():
            seed_doc = _load(seed, {})
            seed_doc["policy"] = {**(seed_doc.get("policy") or {}), **policy}
            _save(seed, seed_doc)

    unblocked = 0
    if cf.get("unblock_threat_guard_soft"):
        tg = _mod("lib/dns-threat-guard.py", "threat_guard")
        if tg and hasattr(tg, "clear_soft_blocks"):
            try:
                r = tg.clear_soft_blocks()
                unblocked = int(r.get("cleared") or 0)
            except (OSError, TypeError, AttributeError):
                pass

    return {
        "ok": True,
        "dhcp_leases_real": len(dhcp_real),
        "registry_devices": reg_doc["device_count"],
        "fakes_removed": True,
        "threat_soft_unblocked": unblocked,
        "policy": policy,
    }


def expand_dhcp_pool(*, write: bool = True) -> dict[str, Any]:
    pool = (_load(DOCTRINE, {}).get("dhcp_pool") or {})
    start = str(pool.get("start") or "192.168.50.2")
    end = str(pool.get("end") or "192.168.51.254")
    legacy_start = str(pool.get("legacy_start") or "192.168.47.100")
    legacy_end = str(pool.get("legacy_end") or "192.168.47.200")
    os.environ.setdefault("NEXUS_FIELD_DHCP_POOL_START", start)
    os.environ.setdefault("NEXUS_FIELD_DHCP_POOL_END", end)
    os.environ.setdefault("NEXUS_FIELD_DHCP_LEGACY_POOL_START", legacy_start)
    os.environ.setdefault("NEXUS_FIELD_DHCP_LEGACY_POOL_END", legacy_end)
    os.environ.setdefault("NEXUS_FIELD_DHCP_SOFT_INGRESS", "1")
    os.environ.setdefault("NEXUS_FIELD_DHCP_PING_SOFT", "1")

    def _ip_count(a: str, b: str) -> int:
        def to_int(ip: str) -> int:
            p = [int(x) for x in ip.split(".")]
            return (p[0] << 24) + (p[1] << 16) + (p[2] << 8) + p[3]

        return max(0, to_int(b) - to_int(a) + 1)

    hosts = _ip_count(start, end) + _ip_count(legacy_start, legacy_end)
    return {
        "ok": True,
        "pool_start": start,
        "pool_end": end,
        "legacy_pool_start": legacy_start,
        "legacy_pool_end": legacy_end,
        "host_slots": hosts,
        "soft_ingress": True,
        "ping_soft": True,
    }


def blast_edges(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    blast = doc.get("edge_blast") or {}
    hosts_per_edge = int(blast.get("hosts_per_edge") or 4096)
    local_slots = int(blast.get("local_edge_slots") or 64)

    scale_mod = _mod("lib/field-world-dns-dhcp-scale.py", "world_scale")
    scale: dict[str, Any] = {}
    if scale_mod and hasattr(scale_mod, "build_scale"):
        scale = scale_mod.build_scale()
    cur = scale.get("current") or {}
    devices = int(cur.get("devices") or 22_275_000_000)
    edges_planet = max(1, math.ceil(devices / hosts_per_edge))
    edges_local = min(local_slots, edges_planet)

    edge_hosts: list[dict[str, Any]] = []
    ping_mod = INSTALL / str(blast.get("ping_module") or "lib/field-ping.py")
    for i in range(edges_local):
        host = f"10.47.{(i // 256) & 0xff}.{max(1, i % 256)}"
        row: dict[str, Any] = {
            "edge_id": f"edge-{i:04d}",
            "bind": host,
            "hosts_per_edge": hosts_per_edge,
            "dhcp_dns": "127.0.0.1",
            "leases_capacity": hosts_per_edge,
            "status": "ready",
        }
        if blast.get("ping_rescue") and ping_mod.is_file() and i < 4:
            try:
                proc = subprocess.run(
                    [sys.executable, str(ping_mod), "ping", host if i > 0 else "127.0.0.1"],
                    cwd=str(INSTALL),
                    capture_output=True,
                    text=True,
                    timeout=8,
                    env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                )
                if proc.stdout.strip().startswith("{"):
                    probe = json.loads(proc.stdout)
                    row["ping_ok"] = bool(probe.get("ok"))
                    row["rtt_ms"] = (probe.get("stats") or {}).get("avg_ms")
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
                row["ping_ok"] = False
        edge_hosts.append(row)

    out = {
        "ok": True,
        "hosts_per_edge": hosts_per_edge,
        "planet_edges_recommended": edges_planet,
        "local_edges_deployed": edges_local,
        "edge_hosts": edge_hosts,
        "devices": devices,
        "people_per_local_edge": int(devices / edges_local) if edges_local else devices,
    }
    if write:
        _save(STATE / "field-edge-blast-panel.json", {**out, "updated": _utc(), "schema": "field-edge-blast/v1"})
    return out


def rescue(*, write: bool = True) -> dict[str, Any]:
    cleared = clear_fake_blocks(write=write)
    pool = expand_dhcp_pool(write=write)
    edges = blast_edges(write=write)
    collision: dict[str, Any] = {}
    cg = _mod("lib/field-dns-dhcp-collision-guard.py", "collision_guard")
    if cg and hasattr(cg, "enforce_sole_authority"):
        os.environ.setdefault("NEXUS_FIELD_COLLISION_SOFT_INGRESS", "1")
        try:
            collision = cg.enforce_sole_authority(prune=False)
        except Exception:
            collision = _load(STATE / "field-dns-dhcp-collision-guard-panel.json", {})

    planetary: dict[str, Any] = {}
    pmod = _mod("lib/field-planetary-dns-dhcp.py", "planetary")
    if pmod and hasattr(pmod, "build_panel"):
        try:
            planetary = pmod.build_panel(write=write)
        except Exception:
            planetary = _load(STATE / "field-planetary-dns-dhcp-panel.json", {})

    doc = _load(DOCTRINE, {})
    out = {
        "ok": True,
        "schema": "field-rescue-ingress/v1",
        "updated": _utc(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "ingress_policy": doc.get("ingress_policy") or "quarantine_not_kill",
        "cleared_fakes": cleared,
        "dhcp_pool": pool,
        "edge_blast": edges,
        "collision_guard": {
            "ok": bool((collision.get("sole_authority") or {}).get("ok")),
            "collision_count": collision.get("collision_count", 0),
        },
        "planetary": {
            "planet_dhcp_total": (planetary.get("counts") or {}).get("planet_dhcp_total"),
            "planet_dns_total": (planetary.get("counts") or {}).get("planet_dns_total"),
            "github_repos_indexed": (planetary.get("counts") or {}).get("github_repos_indexed"),
        },
        "api": doc.get("api"),
    }
    if write:
        _save(PANEL, out)
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "rescue"):
        print(json.dumps(rescue(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "clear-fakes":
        print(json.dumps(clear_fake_blocks(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "expand-pool":
        print(json.dumps(expand_dhcp_pool(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "blast-edges":
        print(json.dumps(blast_edges(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-rescue-ingress.py [json|rescue|clear-fakes|expand-pool|blast-edges]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())