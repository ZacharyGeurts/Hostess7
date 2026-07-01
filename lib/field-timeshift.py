#!/usr/bin/env pythong
"""Field TimeShift — sovereign checkpoints, soft archival, rollback without heat."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
CHECKPOINT_DIR = STATE / "field-timeshift" / "checkpoints"
VAULT_DIR = STATE / "field-soft-vault"
TOMBSTONE_PATH = VAULT_DIR / "tombstones.jsonl"
MANIFEST_NAME = "checkpoint.json"
SCHEMA = "field-timeshift/v1"

_INDEXER = None
_SOVEREIGN = None
_SOFT_VALUE = None


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _indexer() -> Any:
    global _INDEXER
    if _INDEXER is None:
        _INDEXER = _load("field_drive_indexer", INSTALL / "lib" / "field-drive-indexer.py")
    return _INDEXER


def _sovereign() -> Any:
    global _SOVEREIGN
    if _SOVEREIGN is None:
        _SOVEREIGN = _load("sovereign_clock", INSTALL / "lib" / "sovereign-clock.py")
    return _SOVEREIGN


def _soft_value() -> Any:
    global _SOFT_VALUE
    if _SOFT_VALUE is None:
        _SOFT_VALUE = _load("field_soft_value", INSTALL / "lib" / "field-soft-value.py")
    return _SOFT_VALUE


def sovereign_ns() -> int:
    mod = _sovereign()
    if mod:
        return int(mod.ns_linear())
    import time
    return time.time_ns()


def sovereign_z(section: str = "timeshift") -> str:
    mod = _sovereign()
    if mod:
        return mod.utc_z(section)
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sovereign_compact() -> str:
    mod = _sovereign()
    if mod and hasattr(mod, "utc_compact"):
        return mod.utc_compact("timeshift")
    return sovereign_z("timeshift").replace("-", "").replace(":", "").replace(".", "")[:15] + "Z"


def _atomic_write(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_tombstone(doc: dict[str, Any]) -> None:
    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    doc.setdefault("sovereign_ns", sovereign_ns())
    doc.setdefault("sovereign_at", sovereign_z("soft_vault"))
    with TOMBSTONE_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(doc, ensure_ascii=False) + "\n")


def _append_history(doc: dict[str, Any]) -> None:
    idx = _indexer()
    if idx and hasattr(idx, "_append_history"):
        idx._append_history(doc)


def list_checkpoints() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not CHECKPOINT_DIR.is_dir():
        return out
    for child in sorted(CHECKPOINT_DIR.iterdir(), reverse=True):
        if not child.is_dir():
            continue
        manifest = child / MANIFEST_NAME
        if not manifest.is_file():
            continue
        try:
            doc = json.loads(manifest.read_text(encoding="utf-8"))
            doc["checkpoint_id"] = child.name
            doc["path"] = str(child)
            out.append(doc)
        except (OSError, json.JSONDecodeError):
            continue
    return out


def create_checkpoint(
    *,
    label: str | None = None,
    note: str | None = None,
    copy_table: bool = True,
) -> dict[str, Any]:
    """Snapshot sovereign-now index — pop back anytime."""
    idx = _indexer()
    if not idx:
        return {"ok": False, "error": "indexer_missing"}

    table = idx.build_table()
    idx.save_table(table)

    cid = sovereign_compact()
    ckpt = CHECKPOINT_DIR / cid
    ckpt.mkdir(parents=True, exist_ok=True)

    if copy_table:
        table_dst = ckpt / "table.json"
        table_dst.write_text(json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    history_src = STATE / "field-drive-index" / "history.jsonl"
    if history_src.is_file():
        try:
            shutil.copy2(history_src, ckpt / "history.jsonl")
        except OSError:
            pass

    manifest = {
        "schema": SCHEMA,
        "checkpoint_id": cid,
        "label": label or f"checkpoint {cid}",
        "note": note or "Sovereign field drive snapshot — rollback without recompile or heat",
        "sovereign_at": sovereign_z("timeshift"),
        "sovereign_ns": sovereign_ns(),
        "file_count": table.get("file_count"),
        "roots": table.get("roots"),
        "indexed_at_ns": table.get("indexed_at_ns"),
        "destructive": False,
        "soft_delete_policy": "archival_retreat",
    }
    _atomic_write(ckpt / MANIFEST_NAME, manifest)
    _append_history({
        "action": "timeshift_checkpoint",
        "checkpoint_id": cid,
        "file_count": table.get("file_count"),
        "label": manifest["label"],
    })

    store = _load("efficient_store", INSTALL / "lib" / "efficient_store.py")
    if store and hasattr(store, "append_record"):
        try:
            store.append_record("timeshift.checkpoint", manifest)
        except Exception:
            pass

    return {
        "ok": True,
        "checkpoint_id": cid,
        "path": str(ckpt),
        "manifest": manifest,
        "message": f"TimeShift sealed · {table.get('file_count')} files · {cid}",
    }


def rollback(checkpoint_id: str, *, confirm: bool = False) -> dict[str, Any]:
    """Restore table index to a prior checkpoint — non-destructive to live files."""
    if not confirm:
        return {
            "ok": False,
            "error": "confirm_required",
            "message": "Pass confirm=true — rollback restores index view, not live bytes unless vault restore",
            "checkpoint_id": checkpoint_id,
        }

    ckpt = CHECKPOINT_DIR / checkpoint_id
    manifest_path = ckpt / MANIFEST_NAME
    table_path = ckpt / "table.json"
    if not manifest_path.is_file() or not table_path.is_file():
        return {"ok": False, "error": "checkpoint_missing", "checkpoint_id": checkpoint_id}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    table = json.loads(table_path.read_text(encoding="utf-8"))

    index_dir = STATE / "field-drive-index"
    index_dir.mkdir(parents=True, exist_ok=True)
    live_table = index_dir / "table.json"
    backup = index_dir / f"table.pre-rollback.{sovereign_compact()}.json"
    if live_table.is_file():
        try:
            shutil.copy2(live_table, backup)
        except OSError:
            backup = None

    table["rolled_back_from"] = checkpoint_id
    table["rolled_back_at"] = sovereign_z("timeshift")
    table["rolled_back_ns"] = sovereign_ns()
    _atomic_write(live_table, table)

    _append_history({
        "action": "timeshift_rollback",
        "checkpoint_id": checkpoint_id,
        "file_count": table.get("file_count"),
        "backup_table": str(backup) if backup else None,
    })

    return {
        "ok": True,
        "checkpoint_id": checkpoint_id,
        "manifest": manifest,
        "file_count": table.get("file_count"),
        "backup_table": str(backup) if backup else None,
        "message": f"Rolled index back to {checkpoint_id} · live files untouched",
    }


def soft_retire(
    path: str,
    *,
    reason: str | None = None,
    operator: str | None = None,
) -> dict[str, Any]:
    """Archival retreat — vault bytes; never hard-delete another's work."""
    src = Path(path).expanduser().resolve()
    if not src.exists():
        return {"ok": False, "error": "path_missing", "path": str(src)}

    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    vault_id = hashlib.sha256(f"{src}:{sovereign_ns()}".encode()).hexdigest()[:16]
    vault_sub = VAULT_DIR / vault_id
    vault_sub.mkdir(parents=True, exist_ok=True)

    if src.is_file():
        dst = vault_sub / src.name
        try:
            shutil.copy2(src, dst)
        except OSError as exc:
            return {"ok": False, "error": str(exc), "path": str(src)}
        content_hash = hashlib.sha256(dst.read_bytes()).hexdigest()
        retired_path = dst
    else:
        dst = vault_sub / src.name
        try:
            shutil.copytree(src, dst, dirs_exist_ok=True)
        except OSError as exc:
            return {"ok": False, "error": str(exc), "path": str(src)}
        content_hash = None
        retired_path = dst

    sv = _soft_value()
    valuable = sv.resolve_value(src) if sv else {"value": 50, "label": "standard", "type_id": "unknown"}

    tombstone = {
        "schema": "field-soft-vault/v1",
        "id": vault_id,
        "action": "archival_retreat",
        "path": str(src),
        "vault_path": str(retired_path),
        "reason": reason or "soft retire — preserve lineage, reduce field heat",
        "operator": operator or os.environ.get("USER", "field"),
        "content_hash": content_hash,
        "active": True,
        "type_id": valuable.get("type_id"),
        "value": valuable.get("value"),
        "label": valuable.get("label"),
        "vault_bytes": sv._vault_bytes(str(retired_path)) if sv else None,
        "sovereign_ns": sovereign_ns(),
        "sovereign_at": sovereign_z("soft_vault"),
    }
    _append_tombstone(tombstone)
    _append_history({
        "action": "soft_retire",
        "path": str(src),
        "vault_id": vault_id,
        "reason": tombstone["reason"],
    })

    return {
        "ok": True,
        "archival_retreat": True,
        "hard_delete": False,
        "vault_id": vault_id,
        "vault_path": str(retired_path),
        "tombstone": tombstone,
        "message": f"Archived to vault · {src.name} — source left in place until operator confirms removal",
    }


