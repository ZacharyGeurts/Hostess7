#!/usr/bin/env pythong
"""Hostess7 World's Best Librarian — EIN/ISBN bibliography + cover SDF from field drive only."""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
SEED = INSTALL / "data" / "book-bibliography-seed.json"
WAR_SEED = INSTALL / "data" / "war-books-seed.json"

LIBRARIAN = {
    "name": "Hostess7 World's Best Librarian",
    "motto": "Every edition identified — EIN, ISBN, OCLC, Dewey, covers on field drive.",
    "policy": "field_drive_only",
}


def _corps_mod() -> Any | None:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "nexus_librarian_corps",
            INSTALL / "lib" / "nexus-librarian-corps.py",
        )
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def librarian_corps_learn(event: str, **kwargs: Any) -> None:
    corps = _corps_mod()
    if corps:
        try:
            corps.learn(event, **kwargs)
        except Exception:
            pass


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _field_roots() -> list[Path]:
    roots: list[Path] = []
    for p in (HOSTESS7_TEAM_FIELD, HOSTESS7_ROOT / "cache" / "fieldstorage"):
        if p.is_dir() and p not in roots:
            roots.append(p)
    return roots or [HOSTESS7_TEAM_FIELD]


def _brain_score(root: Path) -> int:
    score = 0
    if (root / "brain").is_dir():
        score += 5
    if (root / "brain/library/manifest.json").is_file():
        score += 80
    if (root / "brain/superintel").is_dir():
        score += 50
    return score


def _primary_root() -> Path:
    best: Path | None = None
    best_score = -1
    for r in _field_roots():
        s = _brain_score(r)
        if s > best_score:
            best_score = s
            best = r
    return best or _field_roots()[0]


def library_meta_dir() -> Path:
    return _primary_root() / "brain" / "library"


def covers_dir() -> Path:
    return library_meta_dir() / "covers"


def bibliography_path() -> Path:
    return library_meta_dir() / "bibliography.jsonl"


def librarian_status_path() -> Path:
    return library_meta_dir() / "librarian.json"


def fingerprint_path() -> Path:
    return library_meta_dir() / "field_fingerprint.json"


def catalog_snapshot_path() -> Path:
    return library_meta_dir() / "catalog_snapshot.json"


def _safe_id(book_id: str) -> str:
    return re.sub(r"[^\w.-]", "_", book_id)


def _normalize_isbn(raw: str) -> str:
    return re.sub(r"[^0-9Xx]", "", raw)


def _isbn13_check(digits: str) -> bool:
    if len(digits) != 13 or not digits.isdigit():
        return False
    total = sum(int(d) * (1 if i % 2 else 3) for i, d in enumerate(digits[:12]))
    check = (10 - (total % 10)) % 10
    return check == int(digits[12])


def make_ein(
    *,
    book_id: str,
    isbn_13: str = "",
    isbn_10: str = "",
    gutenberg_id: str = "",
    source: str = "",
) -> str:
    if isbn_13:
        return f"H7-ISBN-{_normalize_isbn(isbn_13)}"
    if isbn_10:
        return f"H7-ISBN10-{_normalize_isbn(isbn_10)}"
    if gutenberg_id:
        return f"H7-GUT-{gutenberg_id}"
    src = (source or "field")[:8].upper()
    digest = hashlib.sha256(book_id.encode()).hexdigest()[:12]
    return f"H7-{src}-{digest}"


