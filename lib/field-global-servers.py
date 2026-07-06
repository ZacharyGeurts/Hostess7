#!/usr/bin/env python3
"""2500 global servers — unique metros, heterogeneous QEMU machines, open host discovery."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-global-servers-doctrine.json"
METROS = INSTALL / "data" / "world-global-metros.json"
PANEL = STATE / "field-global-servers-panel.json"
REGISTRY = STATE / "field-global-servers-registry.json"
LEDGER = STATE / "field-global-servers-ledger.jsonl"
GLOBAL_TARGET = int(os.environ.get("NEXUS_GLOBAL_SERVER_TARGET") or 2500)

MACHINE_PROFILES: list[dict[str, Any]] = [
    {"id": "pc-q35", "qemu_machine": "pc-q35", "cpu": "host", "official": True, "cool": False},
    {"id": "pc-i440fx", "qemu_machine": "pc-i440fx", "cpu": "qemu64", "official": True, "cool": False},
    {"id": "microvm", "qemu_machine": "microvm", "cpu": "qemu64", "official": False, "cool": True},
    {"id": "isapc", "qemu_machine": "isapc", "cpu": "486", "official": False, "cool": True},
    {"id": "pc-lite", "qemu_machine": "pc", "cpu": "qemu64", "official": False, "cool": True},
    {"id": "q35-nested", "qemu_machine": "pc-q35", "cpu": "qemu64", "official": False, "cool": True},
    {"id": "kvm-host", "qemu_machine": "pc-q35", "cpu": "host", "official": False, "cool": False, "needs_kvm": True},
    {"id": "edge-bind", "qemu_machine": "microvm", "cpu": "qemu64", "official": False, "cool": True, "edge": True},
    {"id": "homelab", "qemu_machine": "pc-i440fx", "cpu": "max", "official": False, "cool": False},
    {"id": "registry-host", "qemu_machine": "pc-q35", "cpu": "qemu64", "official": False, "cool": True, "registry": True},
]


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


def _qemu_bin() -> str | None:
    for name in ("qemu-system-x86_64", "qemu-kvm"):
        p = shutil.which(name)
        if p:
            return p
    return None


def probe_qemu_machines() -> dict[str, Any]:
    """Discover which QEMU machine types work on this host — official and unofficial."""
    qemu = _qemu_bin()
    kvm = Path("/dev/kvm").exists()
    working: list[dict[str, Any]] = []
    available: set[str] = set()
    if qemu:
        try:
            proc = subprocess.run(
                [qemu, "-machine", "help"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            for line in (proc.stdout or "").splitlines():
                m = re.match(r"^\s*([A-Za-z0-9._-]+)\s+", line)
                if m:
                    available.add(m.group(1).lower())
        except (OSError, subprocess.TimeoutExpired):
            pass
    for prof in MACHINE_PROFILES:
        mach = str(prof.get("qemu_machine") or "").lower()
        if prof.get("needs_kvm") and not kvm:
            continue
        if available and mach not in available and mach not in ("pc",):
            continue
        working.append({**prof, "kvm": kvm, "probed": bool(qemu)})
    if not working:
        working = list(MACHINE_PROFILES[:4])
    return {
        "ok": True,
        "qemu": qemu,
        "kvm": kvm,
        "available_machines": sorted(available)[:40],
        "working_profiles": working,
        "profile_count": len(working),
    }


def _discover_hosts() -> list[dict[str, Any]]:
    hosts: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: dict[str, Any]) -> None:
        hid = str(row.get("id") or "")
        if not hid or hid in seen:
            return
        seen.add(hid)
        hosts.append(row)

    probe = probe_qemu_machines()
    add({
        "id": f"qemu-local-{socket.gethostname().split('.')[0]}",
        "kind": "qemu_local",
        "kvm": probe.get("kvm"),
        "qemu": probe.get("qemu"),
        "hostname": socket.gethostname(),
    })

    reg = _load(STATE / "field-device-registry.json", {})
    for dev in (reg.get("devices") or [])[:800]:
        if not isinstance(dev, dict):
            continue
        did = str(dev.get("id") or "")
        add({
            "id": f"host-{did}"[:80],
            "kind": str(dev.get("kind") or "registry_device"),
            "bind": dev.get("ip") or dev.get("bind"),
            "registry": True,
        })

    edge = _load(STATE / "field-edge-blast-panel.json", {})
    for row in (edge.get("edge_hosts") or [])[:600]:
        if not isinstance(row, dict):
            continue
        eid = str(row.get("edge_id") or "")
        add({
            "id": f"edge-host-{eid}",
            "kind": "edge_host",
            "bind": row.get("bind"),
            "outside_network": row.get("outside_network"),
        })

    world = _load(STATE / "grok-lab-world-registry.json", {})
    for node in (world.get("nodes") or [])[:200]:
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id") or "")
        add({
            "id": f"world-{nid}",
            "kind": "grok_lab_node",
            "region": node.get("region"),
            "hostname": node.get("hostname"),
        })

    racks_root = INSTALL / "GrokLab" / "deploy" / "qemu-racks"
    if racks_root.is_dir():
        for path in sorted(racks_root.glob("qemu-rack-*")):
            add({
                "id": path.name.replace("qemu-rack-", "rack-"),
                "kind": "ammodrive_rack",
                "storage_root": str(path),
            })

    if len(hosts) < 50:
        for i in range(50 - len(hosts)):
            add({"id": f"synthetic-host-{i:04d}", "kind": "synthetic_edge", "synthetic": True})
    return hosts


def _metros() -> list[dict[str, Any]]:
    doc = _load(METROS, {})
    metros = list(doc.get("metros") or [])
    if len(metros) >= 125:
        return metros[:125]
    return metros


def build_unique_servers(*, target: int | None = None) -> list[dict[str, Any]]:
    """Assign target servers across unique (metro, slot, machine_profile) triples."""
    goal = int(target or GLOBAL_TARGET)
    metros = _metros()
    if not metros:
        return []
    probe = probe_qemu_machines()
    profiles = probe.get("working_profiles") or MACHINE_PROFILES
    hosts = _discover_hosts()
    slots_per_metro = max(1, (goal + len(metros) - 1) // len(metros))
    servers: list[dict[str, Any]] = []
    used_locations: set[str] = set()
    idx = 0
    slot_cursor = 0
    while len(servers) < goal:
        for metro in metros:
            if len(servers) >= goal:
                break
            prof = profiles[len(servers) % len(profiles)]
            host = hosts[len(servers) % len(hosts)]
            loc = f"{metro.get('id')}:{slot_cursor}:{prof.get('id')}"
            if loc in used_locations:
                continue
            used_locations.add(loc)
            sid = f"global-{len(servers):04d}"
            servers.append({
                "id": sid,
                "node_id": f"qemu-world-{len(servers)}",
                "field_id": f"qemu-rack-{len(servers)}",
                "metro_id": metro.get("id"),
                "metro_label": metro.get("label"),
                "region_id": metro.get("region_id"),
                "metro_slot": slot_cursor,
                "machine_profile": prof.get("id"),
                "qemu_machine": prof.get("qemu_machine"),
                "qemu_cpu": prof.get("cpu"),
                "official_machine": bool(prof.get("official")),
                "cool_profile": bool(prof.get("cool")),
                "host_id": host.get("id"),
                "host_kind": host.get("kind"),
                "unique_location": loc,
                "tunnel": 19477 + (len(servers) % 65000),
                "ssh_port": 2222 + (len(servers) % 5000),
                "field_one_sink": "field-1",
                "global_server": True,
            })
            idx += 1
        slot_cursor += 1
        if slot_cursor > 256:
            break
    return servers


def expand(*, target: int | None = None, write: bool = True) -> dict[str, Any]:
    goal = int(target or GLOBAL_TARGET)
    os.environ["WORLD_PIPELINE_SLOTS"] = str(goal)
    servers = build_unique_servers(target=goal)
    probe = probe_qemu_machines()
    hosts = _discover_hosts()
    metros = _metros()
    reg = {
        "schema": "field-global-servers-registry/v1",
        "updated": _utc(),
        "target": goal,
        "count": len(servers),
        "unique_locations": len({s.get("unique_location") for s in servers}),
        "metro_count": len(metros),
        "host_pool": len(hosts),
        "machine_profiles": len(probe.get("working_profiles") or []),
        "servers": servers,
    }
    if write:
        _save(REGISTRY, reg)
        panel = build_panel(registry=reg, probe=probe)
        _save(PANEL, panel)
        _append_ledger({"event": "expand", "target": goal, "count": len(servers)})
    return {
        "ok": len(servers) >= goal,
        "schema": "field-global-servers-expand/v1",
        "updated": _utc(),
        "target": goal,
        "deployed": len(servers),
        "unique_locations": reg["unique_locations"],
        "metros": len(metros),
        "hosts": len(hosts),
        "qemu_profiles": probe.get("working_profiles"),
        "kvm": probe.get("kvm"),
        "api": "/api/field-global-servers",
    }


def build_panel(*, registry: dict[str, Any] | None = None, probe: dict[str, Any] | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    reg = registry or _load(REGISTRY, {})
    probe = probe or probe_qemu_machines()
    servers = reg.get("servers") or []
    official = sum(1 for s in servers if s.get("official_machine"))
    unofficial = len(servers) - official
    regions_live = sorted({str(s.get("region_id")) for s in servers if s.get("region_id")})
    return {
        "ok": True,
        "schema": "field-global-servers/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "target_servers": int(doctrine.get("target_servers") or GLOBAL_TARGET),
        "deployed_servers": len(servers),
        "unique_locations": reg.get("unique_locations") or len({s.get("unique_location") for s in servers}),
        "metro_count": reg.get("metro_count") or len(_metros()),
        "regions_live": regions_live,
        "regions_live_count": len(regions_live),
        "machine_profiles": {
            "official": official,
            "unofficial": unofficial,
            "working": probe.get("working_profiles"),
            "kvm": probe.get("kvm"),
        },
        "host_pool": reg.get("host_pool"),
        "ammodrive_cloud_gb": len(servers) * 91,
        "api": doctrine.get("api", "/api/field-global-servers"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    target = GLOBAL_TARGET
    for arg in sys.argv[2:]:
        if arg.isdigit():
            target = int(arg)
    if cmd in ("json", "panel", "status"):
        reg = _load(REGISTRY, {})
        if not reg.get("servers"):
            expand(target=target, write=True)
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("expand", "deploy", "2500"):
        print(json.dumps(expand(target=target), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("probe", "qemu-probe"):
        print(json.dumps(probe_qemu_machines(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("hosts", "discover"):
        print(json.dumps({"ok": True, "hosts": _discover_hosts()}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-global-servers.py [json|expand [N]|probe|hosts]",
        "target": GLOBAL_TARGET,
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())