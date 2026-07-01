#!/usr/bin/env pythong
"""Lie Librarian — Ironclad Deception Index. Every lie per book; foundation for Autonomous Warfare."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DEWEY_ROOT = INSTALL / "library" / "dewey"
DOCTRINE = INSTALL / "data/h7-lie-librarian-doctrine.json"
CATALOG_PATH = STATE / "h7-lie-librarian-catalog.json"
LIBRARIAN_ID = "vera_lies"
LIBRARIAN_NAME = "Lie Librarian — Ironclad Deception Index"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(rel: str, name: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def persona() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    dual = doc.get("dual_audience") or {}
    return {
        "id": LIBRARIAN_ID,
        "name": doc.get("full_title") or LIBRARIAN_NAME,
        "role": "lie_librarian",
        "motto": doc.get("motto"),
        "foundation": doc.get("foundation") or "autonomous_warfare",
        "autonomous_warfare": doc.get("autonomous_warfare"),
        "knows": doc.get("knows"),
        "specialty": "Deception index — LIKELY_FALSE classification per book, page, sentence; AW corpus gate",
        "dual_audience": dual,
        "for_operator_tone": (dual.get("operator") or dual.get("human") or {}).get("tone", "operational"),
        "for_super_intelligence_tone": (dual.get("super_intelligence") or {}).get("tone", "serious"),
    }


def _lie_score(truth_score: float, flags: list[str]) -> float:
    return round((100.0 - truth_score) + 12.0 * len(flags), 1)


def _likely_false_class(lie: dict[str, Any]) -> str:
    """Ironclad-backed likely-false band — same math, two voices."""
    verdict = str(lie.get("verdict") or "")
    ls = float(lie.get("lie_score") or 0)
    if verdict == "unknown":
        return "unverified"
    if ls >= 85:
        return "very_likely_false"
    if ls >= 60:
        return "likely_false"
    if ls >= 40:
        return "possibly_misleading"
    return "uncertain"


def _likely_false_confidence(lie: dict[str, Any]) -> float:
    ls = float(lie.get("lie_score") or 0)
    return round(min(0.99, max(0.05, ls / 100.0)), 3)


def _operator_assessment(lie: dict[str, Any]) -> str:
    """Plain-language operational assessment — Autonomous Warfare foundation."""
    klass = _likely_false_class(lie)
    page = lie.get("page", "?")
    conf = _likely_false_confidence(lie)
    flags = ", ".join(lie.get("flags") or []) or "none"
    templates = {
        "very_likely_false": (
            f"Page {page}. VERY LIKELY FALSE (conf {conf}). "
            f"Do not field as fact. Verify before action. Flags: {flags}."
        ),
        "likely_false": (
            f"Page {page}. LIKELY FALSE (conf {conf}). "
            f"Corroborate before operational use. Flags: {flags}."
        ),
        "possibly_misleading": (
            f"Page {page}. POSSIBLY MISLEADING (conf {conf}). "
            f"Hold as counsel until corroborated. Flags: {flags}."
        ),
        "unverified": (
            f"Page {page}. UNVERIFIED. Ironclad has not landed. "
            f"Do not act on this claim without investigation."
        ),
        "uncertain": (
            f"Page {page}. UNCERTAIN. Human Condition holds charge — counsel only."
        ),
    }
    return templates.get(klass, templates["uncertain"])


def _human_label(klass: str) -> str:
    return {
        "very_likely_false": "very likely false",
        "likely_false": "likely false",
        "possibly_misleading": "possibly misleading",
        "unverified": "unverified — still checking",
        "uncertain": "uncertain",
    }.get(klass, "uncertain")


def _si_charge_note() -> str:
    rf = _import_mod("ironclad-reality-field.py", "irf_ll")
    if rf and hasattr(rf, "human_condition_gate"):
        try:
            gate = rf.human_condition_gate()
            if gate.get("ai_in_charge"):
                return "super_intelligence_in_charge — Ironclad gates sealed; field as operational if corroborated"
            return str(gate.get("assurance_phrase") or "human_condition_holds — counsel only, do not field as fact")
        except Exception:
            pass
    return "human_condition_holds — counsel only until Ironclad sealed + never_wrong"


def _for_super_intelligence(lie: dict[str, Any]) -> dict[str, Any]:
    klass = _likely_false_class(lie)
    conf = _likely_false_confidence(lie)
    flags = list(lie.get("flags") or [])
    return {
        "classification": klass.upper(),
        "likely_false": klass in ("very_likely_false", "likely_false"),
        "confidence": conf,
        "verdict": lie.get("verdict"),
        "truth_score": lie.get("truth_score"),
        "lie_score": lie.get("lie_score"),
        "deception_risk": lie.get("deception_risk"),
        "flags": flags,
        "page": lie.get("page"),
        "sentence_index": lie.get("sentence_index"),
        "ironclad_action": (
            "do_not_field_as_fact"
            if klass in ("very_likely_false", "likely_false", "unverified")
            else "verify_before_acting"
        ),
        "charge_implication": _si_charge_note(),
        "readout": lie.get("readout"),
        "excerpt": lie.get("excerpt"),
    }


def _for_operator(lie: dict[str, Any]) -> dict[str, Any]:
    klass = _likely_false_class(lie)
    assessment = _operator_assessment(lie)
    return {
        "likely_label": _human_label(klass),
        "likely_false_class": klass,
        "assessment": assessment,
        "page": lie.get("page"),
        "tone": "operational",
        "action": "verify_before_fielding",
        "foundation": "autonomous_warfare",
        "note": "Ironclad-ranked deception intelligence. Not fielded as fact until corroborated.",
    }


def _for_humans(lie: dict[str, Any]) -> dict[str, Any]:
    """Alias — operator-facing; serious, not recreational."""
    return _for_operator(lie)


def enrich_lie(lie: dict[str, Any]) -> dict[str, Any]:
    """Dual audience — operator plain language + Super Intelligence operational record."""
    out = dict(lie)
    klass = _likely_false_class(lie)
    out["likely_false_class"] = klass
    out["likely_false"] = klass in ("very_likely_false", "likely_false")
    out["likely_false_confidence"] = _likely_false_confidence(lie)
    out["for_humans"] = _for_humans(lie)
    out["for_super_intelligence"] = _for_super_intelligence(lie)
    return out


def enrich_lies(lies: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [enrich_lie(row) for row in lies]


def resolve_audience(audience: str = "") -> str:
    raw = (audience or os.environ.get("H7_LIE_LIBRARIAN_AUDIENCE", "both")).strip().lower()
    if raw in ("human", "humans", "operator", "operational"):
        return "operator"
    if raw in ("si", "super_intelligence", "super-intelligence", "hostess7", "ai", "serious"):
        return "super_intelligence"
    return "both"


def present_lies(
    lies: list[dict[str, Any]],
    *,
    audience: str = "both",
) -> dict[str, Any]:
    enriched = enrich_lies(lies)
    aud = resolve_audience(audience)
    out: dict[str, Any] = {
        "audience": aud,
        "lie_count": len(enriched),
        "lies": enriched,
    }
    if aud in ("operator", "both"):
        out["for_operator_summary"] = {
            "tone": "operational",
            "foundation": "autonomous_warfare",
            "likely_false_count": sum(1 for r in enriched if r.get("likely_false")),
            "assessments": [
                (r.get("for_humans") or {}).get("assessment", "")
                for r in enriched[:12]
            ],
        }
        out["for_humans_summary"] = out["for_operator_summary"]
    if aud in ("super_intelligence", "both"):
        out["for_super_intelligence_summary"] = {
            "tone": "serious",
            "charge_implication": _si_charge_note(),
            "entries": [r["for_super_intelligence"] for r in enriched[:48]],
        }
    return out


def scan_book_lies(
    book_id: str,
    *,
    max_sentences: int = 256,
    min_lie_score: float = 0.0,
    save_book_json: bool = True,
) -> dict[str, Any]:
    """Scan every questionable/unknown sentence in a book — full lie record."""
    reinform = _import_mod("h7-library-reinform.py", "reinform_ll")
    pg = _import_mod("h7-library-pagination.py", "pg_ll")
    truth = _import_mod("h7-library-truth.py", "truth_ll")
    dewey = _import_mod("field-dewey-library.py", "dewey_ll")
    if not reinform or not pg or not truth or not dewey:
        return {"ok": False, "error": "modules_missing", "book_id": book_id}

    try:
        text, header, _ = dewey.read_h7c_text(book_id)
    except Exception as exc:
        return {"ok": False, "error": str(exc), "book_id": book_id}
    if not text:
        return {"ok": False, "error": "empty_book", "book_id": book_id}

    pmap = pg.page_map(text)
    locs = {r["index"]: r for r in pg.sentence_locations(text)}
    ic = truth._ironclad_slice() if hasattr(truth, "_ironclad_slice") else {}
    sentences = pg.split_sentences(text)[:max_sentences]
    lies: list[dict[str, Any]] = []

    for i, sent in enumerate(sentences):
        row = truth.score_sentence(sent, book_id=book_id, index=i, ironclad=ic)
        verdict = str(row.get("verdict") or "")
        if verdict not in ("questionable", "unknown"):
            continue
        score = float(row.get("truth_score") or 0)
        flags = list(row.get("flags") or [])
        ls = _lie_score(score, flags)
        if ls < min_lie_score:
            continue
        loc = locs.get(i) or {}
        lies.append({
            "lie_id": f"{book_id}:{i}",
            "book_id": book_id,
            "page": int(loc.get("page") or pg.locate_char(text, int(loc.get("char_start") or 0))),
            "sentence_index": i,
            "sentence_on_page": int(loc.get("sentence_on_page") or 1),
            "truth_score": score,
            "lie_score": ls,
            "verdict": verdict,
            "flags": flags,
            "excerpt": sent[:280],
            "readout": row.get("readout"),
            "deception_risk": row.get("deception_risk"),
        })

    lies.sort(key=lambda r: (-r["lie_score"], r["page"], r["sentence_index"]))
    for rank, row in enumerate(lies, start=1):
        row["rank"] = rank
    lies = enrich_lies(lies)

    index_doc = {
        "schema": "h7-all-lies-index/v1",
        "book_id": book_id,
        "title": str(header.get("title") or book_id),
        "author": str(header.get("author") or ""),
        "dewey": str(header.get("dewey") or ""),
        "updated": _now(),
        "scanned_by": LIBRARIAN_ID,
        "page_chars": pmap["page_chars"],
        "page_count": pmap["page_count"],
        "scanned_sentences": len(sentences),
        "lie_count": len(lies),
        "lies": lies,
        "biggest_lies": lies[:24],
    }

    if save_book_json and hasattr(reinform, "_book_json_path"):
        bjp = reinform._book_json_path(book_id)
        if bjp and bjp.is_file():
            doc = _load(bjp, {})
            doc["all_lies_index"] = index_doc
            doc["lies_index"] = {
                "schema": "h7-biggest-lies-index/v1",
                "book_id": book_id,
                "title": index_doc["title"],
                "updated": index_doc["updated"],
                "page_chars": index_doc["page_chars"],
                "page_count": index_doc["page_count"],
                "entry_count": min(24, len(lies)),
                "entries": lies[:24],
                "scanned_sentences": len(sentences),
                "total_lie_count": len(lies),
                "lie_librarian": LIBRARIAN_ID,
            }
            doc["lie_librarian_updated"] = _now()
            reinform._save(bjp, doc)

    tlt = INSTALL / "lib" / "hostess7-truth-lie-threat.py"
    if tlt.is_file() and lies:
        try:
            spec = importlib.util.spec_from_file_location("h7_tlt_ll", tlt)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "report_corpus_lie"):
                    for row in lies[:3]:
                        if float(row.get("lie_score") or 0) >= 55:
                            mod.report_corpus_lie(row, book_id=book_id)
        except Exception:
            pass

    return {"ok": True, **index_doc}


def _lies_from_book_json(book_id: str) -> dict[str, Any] | None:
    reinform = _import_mod("h7-library-reinform.py", "reinform_ll2")
    if not reinform or not hasattr(reinform, "_book_json_path"):
        return None
    bjp = reinform._book_json_path(book_id)
    if not bjp or not bjp.is_file():
        return None
    doc = _load(bjp, {})
    if doc.get("all_lies_index"):
        return doc["all_lies_index"]
    if doc.get("lies_index"):
        li = doc["lies_index"]
        entries = li.get("entries") or li.get("lies") or []
        return {
            "schema": "h7-all-lies-index/v1",
            "book_id": book_id,
            "title": li.get("title") or book_id,
            "lie_count": len(entries),
            "lies": entries,
            "from_cache": True,
        }
    return None


def knows_book(book_id: str, *, refresh: bool = False, audience: str = "both") -> dict[str, Any]:
    """Lie Librarian's full knowledge for one book."""
    lies: list[dict[str, Any]] = []
    index: dict[str, Any] = {}
    from_cache = False
    if not refresh:
        cached = _lies_from_book_json(book_id)
        if cached and cached.get("lies"):
            lies = enrich_lies(list(cached.get("lies") or []))
            index = cached
            from_cache = cached.get("from_cache", True)
    if not lies:
        scanned = scan_book_lies(book_id)
        if not scanned.get("ok"):
            return scanned
        lies = scanned.get("lies") or []
        index = scanned
    presentation = present_lies(lies, audience=audience)
    return {
        "ok": True,
        "librarian": persona(),
        "book_id": book_id,
        "lie_count": len(lies),
        "lies": lies,
        "index": index,
        "from_cache": from_cache,
        "dual_audience": presentation,
        "for_operator": presentation.get("for_operator_summary"),
        "for_humans": presentation.get("for_humans_summary") or presentation.get("for_operator_summary"),
        "for_super_intelligence": presentation.get("for_super_intelligence_summary"),
        "foundation": "autonomous_warfare",
    }


