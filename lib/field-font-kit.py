#!/usr/bin/env pythong
"""Field Font Kit (FFNT) — Amouranth Bold Professional SDF atlas + glyph manifest."""
from __future__ import annotations

import json
import math
import os
import struct
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-font-doctrine.json"
FONT_JSON = INSTALL / "data" / "field-font-amouranth-bold.json"
PANEL_JSON = STATE / "field-font-panel.json"
ATLAS_DIR = INSTALL / "panel" / "assets" / "fonts"

GLYPHS = tuple(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    + " .,;:!?-'\"()[]{}@#$%&*+/=<>"
)


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


def _glyph_bitmap(ch: str, size: int = 64) -> list[list[float]]:
    """Procedural bold professional glyph mask (0..1)."""
    grid = [[0.0] * size for _ in range(size)]
    stroke = max(4, size // 8)
    margin = size // 8

    def fill_rect(x0: int, y0: int, x1: int, y1: int, v: float = 1.0) -> None:
        for y in range(max(0, y0), min(size, y1)):
            for x in range(max(0, x0), min(size, x1)):
                grid[y][x] = max(grid[y][x], v)

    if ch == " ":
        return grid
    if ch.isalpha() or ch.isdigit():
        fill_rect(margin, margin, size - margin, size - margin, 0.15)
        fill_rect(margin + stroke // 2, margin + stroke // 2, size - margin - stroke // 2, size - margin - stroke // 2, 1.0)
        cx, cy = size // 2, size // 2
        if ch in "AEIOU":
            fill_rect(cx - stroke, margin + stroke, cx + stroke, size - margin - stroke, 0.85)
        if ch in "BDPQR":
            fill_rect(size - margin - stroke * 2, cy - stroke, size - margin, cy + stroke, 0.9)
        return grid
    if ch in ".,":
        fill_rect(size // 2 - stroke, size - margin - stroke * 2, size // 2 + stroke, size - margin, 1.0)
        return grid
    fill_rect(margin, margin, size - margin, size - margin, 0.9)
    return grid


def _bitmap_to_sdf(mask: list[list[float]], spread: int = 8) -> list[list[float]]:
    h, w = len(mask), len(mask[0])
    inf = 1e6
    dist_in = [[inf] * w for _ in range(h)]
    dist_out = [[inf] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if mask[y][x] >= 0.5:
                dist_in[y][x] = 0.0
            else:
                dist_out[y][x] = 0.0
    for _ in range(spread * 2):
        for y in range(h):
            for x in range(w):
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w:
                        dist_in[y][x] = min(dist_in[y][x], dist_in[ny][nx] + 1)
                        dist_out[y][x] = min(dist_out[y][x], dist_out[ny][nx] + 1)
    sdf = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if mask[y][x] >= 0.5:
                d = dist_out[y][x]
                sdf[y][x] = 0.5 + min(d, spread) / (2 * spread)
            else:
                d = dist_in[y][x]
                sdf[y][x] = 0.5 - min(d, spread) / (2 * spread)
    return sdf


def build_ffnt(*, cell: int = 64, atlas_cols: int = 16) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    spread = 8
    glyphs_meta: dict[str, Any] = {}
    atlas_w = cell * atlas_cols
    rows = math.ceil(len(GLYPHS) / atlas_cols)
    atlas_h = cell * rows

    try:
        from PIL import Image
    except ImportError:
        return {"ok": False, "error": "pillow_required"}

    atlas = Image.new("RGBA", (atlas_w, atlas_h), (128, 128, 128, 255))
    px = atlas.load()

    for idx, ch in enumerate(GLYPHS):
        col = idx % atlas_cols
        row = idx // atlas_cols
        ox, oy = col * cell, row * cell
        mask = _glyph_bitmap(ch, cell)
        sdf = _bitmap_to_sdf(mask, spread=spread)
        for y in range(cell):
            for x in range(cell):
                v = int(max(0, min(255, sdf[y][x] * 255)))
                px[ox + x, oy + y] = (v, v, v, 255)
        glyphs_meta[ch] = {
            "unicode": ord(ch),
            "advance": int(cell * 0.62),
            "bearing_x": 4,
            "bearing_y": 0,
            "width": cell,
            "height": cell,
            "sdf_rect": [ox, oy, cell, cell],
            "point_sizes": doctrine.get("point_sizes") or [12, 16, 24, 32, 48],
        }

    ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    atlas_path = ATLAS_DIR / "amouranth-bold-sdf.png"
    preview_path = ATLAS_DIR / "amouranth-bold-preview.png"
    atlas.save(atlas_path)
    preview = atlas.resize((atlas_w // 2, atlas_h // 2))
    preview.save(preview_path)

    doc = {
        "schema": "field-font-ffnt/v1",
        "family": "Amouranth",
        "style": "Bold Professional",
        "weight": 700,
        "units_per_em": 1000,
        "ascender": 800,
        "descender": -200,
        "line_gap": 200,
        "point_sizes": doctrine.get("point_sizes") or [8, 12, 16, 24, 32, 48, 72],
        "sdf": {
            "atlas": "/assets/fonts/amouranth-bold-sdf.png",
            "preview": "/assets/fonts/amouranth-bold-preview.png",
            "atlas_size": [atlas_w, atlas_h],
            "cell": cell,
            "spread": spread,
            "cols": atlas_cols,
        },
        "glyphs": glyphs_meta,
        "glyph_count": len(glyphs_meta),
    }
    FONT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "font": doc, "atlas": str(atlas_path), "font_json": str(FONT_JSON)}


def _save_panel(doc: dict[str, Any]) -> None:
    PANEL_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = PANEL_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL_JSON)


def font_panel() -> dict[str, Any]:
    font = _load(FONT_JSON, {})
    if not font.get("glyphs"):
        built = build_ffnt()
        font = built.get("font") or {}
    panel = {
        "schema": "field-font-panel/v1",
        "ok": bool(font.get("glyphs")),
        "font": font,
        "editor_url": "/field-font-editor",
        "glyph_count": font.get("glyph_count") or len(font.get("glyphs") or {}),
    }
    _save_panel(panel)
    return panel


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("build", "sdf", "publish"):
        print(json.dumps(build_ffnt(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("panel", "json"):
        print(json.dumps(font_panel(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["build", "panel"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())