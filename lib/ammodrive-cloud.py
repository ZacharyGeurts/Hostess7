#!/usr/bin/env python3
"""AmmoDrive Cloud — the new cloud. H7r rackmount, personhood + AmmoDrive ids, open to everyone."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "ammodrive-cloud-doctrine.json"
PANEL = STATE / "ammodrive-cloud-panel.json"
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


def _machine_id() -> str:
    for p in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        try:
            mid = p.read_text(encoding="utf-8").strip()
            if mid:
                return mid
        except OSError:
            pass
    return ""


def personhood_id(*, device_id: str = "", display_name: str = "") -> str:
    host = socket.gethostname()
    mid = _machine_id()
    reg = _load(REGISTRY, {})
    dev_id = device_id
    if not dev_id:
        for d in reg.get("devices") or []:
            if d.get("kind") == "workstation" or d.get("self"):
                dev_id = str(d.get("id") or "")
                display_name = display_name or str(d.get("display_name") or "")
                break
    raw = f"personhood|{dev_id}|{mid}|{host}|{display_name}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def ammodrive_id() -> str:
    rack_mod = _mod("lib/field-rack-uniqueness.py", "rack_unique")
    if rack_mod and hasattr(rack_mod, "field_id_for_box"):
        fid = rack_mod.field_id_for_box()
        return f"ammodrive-{fid}"
    host = socket.gethostname()
    digest = hashlib.sha256(host.encode()).hexdigest()[:16]
    return f"ammodrive-{digest}"


def identity() -> dict[str, Any]:
    ph = personhood_id()
    ad = ammodrive_id()
    return {
        "ok": True,
        "schema": "ammodrive-identity/v1",
        "updated": _utc(),
        "personhood_id": ph,
        "ammodrive_id": ad,
        "hostname": socket.gethostname(),
        "open_to_everyone": True,
        "note": "Personhood = embodied device; AmmoDrive id = cloud locker key for grants",
    }


def cloud_put(
    payload: bytes,
    *,
    name: str = "blob",
    open_read: bool = False,
    owner_personhood_id: str | None = None,
    owner_ammodrive_id: str | None = None,
) -> dict[str, Any]:
    mount = _mod("lib/field-h7r-rackmount.py", "h7r_mount")
    if not mount:
        return {"ok": False, "error": "h7r_rackmount_missing"}
    ph = owner_personhood_id or personhood_id()
    ad = owner_ammodrive_id or ammodrive_id()
    return mount.store_blob(
        payload,
        owner_personhood_id=ph,
        owner_ammodrive_id=ad,
        original_name=name,
        open_read=open_read,
    )


def cloud_get(
    object_id: str,
    *,
    personhood_id_arg: str = "",
    ammodrive_id_arg: str = "",
) -> dict[str, Any]:
    mount = _mod("lib/field-h7r-rackmount.py", "h7r_mount")
    if not mount:
        return {"ok": False, "error": "h7r_rackmount_missing"}
    ph = personhood_id_arg or personhood_id()
    ad = ammodrive_id_arg or ammodrive_id()
    return mount.load_blob(object_id, personhood_id=ph, ammodrive_id=ad)


def cloud_unlock(
    object_id: str,
    *,
    grantee_ammodrive_id: str,
    read: bool = True,
    write: bool = False,
    owner_ammodrive_id: str | None = None,
) -> dict[str, Any]:
    h7r = _mod("lib/field-h7r-format.py", "h7r_fmt")
    mount = _mod("lib/field-h7r-rackmount.py", "h7r_mount")
    if not h7r or not mount:
        return {"ok": False, "error": "h7r_missing"}
    owner = owner_ammodrive_id or ammodrive_id()
    loaded = mount.load_blob(object_id, ammodrive_id=owner)
    if not loaded.get("ok"):
        return loaded
    header = dict(loaded.get("header") or {})
    try:
        header = h7r.grant_acl(
            header,
            owner_ammodrive_id=owner,
            grantee_ammodrive_id=grantee_ammodrive_id,
            read=read,
            write=write,
        )
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    idx_path = STATE / "field-h7r-vault-index.json"
    idx = _load(idx_path, {"objects": {}})
    row = (idx.get("objects") or {}).get(object_id) or {}
    row["acl"] = header.get("acl")
    row["unlocked_for"] = grantee_ammodrive_id
    row["updated"] = _utc()
    idx.setdefault("objects", {})[object_id] = row
    _save(idx_path, idx)
    return {"ok": True, "object_id": object_id, "grantee": grantee_ammodrive_id, "read": read, "write": write}


def cloud_lock(object_id: str, *, owner_ammodrive_id: str | None = None) -> dict[str, Any]:
    owner = owner_ammodrive_id or ammodrive_id()
    idx_path = STATE / "field-h7r-vault-index.json"
    idx = _load(idx_path, {"objects": {}})
    row = (idx.get("objects") or {}).get(object_id)
    if not row:
        return {"ok": False, "error": "not_found"}
    if str(row.get("owner_ammodrive_id") or "") != owner:
        return {"ok": False, "error": "not_owner"}
    row["locked"] = True
    row["readers"] = []
    row["writers"] = []
    row["open_read"] = False
    row["updated"] = _utc()
    idx["objects"][object_id] = row
    _save(idx_path, idx)
    return {"ok": True, "object_id": object_id, "locked": True}


def build_panel() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    storage = doctrine.get("storage") or {}
    rack_mod = _mod("lib/field-h7r-rackmount.py", "h7r_mount")
    rack_panel = rack_mod.panel() if rack_mod and hasattr(rack_mod, "panel") else {}
    ident = identity()
    global_panel = _load(STATE / "field-global-servers-panel.json", {})
    global_count = int(global_panel.get("deployed_servers") or 0)
    rack_count = int(global_panel.get("deployed_servers") or rack_panel.get("rack_count") or storage.get("rack_count_live") or 0)
    gb_per = int(storage.get("gb_per_rack") or 91)
    physical = rack_count * gb_per
    h7s_mult = float(storage.get("h7s_logical_multiplier") or 23.2)
    return {
        "ok": True,
        "schema": "ammodrive-cloud/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "tagline": doctrine.get("tagline"),
        "cloud": doctrine.get("cloud"),
        "product": doctrine.get("product") or "AmmoDrive",
        "the_new_cloud": True,
        "protocol": "h7r/1",
        "hot_lane": "h7s/1",
        "identity": {
            "personhood_id": ident.get("personhood_id"),
            "ammodrive_id": ident.get("ammodrive_id"),
            "open_to_everyone": True,
        },
        "capacity": {
            "global_servers": global_count or rack_count,
            "rack_count": rack_count,
            "physical_gb": physical,
            "h7s_logical_tb": round(physical * h7s_mult / 1024, 2),
            "erasure_shards": "4+2",
            "never_lose_mirrors": int(storage.get("never_lose_mirrors") or 6),
        },
        "security": doctrine.get("security"),
        "vault": rack_panel,
        "api": doctrine.get("api", "/api/ammodrive-cloud"),
        "pages": "https://zacharygeurts.github.io/Hostess7/",
        "loopback": "http://127.0.0.1:9477",
    }


def rapid_storage_distribute(*, workers: int = 48, dry_run: bool = False) -> dict[str, Any]:
    rapid = _mod("lib/ammodrive-storage-rapid.py", "storage_rapid")
    if not rapid:
        return {"ok": False, "error": "ammodrive_storage_rapid_missing"}
    return rapid.rapid_distribute(workers=workers, dry_run=dry_run)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status", "cloud"):
        doc = build_panel()
        _save(PANEL, doc)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd == "identity":
        print(json.dumps(identity(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "put":
        name = "blob"
        open_read = "--open" in sys.argv
        for arg in sys.argv[2:]:
            if arg.startswith("--name="):
                name = arg.split("=", 1)[1]
            elif not arg.startswith("--") and Path(arg).is_file():
                data = Path(arg).read_bytes()
                print(json.dumps(cloud_put(data, name=name, open_read=open_read), ensure_ascii=False, indent=2))
                return 0
        return 1
    if cmd == "get" and len(sys.argv) > 2:
        print(json.dumps(cloud_get(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "unlock" and len(sys.argv) > 3:
        print(json.dumps(cloud_unlock(sys.argv[2], grantee_ammodrive_id=sys.argv[3]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "lock" and len(sys.argv) > 2:
        print(json.dumps(cloud_lock(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("rapid", "rapid-distribute", "upgrade-storage", "h7r-rapid"):
        print(json.dumps(rapid_storage_distribute(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "ammodrive-cloud.py [json|identity|put|get|unlock|lock|rapid-distribute]",
        "api": "/api/ammodrive-cloud",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())