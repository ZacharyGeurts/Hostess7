#!/usr/bin/env pythong
"""AMOURANTHRTX bridge stub — shared FieldX86 state + entropy into OODA scoring."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from hostess7.paths import hostess7_root, nexus_install_root


def _fabric_path() -> Path:
    root = hostess7_root()
    candidates = [
        root / "brain" / "state" / "amouranth_fabric.json",
        nexus_install_root() / ".nexus-state" / "amouranth-fabric.json",
        Path(os.environ.get("AMOURANTHRTX_ROOT", "")) / "brain" / "fieldx86-fabric.json",
    ]
    for c in candidates:
        if c.is_file():
            return c
    return candidates[0]


def read_shared_state() -> dict[str, Any]:
    path = _fabric_path()
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "hostess7-amouranth-bridge/v1",
        "fabric": "FieldX86-memory-stub",
        "connected": False,
        "entropy_seed": int(time.time()) % 9973,
    }


def entropy_for_ooda() -> float:
    """Inject host-bound entropy into OODA threat scoring (0.0–0.25)."""
    state = read_shared_state()
    seed = str(state.get("entropy_seed") or time.time())
    host = os.environ.get("HOSTNAME", "hostess7")
    digest = hashlib.sha256(f"{seed}:{host}:ooda".encode()).hexdigest()
    return (int(digest[:4], 16) % 250) / 1000.0


def bridge_status() -> dict[str, Any]:
    state = read_shared_state()
    return {
        "ok": True,
        "schema": "hostess7-amouranth-bridge-status/v1",
        "root": str(hostess7_root()),
        "fabric_path": str(_fabric_path()),
        "entropy": entropy_for_ooda(),
        "state": state,
        "rtx_env": os.environ.get("AMOURANTHRTX_ROOT", ""),
    }


def main() -> int:
    import sys

    print(json.dumps(bridge_status(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())