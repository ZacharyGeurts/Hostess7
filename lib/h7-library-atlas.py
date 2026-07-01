#!/usr/bin/env pythong
"""H7 Library Atlas — human browse layers + AI passage index from one canonical build."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))

ATLAS_SCHEMA = "h7-library-atlas/v2"
PASSAGE_CHUNK = int(os.environ.get("NEXUS_H7_PASSAGE_CHARS", "960"))
PASSAGE_OVERLAP = int(os.environ.get("NEXUS_H7_PASSAGE_OVERLAP", "120"))
MAX_PASSAGES_PER_BOOK = int(os.environ.get("NEXUS_H7_MAX_PASSAGES", "128"))

COLLECTIONS: tuple[dict[str, Any], ...] = (
    {
        "id": "start-here",
        "title": "Start here",
        "subtitle": "Operator essentials — read these first",
        "icon": "★",
        "kinds": ("guide", "manual"),
        "categories": ("program", "security"),
        "book_ids": (
            "nexus-shield-operator-manual",
            "network-security-field-guide",
            "h7-security-field-corpus",
        ),
    },
    {
        "id": "security-defense",
        "title": "Security & defense",
        "subtitle": "Networks, firewalls, threat response",
        "icon": "🛡",
        "categories": ("security", "military"),
        "dewey_prefix": ("005", "355", "363"),
        "topics": ("security", "network", "firewall", "warfare"),
    },
    {
        "id": "science-stem",
        "title": "Science & STEM",
        "subtitle": "Physics, chemistry, medicine, code",
        "icon": "⚗",
        "categories": ("physics", "chemistry", "medical", "programming"),
        "dewey_prefix": ("500", "540", "610", "005"),
        "topics": ("physics", "chemistry", "medical", "code"),
    },
    {
        "id": "learn-teach",
        "title": "Learn & teach",
        "subtitle": "K-12 textbooks and language",
        "icon": "📖",
        "categories": ("education", "language"),
        "dewey_prefix": ("370", "428", "510"),
        "topics": ("k12", "english", "math"),
        "book_ids": ("h7-k12-field-corpus", "h7-english-field-corpus"),
    },
    {
        "id": "brain-knowledge",
        "title": "Hostess7 brain",
        "subtitle": "Corpus knowledge — vision, people, world",
        "icon": "🧠",
        "formats": ("field-corpus",),
        "topics": ("vision", "people", "world", "memes", "hearing", "imagine"),
    },
    {
        "id": "war-studies",
        "title": "War studies",
        "subtitle": "Strategy, battles, military history",
        "icon": "⚔",
        "war_shelf": True,
        "dewey_prefix": ("355", "940", "973"),
        "book_ids": ("h7-warfare-field-corpus",),
    },
)

TOPIC_DEFS: tuple[dict[str, Any], ...] = (
    {"id": "security", "label": "Security", "aliases": ("firewall", "tls", "dpi", "cyber", "nexus")},
    {"id": "network", "label": "Networking", "aliases": ("tcp", "dns", "ip", "routing", "packet")},
    {"id": "operator", "label": "Operator", "aliases": ("nexus-shield", "panel", "kill", "monitor")},
    {"id": "physics", "label": "Physics", "aliases": ("mechanics", "energy", "quantum")},
    {"id": "chemistry", "label": "Chemistry", "aliases": ("molecule", "reaction", "neurotransmitter")},
    {"id": "medical", "label": "Medicine", "aliases": ("clinic", "health", "anatomy")},
    {"id": "code", "label": "Programming", "aliases": ("python", "software", "algorithm")},
    {"id": "vision", "label": "Vision & motion", "aliases": ("ocr", "camera", "tracking", "perception")},
    {"id": "k12", "label": "K-12 education", "aliases": ("textbook", "openstax", "grade", "math", "science")},
    {"id": "english", "label": "English & writing", "aliases": ("grammar", "literature", "language")},
    {"id": "warfare", "label": "Warfare", "aliases": ("military", "strategy", "battle")},
    {"id": "law", "label": "Law", "aliases": ("legal", "counsel", "statute")},
    {"id": "people", "label": "People registry", "aliases": ("celebrity", "entity", "biography")},
    {"id": "world", "label": "World & civics", "aliases": ("geography", "government", "news")},
)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None


def atlas_dir() -> Path:
    for root in (HOSTESS7_TEAM_FIELD, HOSTESS7_ROOT / "cache" / "fieldstorage"):
        lib = root / "brain" / "library" / "atlas"
        if (root / "brain").is_dir():
            return lib
    return HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "library" / "atlas"


def _kind_for(book: dict[str, Any]) -> str:
    fmt = str(book.get("format", ""))
    if fmt == "field-corpus":
        return "corpus"
    if fmt == "H7":
        return "textbook"
    cat = str(book.get("category", "")).lower()
    if cat in ("program", "security") or "manual" in str(book.get("title", "")).lower():
        return "manual"
    if cat in ("vision", "hearing", "art"):
        return "guide"
    return "book"


def _reading_time_min(char_count: int) -> int:
    return max(1, char_count // 1200)


def _first_sentences(text: str, *, max_len: int = 280) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if not t:
        return ""
    for sep in (". ", "! ", "? "):
        idx = t.find(sep)
        if 40 < idx < max_len:
            return t[: idx + 1].strip()
    return t[:max_len].strip() + ("…" if len(t) > max_len else "")


def _infer_topics(book: dict[str, Any], text_sample: str = "") -> list[str]:
    blob = " ".join(
        str(book.get(k, "")) for k in ("id", "title", "author", "category", "description", "dewey_label")
    ).lower()
    blob += " " + text_sample[:2000].lower()
    found: list[str] = []
    for topic in TOPIC_DEFS:
        tokens = [topic["id"], topic["label"].lower(), *topic.get("aliases", ())]
        if any(tok in blob for tok in tokens if len(str(tok)) > 2):
            found.append(topic["id"])
    if not found:
        cat = str(book.get("category", "")).lower()
        if cat:
            found.append(cat.replace(" ", "_")[:24])
    return found[:8]


def _for_humans(book: dict[str, Any], summary: str) -> str:
    title = book.get("title", "This book")
    author = book.get("author", "")
    dewey = book.get("dewey_label") or book.get("dewey", "")
    kind = _kind_for(book)
    if kind == "corpus":
        return (
            f"{title} is Hostess7 brain knowledge you can browse like a reference shelf. "
            f"It answers questions in context — open it when you need depth on {book.get('category', 'this topic')}."
        )
    parts = [f"{title}"]
    if author:
        parts[0] += f" by {author}"
    parts.append(f"is on the {dewey or 'library'} shelf.")
    if summary:
        parts.append(summary)
    return " ".join(parts)


def _for_ai(book: dict[str, Any], topics: list[str]) -> dict[str, Any]:
    return {
        "kind": _kind_for(book),
        "retrieval_hints": topics[:6],
        "cite_as": f"{book.get('title', book.get('id'))} ({book.get('id')})",
        "format": book.get("format", ""),
        "dewey": book.get("dewey", ""),
        "ready": bool(book.get("ready")),
        "fielded": False,
        "field_depth": 0,
    }


def enrich_book(book: dict[str, Any], *, text_sample: str = "") -> dict[str, Any]:
    desc = str(book.get("description", "") or "")
    sample = text_sample or desc
    summary = _first_sentences(desc) or _first_sentences(sample, max_len=220)
    if not summary and book.get("title"):
        summary = f"{book['title']} — {book.get('category', 'field library')}."
    topics = _infer_topics(book, sample)
    char_count = int(book.get("char_count") or len(sample))
    out = {
        **book,
        "summary": summary,
        "for_humans": _for_humans(book, summary),
        "for_ai": _for_ai(book, topics),
        "topics": topics,
        "kind": _kind_for(book),
        "reading_time_min": _reading_time_min(char_count),
        "collection_ids": [],
    }
    return out


def _book_matches_collection(book: dict[str, Any], coll: dict[str, Any]) -> bool:
    bid = str(book.get("id", ""))
    if bid in (coll.get("book_ids") or ()):
        return True
    if coll.get("war_shelf") and book.get("war_shelf"):
        return True
    fmt = str(book.get("format", ""))
    if coll.get("formats") and fmt in coll["formats"]:
        return True
    if coll.get("kinds") and book.get("kind") in coll["kinds"]:
        return True
    cat = str(book.get("category", "")).lower()
    if coll.get("categories") and cat in coll["categories"]:
        return True
    dewey = str(book.get("dewey", ""))
    for prefix in coll.get("dewey_prefix") or ():
        if dewey.startswith(prefix):
            return True
    topics = set(book.get("topics") or ())
    if coll.get("topics") and topics.intersection(coll["topics"]):
        return True
    return False


def assign_collections(books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for book in books:
        ids = [c["id"] for c in COLLECTIONS if _book_matches_collection(book, c)]
        out.append({**book, "collection_ids": ids})
    return out


def chunk_passages(book_id: str, text: str, *, meta: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    text = (text or "").replace("\r\n", "\n").strip()
    if len(text) < 40:
        return []
    meta = meta or {}
    topics = meta.get("topics") or []
    passages: list[dict[str, Any]] = []
    start = 0
    chunk_i = 0
    while start < len(text) and chunk_i < MAX_PASSAGES_PER_BOOK:
        end = min(len(text), start + PASSAGE_CHUNK)
        chunk = text[start:end]
        if end < len(text):
            brk = max(chunk.rfind("\n\n"), chunk.rfind("\n"), chunk.rfind(". "))
            if brk > PASSAGE_CHUNK // 3:
                chunk = chunk[: brk + 1]
                end = start + len(chunk)
        chunk = chunk.strip()
        if len(chunk) >= 40:
            pid = f"{book_id}:{chunk_i:04d}"
            heading = ""
            m = re.match(r"^#+\s*(.+)$", chunk.split("\n", 1)[0])
            if m:
                heading = m.group(1).strip()
            passages.append({
                "passage_id": pid,
                "book_id": book_id,
                "chunk": chunk_i,
                "text": chunk,
                "char_start": start,
                "char_end": end,
                "heading": heading,
                "topics": topics,
                "title": meta.get("title", book_id),
                "kind": meta.get("kind", "book"),
                "dewey": meta.get("dewey", ""),
            })
            chunk_i += 1
        step = max(len(chunk), 1) - PASSAGE_OVERLAP
        start += max(step, 1)
    return passages


def _topic_index(books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_topic: dict[str, dict[str, Any]] = {}
    for tdef in TOPIC_DEFS:
        by_topic[tdef["id"]] = {
            "id": tdef["id"],
            "label": tdef["label"],
            "aliases": list(tdef.get("aliases", ())),
            "book_ids": [],
            "count": 0,
        }
    for book in books:
        if not book.get("ready"):
            continue
        for tid in book.get("topics") or []:
            row = by_topic.setdefault(tid, {"id": tid, "label": tid.replace("_", " ").title(), "aliases": [], "book_ids": [], "count": 0})
            bid = str(book.get("id", ""))
            if bid and bid not in row["book_ids"]:
                row["book_ids"].append(bid)
                row["count"] = len(row["book_ids"])
    return [v for v in by_topic.values() if v["count"] > 0]


def _collection_index(books: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for coll in COLLECTIONS:
        bids = [str(b["id"]) for b in books if coll["id"] in (b.get("collection_ids") or []) and b.get("ready")]
        if not bids:
            continue
        out.append({
            "id": coll["id"],
            "title": coll["title"],
            "subtitle": coll.get("subtitle", ""),
            "icon": coll.get("icon", "•"),
            "count": len(bids),
            "book_ids": bids,
        })
    return out


def _write_guide(path: Path, atlas: dict[str, Any]) -> None:
    lines = [
        "# Hostess7 Library Atlas",
        "",
        "Read like a person. Retrieve like a model.",
        "",
        "## Start here",
    ]
    for coll in atlas.get("collections") or []:
        if coll["id"] == "start-here":
            for bid in coll.get("book_ids", [])[:6]:
                hit = next((b for b in atlas.get("books", []) if b["id"] == bid), None)
                if hit:
                    lines.append(f"- **{hit['title']}** — {hit.get('summary', '')}")
    lines.extend(["", "## Collections", ""])
    for coll in atlas.get("collections") or []:
        lines.append(f"- {coll.get('icon', '•')} **{coll['title']}** ({coll['count']}) — {coll.get('subtitle', '')}")
    lines.extend([
        "",
        "## For AI agents",
        "",
        f"- Schema: `{ATLAS_SCHEMA}`",
        "- Passages: `brain/library/atlas/passages.jsonl` — one JSON object per line",
        "- Topics: `brain/library/atlas/topics.json`",
        "- Full catalog: `brain/library/atlas/atlas.json`",
        "",
        f"Built: {atlas.get('updated', '')}",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_atlas(
    books: list[dict[str, Any]],
    *,
    text_for_id: Callable[[str], str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Canonical library build — enriches books, writes atlas + passages on field drive."""
    dest = atlas_dir()
    dest.mkdir(parents=True, exist_ok=True)

    enriched: list[dict[str, Any]] = []
    all_passages: list[dict[str, Any]] = []

    for raw in books:
        bid = str(raw.get("id", ""))
        sample = ""
        if text_for_id and raw.get("ready"):
            try:
                sample = text_for_id(bid)[:12000]
            except Exception:
                sample = ""
        row = enrich_book(raw, text_sample=sample)
        enriched.append(row)
        if row.get("ready") and sample and len(sample) > 80:
            all_passages.extend(chunk_passages(bid, sample, meta=row))

    enriched = assign_collections(enriched)
    collections = _collection_index(enriched)
    topics = _topic_index(enriched)

    atlas = {
        "schema": ATLAS_SCHEMA,
        "updated": _now(),
        "motto": "Read like a person. Retrieve like a model.",
        "book_count": len(enriched),
        "ready_count": sum(1 for b in enriched if b.get("ready")),
        "passage_count": len(all_passages),
        "topic_count": len(topics),
        "collection_count": len(collections),
        "collections": collections,
        "topics": topics,
        "books": enriched,
        "ai": {
            "passages_file": "passages.jsonl",
            "passage_chunk_chars": PASSAGE_CHUNK,
            "max_passages_per_book": MAX_PASSAGES_PER_BOOK,
            "retrieval": "search_passages(query) or grep passages.jsonl by topic",
            "truth_filter": "h7-library-truth.py — sentence verdict lands on Ironclad",
            "fielded": False,
            "field_depth": 0,
        },
        "human": {
            "guide_file": "guide.md",
            "start_collection": "start-here",
            "browse_by": ("collections", "topics", "dewey", "title"),
        },
    }

    _save_json(dest / "atlas.json", atlas)
    _save_json(dest / "topics.json", {"schema": "h7-library-topics/v1", "updated": atlas["updated"], "topics": topics})
    _write_passages(dest / "passages.jsonl", all_passages)
    _write_guide(dest / "guide.md", atlas)

    return atlas


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_passages(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    tmp.replace(path)


def load_atlas() -> dict[str, Any] | None:
    path = atlas_dir() / "atlas.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def apply_atlas_to_books(books: list[dict[str, Any]], atlas: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not atlas:
        return books
    by_id = {str(b["id"]): b for b in atlas.get("books") or [] if b.get("id")}
    out: list[dict[str, Any]] = []
    for book in books:
        bid = str(book.get("id", ""))
        merged = {**book, **by_id.get(bid, {})}
        out.append(merged)
    return out


def search_passages(query: str, *, limit: int = 12) -> list[dict[str, Any]]:
    path = atlas_dir() / "passages.jsonl"
    if not path.is_file():
        return []
    toks = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
    if not toks:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            blob = f"{row.get('title', '')} {row.get('heading', '')} {row.get('text', '')} {' '.join(row.get('topics') or [])}".lower()
            score = sum(6 if t in (row.get("topics") or []) else 0 for t in toks)
            score += sum(4 if t in blob else 0 for t in toks)
            if row.get("book_id", "").lower() in query.lower():
                score += 10
            if score > 0:
                scored.append((score, row))
    except OSError:
        return []
    scored.sort(key=lambda x: -x[0])
    return [{**r, "score": s, "excerpt": (r.get("text") or "")[:480]} for s, r in scored[:limit]]


def search_unified(
    query: str,
    books: list[dict[str, Any]],
    *,
    book_search_fn: Callable[[str, int], list[dict[str, Any]]] | None = None,
    limit: int = 24,
) -> dict[str, Any]:
    """Human book hits + AI passage hits in one response."""
    book_hits: list[dict[str, Any]] = []
    if book_search_fn:
        try:
            book_hits = book_search_fn(query, limit=limit)
        except TypeError:
            book_hits = book_search_fn(query, limit)
    passages = search_passages(query, limit=min(12, limit))
    topic_hits = []
    q = query.lower()
    atlas = load_atlas()
    if atlas:
        for topic in atlas.get("topics") or []:
            label = str(topic.get("label", "")).lower()
            if q in label or any(q in str(a).lower() for a in topic.get("aliases") or []):
                topic_hits.append(topic)
    return {
        "ok": True,
        "query": query,
        "books": book_hits,
        "passages": passages,
        "topics": topic_hits[:8],
        "hint_human": "Browse collections or open a book from the list.",
        "hint_ai": "Use passages[] for grounded retrieval; cite passage_id in answers.",
    }


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "atlas"):
        doc = load_atlas() or {"ok": False, "error": "atlas_not_built"}
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("schema") else 1
    if cmd == "passages" and len(sys.argv) >= 3:
        q = " ".join(sys.argv[2:])
        print(json.dumps({"ok": True, "query": q, "hits": search_passages(q)}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "topics":
        atlas = load_atlas()
        print(json.dumps({"ok": True, "topics": (atlas or {}).get("topics", [])}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: h7-library-atlas.py [json|atlas|passages <q>|topics]"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())