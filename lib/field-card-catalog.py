#!/usr/bin/env python3
"""Field Card Catalog — auto book detection, keyword placement, sort & search for librarians."""
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
DOCTRINE = INSTALL / "data" / "field-card-catalog-doctrine.json"
DEWEY_ROOT = INSTALL / "library" / "dewey"
DEWEY_TREE = INSTALL / "data" / "dewey-full-tree.json"
PANEL = STATE / "field-card-catalog-panel.json"
CATALOG = STATE / "field-card-catalog.json"
KEYWORDS_INDEX = STATE / "field-card-catalog-keywords.json"

CATALOG_SHELF_DIR = DEWEY_ROOT / "020-library-science" / "card-catalog"
CATALOG_JSON = CATALOG_SHELF_DIR / "catalog.json"

STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for", "by", "with",
    "from", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "will", "would", "could", "should", "may", "might", "must",
    "shall", "can", "this", "that", "these", "those", "it", "its", "as", "but", "not",
    "no", "nor", "so", "yet", "both", "either", "neither", "each", "every", "all",
    "any", "few", "more", "most", "other", "some", "such", "than", "too", "very",
    "just", "also", "into", "over", "after", "before", "between", "under", "again",
    "further", "then", "once", "here", "there", "when", "where", "why", "how", "what",
    "which", "who", "whom", "book", "edition", "volume", "guide", "manual",
})

DEWEY_HEADINGS: dict[str, str] = {
    "000": "Computer science, information & general works",
    "004": "Data processing & computer science",
    "005": "Computer programming, programs & data",
    "020": "Library & information sciences",
    "100": "Philosophy & psychology",
    "133": "Parapsychology & occult sciences",
    "200": "Religion",
    "300": "Social sciences",
    "320": "Political science",
    "355": "Military science",
    "370": "Education",
    "400": "Language",
    "500": "Science",
    "510": "Mathematics",
    "600": "Technology",
    "613": "Personal health & safety",
    "621": "Applied physics & engineering",
    "700": "Arts & recreation",
    "780": "Music",
    "794": "Indoor games & amusements",
    "800": "Literature & rhetoric",
    "900": "History & geography",
    "920": "Biography & genealogy",
    "940": "History of Europe",
    "973": "History of United States",
}

SEARCH_BLOB_FIELDS: tuple[str, ...] = (
    "card_id", "id", "call_number", "title", "subtitle", "author",
    "dewey", "dewey_label", "shelf", "shelf_title", "collection",
    "format", "subject", "category", "description", "motto",
    "ein", "isbn_13", "isbn_10", "publisher", "grade_band",
    "ironclad_citation", "source", "location",
)

SORT_MODES: tuple[str, ...] = (
    "call_number", "title", "author", "collection", "shelf", "format", "relevance",
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(INSTALL.resolve()))
    except ValueError:
        return str(path)


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _dewey_label(code: str) -> str:
    c = str(code or "").strip()
    if not c:
        return ""
    main = re.sub(r"[^0-9].*", "", c)[:3]
    return DEWEY_HEADINGS.get(main) or DEWEY_HEADINGS.get(c[:3], "")


def _dewey_sort_key(call_number: str) -> tuple:
    raw = str(call_number or "999").strip()
    parts = re.split(r"[^0-9]+", raw)
    nums: list[int] = []
    for p in parts:
        if p:
            try:
                nums.append(int(p))
            except ValueError:
                pass
    while len(nums) < 4:
        nums.append(0)
    return tuple(nums[:6])


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if len(t) > 1 and t not in STOP_WORDS]


def _card_id(book_id: str, dewey: str) -> str:
    dew = re.sub(r"[^0-9A-Za-z]", "", str(dewey or "000"))[:6] or "000"
    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(book_id or "unknown")).strip("-").upper()[:24]
    return f"CAT-{dew}-{slug}"


def _shelf_slug(book_dir: Path) -> str:
    try:
        rel = book_dir.parent.relative_to(DEWEY_ROOT)
        return str(rel).replace("\\", "/")
    except ValueError:
        return book_dir.parent.name


