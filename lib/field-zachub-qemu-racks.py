#!/usr/bin/env python3
"""ZacHub QEMU racks — GrokLab botnet pipeline slots as edge/DNS/DHCP/witness racks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-zachub-qemu-racks-doctrine.json"
REDUNDANT_DOCTRINE = INSTALL / "data" / "field-zachub-redundant-storage-doctrine.json"
PANEL = STATE / "field-zachub-qemu-racks-panel.json"
REDUNDANT_STATE = STATE / "field-zachub-redundant-storage.json"
H7_DOCS = INSTALL / "Hostess7" / "docs"
DEPLOY = Path(os.environ.get("GROK_LAB_DEPLOY", str(INSTALL / "GrokLab" / "deploy")))
PIPELINE = DEPLOY / "qemu-world-pipeline.py"
REGIONS = DEPLOY / "world-node-regions.json"
VM_DIR = Path(os.environ.get("GROK_LAB_VM_DIR", str(DEPLOY / "qemu-vms")))


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


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def redundant_doctrine() -> dict[str, Any]:
    return _load(REDUNDANT_DOCTRINE, {})


def _gb_per_unit() -> int:
    cap = doctrine().get("capacity") or {}
    return int(cap.get("gb_per_unit") or 91)


def _role_ceilings_gb() -> dict[str, float]:
    cap = doctrine().get("capacity") or {}
    per = cap.get("per_role_gb") or {}
    red = redundant_doctrine().get("operational_ceilings_gb") or {}
    return {
        "dns": float(per.get("dns") or red.get("dns") or 12),
        "dhcp": float(per.get("dhcp") or red.get("dhcp") or 12),
        "edge": float(per.get("edge") or red.get("edge") or 16),
        "github_mirror_witness": float(per.get("github_mirror_witness") or red.get("github_mirror_witness") or 8),
    }


def _dir_bytes(path: Path) -> int:
    if not path.is_dir():
        return 0
    try:
        proc = subprocess.run(
            ["du", "-sb", str(path)],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return int(proc.stdout.split()[0])
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass
    total = 0
    try:
        for row in path.rglob("*"):
            if row.is_file():
                try:
                    total += row.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _bytes_to_gb(n: int) -> float:
    return round(n / (1024 ** 3), 3)


def _shared_dns_dhcp_bytes() -> tuple[int, int]:
    """Fallback — sovereign DNS/DHCP state scaled per rack when lane dirs are empty."""
    dns_paths = [
        STATE / "field-dns-queries.jsonl",
        STATE / "field-dns-cache-hints.jsonl",
        STATE / "field-dns-panel.json",
    ]
    dhcp_paths = [
        STATE / "field-dhcp-events.jsonl",
        STATE / "field-dhcp-panel.json",
        STATE / "field-dhcp-leases.json",
    ]
    dns_b = sum(p.stat().st_size for p in dns_paths if p.is_file())
    dhcp_b = sum(p.stat().st_size for p in dhcp_paths if p.is_file())
    return dns_b, dhcp_b


def _rack_lane_usage_gb(root: Path, *, rack_count: int) -> dict[str, float]:
    ceilings = _role_ceilings_gb()
    dns_b = _dir_bytes(root / "dns")
    dhcp_b = _dir_bytes(root / "dhcp")
    if dns_b == 0 and dhcp_b == 0:
        shared_dns, shared_dhcp = _shared_dns_dhcp_bytes()
        share = max(1, rack_count)
        dns_b = shared_dns // share
        dhcp_b = shared_dhcp // share
    dns_used = min(ceilings["dns"], _bytes_to_gb(dns_b))
    dhcp_used = min(ceilings["dhcp"], _bytes_to_gb(dhcp_b))
    edge_used = min(ceilings["edge"], _bytes_to_gb(_dir_bytes(root / "edge")))
    witness_used = min(
        ceilings["github_mirror_witness"],
        _bytes_to_gb(_dir_bytes(root / "witness")),
    )
    return {
        "dns_used_gb": dns_used,
        "dhcp_used_gb": dhcp_used,
        "edge_used_gb": edge_used,
        "witness_used_gb": witness_used,
        "dns_remaining_gb": round(max(0.0, ceilings["dns"] - dns_used), 3),
        "dhcp_remaining_gb": round(max(0.0, ceilings["dhcp"] - dhcp_used), 3),
    }


def _load_redundant_pool(root: Path) -> dict[str, Any]:
    rel = redundant_doctrine().get("paths") or {}
    pool = root / str(rel.get("redundant_pool") or "h7-shard/redundant-pool.json")
    doc = _load(pool, {})
    if not doc:
        return {
            "schema": "zachub-redundant-pool/v1",
            "converted_gb": 0.0,
            "pending_gb": 0.0,
            "dns_dhcp_recovered_gb": 0.0,
        }
    return doc


def _save_redundant_pool(root: Path, doc: dict[str, Any]) -> Path:
    rel = redundant_doctrine().get("paths") or {}
    pool = root / str(rel.get("redundant_pool") or "h7-shard/redundant-pool.json")
    doc["updated"] = _utc()
    _save(pool, doc)
    return pool


def _rack_storage_accounting(slot_meta: dict[str, Any], *, rack_count: int) -> dict[str, Any]:
    gb_unit = float(slot_meta.get("gb_quota") or _gb_per_unit())
    root = Path(str(slot_meta.get("storage_root") or ""))
    usage = _rack_lane_usage_gb(root, rack_count=rack_count)
    ceilings = _role_ceilings_gb()
    operational_gb = (
        ceilings["dns"] + ceilings["dhcp"] + ceilings["edge"] + ceilings["github_mirror_witness"]
    )
    recoverable = usage["dns_remaining_gb"] + usage["dhcp_remaining_gb"]
    pool = _load_redundant_pool(root) if root.is_dir() else {"converted_gb": 0.0}
    converted = float(pool.get("converted_gb") or 0.0)
    max_redundant = max(0.0, gb_unit - operational_gb * 0.5)
    pending = round(min(max_redundant - converted, recoverable + max(0.0, max_redundant - converted)), 3)
    return {
        "field_id": slot_meta.get("field_id"),
        "slot": slot_meta.get("slot"),
        "gb_per_rack": gb_unit,
        **usage,
        "recoverable_dns_dhcp_gb": round(recoverable, 3),
        "converted_redundant_gb": converted,
        "pending_convert_gb": max(0.0, pending),
        "max_redundant_gb": round(max_redundant, 3),
        "new_rack_headroom_gb": round(gb_unit, 3),
    }


def convert_remaining_storage(
    slots: list[dict[str, Any]] | None = None,
    *,
    write: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Slowly move DNS/DHCP remaining quota on each rack into redundant h7-shard pool."""
    red = redundant_doctrine()
    conv = red.get("conversion") or {}
    cap = doctrine().get("capacity") or {}
    pct = float(conv.get("pct_per_cycle") or cap.get("convert_pct_per_cycle") or 0.05)
    min_gb = float(conv.get("min_gb_per_cycle") or 0.25)
    max_per = float(conv.get("max_gb_per_cycle_per_rack") or 4.0)
    sec = red.get("security") or {}

    status = qemu_pipeline_status()
    slots = slots or build_slots(status)
    rack_count = max(1, len(slots))
    rows: list[dict[str, Any]] = []
    total_converted_cycle = 0.0
    total_redundant = 0.0
    total_pending = 0.0

    for meta in slots:
        root = Path(str(meta.get("storage_root") or ""))
        acct = _rack_storage_accounting(meta, rack_count=rack_count)
        recoverable = float(acct.get("recoverable_dns_dhcp_gb") or 0.0)
        pending = float(acct.get("pending_convert_gb") or 0.0)
        pool = _load_redundant_pool(root) if root.is_dir() else {}
        converted = float(pool.get("converted_gb") or 0.0)
        if recoverable <= 0 and pending <= 0:
            rows.append({**acct, "converted_this_cycle_gb": 0.0, "skipped": "no_remainder"})
            total_redundant += converted
            continue
        delta = min(
            max_per,
            max(min_gb, recoverable * pct),
            pending if pending > 0 else recoverable,
        )
        delta = round(delta, 3)
        if dry_run or not write:
            rows.append({**acct, "converted_this_cycle_gb": delta, "dry_run": True})
            total_redundant += converted + delta
            total_pending += max(0.0, pending - delta)
            total_converted_cycle += delta
            continue
        root.mkdir(parents=True, exist_ok=True)
        (root / "h7-shard").mkdir(parents=True, exist_ok=True)
        pool_doc = {
            "schema": "zachub-redundant-pool/v1",
            "field_id": meta.get("field_id"),
            "protocol": red.get("protocol") or "field-h7s-fs",
            "converted_gb": round(converted + delta, 3),
            "pending_gb": round(max(0.0, pending - delta), 3),
            "dns_dhcp_recovered_gb": round(float(pool.get("dns_dhcp_recovered_gb") or 0.0) + delta, 3),
            "internet_isolated": True,
            "security": sec,
            "last_cycle_gb": delta,
        }
        _save_redundant_pool(root, pool_doc)
        rows.append({**acct, "converted_this_cycle_gb": delta, "pool_path": str(root / "h7-shard" / "redundant-pool.json")})
        total_redundant += converted + delta
        total_pending += max(0.0, pending - delta)
        total_converted_cycle += delta

    out = {
        "ok": True,
        "schema": "field-zachub-redundant-convert/v1",
        "updated": _utc(),
        "mode": conv.get("mode") or "slow_dns_dhcp_remainder",
        "internet_isolated": True,
        "outside_internet": False,
        "rack_count": rack_count,
        "converted_this_cycle_gb": round(total_converted_cycle, 3),
        "total_redundant_gb": round(total_redundant, 3),
        "total_pending_convert_gb": round(total_pending, 3),
        "new_rack_growth_gb": _gb_per_unit(),
        "motto": red.get("motto"),
        "security": sec,
        "racks": rows,
    }
    if write and not dry_run:
        try:
            _save(REDUNDANT_STATE, out)
        except OSError:
            pass
    return out


