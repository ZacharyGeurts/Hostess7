#!/usr/bin/env pythong
"""Secure librarian-issued full-page reader — sessions, bookmarks, layout, progress."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
READER_DIR = STATE / "librarian-reader"
KNOWLEDGE_PATH = READER_DIR / "book-knowledge.json"
SESSION_TTL_SEC = int(os.environ.get("NEXUS_READER_SESSION_TTL", "14400"))
SCHEMA = "h7-secure-reader/v1"


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _secret() -> bytes:
    fp = STATE / "librarian-reader-secret"
    if fp.is_file():
        return fp.read_bytes()
    READER_DIR.mkdir(parents=True, exist_ok=True)
    raw = secrets.token_bytes(32)
    fp.write_bytes(raw)
    try:
        fp.chmod(0o600)
    except OSError:
        pass
    return raw


def _book_dir(book_id: str) -> Path:
    safe = hashlib.sha256(book_id.encode()).hexdigest()[:16]
    return READER_DIR / "books" / safe


def _session_path(token: str) -> Path:
    return READER_DIR / "sessions" / f"{token}.json"


def _sign(token: str, book_id: str, exp: int) -> str:
    msg = f"{token}:{book_id}:{exp}".encode()
    return hmac.new(_secret(), msg, hashlib.sha256).hexdigest()


def _book_record_path(book_id: str) -> Path:
    return _book_dir(book_id) / "reader.json"


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        return doc if isinstance(doc, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def book_summary(book: dict[str, Any]) -> dict[str, Any]:
    bid = str(book.get("id") or "")
    return {
        "id": bid,
        "title": str(book.get("title") or bid),
        "author": str(book.get("author") or ""),
        "dewey": str(book.get("dewey") or ""),
        "dewey_label": str(book.get("dewey_label") or ""),
        "subject": str(book.get("subject") or book.get("category") or ""),
        "description": str(book.get("description") or book.get("summary") or "")[:800],
        "format": str(book.get("format") or "H7"),
        "license": str(book.get("license") or ""),
        "ein": str(book.get("ein") or ""),
        "ready": bool(book.get("ready", True)),
        "page_count": book.get("page_count"),
        "char_count": book.get("char_count"),
    }


def sync_book_knowledge(books: list[dict[str, Any]]) -> dict[str, Any]:
    """Librarians ingest every catalogued book — title, author, Dewey, description."""
    index: dict[str, dict[str, Any]] = {}
    for book in books:
        if not book.get("id"):
            continue
        index[str(book["id"])] = book_summary(book)
    doc = {
        "schema": SCHEMA,
        "updated": _now(),
        "book_count": len(index),
        "books": index,
    }
    READER_DIR.mkdir(parents=True, exist_ok=True)
    _save_json(KNOWLEDGE_PATH, doc)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "nexus_librarian_corps",
            INSTALL / "lib" / "nexus-librarian-corps.py",
        )
        if spec and spec.loader:
            corps = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(corps)
            for bid, row in index.items():
                corps.learn(
                    "book_knowledge",
                    book_id=bid,
                    dewey=row.get("dewey", ""),
                    title=row.get("title", ""),
                    detail=row.get("description", "")[:200],
                )
    except Exception:
        pass
    return {"ok": True, "book_count": len(index), "path": str(KNOWLEDGE_PATH)}


def load_book_knowledge() -> dict[str, Any]:
    doc = _load_json(KNOWLEDGE_PATH)
    if doc.get("books"):
        return doc
    return {"schema": SCHEMA, "book_count": 0, "books": {}, "updated": _now()}


def get_book(book_id: str) -> dict[str, Any] | None:
    return (load_book_knowledge().get("books") or {}).get(book_id)


def _pick_librarian(book_id: str, dewey: str = "") -> dict[str, Any]:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "nexus_librarian_corps",
            INSTALL / "lib" / "nexus-librarian-corps.py",
        )
        if spec and spec.loader:
            corps = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(corps)
            return corps.pick_librarian(event="dispense_page", dewey=dewey, book_id=book_id)
    except Exception:
        pass
    return {"id": "hostess7_lead", "name": "Hostess7 World's Best Librarian"}


def issue_session(book_id: str, *, book_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Librarian issues a secure local-only reader session for one book."""
    meta = book_meta or get_book(book_id) or {"id": book_id, "title": book_id}
    if not meta.get("title"):
        meta["title"] = book_id
    dewey = str(meta.get("dewey") or "")
    librarian = _pick_librarian(book_id, dewey)
    lie_librarian: dict[str, Any] = {}
    all_lies: dict[str, Any] = {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "h7_lie_librarian_reader",
            INSTALL / "lib" / "h7-lie-librarian.py",
        )
        if spec and spec.loader:
            ll = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ll)
            if hasattr(ll, "persona"):
                lie_librarian = ll.persona()
            if hasattr(ll, "knows_book"):
                know = ll.knows_book(book_id, audience="both")
                all_lies = {
                    "lie_count": know.get("lie_count", 0),
                    "lies": know.get("lies") or [],
                    "index": know.get("index"),
                    "for_humans": know.get("for_humans"),
                    "for_super_intelligence": know.get("for_super_intelligence"),
                    "dual_audience": know.get("dual_audience"),
                }
                if know.get("lie_count"):
                    librarian = lie_librarian or librarian
    except Exception:
        pass
    token = secrets.token_urlsafe(24)
    exp = int(time.time()) + SESSION_TTL_SEC
    sig = _sign(token, book_id, exp)
    session = {
        "schema": SCHEMA,
        "token": token,
        "book_id": book_id,
        "book": meta,
        "librarian": librarian,
        "issued_at": _now(),
        "expires_epoch": exp,
        "signature": sig,
        "secure": True,
        "local_only": True,
        "features": [
            "bookmarks",
            "layout_themes",
            "font_size",
            "line_height",
            "page_ratio",
            "progress_restore",
            "braille_line",
            "truth_sentences",
            "touch_swipe",
        ],
    }
    READER_DIR.mkdir(parents=True, exist_ok=True)
    (READER_DIR / "sessions").mkdir(parents=True, exist_ok=True)
    _save_json(_session_path(token), session)
    rec = _load_reader_record(book_id)
    page_chars = int(os.environ.get("NEXUS_H7_PAGE_CHARS", "3200"))
    reinform_panel: dict[str, Any] = {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "h7_reinform_reader",
            INSTALL / "lib" / "h7-library-reinform.py",
        )
        if spec and spec.loader:
            rmod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(rmod)
            if hasattr(rmod, "panel_json"):
                reinform_panel = rmod.panel_json(book_id)
    except Exception:
        pass
    return {
        "ok": True,
        "session": {
            "token": token,
            "book_id": book_id,
            "expires_epoch": exp,
            "signature": sig,
            "librarian": librarian,
            "book": meta,
            "features": session["features"] + ["canonical_pages", "lies_index", "corrections_ledger"],
            "page_chars": page_chars,
            "pagination": reinform_panel.get("pagination") or {},
            "page_count": reinform_panel.get("page_count"),
            "lies_index": reinform_panel.get("lies_index"),
            "all_lies": all_lies,
            "lie_librarian": lie_librarian,
            "corrections": reinform_panel.get("corrections") or [],
            "overlap_refs": reinform_panel.get("overlap_refs") or [],
            "appendix_page": reinform_panel.get("appendix_page"),
            "progress": rec.get("progress") or {},
            "bookmarks": rec.get("bookmarks") or [],
            "layout": rec.get("layout") or {},
        },
    }


