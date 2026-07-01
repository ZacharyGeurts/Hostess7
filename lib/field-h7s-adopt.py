#!/usr/bin/env python3
"""H7s global speedup adoption — hot JSON corpora; never kernel boot images."""
from __future__ import annotations

import fnmatch
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-h7s-global-doctrine.json"
REGISTRY = STATE / "field-h7s-speedup-registry.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_h7s() -> Any | None:
    path = INSTALL / "lib" / "field-h7s-format.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_h7s_adopt", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _path_matches_glob(rel: str, pattern: str) -> bool:
    rel = rel.replace("\\", "/").lower()
    pat = pattern.replace("\\", "/").lower()
    if "**" in pat:
        parts = [p for p in pat.split("**") if p]
        pos = 0
        for part in parts:
            part = part.strip("/")
            if not part:
                continue
            hit = rel.find(part, pos)
            if hit < 0:
                return False
            pos = hit + len(part)
        return True
    return fnmatch.fnmatch(rel, pat)


def is_kernel_boot_artifact(path: Path) -> bool:
    """True when path is a boot/kernel runtime binary — never H7s-wrap these."""
    doc = doctrine()
    exc = doc.get("exclude") or {}
    try:
        rel = str(path.resolve().relative_to(INSTALL)).replace("\\", "/")
    except (ValueError, OSError):
        rel = str(path).replace("\\", "/")
    rel_lower = rel.lower()
    name = path.name.lower()
    stem = path.stem.lower()

    for pat in exc.get("path_globs") or []:
        if _path_matches_glob(rel, str(pat)):
            return True
    for ext in exc.get("extensions") or []:
        if name.endswith(str(ext).lower()):
            return True
    for base in exc.get("basenames") or []:
        b = str(base).lower()
        if name == b or stem == b or name.startswith(b):
            return True
    if "/boot/" in rel_lower or rel_lower.startswith("boot/"):
        return True
    return False


def legacy_sidecar_path(src: Path) -> Path:
    """Deprecated twin file — migrate away; never create new sidecars."""
    return src.with_suffix(src.suffix + ".h7s")


def speedup_dest(src: Path) -> Path:
    """In-place disguise — same path, same original extension."""
    return src


def is_h7s_at_path(path: Path) -> bool:
    h7s = _import_h7s()
    if not h7s or not path.is_file():
        return False
    try:
        return bool(h7s.is_h7s_blob(path.read_bytes()))
    except OSError:
        return False


def migrate_legacy_sidecar(path: Path, *, apply: bool = True) -> dict[str, Any]:
    """Fold legacy *.json.h7s twin into canonical path — share original extension."""
    leg = legacy_sidecar_path(path)
    if not leg.is_file():
        return {"ok": True, "migrated": False, "path": str(path)}
    h7s = _import_h7s()
    if not h7s:
        return {"ok": False, "error": "h7s_module_missing", "path": str(path)}
    try:
        blob = leg.read_bytes()
        if not h7s.is_h7s_blob(blob):
            return {"ok": False, "reason": "legacy_not_h7s", "legacy": str(leg)}
        if path.is_file() and not is_h7s_at_path(path):
            props = h7s.read_properties(blob)
            if props.get("lossless_restore", True):
                restored = h7s.restore_bytes(blob)
                if restored != path.read_bytes():
                    return {"ok": False, "reason": "legacy_restore_mismatch", "path": str(path)}
        if not apply:
            return {"ok": True, "dry_run": True, "migrated": True, "path": str(path), "legacy": str(leg)}
        tmp = path.with_suffix(path.suffix + ".migrate.tmp")
        tmp.write_bytes(blob)
        tmp.replace(path)
        leg.unlink()
        return {"ok": True, "migrated": True, "path": str(path), "legacy": str(leg), "in_place": True}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "path": str(path), "legacy": str(leg)}


def can_adopt_speedup(path: Path) -> dict[str, Any]:
    if is_kernel_boot_artifact(path):
        return {
            "ok": False,
            "reason": "kernel_boot_excluded",
            "path": str(path),
            "statement": "KILROY kernel boot images stay native — H7s is hot-read lane only.",
        }
    try:
        if not path.is_file():
            return {"ok": False, "reason": "missing", "path": str(path)}
    except OSError as exc:
        if is_kernel_boot_artifact(path):
            return {
                "ok": False,
                "reason": "kernel_boot_excluded",
                "path": str(path),
                "detail": str(exc)[:80],
            }
        return {"ok": False, "reason": "access_error", "path": str(path), "detail": str(exc)[:80]}
    h7s = _import_h7s()
    if not h7s:
        return {"ok": False, "reason": "h7s_module_missing", "path": str(path)}
    try:
        blob = path.read_bytes()
        if h7s.is_h7s_blob(blob):
            return {"ok": False, "reason": "already_h7s", "path": str(path)}
    except OSError as exc:
        return {"ok": False, "reason": "read_error", "detail": str(exc), "path": str(path)}
    dest = speedup_dest(path)
    return {"ok": True, "path": str(path), "dest": str(dest), "in_place": True, "sidecars": False}


