#!/usr/bin/env pythong
"""Iron plate spot detector — find meld attachment points without heating the host.

Low-power default: cache-first, cool_sort, thermal gate before any heavy import.
Slower is fine when it cuts joules — never bench radix or live bridge under heat.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "iron-plate-spot-doctrine.json"
PANEL = STATE / "iron-plate-spot-panel.json"
RUNTIME = STATE / "iron-plate-spot-runtime.json"
LOW_POWER = os.environ.get("NEXUS_PLATE_SPOT_LOW_POWER", "1") == "1"
ENABLED = os.environ.get("NEXUS_IRON_PLATE_SPOT", "1") == "1"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = INSTALL / "lib" / "sovereign-clock.py"
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


def low_power_mode() -> bool:
    return LOW_POWER


def _thermal_gate_light(*, ops: int = 1) -> dict[str, Any]:
    """Cache-only spot scan — headroom only; never block on missing sanity panels."""
    thermal = _load(STATE / "field-thermal-guard.json", {})
    advisory = _load(STATE / "thermal-advisory.json", {})
    headroom = float(thermal.get("headroom_pct") or 100)
    level = str(advisory.get("level") or thermal.get("level") or "ok").lower()
    allow = headroom >= 12 and level not in ("crit", "storm")
    try:
        tg = INSTALL / "lib" / "field-thermal-guard.py"
        if tg.is_file():
            spec = importlib.util.spec_from_file_location("ftg_spot", tg)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "FieldThermalGuard"):
                    guard = mod.FieldThermalGuard()
                    allow = allow and guard.allow_update(max(1, min(ops, 2)))
    except Exception:
        pass
    return {
        "ok": allow,
        "light_gate": True,
        "allow_plate_work": allow,
        "thermal_headroom_pct": headroom,
        "thermal_level": level,
        "ops_requested": max(1, min(ops, 2)),
        "low_power": LOW_POWER,
        "doctrine": "Light gate — cache-only spot reads; no meld imports, no sanity panel required",
    }


def thermal_gate(*, ops: int = 1) -> dict[str, Any]:
    """Gate plate spot scans — light gate when low_power; full gate only for heavy passes."""
    requested = max(1, ops)
    if LOW_POWER:
        return _thermal_gate_light(ops=requested)
    bridge = INSTALL / "lib" / "field-plate-combinatorics-bridge.py"
    if not bridge.is_file():
        return _thermal_gate_light(ops=requested)
    try:
        spec = importlib.util.spec_from_file_location("comb_spot_gate", bridge)
        if not spec or not spec.loader:
            return _thermal_gate_light(ops=requested)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "thermal_entropy_gate"):
            out = mod.thermal_entropy_gate(ops=requested)
            if not out.get("ok"):
                return _thermal_gate_light(ops=requested)
            out["low_power"] = False
            return out
    except Exception:
        pass
    return _thermal_gate_light(ops=requested)


def _cool_sort_spots(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ascending thermo_proxy — coolest meld spots first (lower power)."""
    return sorted(
        rows,
        key=lambda r: (
            float(r.get("thermo_proxy") or r.get("heat_cost") or 0),
            -float(r.get("priority") or 0),
            str(r.get("id") or ""),
        ),
    )


def _spot_from_condense(group: dict[str, Any]) -> dict[str, Any]:
    gid = str(group.get("group") or group.get("id") or "condense")
    present = int(group.get("present") or group.get("total") or 0)
    return {
        "id": f"condense:{gid}",
        "kind": "combinatorics_condense",
        "label": gid,
        "priority": float(present),
        "thermo_proxy": 0.15 if group.get("condensed") else 0.35,
        "heat_cost": 0.2,
        "live": bool(group.get("condensed") or present),
        "consumer": "combinatorics_bridge",
    }


