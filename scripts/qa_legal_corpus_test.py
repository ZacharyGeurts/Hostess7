#!/usr/bin/env pythong
"""QA: Legal corpus — full formal terms, court lexicon, no truncation."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_legal_corpus import (  # noqa: E402
    FORMAL_EXPANSIONS,
    LEGAL_CORPUS_VERSION,
    _expand_formal,
    corpus_stats,
    ensure_corpus,
    search_court_lexicon,
    search_legal,
    synthesize_legal_paragraphs,
)
from field_legal_court_lexicon import COURT_LEXICON  # noqa: E402
from field_legal_domains import LEGAL_DOMAINS  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    stats = corpus_stats()

    if stats["domains"] < 20:
        return fail(f"expected 20+ domains, got {stats['domains']}")
    if stats["lexicon"] < 40:
        return fail(f"expected 40+ court terms, got {stats['lexicon']}")
    if not stats.get("formal_mode"):
        return fail("formal_mode not enabled")

    corpus = ROOT / "cache" / "fieldstorage" / "brain" / "legal" / "corpus.json"
    data = json.loads(corpus.read_text(encoding="utf-8"))
    if int(data.get("version", 0)) < LEGAL_CORPUS_VERSION:
        return fail("corpus version stale")

    motion = search_court_lexicon("Motion for Summary Judgment", limit=2)
    if not motion or "summary" not in str(motion[0].get("term", "")).lower():
        return fail("summary judgment lexicon miss")

    objection = search_court_lexicon("objection hearsay", limit=2)
    if not any("hearsay" in str(e.get("term", "")).lower() for e in objection):
        return fail("hearsay objection lexicon miss")

    expanded = _expand_formal("Under FRCP 12(b)(6) and FRE 802")
    if "Federal Rules of Civil Procedure" not in expanded:
        return fail("FRCP not expanded")
    if "Federal Rule of Evidence 802" not in expanded:
        return fail("FRE 802 not expanded")

    paras = synthesize_legal_paragraphs("objection hearsay trial court")
    full_text = " ".join(paras)
    if "Objection" not in full_text and "Hearsay" not in full_text:
        return fail("court synthesis missing formal objection language")
    if "… [truncated" in full_text:
        return fail("legal output still truncated")

    # No bare UCC without expansion in synthesis output
    if re_ucc_bare(full_text):
        return fail("bare UCC shorthand in output")

    lit = search_legal("Federal Rules of Evidence hearsay", limit=2)
    if not lit:
        return fail("evidence domain search miss")

    print("OK legal corpus formal court lexicon + domains")
    print(f"METRIC legal_domains={stats['domains']}")
    print(f"METRIC legal_lexicon={stats['lexicon']}")
    print(f"METRIC legal_version={stats['version']}")
    print("METRIC qa_legal_corpus=1")
    return 0


def re_ucc_bare(text: str) -> bool:
    import re
    return bool(re.search(r"\bUCC\b", text))


if __name__ == "__main__":
    raise SystemExit(main())