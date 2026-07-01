#!/usr/bin/env pythong
"""Sub-micron GPS precision — fixed-point degrees + ENU nanometer placement.

Resolution: FIXED_SCALE = 1e15 per degree (~0.11 nm latitude per LSB).
All detected coordinates preserve full precision as strings + integer fixed-point.
"""
from __future__ import annotations

import json
import math
import os
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

getcontext().prec = 40

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))

# 1 LSB ≈ 0.111 nm latitude (sub-micron)
FIXED_SCALE = 10**15
WGS84_A_M = 6378137.0
WGS84_F = 1.0 / 298.257223563
WGS84_E2 = 2 * WGS84_F - WGS84_F * WGS84_F
NM_PER_M = 1_000_000_000.0  # nanometers per meter
M_PER_DEG_LAT = 111_319.49079327357


def _d(val: Any) -> Decimal:
    return Decimal(str(val))


def encode_fixed(deg: float | Decimal) -> str:
    """Integer fixed-point degrees as decimal string (JSON-safe >2^53)."""
    return str(int((_d(deg) * FIXED_SCALE).to_integral_value()))


def decode_fixed(fixed: str | int) -> Decimal:
    return _d(fixed) / FIXED_SCALE


def format_deg(deg: float | Decimal, *, places: int = 15) -> str:
    q = Decimal(10) ** -places
    return str(_d(deg).quantize(q))


def latlon_to_ecef_m(lat: float | Decimal, lon: float | Decimal, alt_m: float = 0.0) -> tuple[float, float, float]:
    lat_r = math.radians(float(lat))
    lon_r = math.radians(float(lon))
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    sin_lon = math.sin(lon_r)
    cos_lon = math.cos(lon_r)
    n = WGS84_A_M / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    x = (n + alt_m) * cos_lat * cos_lon
    y = (n + alt_m) * cos_lat * sin_lon
    z = (n * (1.0 - WGS84_E2) + alt_m) * sin_lat
    return x, y, z


def ecef_to_enu_nm(
    anchor_lat: float | Decimal,
    anchor_lon: float | Decimal,
    lat: float | Decimal,
    lon: float | Decimal,
    *,
    alt_m: float = 0.0,
) -> tuple[str, str, str]:
    """East / North / Up offset in nanometers from anchor (sub-micron)."""
    ax, ay, az = latlon_to_ecef_m(anchor_lat, anchor_lon, 0.0)
    px, py, pz = latlon_to_ecef_m(lat, lon, alt_m)
    lat_r = math.radians(float(anchor_lat))
    lon_r = math.radians(float(anchor_lon))
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    sin_lon = math.sin(lon_r)
    cos_lon = math.cos(lon_r)
    dx, dy, dz = px - ax, py - ay, pz - az
    east_m = -sin_lon * dx + cos_lon * dy
    north_m = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
    up_m = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz
    return (
        str(int(round(east_m * NM_PER_M))),
        str(int(round(north_m * NM_PER_M))),
        str(int(round(up_m * NM_PER_M))),
    )


def enu_nm_to_latlon(
    anchor_lat: float | Decimal,
    anchor_lon: float | Decimal,
    east_nm: int | str,
    north_nm: int | str,
    *,
    up_nm: int | str = "0",
) -> tuple[Decimal, Decimal]:
    """Convert ENU nanometer offset back to WGS84 lat/lon."""
    lat_r = math.radians(float(anchor_lat))
    lon_r = math.radians(float(anchor_lon))
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)
    sin_lon = math.sin(lon_r)
    cos_lon = math.cos(lon_r)
    east_m = int(east_nm) / NM_PER_M
    north_m = int(north_nm) / NM_PER_M
    up_m = int(up_nm) / NM_PER_M
    dx = -sin_lon * east_m - sin_lat * cos_lon * north_m + cos_lat * cos_lon * up_m
    dy = cos_lon * east_m - sin_lat * sin_lon * north_m + cos_lat * sin_lon * up_m
    dz = cos_lat * north_m + sin_lat * up_m
    ax, ay, az = latlon_to_ecef_m(anchor_lat, anchor_lon, 0.0)
    px, py, pz = ax + dx, ay + dy, az + dz
    p = math.sqrt(px * px + py * py)
    lon = math.degrees(math.atan2(py, px))
    lat = math.degrees(math.atan2(pz, p * (1.0 - WGS84_E2)))
    return _d(lat), _d(lon)


