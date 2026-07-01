#!/usr/bin/env pythong
"""Dewey library tree — glob bookshelves, H7→H7c migration, display every book ever."""
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
DOCTRINE = INSTALL / "data" / "field-dewey-library-doctrine.json"
DEWEY_ROOT = INSTALL / "library" / "dewey"
DEWEY_TREE = INSTALL / "data" / "dewey-full-tree.json"
PANEL = STATE / "field-dewey-library-panel.json"
TREE_JSON = STATE / "field-dewey-library-tree.json"


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
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _h7_mod() -> Any | None:
    path = INSTALL / "Hostess7" / "scripts" / "field_h7_book.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_h7_book", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _h7c_mod() -> Any | None:
    return _import_mod("field_h7c", "field-h7c-compression.py")


def _auto_convert_on_open() -> bool:
    doctrine = _load(DOCTRINE, {})
    mig = doctrine.get("migration") or {}
    if os.environ.get("FIELD_H7_AUTO_CONVERT", "1").strip().lower() in ("0", "false", "no"):
        return False
    return bool(mig.get("auto_convert_on_open", True))


def _maybe_rebalance_h7c(p: Path) -> None:
    h7c_mod = _h7c_mod()
    if h7c_mod and hasattr(h7c_mod, "maybe_rebalance_on_open"):
        try:
            h7c_mod.maybe_rebalance_on_open(p)
        except Exception:
            pass


def ensure_h7c_path(path: Path, *, remove_h7: bool = True) -> Path:
    """If path is legacy H7, convert to H7c in-place immediately; return H7c path."""
    p = Path(path)
    if p.suffix.lower() == ".h7c" and p.is_file():
        _maybe_rebalance_h7c(p)
        return p
    sibling = p.with_suffix(".h7c")
    if sibling.is_file() and p.suffix.lower() == ".h7" and p.is_file() and remove_h7:
        try:
            p.unlink()
        except OSError:
            pass
        return sibling
    if p.suffix.lower() == ".h7" and p.is_file() and _auto_convert_on_open():
        result = convert_h7_file(p, remove_h7=remove_h7)
        if result.get("ok") and result.get("h7c"):
            out = Path(result["h7c"])
            _maybe_rebalance_h7c(out)
            return out
    if sibling.is_file():
        _maybe_rebalance_h7c(sibling)
        return sibling
    return p


def ensure_h7c_for_book(book_id: str) -> Path | None:
    """Resolve H7c for a book — convert legacy H7 on sight if needed."""
    hit = find_h7c(book_id, auto_convert=False)
    if hit:
        return hit
    h7 = find_h7(book_id)
    if h7 and _auto_convert_on_open():
        return ensure_h7c_path(h7)
    return find_h7c(book_id, auto_convert=False)


def _ironclad_h7_access() -> Any | None:
    return _import_mod("ironclad_h7_access", "ironclad-h7-access.py")


def find_h7c(book_id: str, *, auto_convert: bool = True) -> Path | None:
    """Locate H7c for a book anywhere under library/dewey."""
    cid = str(book_id or "").strip()
    if not cid or not DEWEY_ROOT.is_dir():
        return None
    iron = _ironclad_h7_access()
    if iron and hasattr(iron, "resolve_h7c_path"):
        try:
            hit = iron.resolve_h7c_path(cid)
            if hit and hit.is_file():
                return hit
        except Exception:
            pass
    for hit in sorted(DEWEY_ROOT.rglob(f"{cid}.h7c")):
        if hit.is_file():
            return hit
    if auto_convert and _auto_convert_on_open():
        h7 = find_h7(cid)
        if h7:
            h7c = ensure_h7c_path(h7)
            if h7c.suffix.lower() == ".h7c" and h7c.is_file():
                return h7c
    return None


def find_h7(book_id: str) -> Path | None:
    cid = str(book_id or "").strip()
    if not cid or not DEWEY_ROOT.is_dir():
        return None
    for hit in sorted(DEWEY_ROOT.rglob(f"{cid}.h7")):
        if hit.is_file():
            return hit
    return None


def glob_h7c_files() -> list[Path]:
    if not DEWEY_ROOT.is_dir():
        return []
    return sorted(DEWEY_ROOT.rglob("*.h7c"))


def glob_h7_files() -> list[Path]:
    if not DEWEY_ROOT.is_dir():
        return []
    return sorted(DEWEY_ROOT.rglob("*.h7"))