def validate_session(token: str, book_id: str, signature: str) -> dict[str, Any] | None:
    if not token or not book_id or not signature:
        return None
    path = _session_path(token)
    if not path.is_file():
        return None
    session = _load_json(path)
    if session.get("book_id") != book_id:
        return None
    exp = int(session.get("expires_epoch") or 0)
    if exp < int(time.time()):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return None
    expected = _sign(token, book_id, exp)
    if not hmac.compare_digest(expected, signature):
        return None
    return session


def _load_reader_record(book_id: str) -> dict[str, Any]:
    doc = _load_json(_book_record_path(book_id))
    if not doc:
        doc = {"schema": SCHEMA, "book_id": book_id, "bookmarks": [], "progress": {}, "layout": {}}
    return doc


def list_bookmarks(book_id: str, *, token: str = "", signature: str = "") -> dict[str, Any]:
    if token and not validate_session(token, book_id, signature):
        return {"ok": False, "error": "invalid_session"}
    rec = _load_reader_record(book_id)
    return {"ok": True, "book_id": book_id, "bookmarks": rec.get("bookmarks") or []}


def save_bookmark(
    book_id: str,
    *,
    page: int,
    label: str = "",
    token: str = "",
    signature: str = "",
) -> dict[str, Any]:
    if not validate_session(token, book_id, signature):
        return {"ok": False, "error": "invalid_session"}
    rec = _load_reader_record(book_id)
    bookmarks: list[dict[str, Any]] = list(rec.get("bookmarks") or [])
    entry = {
        "id": secrets.token_hex(6),
        "page": max(1, int(page)),
        "label": (label or f"Page {page}").strip()[:120],
        "created": _now(),
    }
    bookmarks = [b for b in bookmarks if b.get("page") != entry["page"]]
    bookmarks.append(entry)
    bookmarks.sort(key=lambda b: int(b.get("page") or 0))
    rec["bookmarks"] = bookmarks[-48:]
    _save_json(_book_record_path(book_id), rec)
    return {"ok": True, "bookmark": entry, "bookmarks": rec["bookmarks"]}


