#!/usr/bin/env python3
"""Field Library Registry — single point of informational value for every collection on the globe."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-library-registry-doctrine.json"
REGISTRY = STATE / "field-library-registry.json"
PANEL = STATE / "field-library-registry-panel.json"
DEWEY_ROOT = INSTALL / "library" / "dewey"

SUBJECT_DEWEY: dict[str, str] = {
    "math": "510",
    "science": "500",
    "english_ela": "800",
    "history": "900",
    "civics": "320",
    "geography": "910",
    "health": "613",
    "computer_science": "004",
    "art": "700",
    "music": "780",
    "foreign_language": "400",
    "social_studies": "300",
    "device": "004",
    "game": "794.8",
    "biography": "920.92",
    "format": "005.7",
    "reference": "020",
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


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(INSTALL.resolve()))
    except ValueError:
        return str(path)


def _k12_textbooks() -> list[dict[str, Any]]:
    path = INSTALL / "Hostess7" / "scripts" / "field_k12_catalog.py"
    if not path.is_file():
        return []
    spec = importlib.util.spec_from_file_location("k12_cat", path)
    if not spec or not spec.loader:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if hasattr(mod, "iter_all_textbooks"):
        return list(mod.iter_all_textbooks())
    return [dict(r) for r in getattr(mod, "K12_TEXTBOOKS", ())]


def _cover_for(book_id: str) -> str:
    rel = f"library/assets/covers/{book_id}/front.png"
    if (INSTALL / rel).is_file():
        return f"/{rel}"
    return f"/library/assets/covers/{book_id}/front.png"


def _content_balance(entry: dict[str, Any]) -> dict[str, Any]:
    bal = _import_mod("comb_bal", "field-combinatronic-balance.py")
    if not bal or not hasattr(bal, "read_content_balance"):
        return {}
    try:
        return bal.read_content_balance(
            str(entry.get("id") or ""),
            fmt=str(entry.get("format") or ""),
            collection=str(entry.get("collection") or ""),
        )
    except Exception:
        return {}


def _stamp_entry(entry: dict[str, Any]) -> dict[str, Any]:
    row = dict(entry)
    row["combinatronic"] = True
    cb = _content_balance(row)
    if cb:
        row["combinatronic_balance"] = cb
        if cb.get("balance_id"):
            row["balance_id"] = cb["balance_id"]
        if cb.get("best_identifier"):
            row["best_identifier"] = True
        if cb.get("precise_file"):
            row["precise_file"] = True
        if cb.get("no_cost"):
            row["no_cost"] = True
    return row


def _entry_textbook(book: dict[str, Any]) -> dict[str, Any]:
    bid = str(book.get("id") or "")
    subject = str(book.get("subject") or book.get("category") or "social_studies")
    dewey = book.get("dewey") or SUBJECT_DEWEY.get(subject, "370")
    return {
        "id": bid,
        "title": book.get("title", bid),
        "author": book.get("publisher", "OER"),
        "category": subject,
        "dewey": dewey,
        "grade_band": book.get("grade_band"),
        "publisher": book.get("publisher"),
        "license": book.get("license"),
        "journal": "textbook",
        "format": "textbook",
        "ready": True,
        "source": "field-library-registry",
        "collection": "textbooks",
        "cover": _cover_for(bid),
        "description": (book.get("body") or "")[:240],
    }


def _entry_device(dev: dict[str, Any]) -> dict[str, Any]:
    eid = str(dev.get("id") or "")
    label = dev.get("label") or dev.get("name") or eid
    return {
        "id": eid,
        "title": label,
        "author": dev.get("maker", "Field"),
        "category": "device",
        "dewey": dev.get("dewey", "004"),
        "format": "h7c",
        "ready": True,
        "source": "field-library-registry",
        "collection": "devices",
        "cover": f"/library/assets/devices/{eid}.png",
        "description": f"{label} — {dev.get('cpu', '')} · {dev.get('year', '')}",
    }


def _entry_game(game: dict[str, Any]) -> dict[str, Any]:
    eid = str(game.get("id") or "")
    return {
        "id": eid,
        "title": game.get("title", eid),
        "author": game.get("publisher", "Field"),
        "category": "game",
        "dewey": game.get("dewey", "794.8"),
        "format": "h7c",
        "ready": True,
        "source": "field-library-registry",
        "collection": "games",
        "description": f"{game.get('genre', '')} · {game.get('year', '')}",
    }


def _entry_great(g: dict[str, Any]) -> dict[str, Any]:
    eid = str(g.get("id") or "")
    name = g.get("name", eid)
    return {
        "id": f"great-{eid}",
        "title": f"{name} — Game Programming Great",
        "author": name,
        "category": "biography",
        "dewey": g.get("dewey", "920.92"),
        "format": "h7c",
        "ready": True,
        "source": "field-library-registry",
        "collection": "programming_greats",
        "description": (g.get("bio") or "")[:200],
    }


def _entry_format(fmt: dict[str, Any]) -> dict[str, Any]:
    fid = str(fmt.get("id") or "")
    return {
        "id": f"format-{fid}",
        "title": fmt.get("label", fid),
        "author": "Field File Formats Registry",
        "category": "format",
        "dewey": fmt.get("dewey", "005.7"),
        "format": "registry-entry",
        "ready": True,
        "source": "field-library-registry",
        "collection": "file_formats",
        "cover": f"/library/assets/formats/{fid}.png",
        "extensions": fmt.get("extensions"),
        "magic": fmt.get("magic"),
        "mime": fmt.get("mime"),
        "family": fmt.get("family"),
        "description": fmt.get("description", ""),
    }


def _extensive_library_doc() -> dict[str, Any]:
    cached = _load(STATE / "field-extensive-library.json", {})
    if cached.get("devices"):
        return cached
    mod = _import_mod("ext_lib", "field-extensive-library.py")
    if mod and hasattr(mod, "build_library"):
        try:
            return mod.build_library(sync=False, render_devices=False)
        except Exception:
            pass
    return cached


def _file_formats_rows() -> list[dict[str, Any]]:
    mod = _import_mod("ff", "field-file-formats.py")
    if not mod or not hasattr(mod, "build_table"):
        return _load(STATE / "field-file-formats-table.json", {}).get("formats") or []
    try:
        return list((mod.build_table() or {}).get("formats") or [])
    except Exception:
        return _load(STATE / "field-file-formats-table.json", {}).get("formats") or []


def collect_entries() -> list[dict[str, Any]]:
    """Gather every registry/catalog entry from all collections."""
    entries: list[dict[str, Any]] = []
    lib = _extensive_library_doc()

    for dev in lib.get("devices") or []:
        entries.append(_entry_device(dev))
    for game in lib.get("games") or []:
        entries.append(_entry_game(game))
    for g in lib.get("programming_greats") or []:
        entries.append(_entry_great(g))

    for book in _k12_textbooks():
        entries.append(_entry_textbook(book))

    for fmt in _file_formats_rows():
        entries.append(_entry_format(fmt))

    entries.append({
        "id": "extensive-library-manifest",
        "title": "Field Extensive Library Manifest",
        "author": "NEXUS-Shield / Hostess7",
        "category": "reference",
        "dewey": "020",
        "format": "h7c",
        "ready": True,
        "source": "field-library-registry",
        "collection": "manifests",
        "description": "Every PC, console, game, format, and textbook — unified Dewey catalog.",
    })
    entries.append({
        "id": "file-formats-registry",
        "title": "Field File Formats Registry",
        "author": "Field File Formats",
        "category": "reference",
        "dewey": "005.7",
        "format": "registry",
        "ready": True,
        "source": "field-library-registry",
        "collection": "file_formats",
        "cover": "/library/assets/formats/h7c.png",
        "description": "Complete format table — H7, H7c, media, geometry, sovereign formats.",
    })
    card_catalog = DEWEY_ROOT / "020-library-science" / "card-catalog" / "catalog.json"
    if card_catalog.is_file():
        cc = _load(card_catalog, {})
        entries.append({
            "id": "field-card-catalog",
            "title": "Field Card Catalog",
            "author": "Hostess7 Librarian Corps",
            "category": "library science",
            "dewey": "020",
            "format": "card-catalog",
            "ready": True,
            "source": "field-card-catalog",
            "collection": "catalogs",
            "description": "Auto-detected books — call numbers, keywords placed, sort & search.",
            "page_count": cc.get("card_count"),
            "ironclad_citation": "ironclad:catalog:1",
        })
    speaking_shelf = DEWEY_ROOT / "400-education"
    speaking_count = len(list(speaking_shelf.glob("exploring_speaking_*/book.json")))
    if speaking_count:
        entries.append({
            "id": "exploring-speaking-shelf",
            "title": "Exploring Speaking — every language ever",
            "author": "AmmoOS Field Library",
            "category": "foreign_language",
            "dewey": "400",
            "format": "h7c",
            "ready": True,
            "source": "field-exploring-speaking",
            "collection": "exploring_speaking",
            "description": (
                f"One book per language — Exploring Speaking X · phonetics, dictionary, "
                f"thesaurus, hieroglyphics · {speaking_count} on shelf (target 7743)."
            ),
            "book_count": speaking_count,
            "ironclad_citation": "ironclad:knowledge:2",
            "truth_gate": "lib/h7-library-truth.py",
            "hostess7_doctrine": "data/hostess7-library-doctrine.json",
        })
    tobin_book = DEWEY_ROOT / "133-parapsychology" / "tobins-spirit-guide" / "book.json"
    if tobin_book.is_file():
        tb = _load(tobin_book, {})
        entries.append({
            "id": "tobins-spirit-guide",
            "title": tb.get("title", "THE PINNACLE Tobin's Spirit Guide"),
            "author": tb.get("author", "Tobin / Hostess 7 Field Corps"),
            "category": "parapsychology",
            "dewey": "133",
            "format": "spirit-guide",
            "ready": True,
            "source": "tobins-spirit-guide",
            "collection": "spirit_guides",
            "cover": tb.get("cover"),
            "description": tb.get("motto", "Elite field manual for demon hunters — Emperor is Bowie."),
            "page_count": tb.get("page_count"),
            "ironclad_citation": tb.get("ironclad_citation", "ironclad:tobin:1"),
        })
    return [_stamp_entry(e) for e in entries]


def sync_registry_shelves(*, pack: bool = False) -> dict[str, Any]:
    """Write textbook + format book.json manifests with cover paths to Dewey shelves."""
    synced = {"textbooks": 0, "formats": 0, "covers": 0}
    covers_mod = _import_mod("tb_covers", "field-textbook-covers.py")
    if covers_mod and hasattr(covers_mod, "sync_textbook_covers"):
        synced["covers"] = covers_mod.sync_textbook_covers()

    for book in _k12_textbooks():
        bid = str(book.get("id") or "")
        if not bid:
            continue
        subject = str(book.get("subject") or "social_studies")
        dewey_main = SUBJECT_DEWEY.get(subject, "370")
        shelf_slug = {
            "004": "004-computers",
            "500": "500-science",
            "510": "510-mathematics",
            "800": "800-literature",
            "900": "900-history",
            "370": "370-education",
        }.get(dewey_main, f"{dewey_main}-education")
        book_dir = DEWEY_ROOT / shelf_slug / bid
        book_dir.mkdir(parents=True, exist_ok=True)
        entry = _entry_textbook(book)
        book_json = {
            "id": bid,
            "title": entry["title"],
            "author": entry.get("author", ""),
            "dewey": entry["dewey"],
            "publisher": book.get("publisher"),
            "license": book.get("license"),
            "grade_band": book.get("grade_band"),
            "subject": subject,
            "format": "textbook",
            "journal": "textbook",
            "cover": entry["cover"],
            "cover_asset": _rel(INSTALL / entry["cover"].lstrip("/")) if entry["cover"].startswith("/library") else entry["cover"],
            "updated": _now(),
        }
        (book_dir / "book.json").write_text(json.dumps(book_json, indent=2) + "\n", encoding="utf-8")
        synced["textbooks"] += 1

    fmt_shelf = DEWEY_ROOT / "005-data" / "file-formats"
    fmt_shelf.mkdir(parents=True, exist_ok=True)
    formats = _file_formats_rows()
    shelf_doc = {
        "schema": "dewey-shelf/v1",
        "shelf": "005-data/file-formats",
        "updated": _now(),
        "format_count": len(formats),
        "registry": "field-file-formats-table.json",
    }
    (fmt_shelf / "shelf.json").write_text(json.dumps(shelf_doc, indent=2) + "\n", encoding="utf-8")
    for fmt in formats[:64]:
        fid = str(fmt.get("id") or "")
        if not fid:
            continue
        entry = _entry_format(fmt)
        fmt_dir = fmt_shelf / fid
        fmt_dir.mkdir(parents=True, exist_ok=True)
        (fmt_dir / "book.json").write_text(json.dumps({
            "id": entry["id"],
            "title": entry["title"],
            "dewey": entry["dewey"],
            "format": "registry-entry",
            "family": fmt.get("family"),
            "extensions": fmt.get("extensions"),
            "magic": fmt.get("magic"),
            "cover": entry["cover"],
            "updated": _now(),
        }, indent=2) + "\n", encoding="utf-8")
        synced["formats"] += 1

    return synced


def build_registry(*, sync_shelves: bool = True, sync_covers: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    bal = _import_mod("reg_bal", "field-combinatronic-balance.py")
    gate: dict[str, Any] = {}
    if bal and hasattr(bal, "combinatoric_entry"):
        gate = bal.combinatoric_entry("library_registry", refresh=sync_shelves)
    shelf_sync: dict[str, Any] = {}
    if sync_shelves:
        shelf_sync = sync_registry_shelves()
    elif sync_covers:
        covers_mod = _import_mod("tb_covers", "field-textbook-covers.py")
        if covers_mod and hasattr(covers_mod, "sync_textbook_covers"):
            shelf_sync = {"covers": covers_mod.sync_textbook_covers()}

    entries = collect_entries()
    api = _import_mod("ironclad_api", "ironclad-secure-api.py")
    sort_meta: dict[str, Any] = {}
    if api and hasattr(api, "sort_index"):
        try:
            entries, sort_meta = api.sort_index(entries, context="registry_index")
        except Exception:
            pass
    collections: dict[str, int] = {}
    for e in entries:
        col = str(e.get("collection") or "other")
        collections[col] = collections.get(col, 0) + 1

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "schema": "field-library-registry/v1",
        "updated": _now(),
        "ok": True,
        "motto": "Single point of informational value — registries, catalogs, textbooks, formats, everything.",
        "counts": {
            "total_entries": len(entries),
            **collections,
        },
        "collections": list(collections.keys()),
        "entries": entries,
        "shelf_sync": shelf_sync,
        "elapsed_ms": elapsed_ms,
        "read_path": "field-library-registry.json",
        "statement": "All modules read registry for catalogs — bridge, formats, extensive library, textbooks",
        "balance_gate": gate or None,
        "combinatronic": True,
        "combinatronic_balance": (
            bal.read_content_balance("field-library-registry", fmt="registry", collection="manifests")
            if bal and hasattr(bal, "read_content_balance")
            else {}
        ),
        "ironclad_sort": sort_meta or None,
        "ironclad_citation": "ironclad:api:1",
    }


def publish_panel(*, refresh: bool = True) -> dict[str, Any]:
    doc = build_registry(sync_shelves=refresh, sync_covers=refresh)
    _save(REGISTRY, doc)
    panel = {
        "schema": "field-library-registry-panel/v1",
        "updated": doc["updated"],
        "ok": doc["ok"],
        "counts": doc["counts"],
        "collections": doc["collections"],
        "shelf_sync": doc.get("shelf_sync"),
        "sample_textbooks": [e for e in doc["entries"] if e.get("collection") == "textbooks"][:6],
        "sample_formats": [e for e in doc["entries"] if e.get("collection") == "file_formats"][:8],
        "elapsed_ms": doc.get("elapsed_ms"),
    }
    _save(PANEL, panel)
    return {"ok": True, "panel": panel, "registry_path": str(REGISTRY)}


def registry_entries() -> list[dict[str, Any]]:
    """Entries for h7-library-bridge and all catalog readers."""
    doc = _load(REGISTRY, {})
    if doc.get("entries"):
        return list(doc["entries"])
    return collect_entries()


def search_registry(query: str, *, limit: int = 48) -> list[dict[str, Any]]:
    q = query.lower().strip()
    if not q:
        entries = registry_entries()
        api = _import_mod("ironclad_api", "ironclad-secure-api.py")
        if api:
            try:
                rows, _ = api.IroncladSecureAPI.instance().sort_index(entries, context="registry_index", n=limit)
                return rows[:limit]
            except Exception:
                pass
        return entries[:limit]
    idx = _import_mod("ironclad_search", "ironclad-search-index.py")
    if idx and hasattr(idx, "search_registry_fast"):
        try:
            return idx.search_registry_fast(q, limit=limit)
        except Exception:
            pass
    entries = registry_entries()
    hits: list[tuple[int, dict[str, Any]]] = []
    for row in entries:
        blob = " ".join(
            str(row.get(k) or "") for k in ("title", "label", "id", "collection", "path", "kind")
        ).lower()
        score = sum(4 if tok in blob else 0 for tok in q.split())
        if score:
            hits.append((score, row))
    hits.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    rows = [h[1] for h in hits[: max(limit, len(hits))]]
    api = _import_mod("ironclad_api", "ironclad-secure-api.py")
    if api and hasattr(api, "sort_index") and rows:
        try:
            rows, _ = api.IroncladSecureAPI.instance().sort_index(rows, context="registry_index", n=limit)
            return rows[:limit]
        except Exception:
            pass
    return rows[:limit]


def catalog_for_h7_bridge() -> list[dict[str, Any]]:
    return registry_entries()


def panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached:
        return cached
    return publish_panel(refresh=False).get("panel") or {}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "status", "json"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish", "sync"):
        print(json.dumps(publish_panel(refresh=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "registry":
        print(json.dumps(build_registry(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "catalog":
        print(json.dumps(catalog_for_h7_bridge(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "search":
        q = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps({"query": q, "hits": search_registry(q)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        pub = publish_panel(refresh=True)
        counts = (pub.get("panel") or {}).get("counts") or {}
        ok = (
            counts.get("textbooks", 0) >= 40
            and counts.get("file_formats", 0) >= 20
            and counts.get("devices", 0) >= 40
        )
        covers_mod = _import_mod("tb", "field-textbook-covers.py")
        if covers_mod and hasattr(covers_mod, "verify"):
            pass
        print(json.dumps({"ok": ok, "counts": counts}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["panel", "build", "registry", "catalog", "search", "verify"],
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())