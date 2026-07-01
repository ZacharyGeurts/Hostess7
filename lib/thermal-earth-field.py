#!/usr/bin/env pythong
"""Thermal Earth field — SDF temperature grid, OCR body identification, warm/cold registry.

Top-down equirectangular temperature SDF + 3D globe sampling. Every warm and cold body
on the planet from Open-Meteo, field registry heat, hostility, batteries, and OCR vision.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
OUT_JSON = STATE / "thermal-earth-field.json"
OUT_BODIES = STATE / "thermal-bodies-registry.json"
SDF_DIR = INSTALL / "panel" / "assets" / "sdf"
THERMAL_PNG = SDF_DIR / "earth-thermal.sdf.png"
THERMAL_META = SDF_DIR / "earth-thermal.sdf.json"
OCR_IMAGE_DIR = STATE / "thermal-ocr-images"
PANEL_CACHE = STATE / "thermal-earth-panel.json"

UA = "NEXUS-Shield/5.9.6"
GRID_LAT_STEP = 30
GRID_LON_STEP = 30
WARM_COLD_DELTA_C = 4.0

OCR_WARM_TERMS = re.compile(
    r"\b(heat|hot|warm|energy|casimir|vacuum|active|physics|sigma|timeline|local\s*now)\b",
    re.I,
)
OCR_COLD_TERMS = re.compile(
    r"\b(cold|cool|freeze|ice|vacuum\s*energy|zero|absent|void)\b",
    re.I,
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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _body_id(kind: str, lat: float, lon: float, label: str) -> str:
    blob = f"{kind}:{lat:.4f}:{lon:.4f}:{label}".encode("utf-8")
    return "tb_" + hashlib.sha256(blob).hexdigest()[:16]


def _fetch_temp_c(lat: float, lon: float) -> float | None:
    params = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "current": "temperature_2m",
        "temperature_unit": "celsius",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        return float(data.get("current", {}).get("temperature_2m"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError, TypeError, ValueError):
        return None


def _grid_sample_points() -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []
    lat = -60.0
    while lat <= 75.0:
        lon = -180.0
        while lon < 180.0:
            pts.append((round(lat, 2), round(lon, 2)))
            lon += GRID_LON_STEP
        lat += GRID_LAT_STEP
    return pts


def _registry_sample_points() -> list[dict[str, Any]]:
    pts: list[dict[str, Any]] = []
    reg = _load_json(STATE / "universal-field-registry.json", {})
    panel = _load_json(STATE / "threat-panel.json", {})
    for section, key in (("homes", "home"), ("internet", "internet"), ("mobile", "mobile"), ("batteries", "battery")):
        for row in reg.get(section) or []:
            if not isinstance(row, dict):
                continue
            lat = row.get("lat")
            lon = row.get("lon")
            try:
                lat_f = float(lat)
                lon_f = float(lon)
            except (TypeError, ValueError):
                continue
            heat = 0.0
            if section == "internet":
                heat = float((row.get("meta") or {}).get("heat") or 0)
                if row.get("kind") in ("terror", "hostile"):
                    heat = max(heat, 0.75)
            if section == "batteries":
                cap = row.get("capacity_pct")
                try:
                    heat = float(cap or 0) / 100.0
                except (TypeError, ValueError):
                    heat = 0.3
            pts.append({
                "lat": lat_f,
                "lon": lon_f,
                "label": row.get("label") or row.get("id") or key,
                "source": f"registry_{section}",
                "heat_bias": heat,
                "kind": row.get("kind") or key,
            })
    for p in (panel.get("host_attacks") or {}).get("points") or []:
        if not isinstance(p, dict):
            continue
        try:
            lat_f = float(p.get("lat"))
            lon_f = float(p.get("lon"))
        except (TypeError, ValueError):
            continue
        pts.append({
            "lat": lat_f,
            "lon": lon_f,
            "label": p.get("label") or p.get("ip") or "attack",
            "source": "host_attacks",
            "heat_bias": float(p.get("heat") or 0.8),
            "kind": "terror",
        })
    op = _load_json(STATE / "operator-location.json", {})
    if op.get("lat") is not None and op.get("lon") is not None:
        pts.append({
            "lat": float(op["lat"]),
            "lon": float(op["lon"]),
            "label": op.get("label") or "Operator",
            "source": "operator",
            "heat_bias": 0.55,
            "kind": "home",
        })
    return pts


def _ocr_images() -> list[dict[str, Any]]:
    OCR_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    out: list[dict[str, Any]] = []
    core_py = INSTALL / "lib" / "final-eye-ocr-core.py"
    for img in sorted(OCR_IMAGE_DIR.glob("*")):
        if img.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
            continue
        text = ""
        if core_py.is_file():
            try:
                ocr_mod = _mod("thermal_ocr_h7", "final-eye-ocr-core.py")
                if ocr_mod and hasattr(ocr_mod, "ocr_image_text"):
                    text = str(ocr_mod.ocr_image_text(img, via_hostess7=True) or "").strip()
            except Exception:
                pass
        warm_hits = len(OCR_WARM_TERMS.findall(text))
        cold_hits = len(OCR_COLD_TERMS.findall(text))
        polarity = "warm" if warm_hits >= cold_hits else "cold"
        if warm_hits == 0 and cold_hits == 0:
            polarity = "neutral"
        out.append({
            "image": str(img.name),
            "path": str(img),
            "ocr_text": text[:2400],
            "warm_hits": warm_hits,
            "cold_hits": cold_hits,
            "polarity": polarity,
            "sdf_field": "earth-thermal",
            "physics_terms": list(dict.fromkeys(
                OCR_WARM_TERMS.findall(text) + OCR_COLD_TERMS.findall(text)
            ))[:12],
        })
    return out


def _sample_temperature_field() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    cache = _load_json(STATE / "thermal-grid-cache.json", {"samples": [], "updated": None})
    samples: list[dict[str, Any]] = list(cache.get("samples") or [])
    cache_age_ok = False
    if cache.get("updated"):
        try:
            ts = datetime.strptime(str(cache["updated"]), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            cache_age_ok = (datetime.now(timezone.utc) - ts).total_seconds() < 3600
        except ValueError:
            pass

    if not samples or not cache_age_ok:
        samples = []
        seen: set[str] = set()
        for lat, lon in _grid_sample_points():
            key = f"{lat:.2f},{lon:.2f}"
            if key in seen:
                continue
            seen.add(key)
            temp = _fetch_temp_c(lat, lon)
            if temp is None:
                continue
            samples.append({"lat": lat, "lon": lon, "temp_c": round(temp, 2), "source": "open_meteo_grid"})
        for pt in _registry_sample_points():
            key = f"{pt['lat']:.4f},{pt['lon']:.4f}"
            if key in seen:
                continue
            seen.add(key)
            temp = _fetch_temp_c(pt["lat"], pt["lon"])
            if temp is None:
                continue
            bias = float(pt.get("heat_bias") or 0)
            adj = temp + bias * 6.0
            samples.append({
                "lat": pt["lat"],
                "lon": pt["lon"],
                "temp_c": round(adj, 2),
                "ambient_c": round(temp, 2),
                "source": pt.get("source") or "registry",
                "label": pt.get("label"),
                "heat_bias": bias,
            })
        _save_json(STATE / "thermal-grid-cache.json", {"updated": _now(), "samples": samples})

    temps = [float(s["temp_c"]) for s in samples if s.get("temp_c") is not None]
    median = sorted(temps)[len(temps) // 2] if temps else 15.0
    meta = {
        "sample_count": len(samples),
        "median_temp_c": round(median, 2),
        "min_temp_c": round(min(temps), 2) if temps else None,
        "max_temp_c": round(max(temps), 2) if temps else None,
    }
    return samples, meta


def _idw_temp(lat: float, lon: float, samples: list[dict[str, Any]]) -> float:
    num = den = 0.0
    for s in samples:
        try:
            slat = float(s["lat"])
            slon = float(s["lon"])
            st = float(s["temp_c"])
        except (KeyError, TypeError, ValueError):
            continue
        dlat = (lat - slat) * 111.0
        dlon = (lon - slon) * 111.0 * max(0.35, abs(math.cos(math.radians(lat))))
        dist = math.sqrt(dlat * dlat + dlon * dlon) + 0.05
        w = 1.0 / (dist ** 1.6)
        num += w * st
        den += w
    return num / den if den else 15.0


def _build_thermal_sdf(samples: list[dict[str, Any]], meta: dict[str, Any]) -> dict[str, Any]:
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        return {"ok": False, "error": "numpy_pillow_required"}

    gw, gh = 1024, 512
    temps = [float(s["temp_c"]) for s in samples if s.get("temp_c") is not None]
    tmin = min(temps) if temps else 0.0
    tmax = max(temps) if temps else 35.0
    span = max(1.0, tmax - tmin)
    field = np.zeros((gh, gw), dtype=np.float32)
    for y in range(gh):
        lat = 90.0 - (y + 0.5) / gh * 180.0
        for x in range(gw):
            lon = (x + 0.5) / gw * 360.0 - 180.0
            field[y, x] = (_idw_temp(lat, lon, samples) - tmin) / span

    arr = np.clip(field * 255.0, 0, 255).astype(np.uint8)
    SDF_DIR.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr, mode="L").save(THERMAL_PNG, optimize=True)
    thermal_meta = {
        "id": "earth-thermal",
        "width": gw,
        "height": gh,
        "anchor": [0, 0],
        "bounds": [[-90, -180], [90, 180]],
        "format": "r8",
        "file": "/assets/sdf/earth-thermal.sdf.png",
        "equirectangular": True,
        "thermal": True,
        "temp_min_c": round(tmin, 2),
        "temp_max_c": round(tmax, 2),
        "updated": _now(),
    }
    THERMAL_META.write_text(json.dumps(thermal_meta, indent=2) + "\n", encoding="utf-8")
    manifest_path = SDF_DIR / "manifest.json"
    manifest = _load_json(manifest_path, {"version": 1, "format": "r8", "assets": {}})
    manifest.setdefault("assets", {})["earth-thermal"] = thermal_meta
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(THERMAL_PNG), **thermal_meta}


def _classify_bodies(samples: list[dict[str, Any]], meta: dict[str, Any], ocr_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    median = float(meta.get("median_temp_c") or 15.0)
    bodies: list[dict[str, Any]] = []
    for s in samples:
        try:
            temp = float(s["temp_c"])
            lat = float(s["lat"])
            lon = float(s["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        delta = temp - median
        if delta >= WARM_COLD_DELTA_C or float(s.get("heat_bias") or 0) >= 0.65:
            kind = "warm"
        elif delta <= -WARM_COLD_DELTA_C:
            kind = "cold"
        else:
            kind = "neutral"
        if kind == "neutral" and not s.get("label"):
            continue
        label = str(s.get("label") or f"Grid {lat:.1f},{lon:.1f}")
        bodies.append({
            "id": _body_id(kind, lat, lon, label),
            "kind": kind,
            "temp_c": round(temp, 2),
            "delta_c": round(delta, 2),
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "label": label,
            "source": s.get("source") or "grid",
            "sdf_field": "earth-thermal",
            "ocr_corroborated": False,
            "placed": True,
        })

    op = _load_json(STATE / "operator-location.json", {})
    if op.get("lat") is not None:
        for ocr in ocr_rows:
            if ocr.get("polarity") in ("warm", "cold"):
                bodies.append({
                    "id": _body_id(ocr["polarity"], float(op["lat"]), float(op["lon"]), ocr["image"]),
                    "kind": ocr["polarity"],
                    "temp_c": None,
                    "delta_c": None,
                    "lat": float(op["lat"]),
                    "lon": float(op["lon"]),
                    "label": f"OCR {ocr['image']} — {ocr.get('polarity')} physics",
                    "source": "ocr_sdf",
                    "sdf_field": "earth-thermal",
                    "ocr_corroborated": True,
                    "ocr_snippet": (ocr.get("ocr_text") or "")[:240],
                    "physics_terms": ocr.get("physics_terms") or [],
                    "placed": True,
                })

    bodies.sort(key=lambda b: (
        0 if b.get("kind") == "warm" else (1 if b.get("kind") == "cold" else 2),
        -(abs(float(b.get("delta_c") or 0))),
    ))
    return bodies


def build_thermal_field(*, skip_network: bool = False) -> dict[str, Any]:
    ocr_rows = _ocr_images()
    if skip_network:
        samples = _load_json(STATE / "thermal-grid-cache.json", {}).get("samples") or []
        meta = {"sample_count": len(samples), "median_temp_c": 15.0, "cached": True}
    else:
        samples, meta = _sample_temperature_field()
    sdf_result = _build_thermal_sdf(samples, meta) if samples else {"ok": False}
    bodies = _classify_bodies(samples, meta, ocr_rows)
    warm = [b for b in bodies if b.get("kind") == "warm"]
    cold = [b for b in bodies if b.get("kind") == "cold"]

    doc = {
        "schema": "thermal-earth-field/v1",
        "updated": _now(),
        "motto": "TRUE REALITY MODEL — 3D space + linear time. Every warm and cold body on Earth via SDF + OCR.",
        "tagline": "Top-down temperature SDF · 3D globe thermal view · OCR physics corroboration.",
        "model": {
            "whole_timeline": "ds² metric — full timeline exists at all timestamps",
            "local_now": "Casimir vacuum energy — active physics at operator anchor",
        },
        "sdf": sdf_result,
        "field_meta": meta,
        "bodies": bodies,
        "stats": {
            "total_bodies": len(bodies),
            "warm_bodies": len(warm),
            "cold_bodies": len(cold),
            "neutral_bodies": len(bodies) - len(warm) - len(cold),
            "ocr_images": len(ocr_rows),
            "ocr_warm_cold": sum(1 for o in ocr_rows if o.get("polarity") in ("warm", "cold")),
            "grid_samples": len(samples),
        },
        "ocr": ocr_rows,
        "legend": {
            "warm": {"label": "Warm body", "color": "#ff5c3a"},
            "cold": {"label": "Cold body", "color": "#4d9bff"},
            "neutral": {"label": "Neutral", "color": "#9aa8be"},
        },
        "views": {
            "top_down": {"sdf": "earth-thermal", "projection": "equirectangular"},
            "globe_3d": {"sdf": "earth-thermal", "wireframe": "globe-wireframe", "land": "globe-world"},
        },
    }
    _save_json(OUT_JSON, doc)
    _save_json(OUT_BODIES, {"updated": _now(), "bodies": bodies, "stats": doc["stats"]})
    _save_json(PANEL_CACHE, doc)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL_CACHE.is_file():
        doc = _load_json(PANEL_CACHE, {})
        if doc.get("updated"):
            return doc
    return build_thermal_field()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        skip = os.environ.get("NEXUS_THERMAL_SKIP_NET", "") == "1"
        print(json.dumps(build_thermal_field(skip_network=skip), ensure_ascii=False))
        return 0
    if cmd == "bodies":
        doc = panel_json()
        print(json.dumps({"bodies": doc.get("bodies") or [], "stats": doc.get("stats") or {}}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: thermal-earth-field.py [json|build|bodies]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())