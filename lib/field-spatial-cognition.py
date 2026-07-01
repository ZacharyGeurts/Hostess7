#!/usr/bin/env pythong
"""3D/4D field spatial lattice — networks-of-networks for autonomous being awareness."""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-spatial-doctrine.json"
RUNTIME = STATE / "field-spatial-runtime.json"
PANEL = STATE / "field-spatial-panel.json"
HISTORY = STATE / "field-spatial-history.jsonl"
GRID = 8
SCALE_ORDER = ("planetary", "field", "room", "body")
COUPLE_BLEED = 0.22


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


def _cell_index(x: float, y: float, z: float, *, extent: float = 1.0) -> tuple[int, int, int]:
    half = extent / 2.0

    def clamp(v: float) -> int:
        t = (v + half) / extent
        return max(0, min(GRID - 1, int(t * GRID)))

    return clamp(x), clamp(y), clamp(z)


def _empty_lattice() -> list[list[list[float]]]:
    return [[[0.0 for _ in range(GRID)] for _ in range(GRID)] for _ in range(GRID)]


def _inject_amplitude(
    lattice: list[list[list[float]]],
    *,
    norm_x: float,
    norm_y: float,
    norm_z: float,
    weight: float,
) -> None:
    ix, iy, iz = _cell_index(norm_x, norm_y, norm_z)
    lattice[ix][iy][iz] = min(1.0, lattice[ix][iy][iz] + weight)
    for dx, dy, dz in ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)):
        nx, ny, nz = ix + dx, iy + dy, iz + dz
        if 0 <= nx < GRID and 0 <= ny < GRID and 0 <= nz < GRID:
            lattice[nx][ny][nz] = min(1.0, lattice[nx][ny][nz] + weight * 0.35)


def _peak_cell(lattice: list[list[list[float]]]) -> dict[str, Any]:
    best_i, best_j, best_k, best_v = 0, 0, 0, 0.0
    for i in range(GRID):
        for j in range(GRID):
            for k in range(GRID):
                v = lattice[i][j][k]
                if v > best_v:
                    best_i, best_j, best_k, best_v = i, j, k, v
    return {
        "ix": best_i,
        "iy": best_j,
        "iz": best_k,
        "amplitude": round(best_v, 4),
        "norm": {
            "x": round((best_i + 0.5) / GRID - 0.5, 4),
            "y": round((best_j + 0.5) / GRID - 0.5, 4),
            "z": round((best_k + 0.5) / GRID - 0.5, 4),
        },
    }


def _lattice_energy(lattice: list[list[list[float]]]) -> float:
    return sum(lattice[i][j][k] for i in range(GRID) for j in range(GRID) for k in range(GRID))


def _couple_scales(lattices: dict[str, list[list[list[float]]]]) -> dict[str, float]:
    """Parent net bleeds peak amplitude into child net — networks-of-networks coupling."""
    bleed: dict[str, float] = {}
    for idx in range(1, len(SCALE_ORDER)):
        parent_id = SCALE_ORDER[idx - 1]
        child_id = SCALE_ORDER[idx]
        parent = lattices.get(parent_id)
        child = lattices.get(child_id)
        if not parent or not child:
            continue
        peak = _peak_cell(parent)
        w = peak["amplitude"] * COUPLE_BLEED
        if w <= 0:
            continue
        norm = peak.get("norm") or {}
        _inject_amplitude(
            child,
            norm_x=float(norm.get("x") or 0.0),
            norm_y=float(norm.get("y") or 0.0),
            norm_z=float(norm.get("z") or 0.5),
            weight=w,
        )
        bleed[child_id] = round(w, 4)
    return bleed


def _targets_from_panel(panel: dict[str, Any]) -> list[dict[str, Any]]:
    ha = panel.get("host_attacks") or {}
    pts = ha.get("points") or ha.get("hosts") or []
    if isinstance(pts, dict):
        pts = list(pts.values())
    out: list[dict[str, Any]] = []
    for p in pts if isinstance(pts, list) else []:
        if not isinstance(p, dict):
            continue
        lat = p.get("lat") or p.get("latitude")
        lon = p.get("lon") or p.get("longitude")
        if lat is None or lon is None:
            continue
        heat = float(p.get("heat") or p.get("threat_heat") or 0.5)
        out.append({
            "lat": float(lat),
            "lon": float(lon),
            "heat": heat,
            "ip": p.get("ip"),
            "kind": str(p.get("kind") or p.get("vector") or "hostile"),
        })
    out.sort(key=lambda t: t["heat"], reverse=True)
    return out[:48]