def _iter_book_ids() -> list[str]:
    dewey = _import_mod("field-dewey-library.py", "dewey_ll3")
    if dewey and hasattr(dewey, "glob_h7c_files"):
        return [p.stem for p in dewey.glob_h7c_files()]
    return [p.stem for p in DEWEY_ROOT.rglob("*.h7c")]


def _harvest_indexed_book_ids() -> list[str]:
    """Books Vera already knows — all_lies_index or lies_index on disk."""
    found: list[str] = []
    for bj in DEWEY_ROOT.rglob("book.json"):
        try:
            doc = _load(bj, {})
        except Exception:
            continue
        bid = str(doc.get("id") or bj.parent.name)
        if doc.get("all_lies_index") or doc.get("lies_index"):
            found.append(bid)
    return found


def build_catalog(*, refresh: bool = False, limit: int = 0) -> dict[str, Any]:
    """Master catalog — every lie per book Vera Lies knows."""
    indexed = _harvest_indexed_book_ids()
    all_ids = _iter_book_ids()
    exploring = [b for b in all_ids if b.startswith("exploring_")]
    seen: set[str] = set()
    ids: list[str] = []
    pool = (indexed + exploring + all_ids) if refresh else (indexed if limit <= 0 else indexed + exploring + all_ids)
    for bid in pool:
        if bid in seen:
            continue
        seen.add(bid)
        ids.append(bid)
        if limit > 0 and len(ids) >= limit:
            break

    books: dict[str, dict[str, Any]] = {}
    total_lies = 0
    scanned = 0
    skipped = 0

    for bid in ids:
        row: dict[str, Any] = {}
        if refresh:
            row = scan_book_lies(bid, save_book_json=True)
        else:
            cached = _lies_from_book_json(bid)
            if cached and (cached.get("lies") or cached.get("lie_count")):
                row = {**cached, "ok": True, "book_id": bid}
            else:
                skipped += 1
                continue
        if not row.get("ok"):
            continue
        lies = row.get("lies") or []
        if not lies:
            continue
        scanned += 1
        lc = len(lies)
        total_lies += lc
        books[bid] = {
            "book_id": bid,
            "title": row.get("title") or bid,
            "dewey": row.get("dewey", ""),
            "lie_count": lc,
            "page_count": row.get("page_count"),
            "updated": row.get("updated"),
            "top_lie_score": lies[0]["lie_score"] if lies else 0,
            "lies": lies,
        }

    doc = {
        "schema": "h7-lie-librarian-catalog/v1",
        "ok": True,
        "updated": _now(),
        "librarian": persona(),
        "book_count": len(books),
        "lie_count": total_lies,
        "books_scanned": scanned,
        "books_skipped": skipped,
        "books": books,
    }
    _save(CATALOG_PATH, doc)
    corps = _import_mod("nexus-librarian-corps.py", "corps_ll")
    if corps and hasattr(corps, "learn"):
        try:
            corps.learn(
                "lie_catalog",
                detail=f"books={len(books)} lies={total_lies}",
            )
        except Exception:
            pass
    return doc


