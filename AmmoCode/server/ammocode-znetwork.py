#!/usr/bin/env python3
"""AmmoCode ↔ NewLatest ZNetwork bridge — attach if running, hook if not; never interfere."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SG = ROOT.parent
NEWLATEST = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", NEWLATEST / ".nexus-state"))
ORCH = NEWLATEST / "lib" / "znetwork-orchestrator.py"
FIELD_SH = NEWLATEST / "lib" / "znetwork-field.sh"
ATTACH_JSON = STATE / "ammocode-znetwork-attach.json"
SHIELD_MARKER = STATE / "ammocode-shield-active.marker"

_STATUS_CACHE: dict[str, Any] | None = None
_STATUS_AT = 0.0
_STATUS_TTL = 10.0
_HOOK_LOCK = threading.Lock()
_HOOK_DONE = False


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _runner() -> str:
    for cmd in (os.environ.get("NEXUS_PYTHONG", ""), "pythong", "python3"):
        if cmd and _which(cmd):
            return cmd
    return sys.executable


def _which(cmd: str) -> bool:
    try:
        subprocess.run([cmd, "--version"], capture_output=True, timeout=3, check=False)
        return True
    except (OSError, subprocess.TimeoutExpired):
        return False


def is_running() -> bool:
    if (STATE / "znetwork-running.marker").is_file():
        return True
    sock = STATE / "znetwork-field.sock"
    if sock.exists():
        return True
    op = _load_json(STATE / "znetwork-operator.json", {})
    if op.get("running") is True and op.get("choice") == "yes":
        return True
    try:
        proc = subprocess.run(
            ["pgrep", "-f", "[z]network.*policy"],
            capture_output=True, text=True, timeout=2,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    return False


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(NEWLATEST),
        "NEXUS_STATE_DIR": str(STATE),
        "SG_ROOT": str(SG),
        "NEXUS_ZNETWORK": os.environ.get("NEXUS_ZNETWORK", "1"),
        "NEXUS_ZNETWORK_NO_SUDO": os.environ.get("NEXUS_ZNETWORK_NO_SUDO", "1"),
        "ZNETWORK_NEVER_HARM_OS": os.environ.get("ZNETWORK_NEVER_HARM_OS", "1"),
        "NEXUS_NEVER_HARM_OS": os.environ.get("NEXUS_NEVER_HARM_OS", "1"),
        "ZNETWORK_SMART_INSIDE": os.environ.get("ZNETWORK_SMART_INSIDE", "1"),
        "ZNETWORK_RELAYER": os.environ.get("ZNETWORK_RELAYER", "1"),
        "ZNETWORK_UNDERHOOK": "0",
        "ZNETWORK_MODE": os.environ.get("ZNETWORK_MODE", "REVIEW_ONLY"),
    }


def orchestrator_json() -> dict[str, Any]:
    if not ORCH.is_file():
        return {"ok": False, "error": "orchestrator_missing", "path": str(ORCH)}
    try:
        proc = subprocess.run(
            [_runner(), str(ORCH), "json"],
            capture_output=True, text=True, timeout=12, env=_env(),
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": "orchestrator_empty"}


def _write_attach(running: bool, interfered: bool, detail: str) -> dict[str, Any]:
    doc = {
        "schema": "ammocode-znetwork-attach/v1",
        "ok": True,
        "ammocode": True,
        "znetwork_running": running,
        "interfered": interfered,
        "attach_only": running,
        "detail": detail,
        "hook_depth": [
            "ammocode_editor",
            "g16_security",
            "ddos_guard",
            "znetwork_field",
        ],
        "shield": _load_json(ROOT / "data" / "ammocode-shield-doctrine.json", {}),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        ATTACH_JSON.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        SHIELD_MARKER.write_text("ammocode-shield-active\n", encoding="utf-8")
    except OSError:
        pass
    return doc


def _defield_blocks_hook() -> bool:
    marker = STATE / "ammocode-defield.marker"
    if marker.is_file():
        return True
    if os.environ.get("AMMOCODE_DEFIELD", "").strip().lower() in ("1", "true", "yes"):
        return True
    return False


def hook_ammocode() -> dict[str, Any]:
    """Hook ZNetwork for AmmoCode session. If already running → attach only."""
    global _HOOK_DONE
    if _defield_blocks_hook():
        _write_attach(False, False, "defield_active_no_field")
        return {
            "ok": True,
            "hooked": False,
            "running": False,
            "interfered": False,
            "action": "defield_skip",
            "ammocode_hooked": True,
            "defield": True,
            "message": "SG defielded — ZNetwork field hook skipped",
        }
    with _HOOK_LOCK:
        if _HOOK_DONE:
            running = is_running()
            _write_attach(running, False, "idempotent_attach")
            return {
                "ok": True,
                "hooked": True,
                "running": running,
                "interfered": False,
                "action": "attach_only",
                "ammocode_hooked": True,
                "message": "ZNetwork already running — AmmoCode attached without interference",
            }

        running_before = is_running()
        if running_before:
            _write_attach(True, False, "attach_only_existing_znetwork")
            _light_publish()
            _HOOK_DONE = True
            return {
                "ok": True,
                "hooked": True,
                "running": True,
                "interfered": False,
                "action": "attach_only",
                "ammocode_hooked": True,
                "message": "ZNetwork already running — AmmoCode attached without interference",
            }

    if not FIELD_SH.is_file():
        return {
            "ok": False,
            "hooked": False,
            "running": False,
            "error": "znetwork_field_sh_missing",
            "newlatest": str(NEWLATEST),
        }

    script = (
        f'set -euo pipefail; '
        f'export NEXUS_INSTALL_ROOT="{NEWLATEST}"; '
        f'export NEXUS_STATE_DIR="{STATE}"; '
        f'export SG_ROOT="{SG}"; '
        f'export NEXUS_ZNETWORK=1 NEXUS_ZNETWORK_NO_SUDO=1; '
        f'export ZNETWORK_RELAYER=1 ZNETWORK_UNDERHOOK=0 ZNETWORK_SMART_INSIDE=1 ZNETWORK_TAKEOVER=0; '
        f'export ZNETWORK_NEVER_HARM_OS=1 NEXUS_NEVER_HARM_OS=1; '
        f'source "{FIELD_SH}"; '
        f'nexus_znetwork_relayer_py relay 2>/dev/null || nexus_znetwork_startup_with_us'
    )
    try:
        proc = subprocess.run(
            ["bash", "-c", script],
            capture_output=True, text=True, timeout=45, env=_env(),
        )
        ok = proc.returncode == 0 or is_running()
        _write_attach(is_running(), not running_before, "startup_with_us")
        _HOOK_DONE = True
        return {
            "ok": ok,
            "hooked": ok,
            "running": is_running(),
            "interfered": False,
            "action": "startup_with_us",
            "ammocode_hooked": ok,
            "stdout_tail": (proc.stdout or "")[-400:],
            "stderr_tail": (proc.stderr or "")[-400:],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "hooked": False, "error": str(exc)}


def _light_publish() -> None:
    """Ensure tray/publish on running stack — same as nexus startup_with_us running branch."""
    if not FIELD_SH.is_file():
        return
    script = (
        f'source "{FIELD_SH}" 2>/dev/null; '
        f'nexus_znetwork_ensure_tray 2>/dev/null; '
        f'nexus_znetwork_publish 2>/dev/null; true'
    )
    try:
        subprocess.run(
            ["bash", "-c", script],
            capture_output=True, text=True, timeout=20, env=_env(),
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def status(force: bool = False) -> dict[str, Any]:
    global _STATUS_CACHE, _STATUS_AT
    now = time.monotonic()
    if not force and _STATUS_CACHE and (now - _STATUS_AT) < _STATUS_TTL:
        return _STATUS_CACHE

    running = is_running()
    orch = orchestrator_json() if ORCH.is_file() else {}
    attach = _load_json(ATTACH_JSON, {})
    shield = _load_json(ROOT / "data" / "ammocode-shield-doctrine.json", {})

    doc = {
        "ok": True,
        "znetwork": {
            "running": running,
            "attach": attach,
            "orchestrator": orch if orch.get("ok") else {"ok": False, "posture": orch},
            "newlatest": str(NEWLATEST),
            "state_dir": str(STATE),
            "interfered": False,
            "coexist": True,
        },
        "shield": shield,
        "ammocode_hooked": attach.get("ok") or SHIELD_MARKER.is_file(),
        "capture_policy": shield.get("capture", {}),
    }
    _STATUS_CACHE = doc
    _STATUS_AT = now
    return doc


def hook_on_boot() -> None:
    if os.environ.get("AMMOCODE_NO_ZNETWORK") == "1":
        return
    if _defield_blocks_hook():
        sys.stderr.write("AmmoCode: defield active — skipping ZNetwork field hook\n")
        return
    try:
        hook_ammocode()
    except Exception as exc:
        sys.stderr.write(f"AmmoCode ZNetwork hook: {exc}\n")


def invalidate_cache() -> None:
    global _STATUS_CACHE, _STATUS_AT
    _STATUS_CACHE = None
    _STATUS_AT = 0.0