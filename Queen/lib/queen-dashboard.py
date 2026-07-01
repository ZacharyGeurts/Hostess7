#!/usr/bin/env pythong
"""Queen Dashboard — legacy alias for programmatic NEXUS C2 panels."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]


def _nexus_c2_mod() -> Any:
    path = Path(__file__).resolve().parent / "queen-nexus-c2.py"
    spec = importlib.util.spec_from_file_location("queen_nexus_c2_bridge", path)
    if not spec or not spec.loader:
        raise ImportError("queen-nexus-c2.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def dashboard_posture(*, flyout: bool = False) -> dict[str, Any]:
    return _nexus_c2_mod().nexus_c2_posture(flyout=flyout, legacy_schema="queen-dashboard/v1")


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "posture"):
        return {"ok": True, **dashboard_posture()}
    if action in ("flyout", "flyout_screens"):
        return {"ok": True, **dashboard_posture(flyout=True)}
    if action == "g16_check":
        g16 = _g16_posture()
        ok = g16.get("ready") and bool(g16.get("field_opt_defs"))
        return {"ok": ok, "g16": g16, "verdict": "G16_FIELD_OPT_READY" if ok else "G16_CHECK_HOLD"}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(dashboard_posture(), ensure_ascii=False))
        return 0
    if cmd == "flyout":
        print(json.dumps(dashboard_posture(flyout=True), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(dispatch({"action": cmd}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())