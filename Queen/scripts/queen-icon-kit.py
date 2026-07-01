#!/usr/bin/env pythong
"""Queen icon kit — program-glyph icons (OCR-shaped), tray, desktop, panel. No portrait branding."""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

QUEEN = Path(__file__).resolve().parents[1]
NEXUS = QUEEN.parent
SOURCE = QUEEN / "world" / "assets" / "branding" / "amouranth-gentle.png"
PANEL_ASSETS = NEXUS / "panel" / "assets"
ASSETS = NEXUS / "assets"
BRANDING = QUEEN / "world" / "assets" / "branding"
PROG_ICONS = QUEEN / "world" / "assets" / "icons"
SEALED_ASSETS = NEXUS / "state" / "sealed" / "panel" / "assets"
FIELD_GECKO = QUEEN / "field-gecko"

DESKTOP_SIZES = (16, 22, 24, 32, 48, 64, 128, 256, 512)
TRAY_SIZES = (22, 24, 32)
HICOLOR_ALIASES = (
    "ammoos-field.png",
    "queen-browser.png",
    "ammoos-panel.png",
    "nexus-field.png",
    "nexus-shield-panel.png",
    "nexus-shield.png",
)
LEGACY_TRAY_JPG = PANEL_ASSETS / "nexus-tray-us-source.jpg"
DARK_FILL = (2, 4, 3, 255)
DARK_EDGE = (26, 77, 50, 255)
EMERALD = (34, 197, 94, 255)
ROSE = (244, 114, 182, 255)


def _crop_face(img: Image.Image) -> Image.Image:
    rgba = img.convert("RGBA")
    w, h = rgba.size
    side = min(w, h)
    crop = max(8, int(side * 0.92))
    left = (w - crop) // 2
    top = max(0, int(h * 0.06))
    if top + crop > h:
        top = h - crop
    return rgba.crop((left, top, left + crop, top + crop))


