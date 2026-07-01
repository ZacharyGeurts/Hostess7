#!/usr/bin/env pythong
"""Spatial target geometry — bearing, distance, trespass corridor, approach vectors."""
from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
POLICY = INSTALL / "data" / "lethal-enforcement-policy.json"
OPERATOR_LOC = STATE / "operator-location.json"


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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _geo_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("geo_distance", INSTALL / "lib" / "geo-distance.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _operator() -> dict[str, Any]:
    doc = _load_json(OPERATOR_LOC, {})
    if doc.get("lat") is None:
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "operator_default", INSTALL / "lib" / "operator-default.py",
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                doc = mod.seed_operator_location()
        except Exception:
            doc = {"lat": 45.845976, "lon": -87.055759, "label": "operator_field"}
    return doc


def classify_geometry(
    *,
    target_lat: float | None,
    target_lon: float | None,
    target_kind: str = "",
    wire_trespass: bool = False,
    rf_threat: bool = False,
) -> dict[str, Any]:
    """Recognize spatial geometry relative to operator — trespass, approach, encircle."""
    policy = _load_json(POLICY, {})
    spatial = policy.get("spatial") or {}
    op = _operator()
    op_lat = float(op.get("lat") or 45.845976)
    op_lon = float(op.get("lon") or -87.055759)

    if target_lat is None or target_lon is None:
        return {
            "schema": "spatial-target-geometry/v1",
            "recognized": False,
            "reason": "no_target_coords",
            "operator": {"lat": op_lat, "lon": op_lon},
        }

    geo = _geo_mod()
    dist = geo.distance_fields(op_lat, op_lon, float(target_lat), float(target_lon))
    km = float(dist.get("distance_km") or 0.0)
    brg = bearing_deg(op_lat, op_lon, float(target_lat), float(target_lon))

    exclusion_m = float(spatial.get("operator_exclusion_m") or 500)
    rf_km = float(spatial.get("rf_trespass_km") or 8.0)
    inside_exclusion = km * 1000.0 <= exclusion_m
    rf_trespass_geom = rf_threat and km <= rf_km
    wire_trespass_geom = wire_trespass or inside_exclusion

    geometry = "distant"
    trespass = False
    if wire_trespass_geom:
        geometry = "wire_trespass"
        trespass = True
    elif rf_trespass_geom:
        geometry = "rf_trespass"
        trespass = True
    elif km <= 2.0 and str(target_kind).lower() in ("terror", "hostile"):
        geometry = "approaching"
        trespass = True
    elif km <= 15.0 and str(target_kind).lower() in ("terror", "hostile"):
        geometry = "encircling"
    elif rf_threat:
        geometry = "overhead_rf"

    return {
        "schema": "spatial-target-geometry/v1",
        "recognized": True,
        "updated": _now(),
        "operator": {"lat": op_lat, "lon": op_lon, "label": op.get("label")},
        "target": {"lat": float(target_lat), "lon": float(target_lon), "kind": target_kind},
        "bearing_deg": round(brg, 2),
        "distance_km": dist.get("distance_km"),
        "distance_label": dist.get("distance_label"),
        "geometry": geometry,
        "trespass": trespass,
        "wire_trespass": wire_trespass_geom,
        "rf_trespass": rf_trespass_geom,
        "inside_exclusion": inside_exclusion,
        "shoot_to_kill_geometry": trespass and str(target_kind).lower() in ("terror", "hostile", ""),
    }


def geometry_for_target(row: dict[str, Any]) -> dict[str, Any]:
    lat = row.get("lat")
    lon = row.get("lon")
    geo = row.get("geo") or {}
    if lat is None:
        lat = geo.get("lat")
    if lon is None:
        lon = geo.get("lon")
    kind = str(row.get("kind") or row.get("vector") or "")
    if kind.lower() in ("wifi_threat", "field_antenna_alert"):
        kind = "hostile"
    return classify_geometry(
        target_lat=float(lat) if lat is not None else None,
        target_lon=float(lon) if lon is not None else None,
        target_kind=kind,
        wire_trespass=bool(row.get("wire_trespass") or row.get("hell_chosen")),
        rf_threat=bool(row.get("rf_threat") or row.get("unpermitted_spectrum")),
    )


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: spatial-target-geometry.py [json|classify '<json>']", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "json":
        op = _operator()
        print(json.dumps({"schema": "spatial-target-geometry/v1", "operator": op, "policy": str(POLICY)}))
        return 0
    if cmd == "classify" and len(sys.argv) > 2:
        row = json.loads(sys.argv[2])
        print(json.dumps(geometry_for_target(row), indent=2))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())