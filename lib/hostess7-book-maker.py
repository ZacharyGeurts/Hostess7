#!/usr/bin/env pythong
"""Hostess 7 Book Maker — author studio with per-book information index."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-book-maker-doctrine.json"
LIBRARY = INSTALL / "library" / "dewey"
PANEL = STATE / "hostess7-book-maker-panel.json"
DRAFTS = STATE / "hostess7-book-maker-drafts.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(INSTALL))
    except ValueError:
        return str(path)


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def list_authors() -> dict[str, Any]:
    doctrine = load_doctrine()
    authors = doctrine.get("authors") or {}
    idx = _import_mod("book_info", "lib/field-book-information-index.py")
    presets = getattr(idx, "AUTHOR_PRESETS", {}) if idx else {}
    merged = {**presets, **authors}
    return {
        "schema": "hostess7-book-maker-authors/v1",
        "updated": _now(),
        "authors": list(merged.values()),
        "note": "Grok may author field books; Hostess 7 authors self-biography and operator volumes.",
    }


def _slugify(title: str) -> str:
    base = re.sub(r"[^a-zA-Z0-9]+", "_", title.strip().lower()).strip("_")
    return base[:64] or "untitled_book"


def _import_h7c() -> Any:
    path = INSTALL / "lib" / "field-h7c-compression.py"
    spec = importlib.util.spec_from_file_location("h7c", path)
    if not spec or not spec.loader:
        raise ImportError("field-h7c-compression.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def compose_book_body(
    *,
    title: str,
    author_display: str,
    co_author: str,
    owner: str,
    written_at: str,
    written_date: str,
    body: str,
    dewey: str,
    dewey_label: str,
    shelf: str,
) -> tuple[str, dict[str, str]]:
    idx = _import_mod("book_info", "lib/field-book-information-index.py")
    title_ts = idx.timestamped_title(title, written_at=written_at) if idx else title
    sections: dict[str, str] = {}
    header = "\n".join(x for x in [
        f"# {title_ts}",
        "",
        "![Cover](h7fig:cover)",
        "",
        f"**Title:** {title_ts}",
        f"**Author:** {author_display}",
        f"**Co-author:** {co_author}" if co_author else "",
        f"**Written date:** {written_date}",
        f"**Written at:** {written_at}",
        f"**Owner:** {owner}",
        f"**Dewey:** {dewey}" + (f" — {dewey_label}" if dewey_label else ""),
        f"**Shelf:** {shelf}",
        "**Format:** h7c · format_version 3",
        "",
        "---",
        "",
    ] if x)
    sections["header"] = header
    chapter_title = f"Body · {written_at}" if written_at else "Body"
    sections["body"] = f"\n## {chapter_title}\n\n{body.strip()}\n"
    return "\n".join(sections.values()), sections


def pack_book(
    *,
    title: str,
    body: str,
    author: str = "hostess7",
    co_author: str = "",
    owner: str = "ZacharyGeurts",
    dewey: str = "000",
    dewey_label: str = "",
    shelf: str = "000-computer-science",
    book_id: str = "",
    book_kind: str = "authored",
) -> dict[str, Any]:
    """Pack one authored book — H7c + book.json + manifest + information index."""
    written_at = _now()
    written_date = written_at[:10]
    auth_doc = (_import_mod("book_info", "lib/field-book-information-index.py") or {})
    resolve = getattr(auth_doc, "resolve_author", lambda x: {"display": str(x)})
    auth = resolve(author)
    author_display = str(auth.get("display") or author)
    co = co_author or (
        "Grok (xAI)" if auth.get("id") == "hostess7" else "Hostess 7" if auth.get("id") == "grok" else ""
    )
    slug = book_id or _slugify(title)
    if not dewey_label:
        dewey_label = "General works" if dewey.startswith("000") else "Library"

    text, sections = compose_book_body(
        title=title,
        author_display=author_display,
        co_author=co,
        owner=owner,
        written_at=written_at,
        written_date=written_date,
        body=body,
        dewey=dewey,
        dewey_label=dewey_label,
        shelf=shelf,
    )
    title_ts = f"{title} · {written_at}" if written_at not in title else title

    book_dir = LIBRARY / shelf / slug
    book_dir.mkdir(parents=True, exist_ok=True)
    h7c_path = book_dir / f"{slug}.h7c"

    h7c_mod = _import_h7c()
    meta = {
        "id": slug,
        "title": title_ts,
        "author": author_display,
        "co_author": co,
        "owner": owner,
        "written": written_date,
        "written_at": written_at,
        "dewey": dewey,
        "uploaded": written_at,
        "reader": "NEXUS_H7C",
        "book_kind": book_kind,
    }
    h7c_path.write_bytes(h7c_mod.pack_h7c(text, meta, use_optimizer=True, format_version=3))
    ein = "H7C-H7AUTH-" + hashlib.sha256(text.encode()).hexdigest()[:12]

    book_json = {
        "id": slug,
        "title": title_ts,
        "author": author_display,
        "co_author": co,
        "owner": owner,
        "written_date": written_date,
        "written_at": written_at,
        "dewey": dewey,
        "dewey_label": dewey_label,
        "ein": ein,
        "format": "h7c",
        "format_version": 3,
        "book_kind": book_kind,
        "h7c": _rel(h7c_path),
        "field_path": _rel(h7c_path),
        "github_shelf": shelf,
        "updated": written_at,
    }
    (book_dir / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = {
        "schema": "hostess7-authored-book/v1",
        "id": slug,
        "title": title_ts,
        "author": author_display,
        "written_at": written_at,
        "written_date": written_date,
        "dewey": dewey,
        "shelf": shelf,
        "char_count": len(text),
        "chapter_count": len(sections),
        "chapters": [
            {
                "num": i + 1,
                "slug": k,
                "title": k.replace("_", " ").title(),
                "title_timestamped": f"{k.replace('_', ' ').title()} · {written_at}",
                "written_at": written_at,
            }
            for i, k in enumerate(sections.keys())
        ],
        "updated": written_at,
    }
    (book_dir / "book-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    idx_mod = _import_mod("book_info", "lib/field-book-information-index.py")
    index_doc: dict[str, Any] = {}
    if idx_mod and hasattr(idx_mod, "build_index"):
        index_doc = idx_mod.build_index(
            book_id=slug,
            title=title,
            author=author,
            co_authors=[co] if co else [],
            owner=owner,
            written_at=written_at,
            written_date=written_date,
            dewey=dewey,
            dewey_label=dewey_label,
            shelf=shelf,
            ein=ein,
            h7c=_rel(h7c_path),
            book_kind=book_kind,
            char_count=len(text),
            sections=sections,
            tags=[book_kind, shelf.replace("-", "_")],
        )
        if hasattr(idx_mod, "write_index"):
            idx_mod.write_index(book_dir, index_doc)

    rep = {
        "ok": True,
        "book_id": slug,
        "title": title_ts,
        "author": author_display,
        "h7c": _rel(h7c_path),
        "ein": ein,
        "written_at": written_at,
        "index": index_doc,
        "char_count": len(text),
    }
    drafts = _load(DRAFTS, {"drafts": []})
    drafts["drafts"] = [d for d in drafts.get("drafts") or [] if d.get("book_id") != slug]
    drafts["drafts"].insert(0, {**rep, "packed": True, "updated": _now()})
    drafts["drafts"] = drafts["drafts"][:40]
    _save(DRAFTS, drafts)
    return rep


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = load_doctrine()
    drafts = _load(DRAFTS, {"drafts": []})
    indexes = []
    idx_mod = _import_mod("book_info", "lib/field-book-information-index.py")
    if idx_mod and hasattr(idx_mod, "scan_all"):
        indexes = idx_mod.scan_all()[-20:]
    out = {
        "schema": "hostess7-book-maker-panel/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "panel_route": doctrine.get("panel_route", "/hostess7-book-maker.html"),
        "authors": list_authors().get("authors") or [],
        "recent_packs": drafts.get("drafts") or [],
        "indexed_books": len(indexes),
        "index_sample": [
            {
                "book_id": x.get("book_id"),
                "title": (x.get("title") or {}).get("timestamped"),
                "author": (x.get("authorship") or {}).get("primary"),
                "written_at": (x.get("dates") or {}).get("written_at"),
            }
            for x in indexes[-8:]
        ],
        "required_metadata": doctrine.get("required_metadata") or [],
    }
    if write:
        _save(PANEL, out)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Hostess 7 Book Maker")
    parser.add_argument("cmd", nargs="?", default="panel")
    parser.add_argument("arg", nargs="?", default="")
    parser.add_argument("--title", default="")
    parser.add_argument("--body", default="")
    parser.add_argument("--author", default="hostess7")
    parser.add_argument("--co-author", default="")
    parser.add_argument("--dewey", default="000")
    parser.add_argument("--shelf", default="000-computer-science")
    parser.add_argument("--book-id", default="")
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "authors":
        print(json.dumps(list_authors(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "index":
        bid = args.arg or args.book_id
        idx_mod = _import_mod("book_info", "lib/field-book-information-index.py")
        if bid and idx_mod and hasattr(idx_mod, "read_index"):
            doc = idx_mod.read_index(bid)
            print(json.dumps(doc or {"ok": False, "error": "not_found"}, ensure_ascii=False, indent=2))
            return 0 if doc else 1
        if idx_mod and hasattr(idx_mod, "scan_all"):
            print(json.dumps({"ok": True, "books": idx_mod.scan_all()}, ensure_ascii=False, indent=2))
            return 0
        return 1
    if cmd == "pack":
        title = args.title or args.arg
        body = args.body or "Draft body — replace via book maker panel."
        if not title:
            print(json.dumps({"error": "pack requires --title"}, ensure_ascii=False))
            return 1
        rep = pack_book(
            title=title,
            body=body,
            author=args.author,
            co_author=args.co_author,
            dewey=args.dewey,
            shelf=args.shelf,
            book_id=args.book_id,
        )
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    print(json.dumps({
        "usage": "hostess7-book-maker.py [panel|authors|pack|index]",
        "panel": "/hostess7-book-maker.html",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())