def _load_seed_doc(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return {str(r["id"]): r for r in doc.get("books", []) if r.get("id")}
    except (OSError, json.JSONDecodeError):
        return {}


def _load_seed() -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for path in (SEED, WAR_SEED, INSTALL / "data" / "book-bibliography-seed.json", INSTALL / "data" / "war-books-seed.json"):
        for bid, row in _load_seed_doc(path).items():
            merged.setdefault(bid, {}).update(row)
    return merged


def _load_war_seed_doc() -> dict[str, Any]:
    for path in (WAR_SEED, INSTALL / "data" / "war-books-seed.json"):
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return {"books": [], "ascertain_keywords": []}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _resolve_path(path: str) -> str:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("h7_field_drive_tie", INSTALL / "lib" / "h7-field-drive-tie.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            resolved = mod.resolve_field_path(path)
            if resolved:
                return str(resolved)
    except Exception:
        pass
    return path


def _scan_field_meta() -> dict[str, dict[str, Any]]:
    """Harvest bibliographic hints already on field drive — no network."""
    by_id: dict[str, dict[str, Any]] = {}

    for root in _field_roots():
        lib = root / "brain" / "library"
        for name in ("search_index.jsonl", "bibliography.jsonl"):
            for row in _read_jsonl(lib / name):
                bid = str(row.get("id", ""))
                if bid:
                    by_id.setdefault(bid, {}).update(row)

        manifest = lib / "manifest.json"
        if manifest.is_file():
            try:
                doc = json.loads(manifest.read_text(encoding="utf-8"))
                for row in doc.get("books") or []:
                    bid = str(row.get("id", ""))
                    if bid:
                        merged = dict(row)
                        raw = str(row.get("path") or row.get("h7_path") or "")
                        if raw:
                            merged["path"] = _resolve_path(raw)
                        by_id.setdefault(bid, {}).update(merged)
            except (OSError, json.JSONDecodeError):
                pass

        k12_shard = root / "brain" / "k12" / "infinite" / "shards"
        if k12_shard.is_dir():
            for shard in sorted(k12_shard.glob("*.jsonl"))[:6]:
                for row in _read_jsonl(shard):
                    bid = str(row.get("id", ""))
                    if bid:
                        by_id.setdefault(bid, {}).update({
                            "id": bid,
                            "title": row.get("title", ""),
                            "author": row.get("author", ""),
                            "publisher": row.get("publisher", ""),
                            "subject": row.get("subject", ""),
                            "grade_band": row.get("grade_band", ""),
                            "license": row.get("license", ""),
                        })

        for meta in (root / "textbooks").glob("*.meta.json"):
            try:
                row = json.loads(meta.read_text(encoding="utf-8"))
                bid = str(row.get("id", meta.stem.replace(".meta", "")))
                by_id.setdefault(bid, {}).update(row)
            except (OSError, json.JSONDecodeError):
                continue

        for h7 in root.glob("textbooks/**/*.h7"):
            bid = h7.stem
            by_id.setdefault(bid, {"id": bid, "path": str(h7)})

    return by_id


def _gutenberg_id_from_book_id(book_id: str) -> str:
    m = re.search(r"gutenberg_(\w+)", book_id)
    if not m:
        return ""
    name = m.group(1)
    known = {
        "pride_prejudice": "1342",
        "frankenstein": "84",
        "wizard_oz": "55",
        "tom_sawyer": "74",
        "alice": "11",
        "art_of_war": "132",
        "on_war": "20586",
        "jomini_art_of_war": "28235",
        "caesar_gallic_war": "10657",
        "herodotus_histories": "2707",
        "grant_memoirs": "4367",
        "red_badge_courage": "73",
        "mahan_sea_power": "35899",
        "story_of_siegfried": "54969",
        "war_peace_tolstoy": "2600",
        "all_quiet": "345",
        "treaty_versailles": "15776",
        "bible_kjv": "10",
        "einstein_relativity": "30114",
        "flatland": "201",
        "wind_willows": "289",
        "faraday_candle": "67064",
        "elementary_chemistry": "28595",
    }
    return known.get(name, "")


def enrich_record(book_id: str, base: dict[str, Any] | None = None) -> dict[str, Any]:
    seed = _load_seed().get(book_id, {})
    field = (base or {}).copy()
    row: dict[str, Any] = {
        "id": book_id,
        "title": seed.get("title") or field.get("title", book_id),
        "author": seed.get("author") or field.get("author", ""),
        "publisher": seed.get("publisher") or field.get("publisher", ""),
        "published_year": seed.get("published_year") or field.get("published_year", ""),
        "language": seed.get("language", "en"),
        "license": seed.get("license") or field.get("license", ""),
        "dewey": seed.get("dewey") or field.get("dewey", ""),
        "lc_class": seed.get("lc_class", ""),
        "subject": seed.get("subject") or field.get("subject", field.get("category", "")),
        "isbn_10": seed.get("isbn_10", ""),
        "isbn_13": seed.get("isbn_13", ""),
        "oclc": seed.get("oclc", ""),
        "lccn": seed.get("lccn", ""),
        "gutenberg_id": seed.get("gutenberg_id") or _gutenberg_id_from_book_id(book_id),
        "openstax_slug": seed.get("openstax_slug", ""),
        "pages": seed.get("pages") or field.get("page_count", ""),
        "source": "field_drive",
    }
    row["ein"] = make_ein(
        book_id=book_id,
        isbn_13=str(row.get("isbn_13", "")),
        isbn_10=str(row.get("isbn_10", "")),
        gutenberg_id=str(row.get("gutenberg_id", "")),
        source=str(seed.get("source", "field")),
    )
    if row.get("isbn_13") and not _isbn13_check(_normalize_isbn(str(row["isbn_13"]))):
        row["isbn_13_valid"] = False
    else:
        row["isbn_13_valid"] = bool(row.get("isbn_13"))
    row["covers"] = cover_assets(book_id)
    return row


def cover_paths(book_id: str) -> dict[str, Path | None]:
    safe = _safe_id(book_id)
    roots = [covers_dir()]
    lib_assets = INSTALL / "library" / "assets" / "covers" / safe
    if lib_assets.is_dir():
        roots.insert(0, lib_assets)
    for r in _field_roots():
        roots.append(r / "brain" / "library" / "covers" / safe)
    out: dict[str, Path | None] = {"front": None, "back": None}
    for side in ("front", "back"):
        for base in roots:
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                p = base / f"{side}{ext}" if base.name == safe else base / safe / f"{side}{ext}"
                if p.is_file():
                    out[side] = p
                    break
            if out[side]:
                break
    return out


def cover_assets(book_id: str) -> dict[str, Any]:
    paths = cover_paths(book_id)
    safe = _safe_id(book_id)
    assets: dict[str, Any] = {}
    for side, src in paths.items():
        if not src:
            continue
        sdf_png = src.parent / f"{side}.sdf.png"
        sdf_json = src.parent / f"{side}.sdf.json"
        assets[side] = {
            "source": str(src),
            "sdf_png": str(sdf_png) if sdf_png.is_file() else "",
            "sdf_json": str(sdf_json) if sdf_json.is_file() else "",
            "url": f"/api/library/cover?book={book_id}&side={side}",
            "sdf_url": f"/api/library/cover?book={book_id}&side={side}&format=sdf",
        }
    return assets


def load_bibliography_index() -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(bibliography_path()):
        bid = str(row.get("id", ""))
        if bid:
            index[bid] = row
    seed = _load_seed()
    field = _scan_field_meta()
    all_ids = set(seed) | set(field)
    for bid in sorted(all_ids):
        if bid not in index:
            index[bid] = enrich_record(bid, field.get(bid))
        else:
            merged = enrich_record(bid, {**field.get(bid, {}), **index[bid]})
            index[bid] = merged
    return index


def merge_into_book(book: dict[str, Any]) -> dict[str, Any]:
    bid = str(book.get("id", ""))
    if not bid:
        return book
    bib = load_bibliography_index().get(bid) or enrich_record(bid, book)
    out = {**book}
    for key in (
        "ein", "isbn_10", "isbn_13", "isbn_13_valid", "oclc", "lccn",
        "gutenberg_id", "openstax_slug", "publisher", "published_year",
        "language", "lc_class", "pages", "covers", "cover", "dewey", "dewey_label",
        "subject", "study_note", "grade_band", "license", "collection",
    ):
        if bib.get(key):
            out[key] = bib[key]
    if bib.get("ein"):
        out["ein"] = bib["ein"]
    return out


def _war_match_blob(row: dict[str, Any]) -> str:
    return " ".join(
        str(row.get(k, "")) for k in (
            "id", "title", "author", "subject", "category", "description", "dewey",
        )
    ).lower()


def ascertain_war_books(*, write: bool = True) -> dict[str, Any]:
    """Study field-drive books for war content — merge war seed + on-disk matches."""
    war_doc = _load_war_seed_doc()
    keywords = [k.lower() for k in war_doc.get("ascertain_keywords") or [] if k]
    seed_ids = {str(r["id"]) for r in war_doc.get("books") or [] if r.get("id")}
    index = load_bibliography_index()
    matched: list[dict[str, Any]] = []
    studied: list[dict[str, Any]] = []

    for bid, row in index.items():
        blob = _war_match_blob(row)
        is_seed = bid in seed_ids
        kw_hits = [k for k in keywords if k in blob]
        dewey = str(row.get("dewey", ""))
        is_war_dewey = dewey.startswith("355") or dewey.startswith("940") or dewey.startswith("973.7")
        if is_seed or kw_hits or is_war_dewey:
            seed_row = _load_seed().get(bid, {})
            study = {
                "id": bid,
                "title": row.get("title", bid),
                "author": row.get("author", ""),
                "dewey": seed_row.get("dewey") or row.get("dewey", ""),
                "keyword_hits": kw_hits,
                "on_field_drive": bool(row.get("path") or row.get("covers")),
                "study_note": seed_row.get("study_note", ""),
                "ascertained": _now(),
            }
            studied.append(study)
            matched.append(enrich_record(bid, {**row, **seed_row}))

    study_path = library_meta_dir() / "war_study.jsonl"
    if write and studied:
        try:
            study_path.parent.mkdir(parents=True, exist_ok=True)
            lines = [json.dumps(s, ensure_ascii=False) for s in studied]
            study_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        except OSError:
            pass

    return {
        "ok": True,
        "war_book_count": len(studied),
        "seed_count": len(seed_ids),
        "on_drive": sum(1 for s in studied if s.get("on_field_drive")),
        "study_path": str(study_path),
        "books": matched,
        "studied": studied,
    }


def librarian_status() -> dict[str, Any]:
    index = load_bibliography_index()
    with_covers = sum(1 for r in index.values() if r.get("covers"))
    with_isbn = sum(1 for r in index.values() if r.get("isbn_13") or r.get("isbn_10"))
    corps_doc: dict[str, Any] = {}
    corps = _corps_mod()
    if corps:
        try:
            corps_doc = corps.corps_status()
        except Exception:
            corps_doc = {}
    return {
        **LIBRARIAN,
        "updated": _now(),
        "field_root": str(_primary_root()),
        "bibliography_count": len(index),
        "isbn_count": with_isbn,
        "cover_count": with_covers,
        "bibliography_path": str(bibliography_path()),
        "covers_dir": str(covers_dir()),
        "policy": "field_drive_only — never fetch",
        "fingerprint_method": "micro_sig_v1",
        "field_fingerprint": compute_field_fingerprint(),
        "field_unchanged": field_unchanged(),
        "last_touched": load_fingerprint_doc().get("last_touched", ""),
        "last_touched_same": last_touched_unchanged(),
        "corps": corps_doc,
        "corps_count": corps_doc.get("count", 0),
    }


def _micro_sig(path: Path) -> str:
    """Type-aware micro-signature — only a few bytes read per file."""
    try:
        size = path.stat().st_size
    except OSError:
        return "err:0:"
    name = path.name.lower()
    ext = path.suffix.lower()
    sig_path = path
    if ext == ".h7" or name.endswith(".h7"):
        try:
            dewey_py = INSTALL / "lib" / "field-dewey-library.py"
            if dewey_py.is_file():
                import importlib.util
                spec = importlib.util.spec_from_file_location("field_dewey_lib", dewey_py)
                if spec and spec.loader:
                    dmod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(dmod)
                    if hasattr(dmod, "ensure_h7c_path"):
                        sig_path = dmod.ensure_h7c_path(path)
                        ext = sig_path.suffix.lower()
        except Exception:
            pass
    try:
        with sig_path.open("rb") as fh:
            if ext == ".h7c" or name.endswith(".h7c"):
                blob = fh.read(12)
                return f"h7c:{size}:{blob.hex()}"
            if ext == ".h7" or name.endswith(".h7"):
                blob = fh.read(12)
                return f"h7:{size}:{blob.hex()}"
            if ext == ".png" or name.endswith(".sdf.png"):
                head = fh.read(8)
                if size > 8:
                    fh.seek(size - 8)
                    tail = fh.read(8)
                else:
                    tail = b""
                return f"png:{size}:{head.hex()}{tail.hex()}"
            if ext in (".jpg", ".jpeg", ".webp"):
                head = fh.read(4)
                if size > 6:
                    fh.seek(size - 2)
                    tail = fh.read(2)
                else:
                    tail = b""
                return f"img:{size}:{head.hex()}{tail.hex()}"
            if ext in (".json", ".jsonl") or name.endswith(".meta.json"):
                blob = fh.read(24)
                return f"json:{size}:{blob.hex()}"
            if ext == ".txt":
                blob = fh.read(32)
                return f"txt:{size}:{blob.hex()}"
            blob = fh.read(8)
            return f"bin:{size}:{blob.hex()}"
    except OSError:
        return f"err:{size}:"


_DERIVED_NAMES = frozenset({
    "field_fingerprint.json",
    "catalog_snapshot.json",
    "librarian.json",
    "bibliography.jsonl",
    "dewey_index.json",
    "shelf_index.json",
    "manifest.json",
    "search_index.jsonl",
    "build.jsonl",
})


def _is_source_library_file(path: Path) -> bool:
    name = path.name.lower()
    if name in _DERIVED_NAMES:
        return False
    if name.endswith(".sdf.png") or name.endswith(".sdf.json"):
        return False
    return True


def _library_paths() -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    for root in _field_roots():
        for pattern in (
            "textbooks/**/*.h7c",
            "textbooks/**/*.h7",
            "textbooks/**/*.txt",
            "textbooks/**/*.meta.json",
            "brain/library/covers/**/front.png",
            "brain/library/covers/**/back.png",
            "brain/library/covers/**/front.jpg",
            "brain/library/covers/**/back.jpg",
            "brain/library/covers/**/front.jpeg",
            "brain/library/covers/**/back.jpeg",
        ):
            for path in sorted(root.glob(pattern)):
                if not _is_source_library_file(path):
                    continue
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                paths.append(path)
    seed = SEED if SEED.is_file() else INSTALL / "data" / "book-bibliography-seed.json"
    if seed.is_file():
        paths.append(seed)
    return sorted(paths, key=lambda p: str(p))


def _inventory_entries() -> list[str]:
    """Compact inventory — relative path + micro-sig (few bytes per file)."""
    root = _primary_root()
    lines: list[str] = []
    for path in _library_paths():
        try:
            rel = path.resolve().relative_to(root.resolve())
        except ValueError:
            rel = path.name
        lines.append(f"{rel}|{_micro_sig(path)}")
    return lines


def micro_sig_for_book(book_id: str) -> str:
    safe = _safe_id(book_id)
    for root in _field_roots():
        for path in (
            root.glob(f"textbooks/**/{safe}.h7c"),
            root.glob(f"textbooks/{safe}.h7c"),
            root.glob(f"textbooks/**/{book_id}.h7c"),
            root.glob(f"textbooks/{book_id}.h7c"),
            root.glob(f"textbooks/**/{safe}.h7"),
            root.glob(f"textbooks/{safe}.h7"),
            root.glob(f"textbooks/**/{book_id}.h7"),
            root.glob(f"textbooks/{book_id}.h7"),
        ):
            for hit in path:
                if hit.is_file():
                    return _micro_sig(hit)
        txt = root / "textbooks" / f"{book_id}.txt"
        if txt.is_file():
            return _micro_sig(txt)
    return ""


def compute_field_fingerprint() -> str:
    import hashlib
    h = hashlib.sha256()
    for line in _inventory_entries():
        h.update(line.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()[:24]


def load_fingerprint_doc() -> dict[str, Any]:
    path = fingerprint_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def field_unchanged() -> bool:
    doc = load_fingerprint_doc()
    return bool(doc.get("fingerprint")) and doc.get("fingerprint") == compute_field_fingerprint()


def touch_book(book_id: str, *, dewey: str = "", title: str = "") -> None:
    """Record last book touched + its micro-sig (few bytes)."""
    librarian_corps_learn("classify", book_id=book_id, dewey=dewey, title=title)
    doc = load_fingerprint_doc()
    doc["last_touched"] = book_id
    doc["last_touched_at"] = _now()
    doc["last_touched_sig"] = micro_sig_for_book(book_id)
    fp = fingerprint_path()
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def last_touched_unchanged() -> bool:
    doc = load_fingerprint_doc()
    bid = str(doc.get("last_touched", ""))
    if not bid:
        return True
    prev = str(doc.get("last_touched_sig", ""))
    if not prev:
        return False
    return prev == micro_sig_for_book(bid)


def save_fingerprint(*, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    prev = load_fingerprint_doc()
    fp = compute_field_fingerprint()
    doc = {
        "fingerprint": fp,
        "fingerprint_method": "micro_sig_v1",
        "updated": _now(),
        "file_count": len(_inventory_entries()),
        "last_touched": prev.get("last_touched", ""),
        "last_touched_at": prev.get("last_touched_at", ""),
        "last_touched_sig": prev.get("last_touched_sig", ""),
        "last_touched_same": last_touched_unchanged(),
    }
    fingerprint_path().parent.mkdir(parents=True, exist_ok=True)
    fingerprint_path().write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    if catalog:
        catalog_snapshot_path().write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return doc


def load_catalog_snapshot() -> dict[str, Any] | None:
    path = catalog_snapshot_path()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def sync_covers_for_touched(bib: dict[str, dict[str, Any]], *, force_all: bool = False) -> int:
    """Build cover SDF — textbooks get publisher covers; others on last-touched."""
    import importlib.util
    tb_spec = importlib.util.spec_from_file_location(
        "field_textbook_covers", INSTALL / "lib" / "field-textbook-covers.py"
    )
    if tb_spec and tb_spec.loader:
        try:
            tb_mod = importlib.util.module_from_spec(tb_spec)
            tb_spec.loader.exec_module(tb_mod)
            if hasattr(tb_mod, "sync_textbook_covers"):
                tb_mod.sync_textbook_covers()
        except Exception:
            pass
    if not force_all and last_touched_unchanged():
        return 0
    import importlib.util
    spec = importlib.util.spec_from_file_location("sdf_book_covers", INSTALL / "lib" / "sdf-book-covers.py")
    if not spec or not spec.loader:
        return 0
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    touched = str(load_fingerprint_doc().get("last_touched", ""))
    ids = list(bib.keys()) if force_all else ([touched] if touched and touched in bib else [])
    if not ids and bib and force_all:
        ids = list(bib.keys())[:12]
    built = 0
    for bid in ids:
        row = bib.get(bid, {})
        if mod.build_cover_sdf(bid, "front", title=str(row.get("title", bid)), author=str(row.get("author", ""))):
            built += 1
    return built


def build_bibliography_field(*, write: bool = True) -> dict[str, Any]:
    """Write bibliography.jsonl to field drive from seed + on-disk meta."""
    index = load_bibliography_index()
    lib_dir = library_meta_dir()
    lib_dir.mkdir(parents=True, exist_ok=True)
    covers_dir().mkdir(parents=True, exist_ok=True)
    if write:
        lines = [json.dumps(index[bid], ensure_ascii=False) for bid in sorted(index)]
        blob = "\n".join(lines) + ("\n" if lines else "")
        bib_path = bibliography_path()
        old_sig = _micro_sig(bib_path) if bib_path.is_file() else ""
        new_head = blob[:24].encode("utf-8")
        new_sig = f"json:{len(blob)}:{new_head.hex()}"
        if old_sig != new_sig:
            bib_path.write_text(blob, encoding="utf-8")
        lib_path = librarian_status_path()
        status_blob = json.dumps(librarian_status(), indent=2) + "\n"
        if _micro_sig(lib_path) != f"json:{len(status_blob)}:{status_blob[:24].encode('utf-8').hex()}":
            lib_path.write_text(status_blob, encoding="utf-8")
    built_covers = 0
    if write:
        built_covers = sync_covers_for_touched(index)
    librarian_corps_learn("catalog_build", detail=f"bibliography_count={len(index)}")
    return {
        "ok": True,
        "count": len(index),
        "covers_built": built_covers,
        "path": str(bibliography_path()),
        "librarian": librarian_status(),
    }


def get_cover_bytes(book_id: str, side: str = "front", *, fmt: str = "png") -> tuple[bytes, str] | None:
    paths = cover_paths(book_id)
    src = paths.get(side)
    if not src:
        return None
    if fmt == "sdf":
        sdf = src.parent / f"{side}.sdf.png"
        if sdf.is_file():
            return sdf.read_bytes(), "image/png"
        return None
    ext = src.suffix.lower()
    ctype = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(ext, "application/octet-stream")
    return src.read_bytes(), ctype


def search_dewey_index(query: str, *, limit: int = 24, **filters: Any) -> list[dict[str, Any]]:
    """Search Dewey index librarian — tags, facets, keywords."""
    idx = None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("dewey_idx", INSTALL / "lib" / "field-dewey-index.py")
        if spec and spec.loader:
            idx = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(idx)
    except Exception:
        pass
    if idx and hasattr(idx, "search_index"):
        try:
            rep = idx.search_index(query, limit=limit, **filters)
            return rep.get("hits") or []
        except Exception:
            pass
    return []


def search_bibliography(query: str, *, limit: int = 24) -> list[dict[str, Any]]:
    toks = [t for t in re.split(r"\W+", query.lower()) if len(t) > 1]
    if not toks:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    for row in load_bibliography_index().values():
        blob = " ".join(
            str(row.get(k, "")) for k in (
                "title", "author", "ein", "isbn_10", "isbn_13", "oclc",
                "publisher", "dewey", "lc_class", "gutenberg_id",
            )
        ).lower()
        score = sum(
            (14 if t in str(row.get("ein", "")).lower() else 0)
            + (12 if t in str(row.get("isbn_13", "")).lower() else 0)
            + (10 if t in str(row.get("title", "")).lower() else 0)
            + (6 if t in blob else 0)
            for t in toks
        )
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    bib_hits = [{**r, "score": s, "source": "bibliography"} for s, r in scored[:limit]]
    dewey_hits = search_dewey_index(query, limit=limit)
    if not dewey_hits:
        return bib_hits
    seen = {str(h.get("id") or "") for h in bib_hits}
    merged = list(bib_hits)
    for row in dewey_hits:
        bid = str(row.get("id") or "")
        if bid and bid not in seen:
            seen.add(bid)
            merged.append({**row, "source": "dewey_index"})
    merged.sort(key=lambda x: (-int(x.get("score") or 0), str(x.get("title", ""))))
    return merged[:limit]


def main() -> int:
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "build":
        print(json.dumps(build_bibliography_field(), indent=2))
        return 0
    if cmd == "status":
        print(json.dumps(librarian_status(), indent=2))
        return 0
    if cmd == "search" and len(sys.argv) >= 3:
        q = " ".join(sys.argv[2:])
        print(json.dumps({"ok": True, "hits": search_bibliography(q)}, indent=2))
        return 0
    if cmd == "get" and len(sys.argv) >= 3:
        bid = sys.argv[2]
        idx = load_bibliography_index()
        print(json.dumps(idx.get(bid) or enrich_record(bid), indent=2))
        return 0
    if cmd == "war":
        print(json.dumps(ascertain_war_books(), indent=2))
        return 0
    print("usage: h7-library-librarian.py [status|build|search <q>|get <id>|war]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())