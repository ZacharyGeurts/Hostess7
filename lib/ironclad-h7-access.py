#!/usr/bin/env python3
"""Ironclad H7 access — metadata-only catalog, header-only H7c, no body reads."""
from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any, Iterator

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DEWEY_ROOT = INSTALL / "library" / "dewey"
INDEX_PATH = STATE / "ironclad-h7-access-index.json"

_CATALOG: dict[str, Any] | None = None
_CATALOG_MTIME: float = 0.0


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
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
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


def _h7c_header_mod() -> Any | None:
    return _import_mod("h7c_hdr", "field-h7c-compression.py")


def _read_book_json(book_dir: Path) -> dict[str, Any]:
    p = book_dir / "book.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(INSTALL.resolve()))
    except ValueError:
        return str(path)


def _shelf_slug(shelf_dir: Path) -> str:
    try:
        return str(shelf_dir.relative_to(DEWEY_ROOT)).replace("\\", "/")
    except ValueError:
        return shelf_dir.name


def _iter_book_json_paths() -> Iterator[Path]:
    """Walk Dewey tree — book.json only, no H7c body reads."""
    if not DEWEY_ROOT.is_dir():
        return
    stack = [DEWEY_ROOT]
    while stack:
        node = stack.pop()
        try:
            with os.scandir(node) as it:
                dirs: list[Path] = []
                for entry in it:
                    if entry.name.startswith("."):
                        continue
                    p = Path(entry.path)
                    if entry.is_dir(follow_symlinks=False):
                        dirs.append(p)
                    elif entry.is_file(follow_symlinks=False) and entry.name == "book.json":
                        yield p
                stack.extend(reversed(dirs))
        except OSError:
            continue


def _header_meta(h7c_path: Path) -> dict[str, Any]:
    mod = _h7c_header_mod()
    if not mod or not hasattr(mod, "read_h7c_header_file"):
        return {}
    try:
        return mod.read_h7c_header_file(h7c_path)
    except Exception:
        return {}


def _entry_from_book_json(book_json: Path) -> dict[str, Any] | None:
    book_dir = book_json.parent
    row = _read_book_json(book_dir)
    bid = str(row.get("id") or book_dir.name)
    if not bid:
        return None
    h7c = book_dir / f"{bid}.h7c"
    if not h7c.is_file():
        alt = book_dir / f"{book_dir.name}.h7c"
        h7c = alt if alt.is_file() else h7c
    shelf_dir = book_dir.parent
    entry: dict[str, Any] = {
        "id": bid,
        "title": str(row.get("title") or bid),
        "author": str(row.get("author") or ""),
        "dewey": str(row.get("dewey") or ""),
        "format": str(row.get("format") or ("h7c" if h7c.is_file() else "catalog")),
        "cover": row.get("cover"),
        "path": _rel(book_dir),
        "book_dir": str(book_dir.resolve()),
        "h7c": _rel(h7c) if h7c.is_file() else None,
        "h7c_path": str(h7c.resolve()) if h7c.is_file() else None,
        "ready": h7c.is_file(),
        "shelf": _shelf_slug(shelf_dir),
        "source": "ironclad-h7-access",
        "book_kind": row.get("book_kind"),
        "combinatronic_lang": row.get("combinatronic_lang"),
    }
    if h7c.is_file():
        try:
            st = h7c.stat()
            entry["file_bytes"] = st.st_size
            entry["mtime"] = int(st.st_mtime)
        except OSError:
            pass
        if not entry.get("char_count") and os.environ.get("IRONCLAD_H7_HEADER_READ", "0").strip().lower() not in ("0", "false", "no"):
            hdr = _header_meta(h7c)
            if hdr:
                entry["char_count"] = int(hdr.get("char_count") or 0)
                entry.setdefault("title", str(hdr.get("title") or entry["title"]))
                entry.setdefault("author", str(hdr.get("author") or ""))
                entry.setdefault("dewey", str(hdr.get("dewey") or entry["dewey"]))
    return entry


