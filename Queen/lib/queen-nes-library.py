#!/usr/bin/env pythong
"""Queen NES Library API — catalog tiles, Have sorting, ROM availability for Game Room."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
NEXUS = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN.parent))
CATALOG = NEXUS / "data" / "nes-cartridge-catalog.json"

MAPPER_FIXES: dict[int, str] = {
    0: "NROM — no mapper fix needed",
    1: "MMC1 — battery games need .sav path; verify PRG swap",
    2: "UxROM — UNROM bus conflicts rare; CHR RAM titles OK",
    3: "CNROM — fixed CHR; pirated multi-ROM dumps may need trim",
    4: "MMC3 — IRQ timing sensitive; use CHIPS MMC3 path",
    7: "AxROM — one-screen mirroring titles need four-screen off",
    11: "Color Dreams — unlicensed; CIC disabled in CHIPS",
    34: "BNROM — 32KB PRG switch; verify iNES header PRG count",
    66: "GNROM — dual CHR switch; CHIPS handles GNROM table",
}


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _forge_mod() -> Any | None:
    script = NEXUS / "lib" / "field-nes-cartridge-forge.py"
    if not script.is_file():
        return None
    spec = importlib.util.spec_from_file_location("nes_forge_lib", script)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _resolve_rom_path(entry: dict[str, Any], live_roms: dict[str, dict[str, Any]]) -> tuple[bool, str | None]:
    rom = entry.get("rom") or {}
    path = rom.get("path")
    if path and Path(str(path)).is_file():
        return True, str(Path(path).resolve())
    stem = rom.get("stem") or ""
    if stem and stem in live_roms:
        return True, live_roms[stem]["path"]
    norm_title = str(entry.get("title") or "").lower()
    for s, info in live_roms.items():
        if s.replace("_", " ") in norm_title or norm_title.replace(" ", "_") == s:
            return True, info["path"]
    return False, None


def _library_row(entry: dict[str, Any], live_roms: dict[str, dict[str, Any]]) -> dict[str, Any]:
    have, rom_path = _resolve_rom_path(entry, live_roms)
    ines = entry.get("ines") or {}
    mapper = int(ines.get("mapper") or 0) if ines else 0
    return {
        "id": entry.get("id"),
        "title": entry.get("title"),
        "year": entry.get("year"),
        "publisher": entry.get("publisher"),
        "genre": entry.get("genre"),
        "hardware_form": entry.get("hardware_form") or "nes",
        "license": entry.get("license"),
        "license_label": entry.get("license_label"),
        "have_rom": have,
        "dimmed": not have,
        "rom_path": rom_path,
        "rom_filename": (entry.get("rom") or {}).get("filename"),
        "cart_path": entry.get("cart_path"),
        "box_path": entry.get("box_path"),
        "sleeve_path": entry.get("sleeve_path"),
        "ines": ines or None,
        "mapper_fix": MAPPER_FIXES.get(mapper, f"Mapper {mapper} — CHIPS auto-detect"),
        "playable": have,
    }


def library_panel() -> dict[str, Any]:
    cat = _load(CATALOG, {})
    entries = list(cat.get("entries") or [])
    forge = _forge_mod()
    live_roms = forge.scan_roms() if forge and hasattr(forge, "scan_roms") else {}
    rows = [_library_row(e, live_roms) for e in entries if e.get("id")]
    have_n = sum(1 for r in rows if r.get("have_rom"))
    return {
        "schema": "queen-nes-library/v1",
        "ok": True,
        "system": "nes",
        "count": len(rows),
        "catalog_count": cat.get("count", len(rows)),
        "rom_count": have_n,
        "missing_count": len(rows) - have_n,
        "live_scan": len(live_roms),
        "sort_options": ["title_az", "title_za", "have_first", "have_last"],
        "motto": "Every dumped ROM playable — gray tiles are metadata-only until you add the .nes",
        "any_dumped_rom": True,
        "chips_path": "CHIPS/Nes",
    }


def library_list(
    *,
    sort: str = "title_az",
    query: str = "",
    offset: int = 0,
    limit: int = 96,
    have_only: bool = False,
) -> dict[str, Any]:
    panel = library_panel()
    cat = _load(CATALOG, {})
    entries = list(cat.get("entries") or [])
    forge = _forge_mod()
    live_roms = forge.scan_roms() if forge and hasattr(forge, "scan_roms") else {}
    rows = [_library_row(e, live_roms) for e in entries if e.get("id")]
    q = str(query or "").lower().strip()
    if q:
        rows = [r for r in rows if q in json.dumps(r, ensure_ascii=False).lower()]
    if have_only:
        rows = [r for r in rows if r.get("have_rom")]

    sort_key = str(sort or "title_az").lower()
    if sort_key == "title_za":
        rows.sort(key=lambda r: str(r.get("title") or "").lower(), reverse=True)
    elif sort_key == "have_first":
        rows.sort(key=lambda r: (not r.get("have_rom"), str(r.get("title") or "").lower()))
    elif sort_key == "have_last":
        rows.sort(key=lambda r: (r.get("have_rom"), str(r.get("title") or "").lower()))
    else:
        rows.sort(key=lambda r: str(r.get("title") or "").lower())

    off = max(0, int(offset))
    lim = max(1, min(500, int(limit)))
    page = rows[off : off + lim]
    return {
        **panel,
        "sort": sort_key,
        "query": q or None,
        "offset": off,
        "limit": lim,
        "total": len(rows),
        "entries": page,
    }


def library_detail(nes_id: str) -> dict[str, Any]:
    cat = _load(CATALOG, {})
    entry = next((e for e in (cat.get("entries") or []) if str(e.get("id")) == nes_id), None)
    if not entry:
        return {"ok": False, "error": "not_found", "id": nes_id}
    forge = _forge_mod()
    live_roms = forge.scan_roms() if forge and hasattr(forge, "scan_roms") else {}
    row = _library_row(entry, live_roms)
    return {"ok": True, "entry": row}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "list").strip().lower()
    if action in ("panel", "status", "json"):
        return library_panel()
    if action in ("list", "catalog", "search"):
        return library_list(
            sort=str(body.get("sort") or "title_az"),
            query=str(body.get("query") or body.get("q") or ""),
            offset=int(body.get("offset") or 0),
            limit=int(body.get("limit") or 96),
            have_only=bool(body.get("have_only") or body.get("rom_only")),
        )
    if action in ("detail", "get"):
        return library_detail(str(body.get("id") or body.get("nes_id") or ""))
    return {"ok": False, "error": "unknown_action", "actions": ["panel", "list", "detail"]}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        sort = sys.argv[2] if len(sys.argv) > 2 else "title_az"
        print(json.dumps(library_list(sort=sort), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(library_panel(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())