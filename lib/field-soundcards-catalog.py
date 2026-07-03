#!/usr/bin/env pythong
"""Soundcards catalog — history, CHIPS cross-ref, live ALSA merge."""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fcc", _LIB / "field-chamber-core.py")
fcc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(fcc)

INSTALL = fcc.INSTALL
CATALOG = INSTALL / "data" / "field-soundcards-catalog.json"
CHIPS = INSTALL / "data" / "field-chips-catalog-curation.json"

_AUDIO_CHIP_RE = re.compile(
    r"audio|sound|DAC|SID|Paula|SPC|YM\d|Ensoniq|Sound Blaster|AC.?97|Azalia|codec",
    re.I,
)


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _chips_audio() -> list[dict[str, Any]]:
    doc = _load(CHIPS, {})
    rows: list[dict[str, Any]] = []
    raw = doc.get("entries") or doc.get("chips") or {}
    items = raw.items() if isinstance(raw, dict) else enumerate(raw if isinstance(raw, list) else [])
    for chip_id, entry in items:
        if not isinstance(entry, dict):
            continue
        note = str(entry.get("curator_note") or entry.get("note") or "")
        name = str(entry.get("name") or chip_id or "")
        if not _AUDIO_CHIP_RE.search(note + " " + name + " " + str(chip_id)):
            continue
        rows.append({
            "chip_id": chip_id,
            "name": name,
            "note": note,
            "systems": entry.get("systems") or [],
            "section": "soundcards",
        })
    return rows


def _live_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for row in fcc.alsa_cards() or []:
        cid = str(row.get("id") or "")
        desc = str(row.get("description") or row.get("name") or f"Card {cid}")
        cards.append({
            "id": f"alsa-{cid}",
            "name": desc,
            "era": "live",
            "bus": "ALSA",
            "channels": 8,
            "quality": "high",
            "chips": [],
            "systems": ["This machine"],
            "emulation": "surround_8ch",
            "live": True,
            "alsa_id": cid,
        })
    return cards


def catalog(*, include_live: bool = True) -> dict[str, Any]:
    seed = _load(CATALOG, {})
    cards = list(seed.get("cards") or [])
    seen = {c.get("id") for c in cards if c.get("id")}
    if include_live:
        for live in _live_cards():
            if live["id"] not in seen:
                cards.insert(0, live)
                seen.add(live["id"])
    chips = _chips_audio()
    return {
        "ok": True,
        "schema": "field-soundcards-catalog/v1",
        "title": seed.get("title"),
        "section": seed.get("chips_catalog_section", "soundcards"),
        "default_profile": seed.get("default_profile", "surround_8ch"),
        "default_quality": seed.get("default_quality", "high"),
        "card_count": len(cards),
        "cards": cards,
        "chips": chips,
        "chip_count": len(chips),
    }


def card_by_id(card_id: str) -> dict[str, Any] | None:
    for row in catalog().get("cards") or []:
        if row.get("id") == card_id:
            return row
    return None


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "catalog"):
        print(json.dumps(catalog(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-soundcards-catalog.py [json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())