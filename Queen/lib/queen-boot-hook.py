#!/usr/bin/env pythong
"""Queen boot hook — board before host plugins, daemons, or foreign hooks eat our surface."""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
HOOK_STAMP = STATE / "queen-boot-hook.stamp"
HOOK_DOC = STATE / "queen-boot-hook.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_json(script: Path, *args: str, timeout: int = 45) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(script)}
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(QUEEN),
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(INSTALL),
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _kilroy_kernel() -> bool:
    try:
        ver = Path("/proc/version").read_text(encoding="utf-8", errors="replace").lower()
        return "kilroy" in ver or "field die" in ver
    except OSError:
        return False


def is_boot_os() -> bool:
    flag = os.environ.get("QUEEN_BOOT_OS", os.environ.get("NEXUS_QUEEN_BOOT_OS", "")).strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return True
    if _kilroy_kernel():
        return True
    marker = STATE / "queen-boot-os.marker"
    if marker.is_file():
        return True
    covenant = STATE / "root-sovereign-covenant.json"
    if covenant.is_file() and os.environ.get("QUEEN_SOVEREIGN", "1") == "1":
        doc = _load(covenant, {})
        if doc.get("boot_os") or doc.get("queen_boot_os"):
            return True
    return False


def board_once(*, force: bool = False) -> dict[str, Any]:
    if HOOK_STAMP.is_file() and not force:
        cached = _load(HOOK_DOC, {})
        if cached.get("schema") == "queen-boot-hook/v1":
            cached["from_cache"] = True
            return cached

    native = _run_json(INSTALL / "lib" / "native-layer.py", "json", timeout=30)
    firmware = _run_json(INSTALL / "lib" / "field-firmware-threat-removal.py", "json", timeout=25)
    host_desktop = _run_json(INSTALL / "lib" / "field-host-desktop.py", "build", timeout=60)

    doc: dict[str, Any] = {
        "schema": "queen-boot-hook/v1",
        "ts": _now(),
        "ok": True,
        "boarded": True,
        "boot_os": is_boot_os(),
        "front_hook": {
            "owner": "nexus-front-hook",
            "pass_through": False,
            "policy": "capture_phase_before_foreign_hooks",
        },
        "network_metal": {
            "layer": "bios_witness",
            "flash_chip": False,
            "witness_only": True,
            "firmware_witness": (native.get("firmware_witness") or {}),
            "firmware_threat": {
                "schema": firmware.get("schema"),
                "ok": firmware.get("ok", True),
                "posture": firmware.get("posture") or firmware.get("verdict"),
            },
            "native_stack": native.get("stack") or [],
            "policy": "internet_out_only_no_bullshit",
        },
        "host": {
            "system": platform.system(),
            "node": platform.node(),
            "kilroy_kernel": _kilroy_kernel(),
        },
        "host_desktop_built": bool(host_desktop.get("programs")),
        "install_root": str(INSTALL),
        "state_dir": str(STATE),
    }
    _save(HOOK_DOC, doc)
    HOOK_STAMP.write_text(doc["ts"] + "\n", encoding="utf-8")
    return doc


def posture() -> dict[str, Any]:
    if HOOK_DOC.is_file():
        doc = _load(HOOK_DOC, {})
        if doc.get("schema") == "queen-boot-hook/v1":
            doc["boot_os"] = is_boot_os()
            return doc
    return board_once()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("board", "hook", "startup"):
        print(json.dumps(board_once(force="--force" in sys.argv), ensure_ascii=False))
        return 0
    if cmd == "boot_os":
        print(json.dumps({"boot_os": is_boot_os()}, ensure_ascii=False))
        return 0
    print(json.dumps(posture(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())