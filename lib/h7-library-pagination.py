#!/usr/bin/env pythong
"""Canonical library pagination — stable page numbers for reader, truth, lies index."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PAGE_CHARS = int(os.environ.get("NEXUS_H7_PAGE_CHARS", "3200"))
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])|(?<=[.!?])\s*$")
BIGGEST_LIES_HDR = "## Deception Index (Ironclad — Autonomous Warfare)"


def paginate_text(text: str, *, page_chars: int | None = None) -> list[str]:
    limit = page_chars or PAGE_CHARS
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return [""]
    pages: list[str] = []
    start = 0
    while start < len(text):
        chunk = text[start : start + limit]
        if start + limit < len(text):
            brk = max(chunk.rfind("\n\n"), chunk.rfind("\n"), chunk.rfind(". "))
            if brk > limit // 3:
                chunk = chunk[: brk + 1]
        pages.append(chunk.strip())
        start += max(len(chunk), 1)
    return pages or [""]


def page_map(text: str, *, page_chars: int | None = None) -> dict[str, Any]:
    """Stable page offsets — same logic as h7-library-bridge read_page."""
    limit = page_chars or PAGE_CHARS
    pages = paginate_text(text, page_chars=limit)
    rows: list[dict[str, Any]] = []
    offset = 0
    body = (text or "").replace("\r\n", "\n").strip()
    for i, page_text in enumerate(pages, start=1):
        start = body.find(page_text, offset) if page_text else offset
        if start < 0:
            start = offset
        end = start + len(page_text)
        rows.append({
            "page": i,
            "char_start": start,
            "char_end": end,
            "char_count": len(page_text),
            "page_sha": hashlib.sha256(page_text.encode("utf-8")).hexdigest()[:16],
        })
        offset = end
    return {
        "schema": "h7-library-page-map/v1",
        "page_chars": limit,
        "page_count": len(rows),
        "char_count": len(body),
        "pages": rows,
    }


def split_sentences(text: str) -> list[str]:
    text = (text or "").replace("\r\n", "\n").strip()
    if not text:
        return []
    parts = SENTENCE_RE.split(text)
    out: list[str] = []
    for p in parts:
        s = p.strip()
        if len(s) >= 8:
            out.append(s)
    if not out and text:
        out = [text[:500]]
    return out


def sentence_locations(text: str, *, page_chars: int | None = None) -> list[dict[str, Any]]:
    """Map each sentence to canonical page number and offset."""
    body = (text or "").replace("\r\n", "\n").strip()
    pmap = page_map(body, page_chars=page_chars)
    sentences = split_sentences(body)
    rows: list[dict[str, Any]] = []
    search_from = 0
    for idx, sent in enumerate(sentences):
        pos = body.find(sent, search_from)
        if pos < 0:
            pos = search_from
        page_num = locate_char(body, pos, page_chars=pmap["page_chars"])
        page_row = next((r for r in pmap["pages"] if r["page"] == page_num), None)
        page_start = int(page_row["char_start"]) if page_row else 0
        sent_on_page = len(split_sentences(body[page_start:pos])) + 1
        rows.append({
            "index": idx,
            "page": page_num,
            "sentence_on_page": sent_on_page,
            "char_start": pos,
            "char_end": pos + len(sent),
            "text": sent[:300],
        })
        search_from = pos + max(len(sent), 1)
    return rows


def locate_char(text: str, char_pos: int, *, page_chars: int | None = None) -> int:
    pmap = page_map(text, page_chars=page_chars)
    for row in pmap["pages"]:
        if row["char_start"] <= char_pos < row["char_end"]:
            return int(row["page"])
    return max(1, pmap["page_count"])


def locate_sentence(text: str, sentence_index: int, *, page_chars: int | None = None) -> dict[str, Any]:
    sents = sentence_locations(text, page_chars=page_chars)
    if sentence_index < 0 or sentence_index >= len(sents):
        return {"ok": False, "error": "sentence_index_out_of_range", "sentence_count": len(sents)}
    hit = sents[sentence_index]
    return {"ok": True, **hit}


def appendix_page(text: str, *, header: str = BIGGEST_LIES_HDR, page_chars: int | None = None) -> int | None:
    body = (text or "").replace("\r\n", "\n")
    pos = body.find(header)
    if pos < 0:
        return None
    return locate_char(body, pos, page_chars=page_chars)


def panel_json(book_id: str, text: str, *, page_chars: int | None = None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    pmap = page_map(text, page_chars=page_chars)
    out = {
        "ok": True,
        "schema": "h7-library-pagination-panel/v1",
        "book_id": book_id,
        **pmap,
        "appendix_page": appendix_page(text, page_chars=pmap["page_chars"]),
        "sentence_count": len(split_sentences(text)),
    }
    if extra:
        out.update(extra)
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "help").strip().lower()
    if cmd == "map" and len(sys.argv) >= 3:
        book_id = sys.argv[2]
        dewey = INSTALL / "lib" / "field-dewey-library.py"
        if not dewey.is_file():
            print(json.dumps({"ok": False, "error": "dewey_lib_missing"}))
            return 1
        import importlib.util
        spec = importlib.util.spec_from_file_location("dewey_pg", dewey)
        if not spec or not spec.loader:
            print(json.dumps({"ok": False, "error": "import_failed"}))
            return 1
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        try:
            text, header, _ = mod.read_h7c_text(book_id)
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc), "book_id": book_id}))
            return 1
        chars = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].isdigit() else PAGE_CHARS
        print(json.dumps(panel_json(book_id, text, page_chars=chars, extra={"title": (header or {}).get("title")}), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: h7-library-pagination.py map <book_id> [page_chars]"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())