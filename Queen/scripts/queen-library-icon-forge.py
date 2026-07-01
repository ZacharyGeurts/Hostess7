#!/usr/bin/env pythong
"""Queen library icon forge — original shell/DOS/KILROY/game icons (no MS asset copies)."""
from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

QUEEN = Path(__file__).resolve().parents[1]
NEXUS = QUEEN.parent
MANIFEST = QUEEN / "data" / "queen-windows-icons-manifest.json"
DEVICE_ROOT = NEXUS / "library" / "assets" / "devices"
FORGED_ROOT = QUEEN / "world" / "assets" / "icons" / "forged"
SHELL_ROOT = QUEEN / "world" / "assets" / "icons" / "shell"
PROG_ICONS = QUEEN / "world" / "assets" / "icons"

# Win95-inspired palette — original Queen designs
SILVER = (192, 192, 192, 255)
DARK_SILVER = (128, 128, 128, 255)
NAVY = (0, 0, 128, 255)
TEAL = (0, 128, 128, 255)
YELLOW = (255, 255, 0, 255)
WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)
EMERALD = (34, 197, 94, 255)
ROSE = (244, 114, 182, 255)
DOS_GREEN = (0, 255, 65, 255)
DOS_AMBER = (255, 170, 0, 255)
DOS_BLACK = (8, 8, 8, 255)


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _write(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG", optimize=True)


def _bevel_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: tuple[int, int, int, int] = SILVER,
    highlight: tuple[int, int, int, int] = WHITE,
    shadow: tuple[int, int, int, int] = DARK_SILVER,
) -> None:
    x0, y0, x1, y1 = box
    draw.rectangle(box, fill=fill)
    draw.line([(x0, y0), (x1, y0), (x1, y1)], fill=highlight, width=1)
    draw.line([(x0, y0), (x0, y1)], fill=highlight, width=1)
    draw.line([(x0, y1), (x1, y1), (x1, y0)], fill=shadow, width=1)
    draw.line([(x1, y1), (x1, y0)], fill=shadow, width=1)


