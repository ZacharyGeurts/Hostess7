#!/usr/bin/env pythong
"""Librarian checkout — 14-day default loan, 0 = infinite, daily Noti if overdue. Books never lost."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parent.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
CHECKOUT_DIR = STATE / "librarian-checkout"
ACTIVE_PATH = CHECKOUT_DIR / "active.json"
LEDGER_PATH = CHECKOUT_DIR / "ledger.jsonl"
SCHEMA = "h7-library-checkout/v1"
DEFAULT_DAYS = 14
MAX_DAYS = 365


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _parse_ts(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(event: str, **fields: Any) -> dict[str, Any]:
    CHECKOUT_DIR.mkdir(parents=True, exist_ok=True)
    row = {"schema": SCHEMA, "ts": _now(), "event": event, **fields}
    with LEDGER_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def normalize_days(days: Any) -> int:
    """0 = infinite loan; otherwise 1–365 days. Default 14."""
    if days is None or days == "":
        return DEFAULT_DAYS
    try:
        n = int(days)
    except (TypeError, ValueError):
        return DEFAULT_DAYS
    if n == 0:
        return 0
    return max(1, min(n, MAX_DAYS))


def days_label(days: int) -> str:
    if days == 0:
        return "Infinite"
    if days == DEFAULT_DAYS:
        return f"{days} days (default)"
    return f"{days} day{'s' if days != 1 else ''}"


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
            return corps.pick_librarian(event="checkout", dewey=dewey, book_id=book_id)
    except Exception:
        pass
    return {"id": "hostess7_lead", "name": "Hostess7 World's Best Librarian"}


def _corps_learn(event: str, **kwargs: Any) -> None:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "nexus_librarian_corps",
            INSTALL / "lib" / "nexus-librarian-corps.py",
        )
        if spec and spec.loader:
            corps = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(corps)
            corps.learn(event, **kwargs)
    except Exception:
        pass


def _active_doc() -> dict[str, Any]:
    doc = _load(ACTIVE_PATH, {"schema": SCHEMA, "updated": _now(), "checkouts": {}})
    doc.setdefault("checkouts", {})
    return doc


def _save_active(checkouts: dict[str, Any]) -> None:
    _save(ACTIVE_PATH, {"schema": SCHEMA, "updated": _now(), "checkouts": checkouts})


def get_checkout(book_id: str) -> dict[str, Any] | None:
    rec = (_active_doc().get("checkouts") or {}).get(book_id)
    return dict(rec) if isinstance(rec, dict) else None


def list_active() -> list[dict[str, Any]]:
    rows = []
    for bid, rec in sorted((_active_doc().get("checkouts") or {}).items()):
        if isinstance(rec, dict) and rec.get("status") == "active":
            rows.append(enrich_checkout(dict(rec)))
    return rows


def enrich_checkout(rec: dict[str, Any]) -> dict[str, Any]:
    raw_days = rec.get("checkout_days")
    days = DEFAULT_DAYS if raw_days is None else int(raw_days)
    infinite = bool(rec.get("infinite")) or days == 0
    due_at = rec.get("due_at")
    overdue = False
    days_left: int | None = None
    if not infinite and due_at:
        due = _parse_ts(str(due_at))
        now = datetime.now(timezone.utc)
        delta = due - now
        days_left = int(delta.total_seconds() // 86400)
        overdue = delta.total_seconds() < 0
    out = {
        **rec,
        "checkout_days": days,
        "infinite": infinite,
        "days_label": days_label(days),
        "overdue": overdue,
        "days_left": days_left,
        "due_label": "No due date" if infinite else (due_at or ""),
    }
    return out


def checkout_book(
    book_id: str,
    *,
    days: Any = DEFAULT_DAYS,
    patron: str = "operator",
    book_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Check out a book — stays on shelf; we only track the loan."""
    if not book_id:
        return {"ok": False, "error": "missing_book_id"}
    loan_days = normalize_days(days)
    infinite = loan_days == 0
    meta = book_meta or {}
    dewey = str(meta.get("dewey") or "")
    librarian = _pick_librarian(book_id, dewey)
    now = datetime.now(timezone.utc)
    due_at = None if infinite else (now + timedelta(days=loan_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc = _active_doc()
    checkouts: dict[str, Any] = doc.get("checkouts") or {}
    prev = checkouts.get(book_id)
    if isinstance(prev, dict) and prev.get("status") == "active":
        prev_id = prev.get("id")
        _append_ledger("renewed", checkout_id=prev_id, book_id=book_id, patron=patron, days=loan_days)
    co_id = f"co_{uuid.uuid4().hex[:12]}"
    record = {
        "id": co_id,
        "book_id": book_id,
        "title": str(meta.get("title") or book_id),
        "author": str(meta.get("author") or ""),
        "dewey": dewey,
        "checkout_days": loan_days,
        "infinite": infinite,
        "patron": patron,
        "librarian": librarian,
        "checked_out_at": _now(),
        "due_at": due_at,
        "returned_at": None,
        "status": "active",
        "last_reminded": None,
        "reminder_count": 0,
        "on_shelf": True,
        "note": "Book never leaves the shelf — librarian tracks your loan.",
    }
    checkouts[book_id] = record
    _save_active(checkouts)
    _append_ledger("checked_out", checkout_id=co_id, book_id=book_id, patron=patron, days=loan_days, infinite=infinite)
    _corps_learn("checkout", book_id=book_id, dewey=dewey, title=record["title"], detail=days_label(loan_days))
    return {"ok": True, "checkout": enrich_checkout(record)}


def checkin_book(book_id: str, *, patron: str = "operator") -> dict[str, Any]:
    doc = _active_doc()
    checkouts: dict[str, Any] = doc.get("checkouts") or {}
    rec = checkouts.get(book_id)
    if not isinstance(rec, dict) or rec.get("status") != "active":
        return {"ok": False, "error": "not_checked_out", "book_id": book_id}
    rec = dict(rec)
    rec["status"] = "returned"
    rec["returned_at"] = _now()
    rec["returned_by"] = patron
    checkouts[book_id] = rec
    _save_active(checkouts)
    _append_ledger(
        "checked_in",
        checkout_id=rec.get("id"),
        book_id=book_id,
        patron=patron,
        checked_out_at=rec.get("checked_out_at"),
    )
    _corps_learn("checkin", book_id=book_id, title=rec.get("title", ""))
    return {"ok": True, "checkout": enrich_checkout(rec)}


def attach_to_books(books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active = {r["book_id"]: r for r in list_active()}
    out = []
    for book in books:
        bid = str(book.get("id") or "")
        row = dict(book)
        co = active.get(bid)
        if co:
            row["checkout"] = co
            row["checked_out"] = True
        else:
            row["checked_out"] = False
        out.append(row)
    return out


def posture() -> dict[str, Any]:
    active = list_active()
    overdue = [r for r in active if r.get("overdue")]
    infinite = [r for r in active if r.get("infinite")]
    return {
        "schema": SCHEMA,
        "updated": _now(),
        "default_days": DEFAULT_DAYS,
        "max_days": MAX_DAYS,
        "zero_means": "infinite",
        "active_count": len(active),
        "overdue_count": len(overdue),
        "infinite_count": len(infinite),
        "active": active,
        "overdue": overdue,
        "ledger_path": str(LEDGER_PATH),
        "policy": "Books never leave the shelf — librarian tracks loans; daily Noti if overdue.",
    }


def _noti_mod() -> Any | None:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("noti_checkout", INSTALL / "lib" / "noti.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        return None
    return None


def run_daily_reminders(*, force: bool = False) -> dict[str, Any]:
    """Emit one Noti per overdue loan per calendar day."""
    noti = _noti_mod()
    if not noti or not hasattr(noti, "ingest_alert"):
        return {"ok": False, "error": "noti_missing"}
    today = _today()
    doc = _active_doc()
    checkouts: dict[str, Any] = doc.get("checkouts") or {}
    sent: list[dict[str, Any]] = []
    for book_id, raw in list(checkouts.items()):
        if not isinstance(raw, dict) or raw.get("status") != "active":
            continue
        rec = enrich_checkout(dict(raw))
        if rec.get("infinite") or not rec.get("overdue"):
            continue
        if not force and str(raw.get("last_reminded") or "") == today:
            continue
        days_over = abs(int(rec.get("days_left") or 0))
        title = rec.get("title") or book_id
        lib_name = (rec.get("librarian") or {}).get("name") or "Librarian"
        msg = (
            f"Library: overdue — please return «{title}» "
            f"({days_over} day{'s' if days_over != 1 else ''} past due). "
            f"{lib_name} is holding your place on the shelf."
        )
        alert = noti.ingest_alert(
            kind="library_overdue",
            message=msg,
            source="h7-library-checkout",
            meta={
                "book_id": book_id,
                "checkout_id": rec.get("id"),
                "due_at": rec.get("due_at"),
                "days_overdue": days_over,
                "librarian": rec.get("librarian"),
            },
        )
        raw["last_reminded"] = today
        raw["reminder_count"] = int(raw.get("reminder_count") or 0) + 1
        checkouts[book_id] = raw
        sent.append({"book_id": book_id, "noti_id": alert.get("noti_id"), "message": msg[:120]})
    if sent:
        _save_active(checkouts)
        _append_ledger("daily_reminders", count=len(sent), book_ids=[s["book_id"] for s in sent])
    return {"ok": True, "date": today, "reminded": len(sent), "items": sent}


def read_ledger(*, limit: int = 50) -> list[dict[str, Any]]:
    if not LEDGER_PATH.is_file():
        return []
    lines = LEDGER_PATH.read_text(encoding="utf-8").splitlines()
    rows: list[dict[str, Any]] = []
    for ln in lines[-limit:]:
        try:
            rows.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return rows


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "posture").strip().lower()
    if cmd in ("posture", "status", "json"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "active":
        print(json.dumps({"ok": True, "active": list_active()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "get" and len(sys.argv) > 2:
        rec = get_checkout(sys.argv[2])
        print(json.dumps({"ok": bool(rec), "checkout": rec}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "checkout" and len(sys.argv) > 2:
        days = DEFAULT_DAYS
        patron = "operator"
        meta = None
        if len(sys.argv) > 3:
            try:
                body = json.loads(sys.argv[3])
                days = body.get("days", days)
                patron = str(body.get("patron") or patron)
                meta = body.get("book") if isinstance(body.get("book"), dict) else None
            except json.JSONDecodeError:
                days = sys.argv[3]
        print(json.dumps(
            checkout_book(sys.argv[2], days=days, patron=patron, book_meta=meta),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd == "checkin" and len(sys.argv) > 2:
        patron = sys.argv[3] if len(sys.argv) > 3 else "operator"
        print(json.dumps(checkin_book(sys.argv[2], patron=patron), ensure_ascii=False, indent=2))
        return 0
    if cmd == "remind":
        force = "--force" in sys.argv
        print(json.dumps(run_daily_reminders(force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ledger":
        lim = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        print(json.dumps({"ok": True, "ledger": read_ledger(limit=lim)}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["posture", "active", "get BOOK", "checkout BOOK [json]", "checkin BOOK", "remind", "ledger"],
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())