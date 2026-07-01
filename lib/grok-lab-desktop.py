#!/usr/bin/env pythong
"""Grok AI Lab — AmmoOS desktop surface API (bootable protection + Final Eye OCR brain)."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
LAB = Path(os.environ.get("GROK_LAB_ROOT", str(INSTALL / "GrokLab")))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = LAB / "data" / "grok-ai-lab-doctrine.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _py_json(script: Path, *argv: str, timeout: int = 90) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": f"missing {script}"}
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "GROK_LAB_ROOT": str(LAB),
        "NEXUS_STATE_DIR": str(STATE),
    }
    proc = subprocess.run(
        [sys.executable, str(script), *argv],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        cwd=str(INSTALL),
    )
    try:
        return json.loads(proc.stdout) if proc.stdout.strip() else {"ok": False, "tail": proc.stderr[-500:]}
    except json.JSONDecodeError:
        return {"ok": False, "returncode": proc.returncode, "tail": (proc.stdout or proc.stderr or "")[-1500:]}


def find_urls() -> dict[str, str]:
    port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    eye = int(os.environ.get("FINAL_EYE_PORT", "9479"))
    world = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    return {
        "desktop": f"http://127.0.0.1:{port}/grok-lab",
        "ammoos_field": f"http://127.0.0.1:{port}/field",
        "final_eye": f"http://127.0.0.1:{eye}/",
        "final_eye_ops": f"http://127.0.0.1:{eye}/ops",
        "queen_world": f"http://127.0.0.1:{world}/world/",
        "command_embed": f"http://127.0.0.1:{port}/command?embed=1#grok-lab",
    }


def posture() -> dict[str, Any]:
    doctrine_path = LAB / "data" / "grok-ai-lab-doctrine.json"
    try:
        doctrine = json.loads(doctrine_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        doctrine = {}
    lab = _load_mod("grok_ai_lab", "lib/grok-ai-lab.py")
    status: dict[str, Any] = {}
    if lab and hasattr(lab, "status"):
        try:
            status = lab.status()
        except (OSError, TypeError, ValueError):
            status = {}
    receipt = STATE / "boot-rekill.json"
    reval = STATE / "kill-list-revalidate.json"
    boot_marker = STATE / "grok-lab-boot-desktop.json"
    return {
        "schema": "grok-lab-desktop/v1",
        "updated": _now(),
        "product": "Grok AI Lab",
        "subtitle": "World perimeter · coexist · kill evil · new internet from every home",
        "owner": "grok",
        "home": "127.0.0.1",
        "motto": doctrine.get("motto"),
        "war_posture": (doctrine.get("war") or {}).get("posture", "forever_at_war_with_terror"),
        "perimeter": (doctrine.get("war") or {}).get("perimeter", "the_world"),
        "doctrine": doctrine,
        "lab_status": status,
        "urls": find_urls(),
        "paths": {
            "lab_root": str(LAB),
            "install_root": str(INSTALL),
            "state_dir": str(STATE),
            "cli": str(LAB / "scripts" / "grok-lab-run.sh"),
            "module": str(INSTALL / "lib" / "grok-ai-lab.py"),
        },
        "boot_rekill": (
            json.loads(receipt.read_text(encoding="utf-8")) if receipt.is_file() else None
        ),
        "kill_revalidate": (
            json.loads(reval.read_text(encoding="utf-8")) if reval.is_file() else None
        ),
        "boot_desktop_marker": (
            json.loads(boot_marker.read_text(encoding="utf-8")) if boot_marker.is_file() else None
        ),
        "world_nodes": _world_nodes_slice(),
    }


def _world_nodes_slice() -> dict[str, Any] | None:
    world_py = INSTALL / "lib" / "grok-lab-world.py"
    if not world_py.is_file():
        return None
    return _py_json(world_py, "status", timeout=90)


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    lab_py = INSTALL / "lib" / "grok-ai-lab.py"
    if action in ("status", "json", "posture"):
        return {"ok": True, **posture()}
    if action in ("boot", "protect", "boot_rekill"):
        return {"ok": True, "action": action, **_py_json(lab_py, "boot", timeout=120)}
    if action in ("start", "eye_start"):
        return {"ok": True, "action": action, **_py_json(lab_py, "start", timeout=60)}
    if action in ("battery", "test", "protect_battery"):
        return {"ok": True, "action": action, **_py_json(lab_py, "battery", timeout=180)}
    if action in ("revalidate", "revalidate_kill_list"):
        kit = INSTALL / "lib" / "field-attack-kit.py"
        return {"ok": True, "action": action, **_py_json(kit, "revalidate-kill-list", timeout=60)}
    if action == "live":
        loops = int(body.get("loops") or 3)
        return {"ok": True, "action": action, **_py_json(lab_py, "live", str(loops), timeout=300)}
    world_py = INSTALL / "lib" / "grok-lab-world.py"
    if action in ("world_status", "world"):
        return {"ok": True, "action": action, **_py_json(world_py, "status", timeout=120)}
    if action in ("world_pack",):
        return {"ok": True, "action": action, **_py_json(world_py, "pack", timeout=600)}
    if action in ("world_deploy", "deploy_world"):
        return {"ok": True, "action": action, **_py_json(world_py, "deploy", timeout=900)}
    if action in ("world_bootstrap", "bootstrap_world"):
        return {"ok": True, "action": action, **_py_json(world_py, "register-local", timeout=60)}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch" and len(sys.argv) > 2:
        body = {"action": sys.argv[2], **({"loops": int(sys.argv[3])} if len(sys.argv) > 3 else {})}
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: grok-lab-desktop.py [json|dispatch ACTION]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())