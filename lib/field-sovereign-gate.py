#!/usr/bin/env pythong
"""Sovereign security gate — DNS, DHCP, NTP tied to cycle + derived time.

Never lose a cycle. Sonic, RF, SQUIDGIE — threats log; time continues from monotonic anchor.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))

_SOVEREIGN: Any = None


def _sovereign() -> Any:
    global _SOVEREIGN
    if _SOVEREIGN is not None:
        return _SOVEREIGN
    py = INSTALL / "lib" / "sovereign-time.py"
    spec = importlib.util.spec_from_file_location("sovereign_time_gate", py)
    if not spec or not spec.loader:
        raise ImportError("sovereign-time.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _SOVEREIGN = mod
    return mod


def gate(*, service: str, action: str = "serve") -> dict[str, Any]:
    """Unified gate for DNS · DHCP · NTP — always returns time, always advances cycle."""
    return _sovereign().cycle_gate(service=service, action=action)


def derived_utc() -> str:
    return _sovereign().derived_utc()


def status() -> dict[str, Any]:
    st = _sovereign()
    doc = st.status()
    doc["gate"] = {
        "schema": "field-sovereign-gate/v1",
        "never_lose_cycle": True,
        "services": ["dns", "dhcp", "ntp", "sovereign"],
        "policy": "Threats log — sonic/RF/SQUIDGIE never stop derived time",
    }
    doc["cycle"] = st.cycle_status()
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "gate" and len(sys.argv) > 2:
        svc = sys.argv[2]
        act = sys.argv[3] if len(sys.argv) > 3 else "serve"
        print(json.dumps(gate(service=svc, action=act), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-sovereign-gate.py [json|gate <service> [action]]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())