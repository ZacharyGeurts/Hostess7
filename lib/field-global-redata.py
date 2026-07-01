#!/usr/bin/env pythong
"""Incremental global redata — chunked plate/state refresh; never monolithic blast."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
PANEL = STATE / "field-global-redata.json"

# Regions touched per incremental pass (light plates — not full meld)
REDATA_REGIONS = (
    "iron-plate-panel.json",
    "connection-gatekeeper-panel.json",
    "nexus-logic-gate-runtime.json",
    "field-port-ddos-panel.json",
    "znetwork-status.json",
    "field-switch-safety.json",
    "field-thermal-guard.json",
)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_guard_module():
    path = INSTALL / "lib" / "field-thermal-guard.py"
    spec = importlib.util.spec_from_file_location("field_thermal_guard_redata", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _touch_region(name: str, offset: int, count: int) -> dict[str, Any]:
    """Bounded redata stub — verify region exists or write minimal receipt."""
    path = STATE / name
    if path.is_file():
        try:
            st = path.stat()
            return {"region": name, "ok": True, "bytes": st.st_size, "offset": offset, "count": count}
        except OSError:
            pass
    stub = {
        "schema": "field-global-redata-stub/v1",
        "region": name,
        "offset": offset,
        "ts": _now(),
        "ok": True,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stub, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"region": name, "ok": True, "created": True, "offset": offset}


def incremental_redata(*, boot_test: bool = False) -> dict[str, Any]:
    mod = _load_guard_module()
    if mod is None:
        return {"ok": False, "error": "field-thermal-guard missing"}
    guard = mod.FieldThermalGuard()
    regions = list(REDATA_REGIONS)
    if boot_test:
        regions = regions[:3]

    results: list[dict[str, Any]] = []

    def _chunk(offset: int, count: int) -> None:
        for i in range(offset, min(offset + count, len(regions))):
            results.append(_touch_region(regions[i], offset, count))

    stats = guard.safe_global_redata(len(regions), _chunk)
    doc = {
        "schema": "field-global-redata/v1",
        "ts": _now(),
        "ok": True,
        "boot_test": boot_test,
        "incremental": True,
        "monolithic_blast": False,
        "regions": len(regions),
        "stats": stats,
        "results": results,
        "headroom_pct": round(guard.headroom_pct(), 1),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    PANEL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "incremental"):
        print(json.dumps(incremental_redata(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "boot-test":
        print(json.dumps(incremental_redata(boot_test=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-global-redata.py [json|incremental|boot-test]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())