def storage_totals(slots: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    slots = slots or build_slots()
    rack_count = max(1, len(slots))
    accounts = [_rack_storage_accounting(s, rack_count=rack_count) for s in slots]
    redundant = sum(float(a.get("converted_redundant_gb") or 0.0) for a in accounts)
    pending = sum(float(a.get("pending_convert_gb") or 0.0) for a in accounts)
    recoverable = sum(float(a.get("recoverable_dns_dhcp_gb") or 0.0) for a in accounts)
    per_rack = _gb_per_unit()
    red = redundant_doctrine()
    return {
        "schema": "field-zachub-storage-totals/v1",
        "updated": _utc(),
        "protocol": red.get("protocol") or "field-h7s-fs",
        "internet_isolated": True,
        "rack_count": len(slots),
        "gb_per_rack": per_rack,
        "total_rack_budget_gb": per_rack * len(slots),
        "total_redundant_gb": round(redundant, 3),
        "total_pending_convert_gb": round(pending, 3),
        "total_recoverable_dns_dhcp_gb": round(recoverable, 3),
        "growth_per_new_rack_gb": per_rack,
        "motto": "DNS/DHCP remainder → redundant pool. New rack = more data. No outside internet.",
        "racks": accounts,
    }


def _role_cycle() -> list[str]:
    roles = doctrine().get("roles") or {}
    cycle = roles.get("primary_cycle")
    if isinstance(cycle, list) and cycle:
        return [str(r) for r in cycle]
    return ["dhcp", "dns", "edge", "github_mirror_witness"]


def _deploy_root() -> Path:
    layout = doctrine().get("rack_layout") or {}
    raw = str(
        os.environ.get("GROK_LAB_DEPLOY")
        or layout.get("deploy_root")
        or "GrokLab/deploy"
    )
    p = Path(raw)
    if not p.is_absolute():
        p = INSTALL / p
    return p.resolve()


def _racks_base() -> Path:
    layout = doctrine().get("rack_layout") or {}
    sub = str(layout.get("subdir") or "qemu-racks")
    return _deploy_root() / sub


def _vm_base() -> Path:
    layout = doctrine().get("rack_layout") or {}
    sub = str(layout.get("vm_subdir") or "qemu-vms")
    return _deploy_root() / sub


def qemu_pipeline_status() -> dict[str, Any]:
    if not PIPELINE.is_file():
        return {
            "ok": False,
            "error": "qemu-world-pipeline.py missing",
            "running": False,
            "completed": 0,
            "target": 0,
            "slots": [],
        }
    try:
        proc = subprocess.run(
            [sys.executable, str(PIPELINE), "status"],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        doc = json.loads(proc.stdout or "{}")
        doc.setdefault("ok", True)
        return doc
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc), "running": False, "completed": 0, "target": 0}