def _shelf_slug(path: Path) -> str:
    try:
        return str(path.relative_to(DEWEY_ROOT)).replace("\\", "/")
    except ValueError:
        return path.name


def _book_id_from_path(path: Path) -> str:
    return path.stem


def _read_book_json(book_dir: Path) -> dict[str, Any]:
    p = book_dir / "book.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_book_json(book_dir: Path, doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    doc.setdefault("format", "h7c")
    (book_dir / "book.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def glob_shelves() -> list[dict[str, Any]]:
    """Discover Dewey shelves by glob — every directory with books or shelf.json."""
    if not DEWEY_ROOT.is_dir():
        return []
    shelves: dict[str, dict[str, Any]] = {}
    tree = _load(DEWEY_TREE, {})
    class_titles = {str(c.get("code")): c for c in (tree.get("classes") or [])}
    slug_titles = {str(c.get("slug")): c for c in (tree.get("classes") or [])}

    for book_json in sorted(DEWEY_ROOT.rglob("book.json")):
        shelf_dir = book_json.parent.parent
        slug = _shelf_slug(shelf_dir)
        shelves.setdefault(slug, {
            "slug": slug,
            "path": _rel(shelf_dir),
            "book_count": 0,
            "h7c_count": 0,
            "books": [],
        })
        row = _read_book_json(book_json.parent)
        bid = str(row.get("id") or book_json.parent.name)
        h7c = book_json.parent / f"{bid}.h7c"
        entry = {
            "id": bid,
            "title": row.get("title", bid),
            "author": row.get("author", ""),
            "dewey": row.get("dewey", ""),
            "format": row.get("format", "h7c" if h7c.is_file() else "catalog"),
            "cover": row.get("cover"),
            "path": _rel(book_json.parent),
            "h7c": _rel(h7c) if h7c.is_file() else None,
            "ready": h7c.is_file(),
        }
        shelves[slug]["books"].append(entry)
        shelves[slug]["book_count"] += 1
        if h7c.is_file():
            shelves[slug]["h7c_count"] += 1

    for h7c in glob_h7c_files():
        book_dir = h7c.parent
        shelf_dir = book_dir.parent
        slug = _shelf_slug(shelf_dir)
        bid = _book_id_from_path(h7c)
        shelves.setdefault(slug, {
            "slug": slug,
            "path": _rel(shelf_dir),
            "book_count": 0,
            "h7c_count": 0,
            "books": [],
        })
        if any(b.get("id") == bid for b in shelves[slug]["books"]):
            continue
        entry = {
            "id": bid,
            "title": bid.replace("_", " ").title(),
            "format": "h7c",
            "path": _rel(book_dir),
            "h7c": _rel(h7c),
            "ready": True,
        }
        shelves[slug]["books"].append(entry)
        shelves[slug]["book_count"] += 1
        shelves[slug]["h7c_count"] += 1

    for shelf_json in sorted(DEWEY_ROOT.rglob("shelf.json")):
        slug = _shelf_slug(shelf_json.parent)
        if slug in shelves:
            shelves[slug]["shelf_json"] = _rel(shelf_json)
            continue
        try:
            doc = json.loads(shelf_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            doc = {}
        shelves[slug] = {
            "slug": slug,
            "path": _rel(shelf_json.parent),
            "shelf_json": _rel(shelf_json),
            "book_count": int(doc.get("book_count") or doc.get("count") or 0),
            "h7c_count": 0,
            "books": list(doc.get("books") or []),
            "title": doc.get("title") or doc.get("shelf"),
        }

    out: list[dict[str, Any]] = []
    for slug, row in sorted(shelves.items()):
        main_code = slug.split("-")[0] if "-" in slug else slug[:3]
        cls = class_titles.get(main_code) or slug_titles.get(slug) or {}
        row["code"] = cls.get("code", main_code)
        row["title"] = row.get("title") or cls.get("title", slug)
        row["books"] = sorted(row.get("books") or [], key=lambda b: str(b.get("title", b.get("id", ""))))
        out.append(row)
    return out


def glob_books() -> list[dict[str, Any]]:
    """All books discovered by glob — primary catalog source."""
    books: list[dict[str, Any]] = []
    seen: set[str] = set()
    for shelf in glob_shelves():
        for book in shelf.get("books") or []:
            bid = str(book.get("id") or "")
            if not bid or bid in seen:
                continue
            seen.add(bid)
            books.append({
                **book,
                "shelf": shelf.get("slug"),
                "shelf_title": shelf.get("title"),
                "source": "field-dewey-library",
                "ready": bool(book.get("h7c") or book.get("ready")),
                "format": book.get("format") or ("h7c" if book.get("h7c") else "catalog"),
            })
    return books


def build_dewey_tree(*, include_empty_shelves: bool = True) -> dict[str, Any]:
    """Whole Dewey library tree — every shelf, every book; room for every book ever."""
    t0 = time.perf_counter()
    tree_doc = _load(DEWEY_TREE, {})
    shelves = glob_shelves()
    books = glob_books()
    h7_remaining = len(glob_h7_files())
    h7c_total = len(glob_h7c_files())

    empty_shelves: list[dict[str, Any]] = []
    if include_empty_shelves:
        populated = {s.get("slug") for s in shelves}

        def _reserve(slug: str, code: Any, title: Any) -> None:
            if not slug or slug in populated:
                return
            populated.add(slug)
            empty_shelves.append({
                "slug": slug,
                "code": code,
                "title": title,
                "path": f"library/dewey/{slug}",
                "book_count": 0,
                "h7c_count": 0,
                "books": [],
                "reserved": True,
            })

        for cls in tree_doc.get("classes") or []:
            _reserve(str(cls.get("slug") or ""), cls.get("code"), cls.get("title"))
        for subdiv in (tree_doc.get("subdivisions") or {}).values():
            _reserve(str(subdiv.get("slug") or ""), subdiv.get("code"), subdiv.get("title"))
        for ws in tree_doc.get("war_shelves") or []:
            code = str(ws.get("code") or "")
            slug = f"{code.replace('.', '-')}-war" if code else ""
            _reserve(slug, code, ws.get("title"))

    all_shelves = sorted([*shelves, *empty_shelves], key=lambda s: str(s.get("code", s.get("slug", ""))))
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "schema": "field-dewey-library-tree/v1",
        "updated": _now(),
        "ok": True,
        "motto": "Every book ever — glob Dewey bookshelves, Hostess 7 Condenser (H7c) at no cost.",
        "root": str(DEWEY_ROOT.relative_to(INSTALL)) if DEWEY_ROOT.is_relative_to(INSTALL) else str(DEWEY_ROOT),
        "format_primary": "h7c",
        "counts": {
            "shelves": len(all_shelves),
            "shelves_populated": len(shelves),
            "shelves_reserved": len(empty_shelves),
            "books": len(books),
            "h7c_files": h7c_total,
            "h7_remaining": h7_remaining,
        },
        "shelves": all_shelves,
        "books": books,
        "elapsed_ms": elapsed_ms,
    }


def convert_h7_file(
    h7_path: Path,
    *,
    remove_h7: bool = True,
    remove_corpus_dup: bool = True,
) -> dict[str, Any]:
    """Convert one H7 file to H7c in-place; update book.json; remove H7."""
    h7_mod = _h7_mod()
    h7c_mod = _h7c_mod()
    if not h7_mod or not h7c_mod:
        return {"ok": False, "error": "h7_or_h7c_module_missing", "path": str(h7_path)}

    book_dir = h7_path.parent
    book_id = h7_path.stem
    try:
        header, text = h7_mod.unpack_h7(h7_path.read_bytes(), verify=True)
    except Exception as exc:
        return {"ok": False, "error": "h7_unpack_failed", "path": str(h7_path), "detail": str(exc)[:200]}

    meta = {
        "id": str(header.get("id") or book_id),
        "title": str(header.get("title") or book_id),
        "author": str(header.get("author") or ""),
        "dewey": str(header.get("dewey") or ""),
        "category": str(header.get("subject") or header.get("category") or ""),
        "migrated_from": "h7",
        "migrated": _now(),
    }
    h7c_path = book_dir / f"{book_id}.h7c"
    packed = h7c_mod.pack_h7c(text, meta, use_optimizer=True, format_version=2)
    h7c_path.write_bytes(packed)

    book_doc = _read_book_json(book_dir)
    book_doc.update({
        "id": meta["id"],
        "title": meta["title"],
        "author": meta["author"],
        "dewey": meta.get("dewey") or book_doc.get("dewey", ""),
        "format": "h7c",
        "h7c": _rel(h7c_path),
        "h7": None,
        "cover": book_doc.get("cover"),
        "migrated_from": "h7",
    })
    _write_book_json(book_dir, book_doc)

    removed_h7 = False
    if remove_h7 and h7_path.is_file():
        h7_path.unlink()
        removed_h7 = True

    corpus_dup = DEWEY_ROOT / "004-computers" / "h7c-corpus" / book_id / f"{book_id}.h7c"
    removed_corpus = False
    if remove_corpus_dup and corpus_dup.is_file() and corpus_dup.resolve() != h7c_path.resolve():
        corpus_dup.unlink()
        removed_corpus = True
        parent = corpus_dup.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()

    return {
        "ok": True,
        "id": book_id,
        "h7": str(h7_path),
        "h7c": str(h7c_path),
        "bytes_h7c": len(packed),
        "removed_h7": removed_h7,
        "removed_corpus_dup": removed_corpus,
    }


def migrate_h7_to_h7c(*, remove_h7: bool = True, dry_run: bool = False) -> dict[str, Any]:
    """Convert all Dewey H7 files to H7c in-place."""
    t0 = time.perf_counter()
    h7_files = glob_h7_files()
    converted: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for h7_path in h7_files:
        if dry_run:
            converted.append({"ok": True, "dry_run": True, "path": str(h7_path)})
            continue
        result = convert_h7_file(h7_path, remove_h7=remove_h7)
        if result.get("ok"):
            converted.append(result)
        else:
            errors.append(result)

    rebuild = rebuild_shelf_manifests()
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "schema": "field-dewey-h7c-migration/v1",
        "updated": _now(),
        "ok": len(errors) == 0,
        "dry_run": dry_run,
        "converted": len(converted),
        "errors": len(errors),
        "h7_remaining": len(glob_h7_files()),
        "h7c_total": len(glob_h7c_files()),
        "shelves_rebuilt": rebuild.get("shelves", 0),
        "results": converted[:32],
        "error_samples": errors[:8],
        "elapsed_ms": elapsed_ms,
    }