def _keyword_placement(row: dict[str, Any]) -> tuple[list[str], dict[str, list[str]]]:
    """Place keywords on catalog card from all available metadata."""
    placed: dict[str, list[str]] = {
        "title": [],
        "author": [],
        "dewey": [],
        "subject": [],
        "collection": [],
        "format": [],
        "shelf": [],
        "description": [],
        "auto": [],
    }
    seen: set[str] = set()
    keywords: list[str] = []

    def add(kw: str, source: str) -> None:
        k = kw.strip().lower()
        if not k or len(k) < 2 or k in STOP_WORDS or k in seen:
            return
        seen.add(k)
        keywords.append(k)
        placed.setdefault(source, []).append(k)

    for tok in _tokenize(str(row.get("title") or "")):
        add(tok, "title")
    for tok in _tokenize(str(row.get("subtitle") or "")):
        add(tok, "title")
    for tok in _tokenize(str(row.get("author") or "")):
        add(tok, "author")

    dewey = str(row.get("dewey") or "")
    if dewey:
        add(dewey.replace(".", ""), "dewey")
        add(dewey, "dewey")
        label = row.get("dewey_label") or _dewey_label(dewey)
        if label:
            for tok in _tokenize(label):
                add(tok, "dewey")

    for field, source in (
        ("subject", "subject"), ("category", "subject"), ("grade_band", "subject"),
        ("collection", "collection"), ("format", "format"),
        ("shelf_title", "shelf"), ("shelf", "shelf"),
        ("description", "description"), ("motto", "description"),
        ("study_note", "description"), ("ironclad_citation", "auto"),
        ("combinatorics_facet", "auto"), ("publisher", "auto"),
        ("book_kind", "collection"),
    ):
        val = row.get(field)
        if val:
            for tok in _tokenize(str(val)):
                add(tok, source)

    for kw in row.get("keywords") or row.get("topics") or row.get("tags") or []:
        add(str(kw), "auto")
    if row.get("personhood") is True:
        add("personhood", "auto")
    if row.get("combat") is True:
        add("combat", "auto")
    if row.get("speaking") is True:
        add("speaking", "auto")

    emperor = row.get("emperor")
    if isinstance(emperor, dict):
        for tok in _tokenize(str(emperor.get("mask") or "")):
            add(tok, "auto")
        for tok in _tokenize(str(emperor.get("archetype") or "")):
            add(tok, "auto")

    bid = str(row.get("id") or "")
    if bid:
        for tok in _tokenize(bid.replace("_", " ").replace("-", " ")):
            add(tok, "auto")

    return keywords, placed


