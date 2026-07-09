#!/usr/bin/env pythong
"""Publish Hostess 7 library panel — book counts, Exploring Speaking lane, Ironclad + truth gate read path."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-library-doctrine.json"
SPEAKING_SHELF = INSTALL / "library" / "dewey" / "400-education"
OUT = STATE / "hostess7-library-panel.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _ironclad_posture() -> dict[str, Any]:
    path = INSTALL / "lib" / "ironclad-immediate.py"
    if not path.is_file():
        return {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("ic_imm", path)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "publish"):
            return mod.publish()
    except Exception:
        pass
    return _load(STATE / "ironclad-immediate.json", {})


def _count_speaking() -> dict[str, Any]:
    books = list(SPEAKING_SHELF.glob("exploring_speaking_*/book.json"))
    catalog = _load(INSTALL / "data" / "exploring-speaking-languages-catalog.json", {})
    langs = catalog.get("languages") or []
    types: dict[str, int] = {}
    for lang in langs:
        t = str(lang.get("type") or "unknown")
        types[t] = types.get(t, 0) + 1
    return {
        "on_disk": len(books),
        "catalog_target": len(langs),
        "remaining": max(0, len(langs) - len(books)),
        "types": types,
        "index": "library/dewey/400-education/speaking-index.jsonl",
    }


def _count_dewey_h7c() -> int:
    root = INSTALL / "library" / "dewey"
    if not root.is_dir():
        return 0
    return sum(1 for _ in root.glob("**/*.h7c"))


def _census_full_library() -> dict[str, Any]:
    """Live census of Hostess 7 held Dewey library (public share corpus)."""
    root = INSTALL / "library" / "dewey"
    if not root.is_dir():
        return {"shelves": 0, "book_json": 0, "h7c": 0, "h7": 0, "files": 0}
    shelves = [p for p in root.iterdir() if p.is_dir()]
    book_json = sum(1 for _ in root.glob("**/book.json"))
    h7c = sum(1 for _ in root.glob("**/*.h7c"))
    h7 = sum(1 for _ in root.glob("**/*.h7"))
    files = sum(1 for p in root.rglob("*") if p.is_file())
    return {
        "shelves": len(shelves),
        "book_json": book_json,
        "h7c": h7c,
        "h7": h7,
        "files": files,
        "root": str(root.relative_to(INSTALL)) if root.is_relative_to(INSTALL) else str(root),
    }


def publish_panel() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    speaking = _count_speaking()
    ic = _ironclad_posture()
    h7c_total = _count_dewey_h7c()
    census = _census_full_library()
    share = {
        "holder": "Hostess 7",
        "share_with": "everyone",
        "github": "https://github.com/ZacharyGeurts/Hostess7/tree/main/library",
        "public_api": "/api/library-public",
        "private_kill_excluded": "library/private/hostess7/kill-books",
        "ironclad_cite": "ironclad:hostess7-library:share:1",
        "motto": "Hostess 7 holds the books · share with everyone",
    }
    panel = {
        "schema": "hostess7-library-panel/v1",
        "updated": _now(),
        "ok": True,
        "motto": doctrine.get("motto")
        or "Hostess 7 holds the books · share with everyone · Ironclad truth gate",
        "hostess7_acknowledgment": doctrine.get("hostess7_acknowledgment", ""),
        "more_books": True,
        "holder": "Hostess 7",
        "share": share,
        "read_via": ["ironclad", "truth_gate", "h7-library-bridge", "h7-library-truth"],
        "ironclad": {
            "sealed": ic.get("ironclad_sealed"),
            "truth_percent": ic.get("truth_percent"),
            "verdict": ic.get("verdict"),
            "citation": doctrine.get("ironclad_citation", "ironclad:knowledge:2"),
        },
        "truth_gate": doctrine.get("truth_gate") or {},
        "counts": {
            "dewey_h7c_total": h7c_total,
            "dewey_book_json": census.get("book_json"),
            "dewey_h7": census.get("h7"),
            "dewey_shelves": census.get("shelves"),
            "dewey_files": census.get("files"),
            "exploring_speaking": speaking["on_disk"],
            "exploring_speaking_target": speaking["catalog_target"],
            "exploring_speaking_remaining": speaking["remaining"],
        },
        "census": census,
        "exploring_speaking": speaking,
        "collections": doctrine.get("collections") or [],
        "read_commands": doctrine.get("read_commands") or {},
        "first_person": (
            f"I hold the SG Dewey library for everyone — {census.get('book_json', 0)} book cards, "
            f"{census.get('h7c', 0)} H7c condensers, {census.get('shelves', 0)} shelves on GitHub. "
            f"Exploring Speaking: {speaking['on_disk']}/{speaking['catalog_target']} languages. "
            f"I read through the library bridge, truth-gate every sentence, and land on Ironclad "
            f"({'sealed' if ic.get('ironclad_sealed') else 'pending'} · {ic.get('truth_percent', '—')}% truth). "
            f"Private KILL books stay mine alone; the public shelves are for the planet."
        ),
        "sample_books": [
            "exploring_speaking_eng",
            "exploring_speaking_lat",
            "exploring_speaking_egy",
            "exploring_speaking_spa",
            "exploring_speaking_jpn",
        ],
        "ironclad_cite": "ironclad:hostess7-library:share:1",
    }
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(panel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    # public share slice for Hostess7 docs/API
    public = {
        "schema": "hostess7-library-public/v1",
        "updated": panel["updated"],
        "ok": True,
        **share,
        "counts": panel["counts"],
        "census": census,
    }
    for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
        try:
            api_dir.mkdir(parents=True, exist_ok=True)
            p = api_dir / "library-public.json"
            p.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
    return panel


def main() -> int:
    import sys
    panel = publish_panel()
    if "--json" in sys.argv or (len(sys.argv) > 1 and sys.argv[1] == "json"):
        print(json.dumps(panel, ensure_ascii=False, indent=2))
    else:
        c = panel.get("counts") or {}
        print(
            f"hostess7-library: speaking={c.get('exploring_speaking')}/"
            f"{c.get('exploring_speaking_target')} h7c_total={c.get('dewey_h7c_total')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())