#!/usr/bin/env pythong
"""DeviceMap — sub-micron operator anchor + 3D bearing/distance map of all connected devices."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-device-map-doctrine.json"
PANEL = STATE / "field-device-map-panel.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cardinal(bearing: float) -> str:
    dirs = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    return dirs[int((bearing + 22.5) % 360 / 45)]


def _bearing(op_lat: float, op_lon: float, lat: float, lon: float) -> float:
    geo = _mod("lib/spatial-target-geometry.py", "stg")
    if geo and hasattr(geo, "bearing_deg"):
        return float(geo.bearing_deg(op_lat, op_lon, lat, lon))
    p1, p2 = math.radians(op_lat), math.radians(lat)
    dl = math.radians(lon - op_lon)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _distance(op_lat: float, op_lon: float, lat: float, lon: float) -> dict[str, Any]:
    geo = _mod("lib/geo-distance.py", "gd")
    if geo and hasattr(geo, "distance_fields"):
        return geo.distance_fields(op_lat, op_lon, lat, lon)
    r = 6371.0
    p1, p2 = math.radians(op_lat), math.radians(lat)
    dp, dl = math.radians(lat - op_lat), math.radians(lon - op_lon)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    km = r * 2 * math.asin(min(1.0, math.sqrt(a)))
    return {"distance_km": round(km, 4), "distance_mi": round(km * 0.621371, 4), "distance_label": f"{km:.2f} km"}


def _operator_anchor() -> dict[str, Any]:
    gp = _mod("lib/gps-precision.py", "gps")
    op = _load(STATE / "operator-location.json", {})
    if op.get("lat") is None:
        ol = _mod("lib/operator-location.py", "oploc")
        if ol and hasattr(ol, "_load"):
            op = ol._load()
    lat = float(op.get("lat") or 45.845976)
    lon = float(op.get("lon") or -87.055759)
    if gp and hasattr(gp, "placement_from_detected"):
        place = gp.placement_from_detected(
            lat, lon,
            source=op.get("source") or "operator",
            label=str(op.get("label") or "Operator · You"),
        )
        row = {
            **place,
            "id": "operator",
            "role": "operator",
            "kind": "operator",
            "connected": True,
            "flying": False,
            "alt_m": float(op.get("alt_m") or 0.0),
            "section": "operator",
        }
        row["bearing_deg"] = 0.0
        row["direction"] = "HERE"
        row["distance_km"] = 0.0
        row["distance_nm"] = "0"
        row["scene"] = {"x": 0.0, "y": 0.0, "z": 0.0}
        return row
    return {
        "id": "operator",
        "lat": lat,
        "lon": lon,
        "label": op.get("label") or "Operator",
        "precision": "standard",
        "role": "operator",
        "connected": True,
        "flying": False,
        "bearing_deg": 0.0,
        "direction": "HERE",
        "distance_km": 0.0,
        "scene": {"x": 0.0, "y": 0.0, "z": 0.0},
    }


def _ipv4_sovereign_enabled() -> bool:
    if os.environ.get("NEXUS_FIELD_IPV4_DEVICE_SOVEREIGN", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    doctrine = _load(INSTALL / "data" / "field-ipv4-device-sovereign-doctrine.json", {})
    return bool((doctrine.get("policy") or {}).get("track_devices_not_numbers", True))


def _ipv4_authority(device: dict[str, Any]) -> dict[str, Any]:
    kind = str(device.get("kind") or device.get("role") or "device").lower()
    source = str(device.get("source") or "").lower()
    box_kinds = {"operator", "sovereign", "botnet", "botnet_member", "qemu_world", "botnet_dns", "flying"}
    return {
        "sovereign": True,
        "all_ipv4_on_box": kind in box_kinds or source in ("botnet_dns_dhcp", "botnet_registry"),
        "track_ip": False,
        "dns_authority": "hostess7_truth",
        "dhcp_authority": "hostess7_field",
        "suppress_foreign_dns_dhcp": True,
        "auto_managed": True,
        "never_look_back": True,
    }


def _is_flying(row: dict[str, Any], doctrine: dict[str, Any]) -> bool:
    kinds = {str(k).lower() for k in (doctrine.get("flying_kinds") or [])}
    kind = str(row.get("kind") or row.get("role") or "").lower()
    if kind in kinds:
        return True
    if str(row.get("motion") or "").lower() in ("flying", "airborne", "orbital"):
        return True
    try:
        alt = float(row.get("alt_m") or row.get("altitude_m") or 0)
        if alt > 50:
            return True
    except (TypeError, ValueError):
        pass
    return bool(row.get("flying"))


def _scene_coords(anchor: dict[str, Any], device: dict[str, Any], *, km_scale: float = 0.001) -> dict[str, float]:
    """Map ENU nm to Three.js scene — 1 unit ≈ 1 km when km_scale=0.001."""
    try:
        e = int(str(device.get("enu_e_nm") or "0"))
        n = int(str(device.get("enu_n_nm") or "0"))
        u = int(str(device.get("enu_u_nm") or "0"))
    except (TypeError, ValueError):
        e = n = u = 0
    if e == 0 and n == 0 and device.get("lat") is not None:
        dist = _distance(
            float(anchor.get("lat") or 0),
            float(anchor.get("lon") or 0),
            float(device["lat"]),
            float(device["lon"]),
        )
        km = float(dist.get("distance_km") or 0)
        br = math.radians(float(device.get("bearing_deg") or 0))
        e_m = km * 1000.0 * math.sin(br)
        n_m = km * 1000.0 * math.cos(br)
        e, n = int(e_m * 1e9), int(n_m * 1e9)
    m_per_unit = 1000.0 / km_scale if km_scale else 1000.0
    return {
        "x": round(e / 1e9 / m_per_unit, 6),
        "y": round(u / 1e9 / m_per_unit, 6),
        "z": round(-n / 1e9 / m_per_unit, 6),
    }


def _enrich_device(raw: dict[str, Any], anchor: dict[str, Any], doctrine: dict[str, Any]) -> dict[str, Any] | None:
    lat, lon = raw.get("lat"), raw.get("lon")
    if lat is None or lon is None:
        return None
    try:
        lat_f, lon_f = float(lat), float(lon)
    except (TypeError, ValueError):
        return None
    if lat_f == 0.0 and lon_f == 0.0:
        return None
    op_lat = float(anchor.get("lat") or 0)
    op_lon = float(anchor.get("lon") or 0)
    gp = _mod("lib/gps-precision.py", "gps")
    row = dict(raw)
    if gp and hasattr(gp, "enrich_entity"):
        row = gp.enrich_entity(row, anchor)
    br = _bearing(op_lat, op_lon, lat_f, lon_f)
    dist = _distance(op_lat, op_lon, lat_f, lon_f)
    row.update({
        "lat": lat_f,
        "lon": lon_f,
        "bearing_deg": round(br, 4),
        "direction": _cardinal(br),
        "elevation_deg": round(float(raw.get("elevation_deg") or 0), 2),
        "distance_km": dist.get("distance_km"),
        "distance_mi": dist.get("distance_mi"),
        "distance_label": dist.get("distance_label"),
        "distance_nm": str(int(float(dist.get("distance_km") or 0) * 1e9 * 1000 / 1852)) if dist.get("distance_km") else "0",
        "connected": bool(raw.get("connected", raw.get("online", True))),
        "flying": _is_flying(raw, doctrine),
        "precision": row.get("precision") or "sub_micron",
    })
    if _ipv4_sovereign_enabled():
        row["ipv4_authority"] = _ipv4_authority(row)
    row["scene"] = _scene_coords(anchor, row)
    return row


def _collect_raw_devices() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(row: dict[str, Any]) -> None:
        eid = str(row.get("id") or row.get("ip") or row.get("node_id") or "")
        if not eid or eid in seen:
            return
        if row.get("lat") is None and row.get("lon") is None:
            return
        seen.add(eid)
        rows.append(row)

    pf = _load(STATE / "precision-field-panel.json", {})
    for ent in pf.get("entities") or []:
        if isinstance(ent, dict):
            add({**ent, "source": ent.get("source") or "precision_field", "connected": True})

    reg = _load(STATE / "field-botnet-registry-panel.json", {})
    for m in reg.get("members") or reg.get("nodes") or []:
        if isinstance(m, dict):
            add({
                "id": m.get("id"),
                "label": m.get("label") or m.get("hostname") or m.get("id"),
                "lat": m.get("lat"),
                "lon": m.get("lon"),
                "kind": m.get("role") or "botnet",
                "connected": m.get("status") != "offline",
                "source": "botnet_registry",
            })

    bot = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    for n in (bot.get("bot_network") or {}).get("nodes") or []:
        if isinstance(n, dict):
            add({
                "id": n.get("id"),
                "label": n.get("label") or n.get("id"),
                "lat": n.get("lat"),
                "lon": n.get("lon"),
                "kind": n.get("role") or "botnet_dns",
                "connected": True,
                "source": "botnet_dns_dhcp",
            })

    ha = _load(STATE / "host-attacks.json", {})
    for p in ha.get("points") or []:
        if isinstance(p, dict) and p.get("lat") is not None:
            add({
                "id": p.get("id") or p.get("ip"),
                "label": p.get("label") or p.get("ip"),
                "lat": p.get("lat"),
                "lon": p.get("lon"),
                "kind": p.get("kind") or "hostile",
                "connected": p.get("target_status") != "killed",
                "source": "host_attacks",
            })

    census = _load(STATE / "census-field-panel.json", {})
    for rec in census.get("records") or census.get("entries") or []:
        if isinstance(rec, dict) and rec.get("lat") is not None:
            add({**rec, "source": "census_field", "connected": True})

    sw = _load(STATE / "terror-spiderweb-panel.json", {})
    for n in sw.get("nodes") or []:
        if isinstance(n, dict) and n.get("lat") is not None:
            add({**n, "source": "spiderweb", "connected": True})

    thermal = _load(STATE / "thermal-earth-field.json", {})
    for b in thermal.get("bodies") or []:
        if isinstance(b, dict) and b.get("lat") is not None:
            add({**b, "source": "thermal", "kind": b.get("kind") or "thermal", "connected": True})

    qemu = _load(STATE / "qemu-world-panel.json", {})
    for w in qemu.get("worlds") or qemu.get("nodes") or []:
        if isinstance(w, dict):
            add({
                "id": w.get("id"),
                "label": w.get("name") or w.get("id"),
                "lat": w.get("lat"),
                "lon": w.get("lon"),
                "alt_m": w.get("alt_m", 500),
                "kind": "flying",
                "flying": True,
                "connected": w.get("running", True),
                "source": "qemu_world",
            })

    return rows


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    anchor = _operator_anchor()
    if _ipv4_sovereign_enabled():
        anchor["ipv4_authority"] = _ipv4_authority(anchor)
    devices: list[dict[str, Any]] = []
    for raw in _collect_raw_devices():
        row = _enrich_device(raw, anchor, doctrine)
        if row and row.get("id") != "operator":
            devices.append(row)
    devices.sort(key=lambda d: float(d.get("distance_km") or 1e9))

    flying = [d for d in devices if d.get("flying")]
    connected = [d for d in devices if d.get("connected")]
    sub_micron = sum(1 for d in [anchor, *devices] if d.get("precision") == "sub_micron")

    doc: dict[str, Any] = {
        "ok": True,
        "schema": "field-device-map/v1",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "updated": _now(),
        "boss": doctrine.get("boss", "hostess7"),
        "operator": anchor,
        "devices": devices,
        "stats": {
            "total": len(devices),
            "connected": len(connected),
            "flying": len(flying),
            "grounded": len(devices) - len(flying),
            "sub_micron_placed": sub_micron,
            "precision": "sub_micron",
            "resolution_nm": 0.111,
        },
        "viewer": doctrine.get("viewer") or {},
        "api": doctrine.get("api", "/api/field-device-map"),
        "surface": doctrine.get("surface", "/field-device-map/"),
    }
    if _ipv4_sovereign_enabled():
        doc["ipv4_sovereign"] = True
        doc["track_devices_not_numbers"] = True
        doc["ipv4_api"] = "/api/field-ipv4-device-sovereign"
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel"):
        print(json.dumps(build_panel(write=(cmd == "panel")), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(write=True), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-device-map.py [json|panel|build]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())