def _humanoid_motion() -> list[dict[str, Any]]:
    import importlib.util

    py = INSTALL / "lib" / "humanoid-motion-training.py"
    if not py.is_file():
        panel = _load(STATE / "humanoid-motion-panel.json", {})
        return panel.get("body_motion") or []
    try:
        spec = importlib.util.spec_from_file_location("humanoid_motion", py)
        if not spec or not spec.loader:
            return []
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "body_motion_amplitudes"):
            return mod.body_motion_amplitudes()
    except Exception:
        pass
    panel = _load(STATE / "humanoid-motion-panel.json", {})
    return panel.get("body_motion") or []


def _geometry_mod() -> Any | None:
    import importlib.util

    py = INSTALL / "lib" / "spatial-target-geometry.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("spatial_target_geometry", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _nearest_threat_geometry(targets: list[dict[str, Any]]) -> dict[str, Any]:
    geo = _geometry_mod()
    if not geo or not targets:
        return {"recognized": False}
    top = targets[0]
    try:
        return geo.classify_geometry(
            target_lat=top["lat"],
            target_lon=top["lon"],
            target_kind=top.get("kind") or "hostile",
            rf_threat=top.get("heat", 0) >= 0.7,
        )
    except Exception:
        return {"recognized": False}


def _history_window(limit: int = 8) -> list[dict[str, Any]]:
    if not HISTORY.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in HISTORY.read_text(encoding="utf-8").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        return []
    return rows


def _temporal_velocity(history: list[dict[str, Any]]) -> dict[str, Any]:
    if len(history) < 2:
        return {"samples": len(history), "slope": 0.0, "acceleration": 0.0}
    deltas = [float(h.get("delta_t") or 0) for h in history]
    slope = sum(deltas) / len(deltas)
    accel = 0.0
    if len(deltas) >= 2:
        accel = (deltas[-1] - deltas[0]) / max(1, len(deltas) - 1)
    return {
        "samples": len(history),
        "slope": round(slope, 4),
        "acceleration": round(accel, 4),
    }


def explain_spatial_lattice() -> str:
    """Plain-language doctrine for autonomous beings — 3D/4D nets-of-nets."""
    return (
        "Spatial awareness is a nested 3D lattice per scale — body, room, field, planetary — "
        "each an 8³ amplitude net. Parent nets bleed peak energy into child nets (networks-of-networks). "
        "Time is the fourth dimension: delta_t over history drives movement hints — approach, recede, stable. "
        "No slow 3D CNN — O(neighbors) coupling per tick, melded into Universal Protector."
    )


