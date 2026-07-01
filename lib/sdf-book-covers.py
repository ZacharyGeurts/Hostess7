#!/usr/bin/env pythong
"""Book cover → R8 SDF on field drive. Reads PNG/JPG from field only — never fetches."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def _librarian():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "h7_library_librarian", ROOT / "lib" / "h7-library-librarian.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _save_r8_png(path: Path, field: np.ndarray) -> None:
    arr = np.clip((field * 64.0) + 128.0, 0, 255).astype(np.uint8)
    Image.fromarray(arr, mode="L").save(path, optimize=True)


def _image_to_sdf(img: Image.Image, size: tuple[int, int] = (256, 384)) -> np.ndarray:
    """Cover art → signed distance field (book aspect ratio)."""
    gray = img.convert("L").resize(size, Image.Resampling.LANCZOS)
    arr = np.asarray(gray, dtype=np.float32) / 255.0
    edge = arr < 0.92
    try:
        from scipy.ndimage import distance_transform_edt  # type: ignore

        dist_in = distance_transform_edt(edge)
        dist_out = distance_transform_edt(1.0 - edge)
        field = (dist_out - dist_in).astype(np.float32)
    except ImportError:
        field = np.where(edge, -2.0, 4.0).astype(np.float32)
    return field / max(size) * 10.0


def _generate_title_cover(title: str, author: str, dest: Path) -> Path:
    """Field-local synthetic cover when no image on drive."""
    from PIL import ImageDraw, ImageFont

    w, h = 400, 600
    img = Image.new("RGB", (w, h), color=(18, 28, 42))
    draw = ImageDraw.Draw(img)
    draw.rectangle([12, 12, w - 12, h - 12], outline=(180, 150, 80), width=3)
    try:
        font_t = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", 22)
        font_a = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 16)
    except OSError:
        font_t = ImageFont.load_default()
        font_a = font_t

    words = title.split()
    lines: list[str] = []
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        if len(test) > 28:
            if line:
                lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    y = 80
    for ln in lines[:8]:
        draw.text((30, y), ln, fill=(220, 210, 180), font=font_t)
        y += 32
    if author:
        draw.text((30, h - 80), author[:48], fill=(140, 160, 190), font=font_a)
    draw.text((30, 40), "H7", fill=(200, 170, 90), font=font_t)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, optimize=True)
    return dest


def build_cover_sdf(book_id: str, side: str = "front", *, title: str = "", author: str = "") -> dict[str, Any] | None:
    lib = _librarian()
    paths = lib.cover_paths(book_id)
    src = paths.get(side)
    safe = book_id.replace("/", "_")
    out_dir = lib.covers_dir() / safe
    out_dir.mkdir(parents=True, exist_ok=True)

    if not src:
        if not title:
            return None
        src = _generate_title_cover(title, author, out_dir / f"{side}.png")

    img = Image.open(src)
    field = _image_to_sdf(img)
    sdf_png = out_dir / f"{side}.sdf.png"
    sdf_json = out_dir / f"{side}.sdf.json"
    _save_r8_png(sdf_png, field)
    meta = {
        "id": f"cover-{safe}-{side}",
        "book_id": book_id,
        "side": side,
        "width": field.shape[1],
        "height": field.shape[0],
        "anchor": [field.shape[1] // 2, field.shape[0] // 2],
        "format": "r8",
        "file": f"/api/library/cover?book={book_id}&side={side}&format=sdf",
        "source": str(src),
        "book_cover": True,
    }
    sdf_json.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def build_all_on_field(book_ids: list[str] | None = None, bib: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    lib = _librarian()
    lib.library_meta_dir().mkdir(parents=True, exist_ok=True)
    built = 0
    ids = book_ids or list((bib or {}).keys())
    for bid in ids:
        row = (bib or {}).get(bid, {})
        title = str(row.get("title", bid))
        author = str(row.get("author", ""))
        for side in ("front", "back"):
            if build_cover_sdf(bid, side, title=title if side == "front" else "", author=author):
                built += 1
    return {"ok": True, "built": built, "covers_dir": str(lib.covers_dir())}


def main() -> int:
    lib = _librarian()
    bib = lib.load_bibliography_index()
    if len(sys.argv) > 1 and sys.argv[1] != "all":
        bid = sys.argv[1]
        side = sys.argv[2] if len(sys.argv) > 2 else "front"
        row = bib.get(bid, {"title": bid})
        out = build_cover_sdf(bid, side, title=str(row.get("title", bid)), author=str(row.get("author", "")))
        print(json.dumps(out or {"ok": False}, indent=2))
        return 0 if out else 1
    print(json.dumps(build_all_on_field(bib=bib), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())