#!/usr/bin/env pythong
"""QA: Supreme Court Judge — SCOTUS corpus, bench synthesis, routing."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_legal_corpus import ensure_corpus, search_court_lexicon, search_legal  # noqa: E402
from field_legal_domains import LEGAL_CORPUS_VERSION  # noqa: E402
from field_legal_scotus import (  # noqa: E402
    is_judge_query,
    search_scotus,
    synthesize_judge_paragraphs,
)


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()

    if LEGAL_CORPUS_VERSION < 6:
        return fail("LEGAL_CORPUS_VERSION should be >= 6")

    if not is_judge_query("Should the Supreme Court grant certiorari on First Amendment strict scrutiny?"):
        return fail("judge query detection miss")

    if is_judge_query("What is a breach of contract?"):
        return fail("false positive on contract query")

    scotus = search_scotus("certiorari rule of four", limit=3)
    if not scotus:
        return fail("search_scotus empty")

    legal = search_legal("supreme court scotus", limit=2)
    if not any(d.get("id") == "supreme_court" for d in legal):
        return fail("supreme_court domain miss")

    cert = search_court_lexicon("writ of certiorari", limit=1)
    if not cert or "certiorari" not in str(cert[0].get("term", "")).lower():
        return fail("certiorari lexicon miss")

    paras = synthesize_judge_paragraphs("Miranda Fifth Amendment custodial interrogation")
    blob = " ".join(paras).lower()
    if "miranda" not in blob:
        return fail("Miranda case not in bench synthesis")
    if "educational" not in blob and "not legal advice" not in blob:
        return fail("bench disclaimer missing")

    from field_superintelligence import _classify_intent  # noqa: E402

    if _classify_intent("How would SCOTUS apply strict scrutiny?") != "judge":
        return fail("intent classify judge miss")

    print(f"METRIC scotus_domains={len(scotus)}")
    print(f"METRIC judge_paras={len(paras)}")
    print("OK scotus-judge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())