#!/usr/bin/env pythong
"""Hostess7 core supervisor — single identity, owns boot + web + status."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from hostess7 import __version__
from hostess7.paths import brain_state_dir, hostess7_root, packaged_context, scripts_available, scripts_dir
from hostess7.state import snapshot, status as state_status


def _ping(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return 200 <= getattr(resp, "status", 200) < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def stack_status() -> dict[str, Any]:
    os.environ.setdefault("HOSTESS7_WAR_PROFILE", "1")
    port_web = int(os.environ.get("HOSTESS7_WEB_PORT", "8080"))
    port_panel = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    port_queen = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    web = _ping(f"http://127.0.0.1:{port_web}/health")
    brain_api = _ping(f"http://127.0.0.1:{port_web}/api/status")
    panel = _ping(f"http://127.0.0.1:{port_panel}/field")
    queen = _ping(f"http://127.0.0.1:{port_queen}/api/status")
    st = state_status()
    war_profile = os.environ.get("HOSTESS7_WAR_PROFILE", os.environ.get("HOSTESS7_LICENSE_MODE", "")).lower() in (
        "war", "1", "true", "high_vigilance",
    )
    return {
        "ok": True,
        "schema": "hostess7-core/v1",
        "identity": "Hostess7",
        "version": __version__,
        "root": str(hostess7_root()),
        "state": st,
        "context": packaged_context(),
        "services": {
            "web": web,
            "brain_api": brain_api,
            "panel": panel,
            "queen": queen,
        },
        "ports": {"web": port_web, "panel": port_panel, "queen": port_queen},
        "posture": "war-ready" if war_profile else "operational",
        "war_profile": war_profile,
    }


def start(*, low_power: bool = False) -> dict[str, Any]:
    brain_state_dir()
    root = hostess7_root()
    if not scripts_available():
        return {
            "ok": False,
            "error": "scripts_unavailable",
            "detail": "Set HOSTESS7_ROOT to git clone or use ./Hostess7.sh boot",
            "context": packaged_context(),
        }
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
    from hostess7.cohesion import benchmark_iq, validate_truth  # noqa: WPS433

    core = stack_status()
    iq = benchmark_iq()
    truth = validate_truth()
    war: dict[str, Any] = {"ok": False, "skipped": True}
    if scripts_available():
        war_run = subprocess.run(
            [sys.executable, str(scripts_dir() / "field_warfare_realism.py"), "panel"],
            cwd=str(hostess7_root()),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if war_run.returncode == 0 and war_run.stdout.strip():
            try:
                war = json.loads(war_run.stdout)
            except json.JSONDecodeError:
                war = {"ok": False, "error": "parse_failed"}
    return {
        "ok": True,
        "schema": "hostess7-brain/v2",
        "version": __version__,
        "core": core,
        "cohesion": {"iq": iq, "truth": truth},
        "war_realism": war,
        "endpoints": {
            "status": "/api/status/full",
            "brain": "/api/brain",
            "war_train": "/api/war-train",
            "protect_friendlies": "/api/protect-friendlies",
            "ask": "/api/ask",
            "reflect": "/api/reflect",
            "teach": "/api/teach",
        },
    }


def _cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hostess7-core", description="Hostess7 2.0.7e core CLI")
    p.add_argument("command", nargs="?", default="status", choices=["status", "json", "start", "boot", "brain", "cohesion"])
    p.add_argument("--low-power", action="store_true")
    return p


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] not in ("status", "json", "start", "boot", "brain", "cohesion") and sys.argv[1].startswith("-"):
        args = _cli().parse_args()
        cmd = args.command
    else:
        cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
        args = argparse.Namespace(low_power=os.environ.get("HOSTESS7_LOW_POWER", "0") in ("1", "true", "yes"))

    if cmd in ("status", "json"):
        print(json.dumps(stack_status(), indent=2))
        return 0
    if cmd in ("start", "boot"):
        doc = start(low_power=args.low_power)
        print(json.dumps(doc, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "brain":
        print(json.dumps(brain_api_payload(), indent=2))
        return 0
    if cmd == "cohesion":
        from hostess7.cohesion import benchmark_iq, validate_truth  # noqa: WPS433

        print(json.dumps({"iq": benchmark_iq(), "truth": validate_truth()}, indent=2))
        return 0
    print(json.dumps({"error": "usage: hostess7-core [status|start|brain|cohesion]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())