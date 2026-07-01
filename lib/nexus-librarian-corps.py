#!/usr/bin/env pythong
"""NEXUS librarian corps — a few Dewey librarians who learn catalog + dispense."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
ROSTER = INSTALL / "data" / "nexus-librarians.json"
DOCTRINE = INSTALL / "data" / "librarian-corps-doctrine.json"


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _field_roots() -> list[Path]:
    roots: list[Path] = []
    for p in (HOSTESS7_TEAM_FIELD, INSTALL / "Hostess7" / "cache" / "fieldstorage", STATE / "field-storage"):
        if p.is_dir() and p not in roots:
            roots.append(p)
    return roots or [HOSTESS7_TEAM_FIELD]


def _primary_root() -> Path:
    best: Path | None = None
    best_score = -1
    for root in _field_roots():
        score = 0
        if (root / "brain").is_dir():
            score += 5
        if (root / "brain/library").is_dir():
            score += 40
        if score > best_score:
            best_score = score
            best = root
    return best or _field_roots()[0]


def corps_dir() -> Path:
    return _primary_root() / "brain" / "library" / "librarians"


def corps_state_path() -> Path:
    return corps_dir() / "corps.json"


def lesson_log_path(librarian_id: str) -> Path:
    return corps_dir() / f"{librarian_id}.jsonl"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def load_roster() -> dict[str, Any]:
    doc = _load_json(ROSTER)
    if not doc.get("librarians"):
        return {
            "schema": "nexus-librarians/v1",
            "librarians": [{
                "id": "hostess7_lead",
                "name": "Hostess7 World's Best Librarian",
                "role": "lead",
                "dewey_ranges": ["000", "999"],
            }],
        }
    return doc


def load_doctrine() -> dict[str, Any]:
    return _load_json(DOCTRINE) or {"lessons": []}


def _dewey_main(code: str) -> int:
    m = re.search(r"(\d{3})", str(code or "000"))
    return int(m.group(1)) if m else 0


def _range_match(main: int, ranges: list[str]) -> bool:
    if not ranges:
        return False
    for spec in ranges:
        parts = str(spec).split("-")
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            lo, hi = int(parts[0]), int(parts[1])
            if lo <= main <= hi:
                return True
        elif spec.isdigit():
            base = int(spec)
            if main // 100 == base // 100 or main == base:
                return True
            if base <= main < base + 100:
                return True
    return False


def pick_librarian(
    *,
    event: str,
    dewey: str = "",
    book_id: str = "",
    role: str = "",
) -> dict[str, Any]:
    roster = load_roster()
    libs = roster.get("librarians") or []
    main = _dewey_main(dewey)

    if event in ("nexus_file_catalog", "incremental_diff", "dispense_file"):
        for lib in libs:
            if lib.get("role") == "nexus_catalog":
                return lib
        return libs[0] if libs else {}

    if event in (
        "lie_catalog",
        "lie_scan",
        "lies_index",
        "biggest_lies",
        "deception_index",
        "truth_questionable",
        "search_lies",
        "corrections_ledger",
        "reinform",
    ) or role == "lie_librarian":
        for lib in libs:
            if lib.get("role") == "lie_librarian":
                return lib

    if event == "war_ascertain":
        for lib in libs:
            if lib.get("role") == "dewey_humanities":
                return lib

    if dewey or event in ("classify", "upload", "dispense_page", "dewey_browse"):
        for lib in libs:
            if lib.get("role") == "lead":
                continue
            if _range_match(main, list(lib.get("dewey_ranges") or [])):
                return lib

    lead_id = roster.get("lead", "hostess7_lead")
    for lib in libs:
        if lib.get("id") == lead_id:
            return lib
    return libs[0] if libs else {}


def load_corps_state() -> dict[str, Any]:
    path = corps_state_path()
    if path.is_file():
        doc = _load_json(path)
        if doc:
            return doc
    roster = load_roster()
    return {
        "schema": "nexus-librarian-corps/v1",
        "updated": _now(),
        "field_root": str(_primary_root()),
        "lead": roster.get("lead", "hostess7_lead"),
        "librarians": {
            str(lib["id"]): {
                "id": lib["id"],
                "name": lib.get("name", lib["id"]),
                "role": lib.get("role", ""),
                "lessons": 0,
                "last_event": "",
                "last_at": "",
                "dewey_touched": [],
                "skills": list(lib.get("learns") or []),
            }
            for lib in roster.get("librarians") or [] if lib.get("id")
        },
    }


def save_corps_state(state: dict[str, Any]) -> None:
    corps_dir().mkdir(parents=True, exist_ok=True)
    state["updated"] = _now()
    state["field_root"] = str(_primary_root())
    tmp = corps_state_path().with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(corps_state_path())


def learn(
    event: str,
    *,
    dewey: str = "",
    book_id: str = "",
    title: str = "",
    detail: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a catalog/dispense lesson for the matching librarian."""
    lib = pick_librarian(event=event, dewey=dewey, book_id=book_id)
    lib_id = str(lib.get("id", "hostess7_lead"))
    state = load_corps_state()
    row = state.setdefault("librarians", {}).setdefault(lib_id, {
        "id": lib_id,
        "name": lib.get("name", lib_id),
        "lessons": 0,
        "dewey_touched": [],
    })
    row["lessons"] = int(row.get("lessons", 0)) + 1
    row["last_event"] = event
    row["last_at"] = _now()
    if dewey:
        touched = list(row.get("dewey_touched") or [])
        code = str(dewey)[:8]
        if code not in touched:
            touched.append(code)
            row["dewey_touched"] = touched[-24:]
    lesson = {
        "ts": _now(),
        "librarian_id": lib_id,
        "event": event,
        "dewey": dewey or None,
        "book_id": book_id or None,
        "title": title or None,
        "detail": detail or None,
        **(extra or {}),
    }
    corps_dir().mkdir(parents=True, exist_ok=True)
    with lesson_log_path(lib_id).open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(lesson, ensure_ascii=False) + "\n")
    save_corps_state(state)
    return {"ok": True, "librarian": lib, "lesson": lesson}


