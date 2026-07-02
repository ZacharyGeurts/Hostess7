#!/usr/bin/env pythong
"""QA: Hostess7 thirteen agents — Prime + 12 World Experts."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_agents7 import AGENT_COUNT, AGENTS7, fuse_agent_replies, run_single_agent  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    if len(AGENTS7) != 13 or AGENT_COUNT != 13:
        return fail(f"expected 13 agents, got {len(AGENTS7)}")

    names = {a["name"] for a in AGENTS7}
    required = {"Hostess-Prime", "Economist", "War-Chief", "Horizon"}
    if not required.issubset(names):
        return fail(f"missing core agent names: {required - names}")

    reply = run_single_agent(AGENTS7[0], "Who are you?", timeout=60)
    if not reply.text:
        return fail("Hostess-Prime returned empty")

    fused = fuse_agent_replies([reply], "Who are you?", human_facing=True)
    if not fused or "I'm here" not in fused and "Hostess" not in fused and len(fused) < 10:
        return fail("human fuse too empty")

    fused_full = fuse_agent_replies([reply], "Who are you?", human_facing=False)
    if "Thirteen" not in fused_full and "World Expert" not in fused_full:
        return fail("full fuse missing thirteen header")

    print(f"OK agents13 count={AGENT_COUNT} prime_ms={reply.elapsed_ms}")
    print("METRIC qa_field_agents13=1")
    print("METRIC qa_field_agents7=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())