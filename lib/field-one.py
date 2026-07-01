#!/usr/bin/env pythong
"""Field 1 — everything on one field. Storage, sync, compaction, restore.

Single canonical surface for Hostess7, Queen, and NEXUS panel.
No Hostess7-local ZAC shards — World_Redata WRDT1/WRZC1 owns compaction.

  pythong lib/field-one.py json
  pythong lib/field-one.py sync
  pythong lib/field-one.py compact
  pythong lib/field-one.py restore [--apply] [--confirm]
  pythong lib/field-one.py convert [--apply] [--confirm]
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "field-one-doctrine.json"
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))


def _import_py(name: str, path: Path) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sg_paths() -> Any | None:
    return _import_py("sg_paths", INSTALL / "lib" / "sg_paths.py")


def _converter() -> Any | None:
    return _import_py("field_drive_converter", INSTALL / "lib" / "field-drive-converter.py")


def _unified_device() -> Any | None:
    return _import_py("field_unified_device", INSTALL / "lib" / "field-unified-device.py")


def _hostess7_root() -> Path:
    sp = _sg_paths()
    if sp and hasattr(sp, "hostess7_root"):
        return sp.hostess7_root()
    env = os.environ.get("HOSTESS7_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    nested = INSTALL / "Hostess7"
    if nested.is_dir():
        return nested.resolve()
    legacy = SG / "Hostess7"
    return legacy.resolve() if legacy.is_dir() else nested.resolve()


def storage_root() -> Path:
    sp = _sg_paths()
    if sp and hasattr(sp, "hostess7_team_field"):
        return sp.hostess7_team_field()
    return _hostess7_root() / "cache" / "fieldstorage"


def _team_drive_script() -> Path:
    return _hostess7_root() / "scripts" / "field_team_drive.py"


def _run_team(cmd: str, *extra: str, timeout: int = 3600) -> dict[str, Any]:
    script = _team_drive_script()
    if not script.is_file():
        return {"ok": False, "error": "team_drive_missing", "path": str(script)}
    env = {**os.environ, "HOSTESS7_ROOT": str(_hostess7_root())}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), cmd, *extra],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(_hostess7_root()),
        )
        tail = ((proc.stdout or "") + (proc.stderr or ""))[-4000:]
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "tail": tail}
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _converter_call(fn_name: str, **kwargs: Any) -> dict[str, Any]:
    conv = _converter()
    if not conv:
        return {"ok": False, "error": "field_drive_converter_missing"}
    fn = getattr(conv, fn_name, None)
    if not callable(fn):
        return {"ok": False, "error": f"converter_missing_{fn_name}"}
    try:
        out = fn(**kwargs)
        return out if isinstance(out, dict) else {"ok": True, "result": out}
    except (OSError, ValueError, TypeError) as exc:
        return {"ok": False, "error": str(exc)}


def sync(*, storage_only: bool = False) -> dict[str, Any]:
    args = ("--storage-only",) if storage_only else ()
    rep = _run_team("sync", *args)
    return {"action": "sync", "storage_root": str(storage_root()), **rep}


def compact() -> dict[str, Any]:
    rep = _converter_call("scan")
    return {"action": "compact", "alias": "scan", **rep}


def scan() -> dict[str, Any]:
    rep = _converter_call("scan")
    return {"action": "scan", **rep}


def restore(*, apply: bool = False, confirm: bool = False) -> dict[str, Any]:
    rep = _converter_call("restore_out", apply=apply, confirm=confirm)
    return {"action": "restore", "apply": apply, **rep}


def convert(*, apply: bool = False, confirm: bool = False) -> dict[str, Any]:
    rep = _converter_call("convert", apply=apply, confirm=confirm)
    return {"action": "convert", "apply": apply, **rep}


def defield() -> dict[str, Any]:
    rep = _converter_call("defield_audit")
    return {"action": "defield", **rep}


def refield() -> dict[str, Any]:
    rep = _converter_call("refield")
    return {"action": "refield", **rep}


def install_phase(*, apply: bool = False, confirm: bool = False) -> dict[str, Any]:
    rep = _converter_call("install_phase", apply=apply, confirm=confirm)
    return {"action": "install-phase", "apply": apply, **rep}


def team_status() -> dict[str, Any]:
    rep = _run_team("status", timeout=120)
    return {"action": "team-status", **rep}


def posture() -> dict[str, Any]:
    sp = _sg_paths()
    conv = _converter()
    board: dict[str, Any] = {}
    udev = _unified_device()
    if udev and hasattr(udev, "board"):
        try:
            board = udev.board()
        except (OSError, TypeError):
            board = {}
    converter_posture = conv.posture() if conv and hasattr(conv, "posture") else {}
    team = _run_team("status", timeout=60) if _team_drive_script().is_file() else {"skipped": True}
    doc = _load_json(DOCTRINE, {})
    return {
        "schema": "field-one/v1",
        "title": "Field 1",
        "motto": doc.get("motto", "Everything on one field"),
        "field_one": True,
        "one_field_whole_device": True,
        "storage_root": str(storage_root()),
        "hostess7_root": str(_hostess7_root()),
        "team_field": str(sp.hostess7_team_field()) if sp else str(storage_root()),
        "world_redata": str(sp.world_redata_root()) if sp else None,
        "converter": converter_posture,
        "team": team,
        "board": board,
        "commands": doc.get("commands", {}),
    }


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    apply = "--apply" in args
    confirm = "--confirm" in args
    storage_only = "--storage-only" in args
    args = [a for a in args if a not in ("--apply", "--confirm", "--storage-only")]

    mode = (args[0] if args else "json").strip().lower()
    handlers: dict[str, Callable[[], dict[str, Any]]] = {
        "json": posture,
        "status": posture,
        "posture": posture,
        "sync": lambda: sync(storage_only=storage_only),
        "compact": compact,
        "scan": scan,
        "restore": lambda: restore(apply=apply, confirm=confirm),
        "restore-out": lambda: restore(apply=apply, confirm=confirm),
        "convert": lambda: convert(apply=apply, confirm=confirm),
        "defield": defield,
        "defield-audit": defield,
        "refield": refield,
        "install-phase": lambda: install_phase(apply=apply, confirm=confirm),
        "team-status": team_status,
        "team": team_status,
    }
    fn = handlers.get(mode)
    if not fn:
        print(
            "usage: field-one.py [json|sync|compact|scan|restore|convert|defield|refield|install-phase|team-status] [--apply] [--confirm] [--storage-only]",
            file=sys.stderr,
        )
        return 2
    result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())