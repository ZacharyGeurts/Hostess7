#!/usr/bin/env python3
"""One field per box — whole system per rack; never colocate fields on same host."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-rack-uniqueness-doctrine.json"
LEASE = STATE / "field-rack-lease.json"
REGISTRY = STATE / "field-rack-registry.json"
PANEL = STATE / "field-rack-uniqueness-panel.json"
TEAM = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM1/fieldstorage"))
QUBES = Path(os.environ.get("FIELD_QUBES_MOUNT", "/media/default/FIELD_QUBES"))


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


def _machine_id() -> str:
    for p in (Path("/etc/machine-id"), Path("/var/lib/dbus/machine-id")):
        try:
            mid = p.read_text(encoding="utf-8").strip()
            if mid:
                return mid
        except OSError:
            pass
    return ""


def box_fingerprint() -> dict[str, Any]:
    rack_id = os.environ.get("FIELD_RACK_ID", "").strip()
    slot = os.environ.get("WORLD_PIPELINE_SLOT", "").strip()
    host = socket.gethostname()
    mid = _machine_id()
    parts = [p for p in (rack_id, slot, host, mid) if p]
    raw = "|".join(parts) or host or "unknown-box"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return {
        "raw": raw,
        "digest": digest,
        "hostname": host,
        "machine_id": mid[:12] if mid else None,
        "field_rack_id": rack_id or None,
        "qemu_slot": slot or None,
    }


def field_id_for_box(*, fp: dict[str, Any] | None = None) -> str:
    doc = _load(DOCTRINE, {})
    fp = fp or box_fingerprint()
    explicit = fp.get("field_rack_id")
    if explicit:
        return str(explicit).replace(" ", "-").lower()
    slot = fp.get("qemu_slot")
    prefix = str((doc.get("qemu_box") or {}).get("field_id_prefix") or "rack-")
    if slot:
        return f"{prefix}{slot}"
    return f"rack-{fp.get('digest', 'unknown')[:16]}"


def rack_storage_roots() -> list[Path]:
    doc = _load(DOCTRINE, {})
    sub = str((doc.get("rack_layout") or {}).get("subdir") or "racks")
    roots: list[Path] = []
    for base in (QUBES, TEAM, INSTALL / ".nexus-field-drive"):
        if not base:
            continue
        if base.name == "nexus-field-drive":
            roots.append(base)
        elif "fieldstorage" in str(base) or base.name == "FIELD_QUBES":
            roots.append(base / sub)
        else:
            roots.append(base / "fieldstorage" / sub if (base / "fieldstorage").is_dir() else base / sub)
    seen: set[str] = set()
    out: list[Path] = []
    for r in roots:
        k = str(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def rack_root(field_id: str) -> Path:
    for base in rack_storage_roots():
        candidate = base / field_id / "nexus-field"
        if base.name == "nexus-field-drive":
            candidate = base / "nexus-field"
        return candidate
    return INSTALL / ".nexus-field-drive" / "nexus-field"


def assert_solo_field(*, field_id: str | None = None, write: bool = True) -> dict[str, Any]:
    """Ensure this box hosts at most one field — block colocation."""
    doc = _load(DOCTRINE, {})
    fp = box_fingerprint()
    fid = field_id or field_id_for_box(fp=fp)
    lease = _load(LEASE, {})
    reg = _load(REGISTRY, {"racks": []})
    racks: list[dict[str, Any]] = list(reg.get("racks") or [])

    collision: dict[str, Any] | None = None
    for row in racks:
        if row.get("box_digest") == fp.get("digest") and row.get("field_id") != fid:
            collision = row
            break
        if row.get("field_id") == fid and row.get("box_digest") != fp.get("digest"):
            collision = row

    if lease.get("box_digest") and lease.get("box_digest") != fp.get("digest"):
        collision = lease

    if collision:
        return {
            "ok": False,
            "schema": "field-rack-uniqueness/v1",
            "error": "field_colocation_forbidden",
            "motto": doc.get("motto"),
            "field_id": fid,
            "box": fp,
            "collision": collision,
            "rule": "one_field_per_box",
        }

    new_lease = {
        "schema": "field-rack-lease/v1",
        "updated": _utc(),
        "field_id": fid,
        "box": fp,
        "whole_system": True,
        "zachub": (doc.get("zachub") or {}),
    }
    row = {
        "field_id": fid,
        "box_digest": fp.get("digest"),
        "hostname": fp.get("hostname"),
        "qemu_slot": fp.get("qemu_slot"),
        "rack_root": str(rack_root(fid)),
        "updated": _utc(),
        "whole_system": True,
    }
    found = False
    for i, r in enumerate(racks):
        if r.get("field_id") == fid or r.get("box_digest") == fp.get("digest"):
            racks[i] = row
            found = True
            break
    if not found:
        racks.append(row)

    if write:
        _save(LEASE, new_lease)
        _save(REGISTRY, {"schema": "field-rack-registry/v1", "updated": _utc(), "racks": racks})
    return {
        "ok": True,
        "schema": "field-rack-uniqueness/v1",
        "field_id": fid,
        "box": fp,
        "lease": new_lease,
        "rack_count": len(racks),
        "rack_root": str(rack_root(fid)),
        "rules": doc.get("rules"),
    }


def publish_whole_field(*, field_id: str | None = None, full: bool = True) -> dict[str, Any]:
    """Publish whole nexus-field system to this rack — solo box only."""
    solo = assert_solo_field(field_id=field_id, write=True)
    if not solo.get("ok"):
        return solo
    fid = str(solo.get("field_id"))
    doc = _load(DOCTRINE, {})
    layout = doc.get("rack_layout") or {}
    dirs = list(layout.get("whole_system_dirs") or ["lib", "panel", "data", "config", "assets"])

    roots = rack_storage_roots()
    primary_base = roots[0] if roots else INSTALL / ".nexus-field-drive"
    if primary_base.name == "nexus-field-drive":
        dst_root = primary_base / "nexus-field"
    else:
        dst_root = primary_base / fid / "nexus-field"
    dst_root.mkdir(parents=True, exist_ok=True)
    sys_dst = dst_root / "system"
    st_dst = dst_root / "state"
    sys_dst.mkdir(parents=True, exist_ok=True)
    st_dst.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    for name in dirs:
        if name in ("state", "world-publish"):
            continue
        src = INSTALL / name
        if not src.is_dir() and name != "lib":
            continue
        if name == "lib" and not src.is_dir():
            continue
        target = sys_dst / name if name != "assets" else sys_dst / name
        if name in ("panel", "assets"):
            target = sys_dst / name
        else:
            target = sys_dst / name
        if full and target.exists():
            shutil.rmtree(target, ignore_errors=True)
        if src.is_dir():
            shutil.copytree(src, target, dirs_exist_ok=True)
            copied.append(name)

    for extra in ("nexus.sh", "genius_shield.sh", "MANIFEST.sha256"):
        src = INSTALL / extra
        if src.is_file():
            shutil.copy2(src, sys_dst / extra)
            copied.append(extra)

    gh_dst = dst_root / str(layout.get("github_truth_subdir") or "zachub-github-truth")
    world_src = INSTALL / ".nexus-field-drive" / "nexus-field" / "world-publish"
    if not world_src.is_dir():
        world_src = INSTALL / "Hostess7" / "docs"
    if world_src.is_dir():
        if full and gh_dst.exists():
            shutil.rmtree(gh_dst, ignore_errors=True)
        shutil.copytree(world_src, gh_dst, dirs_exist_ok=True)
        copied.append("zachub-github-truth")

    manifest = {
        "schema": "field-rack-whole-system/v1",
        "updated": _utc(),
        "field_id": fid,
        "box": solo.get("box"),
        "whole_system": True,
        "one_field_per_box": True,
        "zachub_github_truth": str(gh_dst),
        "rack_root": str(dst_root),
        "copied": copied,
        "product": "ZachHub",
    }
    _save(dst_root / "manifest.json", manifest)

    out = {**solo, "publish": manifest, "copied": copied}
    _save(PANEL, out)
    api = INSTALL / "Hostess7" / "docs" / "api" / "field-rack-uniqueness.json"
    api.parent.mkdir(parents=True, exist_ok=True)
    api.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("ok") is not None:
        return cached
    return assert_solo_field(write=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("assert", "solo", "lease"):
        print(json.dumps(assert_solo_field(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("publish", "whole", "provision"):
        print(json.dumps(publish_whole_field(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-rack-uniqueness.py [json|assert|publish]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())