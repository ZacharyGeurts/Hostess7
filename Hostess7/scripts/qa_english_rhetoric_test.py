#!/usr/bin/env pythong
"""QA: English rhetoric — metaphors, thesaurus, sentences, flow."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_english_lexicon import corpus_stats, ensure_corpus, synthesize_english_paragraphs  # noqa: E402
from field_english_rhetoric import (  # noqa: E402
    is_rhetoric_query,
    rhetoric_stats,
    search_rhetoric,
    synthesize_rhetoric_paragraphs,
)
from field_english_thesaurus import lookup_thesaurus, search_thesaurus, synthesize_thesaurus_paragraphs  # noqa: E402
from field_superintelligence import _classify_intent  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    stats = corpus_stats()
    rh = rhetoric_stats()

    if stats.get("version", 0) < 2:
        return fail(f"english corpus version should be >= 2, got {stats.get('version')}")
    if rh.get("domains", 0) < 10:
        return fail(f"expected 10+ rhetoric domains, got {rh.get('domains')}")
    if rh.get("thesaurus_clusters", 0) < 25:
        return fail(f"expected 25+ thesaurus clusters, got {rh.get('thesaurus_clusters')}")

    if not is_rhetoric_query("Explain metaphor and natural language flow"):
        return fail("rhetoric query detection miss")

    meta = search_rhetoric("metaphor simile figurative", limit=2)
    if not meta or "metaphor" not in str(meta[0].get("title", "")).lower():
        return fail("metaphor rhetoric search miss")

    happy = lookup_thesaurus("happy")
    if not happy or len(happy.get("synonyms", ())) < 3:
        return fail("thesaurus lookup happy miss")

    th = synthesize_thesaurus_paragraphs("synonym for happy")
    if "joyful" not in " ".join(th).lower():
        return fail("thesaurus synthesis miss synonyms")

    flow = synthesize_rhetoric_paragraphs("natural language flow transitions cohesion")
    text = " ".join(flow).lower()
    if "flow" not in text or "transition" not in text:
        return fail("flow rhetoric synthesis miss")

    sent = synthesize_english_paragraphs("compound and complex sentence structures")
    if "compound" not in " ".join(sent).lower():
        return fail("sentence structure synthesis miss")

    if _classify_intent("thesaurus synonym for eloquent") != "english":
        return fail("intent classify english rhetoric miss")

    print(f"OK english rhetoric domains={rh.get('domains')} thesaurus={rh.get('thesaurus_clusters')}")
    print(f"METRIC english_rhetoric_domains={rh.get('domains')}")
    print(f"METRIC english_thesaurus_clusters={rh.get('thesaurus_clusters')}")
    print("METRIC qa_english_rhetoric=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())