#!/usr/bin/env pythong
"""One-line OCR chamber binding for Hostess 7 modules."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def bind(
    chamber_id: str,
    *,
    install: Path,
    state: Path,
    ledger: Path | None = None,
) -> dict[str, Any]:
    lib = install / "lib"
    feed_py = lib / "hostess7-ocr-feed.py"
    spec = importlib.util.spec_from_file_location("hostess7_ocr_feed", feed_py)
    if not spec or not spec.loader:
        raise ImportError("hostess7-ocr-feed.py missing")
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    return feed.bind_chamber_ocr(
        chamber_id,
        install=install,
        state=state,
        doctrine_path=install / "data" / f"hostess7-{chamber_id}-ocr-doctrine.json",
        corpus_path=state / f"hostess7-{chamber_id}-ocr-corpus.json",
        train_path=state / f"hostess7-{chamber_id}-ocr-train.json",
        ocr_ledger_path=state / f"hostess7-{chamber_id}-ocr-ledger.jsonl",
        main_ledger_path=ledger,
    )