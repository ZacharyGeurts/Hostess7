#!/usr/bin/env pythong
"""Fast QA: world knowledge + videogame DB + compression smoke."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_fly_codec import fly_pack, fly_unpack  # noqa: E402
from field_videogame_db import ensure_db, search_games, CONSOLES  # noqa: E402
from field_world_catalog import ALL_WORLD_ENTRIES, world_count  # noqa: E402
from field_world_corpus import ensure_corpus, search_world  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    if world_count() < 40:
        return fail(f"expected 40+ world entries, got {world_count()}")

    ensure_corpus()
    ensure_db()

    if len(CONSOLES) < 25:
        return fail(f"expected 25+ consoles, got {len(CONSOLES)}")

    hits = search_world("bible federal law botany")
    if not hits:
        return fail("world search empty")

    vg = search_games("mario zelda nes")
    if not vg:
        return fail("videogame search empty")

    sample = '{"lossless":true,"world":3}'
    if fly_unpack(fly_pack(sample.encode())).decode() != sample:
        return fail("FLD1 smoke failed")

    print(f"OK world_fast entries={len(ALL_WORLD_ENTRIES)} consoles={len(CONSOLES)}")
    print("METRIC qa_world_fast=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())