def build_spatial(*, write: bool = True) -> dict[str, Any]:
    """3D lattice now + 4D delta from history — nested scale nets."""
    doctrine = _load(DOCTRINE, {})
    panel = _load(STATE / "threat-panel.json", {})
    op = _load(STATE / "operator-location.json", {"lat": 45.846, "lon": -87.056})
    sense = _load(STATE / "field-sense-package-panel.json", {})
    prev = _load(RUNTIME, {})

    op_lat = float(op.get("lat") or 45.846)
    op_lon = float(op.get("lon") or -87.056)
    targets = _targets_from_panel(panel)
    threat_geo = _nearest_threat_geometry(targets)

    lattices: dict[str, list[list[list[float]]]] = {}
    for scale_id in SCALE_ORDER:
        lattice = _empty_lattice()
        if scale_id == "planetary":
            for t in targets:
                dlat = (t["lat"] - op_lat) / 90.0
                dlon = (t["lon"] - op_lon) / 180.0
                _inject_amplitude(lattice, norm_x=dlon, norm_y=dlat, norm_z=0.0, weight=min(1.0, t["heat"]))
        elif scale_id == "field":
            rf = panel.get("field_rf") or {}
            bursts = len(rf.get("recent_bursts") or [])
            w = min(1.0, bursts / 12.0)
            if threat_geo.get("rf_trespass"):
                w = min(1.0, w + 0.35)
            _inject_amplitude(lattice, norm_x=0.0, norm_y=0.0, norm_z=0.2, weight=w)
        elif scale_id == "room":
            hot = int((panel.get("field_command") or {}).get("pulse", {}).get("host_hot") or 0)
            w = min(1.0, hot / 8.0)
            if threat_geo.get("geometry") in ("approaching", "wire_trespass", "rf_trespass"):
                w = min(1.0, w + 0.4)
            _inject_amplitude(lattice, norm_x=0.0, norm_y=0.0, norm_z=0.5, weight=w)
        else:
            eye = (sense.get("summary") or {}).get("eye_live")
            ear = (sense.get("summary") or {}).get("ear_live")
            w = 0.85 if eye else 0.25
            if ear:
                w = min(1.0, w + 0.15)
            _inject_amplitude(lattice, norm_x=0.0, norm_y=0.0, norm_z=0.8, weight=w)
            for m in _humanoid_motion():
                _inject_amplitude(
                    lattice,
                    norm_x=float(m.get("norm_x") or 0),
                    norm_y=float(m.get("norm_y") or 0),
                    norm_z=float(m.get("norm_z") or 0.5),
                    weight=float(m.get("weight") or 0.3),
                )
        lattices[scale_id] = lattice

    coupling = _couple_scales(lattices)

    scales: dict[str, Any] = {}
    for scale_id, lattice in lattices.items():
        cfg = (doctrine.get("networks_of_networks") or {}).get(scale_id) or {}
        peak = _peak_cell(lattice)
        energy = _lattice_energy(lattice)
        scales[scale_id] = {
            "lattice_cells": GRID,
            "peak_amplitude": peak["amplitude"],
            "peak_cell": peak,
            "field_energy": round(energy, 4),
            "net_of_nets": True,
            "parent_bleed": coupling.get(scale_id),
            "role": cfg.get("role"),
        }

    prev_energy = float(prev.get("total_energy") or 0)
    total_energy = sum(s.get("field_energy", 0) for s in scales.values())
    delta_t = total_energy - prev_energy
    history = _history_window()
    temporal = _temporal_velocity(history)

    approach = delta_t > 0.5 or temporal.get("slope", 0) > 0.25
    recede = delta_t < -0.5 or temporal.get("slope", 0) < -0.25
    bearing = threat_geo.get("bearing_deg")
    geometry = threat_geo.get("geometry") or "stable"

    doc = {
        "schema": "field-spatial-runtime/v1",
        "updated": _now(),
        "autonomous_being": True,
        "product": "Universal Protector",
        "dimensions": "3D+T",
        "lattice_axes": ["x", "y", "z", "t"],
        "networks_of_networks": scales,
        "scale_order": list(SCALE_ORDER),
        "coupling_bleed": COUPLE_BLEED,
        "coupling_applied": coupling,
        "total_energy": round(total_energy, 4),
        "delta_t": round(delta_t, 4),
        "temporal_4d": temporal,
        "movement_vector": {
            "approach": approach,
            "recede": recede,
            "stable": not approach and not recede,
            "bearing_deg": bearing,
            "geometry": geometry,
            "trespass": bool(threat_geo.get("trespass")),
        },
        "operator": {"lat": op_lat, "lon": op_lon},
        "target_count": len(targets),
        "nearest_threat": threat_geo.get("target") if threat_geo.get("recognized") else None,
        "eye_live": (sense.get("summary") or {}).get("eye_live"),
        "ear_live": (sense.get("summary") or {}).get("ear_live"),
        "humanoid_motion": len(_humanoid_motion()),
        "motto": doctrine.get("motto"),
        "explain": explain_spatial_lattice(),
    }

    if write:
        _save(RUNTIME, doc)
        _save(PANEL, {**doc, "schema": "field-spatial-panel/v1"})
        try:
            with HISTORY.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "ts": doc["updated"],
                    "energy": total_energy,
                    "delta_t": delta_t,
                    "geometry": geometry,
                    "bearing_deg": bearing,
                }) + "\n")
        except OSError:
            pass
    return doc


def panel_json() -> dict[str, Any]:
    return build_spatial(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "build"):
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "explain":
        print(json.dumps({"explain": explain_spatial_lattice()}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-spatial-cognition.py [json|panel|explain]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())