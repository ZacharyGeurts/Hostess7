#!/usr/bin/env pythong
"""Generate World's Best Dewey Library folder tree for GitHub — shelf.json + book manifests."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
ROOT = Path(os.environ.get("NEXUS_REPO_ROOT", INSTALL.parent.parent if INSTALL.name == "nexus-shield" else INSTALL))
LIBRARY_ROOT = Path(os.environ.get("NEXUS_DEWEY_GITHUB_ROOT", ROOT / "library"))
DEWEY_TREE = INSTALL / "data" / "dewey-full-tree.json"
PROFILES = INSTALL / "data" / "library-profiles.json"


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



def _slug(code: str, title: str = "") -> str:
    main = re.sub(r"[^0-9].*", "", code)[:3].ljust(3, "0")
    if title:
        tail = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40]
        return f"{main}-{tail}" if tail else main
    for path in (DEWEY_TREE, INSTALL / "data" / "dewey-full-tree.json"):
        if path.is_file():
            doc = json.loads(path.read_text(encoding="utf-8"))
            for cls in doc.get("classes") or []:
                if str(cls.get("code")) == main:
                    return str(cls.get("slug", main))
    return main


def _load_catalog() -> dict[str, Any]:
    import importlib.util
    bridge = INSTALL / "lib" / "h7-library-bridge.py"
    spec = importlib.util.spec_from_file_location("h7_library_bridge", bridge)
    if not spec or not spec.loader:
        return {"books": [], "shelves": []}
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.build_catalog(force=True)


def _book_dir_name(book_id: str) -> str:
    return re.sub(r"[^\w.-]", "_", book_id)


def _write_json(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _shelf_readme(code: str, title: str, books: list[dict[str, Any]]) -> str:
    lines = [
        f"# Dewey {code} — {title}",
        "",
        f"**World's Best Dewey Library** · Hostess 7 field catalog · generated {_now()}",
        "",
        f"Books on this shelf: **{len(books)}**",
        "",
        "| Title | Author | Dewey | EIN | Format |",
        "|-------|--------|-------|-----|--------|",
    ]
    for b in sorted(books, key=lambda x: str(x.get("title", ""))):
        lines.append(
            f"| {b.get('title', b.get('id', ''))} "
            f"| {b.get('author', '—')} "
            f"| {b.get('dewey', '—')} "
            f"| {b.get('ein', '—')} "
            f"| {b.get('format', 'H7')} |"
        )
    lines.extend([
        "",
        "Content lives on the Hostess 7 field drive (`.h7c` / `.txt`). This GitHub tree is the catalog manifest.",
        "",
        "Hot-swap library profiles: `library/profiles/` — LOC, British Library, OCLC WorldCat.",
    ])
    return "\n".join(lines) + "\n"


def build_github_tree(*, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = catalog or _load_catalog()
    books: list[dict[str, Any]] = doc.get("books") or []
    tree_path = DEWEY_TREE if DEWEY_TREE.is_file() else INSTALL / "data" / "dewey-full-tree.json"
    tree = json.loads(tree_path.read_text(encoding="utf-8")) if tree_path.is_file() else {"classes": []}

    dewey_root = LIBRARY_ROOT / "dewey"
    profiles_root = LIBRARY_ROOT / "profiles"
    dewey_root.mkdir(parents=True, exist_ok=True)
    profiles_root.mkdir(parents=True, exist_ok=True)

    buckets: dict[str, list[dict[str, Any]]] = {}
    sub_buckets: dict[str, list[dict[str, Any]]] = {}
    for book in books:
        code = str(book.get("dewey", "000"))
        main = re.sub(r"[^0-9].*", "", code)[:3].ljust(3, "0")
        buckets.setdefault(main, []).append(book)
        sub_key = code if "." in code else main
        sub_buckets.setdefault(sub_key, []).append(book)

    shelf_count = 0
    book_manifest_count = 0

    for cls in tree.get("classes") or []:
        code = str(cls["code"])
        slug = str(cls.get("slug", _slug(code)))
        shelf_dir = dewey_root / slug
        shelf_books = buckets.get(code, [])
        shelf_doc = {
            "code": code,
            "title": cls.get("title", code),
            "slug": slug,
            "count": len(shelf_books),
            "updated": _now(),
            "books": [
                {
                    "id": b.get("id"),
                    "title": b.get("title"),
                    "author": b.get("author"),
                    "dewey": b.get("dewey"),
                    "ein": b.get("ein", ""),
                    "format": b.get("format", "H7"),
                    "ready": b.get("ready", False),
                    "path": b.get("path", ""),
                }
                for b in sorted(shelf_books, key=lambda x: str(x.get("title", "")))
            ],
        }
        _write_json(shelf_dir / "shelf.json", shelf_doc)
        (shelf_dir / "README.md").write_text(
            _shelf_readme(code, str(cls.get("title", code)), shelf_books),
            encoding="utf-8",
        )
        shelf_count += 1
        for b in shelf_books:
            bid = str(b.get("id", ""))
            if not bid:
                continue
            book_dir = shelf_dir / _book_dir_name(bid)
            manifest = {
                "id": bid,
                "title": b.get("title"),
                "author": b.get("author"),
                "dewey": b.get("dewey"),
                "dewey_label": b.get("dewey_label"),
                "ein": b.get("ein", ""),
                "isbn_13": b.get("isbn_13", ""),
                "gutenberg_id": b.get("gutenberg_id", ""),
                "format": b.get("format", "H7"),
                "field_path": b.get("path", ""),
                "cover": b.get("cover", ""),
                "github_shelf": slug,
                "updated": _now(),
            }
            _write_json(book_dir / "book.json", manifest)
            readme = (
                f"# {b.get('title', bid)}\n\n"
                f"**Dewey {b.get('dewey', '?')}** · {b.get('author', '')}\n\n"
                f"EIN: `{b.get('ein', '—')}`\n\n"
                f"Field path: `{b.get('path', 'on Hostess 7 drive')}`\n"
            )
            (book_dir / "README.md").write_text(readme, encoding="utf-8")
            book_manifest_count += 1

    for code, sub in (tree.get("subdivisions") or {}).items():
        slug = str(sub.get("slug", _slug(code, str(sub.get("title", "")))))
        sub_dir = dewey_root / slug
        sub_books = sub_buckets.get(code, [])
        if not sub_books:
            continue
        _write_json(sub_dir / "shelf.json", {
            "code": code,
            "title": sub.get("title", code),
            "parent": sub.get("parent", ""),
            "count": len(sub_books),
            "updated": _now(),
            "books": [{"id": b.get("id"), "title": b.get("title"), "dewey": b.get("dewey")} for b in sub_books],
        })
        (sub_dir / "README.md").write_text(
            _shelf_readme(code, str(sub.get("title", code)), sub_books),
            encoding="utf-8",
        )
        shelf_count += 1

    if PROFILES.is_file():
        prof_doc = json.loads(PROFILES.read_text(encoding="utf-8"))
        for pid, prof in (prof_doc.get("profiles") or {}).items():
            _write_json(profiles_root / f"{pid}.json", prof)

    root_readme = LIBRARY_ROOT / "README.md"
    root_readme.write_text(
        "\n".join([
            "# World's Best Dewey Library",
            "",
            "Hostess 7 field-drive catalog mirrored for GitHub browsing.",
            "",
            f"- **Shelves:** {shelf_count}",
            f"- **Book manifests:** {book_manifest_count}",
            f"- **Updated:** {_now()}",
            "",
            "## Browse",
            "",
            "- `dewey/` — Dewey Decimal shelves (000–900)",
            "- `profiles/` — Hot-swappable library profiles (H7, LOC, British Library, OCLC)",
            "",
            "## Profiles",
            "",
            "Switch catalog labels without moving books — translation text in each profile JSON.",
            "",
            "Generated by `lib/dewey-library-github.py` / `scripts/sync-dewey-github.sh`.",
        ]) + "\n",
        encoding="utf-8",
    )

    return {
        "ok": True,
        "library_root": str(LIBRARY_ROOT),
        "shelf_count": shelf_count,
        "book_manifest_count": book_manifest_count,
        "book_count": len(books),
        "updated": _now(),
    }


def main() -> int:
    result = build_github_tree()
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())