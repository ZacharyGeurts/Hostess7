#!/usr/bin/env python3
"""Rapid H7r storage distribution — 500+ botnet + 2500 global, parallel, efficient."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "ammodrive-storage-rapid-panel.json"
LEDGER = STATE / "ammodrive-storage-rapid-ledger.jsonl"
STAMP_VAULT = STATE / "field-one-device-stamps"
H7R_INDEX = STATE / "field-h7r-vault-index.json"
GLOBAL_REG = STATE / "field-global-servers-registry.json"
DEVICE_REG = STATE / "field-device-registry.json"
RACKS_ROOT = INSTALL / "GrokLab" / "deploy" / "qemu-racks"

STORAGE_VERSION = "h7r/1"
FIELD_ONE_VERSION = "field-one-rack-stack/v2"
DEFAULT_WORKERS = int(os.environ.get("NEXUS_STORAGE_RAPID_WORKERS") or 48)
DEFAULT_BATCH = int(os.environ.get("NEXUS_STORAGE_RAPID_BATCH") or 512)


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


def _safe_id(node_id: str) -> str:
    import re
    return re.sub(r"[^\w\-.]+", "_", str(node_id or "node"))[:120]


def _rack_paths() -> list[Path]:
    if not RACKS_ROOT.is_dir():
        return []
    return sorted(p for p in RACKS_ROOT.glob("qemu-rack-*") if p.is_dir())


def _hub() -> dict[str, Any]:
    return _load(INSTALL / "data" / "field-one-doctrine.json", {}).get("hub") or {}


def storage_stamp_doc(
    node: dict[str, Any],
    *,
    rack_id: str = "",
    metro_id: str = "",
    region_id: str = "",
) -> dict[str, Any]:
    nid = str(node.get("id") or "")
    pre = {
        "schema": FIELD_ONE_VERSION,
        "storage_version": STORAGE_VERSION,
        "storage_format": "h7r/1",
        "version": 3,
        "updated": _utc(),
        "field_one": True,
        "field_one_updated": True,
        "h7r_updated": True,
        "never_lose": True,
        "cooperative_mesh": True,
        "hub": _hub(),
        "node_id": nid,
        "kind": node.get("kind"),
        "rack_id": rack_id or node.get("field_id"),
        "metro_id": metro_id or node.get("metro_id"),
        "region_id": region_id or node.get("region_id"),
        "internet_isolated": True,
    }
    h = hashlib.sha256(json.dumps(pre, sort_keys=True).encode()).hexdigest()[:32]
    pre["content_hash"] = h
    return pre


def _stamp_path(node: dict[str, Any]) -> Path:
    root = str(node.get("storage_root") or "").strip()
    if root and Path(root).is_dir():
        return Path(root) / "field-one-stack.json"
    return STAMP_VAULT / f"{_safe_id(str(node.get('id') or ''))}.json"


def _has_latest(node: dict[str, Any]) -> bool:
    for path in (_stamp_path(node), STAMP_VAULT / f"{_safe_id(str(node.get('id') or ''))}.json"):
        if not path.is_file():
            continue
        doc = _load(path, {})
        if doc.get("storage_version") == STORAGE_VERSION and doc.get("h7r_updated"):
            return True
    if node.get("storage_version") == STORAGE_VERSION and node.get("h7r_updated"):
        return True
    return False


def _collect_targets() -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    seen: set[str] = set()

    rollout = _mod("lib/field-one-rollout.py", "rollout")
    if rollout:
        for n in rollout._load_botnet_nodes():
            nid = str(n.get("id") or "")
            if nid and nid not in seen:
                seen.add(nid)
                targets.append({**n, "source": "botnet"})

    gs = _load(GLOBAL_REG, {})
    for s in gs.get("servers") or []:
        nid = str(s.get("id") or s.get("node_id") or "")
        if not nid or nid in seen:
            continue
        seen.add(nid)
        targets.append({
            "id": nid,
            "node_id": s.get("node_id"),
            "kind": "global_server",
            "storage_root": str(RACKS_ROOT / str(s.get("field_id") or f"qemu-rack-{s.get('id', '').split('-')[-1]}")),
            "field_id": s.get("field_id"),
            "metro_id": s.get("metro_id"),
            "region_id": s.get("region_id"),
            "machine_profile": s.get("machine_profile"),
            "unique_location": s.get("unique_location"),
            "source": "global",
        })
    return targets


def _stamp_one(node: dict[str, Any], racks: list[Path]) -> dict[str, Any]:
    nid = str(node.get("id") or "")
    if _has_latest(node):
        return {"ok": True, "id": nid, "skipped": True}
    rack_idx = int(hashlib.sha256(nid.encode()).hexdigest()[:8], 16) % max(1, len(racks))
    rack = racks[rack_idx] if racks else None
    doc = storage_stamp_doc(
        node,
        rack_id=rack.name if rack else "",
        metro_id=str(node.get("metro_id") or ""),
        region_id=str(node.get("region_id") or ""),
    )
    primary = _stamp_path(node)
    compact = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    try:
        primary.parent.mkdir(parents=True, exist_ok=True)
        primary.write_text(compact, encoding="utf-8")
        vault = STAMP_VAULT / f"{_safe_id(nid)}.json"
        STAMP_VAULT.mkdir(parents=True, exist_ok=True)
        vault.write_text(compact, encoding="utf-8")
        if rack:
            h7r_dir = rack / "h7-shard" / "h7r-vault" / "stamps"
            h7r_dir.mkdir(parents=True, exist_ok=True)
            (h7r_dir / f"{_safe_id(nid)}.json").write_text(compact, encoding="utf-8")
        return {"ok": True, "id": nid, "primary": str(primary), "rack": rack.name if rack else None}
    except OSError as exc:
        return {"ok": False, "id": nid, "error": str(exc)[:120]}


def rapid_distribute(
    *,
    workers: int | None = None,
    batch_size: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Stamp all 500+ and 2500 targets with latest H7r storage — parallel waves."""
    workers_n = int(workers or DEFAULT_WORKERS)
    batch = int(batch_size or DEFAULT_BATCH)
    targets = _collect_targets()
    pending = [t for t in targets if not _has_latest(t)]
    racks = _rack_paths()

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "targets_total": len(targets),
            "pending": len(pending),
            "workers": workers_n,
            "batch_size": batch,
        }

    stamped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    skipped = 0

    for wave_start in range(0, len(pending), batch):
        wave = pending[wave_start: wave_start + batch]
        with ThreadPoolExecutor(max_workers=workers_n) as pool:
            futs = {pool.submit(_stamp_one, node, racks): node for node in wave}
            for fut in as_completed(futs):
                row = fut.result()
                if row.get("skipped"):
                    skipped += 1
                elif row.get("ok"):
                    stamped.append(row)
                else:
                    errors.append(row)

    # Bulk index update
    h7r_idx = _load(H7R_INDEX, {"schema": "field-h7r-vault-index/v1", "objects": {}})
    for row in stamped:
        nid = str(row.get("id") or "")
        h7r_idx.setdefault("objects", {})[nid] = {
            "node_id": nid,
            "storage_version": STORAGE_VERSION,
            "updated": _utc(),
            "rack": row.get("rack"),
        }
    h7r_idx["count"] = len(h7r_idx.get("objects") or {})
    h7r_idx["storage_version"] = STORAGE_VERSION
    h7r_idx["updated"] = _utc()
    _save(H7R_INDEX, h7r_idx)

    # Bulk global registry flag
    gs = _load(GLOBAL_REG, {})
    gs_servers = []
    for s in gs.get("servers") or []:
        sid = str(s.get("id") or "")
        gs_servers.append({
            **s,
            "storage_version": STORAGE_VERSION,
            "h7r_updated": True,
            "field_one_updated": True,
        } if sid else s)
    gs["servers"] = gs_servers
    gs["storage_version"] = STORAGE_VERSION
    gs["h7r_rapid"] = _utc()
    _save(GLOBAL_REG, gs)

    # Bulk device registry — single pass
    dev_reg = _load(DEVICE_REG, {})
    devices = list(dev_reg.get("devices") or [])
    for i, dev in enumerate(devices):
        devices[i] = {
            **dev,
            "storage_version": STORAGE_VERSION,
            "h7r_updated": True,
            "field_one_updated": True,
            "field_one_version": FIELD_ONE_VERSION,
        }
    dev_reg["devices"] = devices
    dev_reg["storage_version"] = STORAGE_VERSION
    dev_reg["h7r_rapid"] = _utc()
    _save(DEVICE_REG, dev_reg)

    out = {
        "ok": len(errors) == 0,
        "schema": "ammodrive-storage-rapid/v1",
        "updated": _utc(),
        "storage_version": STORAGE_VERSION,
        "targets_total": len(targets),
        "pending_before": len(pending),
        "stamped": len(stamped),
        "skipped_already_latest": skipped + (len(targets) - len(pending)),
        "errors": len(errors),
        "workers": workers_n,
        "waves": (len(pending) + batch - 1) // batch if pending else 0,
        "racks_used": len(racks),
        "api": "/api/ammodrive-storage-rapid",
    }
    _save(PANEL, out)
    _append_ledger({"event": "rapid_distribute", **{k: out[k] for k in ("stamped", "targets_total", "errors")}})
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "distribute").strip().lower()
    dry = "--dry-run" in sys.argv
    workers = DEFAULT_WORKERS
    batch = DEFAULT_BATCH
    for arg in sys.argv[2:]:
        if arg.isdigit():
            workers = int(arg)
    if cmd in ("distribute", "rapid", "upgrade", "h7r"):
        print(json.dumps(rapid_distribute(workers=workers, batch_size=batch, dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(_load(PANEL, {"ok": True, "pending": "run distribute"}), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "ammodrive-storage-rapid.py [distribute|json] [--dry-run]",
        "storage_version": STORAGE_VERSION,
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())