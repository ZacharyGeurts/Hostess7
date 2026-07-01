#!/usr/bin/env pythong
"""Code catalog — ISA opcodes + programming languages merged for infinite ingest."""
from __future__ import annotations

from field_isa_data import CHIP_PLATFORMS, chip_count, iter_isa_entries, opcode_count  # noqa: E402
from field_langs_data import iter_lang_entries, lang_count  # noqa: E402


def catalog_count() -> int:
    return chip_count() + lang_count()


def iter_all_entries() -> list[dict]:
    rows: list[dict] = []
    rows.extend(iter_isa_entries())
    rows.extend(iter_lang_entries())
    return rows


def catalog_stats() -> dict:
    isa = iter_isa_entries()
    langs = iter_lang_entries()
    chips = {r["chip"] for r in isa if r.get("chip")}
    return {
        "chips": len(CHIP_PLATFORMS),
        "chip_ids": len(chips),
        "opcodes": len(isa),
        "languages": len(langs),
        "total": len(isa) + len(langs),
    }