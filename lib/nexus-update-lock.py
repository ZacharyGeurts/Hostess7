#!/usr/bin/env pythong
"""GitHub update lock — prevents concurrent or mid-update panel breaks."""
from __future__ import annotations

import json
import os
import secrets
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
LOCK_PATH = STATE / "github-update.lock"
MAX_LOCK_SEC = int(os.environ.get("NEXUS_UPDATE_LOCK_MAX_SEC", "2400"))
HEARTBEAT_STALE_SEC = int(os.environ.get("NEXUS_UPDATE_HEARTBEAT_STALE_SEC", "180"))


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_lock() -> dict[str, Any] | None:
    try:
        doc = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def _save_lock(doc: dict[str, Any]) -> None:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc["heartbeat_at"] = _now()
    doc["heartbeat_epoch"] = time.time()
    tmp = LOCK_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(LOCK_PATH)
    try:
        os.chmod(LOCK_PATH, 0o640)
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _is_stale(doc: dict[str, Any]) -> bool:
    started = float(doc.get("started_epoch") or 0)
    heartbeat = float(doc.get("heartbeat_epoch") or started)
    age = time.time() - started if started else 0
    hb_age = time.time() - heartbeat if heartbeat else age
    pid = int(doc.get("pid") or 0)
    if age > MAX_LOCK_SEC:
        return True
    if hb_age > HEARTBEAT_STALE_SEC and not _pid_alive(pid):
        return True
    if not _pid_alive(pid) and hb_age > 30:
        return True
    return False


def lock_status() -> dict[str, Any]:
    doc = _load_lock()
    if not doc:
        return {"locked": False, "ok": True}
    stale = _is_stale(doc)
    if stale:
        return {
            "locked": False,
            "ok": True,
            "stale_cleared": False,
            "stale_lock": doc,
        }
    return {
        "locked": True,
        "ok": True,
        "token": doc.get("token"),
        "pid": doc.get("pid"),
        "holder": doc.get("holder"),
        "phase": doc.get("phase"),
        "target_version": doc.get("target_version"),
        "previous_version": doc.get("previous_version"),
        "started_at": doc.get("started_at"),
        "heartbeat_at": doc.get("heartbeat_at"),
        "message": _status_message(doc),
    }


def _status_message(doc: dict[str, Any]) -> str:
    phase = str(doc.get("phase") or "updating")
    prev = doc.get("previous_version") or "?"
    tgt = doc.get("target_version") or "?"
    labels = {
        "acquired": "Preparing update",
        "git_fetch": "Fetching from GitHub",
        "git_pull": "Pulling latest code",
        "stealth_install": "Running install",
        "stopping_services": "Stopping services",
        "copying_files": "Copying files",
        "signing": "Signing manifest",
        "starting_service": "Starting NEXUS",
        "restarting": "Restarting panel",
        "awaiting_sudo": "Waiting for administrator password",
        "failed": "Update failed",
    }
    label = labels.get(phase, phase.replace("_", " "))
    return f"{label} — {prev} → {tgt}"


def clear_stale_lock() -> bool:
    doc = _load_lock()
    if not doc:
        return False
    if not _is_stale(doc):
        return False
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        return False
    return True


