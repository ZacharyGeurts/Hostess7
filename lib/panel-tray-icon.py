#!/usr/bin/env pythong
"""Queen tray icon — Amouranth branding at taskbar pixel size (local assets only)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

TRAY_PIXEL_SIZES = (22, 24, 32)
DARK_FILL = (2, 4, 3, 255)
DARK_EDGE = (26, 77, 50, 255)
EMERALD = (34, 197, 94, 255)
ICON_BASENAME = "queen-tray"
LEGACY_BASENAME = "nexus-tray-us"
ZNETWORK_BASENAME = "znetwork-tray"
ZNETWORK_FILL = (8, 18, 32, 255)
ZNETWORK_EDGE = (56, 189, 248, 255)
ZNETWORK_GLOW = (14, 165, 233, 255)
ZNETWORK_CORE = (125, 211, 252, 255)


def _queen_source(install: Path) -> Path:
    candidates = (
        install / "Queen" / "world" / "assets" / "branding" / "amouranth-gentle.png",
        install / "Queen" / "world" / "assets" / "branding" / "queen-tray-source.png",
        install / "panel" / "assets" / "nexus-field-256.png",
        install / "panel" / "assets" / "nexus-field.png",
        install / "panel" / "assets" / f"{ICON_BASENAME}.png",
    )
    for p in candidates:
        if p.is_file() and p.stat().st_size > 0:
            return p
    return candidates[0]


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


def render_tray_icon(face: Image.Image, size: int) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    margin = 1
    icon_px = size - 2 * margin
    icon_sq = _crop_face(face).resize((icon_px, icon_px), Image.Resampling.LANCZOS)
    if size <= 32:
        icon_sq = icon_sq.filter(ImageFilter.UnsharpMask(radius=0.5, percent=150, threshold=1))

    mask = Image.new("L", (icon_px, icon_px), 0)
    draw_mask = ImageDraw.Draw(mask)
    radius = max(2, icon_px // 6)
    draw_mask.rounded_rectangle((0, 0, icon_px - 1, icon_px - 1), radius=radius, fill=255)
    icon_sq.putalpha(mask)

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (margin, margin, margin + icon_px - 1, margin + icon_px - 1),
        radius=radius,
        fill=DARK_FILL,
        outline=DARK_EDGE,
        width=1,
    )
    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=radius + 1,
        outline=EMERALD,
        width=1,
    )
    canvas.paste(icon_sq, (margin, margin), icon_sq)
    return canvas


def install_xdg_tray_icons(install: Path, home: Path | None = None) -> None:
    home = home or Path(os.environ.get("HOME", "/home/default"))
    assets = install / "panel" / "assets"
    cache_root = home / ".local/share/icons/hicolor"
    for px in TRAY_PIXEL_SIZES:
        for base in (ICON_BASENAME, LEGACY_BASENAME, "nexus-field"):
            src = assets / f"{base}-{px}.png"
            if not src.is_file() and base != "nexus-field":
                continue
            if base == "nexus-field":
                src = assets / f"nexus-field-{px}.png"
            if not src.is_file():
                continue
            for name in ("queen-browser.png", "nexus-shield-panel.png", "nexus-field.png"):
                dest = cache_root / f"{px}x{px}" / "apps" / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
    for px_dir in cache_root.glob("*x*"):
        if px_dir.is_dir():
            subprocess.run(["gtk-update-icon-cache", "-f", str(px_dir)], capture_output=True, timeout=8)


def _znetwork_z_points(cx: int, cy: int, w: int, h: int) -> list[tuple[int, int]]:
    """Bold Z polygon for tray overlay."""
    x0, x1 = cx - w // 2, cx + w // 2
    y0, y1 = cy - h // 2, cy + h // 2
    thick = max(2, w // 5)
    return [
        (x0, y0),
        (x1, y0),
        (x1, y0 + thick),
        (x0 + thick * 2, y1 - thick),
        (x1, y1 - thick),
        (x1, y1),
        (x0, y1),
        (x0, y1 - thick),
        (x1 - thick * 2, y0 + thick),
        (x0, y0 + thick),
    ]


def render_znetwork_tray_icon(size: int) -> Image.Image:
    """ZNetwork taskbar glyph — network graph with Z overlay (no external assets)."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    margin = max(1, size // 10)
    radius = max(2, size // 6)
    draw.rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=radius,
        fill=ZNETWORK_FILL,
        outline=ZNETWORK_EDGE,
        width=1,
    )

    cx, cy = size // 2, size // 2
    node_r = max(1, size // 10)
    nodes = [
        (margin + node_r, margin + node_r * 2),
        (size - margin - node_r, margin + node_r * 2),
        (margin + node_r, size - margin - node_r),
        (size - margin - node_r, size - margin - node_r),
        (cx, cy - node_r),
        (cx, cy + node_r),
    ]
    edges = (
        (0, 4), (1, 4), (2, 5), (3, 5), (0, 2), (1, 3), (4, 5), (0, 1), (2, 3),
    )
    for a, b in edges:
        x0, y0 = nodes[a]
        x1, y1 = nodes[b]
        draw.line((x0, y0, x1, y1), fill=ZNETWORK_GLOW, width=max(1, size // 16))
    for nx, ny in nodes:
        draw.ellipse(
            (nx - node_r, ny - node_r, nx + node_r, ny + node_r),
            fill=ZNETWORK_CORE,
            outline=ZNETWORK_GLOW,
        )

    zw = max(6, size - 2 * margin - 2)
    zh = max(6, int(zw * 0.72))
    z_pts = _znetwork_z_points(cx, cy, zw, zh)
    draw.polygon(z_pts, fill=(240, 249, 255, 245), outline=ZNETWORK_EDGE)
    return canvas


def install_znetwork_xdg_icons(install: Path, home: Path | None = None) -> None:
    home = home or Path(os.environ.get("HOME", "/home/default"))
    cache_root = home / ".local/share/icons/hicolor"
    assets = install / "panel" / "assets"
    for px in TRAY_PIXEL_SIZES:
        src = assets / f"{ZNETWORK_BASENAME}-{px}.png"
        if not src.is_file():
            continue
        for name in ("znetwork-field-panel.png", "znetwork-tray.png"):
            dest = cache_root / f"{px}x{px}" / "apps" / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(src.read_bytes())
    for px_dir in cache_root.glob("*x*"):
        if px_dir.is_dir():
            subprocess.run(["gtk-update-icon-cache", "-f", str(px_dir)], capture_output=True, timeout=8)


def build_znetwork_tray_icons(install: Path, state: Path, *, force: bool = False) -> Path:
    icon = state / "znetwork-tray.png"
    stamp_file = state / "znetwork-tray-icon.stamp"
    tag = "znetwork-v3:z-over-network"
    state.mkdir(parents=True, exist_ok=True)
    assets = install / "panel" / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    if (
        not force
        and icon.is_file()
        and icon.stat().st_size > 0
        and stamp_file.is_file()
        and stamp_file.read_text(encoding="utf-8", errors="replace").strip() == tag
    ):
        return icon
    rendered: dict[int, Image.Image] = {}
    for px in TRAY_PIXEL_SIZES:
        rendered[px] = render_znetwork_tray_icon(px)
        rendered[px].save(assets / f"{ZNETWORK_BASENAME}-{px}.png", format="PNG")
    rendered[max(TRAY_PIXEL_SIZES)].save(icon, format="PNG")
    install_znetwork_xdg_icons(install)
    stamp_file.write_text(tag + "\n", encoding="utf-8")
    return icon


def build_tray_icons(install: Path, state: Path, *, force: bool = False) -> Path:
    kit = install / "Queen" / "scripts" / "queen-icon-kit.py"
    if kit.is_file() and force:
        subprocess.run([sys.executable, str(kit)], capture_output=True, timeout=60)

    src = _queen_source(install)
    icon = state / "nexus-tray.png"
    stamp_file = state / "nexus-tray-icon.stamp"
    tag = f"queen-v1:{src}:{src.stat().st_mtime_ns if src.is_file() else 0}"
    state.mkdir(parents=True, exist_ok=True)
    assets = install / "panel" / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    prebuilt = assets / f"{ICON_BASENAME}-32.png"
    if not force and prebuilt.is_file() and prebuilt.stat().st_size > 0:
        prebuilt_bytes = prebuilt.read_bytes()
        icon.write_bytes(prebuilt_bytes)
        install_xdg_tray_icons(install)
        stamp_file.write_text(tag + "\n", encoding="utf-8")
        return icon

    if not src.is_file():
        raise FileNotFoundError(f"Queen tray source missing: {src}")

    face = Image.open(src)
    rendered: dict[int, Image.Image] = {}
    for px in TRAY_PIXEL_SIZES:
        rendered[px] = render_tray_icon(face, px)
        for base in (ICON_BASENAME, LEGACY_BASENAME):
            rendered[px].save(assets / f"{base}-{px}.png", format="PNG")
    for px in (64, 128):
        img = render_tray_icon(face, px)
        img.save(assets / f"{ICON_BASENAME}-64.png", format="PNG")
        img.save(assets / f"{LEGACY_BASENAME}-64.png", format="PNG")
        if px == 128:
            img.save(assets / f"{ICON_BASENAME}.png", format="PNG")
            img.save(assets / f"{LEGACY_BASENAME}.png", format="PNG")

    rendered[max(TRAY_PIXEL_SIZES)].save(icon, format="PNG")
    install_xdg_tray_icons(install)
    stamp_file.write_text(tag + "\n", encoding="utf-8")
    return icon


def main() -> int:
    install = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
    state = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
    force = os.environ.get("NEXUS_TRAY_ICON_REFRESH", "0") == "1" or "--force" in sys.argv
    znet_mode = os.environ.get("NEXUS_TRAY_MODE", "").strip().lower() == "znetwork" or "--znetwork" in sys.argv
    try:
        out = build_znetwork_tray_icons(install, state, force=force) if znet_mode else build_tray_icons(install, state, force=force)
        print(out)
        return 0
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())