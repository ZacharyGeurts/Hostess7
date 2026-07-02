#!/usr/bin/env pythong
"""QA: Grok Imagine + live video corpus."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_imagine_corpus import (  # noqa: E402
    LIVE_VIDEO_ENTRIES,
    ensure_corpus,
    list_realtime_entries,
    recommend_live_backend,
    search_imagine,
)
from field_live_video import live_video_plan, present_talk_frame  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    if len(LIVE_VIDEO_ENTRIES) < 20:
        return fail(f"expected 20+ live video entries, got {len(LIVE_VIDEO_ENTRIES)}")

    rt = list_realtime_entries()
    if len(rt) < 10:
        return fail(f"expected 10+ realtime entries, got {len(rt)}")

    rec = recommend_live_backend()
    if not rec.get("primary"):
        return fail("recommend_live_backend empty")

    hits = search_imagine("real-time live video lip sync streaming")
    if not hits or not any(h.get("id") in ("faster_liveportrait", "liveportrait", "musetalk") for h in hits):
        return fail("realtime search miss")

    plan = live_video_plan()
    if "pipeline" not in plan or len(plan["pipeline"]) < 4:
        return fail("live video plan incomplete")

    frame = present_talk_frame("QA live video frame")
    if not frame or not frame.get("version"):
        return fail("talk frame present failed")

    print(f"OK imagine entries={len(LIVE_VIDEO_ENTRIES)} hits={len(hits)}")
    print("METRIC qa_imagine_corpus=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())