def _chain_node_live(node: dict[str, Any]) -> bool:
    if node.get("live") is not None:
        return bool(node.get("live"))
    nid = str(node.get("id") or "")
    mod_path = str(node.get("module") or "")
    if nid == "browser_display":
        return True
    if mod_path.startswith("Grok16/"):
        return (GROK16 / mod_path.replace("Grok16/", "", 1)).is_file()
    if mod_path:
        return (INSTALL / mod_path).is_file()
    if nid == "ironclad":
        return (INSTALL / "lib" / "ironclad-immediate.py").is_file()
    return False


def _spot_from_chain_node(node: dict[str, Any]) -> dict[str, Any]:
    nid = str(node.get("id") or "node")
    return {
        "id": f"chain:{nid}",
        "kind": "ironclad_chain",
        "label": nid,
        "priority": 8.0 if nid in ("ironclad", "combinatorics_bridge", "c2_taskbar") else 5.0,
        "thermo_proxy": 0.1 if nid == "browser_display" else 0.25,
        "heat_cost": 0.12 if node.get("display_only") else 0.28,
        "live": _chain_node_live(node),
        "module": node.get("module"),
        "consumer": node.get("consumer"),
    }


def _spot_from_connection(conn: dict[str, Any], *, max_storm: bool = False) -> dict[str, Any] | None:
    if max_storm and conn.get("storm"):
        return None
    load = int(conn.get("load") or 0)
    storm = bool(conn.get("storm"))
    thermo = min(1.0, 0.08 + load / 512.0 + (0.4 if storm else 0.0))
    return {
        "id": f"iron:{conn.get('id') or conn.get('label')}",
        "kind": "operator_iron_plate",
        "label": str(conn.get("label") or conn.get("id") or "—"),
        "bus": conn.get("bus"),
        "priority": float(255 - int(conn.get("quality") or 128)),
        "thermo_proxy": thermo,
        "heat_cost": thermo,
        "live": True,
        "board_direct": bool(conn.get("board_direct")),
        "storm": storm,
    }


def _spot_from_organize_surface(surface: dict[str, Any]) -> dict[str, Any]:
    sid = str(surface.get("id") or "surface")
    return {
        "id": f"surface:{sid}",
        "kind": "organize_surface",
        "label": sid,
        "priority": float(surface.get("priority") or 4),
        "thermo_proxy": 0.18,
        "heat_cost": 0.15,
        "live": bool(surface.get("iron_plate_sorted") or surface.get("ok")),
    }


