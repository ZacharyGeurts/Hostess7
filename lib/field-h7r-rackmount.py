#!/usr/bin/env python3
"""H7r rackmount vault — stripe mirrors across AmmoDrive QEMU racks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-h7r-doctrine.json"
FOREVER_LEDGER = STATE / "field-h7r-forever-ledger.jsonl"
VAULT_INDEX = STATE / "field-h7r-vault-index.json"
RACKS_ROOT = INSTALL / "GrokLab" / "deploy" / "qemu-racks"


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


def _h7r() -> Any:
    mod = _mod("lib/field-h7r-format.py", "h7r")
    if not mod:
        raise RuntimeError("field-h7r-format.py missing")
    return mod


def rack_vault_dir(rack_path: Path) -> Path:
    return rack_path / "h7-shard" / "h7r-vault"


def rack_stripe_dir(rack_path: Path) -> Path:
    return rack_path / "h7-shard" / "h7r-stripes"


def list_racks() -> list[Path]:
    if not RACKS_ROOT.is_dir():
        return []
    return sorted(p for p in RACKS_ROOT.glob("qemu-rack-*") if p.is_dir())


def object_id(forever_hash: str) -> str:
    return forever_hash[:32]


def store_blob(
    payload: bytes,
    *,
    owner_personhood_id: str,
    owner_ammodrive_id: str,
    original_name: str = "blob",
    open_read: bool = False,
) -> dict[str, Any]:
    h7r = _h7r()
    packed = h7r.pack(
        payload,
        owner_personhood_id=owner_personhood_id,
        owner_ammodrive_id=owner_ammodrive_id,
        original_name=original_name,
        open_read=open_read,
    )
    header, _ = h7r.unpack(packed)
    oid = object_id(str(header.get("forever_hash") or ""))
    racks = list_racks()
    if not racks:
        central = STATE / "field-h7r-vault" / f"{oid}.h7r"
        central.parent.mkdir(parents=True, exist_ok=True)
        central.write_bytes(packed)
        mirrors = [str(central)]
    else:
        mirrors = []
        for i, rack in enumerate(racks):
            vault = rack_vault_dir(rack)
            vault.mkdir(parents=True, exist_ok=True)
            target = vault / f"{oid}.h7r"
            target.write_bytes(packed)
            mirrors.append(str(target))
            stripe_dir = rack_stripe_dir(rack)
            stripe_dir.mkdir(parents=True, exist_ok=True)
            stripe_copy = stripe_dir / f"{oid}.stripe"
            shutil.copy2(target, stripe_copy)
            if i >= 2:
                break
    row = {
        "object_id": oid,
        "forever_hash": header.get("forever_hash"),
        "owner_personhood_id": owner_personhood_id,
        "owner_ammodrive_id": owner_ammodrive_id,
        "original_name": original_name,
        "byte_count": header.get("byte_count"),
        "mirrors": mirrors,
        "mirror_count": len(mirrors),
        "stored": _utc(),
        "open_read": open_read,
    }
    idx = _load(VAULT_INDEX, {"schema": "field-h7r-vault-index/v1", "objects": {}})
    idx.setdefault("objects", {})[oid] = row
    idx["count"] = len(idx.get("objects") or {})
    idx["updated"] = _utc()
    _save(VAULT_INDEX, idx)
    _append_forever({"event": "store", **row})
    return {"ok": True, **row}


def load_blob(
    oid: str,
    *,
    personhood_id: str = "",
    ammodrive_id: str = "",
) -> dict[str, Any]:
    h7r = _h7r()
    paths: list[Path] = []
    idx = _load(VAULT_INDEX, {})
    meta = (idx.get("objects") or {}).get(oid) or {}
    for p in meta.get("mirrors") or []:
        paths.append(Path(p))
    if not paths:
        for rack in list_racks():
            p = rack_vault_dir(rack) / f"{oid}.h7r"
            if p.is_file():
                paths.append(p)
        central = STATE / "field-h7r-vault" / f"{oid}.h7r"
        if central.is_file():
            paths.append(central)
    last_err = ""
    for path in paths:
        try:
            header, payload = h7r.unpack(path.read_bytes())
            if not h7r.acl_can_read(header, personhood_id=personhood_id, ammodrive_id=ammodrive_id):
                return {"ok": False, "error": "acl_denied", "object_id": oid}
            return {
                "ok": True,
                "object_id": oid,
                "header": header,
                "byte_count": len(payload),
                "forever_hash": header.get("forever_hash"),
                "path": str(path),
            }
        except Exception as exc:
            last_err = str(exc)
    return {"ok": False, "error": "not_found_or_corrupt", "detail": last_err, "object_id": oid}


def tombstone(
    oid: str,
    *,
    request_hash: str,
    requester_personhood_id: str,
) -> dict[str, Any]:
    h7r = _h7r()
    loaded = load_blob(oid, personhood_id=requester_personhood_id)
    if not loaded.get("ok"):
        return loaded
    header = loaded.get("header") or {}
    if not h7r.verify_forever_delete(header, request_hash=request_hash, requester_personhood_id=requester_personhood_id):
        return {"ok": False, "error": "forever_hash_or_personhood_denied"}
    idx = _load(VAULT_INDEX, {"objects": {}})
    meta = (idx.get("objects") or {}).pop(oid, None)
    idx["count"] = len(idx.get("objects") or {})
    idx["updated"] = _utc()
    _save(VAULT_INDEX, idx)
    _append_forever({
        "event": "tombstone",
        "object_id": oid,
        "forever_hash": request_hash,
        "requester_personhood_id": requester_personhood_id,
        "meta": meta,
    })
    return {"ok": True, "tombstoned": oid, "forever_hash": request_hash, "note": "index_only_never_hard_delete_without_hash"}


def _append_forever(row: dict[str, Any]) -> None:
    try:
        FOREVER_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with FOREVER_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def panel() -> dict[str, Any]:
    racks = list_racks()
    idx = _load(VAULT_INDEX, {})
    gb_per = int((_load(DOCTRINE, {}).get("rackmount") or {}).get("gb_per_rack") or 91)
    return {
        "ok": True,
        "schema": "field-h7r-rackmount/v1",
        "updated": _utc(),
        "format": "h7r/1",
        "rack_count": len(racks),
        "physical_gb": len(racks) * gb_per,
        "object_count": idx.get("count") or len(idx.get("objects") or {}),
        "vault_index": str(VAULT_INDEX),
        "forever_ledger": str(FOREVER_LEDGER),
    }


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-h7r-rackmount.py [panel]"}, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())