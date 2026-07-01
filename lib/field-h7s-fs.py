#!/usr/bin/env python3
"""H7s filesystem lane — in-place format disguise; no sidecars; KILROY boot excluded."""
from __future__ import annotations

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
REGISTRY = STATE / "field-h7s-fs-registry.json"
ENABLED = os.environ.get("NEXUS_H7S_FS", "1") == "1"


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


def _import_mod(rel: str, name: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _adopt_mod() -> Any | None:
    return _import_mod("field-h7s-adopt.py", "field_h7s_fs_adopt")


def _h7s_mod() -> Any | None:
    return _import_mod("field-h7s-format.py", "field_h7s_fs_fmt")


def _lane_mod() -> Any | None:
    return _import_mod("field-h7s-lane.py", "field_h7s_fs_lane")


def is_h7s_file(path: Path) -> bool:
    adopt = _adopt_mod()
    if adopt and hasattr(adopt, "is_h7s_at_path"):
        return bool(adopt.is_h7s_at_path(path))
    h7s = _h7s_mod()
    if not h7s or not path.is_file():
        return False
    try:
        return bool(h7s.is_h7s_blob(path.read_bytes()))
    except OSError:
        return False


def can_adopt(path: Path) -> dict[str, Any]:
    if not ENABLED:
        return {"ok": False, "reason": "h7s_fs_disabled", "path": str(path)}
    adopt = _adopt_mod()
    if not adopt:
        return {"ok": False, "reason": "adopt_module_missing", "path": str(path)}
    return adopt.can_adopt_speedup(path)


def canonical_read_path(path: Path) -> Path:
    """Single canonical path — readers handle H7s vs native at original extension."""
    if not ENABLED:
        return path
    adopt = _adopt_mod()
    if adopt and hasattr(adopt, "resolve_read_path"):
        return adopt.resolve_read_path(path)
    return path


def read_bytes(path: Path) -> bytes:
    read_path = canonical_read_path(path)
    blob = read_path.read_bytes()
    h7s = _h7s_mod()
    if h7s and h7s.is_h7s_blob(blob):
        try:
            props = h7s.read_properties(blob)
            if props.get("lossless_restore", True):
                return h7s.restore_bytes(blob)
        except Exception:
            pass
    return blob


def read_json(path: Path, default: Any = None) -> Any:
    lane = _lane_mod()
    if lane and hasattr(lane, "load_json"):
        return lane.load_json(path, default=default)
    try:
        return json.loads(read_bytes(path).decode("utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def vfs_resolve(path: Path) -> dict[str, Any]:
    """Always Files / VFS — in-place H7s at original extension; no sidecars."""
    p = path.resolve() if path.is_absolute() else path
    read_path = canonical_read_path(p)
    h7s_active = is_h7s_file(read_path)
    adopt = _adopt_mod()
    legacy = adopt.legacy_sidecar_path(p) if adopt and hasattr(adopt, "legacy_sidecar_path") else None
    gate = can_adopt(p) if p.is_file() else {"ok": False, "reason": "not_file"}
    return {
        "schema": "field-h7s-fs-resolve/v1",
        "path": str(p),
        "read_path": str(read_path),
        "h7s_active": h7s_active,
        "h7s_in_place": h7s_active,
        "sidecars": False,
        "face_extension": p.suffix,
        "legacy_sidecar": str(legacy) if legacy and legacy.is_file() else None,
        "format": "h7s/1" if h7s_active else "native",
        "can_adopt": gate.get("ok"),
        "kernel_boot_excluded": gate.get("reason") == "kernel_boot_excluded",
    }


def adopt_path(path: Path, *, apply: bool = False, replace_native: bool = False) -> dict[str, Any]:
    adopt = _adopt_mod()
    if not adopt:
        return {"ok": False, "reason": "adopt_module_missing"}
    if adopt and hasattr(adopt, "is_h7s_at_path") and adopt.is_h7s_at_path(path):
        return {"ok": True, "reason": "already_h7s", "path": str(path), "in_place": True, "sidecars": False}
    gate = adopt.can_adopt_speedup(path)
    if not gate.get("ok"):
        return gate
    if not apply:
        return {
            "ok": True,
            "dry_run": True,
            "path": str(path),
            "dest": str(path),
            "in_place": True,
            "sidecars": False,
        }
    out = adopt.adopt_speedup(path, apply=True)
    reg = _load(REGISTRY, {"schema": "field-h7s-fs-registry/v1", "entries": {}})
    reg.setdefault("entries", {})[str(path)] = {
        "dest": str(path),
        "in_place": True,
        "sidecars": False,
        "at": _now(),
        **out,
    }
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    return out


def adopt_state_tree(*, apply: bool = False) -> dict[str, Any]:
    """Adopt eligible .nexus-state JSON corpora in-place — same extension, no sidecars."""
    adopt = _adopt_mod()
    results: list[dict[str, Any]] = []
    if adopt and hasattr(adopt, "hot_corpus_paths"):
        for src in adopt.hot_corpus_paths():
            results.append(adopt_path(src, apply=apply))
    return {"ok": True, "apply": apply, "sidecars": False, "count": len(results), "results": results, "updated": _now()}


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "status").lower()
    apply = "--apply" in args

    if cmd == "resolve" and len(args) >= 2:
        print(json.dumps(vfs_resolve(Path(args[1])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "adopt" and len(args) >= 2:
        print(json.dumps(adopt_path(Path(args[1]), apply=apply), ensure_ascii=False, indent=2))
        return 0
    if cmd == "adopt-state":
        print(json.dumps(adopt_state_tree(apply=apply), ensure_ascii=False, indent=2))
        return 0
    if cmd == "read" and len(args) >= 2:
        p = Path(args[1])
        if p.suffix.lower() == ".json":
            doc = read_json(p)
            print(json.dumps({"ok": True, "keys": list(doc.keys())[:20] if isinstance(doc, dict) else None}, indent=2))
        else:
            data = read_bytes(p)
            print(json.dumps({"ok": True, "bytes": len(data)}, indent=2))
        return 0
    print(json.dumps({
        "schema": "field-h7s-fs/v1",
        "enabled": ENABLED,
        "sidecars": False,
        "in_place": True,
        "registry": str(REGISTRY),
        "cmds": ["resolve <path>", "read <path>", "adopt <path> [--apply]", "adopt-state [--apply]"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())