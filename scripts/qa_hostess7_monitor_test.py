#!/usr/bin/env pythong
"""QA: Hostess7 monitor data collector."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_monitor_data import collect_snapshot, format_snapshot_text  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    snap = collect_snapshot()
    if not snap.events and snap.thoughts_n < 1:
        print("WARN monitor no events yet")
    if len(snap.area_glow) < 5:
        return fail("area_glow too small")
    text = format_snapshot_text(snap)
    if "Hostess7 Monitor" not in text:
        return fail("format missing header")
    print(f"OK monitor events={len(snap.events)} brain={snap.brain_mb:.1f}MiB agents={snap.agents_running}")
    print("METRIC qa_hostess7_monitor=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())