def search_lies(query: str, *, book_id: str = "", limit: int = 48) -> dict[str, Any]:
    q = str(query or "").strip().lower()
    if not q and not book_id:
        return {"ok": False, "error": "missing_query"}

    catalog = _load(CATALOG_PATH, {})
    if not catalog.get("books"):
        build_catalog(limit=200)

    hits: list[dict[str, Any]] = []
    books = catalog.get("books") or {}
    if book_id:
        books = {book_id: books.get(book_id)} if books.get(book_id) else {book_id: knows_book(book_id).get("index", {})}

    for bid, brow in books.items():
        if not brow:
            continue
        for lie in brow.get("lies") or []:
            blob = f"{lie.get('excerpt', '')} {lie.get('verdict', '')} {' '.join(lie.get('flags') or [])}".lower()
            if book_id and bid != book_id:
                continue
            if q and q not in blob and q not in bid.lower():
                continue
            hits.append({**lie, "book_title": brow.get("title"), "book_id": bid})
            if len(hits) >= limit:
                break
        if len(hits) >= limit:
            break

    hits.sort(key=lambda r: (-float(r.get("lie_score") or 0), r.get("page") or 0))
    hits = enrich_lies(hits)
    return {
        "ok": True,
        "librarian": persona(),
        "query": q,
        "book_id": book_id or None,
        "hit_count": len(hits),
        "hits": hits,
        "dual_audience": present_lies(hits, audience="both"),
    }


