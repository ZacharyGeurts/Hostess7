#!/usr/bin/env pythong
"""QA: Hostess 7 unified talk router + storage + graphics."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_storage_check import scan_storage  # noqa: E402
from field_vision_corpus import VISION_CORPUS_VERSION, ensure_corpus  # noqa: E402
from hostess7_graphics import graphics_for_query, tv_smpte_bars  # noqa: E402
from hostess7_talk import dispatch  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    import json
    vis = json.loads(
        (ROOT / "cache" / "fieldstorage" / "brain" / "vision" / "corpus.json").read_text()
    )
    if int(vis.get("version", 0)) < VISION_CORPUS_VERSION:
        return fail("vision corpus v3 required for TV/pixel")
    if vis.get("domain_count", 0) < 18:
        return fail(f"expected 18+ vision domains, got {vis.get('domain_count')}")

    rep = scan_storage()
    if "lossless_policy" not in rep:
        return fail("storage report missing lossless policy")

    bars = tv_smpte_bars(32, 4)
    if len(bars) < 5:
        return fail("TV bar graphics too short")

    gfx = graphics_for_query("tv pixel storage lossless", storage_report=rep)
    if len(gfx) < 3:
        return fail("graphics_for_query too short")

    help_r = dispatch("/help")
    if "one talk window" not in help_r.text.lower():
        return fail("help missing talk window")

    stor = dispatch("/storage", storage_cache=rep)
    if not stor.graphics:
        return fail("/storage should include graphics")
    if "lossless" not in stor.text.lower():
        return fail("/storage text missing lossless")

    gfx_r = dispatch("/gfx tv")
    if not gfx_r.graphics:
        return fail("/gfx tv should render graphics")

    print("OK hostess talk window + lossless storage + TV/pixel graphics")
    print(f"METRIC vision_domains={vis.get('domain_count')}")
    print(f"METRIC storage_bytes={rep.get('total_bytes', 0)}")
    print("METRIC qa_hostess_talk=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())