def delete_bookmark(book_id: str, *, bookmark_id: str, token: str = "", signature: str = "") -> dict[str, Any]:
    if not validate_session(token, book_id, signature):
        return {"ok": False, "error": "invalid_session"}
    rec = _load_reader_record(book_id)
    bookmarks = [b for b in (rec.get("bookmarks") or []) if b.get("id") != bookmark_id]
    rec["bookmarks"] = bookmarks
    _save_json(_book_record_path(book_id), rec)
    return {"ok": True, "bookmarks": bookmarks}


def save_progress(
    book_id: str,
    *,
    page: int,
    page_count: int = 0,
    token: str = "",
    signature: str = "",
) -> dict[str, Any]:
    if not validate_session(token, book_id, signature):
        return {"ok": False, "error": "invalid_session"}
    rec = _load_reader_record(book_id)
    rec["progress"] = {
        "page": max(1, int(page)),
        "page_count": int(page_count or 0),
        "updated": _now(),
    }
    _save_json(_book_record_path(book_id), rec)
    return {"ok": True, "progress": rec["progress"]}


def save_layout(
    book_id: str,
    *,
    layout: dict[str, Any],
    token: str = "",
    signature: str = "",
) -> dict[str, Any]:
    if not validate_session(token, book_id, signature):
        return {"ok": False, "error": "invalid_session"}
    rec = _load_reader_record(book_id)
    rec["layout"] = {k: layout[k] for k in layout if k in (
        "fontSize", "fontColor", "bgColor", "fontId", "ratioId", "lineHeight",
        "themeId", "marginPx", "brailleMode",
    )}
    _save_json(_book_record_path(book_id), rec)
    return {"ok": True, "layout": rec["layout"]}


def knowledge_query(*, book_id: str = "", q: str = "") -> dict[str, Any]:
    doc = load_book_knowledge()
    books: dict[str, Any] = doc.get("books") or {}
    if book_id:
        row = books.get(book_id)
        return {"ok": bool(row), "book": row} if row else {"ok": False, "error": "unknown_book"}
    if q:
        toks = [t.lower() for t in q.split() if len(t) > 1]
        hits = []
        for row in books.values():
            blob = " ".join(str(row.get(k, "")) for k in ("title", "author", "description", "subject", "dewey_label")).lower()
            score = sum(1 for t in toks if t in blob)
            if score:
                hits.append({**row, "score": score})
        hits.sort(key=lambda r: (-r["score"], r.get("title", "")))
        return {"ok": True, "hits": hits[:32], "query": q}
    return {"ok": True, **doc}


def main() -> int:
    import sys

    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: issue|knowledge|bookmarks|progress|layout ..."}, ensure_ascii=False))
        return 1
    cmd = sys.argv[1]
    if cmd == "issue" and len(sys.argv) >= 3:
        import importlib.util
        corps_spec = importlib.util.spec_from_file_location(
            "nexus_librarian_corps",
            INSTALL / "lib" / "nexus-librarian-corps.py",
        )
        if corps_spec and corps_spec.loader:
            corps = importlib.util.module_from_spec(corps_spec)
            corps_spec.loader.exec_module(corps)
            corps.learn("issue_reader", book_id=sys.argv[2])
        meta = None
        if len(sys.argv) > 3:
            try:
                meta = json.loads(sys.argv[3])
            except json.JSONDecodeError:
                pass
        print(json.dumps(issue_session(sys.argv[2], book_meta=meta), ensure_ascii=False, indent=2))
        return 0
    if cmd == "knowledge":
        bid = sys.argv[2] if len(sys.argv) > 2 else ""
        q = sys.argv[3] if len(sys.argv) > 3 else ""
        print(json.dumps(knowledge_query(book_id=bid, q=q), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sync" and len(sys.argv) >= 3:
        books = json.loads(sys.argv[2])
        print(json.dumps(sync_book_knowledge(books), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "unknown_command"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())