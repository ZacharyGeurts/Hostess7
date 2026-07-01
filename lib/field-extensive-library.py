#!/usr/bin/env pythong
"""Extensive library — every PC/console, game catalog, programming greats, Dewey + H7/H7c."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-extensive-library-doctrine.json"
SEED = INSTALL / "data" / "field-extensive-library-seed.json"
PANEL = STATE / "field-extensive-library-panel.json"
LIBRARY = STATE / "field-extensive-library.json"
DEWEY_ROOT = INSTALL / "library" / "dewey"
SHELF_DEVICES = DEWEY_ROOT / "004-computers"
SHELF_GAMES = DEWEY_ROOT / "700-arts" / "games"
SHELF_GREATS = DEWEY_ROOT / "920-biography" / "game-programming-greats"
SHELF_H7C = DEWEY_ROOT


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


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(INSTALL.resolve()))
    except ValueError:
        return str(path)


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _queen_systems() -> list[dict[str, Any]]:
    qr = INSTALL / "Queen" / "data" / "queen-game-room.json"
    doc = _load(qr, {})
    out = []
    for row in doc.get("systems") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        out.append({
            "id": row["id"],
            "name": row.get("label", row["id"]),
            "year": int(str(row.get("era", "1980")).replace("—", "0") or 1980),
            "maker": "Various",
            "cpu": row.get("cpu", ""),
            "source": "queen_game_room",
            "form_factor": "handheld" if row.get("ratio") == "10/9" else "console",
        })
    return out


def _videogame_consoles() -> list[dict[str, Any]]:
    vg = INSTALL / "Hostess7" / "scripts" / "field_videogame_db.py"
    if not vg.is_file():
        return []
    spec = importlib.util.spec_from_file_location("field_videogame_db", vg)
    if not spec or not spec.loader:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [dict(c, source="videogame_db") for c in getattr(mod, "CONSOLES", ())]


def _videogame_games() -> list[dict[str, Any]]:
    vg = INSTALL / "Hostess7" / "scripts" / "field_videogame_db.py"
    if not vg.is_file():
        return []
    spec = importlib.util.spec_from_file_location("field_videogame_db", vg)
    if not spec or not spec.loader:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [dict(g, source="videogame_db") for g in getattr(mod, "SEED_GAMES", ())]


def _merge_consoles(seed: dict[str, Any]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in seed.get("consoles") or []:
        if isinstance(row, dict) and row.get("id"):
            by_id[str(row["id"])] = {**row, "source": "seed"}
    for row in _videogame_consoles():
        cid = str(row.get("id", ""))
        if cid:
            by_id[cid] = {**by_id.get(cid, {}), **row}
    for row in _queen_systems():
        cid = str(row.get("id", ""))
        if cid:
            prev = by_id.get(cid, {})
            by_id[cid] = {**prev, **row, "name": prev.get("name") or row.get("name")}
    return sorted(by_id.values(), key=lambda r: (int(r.get("year") or 0), str(r.get("name") or r.get("id"))))


def _merge_devices(seed: dict[str, Any]) -> list[dict[str, Any]]:
    devices = list(seed.get("devices") or [])
    seen = {str(d.get("id")) for d in devices}
    for con in _merge_consoles(seed):
        cid = str(con.get("id", ""))
        if cid and cid not in seen:
            devices.append({
                "id": cid,
                "label": con.get("name") or cid,
                "maker": con.get("maker", "Various"),
                "year": con.get("year"),
                "form_factor": con.get("form_factor", "console"),
                "cpu": con.get("cpu", ""),
                "source": con.get("source", "console"),
                "dewey": "004.678",
            })
            seen.add(cid)
    return devices


def _nes_catalog_games() -> list[dict[str, Any]]:
    cat = INSTALL / "data" / "nes-cartridge-catalog.json"
    doc = _load(cat, {})
    out: list[dict[str, Any]] = []
    for row in doc.get("entries") or []:
        if not isinstance(row, dict) or not row.get("id"):
            continue
        out.append({**row, "source": "nes_cartridge_catalog"})
    return out


def _merge_games(seed: dict[str, Any]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in seed.get("games") or []:
        if isinstance(row, dict) and row.get("id"):
            by_id[str(row["id"])] = {**row, "source": "seed"}
    for row in _videogame_games():
        gid = str(row.get("id", ""))
        if gid:
            by_id[gid] = {**by_id.get(gid, {}), **row}
    for row in _nes_catalog_games():
        gid = str(row.get("id", ""))
        if gid:
            by_id[gid] = {**by_id.get(gid, {}), **row}
    return sorted(by_id.values(), key=lambda r: (int(r.get("year") or 0), str(r.get("title") or r.get("id"))))


def _greats(seed: dict[str, Any]) -> list[dict[str, Any]]:
    return list(seed.get("programming_greats") or [])


def _entry_text_device(dev: dict[str, Any]) -> str:
    label = dev.get("label") or dev.get("name") or dev.get("id")
    lines = [
        f"# {label}",
        "",
        f"**Maker:** {dev.get('maker', 'Unknown')}",
        f"**Year:** {dev.get('year', '—')}",
        f"**Form factor:** {dev.get('form_factor', dev.get('type', 'device'))}",
        f"**CPU:** {dev.get('cpu', '—')}",
        f"**Dewey:** {dev.get('dewey', '004')}",
        "",
        "## Overview",
        f"The {label} is catalogued in the Field extensive library.",
        "Device image generated procedurally for library shelf display.",
        "",
        "## Library ties",
        "- Dewey shelf: 004-computers",
        "- H7c compressed entry available",
        "- Combinatronic balance table resolves on read",
    ]
    return "\n".join(lines)


def _entry_text_great(g: dict[str, Any]) -> str:
    lines = [
        f"# {g.get('name', g.get('id'))}",
        "",
        f"**Born:** {g.get('born', '—')}",
        f"**Era:** {g.get('era', '—')}",
        f"**Known for:** {', '.join(g.get('known_for') or [])}",
        "",
        "## Biography",
        str(g.get("bio", "")),
        "",
        "## Dewey",
        f"Classification: {g.get('dewey', '920.92')} — Game programming greats",
    ]
    return "\n".join(lines)


def _entry_text_game(game: dict[str, Any]) -> str:
    title = game.get("title", game.get("id"))
    lines = [
        f"# {title}",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Console | {game.get('console_id', '—')} |",
        f"| Year | {game.get('year', '—')} |",
        f"| Publisher | {game.get('publisher', '—')} |",
        f"| Developer | {game.get('developer', '—')} |",
        f"| Genre | {game.get('genre', '—')} |",
        f"| Media | {game.get('media_type', 'cartridge')} |",
    ]
    if game.get("rom"):
        rom = game["rom"]
        lines.append(f"| ROM file | `{rom.get('filename', '—')}` |")
    if game.get("ines"):
        ines = game["ines"]
        lines.extend([
            f"| PRG ROM | {ines.get('prg_kb', 0)} KB |",
            f"| CHR ROM | {ines.get('chr_kb', 0)} KB |",
            f"| Mapper | {ines.get('mapper', '—')} ({ines.get('mapper_name', '')}) |",
        ])
    lines.extend([
        "",
        "## Catalog entry",
        "Part of the Field extensive game catalog — every game ever, expand via ingest.",
        f"Dewey: {game.get('dewey', '794.8')}",
    ])
    if game.get("cover") or game.get("box_path"):
        lines.extend([
            "",
            "## Cover art",
            f"- Box: `{game.get('cover') or game.get('box_path')}`",
            f"- Cartridge: `{game.get('cart_path', '')}`",
        ])
    return "\n".join(lines)


def _pack_entry_h7c(entry_id: str, text: str, meta: dict[str, Any], shelf: Path) -> Path | None:
    """Pack H7c in-place on Dewey shelf — primary library format."""
    h7c = _import_mod("field_h7c", "field-h7c-compression.py")
    if not h7c:
        return None
    book_dir = shelf / entry_id
    dest = book_dir / f"{entry_id}.h7c"
    try:
        m = {"id": entry_id, "field_layer": 1, "block_wrapper": True, "ironclad_citation": "ironclad:h7c:1", **meta}
        packed = h7c.pack_h7c(text, m, use_optimizer=True, format_version=2)
        if hasattr(h7c, "wrap_h7c_block"):
            packed = h7c.wrap_h7c_block(packed, m)
        book_dir.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(packed)
        cover = f"/library/assets/devices/{entry_id}.png"
        if meta.get("category") == "game":
            cover = str(meta.get("cover") or meta.get("box_path") or "")
        elif meta.get("category") == "biography":
            cover = ""
        (book_dir / "book.json").write_text(json.dumps({
            "id": entry_id,
            "title": meta.get("title", entry_id),
            "author": meta.get("author", "Field Extensive Library"),
            "dewey": meta.get("dewey", ""),
            "format": "h7c",
            "h7c": _rel(dest),
            "cover": cover or None,
            "ready": True,
        }, indent=2) + "\n", encoding="utf-8")
        legacy_h7 = book_dir / f"{entry_id}.h7"
        if legacy_h7.is_file():
            legacy_h7.unlink()
        return dest
    except Exception:
        return None


def sync_dewey_shelves(*, pack: bool = True) -> dict[str, Any]:
    seed = _load(SEED, {})
    devices = _merge_devices(seed)
    games = _merge_games(seed)
    greats = _greats(seed)
    synced = {"devices": 0, "games": 0, "greats": 0, "h7c": 0}

    for dev in devices:
        eid = str(dev.get("id", ""))
        if not eid:
            continue
        text = _entry_text_device(dev)
        meta = {"title": dev.get("label") or dev.get("name"), "category": "device", "dewey": dev.get("dewey", "004")}
        if pack and _pack_entry_h7c(eid, text, meta, SHELF_DEVICES):
            synced["h7c"] += 1
        synced["devices"] += 1

    for g in greats:
        eid = str(g.get("id", ""))
        if not eid:
            continue
        text = _entry_text_great(g)
        meta = {"title": g.get("name"), "category": "biography", "dewey": g.get("dewey", "920.92"), "author": g.get("name")}
        if pack and _pack_entry_h7c(eid, text, meta, SHELF_GREATS):
            synced["h7c"] += 1
        synced["greats"] += 1

    for game in games:
        eid = str(game.get("id", ""))
        if not eid:
            continue
        text = _entry_text_game(game)
        meta = {
            "title": game.get("title"),
            "category": "game",
            "dewey": game.get("dewey", "794.8"),
            "cover": game.get("cover") or game.get("box_path"),
            "box_path": game.get("box_path"),
            "cart_path": game.get("cart_path"),
        }
        shelf = SHELF_GAMES / "nes" if str(game.get("console_id")) == "nes" and str(game.get("id", "")).startswith("nes_") else SHELF_GAMES
        if pack and _pack_entry_h7c(eid, text, meta, shelf):
            synced["h7c"] += 1
        synced["games"] += 1

    manifest_text = _manifest_text(devices, games, greats)
    manifest_dir = SHELF_DEVICES / "extensive_library_manifest"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / "manifest.txt").write_text(manifest_text, encoding="utf-8")
    if pack:
        h7c = _import_mod("field_h7c", "field-h7c-compression.py")
        if h7c:
            packed = h7c.pack_h7c(manifest_text, {"id": "extensive_library_manifest", "title": "Extensive Library Manifest"})
            (manifest_dir / "manifest.h7c").write_bytes(packed)

    for shelf, name in (
        (SHELF_DEVICES, "004-computers"),
        (SHELF_GAMES, "700-arts/games"),
        (SHELF_GREATS, "920-biography/game-programming-greats"),
    ):
        shelf.mkdir(parents=True, exist_ok=True)
        shelf_json = shelf / "shelf.json"
        shelf_json.write_text(json.dumps({
            "schema": "dewey-shelf/v1",
            "shelf": name,
            "updated": _now(),
            "device_count": len(devices) if "004" in name else None,
            "game_count": len(games) if "games" in name else None,
            "greats_count": len(greats) if "greats" in name else None,
        }, indent=2) + "\n", encoding="utf-8")

    return synced


def _manifest_text(devices: list, games: list, greats: list) -> str:
    lines = [
        "# Field Extensive Library Manifest",
        "",
        f"Devices: {len(devices)}",
        f"Consoles/PCs catalogued with procedural device images.",
        f"Games: {len(games)}",
        f"Programming greats: {len(greats)}",
        "",
        "## H7 / H7c",
        "Every entry packed as H7 (zlib+FLD1) and H7c (combinatronic balance table).",
        "Decompression near-instant as balance table fills on execute.",
        "",
        "## Dewey shelves",
        "- 004-computers — devices and PCs",
        "- 700-arts/games — game catalog",
        "- 920-biography/game-programming-greats — history of game programming legends",
        "- library/dewey — H7c in-place on every shelf",
    ]
    return "\n".join(lines)


def build_library(*, sync: bool = True, render_devices: bool = True, force: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    bal = _import_mod("ext_bal", "field-combinatronic-balance.py")
    entry: dict[str, Any] = {}
    if bal and hasattr(bal, "combinatoric_entry"):
        entry = bal.combinatoric_entry("library", refresh=sync, force=force, battery_path=LIBRARY)
        if entry.get("skip_build") and entry.get("cached_doc"):
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            if hasattr(bal, "record_cycle"):
                bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
            out = dict(entry["cached_doc"])
            out["fast_path"] = True
            out["balance_hold"] = True
            out["balance_gate"] = entry.get("gate")
            out["elapsed_ms"] = elapsed_ms
            out["combinatronic"] = True
            out["optimized_combinatronic"] = True
            return out
    seed = _load(SEED, {})
    devices = _merge_devices(seed)
    consoles = _merge_consoles(seed)
    games = _merge_games(seed)
    greats = _greats(seed)

    device_visuals = None
    if render_devices:
        dv = _import_mod("field_device_visuals", "field-device-visuals.py")
        if dv:
            try:
                device_visuals = dv.generate_all()
            except Exception as exc:
                device_visuals = {"ok": False, "error": str(exc)}

    dewey_sync = sync_dewey_shelves(pack=sync) if sync else {}

    registry_sync: dict[str, Any] = {}
    if sync:
        reg = _import_mod("field_library_registry", "field-library-registry.py")
        if reg and hasattr(reg, "sync_registry_shelves"):
            try:
                registry_sync = reg.sync_registry_shelves()
            except Exception as exc:
                registry_sync = {"ok": False, "error": str(exc)}

    h7c_panel = {}
    h7c_mod = _import_mod("field_h7c", "field-h7c-compression.py")
    if h7c_mod:
        h7c_panel = h7c_mod.panel()

    for pool in (devices, consoles, games, greats):
        for row in pool:
            row["combinatronic"] = True
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    gate = entry.get("gate") or {}
    doc = {
        "schema": "field-extensive-library/v1",
        "updated": _now(),
        "ok": True,
        "motto": seed.get("motto", "Every PC and console — Dewey-tied library."),
        "counts": {
            "devices": len(devices),
            "consoles": len(consoles),
            "games": len(games),
            "greats": len(greats),
            "total_entries": len(devices) + len(games) + len(greats),
        },
        "dewey_shelves": seed.get("dewey_shelves", {}),
        "dewey_sync": dewey_sync,
        "registry_sync": registry_sync,
        "device_visuals": device_visuals,
        "h7c": h7c_panel,
        "ingest_sources": seed.get("ingest_sources", []),
        "devices": devices,
        "consoles": consoles,
        "games": games,
        "programming_greats": greats,
        "elapsed_ms": elapsed_ms,
        "balance_gate": gate or None,
        "combinatronic": True,
        "all_data_combinatronic": True,
        "optimized_combinatronic": bool(gate.get("balanced")),
        "entry_synchronous": True,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=not gate.get("skip_reorganize"), elapsed_ms=elapsed_ms)
    return doc


def publish_panel(*, refresh: bool = True) -> dict[str, Any]:
    lib = build_library(sync=refresh, render_devices=refresh)
    _save(LIBRARY, lib)
    panel = {
        "schema": "field-extensive-library-panel/v1",
        "updated": lib["updated"],
        "ok": lib["ok"],
        "counts": lib["counts"],
        "h7c_balance": (lib.get("h7c") or {}).get("balance"),
        "h7c_balanced": (lib.get("h7c") or {}).get("balanced"),
        "dewey_sync": lib.get("dewey_sync"),
        "sample_devices": (lib.get("devices") or [])[:8],
        "sample_games": (lib.get("games") or [])[:8],
        "sample_greats": (lib.get("programming_greats") or [])[:6],
    }
    _save(PANEL, panel)
    return {"ok": True, "panel": panel, "library_path": str(LIBRARY)}


def search_library(query: str, *, limit: int = 48) -> list[dict[str, Any]]:
    lib = _load(LIBRARY, {}) or build_library(sync=False, render_devices=False)
    q = query.lower().strip()
    if not q:
        return []
    hits: list[tuple[int, dict[str, Any]]] = []
    pools = [
        ("device", lib.get("devices") or []),
        ("console", lib.get("consoles") or []),
        ("game", lib.get("games") or []),
        ("great", lib.get("programming_greats") or []),
    ]
    for kind, rows in pools:
        for row in rows:
            blob = json.dumps(row, ensure_ascii=False).lower()
            score = sum(3 if tok in blob else 0 for tok in q.split())
            if score:
                hits.append((score, {"kind": kind, **row}))
    hits.sort(key=lambda x: (-x[0], x[1].get("label") or x[1].get("title") or x[1].get("name") or ""))
    return [h[1] for h in hits[:limit]]


def catalog_for_h7_bridge() -> list[dict[str, Any]]:
    """Entries exposed to h7-library-bridge — reads unified field-library-registry."""
    reg = _import_mod("field_library_registry", "field-library-registry.py")
    if reg and hasattr(reg, "catalog_for_h7_bridge"):
        try:
            return reg.catalog_for_h7_bridge()
        except Exception:
            pass
    lib = _load(LIBRARY, {}) or build_library(sync=False, render_devices=False)
    books: list[dict[str, Any]] = []
    for g in lib.get("programming_greats") or []:
        books.append({
            "id": f"great-{g['id']}",
            "title": f"{g.get('name')} — Game Programming Great",
            "author": g.get("name", "Field"),
            "category": "biography",
            "dewey": g.get("dewey", "920.92"),
            "description": (g.get("bio") or "")[:200],
            "source": "field-extensive-library",
        })
    books.append({
        "id": "extensive-library-manifest",
        "title": "Field Extensive Library Manifest",
        "author": "NEXUS-Shield / Hostess7",
        "category": "reference",
        "dewey": "004",
        "description": "Every PC, console, game, and programming great — Dewey catalog with H7/H7c.",
        "source": "field-extensive-library",
    })
    return books


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "status", "json"):
        if PANEL.is_file() and cmd != "build":
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel().get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish", "sync"):
        refresh = "--no-render" not in sys.argv
        print(json.dumps(publish_panel(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "library":
        print(json.dumps(build_library(sync=False, render_devices=False), ensure_ascii=False, indent=2))
        return 0
    if cmd == "search":
        q = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps({"query": q, "hits": search_library(q)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "catalog":
        print(json.dumps(catalog_for_h7_bridge(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        pub = publish_panel(refresh=True)
        counts = (pub.get("panel") or {}).get("counts") or {}
        ok = (
            counts.get("devices", 0) >= 40
            and counts.get("games", 0) >= 25
            and counts.get("greats", 0) >= 15
        )
        print(json.dumps({"ok": ok, "counts": counts}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({"error": "usage", "cmds": ["panel", "build", "library", "search", "catalog", "verify"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())