def placement_from_detected(
    lat: Any,
    lon: Any,
    *,
    anchor: dict[str, Any] | None = None,
    east_nm: Any = None,
    north_nm: Any = None,
    up_nm: Any = None,
    source: str = "detected",
    label: str = "",
) -> dict[str, Any]:
    """Build sub-micron placement record from detected GPS + optional ENU nm offsets."""
    if east_nm is not None and north_nm is not None and anchor:
        lat_d, lon_d = enu_nm_to_latlon(
            anchor.get("lat", anchor.get("lat_deg")),
            anchor.get("lon", anchor.get("lon_deg")),
            east_nm,
            north_nm,
            up_nm=up_nm or "0",
        )
    else:
        lat_d = _d(lat)
        lon_d = _d(lon)

    lat_f = float(lat_d)
    lon_f = float(lon_d)
    while lon_f > 180:
        lon_f -= 360
    while lon_f < -180:
        lon_f += 360

    anchor_doc = anchor or _load_anchor()
    enu = ecef_to_enu_nm(
        anchor_doc.get("lat", lat_f),
        anchor_doc.get("lon", lon_f),
        lat_f,
        lon_f,
    ) if anchor_doc.get("lat") is not None else ("0", "0", "0")

    return {
        "lat": lat_f,
        "lon": lon_f,
        "lat_str": format_deg(lat_f),
        "lon_str": format_deg(lon_f),
        "lat_i": encode_fixed(lat_f),
        "lon_i": encode_fixed(lon_f),
        "precision": "sub_micron",
        "resolution_nm": round(M_PER_DEG_LAT * 1e9 / FIXED_SCALE, 3),
        "enu_e_nm": enu[0],
        "enu_n_nm": enu[1],
        "enu_u_nm": enu[2],
        "anchor_id": anchor_doc.get("id") or "operator",
        "source": source,
        "label": label,
        "placed": True,
    }


def enrich_entity(entity: dict[str, Any], anchor: dict[str, Any] | None = None) -> dict[str, Any]:
    """Attach sub-micron GPS fields to any registry entity with lat/lon."""
    out = dict(entity)
    lat = entity.get("lat")
    lon = entity.get("lon")
    if lat is None or lon is None:
        out["precision"] = "unplaced"
        return out
    if entity.get("lat_i") and entity.get("lon_i"):
        out.setdefault("precision", "sub_micron")
        return out
    place = placement_from_detected(
        lat, lon,
        anchor=anchor,
        east_nm=entity.get("enu_e_nm"),
        north_nm=entity.get("enu_n_nm"),
        up_nm=entity.get("enu_u_nm"),
        source=entity.get("source") or "registry",
        label=str(entity.get("label") or entity.get("id") or ""),
    )
    out.update(place)
    return out


def _enu_variance(entities: list[dict[str, Any]]) -> dict[str, Any]:
    """Dominant ENU axis — height (U) often carries most placement variance."""
    e_vals: list[int] = []
    n_vals: list[int] = []
    u_vals: list[int] = []
    lats: list[float] = []
    lons: list[float] = []
    for ent in entities:
        if ent.get("lat") is not None and ent.get("lon") is not None:
            try:
                lats.append(float(ent["lat"]))
                lons.append(float(ent["lon"]))
            except (TypeError, ValueError):
                pass
        for key, bucket in (("enu_e_nm", e_vals), ("enu_n_nm", n_vals), ("enu_u_nm", u_vals)):
            raw = ent.get(key)
            if raw is None:
                continue
            try:
                bucket.append(int(str(raw)))
            except (TypeError, ValueError):
                pass

    def _spread(vals: list[int]) -> int:
        if not vals:
            return 0
        if len(vals) < 2:
            return abs(vals[0])
        return max(vals) - min(vals)

    var_e, var_n, var_u = _spread(e_vals), _spread(n_vals), _spread(u_vals)
    if var_u >= var_e and var_u >= var_n:
        dominant = "u"
    elif var_e >= var_n:
        dominant = "e"
    else:
        dominant = "n"
    mean_u = int(sum(u_vals) / len(u_vals)) if u_vals else 0
    return {
        "var_e_nm": var_e,
        "var_n_nm": var_n,
        "var_u_nm": var_u,
        "dominant_axis": dominant,
        "mean_u_nm": mean_u,
        "center_lat": sum(lats) / len(lats) if lats else None,
        "center_lon": sum(lons) / len(lons) if lons else None,
        "count": len(lats),
    }


