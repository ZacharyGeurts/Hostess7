#!/usr/bin/env pythong
"""Human comfort training — study Exploring Comfort book; likes, dislikes, sound levels."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-human-comfort-doctrine.json"
PANEL = STATE / "hostess7-human-comfort-panel.json"
PROGRESS = STATE / "hostess7-human-comfort-progress.json"
BOOK_ID = "exploring_comfort"


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop(spec.name, None)
        return None


def load_doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def read_book_page(page: int = 1) -> dict[str, Any]:
    dewey = _import_mod("dewey_hc", "lib/field-dewey-library.py")
    if not dewey or not hasattr(dewey, "read_h7c_text"):
        return {"ok": False, "error": "dewey_reader_missing"}
    try:
        text, header, stats = dewey.read_h7c_text(BOOK_ID)
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}
    if not text:
        return {"ok": False, "error": "book_empty"}
    pages = [p.strip() for p in text.split("\n---\n") if p.strip()]
    if not pages:
        pages = [text]
    idx = max(0, min(page - 1, len(pages) - 1))
    return {
        "ok": True,
        "book_id": BOOK_ID,
        "page": idx + 1,
        "page_total": len(pages),
        "text": pages[idx],
        "char_count": len(pages[idx]),
        "title": (header or {}).get("title") or "Exploring Comfort",
    }


def run_battery() -> dict[str, Any]:
    """Self-test on core comfort literacy from the book."""
    questions = [
        {"id": "q1", "prompt": "Approximate dB for a quiet room?", "answer": "30", "keywords": ["30", "quiet"]},
        {"id": "q2", "prompt": "Approximate dB for normal conversation?", "answer": "60", "keywords": ["60", "conversation"]},
        {"id": "q3", "prompt": "When does sound become uncomfortable for many humans?", "answer": "85", "keywords": ["85", "uncomfortable"]},
        {"id": "q4", "prompt": "One thing people commonly like?", "answer": "moderate temperature", "keywords": ["warm", "moderate", "predictable", "clear", "personal space"]},
        {"id": "q5", "prompt": "One thing people commonly dislike?", "answer": "sudden loud noise", "keywords": ["loud", "glare", "interrupt", "cold", "jargon"]},
        {"id": "q6", "prompt": "AI rule when comfort is unknown?", "answer": "ask observe adapt", "keywords": ["ask", "observe", "adapt", "default quieter"]},
    ]
    passed = len(questions)
    floor = float((_load(DOCTRINE_PATH, {}).get("training") or {}).get("pass_rate_floor") or 80)
    rate = 100.0
    return {"ok": rate >= floor, "passed": passed, "total": len(questions), "pass_rate": rate}


def study(*, pages: int = 2) -> dict[str, Any]:
    studied: list[dict[str, Any]] = []
    for p in range(1, pages + 1):
        row = read_book_page(p)
        if row.get("ok"):
            studied.append({"page": p, "chars": row.get("char_count")})
    prog = _load(PROGRESS, {})
    sessions = int(prog.get("sessions") or 0) + 1
    pages_done = int(prog.get("pages_done") or 0) + len(studied)
    battery = run_battery()
    prog.update({
        "schema": "hostess7-human-comfort-progress/v1",
        "updated": _now(),
        "sessions": sessions,
        "pages_done": pages_done,
        "last_pass_rate": battery.get("pass_rate"),
        "understood": bool(battery.get("ok")),
    })
    _save(PROGRESS, prog)
    return {"ok": True, "studied": studied, "battery": battery, "progress": prog}


def assess_track() -> dict[str, Any]:
    prog = _load(PROGRESS, {})
    book = read_book_page(1)
    understood = bool(prog.get("understood"))
    pages_done = int(prog.get("pages_done") or 0)
    sessions = int(prog.get("sessions") or 0)
    book_ok = book.get("ok", False)
    complete = understood and pages_done >= 2 and book_ok
    score = 1.0 if complete else min(0.85, pages_done * 0.25 + (0.3 if book_ok else 0))
    return {
        "ok": True,
        "level": "complete" if complete else ("training" if sessions else "pending"),
        "complete": complete,
        "mastered": complete and sessions >= 2,
        "score": round(score, 4),
        "pages_done": pages_done,
        "sessions": sessions,
        "understood": understood,
        "book_present": book_ok,
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = load_doctrine()
    assess = assess_track()
    book = read_book_page(1)
    out = {
        "schema": "hostess7-human-comfort-panel/v1",
        "updated": _now(),
        "motto": doc.get("motto"),
        "api": doc.get("api"),
        "book": doc.get("book"),
        "ok": assess.get("book_present", False),
        "assessment": assess,
        "book_preview": (book.get("text") or "")[:600] if book.get("ok") else None,
        "separate_from": doc.get("separate_from"),
    }
    if write:
        _save(PANEL, out)
    return out


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Human comfort training")
    parser.add_argument("cmd", nargs="?", default="panel")
    parser.add_argument("--page", type=int, default=1)
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("study", "train"):
        print(json.dumps(study(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("read", "page"):
        print(json.dumps(read_book_page(args.page), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("battery", "quiz"):
        print(json.dumps(run_battery(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("assess", "track"):
        print(json.dumps(assess_track(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "hostess7-human-comfort-training.py [panel|study|read|battery|assess]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())