#!/usr/bin/env pythong
"""Queen field boot — login, rebuild, reboot (Hostess zac/self-update patterns inside Queen)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", QUEEN.parent.parent / "Hostess7"))
GROK_AUTH = Path.home() / ".grok" / "auth.json"
BOOT_LOG = STATE / "queen-boot.log"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _log(msg: str) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with BOOT_LOG.open("a", encoding="utf-8") as f:
        f.write(f"[{_now()}] {msg}\n")


def _env_on(key: str) -> bool:
    return os.environ.get(key, "") in ("1", "true", "yes", "on")


def load_rtx_doctrine() -> dict[str, Any]:
    for p in (QUEEN / "data" / "field-rtx-sovereign.json", INSTALL / "data" / "field-rtx-sovereign.json"):
        doc = _load_json(p, {})
        if doc.get("schema") == "field-rtx-sovereign/v1":
            return doc
    return {}


def grok_login_status() -> dict[str, Any]:
    authed = GROK_AUTH.is_file()
    detail: dict[str, Any] = {"path": str(GROK_AUTH), "present": authed}
    if authed:
        doc = _load_json(GROK_AUTH, {})
        detail["has_token"] = bool(doc.get("access_token") or doc.get("token") or doc)
    return {
        "logged_in": authed,
        "auth": detail,
        "login_cmd": "grok login --oauth",
        "headless_cmd": "grok login --device-auth",
        "secure_channel": _env_on("NEXUS_AI_SECURE_CHANNEL") and _env_on("QUEEN_GROK_BUILD_SECURE"),
    }


def grok_login_start(*, device: bool = False) -> dict[str, Any]:
    if not (_env_on("NEXUS_AI_SECURE_CHANNEL") or _env_on("QUEEN_GROK_BUILD_SECURE")):
        return {"ok": False, "error": "secure_channel_required"}
    cmd = ["grok", "login", "--device-auth" if device else "--oauth"]
    try:
        proc = subprocess.run(cmd, cwd=str(QUEEN), timeout=300, text=True, capture_output=True)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[-1500:],
            "stderr": (proc.stderr or "")[-1500:],
            "status": grok_login_status(),
        }
    except FileNotFoundError:
        return {"ok": False, "error": "grok_cli_missing", "hint": "Install Grok CLI for in-engine login"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "login_timeout"}


def hostess_teach_redata_optional() -> dict[str, Any]:
    bridge = QUEEN / "lib" / "queen-hostess-brain.py"
    if not bridge.is_file() or not HOSTESS.is_dir():
        return {"ok": True, "skipped": True, "reason": "no_hostess_bridge"}
    _log("hostess_teach_redata start")
    try:
        proc = subprocess.run(
            [sys.executable, str(bridge), "teach"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=180,
        )
        _log(f"hostess_teach_redata rc={proc.returncode}")
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "tail": (proc.stdout or "")[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "teach_timeout"}


def sdf_verify_redata_optional() -> dict[str, Any]:
    h7sh = HOSTESS / "Hostess7.sh"
    if not h7sh.is_file():
        return {"ok": True, "skipped": True, "reason": "no_hostess7"}
    _log("sdf_verify_redata start")
    try:
        proc = subprocess.run(
            [str(h7sh), "sdf-verify-redata"],
            cwd=str(HOSTESS),
            capture_output=True,
            text=True,
            timeout=120,
        )
        _log(f"sdf_verify_redata rc={proc.returncode}")
        return {
            "ok": proc.returncode == 0,
            "skipped": proc.returncode != 0 and b"segments missing" in (proc.stderr or "").encode(),
            "returncode": proc.returncode,
            "tail": ((proc.stdout or "") + (proc.stderr or ""))[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "verify_timeout"}


def zac_restore_optional() -> dict[str, Any]:
    zac = HOSTESS / "scripts" / "field_zac.py"
    zac_dir = HOSTESS / "zac"
    if not zac.is_file() or not zac_dir.is_dir():
        return {"ok": True, "skipped": True, "reason": "no_hostess_zac"}
    _log("zac_restore start")
    try:
        proc = subprocess.run(
            [sys.executable, str(zac), "restore", "--from", str(zac_dir)],
            cwd=str(HOSTESS),
            capture_output=True,
            text=True,
            timeout=600,
        )
        _log(f"zac_restore rc={proc.returncode}")
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "tail": ((proc.stdout or "") + (proc.stderr or ""))[-2000:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "zac_timeout"}


def rebuild_core() -> dict[str, Any]:
    build = QUEEN / "lib" / "queen-build.py"
    if not build.is_file():
        return {"ok": False, "error": "queen_build_missing"}
    _log("rebuild_core start")
    proc = subprocess.run(
        [sys.executable, str(build), "run-all"],
        cwd=str(QUEEN),
        capture_output=True,
        text=True,
        timeout=7200,
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "QUEEN_ROOT": str(QUEEN)},
    )
    _log(f"rebuild_core rc={proc.returncode}")
    try:
        status = json.loads(proc.stdout.splitlines()[-1] if proc.stdout else "{}")
    except (json.JSONDecodeError, IndexError):
        status = {}
    return {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-3000:],
        "build_status": status,
    }


def reboot_queen(*, detach: bool = True) -> dict[str, Any]:
    launcher = QUEEN / "scripts" / "run-queen.sh"
    if not launcher.is_file():
        return {"ok": False, "error": "queen_launcher_missing", "hint": "Queen/scripts/run-queen.sh missing"}
    _log("reboot_queen")
    retire = INSTALL / "lib" / "amouranthrtx-window-retire.sh"
    if retire.is_file():
        subprocess.run(["bash", "-c", f"source '{retire}' && amouranthrtx_window_retire_cycle"], check=False, timeout=10)
    cmd = [str(launcher)]
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "QUEEN_ROOT": str(QUEEN),
        "QUEEN_FIELD_GPU": "1",
        "QUEEN_GROK_BUILD": "1",
        "QUEEN_GROK_BUILD_SECURE": "1",
        "NEXUS_AI_SECURE_CHANNEL": "1",
        "QUEEN_AI_TELEMETRY_OK": "1",
    }
    if detach:
        proc = subprocess.Popen(
            cmd,
            cwd=str(QUEEN),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return {"ok": True, "pid": proc.pid, "cmd": cmd, "detached": True}
    proc = subprocess.run(cmd, cwd=str(QUEEN), env=env, timeout=30, capture_output=True, text=True)
    return {"ok": proc.returncode == 0, "returncode": proc.returncode}


def boot_status() -> dict[str, Any]:
    binary = QUEEN / "build" / "rtx/bin/Linux/queen-browser"
    mandate = _load_json(QUEEN / "data" / "queen-boot-mandate.json", {})
    rtx = load_rtx_doctrine()
    return {
        "schema": "queen-field-boot/v1",
        "updated": _now(),
        "queen_root": str(QUEEN),
        "hostess_root": str(HOSTESS) if HOSTESS.is_dir() else None,
        "inside": (QUEEN / ".queen-inside").is_file(),
        "grok_login": grok_login_status(),
        "rtx_sovereign": {
            "title": rtx.get("title"),
            "phase_now": (rtx.get("phases") or {}).get("now"),
            "phase_forever": (rtx.get("phases") or {}).get("forever"),
            "field_gpu": _env_on("QUEEN_FIELD_GPU"),
        },
        "binary_ready": binary.is_file() and os.access(binary, os.X_OK),
        "binary": str(binary),
        "boot_sequence": mandate.get("boot_sequence") or [],
        "can_rebuild": (QUEEN / "lib" / "queen-forge.py").is_file() and (QUEEN / "lib" / "queen-build.py").is_file(),
        "forge": "lib/queen-forge.py",
        "can_zac_restore": (HOSTESS / "scripts" / "field_zac.py").is_file(),
        "hostess_brain": _hostess_brain_summary(),
    }


def _hostess_brain_summary() -> dict[str, Any]:
    bridge = QUEEN / "lib" / "queen-hostess-brain.py"
    if not bridge.is_file():
        return {"available": False}
    try:
        proc = subprocess.run(
            [sys.executable, str(bridge), "json"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    except (json.JSONDecodeError, subprocess.TimeoutExpired):
        pass
    return {"available": False}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json"):
        return {"ok": True, **boot_status()}
    if action in ("login", "grok-login", "grok_login"):
        return grok_login_start(device=body.get("device") in (True, 1, "1", "device"))
    if action in ("rebuild", "build", "run-all"):
        return rebuild_core()
    if action in ("reboot", "restart"):
        return reboot_queen(detach=body.get("detach", True) is not False)
    if action in ("zac-restore", "zac_restore"):
        return zac_restore_optional()
    if action in ("hostess-teach", "hostess_teach", "queen-teach-redata"):
        return hostess_teach_redata_optional()
    if action in ("sdf-verify-redata", "sdf_verify_redata", "verify-redata"):
        return sdf_verify_redata_optional()
    if action in ("hostess-brain", "hostess_brain"):
        return {"ok": True, **_hostess_brain_summary()}
    if action in ("full-boot", "full_boot", "boot"):
        steps = []
        for name, fn in (
            ("grok_login", lambda: grok_login_status()),
            ("zac_restore", zac_restore_optional),
            ("hostess_teach_redata", hostess_teach_redata_optional),
            ("sdf_verify_redata", sdf_verify_redata_optional),
            ("rebuild", rebuild_core),
            ("reboot", lambda: reboot_queen(detach=True)),
        ):
            if name == "grok_login":
                st = fn()
                steps.append({"step": name, "logged_in": st.get("logged_in")})
                if not st.get("logged_in"):
                    steps.append({"step": "login_required", "ok": False})
                    return {"ok": False, "steps": steps, "status": boot_status()}
                continue
            if name == "zac_restore" and body.get("skip_zac"):
                steps.append({"step": name, "skipped": True})
                continue
            if name in ("hostess_teach_redata", "sdf_verify_redata") and body.get("skip_hostess"):
                steps.append({"step": name, "skipped": True})
                continue
            out = fn()
            steps.append({"step": name, **out})
            if not out.get("ok", True) and not out.get("skipped"):
                return {"ok": False, "steps": steps, "status": boot_status()}
        return {"ok": True, "steps": steps, "status": boot_status()}
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(boot_status(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-field-boot.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())