def _slot_count(status: dict[str, Any]) -> tuple[int, int, int]:
    regions = _load(REGIONS, {})
    port_base = int(regions.get("tunnel_port_base") or status.get("tunnel_port_base") or 19477)
    ssh_base = int(regions.get("ssh_port_base") or 2222)
    # Rolling pipeline uses concurrent QEMU slots (6), not geographic target (57).
    slots = int(
        os.environ.get("WORLD_PIPELINE_SLOTS")
        or regions.get("qemu_concurrent_slots")
        or status.get("slots_total")
        or 6
    )
    slots = max(1, min(slots, 16))
    return slots, port_base, ssh_base


def slot_roles(slot: int) -> dict[str, Any]:
    doc = doctrine()
    roles_doc = doc.get("roles") or {}
    cycle = _role_cycle()
    primary = cycle[slot % len(cycle)]
    all_slots = list(roles_doc.get("all_slots") or ["dns_relay", "dhcp_relay", "truth_mirror"])
    edge = list(roles_doc.get("edge_bundle") or ["edge", "dns_relay", "dhcp_relay"])
    combined = list(dict.fromkeys([primary, *edge, *all_slots]))
    layout = doc.get("rack_layout") or {}
    prefix = str(layout.get("field_id_prefix") or "qemu-rack-")
    node_prefix = str(layout.get("node_id_prefix") or "qemu-world-")
    return {
        "slot": slot,
        "field_id": f"{prefix}{slot}",
        "node_id": f"{node_prefix}{slot}",
        "primary_role": primary,
        "roles": combined,
        "botnet_roles": all_slots,
        "edge_roles": edge,
    }


