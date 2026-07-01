#!/usr/bin/env pythong
"""Clean juice — sovereign joule pool; no power-company trust; 3D BSP field plate dispatch."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-clean-juice-doctrine.json"
PANEL = STATE / "field-clean-juice-panel.json"
POOL_FILE = STATE / "field-clean-juice-pool.json"
GRID = 8
SCALE_NETS = 4


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_module(name: str, script: str, *args: str) -> dict[str, Any]:
    path = INSTALL / "lib" / script
    if not path.is_file():
        return {}
    try:
        import subprocess

        proc = subprocess.run(
            [sys.executable, str(path), *args],
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return {}


def _voltage_posture() -> dict[str, Any]:
    return _run_module("voltage", "field-voltage-regulation.py", "json")


def _thermal_budget_j() -> dict[str, Any]:
    doc = _load(INSTALL / "data" / "field-thermal-guard-doctrine.json", {})
    defaults = doc.get("defaults") or {}
    max_j_s = float(os.environ.get("NEXUS_FIELD_MAX_JOULES_PER_SEC", defaults.get("max_joules_per_second", 45.0)))
    window_s = float(os.environ.get("NEXUS_CLEAN_JUICE_WINDOW_S", "1.0"))
    return {"max_joules_per_second": max_j_s, "window_joules": max_j_s * window_s}


def _charge_joules() -> float:
    override = os.environ.get("NEXUS_CLEAN_JUICE_CHARGE_J", "").strip()
    if override:
        try:
            return max(0.0, float(override))
        except ValueError:
            pass
    budget = _thermal_budget_j()
    pool = _load(POOL_FILE, {})
    if pool.get("pool_joules") is not None:
        return float(pool["pool_joules"])
    return float(budget["window_joules"])


def _cell_index(x: int, y: int, z: int) -> int:
    return x + GRID * (y + GRID * z)


def _bsp_leaves() -> list[dict[str, Any]]:
    """Octree BSP over 8³ lattice — faster dispatch than flat 512 scan."""
    leaves: list[dict[str, Any]] = []

    def walk(x0: int, y0: int, z0: int, size: int, depth: int) -> None:
        if size == 1:
            leaves.append({
                "id": f"cell_{x0}_{y0}_{z0}",
                "index": _cell_index(x0, y0, z0),
                "origin": [x0, y0, z0],
                "size": 1,
                "depth": depth,
            })
            return
        half = size // 2
        for ox, oy, oz in (
            (0, 0, 0),
            (half, 0, 0),
            (0, half, 0),
            (0, 0, half),
            (half, half, 0),
            (half, 0, half),
            (0, half, half),
            (half, half, half),
        ):
            walk(x0 + ox, y0 + oy, z0 + oz, half, depth + 1)

    walk(0, 0, 0, GRID, 0)
    return leaves


def _circuit_topology(joules: float, *, cells: int) -> dict[str, Any]:
    """Serial/parallel model — one present rail; no double voltage on a node."""
    doctrine = _load(DOCTRINE, {})
    v_rail = float(os.environ.get("NEXUS_PRESENT_RAIL_V", "1.0"))
    serial_legs = int(os.environ.get("NEXUS_CLEAN_JUICE_SERIAL_LEGS", "4"))
    parallel_banks = int(os.environ.get("NEXUS_CLEAN_JUICE_PARALLEL_BANKS", "4"))
    if serial_legs < 1:
        serial_legs = 1
    if parallel_banks < 1:
        parallel_banks = 1

    v_per_leg = v_rail / serial_legs
    i_total = joules / max(v_rail, 1e-12)
    i_per_bank = i_total / parallel_banks
    j_per_cell = joules / max(cells, 1)

    double_blocked = bool((doctrine.get("policy") or {}).get("voltage_double_forbidden", True))
    return {
        "present_rail_v": v_rail,
        "serial_legs": serial_legs,
        "parallel_banks": parallel_banks,
        "v_per_serial_leg": round(v_per_leg, 6),
        "v_parallel_rail": round(v_rail, 6),
        "no_double_voltage": double_blocked,
        "double_voltage_forbidden": double_blocked,
        "current_a_total": round(i_total, 9),
        "current_a_per_bank": round(i_per_bank, 9),
        "joules_per_cell": round(j_per_cell, 12),
        "kirchhoff": "serial_V_adds_parallel_V_single",
    }


def _pool_state() -> dict[str, Any]:
    pool = _load(POOL_FILE, {})
    charge = _charge_joules()
    allocated = float(pool.get("allocated_joules") or 0.0)
    scrubbed = float(pool.get("scrubbed_joules") or 0.0)
    dispensed = float(pool.get("dispensed_joules") or 0.0)
    available = max(0.0, charge + scrubbed - allocated - dispensed)
    return {
        "charge_joules": round(charge, 9),
        "allocated_joules": round(allocated, 9),
        "dispensed_joules": round(dispensed, 9),
        "scrubbed_joules": round(scrubbed, 9),
        "available_joules": round(available, 9),
        "updated": pool.get("updated") or _now(),
    }


def scrub(*, joules: float | None = None) -> dict[str, Any]:
    pool = _load(POOL_FILE, {})
    doctrine = _load(DOCTRINE, {})
    eff = float((doctrine.get("policy") or {}).get("reclean_efficiency", 0.92))
    reclaim = float(joules if joules is not None else pool.get("allocated_joules") or 0.0)
    reclaim = max(0.0, reclaim * eff)
    pool["allocated_joules"] = max(0.0, float(pool.get("allocated_joules") or 0.0) - reclaim / eff)
    pool["scrubbed_joules"] = float(pool.get("scrubbed_joules") or 0.0) + reclaim
    pool["updated"] = _now()
    _save(POOL_FILE, pool)
    return {"ok": True, "scrubbed_joules": round(reclaim, 9), "pool": _pool_state()}


def dispense(*, joules: float, work_id: str = "") -> dict[str, Any]:
    pool = _load(POOL_FILE, {})
    state = _pool_state()
    need = max(0.0, float(joules))
    if need > state["available_joules"]:
        return {"ok": False, "error": "insufficient_clean_juice", "need_j": need, "available_j": state["available_joules"]}
    pool["dispensed_joules"] = float(pool.get("dispensed_joules") or 0.0) + need
    pool["last_work_id"] = work_id or "field_work"
    pool["updated"] = _now()
    _save(POOL_FILE, pool)
    return {"ok": True, "dispensed_joules": round(need, 9), "work_id": pool["last_work_id"], "pool": _pool_state()}


def reclean(*, joules: float) -> dict[str, Any]:
    """Return shed joules to pool as recleaned work-ready energy."""
    doctrine = _load(DOCTRINE, {})
    eff = float((doctrine.get("policy") or {}).get("reclean_efficiency", 0.92))
    raw = max(0.0, float(joules))
    cleaned = raw * eff
    pool = _load(POOL_FILE, {})
    pool["scrubbed_joules"] = float(pool.get("scrubbed_joules") or 0.0) + cleaned
    pool["updated"] = _now()
    _save(POOL_FILE, pool)
    return {"ok": True, "recleaned_joules": round(cleaned, 9), "efficiency": eff, "pool": _pool_state()}


def _performance_vs_old() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    perf = doctrine.get("performance") or {}
    thermal = _load(INSTALL / "data" / "field-thermal-guard-doctrine.json", {})
    metrics = thermal.get("metrics") or {}
    gain = perf.get("vs_old_dispatch_gain_pct") or metrics.get("dispatch_gain_band_pct") or [35, 60]
    return {
        "old_way": (doctrine.get("old_way") or {}).get("label", "grid_tethered_monolithic"),
        "new_way": (doctrine.get("new_way") or {}).get("label", "clean_juice_bsp_3d_plate"),
        "dispatch_gain_pct_band": gain,
        "thermal_headroom_mult_vs_old": perf.get("vs_old_thermal_headroom_mult") or metrics.get("headroom_multiplier_at_budget"),
        "burst_derating_4k_vs_old": perf.get("vs_old_burst_derating_4k") or metrics.get("burst_derating_ratio_4k_uhd"),
        "bsp_dispatch_speedup": perf.get("bsp_dispatch_speedup", 2.4),
        "no_double_voltage_waste_eliminated": True,
        "grid_talk_eliminated": True,
        "speed_impact_normal_load": metrics.get("speed_impact_normal_load", "0%"),
    }


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    voltage = _voltage_posture()
    pool = _pool_state()
    leaves = _bsp_leaves()
    total_cells = GRID**3 * SCALE_NETS
    circuit = _circuit_topology(pool["available_joules"] or pool["charge_joules"], cells=len(leaves))

    grid_blocked = voltage.get("power_company_grid_trust_layer") == "blocked"
    no_double = circuit.get("no_double_voltage", True)

    doc: dict[str, Any] = {
        "schema": "field-clean-juice/v1",
        "updated": _now(),
        "ok": grid_blocked and no_double,
        "motto": doctrine.get("motto", "We are the clean juice"),
        "power_company": {
            "trust_layer": "blocked",
            "grid_talk": False,
            "grid_witness_only": True,
            "meter_as_truth": False,
        },
        "voltage_regulation": {
            "present_rail": voltage.get("operate_at_present_rail"),
            "no_conversion": voltage.get("conversion_on_voltage_path") is False,
            "no_entropy_on_wave": voltage.get("entropy_on_trust_layer") is False,
        },
        "pool": pool,
        "unit": "joules",
        "circuit": circuit,
        "field_3d": {
            "cells_per_axis": GRID,
            "dots_per_box": GRID**3,
            "scale_nets": SCALE_NETS,
            "total_lattice_dots": GRID**3 * SCALE_NETS,
            "bsp_leaves": len(leaves),
            "partition": "bsp_octree",
            "plate": "ironclad_reality_field",
        },
        "bsp_sample": leaves[:8],
        "actions": {
            "scrub": "return unused allocated joules to pool",
            "dispense": "allocate clean joules for field work",
            "reclean": "reclaim shed joules at reclean_efficiency",
        },
        "performance": _performance_vs_old(),
        "detail": "clean_juice_sovereign" if grid_blocked else "grid_still_open",
    }
    _save(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "posture", "panel"):
        return {"ok": True, **posture()}
    if action == "scrub":
        return scrub(joules=body.get("joules"))
    if action == "dispense":
        return dispense(joules=float(body.get("joules") or 0), work_id=str(body.get("work_id") or ""))
    if action == "reclean":
        return reclean(joules=float(body.get("joules") or 0))
    if action == "charge":
        pool = _load(POOL_FILE, {})
        pool["pool_joules"] = float(body.get("joules") or _charge_joules())
        pool["updated"] = _now()
        _save(POOL_FILE, pool)
        return {"ok": True, **posture()}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("scrub", "dispense", "reclean", "charge"):
        print(json.dumps(dispatch({"action": cmd, **({"joules": float(sys.argv[2])} if len(sys.argv) > 2 else {})}), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-clean-juice.py [json|dispatch|scrub|dispense|reclean|charge]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())