def acquire_lock(
    holder: str = "panel",
    phase: str = "acquired",
    target_version: str = "",
    previous_version: str = "",
    pid: int | None = None,
) -> dict[str, Any]:
    clear_stale_lock()
    existing = _load_lock()
    if existing and not _is_stale(existing):
        return {
            "ok": False,
            "locked": True,
            "error": "update_in_progress",
            "message": _status_message(existing),
            **{k: existing.get(k) for k in ("phase", "target_version", "previous_version", "holder", "started_at")},
        }
    token = secrets.token_hex(16)
    doc = {
        "locked": True,
        "token": token,
        "pid": pid if pid is not None else os.getpid(),
        "holder": holder,
        "phase": phase,
        "target_version": target_version,
        "previous_version": previous_version,
        "started_at": _now(),
        "started_epoch": time.time(),
        "heartbeat_at": _now(),
        "heartbeat_epoch": time.time(),
    }
    try:
        LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o640)
        try:
            os.write(fd, (json.dumps(doc, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        finally:
            os.close(fd)
    except FileExistsError:
        existing = _load_lock()
        if existing and _is_stale(existing):
            clear_stale_lock()
            return acquire_lock(holder, phase, target_version, previous_version, pid)
        return {
            "ok": False,
            "locked": True,
            "error": "update_in_progress",
            "message": _status_message(existing or {}),
        }
    except OSError as exc:
        return {"ok": False, "error": f"lock_failed: {exc}"}
    return {"ok": True, "locked": True, "token": token, **doc}


def adopt_lock(token: str, holder: str = "stealth_install", phase: str = "stealth_install") -> dict[str, Any]:
    doc = _load_lock()
    if not doc:
        return {"ok": False, "error": "no_lock"}
    if str(doc.get("token") or "") != str(token):
        if not _is_stale(doc):
            return {"ok": False, "error": "lock_token_mismatch", "locked": True}
        clear_stale_lock()
        return acquire_lock(holder, phase, str(doc.get("target_version") or ""), str(doc.get("previous_version") or ""))
    doc["pid"] = os.getpid()
    doc["holder"] = holder
    doc["phase"] = phase
    _save_lock(doc)
    return {"ok": True, "adopted": True, "token": token, "phase": phase}


def set_phase(phase: str, token: str = "") -> dict[str, Any]:
    doc = _load_lock()
    if not doc:
        return {"ok": False, "error": "no_lock"}
    if token and str(doc.get("token") or "") != str(token):
        return {"ok": False, "error": "lock_token_mismatch"}
    doc["phase"] = phase
    _save_lock(doc)
    return {"ok": True, "phase": phase}


def heartbeat(token: str = "") -> dict[str, Any]:
    doc = _load_lock()
    if not doc:
        return {"ok": False, "error": "no_lock"}
    if token and str(doc.get("token") or "") != str(token):
        return {"ok": False, "error": "lock_token_mismatch"}
    _save_lock(doc)
    return {"ok": True, "heartbeat_at": doc.get("heartbeat_at")}


def release_lock(token: str = "", force: bool = False) -> dict[str, Any]:
    doc = _load_lock()
    if not doc:
        return {"ok": True, "released": False}
    if token and str(doc.get("token") or "") != str(token) and not force:
        return {"ok": False, "error": "lock_token_mismatch"}
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError as exc:
        return {"ok": False, "error": f"release_failed: {exc}"}
    return {"ok": True, "released": True}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip()
    if cmd == "status":
        out = lock_status()
        if out.get("stale_lock"):
            clear_stale_lock()
            out = lock_status()
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if cmd == "acquire":
        holder = "panel"
        phase = "acquired"
        target = ""
        previous = ""
        for arg in sys.argv[2:]:
            if arg.startswith("--holder="):
                holder = arg.split("=", 1)[1]
            elif arg.startswith("--phase="):
                phase = arg.split("=", 1)[1]
            elif arg.startswith("--target="):
                target = arg.split("=", 1)[1]
            elif arg.startswith("--previous="):
                previous = arg.split("=", 1)[1]
        print(json.dumps(acquire_lock(holder, phase, target, previous), ensure_ascii=False))
        return 0
    if cmd == "adopt" and len(sys.argv) >= 3:
        holder = "stealth_install"
        phase = "stealth_install"
        for arg in sys.argv[3:]:
            if arg.startswith("--holder="):
                holder = arg.split("=", 1)[1]
            elif arg.startswith("--phase="):
                phase = arg.split("=", 1)[1]
        out = adopt_lock(sys.argv[2], holder, phase)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "phase" and len(sys.argv) >= 3:
        token = ""
        for arg in sys.argv[3:]:
            if arg.startswith("--token="):
                token = arg.split("=", 1)[1]
        out = set_phase(sys.argv[2], token)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "heartbeat":
        token = ""
        for arg in sys.argv[2:]:
            if arg.startswith("--token="):
                token = arg.split("=", 1)[1]
        out = heartbeat(token)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "release":
        token = ""
        force = "--force" in sys.argv
        for arg in sys.argv[2:]:
            if arg.startswith("--token="):
                token = arg.split("=", 1)[1]
        out = release_lock(token, force=force)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd == "clear-stale":
        print(json.dumps({"ok": True, "cleared": clear_stale_lock()}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: nexus-update-lock.py [status|acquire|adopt TOKEN|phase NAME|heartbeat|release|clear-stale]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())