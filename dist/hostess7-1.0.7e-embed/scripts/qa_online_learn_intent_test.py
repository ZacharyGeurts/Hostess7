#!/usr/bin/env pythong
"""QA: go-online intent must not classify as Go programming language."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_agents7 import is_online_learn_query  # noqa: E402
from field_superintelligence import _classify_intent  # noqa: E402


def main() -> int:
    q = (
        "go online and make yourself smarter at conversation and whatever else you feel like learning, "
        "then come back and tell me you want to talk some more"
    )
    if _classify_intent(q) != "online_learn":
        print(f"FAIL intent={_classify_intent(q)} expected online_learn", file=sys.stderr)
        return 1
    if not is_online_learn_query(q):
        print("FAIL is_online_learn_query false", file=sys.stderr)
        return 1
    if _classify_intent("what is go used for in programming") != "code":
        print("FAIL go language query should still be code", file=sys.stderr)
        return 1
    print("OK online_learn_intent")
    print("METRIC qa_online_learn_intent=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())