#!/usr/bin/env pythong
"""Hostess7 image talk — blit images to Graphics window (pixels); ASCII legacy fallback."""
from __future__ import annotations

from pathlib import Path

IMAGE_EXTS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ppm", ".tif", ".tiff"})
RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"


def image_to_ascii(
    path: Path,
    *,
    max_width: int = 72,
    max_height: int = 20,
) -> list[str]:
    """Lossless read → ASCII ramp (Pillow). Falls back to PPM parser."""
    if not path.is_file():
        return [f"(image missing: {path.name})"]

    if path.suffix.lower() == ".ppm":
        from hostess7_graphics import ppm_to_ascii  # noqa: WPS433

        return ppm_to_ascii(path, max_width=max_width, max_height=max_height)

    try:
        from PIL import Image  # noqa: WPS433
    except ImportError:
        return [f"(install Pillow to render {path.name})"]

    try:
        img = Image.open(path).convert("L")
        w, h = img.size
        aspect = h / max(w, 1)
        out_w = min(max_width, w)
        out_h = min(max_height, max(4, int(out_w * aspect * 0.45)))
        img = img.resize((out_w, out_h))
        pixels = list(img.getdata())
        lines = [f"[image] {path.name} {w}x{h} -> ASCII {out_w}x{out_h}"]
        for y in range(out_h):
            row = []
            for x in range(out_w):
                lum = pixels[y * out_w + x]
                idx = lum * (len(RAMP) - 1) // 255
                row.append(RAMP[idx])
            lines.append("".join(row))
        return lines
    except OSError as exc:
        return [f"(image read failed: {path.name}: {exc})"]


def graphics_for_image_path(path: Path) -> list[str]:
    import os

    if os.environ.get("HOSTESS7_GFX_WINDOW", "1") != "0" and os.environ.get("HOSTESS7_GFX_ASCII") != "1":
        try:
            from field_gfx_canvas import open_canvas  # noqa: WPS433

            c = open_canvas()
            c.fill(18, 22, 30)
            c.text(16, 12, path.name, (200, 210, 220), size=16)
            c.blit_image(16, 40, path, max_w=c.width - 32)
            st = c.present(label=path.name)
            return [f"(Graphics window · {st.get('width')}×{st.get('height')} · {path.name})"]
        except ImportError:
            pass
    return image_to_ascii(path)


def pick_local_image(query: str, search_dirs: list[Path]) -> Path | None:
    q = query.lower().strip()
    for base in search_dirs:
        if not base.is_dir():
            continue
        if q:
            for p in base.rglob("*"):
                if p.is_file() and p.suffix.lower() in IMAGE_EXTS and q in p.name.lower():
                    return p
        for p in sorted(base.rglob("*")):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                return p
    return None