def _load_cached_index() -> dict[str, Any] | None:
    global _CATALOG, _CATALOG_MTIME
    if not INDEX_PATH.is_file():
        return None
    try:
        mtime = INDEX_PATH.stat().st_mtime
    except OSError:
        return None
    if _CATALOG and _CATALOG_MTIME == mtime:
        return _CATALOG
    cached = _load(INDEX_PATH, {})
    if cached.get("schema") == "ironclad-h7-access/v1" and cached.get("catalog"):
        _CATALOG = cached
        _CATALOG_MTIME = mtime
        return cached
    return None


def build_index(*, refresh: bool = False) -> dict[str, Any]:
    """Build metadata catalog — book.json + stat only by default; headers optional."""
    global _CATALOG, _CATALOG_MTIME
    if not refresh:
        hit = _load_cached_index()
        if hit:
            return hit
    if not refresh and not os.environ.get("IRONCLAD_ACCESS_BUILD", "").strip().lower() in ("1", "true", "yes"):
        # Posture/resolve must not block on cold build — return empty shell if no cache
        return {
            "schema": "ironclad-h7-access/v1",
            "updated": _now(),
            "ok": True,
            "entry_count": 0,
            "catalog": {},
            "path_map": {},
            "postings": {},
            "hint": "run with IRONCLAD_ACCESS_BUILD=1 lib/ironclad-h7-access.py build",
        }

    t0 = time.perf_counter()
    catalog: dict[str, dict[str, Any]] = {}
    path_map: dict[str, str] = {}

    for book_json in _iter_book_json_paths():
        entry = _entry_from_book_json(book_json)
        if not entry:
            continue
        bid = entry["id"]
        catalog[bid] = entry
        if entry.get("h7c_path"):
            path_map[bid] = str(entry["h7c_path"])

    # Manifest metadata only — jsonl/manifest reads, no H7 bodies
    if os.environ.get("IRONCLAD_H7_SKIP_MANIFEST", "").strip().lower() not in ("1", "true", "yes"):
        tie = _import_mod("h7_tie", "h7-field-drive-tie.py")
        if tie and hasattr(tie, "manifest_index"):
            try:
                for bid, row in tie.manifest_index().items():
                    merged = {**catalog.get(bid, {}), **row, "id": bid}
                    if row.get("path") and not merged.get("h7c_path"):
                        merged["field_path"] = row.get("path")
                    catalog[bid] = merged
            except Exception:
                pass

    # Registry overlay — cached JSON only, never triggers full registry rebuild
    if os.environ.get("IRONCLAD_H7_SKIP_REGISTRY", "").strip().lower() not in ("1", "true", "yes"):
        reg_json = STATE / "field-library-registry.json"
        if reg_json.is_file():
            try:
                for row in (_load(reg_json, {}).get("entries") or []):
                    bid = str(row.get("id") or "")
                    if not bid:
                        continue
                    if bid not in catalog:
                        catalog[bid] = {**row, "source": "registry_cache"}
                    else:
                        catalog[bid] = {**catalog[bid], **{k: v for k, v in row.items() if v and k not in catalog[bid]}}
            except Exception:
                pass

    idx_mod = _import_mod("ironclad_tok", "ironclad-search-index.py")
    postings: dict[str, list[str]] = {}
    if idx_mod and hasattr(idx_mod, "build_token_index"):
        tok_idx = idx_mod.build_token_index(list(catalog.values()), id_key="id")
        postings = tok_idx.get("postings") or {}

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    doc = {
        "schema": "ironclad-h7-access/v1",
        "updated": _now(),
        "ok": True,
        "entry_count": len(catalog),
        "token_count": len(postings),
        "catalog": catalog,
        "path_map": path_map,
        "postings": postings,
        "elapsed_ms": elapsed_ms,
        "motto": "Ironclad H7 — metadata and headers only; no H7c body reads",
        "ironclad_citation": "ironclad:h7:1",
    }
    _save(INDEX_PATH, doc)
    _CATALOG = doc
    _CATALOG_MTIME = INDEX_PATH.stat().st_mtime
    return doc


def load_index(*, refresh: bool = False) -> dict[str, Any]:
    return build_index(refresh=refresh)


