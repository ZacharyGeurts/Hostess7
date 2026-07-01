#!/usr/bin/env pythong
"""NES cartridge forge — catalog metadata, iNES ROM headers, procedural cart/box art."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import struct
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SOURCE_URL = "https://raw.githubusercontent.com/thawkin3/nes-games-api/master/nes_games.json"
SOURCE_PATH = INSTALL / "data" / "nes-games-source.json"
CATALOG_PATH = INSTALL / "data" / "nes-cartridge-catalog.json"
PANEL_PATH = STATE / "field-nes-cartridge-forge-panel.json"
ASSETS = INSTALL / "library" / "assets" / "cartridges" / "nes"
SHELF_GAMES = INSTALL / "library" / "dewey" / "700-arts" / "games"
NES_SHELF = SHELF_GAMES / "nes"
VG_DB = INSTALL / "Hostess7" / "cache" / "fieldstorage" / "brain" / "videogames" / "database.json"

GENRE_COLORS: dict[str, tuple[int, int, int]] = {
    "action": (196, 48, 48),
    "shooter": (36, 88, 168),
    "platform": (48, 168, 88),
    "puzzle": (168, 120, 36),
    "racing": (48, 48, 168),
    "sports": (36, 140, 72),
    "fighting": (168, 48, 120),
    "role-playing": (120, 48, 168),
    "adventure": (48, 140, 168),
    "strategy": (88, 88, 48),
    "simulation": (88, 120, 140),
    "traditional": (120, 100, 72),
    "educational": (72, 140, 120),
    "adult": (80, 80, 80),
}

MAPPER_NAMES: dict[int, str] = {
    0: "NROM",
    1: "MMC1",
    2: "UxROM",
    3: "CNROM",
    4: "MMC3",
    7: "AxROM",
    9: "MMC2",
    11: "Color Dreams",
    34: "BNROM",
    66: "GNROM",
}

LICENSED_MAJORS = frozenset({
    "nintendo", "capcom", "konami", "hudson soft", "square", "square co., ltd.",
    "namco", "taito", "sega", "bandai", "sunsoft", "jaleco", "data east",
    "hal laboratory", "snk", "atari", "milton bradley", "acclaim", "ultra games",
    "lucasarts", "rare", "tecmo", "koei", "enix", "activision", "electronic arts",
})

UNLICENSED_PUBLISHERS = frozenset({
    "color dreams", "camerica", "wisdom tree", "active", "hack", "tengen ltd.",
    "american video entertainment", "ave", "sachen", "caltron", "unlicensed",
})

BOOTLEG_MARKERS = frozenset({"hack", "pirate", "bootleg", "multicart", "paltool"})

JP_ONLY_HINTS = frozenset({
    "coconuts japan", "pony canyon", "sammy corporation", "king records",
    "pack-in-video", "victor musical", "tokyo shoseki", "induction produce",
    "jingukan", "super mega", "c dream", "a wave", "nihon corp.",
})

US_PUBLISHER_HINTS = frozenset({
    "nintendo", "acclaim", "milton bradley", "ljn", "thq", "mindscape",
    "activision", "electronic arts", "taxan", "tradewest", "sunsoft",
})


def _classify_license(title: str, publisher: str, developer: str) -> dict[str, str]:
    pub = str(publisher or "").lower().strip()
    dev = str(developer or "").lower().strip()
    tit = str(title or "").lower()
    if any(m in pub or m in dev or m in tit for m in BOOTLEG_MARKERS):
        return {"license": "bootleg", "license_label": "Bootleg / pirate"}
    if pub in UNLICENSED_PUBLISHERS or dev in UNLICENSED_PUBLISHERS:
        return {"license": "unlicensed", "license_label": "Unlicensed (no Nintendo seal)"}
    if any(m in pub for m in LICENSED_MAJORS) or any(m in dev for m in LICENSED_MAJORS):
        brand = "Capcom" if "capcom" in pub or "capcom" in dev else (
            "Konami" if "konami" in pub or "konami" in dev else (
                "Nintendo" if "nintendo" in pub else "Licensed third party"
            )
        )
        return {"license": "licensed", "license_label": f"Licensed — {brand}"}
    if "nintendo" in tit:
        return {"license": "licensed", "license_label": "Licensed — Nintendo"}
    return {"license": "licensed", "license_label": "Licensed (assumed)"}


def _hardware_form(title: str, publisher: str) -> str:
    """Return nes (72-pin Game Pak) or famicom (60-pin cassette)."""
    pub = str(publisher or "").lower()
    tit = str(title or "")
    if any(h in pub for h in JP_ONLY_HINTS) and not any(h in pub for h in US_PUBLISHER_HINTS):
        return "famicom"
    if re.search(r"[\u3040-\u30ff\u4e00-\u9fff]", tit):
        return "famicom"
    if "famicom" in tit.lower() or "family computer" in tit.lower():
        return "famicom"
    return "nes"


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


def _save(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _slug(title: str) -> str:
    t = str(title or "").lower().strip()
    t = re.sub(r"^the\s+", "", t)
    t = re.sub(r"[''`´]", "", t)
    t = re.sub(r"[^a-z0-9]+", "_", t)
    return t.strip("_")[:56] or "untitled"


def _norm_title(title: str) -> str:
    t = str(title or "").lower()
    t = re.sub(r"^the\s+", "", t)
    t = re.sub(r"[^a-z0-9]+", "", t)
    return t


def _font(size: int, *, bold: bool = False):
    from PIL import ImageFont  # noqa: WPS433

    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _seed_int(text: str) -> int:
    return int(hashlib.md5(text.encode()).hexdigest()[:8], 16)


def _genre_color(genre: str | None) -> tuple[int, int, int]:
    key = str(genre or "action").lower().replace("_", "-")
    return GENRE_COLORS.get(key, (72, 88, 120))


def parse_ines(path: Path) -> dict[str, Any] | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if len(data) < 16 or data[:4] != b"NES\x1a":
        return None
    prg_banks = data[4]
    chr_banks = data[5]
    flags6 = data[6]
    flags7 = data[7]
    mapper = (flags7 & 0xF0) | (flags6 >> 4)
    mirroring = "vertical" if flags6 & 1 else "horizontal"
    battery = bool(flags6 & 2)
    trainer = bool(flags6 & 4)
    four_screen = bool(flags6 & 8)
    prg_kb = prg_banks * 16
    chr_kb = chr_banks * 8
    return {
        "format": "iNES",
        "prg_banks": prg_banks,
        "chr_banks": chr_banks,
        "prg_kb": prg_kb,
        "chr_kb": chr_kb,
        "mapper": mapper,
        "mapper_name": MAPPER_NAMES.get(mapper, f"Mapper {mapper}"),
        "mirroring": mirroring,
        "battery": battery,
        "trainer": trainer,
        "four_screen": four_screen,
        "file_size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def scan_roms() -> dict[str, dict[str, Any]]:
    """Scan workspace for unique .nes ROMs (canonical path per sha256)."""
    seen_hash: set[str] = set()
    out: dict[str, dict[str, Any]] = {}
    skip_parts = {"/dist/", "/build/", "/.git/"}
    for root, _dirs, files in os.walk(SG):
        if any(p in root for p in skip_parts):
            continue
        for name in files:
            if not name.lower().endswith(".nes"):
                continue
            path = Path(root) / name
            header = parse_ines(path)
            if not header:
                continue
            sha = header["sha256"]
            if sha in seen_hash:
                continue
            seen_hash.add(sha)
            stem = path.stem.lower()
            out[stem] = {
                "filename": name,
                "path": str(path.resolve()),
                "stem": stem,
                "header": header,
            }
    return out


def fetch_source() -> Path:
    if SOURCE_PATH.is_file():
        return SOURCE_PATH
    try:
        import urllib.request

        urllib.request.urlretrieve(SOURCE_URL, SOURCE_PATH)
    except Exception as exc:
        raise RuntimeError(f"fetch failed: {exc}") from exc
    return SOURCE_PATH


def build_catalog(*, link_roms: bool = True) -> dict[str, Any]:
    fetch_source()
    raw = _load(SOURCE_PATH, [])
    if not isinstance(raw, list):
        raise RuntimeError("invalid nes-games-source.json")

    roms = scan_roms() if link_roms else {}
    rom_by_norm: dict[str, list[str]] = {}
    for stem, info in roms.items():
        norm = _norm_title(stem.replace("_", " "))
        rom_by_norm.setdefault(norm, []).append(stem)

    slug_seen: dict[str, int] = {}
    entries: list[dict[str, Any]] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        if not title:
            continue
        base_slug = _slug(title)
        n = slug_seen.get(base_slug, 0)
        slug_seen[base_slug] = n + 1
        entry_id = f"nes_{base_slug}" if n == 0 else f"nes_{base_slug}_{n + 1}"
        genre = str(row.get("category") or "Action")
        year = row.get("releaseYear")
        publisher = str(row.get("publisher") or "—")
        developer = str(row.get("developer") or "—")

        rom_link = None
        norm = _norm_title(title)
        for stem in rom_by_norm.get(norm, []):
            if stem not in roms:
                continue
            rom_link = roms.pop(stem)
            break
        if not rom_link:
            for stem in list(roms.keys()):
                if stem == base_slug or stem in base_slug or base_slug.startswith(stem):
                    rom_link = roms.pop(stem)
                    break

        nes_header = rom_link["header"] if rom_link else None
        lic = _classify_license(title, publisher, developer)
        hw = _hardware_form(title, publisher)
        entry: dict[str, Any] = {
            "id": entry_id,
            "title": title,
            "console_id": "nes",
            "hardware_form": hw,
            "year": year,
            "publisher": publisher,
            "developer": developer,
            "genre": genre,
            "media_type": "cartridge",
            "region": "NTSC-J" if hw == "famicom" else "NTSC-U",
            "license": lic["license"],
            "license_label": lic["license_label"],
            "source_id": row.get("id"),
            "source": "thawkin3/nes-games-api",
            "dewey": "794.8",
            "cart_path": f"/library/assets/cartridges/nes/{entry_id}-cart.png",
            "box_path": f"/library/assets/cartridges/nes/{entry_id}-box.png",
            "booklet_path": f"/library/assets/cartridges/nes/{entry_id}-booklet.png",
            "sleeve_path": f"/library/assets/cartridges/nes/{entry_id}-sleeve.png",
            "cover": f"/library/assets/cartridges/nes/{entry_id}-box.png",
            "rom": None,
            "ines": None,
        }
        if rom_link:
            entry["rom"] = {
                "filename": rom_link["filename"],
                "path": rom_link["path"],
                "stem": rom_link["stem"],
            }
            entry["ines"] = nes_header
        entries.append(entry)

    for stem, info in roms.items():
        matched = any(
            e.get("rom", {}).get("stem") == stem
            for e in entries
            if e.get("rom")
        )
        if matched:
            continue
        entry_id = f"nes_rom_{stem}"
        tit = stem.replace("_", " ").title()
        lic = _classify_license(tit, "", "")
        entries.append({
            "id": entry_id,
            "title": tit,
            "console_id": "nes",
            "hardware_form": "nes",
            "year": None,
            "publisher": "—",
            "developer": "—",
            "genre": "Action",
            "media_type": "cartridge",
            "region": "NTSC-U",
            "license": lic["license"],
            "license_label": lic["license_label"],
            "source": "rom_scan",
            "dewey": "794.8",
            "cart_path": f"/library/assets/cartridges/nes/{entry_id}-cart.png",
            "box_path": f"/library/assets/cartridges/nes/{entry_id}-box.png",
            "booklet_path": f"/library/assets/cartridges/nes/{entry_id}-booklet.png",
            "sleeve_path": f"/library/assets/cartridges/nes/{entry_id}-sleeve.png",
            "cover": f"/library/assets/cartridges/nes/{entry_id}-box.png",
            "rom": {
                "filename": info["filename"],
                "path": info["path"],
                "stem": info["stem"],
            },
            "ines": info["header"],
        })

    doc = {
        "schema": "nes-cartridge-catalog/v1",
        "updated": _now(),
        "source_url": SOURCE_URL,
        "source_license": "MIT (thawkin3/nes-games-api)",
        "count": len(entries),
        "rom_count": sum(1 for e in entries if e.get("rom")),
        "entries": entries,
    }
    _save(CATALOG_PATH, doc)
    return doc


def _wrap_text(draw, text: str, font, max_w: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:4]


def render_generic_cart(out: Path | None = None) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    w, h = 200, 280
    img = Image.new("RGB", (w, h), (28, 30, 36))
    draw = ImageDraw.Draw(img)
    body = (168, 168, 172)
    edge = (120, 120, 128)
    draw.rounded_rectangle((36, 20, w - 36, h - 48), radius=8, fill=body, outline=edge, width=3)
    draw.rounded_rectangle((48, 36, w - 48, h - 120), radius=4, fill=(220, 220, 224), outline=(140, 140, 148))
    for x in range(52, w - 52, 14):
        draw.rectangle((x, h - 40, x + 8, h - 28), fill=(90, 92, 100))
    font = _font(11, bold=True)
    tw = draw.textlength("NES", font=font)
    draw.text(((w - tw) / 2, h - 22), "NES", fill=(60, 64, 72), font=font)
    dest = out or ASSETS / "_generic-cart.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", optimize=True)
    return dest


def render_cartridge(entry: dict[str, Any], *, out: Path | None = None) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    eid = str(entry["id"])
    title = str(entry.get("title") or eid)
    publisher = str(entry.get("publisher") or "")[:28]
    year = entry.get("year")
    genre = str(entry.get("genre") or "Action")
    accent = _genre_color(genre)
    hw = str(entry.get("hardware_form") or "nes")
    famicom = hw == "famicom"

    w, h = (180, 220) if famicom else (200, 280)
    img = Image.new("RGB", (w, h), (18, 20, 26))
    draw = ImageDraw.Draw(img)
    body = (198, 62, 48) if famicom else (158, 158, 162)
    top, bot = (24, 28, h - (36 if famicom else 48))
    draw.rounded_rectangle((40 if famicom else 36, top, w - (40 if famicom else 36), bot), radius=6 if famicom else 8, fill=body, outline=(108, 108, 116), width=3)
    draw.rounded_rectangle((50, top + 14, w - 50, bot - 70), radius=4, fill=(248, 248, 250), outline=accent, width=2)
    title_font = _font(12 if famicom else 13, bold=True)
    pub_font = _font(9)
    lines = _wrap_text(draw, title, title_font, w - 100)
    y = top + 22
    for line in lines:
        draw.text((54, y), line, fill=(24, 28, 36), font=title_font)
        y += 15
    if publisher and publisher != "—":
        draw.text((54, bot - 82), publisher[:22], fill=(80, 88, 100), font=pub_font)
    if year:
        draw.text((54, bot - 68), str(year), fill=accent, font=pub_font)
    pin_w = 10 if famicom else 14
    for x in range(54, w - 54, pin_w + 4):
        draw.rectangle((x, bot - 28, x + pin_w, bot - 18), fill=(80, 82, 90))
    badge = _font(10, bold=True)
    badge_txt = "FC" if famicom else "NES"
    draw.text((54, bot - 14), badge_txt, fill=(50, 54, 62), font=badge)
    dest = out or ASSETS / f"{eid}-cart.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", optimize=True)
    return dest


def render_booklet(entry: dict[str, Any], *, out: Path | None = None) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    eid = str(entry["id"])
    title = str(entry.get("title") or eid)
    publisher = str(entry.get("publisher") or "—")[:36]
    year = entry.get("year") or "—"
    genre = str(entry.get("genre") or "—")
    lic = str(entry.get("license_label") or "Licensed")

    w, h = 140, 200
    img = Image.new("RGB", (w, h), (252, 250, 244))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, w - 1, h - 1), outline=(180, 176, 168), width=2)
    draw.line([(w // 2, 8), (w // 2, h - 8)], fill=(200, 196, 188), width=1)
    tf = _font(11, bold=True)
    bf = _font(8)
    lines = _wrap_text(draw, title, tf, w - 24)
    y = 16
    for line in lines:
        draw.text((12, y), line, fill=(28, 32, 40), font=tf)
        y += 14
    y += 8
    for row in (f"Publisher: {publisher}", f"Year: {year}", f"Genre: {genre}", lic[:40]):
        draw.text((12, y), row, fill=(72, 78, 88), font=bf)
        y += 12
    draw.text((12, h - 28), "Instruction booklet", fill=(140, 144, 152), font=bf)
    dest = out or ASSETS / f"{eid}-booklet.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", optimize=True)
    return dest


def render_sleeve(entry: dict[str, Any], *, out: Path | None = None) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    eid = str(entry["id"])
    title = str(entry.get("title") or eid)[:32]

    w, h = 220, 300
    img = Image.new("RGB", (w, h), (12, 12, 14))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((16, 16, w - 16, h - 16), radius=4, fill=(18, 18, 22), outline=(40, 40, 48), width=3)
    draw.rectangle((24, 24, w - 24, h - 24), fill=(8, 8, 10))
    draw.text((32, h // 2 - 10), "Nintendo", fill=(200, 200, 208), font=_font(14, bold=True))
    draw.text((32, h // 2 + 8), title, fill=(120, 124, 132), font=_font(9))
    dest = out or ASSETS / f"{eid}-sleeve.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", optimize=True)
    return dest


def render_box(entry: dict[str, Any], *, out: Path | None = None) -> Path:
    from PIL import Image, ImageDraw  # noqa: WPS433

    eid = str(entry["id"])
    title = str(entry.get("title") or eid)
    publisher = str(entry.get("publisher") or "")[:32]
    year = entry.get("year")
    genre = str(entry.get("genre") or "Action")
    accent = _genre_color(genre)
    rng = _seed_int(eid)

    w, h = 320, 460
    img = Image.new("RGB", (w, h), (12, 14, 20))
    draw = ImageDraw.Draw(img)
    bg_top = tuple(max(0, c - 40) for c in accent)
    for y in range(h):
        t = y / h
        r = int(bg_top[0] * (1 - t) + accent[0] * t)
        g = int(bg_top[1] * (1 - t) + accent[1] * t)
        b = int(bg_top[2] * (1 - t) + accent[2] * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    draw.rectangle((0, 0, w, 52), fill=(220, 28, 36))
    draw.rectangle((0, h - 64, w, h), fill=(24, 26, 32))
    nes_font = _font(18, bold=True)
    draw.text((16, 14), "Nintendo Entertainment System", fill=(255, 255, 255), font=_font(11, bold=True))

    title_font = _font(22, bold=True)
    lines = _wrap_text(draw, title, title_font, w - 32)
    ty = 72
    for line in lines:
        draw.text((16, ty), line, fill=(255, 255, 255), font=title_font)
        ty += 26

    cx, cy = w // 2, h // 2 + 20
    for i in range(6):
        angle = (rng % 360) + i * 60
        rad = 40 + (rng % 50) + i * 12
        import math

        x = int(cx + math.cos(math.radians(angle)) * rad)
        y = int(cy + math.sin(math.radians(angle)) * rad * 0.7)
        size = 28 + (rng >> (i * 2)) % 40
        col = (
            min(255, accent[0] + (i * 20) % 80),
            min(255, accent[1] + (i * 30) % 60),
            min(255, accent[2] + (i * 10) % 90),
        )
        draw.ellipse((x - size // 2, y - size // 2, x + size // 2, y + size // 2), fill=col, outline=(255, 255, 255), width=2)

    meta_font = _font(11)
    meta = f"{publisher}"
    if year:
        meta += f"  ·  {year}"
    meta += f"  ·  {genre}"
    draw.text((16, h - 48), meta[:52], fill=(200, 204, 212), font=meta_font)
    draw.text((16, h - 30), "Queen Library — inspired cover (not official art)", fill=(120, 128, 140), font=_font(9))

    dest = out or ASSETS / f"{eid}-box.png"
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, "PNG", optimize=True)
    return dest


def render_all(*, force: bool = False) -> dict[str, Any]:
    catalog = _load(CATALOG_PATH) or build_catalog()
    entries = catalog.get("entries") or []
    render_generic_cart()
    rendered = 0
    skipped = 0
    errors: list[dict[str, str]] = []
    for entry in entries:
        eid = str(entry.get("id") or "")
        if not eid:
            continue
        cart = ASSETS / f"{eid}-cart.png"
        box = ASSETS / f"{eid}-box.png"
        try:
            if force or not cart.is_file() or cart.stat().st_size < 500:
                render_cartridge(entry, out=cart)
            else:
                skipped += 1
            if force or not box.is_file() or box.stat().st_size < 500:
                render_box(entry, out=box)
            booklet = ASSETS / f"{eid}-booklet.png"
            sleeve = ASSETS / f"{eid}-sleeve.png"
            if force or not booklet.is_file():
                render_booklet(entry, out=booklet)
            if force or not sleeve.is_file():
                render_sleeve(entry, out=sleeve)
            rendered += 1
        except Exception as exc:
            errors.append({"id": eid, "error": str(exc)})
    panel = {
        "schema": "field-nes-cartridge-forge-panel/v1",
        "updated": _now(),
        "ok": len(errors) == 0,
        "catalog_count": len(entries),
        "rendered": rendered,
        "skipped": skipped,
        "errors": errors[:20],
        "assets_dir": str(ASSETS),
    }
    _save(PANEL_PATH, panel)
    return panel


def _entry_markdown(entry: dict[str, Any]) -> str:
    title = entry.get("title", entry.get("id"))
    lines = [
        f"# {title}",
        "",
        "## Cartridge information",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Title | {title} |",
        f"| Console | Nintendo Entertainment System |",
        f"| Year | {entry.get('year') or '—'} |",
        f"| Publisher | {entry.get('publisher') or '—'} |",
        f"| Developer | {entry.get('developer') or '—'} |",
        f"| Genre | {entry.get('genre') or '—'} |",
        f"| Region | {entry.get('region') or 'NTSC'} |",
        f"| Hardware | {entry.get('hardware_form', 'nes').upper()} ({'60-pin Famicom' if entry.get('hardware_form') == 'famicom' else '72-pin NES Game Pak'}) |",
        f"| License | {entry.get('license_label') or entry.get('license') or '—'} |",
        f"| Media | NES Game Pak (cartridge) |",
        f"| Catalog ID | `{entry.get('id')}` |",
        f"| Data source | {entry.get('source', 'nes-cartridge-catalog')} |",
    ]
    rom = entry.get("rom")
    ines = entry.get("ines")
    if rom:
        lines.extend([
            "",
            "## ROM file (.nes)",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Filename | `{rom.get('filename', '—')}` |",
            f"| Path | `{rom.get('path', '—')}` |",
        ])
    if ines:
        lines.extend([
            "",
            "## iNES header",
            "",
            "| Field | Value |",
            "| --- | --- |",
            f"| Format | {ines.get('format', 'iNES')} |",
            f"| PRG ROM | {ines.get('prg_kb', 0)} KB ({ines.get('prg_banks', 0)} × 16 KB) |",
            f"| CHR ROM | {ines.get('chr_kb', 0)} KB ({ines.get('chr_banks', 0)} × 8 KB) |",
            f"| Mapper | {ines.get('mapper', '—')} ({ines.get('mapper_name', '')}) |",
            f"| Mirroring | {ines.get('mirroring', '—')} |",
            f"| Battery-backed SRAM | {'yes' if ines.get('battery') else 'no'} |",
            f"| Trainer | {'yes' if ines.get('trainer') else 'no'} |",
            f"| File size | {ines.get('file_size', 0):,} bytes |",
            f"| SHA-256 | `{ines.get('sha256', '')}` |",
        ])
    lines.extend([
        "",
        "## Library assets",
        "",
        f"- Cartridge: `{entry.get('cart_path')}`",
        f"- Box cover: `{entry.get('box_path')}`",
        "",
        "## Dewey",
        f"Classification: {entry.get('dewey', '794.8')} — Video games",
    ])
    return "\n".join(lines)


def _import_h7c() -> Any | None:
    path = INSTALL / "lib" / "field-h7c-compression.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_h7c", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sync_dewey_shelf() -> dict[str, Any]:
    catalog = _load(CATALOG_PATH) or build_catalog()
    entries = catalog.get("entries") or []
    h7c = _import_h7c()
    NES_SHELF.mkdir(parents=True, exist_ok=True)
    synced = 0
    for entry in entries:
        eid = str(entry.get("id") or "")
        if not eid:
            continue
        book_dir = NES_SHELF / eid
        book_dir.mkdir(parents=True, exist_ok=True)
        text = _entry_markdown(entry)
        cover = entry.get("cover") or entry.get("box_path")
        book = {
            "id": eid,
            "title": entry.get("title", eid),
            "author": entry.get("publisher", "Field NES Catalog"),
            "dewey": entry.get("dewey", "794.8"),
            "format": "h7c",
            "cover": cover,
            "ready": True,
            "console_id": "nes",
            "genre": entry.get("genre"),
            "year": entry.get("year"),
            "has_rom": bool(entry.get("rom")),
        }
        if h7c:
            try:
                packed = h7c.pack_h7c(text, {"id": eid, "title": entry.get("title"), "category": "game"}, use_optimizer=True, format_version=2)
                h7c_path = book_dir / f"{eid}.h7c"
                h7c_path.write_bytes(packed)
                book["h7c"] = str(h7c_path.relative_to(INSTALL))
            except Exception:
                pass
        (book_dir / "book.json").write_text(json.dumps(book, indent=2) + "\n", encoding="utf-8")
        synced += 1

    shelf_json = {
        "schema": "dewey-shelf/v1",
        "shelf": "700-arts/games/nes",
        "code": "794.8",
        "title": "NES cartridges",
        "updated": _now(),
        "format_primary": "h7c",
        "book_count": synced,
        "h7c_count": synced,
        "rom_count": sum(1 for e in entries if e.get("rom")),
        "books": [
            {
                "id": e["id"],
                "title": e.get("title"),
                "author": e.get("publisher", ""),
                "dewey": e.get("dewey", "794.8"),
                "format": "h7c",
                "h7c": f"library/dewey/700-arts/games/nes/{e['id']}/{e['id']}.h7c",
                "cover": e.get("cover"),
                "ready": True,
                "has_rom": bool(e.get("rom")),
            }
            for e in entries
        ],
    }
    (NES_SHELF / "shelf.json").write_text(json.dumps(shelf_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"synced": synced, "rom_count": shelf_json["rom_count"], "shelf": str(NES_SHELF)}


def sync_videogame_db() -> dict[str, Any]:
    catalog = _load(CATALOG_PATH) or build_catalog()
    entries = catalog.get("entries") or []
    vg_path = INSTALL / "Hostess7" / "scripts" / "field_videogame_db.py"
    spec = importlib.util.spec_from_file_location("field_videogame_db", vg_path)
    if not spec or not spec.loader:
        return {"ok": False, "error": "videogame_db missing"}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ensure_db()
    data = _load(mod.DB_PATH, {})
    existing = {str(g.get("id")): g for g in data.get("games") or []}
    added = 0
    for entry in entries:
        eid = str(entry.get("id") or "")
        if not eid or eid in existing:
            continue
        existing[eid] = {
            "id": eid,
            "title": entry.get("title"),
            "console_id": "nes",
            "year": entry.get("year"),
            "publisher": entry.get("publisher"),
            "developer": entry.get("developer"),
            "genre": entry.get("genre"),
            "media_type": "cartridge",
            "region": entry.get("region", "NTSC"),
            "license": entry.get("license"),
            "license_label": entry.get("license_label"),
            "hardware_form": entry.get("hardware_form", "nes"),
            "box_art_url": entry.get("box_path"),
            "cartridge_label": entry.get("cart_path"),
            "booklet_url": entry.get("booklet_path"),
            "sleeve_url": entry.get("sleeve_path"),
            "description": f"NES — {entry.get('title')}",
            "has_rom": bool(entry.get("rom")),
            "ines": entry.get("ines"),
        }
        added += 1
    data["games"] = list(existing.values())
    data["stats"] = {
        "console_count": len(data.get("consoles") or []),
        "game_count": len(data["games"]),
        "nes_catalog_count": len(entries),
        "note": "NES catalog from field-nes-cartridge-forge + seed games",
    }
    data["nes_catalog"] = {
        "path": str(CATALOG_PATH.relative_to(INSTALL)),
        "count": len(entries),
        "rom_count": sum(1 for e in entries if e.get("rom")),
        "source": SOURCE_URL,
    }
    mod.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    mod.DB_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "added": added, "total_games": len(data["games"])}


def build_all(*, force_render: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    catalog = build_catalog()
    render_panel = render_all(force=force_render)
    dewey = sync_dewey_shelf()
    vg = sync_videogame_db()
    elapsed = round((time.perf_counter() - t0) * 1000, 1)
    result = {
        "ok": True,
        "catalog_count": catalog.get("count"),
        "rom_count": catalog.get("rom_count"),
        "rendered": render_panel.get("rendered"),
        "dewey_synced": dewey.get("synced"),
        "videogame_db": vg,
        "elapsed_ms": elapsed,
    }
    _save(PANEL_PATH, {**render_panel, **result, "updated": _now()})
    return result


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    force = "--force" in sys.argv
    if cmd in ("panel", "status"):
        doc = _load(PANEL_PATH, {})
        if not doc:
            doc = build_all(force_render=False)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd == "fetch":
        fetch_source()
        print(json.dumps({"ok": True, "path": str(SOURCE_PATH)}, indent=2))
        return 0
    if cmd == "catalog":
        print(json.dumps(build_catalog(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("render", "images"):
        print(json.dumps(render_all(force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sync":
        print(json.dumps({"dewey": sync_dewey_shelf(), "videogame_db": sync_videogame_db()}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "all"):
        print(json.dumps(build_all(force_render=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "roms":
        print(json.dumps(scan_roms(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["panel", "fetch", "catalog", "render", "sync", "build", "roms"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())