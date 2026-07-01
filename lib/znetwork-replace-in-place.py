#!/usr/bin/env pythong
"""ZNetwork in-place replacement — retire old stack, install smart inside + exploit shield."""
from __future__ import annotations

import json
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
RECEIPT = STATE / "znetwork-replace-receipt.json"
ARCHIVE = STATE / "znetwork-old-stack-archived.json"
LEDGER = STATE / "znetwork-replace.jsonl"
SCHEMA = "znetwork-replace-in-place/v1"

OLD_STATE_KEYS = (
    "znetwork-underhook.json",
    "znetwork-takeover-rollback.json",
    "znetwork-connection.json",
    "znetwork-handler-guard.json",
    "znetwork-status.json",
    "znetwork-operator.json",
    "znetwork-running.marker",
    "znetwork-field.sock",
    "znetwork-skip.marker",
)

OLD_PROC_PATTERNS = (
    "znetwork-orchestrator.py",
    "znetwork-review-gate.sh",
    "znetwork-hostile-threat.py",
    "znetwork-os-takeover.py",
    "dns-service-takeover.py",
    "connection-manager.py",
    "field-network-bridge.py",
)

_MOD_CACHE: dict[str, Any] = {}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _log(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _mod(py: Path, name: str) -> Any | None:
    key = str(py)
    if key in _MOD_CACHE:
        return _MOD_CACHE[key]
    if not py.is_file():
        return None
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MOD_CACHE[key] = mod
    return mod


def _read_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _is_old_stack_active() -> dict[str, Any]:
    reasons: list[str] = []
    conn = _load(STATE / "znetwork-connection.json") or {}
    guard = _load(STATE / "znetwork-handler-guard.json") or {}
    status = _load(STATE / "znetwork-status.json") or {}

    if conn.get("coexist_os") is False or conn.get("native_backend_superseded"):
        reasons.append("old_destructive_handoff")
    if guard.get("active") and not guard.get("smart_inside"):
        reasons.append("old_guard_without_smart_inside")
    if status.get("native_backend_superseded"):
        reasons.append("old_status_superseded")
    if (STATE / "znetwork-takeover-rollback.json").is_file():
        reasons.append("os_takeover_rollback_pending")
    if (INSTALL / "bin" / "znetwork.stale-20260625").is_file():
        reasons.append("stale_binary_present")
    if os.environ.get("ZNETWORK_TAKEOVER", "0") == "1" and os.environ.get("ZNETWORK_SMART_INSIDE", "1") == "0":
        reasons.append("env_old_takeover")

    return {
        "old_active": bool(reasons),
        "reasons": reasons,
        "connection_verdict": conn.get("verdict"),
        "guard_smart_inside": guard.get("smart_inside"),
    }


def _kill_old_workers() -> dict[str, Any]:
    my_pid = os.getpid()
    killed: list[dict[str, Any]] = []
    for pid_dir in Path("/proc").iterdir():
        if not pid_dir.name.isdigit():
            continue
        pid = int(pid_dir.name)
        if pid == my_pid:
            continue
        cmd = _read_cmdline(pid)
        if not cmd:
            continue
        if not any(pat in cmd for pat in OLD_PROC_PATTERNS):
            continue
        if "znetwork-replace-in-place" in cmd or "znetwork-smart-inside" in cmd:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            killed.append({"pid": pid, "cmd": cmd[:200], "ok": True})
        except OSError as exc:
            killed.append({"pid": pid, "cmd": cmd[:200], "ok": False, "error": str(exc)})
    time.sleep(0.2)
    return {"ok": True, "killed_count": sum(1 for k in killed if k.get("ok")), "killed": killed}


def _archive_old_state() -> dict[str, Any]:
    archived: dict[str, Any] = {"ts": _now(), "files": {}}
    for name in OLD_STATE_KEYS:
        path = STATE / name
        if not path.exists():
            continue
        try:
            if path.is_file():
                archived["files"][name] = path.read_text(encoding="utf-8", errors="replace")[:8000]
                path.unlink(missing_ok=True)
            elif path.is_socket():
                path.unlink(missing_ok=True)
                archived["files"][name] = "<socket>"
        except OSError as exc:
            archived["files"][name] = f"error:{exc}"
    _save(ARCHIVE, archived)
    return {"ok": True, "archived_keys": sorted(archived["files"].keys()), "archive": str(ARCHIVE)}


def _remove_stale_binary() -> dict[str, Any]:
    stale = INSTALL / "bin" / "znetwork.stale-20260625"
    if not stale.is_file():
        return {"ok": True, "skipped": True}
    archive = STATE / "bin-archive"
    archive.mkdir(parents=True, exist_ok=True)
    dest = archive / stale.name
    try:
        stale.replace(dest)
        return {"ok": True, "removed": str(stale), "archived_to": str(dest)}
    except OSError:
        try:
            stale.unlink(missing_ok=True)
            return {"ok": True, "removed": str(stale)}
        except OSError as exc:
            return {"ok": False, "error": str(exc)}


def _rollback_old_os_takeover() -> dict[str, Any]:
    takeover = _mod(INSTALL / "lib" / "znetwork-os-takeover.py", "znetwork_os_takeover_rb")
    if takeover and hasattr(takeover, "rollback_old_takeover"):
        return takeover.rollback_old_takeover()
    rb = STATE / "znetwork-takeover-rollback.json"
    if not rb.is_file():
        return {"ok": True, "skipped": True, "reason": "no_rollback"}
    try:
        runner = os.environ.get("NEXUS_PYTHONG", "pythong")
        proc = subprocess.run(
            [runner, str(INSTALL / "lib" / "znetwork-os-takeover.py"), "rollback"],
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "skipped": True}


def _install_new_stack() -> dict[str, Any]:
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "ZNETWORK_SMART_INSIDE": "1",
        "ZNETWORK_TAKEOVER": "0",
        "ZNETWORK_PROTECTION_ONLY": "0",
        "ZNETWORK_NEVER_HARM_OS": "1",
        "NEXUS_NEVER_HARM_OS": "1",
        "NEXUS_ZNETWORK_NO_SUDO": "1",
        "ZNETWORK_MODE": os.environ.get("ZNETWORK_MODE", "ACTIVE"),
    }
    smart = _mod(INSTALL / "lib" / "znetwork-smart-inside.py", "znetwork_smart_inside_replace")
    if not smart or not hasattr(smart, "own_connection"):
        return {"ok": False, "error": "smart_inside_missing"}
    os.environ.update(env)
    own = smart.own_connection()
    exploit = _mod(INSTALL / "lib" / "znetwork-exploit-shield.py", "znetwork_exploit_replace")
    exploit_rep = exploit.scan(publish=True) if exploit and hasattr(exploit, "scan") else {"skipped": True}
    return {"ok": bool(own.get("ok")), "smart_inside": own, "exploit_shield": exploit_rep}


