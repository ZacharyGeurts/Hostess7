#!/usr/bin/env pythong
"""Ingest all catalogued Bible / scripture volumes into .H7 (slow fetch for large texts)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_library import pack_book  # noqa: E402
from field_library_catalog import iter_all_library_books  # noqa: E402
from field_world_catalog import BIBLE_ENTRIES  # noqa: E402

LOG = ROOT / "cache" / "fieldstorage" / "brain" / "library" / "bible_ingest.jsonl"
BIBLE_CATEGORIES = frozenset({"bible", "theology", "scripture"})


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bible_books() -> list[dict]:
    seen: set[str] = set()
    rows: list[dict] = []
    for book in iter_all_library_books():
        cat = str(book.get("category", book.get("subject", ""))).lower()
        if cat not in BIBLE_CATEGORIES and "bible" not in str(book.get("tags", "")).lower():
            continue
        if not book.get("fetch_url"):
            continue
        bid = str(book.get("id", ""))
        if bid in seen:
            continue
        seen.add(bid)
        rows.append(dict(book))
    return rows


def run_bible_ingest(*, force: bool = False) -> dict:
    os.environ.setdefault("HOSTESS7_INTERNET", "1")
    books = _bible_books()
    results: list[dict] = []
    ok_n = 0
    for book in books:
        row = pack_book(book, force_fetch=force, fast_only=False)
        results.append(row)
        if row.get("ok"):
            ok_n += 1

    report = {
        "ts": _ts(),
        "catalog_bible_entries": len(BIBLE_ENTRIES),
        "fetchable_books": len(books),
        "packed_ok": ok_n,
        "results": results,
        "ok": ok_n > 0 or len(books) == 0,
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")
    return report


def main() -> int:
    force = "--force" in sys.argv
    report = run_bible_ingest(force=force)
    human = os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1"
    if human:
        print(
            f"I packed {report['packed_ok']}/{report['fetchable_books']} scripture volumes to .H7. "
            f"Catalog lists {report['catalog_bible_entries']} denominations/traditions."
        )
    else:
        for row in report.get("results") or []:
            mark = "OK" if row.get("ok") else "SKIP"
            err = f" — {row.get('error')}" if row.get("error") else ""
            print(f"  [{mark}] {row.get('id')}{err}")
    print(f"METRIC bible_catalog={report['catalog_bible_entries']}")
    print(f"METRIC bible_packed={report['packed_ok']}")
    print(f"METRIC bible_fetchable={report['fetchable_books']}")
    print("OK bible-ingest" if report.get("ok") else "FAIL bible-ingest")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())