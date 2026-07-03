#!/usr/bin/env pythong
"""AmmoSecurity / bot-net health — aggregates net harden, watcher, C2 witness (loopback)."""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
AMMO = INSTALL / "ammosecurity"
STATE = Path(os.environ.get("AMMO_STATE_DIR", "/var/lib/ammosecurity"))
NEXUS_STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL_CACHE = NEXUS_STATE / "ammo-net-health-panel.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run_module(script: str, *args: str, timeout: int = 25) -> dict[str, Any]:
    path = AMMO / "modules" / script
    if not path.is_file():
        return {"ok": False, "error": "missing", "script": script}
    env = {
        **os.environ,
        "AMMO_STATE_DIR": str(STATE),
        "NEXUS_INSTALL_ROOT": str(INSTALL),
    }
    try:
        proc = subprocess.run(
            ["bash", str(path), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(AMMO),
            env=env,
        )
        return {
            "ok": proc.returncode == 0,
            "rc": proc.returncode,
            "stdout": (proc.stdout or "").strip()[-4000:],
            "stderr": (proc.stderr or "").strip()[-500:],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "script": script}


def _tail_log(path: Path, *, limit: int = 8) -> list[str]:
    if not path.is_file():
        alt = Path.home() / f".ammo-{path.name}"
        path = alt if alt.is_file() else path
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return lines[-limit:]


def _c2_witness() -> dict[str, Any]:
    monster = NEXUS_STATE / "field-monster-monitor-panel.json"
    boot = NEXUS_STATE / "hostess7-boot-last.json"
    out: dict[str, Any] = {"monster_panel": monster.is_file(), "boot_last": boot.is_file()}
    if boot.is_file():
        try:
            doc = json.loads(boot.read_text(encoding="utf-8"))
            out["boot_ok"] = doc.get("ok")
        except (OSError, json.JSONDecodeError):
            pass
    return out


def build() -> dict[str, Any]:
    net = _run_module("sg_net_harden.sh", "status")
    watch = _run_module("ammo_watch.sh", "status")
    ingress = _run_module("sg_ingress_clasp.sh", "status")
    services = _run_module("sg_service_cleaner.sh", "status")
    guard = _run_module("interface_guard.sh", "status")

    violations = _tail_log(STATE / "violations.log")
    health = _tail_log(STATE / "health.log")

    doc = {
        "schema": "ammo-net-health/v1",
        "ts": _now(),
        "ok": True,
        "loopback_only": True,
        "state_dir": str(STATE),
        "modules": {
            "net_harden": net,
            "ammo_watch": watch,
            "ingress_clasp": ingress,
            "service_cleaner": services,
            "interface_guard": guard,
        },
        "violations_tail": violations,
        "health_tail": health,
        "c2": _c2_witness(),
        "commands": {
            "status": "bash ammosecurity/modules/sg_net_harden.sh status",
            "watch_once": "bash ammosecurity/modules/ammo_watch.sh once",
            "watch_start": "bash ammosecurity/modules/ammo_watch.sh start",
        },
    }
    try:
        PANEL_CACHE.parent.mkdir(parents=True, exist_ok=True)
        tmp = PANEL_CACHE.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL_CACHE)
    except OSError:
        pass
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: ammo-net-health.py [json|panel]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())