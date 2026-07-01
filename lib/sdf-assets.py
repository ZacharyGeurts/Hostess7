#!/usr/bin/env pythong
"""NEXUS SDF asset generator — compact signed-distance imagery for the host attack map.

All panel map graphics ship as R8 SDF PNG + JSON manifest (anchor, pointy-tip accuracy).
"""
from __future__ import annotations

import json
import math
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "panel" / "assets" / "sdf"
GEO_DIR = ROOT / "panel" / "assets" / "geo"
EARTH_SRC = ROOT / "panel" / "assets" / "earth-satellite-2k.jpg"
NE_COUNTRIES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_0_countries.geojson"
)
NE_STATES_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_1_states_provinces.geojson"
)


def _save_r8_png(path: Path, field: np.ndarray) -> None:
    """Save normalized SDF as 8-bit PNG (128 = surface, <128 inside, >128 outside)."""
    arr = np.clip((field * 64.0) + 128.0, 0, 255).astype(np.uint8)
    Image.fromarray(arr, mode="L").save(path, optimize=True)


def _save_meta(path: Path, meta: dict) -> None:
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def _analytic_pin_sdf(w: int, h: int) -> tuple[np.ndarray, list[int]]:
    """Big pointy map pin — anchor at tip (bottom center) for geo accuracy."""
    anchor = [w // 2, h - 1]
    head_cx = 0.5
    head_cy = 0.26
    head_r = 0.19
    tip_x = 0.5
    tip_y = 0.98
    neck_y = 0.46

    ys, xs = np.mgrid[0:h, 0:w]
    nx = (xs + 0.5) / w
    ny = (ys + 0.5) / h

    d_head = np.sqrt((nx - head_cx) ** 2 + (ny - head_cy) ** 2) - head_r

    # Cone body: distance to two lines forming pin shaft + tip
    def _line_dist(px: np.ndarray, py: np.ndarray, x0: float, y0: float, x1: float, y1: float) -> np.ndarray:
        dx = x1 - x0
        dy = y1 - y0
        t = np.clip(((px - x0) * dx + (py - y0) * dy) / (dx * dx + dy * dy + 1e-9), 0.0, 1.0)
        lx = x0 + t * dx
        ly = y0 + t * dy
        return np.sqrt((px - lx) ** 2 + (py - ly) ** 2)

    left = _line_dist(nx, ny, head_cx - head_r * 0.55, neck_y, tip_x, tip_y)
    right = _line_dist(nx, ny, head_cx + head_r * 0.55, neck_y, tip_x, tip_y)
    base = np.maximum(ny - neck_y, 0.0) * 3.0
    d_body = np.maximum(np.maximum(left, right), base)

    inside_head = d_head < 0
    inside_body = (ny >= neck_y) & (nx >= tip_x - (tip_y - ny) * 0.35) & (nx <= tip_x + (tip_y - ny) * 0.35)
    inside = inside_head | inside_body

    d = np.where(inside, -np.minimum(-d_head, d_body + 0.02), np.minimum(d_head, d_body))
    return d.astype(np.float32), anchor


def _ring_sdf(size: int) -> np.ndarray:
    cx = cy = (size - 1) / 2.0
    r = size * 0.34
    w = size * 0.08
    ys, xs = np.mgrid[0:size, 0:size]
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    return (np.abs(dist - r) - w / 2.0).astype(np.float32)


def _antenna_bloom_sdf(size: int) -> np.ndarray:
    """Soft radial bloom for antenna field pulses."""
    cx = cy = (size - 1) / 2.0
    ys, xs = np.mgrid[0:size, 0:size]
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2).astype(np.float32)
    r = size * 0.42
    soft = r * (1.0 - np.exp(-dist / max(size * 0.18, 1.0)))
    return (dist - soft).astype(np.float32)


def _field_wave_sdf(size: int) -> np.ndarray:
    """Concentric wave interference pattern for signal fields."""
    cx = cy = (size - 1) / 2.0
    ys, xs = np.mgrid[0:size, 0:size]
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2).astype(np.float32)
    wave = np.sin(dist / max(size, 1) * 22.0) * 0.55
    return (dist / max(size, 1) * 0.82 + wave - 0.32).astype(np.float32)


def _dot_sdf(size: int) -> np.ndarray:
    cx = cy = (size - 1) / 2.0
    r = size * 0.38
    ys, xs = np.mgrid[0:size, 0:size]
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    return (dist - r).astype(np.float32)


