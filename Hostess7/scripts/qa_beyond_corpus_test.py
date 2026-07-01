#!/usr/bin/env pythong
"""QA: Beyond corpus — expert breadth, search, category routing."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_beyond_corpus import (  # noqa: E402
    CORPUS_VERSION,
    domain_stats,
    ensure_corpus,
    search_beyond,
    search_beyond_multi_category,
    synthesize_beyond_paragraphs,
)
from field_beyond_domains import BEYOND_CATEGORIES, BEYOND_DOMAINS  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    stats = domain_stats()

    if stats["total"] < 33:
        return fail(f"expected 33+ domains, got {stats['total']}")
    if stats["version"] < CORPUS_VERSION:
        return fail(f"corpus version stale: {stats['version']}")

    for cat in BEYOND_CATEGORIES:
        if stats["by_category"].get(cat, 0) < 1:
            return fail(f"missing category: {cat}")

    robotics = search_beyond("robotics kinematics SLAM", limit=3)
    if not robotics or robotics[0].get("id") != "robotics_automation":
        return fail(f"robotics search wrong: {[r.get('id') for r in robotics]}")

    finance = search_beyond("finance inflation monetary policy", limit=3)
    if not any(r.get("id") == "economics_finance" for r in finance):
        return fail("finance/economics search miss")

    broad = search_beyond_multi_category("science technology economics overview")
    cats_hit = {str(d.get("category")) for d in broad}
    if len(cats_hit) < 2:
        return fail(f"multi-category too narrow: {cats_hit}")

    paras = synthesize_beyond_paragraphs("robotics expert automation")
    if len(paras) < 2:
        return fail("synthesis too thin")

    corpus = ROOT / "cache" / "fieldstorage" / "brain" / "beyond" / "corpus.json"
    data = json.loads(corpus.read_text(encoding="utf-8"))
    if len(data.get("domains", [])) != len(BEYOND_DOMAINS):
        return fail("cached domain count mismatch")

    print("OK beyond corpus expert breadth + search + synthesis")
    print(f"METRIC beyond_domains={stats['total']}")
    print(f"METRIC beyond_version={stats['version']}")
    print(f"METRIC beyond_categories={len(BEYOND_CATEGORIES)}")
    print("METRIC qa_beyond_corpus=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())