def build_slots(status: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    status = status or qemu_pipeline_status()
    count, port_base, ssh_base = _slot_count(status)
    prov = set(status.get("provisioned") or [])
    staged = set(status.get("staged") or [])
    slots: list[dict[str, Any]] = []
    for i in range(count):
        meta = slot_roles(i)
        slots.append({
            **meta,
            "tunnel": port_base + i,
            "ssh_port": ssh_base + i,
            "pipeline_running": bool(status.get("running")),
            "provisioned": f"qemu-world-{i}" in prov or str(i) in prov,
            "staged": f"qemu-world-{i}" in staged,
            "storage_root": str(_racks_base() / meta["field_id"]),
            "vm_root": str(_vm_base()),
            "gb_quota": _gb_per_unit(),
            "no_team_drive": True,
        })
    return slots


def burn_stale_team_qemu(*, dry_run: bool = False) -> dict[str, Any]:
    """Burn stale TEAM QEMU stubs and wrongly-placed TEAM rack trees."""
    doc = doctrine()
    stale = doc.get("stale_burn") or {}
    paths = list(stale.get("paths") or [])
    reason = str(stale.get("reason") or "stale TEAM QEMU stub")
    burned: list[dict[str, Any]] = []
    for raw in paths:
        p = Path(str(raw))
        row = {"path": str(p), "reason": reason}
        if not p.exists() and not p.is_symlink():
            row["skipped"] = "missing"
            burned.append(row)
            continue
        if dry_run:
            row["dry"] = True
            burned.append(row)
            continue
        try:
            if p.is_symlink() or p.is_file():
                p.unlink()
            elif p.is_dir():
                shutil.rmtree(p)
            row["ok"] = True
            burned.append(row)
        except OSError as exc:
            burned.append({**row, "ok": False, "error": str(exc)[:200]})
    return {
        "ok": all(r.get("ok", True) for r in burned if not r.get("skipped") and not r.get("dry")),
        "schema": "field-zachub-qemu-burn/v1",
        "updated": _utc(),
        "dry_run": dry_run,
        "burned_count": len([r for r in burned if r.get("ok")]),
        "burned": burned,
    }


def _one_big_drive_manifest(slots: list[dict[str, Any]]) -> dict[str, Any]:
    doc = doctrine()
    cap = doc.get("capacity") or {}
    gb = _gb_per_unit()
    redundancy = int(cap.get("redundancy_factor") or 2)
    stripe = int(cap.get("stripe_width") or 4)
    totals = storage_totals(slots)
    shards: list[dict[str, Any]] = []
    rack_count = max(1, len(slots))
    for s in slots:
        fid = str(s.get("field_id") or "")
        root = Path(str(s.get("storage_root") or ""))
        acct = _rack_storage_accounting(s, rack_count=rack_count)
        shard_gb = float(acct.get("converted_redundant_gb") or 0.0)
        if shard_gb <= 0:
            shard_gb = float(acct.get("max_redundant_gb") or gb)
        digest = hashlib.sha256(f"{fid}|{root}|{shard_gb}".encode()).hexdigest()[:16]
        shards.append({
            "field_id": fid,
            "slot": s.get("slot"),
            "node_id": s.get("node_id"),
            "primary_role": s.get("primary_role"),
            "storage_root": str(root),
            "h7_shard": str(root / "h7-shard"),
            "gb": round(shard_gb, 3),
            "converted_redundant_gb": acct.get("converted_redundant_gb"),
            "pending_convert_gb": acct.get("pending_convert_gb"),
            "dns_remaining_gb": acct.get("dns_remaining_gb"),
            "dhcp_remaining_gb": acct.get("dhcp_remaining_gb"),
            "digest": digest,
            "redundancy_peers": [
                other["field_id"]
                for other in slots
                if other.get("field_id") != fid
            ][:redundancy],
        })
    logical_gb = round(float(totals.get("total_redundant_gb") or 0.0), 3)
    potential_gb = round(
        logical_gb + float(totals.get("total_pending_convert_gb") or 0.0),
        3,
    )
    budget_gb = float(totals.get("total_rack_budget_gb") or gb * len(slots))
    effective_gb = round(logical_gb * redundancy / max(1, redundancy), 3)
    layout = doc.get("rack_layout") or {}
    manifest_name = str(layout.get("one_big_drive_manifest") or "zachub-manifest/one-big-drive.json")
    deploy = _deploy_root()
    red = redundant_doctrine()
    return {
        "schema": "zachub-one-big-drive/v2",
        "updated": _utc(),
        "product": "ZacHub",
        "protocol": "field-h7s-fs",
        "motto": "DNS/DHCP remainder converts slowly to redundant H7 pool — new rack grows data. Super secure from outside internet.",
        "no_team_drive_servers": True,
        "internet_isolated": True,
        "storage_kind": cap.get("storage_kind") or "grok_lab_deploy",
        "deploy_root": str(deploy),
        "vm_root": str(_vm_base()),
        "gb_per_unit": gb,
        "redundancy_factor": redundancy,
        "stripe_width": stripe,
        "logical_gb": logical_gb,
        "potential_gb": potential_gb,
        "rack_budget_gb": budget_gb,
        "effective_gb_with_redundancy": effective_gb,
        "growth_per_new_rack_gb": gb,
        "rack_count": len(slots),
        "storage_totals": totals,
        "security": red.get("security") or {},
        "shards": shards,
        "manifest_path": str(deploy / manifest_name),
        "qemu_pipeline": str(PIPELINE),
    }


def provision_rack(
    slot_meta: dict[str, Any],
    *,
    write: bool = True,
    dry_run: bool = False,
) -> dict[str, Any]:
    doc = doctrine()
    layout = doc.get("rack_layout") or {}
    dirs = list(layout.get("per_rack_dirs") or [])
    fid = str(slot_meta.get("field_id") or "")
    root = _racks_base() / fid
    created: list[str] = []
    row: dict[str, Any] = {
        "field_id": fid,
        "slot": slot_meta.get("slot"),
        "node_id": slot_meta.get("node_id"),
        "primary_role": slot_meta.get("primary_role"),
        "roles": slot_meta.get("roles"),
        "storage_root": str(root),
        "gb_quota": _gb_per_unit(),
    }
    if dry_run or not write:
        for name in dirs:
            created.append(str(root / name))
        row["dry_run"] = True
        row["created"] = created
        return row
    try:
        root.mkdir(parents=True, exist_ok=True)
        for name in dirs:
            p = root / name
            p.mkdir(parents=True, exist_ok=True)
            created.append(str(p))
        manifest = {
            "schema": "field-zachub-qemu-rack/v1",
            "updated": _utc(),
            "field_id": fid,
            "slot": slot_meta.get("slot"),
            "node_id": slot_meta.get("node_id"),
            "primary_role": slot_meta.get("primary_role"),
            "roles": slot_meta.get("roles"),
            "tunnel": slot_meta.get("tunnel"),
            "ssh_port": slot_meta.get("ssh_port"),
            "gb_quota": _gb_per_unit(),
            "h7_protocol": "field-h7s-fs",
            "one_big_drive": True,
            "qemu_source": "GrokLab/deploy/qemu-world-pipeline.py",
            "deploy_root": str(_deploy_root()),
            "vm_root": str(_vm_base()),
            "no_team_drive": True,
            "product": "ZacHub",
            "owners": ["Grok", "Zac"],
        }
        _save(root / "manifest.json", manifest)
        created.append(str(root / "manifest.json"))
        ceilings = _role_ceilings_gb()
        quota = root / "h7-shard" / "quota.json"
        _save(quota, {
            "schema": "zachub-h7-quota/v2",
            "gb_per_rack": _gb_per_unit(),
            "operational_ceilings_gb": ceilings,
            "roles": slot_meta.get("roles"),
            "field_id": fid,
            "redundant_from_dns_dhcp_remainder": True,
            "internet_isolated": True,
        })
        created.append(str(quota))
        pool = root / "h7-shard" / "redundant-pool.json"
        if not pool.is_file():
            _save(pool, {
                "schema": "zachub-redundant-pool/v1",
                "field_id": fid,
                "converted_gb": 0.0,
                "pending_gb": round(_gb_per_unit() - sum(ceilings.values()) * 0.25, 3),
                "protocol": "field-h7s-fs",
                "internet_isolated": True,
            })
            created.append(str(pool))
        row["ok"] = True
        row["created"] = created
    except OSError as exc:
        row["ok"] = False
        row["error"] = str(exc)[:200]
    return row


def provision(
    *,
    write: bool = True,
    dry_run: bool = False,
    burn_stale: bool = True,
) -> dict[str, Any]:
    doc = doctrine()
    status = qemu_pipeline_status()
    slots = build_slots(status)
    burn = burn_stale_team_qemu(dry_run=dry_run) if burn_stale else {"skipped": True}
    racks: list[dict[str, Any]] = []
    for meta in slots:
        racks.append(provision_rack(meta, write=write, dry_run=dry_run))

    big_drive = _one_big_drive_manifest(slots)
    manifest_path = Path(big_drive["manifest_path"])
    convert = convert_remaining_storage(slots, write=write, dry_run=dry_run)
    if write and not dry_run:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        _save(manifest_path, big_drive)
        big_drive = _one_big_drive_manifest(slots)

    solo = None
    rack_mod = _mod("lib/field-rack-uniqueness.py", "rack_uniqueness")
    if rack_mod and hasattr(rack_mod, "assert_solo_field"):
        os.environ.setdefault("WORLD_PIPELINE_SLOT", "host")
        try:
            solo = rack_mod.assert_solo_field(write=False)
        except (OSError, TypeError, ValueError):
            solo = None

    out = {
        "ok": status.get("ok", True) and all(r.get("ok", True) for r in racks),
        "schema": "field-zachub-qemu-racks/v1",
        "updated": _utc(),
        "product": "ZacHub",
        "owners": ["Grok", "Zac"],
        "motto": doc.get("motto"),
        "dry_run": dry_run,
        "no_team_drive_servers": True,
        "deploy_root": str(_deploy_root()),
        "vm_root": str(_vm_base()),
        "qemu_pipeline": {
            "path": str(PIPELINE),
            "running": status.get("running"),
            "completed": status.get("completed"),
            "target": status.get("target"),
        },
        "burn_stale_qemu": burn,
        "slots": slots,
        "racks_provisioned": racks,
        "one_big_drive": big_drive,
        "storage_totals": big_drive.get("storage_totals") or storage_totals(slots),
        "redundant_convert": convert,
        "internet_isolated": True,
        "solo_field": solo,
        "edge_roles": list((doc.get("roles") or {}).get("primary_cycle") or []),
    }
    if write and not dry_run:
        _save(PANEL, out)
        api = H7_DOCS / "api" / "field-zachub-qemu-racks.json"
        api.parent.mkdir(parents=True, exist_ok=True)
        api.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "field-zachub-qemu-racks/v1":
        cached["qemu_pipeline"] = {
            **(cached.get("qemu_pipeline") or {}),
            **{
                k: v
                for k, v in qemu_pipeline_status().items()
                if k in ("running", "completed", "target", "ok")
            },
        }
        cached["slots"] = build_slots(qemu_pipeline_status())
        cached["storage_totals"] = storage_totals(cached["slots"])
        cached["internet_isolated"] = True
        return cached
    return provision(write=False, dry_run=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    dry_run = "--dry-run" in sys.argv or os.environ.get("ZACHUB_DRY_RUN", "").strip() in ("1", "yes")
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("slots", "map"):
        print(json.dumps({"slots": build_slots()}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("burn", "burn-stale"):
        print(json.dumps(burn_stale_team_qemu(dry_run=dry_run), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("provision", "apply"):
        no_burn = "--no-burn" in sys.argv
        print(json.dumps(
            provision(write=not dry_run, dry_run=dry_run, burn_stale=not no_burn),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("convert", "convert-remaining", "redundant"):
        print(json.dumps(
            convert_remaining_storage(write=not dry_run, dry_run=dry_run),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd in ("storage-totals", "totals"):
        print(json.dumps(storage_totals(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-zachub-qemu-racks.py [json|provision|convert|storage-totals|slots|burn] [--dry-run] [--no-burn]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())