def _ensure_geojson(name: str, url: str) -> Path:
    GEO_DIR.mkdir(parents=True, exist_ok=True)
    dest = GEO_DIR / name
    if dest.is_file() and dest.stat().st_size > 1000:
        return dest
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-SDF-Builder"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dest.write_bytes(resp.read())
    except (OSError, urllib.error.URLError):
        if not dest.is_file():
            dest.write_text('{"type":"FeatureCollection","features":[]}\n', encoding="utf-8")
    return dest


def _lonlat_to_px(lon: float, lat: float, w: int, h: int) -> tuple[float, float]:
    x = (lon + 180.0) / 360.0 * (w - 1)
    y = (90.0 - lat) / 180.0 * (h - 1)
    return x, y


def _draw_geo_rings(draw: ImageDraw.ImageDraw, geom: dict, w: int, h: int) -> None:
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not coords:
        return

    def _ring(ring: list) -> None:
        if len(ring) < 2:
            return
        pts = [_lonlat_to_px(lon, lat, w, h) for lon, lat in ring]
        draw.line(pts, fill=255, width=1)

    if gtype == "Polygon":
        for ring in coords:
            _ring(ring)
    elif gtype == "MultiPolygon":
        for poly in coords:
            for ring in poly:
                _ring(ring)
    elif gtype == "LineString":
        _ring(coords)


def _wireframe_sdf(w: int, h: int) -> np.ndarray:
    """Admin-0 country + admin-1 state/province borders → wireframe distance field."""
    countries = _ensure_geojson("ne_110m_admin_0_countries.geojson", NE_COUNTRIES_URL)
    states = _ensure_geojson("ne_110m_admin_1_states_provinces.geojson", NE_STATES_URL)
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    for path in (countries, states):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for feat in doc.get("features") or []:
            _draw_geo_rings(draw, feat.get("geometry") or {}, w, h)
    arr = np.asarray(mask, dtype=np.float32) / 255.0
    border = arr > 0.35
    try:
        from scipy.ndimage import distance_transform_edt  # type: ignore

        dist_in = distance_transform_edt(border)
        dist_out = distance_transform_edt(1.0 - border)
        field = (dist_out - dist_in).astype(np.float32)
    except ImportError:
        field = np.where(border, -2.0, 4.0).astype(np.float32)
    return field / max(w, h) * 14.0


def _globe_sdf_from_jpg(w: int = 512, h: int = 256) -> np.ndarray:
    """Coastline/edge SDF from offline earth image — compact storage, crisp at any zoom."""
    if not EARTH_SRC.is_file():
        ys, xs = np.mgrid[0:h, 0:w]
        land = (np.sin(xs / 18.0) * np.cos(ys / 11.0) > 0.15).astype(np.float32)
        from scipy.ndimage import distance_transform_edt  # type: ignore

        dist_in = distance_transform_edt(land)
        dist_out = distance_transform_edt(1.0 - land)
        return (dist_out - dist_in).astype(np.float32) / max(w, h) * 8.0

    img = Image.open(EARTH_SRC).convert("L").resize((w, h), Image.Resampling.LANCZOS)
    gray = np.asarray(img, dtype=np.float32) / 255.0
    gx = np.zeros_like(gray)
    gy = np.zeros_like(gray)
    gx[:, 1:-1] = gray[:, 2:] - gray[:, :-2]
    gy[1:-1, :] = gray[2:, :] - gray[:-2, :]
    edge = np.sqrt(gx * gx + gy * gy)
    edge = (edge > 0.08).astype(np.float32)

    try:
        from scipy.ndimage import distance_transform_edt  # type: ignore

        dist_in = distance_transform_edt(edge)
        dist_out = distance_transform_edt(1.0 - edge)
        field = (dist_out - dist_in).astype(np.float32)
    except ImportError:
        field = edge - 0.5

    return field / max(w, h) * 12.0


def _edt_fallback(inside: np.ndarray) -> np.ndarray:
    """Pure-numpy approximate EDT when scipy absent."""
    h, w = inside.shape
    out = np.full((h, w), 4.0, dtype=np.float32)
    out[inside] = -4.0
    return out


