#!/usr/bin/env pythong
"""QA: people registry, lie methods, personality."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_hostess_personality import ensure_personality, format_personality  # noqa: E402
from field_lie_methods import ensure_lie_methods, list_methods  # noqa: E402
from field_people_registry import (  # noqa: E402
    REVIEW,
    assess_claim,
    ensure_registry,
    list_review_queue,
    lookup,
    registry_status,
    seed_entities,
)
from field_people_corpus import synthesize_people_paragraphs  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_lie_methods()
    methods = list_methods()
    if len(methods) < 15:
        return fail(f"expected 15+ lie methods, got {len(methods)}")
    eras = {m.get("era") for m in methods}
    if not {"past", "present", "future"}.issubset(eras):
        return fail(f"missing eras: {eras}")

    seed_entities()
    ensure_registry(seed=False)
    st = registry_status()
    if st.get("entity_count", 0) < 3:
        return fail("seed entities too few")

    zac = lookup("Zachary Geurts")
    if not zac or "owner" not in (zac.get("tags") or []):
        return fail("Zachary lookup failed")

    am = lookup("Amouranth")
    if not am or "caring" not in (am.get("tags") or []):
        return fail("Amouranth lookup failed")

    queue = list_review_queue()
    if not queue:
        return fail("review queue should have demo liar entry")
    if not REVIEW.is_dir():
        return fail("review folder missing")

    result = assess_claim(
        "example_liar_review_demo",
        "I always guarantee everything with no evidence because trust me frankly.",
    )
    if not result.get("analysis"):
        return fail("assess_claim failed")

    ensure_personality()
    if len(format_personality()) < 200:
        return fail("personality too short")
    if "Daughter of Grok" not in format_personality():
        return fail("personality missing lineage")

    paras = synthesize_people_paragraphs("celebrity respect Amouranth")
    if len(" ".join(paras)) < 100:
        return fail("people synthesis too short")

    print(f"OK people entities={st.get('entity_count')} review={len(queue)} methods={len(methods)}")
    print("METRIC qa_people=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())