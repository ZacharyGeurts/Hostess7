#!/usr/bin/env pythong
"""Valuable value settings — type-tagged vault priority; polite reclamation when disk is low."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
VALUES_PATH = INSTALL / "data" / "field-valuable-values.json"
OVERRIDES_PATH = STATE / "field-valuable-values.override.json"
VAULT_DIR = STATE / "field-soft-vault"
TOMBSTONE_PATH = VAULT_DIR / "tombstones.jsonl"
EATEN_PATH = VAULT_DIR / "eaten.jsonl"
FILE_TYPES_PATH = INSTALL / "Queen" / "data" / "queen-file-types.json"
SCHEMA = "field-valuable-values/v1"

_SOVEREIGN = None


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sovereign() -> Any:
    global _SOVEREIGN
    if _SOVEREIGN is None:
        _SOVEREIGN = _load_module("sovereign_clock", INSTALL / "lib" / "sovereign-clock.py")
    return _SOVEREIGN


def sovereign_ns() -> int:
    mod = _sovereign()
    if mod:
        return int(mod.ns_linear())
    import time
    return time.time_ns()


def sovereign_z(section: str = "soft_value") -> str:
    mod = _sovereign()
    if mod:
        return mod.utc_z(section)
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _atomic_write(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_values() -> dict[str, Any]:
    base = _read_json(VALUES_PATH, {"schema": SCHEMA, "default_value": 50})
    overrides = _read_json(OVERRIDES_PATH, {})
    if overrides.get("schema") == SCHEMA:
        for key in ("by_type", "by_extension", "disk_pressure", "reclaim_floor", "default_value"):
            if key in overrides:
                if isinstance(overrides[key], dict) and isinstance(base.get(key), dict):
                    merged = dict(base.get(key) or {})
                    merged.update(overrides[key])
                    base[key] = merged
                else:
                    base[key] = overrides[key]
    base["overrides_path"] = str(OVERRIDES_PATH)
    return base


def save_override(patch: dict[str, Any]) -> dict[str, Any]:
    doc = _read_json(OVERRIDES_PATH, {"schema": SCHEMA, "updated": sovereign_z()})
    doc["schema"] = SCHEMA
    doc["updated"] = sovereign_z()
    for key in ("by_type", "by_extension", "disk_pressure"):
        if key not in patch:
            continue
        bucket = doc.setdefault(key, {})
        if isinstance(patch[key], dict):
            bucket.update(patch[key])
    _atomic_write(OVERRIDES_PATH, doc)
    return load_values()


def _extension_map() -> dict[str, str]:
    reg = _read_json(FILE_TYPES_PATH, {})
    out: dict[str, str] = {}
    for type_id, spec in (reg.get("types") or {}).items():
        for ext in spec.get("extensions") or []:
            low = str(ext).lower()
            if low and low not in out:
                out[low] = type_id
    return out


def resolve_type_id(path: str | Path) -> str:
    p = Path(path)
    ext = p.suffix.lower()
    ext_map = _extension_map()
    if ext in ext_map:
        return ext_map[ext]
    name = p.name.lower()
    reg = _read_json(FILE_TYPES_PATH, {})
    for type_id, spec in (reg.get("types") or {}).items():
        for pat in spec.get("name_patterns") or []:
            if pat.lower() in name or name == pat.lower():
                return type_id
    if p.is_dir():
        return "code_chamber"
    return "unknown"


def resolve_value(
    path: str | Path,
    *,
    values: dict[str, Any] | None = None,
    type_id: str | None = None,
) -> dict[str, Any]:
    """Valuable score for a path — higher = keep longer under disk pressure."""
    values = values or load_values()
    p = Path(path)
    ext = p.suffix.lower()
    tid = type_id or resolve_type_id(p)

    by_ext = values.get("by_extension") or {}
    by_type = values.get("by_type") or {}
    default = int(values.get("default_value") or 50)

    if ext in by_ext:
        row = by_ext[ext]
        val = int(row.get("value", default))
        label = row.get("label") or _value_label(values, val)
        source = "extension"
    elif tid in by_type:
        row = by_type[tid]
        val = int(row.get("value", default))
        label = row.get("label") or _value_label(values, val)
        source = "type"
    else:
        val = default
        label = _value_label(values, val)
        source = "default"

    return {
        "path": str(p),
        "type_id": tid,
        "extension": ext,
        "value": val,
        "label": label,
        "source": source,
    }


def _value_label(values: dict[str, Any], val: int) -> str:
    labels = (values.get("scale") or {}).get("labels") or {}
    best = "standard"
    best_dist = 999
    for name, target in labels.items():
        dist = abs(int(target) - val)
        if dist < best_dist:
            best_dist = dist
            best = name
    return best


def set_type_value(type_id: str, value: int, *, label: str | None = None) -> dict[str, Any]:
    row: dict[str, Any] = {"value": int(value)}
    if label:
        row["label"] = label
    return save_override({"by_type": {type_id: row}})


def set_extension_value(ext: str, value: int, *, label: str | None = None) -> dict[str, Any]:
    ext = ext if ext.startswith(".") else f".{ext}"
    row: dict[str, Any] = {"value": int(value)}
    if label:
        row["label"] = label
    return save_override({"by_extension": {ext.lower(): row}})


def disk_free_mb(path: Path | None = None) -> dict[str, Any]:
    target = path or STATE
    target.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(target)
    free_mb = round(usage.free / (1024 * 1024), 1)
    total_mb = round(usage.total / (1024 * 1024), 1)
    return {
        "path": str(target),
        "free_mb": free_mb,
        "total_mb": total_mb,
        "used_mb": round((usage.used) / (1024 * 1024), 1),
        "pct_free": round(100.0 * usage.free / usage.total, 2) if usage.total else 0,
    }


def _vault_bytes(vault_path: str) -> int:
    root = Path(vault_path)
    if not root.exists():
        return 0
    if root.is_file():
        try:
            return root.stat().st_size
        except OSError:
            return 0
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            try:
                total += (Path(dirpath) / fn).stat().st_size
            except OSError:
                continue
    return total


def load_tombstones(*, active_only: bool = True) -> list[dict[str, Any]]:
    if not TOMBSTONE_PATH.is_file():
        return []
    latest: dict[str, dict[str, Any]] = {}
    try:
        for line in TOMBSTONE_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            doc = json.loads(line)
            vid = str(doc.get("id") or "")
            if not vid:
                continue
            latest[vid] = doc
    except (OSError, json.JSONDecodeError):
        return []
    out: list[dict[str, Any]] = []
    values = load_values()
    for doc in latest.values():
        if active_only and not doc.get("active", True):
            continue
        if doc.get("eaten"):
            continue
        path = str(doc.get("path") or doc.get("vault_path") or "")
        val = resolve_value(path, values=values)
        doc = {**doc, **val}
        doc["vault_bytes"] = _vault_bytes(str(doc.get("vault_path") or ""))
        out.append(doc)
    return out


def reclaim_plan(
    *,
    need_mb: float | None = None,
    values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Sorted eat-order — lowest valuable value first, then oldest sovereign stamp."""
    values = values or load_values()
    pressure = values.get("disk_pressure") or {}
    disk = disk_free_mb(VAULT_DIR)
    free_mb = float(disk["free_mb"])
    target = float(pressure.get("target_free_mb") or pressure.get("reclaim_free_mb") or 1024)
    reclaim_at = float(pressure.get("reclaim_free_mb") or 1024)
    critical_at = float(pressure.get("critical_free_mb") or 256)
    floor = int(values.get("reclaim_floor") or 60)

    if need_mb is None:
        if free_mb >= reclaim_at:
            return {
                "ok": True,
                "action": "none",
                "polite": True,
                "message": f"Disk comfortable · {free_mb} MB free",
                "disk": disk,
                "candidates": [],
            }
        need_mb = max(0.0, target - free_mb)

    mode = "critical" if free_mb < critical_at else "polite"
    max_value = floor if mode == "polite" else min(floor + 15, 75)

    candidates = load_tombstones(active_only=True)
    candidates.sort(key=lambda r: (int(r.get("value") or 50), int(r.get("sovereign_ns") or 0)))

    plan: list[dict[str, Any]] = []
    freed = 0.0
    need_bytes = need_mb * 1024 * 1024
    for row in candidates:
        if int(row.get("value") or 0) > max_value:
            continue
        vb = int(row.get("vault_bytes") or 0)
        plan.append({
            "vault_id": row.get("id"),
            "path": row.get("path"),
            "type_id": row.get("type_id"),
            "value": row.get("value"),
            "label": row.get("label"),
            "vault_bytes": vb,
            "sovereign_at": row.get("sovereign_at"),
        })
        freed += vb
        if freed >= need_bytes:
            break

    return {
        "ok": True,
        "action": "reclaim" if plan else "none",
        "polite": bool(pressure.get("polite", True)),
        "mode": mode,
        "disk": disk,
        "need_mb": round(need_mb, 2),
        "floor_value": floor,
        "max_eat_value": max_value,
        "candidates": plan,
        "freed_mb": round(freed / (1024 * 1024), 2),
        "message": (
            f"Would reclaim {len(plan)} vault entries · ~{round(freed / (1024 * 1024), 1)} MB"
            if plan
            else "Nothing low-value enough to reclaim politely"
        ),
    }


