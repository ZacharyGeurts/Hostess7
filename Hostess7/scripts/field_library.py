#!/usr/bin/env pythong
"""Hostess 7 library — textbooks folder, .H7 books, free OER + classics for H7 to read."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_h7_book import read_h7_file, unpack_h7, write_h7  # noqa: E402
from field_library_catalog import books_with_fetch_url, iter_all_library_books, library_count  # noqa: E402
from field_library_fetch import MAX_LIBRARY_BYTES, MIN_LIBRARY_BPS, fetch_library_fast  # noqa: E402
from field_paths import ROOT

TEXTBOOKS_DIR = ROOT / "cache" / "fieldstorage" / "textbooks"
LIBRARY_META = ROOT / "cache" / "fieldstorage" / "brain" / "library"
MANIFEST = LIBRARY_META / "manifest.json"
INDEX = LIBRARY_META / "search_index.jsonl"
BUILD_LOG = LIBRARY_META / "build.jsonl"
K12_FETCH = ROOT / "cache" / "fieldstorage" / "team_staging" / "k12_bulk" / "fetched"
INTERNET_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "internet" / "cache"

LIBRARY_VERSION = 2


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_layout() -> None:
    TEXTBOOKS_DIR.mkdir(parents=True, exist_ok=True)
    LIBRARY_META.mkdir(parents=True, exist_ok=True)


def classify_dewey_for_pack(book: dict[str, Any], text: str) -> dict[str, str]:
    from field_library_organize import classify_dewey  # noqa: WPS433

    return classify_dewey(
        category=str(book.get("category", book.get("subject", ""))),
        title=str(book.get("title", "")),
        subject=str(book.get("subject", "")),
        author=str(book.get("author", "")),
        text_sample=text[:3000],
    )


def _h7_path(book_id: str, book: dict[str, Any] | None = None) -> Path:
    from field_library_organize import h7_path_for_book  # noqa: WPS433

    if book:
        return h7_path_for_book(book_id, book)
    safe = re.sub(r"[^\w.-]", "_", book_id)
    legacy = TEXTBOOKS_DIR / f"{safe}.h7"
    if legacy.is_file():
        return legacy
    for hit in TEXTBOOKS_DIR.glob(f"**/{safe}.h7"):
        return hit
    return TEXTBOOKS_DIR / "dewey" / "000" / f"{safe}.h7"


def _full_cached_text(url: str) -> str:
    from field_internet import _cache_key  # noqa: WPS433

    bin_path = INTERNET_CACHE / f"{_cache_key(url)}.bin"
    if bin_path.is_file():
        return bin_path.read_text(encoding="utf-8", errors="replace")
    return ""


def _text_for_book(
    book: dict[str, Any],
    *,
    force_fetch: bool = False,
    fast_only: bool = True,
) -> tuple[str, str]:
    """Resolve lossless text — k12 cache, fast cache, or fast network fetch (≤3 MiB, ≥3 MiB/s)."""
    bid = str(book.get("id", ""))
    k12_path = K12_FETCH / f"{bid}.txt"
    if k12_path.is_file() and not force_fetch:
        return k12_path.read_text(encoding="utf-8", errors="replace"), "k12_cache"

    url = str(book.get("fetch_url", ""))
    if not url:
        return "", "missing_url"

    if "wikibooks.org" in url and "action=render" not in url:
        url += "&action=render" if "?" in url else "?action=render"

    if not force_fetch:
        full = _full_cached_text(url)
        if len(full) > 500:
            if fast_only and len(full.encode("utf-8")) > MAX_LIBRARY_BYTES:
                return "", f"cache_too_large:{len(full.encode('utf-8'))}>{MAX_LIBRARY_BYTES}"
            return full, "internet_cache"

    if fast_only:
        os.environ.setdefault("HOSTESS7_INTERNET", "1")
        rec = fetch_library_fast(url, force=force_fetch)
        if not rec.get("ok"):
            return "", f"fast_fetch_fail:{rec.get('error', '')}"
        return str(rec.get("text", "")), f"fast_fetched:{rec.get('bps', 0)}bps"

    os.environ.setdefault("HOSTESS7_INTERNET", "1")
    from field_internet import fetch_url  # noqa: WPS433

    rec = fetch_url(url, force=force_fetch)
    if not rec.get("ok"):
        return "", f"fetch_fail:{rec.get('error', '')}"
    text = _full_cached_text(url) or str(rec.get("text_preview", ""))
    return text, "fetched"


def pack_book(book: dict[str, Any], *, force_fetch: bool = False, fast_only: bool = True) -> dict[str, Any]:
    bid = str(book.get("id", ""))
    text, source = _text_for_book(book, force_fetch=force_fetch, fast_only=fast_only)
    if len(text.strip()) < 80:
        return {"id": bid, "ok": False, "error": f"no text ({source})", "source": source}

    meta = {
        "id": bid,
        "title": book.get("title", bid),
        "author": book.get("author", ""),
        "full_name": book.get("full_name") or book.get("title", ""),
        "license": book.get("license", "OER"),
        "publisher": book.get("publisher", ""),
        "subject": book.get("subject", book.get("category", "")),
        "grade_band": book.get("grade_band", ""),
        "fetch_url": book.get("fetch_url", ""),
        "source": source,
        "packed": _ts(),
        "reader": "Hostess7_only",
    }
    path = _h7_path(bid, book)
    dewey = classify_dewey_for_pack(book, text)
    meta["dewey"] = dewey["code"]
    meta["dewey_label"] = dewey["label"]
    stats = write_h7(path, text, meta)
    return {"id": bid, "ok": True, "path": str(path), "source": source, **stats}


def build_library(
    *,
    force_fetch: bool = False,
    limit: int | None = None,
    fast_only: bool = True,
    stem_only: bool = False,
) -> dict[str, Any]:
    """Pack catalog books into .H7 — fast policy: ≤3 MiB, ≥3 MiB/s on network."""
    _ensure_layout()
    books = books_with_fetch_url(stem_only=stem_only)
    if limit:
        books = books[:limit]

    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: list[dict[str, Any]] = []
    ok_n = 0
    workers = min(8, max(1, len(books)))
    if workers <= 1 or len(books) <= 2:
        for book in books:
            row = pack_book(book, force_fetch=force_fetch, fast_only=fast_only)
            results.append(row)
            if row.get("ok"):
                ok_n += 1
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(pack_book, book, force_fetch=force_fetch, fast_only=fast_only): book
                for book in books
            }
            for fut in as_completed(futures):
                row = fut.result()
                results.append(row)
                if row.get("ok"):
                    ok_n += 1

    index_rows: list[dict[str, Any]] = []
    for book in iter_all_library_books():
        bid = str(book.get("id", ""))
        h7 = _h7_path(bid)
        entry: dict[str, Any] = {
            "id": bid,
            "title": book.get("title", ""),
            "author": book.get("author", ""),
            "subject": book.get("subject", ""),
            "grade_band": book.get("grade_band", ""),
            "license": book.get("license", ""),
            "h7_path": str(h7) if h7.is_file() else "",
            "has_h7": h7.is_file(),
        }
        if h7.is_file():
            try:
                header, _ = unpack_h7(h7.read_bytes(), verify=True)
                entry.update({
                    "char_count": header.get("char_count"),
                    "line_count": header.get("line_count"),
                    "file_bytes": h7.stat().st_size,
                })
                sample = read_h7_file(h7, line_start=1, line_end=3)
                entry["blob"] = (
                    f"{entry['title']} {entry.get('author', '')} {sample.get('text', '')[:2000]}"
                ).lower()
            except (OSError, ValueError):
                entry["has_h7"] = False
        else:
            entry["blob"] = f"{book.get('title', '')} {book.get('subject', '')}".lower()
        index_rows.append(entry)

    with INDEX.open("w", encoding="utf-8") as f:
        for row in index_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    manifest = {
        "version": LIBRARY_VERSION,
        "updated": _ts(),
        "textbooks_dir": str(TEXTBOOKS_DIR),
        "catalog_count": library_count(),
        "h7_packed": ok_n,
        "h7_on_disk": sum(1 for p in TEXTBOOKS_DIR.glob("*.h7")),
        "format": "h7b/1",
        "fast_policy": {
            "max_bytes": MAX_LIBRARY_BYTES,
            "min_bps": MIN_LIBRARY_BPS,
            "fast_only": fast_only,
        },
        "note": "Lossless .H7 — every character and line; fast fetch ≤3 MiB per book",
        "books": results,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with BUILD_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _ts(), "packed": ok_n, "total": len(books)}) + "\n")
    return manifest


def list_library() -> list[dict[str, Any]]:
    _ensure_layout()
    rows: list[dict[str, Any]] = []
    for path in sorted(TEXTBOOKS_DIR.glob("*.h7")):
        try:
            header, _ = unpack_h7(path.read_bytes(), verify=False)
            rows.append({
                "id": header.get("id", path.stem),
                "title": header.get("title", path.stem),
                "author": header.get("author", ""),
                "lines": header.get("line_count"),
                "chars": header.get("char_count"),
                "bytes": path.stat().st_size,
                "path": str(path),
            })
        except (OSError, ValueError):
            continue
    return rows


def read_library(book_id: str, *, line_start: int = 1, line_end: int | None = None) -> dict[str, Any]:
    path = _h7_path(book_id)
    if not path.is_file():
        for p in TEXTBOOKS_DIR.glob("*.h7"):
            try:
                h, _ = unpack_h7(p.read_bytes(), verify=False)
                if str(h.get("id", "")) == book_id:
                    path = p
                    break
            except ValueError:
                continue
    if not path.is_file():
        return {"ok": False, "error": f"no .H7 for {book_id}"}
    doc = read_h7_file(path, line_start=line_start, line_end=line_end)
    doc["ok"] = True
    return doc


def search_library(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    _ensure_layout()
    if not INDEX.is_file():
        build_library(force_fetch=False)
    toks = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
    scored: list[tuple[int, dict[str, Any]]] = []
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not row.get("has_h7"):
            continue
        blob = str(row.get("blob", "")).lower()
        score = sum(6 if t in blob else 0 for t in toks)
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:limit]]


def synthesize_library_reading(query: str, *, line_window: int = 12) -> list[str]:
    """Hostess 7 reads matching .H7 books and returns excerpts."""
    hits = search_library(query, limit=3)
    if not hits:
        hits = search_library("math science history literature", limit=3)
    paras: list[str] = [
        f"Hostess 7 library — {TEXTBOOKS_DIR} · .H7 lossless (programming, physics, chemistry, medical, K-12).",
        f"Fast fetch policy: ≤{MAX_LIBRARY_BYTES // (1024 * 1024)} MiB per book (small = fast connection).",
    ]
    if MANIFEST.is_file():
        try:
            m = json.loads(MANIFEST.read_text(encoding="utf-8"))
            paras.append(
                f"On shelf: {m.get('h7_on_disk', 0)} .H7 volumes · catalog {m.get('catalog_count', 0)} free books."
            )
        except json.JSONDecodeError:
            pass
    for hit in hits:
        bid = str(hit.get("id", ""))
        doc = read_library(bid, line_start=1, line_end=line_window)
        if not doc.get("ok"):
            continue
        title = doc.get("title", bid)
        lines = doc.get("lines") or []
        excerpt = "\n".join(lines[:line_window])
        paras.append(
            f"Reading [{title}] (lines 1–{min(line_window, len(lines))}, "
            f"{doc.get('line_count', '?')} total lines, {doc.get('char_count', '?')} chars):\n{excerpt[:2400]}"
        )
    if len(paras) < 2:
        paras.append("Build library: `./Hostess7.sh library-build`")
    return paras


def format_library_report(manifest: dict[str, Any]) -> str:
    lines = [
        "=== Hostess 7 — H7 Library Build ===",
        f"Textbooks folder: `{TEXTBOOKS_DIR}`",
        f"Packed: {manifest.get('h7_packed')} · on disk: {manifest.get('h7_on_disk')} · catalog: {manifest.get('catalog_count')}",
        "",
        "Recent:",
    ]
    for b in (manifest.get("books") or [])[-8:]:
        if b.get("ok"):
            lines.append(
                f"  • {b.get('id')}: {b.get('char_count', '?')} chars · "
                f"{b.get('file_bytes', '?')} B .H7 · ratio ~{b.get('compression_ratio', '?')}x"
            )
        else:
            lines.append(f"  • {b.get('id')}: SKIP — {b.get('error', '?')}")
    lines.append("")
    lines.append(f"Manifest: `{MANIFEST}`")
    lines.append("Read: `./Hostess7.sh library-read <id>` · Search: `./Hostess7.sh library-search \"…\"`")
    return "\n".join(lines)


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd in ("build", "pack", "seed"):
        force = "--force" in sys.argv
        fast_only = "--slow" not in sys.argv
        stem_only = "--stem" in sys.argv
        limit = None
        for i, a in enumerate(sys.argv):
            if a == "--limit" and i + 1 < len(sys.argv) and sys.argv[i + 1].isdigit():
                limit = int(sys.argv[i + 1])
        manifest = build_library(force_fetch=force, limit=limit, fast_only=fast_only, stem_only=stem_only)
        print(format_library_report(manifest))
        print(f"METRIC library_h7={manifest.get('h7_on_disk')}")
        print(f"METRIC library_packed={manifest.get('h7_packed')}")
        print("OK library-build")
        return 0 if manifest.get("h7_packed", 0) > 0 else 1
    if cmd in ("list", "ls"):
        rows = list_library()
        for r in rows:
            print(f"  • {r.get('id')}: {r.get('title')} — {r.get('lines')} lines, {r.get('bytes')} B")
        print(f"METRIC library_count={len(rows)}")
        print("OK library-list")
        return 0
    if cmd in ("read", "open"):
        if len(sys.argv) < 3:
            print("usage: field_library.py read <book_id> [line_start] [line_end]", file=sys.stderr)
            return 1
        bid = sys.argv[2]
        ls = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else 1
        le = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[4].isdigit() else None
        doc = read_library(bid, line_start=ls, line_end=le)
        if not doc.get("ok"):
            print(f"BLOCKER: {doc.get('error')}", file=sys.stderr)
            return 1
        print(f"# {doc.get('title')} — lines {doc.get('line_start', ls)}–{doc.get('line_end', le or doc.get('line_count'))}")
        print(doc.get("text", ""))
        print(f"METRIC library_chars={doc.get('char_count')}")
        print(f"METRIC library_lines={doc.get('line_count')}")
        print("OK library-read")
        return 0
    if cmd in ("search", "find"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "textbook"
        for hit in search_library(q):
            print(f"  • {hit.get('id')}: {hit.get('title')} · {hit.get('line_count', '?')} lines")
        print("OK library-search")
        return 0
    st = json.loads(MANIFEST.read_text()) if MANIFEST.is_file() else {}
    on_disk = len(list(TEXTBOOKS_DIR.glob("*.h7")))
    print(f"H7 library: {on_disk} books · catalog {library_count()} · dir `{TEXTBOOKS_DIR}`")
    print(f"METRIC library_h7={on_disk}")
    print("OK library-status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())