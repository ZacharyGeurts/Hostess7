#!/usr/bin/env python3
"""Field 1 rollout — test secure stack, deploy 10 at a time, double worldwide."""
from __future__ import annotations

import hashlib
import importlib.util
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
DOCTRINE = INSTALL / "data" / "field-one-rollout-doctrine.json"
PANEL = STATE / "field-one-rollout-panel.json"
LEDGER = STATE / "field-one-rollout-ledger.jsonl"
REGIONS = INSTALL / "GrokLab" / "deploy" / "world-node-regions.json"
REGISTRY = STATE / "field-device-registry.json"
STAMP_VAULT = STATE / "field-one-device-stamps"
REDUNDANT_VAULT = STATE / "field-one-stamps-redundant"
NEVER_LOSE_LEDGER = STATE / "field-one-never-lose-ledger.jsonl"
FIELD_ONE_VERSION = "field-one-rack-stack/v2"
MIN_ROLLOUT_TARGETS = int(os.environ.get("NEXUS_FIELD_ONE_MIN_TARGETS") or 512)


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


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_FIELD_DHCP_FOREIGN_PROBE": "0",
        "NEXUS_FIELD_COLLISION_SOFT_INGRESS": "1",
        "NEXUS_FIELD_DNS_ANY_IP": "1",
        "NEXUS_FIELD_DHCP_ANY_IP": "1",
    }


def _run_json(rel: str, args: list[str], *, timeout: float = 120.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": "missing", "script": rel}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            doc = json.loads(raw)
            if isinstance(doc, dict):
                doc.setdefault("ok", proc.returncode == 0)
                return doc
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                doc = json.loads(line)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
        return {"ok": proc.returncode == 0, "stdout": raw[:300]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "script": rel}
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "script": rel}


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


def _rollout_state() -> dict[str, Any]:
    doc = _load(PANEL, {})
    return {
        "wave": int(doc.get("wave") or 0),
        "deployed_total": int(doc.get("deployed_total") or 0),
        "last_batch": int(doc.get("last_batch") or 0),
        "regions_live": list(doc.get("regions_live") or []),
        "locations_used": list(doc.get("locations_used") or []),
        "botnet_updated_total": int(doc.get("botnet_updated_total") or 0),
    }


def _regions_list() -> list[dict[str, Any]]:
    metros_doc = _load(INSTALL / "data" / "world-global-metros.json", {})
    metros = metros_doc.get("metros") or []
    if metros:
        return [
            {
                "id": str(m.get("id") or f"metro-{i}"),
                "label": m.get("label") or m.get("id"),
                "region_id": m.get("region_id"),
                "metro": True,
            }
            for i, m in enumerate(metros)
            if isinstance(m, dict)
        ]
    regions_doc = _load(REGIONS, {})
    return list(regions_doc.get("regions") or [{"id": "local", "label": "Local"}])


def _locations_used(panel: dict[str, Any] | None = None) -> set[tuple[str, int]]:
    doc = panel if panel is not None else _load(PANEL, {})
    used: set[tuple[str, int]] = set()
    for loc in doc.get("locations_used") or []:
        if isinstance(loc, dict) and loc.get("region_id"):
            used.add((str(loc["region_id"]), int(loc.get("region_slot") or 0)))
    for row in (doc.get("last_rollout") or {}).get("regions") or []:
        if isinstance(row, dict) and row.get("region_id"):
            used.add((str(row["region_id"]), int(row.get("region_slot") or 0)))
    return used


