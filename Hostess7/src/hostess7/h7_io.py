"""H7/H7s-aware reads — build + publish paths decode disguised JSON natively."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

H7S_MAGIC = b"H7S\x01"


def _install_root() -> Path:
    env = os.environ.get("NEXUS_INSTALL_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2].parent


def _load_mod(name: str, rel: str) -> Any | None:
    path = _install_root() / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_bytes(path: Path) -> bytes:
    fs = _load_mod("field_h7s_fs", "field-h7s-fs.py")
    if fs and hasattr(fs, "read_bytes"):
        try:
            return fs.read_bytes(path)
        except Exception:
            pass
    blob = path.read_bytes()
    h7s = _load_mod("field_h7s_fmt", "field-h7s-format.py")
    if h7s and hasattr(h7s, "is_h7s_blob") and h7s.is_h7s_blob(blob) and hasattr(h7s, "restore_bytes"):
        try:
            return h7s.restore_bytes(blob)
        except Exception:
            pass
    return blob


def read_text(path: Path, *, encoding: str = "utf-8", errors: str = "strict") -> str:
    return read_bytes(path).decode(encoding, errors=errors)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(read_bytes(path).decode("utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def is_h7_container(path: Path) -> bool:
    try:
        blob = path.read_bytes()[:4]
    except OSError:
        return False
    return blob == H7S_MAGIC or blob == b"H7\x07\x01"