def restore_vault(vault_id: str, *, dest: str | None = None) -> dict[str, Any]:
    """Restore vaulted bytes to dest or original path."""
    vault_sub = VAULT_DIR / vault_id
    if not vault_sub.is_dir():
        return {"ok": False, "error": "vault_missing", "vault_id": vault_id}

    original = None
    if TOMBSTONE_PATH.is_file():
        for line in TOMBSTONE_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue
            if doc.get("id") == vault_id:
                original = str(doc.get("path") or "")
                break

    target = Path(dest or original or "").expanduser()
    if not str(target):
        return {"ok": False, "error": "dest_required", "vault_id": vault_id}

    children = list(vault_sub.iterdir())
    if not children:
        return {"ok": False, "error": "vault_empty", "vault_id": vault_id}

    src = children[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if src.is_file():
            shutil.copy2(src, target)
        else:
            if target.exists():
                return {"ok": False, "error": "dest_exists", "path": str(target)}
            shutil.copytree(src, target)
    except OSError as exc:
        return {"ok": False, "error": str(exc), "vault_id": vault_id}

    _append_history({
        "action": "vault_restore",
        "vault_id": vault_id,
        "path": str(target),
        "original_path": original,
    })

    return {
        "ok": True,
        "vault_id": vault_id,
        "restored_to": str(target),
        "message": f"Restored from vault {vault_id}",
    }


def pop_back(checkpoint_id: str | None = None) -> dict[str, Any]:
    """Operator-friendly rollback — latest checkpoint if id omitted."""
    checkpoints = list_checkpoints()
    if not checkpoints:
        return {"ok": False, "error": "no_checkpoints", "message": "Create a checkpoint first"}
    cid = checkpoint_id or checkpoints[0]["checkpoint_id"]
    return rollback(cid, confirm=True)


def status() -> dict[str, Any]:
    idx = _indexer()
    now = idx.now_snapshot() if idx else {}
    sv = _soft_value()
    valuable = sv.panel_json() if sv else {}
    reclaim = sv.reclaim_plan() if sv else {}
    return {
        "schema": SCHEMA,
        "sovereign_at": sovereign_z("timeshift"),
        "checkpoints": len(list_checkpoints()),
        "latest_checkpoint": list_checkpoints()[:1],
        "vault_dir": str(VAULT_DIR),
        "tombstone_path": str(TOMBSTONE_PATH),
        "index_now": now,
        "valuable_values": valuable,
        "reclaim_posture": reclaim,
        "policy": {
            "hard_delete": False,
            "rollback": "index_and_vault",
            "heat": "archival_retreat_not_erasure",
            "disk_reclaim": "eat_lowest_value_first",
        },
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "checkpoint":
        label = sys.argv[2] if len(sys.argv) > 2 else None
        out = create_checkpoint(label=label)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "list":
        print(json.dumps({"checkpoints": list_checkpoints()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "rollback" and len(sys.argv) > 2:
        confirm = os.environ.get("FIELD_TIMESHIFT_CONFIRM", "").lower() in ("1", "true", "yes")
        out = rollback(sys.argv[2], confirm=confirm or "--confirm" in sys.argv)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "pop":
        cid = sys.argv[2] if len(sys.argv) > 2 else None
        out = pop_back(cid)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "retire" and len(sys.argv) > 2:
        reason = sys.argv[3] if len(sys.argv) > 3 else None
        out = soft_retire(sys.argv[2], reason=reason)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "restore" and len(sys.argv) > 2:
        dest = sys.argv[3] if len(sys.argv) > 3 else None
        out = restore_vault(sys.argv[2], dest=dest)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "values":
        sv = _soft_value()
        print(json.dumps(sv.panel_json() if sv else {}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "plan":
        sv = _soft_value()
        need = float(sys.argv[2]) if len(sys.argv) > 2 else None
        print(json.dumps(sv.reclaim_plan(need_mb=need) if sv else {}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "reclaim":
        sv = _soft_value()
        need = None
        if len(sys.argv) > 2 and sys.argv[2] not in ("--dry-run", "--confirm"):
            try:
                need = float(sys.argv[2])
            except ValueError:
                need = None
        dry = "--dry-run" in sys.argv
        confirm = "--confirm" in sys.argv or os.environ.get("FIELD_RECLAIM_CONFIRM", "").lower() in ("1", "true")
        out = sv.reclaim_space(need_mb=need, dry_run=dry, confirm=confirm) if sv else {"ok": False}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "set-type" and len(sys.argv) > 3:
        sv = _soft_value()
        label = sys.argv[4] if len(sys.argv) > 4 else None
        out = sv.set_type_value(sys.argv[2], int(sys.argv[3]), label=label) if sv else {}
        print(json.dumps({"ok": True, "values": out}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "set-ext" and len(sys.argv) > 3:
        sv = _soft_value()
        label = sys.argv[4] if len(sys.argv) > 4 else None
        out = sv.set_extension_value(sys.argv[2], int(sys.argv[3]), label=label) if sv else {}
        print(json.dumps({"ok": True, "values": out}, ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage",
                "cmds": [
                    "status",
                    "checkpoint [label]",
                    "list",
                    "rollback ID [--confirm]",
                    "pop [ID]",
                    "retire PATH [reason]",
                    "restore VAULT_ID [dest]",
                    "values",
                    "plan [need_mb]",
                    "reclaim [need_mb] [--dry-run] [--confirm]",
                    "set-type TYPE_ID VALUE [label]",
                    "set-ext EXT VALUE [label]",
                ],
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())