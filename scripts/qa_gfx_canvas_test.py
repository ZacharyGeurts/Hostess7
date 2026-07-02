#!/usr/bin/env pythong
"""QA: Graphics canvas — lossless pixels + PNG present."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_gfx_canvas import FRAME_PNG, open_canvas  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    c = open_canvas(320, 180)
    c.fill(10, 12, 18)
    c.pixel(50, 50, 255, 128, 0)
    c.rect(10, 10, 100, 40, 0, 120, 200)
    c.text(20, 60, "Hostess 7", (230, 235, 245), size=16)
    st = c.present(label="qa")
    if not FRAME_PNG.is_file():
        return fail("frame.png missing")
    if FRAME_PNG.stat().st_size < 100:
        return fail("frame.png too small")
    if int(st.get("version", 0)) < 1:
        return fail("version not bumped")
    print(f"OK gfx_canvas {st.get('width')}x{st.get('height')} png={FRAME_PNG.stat().st_size}")
    print("METRIC qa_gfx_canvas=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())