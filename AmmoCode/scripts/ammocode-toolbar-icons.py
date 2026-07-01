#!/usr/bin/env python3
"""AmmoCode toolbar icons — NEXUS C2 glyphs, sealed storage sync (queen-icon-kit pattern)."""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SG = Path(__import__("os").environ.get("SG_ROOT", ROOT.parent))
NEXUS = Path(__import__("os").environ.get("NEXUS_INSTALL_ROOT", SG / "AmmoOS"))
DOCTRINE = ROOT / "data" / "ammocode-toolbar-doctrine.json"
OUT = ROOT / "assets" / "icons" / "toolbar"
SEALED = NEXUS / "state" / "sealed" / "panel" / "assets" / "ammocode-toolbar"
SIZES = (16, 20, 24, 32)

DARK_FILL = (8, 16, 12, 255)
DARK_EDGE = (26, 77, 50, 255)
EMERALD = (62, 207, 142, 255)
ROSE = (244, 114, 182, 255)
GOLD = (184, 149, 106, 255)
WHITE = (230, 242, 234, 255)


def _plate(size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    m = max(1, size // 10)
    inner = size - 2 * m
    r = max(2, inner // 5)
    draw.rounded_rectangle((m, m, m + inner - 1, m + inner - 1), radius=r, fill=DARK_FILL, outline=DARK_EDGE, width=max(1, size // 32))
    ring = max(1, size // 24)
    draw.rounded_rectangle((m - ring, m - ring, m + inner - 1 + ring, m + inner - 1 + ring), radius=r + ring, outline=EMERALD, width=ring)
    return canvas


def _box(size: int) -> tuple[int, int, int, int]:
    m = max(3, size // 5)
    return (m, m, size - m, size - m)


def _draw(draw: ImageDraw.ImageDraw, tool_id: str, box: tuple[int, int, int, int], stroke: int) -> None:
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    w, h = x1 - x0, y1 - y0

    if tool_id == "new":
        draw.line([(cx, y0 + h // 5), (cx, y1 - h // 5)], fill=EMERALD, width=stroke)
        draw.line([(x0 + w // 5, cy), (x1 - w // 5, cy)], fill=EMERALD, width=stroke)
    elif tool_id == "open":
        draw.rectangle((x0 + w // 8, y0 + h // 6, x1 - w // 8, y1 - h // 8), outline=EMERALD, width=stroke)
        draw.polygon([(x0 + w // 4, y0 + h // 3), (x1 - w // 4, y0 + h // 3), (x1 - w // 5, cy), (x0 + w // 5, cy)], outline=ROSE, width=stroke)
    elif tool_id in ("save", "save_all"):
        draw.rectangle((x0 + w // 6, y0 + h // 5, x1 - w // 6, y1 - h // 6), outline=EMERALD, width=stroke)
        draw.rectangle((x0 + w // 4, y0 + h // 8, x1 - w // 4, y0 + h // 3), fill=EMERALD)
        if tool_id == "save_all":
            draw.rectangle((x0 + w // 3, y0 + h // 4, x1 - w // 5, y1 - h // 5), outline=ROSE, width=stroke)
    elif tool_id == "undo":
        draw.arc((x0, y0, x1, y1), 200, 340, fill=EMERALD, width=stroke)
        draw.polygon([(x0 + w // 4, cy), (x0 + w // 2, cy - h // 6), (x0 + w // 2, cy + h // 6)], fill=EMERALD)
    elif tool_id == "redo":
        draw.arc((x0, y0, x1, y1), 160, 300, fill=ROSE, width=stroke)
        draw.polygon([(x1 - w // 4, cy), (x1 - w // 2, cy - h // 6), (x1 - w // 2, cy + h // 6)], fill=ROSE)
    elif tool_id == "cut":
        draw.line([(x0 + w // 6, y1 - h // 6), (x1 - w // 6, y0 + h // 6)], fill=ROSE, width=stroke)
        draw.ellipse((x0 + w // 8, y0 + h // 8, cx, cy), outline=EMERALD, width=stroke)
        draw.ellipse((cx, cy, x1 - w // 8, y1 - h // 8), outline=EMERALD, width=stroke)
    elif tool_id == "copy":
        draw.rectangle((x0 + w // 5, y0 + h // 5, x1 - w // 4, y1 - h // 4), outline=EMERALD, width=stroke)
        draw.rectangle((x0 + w // 3, y0 + h // 3, x1 - w // 6, y1 - h // 6), outline=ROSE, width=stroke)
    elif tool_id == "paste":
        draw.rectangle((x0 + w // 6, y0 + h // 4, x1 - w // 6, y1 - h // 6), outline=EMERALD, width=stroke)
        draw.rectangle((x0 + w // 4, y0 + h // 6, x1 - w // 4, y0 + h // 3), fill=GOLD)
    elif tool_id == "find":
        draw.ellipse((x0 + w // 8, y0 + h // 8, cx + w // 8, cy + h // 8), outline=EMERALD, width=stroke)
        draw.line([(cx + w // 10, cy + h // 10), (x1 - w // 8, y1 - h // 8)], fill=ROSE, width=stroke)
    elif tool_id == "replace":
        _draw(draw, "find", box, stroke)
        draw.line([(x0 + w // 3, y1 - h // 4), (x1 - w // 3, y0 + h // 4)], fill=GOLD, width=stroke)
    elif tool_id == "comment":
        draw.rectangle((x0 + w // 6, y0 + h // 4, x1 - w // 6, y1 - h // 4), outline=EMERALD, width=stroke)
        draw.text((x0 + w // 5, cy - h // 8), "//", fill=GOLD)
    elif tool_id == "format":
        draw.line([(x0 + w // 4, cy), (x1 - w // 4, cy)], fill=WHITE, width=stroke)
        for i in range(3):
            draw.line([(x0 + w // 4 + i * w // 8, cy - h // 8), (x0 + w // 3 + i * w // 8, cy + h // 8)], fill=EMERALD, width=stroke)
    elif tool_id == "goto_line":
        draw.polygon([(cx, y0 + h // 6), (x1 - w // 5, cy), (cx, y1 - h // 6), (x0 + w // 5, cy)], outline=EMERALD, width=stroke)
        draw.line([(x0 + w // 4, cy), (x1 - w // 4, cy)], fill=ROSE, width=stroke)
    elif tool_id == "g16_check":
        draw.polygon([(x0 + w // 4, cy), (cx - w // 12, y1 - h // 4), (x1 - w // 5, y0 + h // 4)], outline=EMERALD, width=stroke)
    elif tool_id == "g16_build":
        draw.rectangle((x0 + w // 5, y0 + h // 4, x1 - w // 5, y1 - h // 4), outline=EMERALD, width=stroke)
        draw.text((x0 + w // 6, cy - h // 8), "g16", fill=GOLD)
    elif tool_id == "g16_run":
        draw.polygon([(x0 + w // 4, y0 + h // 5), (x0 + w // 4, y1 - h // 5), (x1 - w // 5, cy)], fill=ROSE)
    elif tool_id == "g16_profile":
        draw.ellipse((cx - w // 5, cy - h // 5, cx + w // 5, cy + h // 5), outline=EMERALD, width=stroke)
        draw.text((cx - w // 8, cy - h // 8), "G", fill=GOLD)
    elif tool_id == "launch_chamber":
        draw.polygon([(x0 + w // 3, y1 - h // 4), (x1 - w // 3, y1 - h // 4), (cx, y0 + h // 5)], outline=ROSE, width=stroke)
        draw.rectangle((x0 + w // 4, y1 - h // 3, x1 - w // 4, y1 - h // 6), fill=EMERALD)
    elif tool_id == "discern_lang":
        draw.ellipse((cx - w // 6, cy - h // 6, cx + w // 6, cy + h // 6), outline=EMERALD, width=stroke)
        for ang in range(0, 360, 72):
            rad = math.radians(ang)
            draw.line([(cx, cy), (cx + int(math.cos(rad) * w // 3), cy + int(math.sin(rad) * h // 3))], fill=ROSE, width=stroke)
    elif tool_id == "ironclad_verify":
        draw.polygon([(cx, y0 + h // 8), (x1 - w // 6, y0 + h // 3), (x1 - w // 5, y1 - h // 4), (cx, y1 - h // 8), (x0 + w // 5, y1 - h // 4), (x0 + w // 6, y0 + h // 3)], outline=EMERALD, width=stroke)
    elif tool_id == "path_jail":
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), outline=EMERALD, width=stroke)
        draw.rectangle((cx - w // 10, cy, cx + w // 10, y1 - h // 6), fill=ROSE)
        draw.arc((x0 + w // 4, y0 + h // 6, x1 - w // 4, cy), 180, 0, fill=GOLD, width=stroke)
    elif tool_id == "word_wrap":
        draw.arc((x0 + w // 6, y0 + h // 5, x1 - w // 6, y1 - h // 5), 0, 180, fill=EMERALD, width=stroke)
        draw.line([(x0 + w // 4, cy), (x1 - w // 4, cy)], fill=ROSE, width=stroke)
    elif tool_id == "font_dec":
        draw.text((x0 + w // 5, cy - h // 6), "A−", fill=EMERALD)
    elif tool_id == "font_inc":
        draw.text((x0 + w // 5, cy - h // 6), "A+", fill=EMERALD)
    elif tool_id == "minimap":
        draw.rectangle((x0 + w // 4, y0 + h // 6, x1 - w // 6, y1 - h // 6), outline=EMERALD, width=stroke)
        for i in range(4):
            draw.line([(x0 + w // 3, y0 + h // 5 + i * h // 6), (x1 - w // 4, y0 + h // 5 + i * h // 6)], fill=ROSE if i % 2 else GOLD, width=1)
    elif tool_id == "split_editor":
        draw.line([(cx, y0 + h // 6), (cx, y1 - h // 6)], fill=EMERALD, width=stroke)
        draw.rectangle((x0 + w // 8, y0 + h // 6, cx - w // 12, y1 - h // 6), outline=ROSE, width=stroke)
        draw.rectangle((cx + w // 12, y0 + h // 6, x1 - w // 8, y1 - h // 6), outline=ROSE, width=stroke)
    elif tool_id == "breadcrumbs":
        for i, col in enumerate((EMERALD, GOLD, ROSE)):
            draw.ellipse((x0 + w // 6 + i * w // 5, cy - h // 10, x0 + w // 4 + i * w // 5, cy + h // 10), fill=col)
        draw.line([(x0 + w // 5, cy), (x1 - w // 5, cy)], fill=WHITE, width=stroke)
    elif tool_id == "fullscreen":
        draw.polygon([(x0 + w // 5, y0 + h // 4), (x0 + w // 3, y0 + h // 4), (x0 + w // 3, y0 + h // 6), (x1 - w // 5, y0 + h // 6), (x1 - w // 5, y1 - h // 4), (x0 + w // 5, y1 - h // 4)], outline=EMERALD, width=stroke)
    elif tool_id == "theme":
        draw.pieslice((x0 + w // 8, y0 + h // 8, x1 - w // 8, y1 - h // 8), 0, 180, fill=EMERALD)
        draw.pieslice((x0 + w // 8, y0 + h // 8, x1 - w // 8, y1 - h // 8), 180, 360, fill=ROSE)
    elif tool_id == "syntax_theme":
        draw.rectangle((x0 + w // 6, y0 + h // 5, x1 - w // 6, y1 - h // 5), outline=EMERALD, width=stroke)
        draw.line([(x0 + w // 4, cy - h // 8), (x1 - w // 3, cy - h // 8)], fill=GOLD, width=stroke)
        draw.line([(x0 + w // 4, cy), (x1 - w // 4, cy)], fill=ROSE, width=stroke)
        draw.line([(x0 + w // 4, cy + h // 8), (x1 - w // 5, cy + h // 8)], fill=EMERALD, width=stroke)
    elif tool_id == "settings":
        for ang in range(0, 360, 60):
            rad = math.radians(ang)
            px = cx + int(math.cos(rad) * w // 4)
            py = cy + int(math.sin(rad) * h // 4)
            draw.ellipse((px - stroke, py - stroke, px + stroke, py + stroke), fill=EMERALD)
        draw.ellipse((cx - w // 8, cy - h // 8, cx + w // 8, cy + h // 8), outline=ROSE, width=stroke)
    elif tool_id == "terminal":
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), outline=EMERALD, width=stroke)
        draw.polygon([(x0 + w // 4, cy), (x0 + w // 2, cy - h // 6), (x0 + w // 2, cy + h // 6)], fill=ROSE)
        draw.line([(x0 + w // 2, cy + h // 8), (x1 - w // 5, cy + h // 8)], fill=WHITE, width=stroke)
    elif tool_id == "problems":
        draw.polygon([(cx, y0 + h // 6), (x1 - w // 5, y1 - h // 4), (x0 + w // 5, y1 - h // 4)], outline=GOLD, width=stroke)
        draw.text((cx - w // 16, cy - h // 12), "!", fill=ROSE)
    elif tool_id == "git_status":
        draw.line([(x0 + w // 3, y0 + h // 4), (x0 + w // 3, y1 - h // 4)], fill=EMERALD, width=stroke)
        draw.ellipse((x0 + w // 4, y0 + h // 3, x0 + w // 2, y0 + h // 2), fill=ROSE)
        draw.ellipse((x0 + w // 4, y1 - h // 2, x0 + w // 2, y1 - h // 3), fill=GOLD)
    elif tool_id == "memory_vault":
        draw.rectangle((x0 + w // 4, cy, x1 - w // 4, y1 - h // 6), fill=(40, 50, 45, 255), outline=EMERALD, width=stroke)
        draw.arc((x0 + w // 3, y0 + h // 6, x1 - w // 3, cy), 180, 0, fill=GOLD, width=stroke)
    elif tool_id == "znetwork_shield":
        _draw(draw, "ironclad_verify", box, stroke)
        draw.line([(x0 + w // 5, cy), (x1 - w // 5, cy)], fill=ROSE, width=stroke)
    elif tool_id == "combinatorics":
        for row in range(2):
            for col in range(2):
                px = x0 + col * w // 3 + w // 8
                py = y0 + row * h // 3 + h // 8
                draw.rectangle((px, py, px + w // 5, py + h // 5), outline=EMERALD, width=stroke)
    elif tool_id == "collab":
        draw.ellipse((x0 + w // 6, cy - h // 6, x0 + w // 2, cy + h // 6), outline=EMERALD, width=stroke)
        draw.ellipse((x0 + w // 3, cy - h // 6, x1 - w // 6, cy + h // 6), outline=ROSE, width=stroke)
    elif tool_id == "screenshare":
        draw.rectangle((x0 + w // 8, y0 + h // 5, x1 - w // 8, y1 - h // 4), outline=EMERALD, width=stroke)
        draw.polygon([(cx - w // 8, y1 - h // 5), (cx + w // 8, y1 - h // 5), (cx, y1 - h // 8)], fill=ROSE)
    elif tool_id == "screenshot":
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), outline=EMERALD, width=stroke)
        draw.ellipse((cx - w // 10, cy - h // 10, cx + w // 10, cy + h // 10), fill=GOLD)
    elif tool_id == "export":
        draw.polygon([(cx, y0 + h // 5), (x1 - w // 5, cy), (cx, y1 - h // 5), (x0 + w // 5, cy)], outline=EMERALD, width=stroke)
    elif tool_id == "print":
        draw.rectangle((x0 + w // 5, y0 + h // 3, x1 - w // 5, y1 - h // 5), outline=EMERALD, width=stroke)
        draw.rectangle((x0 + w // 4, y0 + h // 6, x1 - w // 4, y0 + h // 3), fill=GOLD)
    else:
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), outline=EMERALD, width=stroke)


def render_icon(tool_id: str, size: int) -> Image.Image:
    canvas = _plate(size)
    stroke = max(1, size // 16)
    _draw(ImageDraw.Draw(canvas), tool_id, _box(size), stroke)
    return canvas


def main() -> int:
    doc = json.loads(DOCTRINE.read_text(encoding="utf-8"))
    ids = [str(it["id"]) for it in doc.get("items") or [] if it.get("id")]
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, list[str]] = {"icons": [], "sizes": list(SIZES), "sealed": []}
    for tid in ids:
        for size in SIZES:
            img = render_icon(tid, size)
            path = OUT / f"{tid}-{size}.png"
            img.save(path, format="PNG", optimize=True)
            manifest["icons"].append(str(path.relative_to(ROOT)))
            if SEALED.parent.is_dir():
                SEALED.mkdir(parents=True, exist_ok=True)
                sealed_path = SEALED / f"{tid}-{size}.png"
                shutil.copy2(path, sealed_path)
                manifest["sealed"].append(str(sealed_path))
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "count": len(ids), "files": len(manifest["icons"]), "sealed": len(manifest["sealed"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())