def rebuild_shelf_manifests() -> dict[str, Any]:
    """Rebuild shelf.json for every populated Dewey shelf from glob."""
    rebuilt = 0
    for shelf in glob_shelves():
        if not shelf.get("books"):
            continue
        shelf_dir = INSTALL / str(shelf.get("path", ""))
        if not shelf_dir.is_dir():
            continue
        doc = {
            "schema": "dewey-shelf/v1",
            "shelf": shelf.get("slug"),
            "code": shelf.get("code"),
            "title": shelf.get("title"),
            "updated": _now(),
            "format_primary": "h7c",
            "book_count": shelf.get("book_count", 0),
            "h7c_count": shelf.get("h7c_count", 0),
            "books": [
                {
                    "id": b.get("id"),
                    "title": b.get("title"),
                    "author": b.get("author"),
                    "dewey": b.get("dewey"),
                    "format": b.get("format", "h7c"),
                    "h7c": b.get("h7c"),
                    "cover": b.get("cover"),
                    "ready": b.get("ready", True),
                }
                for b in shelf.get("books") or []
            ],
        }
        (shelf_dir / "shelf.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rebuilt += 1
    return {"ok": True, "shelves": rebuilt}


def h7c_meta(path: Path) -> dict[str, Any] | None:
    path = ensure_h7c_path(path) if path.suffix.lower() == ".h7" else path
    iron = _ironclad_h7_access()
    if iron and hasattr(iron, "h7c_meta_fast"):
        try:
            row = iron.h7c_meta_fast(path)
            if row:
                return row
        except Exception:
            pass
    h7c_mod = _h7c_mod()
    if not h7c_mod or not path.is_file():
        return None
    if hasattr(h7c_mod, "read_h7c_header_file"):
        try:
            header = h7c_mod.read_h7c_header_file(path)
            book_id = str(header.get("id") or path.stem)
            shelf_slug = _shelf_slug(path.parent.parent)
            return {
                "id": book_id,
                "title": str(header.get("title") or book_id),
                "author": str(header.get("author", "")),
                "category": str(header.get("category") or header.get("subject") or ""),
                "char_count": int(header.get("char_count") or 0),
                "file_bytes": path.stat().st_size,
                "format": "h7c",
                "path": str(path),
                "h7c": _rel(path),
                "dewey": str(header.get("dewey") or ""),
                "shelf": shelf_slug,
                "ready": True,
                "source": "field-dewey-library",
            }
        except Exception:
            pass
    try:
        header, _, stats = h7c_mod.decompress_h7c(path.read_bytes(), verify=False)
        book_id = str(header.get("id") or path.stem)
        shelf_slug = _shelf_slug(path.parent.parent)
        return {
            "id": book_id,
            "title": str(header.get("title") or book_id),
            "author": str(header.get("author", "")),
            "category": str(header.get("category") or header.get("subject") or ""),
            "char_count": int(header.get("char_count") or 0),
            "file_bytes": path.stat().st_size,
            "format": "h7c",
            "path": str(path),
            "h7c": _rel(path),
            "dewey": str(header.get("dewey") or ""),
            "shelf": shelf_slug,
            "ready": True,
            "balance_id": stats.get("balance_id") or (stats.get("combinatronic_balance") or {}).get("balance_id"),
            "source": "field-dewey-library",
        }
    except Exception:
        return None


def read_h7c_text(book_id: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    """Read book text from H7c — auto-converts legacy H7 on open."""
    path = ensure_h7c_for_book(book_id) or find_h7c(book_id)
    if not path:
        return "", {}, {}
    h7c_mod = _h7c_mod()
    if not h7c_mod:
        return "", {}, {}
    header, text, stats = h7c_mod.decompress_h7c(path.read_bytes(), verify=True)
    return text, header, stats


def _rebuild_dewey_index() -> dict[str, Any]:
    idx = _import_mod("dewey_idx", "field-dewey-index.py")
    if idx and hasattr(idx, "build_index"):
        try:
            return idx.build_index(write=True)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:160]}
    return {"ok": False, "error": "dewey_index_missing"}