def build_assets() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"version": 1, "format": "r8", "assets": {}}

    pin_w, pin_h = 128, 192
    pin_field, pin_anchor = _analytic_pin_sdf(pin_w, pin_h)
    for name in ("pin-hostile", "pin-killed", "pin-friendly"):
        png = OUT / f"{name}.sdf.png"
        meta_path = OUT / f"{name}.sdf.json"
        _save_r8_png(png, pin_field)
        meta = {
            "id": name,
            "width": pin_w,
            "height": pin_h,
            "anchor": pin_anchor,
            "pointy_tip": True,
            "format": "r8",
            "file": f"/assets/sdf/{name}.sdf.png",
            "display_scale": 1.05 if name == "pin-hostile" else 0.95,
        }
        _save_meta(meta_path, meta)
        manifest["assets"][name] = meta

    ring_size = 64
    ring_field = _ring_sdf(ring_size)
    _save_r8_png(OUT / "ring-pulse.sdf.png", ring_field)
    ring_meta = {
        "id": "ring-pulse",
        "width": ring_size,
        "height": ring_size,
        "anchor": [ring_size // 2, ring_size // 2],
        "format": "r8",
        "file": "/assets/sdf/ring-pulse.sdf.png",
        "display_scale": 1.0,
    }
    _save_meta(OUT / "ring-pulse.sdf.json", ring_meta)
    manifest["assets"]["ring-pulse"] = ring_meta

    dot_size = 32
    dot_field = _dot_sdf(dot_size)
    _save_r8_png(OUT / "legend-dot.sdf.png", dot_field)
    dot_meta = {
        "id": "legend-dot",
        "width": dot_size,
        "height": dot_size,
        "anchor": [dot_size // 2, dot_size // 2],
        "format": "r8",
        "file": "/assets/sdf/legend-dot.sdf.png",
        "display_scale": 0.35,
    }
    _save_meta(OUT / "legend-dot.sdf.json", dot_meta)
    manifest["assets"]["legend-dot"] = dot_meta

    bloom_size = 128
    bloom_field = _antenna_bloom_sdf(bloom_size)
    _save_r8_png(OUT / "antenna-bloom.sdf.png", bloom_field)
    bloom_meta = {
        "id": "antenna-bloom",
        "width": bloom_size,
        "height": bloom_size,
        "anchor": [bloom_size // 2, bloom_size // 2],
        "format": "r8",
        "file": "/assets/sdf/antenna-bloom.sdf.png",
        "display_scale": 1.2,
        "animated": True,
    }
    _save_meta(OUT / "antenna-bloom.sdf.json", bloom_meta)
    manifest["assets"]["antenna-bloom"] = bloom_meta

    wave_size = 96
    wave_field = _field_wave_sdf(wave_size)
    _save_r8_png(OUT / "field-wave.sdf.png", wave_field)
    wave_meta = {
        "id": "field-wave",
        "width": wave_size,
        "height": wave_size,
        "anchor": [wave_size // 2, wave_size // 2],
        "format": "r8",
        "file": "/assets/sdf/field-wave.sdf.png",
        "display_scale": 1.0,
        "animated": True,
    }
    _save_meta(OUT / "field-wave.sdf.json", wave_meta)
    manifest["assets"]["field-wave"] = wave_meta

    gw, gh = 1024, 512
    globe_field = _globe_sdf_from_jpg(gw, gh)
    _save_r8_png(OUT / "globe-world.sdf.png", globe_field)
    globe_meta = {
        "id": "globe-world",
        "width": gw,
        "height": gh,
        "anchor": [0, 0],
        "bounds": [[-90, -180], [90, 180]],
        "format": "r8",
        "file": "/assets/sdf/globe-world.sdf.png",
        "equirectangular": True,
    }
    _save_meta(OUT / "globe-world.sdf.json", globe_meta)
    manifest["assets"]["globe-world"] = globe_meta

    wire_field = _wireframe_sdf(gw, gh)
    _save_r8_png(OUT / "globe-wireframe.sdf.png", wire_field)
    wire_meta = {
        "id": "globe-wireframe",
        "width": gw,
        "height": gh,
        "anchor": [0, 0],
        "bounds": [[-90, -180], [90, 180]],
        "format": "r8",
        "file": "/assets/sdf/globe-wireframe.sdf.png",
        "equirectangular": True,
        "wireframe": True,
        "source": "Natural Earth 110m admin-0 + admin-1",
    }
    _save_meta(OUT / "globe-wireframe.sdf.json", wire_meta)
    manifest["assets"]["globe-wireframe"] = wire_meta

    manifest_path = OUT / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    doc = build_assets()
    print(json.dumps({"ok": True, "assets": list(doc["assets"].keys()), "out": str(OUT)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())