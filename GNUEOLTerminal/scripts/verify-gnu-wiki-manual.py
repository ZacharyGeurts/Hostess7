#!/usr/bin/env python3
"""Verify GNU EOL Terminal full wiki manual — md source + built HTML + index links."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
DOCS_WIKI = ROOT / "docs" / "wiki"
MANUAL_MD = WIKI / "eol-terminal-full-manual.md"
MANUAL_HTML = DOCS_WIKI / "eol-terminal-full-manual.html"
INDEX_HTML = DOCS_WIKI / "index.html"
MIN_WORDS = 1950
REQUIRED_SECTIONS = tuple(str(i) for i in range(1, 18))
FT_CHAPTERS = tuple(f"ft-ch{n:02d}" for n in range(1, 23))


def _fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def verify(*, strict: bool = True) -> dict:
    errors: list[str] = []
    checks: list[dict] = []

    def ok(name: str, detail: str = "") -> None:
        checks.append({"check": name, "ok": True, "detail": detail})

    if not MANUAL_MD.is_file():
        _fail(f"missing source: {MANUAL_MD}", errors)
    else:
        text = MANUAL_MD.read_text(encoding="utf-8")
        words = len(text.split())
        ok("manual_md_exists", f"{words} words")
        if words < MIN_WORDS:
            _fail(f"manual too short: {words} words (need ≥{MIN_WORDS})", errors)
        for sec in REQUIRED_SECTIONS:
            if f"## {sec}." not in text and f"## {sec} " not in text:
                _fail(f"missing section ## {sec}. in full manual", errors)
            else:
                ok(f"section_{sec}", "")
        for needle in (
            "legacy-connect-primary",
            "field-legacy-connect",
            "Hostess7 stack update",
            "verify-gnu-wiki-manual",
            "Dreamcast",
        ):
            if needle.lower() not in text.lower():
                _fail(f"manual missing required topic: {needle}", errors)
            else:
                ok(f"topic_{needle}", "")

    if not MANUAL_HTML.is_file():
        _fail(f"missing built HTML: {MANUAL_HTML} — run build-site.py", errors)
    else:
        html = MANUAL_HTML.read_text(encoding="utf-8", errors="replace")
        ok("manual_html_exists", f"{len(html)} bytes")
        if "legacy-connect-primary" not in html and "Legacy open" not in html:
            _fail("built HTML missing legacy-connect / Legacy open section", errors)
        if len(html) < 8000:
            _fail(f"built HTML suspiciously small: {len(html)} bytes", errors)

    if not INDEX_HTML.is_file():
        _fail(f"missing wiki index: {INDEX_HTML}", errors)
    else:
        idx = INDEX_HTML.read_text(encoding="utf-8", errors="replace")
        if "eol-terminal-full-manual" not in idx:
            _fail("wiki index does not link eol-terminal-full-manual", errors)
        else:
            ok("index_links_full_manual", "")

    ft_missing = []
    for slug in FT_CHAPTERS:
        if not list(WIKI.glob(f"{slug}-*.md")):
            ft_missing.append(slug)
    if ft_missing:
        _fail(f"missing Field Technology wiki chapters: {', '.join(ft_missing[:5])}", errors)
    else:
        ok("ft_chapters_22", "ft-ch01 … ft-ch22")

    wiki_html_count = len(list(DOCS_WIKI.glob("*.html"))) if DOCS_WIKI.is_dir() else 0
    if wiki_html_count < 30:
        _fail(f"wiki HTML count low: {wiki_html_count} (expected ≥30)", errors)
    else:
        ok("wiki_html_count", str(wiki_html_count))

    out = {
        "schema": "gnueol-wiki-verify/v1",
        "ok": len(errors) == 0,
        "checks": checks,
        "errors": errors,
        "manual_md": str(MANUAL_MD.relative_to(ROOT)),
        "manual_html": str(MANUAL_HTML.relative_to(ROOT)) if MANUAL_HTML.is_file() else None,
        "wiki_pages_html": wiki_html_count,
    }
    if strict and errors:
        out["hint"] = "Run: python3 scripts/forge-gnu-wiki-manual.py && python3 scripts/build-site.py"
    return out


def main() -> int:
    doc = verify(strict=True)
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())