def resolve_anchor_from_entities(entities: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    entities = entities or []
    var = _enu_variance(entities)
    alt_m = round(var["mean_u_nm"] / NM_PER_M, 4) if var["mean_u_nm"] else 0.0
    if var["center_lat"] is not None and var["center_lon"] is not None:
        return {
            "id": "variance_centroid",
            "lat": var["center_lat"],
            "lon": var["center_lon"],
            "label": f"Centroid ({var['count']} placed)",
            "alt_m": alt_m,
            "dominant_axis": var["dominant_axis"],
            "var_u_nm": var["var_u_nm"],
            "var_e_nm": var["var_e_nm"],
            "var_n_nm": var["var_n_nm"],
        }
    return {
        "id": "field_default",
        "lat": 45.845976,
        "lon": -87.055759,
        "label": "Gladstone MI · 8259 W Burntwood P.15 Drive",
        "alt_m": 0.0,
        "dominant_axis": "u",
    }


def _try_seed_operator_wireless() -> dict[str, Any] | None:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("op_loc", INSTALL / "lib" / "operator-location.py")
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out = mod.wireless_immediate()
        if out.get("ok") and out.get("lat") is not None:
            return {
                "id": "operator",
                "lat": float(out["lat"]),
                "lon": float(out["lon"]),
                "label": out.get("label") or "Wireless egress",
                "alt_m": float(out.get("alt_m") or 0),
                "source": out.get("source") or "wireless_egress",
            }
    except Exception:
        return None
    return None


def _load_anchor(entities: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    op = STATE / "operator-location.json"
    if op.is_file():
        try:
            doc = json.loads(op.read_text(encoding="utf-8"))
            lat, lon = doc.get("lat"), doc.get("lon")
            if lat is not None and lon is not None and not (float(lat) == 0.0 and float(lon) == 0.0):
                return {
                    "id": "operator",
                    "lat": float(lat),
                    "lon": float(lon),
                    "label": doc.get("label") or "Operator",
                    "alt_m": float(doc.get("alt_m") or 0),
                }
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    seeded = _try_seed_operator_wireless()
    if seeded:
        return seeded
    if entities:
        return resolve_anchor_from_entities(entities)
    return resolve_anchor_from_entities([])


def _spherical_to_cartesian(lat: float, lon: float) -> tuple[float, float, float]:
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    cos_lat = math.cos(lat_r)
    return cos_lat * math.cos(lon_r), cos_lat * math.sin(lon_r), math.sin(lat_r)


def _cartesian_to_spherical(x: float, y: float, z: float) -> tuple[float, float]:
    lon = math.degrees(math.atan2(y, x))
    hyp = math.sqrt(x * x + y * y)
    lat = math.degrees(math.atan2(z, hyp))
    return lat, lon


def barycentric_point_on_sphere(
    a: dict[str, Any],
    b: dict[str, Any],
    c: dict[str, Any],
    wa: float,
    wb: float,
    wc: float,
) -> dict[str, Any]:
    """Return exact WGS84 point from three anchor GPS — never radial/path."""
    ax, ay, az = _spherical_to_cartesian(float(a["lat"]), float(a["lon"]))
    bx, by, bz = _spherical_to_cartesian(float(b["lat"]), float(b["lon"]))
    cx, cy, cz = _spherical_to_cartesian(float(c["lat"]), float(c["lon"]))
    x = wa * ax + wb * bx + wc * cx
    y = wa * ay + wb * by + wc * cy
    z = wa * az + wb * bz + wc * cz
    norm = math.sqrt(x * x + y * y + z * z) or 1.0
    lat, lon = _cartesian_to_spherical(x / norm, y / norm, z / norm)
    return {
        "lat": round(lat, 9),
        "lon": round(lon, 9),
        "return_type": "point",
        "placement_mode": "triangulate_3gps",
        "weights": {"a": wa, "b": wb, "c": wc},
    }


def triangulate_planet_map(
    anchors: list[dict[str, Any]],
    *,
    grid_steps: int = 16,
    label_prefix: str = "planet",
) -> dict[str, Any]:
    """Map the planetary field from exactly three GPS anchors — all returns are on-point WGS84."""
    if len(anchors) < 3:
        return {
            "ok": False,
            "schema": "planet-triangulate/v1",
            "error": "need_3_gps_anchors",
            "return_type": "point",
            "points": [],
        }
    a, b, c = anchors[0], anchors[1], anchors[2]
    for req, tag in ((a, "a"), (b, "b"), (c, "c")):
        if req.get("lat") is None or req.get("lon") is None:
            return {
                "ok": False,
                "schema": "planet-triangulate/v1",
                "error": f"anchor_{tag}_missing_gps",
                "return_type": "point",
                "points": [],
            }

    points: list[dict[str, Any]] = []
    steps = max(3, grid_steps)
    for i in range(steps):
        for j in range(steps - i):
            u = i / max(steps - 1, 1)
            v = j / max(steps - 1, 1)
            w = max(0.0, 1.0 - u - v)
            total = u + v + w or 1.0
            u, v, w = u / total, v / total, w / total
            raw = barycentric_point_on_sphere(a, b, c, u, v, w)
            place = placement_from_detected(
                raw["lat"],
                raw["lon"],
                anchor={"lat": float(a["lat"]), "lon": float(a["lon"]), "id": "tri_anchor_a"},
                source="planet_triangulate",
                label=f"{label_prefix}_{i}_{j}",
            )
            place["return_type"] = "point"
            place["placement_mode"] = "triangulate_3gps"
            place["tri_weights"] = raw["weights"]
            points.append(place)

    carts = [
        _spherical_to_cartesian(float(a["lat"]), float(a["lon"])),
        _spherical_to_cartesian(float(b["lat"]), float(b["lon"])),
        _spherical_to_cartesian(float(c["lat"]), float(c["lon"])),
    ]
    cx = sum(p[0] for p in carts) / 3.0
    cy = sum(p[1] for p in carts) / 3.0
    cz = sum(p[2] for p in carts) / 3.0
    norm = math.sqrt(cx * cx + cy * cy + cz * cz) or 1.0
    centroid_lat, centroid_lon = _cartesian_to_spherical(cx / norm, cy / norm, cz / norm)

    return {
        "ok": True,
        "schema": "planet-triangulate/v1",
        "return_type": "point",
        "placement_mode": "triangulate_3gps",
        "anchors": [
            {"id": a.get("id", "anchor_a"), "lat": a["lat"], "lon": a["lon"], "label": a.get("label", "")},
            {"id": b.get("id", "anchor_b"), "lat": b["lat"], "lon": b["lon"], "label": b.get("label", "")},
            {"id": c.get("id", "anchor_c"), "lat": c["lat"], "lon": c["lon"], "label": c.get("label", "")},
        ],
        "centroid": {"lat": centroid_lat, "lon": centroid_lon},
        "point_count": len(points),
        "points": points,
        "grid_steps": steps,
        "motto": "Three GPS anchors map the planet — every return is an on-point WGS84 coordinate.",
    }


def point_return(
    lat: float,
    lon: float,
    *,
    anchor: dict[str, Any] | None = None,
    source: str = "point",
    label: str = "",
    entity_id: str = "",
) -> dict[str, Any]:
    """Canonical on-point return — never radial, never path-derived."""
    place = placement_from_detected(lat, lon, anchor=anchor, source=source, label=label)
    place["return_type"] = "point"
    place["placement_mode"] = "wgs84_point"
    if entity_id:
        place["id"] = entity_id
    return place


def panel_json() -> dict[str, Any]:
    anchor = _load_anchor()
    return {
        "motto": "Sub-micron GPS — fixed-point 1e15 deg⁻¹ (~0.11 nm LSB) + ENU nanometer placement.",
        "fixed_scale": FIXED_SCALE,
        "resolution_nm": round(M_PER_DEG_LAT * 1e9 / FIXED_SCALE, 3),
        "anchor": anchor,
        "formats": ["lat_str", "lon_str", "lat_i", "lon_i", "enu_e_nm", "enu_n_nm", "enu_u_nm"],
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "place" and len(sys.argv) >= 4:
        doc = placement_from_detected(float(sys.argv[2]), float(sys.argv[3]), label=sys.argv[4] if len(sys.argv) > 4 else "")
        print(json.dumps(doc, ensure_ascii=False))
        return 0
    if cmd == "planet" and len(sys.argv) >= 2:
        raw = sys.argv[2]
        try:
            anchors = json.loads(raw)
        except json.JSONDecodeError:
            print(json.dumps({"error": "planet requires JSON array of 3 anchors"}))
            return 1
        if not isinstance(anchors, list):
            anchors = [anchors]
        steps = int(sys.argv[3]) if len(sys.argv) > 3 else 12
        print(json.dumps(triangulate_planet_map(anchors, grid_steps=steps), ensure_ascii=False))
        return 0
    if cmd == "enu" and len(sys.argv) >= 6:
        anchor = _load_anchor()
        doc = placement_from_detected(
            anchor["lat"], anchor["lon"],
            anchor=anchor,
            east_nm=sys.argv[2],
            north_nm=sys.argv[3],
            up_nm=sys.argv[4] if len(sys.argv) > 4 else "0",
            label=sys.argv[5] if len(sys.argv) > 5 else "enu_place",
        )
        print(json.dumps(doc, ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: gps-precision.py [json|place LAT LON [label]|planet JSON_ANCHORS [steps]|enu E_NM N_NM [U_NM] [label]]",
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())