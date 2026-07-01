#!/usr/bin/env pythong
"""Field filesystem update — disk pressure warnings, tiered delete destroy, destroyed catalog."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-filesystem-doctrine.json"
OVERLAY_PATH = STATE / "field-filesystem-overlay.json"
LISTED_DELETES = STATE / "field-filesystem-listed-deletes.jsonl"
DESTROYED_CATALOG = STATE / "field-filesystem-destroyed-catalog.jsonl"
PANEL_PATH = STATE / "field-filesystem-panel.json"
VAULT_DIR = STATE / "field-soft-vault"
TOMBSTONE_PATH = VAULT_DIR / "tombstones.jsonl"
SCHEMA = "field-filesystem-update/v1"

_SOFT = None
_INDEXER = None


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _soft() -> Any:
    global _SOFT
    if _SOFT is None:
        _SOFT = _load_module("field_soft_value", INSTALL / "lib" / "field-soft-value.py")
    return _SOFT


def _indexer() -> Any:
    global _INDEXER
    if _INDEXER is None:
        _INDEXER = _load_module("field_drive_indexer", INSTALL / "lib" / "field-drive-indexer.py")
    return _INDEXER


def _now() -> str:
    mod = _load_module("sovereign_clock", INSTALL / "lib" / "sovereign-clock.py")
    if mod:
        return mod.utc_z("filesystem")
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def _append_jsonl(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False) + "\n")


def _doctrine() -> dict[str, Any]:
    return _read_json(DOCTRINE, {"disk_pressure": {}, "tiers": {}})


def _tier_rank(tier: str) -> int:
    tiers = (_doctrine().get("tiers") or {})
    row = tiers.get(tier) or {}
    return int(row.get("rank") or (1 if tier == "listed" else 2 if tier == "bin" else 99))


def load_overlay() -> dict[str, Any]:
    doc = _read_json(OVERLAY_PATH, {"schema": "field-filesystem-overlay/v1", "entries": {}})
    if not isinstance(doc.get("entries"), dict):
        doc["entries"] = {}
    return doc


def save_overlay(doc: dict[str, Any]) -> None:
    doc["schema"] = "field-filesystem-overlay/v1"
    doc["updated"] = _now()
    _atomic_write(OVERLAY_PATH, doc)


def _overlay_entry(path: str) -> dict[str, Any]:
    key = str(path).replace("\\", "/")
    overlay = load_overlay()
    return dict((overlay.get("entries") or {}).get(key) or {})


def _set_overlay(path: str, patch: dict[str, Any]) -> dict[str, Any]:
    overlay = load_overlay()
    entries: dict[str, Any] = overlay.setdefault("entries", {})
    key = str(path).replace("\\", "/")
    row = dict(entries.get(key) or {"path": key})
    row.update(patch)
    row["path"] = key
    row["updated"] = _now()
    entries[key] = row
    save_overlay(overlay)
    return row


def enrich_catalog_row(row: dict[str, Any]) -> dict[str, Any]:
    """Merge overlay deleted/destroyed fields onto a catalog file row."""
    path = str(row.get("path") or "")
    if not path:
        return row
    ov = _overlay_entry(path)
    out = {**row}
    for key in ("deleted", "destroyed", "destroyed_at", "destroyed_date", "tier", "deleted_at"):
        if key in ov:
            out[key] = ov[key]
    if ov.get("destroyed"):
        out["catalog_only"] = True
    return out


def disk_snapshot(path: Path | None = None) -> dict[str, Any]:
    target = path or STATE
    target.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(target)
    total = int(usage.total)
    used = int(usage.used)
    free = int(usage.free)
    return {
        "path": str(target),
        "total_bytes": total,
        "used_bytes": used,
        "free_bytes": free,
        "total_mb": round(total / (1024 * 1024), 1),
        "used_mb": round(used / (1024 * 1024), 1),
        "free_mb": round(free / (1024 * 1024), 1),
        "pct_used": round(100.0 * used / total, 2) if total else 0,
        "pct_free": round(100.0 * free / total, 2) if total else 0,
    }


def _pressure_thresholds() -> dict[str, float]:
    sv = _soft()
    values = sv.load_values() if sv else {}
    pressure = values.get("disk_pressure") or _doctrine().get("disk_pressure") or {}
    return {
        "warn_free_mb": float(pressure.get("warn_free_mb") or 2048),
        "reclaim_free_mb": float(pressure.get("reclaim_free_mb") or 1024),
        "critical_free_mb": float(pressure.get("critical_free_mb") or 256),
        "target_free_mb": float(pressure.get("target_free_mb") or 1536),
    }


def pressure_level(disk: dict[str, Any] | None = None) -> str:
    disk = disk or disk_snapshot()
    free_mb = float(disk.get("free_mb") or 0)
    th = _pressure_thresholds()
    if free_mb < th["critical_free_mb"]:
        return "critical"
    if free_mb < th["reclaim_free_mb"]:
        return "reclaim"
    if free_mb < th["warn_free_mb"]:
        return "warn"
    return "ok"


def _listed_delete_rows() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not LISTED_DELETES.is_file():
        return out
    try:
        for line in LISTED_DELETES.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            doc = json.loads(line)
            if doc.get("destroyed"):
                continue
            if doc.get("active", True):
                out.append(doc)
    except (OSError, json.JSONDecodeError):
        pass
    return out


def _bin_rows() -> list[dict[str, Any]]:
    sv = _soft()
    if not sv:
        return []
    rows = sv.load_tombstones(active_only=True)
    for row in rows:
        row.setdefault("tier", "bin")
    return rows


def deleted_inventory() -> dict[str, Any]:
    """Bytes in deleted tiers still on disk — listed first to destroy, bin more protected."""
    listed = _listed_delete_rows()
    bin_rows = _bin_rows()
    sv = _soft()
    values = sv.load_values() if sv else {}

    def _enrich(row: dict[str, Any], tier: str) -> dict[str, Any]:
        path = str(row.get("path") or row.get("vault_path") or "")
        val = sv.resolve_value(path, values=values) if sv and path else {"value": 50, "label": "standard"}
        size = int(row.get("size") or row.get("vault_bytes") or 0)
        if not size and path:
            p = Path(path)
            if p.is_file():
                try:
                    size = p.stat().st_size
                except OSError:
                    size = 0
        return {
            **row,
            "tier": tier,
            "tier_rank": _tier_rank(tier),
            "value": int(val.get("value") or 50),
            "label": val.get("label"),
            "bytes": size,
        }

    listed_e = [_enrich(r, "listed") for r in listed]
    bin_e = [_enrich(r, "bin") for r in bin_rows]
    listed_bytes = sum(int(r.get("bytes") or 0) for r in listed_e)
    bin_bytes = sum(int(r.get("bytes") or 0) for r in bin_e)
    return {
        "listed": {"count": len(listed_e), "bytes": listed_bytes, "entries": listed_e},
        "bin": {"count": len(bin_e), "bytes": bin_bytes, "entries": bin_e},
        "deleted_bytes": listed_bytes + bin_bytes,
        "listed_bytes": listed_bytes,
        "bin_bytes": bin_bytes,
    }


def destroy_plan(*, need_mb: float | None = None) -> dict[str, Any]:
    disk = disk_snapshot()
    level = pressure_level(disk)
    th = _pressure_thresholds()
    free_mb = float(disk["free_mb"])
    inv = deleted_inventory()

    if need_mb is None:
        if level in ("ok",):
            need_mb = 0.0
        elif level == "warn":
            need_mb = max(0.0, th["target_free_mb"] - free_mb)
        else:
            need_mb = max(0.0, th["target_free_mb"] - free_mb)

    candidates: list[dict[str, Any]] = []
    for tier in ("listed", "bin"):
        bucket = inv.get(tier) or {}
        for row in bucket.get("entries") or []:
            candidates.append(row)
    candidates.sort(key=lambda r: (int(r.get("tier_rank") or 99), int(r.get("value") or 50), str(r.get("deleted_at") or r.get("sovereign_at") or "")))

    plan: list[dict[str, Any]] = []
    freed = 0
    need_bytes = int(need_mb * 1024 * 1024)
    for row in candidates:
        vb = int(row.get("bytes") or 0)
        plan.append({
            "path": row.get("path"),
            "vault_id": row.get("id") or row.get("vault_id"),
            "tier": row.get("tier"),
            "tier_rank": row.get("tier_rank"),
            "value": row.get("value"),
            "label": row.get("label"),
            "bytes": vb,
            "bytes_mb": round(vb / (1024 * 1024), 3),
        })
        freed += vb
        if need_bytes > 0 and freed >= need_bytes:
            break

    warn_msg = (_doctrine().get("disk_pressure") or {}).get("warn_message")
    if level == "warn":
        message = warn_msg or "Disk is getting full — deleted files will begin being destroyed (listed, then bin)."
    elif level == "reclaim":
        message = (
            f"Reclaim active — {round(inv['deleted_bytes'] / (1024 * 1024), 1)} MB deleted bytes may be overwritten "
            f"(listed {round(inv['listed_bytes'] / (1024 * 1024), 1)} MB, bin {round(inv['bin_bytes'] / (1024 * 1024), 1)} MB)."
        )
    elif level == "critical":
        message = "Critical disk pressure — destroying least important deleted files now."
    else:
        message = f"Disk comfortable · {free_mb} MB free"

    return {
        "ok": True,
        "level": level,
        "disk": disk,
        "deleted": inv,
        "need_mb": round(need_mb, 2),
        "overwrite_pending_mb": round(inv["deleted_bytes"] / (1024 * 1024), 2),
        "plan_freed_mb": round(freed / (1024 * 1024), 2),
        "candidates": plan,
        "destroy_order": ["listed", "bin"],
        "warn": level in ("warn", "reclaim", "critical"),
        "message": message,
    }


def mark_deleted(
    path: str,
    *,
    tier: str = "listed",
    reason: str | None = None,
    size: int | None = None,
) -> dict[str, Any]:
    """Soft-delete — listed tier by default (destroyed before bin under pressure)."""
    p = Path(path).expanduser().resolve()
    key = str(p).replace("\\", "/")
    if size is None and p.is_file():
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
    doc = {
        "schema": SCHEMA,
        "path": key,
        "tier": tier,
        "deleted": True,
        "deleted_at": _now(),
        "reason": reason or "operator_listed_delete",
        "size": int(size or 0),
        "active": True,
        "destroyed": False,
    }
    if tier == "listed":
        _append_jsonl(LISTED_DELETES, doc)
    _set_overlay(key, {
        "deleted": True,
        "deleted_at": doc["deleted_at"],
        "tier": tier,
        "destroyed": False,
    })
    return {"ok": True, **doc}


def _catalog_destroy_record(row: dict[str, Any], *, reason: str) -> dict[str, Any]:
    destroyed_at = _now()
    return {
        "schema": "field-filesystem-destroyed/v1",
        "path": row.get("path"),
        "tier": row.get("tier"),
        "destroyed": True,
        "destroyed_at": destroyed_at,
        "destroyed_date": _today(),
        "catalog_only": True,
        "bytes_destroyed": int(row.get("bytes") or 0),
        "value": row.get("value"),
        "label": row.get("label"),
        "vault_id": row.get("vault_id"),
        "reason": reason,
        "sha256": row.get("sha256"),
        "role": row.get("role"),
        "description": row.get("description"),
    }


def destroy_candidates(
    *,
    need_mb: float | None = None,
    dry_run: bool = False,
    confirm: bool = False,
) -> dict[str, Any]:
    """Destroy deleted-tier bytes — catalog preserved with destroyed date."""
    plan_doc = destroy_plan(need_mb=need_mb)
    level = plan_doc.get("level") or "ok"
    if level == "ok" and not need_mb:
        return {**plan_doc, "action": "none", "destroyed_count": 0}

    candidates = plan_doc.get("candidates") or []
    if not candidates:
        return {**plan_doc, "action": "none", "destroyed_count": 0}

    if dry_run:
        return {**plan_doc, "action": "dry_run", "dry_run": True}

    if not confirm and level not in ("critical", "reclaim"):
        return {
            **plan_doc,
            "ok": False,
            "action": "confirm_required",
            "error": "confirm_required",
            "message": "Pass confirm=true to destroy deleted bytes and write destroyed catalog rows",
        }

    sv = _soft()
    destroyed: list[dict[str, Any]] = []
    freed = 0
    batch = int((_doctrine().get("disk_pressure") or {}).get("batch_limit") or 32)

    for row in candidates[:batch]:
        tier = str(row.get("tier") or "listed")
        path = str(row.get("path") or "")
        vault_id = str(row.get("vault_id") or "")

        if tier == "bin" and vault_id:
            vault_sub = VAULT_DIR / vault_id
            try:
                if vault_sub.is_dir():
                    shutil.rmtree(vault_sub)
                elif vault_sub.is_file():
                    vault_sub.unlink()
            except OSError as exc:
                destroyed.append({"path": path, "vault_id": vault_id, "ok": False, "error": str(exc)})
                continue
            tombstone = {
                "schema": "field-soft-vault/v1",
                "id": vault_id,
                "action": "filesystem_destroyed",
                "active": False,
                "eaten": True,
                "destroyed": True,
                "path": path,
                "vault_bytes": int(row.get("bytes") or 0),
                "reason": "disk_pressure_bin_overwrite",
                "sovereign_at": _now(),
            }
            _append_jsonl(TOMBSTONE_PATH, tombstone)
            rec = _catalog_destroy_record({**row, "path": path}, reason="disk_pressure_bin_overwrite")
            _append_jsonl(DESTROYED_CATALOG, rec)
            if path:
                _set_overlay(path, {
                    "deleted": True,
                    "destroyed": True,
                    "destroyed_at": rec["destroyed_at"],
                    "destroyed_date": rec["destroyed_date"],
                    "tier": "bin",
                    "catalog_only": True,
                })
            destroyed.append(rec)
            freed += int(row.get("bytes") or 0)
            continue

        # Listed tier — remove bytes if present, always catalog
        p = Path(path) if path else None
        if p and p.exists():
            try:
                if p.is_file():
                    p.unlink()
                elif p.is_dir():
                    shutil.rmtree(p)
            except OSError as exc:
                destroyed.append({"path": path, "ok": False, "error": str(exc)})
                continue

        rec = _catalog_destroy_record(row, reason="disk_pressure_listed_overwrite")
        _append_jsonl(DESTROYED_CATALOG, rec)
        if path:
            _set_overlay(path, {
                "deleted": True,
                "destroyed": True,
                "destroyed_at": rec["destroyed_at"],
                "destroyed_date": rec["destroyed_date"],
                "tier": "listed",
                "catalog_only": True,
            })
        # Mark listed delete ledger
        _append_jsonl(LISTED_DELETES, {**rec, "active": False})
        destroyed.append(rec)
        freed += int(row.get("bytes") or 0)

    panel = status(write=True)
    return {
        **plan_doc,
        "ok": True,
        "action": "destroyed",
        "destroyed_count": len(destroyed),
        "freed_mb": round(freed / (1024 * 1024), 2),
        "destroyed": destroyed,
        "disk_after": disk_snapshot(),
        "panel": panel,
        "message": f"Destroyed {len(destroyed)} deleted entries · catalog kept for {_today()}",
    }


def load_destroyed_catalog(*, date: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    if not DESTROYED_CATALOG.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in DESTROYED_CATALOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            doc = json.loads(line)
            if date and doc.get("destroyed_date") != date:
                continue
            out.append(doc)
            if len(out) >= limit:
                break
    except (OSError, json.JSONDecodeError):
        pass
    return out


def status(*, write: bool = False) -> dict[str, Any]:
    disk = disk_snapshot()
    plan = destroy_plan()
    inv = plan.get("deleted") or deleted_inventory()
    doc = {
        "schema": SCHEMA,
        "updated": _now(),
        "ok": True,
        "motto": (_doctrine().get("motto") or "Warn before overwrite — listed before bin, catalog keeps destroy date."),
        "disk": disk,
        "pressure_level": plan.get("level"),
        "warn": plan.get("warn"),
        "message": plan.get("message"),
        "used_mb": disk.get("used_mb"),
        "free_mb": disk.get("free_mb"),
        "deleted_bytes": inv.get("deleted_bytes"),
        "deleted_mb": round(int(inv.get("deleted_bytes") or 0) / (1024 * 1024), 2),
        "listed_deleted_mb": round(int(inv.get("listed_bytes") or 0) / (1024 * 1024), 2),
        "bin_deleted_mb": round(int(inv.get("bin_bytes") or 0) / (1024 * 1024), 2),
        "overwrite_pending_mb": plan.get("overwrite_pending_mb"),
        "need_mb": plan.get("need_mb"),
        "destroy_order": plan.get("destroy_order"),
        "destroy_candidates": len(plan.get("candidates") or []),
        "destroyed_catalog_count": len(load_destroyed_catalog(limit=10000)),
        "thresholds": _pressure_thresholds(),
    }
    if write:
        _atomic_write(PANEL_PATH, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return status(write=True)
    if action in ("plan", "destroy_plan"):
        return destroy_plan(need_mb=body.get("need_mb"))
    if action == "mark_deleted":
        return mark_deleted(
            str(body.get("path") or ""),
            tier=str(body.get("tier") or "listed"),
            reason=body.get("reason"),
        )
    if action in ("destroy", "reclaim", "overwrite"):
        return destroy_candidates(
            need_mb=body.get("need_mb"),
            dry_run=bool(body.get("dry_run")),
            confirm=bool(body.get("confirm")),
        )
    if action == "destroyed_catalog":
        return {
            "ok": True,
            "date": body.get("date"),
            "entries": load_destroyed_catalog(date=body.get("date"), limit=int(body.get("limit") or 200)),
        }
    if action == "enrich":
        row = body.get("row") or body
        return {"ok": True, "row": enrich_catalog_row(row if isinstance(row, dict) else {})}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "panel"):
        print(json.dumps(status(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "plan":
        need = float(sys.argv[2]) if len(sys.argv) > 2 else None
        print(json.dumps(destroy_plan(need_mb=need), ensure_ascii=False, indent=2))
        return 0
    if cmd == "mark" and len(sys.argv) > 2:
        print(json.dumps(mark_deleted(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "destroy":
        dry = "--dry-run" in sys.argv
        confirm = "--confirm" in sys.argv or os.environ.get("FIELD_FS_DESTROY_CONFIRM", "").lower() in ("1", "true")
        need = None
        for arg in sys.argv[2:]:
            if arg.startswith("--"):
                continue
            try:
                need = float(arg)
            except ValueError:
                pass
        print(json.dumps(destroy_candidates(need_mb=need, dry_run=dry, confirm=confirm), ensure_ascii=False, indent=2))
        return 0
    if cmd == "destroyed":
        date = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps({"entries": load_destroyed_catalog(date=date)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["json", "plan", "mark PATH", "destroy [--dry-run] [--confirm]", "destroyed [date]", "dispatch"]}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())