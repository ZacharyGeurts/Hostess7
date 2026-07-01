#!/usr/bin/env pythong
"""Dewey index librarian — comprehensive catalog, tagging, faceted search for every shelf book."""
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
DOCTRINE = INSTALL / "data" / "field-dewey-index-doctrine.json"
DEWEY_ROOT = INSTALL / "library" / "dewey"
INDEX = STATE / "field-dewey-index.json"
SEARCH_JSONL = STATE / "field-dewey-search.jsonl"
TAGS = STATE / "field-dewey-tags.json"
PANEL = STATE / "field-dewey-index-panel.json"

STOP = frozenset({
    "a", "an", "the", "and", "or", "of", "in", "on", "at", "to", "for", "by", "with", "from",
    "is", "are", "was", "book", "exploring", "hostess", "field", "library",
})

DEWEY_LABELS: dict[str, str] = {
    "000": "Computer science & general works",
    "004": "Data processing & computer science",
    "005": "Computer programming",
    "020": "Library & information sciences",
    "133": "Parapsychology & occult",
    "300": "Social sciences",
    "355": "Military science",
    "370": "Education",
    "400": "Language",
    "500": "Science",
    "510": "Mathematics",
    "540": "Chemistry",
    "570": "Biology",
    "600": "Technology",
    "629": "Vehicle engineering",
    "700": "Arts & recreation",
    "800": "Literature",
    "900": "History & geography",
    "910": "Geography",
    "920": "Biography",
}

ID_TAG_RULES: list[tuple[re.Pattern[str], list[str]]] = [
    (re.compile(r"^exploring_speaking_"), ["exploring", "speaking", "language", "phonetics", "education"]),
    (re.compile(r"^exploring_the_"), ["exploring", "anatomy", "biology", "mechanical", "combat", "personhood", "combat-anatomy"]),
    (re.compile(r"^exploring_the_hand"), ["hand", "grip", "dexterity", "fingers"]),
    (re.compile(r"^exploring_hand_to_hand"), ["exploring", "combat", "personhood", "hand-to-hand", "martial-arts", "bjj", "grappling"]),
    (re.compile(r"^exploring_weaponized"), ["exploring", "combat", "personhood", "weaponized", "firearms", "knives", "weapons"]),
    (re.compile(r"^exploring_military_vehicles"), ["exploring", "vehicles", "military", "not-personhood"]),
    (re.compile(r"^exploring_combat$"), ["exploring", "combat", "martial-arts"]),
    (re.compile(r"^exploring_biology"), ["exploring", "stem", "biology", "science"]),
    (re.compile(r"^exploring_chemistry"), ["exploring", "stem", "chemistry", "science"]),
    (re.compile(r"^exploring_mathematics"), ["exploring", "stem", "mathematics", "science"]),
    (re.compile(r"^exploring_history"), ["exploring", "history", "humanities"]),
    (re.compile(r"^exploring_geography"), ["exploring", "geography", "humanities"]),
    (re.compile(r"^exploring_engineering"), ["exploring", "engineering", "technology"]),
    (re.compile(r"^exploring_vehicles"), ["exploring", "vehicles", "transport"]),
    (re.compile(r"^exploring_hostess_7"), ["exploring", "biography", "hostess7", "exploring_self", "solidification"]),
    (re.compile(r"^explaining_"), ["programming", "manual", "code"]),
    (re.compile(r"gutenberg"), ["literature", "classic", "public-domain"]),
    (re.compile(r"tobin"), ["occult", "spirit-guide", "parapsychology"]),
    (re.compile(r"future_war"), ["war", "military", "strategy"]),
]


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


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(INSTALL.resolve()))
    except ValueError:
        return str(path)


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _dewey_label(code: str) -> str:
    c = str(code or "").strip()
    if not c:
        return ""
    main = re.sub(r"[^0-9].*", "", c)[:3]
    return DEWEY_LABELS.get(main) or DEWEY_LABELS.get(c[:3], "")


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if len(t) > 1 and t not in STOP]


