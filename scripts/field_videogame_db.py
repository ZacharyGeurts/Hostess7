#!/usr/bin/bin/env pythong
"""Video game database — consoles, cartridges, boxes, manuals from dawn to present."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "cache" / "fieldstorage" / "brain" / "videogames" / "database.json"
DB_VERSION = 1

# Major consoles — dawn of time → present
CONSOLES: tuple[dict[str, Any], ...] = (
    {"id": "magnavox_odyssey", "name": "Magnavox Odyssey", "year": 1972, "maker": "Magnavox", "media": "cartridge", "generation": 1},
    {"id": "atari_2600", "name": "Atari 2600", "year": 1977, "maker": "Atari", "media": "cartridge", "generation": 2},
    {"id": "intellivision", "name": "Intellivision", "year": 1979, "maker": "Mattel", "media": "cartridge", "generation": 2},
    {"id": "colecovision", "name": "ColecoVision", "year": 1982, "maker": "Coleco", "media": "cartridge", "generation": 2},
    {"id": "nes", "name": "Nintendo Entertainment System", "year": 1985, "maker": "Nintendo", "media": "cartridge", "generation": 3},
    {"id": "master_system", "name": "Sega Master System", "year": 1986, "maker": "Sega", "media": "cartridge", "generation": 3},
    {"id": "atari_7800", "name": "Atari 7800", "year": 1986, "maker": "Atari", "media": "cartridge", "generation": 3},
    {"id": "tg16", "name": "TurboGrafx-16", "year": 1989, "maker": "NEC", "media": "cartridge", "generation": 4},
    {"id": "genesis", "name": "Sega Genesis", "year": 1989, "maker": "Sega", "media": "cartridge", "generation": 4},
    {"id": "snes", "name": "Super Nintendo", "year": 1991, "maker": "Nintendo", "media": "cartridge", "generation": 4},
    {"id": "cdi", "name": "Philips CD-i", "year": 1991, "maker": "Philips", "media": "disc", "generation": 4},
    {"id": "jaguar", "name": "Atari Jaguar", "year": 1993, "maker": "Atari", "media": "cartridge", "generation": 5},
    {"id": "3do", "name": "3DO", "year": 1993, "maker": "3DO", "media": "disc", "generation": 5},
    {"id": "ps1", "name": "PlayStation", "year": 1995, "maker": "Sony", "media": "disc", "generation": 5},
    {"id": "saturn", "name": "Sega Saturn", "year": 1995, "maker": "Sega", "media": "disc", "generation": 5},
    {"id": "n64", "name": "Nintendo 64", "year": 1996, "maker": "Nintendo", "media": "cartridge", "generation": 5},
    {"id": "dreamcast", "name": "Dreamcast", "year": 1999, "maker": "Sega", "media": "disc", "generation": 6},
    {"id": "ps2", "name": "PlayStation 2", "year": 2000, "maker": "Sony", "media": "disc", "generation": 6},
    {"id": "gc", "name": "GameCube", "year": 2001, "maker": "Nintendo", "media": "disc", "generation": 6},
    {"id": "xbox", "name": "Xbox", "year": 2001, "maker": "Microsoft", "media": "disc", "generation": 6},
    {"id": "xbox360", "name": "Xbox 360", "year": 2005, "maker": "Microsoft", "media": "disc", "generation": 7},
    {"id": "ps3", "name": "PlayStation 3", "year": 2006, "maker": "Sony", "media": "disc", "generation": 7},
    {"id": "wii", "name": "Wii", "year": 2006, "maker": "Nintendo", "media": "disc", "generation": 7},
    {"id": "ps4", "name": "PlayStation 4", "year": 2013, "maker": "Sony", "media": "disc", "generation": 8},
    {"id": "xbox_one", "name": "Xbox One", "year": 2013, "maker": "Microsoft", "media": "disc", "generation": 8},
    {"id": "switch", "name": "Nintendo Switch", "year": 2017, "maker": "Nintendo", "media": "cartridge", "generation": 8},
    {"id": "ps5", "name": "PlayStation 5", "year": 2020, "maker": "Sony", "media": "disc", "generation": 9},
    {"id": "xbox_series", "name": "Xbox Series X/S", "year": 2020, "maker": "Microsoft", "media": "disc", "generation": 9},
    {"id": "pc_dos", "name": "PC DOS games", "year": 1981, "maker": "Various", "media": "floppy", "generation": "pc"},
    {"id": "pc_windows", "name": "PC Windows", "year": 1995, "maker": "Various", "media": "digital", "generation": "pc"},
    {"id": "arcade", "name": "Arcade cabinets", "year": 1971, "maker": "Various", "media": "pcb", "generation": "arcade"},
    {"id": "gameboy", "name": "Game Boy", "year": 1989, "maker": "Nintendo", "media": "cartridge", "generation": "handheld"},
    {"id": "gba", "name": "Game Boy Advance", "year": 2001, "maker": "Nintendo", "media": "cartridge", "generation": "handheld"},
    {"id": "nds", "name": "Nintendo DS", "year": 2004, "maker": "Nintendo", "media": "cartridge", "generation": "handheld"},
    {"id": "psp", "name": "PlayStation Portable", "year": 2005, "maker": "Sony", "media": "disc", "generation": "handheld"},
    {"id": "3ds", "name": "Nintendo 3DS", "year": 2011, "maker": "Nintendo", "media": "cartridge", "generation": "handheld"},
)

# Seed titles — schema supports infinite expansion via ingest
GAME_TEMPLATE_FIELDS = (
    "id", "title", "console_id", "year", "publisher", "developer",
    "media_type", "region", "genre", "players", "manual_url", "box_art_url",
    "cartridge_label", "mobygames_id", "tgdb_id", "description",
)

SEED_GAMES: tuple[dict[str, Any], ...] = (
    {"id": "pacman_arcade", "title": "Pac-Man", "console_id": "arcade", "year": 1980, "publisher": "Namco", "genre": "maze", "media_type": "pcb"},
    {"id": "super_mario_bros", "title": "Super Mario Bros.", "console_id": "nes", "year": 1985, "publisher": "Nintendo", "genre": "platform", "media_type": "cartridge"},
    {"id": "zelda_nes", "title": "The Legend of Zelda", "console_id": "nes", "year": 1986, "publisher": "Nintendo", "genre": "action-adventure", "media_type": "cartridge"},
    {"id": "sonic_genesis", "title": "Sonic the Hedgehog", "console_id": "genesis", "year": 1991, "publisher": "Sega", "genre": "platform", "media_type": "cartridge"},
    {"id": "street_fighter2", "title": "Street Fighter II", "console_id": "snes", "year": 1992, "publisher": "Capcom", "genre": "fighting", "media_type": "cartridge"},
    {"id": "chrono_trigger", "title": "Chrono Trigger", "console_id": "snes", "year": 1995, "publisher": "Square", "genre": "rpg", "media_type": "cartridge"},
    {"id": "mario_64", "title": "Super Mario 64", "console_id": "n64", "year": 1996, "publisher": "Nintendo", "genre": "platform", "media_type": "cartridge"},
    {"id": "ff7", "title": "Final Fantasy VII", "console_id": "ps1", "year": 1997, "publisher": "Square", "genre": "rpg", "media_type": "disc"},
    {"id": "half_life", "title": "Half-Life", "console_id": "pc_windows", "year": 1998, "publisher": "Valve", "genre": "fps", "media_type": "disc"},
    {"id": "halo_xbox", "title": "Halo: Combat Evolved", "console_id": "xbox", "year": 2001, "publisher": "Microsoft", "genre": "fps", "media_type": "disc"},
    {"id": "gta3", "title": "Grand Theft Auto III", "console_id": "ps2", "year": 2001, "publisher": "Rockstar", "genre": "action", "media_type": "disc"},
    {"id": "minecraft", "title": "Minecraft", "console_id": "pc_windows", "year": 2011, "publisher": "Mojang", "genre": "sandbox", "media_type": "digital"},
    {"id": "breath_wild", "title": "The Legend of Zelda: Breath of the Wild", "console_id": "switch", "year": 2017, "publisher": "Nintendo", "genre": "action-adventure", "media_type": "cartridge"},
    {"id": "elden_ring", "title": "Elden Ring", "console_id": "ps5", "year": 2022, "publisher": "Bandai Namco", "genre": "action-rpg", "media_type": "disc"},
    {"id": "pong_odyssey", "title": "Table Tennis (Pong)", "console_id": "magnavox_odyssey", "year": 1972, "publisher": "Magnavox", "genre": "sports", "media_type": "cartridge"},
    {"id": "adventure_2600", "title": "Adventure", "console_id": "atari_2600", "year": 1980, "publisher": "Atari", "genre": "action-adventure", "media_type": "cartridge"},
)

INGEST_SOURCES: tuple[dict[str, str], ...] = (
    {"id": "mobygames", "url": "https://www.mobygames.com", "why": "Game metadata + covers + manuals"},
    {"id": "tgdb", "url": "https://thegamesdb.net", "why": "Box art + platform databases"},
    {"id": "igdb", "url": "https://www.igdb.com", "why": "Comprehensive game API"},
    {"id": "tcrf", "url": "https://tcrf.net", "why": "Prototype/unused content"},
    {"id": "archive_org_games", "url": "https://archive.org/details/software", "why": "Historical software + manuals"},
)


def ensure_db() -> Path:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if DB_PATH.is_file():
        try:
            data = json.loads(DB_PATH.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < DB_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        doc = {
            "version": DB_VERSION,
            "schema": list(GAME_TEMPLATE_FIELDS),
            "consoles": list(CONSOLES),
            "games": list(SEED_GAMES),
            "ingest_sources": list(INGEST_SOURCES),
            "stats": {
                "console_count": len(CONSOLES),
                "game_count": len(SEED_GAMES),
                "note": "Expand via mobygames/tgdb ingest — every cartridge/box/manual indexed by id",
            },
        }
        DB_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return DB_PATH


def search_games(query: str, *, limit: int = 12) -> list[dict[str, Any]]:
    ensure_db()
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    consoles = {c["id"]: c for c in data.get("consoles", [])}
    q = query.lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 2]
    scored: list[tuple[int, dict]] = []
    for g in data.get("games", []):
        cid = g.get("console_id", "")
        cname = consoles.get(cid, {}).get("name", "")
        blob = f"{g.get('title','')} {cid} {cname} {g.get('publisher','')} {g.get('genre','')}".lower()
        score = sum(6 if t in blob else 0 for t in tokens)
        if q in blob:
            score += 15
        if score > 0:
            hit = dict(g)
            hit["console_name"] = cname
            scored.append((score, hit))
    for c in data.get("consoles", []):
        blob = f"{c.get('name','')} {c.get('id','')} {c.get('maker','')}".lower()
        score = sum(6 if t in blob else 0 for t in tokens)
        if score > 0:
            scored.append((score, {"type": "console", **c}))
    scored.sort(key=lambda x: -x[0])
    return [x[1] for x in scored[:limit]]


def format_db_summary() -> str:
    ensure_db()
    data = json.loads(DB_PATH.read_text(encoding="utf-8"))
    return (
        f"Video game DB: {data['stats']['console_count']} consoles, "
        f"{data['stats']['game_count']} seed titles — expand to every cartridge/box/manual."
    )


def main() -> int:
    ensure_db()
    print(format_db_summary())
    print(f"METRIC videogame_consoles={len(CONSOLES)}")
    print(f"METRIC videogame_seed_games={len(SEED_GAMES)}")
    print("OK videogame-db")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())