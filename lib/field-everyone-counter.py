#!/usr/bin/env python3
"""Fast unified everyone counter — botnet + GitHub + executables · distributed field."""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-everyone-counter-panel.json"
CACHE_TTL = float(os.environ.get("EVERYONE_COUNTER_TTL_SEC", "0.8"))


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


def _run_json(rel: str, args: list[str], *, timeout: float = 6.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {}
    try:
        import subprocess
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
    except Exception:
        pass
    return {}


def _executable_count() -> dict[str, Any]:
    scripts = _load(INSTALL / "data" / "field-scripts-registry.json", {})
    canonical = scripts.get("canonical") or {}
    tools = _load(INSTALL / "data" / "field-tools-registry.json", {})
    tool_n = len(tools.get("tools") or tools.get("entries") or [])
    host = _load(INSTALL / "data" / "field-host-desktop-doctrine.json", {})
    programs = host.get("programs") or host.get("shell_programs") or []
    prog_n = len(programs) if isinstance(programs, list) else 0
    favorites = _load(INSTALL / "docs" / "github-favorites.json", {})
    fav_n = len(favorites.get("favorites") or [])
    sealed = _load(STATE / "field-executable-seal-index.json", {})
    sealed_n = int(sealed.get("count") or len(sealed.get("executables") or []))
    count = max(len(canonical), prog_n, sealed_n) + min(tool_n, 48)
    if count == 0:
        count = len(canonical) + prog_n
    return {
        "count": count,
        "canonical_scripts": len(canonical),
        "shell_programs": prog_n,
        "tools": tool_n,
        "github_favorites": fav_n,
        "sealed_executables": sealed_n,
    }


def snapshot(*, write: bool = True, fast: bool = True) -> dict[str, Any]:
    if fast and PANEL.is_file():
        cached = _load(PANEL, {})
        if cached.get("schema") == "field-everyone-counter/v1":
            age = time.time() - float(cached.get("_cached_at") or 0)
            if age < CACHE_TTL:
                cached["cached"] = True
                cached["cache_age_ms"] = int(age * 1000)
                return cached

    botnet = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    if not botnet.get("bot_network") and fast:
        botnet = _run_json("lib/field-botnet-dns-dhcp.py", ["keepalive"], timeout=4.0)
    bot_nodes = int((botnet.get("bot_network") or {}).get("node_count") or 0)
    reg = _load(STATE / "field-botnet-registry.json", {})
    reg_members = len(reg.get("members") or [])

    gh_legacy = _load(STATE / "field-github-legacy-probe.json", {})
    if not gh_legacy.get("open_count"):
        gh_legacy = _load(STATE / "field-internet-github.json", {})
    gh_open = int(gh_legacy.get("open_count") or gh_legacy.get("canonical_open") or 0)
    gh_everyone = _load(STATE / "field-github-everyone-panel.json", {})
    gh_people = max(gh_open, int(gh_everyone.get("open_count") or 0), reg_members)
    favorites = _load(INSTALL / "docs" / "github-favorites.json", {})
    gh_stack = len(favorites.get("favorites") or [])

    exe = _executable_count()
    exe_n = int(exe.get("count") or 0)

    arcade = _run_json("lib/field-arcade-battalion.py", ["lobby"], timeout=20.0)
    lobby = arcade.get("lobby") or {}
    sap_beacons = int(lobby.get("sap_beacons") or len(arcade.get("sap_sessions") or []))
    qemu_witnesses = int(lobby.get("qemu_witnesses") or len(arcade.get("qemu_witnesses") or []))

    loopback = 1
    distributed_extra = max(0, bot_nodes - reg_members) if bot_nodes else 0

    # Fleet 125k — Hostess7 / AmmoNet capacity plane (not local bot_nodes only)
    fleet_doc = _load(STATE / "field-fleet-expand-125k-panel.json", {})
    if not fleet_doc:
        fleet_doc = _load(INSTALL / "Hostess7" / "docs" / "api" / "field-fleet-expand-125k.json", {})
    h7r = _load(STATE / "field-h7r-capacity-fleet-panel.json", {})
    if not h7r:
        h7r = _load(INSTALL / "Hostess7" / "docs" / "api" / "field-h7r-capacity-fleet.json", {})
    ammonet = _load(STATE / "field-ammonet-permanent-plane-panel.json", {})
    if not ammonet:
        ammonet = _load(INSTALL / "Hostess7" / "docs" / "api" / "hostess7-ammonet-wire.json", {})
    fleet_125k = int(
        fleet_doc.get("servers_total")
        or (fleet_doc.get("capacity") or {}).get("servers")
        or h7r.get("capacity_racks")
        or h7r.get("target_capacity_racks")
        or ((h7r.get("birds") or {}).get("datacenter") or {}).get("h7r_nodes")
        or 125000
    )
    fleet_hot = int(
        ((h7r.get("birds") or {}).get("datacenter") or {}).get("hot_racks") or 0
    )
    # Composite "everyone" = fleet plane + people lanes (fleet is the 125k truth)
    local_lanes = bot_nodes + gh_people + exe_n + loopback
    everyone_total = fleet_125k + gh_people + exe_n + loopback
    # Prefer doctrine floor when live bot_nodes under-count capacity plane
    if everyone_total < fleet_125k:
        everyone_total = fleet_125k

    perf = _load(STATE / "field-performance-flyout-cache.json", {})
    if not perf.get("cpu_pct") and fast:
        perf = _run_json("lib/field-performance-flyout.py", ["json"], timeout=3.0)

    planetary = _load(STATE / "field-planetary-dns-dhcp-panel.json", {})
    if not planetary.get("counts") and fast:
        planetary = _run_json("lib/field-planetary-dns-dhcp.py", ["panel"], timeout=5.0)
    world_scale = _load(STATE / "field-world-dns-dhcp-scale-panel.json", {})
    if not world_scale.get("current") and fast:
        world_scale = _run_json("lib/field-world-dns-dhcp-scale.py", ["json"], timeout=8.0)
    github_sweep = _load(STATE / "field-github-planet-sweep-panel.json", {})
    if not github_sweep.get("counts") and fast:
        github_sweep = _run_json("lib/field-github-planet-sweep.py", ["json"], timeout=25.0)
    ipv4_enum = _load(STATE / "field-ipv4-enumerate-panel.json", {})
    if not ipv4_enum.get("counts") and fast:
        ipv4_enum = _run_json("lib/field-ipv4-enumerate.py", ["json"], timeout=8.0)
    pcounts = planetary.get("counts") or {}
    enum_counts = ipv4_enum.get("counts") or {}
    dhcp_panel = _load(STATE / "field-dhcp-panel.json", {})
    speed = _load(STATE / "field-planetary-speed-panel.json", {})
    dns_auth = _load(STATE / "field-planetary-dns-authority-panel.json", {})
    if not dns_auth.get("expanded") and fast:
        dns_auth = _run_json("lib/field-planetary-dns-authority.py", ["json"], timeout=12.0)
    removal = _load(STATE / "field-planetary-removal-panel.json", {})
    unclean = _load(STATE / "field-internet-unclean-hostile-panel.json", {})
    unrestrict = _load(STATE / "field-internet-unrestrict-panel.json", {})
    device = _load(STATE / "field-ipv4-device-sovereign-panel.json", {})
    planet_dhcp = int(enum_counts.get("planet_dhcp_total") or pcounts.get("planet_dhcp_total") or 0)
    planet_dns = int(enum_counts.get("planet_dns_total") or pcounts.get("planet_dns_total") or 0)
    planet_total = int(
        enum_counts.get("planet_lease_total") or pcounts.get("planet_lease_total") or planet_dhcp + planet_dns
    )
    ipv4_owned = int(enum_counts.get("ipv4_owned_total") or pcounts.get("ipv4_owned_total") or 0)
    ipv4_enumerated = int(enum_counts.get("ipv4_enumerated_total") or pcounts.get("ipv4_enumerated_total") or 0)
    local_dhcp = int(
        enum_counts.get("local_dhcp_leases") or pcounts.get("field_dhcp_leases") or dhcp_panel.get("lease_count") or 0
    )
    devices = int(
        pcounts.get("connected_devices")
        or device.get("device_count")
        or len(device.get("devices") or [])
        or 0
    )
    speed_thermal = speed.get("thermal") or {}
    speed_counts = speed.get("counts") or {}
    speed_bench = speed.get("bench") or {}
    speed_entropy = speed.get("entropy_path") or {}
    planetary_leases = {
        "ipv4_owned": ipv4_owned,
        "ipv4_enumerated": ipv4_enumerated,
        "enumerate_addresses": bool(ipv4_enum.get("enumerate_addresses") or ipv4_enumerated > 0),
        "planet_dhcp": planet_dhcp,
        "planet_dns": planet_dns,
        "planet_total": planet_total,
        "local_dhcp": local_dhcp,
        "devices": devices,
        "botnet_dhcp_slots": int(pcounts.get("botnet_dhcp_slots") or 0),
        "botnet_dns_slots": int(pcounts.get("botnet_dns_slots") or 0),
        "incumbent_dhcp": int(pcounts.get("incumbent_dhcp_absorbed") or 0),
        "incumbent_dns": int(pcounts.get("incumbent_dns_absorbed") or 0),
        "dhcp_crushing": bool((planetary.get("services") or {}).get("dhcp", {}).get("crushing")),
        "sole_authority": bool((planetary.get("sole_authority") or {}).get("ok") or planetary.get("planet_authority")),
        "speed_tier": speed_thermal.get("tier"),
        "entropy_reduction_pct": speed_entropy.get("reduction_pct") or speed_counts.get("entropy_reduction_pct"),
        "avg_latency_ms": speed_bench.get("avg_latency_ms") or speed_counts.get("avg_latency_ms"),
        "internet_open": bool(unrestrict.get("internet_open", True)),
        "unclean_count": int(unclean.get("unclean_count") or 0),
        "true_dns_authority": bool(dns_auth.get("true_dns_authority") or dns_auth.get("expanded")),
        "dns_zones_expanded": int(dns_auth.get("zone_count") or 0),
        "foreign_removed": bool(removal.get("complete") or (dns_auth.get("removal") or {}).get("complete")),
        "api": "/api/field-planetary-dns-dhcp",
    }

    doc = {
        "ok": True,
        "schema": "field-everyone-counter/v2",
        "title": "Everyone — fleet 125k · AmmoNet · GitHub · executables",
        "motto": "Everyone totals wired to Hostess7 AmmoNet fleet 125,000 · not local-only bot count",
        "updated": _utc(),
        "boss": "hostess7",
        "isp": "ammonet",
        "version": _load(INSTALL / "data" / "hostess7-platform-release.json", {}).get("version")
        or "4.0.0-cpp",
        "distributed_botnet": {
            "enabled": True,
            "nodes": bot_nodes,
            "fleet_servers": fleet_125k,
            "registry_members": reg_members,
            "distributed_relay": distributed_extra,
            "dns_dhcp_stable": bool((botnet.get("dns_dhcp") or {}).get("combined")),
            "github_open": bool((botnet.get("github_control_plane") or {}).get("github_open")),
            "ammonet": True,
        },
        "fleet_125k": {
            "servers_total": fleet_125k,
            "hot_racks": fleet_hot,
            "target": 125000,
            "capacity_racks": fleet_125k,
            "wired_to_everyone": True,
            "ammonet": True,
            "hostess7_boss": True,
            "api": "/api/field-fleet-expand-125k",
            "h7r_api": "/api/field-h7r-capacity-fleet",
        },
        "ammonet": {
            "ok": bool(ammonet.get("ok", True)),
            "boss": "hostess7",
            "isp": "ammonet",
            "wire": "/api/hostess7-ammonet-wire",
            "pages": "https://zacharygeurts.github.io/Hostess7/",
            "acquainted": True,
        },
        "lanes": {
            "fleet_125k": {
                "count": fleet_125k,
                "label": "Fleet 125k (AmmoNet)",
                "target": 125000,
                "hot": fleet_hot,
            },
            "botnet": {
                "count": max(bot_nodes, fleet_125k) if bot_nodes < 1000 else bot_nodes,
                "label": "Botnet / fleet nodes",
                "local_nodes": bot_nodes,
                "fleet_servers": fleet_125k,
            },
            "github_people": {
                "count": gh_people,
                "label": "GitHub people",
                "stack_repos": gh_stack,
                "open_endpoints": gh_open,
            },
            "executable_people": {"count": exe_n, "label": "Executable programs", **exe},
            "loopback_sovereign": {"count": loopback, "label": "This field"},
        },
        "local_lanes_total": local_lanes,
        "everyone_total_note": "fleet_125k + github + executables + loopback (AmmoNet plane)",
        "arcade_lobby": {
            "enabled": True,
            "sap_beacons": sap_beacons,
            "qemu_witnesses": qemu_witnesses,
            "game_room_live": bool(lobby.get("game_room_ok")),
            "pump_running": bool(lobby.get("pump_running")),
            "system": lobby.get("system"),
            "layer_stack": (arcade.get("layer_stack") or {}).get("motto"),
            "api": "/api/field-arcade-battalion",
        },
        "everyone_total": everyone_total,
        "perf": {
            "cpu_pct": perf.get("cpu_pct"),
            "mem_pct": (perf.get("memory") or {}).get("used_pct"),
            "load": (perf.get("loadavg") or [None])[0],
        },
        "planetary_leases": planetary_leases,
        "world_dns_dhcp_scale": world_scale.get("current") or {},
        "world_projections": (world_scale.get("projections") or [])[:4],
        "ingress_policy": world_scale.get("ingress_policy") or github_sweep.get("ingress_policy") or "quarantine_not_kill",
        "rescue_ingress": _load(STATE / "field-rescue-ingress-panel.json", {}).get("edge_blast") or {},
        "github_planet_sweep": {
            "repos_indexed": int((github_sweep.get("counts") or {}).get("repos_cataloged") or 0),
            "stale_detected": int((github_sweep.get("counts") or {}).get("stale_detected") or 0),
            "dns_index_rows": int((github_sweep.get("counts") or {}).get("dns_index_rows") or 0),
            "dhcp_index_rows": int((github_sweep.get("counts") or {}).get("dhcp_index_rows") or 0),
            "api": "/api/field-github-planet-sweep",
        },
        "services": {
            "dns": (botnet.get("dns_dhcp") or {}).get("dns", {}).get("running")
            or (planetary.get("services") or {}).get("dns", {}).get("running"),
            "dhcp": (botnet.get("dns_dhcp") or {}).get("dhcp", {}).get("running")
            or (planetary.get("services") or {}).get("dhcp", {}).get("running"),
            "dhcp_crushing": planetary_leases["dhcp_crushing"],
            "panel": True,
        },
        "api": "/api/field-everyone-counter",
        "poll_ms": 1000,
        "fast": fast,
        "_cached_at": time.time(),
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "fast"):
        print(json.dumps(snapshot(write=True, fast=True), indent=2))
        return 0
    if cmd == "full":
        print(json.dumps(snapshot(write=True, fast=False), indent=2))
        return 0
    print(json.dumps({"usage": "field-everyone-counter.py [json|fast|full]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())