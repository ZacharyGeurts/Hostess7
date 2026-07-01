#!/usr/bin/env python3
"""Final Eye GPS navigation — sub-micron place + heading, azimuth, bearing per capture."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import subprocess
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "final-eye-nav-doctrine.json"
NAV_STATE = STATE / "final-eye-nav-state.json"
NAV_PANEL = STATE / "final-eye-nav-panel.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(rel: str, name: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _norm_deg(deg: float | None) -> float | None:
    if deg is None:
        return None
    return float(deg) % 360.0


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(rlat2)
    y = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def _load_nav_state() -> dict[str, Any]:
    doc = _load_json(NAV_STATE, {})
    if not doc:
        return {"schema": "final-eye-nav-state/v1", "history": []}
    return doc


def _save_nav_state(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    _save_json(NAV_STATE, doc)


def _operator_location() -> dict[str, Any]:
    op = _import_mod("operator-location.py", "fe_nav_op_loc")
    if op and hasattr(op, "panel_json"):
        try:
            doc = op.panel_json()
            if doc.get("lat") is not None and doc.get("lon") is not None:
                return doc
        except Exception:
            pass
    seed = _import_mod("operator-default.py", "fe_nav_op_default")
    if seed and hasattr(seed, "seed_operator_location"):
        try:
            return seed.seed_operator_location()
        except Exception:
            pass
    return {"lat": 45.845976, "lon": -87.055759, "label": "Gladstone MI", "source": "default"}


def _try_gpsd() -> dict[str, Any] | None:
    """One-shot gpsd fix via gpspipe when available."""
    if not subprocess.run(["which", "gpspipe"], capture_output=True).returncode == 0:
        return None
    try:
        proc = subprocess.run(
            ["gpspipe", "-w", "-n", "8"],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    fix: dict[str, Any] = {}
    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        cls = row.get("class")
        if cls == "TPV":
            if row.get("mode", 0) >= 2:
                fix.update({
                    "lat": row.get("lat"),
                    "lon": row.get("lon"),
                    "speed_mps": row.get("speed"),
                    "course_deg": row.get("track"),
                    "heading_deg": row.get("track"),
                    "altitude_m": row.get("alt"),
                    "accuracy_m": row.get("eph"),
                    "source": "gpsd",
                })
        elif cls == "ATT":
            fix.setdefault("pitch_deg", row.get("pitch"))
            fix.setdefault("roll_deg", row.get("roll"))
            fix.setdefault("heading_deg", row.get("heading"))
            fix.setdefault("source", "gpsd")
    if fix.get("lat") is None or fix.get("lon") is None:
        return None
    return fix


def _try_compass() -> dict[str, Any] | None:
    """Linux IIO magnetometer heading when exposed."""
    iio = Path("/sys/bus/iio/devices")
    if not iio.is_dir():
        return None
    for dev in sorted(iio.iterdir()):
        if not dev.name.startswith("iio:"):
            continue
        try:
            names = (dev / "name").read_text(encoding="utf-8").strip().lower()
        except OSError:
            names = ""
        if "mag" not in names and "compass" not in names:
            continue
        axes: dict[str, float] = {}
        for axis in ("x", "y", "z"):
            for pat in (f"in_magn_{axis}_raw", f"in_mag_{axis}_raw"):
                p = dev / pat
                if p.is_file():
                    try:
                        axes[axis] = float(p.read_text(encoding="utf-8").strip())
                    except (OSError, ValueError):
                        pass
                    break
        if "x" in axes and "y" in axes:
            heading = math.degrees(math.atan2(axes["y"], axes["x"]))
            return {
                "heading_deg": _norm_deg(heading),
                "source": "compass",
                "compass_device": dev.name,
            }
    return None


def _gaze_azimuth_offset(eye_meta: dict[str, Any] | None) -> float:
    """Approximate horizontal look offset from stereo rig eye offsets."""
    if not eye_meta:
        return 0.0
    eyes = eye_meta.get("eyes") or []
    if not eyes:
        return 0.0
    active = next((e for e in eyes if e.get("role") in ("center", "left") and e.get("perceived")), eyes[0])
    offset_x = float(active.get("offset_x") or 0.0)
    stereo = eye_meta.get("stereo") or {}
    fov_h = float(stereo.get("fov_h_deg") or 60.0)
    baseline = max(float(stereo.get("baseline_mm") or 63.0), 1.0)
    gaze = (offset_x / baseline) * (fov_h * 0.15)
    disp = float((stereo.get("disparity_mean") or 0.0))
    if disp > 8.0:
        gaze += min(12.0, disp * 0.04)
    return max(-fov_h * 0.45, min(fov_h * 0.45, gaze))


def _precision_place(lat: float, lon: float, *, source: str, label: str = "") -> dict[str, Any]:
    gps = _import_mod("gps-precision.py", "fe_nav_gps_precision")
    if gps and hasattr(gps, "placement_from_detected"):
        try:
            return gps.placement_from_detected(lat, lon, source=source, label=label)
        except Exception:
            pass
    return {
        "lat": lat,
        "lon": lon,
        "lat_str": f"{lat:.15f}",
        "lon_str": f"{lon:.15f}",
        "precision": "standard",
        "source": source,
        "label": label,
    }


def _course_from_history(lat: float, lon: float, st: dict[str, Any]) -> float | None:
    hist = st.get("history") or []
    if not hist:
        return None
    prev = hist[-1]
    plat, plon = prev.get("lat"), prev.get("lon")
    if plat is None or plon is None:
        return None
    if abs(float(plat) - lat) < 1e-9 and abs(float(plon) - lon) < 1e-9:
        return prev.get("course_deg")
    return round(_bearing_deg(float(plat), float(plon), lat, lon), 2)


def _nav_visibility(accuracy_m: float | None, *, source: str = "") -> float:
    if source == "gpsd":
        base = 0.8
    else:
        base = 0.6
    if accuracy_m is None:
        return base
    return max(0.0, min(1.0, base - float(accuracy_m) / 120.0))


def _last_known_nav_fallback(st: dict[str, Any], op: dict[str, Any]) -> dict[str, Any] | None:
    lat = st.get("last_lat")
    lon = st.get("last_lon")
    if lat is None or lon is None:
        hist = st.get("history") or []
        if hist:
            lat = hist[-1].get("lat")
            lon = hist[-1].get("lon")
    if lat is None or lon is None:
        if op.get("lat") is not None and op.get("lon") is not None:
            lat = float(op["lat"])
            lon = float(op["lon"])
        else:
            return None
    heading = st.get("last_heading_deg") or st.get("manual_heading_deg") or st.get("last_course_deg")
    return {
        "lat": float(lat),
        "lon": float(lon),
        "label": op.get("label") or "last_known",
        "source": "last_known_map",
        "heading_deg": heading,
        "course_deg": st.get("last_course_deg"),
        "accuracy_m": None,
    }


def _touch_component_whole(live: dict[str, Any], visibility: float) -> None:
    try:
        wholes = _import_mod("field-body-component-wholes.py", "fe_nav_wholes")
        if wholes and hasattr(wholes, "update_component"):
            wholes.update_component("nav", live=live, visibility=visibility, source="final-eye-gps-nav")
    except Exception:
        pass


def _update_history(lat: float, lon: float, course: float | None, st: dict[str, Any]) -> None:
    hist: list[dict[str, Any]] = list(st.get("history") or [])
    hist.append({"ts": _now(), "lat": lat, "lon": lon, "course_deg": course})
    st["history"] = hist[-32:]
    st["last_lat"] = lat
    st["last_lon"] = lon
    if course is not None:
        st["last_course_deg"] = course


def nav_snapshot(
    *,
    eye_meta: dict[str, Any] | None = None,
    target_lat: float | None = None,
    target_lon: float | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full navigation receipt for a Final Eye capture."""
    st = _load_nav_state()
    sources: list[str] = []

    fix = _try_gpsd()
    if fix:
        sources.append("gpsd")
    op = _operator_location()
    if not fix:
        if op.get("lat") is not None and op.get("lon") is not None:
            fix = {
                "lat": float(op["lat"]),
                "lon": float(op["lon"]),
                "label": op.get("label") or "",
                "source": op.get("source") or "operator",
                "altitude_m": op.get("alt_m"),
            }
            sources.append(str(fix["source"]))

    serving_mode = "live"
    if not fix or fix.get("lat") is None or fix.get("lon") is None:
        fix = _last_known_nav_fallback(st, op)
        if not fix:
            return {
                "schema": "final-eye-nav/v1",
                "ok": False,
                "error": "no_gps_fix",
                "sources": sources,
            }
        serving_mode = "last_known_map"
        sources.append("last_known_map")

    lat = float(fix["lat"])
    lon = float(fix["lon"])
    label = str(fix.get("label") or op.get("label") or "")
    place = _precision_place(lat, lon, source=str(fix.get("source") or "detected"), label=label)

    heading = fix.get("heading_deg")
    if heading is not None:
        heading = _norm_deg(float(heading))
        sources.append("gpsd_track")
    compass = _try_compass()
    if heading is None and compass:
        heading = compass.get("heading_deg")
        sources.append("compass")
    manual = st.get("manual_heading_deg")
    if heading is None and manual is not None:
        heading = _norm_deg(float(manual))
        sources.append("manual")

    course = fix.get("course_deg")
    if course is not None:
        course = _norm_deg(float(course))
    else:
        course = _course_from_history(lat, lon, st)
        if course is not None:
            sources.append("course_history")

    speed = fix.get("speed_mps")
    if speed is not None:
        try:
            speed = round(float(speed), 3)
        except (TypeError, ValueError):
            speed = None

    gaze = _gaze_azimuth_offset(eye_meta)
    azimuth = _norm_deg((heading or course or 0.0) + gaze) if (heading is not None or course is not None) else _norm_deg(gaze) if gaze else None
    if gaze and "gaze_offset" not in sources:
        sources.append("gaze_offset")

    bearing: float | None = None
    if target_lat is not None and target_lon is not None:
        bearing = round(_bearing_deg(lat, lon, float(target_lat), float(target_lon)), 2)
        sources.append("target_bearing")
    elif course is not None:
        bearing = course

    accuracy = fix.get("accuracy_m")
    if accuracy is not None:
        try:
            accuracy = round(float(accuracy), 2)
        except (TypeError, ValueError):
            accuracy = None

    altitude = fix.get("altitude_m")
    if altitude is not None:
        try:
            altitude = round(float(altitude), 2)
        except (TypeError, ValueError):
            altitude = None

    pitch = fix.get("pitch_deg")
    roll = fix.get("roll_deg")

    visibility = _nav_visibility(accuracy, source=str(fix.get("source") or ""))
    if serving_mode == "live" and visibility < 0.4:
        lk = _last_known_nav_fallback(st, op)
        if lk and (lk.get("lat"), lk.get("lon")) != (lat, lon):
            serving_mode = "degraded"
            sources.append("degraded_live")
        elif visibility < 0.35:
            serving_mode = "last_known_map"
            fb = _last_known_nav_fallback(st, op)
            if fb:
                lat = float(fb["lat"])
                lon = float(fb["lon"])
                label = str(fb.get("label") or label)
                place = _precision_place(lat, lon, source="last_known_map", label=label)
                if fb.get("heading_deg") is not None:
                    heading = _norm_deg(float(fb["heading_deg"]))
                sources.append("last_known_map")

    if serving_mode == "live":
        _update_history(lat, lon, course, st)
    if heading is not None:
        st["last_heading_deg"] = heading
    _save_nav_state(st)

    receipt: dict[str, Any] = {
        "schema": "final-eye-nav/v1",
        "ok": True,
        "ts": _now(),
        "mode": serving_mode,
        "visibility": round(visibility, 3),
        "label": label,
        "heading_deg": round(heading, 2) if heading is not None else None,
        "azimuth_deg": round(azimuth, 2) if azimuth is not None else None,
        "bearing_deg": bearing,
        "course_deg": round(course, 2) if course is not None else None,
        "pitch_deg": round(float(pitch), 2) if pitch is not None else None,
        "roll_deg": round(float(roll), 2) if roll is not None else None,
        "accuracy_m": accuracy,
        "speed_mps": speed,
        "altitude_m": altitude,
        "gaze_offset_deg": round(gaze, 2),
        "sources": sorted(set(sources)),
        "primary_source": fix.get("source") or "operator",
        "operator": {
            "label": op.get("label"),
            "source": op.get("source"),
            "wireless": op.get("wireless"),
        },
        "precision": place.get("precision"),
        "resolution_nm": place.get("resolution_nm"),
    }
    receipt.update({k: place[k] for k in ("lat", "lon", "lat_str", "lon_str", "lat_i", "lon_i", "enu_e_nm", "enu_n_nm", "enu_u_nm", "anchor_id") if k in place})
    if extra:
        receipt["extra"] = extra
    _touch_component_whole(receipt, visibility)
    return receipt