def _auto_tags(book_id: str, row: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()

    def add(*items: str) -> None:
        for item in items:
            k = str(item).strip().lower()
            if k and k not in seen:
                seen.add(k)
                tags.append(k)

    bid = str(book_id or "")
    for pat, rule_tags in ID_TAG_RULES:
        if pat.search(bid):
            add(*rule_tags)

    if row.get("book_kind"):
        add(str(row["book_kind"]))
    if row.get("personhood") is True:
        add("personhood")
    if row.get("personhood") is False or row.get("not_personhood"):
        add("not-personhood")
    if "vehicle" in bid or row.get("vehicles"):
        add("vehicles")
    if row.get("speaking_lane") or bid.startswith("exploring_speaking_"):
        add("speaking")
        code = bid.replace("exploring_speaking_", "")
        if len(code) == 3:
            add(f"lang-{code}", "iso6393")

    for key in ("tags", "keywords", "topics", "subjects"):
        for t in row.get(key) or []:
            add(str(t))

    for tok in _tokenize(str(row.get("title") or "")):
        if len(tok) > 3:
            add(tok)
    for tok in _tokenize(str(row.get("subject") or row.get("category") or "")):
        add(tok)

    dewey = str(row.get("dewey") or "")
    if dewey.startswith("355"):
        add("military", "combat")
    if dewey.startswith("400"):
        add("language", "education")
    if dewey.startswith("510"):
        add("mathematics")
    if dewey.startswith("629"):
        add("vehicles")

    return tags


def _entry_from_row(row: dict[str, Any], *, source: str, shelf: str = "", shelf_title: str = "") -> dict[str, Any]:
    bid = str(row.get("id") or "")
    dewey = str(row.get("dewey") or "")
    tags = _auto_tags(bid, row)
    title = str(row.get("title") or bid)
    return {
        "id": bid,
        "title": title,
        "author": str(row.get("author") or ""),
        "dewey": dewey,
        "dewey_label": row.get("dewey_label") or _dewey_label(dewey),
        "shelf": row.get("shelf") or shelf,
        "shelf_title": row.get("shelf_title") or shelf_title,
        "format": str(row.get("format") or "h7c"),
        "book_kind": str(row.get("book_kind") or ("speaking" if bid.startswith("exploring_speaking_") else "library")),
        "collection": str(row.get("collection") or row.get("github_shelf") or shelf),
        "h7c": row.get("h7c"),
        "path": row.get("path") or row.get("field_path") or row.get("location"),
        "cover": row.get("cover"),
        "ready": bool(row.get("ready", row.get("h7c"))),
        "personhood": bool(row.get("personhood")) if "personhood" in row else (
            "personhood" in tags and "not-personhood" not in tags
        ),
        "vehicles": "vehicles" in tags,
        "speaking": bid.startswith("exploring_speaking_") or "speaking" in tags,
        "combat": "combat" in tags or dewey.startswith("355") or bool(row.get("combat_anatomy")),
        "combat_anatomy": bool(row.get("combat_anatomy")) or "combat-anatomy" in tags,
        "tags": tags,
        "keywords": tags,
        "chapter_count": row.get("chapter_count"),
        "char_count": row.get("char_count"),
        "ein": row.get("ein"),
        "source": source,
        "search_blob": " ".join(filter(None, [bid, title, row.get("author"), dewey, shelf, " ".join(tags)])).lower(),
    }


def _scan_shelf_json() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not DEWEY_ROOT.is_dir():
        return entries
    for shelf_json in sorted(DEWEY_ROOT.rglob("shelf.json")):
        if "card-catalog" in str(shelf_json) or "/private/" in str(shelf_json):
            continue
        try:
            doc = json.loads(shelf_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        shelf_slug = str(doc.get("shelf") or shelf_json.parent.name)
        shelf_title = str(doc.get("title") or shelf_slug)
        for book in doc.get("books") or []:
            if not isinstance(book, dict):
                continue
            row = dict(book)
            row.setdefault("shelf", shelf_slug)
            row.setdefault("shelf_title", shelf_title)
            if not row.get("dewey"):
                row["dewey"] = str(doc.get("code") or "")
            entries.append(_entry_from_row(row, source="shelf.json", shelf=shelf_slug, shelf_title=shelf_title))
    return entries


def _scan_book_json(seen: set[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for book_json in sorted(DEWEY_ROOT.rglob("book.json")):
        if "card-catalog" in str(book_json) or "/private/" in str(book_json):
            continue
        try:
            book = json.loads(book_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(book, dict):
            continue
        bid = str(book.get("id") or book_json.parent.name)
        if bid in seen:
            continue
        seen.add(bid)
        try:
            shelf_slug = str(book_json.parent.parent.relative_to(DEWEY_ROOT)).replace("\\", "/")
        except ValueError:
            shelf_slug = ""
        book.setdefault("path", _rel(book_json.parent))
        entries.append(_entry_from_row(book, source="book.json", shelf=shelf_slug))
    return entries


def _scan_information_indexes(by_id: dict[str, dict[str, Any]]) -> int:
    enriched = 0
    for index_path in sorted(DEWEY_ROOT.rglob("book-information-index.json")):
        if "card-catalog" in str(index_path) or "/private/" in str(index_path):
            continue
        try:
            doc = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        bid = str(doc.get("book_id") or index_path.parent.name)
        if bid not in by_id:
            continue
        row = by_id[bid]
        title_block = doc.get("title") or {}
        auth = doc.get("authorship") or {}
        dates = doc.get("dates") or {}
        catalog = doc.get("catalog") or {}
        content = doc.get("content") or {}
        if title_block.get("timestamped"):
            row["title"] = title_block["timestamped"]
            row["title_display"] = title_block.get("display")
        if auth.get("primary"):
            row["author"] = auth["primary"]
        if auth.get("co_authors"):
            row["co_authors"] = auth["co_authors"]
        if dates.get("written_at"):
            row["written_at"] = dates["written_at"]
        if dates.get("written_date"):
            row["written_date"] = dates["written_date"]
        if catalog.get("ein"):
            row["ein"] = catalog["ein"]
        if content.get("char_count"):
            row["char_count"] = content["char_count"]
        if content.get("chapter_count"):
            row["chapter_count"] = content["chapter_count"]
        idx_tags = list(doc.get("tags") or [])
        if idx_tags:
            merged = list(dict.fromkeys((row.get("tags") or []) + idx_tags))
            row["tags"] = merged
            row["keywords"] = merged
        row["information_index"] = _rel(index_path)
        row["search_blob"] = (row.get("search_blob") or "") + " " + str(doc.get("search_blob") or "")
        enriched += 1
    return enriched


def _scan_manifests(seen: set[str], by_id: dict[str, dict[str, Any]]) -> int:
    enriched = 0
    for manifest in sorted(DEWEY_ROOT.rglob("book-manifest.json")):
        if "card-catalog" in str(manifest) or "/private/" in str(manifest):
            continue
        try:
            doc = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        bid = str(doc.get("id") or manifest.parent.name)
        if bid not in by_id:
            continue
        row = by_id[bid]
        if doc.get("chapter_count"):
            row["chapter_count"] = doc["chapter_count"]
        if doc.get("char_count"):
            row["char_count"] = doc["char_count"]
        ch_tags = []
        for ch in doc.get("chapters") or []:
            slug = str(ch.get("slug") or "")
            for tok in _tokenize(slug.replace("-", " ")):
                ch_tags.append(tok)
        if ch_tags:
            merged = list(dict.fromkeys((row.get("tags") or []) + ch_tags[:12]))
            row["tags"] = merged
            row["keywords"] = merged
            row["search_blob"] = (row.get("search_blob") or "") + " " + " ".join(ch_tags)
        enriched += 1
    return enriched


def _scan_h7c_orphans(seen: set[str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for h7c in sorted(DEWEY_ROOT.rglob("*.h7c")):
        if "card-catalog" in str(h7c) or "/private/" in str(h7c):
            continue
        bid = h7c.stem
        if bid in seen:
            continue
        seen.add(bid)
        try:
            shelf_slug = str(h7c.parent.parent.relative_to(DEWEY_ROOT)).replace("\\", "/")
        except ValueError:
            shelf_slug = ""
        row = {
            "id": bid,
            "title": bid.replace("_", " ").replace("-", " ").title(),
            "format": "h7c",
            "h7c": _rel(h7c),
            "path": _rel(h7c.parent),
            "ready": True,
        }
        entries.append(_entry_from_row(row, source="h7c_glob", shelf=shelf_slug))
    return entries


def _scan_speaking_index(by_id: dict[str, dict[str, Any]]) -> int:
    idx_path = DEWEY_ROOT / "400-education" / "speaking-index.jsonl"
    if not idx_path.is_file():
        return 0
    count = 0
    try:
        for line in idx_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            bid = str(row.get("book_id") or row.get("id") or "")
            if not bid or bid not in by_id:
                continue
            ent = by_id[bid]
            ent["language_code"] = row.get("iso6393") or row.get("code")
            ent["language_name"] = row.get("name") or row.get("language")
            if ent.get("language_code"):
                tag = f"lang-{ent['language_code']}"
                tags = list(dict.fromkeys((ent.get("tags") or []) + [tag]))
                ent["tags"] = tags
                ent["keywords"] = tags
            count += 1
    except (OSError, json.JSONDecodeError):
        pass
    return count


def _build_tag_index(entries: list[dict[str, Any]]) -> dict[str, Any]:
    index: dict[str, list[str]] = {}
    families: dict[str, list[str]] = {}
    doc = _load(DOCTRINE, {})
    for fam, members in (doc.get("tag_families") or {}).items():
        families[fam] = []
        for m in members:
            hits = [e["id"] for e in entries if m in (e.get("tags") or [])]
            if hits:
                families[fam].append(m)
                index.setdefault(m, []).extend(hits)
    for ent in entries:
        for tag in ent.get("tags") or []:
            index.setdefault(tag, []).append(ent["id"])
    return {
        "schema": "field-dewey-tags/v1",
        "updated": _now(),
        "term_count": len(index),
        "book_count": len(entries),
        "families": families,
        "index": {k: sorted(set(v)) for k, v in sorted(index.items())},
    }


def _facet_counts(entries: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    facets: dict[str, dict[str, int]] = {
        "book_kind": {},
        "dewey": {},
        "shelf": {},
        "format": {},
        "tag": {},
    }
    for ent in entries:
        for key in ("book_kind", "format"):
            val = str(ent.get(key) or "unknown")
            facets[key][val] = facets.get(key, {}).get(val, 0) + 1
        dew = str(ent.get("dewey") or "000")[:3]
        facets["dewey"][dew] = facets["dewey"].get(dew, 0) + 1
        sh = str(ent.get("shelf") or "unknown")
        facets["shelf"][sh] = facets["shelf"].get(sh, 0) + 1
        for tag in ent.get("tags") or []:
            facets["tag"][tag] = facets["tag"].get(tag, 0) + 1
    facets["personhood"] = {"true": sum(1 for e in entries if e.get("personhood")), "false": sum(1 for e in entries if not e.get("personhood"))}
    facets["speaking"] = {"true": sum(1 for e in entries if e.get("speaking")), "false": sum(1 for e in entries if not e.get("speaking"))}
    facets["combat"] = {"true": sum(1 for e in entries if e.get("combat")), "false": sum(1 for e in entries if not e.get("combat"))}
    facets["combat_anatomy"] = {"true": sum(1 for e in entries if e.get("combat_anatomy")), "false": sum(1 for e in entries if not e.get("combat_anatomy"))}
    facets["vehicles"] = {"true": sum(1 for e in entries if e.get("vehicles")), "false": sum(1 for e in entries if not e.get("vehicles"))}
    facets["ready"] = {"true": sum(1 for e in entries if e.get("ready")), "false": sum(1 for e in entries if not e.get("ready"))}
    return facets


def build_index(*, write: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    seen: set[str] = set()
    by_id: dict[str, dict[str, Any]] = {}

    for ent in _scan_shelf_json():
        bid = ent["id"]
        if bid and bid not in seen:
            seen.add(bid)
            by_id[bid] = ent

    for ent in _scan_book_json(seen):
        bid = ent["id"]
        if bid:
            if bid in by_id:
                by_id[bid].update({k: v for k, v in ent.items() if v})
            else:
                by_id[bid] = ent
                seen.add(bid)

    for ent in _scan_h7c_orphans(seen):
        bid = ent["id"]
        if bid:
            by_id[bid] = ent
            seen.add(bid)

    entries = list(by_id.values())
    _scan_manifests(seen, by_id)
    _scan_information_indexes(by_id)
    _scan_speaking_index(by_id)
    entries = list(by_id.values())
    entries.sort(key=lambda e: (str(e.get("dewey") or "999"), str(e.get("title") or "").lower()))

    tag_doc = _build_tag_index(entries)
    facets = _facet_counts(entries)
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    doc = {
        "schema": "field-dewey-index/v1",
        "updated": _now(),
        "ok": True,
        "motto": _load(DOCTRINE, {}).get("motto"),
        "counts": {
            "books": len(entries),
            "tags": tag_doc.get("term_count", 0),
            "shelves": len(facets.get("shelf", {})),
            "ready": facets.get("ready", {}).get("true", 0),
            "speaking": facets.get("speaking", {}).get("true", 0),
            "combat": facets.get("combat", {}).get("true", 0),
            "combat_anatomy": facets.get("combat_anatomy", {}).get("true", 0),
            "personhood": facets.get("personhood", {}).get("true", 0),
        },
        "facets": facets,
        "books": entries,
        "elapsed_ms": elapsed_ms,
    }

    if write:
        _save(INDEX, doc)
        _save(TAGS, tag_doc)
        lines = [json.dumps({k: ent[k] for k in (
            "id", "title", "author", "dewey", "shelf", "book_kind", "tags", "ready", "personhood", "combat", "speaking", "search_blob",
        ) if k in ent}, ensure_ascii=False) for ent in entries]
        SEARCH_JSONL.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        _save(PANEL, {
            "schema": "field-dewey-index-panel/v1",
            "updated": doc["updated"],
            "counts": doc["counts"],
            "top_tags": sorted(facets.get("tag", {}).items(), key=lambda x: -x[1])[:24],
            "api": "/api/dewey-index",
        })
        _mirror_to_brain(doc)

    return doc


def _mirror_to_brain(doc: dict[str, Any]) -> None:
    lib = _import_mod("h7lib", "h7-library-librarian.py")
    if not lib or not hasattr(lib, "library_meta_dir"):
        return
    try:
        brain_path = lib.library_meta_dir() / "dewey_index.json"
        brain_path.parent.mkdir(parents=True, exist_ok=True)
        compact = {
            "schema": "dewey-index/v1",
            "updated": doc.get("updated"),
            "counts": doc.get("counts"),
            "books": [
                {k: b.get(k) for k in ("id", "title", "dewey", "shelf", "tags", "book_kind", "ready", "h7c")}
                for b in (doc.get("books") or [])
            ],
        }
        brain_path.write_text(json.dumps(compact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass


def load_index(*, refresh: bool = False) -> dict[str, Any]:
    if refresh or not INDEX.is_file():
        return build_index(write=True)
    doc = _load(INDEX, {})
    return doc if doc.get("books") else build_index(write=True)


def _score(entry: dict[str, Any], query: str) -> int:
    q = query.strip().lower()
    if not q:
        return 0
    score = 0
    blob = str(entry.get("search_blob") or "")
    eid = str(entry.get("id") or "").lower()
    title = str(entry.get("title") or "").lower()
    tags = [str(t).lower() for t in (entry.get("tags") or [])]
    tokens = [t for t in re.split(r"\W+", q) if t]
    if q in eid:
        score += 30
    if q in title:
        score += 22
    if q in tags:
        score += 18
    if q in blob:
        score += 12
    for tok in tokens:
        if tok in eid:
            score += 12
        if tok in title:
            score += 10
        if tok in tags:
            score += 14
        if tok in blob:
            score += 5
    return score


def search_index(
    query: str = "",
    *,
    tag: str = "",
    dewey_prefix: str = "",
    book_kind: str = "",
    shelf: str = "",
    personhood: bool | None = None,
    combat: bool | None = None,
    speaking: bool | None = None,
    ready_only: bool = False,
    limit: int = 48,
) -> dict[str, Any]:
    doc = load_index()
    pool = list(doc.get("books") or [])

    if tag:
        tg = tag.strip().lower()
        pool = [e for e in pool if tg in (e.get("tags") or [])]
    if dewey_prefix:
        dp = dewey_prefix.strip()
        pool = [e for e in pool if str(e.get("dewey") or "").startswith(dp)]
    if book_kind:
        bk = book_kind.strip().lower()
        pool = [e for e in pool if bk in str(e.get("book_kind") or "").lower()]
    if shelf:
        sh = shelf.strip().lower()
        pool = [e for e in pool if sh in str(e.get("shelf") or "").lower()]
    if personhood is True:
        pool = [e for e in pool if e.get("personhood")]
    if combat is True:
        pool = [e for e in pool if e.get("combat")]
    if speaking is True:
        pool = [e for e in pool if e.get("speaking")]
    if ready_only:
        pool = [e for e in pool if e.get("ready")]

    q = query.strip()
    if q:
        scored = [( _score(e, q), e) for e in pool]
        scored = [(s, e) for s, e in scored if s > 0]
        scored.sort(key=lambda t: (-t[0], str(t[1].get("title", "")).lower()))
        hits = [{**e, "score": s} for s, e in scored[:limit]]
    else:
        pool.sort(key=lambda e: (str(e.get("dewey") or ""), str(e.get("title", "")).lower()))
        hits = pool[:limit]

    return {
        "schema": "field-dewey-index-search/v1",
        "ok": True,
        "query": q,
        "filters": {
            "tag": tag or None,
            "dewey_prefix": dewey_prefix or None,
            "book_kind": book_kind or None,
            "shelf": shelf or None,
            "personhood": personhood,
            "combat": combat,
            "speaking": speaking,
            "ready_only": ready_only,
        },
        "hits": hits,
        "count": len(hits),
        "total_pool": len(pool),
        "index_updated": doc.get("updated"),
    }


def book_detail(book_id: str) -> dict[str, Any]:
    doc = load_index()
    needle = str(book_id or "").strip()
    for ent in doc.get("books") or []:
        if str(ent.get("id")) == needle:
            return {"ok": True, "book": ent}
    return {"ok": False, "error": "not_found", "id": needle}


def tags_panel() -> dict[str, Any]:
    doc = _load(TAGS, {})
    if not doc.get("index"):
        build_index(write=True)
        doc = _load(TAGS, {})
    return doc


def facets_panel() -> dict[str, Any]:
    doc = load_index()
    return {
        "schema": "field-dewey-index-facets/v1",
        "updated": doc.get("updated"),
        "facets": doc.get("facets") or {},
        "counts": doc.get("counts") or {},
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    refresh = "--refresh" in sys.argv

    if cmd in ("panel", "status", "json"):
        if refresh or not PANEL.is_file():
            build_index(write=True)
        print(json.dumps(_load(PANEL, {}), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "reindex", "sync"):
        print(json.dumps(build_index(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "search":
        kwargs: dict[str, Any] = {"limit": 48}
        q_parts: list[str] = []
        i = 2
        while i < len(sys.argv):
            arg = sys.argv[i]
            if arg == "--tag" and i + 1 < len(sys.argv):
                kwargs["tag"] = sys.argv[i + 1]
                i += 2
                continue
            if arg == "--dewey" and i + 1 < len(sys.argv):
                kwargs["dewey_prefix"] = sys.argv[i + 1]
                i += 2
                continue
            if arg == "--kind" and i + 1 < len(sys.argv):
                kwargs["book_kind"] = sys.argv[i + 1]
                i += 2
                continue
            if arg == "--shelf" and i + 1 < len(sys.argv):
                kwargs["shelf"] = sys.argv[i + 1]
                i += 2
                continue
            if arg == "--personhood":
                kwargs["personhood"] = True
                i += 1
                continue
            if arg == "--combat":
                kwargs["combat"] = True
                i += 1
                continue
            if arg == "--speaking":
                kwargs["speaking"] = True
                i += 1
                continue
            if arg == "--limit" and i + 1 < len(sys.argv):
                try:
                    kwargs["limit"] = int(sys.argv[i + 1])
                except ValueError:
                    pass
                i += 2
                continue
            if not arg.startswith("--"):
                q_parts.append(arg)
            i += 1
        print(json.dumps(search_index(" ".join(q_parts), **kwargs), ensure_ascii=False, indent=2))
        return 0
    if cmd == "tags":
        print(json.dumps(tags_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "facets":
        print(json.dumps(facets_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "book" and len(sys.argv) > 2:
        print(json.dumps(book_detail(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0 if book_detail(sys.argv[2]).get("ok") else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["panel", "build", "search [q] [--tag T] [--dewey 355] [--personhood] [--combat]", "tags", "facets", "book ID"],
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())