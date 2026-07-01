#!/usr/bin/env pythong
"""QA: Hostess7 reach — external roots, OS tools, self-update plan."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_paths import amouranthrtx_root, hostess7_root, reach_roots  # noqa: E402
from field_reach import (  # noqa: E402
    command_allowed,
    grep_reach,
    reach_snapshot,
    self_update_steps,
)


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    h = hostess7_root()
    if not h.is_dir():
        return fail("hostess7_root missing")

    roots = reach_roots()
    if not roots or roots[0]["role"] != "hostess7":
        return fail("reach_roots must include hostess7")

    snap = reach_snapshot()
    if not snap.get("tools"):
        return fail("no OS tools on PATH")

    rtx = amouranthrtx_root()
    if rtx is None:
        print("WARN amouranthrtx_root not found — reach partial")

    hits = grep_reach("Hostess7 SuperIntelligence field storage", limit=5)
    if not hits:
        return fail("grep_reach returned no hits")

    if not command_allowed("git status"):
        return fail("git status should be allowlisted")
    if command_allowed("sudo rm -rf /"):
        return fail("destructive command must be blocked")

    steps = self_update_steps(apply=False)
    if len(steps) < 2:
        return fail("self_update_steps too short")

    print(f"OK field reach roots={len(roots)} tools={len(snap['tools'])} hits={len(hits)} steps={len(steps)}")
    print("METRIC qa_field_reach=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())