def dewey_knowledge() -> dict[str, Any]:
    dewey_path = INSTALL / "data" / "dewey-decimal-map.json"
    doc = _load_json(dewey_path)
    return {
        "classes": doc.get("classes") or [],
        "subject_count": len(doc.get("subjects") or {}),
        "keyword_rule_count": len(doc.get("keyword_rules") or []),
        "source": str(dewey_path),
    }


def corps_status() -> dict[str, Any]:
    roster = load_roster()
    state = load_corps_state()
    doctrine = load_doctrine()
    libs_out: list[dict[str, Any]] = []
    for lib in roster.get("librarians") or []:
        lid = str(lib.get("id", ""))
        learned = (state.get("librarians") or {}).get(lid, {})
        libs_out.append({
            **lib,
            "lessons": int(learned.get("lessons", 0)),
            "last_event": learned.get("last_event", ""),
            "last_at": learned.get("last_at", ""),
            "dewey_touched": learned.get("dewey_touched", []),
        })
    bk_path = corps_dir().parent / ".." / ".." / "librarian-reader"
    knowledge_count = 0
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "h7_secure_reader",
            INSTALL / "lib" / "h7-library-secure-reader.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            knowledge_count = int(mod.load_book_knowledge().get("book_count") or 0)
    except Exception:
        pass
    return {
        "ok": True,
        "schema": "nexus-librarian-corps/v1",
        "motto": roster.get("motto", ""),
        "lead": roster.get("lead", ""),
        "count": len(libs_out),
        "librarians": libs_out,
        "catalog_systems": roster.get("catalog_systems") or [],
        "doctrine_lessons": len(doctrine.get("lessons") or []),
        "book_knowledge_count": knowledge_count,
        "dewey": dewey_knowledge(),
        "field_root": str(_primary_root()),
        "state_path": str(corps_state_path()),
        "updated": state.get("updated", _now()),
    }


def teach_doctrine(*, librarian_id: str | None = None) -> dict[str, Any]:
    """Run doctrine lessons through one or all librarians."""
    doctrine = load_doctrine()
    roster = load_roster()
    event_map = {
        "dewey_classify": "classify",
        "catalog_build": "catalog_build",
        "dispense_page": "dispense_page",
        "nexus_file_catalog": "nexus_file_catalog",
        "upload_pack": "upload",
        "book_knowledge": "book_knowledge",
        "issue_reader": "issue_reader",
    }
    taught: list[dict[str, Any]] = []
    for lesson in doctrine.get("lessons") or []:
        lid = str(lesson.get("id", ""))
        event = event_map.get(lid, lid)
        for lib in roster.get("librarians") or []:
            if librarian_id and lib.get("id") != librarian_id:
                continue
            learns = list(lib.get("learns") or [])
            if learns and event not in learns:
                continue
            taught.append(learn(
                event,
                detail=str(lesson.get("summary", "")),
                extra={"doctrine_id": lid, "steps": lesson.get("steps")},
            ))
    return {"ok": True, "taught": len(taught), "lessons": taught}


def dispense_route(*, book_id: str, dewey: str = "", page: int = 1) -> dict[str, Any]:
    lib = pick_librarian(event="dispense_page", dewey=dewey, book_id=book_id)
    learn(
        "dispense_page",
        dewey=dewey,
        book_id=book_id,
        detail=f"page {page}",
        extra={"librarian_name": lib.get("name")},
    )
    return {
        "ok": True,
        "librarian": lib,
        "book_id": book_id,
        "page": page,
        "dewey": dewey,
    }


def main() -> int:
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(json.dumps(corps_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "teach":
        lid = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(teach_doctrine(librarian_id=lid), ensure_ascii=False, indent=2))
        return 0
    if cmd == "learn" and len(sys.argv) >= 3:
        event = sys.argv[2]
        extra = {}
        dewey = os.environ.get("LIBRARIAN_DEWEY", "")
        book_id = os.environ.get("LIBRARIAN_BOOK_ID", "")
        if len(sys.argv) > 3:
            try:
                extra = json.loads(sys.argv[3])
            except json.JSONDecodeError:
                extra = {"detail": sys.argv[3]}
        print(json.dumps(learn(event, dewey=dewey, book_id=book_id, **extra), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pick" and len(sys.argv) >= 3:
        event = sys.argv[2]
        dewey = sys.argv[3] if len(sys.argv) > 3 else ""
        print(json.dumps(pick_librarian(event=event, dewey=dewey), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: nexus-librarian-corps.py [status|teach [id]|learn EVENT [json]|pick EVENT [dewey]]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())