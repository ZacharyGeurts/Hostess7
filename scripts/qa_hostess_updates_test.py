#!/usr/bin/env pythong
"""QA: Hostess 7 self-update advisory — truth filter + brain scan."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_hostess_updates import (  # noqa: E402
    ADVISORY,
    ADVISORY_VERSION,
    TRUTH_FLOOR_SCORE,
    TRUTH_RATIO,
    advise_updates,
    build_advisory,
    build_update_items,
)


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    adv = advise_updates()
    if adv.get("version", 0) < ADVISORY_VERSION:
        return fail("advisory version stale")
    if not ADVISORY.is_file():
        return fail("update_advisory.json not written")

    items = adv.get("updates") or []
    if len(items) < 3:
        return fail(f"expected 3+ update items, got {len(items)}")

    self_loop = next((i for i in items if i.get("id") == "self-advisory-loop"), None)
    if not self_loop:
        return fail("missing self-advisory-loop item")

    truth_extract = next((i for i in items if i.get("id") == "infinite-truth-extract"), None)
    if not truth_extract:
        return fail("missing infinite-truth-extract item")
    if "94" not in str(truth_extract.get("why", "")):
        return fail("truth philosophy not in infinite-truth-extract")

    for item in items:
        if item.get("id") == "self-advisory-loop":
            continue
        if float(item.get("truth_score", 0)) < TRUTH_FLOOR_SCORE:
            return fail(f"item below truth floor: {item.get('id')}")

    doc = json.loads(ADVISORY.read_text(encoding="utf-8"))
    if not doc.get("philosophy", {}).get("mantra"):
        return fail("philosophy mantra missing")

    raw_items = build_update_items(build_advisory().get("brain_snapshot"))
    if not raw_items:
        return fail("build_update_items empty")

    print("OK hostess self-update advisory")
    print(f"METRIC hostess_updates={len(items)}")
    print(f"METRIC hostess_truth_ratio={TRUTH_RATIO}")
    print(f"METRIC qa_hostess_updates=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())