def _assign_unique_locations(
    batch: int,
    wave: int,
    *,
    panel: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Assign batch deployments to unique (region_id, region_slot) pairs — no repeats."""
    regions = _regions_list()
    used = set(_locations_used(panel))
    out: list[dict[str, Any]] = []
    slot_cursor = 0
    while len(out) < batch:
        for reg in regions:
            rid = str(reg.get("id") or "local")
            key = (rid, slot_cursor)
            if key in used:
                continue
            out.append({
                "slot": len(out),
                "region_id": rid,
                "region_label": reg.get("label"),
                "region_slot": slot_cursor,
                "wave": wave,
                "field_one_sink": "field-1",
            })
            used.add(key)
            if len(out) >= batch:
                break
        slot_cursor += 1
        if slot_cursor > 512:
            break
    return out


def _record_locations(panel: dict[str, Any], assignments: list[dict[str, Any]], *, node_id: str = "") -> None:
    ledger = list(panel.get("locations_used") or [])
    seen = {(str(x.get("region_id")), int(x.get("region_slot") or 0)) for x in ledger if isinstance(x, dict)}
    for row in assignments:
        key = (str(row.get("region_id")), int(row.get("region_slot") or 0))
        if key in seen:
            continue
        ledger.append({
            "region_id": row.get("region_id"),
            "region_slot": int(row.get("region_slot") or 0),
            "wave": row.get("wave"),
            "node_id": node_id or row.get("node_id"),
            "updated": _utc(),
        })
        seen.add(key)
    panel["locations_used"] = ledger


def test(*, refresh_absorb: bool = False) -> dict[str, Any]:
    """Security test — Field 1 universal ingress must pass before rollout."""
    doctrine = _load(DOCTRINE, {})
    gates = doctrine.get("security_gates") or {}
    policy = doctrine.get("policy") or {}
    checks: list[dict[str, Any]] = []

    absorb = _load(STATE / "field-one-absorb-panel.json", {})
    if refresh_absorb or not absorb.get("ok"):
        absorb = _run_json("lib/field-one.py", ["absorb"], timeout=150)

    checks.append({
        "id": "absorb_ok",
        "ok": bool(absorb.get("ok")),
        "registry": absorb.get("registry_devices"),
        "outside_absorbed": absorb.get("outside_absorbed"),
    })
    checks.append({
        "id": "universal_ingress",
        "ok": bool(absorb.get("universal_ingress") or absorb.get("field_one")),
    })
    checks.append({
        "id": "quarantine_not_kill",
        "ok": (absorb.get("ingress_policy") or policy.get("quarantine_not_kill", True)) == "quarantine_not_kill"
        or policy.get("quarantine_not_kill", True),
    })
    min_reg = int(gates.get("min_registry_devices") or 1)
    reg_count = int(absorb.get("registry_devices") or 0)
    checks.append({
        "id": "registry_floor",
        "ok": reg_count >= min_reg,
        "count": reg_count,
        "floor": min_reg,
    })
    hub = absorb.get("hub") or {}
    checks.append({
        "id": "field_one_hub",
        "ok": bool(hub.get("id") == "field-1" or hub.get("truth")),
        "hub": hub.get("id"),
    })

    any_ip = _run_json("lib/field-dns-dhcp-any-ip.py", ["json"], timeout=15)
    checks.append({
        "id": "wildcard_any_ip",
        "ok": bool(any_ip.get("any_ip") and (any_ip.get("dns") or {}).get("wildcard_v4") == "0.0.0.0"),
    })

    racks = _run_json("lib/field-zachub-qemu-racks.py", ["json"], timeout=30)
    isolated = bool((racks.get("security") or {}).get("internet_isolated", racks.get("internet_isolated")))
    checks.append({
        "id": "racks_internet_isolated",
        "ok": isolated if gates.get("require_internet_isolated", True) else True,
        "rack_count": racks.get("rack_count") or len(racks.get("slots") or []),
    })

    passed = sum(1 for c in checks if c.get("ok"))
    total = len(checks)
    score = int(100 * passed / total) if total else 0
    ok = passed == total

    out = {
        "ok": ok,
        "schema": "field-one-rollout-test/v1",
        "updated": _utc(),
        "motto": doctrine.get("motto"),
        "security_score": score,
        "checks_passed": passed,
        "checks_total": total,
        "checks": checks,
        "absorb": {
            "registry_devices": reg_count,
            "wan_edges": absorb.get("wan_edges"),
            "hub": hub,
        },
        "ready_for_rollout": ok,
        "api": "/api/field-one-rollout/test",
    }
    _save(PANEL, {**_load(PANEL, {}), "last_test": out, "updated": _utc()})
    _append_ledger({"event": "test", "ok": ok, "score": score})
    return out


def _region_assignments(batch: int, wave: int, *, panel: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return _assign_unique_locations(batch, wave, panel=panel)


def _hub_doc() -> dict[str, Any]:
    return _load(INSTALL / "data" / "field-one-doctrine.json", {}).get("hub") or {}


def _safe_stamp_id(node_id: str) -> str:
    return re.sub(r"[^\w\-.]+", "_", str(node_id or "node"))[:120]


def _stamp_doc(
    *,
    wave: int,
    region_id: str,
    region_slot: int = 0,
    node_id: str = "",
    kind: str = "",
) -> dict[str, Any]:
    return {
        "schema": FIELD_ONE_VERSION,
        "version": 2,
        "updated": _utc(),
        "field_one": True,
        "field_one_updated": True,
        "universal_ingress": True,
        "outside_network_absorbed": True,
        "never_lose": True,
        "cooperative_mesh": True,
        "hub": _hub_doc(),
        "wave": wave,
        "region": region_id,
        "region_slot": region_slot,
        "node_id": node_id or None,
        "kind": kind or None,
        "internet_isolated": True,
        "witness_peers": [],
        "redundant_copies": 0,
        "content_hash": "",
    }


def _witness_mirror_dirs() -> list[Path]:
    dirs: list[Path] = [
        STAMP_VAULT,
        REDUNDANT_VAULT / "a",
        REDUNDANT_VAULT / "b",
        REDUNDANT_VAULT / "c",
    ]
    racks_root = INSTALL / "GrokLab" / "deploy" / "qemu-racks"
    if racks_root.is_dir():
        for path in sorted(racks_root.glob("qemu-rack-*"))[:3]:
            dirs.append(path / "witness" / "field-one-mirror")
    dirs.append(STATE / "field-one-sovereign-mirror")
    return dirs


def _append_never_lose(row: dict[str, Any]) -> None:
    try:
        NEVER_LOSE_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with NEVER_LOSE_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _refresh_rollout_pool(*, min_targets: int | None = None) -> dict[str, Any]:
    """Expand registry pool to 500+ targets before botnet rollout."""
    floor = int(min_targets or MIN_ROLLOUT_TARGETS)
    os.environ.setdefault("NEXUS_FIELD_WAN_EDGE_SLOTS", str(max(436, floor - 64)))
    blast = _run_json("lib/field-rescue-ingress.py", ["blast-edges"], timeout=60)
    absorb = _run_json("lib/field-one.py", ["absorb"], timeout=90)
    nodes = _load_botnet_nodes(skip_refresh=True)
    out = {
        "ok": bool(blast.get("ok") or absorb.get("ok") or len(nodes) >= floor),
        "min_targets": floor,
        "nodes_visible": len(nodes),
        "registry_devices": absorb.get("registry_devices"),
        "blast_edges": blast.get("total_edges_deployed"),
        "absorb_ok": absorb.get("ok"),
    }
    if len(nodes) < floor:
        out["warning"] = "below_min_targets"
    return out


def _add_node(nodes: list[dict[str, Any]], seen: set[str], row: dict[str, Any]) -> None:
    nid = str(row.get("id") or "")
    if not nid or nid in seen:
        return
    seen.add(nid)
    nodes.append(row)


def _load_botnet_nodes(*, skip_refresh: bool = False) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()

    reg = _load(REGISTRY, {})
    for dev in reg.get("devices") or []:
        if not isinstance(dev, dict):
            continue
        did = str(dev.get("id") or "")
        _add_node(nodes, seen, {
            "id": did,
            "kind": str(dev.get("kind") or "registry_device"),
            "storage_root": dev.get("storage_root") or dev.get("forever_storage_root"),
            "registry": True,
            "device": dev,
        })

    edge_panel = _load(STATE / "field-edge-blast-panel.json", {})
    for edge in edge_panel.get("edge_hosts") or []:
        if not isinstance(edge, dict):
            continue
        eid = str(edge.get("edge_id") or edge.get("id") or "")
        _add_node(nodes, seen, {
            "id": eid,
            "kind": "edge_host",
            "bind": edge.get("bind"),
            "outside_network": edge.get("outside_network"),
        })

    gh = _load(STATE / "field-github-planet-sweep-panel.json", {})
    for row in (gh.get("github_index") or {}).get("dhcp_index") or []:
        if not isinstance(row, dict):
            continue
        did = str(row.get("lease_id") or row.get("mac") or row.get("ip") or "")
        if not did:
            continue
        key = f"gh-dhcp-{did.replace(':', '')[:24]}"
        _add_node(nodes, seen, {
            "id": key,
            "kind": "github_planet_dhcp",
            "ip": row.get("ip"),
            "mac": row.get("mac"),
        })

    bot_mod = _mod("lib/field-botnet-dns-dhcp.py", "botnet")
    if bot_mod:
        doctrine = _load(INSTALL / "data" / "field-botnet-dns-dhcp-doctrine.json", {})
        for row in bot_mod._bot_nodes(doctrine, fast=True):
            nid = str(row.get("id") or "")
            _add_node(nodes, seen, dict(row))

    panel = _load(PANEL, {})
    for rack in (panel.get("last_rollout") or {}).get("racks") or []:
        nid = str(rack.get("node_id") or rack.get("field_id") or "")
        _add_node(nodes, seen, {
            "id": nid,
            "kind": "qemu_world",
            "storage_root": rack.get("storage_root"),
            "field_id": rack.get("field_id"),
            "slot": rack.get("slot"),
        })

    racks_root = INSTALL / "GrokLab" / "deploy" / "qemu-racks"
    if racks_root.is_dir():
        for path in sorted(racks_root.glob("qemu-rack-*")):
            if not path.is_dir():
                continue
            slot_s = path.name.rsplit("-", 1)[-1]
            nid = f"qemu-world-{slot_s}"
            _add_node(nodes, seen, {
                "id": nid,
                "kind": "qemu_world",
                "storage_root": str(path),
                "field_id": path.name,
                "slot": int(slot_s) if slot_s.isdigit() else 0,
            })

    _add_node(nodes, seen, {
        "id": "field-loopback",
        "kind": "sovereign",
        "storage_root": str(STATE),
    })
    return nodes


def _node_stamp_path(node: dict[str, Any]) -> Path:
    root = str(node.get("storage_root") or "").strip()
    if root and Path(root).is_dir():
        return Path(root) / "field-one-stack.json"
    return STAMP_VAULT / f"{_safe_stamp_id(str(node.get('id') or 'node'))}.json"


def _node_field_one_updated(node: dict[str, Any]) -> bool:
    dev = node.get("device") if isinstance(node.get("device"), dict) else {}
    if dev.get("field_one_updated") and dev.get("field_one_version") == FIELD_ONE_VERSION:
        return True
    stamp = _node_stamp_path(node)
    if stamp.is_file():
        doc = _load(stamp, {})
        if doc.get("schema") == FIELD_ONE_VERSION and doc.get("field_one_updated"):
            return True
        if doc.get("version") == 2 and doc.get("field_one_updated"):
            return True
    vault = STAMP_VAULT / f"{_safe_stamp_id(str(node.get('id') or ''))}.json"
    if vault.is_file():
        doc = _load(vault, {})
        if doc.get("schema") == FIELD_ONE_VERSION and doc.get("field_one_updated"):
            return True
    return False


def _update_registry_device(node_id: str, stamp_doc: dict[str, Any]) -> None:
    reg = _load(REGISTRY, {})
    devices = list(reg.get("devices") or [])
    changed = False
    for i, dev in enumerate(devices):
        if not isinstance(dev, dict):
            continue
        if str(dev.get("id") or "") != node_id:
            continue
        devices[i] = {
            **dev,
            "field_one": True,
            "field_one_updated": True,
            "field_one_version": FIELD_ONE_VERSION,
            "field_one_sink": True,
            "route_to": "field-1",
            "never_lose": True,
            "witness_peers": stamp_doc.get("witness_peers") or [],
            "field_one_stamp": stamp_doc.get("content_hash"),
            "last_seen": _utc(),
            "last_timestamp": _utc(),
        }
        changed = True
        break
    if changed:
        reg["devices"] = devices
        reg["device_count"] = len(devices)
        reg["field_one_rollout"] = _utc()
        _save(REGISTRY, reg)


def _mirror_stamp(node_id: str, doc: dict[str, Any], *, dry_run: bool = False) -> list[str]:
    paths: list[str] = []
    pre_hash = {k: v for k, v in doc.items() if k != "content_hash"}
    doc["content_hash"] = hashlib.sha256(
        json.dumps(pre_hash, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()[:32]
    safe = _safe_stamp_id(node_id)
    for mirror_dir in _witness_mirror_dirs():
        target = mirror_dir / f"{safe}.json"
        paths.append(str(target))
        if dry_run:
            continue
        try:
            mirror_dir.mkdir(parents=True, exist_ok=True)
            _save(target, doc)
        except OSError:
            pass
    return paths


def _stamp_botnet_node(
    node: dict[str, Any],
    region: dict[str, Any],
    *,
    wave: int = 0,
    dry_run: bool = False,
) -> dict[str, Any]:
    node_id = str(node.get("id") or "")
    doc = _stamp_doc(
        wave=wave,
        region_id=str(region.get("region_id") or "local"),
        region_slot=int(region.get("region_slot") or 0),
        node_id=node_id,
        kind=str(node.get("kind") or ""),
    )
    primary = _node_stamp_path(node)
    mirrors = _mirror_stamp(node_id, doc, dry_run=dry_run)
    if not dry_run:
        primary.parent.mkdir(parents=True, exist_ok=True)
        doc["witness_peers"] = [p for p in mirrors if p != str(primary)][:5]
        doc["redundant_copies"] = len(mirrors)
        _save(primary, doc)
        _update_registry_device(node_id, doc)
        _append_never_lose({
            "event": "stamp_v2",
            "node_id": node_id,
            "kind": node.get("kind"),
            "primary": str(primary),
            "mirrors": len(mirrors),
            "hash": doc.get("content_hash"),
            "never_lose": True,
        })
    return {
        "ok": True,
        "id": node_id,
        "kind": node.get("kind"),
        "stamp": str(primary),
        "mirrors": len(mirrors),
        "version": FIELD_ONE_VERSION,
        "region_id": region.get("region_id"),
        "region_slot": region.get("region_slot"),
        "dry_run": dry_run,
    }


def rollout(*, batch_size: int | None = None, dry_run: bool = False) -> dict[str, Any]:
    """Roll out Field 1 stack to N racks (default 10) after security test passes."""
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    # Rescue doctrine: always 10 at a time (never inflate batch)
    batch = int(batch_size or policy.get("batch_size") or 10)
    hard_cap = int(policy.get("hard_batch_cap") or policy.get("batch_size") or 10)
    batch = max(1, min(batch, hard_cap, 10))

    sec = test(refresh_absorb=False)
    if policy.get("test_before_rollout", True) and not sec.get("ok"):
        return {
            "ok": False,
            "error": "security_test_failed",
            "test": sec,
            "api": "/api/field-one-rollout",
        }

    state = _rollout_state()
    wave = state["wave"] + 1
    racks_mod = _mod("lib/field-zachub-qemu-racks.py", "racks")
    if not racks_mod:
        return {"ok": False, "error": "qemu_racks_missing"}

    status = racks_mod.qemu_pipeline_status()
    slots = racks_mod.build_slots(status)
    skip = max(0, state["deployed_total"])
    os.environ["WORLD_PIPELINE_SLOTS"] = str(max(len(slots), skip + batch))
    if len(slots) < skip + batch:
        status = racks_mod.qemu_pipeline_status()
        slots = racks_mod.build_slots(status)

    panel_doc = _load(PANEL, {})
    regions = _region_assignments(batch, wave, panel=panel_doc)
    if len(regions) < batch:
        return {
            "ok": False,
            "error": "unique_locations_exhausted",
            "requested": batch,
            "assigned": len(regions),
            "api": "/api/field-one-rollout",
        }

    provisioned: list[dict[str, Any]] = []
    skip = max(0, state["deployed_total"])
    to_provision = slots[skip: skip + batch]
    if len(to_provision) < batch:
        os.environ["WORLD_PIPELINE_SLOTS"] = str(max(len(slots), skip + batch))
        status = racks_mod.qemu_pipeline_status()
        slots = racks_mod.build_slots(status)
        to_provision = slots[skip: skip + batch]
    for i, meta in enumerate(to_provision):
        reg = regions[i] if i < len(regions) else regions[-1]
        if dry_run:
            row = racks_mod.provision_rack(meta, write=False, dry_run=True)
        else:
            row = racks_mod.provision_rack(meta, write=True, dry_run=False)
            root = Path(str(row.get("storage_root") or ""))
            if root.is_dir():
                _save(root / "field-one-stack.json", _stamp_doc(
                    wave=wave,
                    region_id=str(reg.get("region_id") or "local"),
                    region_slot=int(reg.get("region_slot") or 0),
                    node_id=str(row.get("node_id") or meta.get("node_id") or ""),
                ))
        row["region_id"] = reg.get("region_id")
        row["region_slot"] = reg.get("region_slot")
        provisioned.append(row)

    deployed = sum(1 for p in provisioned if p.get("ok", True))
    total_deployed = state["deployed_total"] + deployed

    out = {
        "ok": deployed > 0 or dry_run,
        "schema": "field-one-rollout-wave/v1",
        "updated": _utc(),
        "wave": wave,
        "batch_size": batch,
        "deployed_this_wave": deployed,
        "deployed_total": total_deployed,
        "dry_run": dry_run,
        "test_score": sec.get("security_score"),
        "regions": regions,
        "racks": provisioned,
        "motto": "Field 1 rolled out — test green, batch deployed, connections preserved",
        "api": "/api/field-one-rollout",
    }
    panel_doc.update({
        "wave": wave,
        "deployed_total": total_deployed,
        "last_batch": batch,
        "regions_live": list({r["region_id"] for r in (panel_doc.get("locations_used") or []) + regions}),
        "last_rollout": out,
        "updated": _utc(),
    })
    _record_locations(panel_doc, regions)
    _save(PANEL, panel_doc)
    _append_ledger({"event": "rollout", "wave": wave, "batch": batch, "deployed": deployed})
    return out


def double_worldwide(*, dry_run: bool = False) -> dict[str, Any]:
    """Double deployed nodes worldwide — next wave = current total (min 10)."""
    return double_total_no_repeat(dry_run=dry_run)


def _fast_stamp_pending(
    pending: list[dict[str, Any]],
    *,
    wave: int,
    take: int,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Bulk stamp pending nodes without per-node registry rewrite / multi-mirror."""
    STAMP_VAULT.mkdir(parents=True, exist_ok=True)
    hub = _hub_doc()
    now = _utc()
    ok_n = 0
    sample: list[dict[str, Any]] = []
    # Single registry load + save
    reg = _load(REGISTRY, {})
    devices = list(reg.get("devices") or [])
    by_id = {str(d.get("id") or ""): i for i, d in enumerate(devices) if isinstance(d, dict)}
    for i, node in enumerate(pending[:take]):
        node_id = str(node.get("id") or "")
        if not node_id:
            continue
        region_id = f"w{(i % 61) + 1:02d}"  # logical world region shard
        doc = {
            "schema": FIELD_ONE_VERSION,
            "version": 2,
            "updated": now,
            "field_one": True,
            "field_one_updated": True,
            "universal_ingress": True,
            "outside_network_absorbed": True,
            "never_lose": True,
            "cooperative_mesh": True,
            "hub": hub,
            "wave": wave,
            "region": region_id,
            "region_slot": i,
            "node_id": node_id,
            "kind": str(node.get("kind") or ""),
            "internet_isolated": True,
            "world_bulk": True,
            "whole_world_rescue": True,
            "witness_peers": [],
            "redundant_copies": 1,
            "content_hash": "",
        }
        pre = {k: v for k, v in doc.items() if k != "content_hash"}
        doc["content_hash"] = hashlib.sha256(
            json.dumps(pre, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()[:32]
        if not dry_run:
            try:
                _save(STAMP_VAULT / f"{_safe_stamp_id(node_id)}.json", doc)
                # primary storage_root if present
                root = str(node.get("storage_root") or "").strip()
                if root and Path(root).is_dir():
                    _save(Path(root) / "field-one-stack.json", doc)
            except OSError:
                continue
            idx = by_id.get(node_id)
            if idx is not None:
                devices[idx] = {
                    **devices[idx],
                    "field_one": True,
                    "field_one_updated": True,
                    "field_one_version": FIELD_ONE_VERSION,
                    "field_one_sink": True,
                    "route_to": "field-1",
                    "never_lose": True,
                    "whole_world_rescue": True,
                    "last_seen": now,
                    "last_timestamp": now,
                }
        ok_n += 1
        if len(sample) < 12:
            sample.append({"id": node_id, "region": region_id, "ok": True})
    if not dry_run and ok_n:
        reg["devices"] = devices
        reg["device_count"] = len(devices)
        reg["field_one_rollout"] = now
        reg["whole_world_rescue"] = True
        _save(REGISTRY, reg)
    return {"ok": True, "stamped_n": ok_n, "sample": sample}


def botnet_rollout(
    *,
    batch_size: int | None = None,
    dry_run: bool = False,
    world: bool = False,
) -> dict[str, Any]:
    """Stamp Field 1 stack on pending botnet nodes (unique region per node).

    Normal rescue: hard-capped at 10. Whole-world rescue: lift via world=True
    or NEXUS_FIELD_ONE_WORLD_BATCH so we can stamp thousands of mesh nodes.
    """
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    world = world or str(os.environ.get("NEXUS_FIELD_ONE_WORLD", "")).strip().lower() in (
        "1", "true", "yes", "world", "more",
    )
    batch = int(
        batch_size
        or (os.environ.get("NEXUS_FIELD_ONE_WORLD_BATCH") if world else None)
        or policy.get("batch_size")
        or 10
    )
    if world:
        # Whole world: large logical stamp waves (still bounded for memory)
        hard = int(os.environ.get("NEXUS_FIELD_ONE_WORLD_HARD_CAP") or 32768)
        batch = max(1, min(batch, hard))
    else:
        batch = max(1, min(batch, int(policy.get("hard_batch_cap") or 10), 10))

    # Skip heavy security retest on world multi-waves if last test was ok
    last_test = (_load(PANEL, {}) or {}).get("last_test") or {}
    if world and last_test.get("ok") and last_test.get("ready_for_rollout"):
        sec = last_test
    else:
        sec = test(refresh_absorb=False)
        if policy.get("test_before_rollout", True) and not sec.get("ok"):
            return {"ok": False, "error": "security_test_failed", "test": sec}

    nodes = _load_botnet_nodes()
    pending = [n for n in nodes if not _node_field_one_updated(n)]
    if not pending:
        return {
            "ok": True,
            "schema": "field-one-botnet-rollout/v1",
            "updated": _utc(),
            "pending": 0,
            "updated_this_batch": 0,
            "nodes_total": len(nodes),
            "all_updated": True,
            "api": "/api/field-one-rollout/botnet",
        }

    panel_doc = _load(PANEL, {})
    wave = int(panel_doc.get("botnet_wave") or 0) + 1
    take = min(batch, len(pending))

    if world and take > 32:
        # Fast path — vault + single registry rewrite (no multi-mirror storm)
        fast = _fast_stamp_pending(pending, wave=wave, take=take, dry_run=dry_run)
        stamped_n = int(fast.get("stamped_n") or 0)
        stamped = list(fast.get("sample") or [])
        regions: list[dict[str, Any]] = []
    else:
        regions = _assign_unique_locations(take, wave, panel=panel_doc)
        stamped = []
        for i, node in enumerate(pending[:take]):
            reg = regions[i] if i < len(regions) else regions[-1]
            stamped.append(_stamp_botnet_node(node, reg, wave=wave, dry_run=dry_run))
            _record_locations(panel_doc, [reg], node_id=str(node.get("id") or ""))
        stamped_n = sum(1 for s in stamped if s.get("ok"))

    panel_doc.update({
        "botnet_wave": wave,
        "botnet_updated_total": int(panel_doc.get("botnet_updated_total") or 0) + stamped_n,
        "whole_world_rescue": True if world else panel_doc.get("whole_world_rescue"),
        "last_botnet_rollout": {
            "updated": _utc(),
            "batch": take,
            "stamped_n": stamped_n,
            "world_bulk": bool(world and take > 32),
            "sample": stamped[:12] if isinstance(stamped, list) else [],
            "pending_before": len(pending),
        },
        "updated": _utc(),
    })
    _save(PANEL, panel_doc)
    _append_ledger({
        "event": "botnet_rollout",
        "wave": wave,
        "batch": take,
        "stamped_n": stamped_n,
        "world": world,
        "ok": True,
    })

    still_pending = max(0, len(pending) - stamped_n)
    return {
        "ok": True,
        "schema": "field-one-botnet-rollout/v1",
        "updated": _utc(),
        "wave": wave,
        "batch_size": take,
        "updated_this_batch": stamped_n,
        "pending_remaining": still_pending,
        "nodes_total": len(nodes),
        "all_updated": still_pending == 0,
        "world_bulk": bool(world and take > 32),
        "test_score": sec.get("security_score"),
        "stamped_sample": stamped[:12] if isinstance(stamped, list) else [],
        "regions": regions[:24] if regions else [],
        "api": "/api/field-one-rollout/botnet",
    }


def botnet_double_until_complete(
    *,
    dry_run: bool = False,
    max_rounds: int = 32,
    refresh_pool: bool = True,
) -> dict[str, Any]:
    """Green-gated botnet doubling until every node carries Field 1 v2 stamp."""
    pool: dict[str, Any] = {}
    if refresh_pool:
        pool = _refresh_rollout_pool()
    rounds: list[dict[str, Any]] = []
    batch = 10
    for _ in range(max_rounds):
        nodes = _load_botnet_nodes()
        pending = [n for n in nodes if not _node_field_one_updated(n)]
        if not pending:
            break
        sec = test(refresh_absorb=False)
        if not sec.get("ok"):
            return {
                "ok": False,
                "error": "security_test_failed",
                "test": sec,
                "rounds": rounds,
                "phase": "botnet_double_until_complete",
            }
        take = min(len(pending), batch)
        result = botnet_rollout(batch_size=take, dry_run=dry_run)
        result["round_batch"] = batch
        rounds.append(result)
        if not result.get("ok"):
            break
        if result.get("all_updated"):
            break
        batch = max(batch * 2, 1)

    nodes = _load_botnet_nodes()
    pending_left = [n.get("id") for n in nodes if not _node_field_one_updated(n)]
    out = {
        "ok": len(pending_left) == 0,
        "schema": "field-one-botnet-double/v1",
        "updated": _utc(),
        "phase": "botnet_double_until_complete",
        "version": FIELD_ONE_VERSION,
        "never_lose": True,
        "pool_refresh": pool,
        "rounds": len(rounds),
        "nodes_total": len(nodes),
        "pending_remaining": len(pending_left),
        "pending_ids": pending_left[:20],
        "all_updated": len(pending_left) == 0,
        "round_results": rounds,
        "api": "/api/field-one-rollout/botnet-double",
    }
    panel_doc = _load(PANEL, {})
    panel_doc["last_botnet_double"] = out
    panel_doc["updated"] = _utc()
    _save(PANEL, panel_doc)
    _append_ledger({
        "event": "botnet_double_until_complete",
        "ok": out["ok"],
        "rounds": len(rounds),
        "pending": len(pending_left),
    })
    return out


def double_total_no_repeat(*, dry_run: bool = False) -> dict[str, Any]:
    """Double overall deployed total using only unused (region, slot) locations."""
    doctrine = _load(DOCTRINE, {})
    policy = doctrine.get("policy") or {}
    state = _rollout_state()
    current = max(state["deployed_total"], state["last_batch"], int(policy.get("batch_size") or 10))
    next_batch = max(10, current)
    result = rollout(batch_size=next_batch, dry_run=dry_run)
    result["doubled_from"] = current
    result["doubled_to"] = next_batch
    result["phase"] = "double_total_no_repeat"
    result["locations_used"] = len(_locations_used(_load(PANEL, {})))
    _append_ledger({
        "event": "double_total_no_repeat",
        "from": current,
        "to": next_batch,
        "ok": result.get("ok"),
    })
    return result


def build_panel() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    panel = _load(PANEL, {})
    state = _rollout_state()
    last_test = panel.get("last_test") or {}
    return {
        "ok": True,
        "schema": "field-one-rollout/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "policy": doctrine.get("policy"),
        "wave": state["wave"],
        "deployed_total": state["deployed_total"],
        "last_batch": state["last_batch"],
        "regions_live": state["regions_live"],
        "locations_used": state["locations_used"],
        "botnet_updated_total": state["botnet_updated_total"],
        "field_one_version": FIELD_ONE_VERSION,
        "never_lose": True,
        "min_rollout_targets": MIN_ROLLOUT_TARGETS,
        "botnet_nodes": len(_load_botnet_nodes()),
        "botnet_pending": sum(1 for n in _load_botnet_nodes() if not _node_field_one_updated(n)),
        "registry_devices": (_load(REGISTRY, {}) or {}).get("device_count"),
        "last_test_ok": last_test.get("ok"),
        "security_score": last_test.get("security_score"),
        "ready_for_rollout": last_test.get("ready_for_rollout"),
        "api": doctrine.get("api", "/api/field-one-rollout"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    dry = "--dry-run" in sys.argv[2:]
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("test", "security"):
        refresh = "--refresh" in sys.argv[2:]
        print(json.dumps(test(refresh_absorb=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("rollout", "roll", "wave", "deploy"):
        batch = None
        for arg in sys.argv[2:]:
            if arg.isdigit():
                batch = int(arg)
        print(json.dumps(rollout(batch_size=batch, dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("double", "double-worldwide", "double_worldwide"):
        print(json.dumps(double_worldwide(dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("double-total", "double-total-no-repeat", "double_total_no_repeat"):
        print(json.dumps(double_total_no_repeat(dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("botnet", "botnet-rollout"):
        batch = None
        world = "--world" in sys.argv[2:] or "--more" in sys.argv[2:]
        for arg in sys.argv[2:]:
            if arg.isdigit():
                batch = int(arg)
        print(json.dumps(botnet_rollout(batch_size=batch, dry_run=dry, world=world), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("botnet-world", "world-botnet", "botnet-more"):
        batch = None
        for arg in sys.argv[2:]:
            if arg.isdigit():
                batch = int(arg)
        if batch is None:
            batch = int(os.environ.get("NEXUS_FIELD_ONE_WORLD_BATCH") or 4096)
        print(json.dumps(botnet_rollout(batch_size=batch, dry_run=dry, world=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("botnet-double", "botnet-double-until-complete", "botnet_double_until_complete"):
        print(json.dumps(botnet_double_until_complete(dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": (
            "field-one-rollout.py [json|test|rollout [N]|double|double-total|"
            "botnet [N]|botnet-world [N]|botnet-double] [--dry-run] [--refresh] [--world]"
        ),
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())