#!/usr/bin/env pythong
"""Probe Queen world / panel / training / RTX for Pages bridge + C2."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL / "Queen"))


def _up(url: str, *, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return 200 <= resp.status < 400
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def probe_json() -> dict[str, Any]:
    world_port = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    panel_port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    train_port = int(os.environ.get("H7_TRAINING_VIEWER_PORT", "9488"))
    shell = f"http://127.0.0.1:{world_port}/world/browser.html"
    rtx_bin = QUEEN / "build" / "rtx" / "bin" / "Linux" / "queen-browser"
    rtx_ready = rtx_bin.is_file() and os.access(rtx_bin, os.X_OK)
    world_ok = _up(f"http://127.0.0.1:{world_port}/api/status?fast=1")
    panel_ok = _up(f"http://127.0.0.1:{panel_port}/field")
    training_ok = _up(f"http://127.0.0.1:{train_port}/api/health")
    engine = "queen-rtx" if rtx_ready and world_ok else ("queen-world" if world_ok else "offline")
    return {
        "ok": True,
        "schema": "queen-loopback-probe/v1",
        "shell": shell,
        "world": f"http://127.0.0.1:{world_port}",
        "queen": world_ok,
        "world_ok": world_ok,
        "panel": panel_ok,
        "training": training_ok,
        "rtx": rtx_ready,
        "rtx_binary": str(rtx_bin) if rtx_ready else None,
        "engine": engine,
    }


def main() -> int:
    print(json.dumps(probe_json(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())