def find_spots(*, allow_stale: bool = True, max_iron_connections: int | None = None) -> dict[str, Any]:
    """Discover plate meld spots from caches — gated, low-power, cool_sorted."""
    t0 = time.perf_counter()
    gate = thermal_gate(ops=1 if LOW_POWER else 3)
    if not gate.get("ok"):
        cached = _load(PANEL, {})
        if cached and allow_stale:
            cached["thermal_deferred"] = True
            cached["gate"] = gate
            cached["posture"] = "Hot — serving last-good plate spots (zero scan joules)"
            return cached
        return {
            "ok": False,
            "schema": "iron-plate-spot/v1",
            "error": "thermal_entropy_gate",
            "gate": gate,
            "low_power": LOW_POWER,
        }

    doctrine = _load(DOCTRINE, {})
    organize_doc = _load(STATE / "iron-plate-organize-panel.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    iron = _load(STATE / "field-operator-iron-plate.json", {})
    ironclad = _load(STATE / "ironclad-immediate.json", {}) or _load(STATE / "ironclad-plate.json", {})
    chain_doc = organize_doc.get("ironclad_chain") or _load(INSTALL / "data" / "iron-plate-organize-doctrine.json", {}).get("ironclad_chain") or {}

    spots: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _add(sp: dict[str, Any] | None) -> None:
        if not sp:
            return
        sid = str(sp.get("id") or "")
        if not sid or sid in seen:
            return
        seen.add(sid)
        spots.append(sp)

    for node in chain_doc.get("tree") or organize_doc.get("ironclad_chain", {}).get("connections") or []:
        _add(_spot_from_chain_node(node))

    for group in (bridge.get("plate_condense") or {}).get("groups") or organize_doc.get("condense_groups") or []:
        _add(_spot_from_condense(group))

    surfaces = (organize_doc.get("surfaces") or {})
    for key, surf in surfaces.items():
        if isinstance(surf, dict):
            _add(_spot_from_organize_surface({**surf, "id": key}))

    cap = max_iron_connections
    if cap is None:
        cap = 8 if LOW_POWER else 24
    for conn in (iron.get("connections") or [])[:cap]:
        _add(_spot_from_connection(conn, max_storm=LOW_POWER))

    for tool in doctrine.get("spot_sources") or []:
        rel = str(tool.get("panel") or "")
        if not rel:
            continue
        doc = _load(STATE / rel, {})
        if doc.get("ok") is False:
            continue
        _add({
            "id": f"tool:{tool.get('id')}",
            "kind": "organizational_tool",
            "label": str(tool.get("id")),
            "priority": 6.0,
            "thermo_proxy": 0.22,
            "heat_cost": 0.2,
            "live": bool(doc.get("ok") or doc.get("plated")),
            "panel": rel,
        })

    sorted_spots = _cool_sort_spots(spots)
    live_n = sum(1 for s in sorted_spots if s.get("live"))
    sealed = bool(ironclad.get("ironclad_sealed") or ironclad.get("realized"))
    doctrine_realized = bool(_load(INSTALL / "data" / "ironclad-doctrine.json", {}).get("immutability", {}).get("realized"))
    sealed = sealed or doctrine_realized
    elapsed = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "schema": "iron-plate-spot/v1",
        "updated": _now(),
        "ok": ENABLED and (live_n > 0 or len(sorted_spots) > 0),
        "enabled": ENABLED,
        "low_power": LOW_POWER,
        "thermal_gate": gate,
        "ironclad_sealed": sealed,
        "ironclad_grounded": bool(
            ironclad.get("plate_to_sense", {}).get("ironclad_grounded") or sealed
        ),
        "spot_count": len(sorted_spots),
        "spots_live": live_n,
        "spots": sorted_spots,
        "top_spots": [s.get("id") for s in sorted_spots[:8]],
        "coolest_spot": sorted_spots[0].get("id") if sorted_spots else None,
        "organize_gain": organize_doc.get("organize_gain"),
        "replate_recommended": organize_doc.get("replate_recommended"),
        "scan": {"elapsed_ms": elapsed, "cache_only": True, "max_iron_connections": cap},
        "posture": (
            f"Low-power spot detect — {live_n}/{len(sorted_spots)} live · "
            f"cool_sort · {elapsed:.1f}ms · gate ok"
        ),
        "motto": doctrine.get("motto"),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = find_spots(allow_stale=True)
    if write and doc.get("ok") is not False:
        _save(PANEL, doc)
        _save(
            RUNTIME,
            {
                "schema": "iron-plate-spot-runtime/v1",
                "updated": doc.get("updated"),
                "ok": doc.get("ok"),
                "spot_count": doc.get("spot_count"),
                "spots_live": doc.get("spots_live"),
                "low_power": doc.get("low_power"),
                "coolest_spot": doc.get("coolest_spot"),
            },
        )
    return doc


def slice_for_organize() -> dict[str, Any]:
    doc = _load(PANEL, {}) or build_panel(write=False)
    return {
        "ok": doc.get("ok"),
        "spot_count": doc.get("spot_count"),
        "spots_live": doc.get("spots_live"),
        "top_spots": doc.get("top_spots"),
        "coolest_spot": doc.get("coolest_spot"),
        "low_power": doc.get("low_power"),
        "thermal_deferred": doc.get("thermal_deferred"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=True), ensure_ascii=False))
        return 0
    if cmd in ("detect", "find", "spots"):
        print(json.dumps(find_spots(), ensure_ascii=False))
        return 0
    if cmd == "gate":
        print(json.dumps(thermal_gate(ops=2), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: iron-plate-spot-detector.py [json|detect|gate]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())