def enrich_capture_meta(meta: dict[str, Any] | None, *, eye_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge nav receipt into capture meta — lat/lon for spatial look pairing."""
    out = dict(meta or {})
    nav = nav_snapshot(eye_meta=eye_meta or out.get("eye"))
    out["nav"] = nav
    if nav.get("ok"):
        for key in ("lat", "lon", "lat_str", "lon_str", "heading_deg", "azimuth_deg", "bearing_deg", "course_deg", "accuracy_m"):
            if nav.get(key) is not None and key not in out:
                out[key] = nav[key]
    return out


def set_heading(heading_deg: float) -> dict[str, Any]:
    st = _load_nav_state()
    st["manual_heading_deg"] = _norm_deg(float(heading_deg))
    _save_nav_state(st)
    return {"ok": True, "manual_heading_deg": st["manual_heading_deg"], "updated": st["updated"]}


def panel_json() -> dict[str, Any]:
    doctrine = _load_json(DOCTRINE, {})
    snap = nav_snapshot()
    doc = {
        "schema": "final-eye-nav-panel/v1",
        "ok": True,
        "motto": doctrine.get("motto"),
        "doctrine": str(DOCTRINE),
        "snapshot": snap,
        "state_path": str(NAV_STATE),
        "receipt_fields": doctrine.get("receipt_fields") or [],
        "updated": _now(),
    }
    _save_json(NAV_PANEL, doc)
    return doc


def append_h7s_feed(
    image_path: Path,
    *,
    text: str = "",
    meta: dict[str, Any] | None = None,
    feed_id: str | None = None,
) -> dict[str, Any] | None:
    """Append capture to desktop H7s live feed with nav meta."""
    if not image_path.is_file():
        return None
    doctrine = _load_json(DOCTRINE, {})
    fid = feed_id or doctrine.get("h7s_feed") or "desktop-live"
    bundle = _import_mod("field-h7s-desktop-bundle.py", "fe_nav_h7s_bundle")
    if not bundle or not hasattr(bundle, "append_feed_capture"):
        return None
    try:
        img = image_path.read_bytes()
        txt = text.encode("utf-8") if text else None
        return bundle.append_feed_capture(fid, img, text=txt, meta=meta)
    except Exception:
        return None


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "snapshot":
        print(json.dumps(nav_snapshot(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "set-heading" and len(sys.argv) >= 3:
        print(json.dumps(set_heading(float(sys.argv[2])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "enrich" and len(sys.argv) >= 3:
        meta = json.loads(sys.argv[2])
        print(json.dumps(enrich_capture_meta(meta), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: final-eye-gps-nav.py [json|snapshot|set-heading DEG|enrich JSON_META]",
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())