def _stroke(draw: ImageDraw.ImageDraw, size: int) -> int:
    return max(1, size // 16)


def _box(size: int, margin: float = 0.12) -> tuple[int, int, int, int]:
    m = int(size * margin)
    return (m, m, size - m, size - m)


def _draw_glyph(draw: ImageDraw.ImageDraw, glyph: str, size: int) -> None:
    x0, y0, x1, y1 = _box(size)
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    w = x1 - x0
    h = y1 - y0
    s = _stroke(draw, size)

    g = glyph
    if g == "monitor_tower":
        _bevel_rect(draw, (x0 + w // 8, y0 + h // 6, x0 + w // 2, y1 - h // 8))
        draw.rectangle((x0 + w // 6, y0 + h // 5, x0 + w // 2 - w // 12, y0 + h // 2), fill=TEAL)
        _bevel_rect(draw, (x0 + w // 2 + w // 16, y0 + h // 4, x1 - w // 8, y1 - h // 6))
        draw.rectangle((x0 + w // 2 + w // 10, y0 + h // 3, x1 - w // 6, y1 - h // 4), fill=NAVY)
    elif g == "network_globe":
        draw.ellipse((x0, y0, x1, y1), outline=TEAL, width=s)
        draw.arc((x0, y0, x1, y1), 0, 180, fill=NAVY, width=s)
        draw.line([(x0, cy), (x1, cy)], fill=NAVY, width=s)
        draw.ellipse((cx - w // 8, cy - h // 8, cx + w // 8, cy + h // 8), fill=EMERALD)
    elif g == "recycle_bin":
        draw.polygon([(x0 + w // 6, y0 + h // 4), (x1 - w // 6, y0 + h // 4), (x1 - w // 8, y1), (x0 + w // 8, y1)], fill=SILVER, outline=DARK_SILVER)
        draw.line([(x0 + w // 4, y0 + h // 6), (x1 - w // 4, y0 + h // 6)], fill=DARK_SILVER, width=s)
        draw.arc((cx - w // 6, y0, cx + w // 6, y0 + h // 3), 180, 0, fill=TEAL, width=s)
    elif g in ("folder_closed", "folder_open", "dos_folder"):
        tab = w // 3
        top = y0 + h // 4 if g != "folder_open" else y0 + h // 5
        draw.polygon(
            [(x0 + w // 10, top), (x0 + w // 10 + tab, top), (x0 + w // 10 + tab + w // 12, y0 + h // 8), (x1 - w // 10, y0 + h // 8), (x1 - w // 10, y1 - h // 10), (x0 + w // 10, y1 - h // 10)],
            fill=YELLOW if g != "dos_folder" else DOS_AMBER,
            outline=DARK_SILVER,
        )
        if g == "folder_open":
            draw.line([(x0 + w // 8, top + h // 8), (x1 - w // 8, top + h // 8)], fill=WHITE, width=s)
    elif g == "floppy" or g == "dos_floppy":
        _bevel_rect(draw, (x0 + w // 6, y0 + h // 8, x1 - w // 6, y1 - h // 8))
        draw.rectangle((x0 + w // 4, y0 + h // 6, x1 - w // 4, y0 + h // 3), fill=DARK_SILVER)
        metal = DOS_AMBER if g == "dos_floppy" else SILVER
        draw.rectangle((x0 + w // 3, y0 + h // 2, x1 - w // 3, y1 - h // 4), fill=metal)
    elif g in ("hard_drive", "dos_hdd"):
        _bevel_rect(draw, (x0 + w // 8, y0 + h // 4, x1 - w // 8, y1 - h // 6))
        draw.ellipse((x0 + w // 5, cy - h // 10, x0 + w // 5 + w // 8, cy + h // 10), fill=BLACK)
        draw.rectangle((x0 + w // 3, y0 + h // 3, x1 - w // 4, y1 - h // 4), fill=NAVY if g == "hard_drive" else DOS_BLACK)
        if g == "dos_hdd":
            draw.text((x0 + w // 3, cy - h // 12), "C:", fill=DOS_GREEN)
    elif g == "cd_rom":
        draw.ellipse((x0 + w // 8, y0 + h // 8, x1 - w // 8, y1 - h // 8), fill=SILVER, outline=DARK_SILVER)
        draw.ellipse((cx - w // 6, cy - w // 6, cx + w // 6, cy + w // 6), fill=YELLOW)
        draw.ellipse((cx - w // 16, cy - w // 16, cx + w // 16, cy + w // 16), fill=BLACK)
    elif g == "printer":
        _bevel_rect(draw, (x0 + w // 6, y0 + h // 3, x1 - w // 6, y1 - h // 5))
        draw.rectangle((x0 + w // 4, y0 + h // 6, x1 - w // 4, y0 + h // 3), fill=WHITE, outline=DARK_SILVER)
        draw.rectangle((x0 + w // 3, y1 - h // 4, x1 - w // 3, y1 - h // 8), fill=WHITE)
    elif g == "control_panel":
        _bevel_rect(draw, (x0 + w // 8, y0 + h // 8, x1 - w // 8, y1 - h // 8))
        for i, col in enumerate((TEAL, NAVY, EMERALD)):
            draw.ellipse((x0 + w // 5 + i * w // 4, cy - h // 10, x0 + w // 5 + i * w // 4 + w // 8, cy + h // 10), fill=col)
    elif g == "notepad":
        draw.rectangle((x0 + w // 5, y0 + h // 8, x1 - w // 6, y1 - h // 8), fill=WHITE, outline=DARK_SILVER)
        for i in range(4):
            yy = y0 + h // 5 + i * h // 7
            draw.line([(x0 + w // 4, yy), (x1 - w // 5, yy)], fill=TEAL, width=1)
    elif g == "calculator":
        _bevel_rect(draw, (x0 + w // 6, y0 + h // 8, x1 - w // 6, y1 - h // 8))
        draw.rectangle((x0 + w // 5, y0 + h // 6, x1 - w // 5, y0 + h // 3), fill=TEAL)
        cell = w // 5
        for row in range(2):
            for col in range(3):
                px = x0 + w // 5 + col * cell
                py = y0 + h // 2 + row * cell
                draw.rectangle((px, py, px + cell - 2, py + cell - 2), fill=SILVER, outline=DARK_SILVER)
    elif g == "paint":
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), fill=WHITE, outline=DARK_SILVER)
        draw.ellipse((x0 + w // 5, y0 + h // 5, x0 + w // 2, y0 + h // 2), fill=ROSE)
        draw.rectangle((x0 + w // 2, y0 + h // 2, x1 - w // 5, y1 - h // 5), fill=EMERALD)
    elif g == "solitaire":
        draw.rectangle((x0 + w // 6, y0 + h // 5, x0 + w // 2, y1 - h // 4), fill=WHITE, outline=TEAL)
        draw.rectangle((x0 + w // 3, y0 + h // 4, x0 + w // 2 + w // 6, y1 - h // 5), fill=WHITE, outline=NAVY)
        draw.polygon([(cx, y0 + h // 6), (cx + w // 8, cy), (cx, cy + h // 8), (cx - w // 8, cy)], fill=ROSE)
    elif g == "minesweeper":
        _bevel_rect(draw, (x0 + w // 8, y0 + h // 8, x1 - w // 8, y1 - h // 8))
        cell = w // 5
        for row in range(3):
            for col in range(3):
                px = x0 + w // 6 + col * cell
                py = y0 + h // 5 + row * cell
                draw.rectangle((px, py, px + cell - 1, py + cell - 1), fill=SILVER, outline=DARK_SILVER)
        draw.ellipse((cx - w // 12, cy - h // 12, cx + w // 12, cy + h // 12), fill=BLACK)
    elif g == "media_player":
        draw.rectangle((x0 + w // 8, y0 + h // 4, x1 - w // 8, y1 - h // 4), fill=NAVY, outline=TEAL)
        draw.polygon([(x0 + w // 3, y0 + h // 3), (x0 + w // 3, y1 - h // 3), (x1 - w // 4, cy)], fill=YELLOW)
    elif g == "magnifier":
        draw.ellipse((x0, y0, x1 - w // 5, y1 - h // 5), outline=TEAL, width=s)
        draw.line([(x1 - w // 4, y1 - h // 4), (x1, y1)], fill=DARK_SILVER, width=s + 1)
    elif g == "help_book":
        draw.polygon([(x0 + w // 5, y0 + h // 8), (x1 - w // 6, y0 + h // 6), (x1 - w // 8, y1 - h // 8), (x0 + w // 6, y1 - h // 6)], fill=TEAL, outline=NAVY)
        draw.text((x0 + w // 3, cy - h // 10), "?", fill=YELLOW)
    elif g == "gear":
        draw.ellipse((cx - w // 4, cy - w // 4, cx + w // 4, cy + w // 4), fill=SILVER, outline=DARK_SILVER)
        for ang in range(0, 360, 45):
            rad = math.radians(ang)
            dx = int(math.cos(rad) * w // 3)
            dy = int(math.sin(rad) * h // 3)
            draw.rectangle((cx + dx - 2, cy + dy - 2, cx + dx + 2, cy + dy + 2), fill=DARK_SILVER)
    elif g == "start_flag":
        draw.polygon([(x0 + w // 6, y0 + h // 5), (x1 - w // 5, cy - h // 8), (x0 + w // 6, y1 - h // 5)], fill=EMERALD)
        draw.line([(x0 + w // 6, y0 + h // 5), (x0 + w // 6, y1 - h // 5)], fill=ROSE, width=s)
    elif g == "taskbar":
        draw.rectangle((x0, y1 - h // 3, x1, y1), fill=SILVER, outline=DARK_SILVER)
        draw.rectangle((x0 + w // 12, y1 - h // 4, x0 + w // 4, y1 - h // 8), fill=TEAL)
    elif g == "window_frame":
        draw.rectangle((x0 + w // 10, y0 + h // 6, x1 - w // 10, y1 - h // 10), fill=WHITE, outline=DARK_SILVER)
        draw.rectangle((x0 + w // 10, y0 + h // 6, x1 - w // 10, y0 + h // 4), fill=TEAL)
    elif g == "shortcut_arrow":
        draw.rectangle((x0 + w // 6, y0 + h // 8, x1 - w // 5, y1 - h // 6), fill=YELLOW, outline=DARK_SILVER)
        draw.polygon([(x1 - w // 4, y0 + h // 4), (x1 - w // 8, y0 + h // 4), (x1 - w // 8, y0 + h // 6)], fill=BLACK)
    elif g == "dos_prompt" or g == "command_com":
        draw.rectangle((x0, y0, x1, y1), fill=DOS_BLACK)
        prompt = "C:\\>" if g == "dos_prompt" else "CMD"
        draw.text((x0 + w // 12, cy - h // 10), prompt, fill=DOS_GREEN)
        draw.rectangle((x0 + w // 2, cy - h // 12, x0 + w // 2 + w // 16, cy + h // 12), fill=DOS_GREEN)
    elif g in ("batch_file", "dos_bat"):
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), fill=DOS_BLACK, outline=DOS_GREEN)
        draw.text((x0 + w // 5, cy - h // 10), ".BAT", fill=DOS_AMBER)
    elif g == "config_sys":
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), fill=DOS_BLACK, outline=DOS_GREEN)
        draw.text((x0 + w // 8, cy - h // 10), "SYS", fill=DOS_GREEN)
    elif g in ("dos_exe", "dos_com"):
        draw.rectangle((x0 + w // 5, y0 + h // 5, x1 - w // 5, y1 - h // 5), fill=DOS_BLACK, outline=DOS_AMBER)
        ext = "EXE" if g == "dos_exe" else "COM"
        draw.text((x0 + w // 4, cy - h // 10), ext, fill=DOS_GREEN)
    elif g in ("pc_dos", "ms_dos"):
        draw.rectangle((x0, y0, x1, y1), fill=DOS_BLACK)
        label = "PC" if g == "pc_dos" else "MS"
        draw.text((x0 + w // 6, y0 + h // 5), label, fill=DOS_AMBER)
        draw.text((x0 + w // 6, y0 + h // 2), "DOS", fill=DOS_GREEN)
    elif g == "kilroy_face":
        draw.rectangle((x0, y0, x1, y1), fill=(12, 18, 14, 255))
        draw.arc((x0 + w // 8, y0 + h // 6, x1 - w // 8, y1 - h // 5), 200, 340, fill=EMERALD, width=s + 1)
        draw.ellipse((x0 + w // 3, y0 + h // 3, x0 + w // 2, y0 + h // 2), fill=ROSE)
        draw.ellipse((x0 + w // 2, y0 + h // 3, x1 - w // 3, y0 + h // 2), fill=ROSE)
        draw.arc((x0 + w // 4, y0 + h // 2, x1 - w // 4, y1 - h // 6), 10, 170, fill=EMERALD, width=s)
        draw.text((x0 + w // 10, y1 - h // 4), "KILROY", fill=EMERALD)
    elif g == "kilroy_daemon":
        draw.ellipse((cx - w // 3, cy - h // 3, cx + w // 3, cy + h // 3), fill=(20, 30, 22, 255), outline=EMERALD, width=s)
        draw.polygon([(cx, y0 + h // 5), (x1 - w // 5, cy), (cx, y1 - h // 5), (x0 + w // 5, cy)], fill=ROSE)
    elif g == "kilroy_memory":
        cell = w // 5
        for row in range(3):
            for col in range(4):
                px = x0 + w // 10 + col * cell
                py = y0 + h // 5 + row * cell
                draw.rectangle((px, py, px + cell - 2, py + cell - 2), fill=(30, 40, 32, 255), outline=EMERALD)
    elif g == "kilroy_syscall":
        draw.rectangle((x0 + w // 6, y0 + h // 4, x1 - w // 6, y1 - h // 4), fill=(10, 16, 12, 255), outline=ROSE)
        draw.text((x0 + w // 5, cy - h // 10), "SYS", fill=EMERALD)
    elif g == "kilroy_scheduler":
        draw.ellipse((cx - w // 3, cy - w // 3, cx + w // 3, cy + w // 3), outline=EMERALD, width=s)
        for ang in (90, 210, 330):
            rad = math.radians(ang)
            dx = int(math.cos(rad) * w // 4)
            dy = int(math.sin(rad) * h // 4)
            draw.line([(cx, cy), (cx + dx, cy + dy)], fill=ROSE, width=s)
    elif g == "kilroy_driver":
        draw.rectangle((x0 + w // 5, y0 + h // 3, x1 - w // 5, y1 - h // 4), fill=DARK_SILVER, outline=EMERALD)
        for i in range(4):
            draw.line([(x0 + w // 4, y0 + h // 3 + i * h // 8), (x1 - w // 4, y0 + h // 3 + i * h // 8)], fill=ROSE, width=1)
    elif g == "kilroy_shell":
        draw.rectangle((x0, y0, x1, y1), fill=(6, 10, 8, 255))
        draw.text((x0 + w // 8, cy - h // 10), "K>", fill=EMERALD)
    elif g == "cartridge":
        draw.rounded_rectangle((x0 + w // 8, y0 + h // 6, x1 - w // 8, y1 - h // 6), radius=4, fill=DARK_SILVER, outline=TEAL)
        draw.rectangle((x0 + w // 4, y0 + h // 4, x1 - w // 4, y1 - h // 3), fill=NAVY)
        draw.rectangle((x0 + w // 3, y1 - h // 3, x1 - w // 3, y1 - h // 6), fill=(218, 165, 32, 255))
    elif g == "disc":
        draw.ellipse((x0 + w // 10, y0 + h // 10, x1 - w // 10, y1 - h // 10), fill=SILVER, outline=TEAL)
        draw.ellipse((cx - w // 5, cy - w // 5, cx + w // 5, cy + w // 5), fill=ROSE)
        draw.ellipse((cx - w // 14, cy - w // 14, cx + w // 14, cy + w // 14), fill=BLACK)
    elif g == "arcade":
        _bevel_rect(draw, (x0 + w // 6, y0 + h // 5, x1 - w // 6, y1 - h // 8))
        draw.rectangle((x0 + w // 5, y0 + h // 4, x1 - w // 5, y0 + h // 2), fill=NAVY)
        draw.polygon([(x0 + w // 3, y0 + h // 2), (x0 + w // 3, y1 - h // 5), (x1 - w // 4, cy)], fill=YELLOW)
    elif g == "handheld":
        _bevel_rect(draw, (x0 + w // 4, y0 + h // 6, x1 - w // 4, y1 - h // 6))
        draw.rectangle((x0 + w // 3, y0 + h // 5, x1 - w // 3, y0 + h // 2), fill=TEAL)
        draw.ellipse((x0 + w // 3, y1 - h // 4, x0 + w // 2, y1 - h // 6), fill=DARK_SILVER)
        draw.ellipse((x0 + w // 2, y1 - h // 4, x1 - w // 3, y1 - h // 6), fill=DARK_SILVER)
    elif g == "game_floppy":
        _bevel_rect(draw, (x0 + w // 6, y0 + h // 8, x1 - w // 6, y1 - h // 8))
        draw.rectangle((x0 + w // 3, y0 + h // 2, x1 - w // 3, y1 - h // 4), fill=EMERALD)
        draw.text((x0 + w // 4, y0 + h // 3), "GAME", fill=BLACK)
    elif g == "digital":
        draw.rounded_rectangle((x0 + w // 8, y0 + h // 8, x1 - w // 8, y1 - h // 8), radius=6, fill=NAVY, outline=EMERALD)
        draw.polygon([(x0 + w // 3, cy - h // 6), (x0 + w // 3, cy + h // 6), (x1 - w // 3, cy)], fill=ROSE)
    elif g == "manual":
        draw.rectangle((x0 + w // 5, y0 + h // 8, x1 - w // 6, y1 - h // 8), fill=WHITE, outline=TEAL)
        draw.text((x0 + w // 4, cy - h // 12), "MAN", fill=NAVY)
    elif g == "box_art":
        draw.rectangle((x0 + w // 6, y0 + h // 8, x1 - w // 6, y1 - h // 8), fill=ROSE, outline=DARK_SILVER)
        draw.rectangle((x0 + w // 5, y0 + h // 6, x1 - w // 5, y1 - h // 5), fill=TEAL)
    elif g == "game_generic":
        draw.ellipse((x0 + w // 8, y0 + h // 8, x1 - w // 8, y1 - h // 8), fill=NAVY, outline=EMERALD)
        draw.text((x0 + w // 3, cy - h // 10), "PLAY", fill=YELLOW)
    else:
        draw.rectangle((x0 + w // 6, y0 + h // 6, x1 - w // 6, y1 - h // 6), fill=SILVER, outline=TEAL)


def render_icon(glyph: str, size: int, *, dos_mode: bool = False) -> Image.Image:
    if dos_mode or glyph.startswith("dos_") or glyph in ("command_com", "batch_file", "config_sys", "pc_dos", "ms_dos"):
        canvas = Image.new("RGBA", (size, size), DOS_BLACK)
    elif glyph.startswith("kilroy"):
        canvas = Image.new("RGBA", (size, size), (6, 10, 8, 255))
    else:
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    _draw_glyph(ImageDraw.Draw(canvas), glyph, size)
    return canvas


def _color_from_title(title: str) -> tuple[int, int, int, int]:
    h = hashlib.md5(title.encode()).hexdigest()
    r = 80 + int(h[0:2], 16) % 120
    g = 80 + int(h[2:4], 16) % 120
    b = 100 + int(h[4:6], 16) % 100
    return (r, g, b, 255)


def render_game_icon(title: str, media_glyph: str, size: int) -> Image.Image:
    base = render_icon(media_glyph, size)
    draw = ImageDraw.Draw(base)
    x0, y0, x1, y1 = _box(size, 0.18)
    letter = re.sub(r"[^A-Za-z0-9]", "", title)[:1].upper() or "?"
    tint = _color_from_title(title)
    draw.rounded_rectangle((x0, y0, x1, y1), radius=max(2, size // 10), fill=tint)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", max(8, size // 3))
    except OSError:
        font = ImageFont.load_default()
    draw.text((x0 + size // 8, y0 + size // 10), letter, fill=WHITE, font=font)
    return base


def forge_manifest(*, force: bool = True) -> dict[str, Any]:
    doc = _load_manifest()
    sizes = doc.get("sizes") or [32, 48]
    out: dict[str, Any] = {"forged": [], "shell": [], "devices": [], "games": [], "kilroy_prog": []}
    categories = doc.get("categories") or {}

    for cat_name, cat in categories.items():
        dewey = cat.get("dewey", "005.4")
        for spec in cat.get("icons") or []:
            iid = spec["id"]
            glyph = spec.get("glyph", "game_generic")
            dos_mode = cat_name == "dos"
            for sz in sizes:
                dest = FORGED_ROOT / cat_name / f"{iid}-{sz}.png"
                if force or not dest.is_file():
                    img = render_icon(glyph, sz, dos_mode=dos_mode)
                    _write(img, dest)
                out["forged"].append(str(dest))
                if cat_name == "shell":
                    shell_dest = SHELL_ROOT / f"{iid}-{sz}.png"
                    if force or not shell_dest.is_file():
                        _write(render_icon(glyph, sz), shell_dest)
                    out["shell"].append(str(shell_dest))

    # Refresh KILROY program icon from kilroy-kernel glyph
    for sz in (32, 48, 64):
        img = render_icon("kilroy_face", sz, dos_mode=False)
        for name in (f"prog-kilroy-{sz}.png", f"prog-kilroy.png" if sz == 64 else ""):
            if not name:
                continue
            dest = PROG_ICONS / name
            _write(img, dest)
            out["kilroy_prog"].append(str(dest))

    # Mirror device assets into forged/devices
    device_out = FORGED_ROOT / "devices"
    if DEVICE_ROOT.is_dir():
        for src in sorted(DEVICE_ROOT.glob("*.png")):
            for sz in sizes:
                dest = device_out / f"{src.stem}-{sz}.png"
                if force or not dest.is_file():
                    img = Image.open(src).convert("RGBA").resize((sz, sz), Image.Resampling.LANCZOS)
                    _write(img, dest)
                out["devices"].append(str(dest))

    return {"ok": True, "forged_count": len(out["forged"]), **out}


def forge_games(*, force: bool = True) -> dict[str, Any]:
    doc = _load_manifest()
    sizes = doc.get("sizes") or [32, 48]
    media_map = doc.get("console_media_map") or {}
    glyph_by_media = {
        "cartridge": "cartridge",
        "disc": "disc",
        "floppy": "game_floppy",
        "digital": "digital",
        "arcade": "arcade",
        "pcb": "arcade",
    }
    console_glyph: dict[str, str] = {}
    for media, consoles in media_map.items():
        g = glyph_by_media.get(media, "game_generic")
        for cid in consoles:
            console_glyph[cid] = g

    import importlib.util
    vg_path = NEXUS / "Hostess7" / "scripts" / "field_videogame_db.py"
    spec = importlib.util.spec_from_file_location("field_videogame_db", vg_path)
    if not spec or not spec.loader:
        return {"ok": False, "error": "videogame_db_missing"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ensure_db()
    db = json.loads(mod.DB_PATH.read_text(encoding="utf-8"))
    out: list[str] = []

    game_root = FORGED_ROOT / "games"
    console_root = FORGED_ROOT / "consoles"
    for c in db.get("consoles") or []:
        cid = c.get("id", "")
        glyph = console_glyph.get(cid, "game_generic")
        for sz in sizes:
            dest = console_root / f"{cid}-{sz}.png"
            if force or not dest.is_file():
                dev_src = DEVICE_ROOT / f"{cid}.png"
                if dev_src.is_file():
                    img = Image.open(dev_src).convert("RGBA").resize((sz, sz), Image.Resampling.LANCZOS)
                else:
                    img = render_icon(glyph, sz)
                _write(img, dest)
            out.append(str(dest))

    for g in db.get("games") or []:
        gid = g.get("id", "")
        title = g.get("title", gid)
        cid = g.get("console_id", "")
        glyph = console_glyph.get(cid, "game_generic")
        for sz in sizes:
            dest = game_root / f"{gid}-{sz}.png"
            if force or not dest.is_file():
                _write(render_game_icon(title, glyph, sz), dest)
            out.append(str(dest))

    return {"ok": True, "game_icons": len(out), "paths": out}


def build_all(*, force: bool = True) -> dict[str, Any]:
    m = forge_manifest(force=force)
    g = forge_games(force=force)
    return {"ok": True, "manifest": m, "games": g}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "build").strip().lower()
    force = "--force" in sys.argv or "-f" in sys.argv
    if cmd in ("build", "all"):
        print(json.dumps(build_all(force=force), ensure_ascii=False))
        return 0
    if cmd == "manifest":
        print(json.dumps(forge_manifest(force=force), ensure_ascii=False))
        return 0
    if cmd == "games":
        print(json.dumps(forge_games(force=force), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-library-icon-forge.py [build|manifest|games] [--force]"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())