#!/usr/bin/env pythong
"""Hostess 7 brain training campus — library study hall + body embodiment zone."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-brain-training-doctrine.json"
PANEL = STATE / "hostess7-brain-training-panel.json"
PROGRESS = STATE / "hostess7-brain-training-progress.json"
LEDGER = STATE / "hostess7-brain-training-ledger.jsonl"


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location("sovereign_clock_btc", _LIB / "sovereign-clock.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "utc_z"):
                return mod.utc_z()
    except Exception:
        pass
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


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any | None:
    import sys

    py = INSTALL / rel
    if not py.is_file():
        py = HOSTESS7 / rel.replace("Hostess7/", "")
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


def _progress_doc() -> dict[str, Any]:
    doc = _load(PROGRESS, {"books": {}, "body_sessions": 0, "brain_sessions": 0})
    doc.setdefault("books", {})
    return doc


def _save_progress(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    _save(PROGRESS, doc)


def _dewey_prefix(book: dict[str, Any]) -> str:
    shelf = str(book.get("shelf") or book.get("dewey") or "")
    m = re.search(r"(\d{3})", shelf)
    if m:
        return m.group(1)
    code = str(book.get("code") or book.get("dewey_code") or "")
    m = re.search(r"(\d{3})", code)
    return m.group(1) if m else "000"


def brain_lane(book: dict[str, Any], *, zone: str = "brain") -> dict[str, Any]:
    doctrine = load_doctrine()
    prefix = _dewey_prefix(book)
    lanes = doctrine.get("brain_lanes") or []
    best = lanes[0] if lanes else {"brain_area": "wernicke", "workspace": "default", "intent": "english"}
    best_p = ""
    for lane in lanes:
        p = str(lane.get("dewey_prefix") or "")
        if prefix.startswith(p) and len(p) >= len(best_p):
            best_p = p
            best = lane
    if zone == "body" or best.get("zone") == "body":
        return {**best, "zone": "body", "workspace": "clinic", "brain_area": "temporal"}
    return {**best, "zone": zone}


def library_stats() -> dict[str, Any]:
    tree = _load(STATE / "field-dewey-library-tree.json", {})
    books = _catalog_books()
    shelves = len(tree.get("shelves") or [])
    if not books:
        counts = (tree.get("counts") or {})
        book_n = int(counts.get("books") or counts.get("h7c_books") or 0)
    else:
        book_n = len(books)
    prog = _progress_doc()
    studied = sum(1 for b in (prog.get("books") or {}).values() if int(b.get("pages_done") or 0) > 0)
    complete = sum(
        1 for b in (prog.get("books") or {}).values()
        if int(b.get("pages_done") or 0) >= int(b.get("page_total") or 1)
    )
    return {
        "book_count": book_n,
        "shelf_count": shelves,
        "books_studied": studied,
        "books_complete": complete,
        "brain_sessions": int(prog.get("brain_sessions") or 0),
        "body_sessions": int(prog.get("body_sessions") or 0),
    }


_CATALOG_CACHE: list[dict[str, Any]] | None = None


def _catalog_from_tree() -> list[dict[str, Any]]:
    tree = _load(STATE / "field-dewey-library-tree.json", {})
    books: list[dict[str, Any]] = []
    for shelf in tree.get("shelves") or []:
        for book in shelf.get("books") or []:
            if book.get("id"):
                books.append({**book, "shelf": shelf.get("slug"), "ready": True})
    return books


def _catalog_books(*, refresh: bool = False) -> list[dict[str, Any]]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None and not refresh:
        return _CATALOG_CACHE
    books = _catalog_from_tree()
    if len(books) < 100:
        dewey = _import_mod("dewey_lib", "lib/field-dewey-library.py")
        if dewey and hasattr(dewey, "glob_books"):
            try:
                books = list(dewey.glob_books())
            except Exception:
                pass
    _CATALOG_CACHE = books
    return books


def study_queue(*, limit: int = 24, zone: str = "brain") -> list[dict[str, Any]]:
    doctrine = load_doctrine()
    priority = list(doctrine.get("priority_collections") or [])
    prog = _progress_doc()
    anatomy_ids = set()
    anatomy_titles: dict[str, str] = {}
    if zone == "body":
        idx = _load(INSTALL / "data" / "hostess7-anatomy-books-index.json", {})
        for b in idx.get("books") or []:
            if b.get("id"):
                anatomy_ids.add(str(b["id"]))
                anatomy_titles[str(b["id"])] = str(b.get("title") or b["id"])

    candidates: list[dict[str, Any]] = []
    for bid in priority:
        candidates.append({"id": bid, "title": bid, "shelf": "", "ready": True})
    for bid in anatomy_ids:
        candidates.append({"id": bid, "title": anatomy_titles.get(bid, bid), "shelf": "611-human-anatomy", "ready": True})
    for bid, row in (prog.get("books") or {}).items():
        if int(row.get("pages_done") or 0) < int(row.get("page_total") or 999999):
            candidates.append({
                "id": bid,
                "title": row.get("title") or bid,
                "shelf": row.get("shelf") or "",
                "ready": True,
            })
    if len(candidates) < limit:
        for b in _catalog_books()[: max(limit * 4, 48)]:
            candidates.append(b)

    seen: set[str] = set()

    def score_book(b: dict[str, Any]) -> tuple[int, int, str]:
        bid = str(b.get("id") or "")
        row = (prog.get("books") or {}).get(bid) or {}
        done = int(row.get("pages_done") or 0)
        total = int(row.get("page_total") or 0)
        pri = priority.index(bid) if bid in priority else 99
        if zone == "body":
            if bid not in anatomy_ids and not str(b.get("shelf") or "").startswith("611"):
                return (999, done, bid)
            return (pri, done, bid)
        if total and done >= total:
            return (999, done, bid)
        return (pri, done, bid)

    ranked: list[dict[str, Any]] = []
    for b in candidates:
        bid = str(b.get("id") or "")
        if not bid or bid in seen:
            continue
        seen.add(bid)
        if b.get("ready", True) or b.get("h7c"):
            ranked.append(b)
    ranked.sort(key=score_book)
    out: list[dict[str, Any]] = []
    for b in ranked[:limit]:
        bid = str(b.get("id") or "")
        lane = brain_lane(b, zone=zone)
        row = (prog.get("books") or {}).get(bid) or {}
        out.append({
            "book_id": bid,
            "title": b.get("title") or bid,
            "shelf": b.get("shelf"),
            "zone": lane.get("zone", zone),
            "brain_area": lane.get("brain_area"),
            "workspace": lane.get("workspace"),
            "pages_done": int(row.get("pages_done") or 0),
            "page_total": int(row.get("page_total") or 0),
        })
    return out


def _callosum_receipt(
    *,
    lane: dict[str, Any],
    book_id: str,
    page: int,
    sentences: list[dict[str, Any]],
) -> dict[str, Any]:
    brain = (
        _import_mod("field_brain_core", "Hostess7/scripts/field_brain_core.py")
        or _import_mod("field_brain_core_h7", str(HOSTESS7 / "scripts" / "field_brain_core.py"))
    )
    if not brain or not hasattr(brain, "callosum_transfer"):
        return {"transferred": False, "reason": "brain_core_unavailable"}
    area = str(lane.get("brain_area") or "wernicke")
    ws = str(lane.get("workspace") or "default")
    hemi = "left"
    for a in getattr(brain, "BRAIN_AREAS", ()) or ():
        if a.get("id") == area:
            hemi = a.get("hemisphere") or "left"
            break
    to_hemi = "right" if hemi == "left" else "left"
    payload = {
        "kind": "library_study",
        "book_id": book_id,
        "page": page,
        "zone": lane.get("zone", "brain"),
        "brain_area": area,
        "workspace": ws,
        "tokens": [s.get("text", "")[:120] for s in sentences[:6]],
        "sealed": sum(1 for s in sentences if s.get("verdict") in ("sealed", "green", "ok")),
    }
    try:
        if hasattr(brain, "set_workspace"):
            brain.set_workspace(ws)
        result = brain.callosum_transfer(hemi, to_hemi, payload, area=area, workspace=ws)
        return {"transferred": True, "packet_id": getattr(result, "packet_id", None), "area": area}
    except Exception as exc:
        return {"transferred": False, "reason": str(exc)[:80]}


def _truth_sentences(book_id: str, page_text: str, *, max_n: int = 3) -> list[dict[str, Any]]:
    truth = _import_mod("h7_truth", "lib/h7-library-truth.py")
    pag = _import_mod("h7_pg", "lib/h7-library-pagination.py")
    sentences: list[str] = []
    if pag and hasattr(pag, "split_sentences"):
        sentences = pag.split_sentences(page_text)
    elif truth and hasattr(truth, "split_sentences"):
        sentences = truth.split_sentences(page_text)
    else:
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", page_text) if len(s.strip()) >= 12][:max_n]

    out: list[dict[str, Any]] = []
    for i, sent in enumerate(sentences[:max_n]):
        row: dict[str, Any] = {"index": i, "text": sent[:400]}
        if truth and hasattr(truth, "score_sentence"):
            try:
                scored = truth.score_sentence(sent, book_id=book_id, index=i)
                row.update({
                    "truth_score": scored.get("truth_score"),
                    "verdict": scored.get("verdict"),
                    "flags": scored.get("flags") or [],
                })
            except Exception:
                row["verdict"] = "unscored"
        else:
            row["verdict"] = "unscored"
        out.append(row)
    return out


def _read_source_text(book_id: str) -> tuple[str, dict[str, Any]]:
    dewey = _import_mod("dewey_lib", "lib/field-dewey-library.py")
    if dewey and hasattr(dewey, "read_h7c_text"):
        try:
            text, header, stats = dewey.read_h7c_text(book_id)
            if text:
                return text, {
                    "id": book_id,
                    "title": (header or {}).get("title") or book_id,
                    "author": (header or {}).get("author") or "",
                    "format": "h7c",
                }
        except Exception:
            pass
    for base in (INSTALL / "lib" / "field-books", STATE / "field-books"):
        for ext in (".txt", ".h7", ".md"):
            path = base / f"{book_id}{ext}"
            if path.is_file():
                try:
                    return path.read_text(encoding="utf-8", errors="replace"), {
                        "id": book_id,
                        "title": book_id.replace("-", " ").title(),
                        "format": ext.lstrip("."),
                    }
                except OSError:
                    pass
    if dewey and hasattr(dewey, "find_h7c"):
        try:
            hit = dewey.find_h7c(book_id, auto_convert=False)
            if hit and hit.is_file():
                h7c = _import_mod("h7c", "lib/field-h7c-compression.py")
                if h7c and hasattr(h7c, "decompress_h7c"):
                    header, text, _stats = h7c.decompress_h7c(hit.read_bytes(), verify=True)
                    if text:
                        return text, {
                            "id": book_id,
                            "title": (header or {}).get("title") or book_id,
                            "format": "h7c",
                        }
        except Exception:
            pass
    return "", {}


def _read_book_page_fast(book_id: str, page: int) -> dict[str, Any]:
    """Direct read + local pagination — avoids full library catalog scan."""
    pag = _import_mod("h7_pg", "lib/h7-library-pagination.py")
    text, meta = _read_source_text(book_id)
    if not text:
        return {"ok": False, "error": "empty_book", "book_id": book_id}
    if pag and hasattr(pag, "paginate_text"):
        pages = pag.paginate_text(text)
    else:
        limit = 3200
        pages = [text[i : i + limit] for i in range(0, max(len(text), 1), limit)] or [""]
    pnum = max(1, min(page, len(pages)))
    return {
        "ok": True,
        "book": meta or {"id": book_id, "title": book_id},
        "page": pnum,
        "page_count": len(pages),
        "text": pages[pnum - 1],
        "char_count": len(text),
    }


def study_page(
    book_id: str,
    page: int = 1,
    *,
    zone: str = "brain",
    pages_to_read: int = 1,
) -> dict[str, Any]:
    if not book_id:
        return {"ok": False, "error": "book_id_required"}

    doctrine = load_doctrine()
    zone_cfg = (doctrine.get("zones") or {}).get(zone) or {}
    max_sent = int(zone_cfg.get("sentences_per_page") or 3)
    pages_to_read = max(1, min(pages_to_read, 4))

    meta_book = {"id": book_id, "shelf": ""}
    cached_meta = _read_source_text(book_id)[1]
    if cached_meta:
        meta_book = {**meta_book, **cached_meta}
    for b in _catalog_books()[:2000]:
        if str(b.get("id")) == book_id:
            meta_book = b
            break
    lane = brain_lane(meta_book, zone=zone)

    results: list[dict[str, Any]] = []
    for offset in range(pages_to_read):
        pnum = page + offset
        try:
            pg = _read_book_page_fast(book_id, pnum)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:80], "book_id": book_id, "page": pnum}
        if not pg.get("ok", True) and pg.get("error"):
            if results:
                break
            return {"ok": False, **pg}
        meta_book = pg.get("book") or meta_book
        lane = brain_lane(meta_book, zone=zone)
        text = str(pg.get("text") or pg.get("page_text") or "")
        page_total = int(pg.get("page_count") or pg.get("pages") or 1)
        sentences = _truth_sentences(book_id, text, max_n=max_sent)
        xfer = _callosum_receipt(lane=lane, book_id=book_id, page=pnum, sentences=sentences)
        results.append({
            "page": pnum,
            "page_total": page_total,
            "char_count": len(text),
            "sentences": sentences,
            "callosum": xfer,
        })

        prog = _progress_doc()
        books = prog.setdefault("books", {})
        row = books.get(book_id) or {"book_id": book_id, "first_study": _now()}
        row["pages_done"] = max(int(row.get("pages_done") or 0), pnum)
        row["page_total"] = page_total
        row["last_page"] = pnum
        row["zone"] = zone
        row["brain_area"] = lane.get("brain_area")
        row["workspace"] = lane.get("workspace")
        row["title"] = meta_book.get("title") or book_id
        row["last_study"] = _now()
        row["sentences_sealed"] = int(row.get("sentences_sealed") or 0) + sum(
            1 for s in sentences if str(s.get("verdict", "")).lower() in ("sealed", "green", "ok", "truth")
        )
        books[book_id] = row
        if zone == "body":
            prog["body_sessions"] = int(prog.get("body_sessions") or 0) + 1
        else:
            prog["brain_sessions"] = int(prog.get("brain_sessions") or 0) + 1
        prog["pages_total_studied"] = int(prog.get("pages_total_studied") or 0) + 1
        _save_progress(prog)

    last = results[-1] if results else {}
    _append({
        "zone": zone,
        "book_id": book_id,
        "pages": [r["page"] for r in results],
        "brain_area": lane.get("brain_area"),
        "workspace": lane.get("workspace"),
    })
    return {
        "ok": True,
        "zone": zone,
        "book_id": book_id,
        "lane": lane,
        "pages_studied": results,
        "page_total": last.get("page_total"),
        "pages_done": last.get("page"),
    }


def study_batch(*, limit: int = 3, zone: str = "brain") -> dict[str, Any]:
    doctrine = load_doctrine()
    zone_cfg = (doctrine.get("zones") or {}).get(zone) or {}
    pages = int(zone_cfg.get("pages_per_session") or 2)
    queue = study_queue(limit=limit, zone=zone)
    sessions: list[dict[str, Any]] = []
    for item in queue[:limit]:
        bid = item.get("book_id")
        if not bid:
            continue
        next_page = int(item.get("pages_done") or 0) + 1
        sess = study_page(bid, next_page, zone=zone, pages_to_read=pages)
        sessions.append(sess)
    ok_n = sum(1 for s in sessions if s.get("ok"))
    return {
        "ok": ok_n > 0,
        "zone": zone,
        "sessions_run": len(sessions),
        "sessions_ok": ok_n,
        "sessions": sessions,
    }


def body_posture() -> dict[str, Any]:
    motion = _load(STATE / "humanoid-motion-panel.json", {})
    body = _load(STATE / "hostess7-body-core-panel.json", {})
    anatomy = _load(INSTALL / "data" / "hostess7-anatomy-books-index.json", {})
    chamber_panel = _load(STATE / "hostess7-training-chamber-panel.json", {})
    return {
        "training_chamber": chamber_panel,
        "humanoid_motion": {
            "active_skill": (_load(STATE / "humanoid-motion-runtime.json", {}).get("active_skill")),
            "proficiency": motion.get("proficiency"),
            "opponents": len(motion.get("opponents") or motion.get("arena_opponents") or []),
        },
        "body_core": {
            "ok": bool(body.get("ok")),
            "joints": len(body.get("joints") or body.get("pose") or {}),
        },
        "anatomy_books": len(anatomy.get("books") or []),
        "gap_count": (chamber_panel.get("needs") or {}).get("gap_count"),
    }


def body_session(*, ticks: int = 32) -> dict[str, Any]:
    """Body zone — anatomy page + embodiment chamber tick."""
    out: dict[str, Any] = {"ok": True, "zone": "body", "steps": []}
    queue = study_queue(limit=1, zone="body")
    if queue:
        bid = queue[0]["book_id"]
        page = int(queue[0].get("pages_done") or 0) + 1
        study = study_page(bid, page, zone="body", pages_to_read=1)
        out["steps"].append({"kind": "anatomy_study", **study})

    chamber = _import_mod("h7_chamber", "lib/hostess7-training-chamber.py")
    if chamber and hasattr(chamber, "build_panel"):
        try:
            panel = chamber.build_panel(write=True)
            out["steps"].append({"kind": "embodiment_panel", "gap_count": panel.get("gap_count")})
        except Exception:
            pass

    motion = _import_mod("humanoid_motion", "lib/humanoid-motion-training.py")
    if motion and hasattr(motion, "train_tick"):
        try:
            tick = motion.train_tick(ticks=ticks)
            out["steps"].append({"kind": "motion_tick", "ok": bool(tick)})
        except Exception:
            pass

    out["posture"] = body_posture()
    _append({"zone": "body", "event": "body_session", "steps": len(out["steps"])})
    return out


def campus_session(*, brain_books: int = 2, body: bool = True, pack_h7b: bool = False) -> dict[str, Any]:
    """Full campus cycle — brain batch then body."""
    brain = study_batch(limit=brain_books, zone="brain")
    body_out = body_session() if body else {"ok": True, "skipped": True}
    h7b_out: dict[str, Any] = {"skipped": True}
    if pack_h7b:
        h7b = _import_mod("h7b_brain", "lib/field-h7b-brain-storage.py")
        if h7b and hasattr(h7b, "pack_brain"):
            try:
                h7b_out = h7b.pack_brain(write=True)
            except Exception as exc:
                h7b_out = {"ok": False, "error": str(exc)[:120]}
        else:
            h7b_out = {"ok": False, "error": "h7b_brain_module_missing"}
    return {
        "ok": bool(brain.get("ok") or body_out.get("ok")),
        "brain": brain,
        "body": body_out,
        "h7b": h7b_out,
        "stats": library_stats(),
    }


def assess_track() -> dict[str, Any]:
    stats = library_stats()
    prog = _progress_doc()
    book_count = max(stats.get("book_count") or 1, 1)
    studied = stats.get("books_studied") or 0
    complete = stats.get("books_complete") or 0
    brain_sess = int(stats.get("brain_sessions") or 0)
    body_sess = int(stats.get("body_sessions") or 0)
    pages = int(prog.get("pages_total_studied") or 0)

    brain_score = min(1.0, (studied / min(book_count, 200)) * 0.4 + min(pages / 100, 1.0) * 0.4 + min(brain_sess / 20, 1.0) * 0.2)
    body_score = min(1.0, body_sess / 10.0)
    posture = body_posture()
    gap = int(posture.get("gap_count") or 99)
    if gap <= 2:
        body_score = min(1.0, body_score + 0.25)
    score = round(brain_score * 0.65 + body_score * 0.35, 4)

    complete_thresh = studied >= 5 and pages >= 20 and body_sess >= 1
    mastered = studied >= 25 and pages >= 200 and body_sess >= 5 and gap <= 1

    def _level() -> str:
        if mastered:
            return "mastered"
        if complete_thresh or score >= 0.92:
            return "complete"
        if score >= 0.2 or brain_sess > 0:
            return "training"
        return "pending"

    level = _level()
    return {
        "ok": True,
        "level": level,
        "complete": level in ("complete", "mastered"),
        "mastered": mastered,
        "score": score,
        "brain_score": round(brain_score, 4),
        "body_score": round(body_score, 4),
        "book_count": book_count,
        "books_studied": studied,
        "books_complete": complete,
        "pages_studied": pages,
        "brain_sessions": brain_sess,
        "body_sessions": body_sess,
        "body_gap_count": gap,
        "pass_rate": round(score * 100, 1),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = load_doctrine()
    stats = library_stats()
    assess = assess_track()
    doc = {
        "schema": "hostess7-brain-training-panel/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "api": doctrine.get("api"),
        "ui": doctrine.get("ui"),
        "zones": doctrine.get("zones"),
        "ok": assess.get("complete", False),
        "assessment": assess,
        "stats": stats,
        "brain_queue": study_queue(limit=12, zone="brain"),
        "body_queue": study_queue(limit=8, zone="body"),
        "body_posture": body_posture(),
        "summary": (
            f"Campus: {stats.get('book_count', 0)} books · "
            f"{stats.get('books_studied', 0)} studied · "
            f"{assess.get('pages_studied', 0)} pages · "
            f"brain {assess.get('brain_sessions', 0)} / body {assess.get('body_sessions', 0)} sessions"
        ),
    }
    if write:
        _save(PANEL, doc)
        _append({"event": "panel", "score": assess.get("score"), "level": assess.get("level")})
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    zone = str(body.get("zone") or "brain").strip().lower()

    if action in ("panel", "status", "json"):
        return {"ok": True, **build_panel(write=True)}
    if action in ("stats", "catalog"):
        return {"ok": True, "stats": library_stats()}
    if action == "queue":
        return {"ok": True, "queue": study_queue(limit=int(body.get("limit") or 24), zone=zone)}
    if action in ("study", "study_page"):
        return study_page(
            str(body.get("book_id") or body.get("book") or ""),
            int(body.get("page") or 1),
            zone=zone,
            pages_to_read=int(body.get("pages") or body.get("pages_to_read") or 1),
        )
    if action in ("batch", "study_batch"):
        return study_batch(limit=int(body.get("limit") or 3), zone=zone)
    if action == "body_session":
        return body_session(ticks=int(body.get("ticks") or 32))
    if action in ("campus", "session", "cycle"):
        return campus_session(
            brain_books=int(body.get("brain_books") or body.get("limit") or 2),
            body=bool(body.get("body", True)),
        )
    if action == "assess":
        return {"ok": True, "assessment": assess_track()}
    if action == "body_posture":
        return {"ok": True, "posture": body_posture()}
    return {"ok": False, "error": "unknown_action", "action": action}


def format_output(doc: dict[str, Any] | None = None) -> str:
    doc = doc or build_panel(write=False)
    aw = doc.get("assessment") or {}
    lines = [
        "=== Hostess 7 — Brain Training Campus ===",
        f"Updated: {doc.get('updated', '—')}",
        f"Summary: {doc.get('summary', '')}",
        "",
        "— Brain study hall (library) —",
        f"  Books on shelf: {aw.get('book_count', '—')}",
        f"  Studied: {aw.get('books_studied', 0)} · Pages: {aw.get('pages_studied', 0)}",
        f"  Brain sessions: {aw.get('brain_sessions', 0)} · Score: {aw.get('brain_score', '—')}",
        "",
        "— Body & other embodiment —",
        f"  Body sessions: {aw.get('body_sessions', 0)} · Score: {aw.get('body_score', '—')}",
        f"  Training chamber gaps: {aw.get('body_gap_count', '—')}",
        "",
        "— Next brain queue —",
    ]
    for q in (doc.get("brain_queue") or [])[:8]:
        lines.append(f"  {q.get('title')} · {q.get('brain_area')} · p{q.get('pages_done', 0)}/{q.get('page_total') or '?'}")
    lines.extend(["", "— Next body queue —"])
    for q in (doc.get("body_queue") or [])[:6]:
        lines.append(f"  {q.get('title')} · anatomy/body · p{q.get('pages_done', 0)}/{q.get('page_total') or '?'}")
    lines.append("")
    lines.append("Doctrine: data/hostess7-brain-training-doctrine.json")
    return "\n".join(lines)


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Hostess 7 brain training campus")
    parser.add_argument("cmd", nargs="?", default="panel")
    parser.add_argument("--book", dest="book_id", default="")
    parser.add_argument("--page", type=int, default=1)
    parser.add_argument("--zone", default="brain")
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("assess", "assessment"):
        print(json.dumps(assess_track(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "stats":
        print(json.dumps(library_stats(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "queue":
        print(json.dumps(study_queue(limit=args.limit, zone=args.zone), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("study", "page"):
        if not args.book_id:
            print(json.dumps({"ok": False, "error": "book_id required"}, ensure_ascii=False))
            return 1
        print(json.dumps(study_page(args.book_id, args.page, zone=args.zone), ensure_ascii=False, indent=2))
        return 0
    if cmd == "batch":
        print(json.dumps(study_batch(limit=args.limit, zone=args.zone), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("body", "body_session"):
        print(json.dumps(body_session(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("campus", "cycle", "session"):
        print(json.dumps(campus_session(brain_books=args.limit), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("output", "text"):
        print(format_output())
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            body = {}
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-brain-training-chamber.py [panel|assess|queue|study|batch|body|campus|output]",
        "api": "/api/hostess7/brain-training",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())