def resolve_h7c_path(book_id: str) -> Path | None:
    """O(1) H7c path resolve — Ironclad index, no tree walk."""
    doc = load_index()
    hit = (doc.get("path_map") or {}).get(book_id)
    if hit:
        p = Path(hit)
        if p.is_file():
            return p
    row = (doc.get("catalog") or {}).get(book_id) or {}
    for key in ("h7c_path", "path"):
        raw = row.get(key)
        if not raw:
            continue
        p = Path(str(raw))
        if not p.is_absolute():
            p = INSTALL / p
        h7c = p if p.suffix.lower() == ".h7c" else p / f"{book_id}.h7c"
        if h7c.is_file():
            return h7c
    return None


def catalog_entries() -> list[dict[str, Any]]:
    doc = load_index()
    return list((doc.get("catalog") or {}).values())


def search_books(query: str, *, limit: int = 24) -> list[dict[str, Any]]:
    doc = load_index()
    idx_mod = _import_mod("ironclad_tok_s", "ironclad-search-index.py")
    catalog = doc.get("catalog") or {}
    if idx_mod and hasattr(idx_mod, "search_token_index"):
        hits = idx_mod.search_token_index(doc, query, limit=limit * 2)
        if idx_mod and hasattr(idx_mod, "ironclad_sort"):
            hits, _ = idx_mod.ironclad_sort(hits, context="catalog_index", n=limit)
        return hits[:limit]
    q = query.lower().strip()
    if not q:
        return list(catalog.values())[:limit]
    out: list[dict[str, Any]] = []
    for row in catalog.values():
        blob = f"{row.get('id')} {row.get('title')} {row.get('author')} {row.get('dewey')}".lower()
        if q in blob:
            out.append(row)
    if idx_mod and hasattr(idx_mod, "ironclad_sort"):
        out, _ = idx_mod.ironclad_sort(out, context="catalog_index", n=limit)
    return out[:limit]


def h7c_meta_fast(path: Path) -> dict[str, Any] | None:
    """Book row from path — header-only, no decompress."""
    p = Path(path)
    if p.suffix.lower() != ".h7c" or not p.is_file():
        return None
    hdr = _header_meta(p)
    bid = str(hdr.get("id") or p.stem)
    return {
        "id": bid,
        "title": str(hdr.get("title") or bid),
        "author": str(hdr.get("author", "")),
        "category": str(hdr.get("category") or hdr.get("subject") or ""),
        "char_count": int(hdr.get("char_count") or 0),
        "file_bytes": p.stat().st_size,
        "format": "h7c",
        "path": str(p),
        "h7c": _rel(p),
        "h7c_path": str(p.resolve()),
        "dewey": str(hdr.get("dewey") or ""),
        "shelf": _shelf_slug(p.parent.parent),
        "ready": True,
        "source": "ironclad-h7-access",
    }


def posture() -> dict[str, Any]:
    doc = _load_cached_index() or load_index()
    return {
        "schema": "ironclad-h7-access-posture/v1",
        "updated": _now(),
        "ok": bool(doc.get("ok")),
        "entry_count": doc.get("entry_count", 0),
        "token_count": doc.get("token_count", 0),
        "index_path": str(INDEX_PATH),
        "elapsed_ms": doc.get("elapsed_ms"),
        "motto": doc.get("motto"),
        "no_body_reads": True,
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Ironclad H7 access index")
    ap.add_argument("cmd", nargs="?", default="posture")
    ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--limit", type=int, default=24)
    args = ap.parse_args()
    cmd = args.cmd.strip().lower()
    if cmd in ("posture", "json", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "build":
        print(json.dumps(build_index(refresh=True), ensure_ascii=False)[:4000])
        return 0
    if cmd == "resolve":
        p = resolve_h7c_path(args.arg)
        print(json.dumps({"book_id": args.arg, "h7c": str(p) if p else None}, indent=2))
        return 0 if p else 1
    if cmd == "search":
        print(json.dumps({"hits": search_books(args.arg, limit=args.limit)}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["posture", "build", "resolve BOOK", "search QUERY"]}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())