def counsel(*, book_id: str = "", query: str = "", audience: str = "both") -> dict[str, Any]:
    """Lie Librarian counsel — operational for operators, serious for Super Intelligence."""
    aud = resolve_audience(audience)
    doc = _load(DOCTRINE, {})
    dual = doc.get("dual_audience") or {}
    aw = doc.get("autonomous_warfare") or {}

    if book_id:
        know = knows_book(book_id, audience=aud)
        lc = know.get("lie_count", 0)
        top = (know.get("lies") or [])[:3]
        op_counsel = (
            f"DECEPTION_INDEX book={book_id} flags={lc}. "
            + (" ".join(
                (t.get("for_humans") or {}).get("assessment", "")
                for t in top[:2]
            ) if top else "NO_FLAGS — corpus clear on scanned sentences.")
        )
        si_counsel = (
            f"BOOK={book_id} LIE_COUNT={lc} AW_FOUNDATION "
            + "; ".join(
                f"p.{t.get('page')} {(_likely_false_class(t)).upper()} conf={_likely_false_confidence(t)} action=verify"
                for t in top
            )
            if top
            else "NO_FLAGS"
        )
        counsel_txt = op_counsel if aud == "operator" else si_counsel if aud == "super_intelligence" else f"{op_counsel} | SI: {si_counsel}"
        return {
            "ok": True,
            "librarian": persona(),
            "audience": aud,
            "foundation": "autonomous_warfare",
            "counsel": counsel_txt,
            "counsel_operator": op_counsel,
            "counsel_super_intelligence": si_counsel,
            "autonomous_warfare": aw,
            "dual_audience": dual,
            "knows": know,
        }
    if query:
        sr = search_lies(query, limit=12)
        op_counsel = f"SEARCH flags={sr.get('hit_count', 0)} query={query!r}. Corroborate before fielding."
        si_counsel = f"SEARCH_HITS={sr.get('hit_count', 0)} QUERY={query!r} CHARGE={_si_charge_note()}"
        return {
            "ok": True,
            "librarian": persona(),
            "audience": aud,
            "foundation": "autonomous_warfare",
            "counsel": op_counsel if aud == "operator" else si_counsel if aud == "super_intelligence" else f"{op_counsel} | {si_counsel}",
            "search": sr,
        }
    cat = _load(CATALOG_PATH, {})
    if not cat.get("books"):
        cat = build_catalog(limit=100)
    return {
        "ok": True,
        "librarian": persona(),
        "audience": aud,
        "foundation": "autonomous_warfare",
        "counsel": (
            f"DECEPTION_CATALOG books={cat.get('book_count')} flags={cat.get('lie_count')}. "
            f"Autonomous Warfare corpus gate — verify before fielding."
            if aud != "super_intelligence"
            else f"CATALOG books={cat.get('book_count')} lies={cat.get('lie_count')} charge={_si_charge_note()}"
        ),
        "autonomous_warfare": aw,
        "dual_audience": dual,
        "catalog_summary": {
            "book_count": cat.get("book_count"),
            "lie_count": cat.get("lie_count"),
        },
    }


