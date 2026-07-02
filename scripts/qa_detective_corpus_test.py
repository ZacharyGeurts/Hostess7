#!/usr/bin/env pythong
"""QA: Detective & lie-detector corpus + truth analysis."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_brain_core import ensure_brain_layout, route_query, set_active_workspace  # noqa: E402
from field_detective_corpus import (  # noqa: E402
    DETECTIVE_CORPUS_VERSION,
    analyze_truth,
    corpus_stats,
    ensure_corpus,
    ironclad_slice,
    search_detective,
    synthesize_detective_paragraphs,
)


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    ensure_brain_layout()
    stats = corpus_stats()

    if stats["domains"] < 9:
        return fail(f"expected 9+ detective domains (incl. ironclad), got {stats['domains']}")
    if stats["version"] < DETECTIVE_CORPUS_VERSION:
        return fail("detective corpus version stale")

    lie = search_detective("lie detector deception polygraph", limit=3)
    if not lie or lie[0].get("id") not in (
        "lie_detection_verbal", "lie_detection_nonverbal", "hostess_lie_detector",
    ):
        return fail(f"lie detection search wrong: {[r.get('id') for r in lie]}")

    forensic = search_detective("forensic fingerprint dna digital", limit=2)
    if not any(r.get("id") in ("forensic_science", "digital_investigation") for r in forensic):
        return fail("forensic search miss")

    analysis = analyze_truth(
        "This release is definitely 100% guaranteed perfect with no evidence",
        local_evidence=0,
        qa_green=False,
    )
    if analysis["deception_risk"] not in ("medium", "high"):
        return fail(f"expected high deception risk for absolute claim, got {analysis['deception_risk']}")
    if not analysis.get("inconsistency_flags"):
        return fail("expected inconsistency flags on absolute claim")

    ic = ironclad_slice()
    if "ironclad_sealed" not in ic:
        return fail("ironclad_slice missing ironclad_sealed")
    if "verdict" not in ic:
        return fail("ironclad_slice missing verdict")

    iron_hits = search_detective("ironclad sealed canonical witness", limit=2)
    if not iron_hits or iron_hits[0].get("id") != "ironclad_truth":
        return fail(f"ironclad search miss: {[r.get('id') for r in iron_hits]}")

    good = analyze_truth(
        "grep evidence in Pipeline.hpp FieldHostess7 tick documented in QA",
        local_evidence=3,
        qa_green=True,
        corroboration_channels=3,
        ironclad=ic,
    )
    if float(good["truth_score"]) < 50:
        return fail(f"corroborated claim should score higher, got {good['truth_score']}")
    if "ironclad" not in good:
        return fail("analyze_truth missing ironclad block")

    paras = synthesize_detective_paragraphs("detective corroboration 94 percent noise")
    if len(paras) < 2:
        return fail("synthesis too short")

    set_active_workspace("detective")
    route = route_query("lie detector forensic corroboration", "detective")
    if not route.cross_transfer:
        return fail("detective workspace should trigger cross_transfer")
    if route.primary_area != "insula":
        return fail(f"expected insula area, got {route.primary_area}")

    set_active_workspace("default")
    print("OK detective lie-detector corpus + truth analysis")
    print(f"METRIC detective_domains={stats['domains']}")
    print(f"METRIC qa_detective_corpus=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())