def render_queen_icon(face: Image.Image, size: int, *, tray: bool = False) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    margin = max(1, size // 14) if tray else max(2, size // 16)
    inner = size - 2 * margin
    icon = _crop_face(face).resize((inner, inner), Image.Resampling.LANCZOS)
    if size <= 32:
        icon = icon.filter(ImageFilter.UnsharpMask(radius=0.6, percent=140, threshold=1))

    mask = Image.new("L", (inner, inner), 0)
    draw_m = ImageDraw.Draw(mask)
    radius = max(2, inner // 5)
    draw_m.rounded_rectangle((0, 0, inner - 1, inner - 1), radius=radius, fill=255)
    icon.putalpha(mask)

    draw = ImageDraw.Draw(canvas)
    bg = DARK_FILL if tray else (8, 16, 12, 255)
    draw.rounded_rectangle(
        (margin, margin, margin + inner - 1, margin + inner - 1),
        radius=radius,
        fill=bg,
        outline=DARK_EDGE,
        width=max(1, size // 32),
    )
    ring = max(1, size // 24)
    draw.rounded_rectangle(
        (margin - ring, margin - ring, margin + inner - 1 + ring, margin + inner - 1 + ring),
        radius=radius + ring,
        outline=EMERALD,
        width=ring,
    )
    if size >= 48 and not tray:
        draw.arc(
            (margin - ring * 2, margin - ring * 2, margin + inner + ring * 2, margin + inner + ring * 2),
            200,
            340,
            fill=ROSE,
            width=max(1, ring),
        )
    canvas.paste(icon, (margin, margin), icon)
    return canvas


def _write(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def _sync_sealed(paths: list[Path]) -> list[str]:
    synced: list[str] = []
    if not SEALED_ASSETS.parent.is_dir():
        return synced
    SEALED_ASSETS.mkdir(parents=True, exist_ok=True)
    for src in paths:
        if not src.is_file():
            continue
        dest = SEALED_ASSETS / src.name
        shutil.copy2(src, dest)
        synced.append(str(dest))
    return synced


def _mirror_icon(src: Path, dest: Path) -> None:
    if src.is_file() and src != dest:
        shutil.copy2(src, dest)


def install_hicolor(home: Path | None = None) -> None:
    home = home or Path(os.environ.get("HOME", "/home/default"))
    cache = home / ".local/share/icons/hicolor"
    for sz in DESKTOP_SIZES:
        src = PANEL_ASSETS / f"ammoos-field-{sz}.png"
        if not src.is_file():
            src = PANEL_ASSETS / f"nexus-field-{sz}.png"
        if not src.is_file():
            continue
        for name in HICOLOR_ALIASES:
            dest = cache / f"{sz}x{sz}" / "apps" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
    for px_dir in cache.glob("*x*"):
        if px_dir.is_dir() and (px_dir / "apps").is_dir():
            subprocess.run(["gtk-update-icon-cache", "-f", str(px_dir)], capture_output=True, timeout=8)


PROGRAM_IDS = (
    "ammoos",
    "nexus",
    "browser",
    "os",
    "terminal",
    "chips",
    "cpu-library",
    "font-editor",
    "clipboard",
    "cores",
    "gameroom",
    "forge",
    "hostess",
    "eyeball",
    "earball",
    "kilroy",
    "g16",
    "gpy",
    "field",
    "command",
    "underlay",
    "files",
    "code",
    "tristate",
    "network",
    "znetwork",
    "lock",
    "shield",
    "c2-desktop",
    "nexus-c2-desktop",
    "calc",
    "calendar",
    "popcorn",
    "gpu",
    "big-drive",
    "gimp",
    "image",
    "combinatorics",
    "compatibility",
    "ellie",
    "broadcaster",
    "audio-settings",
    "launch-explorer",
    "control-panel",
    "nexus-calc",
    "nexus-calendar",
    "ammoos-image",
    "field-gimp",
    "field-popcorn",
    "field-gpu",
    "field-big-drive",
    "nexus-combinatorics",
    "nexus-compatibility",
    "nexus-control-panel",
    "nexus-field-command",
    "nexus-packets",
    "nexus-threats",
    "nexus-dns",
    "nexus-library",
    "nexus-training",
    "nexus-intel",
    "nexus-final-eye",
    "nexus-final-ear",
    "nexus-final-mouth",
    "queen-chips",
    "queen-code",
    "queen-files",
    "view",
    "queen-gameroom",
    "queen-terminal",
)

FILE_BATTERY_IDS = (
    "folder",
    "file",
    "json",
    "python",
    "launch",
    "image",
    "markdown",
    "config",
    "shell",
    "symlink",
    "lock",
    "shield",
    "network",
    "audio",
    "video",
    "binary",
    "archive",
    "code",
)


def _program_plate(size: int, *, accent: tuple[int, int, int, int] = EMERALD) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    margin = max(1, size // 10)
    inner = size - 2 * margin
    radius = max(3, inner // 5)
    draw.rounded_rectangle(
        (margin, margin, margin + inner - 1, margin + inner - 1),
        radius=radius,
        fill=(8, 16, 12, 255),
        outline=DARK_EDGE,
        width=max(1, size // 32),
    )
    ring = max(1, size // 24)
    draw.rounded_rectangle(
        (margin - ring, margin - ring, margin + inner - 1 + ring, margin + inner - 1 + ring),
        radius=radius + ring,
        outline=accent,
        width=ring,
    )
    return canvas


def _draw_file_glyph(draw: ImageDraw.ImageDraw, file_id: str, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    w = x1 - x0
    h = y1 - y0
    stroke = max(1, w // 16)
    emerald = (62, 207, 142, 255)
    rose = (244, 114, 182, 255)
    white = (232, 242, 234, 255)
    amber = (250, 204, 21, 255)

    if file_id == "folder":
        tab_w = w // 3
        draw.polygon(
            [(x0 + w // 8, y0 + h // 3), (x0 + w // 8 + tab_w, y0 + h // 3), (x0 + w // 8 + tab_w + w // 10, y0 + h // 6), (x1 - w // 8, y0 + h // 6), (x1 - w // 8, y1 - h // 8), (x0 + w // 8, y1 - h // 8)],
            outline=emerald,
            width=stroke,
        )
        draw.rectangle((x0 + w // 8, y0 + h // 3, x1 - w // 8, y1 - h // 8), outline=emerald, width=stroke)
    elif file_id == "file":
        draw.rectangle((x0 + w // 6, y0 + h // 8, x1 - w // 6, y1 - h // 8), outline=emerald, width=stroke)
        draw.line([(x0 + w // 4, cy), (x1 - w // 4, cy)], fill=white, width=stroke)
        draw.line([(x0 + w // 4, cy + h // 6), (x1 - w // 3, cy + h // 6)], fill=rose, width=stroke)
    elif file_id == "json":
        draw.rectangle((x0 + w // 6, y0 + h // 8, x1 - w // 6, y1 - h // 8), outline=amber, width=stroke)
        draw.text((x0 + w // 5, y0 + h // 4), "{}", fill=emerald)
    elif file_id == "python":
        draw.ellipse((cx - w // 4, cy - h // 5, cx + w // 4, cy + h // 5), outline=emerald, width=stroke)
        draw.text((cx - w // 10, cy - h // 8), "Py", fill=rose)
    elif file_id == "launch":
        draw.polygon([(x0 + w // 4, y0 + h // 5), (x0 + w // 4, y1 - h // 5), (x1 - w // 5, cy)], fill=rose)
    elif file_id == "image":
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), outline=emerald, width=stroke)
        draw.ellipse((cx - w // 10, cy - h // 10, cx + w // 10, cy + h // 10), fill=rose)
    elif file_id == "markdown":
        draw.rectangle((x0 + w // 6, y0 + h // 8, x1 - w // 6, y1 - h // 8), outline=emerald, width=stroke)
        draw.text((x0 + w // 5, y0 + h // 4), "M↓", fill=white)
    elif file_id == "config":
        draw.rectangle((x0 + w // 5, y0 + h // 5, x1 - w // 5, y1 - h // 5), outline=amber, width=stroke)
        for i in range(3):
            yy = y0 + h // 4 + i * h // 5
            draw.line([(x0 + w // 4, yy), (x1 - w // 4, yy)], fill=emerald, width=stroke)
    elif file_id == "shell":
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), outline=emerald, width=stroke)
        draw.polygon([(x0 + w // 3, cy), (x0 + w // 2, cy - h // 8), (x0 + w // 2, cy + h // 8)], fill=rose)
    elif file_id == "symlink":
        draw.arc((x0, y0, cx + w // 6, y1), 45, 235, fill=emerald, width=stroke)
        draw.arc((cx - w // 8, y0, x1, y1), 45, 235, fill=rose, width=stroke)
    elif file_id == "lock":
        draw.rectangle((x0 + w // 4, cy, x1 - w // 4, y1 - h // 6), fill=(40, 50, 45, 255), outline=emerald, width=stroke)
        draw.arc((x0 + w // 3, y0 + h // 6, x1 - w // 3, cy), 180, 0, fill=emerald, width=stroke)
    elif file_id == "shield":
        draw.polygon([(cx, y0 + h // 8), (x1 - w // 6, y0 + h // 3), (x1 - w // 5, y1 - h // 4), (cx, y1 - h // 8), (x0 + w // 5, y1 - h // 4), (x0 + w // 6, y0 + h // 3)], outline=emerald, width=stroke)
    elif file_id == "network":
        draw.ellipse((cx - w // 12, cy - h // 12, cx + w // 12, cy + h // 12), fill=rose)
        for ang in (0, 60, 120, 180, 240, 300):
            rad = math.radians(ang)
            dx = int(math.cos(rad) * w // 4)
            dy = int(math.sin(rad) * h // 4)
            draw.line([(cx, cy), (cx + dx, cy + dy)], fill=emerald, width=stroke)
    elif file_id == "audio":
        draw.polygon([(x0 + w // 4, y0 + h // 3), (x0 + w // 2, y0 + h // 3), (x0 + w // 2, y1 - h // 3), (x0 + w // 4, y1 - h // 3)], fill=emerald)
        for i, amp in enumerate((2, 4, 3)):
            draw.arc((x0 + w // 2 + i * w // 10, cy - amp * h // 16, x1 - w // 6, cy + amp * h // 16), 270, 90, fill=rose, width=stroke)
    elif file_id == "video":
        draw.rectangle((x0 + w // 6, y0 + h // 5, x1 - w // 6, y1 - h // 5), outline=emerald, width=stroke)
        draw.polygon([(x0 + w // 3, y0 + h // 3), (x0 + w // 3, y1 - h // 3), (x1 - w // 4, cy)], fill=rose)
    elif file_id == "archive":
        draw.rectangle((x0 + w // 5, y0 + h // 6, x1 - w // 5, y1 - h // 6), outline=amber, width=stroke)
        draw.line([(x0 + w // 4, cy - h // 8), (x1 - w // 4, cy - h // 8)], fill=emerald, width=stroke)
        draw.line([(x0 + w // 4, cy + h // 8), (x1 - w // 4, cy + h // 8)], fill=emerald, width=stroke)
    elif file_id == "binary":
        draw.rectangle((x0 + w // 5, y0 + h // 5, x1 - w // 5, y1 - h // 5), outline=rose, width=stroke)
        draw.text((x0 + w // 5, y0 + h // 4), "01", fill=emerald)
    elif file_id == "code":
        draw.line([(x0 + w // 3, y0 + h // 4), (x0 + w // 5, cy), (x0 + w // 3, y1 - h // 4)], fill=emerald, width=stroke)
        draw.line([(x1 - w // 3, y0 + h // 4), (x1 - w // 5, cy), (x1 - w // 3, y1 - h // 4)], fill=rose, width=stroke)
    else:
        draw.rectangle((x0 + w // 6, y0 + h // 8, x1 - w // 6, y1 - h // 8), outline=emerald, width=stroke)


def render_file_icon(file_id: str, size: int) -> Image.Image:
    accent = ROSE if file_id in ("launch", "video", "lock", "shield") else EMERALD
    if file_id in ("json", "config", "archive"):
        accent = (250, 204, 21, 255)
    canvas = _program_plate(size, accent=accent)
    margin = max(3, size // 5)
    _draw_file_glyph(ImageDraw.Draw(canvas), file_id, (margin, margin, size - margin, size - margin))
    return canvas


def _draw_program_glyph(draw: ImageDraw.ImageDraw, prog_id: str, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    w = x1 - x0
    h = y1 - y0
    stroke = max(1, w // 16)
    emerald = (62, 207, 142, 255)
    rose = (244, 114, 182, 255)
    white = (232, 242, 234, 255)

    if prog_id == "browser":
        draw.rounded_rectangle((x0, y0 + h // 6, x1, y1), radius=w // 8, outline=emerald, width=stroke)
        draw.rectangle((x0, y0 + h // 6, x1, y0 + h // 3), fill=emerald)
    elif prog_id == "terminal":
        draw.polygon([(x0 + w // 5, cy), (x0 + w // 2, cy - h // 5), (x0 + w // 2, cy + h // 5)], fill=emerald)
        draw.line([(x0 + w // 2, cy + h // 6), (x1 - w // 6, cy + h // 6)], fill=white, width=stroke)
    elif prog_id == "chips":
        cell = w // 4
        for row in range(2):
            for col in range(2):
                px = x0 + col * cell + cell // 3
                py = y0 + row * cell + cell // 3
                draw.rectangle((px, py, px + cell - cell // 4, py + cell - cell // 4), outline=emerald, width=stroke)
    elif prog_id == "cpu-library":
        draw.rectangle((x0 + w // 8, y0 + h // 6, x1 - w // 8, y1 - h // 6), outline=emerald, width=stroke)
        for i in range(3):
            yy = y0 + h // 4 + i * h // 5
            draw.line([(x0 + w // 5, yy), (x1 - w // 5, yy)], fill=rose if i == 0 else white, width=stroke)
        draw.text((x0 + w // 6, y1 - h // 3), "CPU", fill=emerald)
    elif prog_id == "font-editor":
        draw.rectangle((x0 + w // 5, y0 + h // 5, x1 - w // 5, y1 - h // 5), outline=emerald, width=stroke)
        draw.text((x0 + w // 5, cy - h // 8), "A", fill=rose)
        draw.line([(x0 + w // 4, y1 - h // 4), (x1 - w // 4, y1 - h // 4)], fill=white, width=stroke)
    elif prog_id == "clipboard":
        draw.rounded_rectangle((x0 + w // 6, y0 + h // 5, x1 - w // 6, y1 - h // 5), radius=w // 10, outline=emerald, width=stroke)
        draw.line([(x0 + w // 4, cy - h // 10), (x1 - w // 4, cy - h // 10)], fill=rose, width=stroke)
        draw.line([(x0 + w // 4, cy + h // 10), (x1 - w // 3, cy + h // 10)], fill=white, width=stroke)
    elif prog_id == "cores":
        draw.ellipse((cx - w // 3, cy - w // 3, cx + w // 3, cy + w // 3), outline=emerald, width=stroke)
        draw.ellipse((cx - w // 8, cy - w // 8, cx + w // 8, cy + w // 8), fill=rose)
    elif prog_id == "gameroom":
        draw.polygon([(x0 + w // 4, y0), (x1, cy), (x0 + w // 4, y1)], fill=rose)
    elif prog_id == "forge":
        draw.rectangle((x0 + w // 4, cy, x1 - w // 4, y1 - h // 6), fill=(120, 120, 130, 255))
        draw.polygon([(x0, cy), (x1, y0 + h // 5), (x1 - w // 5, cy)], fill=emerald)
    elif prog_id == "hostess":
        draw.ellipse((cx - w // 3, cy - h // 4, cx + w // 3, cy + h // 4), outline=emerald, width=stroke)
        draw.ellipse((cx - w // 10, cy - h // 12, cx + w // 10, cy + h // 12), fill=rose)
    elif prog_id in ("eyeball", "earball"):
        draw.ellipse((cx - w // 3, cy - h // 3, cx + w // 3, cy + h // 3), outline=emerald, width=stroke)
        draw.ellipse((cx - w // 8, cy - h // 8, cx + w // 8, cy + h // 8), fill=rose if prog_id == "eyeball" else emerald)
    elif prog_id in ("g16", "gpy"):
        label = "16" if prog_id == "g16" else "Py"
        draw.text((x0 + w // 6, y0 + h // 5), label, fill=emerald)
    elif prog_id == "underlay":
        draw.line([(x0, y1 - h // 5), (x1, y1 - h // 5)], fill=emerald, width=stroke)
        draw.polygon([(cx - w // 6, cy), (cx, y0 + h // 5), (cx + w // 6, cy)], fill=rose)
    elif prog_id in ("files", "queen-files", "view"):
        draw.polygon([(x0 + w // 5, y0 + h // 4), (x0 + w // 2, y0), (x1 - w // 5, y0), (x1 - w // 5, y1), (x0 + w // 5, y1)], outline=emerald, width=stroke)
        if prog_id == "view":
            draw.text((x0 + w // 4, cy - h // 10), "V", fill=rose)
    elif prog_id in ("ammoos", "nexus", "field"):
        draw.polygon([(cx, y0 + h // 8), (x1 - w // 6, cy), (cx, y1 - h // 8), (x0 + w // 6, cy)], outline=emerald, width=stroke)
        draw.ellipse((cx - w // 10, cy - h // 10, cx + w // 10, cy + h // 10), fill=rose)
    elif prog_id == "os":
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), outline=emerald, width=stroke)
        draw.ellipse((cx - w // 12, cy - h // 12, cx + w // 12, cy + h // 12), fill=rose)
    elif prog_id == "code":
        draw.line([(x0 + w // 3, y0 + h // 4), (x0 + w // 5, cy), (x0 + w // 3, y1 - h // 4)], fill=emerald, width=stroke)
        draw.line([(x1 - w // 3, y0 + h // 4), (x1 - w // 5, cy), (x1 - w // 3, y1 - h // 4)], fill=rose, width=stroke)
    elif prog_id == "network":
        draw.ellipse((cx - w // 10, cy - h // 10, cx + w // 10, cy + h // 10), fill=rose)
        draw.ellipse((x0 + w // 6, y0 + h // 4, x1 - w // 6, y1 - h // 4), outline=emerald, width=stroke)
    elif prog_id == "znetwork":
        sky = (56, 189, 248, 255)
        core = (125, 211, 252, 255)
        for ang in (0, 60, 120, 180, 240, 300):
            rad = math.radians(ang)
            dx = int(math.cos(rad) * w // 4)
            dy = int(math.sin(rad) * h // 4)
            draw.line([(cx, cy), (cx + dx, cy + dy)], fill=sky, width=stroke)
        draw.ellipse((cx - w // 10, cy - h // 10, cx + w // 10, cy + h // 10), fill=core, outline=sky)
        zw = max(6, w // 2)
        zh = max(5, int(zw * 0.72))
        thick = max(2, zw // 5)
        x0z, x1z = cx - zw // 2, cx + zw // 2
        y0z, y1z = cy - zh // 2, cy + zh // 2
        draw.polygon(
            [
                (x0z, y0z),
                (x1z, y0z),
                (x1z, y0z + thick),
                (x0z + thick * 2, y1z - thick),
                (x1z, y1z - thick),
                (x1z, y1z),
                (x0z, y1z),
                (x0z, y1z - thick),
                (x1z - thick * 2, y0z + thick),
                (x0z, y0z + thick),
            ],
            fill=(240, 249, 255, 245),
            outline=sky,
        )
    elif prog_id == "lock":
        draw.rectangle((x0 + w // 4, cy, x1 - w // 4, y1 - h // 6), outline=emerald, width=stroke)
        draw.arc((x0 + w // 3, y0 + h // 5, x1 - w // 3, cy), 180, 0, fill=emerald, width=stroke)
    elif prog_id == "shield":
        draw.polygon([(cx, y0 + h // 8), (x1 - w // 6, y0 + h // 3), (x1 - w // 5, y1 - h // 4), (cx, y1 - h // 8), (x0 + w // 5, y1 - h // 4), (x0 + w // 6, y0 + h // 3)], outline=emerald, width=stroke)
    elif prog_id in ("calc", "nexus-calc"):
        draw.rectangle((x0 + w // 6, y0 + h // 8, x1 - w // 6, y1 - h // 8), outline=emerald, width=stroke)
        for i, ch in enumerate(("7", "+", "=")):
            draw.text((x0 + w // 5, y0 + h // 5 + i * h // 5), ch, fill=rose if i == 1 else white)
    elif prog_id in ("calendar", "nexus-calendar"):
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 8), outline=emerald, width=stroke)
        draw.line([(x0 + w // 6, y0 + h // 3), (x1 - w // 6, y0 + h // 3)], fill=rose, width=stroke)
        draw.text((cx - w // 10, cy), "31", fill=white)
    elif prog_id in ("popcorn", "field-popcorn"):
        draw.polygon([(cx, y0 + h // 8), (x1 - w // 5, y1 - h // 4), (x0 + w // 5, y1 - h // 4)], outline=rose, width=stroke)
        draw.ellipse((cx - w // 8, cy - h // 10, cx + w // 8, cy + h // 10), fill=emerald)
    elif prog_id in ("gpu", "field-gpu"):
        draw.rectangle((x0 + w // 5, y0 + h // 4, x1 - w // 5, y1 - h // 5), outline=emerald, width=stroke)
        draw.text((x0 + w // 5, cy - h // 10), "GPU", fill=rose)
    elif prog_id in ("big-drive", "field-big-drive"):
        draw.ellipse((cx - w // 3, cy - h // 4, cx + w // 3, cy + h // 4), outline=emerald, width=stroke)
        draw.rectangle((cx - w // 12, cy - h // 12, cx + w // 12, cy + h // 12), fill=rose)
    elif prog_id in ("gimp", "image", "ammoos-image", "field-gimp"):
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), outline=emerald, width=stroke)
        draw.ellipse((cx - w // 8, cy - h // 8, cx + w // 8, cy + h // 8), fill=rose)
        draw.line([(x0 + w // 4, y1 - h // 4), (x1 - w // 4, y0 + h // 4)], fill=white, width=stroke)
    elif prog_id in ("combinatorics", "nexus-combinatorics"):
        for i in range(3):
            draw.rectangle((x0 + w // 6 + i * w // 8, y0 + h // 5 + i * h // 10, x0 + w // 3 + i * w // 8, y1 - h // 5), outline=emerald, width=stroke)
    elif prog_id in ("compatibility", "nexus-compatibility"):
        draw.ellipse((x0 + w // 4, cy - h // 5, cx, cy + h // 5), outline=emerald, width=stroke)
        draw.ellipse((cx, cy - h // 5, x1 - w // 4, cy + h // 5), outline=rose, width=stroke)
    elif prog_id in ("ellie", "nexus-threats", "nexus-packets", "nexus-dns", "nexus-intel"):
        draw.polygon([(cx, y0 + h // 8), (x1 - w // 6, y0 + h // 3), (x1 - w // 5, y1 - h // 4), (cx, y1 - h // 8), (x0 + w // 5, y1 - h // 4), (x0 + w // 6, y0 + h // 3)], outline=emerald, width=stroke)
        draw.ellipse((cx - w // 12, cy - h // 12, cx + w // 12, cy + h // 12), fill=rose)
    elif prog_id in ("broadcaster", "field-broadcaster"):
        draw.polygon([(cx, y0 + h // 5), (x1 - w // 5, y1 - h // 3), (x0 + w // 5, y1 - h // 3)], fill=rose)
        draw.ellipse((cx - w // 10, cy, cx + w // 10, cy + h // 5), fill=emerald)
    elif prog_id in ("audio-settings", "field-audio-settings"):
        draw.polygon([(x0 + w // 4, y0 + h // 3), (x0 + w // 2, y0 + h // 3), (x0 + w // 2, y1 - h // 3), (x0 + w // 4, y1 - h // 3)], fill=emerald)
        draw.arc((x0 + w // 2, cy - h // 6, x1 - w // 6, cy + h // 6), 270, 90, fill=rose, width=stroke)
    elif prog_id in ("launch-explorer", "field-launch-explorer"):
        draw.polygon([(x0 + w // 4, y0 + h // 5), (x0 + w // 4, y1 - h // 5), (x1 - w // 5, cy)], fill=rose)
        draw.rectangle((x0 + w // 2, y0 + h // 3, x1 - w // 4, y1 - h // 3), outline=emerald, width=stroke)
    elif prog_id in ("control-panel", "nexus-control-panel"):
        draw.rectangle((x0 + w // 5, y0 + h // 5, x1 - w // 5, y1 - h // 5), outline=emerald, width=stroke)
        for i in range(3):
            yy = y0 + h // 4 + i * h // 5
            draw.ellipse((x0 + w // 4, yy - h // 16, x0 + w // 3, yy + h // 16), fill=rose if i == 0 else emerald)
            draw.line([(x0 + w // 2, yy), (x1 - w // 4, yy)], fill=white, width=stroke)
    elif prog_id in ("c2-desktop", "nexus-c2-desktop"):
        draw.rounded_rectangle((x0 + w // 8, y0 + h // 6, x1 - w // 8, y1 - h // 8), radius=w // 10, outline=emerald, width=stroke)
        draw.text((x0 + w // 5, cy - h // 10), "C2", fill=rose)
    elif prog_id in ("nexus-field-command", "nexus-command", "command"):
        draw.rectangle((x0 + w // 5, y0 + h // 5, x1 - w // 5, y1 - h // 5), outline=emerald, width=stroke)
        draw.line([(x0 + w // 4, cy), (x1 - w // 4, cy)], fill=rose, width=stroke)
        draw.line([(cx, y0 + h // 3), (cx, y1 - h // 3)], fill=white, width=stroke)
    elif prog_id in ("nexus-library", "nexus-training"):
        draw.rectangle((x0 + w // 5, y0 + h // 6, x1 - w // 5, y1 - h // 6), outline=emerald, width=stroke)
        draw.line([(x0 + w // 4, y0 + h // 3), (x1 - w // 4, y0 + h // 3)], fill=rose, width=stroke)
        for i in range(3):
            draw.line([(x0 + w // 4, y0 + h // 2 + i * h // 8), (x1 - w // 3, y0 + h // 2 + i * h // 8)], fill=white, width=stroke)
    elif prog_id in ("nexus-final-eye", "eyeball"):
        draw.ellipse((cx - w // 3, cy - h // 3, cx + w // 3, cy + h // 3), outline=emerald, width=stroke)
        draw.ellipse((cx - w // 8, cy - h // 8, cx + w // 8, cy + h // 8), fill=rose)
    elif prog_id in ("nexus-final-ear", "earball"):
        draw.arc((x0 + w // 5, y0 + h // 5, x1 - w // 5, y1 - h // 5), 200, 340, fill=emerald, width=stroke)
        draw.ellipse((cx - w // 10, cy, cx + w // 10, cy + h // 6), fill=rose)
    elif prog_id in ("nexus-final-mouth", "hostess"):
        draw.arc((x0 + w // 4, y0 + h // 4, x1 - w // 4, y1 - h // 4), 20, 160, fill=rose, width=stroke)
    else:
        draw.polygon(
            [(cx, y0 + h // 8), (x1 - w // 6, cy + h // 6), (cx + w // 8, y1 - h // 8), (x0 + w // 6, cy + h // 6)],
            outline=emerald,
            width=stroke,
        )
        draw.ellipse((cx - w // 12, cy - h // 12, cx + w // 12, cy + h // 12), fill=rose)


def render_program_icon(prog_id: str, size: int, face: Image.Image | None = None) -> Image.Image:
    accent = ROSE if prog_id in ("browser", "gameroom", "eyeball") else EMERALD
    canvas = _program_plate(size, accent=accent)
    margin = max(3, size // 5)
    inner_box = (margin, margin, size - margin, size - margin)
    portrait_ids: tuple[str, ...] = ()
    if prog_id in portrait_ids and face is not None:
        inset = size - 2 * margin
        portrait = _crop_face(face).resize((inset, inset), Image.Resampling.LANCZOS)
        mask = Image.new("L", (inset, inset), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, inset - 1, inset - 1), radius=max(2, inset // 5), fill=255)
        portrait.putalpha(mask)
        canvas.paste(portrait, (margin, margin), portrait)
    else:
        _draw_program_glyph(ImageDraw.Draw(canvas), prog_id, inner_box)
    return canvas


def _build_plate(face: Image.Image) -> Image.Image:
    plate_w, plate_h = 1920, 1080
    plate = Image.new("RGBA", (plate_w, plate_h), DARK_FILL)
    portrait = _crop_face(face).resize((plate_w, plate_h), Image.Resampling.LANCZOS)
    if portrait.mode == "RGBA":
        plate.paste(portrait, (0, 0), portrait)
    else:
        plate.paste(portrait, (0, 0))
    overlay = Image.new("RGBA", (plate_w, plate_h), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(plate_h):
        t = y / max(plate_h - 1, 1)
        alpha = int(40 + 180 * (t ** 1.4))
        od.line([(0, y), (plate_w, y)], fill=(2, 4, 3, min(255, alpha)))
    od.ellipse((plate_w * 0.55, -plate_h * 0.15, plate_w * 1.15, plate_h * 0.55), fill=(235, 72, 140, 38))
    od.ellipse((-plate_w * 0.2, plate_h * 0.35, plate_w * 0.55, plate_h * 1.1), fill=(34, 197, 94, 32))
    return Image.alpha_composite(plate.convert("RGBA"), overlay).convert("RGB")


def render_brand_icon(size: int, *, tray: bool = False) -> Image.Image:
    """AmmoOS start/tray glyph — program-shaped, no portrait."""
    return render_program_icon("ammoos", size, face=None)


def build_all(*, force: bool = True) -> dict:
    face = Image.open(SOURCE) if SOURCE.is_file() else None
    PANEL_ASSETS.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    BRANDING.mkdir(parents=True, exist_ok=True)

    out: dict[str, list[str]] = {"desktop": [], "tray": [], "aliases": [], "sealed": []}
    touched: list[Path] = []

    master = render_brand_icon(256) if face is None else render_queen_icon(face, 256)
    primary_dest = (
        ASSETS / "ammoos-field.png",
        PANEL_ASSETS / "ammoos-field.png",
        PANEL_ASSETS / "ammoos-panel.png",
        PANEL_ASSETS / "queen-browser.png",
        BRANDING / "queen-browser-256.png",
        BRANDING / "ammoos-field-256.png",
    )
    legacy_dest = (
        ASSETS / "nexus-field.png",
        ASSETS / "nexus-shield.png",
        PANEL_ASSETS / "nexus-field.png",
        PANEL_ASSETS / "nexus-shield.png",
        PANEL_ASSETS / "nexus-shield-panel.png",
    )
    for dest in primary_dest + legacy_dest:
        _write(master, dest)
        touched.append(dest)
        out["desktop"].append(str(dest))

    for sz in DESKTOP_SIZES:
        img = render_brand_icon(sz) if face is None else render_queen_icon(face, sz)
        p = PANEL_ASSETS / f"ammoos-field-{sz}.png"
        _write(img, p)
        touched.append(p)
        out["desktop"].append(str(p))
        _mirror_icon(p, PANEL_ASSETS / f"nexus-field-{sz}.png")
        touched.append(PANEL_ASSETS / f"nexus-field-{sz}.png")
        out["legacy_aliases"] = out.get("legacy_aliases", []) + [str(PANEL_ASSETS / f"nexus-field-{sz}.png")]
        if sz in (32, 48, 128, 256):
            for alias in (f"ammoos-panel-{sz}.png", f"nexus-shield-panel-{sz}.png"):
                ap = PANEL_ASSETS / alias
                _write(img, ap)
                touched.append(ap)
                out["aliases"].append(str(ap))

    for sz in TRAY_SIZES:
        img = render_brand_icon(sz) if face is None else render_queen_icon(face, sz, tray=True)
        for base in ("ammoos-tray", "queen-tray", "nexus-tray-us"):
            p = PANEL_ASSETS / f"{base}-{sz}.png"
            _write(img, p)
            touched.append(p)
            out["tray"].append(str(p))
    for sz, names in (
        (64, ("ammoos-tray-64.png", "queen-tray-64.png", "nexus-tray-us-64.png")),
        (128, ("ammoos-tray.png", "queen-tray.png", "nexus-tray-us.png")),
    ):
        img = render_brand_icon(sz) if face is None else render_queen_icon(face, sz, tray=True)
        for n in names:
            p = PANEL_ASSETS / n
            _write(img, p)
            touched.append(p)
            out["tray"].append(str(p))

    fav48 = render_brand_icon(48)
    tray_src = render_brand_icon(32)
    _write(fav48, BRANDING / "queen-favicon-48.png")
    _write(tray_src, BRANDING / "queen-tray-source.png")
    touched.extend([BRANDING / "queen-favicon-48.png", BRANDING / "queen-tray-source.png"])

    for name in ("queen-tray-source.png", "queen-favicon-48.png"):
        dest = PANEL_ASSETS / name
        shutil.copy2(BRANDING / name, dest)
        touched.append(dest)
        out["panel_branding"] = out.get("panel_branding", []) + [str(dest)]

    PROG_ICONS.mkdir(parents=True, exist_ok=True)
    out["program_icons"] = []
    for prog_id in PROGRAM_IDS:
        for sz in (32, 48, 64):
            icon = render_program_icon(prog_id, sz, face)
            p = PROG_ICONS / f"prog-{prog_id}-{sz}.png"
            _write(icon, p)
            touched.append(p)
            out["program_icons"].append(str(p))
        master_prog = render_program_icon(prog_id, 64, face)
        p64 = PROG_ICONS / f"prog-{prog_id}.png"
        _write(master_prog, p64)
        touched.append(p64)
        panel_copy = PANEL_ASSETS / f"queen-prog-{prog_id}.png"
        _write(master_prog, panel_copy)
        touched.append(panel_copy)
        out["program_icons"].append(str(p64))

    out["file_battery"] = []
    for file_id in FILE_BATTERY_IDS:
        for sz in (20, 32, 48):
            icon = render_file_icon(file_id, sz)
            p = PROG_ICONS / f"file-{file_id}-{sz}.png"
            _write(icon, p)
            touched.append(p)
            out["file_battery"].append(str(p))
            if sz in (20, 32):
                panel_file = PANEL_ASSETS / f"file-{file_id}-{sz}.png"
                _write(icon, panel_file)
                touched.append(panel_file)
                out["file_battery"].append(str(panel_file))
        master_file = render_file_icon(file_id, 48)
        p48 = PROG_ICONS / f"file-{file_id}.png"
        _write(master_file, p48)
        touched.append(p48)
        out["file_battery"].append(str(p48))
        panel_master = PANEL_ASSETS / f"file-{file_id}.png"
        _write(master_file, panel_master)
        touched.append(panel_master)
        out["file_battery"].append(str(panel_master))

    battery_doc = {
        "schema": "queen-icon-battery/v1",
        "programs": list(PROGRAM_IDS),
        "files": list(FILE_BATTERY_IDS),
        "world_base": "/world/assets/icons/",
        "panel_base": "/assets/",
        "folder_icon": "file-folder-32.png",
        "default_file_icon": "file-file-32.png",
    }
    battery_path = QUEEN / "data" / "queen-icon-battery.json"
    battery_path.write_text(json.dumps(battery_doc, indent=2) + "\n", encoding="utf-8")
    out["battery_manifest"] = str(battery_path)

    for svg_name in (
        "ammoos-wordmark.svg",
        "queen-wordmark.svg",
        "queen-chrome-restore.svg",
        "queen-chrome-icons.svg",
        "queen-start-icon.svg",
    ):
        src_svg = BRANDING / svg_name
        if src_svg.is_file():
            for dest_dir in (PANEL_ASSETS, BRANDING):
                dest = dest_dir / svg_name
                if dest_dir == BRANDING and dest == src_svg:
                    continue
                shutil.copy2(src_svg, dest)
                touched.append(dest)
                out["wordmarks"] = out.get("wordmarks", []) + [str(dest)]

    if face is not None:
        _write(_build_plate(face), BRANDING / "amouranth-plate.png")
        touched.append(BRANDING / "amouranth-plate.png")

    if LEGACY_TRAY_JPG.is_file():
        LEGACY_TRAY_JPG.unlink()
        out["removed_legacy"] = [str(LEGACY_TRAY_JPG)]
    sealed_legacy = SEALED_ASSETS / LEGACY_TRAY_JPG.name
    if sealed_legacy.is_file():
        sealed_legacy.unlink()
        out["removed_legacy"] = out.get("removed_legacy", []) + [str(sealed_legacy)]

    if FIELD_GECKO.is_dir():
        fg_icons = FIELD_GECKO / "icons"
        fg_icons.mkdir(parents=True, exist_ok=True)
        out["field_gecko"] = []
        for sz in (16, 32, 48, 64, 128, 256):
            icon = render_queen_icon(face, sz, tray=sz <= 32)
            p = fg_icons / f"queen-field-{sz}.png"
            _write(icon, p)
            out["field_gecko"].append(str(p))
        ammoos48 = PANEL_ASSETS / "ammoos-field-48.png"
        fav_src = ammoos48 if ammoos48.is_file() else BRANDING / "queen-favicon-48.png"
        shutil.copy2(fav_src, fg_icons / "ammoos-field-48.png")
        shutil.copy2(fav_src, fg_icons / "queen-favicon-48.png")
        shutil.copy2(fav_src, fg_icons / "default48.png")
        out["field_gecko"].extend([
            str(fg_icons / "ammoos-field-48.png"),
            str(fg_icons / "queen-favicon-48.png"),
            str(fg_icons / "default48.png"),
        ])

    out["sealed"] = _sync_sealed(touched)
    install_hicolor()

    state = Path(os.environ.get("NEXUS_STATE_DIR", NEXUS / "state"))
    state.mkdir(parents=True, exist_ok=True)
    for state_name in ("ammoos-tray.png", "nexus-tray.png", "queen-tray-state.png"):
        tray_state = state / state_name
        src_tray = PANEL_ASSETS / "ammoos-tray-32.png"
        if not src_tray.is_file():
            src_tray = PANEL_ASSETS / "queen-tray-32.png"
        shutil.copy2(src_tray, tray_state)
        out["state_tray"] = str(tray_state)

    return {
        "ok": True,
        "product": "AmmoOS",
        "browser": "Queen Browser",
        "theme": "black_emerald_rose_2026",
        "source": str(SOURCE),
        **out,
        "count": len(out["desktop"]) + len(out["tray"]) + len(out.get("aliases", [])),
    }


def main() -> int:
    import json

    try:
        doc = build_all()
        print(json.dumps(doc, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())