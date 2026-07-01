#!/usr/bin/env pythong
"""Score engine bridge — Rust NexusCore when NEXUS_RUST_CORE=1, else Python fallback."""
from __future__ import annotations

import json
import os
import sys
from typing import Any

HEAT_CRUSH = float(os.environ.get("NEXUS_HEAT_CRUSH_THRESHOLD", "0.7"))
_RUST = None


def _rust_core():
    global _RUST
    if _RUST is not None:
        return _RUST
    if os.environ.get("NEXUS_RUST_CORE", "0") != "1":
        _RUST = False
        return _RUST
    try:
        import nexus_core  # type: ignore

        _RUST = nexus_core.NexusCore()
    except ImportError:
        _RUST = False
    return _RUST


def score_ip(ip: str, axes: list[float]) -> dict[str, Any]:
    core = _rust_core()
    if core:
        heat = float(core.score(ip, axes))
        crush = heat >= HEAT_CRUSH
        return {"engine": "rust", "ip": ip, "heat": heat, "auto_crush": crush}
    if not axes:
        return {"engine": "python", "ip": ip, "heat": 0.0, "auto_crush": False}
    heat = sum(axes) / (len(axes) * 10.0)
    return {
        "engine": "python",
        "ip": ip,
        "heat": heat,
        "auto_crush": heat >= HEAT_CRUSH,
    }


def main() -> int:
    if len(sys.argv) < 4:
        print(json.dumps({"error": "usage: score-engine-bridge.py score IP JSON_AXES"}, ensure_ascii=False))
        return 1
    axes = json.loads(sys.argv[3])
    if not isinstance(axes, list):
        axes = []
    print(json.dumps(score_ip(sys.argv[2], [float(x) for x in axes]), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
