#!/usr/bin/env pythong
"""Queen update bridge — NXF/GitHub update API for browser shell (:9481)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
NEXUS = QUEEN.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", NEXUS / ".nexus-state"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", NEXUS))


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_FIELD_STANDALONE": "1",
    }


def _run_json(script: Path, *args: str, timeout: int = 30) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(script)}
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_env(),
        cwd=str(NEXUS),
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-1500:] + (proc.stderr or "")[-1500:]}


def _update_script() -> Path:
    ammoos = INSTALL / "lib" / "ammoos-update-inplace.py"
    if ammoos.is_file():
        return ammoos
    return INSTALL / "lib" / "nexus-update.py"


def status(*, force: bool = False) -> dict[str, Any]:
    script = _update_script()
    if script.name == "ammoos-update-inplace.py":
        args = ["check"] + (["--force"] if force else [])
        upd = _run_json(script, *args)
    else:
        upd = _run_json(script)
        if force:
            upd = _run_json(script, "--force")
    lock = _run_json(INSTALL / "lib" / "nexus-update-lock.py", "status")
    upd["update_lock"] = lock
    upd["update_in_progress"] = bool(lock.get("locked"))
    needs = STATE / "update-needs-sudo.json"
    if needs.is_file():
        try:
            doc = json.loads(needs.read_text(encoding="utf-8"))
            upd["needs_sudo"] = True
            upd["sudo_prompt"] = doc
        except (OSError, json.JSONDecodeError):
            pass
    if lock.get("locked"):
        upd["update_available"] = False
        upd["message"] = lock.get("message") or "Update in progress"
    return upd


def apply() -> dict[str, Any]:
    lock = _run_json(INSTALL / "lib" / "nexus-update-lock.py", "status")
    if lock.get("locked"):
        return {
            "ok": False,
            "error": "update_in_progress",
            "update_in_progress": True,
            "message": lock.get("message") or "Update already running",
            "update_lock": lock,
        }
    try:
        STATE.joinpath("update-needs-sudo.json").unlink(missing_ok=True)
    except OSError:
        pass
    upd = status(force=True)
    if not upd.get("update_available"):
        return {"ok": True, "already_current": True, **upd}
    script = _update_script()
    product = "AmmoOS" if script.name == "ammoos-update-inplace.py" else "NEXUS"
    target = str(upd.get("latest") or "")
    previous = str(upd.get("previous") or upd.get("current") or "")
    mode = str(upd.get("update_mode") or ("git_tree" if product == "AmmoOS" else "release"))
    git_dir = str(upd.get("source_root") or NEXUS)
    phase = "download_tarball" if mode == "release" else "git_fetch"
    acq = _run_json(
        INSTALL / "lib" / "nexus-update-lock.py",
        "acquire",
        "--holder=queen-browser",
        f"--phase={phase}",
        f"--target={target}",
        f"--previous={previous}",
    )
    if not acq.get("ok"):
        return {
            "ok": False,
            "error": acq.get("error") or "update_in_progress",
            "update_in_progress": True,
            "message": acq.get("message") or "Could not acquire update lock",
        }
    token = str(acq.get("token") or "")
    tarball = str(upd.get("source_tarball") or "")
    if mode == "release" and not tarball:
        _run_json(INSTALL / "lib" / "nexus-update-lock.py", "release", f"--token={token}")
        return {
            "ok": False,
            "error": "release_tarball_missing",
            "message": "No release tarball — check GitHub NXF manifest",
            "release_url": upd.get("release_url"),
        }
    env = _env()
    env.update({
        "NEXUS_UPDATE_LOCK_TOKEN": token,
        "NEXUS_UPDATE_TARGET": target,
        "NEXUS_UPDATE_PREVIOUS": previous,
        "NEXUS_UPDATE_MODE": mode,
        "NEXUS_UPDATE_GIT_DIR": git_dir,
        "NEXUS_UPDATE_TARBALL_URL": tarball,
        "AMMOOS_UPDATE_MODE": mode,
    })
    helper = INSTALL / "lib" / "nexus-update-apply.sh"
    if not helper.is_file():
        _run_json(INSTALL / "lib" / "nexus-update-lock.py", "release", f"--token={token}")
        return {"ok": False, "error": "update_apply_missing"}
    try:
        subprocess.Popen(
            ["bash", str(helper)],
            env=env,
            start_new_session=True,
            cwd=git_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        _run_json(INSTALL / "lib" / "nexus-update-lock.py", "release", f"--token={token}")
        return {"ok": False, "error": "update_spawn_failed", "message": str(exc)}
    lock_now = _run_json(INSTALL / "lib" / "nexus-update-lock.py", "status")
    return {
        "ok": True,
        "started": True,
        "update_in_progress": True,
        "reload_panel": True,
        "message": f"{product} update — {previous} → {target}",
        "previous": previous,
        "latest": target,
        "apply_via": upd.get("apply_via") or "nxf_release",
        "source_tarball": tarball or None,
        "update_lock": lock_now,
        "log": str(STATE / "update-apply.log"),
    }


def sudo_prompt() -> dict[str, Any]:
    lock = _run_json(INSTALL / "lib" / "nexus-update-lock.py", "status")
    needs_path = STATE / "update-needs-sudo.json"
    needs = None
    if needs_path.is_file():
        try:
            needs = json.loads(needs_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            needs = None
    if not needs and not lock.get("locked"):
        return {"ok": False, "error": "no_pending_sudo"}
    token = str(lock.get("token") or os.environ.get("NEXUS_UPDATE_LOCK_TOKEN", ""))
    target = str(lock.get("target_version") or (needs or {}).get("target") or "")
    previous = str(lock.get("previous_version") or (needs or {}).get("previous") or "")
    mode = str((needs or {}).get("update_mode") or os.environ.get("NEXUS_UPDATE_MODE", "release"))
    upd = status()
    env = _env()
    env.update({
        "NEXUS_UPDATE_LOCK_TOKEN": token,
        "NEXUS_UPDATE_TARGET": target,
        "NEXUS_UPDATE_PREVIOUS": previous,
        "NEXUS_UPDATE_MODE": mode,
        "NEXUS_UPDATE_GIT_DIR": str(NEXUS),
    })
    if upd.get("source_tarball"):
        env["NEXUS_UPDATE_TARBALL_URL"] = str(upd["source_tarball"])
    helper = INSTALL / "lib" / "nexus-update-apply.sh"
    try:
        subprocess.Popen(
            ["bash", str(helper)],
            env=env,
            start_new_session=True,
            cwd=str(NEXUS),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"ok": True, "prompt_started": True, "message": "Password prompt opened"}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps(status(), ensure_ascii=False))
        return 0
    cmd = sys.argv[1]
    if cmd == "status":
        force = "--force" in sys.argv
        print(json.dumps(status(force=force), ensure_ascii=False))
        return 0
    if cmd == "apply":
        print(json.dumps(apply(), ensure_ascii=False))
        return 0
    if cmd == "sudo-prompt":
        print(json.dumps(sudo_prompt(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-update.py [status|apply|sudo-prompt]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())