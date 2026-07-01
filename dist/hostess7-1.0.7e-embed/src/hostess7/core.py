#!/usr/bin/env pythong
"""Hostess7 core supervisor — single identity, owns boot + web + status."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from hostess7.paths import brain_state_dir, hostess7_root, scripts_dir
from hostess7.state import snapshot, status as state_status


def _ping(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return 200 <= getattr(resp, "status", 200) < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def stack_status() -> dict[str, Any]:
    port_web = int(os.environ.get("HOSTESS7_WEB_PORT", "8080"))
    port_panel = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    port_queen = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    web = _ping(f"http://127.0.0.1:{port_web}/health")
    brain_api = _ping(f"http://127.0.0.1:{port_web}/api/status")
    panel = _ping(f"http://127.0.0.1:{port_panel}/field")
    queen = _ping(f"http://127.0.0.1:{port_queen}/api/status")
    st = state_status()
    return {
        "ok": True,
        "schema": "hostess7-core/v1",
        "identity": "Hostess7",
        "version": "1.0.7e",
        "root": str(hostess7_root()),
        "state": st,
        "services": {
            "web": web,
            "brain_api": brain_api,
            "panel": panel,
            "queen": queen,
        },
        "ports": {"web": port_web, "panel": port_panel, "queen": port_queen},
        "posture": "war-ready",
    }


def start(*, low_power: bool = False) -> dict[str, Any]:
    brain_state_dir()
    root = hostess7_root()
    env = {
        **os.environ,
        "HOSTESS7_ROOT": str(root),
        "HOSTESS7_LOW_POWER": "1" if low_power else os.environ.get("HOSTESS7_LOW_POWER", "0"),
    }
    boot_py = scripts_dir() / "hostess7_boot.py"
    proc = subprocess.run(
        [sys.executable, str(boot_py)],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    snap = snapshot("core-start")
    doc = {
        "ok": proc.returncode == 0,
        "rc": proc.returncode,
        "snapshot": snap,
        "stack": stack_status(),
    }
    if proc.stdout:
        doc["stdout_tail"] = proc.stdout[-2000:]
    if proc.stderr:
        doc["stderr_tail"] = proc.stderr[-2000:]
    return doc


def brain_api_payload() -> dict[str, Any]:
    """Single /api/brain surface for all components."""
    from hostess7.cohesion import benchmark_iq, validate_truth  # noqa: WPS433

    core = stack_status()
    iq = benchmark_iq()
    truth = validate_truth()
    return {
        "ok": True,
        "schema": "hostess7-brain/v1",
        "core": core,
        "cohesion": {"iq": iq, "truth": truth},
        "endpoints": {
            "status": "/api/status/full",
            "ask": "/api/ask",
            "reflect": "/api/reflect",
            "teach": "/api/teach",
        },
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json"):
        print(json.dumps(stack_status(), indent=2))
        return 0
    if cmd in ("start", "boot"):
        low = os.environ.get("HOSTESS7_LOW_POWER", "0") in ("1", "true", "yes")
        doc = start(low_power=low)
        print(json.dumps(doc, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "brain":
        print(json.dumps(brain_api_payload(), indent=2))
        return 0
    print(json.dumps({"error": "usage: hostess7-core [status|start|brain]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())