#!/usr/bin/env python3
"""Generate OG social preview from hero + title overlay."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
HERO = ROOT / "assets/images/field-research-hero.jpg"
OUT = ROOT / "docs/assets/images/og-image.jpg"
SIZE = (1200, 630)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def main() -> None:
    base = Image.open(HERO).convert("RGB")
    base = base.resize(
        (max(SIZE[0], int(base.width * SIZE[1] / base.height)), SIZE[1]),
        Image.Resampling.LANCZOS,
    )
    left = (base.width - SIZE[0]) // 2
    base = base.crop((left, 0, left + SIZE[0], SIZE[1]))
    overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(SIZE[1]):
        t = y / SIZE[1]
        a = int(120 + 135 * t**1.2)
        draw.line([(0, y), (SIZE[0], y)], fill=(10, 4, 12, a))
    img = Image.alpha_composite(base.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(img)
    draw.text((48, 420), "FIELD RESEARCH", font=font(FONT_REG, 22), fill=(251, 113, 133, 255))
    draw.text((48, 455), "The Book of Grok's Heart", font=font(FONT_BOLD, 44), fill=(255, 240, 245, 255))
    draw.text((48, 530), "13 chapters · Grok16 · combinatorics · compatibility layers", font=font(FONT_REG, 20), fill=(184, 160, 176, 255))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.convert("RGB").save(OUT, quality=92)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()