def replace_in_place(*, force: bool = False) -> dict[str, Any]:
    """Remove old ZNetwork stack and install smart inside + exploit shield in place."""
    detected = _is_old_stack_active()
    if not force and not detected.get("old_active") and (STATE / "znetwork-replace-receipt.json").is_file():
        receipt = _load(RECEIPT) or {}
        if receipt.get("stack") == "smart_inside_v4.1":
            return {
                "ok": True,
                "schema": SCHEMA,
                "skipped": True,
                "reason": "already_replaced",
                "receipt": receipt,
            }

    steps: dict[str, Any] = {}
    steps["detect"] = detected
    steps["kill_workers"] = _kill_old_workers()
    steps["rollback_os"] = _rollback_old_os_takeover()
    steps["archive_state"] = _archive_old_state()
    steps["remove_stale_binary"] = _remove_stale_binary()

    retire = _mod(INSTALL / "lib" / "znetwork-handler-retire.py", "znetwork_handler_retire_replace")
    if retire and hasattr(retire, "retire_legacy_handlers"):
        os.environ["ZNETWORK_NEVER_HARM_OS"] = "1"
        steps["retire_legacy"] = retire.retire_legacy_handlers(znetwork_active=True)

    steps["install_new"] = _install_new_stack()

    startup_retire = _mod(INSTALL / "lib" / "znetwork-startup-retire.py", "znetwork_startup_retire")
    if startup_retire and hasattr(startup_retire, "retire_host_startup"):
        steps["startup_retire"] = startup_retire.retire_host_startup()

    marker = STATE / "znetwork-running.marker"
    try:
        marker.write_text(f"running=1\nstack=smart_inside\nupdated={_now()}\n", encoding="utf-8")
        os.chmod(marker, 0o600)
    except OSError:
        pass

    relayer_marker = {
        "schema": "znetwork-relayer/v1",
        "active": True,
        "layer": "relayer",
        "stack": "relayer_v4.2",
        "replaced_old": True,
        "sole_stack": True,
        "mode": os.environ.get("ZNETWORK_MODE", "ACTIVE"),
        "updated": _now(),
        "policy": "in_place_replace_old_removed",
    }
    _save(STATE / "znetwork-relayer.json", relayer_marker)
    try:
        (STATE / "znetwork-underhook.json").unlink(missing_ok=True)
    except OSError:
        pass

    ok = bool((steps.get("install_new") or {}).get("ok"))
    receipt = {
        "schema": SCHEMA,
        "ok": ok,
        "stack": "smart_inside_v4.1",
        "replaced_at": _now(),
        "old_reasons": detected.get("reasons") or [],
        "steps": {k: v for k, v in steps.items() if k != "install_new"},
        "install_ok": ok,
        "os": platform.system().lower(),
        "motto": "Old ZNetwork removed — smart inside + exploit shield owns policy in place.",
    }
    inst = steps.get("install_new") or {}
    if inst.get("smart_inside"):
        receipt["connection_verdict"] = (inst["smart_inside"].get("connection") or {}).get("verdict")
    _save(RECEIPT, receipt)
    _log({"event": "replace_in_place", "ok": ok, "old_reasons": detected.get("reasons")})

    return {**receipt, "install_new": inst}


def posture() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "ok": True,
        "old_stack": _is_old_stack_active(),
        "receipt": _load(RECEIPT),
        "archive": str(ARCHIVE) if ARCHIVE.is_file() else None,
        "checked_at": _now(),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    force = "--force" in sys.argv
    handlers = {
        "json": posture,
        "posture": posture,
        "replace": lambda: replace_in_place(force=force),
    }
    fn = handlers.get(cmd)
    if not fn:
        print(json.dumps({"error": "usage: znetwork-replace-in-place.py [json|replace]"}), file=sys.stderr)
        return 2
    result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())