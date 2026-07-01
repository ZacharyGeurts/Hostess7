#!/usr/bin/env pythong
"""Textbook cover art — publisher-accurate procedural covers for every OER textbook."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-textbook-covers-doctrine.json"
ASSETS = INSTALL / "library" / "assets" / "covers"
PANEL = STATE / "field-textbook-covers-panel.json"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

PUBLISHER_STYLE: dict[str, dict[str, Any]] = {
    "OpenStax": {
        "header": (229, 106, 84),
        "accent": (196, 69, 54),
        "body": (248, 248, 246),
        "title": (26, 42, 68),
        "badge": "OpenStax",
        "badge_color": (255, 255, 255),
    },
    "Wikibooks": {
        "header": (51, 102, 153),
        "accent": (36, 74, 112),
        "body": (240, 246, 252),
        "title": (20, 36, 56),
        "badge": "Wikibooks",
        "badge_color": (255, 255, 255),
    },
    "Project Gutenberg": {
        "header": (92, 58, 36),
        "accent": (140, 96, 58),
        "body": (252, 246, 236),
        "title": (48, 32, 20),
        "badge": "Gutenberg",
        "badge_color": (255, 248, 220),
    },
    "Field": {
        "header": (42, 58, 78),
        "accent": (94, 234, 212),
        "body": (24, 28, 36),
        "title": (220, 228, 240),
        "badge": "Field",
        "badge_color": (94, 234, 212),
    },
}

SUBJECT_MOTIF: dict[str, dict[str, Any]] = {
    "math": {"glyph": "∑", "band": (32, 56, 96), "orb": (218, 180, 72)},
    "science": {"glyph": "⚗", "band": (28, 110, 88), "orb": (120, 200, 160)},
    "english_ela": {"glyph": "Aa", "band": (96, 48, 72), "orb": (200, 160, 180)},
    "history": {"glyph": "⌛", "band": (120, 48, 40), "orb": (200, 140, 90)},
    "civics": {"glyph": "⚖", "band": (48, 72, 120), "orb": (140, 170, 220)},
    "geography": {"glyph": "🌐", "band": (40, 100, 140), "orb": (100, 180, 220)},
    "health": {"glyph": "+", "band": (180, 60, 72), "orb": (240, 160, 170)},
    "computer_science": {"glyph": "</>", "band": (36, 52, 88), "orb": (100, 200, 180)},
    "art": {"glyph": "◆", "band": (140, 56, 120), "orb": (220, 140, 200)},
    "music": {"glyph": "♪", "band": (72, 40, 100), "orb": (180, 120, 220)},
    "foreign_language": {"glyph": "文", "band": (56, 88, 120), "orb": (160, 190, 220)},
    "social_studies": {"glyph": "◎", "band": (88, 64, 48), "orb": (180, 150, 110)},
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _font(size: int, *, bold: bool = False):
    from PIL import ImageFont  # noqa: WPS433

    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _publisher_for(book: dict[str, Any]) -> str:
    pub = str(book.get("publisher") or "")
    if pub in PUBLISHER_STYLE:
        return pub
    bid = str(book.get("id") or "")
    if bid.startswith("openstax_"):
        return "OpenStax"
    if bid.startswith("wikibooks_"):
        return "Wikibooks"
    if bid.startswith("gutenberg_"):
        return "Project Gutenberg"
    return "Field"


def _subject_for(book: dict[str, Any]) -> str:
    return str(book.get("subject") or book.get("category") or "social_studies")


def _wrap_lines(draw, text: str, font, max_width: int, *, limit: int = 6) -> list[str]:
    words = text.replace("—", " ").split()
    lines: list[str] = []
    line = ""
    for word in words:
        test = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and line:
            lines.append(line)
            line = word
        else:
            line = test
    if line:
        lines.append(line)
    return lines[:limit]


def render_textbook_cover(book: dict[str, Any], dest: Path | None = None) -> Path:
    """Render publisher-style textbook cover PNG — actual cover art, not placeholder."""
    from PIL import Image, ImageDraw  # noqa: WPS433

    book_id = str(book.get("id") or "textbook")
    title = str(book.get("title") or book_id)
    publisher = _publisher_for(book)
    subject = _subject_for(book)
    style = PUBLISHER_STYLE.get(publisher, PUBLISHER_STYLE["Field"])
    motif = SUBJECT_MOTIF.get(subject, SUBJECT_MOTIF["social_studies"])
    grade = str(book.get("grade_band") or "")

    w, h = 400, 600
    img = Image.new("RGB", (w, h), color=style["body"])
    draw = ImageDraw.Draw(img)

    header_h = 88
    draw.rectangle([0, 0, w, header_h], fill=style["header"])
    draw.rectangle([0, header_h - 6, w, header_h], fill=style["accent"])
    draw.rectangle([16, h - 72, w - 16, h - 16], outline=style["accent"], width=2)

    badge_font = _font(18, bold=True)
    title_font = _font(26, bold=True)
    sub_font = _font(14)
    small_font = _font(12)

    draw.text((24, 18), str(style["badge"]), fill=style["badge_color"], font=badge_font)

    orb_x, orb_y = w - 90, 140
    draw.ellipse([orb_x, orb_y, orb_x + 120, orb_y + 120], fill=motif["orb"], outline=motif["band"], width=3)
    glyph_font = _font(42, bold=True)
    draw.text((orb_x + 36, orb_y + 32), str(motif["glyph"]), fill=motif["band"], font=glyph_font)

    y = 110
    for ln in _wrap_lines(draw, title, title_font, w - 48, limit=5):
        draw.text((24, y), ln, fill=style["title"], font=title_font)
        y += 34

    if grade:
        draw.text((24, h - 108), f"Grades {grade}", fill=style["accent"], font=sub_font)
    draw.text((24, h - 84), publisher, fill=style["title"], font=sub_font)
    lic = str(book.get("license") or "OER")
    draw.text((24, h - 62), lic, fill=style["accent"], font=small_font)

    digest = hashlib.sha256(f"{book_id}:{title}".encode()).hexdigest()[:6]
    draw.text((w - 90, h - 40), digest.upper(), fill=style["accent"], font=small_font)

    out_dir = dest.parent if dest else ASSETS / book_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = dest or (out_dir / "front.png")
    img.save(out_path, optimize=True)
    return out_path


def cover_asset_path(book_id: str) -> Path:
    return ASSETS / book_id / "front.png"


def cover_url(book_id: str) -> str:
    return f"/library/assets/covers/{book_id}/front.png"


def _k12_catalog() -> list[dict[str, Any]]:
    path = INSTALL / "Hostess7" / "scripts" / "field_k12_catalog.py"
    if not path.is_file():
        return []
    spec = importlib.util.spec_from_file_location("field_k12_catalog", path)
    if not spec or not spec.loader:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "iter_all_textbooks"):
        return list(mod.iter_all_textbooks())
    return [dict(r) for r in getattr(mod, "K12_TEXTBOOKS", ())]


def _mirror_to_field_drive(book_id: str, src: Path) -> Path | None:
    lib_path = INSTALL / "lib" / "h7-library-librarian.py"
    if not lib_path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("h7_lib_librarian", lib_path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        safe = book_id.replace("/", "_")
        dest_dir = mod.covers_dir() / safe
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "front.png"
        dest.write_bytes(src.read_bytes())
        return dest
    except Exception:
        return None


def generate_cover(book_id: str, book: dict[str, Any] | None = None) -> dict[str, Any]:
    row = book or {"id": book_id, "title": book_id}
    if not row.get("title"):
        row["title"] = book_id
    src = render_textbook_cover(row)
    field_copy = _mirror_to_field_drive(book_id, src)
    return {
        "id": book_id,
        "cover": cover_url(book_id),
        "cover_path": str(src.relative_to(INSTALL)) if src.is_relative_to(INSTALL) else str(src),
        "field_cover": str(field_copy) if field_copy else None,
        "publisher": _publisher_for(row),
        "subject": _subject_for(row),
    }


def generate_all_textbooks(*, mirror_field: bool = True) -> dict[str, Any]:
    books = _k12_catalog()
    generated: list[dict[str, Any]] = []
    for book in books:
        bid = str(book.get("id") or "")
        if not bid:
            continue
        generated.append(generate_cover(bid, book))
    return {
        "schema": "field-textbook-covers/v1",
        "updated": _now(),
        "ok": True,
        "count": len(generated),
        "covers": generated,
        "assets_root": str(ASSETS.relative_to(INSTALL)) if ASSETS.is_relative_to(INSTALL) else str(ASSETS),
    }


def sync_textbook_covers(books: list[dict[str, Any]] | None = None) -> int:
    """Ensure every textbook in catalog has an actual cover image."""
    rows = books if books is not None else _k12_catalog()
    built = 0
    for book in rows:
        bid = str(book.get("id") or "")
        if not bid:
            continue
        dest = cover_asset_path(bid)
        if dest.is_file() and dest.stat().st_size > 500:
            continue
        generate_cover(bid, book)
        built += 1
    return built


def panel() -> dict[str, Any]:
    covers = list(ASSETS.glob("*/front.png")) if ASSETS.is_dir() else []
    k12 = _k12_catalog()
    return {
        "schema": "field-textbook-covers-panel/v1",
        "updated": _now(),
        "ok": True,
        "k12_count": len(k12),
        "cover_count": len(covers),
        "assets_root": str(ASSETS.relative_to(INSTALL)) if ASSETS.is_relative_to(INSTALL) else str(ASSETS),
        "publishers": list(PUBLISHER_STYLE.keys()),
        "subjects": list(SUBJECT_MOTIF.keys()),
        "statement": "Publisher-accurate textbook covers — OpenStax, Wikibooks, Gutenberg styling",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "status", "json"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("generate", "build", "all"):
        print(json.dumps(generate_all_textbooks(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "render" and len(sys.argv) >= 3:
        bid = sys.argv[2]
        books = {str(b.get("id")): b for b in _k12_catalog()}
        print(json.dumps(generate_cover(bid, books.get(bid)), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        sync_textbook_covers()
        k12 = _k12_catalog()
        missing = [str(b["id"]) for b in k12 if not cover_asset_path(str(b["id"])).is_file()]
        ok = len(missing) == 0
        print(json.dumps({"ok": ok, "k12": len(k12), "missing": missing[:8]}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({"error": "usage", "cmds": ["panel", "generate", "render <id>", "verify"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())