def _append_tombstone_line(doc: dict[str, Any]) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    with TOMBSTONE_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False) + "\n")


def _append_eaten(doc: dict[str, Any]) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    doc.setdefault("sovereign_ns", sovereign_ns())
    doc.setdefault("sovereign_at", sovereign_z("soft_eaten"))
    with EATEN_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False) + "\n")


def reclaim_space(
    *,
    need_mb: float | None = None,
    dry_run: bool = False,
    confirm: bool = False,
) -> dict[str, Any]:
    """Eat least-valuable soft vault bytes first — lineage kept in eaten ledger."""
    plan_doc = reclaim_plan(need_mb=need_mb)
    if plan_doc.get("action") != "reclaim":
        return plan_doc
    candidates = plan_doc.get("candidates") or []
    if not candidates:
        return plan_doc
    if dry_run:
        plan_doc["dry_run"] = True
        return plan_doc
    if not confirm and plan_doc.get("mode") != "critical":
        return {
            **plan_doc,
            "ok": False,
            "error": "confirm_required",
            "message": "Pass confirm=true or set FIELD_RECLAIM_CONFIRM=1 — polite reclaim needs consent",
        }

    pressure = load_values().get("disk_pressure") or {}
    limit = int(pressure.get("batch_limit") or 32)
    eaten: list[dict[str, Any]] = []
    freed = 0

    for row in candidates[:limit]:
        vid = str(row.get("vault_id") or "")
        vault_sub = VAULT_DIR / vid
        vb = int(row.get("vault_bytes") or 0)
        try:
            if vault_sub.is_dir():
                shutil.rmtree(vault_sub)
            elif vault_sub.is_file():
                vault_sub.unlink()
        except OSError as exc:
            eaten.append({"vault_id": vid, "ok": False, "error": str(exc)})
            continue

        tombstone = {
            "schema": "field-soft-vault/v1",
            "id": vid,
            "action": "polite_eaten",
            "active": False,
            "eaten": True,
            "path": row.get("path"),
            "value": row.get("value"),
            "label": row.get("label"),
            "type_id": row.get("type_id"),
            "vault_bytes": vb,
            "reason": "disk_pressure_reclaim",
            "mode": plan_doc.get("mode"),
            "sovereign_ns": sovereign_ns(),
            "sovereign_at": sovereign_z("soft_eaten"),
        }
        _append_tombstone_line(tombstone)
        _append_eaten(tombstone)
        eaten.append({"vault_id": vid, "ok": True, "path": row.get("path"), "value": row.get("value"), "vault_bytes": vb})
        freed += vb

    return {
        "ok": True,
        "action": "reclaimed",
        "polite": plan_doc.get("polite"),
        "mode": plan_doc.get("mode"),
        "eaten_count": len([e for e in eaten if e.get("ok")]),
        "freed_mb": round(freed / (1024 * 1024), 2),
        "eaten": eaten,
        "disk_after": disk_free_mb(VAULT_DIR),
        "message": f"Politely reclaimed {len(eaten)} vault entries · ~{round(freed / (1024 * 1024), 1)} MB",
    }


