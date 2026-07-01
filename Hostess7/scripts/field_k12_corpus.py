#!/usr/bin/env pythong
"""K-12 textbook corpus — search and synthesis for Hostess 7 education queries."""
from __future__ import annotations

import json
import re
from pathlib import Path

from field_k12_catalog import catalog_count  # noqa: E402
from field_k12_infinite import INDEX, infinite_status, ingest_catalog, search_infinite  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "k12" / "corpus.json"
K12_CORPUS_VERSION = 1


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    if not INDEX.is_file():
        try:
            ingest_catalog(vacuum=False)
        except OSError:
            pass
    st = infinite_status()
    doc = {
        "version": K12_CORPUS_VERSION,
        "textbook_count": st.get("textbook_count", catalog_count()),
        "fetched_count": st.get("fetched_count", 0),
        "by_grade": st.get("by_grade", {}),
        "by_subject": st.get("by_subject", {}),
        "truth_filter": True,
        "disclaimer": (
            "K-12 corpus uses OER and public-domain textbooks only — OpenStax, Wikibooks, Gutenberg. "
            "Truth-filtered on ingest (94% noise / 6% truth). Not a school curriculum authority."
        ),
    }
    CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return CORPUS_CACHE


def synthesize_k12_paragraphs(query: str) -> list[str]:
    paras: list[str] = []
    try:
        from field_library import synthesize_library_reading  # noqa: WPS433

        paras = synthesize_library_reading(query, line_window=10)
    except ImportError:
        pass
    ensure_corpus()
    hits = search_infinite(query, limit=5)
    st = infinite_status()
    if not paras:
        paras = []
    paras.append(
        f"K-12 textbook drive — {st.get('textbook_count', 0)} catalogued, "
        f"{st.get('fetched_count', 0)} truth-filtered fetches, "
        f"grades K-12 across {len(st.get('by_subject') or {})} subjects."
    )
    paras.append(
        "H7 library: `./Hostess7.sh library-build` · read `.H7` lossless books in `cache/fieldstorage/textbooks/`. "
        "Sources: OpenStax (CC BY), Wikibooks (CC BY-SA), Project Gutenberg (public domain)."
    )
    if not hits:
        hits = search_infinite("math science history english", limit=4)
    for h in hits:
        title = h.get("full_name") or h.get("title", "Textbook")
        grade = h.get("grade_band", "?")
        subj = h.get("subject", "?")
        truth = h.get("truth_score")
        body = str(h.get("body", ""))[:1200]
        ts = f" · truth={truth}%" if truth else ""
        paras.append(f"[{grade} {subj}] {title}{ts}: {body}")
    return paras


def corpus_stats() -> dict:
    ensure_corpus()
    return infinite_status()