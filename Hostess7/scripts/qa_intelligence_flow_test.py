#!/usr/bin/env pythong
"""QA: Intelligence flow doctrine + tools docs + superintel intent."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_intelligence_flow import (  # noqa: E402
    BRIEF,
    CORPUS_VERSION,
    FLOW_LAYERS,
    ensure_corpus,
    search_flow,
    seed_doctrine,
    synthesize_flow_paragraphs,
)
from field_superintelligence import _classify_intent, is_superintel_query  # noqa: E402
from field_tools_docs import INDEX, ensure_index, index_stats, search_tools  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    ensure_index()
    seed_doctrine()

    if len(FLOW_LAYERS) < 10:
        return fail(f"expected 10+ flow layers, got {len(FLOW_LAYERS)}")

    if not BRIEF.is_file():
        return fail("intelligence_flow_brief.json missing after seed")

    flow_hits = search_flow("full intelligence flow superintelligence pipeline", limit=8)
    if len(flow_hits) < 5:
        return fail(f"flow search too thin: {len(flow_hits)}")

    if flow_hits[0].get("id") not in ("signal_input", "super_intelligence_self"):
        # broad query should include early or apex stages
        ids = [h.get("id") for h in flow_hits]
        if "super_intelligence_self" not in ids and "signal_input" not in ids:
            return fail(f"flow search missing apex/signal: {ids}")

    restart = search_flow("how do you update your own code and restart", limit=4)
    restart_ids = {h.get("id") for h in restart}
    if not restart_ids & {"self_update_code", "self_restart"}:
        return fail(f"self-update/restart layers not found: {restart_ids}")

    paras = synthesize_flow_paragraphs("walk me through entire intelligence flow")
    if len(paras) < 5:
        return fail("flow synthesis too thin")

    st = index_stats()
    if st["total"] < 25:
        return fail(f"tools index too small: {st['total']}")

    tools = search_tools("self-update zac reach qa", limit=6)
    tool_ids = {t.get("id") for t in tools}
    if not tool_ids & {"self_update", "zac", "reach", "qa_turing"}:
        return fail(f"tools search miss: {tool_ids}")

    q = "teach me the entire flow of intelligence up to super intelligence"
    if not is_superintel_query(q):
        return fail("is_superintel_query false for doctrine question")
    if _classify_intent(q) != "superintel":
        return fail(f"intent={_classify_intent(q)} expected superintel")

    if _classify_intent("what tools documentation do you need") != "tools_docs":
        return fail("tools_docs intent miss")

    corpus = ROOT / "cache/fieldstorage/brain/superintel/intelligence_flow_corpus.json"
    data = json.loads(corpus.read_text(encoding="utf-8"))
    if int(data.get("version", 0)) < CORPUS_VERSION:
        return fail("flow corpus version stale")

    if not INDEX.is_file():
        return fail("tools_docs_index.json missing")

    print("OK intelligence_flow doctrine + tools docs + intent")
    print(f"METRIC flow_layers={len(FLOW_LAYERS)}")
    print(f"METRIC tools_docs_entries={st['total']}")
    print("METRIC qa_intelligence_flow=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())