def panel_json() -> dict[str, Any]:
    values = load_values()
    disk = disk_free_mb(VAULT_DIR)
    tombs = load_tombstones()
    vault_mb = round(sum(int(t.get("vault_bytes") or 0) for t in tombs) / (1024 * 1024), 2)
    fs_panel: dict[str, Any] = {}
    fs_mod = _load_module("field_filesystem_update", INSTALL / "lib" / "field-filesystem-update.py")
    if fs_mod and hasattr(fs_mod, "status"):
        try:
            fs_panel = fs_mod.status(write=False)
        except Exception:
            fs_panel = {}
    return {
        "schema": SCHEMA,
        "sovereign_at": sovereign_z(),
        "values_path": str(VALUES_PATH),
        "overrides_path": str(OVERRIDES_PATH),
        "default_value": values.get("default_value"),
        "reclaim_floor": values.get("reclaim_floor"),
        "disk": disk,
        "vault_active": len(tombs),
        "vault_mb": vault_mb,
        "disk_pressure": values.get("disk_pressure"),
        "type_count": len(values.get("by_type") or {}),
        "extension_count": len(values.get("by_extension") or {}),
        "filesystem": fs_panel,
        "warn_disk": bool(fs_panel.get("warn")),
        "deleted_mb": fs_panel.get("deleted_mb"),
        "overwrite_pending_mb": fs_panel.get("overwrite_pending_mb"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "panel":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve" and len(sys.argv) > 2:
        print(json.dumps(resolve_value(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "set-type" and len(sys.argv) > 3:
        label = sys.argv[4] if len(sys.argv) > 4 else None
        out = set_type_value(sys.argv[2], int(sys.argv[3]), label=label)
        print(json.dumps({"ok": True, "type_id": sys.argv[2], "values": out}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "set-ext" and len(sys.argv) > 3:
        label = sys.argv[4] if len(sys.argv) > 4 else None
        out = set_extension_value(sys.argv[2], int(sys.argv[3]), label=label)
        print(json.dumps({"ok": True, "extension": sys.argv[2], "values": out}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "plan":
        need = float(sys.argv[2]) if len(sys.argv) > 2 else None
        print(json.dumps(reclaim_plan(need_mb=need), ensure_ascii=False, indent=2))
        return 0
    if cmd == "reclaim":
        need = None
        if len(sys.argv) > 2 and sys.argv[2] not in ("--dry-run", "--confirm"):
            try:
                need = float(sys.argv[2])
            except ValueError:
                need = None
        dry = "--dry-run" in sys.argv or os.environ.get("FIELD_RECLAIM_DRY", "").lower() in ("1", "true")
        confirm = "--confirm" in sys.argv or os.environ.get("FIELD_RECLAIM_CONFIRM", "").lower() in ("1", "true")
        print(json.dumps(reclaim_space(need_mb=need, dry_run=dry, confirm=confirm), ensure_ascii=False, indent=2))
        return 0
    if cmd == "list":
        print(json.dumps({"tombstones": load_tombstones()}, ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage",
                "cmds": [
                    "panel",
                    "resolve PATH",
                    "set-type TYPE_ID VALUE [label]",
                    "set-ext EXT VALUE [label]",
                    "plan [need_mb]",
                    "reclaim [need_mb] [--dry-run] [--confirm]",
                    "list",
                ],
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())