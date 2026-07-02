#!/usr/bin/env pythong
"""QA: Medical corpus + infinite papers drive."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_medical_corpus import (  # noqa: E402
    MEDICAL_CORPUS_VERSION,
    corpus_stats,
    ensure_corpus,
    search_medical,
    synthesize_medical_paragraphs,
)
from field_medical_papers_catalog import catalog_count  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    stats = corpus_stats()

    if stats["domains"] < 18:
        return fail(f"expected 18+ medical domains, got {stats['domains']}")
    if stats["version"] < MEDICAL_CORPUS_VERSION:
        return fail("medical corpus version stale")
    if stats.get("infinite_indexed", 0) < catalog_count():
        return fail(
            f"infinite drive under-seeded: {stats.get('infinite_indexed')} < {catalog_count()}"
        )

    emergency = search_medical("chest pain heart attack emergency", limit=3)
    if not any(r.get("id") == "emergency" or "emergency" in str(r.get("title", "")).lower() for r in emergency):
        return fail("emergency search miss")

    paper = search_medical("ISIS-2 aspirin myocardial infarction trial", limit=3)
    if not any("isis" in str(r.get("full_name", r.get("title", ""))).lower() for r in paper):
        return fail("landmark paper search miss")

    guideline = search_medical("ADA diabetes guideline standards of care", limit=3)
    if not any("diabetes" in str(r.get("full_name", r.get("title", ""))).lower() for r in guideline):
        return fail("guideline search miss")

    paras = synthesize_medical_paragraphs("stroke thrombolysis neurology")
    if len(paras) < 2:
        return fail("medical synthesis too short")

    print("OK medical corpus + infinite papers")
    print(f"METRIC medical_domains={stats['domains']}")
    print(f"METRIC medical_infinite={stats.get('infinite_indexed', 0)}")
    print(f"METRIC medical_version={stats['version']}")
    print("METRIC qa_medical_corpus=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())