def adopt_speedup(path: Path, *, apply: bool = False) -> dict[str, Any]:
    migrate_legacy_sidecar(path, apply=apply)
    if is_h7s_at_path(path):
        return {"ok": True, "applied": False, "reason": "already_h7s", "path": str(path), "in_place": True}
    gate = can_adopt_speedup(path)
    if not gate.get("ok"):
        return {**gate, "applied": False}
    h7s = _import_h7s()
    dest = speedup_dest(path)
    if not apply:
        return {
            "ok": True,
            "dry_run": True,
            "path": str(path),
            "dest": str(dest),
            "in_place": True,
            "sidecars": False,
            "bytes": path.stat().st_size,
        }
    try:
        out = h7s.pack_any_file(path, dest)
        reg = _load(REGISTRY, {"schema": "field-h7s-speedup-registry/v1", "entries": {}})
        reg.setdefault("entries", {})
        reg["entries"][str(path)] = {
            "dest": str(dest),
            "in_place": True,
            "sidecars": False,
            "face_extension": path.suffix,
            "packed_at": _now(),
            "packed_bytes": out.get("packed_bytes") or dest.stat().st_size,
            "properties": out.get("properties") or {},
        }
        reg["updated"] = _now()
        _save(REGISTRY, reg)
        return {
            "ok": True,
            "applied": True,
            "path": str(path),
            "dest": str(dest),
            "in_place": True,
            "sidecars": False,
            **out,
        }
    except Exception as exc:
        return {"ok": False, "applied": False, "path": str(path), "error": str(exc)}


def hot_corpus_paths() -> list[Path]:
    doc = doctrine()
    out: list[Path] = []
    for rel in (doc.get("include") or {}).get("hot_json_corpora") or []:
        p = INSTALL / str(rel) if not str(rel).startswith("/") else Path(str(rel))
        if p.is_file():
            out.append(p)
    return out


def audit() -> dict[str, Any]:
    corpora = hot_corpus_paths()
    rows: list[dict[str, Any]] = []
    for src in corpora:
        gate = can_adopt_speedup(src)
        h7s_active = is_h7s_at_path(src)
        leg = legacy_sidecar_path(src)
        rows.append({
            "path": str(src.relative_to(INSTALL)),
            "bytes": src.stat().st_size,
            "h7s_in_place": h7s_active,
            "h7s_bytes": src.stat().st_size if h7s_active else 0,
            "legacy_sidecar": str(leg.relative_to(INSTALL)) if leg.is_file() else None,
            "can_adopt": gate.get("ok"),
            "reason": gate.get("reason"),
            "kernel_excluded": gate.get("reason") == "kernel_boot_excluded",
            "sidecars": False,
        })
    boot_samples = [
        INSTALL / "KILROY" / "build" / "vmlinuz",
        Path("/boot/vmlinuz"),
    ]
    boot_checks = [
        {"path": str(p), "excluded": is_kernel_boot_artifact(p)}
        for p in boot_samples
    ]
    return {
        "schema": "field-h7s-global-audit/v1",
        "ok": True,
        "kilroy": (doctrine().get("kilroy") or {}),
        "corpus_count": len(corpora),
        "rows": rows,
        "boot_guard": boot_checks,
        "registry": str(REGISTRY),
        "updated": _now(),
    }


def adopt_all(*, apply: bool = False) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for src in hot_corpus_paths():
        results.append(adopt_speedup(src, apply=apply))
    ok = all(r.get("ok") or r.get("reason") in ("already_h7s",) for r in results)
    return {
        "schema": "field-h7s-global-adopt/v1",
        "ok": ok,
        "apply": apply,
        "count": len(results),
        "results": results,
        "updated": _now(),
    }


def resolve_read_path(path: Path) -> Path:
    """Canonical path — format layer handles H7s in-place at original extension."""
    migrate_legacy_sidecar(path, apply=True)
    return path


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "audit").lower()
    apply = "--apply" in args

    if cmd == "audit":
        print(json.dumps(audit(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "adopt":
        print(json.dumps(adopt_all(apply=apply), ensure_ascii=False, indent=2))
        return 0
    if cmd == "guard" and len(args) >= 2:
        p = Path(args[1])
        print(json.dumps({
            "path": str(p),
            "kernel_boot_excluded": is_kernel_boot_artifact(p),
            "can_adopt": can_adopt_speedup(p),
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve" and len(args) >= 2:
        p = Path(args[1])
        r = resolve_read_path(p)
        print(json.dumps({
            "src": str(p),
            "read_path": str(r),
            "h7s_in_place": is_h7s_at_path(r),
            "sidecars": False,
        }, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["audit", "adopt [--apply]", "guard <path>", "resolve <path>"],
        "doctrine": str(DOCTRINE),
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())