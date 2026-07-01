#!/usr/bin/env python3
"""AmmoCode non-destructive guard — never harm self or outside without operator export."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
SG = Path(os.environ.get("SG_ROOT", ROOT.parent))
NEXUS = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "AmmoOS"))
_SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_SG_PATHS_LIB) not in sys.path:
    sys.path.insert(0, str(_SG_PATHS_LIB))
from sg_paths import grok16_root

GROK16 = grok16_root()
STATE = Path(os.environ.get("NEXUS_STATE_DIR", NEXUS / ".nexus-state"))

DOCTRINE_PATH = ROOT / "data" / "ammocode-nondestructive-doctrine.json"

# API may never write here (read OK for editor open).
WRITE_FORBIDDEN_PREFIXES: tuple[Path, ...] = (
    ROOT.resolve(),
    (GROK16 / "bin").resolve(),
    Path("/usr"),
    Path("/bin"),
    Path("/sbin"),
    Path("/etc"),
    Path("/boot"),
    Path("/lib"),
    Path("/lib64"),
)

# Never execute as g16_run / bash runner — protects AmmoCode + system.
RUN_FORBIDDEN_PREFIXES: tuple[Path, ...] = (
    ROOT.resolve(),
    SERVER.resolve(),
    (GROK16 / "bin").resolve(),
    Path("/usr/bin"),
    Path("/bin"),
    Path("/sbin"),
)

READ_ALLOWED_PREFIXES: tuple[Path, ...] = (
    Path.home().resolve(),
    SG.resolve(),
    NEXUS.resolve(),
    Path("/tmp").resolve(),
)

BLOCKED_API_ACTIONS = frozenset({
    "write_file",
    "save_file",
    "delete_file",
    "unlink",
    "rmtree",
    "exec_shell",
    "exec",
    "eval",
    "patch_file",
    "overwrite",
})


def load_doctrine() -> dict[str, Any]:
    if DOCTRINE_PATH.is_file():
        try:
            return json.loads(DOCTRINE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "ammocode-nondestructive/v1",
        "motto": "Read and export only — AmmoCode never destructively writes self or foreign paths",
    }


def _under(path: Path, roots: tuple[Path, ...]) -> bool:
    s = str(path.resolve())
    return any(s == str(r) or s.startswith(str(r) + os.sep) for r in roots)


def is_read_allowed(path: str | Path) -> bool:
    p = Path(path).expanduser().resolve()
    return _under(p, READ_ALLOWED_PREFIXES)


def is_write_forbidden(path: str | Path) -> bool:
    p = Path(path).expanduser().resolve()
    return _under(p, WRITE_FORBIDDEN_PREFIXES)


def is_run_forbidden(path: str | Path) -> bool:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return True
    return _under(p, RUN_FORBIDDEN_PREFIXES)


def assert_read(path: str) -> dict[str, Any] | None:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return {"ok": False, "error": "not_found", "nondestructive": True}
    if not is_read_allowed(p):
        return {"ok": False, "error": "path_forbidden", "nondestructive": True}
    return None


def assert_run(path: str) -> dict[str, Any] | None:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        return {"ok": False, "error": "not_found", "nondestructive": True}
    if not is_read_allowed(p):
        return {"ok": False, "error": "path_forbidden", "nondestructive": True}
    if is_run_forbidden(p):
        return {
            "ok": False,
            "error": "nondestructive_run_blocked",
            "detail": "AmmoCode does not execute files inside itself or system paths",
            "path": str(p),
        }
    return None


def assert_api_action(action: str) -> dict[str, Any] | None:
    a = str(action or "").lower()
    if a in BLOCKED_API_ACTIONS:
        return {
            "ok": False,
            "error": "nondestructive_action_blocked",
            "action": a,
            "detail": "AmmoCode API is read-only for disk — use browser Export to save",
        }
    return None


def settings_write_allowed(path: Path) -> bool:
    """Settings may only land in operator config dir, never in bundle."""
    p = path.expanduser().resolve()
    if is_write_forbidden(p):
        return False
    cfg = Path.home() / ".config" / "ammocode"
    state_ac = STATE / "ammocode"
    return (
        str(p).startswith(str(cfg))
        or str(p).startswith(str(state_ac))
        or str(p).startswith(str(STATE / "ammocode-settings"))
    )


def status() -> dict[str, Any]:
    doc = load_doctrine()
    return {
        "ok": True,
        "nondestructive": True,
        "schema": doc.get("schema", "ammocode-nondestructive/v1"),
        "disk_write_api": False,
        "save_model": "browser_export_only",
        "self_protected": str(ROOT),
        "run_blocked_inside_self": True,
        "blocked_actions": sorted(BLOCKED_API_ACTIONS),
    }