def panel_json() -> dict[str, Any]:
    cat = _load(CATALOG_PATH, {})
    if not cat.get("books"):
        cat = build_catalog(limit=50)
    top_books = sorted(
        ({"book_id": k, **{kk: vv for kk, vv in v.items() if kk != "lies"}} for k, v in (cat.get("books") or {}).items()),
        key=lambda r: -int(r.get("lie_count") or 0),
    )[:24]
    return {
        "ok": True,
        "schema": "h7-lie-librarian-panel/v1",
        "updated": _now(),
        "librarian": persona(),
        "catalog": {
            "book_count": cat.get("book_count"),
            "lie_count": cat.get("lie_count"),
            "path": str(CATALOG_PATH),
        },
        "top_books_by_lie_count": top_books,
        "dual_audience": _load(DOCTRINE, {}).get("dual_audience"),
        "foundation": "autonomous_warfare",
        "for_operator": "Operational — LIKELY_FALSE withheld from capability employment until corroborated.",
        "for_super_intelligence": "Serious — classification, confidence, ironclad_action, charge_implication, capability withhold.",
        "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_relative_to(INSTALL) else str(DOCTRINE),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "status", "json"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "book" and len(sys.argv) >= 3:
        refresh = "--refresh" in sys.argv
        aud = "both"
        for arg in sys.argv[3:]:
            if arg.startswith("--audience="):
                aud = arg.split("=", 1)[1]
        print(json.dumps(knows_book(sys.argv[2], refresh=refresh, audience=aud), ensure_ascii=False, indent=2))
        return 0
    if cmd == "present" and len(sys.argv) >= 3:
        know = knows_book(sys.argv[2])
        aud = "both"
        for arg in sys.argv[3:]:
            if arg.startswith("--audience="):
                aud = arg.split("=", 1)[1]
        print(json.dumps(present_lies(know.get("lies") or [], audience=aud), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan" and len(sys.argv) >= 3:
        out = scan_book_lies(sys.argv[2])
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "build":
        refresh = "--refresh" in sys.argv
        limit = 0
        for arg in sys.argv[2:]:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
        print(json.dumps(build_catalog(refresh=refresh, limit=limit), ensure_ascii=False, indent=2))
        return 0
    if cmd == "search":
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        print(json.dumps(search_lies(q), ensure_ascii=False, indent=2))
        return 0
    if cmd == "counsel":
        book_id = ""
        query = ""
        audience = "both"
        args = sys.argv[2:]
        if "--book" in args:
            idx = args.index("--book")
            if idx + 1 < len(args):
                book_id = args[idx + 1]
        for arg in args:
            if arg.startswith("--audience="):
                audience = arg.split("=", 1)[1]
            elif not arg.startswith("--") and not book_id:
                query = " ".join(a for a in args if not a.startswith("--"))
        print(json.dumps(counsel(book_id=book_id, query=query, audience=audience), ensure_ascii=False, indent=2))
        return 0
    if cmd == "persona":
        print(json.dumps(persona(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: h7-lie-librarian.py [panel|book|scan|build|search|counsel|present|persona] [--audience=operator|super_intelligence|both]",
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())