def _search_blob(card: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in SEARCH_BLOB_FIELDS:
        val = card.get(key)
        if val:
            parts.append(str(val))
    for kw in card.get("keywords") or []:
        parts.append(str(kw))
    return " ".join(parts).lower()


def _merge_bibliography(book: dict[str, Any], bib: dict[str, dict[str, Any]]) -> dict[str, Any]:
    bid = str(book.get("id") or "")
    row = dict(book)
    if bid and bid in bib:
        b = bib[bid]
        for key in (
            "ein", "isbn_10", "isbn_13", "oclc", "publisher", "published_year",
            "language", "lc_class", "pages", "grade_band", "license", "subject",
            "study_note", "collection",
        ):
            if b.get(key) and not row.get(key):
                row[key] = b[key]
    return row


def _card_from_book(
    book: dict[str, Any],
    *,
    book_path: Path | None = None,
    detected_by: str = "dewey_glob",
    seq: int = 0,
) -> dict[str, Any]:
    bid = str(book.get("id") or (book_path.parent.name if book_path else ""))
    dewey = str(book.get("dewey") or "")
    shelf = book.get("shelf") or (_shelf_slug(book_path.parent) if book_path else "")
    keywords, keyword_placement = _keyword_placement({**book, "shelf": shelf})

    location = _rel(book_path.parent) if book_path else str(book.get("path") or "")

    card = {
        "schema": "field-card-catalog-card/v1",
        "card_id": _card_id(bid, dewey),
        "id": bid,
        "call_number": dewey or "000",
        "title": str(book.get("title") or bid),
        "subtitle": book.get("subtitle") or "",
        "author": str(book.get("author") or ""),
        "dewey": dewey,
        "dewey_label": book.get("dewey_label") or _dewey_label(dewey),
        "shelf": shelf,
        "shelf_title": book.get("shelf_title") or "",
        "location": location,
        "format": str(book.get("format") or "catalog"),
        "collection": str(book.get("collection") or book.get("source") or "dewey"),
        "source": str(book.get("source") or detected_by),
        "detected_by": detected_by,
        "ready": bool(book.get("ready", book.get("h7c") or book.get("page_count"))),
        "cover": book.get("cover"),
        "thumb": book.get("thumb") or book.get("cover"),
        "page_count": book.get("page_count"),
        "ein": book.get("ein"),
        "isbn_13": book.get("isbn_13"),
        "isbn_10": book.get("isbn_10"),
        "publisher": book.get("publisher"),
        "grade_band": book.get("grade_band"),
        "subject": book.get("subject") or book.get("category"),
        "description": book.get("description") or book.get("motto"),
        "ironclad_citation": book.get("ironclad_citation"),
        "keywords": keywords,
        "keyword_placement": keyword_placement,
        "catalog_seq": seq,
        "family": str(book.get("collection") or book.get("format") or "library"),
        "label": str(book.get("title") or bid),
    }
    card["search_blob"] = _search_blob(card)
    return card


def _detect_from_dewey_index(bib: dict[str, dict[str, Any]], seen: set[str]) -> list[dict[str, Any]]:
    """Ingest tagged entries from field-dewey-index — shelf.json books without book.json."""
    idx_mod = _import_mod("dewey_idx", "field-dewey-index.py")
    if not idx_mod or not hasattr(idx_mod, "load_index"):
        return []
    try:
        doc = idx_mod.load_index()
    except Exception:
        return []
    cards: list[dict[str, Any]] = []
    seq = 0
    for ent in doc.get("books") or []:
        bid = str(ent.get("id") or "")
        if not bid or bid in seen:
            continue
        seen.add(bid)
        seq += 1
        merged = _merge_bibliography(dict(ent), bib)
        merged.setdefault("keywords", ent.get("tags") or ent.get("keywords") or [])
        merged.setdefault("tags", ent.get("tags") or [])
        merged.setdefault("topics", ent.get("tags") or [])
        cards.append(_card_from_book(merged, detected_by="dewey_index", seq=seq))
    return cards


def _detect_dewey_books(bib: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    if not DEWEY_ROOT.is_dir():
        return cards
    seq = 0
    for book_json in sorted(DEWEY_ROOT.rglob("book.json")):
        if "card-catalog" in str(book_json):
            continue
        try:
            book = json.loads(book_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(book, dict):
            continue
        bid = str(book.get("id") or book_json.parent.name)
        book["id"] = bid
        book = _merge_bibliography(book, bib)
        shelf_dir = book_json.parent.parent
        shelf_slug = _shelf_slug(book_json.parent)
        book.setdefault("shelf", shelf_slug)
        book.setdefault("path", _rel(book_json.parent))
        book.setdefault("source", "field-dewey-library")
        if book.get("emperor") and isinstance(book["emperor"], dict):
            book.setdefault("keywords", book.get("keywords") or [])
        seq += 1
        cards.append(_card_from_book(book, book_path=book_json, detected_by="dewey_glob", seq=seq))
    return cards


def _detect_registry_books(
    cards: list[dict[str, Any]],
    bib: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    seen = {c["id"] for c in cards}
    reg = _import_mod("reg", "field-library-registry.py")
    if not reg:
        return cards
    entries: list[dict[str, Any]] = []
    if hasattr(reg, "registry_entries"):
        try:
            entries = reg.registry_entries()
        except Exception:
            entries = []
    if not entries and hasattr(reg, "collect_entries") and os.environ.get("CARD_CATALOG_FULL_REGISTRY", "0") == "1":
        try:
            entries = reg.collect_entries()
        except Exception:
            entries = []
    seq = len(cards)
    for row in entries:
        bid = str(row.get("id") or "")
        if not bid or bid in seen:
            continue
        seen.add(bid)
        seq += 1
        merged = _merge_bibliography(dict(row), bib)
        cards.append(_card_from_book(merged, detected_by="library_registry", seq=seq))
    return cards


def _load_bibliography() -> dict[str, dict[str, Any]]:
    lib = _import_mod("h7lib", "h7-library-librarian.py")
    if lib and hasattr(lib, "load_bibliography_index"):
        try:
            return lib.load_bibliography_index()
        except Exception:
            pass
    return {}


def _sync_keywords_to_books(cards: list[dict[str, Any]], *, only_missing: bool = True) -> int:
    doctrine = _load(DOCTRINE, {})
    auto = doctrine.get("auto_detect") or {}
    if not auto.get("sync_keywords_to_books", True):
        return 0
    only_missing = bool(auto.get("keywords_only_if_missing", only_missing))
    synced = 0
    for card in cards:
        loc = card.get("location") or ""
        if not loc:
            continue
        book_path = INSTALL / loc / "book.json"
        if not book_path.is_file():
            continue
        try:
            book = json.loads(book_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        kws = card.get("keywords") or []
        if not kws:
            continue
        if only_missing and book.get("keywords"):
            continue
        if (
            book.get("keywords") == kws
            and book.get("card_id") == card.get("card_id")
            and book.get("catalog_call_number") == card.get("call_number")
        ):
            continue
        book["keywords"] = kws
        book["keyword_placement"] = card.get("keyword_placement")
        book["card_id"] = card.get("card_id")
        book["catalog_call_number"] = card.get("call_number")
        book["catalog_updated"] = _now()
        try:
            book_path.write_text(json.dumps(book, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            synced += 1
        except OSError:
            pass
    return synced


def _build_keywords_index(cards: list[dict[str, Any]]) -> dict[str, Any]:
    index: dict[str, list[str]] = {}
    for card in cards:
        cid = str(card.get("card_id") or card.get("id") or "")
        for kw in card.get("keywords") or []:
            index.setdefault(str(kw).lower(), []).append(cid)
    return {
        "schema": "field-card-catalog-keywords/v1",
        "updated": _now(),
        "term_count": len(index),
        "card_count": len(cards),
        "index": {k: sorted(set(v)) for k, v in sorted(index.items())},
    }


def detect_cards(*, sync_keywords: bool = False) -> list[dict[str, Any]]:
    bib = _load_bibliography()
    cards = _detect_dewey_books(bib)
    seen = {c["id"] for c in cards}
    cards.extend(_detect_from_dewey_index(bib, seen))
    cards = _detect_registry_books(cards, bib)
    if sync_keywords:
        _sync_keywords_to_books(cards)
    return cards


def _sort_cards(
    cards: list[dict[str, Any]],
    *,
    mode: str = "call_number",
    query: str = "",
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    mode = (mode or "call_number").strip().lower()
    if mode not in SORT_MODES:
        mode = "call_number"

    if mode == "relevance" and query.strip():
        ql = query.strip().lower()
        scored = [(_score_card(c, ql), c) for c in cards]
        scored = [(s, c) for s, c in scored if s > 0]
        scored.sort(key=lambda t: (-t[0], _dewey_sort_key(t[1].get("call_number", ""))))
        rows = [c for _, c in scored]
        meta = {"sort_mode": mode, "algorithm": "relevance_then_call_number", "query": query}
    elif mode == "call_number":
        rows = sorted(cards, key=lambda c: (_dewey_sort_key(c.get("call_number", "")), str(c.get("title", "")).lower()))
        meta = {"sort_mode": mode, "algorithm": "dewey_numeric_then_title"}
    elif mode == "title":
        rows = sorted(cards, key=lambda c: str(c.get("title", "")).lower())
        meta = {"sort_mode": mode, "algorithm": "title_ci"}
    elif mode == "author":
        rows = sorted(cards, key=lambda c: (str(c.get("author", "")).lower(), str(c.get("title", "")).lower()))
        meta = {"sort_mode": mode, "algorithm": "author_then_title"}
    elif mode == "shelf":
        rows = sorted(cards, key=lambda c: (str(c.get("shelf", "")).lower(), _dewey_sort_key(c.get("call_number", ""))))
        meta = {"sort_mode": mode, "algorithm": "shelf_then_call_number"}
    elif mode == "format":
        rows = sorted(cards, key=lambda c: (str(c.get("format", "")).lower(), str(c.get("title", "")).lower()))
        meta = {"sort_mode": mode, "algorithm": "format_then_title"}
    else:
        api = _import_mod("ironclad", "ironclad-secure-api.py")
        rows = list(cards)
        sort_meta: dict[str, Any] = {}
        if api and hasattr(api, "sort_index"):
            try:
                rows, sort_meta = api.sort_index(rows, context="catalog_index")
            except Exception:
                rows = sorted(rows, key=lambda c: (
                    str(c.get("family") or c.get("collection") or ""),
                    str(c.get("title", "")).lower(),
                ))
        else:
            best = _import_mod("best_sort", "field-best-sort.py")
            if best and hasattr(best, "apply_best"):
                rows, sort_meta = best.apply_best(rows, context="catalog_index")
            else:
                rows = sorted(rows, key=lambda c: str(c.get("title", "")).lower())
        meta = {"sort_mode": mode, "algorithm": "catalog_index", **sort_meta}

    meta["count"] = len(rows)
    meta["ironclad_citation"] = "ironclad:catalog:1"
    return rows, meta


def _score_card(card: dict[str, Any], query: str) -> int:
    q = query.strip().lower()
    if not q:
        return 0
    blob = card.get("search_blob") or _search_blob(card)
    tokens = [t for t in re.split(r"\W+", q) if t]
    score = 0
    if q in blob:
        score += 28
    cid = str(card.get("id") or "").lower()
    title = str(card.get("title") or "").lower()
    author = str(card.get("author") or "").lower()
    call = str(card.get("call_number") or "").lower()
    if q in cid:
        score += 22
    if title.startswith(q):
        score += 20
    if q in title:
        score += 14
    if q in author:
        score += 10
    if q in call:
        score += 12
    keywords = [str(k).lower() for k in (card.get("keywords") or [])]
    if q in keywords:
        score += 16
    for tok in tokens:
        if tok in cid:
            score += 10
        if tok in title:
            score += 8
        if tok in author:
            score += 6
        if tok in call:
            score += 6
        if tok in keywords:
            score += 7
        if tok in blob:
            score += 4
    return score


def _autocomplete_hit(card: dict[str, Any], *, score: int, query: str) -> dict[str, Any]:
    return {
        "card_id": card.get("card_id"),
        "id": card.get("id"),
        "call_number": card.get("call_number"),
        "title": card.get("title"),
        "author": card.get("author"),
        "dewey": card.get("dewey"),
        "shelf": card.get("shelf"),
        "format": card.get("format"),
        "keywords": (card.get("keywords") or [])[:8],
        "cover": card.get("cover"),
        "score": score,
        "query": query,
    }


def search_cards(
    query: str,
    *,
    limit: int = 48,
    dewey_prefix: str = "",
    collection: str = "",
    format_filter: str = "",
    shelf: str = "",
    ready_only: bool = False,
) -> dict[str, Any]:
    doc = catalog_json()
    cards = list(doc.get("cards") or [])
    q = query.strip()

    if dewey_prefix:
        dp = dewey_prefix.strip()
        cards = [c for c in cards if str(c.get("call_number", "")).startswith(dp)]
    if collection:
        col = collection.strip().lower()
        cards = [c for c in cards if col in str(c.get("collection", "")).lower()]
    if format_filter:
        fmt = format_filter.strip().lower()
        cards = [c for c in cards if fmt in str(c.get("format", "")).lower()]
    if shelf:
        sh = shelf.strip().lower()
        cards = [c for c in cards if sh in str(c.get("shelf", "")).lower()]
    if ready_only:
        cards = [c for c in cards if c.get("ready")]

    if not q:
        rows, sort_meta = _sort_cards(cards, mode="call_number")
        return {
            "schema": "field-card-catalog-search/v1",
            "query": q,
            "hits": [_autocomplete_hit(c, score=0, query=q) for c in rows[:limit]],
            "count": min(limit, len(rows)),
            "total_pool": len(cards),
            "sort": sort_meta,
            "search_engine": "field-card-catalog/v1",
        }

    hits: list[tuple[int, dict[str, Any]]] = []
    for card in cards:
        score = _score_card(card, q)
        if score > 0:
            hits.append((score, card))
    hits.sort(key=lambda t: (-t[0], _dewey_sort_key(t[1].get("call_number", ""))))
    out = [_autocomplete_hit(c, score=s, query=q) for s, c in hits[:limit]]
    return {
        "schema": "field-card-catalog-search/v1",
        "query": q,
        "hits": out,
        "count": len(out),
        "total_pool": len(cards),
        "sort": {"sort_mode": "relevance", "algorithm": "relevance_then_call_number"},
        "search_engine": "field-card-catalog/v1",
    }


def autocomplete(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    return search_cards(query, limit=limit).get("hits") or []


def card_detail(card_id: str) -> dict[str, Any] | None:
    doc = catalog_json()
    needle = card_id.strip()
    for card in doc.get("cards") or []:
        if str(card.get("card_id")) == needle or str(card.get("id")) == needle:
            return {"ok": True, "card": card}
    return None


def build_catalog(*, sync_keywords: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    cards = detect_cards(sync_keywords=sync_keywords)
    cards, sort_meta = _sort_cards(cards, mode="call_number")

    collections: dict[str, int] = {}
    formats: dict[str, int] = {}
    shelves: dict[str, int] = {}
    for c in cards:
        col = str(c.get("collection") or "other")
        collections[col] = collections.get(col, 0) + 1
        fmt = str(c.get("format") or "unknown")
        formats[fmt] = formats.get(fmt, 0) + 1
        sh = str(c.get("shelf") or "unknown")
        shelves[sh] = shelves.get(sh, 0) + 1

    kw_index = _build_keywords_index(cards)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    return {
        "schema": "field-card-catalog/v1",
        "title": "Field Card Catalog",
        "motto": "Every book a card — call number, keywords placed, one best sort.",
        "updated": _now(),
        "ok": True,
        "ironclad_citation": "ironclad:catalog:1",
        "counts": {
            "cards": len(cards),
            "collections": len(collections),
            "formats": len(formats),
            "shelves": len(shelves),
            "keyword_terms": kw_index.get("term_count", 0),
        },
        "collections": collections,
        "formats": formats,
        "shelf_sample": dict(sorted(shelves.items(), key=lambda x: -x[1])[:24]),
        "sort_modes": list(SORT_MODES),
        "cards": cards,
        "sort_meta": sort_meta,
        "elapsed_ms": elapsed_ms,
    }


def build_dewey_catalog_shelf(cat: dict[str, Any]) -> dict[str, Any]:
    CATALOG_SHELF_DIR.mkdir(parents=True, exist_ok=True)
    compact = {
        "schema": "field-card-catalog-drawer/v1",
        "title": "Library Card Catalog",
        "motto": cat.get("motto"),
        "updated": cat.get("updated"),
        "card_count": len(cat.get("cards") or []),
        "sort_modes": cat.get("sort_modes"),
        "counts": cat.get("counts"),
        "cards": [
            {
                "card_id": c.get("card_id"),
                "call_number": c.get("call_number"),
                "title": c.get("title"),
                "author": c.get("author"),
                "keywords": c.get("keywords"),
                "shelf": c.get("shelf"),
                "format": c.get("format"),
                "location": c.get("location"),
            }
            for c in (cat.get("cards") or [])
        ],
    }
    _save(CATALOG_JSON, compact)

    shelf = {
        "schema": "dewey-shelf/v1",
        "shelf": "020-library-science/card-catalog",
        "code": "020",
        "title": "Library Science — Card Catalog",
        "updated": cat.get("updated"),
        "format_primary": "card-catalog",
        "book_count": 1,
        "books": [{
            "id": "field-card-catalog",
            "title": "Field Card Catalog",
            "author": "Hostess7 Librarian Corps",
            "dewey": "020",
            "format": "card-catalog",
            "card_count": len(cat.get("cards") or []),
            "ready": True,
        }],
    }
    _save(CATALOG_SHELF_DIR / "shelf.json", shelf)
    _save(KEYWORDS_INDEX, _build_keywords_index(cat.get("cards") or []))
    return {"ok": True, "catalog": _rel(CATALOG_JSON), "shelf": _rel(CATALOG_SHELF_DIR / "shelf.json")}


def publish_catalog(*, refresh: bool = True, sync_keywords: bool = False) -> dict[str, Any]:
    idx = _import_mod("dewey_idx_pub", "field-dewey-index.py")
    if idx and hasattr(idx, "build_index"):
        try:
            idx.build_index(write=True)
        except Exception:
            pass
    cat = build_catalog(sync_keywords=sync_keywords)
    _save(CATALOG, cat)
    dewey = build_dewey_catalog_shelf(cat)
    panel_doc = {
        "schema": "field-card-catalog-panel/v1",
        "updated": cat["updated"],
        "ok": True,
        "counts": cat["counts"],
        "sort_modes": cat["sort_modes"],
        "motto": cat["motto"],
        "sample_cards": [
            {
                "card_id": c.get("card_id"),
                "call_number": c.get("call_number"),
                "title": c.get("title"),
                "author": c.get("author"),
                "keywords": (c.get("keywords") or [])[:6],
            }
            for c in (cat.get("cards") or [])[:12]
        ],
        "api": "/api/card-catalog",
        "reader": "/library/dewey/020-library-science/card-catalog/catalog.json",
        "ui": "/panel/field-card-catalog.html",
        "elapsed_ms": cat.get("elapsed_ms"),
    }
    _save(PANEL, panel_doc)

    if os.environ.get("CARD_CATALOG_CORPS_LEARN", "0") == "1":
        corps = _import_mod("corps", "nexus-librarian-corps.py")
        if corps and hasattr(corps, "learn"):
            try:
                corps.learn("card_catalog_build", detail=str(cat["counts"].get("cards", 0)))
            except Exception:
                pass

    return {"ok": True, "panel": panel_doc, "catalog_path": str(CATALOG), "dewey": dewey}


def catalog_json(*, refresh: bool = False) -> dict[str, Any]:
    if refresh or not CATALOG.is_file():
        return build_catalog()
    doc = _load(CATALOG, {})
    if doc.get("cards"):
        return doc
    return build_catalog()


def panel() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached:
        return cached
    return publish_catalog(refresh=False).get("panel") or {}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    refresh = "--refresh" in sys.argv

    if cmd in ("panel", "status", "json"):
        if PANEL.is_file() and not refresh:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_catalog(refresh=True).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sync-keywords":
        cards = detect_cards(sync_keywords=False)
        n = _sync_keywords_to_books(cards)
        print(json.dumps({"ok": True, "synced": n, "cards": len(cards)}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish", "detect"):
        do_sync = "--sync-keywords" in sys.argv
        print(json.dumps(publish_catalog(refresh=True, sync_keywords=do_sync), ensure_ascii=False, indent=2))
        return 0
    if cmd == "catalog":
        print(json.dumps(catalog_json(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "search":
        q = sys.argv[2] if len(sys.argv) > 2 else ""
        limit = 48
        for i, arg in enumerate(sys.argv):
            if arg == "--limit" and i + 1 < len(sys.argv):
                try:
                    limit = int(sys.argv[i + 1])
                except ValueError:
                    pass
        print(json.dumps(search_cards(q, limit=limit), ensure_ascii=False, indent=2))
        return 0
    if cmd == "autocomplete":
        q = sys.argv[2] if len(sys.argv) > 2 else ""
        limit = 20
        print(json.dumps({"query": q, "hits": autocomplete(q, limit=limit)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "sort":
        mode = sys.argv[2] if len(sys.argv) > 2 else "call_number"
        doc = catalog_json()
        rows, meta = _sort_cards(doc.get("cards") or [], mode=mode)
        print(json.dumps({"sort": meta, "cards": rows[:64], "count": len(rows)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "card":
        cid = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(card_detail(cid) or {"ok": False, "error": "not_found", "id": cid}, ensure_ascii=False, indent=2))
        return 0 if card_detail(cid) else 1
    if cmd == "verify":
        pub = publish_catalog(refresh=True, sync_keywords=False)
        cat = _load(CATALOG, {})
        drawer = _load(CATALOG_JSON, {})
        ok = (
            cat.get("counts", {}).get("cards", 0) >= 100
            and drawer.get("card_count", 0) >= 100
            and cat.get("counts", {}).get("keyword_terms", 0) >= 50
        )
        print(json.dumps({
            "ok": ok,
            "counts": cat.get("counts"),
            "drawer_cards": drawer.get("card_count"),
            "elapsed_ms": cat.get("elapsed_ms"),
        }, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["panel", "build", "detect", "catalog", "search", "autocomplete", "sort", "card", "verify"],
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())