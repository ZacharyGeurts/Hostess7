#!/usr/bin/env pythong
"""QA: .H7 book format — lossless pack/unpack + library build from cache."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_h7_book import pack_h7, read_h7_file, unpack_h7, write_h7  # noqa: E402
from field_library import TEXTBOOKS_DIR, build_library, read_library, search_library  # noqa: E402
from field_library_catalog import library_count  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    sample = "Line one\nLine two\nLine three — every character: café, 日本語, tab\there\n"
    blob = pack_h7(sample, {"id": "test", "title": "Roundtrip"})
    header, text = unpack_h7(blob)
    if text != sample:
        return fail("H7 roundtrip text mismatch")
    if header.get("line_count") != 4:
        return fail(f"expected 4 lines, got {header.get('line_count')}")
    if header.get("char_count") != len(sample):
        return fail("char_count mismatch")

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "test.h7"
        write_h7(p, sample, {"id": "test", "title": "File"})
        doc = read_h7_file(p, line_start=2, line_end=2)
        if doc.get("lines") != ["Line two"]:
            return fail(f"line read got {doc.get('lines')}")

    if library_count() < 85:
        return fail(f"expected 85+ catalog books, got {library_count()}")

    manifest = build_library(force_fetch=False)
    if manifest.get("h7_packed", 0) < 20:
        return fail(f"too few packed: {manifest.get('h7_packed')}")

    on_disk = len(list(TEXTBOOKS_DIR.glob("*.h7")))
    if on_disk < 20:
        return fail(f"too few .h7 on disk: {on_disk}")

    doc = read_library("gutenberg_mcgruffey_1", line_start=1, line_end=5)
    if not doc.get("ok") or not doc.get("lines"):
        return fail("could not read gutenberg_mcgruffey_1.h7")

    hits = search_library("algebra math textbook")
    if not hits:
        return fail("library search empty")

    print(f"OK h7_library books={on_disk} catalog={library_count()}")
    print(f"METRIC h7_books={on_disk}")
    print("OK h7-library-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())