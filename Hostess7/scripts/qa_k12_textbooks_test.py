#!/usr/bin/env pythong
"""QA: K-12 textbook catalog, truth filter, infinite drive."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_k12_catalog import catalog_count, textbooks_with_fetch_url  # noqa: E402
from field_k12_infinite import ingest_catalog, infinite_status, search_infinite  # noqa: E402
from field_k12_truth import score_k12_text  # noqa: E402
from field_k12_corpus import synthesize_k12_paragraphs  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    if catalog_count() < 40:
        return fail(f"expected 40+ textbooks, got {catalog_count()}")
    if len(textbooks_with_fetch_url()) < 40:
        return fail("fetch URLs missing")

    sample = (
        "Chapter 1 Introduction to Algebra. Students learn equations and problem solving across "
        "the curriculum. Lesson exercises include definitions and theorems for grade 9. "
        "Each section teaches variables, expressions, and functions with experiments in reasoning. "
        "Reading and writing mathematics builds science literacy. History of algebra informs modern "
        "government statistics and geography data. Biology and chemistry use the same equation tools. "
        "Teachers assign problems daily; learners practice until mastery. "
    ) * 3
    v = score_k12_text(sample, title="OpenStax Algebra")
    if not v.get("accepted"):
        return fail(f"educational sample should pass truth filter: {v}")
    spam = "cookie subscribe click here buy now"
    v2 = score_k12_text(spam)
    if v2.get("accepted"):
        return fail("spam should fail truth filter")

    m = ingest_catalog()
    if m.get("textbook_count", 0) < 40:
        return fail("ingest catalog too small")

    hits = search_infinite("biology openstax", limit=2)
    if not hits:
        return fail("biology search miss")

    paras = synthesize_k12_paragraphs("high school math textbook")
    if len(" ".join(paras)) < 100:
        return fail("k12 synthesis too short")

    st = infinite_status()
    print(f"OK k12 textbooks={st.get('textbook_count')} fetched={st.get('fetched_count')}")
    print(f"METRIC k12_textbooks={st.get('textbook_count')}")
    print("METRIC qa_k12=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())