def publish_panel(*, migrate: bool = False) -> dict[str, Any]:
    if migrate:
        migrate_h7_to_h7c(remove_h7=True)
    tree = build_dewey_tree()
    _save(TREE_JSON, tree)
    index = _rebuild_dewey_index()
    panel = {
        "schema": "field-dewey-library-panel/v1",
        "updated": tree["updated"],
        "ok": tree["ok"],
        "counts": tree["counts"],
        "format_primary": "h7c",
        "sample_shelves": (tree.get("shelves") or [])[:8],
    }
    _save(PANEL, panel)
    if index.get("counts"):
        panel["dewey_index"] = index.get("counts")
    return {"ok": True, "panel": panel, "tree_path": str(TREE_JSON), "dewey_index": index.get("counts")}


def panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached:
        return cached
    return publish_panel(migrate=False).get("panel") or {}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "status", "json"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("tree", "shelves", "glob"):
        print(json.dumps(build_dewey_tree(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "books":
        print(json.dumps({"books": glob_books(), "count": len(glob_books())}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("migrate", "convert"):
        dry = "--dry-run" in sys.argv
        print(json.dumps(migrate_h7_to_h7c(remove_h7="--keep-h7" not in sys.argv, dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    if cmd == "rebuild":
        print(json.dumps(rebuild_shelf_manifests(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "open" and len(sys.argv) > 2:
        src = Path(sys.argv[2])
        if not src.is_file():
            src = INSTALL / sys.argv[2]
        out = ensure_h7c_path(src)
        print(json.dumps({
            "ok": out.suffix.lower() == ".h7c" and out.is_file(),
            "source": str(src),
            "h7c": str(out),
            "converted": str(out) != str(src),
        }, ensure_ascii=False, indent=2))
        return 0 if out.suffix.lower() == ".h7c" and out.is_file() else 1
    if cmd == "read" and len(sys.argv) > 2:
        text, header, stats = read_h7c_text(sys.argv[2])
        print(json.dumps({
            "ok": bool(text),
            "id": sys.argv[2],
            "chars": len(text),
            "header": header,
            "stats": stats,
            "preview": text[:240],
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        tree = build_dewey_tree()
        ok = tree["counts"]["h7c_files"] > 0 and tree["counts"]["books"] > 0
        if tree["counts"]["h7_remaining"] > 0:
            mig = migrate_h7_to_h7c(remove_h7=True)
            ok = ok and mig.get("ok", False)
            tree = build_dewey_tree()
        ok = ok and tree["counts"]["h7_remaining"] == 0
        print(json.dumps({"ok": ok, "counts": tree["counts"]}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["panel", "tree", "books", "migrate", "rebuild", "open <path>", "read <id>", "verify"],
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())