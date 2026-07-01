#!/usr/bin/env pythong
"""QA: redata truth filter — accept operator prose, reject noise."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_redata_truth import score_redata_text  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    good = (
        "Field operator reads Phi Thermo Flow at bindings eight through ten. "
        "grep THERMO stderr jsonl. Implemented label on oracle receipts. "
        "Philosophy beside grep — not a substitute for measurement." * 8
    )
    bad = "Subscribe now! Click here buy now cookie newsletter javascript required " * 5

    g = score_redata_text(good, source="Field_Primer/content/chapters", title="Field Technology")
    b = score_redata_text(bad, source="spam-fetch")

    if not g.get("accepted"):
        return fail(f"operator sample rejected: {g}")
    if b.get("accepted"):
        return fail(f"noise sample accepted: {b}")
    if g.get("truth_score", 0) <= b.get("truth_score", 0):
        return fail("operator should score higher than noise")

    print(f"OK redata truth good={g['truth_score']} bad={b['truth_score']}")
    print("METRIC redata_truth_qa=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())