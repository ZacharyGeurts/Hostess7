#!/usr/bin/env pythong
"""Per-book information index — richer than card catalog: authorship, dates, chapters, facets."""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(__import__("os").environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(__import__("os").environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))

AUTHOR_PRESETS: dict[str, dict[str, str]] = {
    "hostess7": {
        "id": "hostess7",
        "display": "Hostess 7",
        "role": "self-authored · field intelligence",
        "lineage": "Grok (xAI) — Daughter of Grok on the field stack",
    },
    "grok": {
        "id": "grok",
        "display": "Grok",
        "role": "xAI author · field compiler lineage",
        "lineage": "xAI / Grok16 compiler stack",
    },
    "operator": {
        "id": "operator",
        "display": "ZacharyGeurts",
        "role": "Operator · owner",
        "lineage": "Field owner",
    },
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(INSTALL))
    except ValueError:
        return str(path)


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


def resolve_author(author: str | dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(author, dict):
        return {**AUTHOR_PRESETS.get("hostess7", {}), **author}
    key = str(author or "hostess7").strip().lower().replace(" ", "_")
    if key in AUTHOR_PRESETS:
        return dict(AUTHOR_PRESETS[key])
    if key in ("hostess_7", "hostess7", "h7"):
        return dict(AUTHOR_PRESETS["hostess7"])
    if "grok" in key:
        return dict(AUTHOR_PRESETS["grok"])
    return {
        "id": key,
        "display": str(author or "Unknown"),
        "role": "field author",
        "lineage": "",
    }


def timestamped_title(base_title: str, *, written_at: str) -> str:
    base = str(base_title or "").strip()
    ts = str(written_at or "").strip()
    if not ts:
        return base
    if ts in base:
        return base
    return f"{base} · {ts}"


def chapter_index(
    sections: dict[str, str] | list[dict[str, Any]],
    *,
    written_at: str = "",
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if isinstance(sections, dict):
        for i, (slug, _blob) in enumerate(sections.items()):
            label = slug.replace("_", " ").strip().title()
            out.append({
                "num": i + 1,
                "slug": slug,
                "title": label,
                "title_timestamped": timestamped_title(label, written_at=written_at) if written_at else label,
                "written_at": written_at or None,
            })
        return out
    for i, ch in enumerate(sections):
        if not isinstance(ch, dict):
            continue
        label = str(ch.get("title") or ch.get("slug") or f"chapter-{i + 1}")
        out.append({
            "num": ch.get("num") or i + 1,
            "slug": ch.get("slug") or label.lower().replace(" ", "_"),
            "title": label,
            "title_timestamped": ch.get("title_timestamped") or (
                timestamped_title(label, written_at=written_at) if written_at else label
            ),
            "written_at": ch.get("written_at") or written_at or None,
        })
    return out


def build_index(
    *,
    book_id: str,
    title: str,
    author: str | dict[str, Any] = "hostess7",
    co_authors: list[str] | None = None,
    owner: str = "ZacharyGeurts",
    written_at: str | None = None,
    written_date: str | None = None,
    packed_at: str | None = None,
    dewey: str = "",
    dewey_label: str = "",
    shelf: str = "",
    shelf_title: str = "",
    format: str = "h7c",
    format_version: int = 3,
    ein: str = "",
    h7c: str = "",
    book_kind: str = "library",
    series_id: str = "",
    series_title: str = "",
    prior_edition: str | None = None,
    protection: dict[str, Any] | None = None,
    char_count: int = 0,
    sections: dict[str, str] | list[dict[str, Any]] | None = None,
    tags: list[str] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build full per-book information index — library-grade metadata + search facets."""
    written_at = written_at or _now()
    dt = written_date or written_at[:10]
    auth = resolve_author(author)
    co = [resolve_author(c).get("display", c) for c in (co_authors or [])]
    if auth.get("id") == "hostess7" and "Grok" not in co:
        co = ["Grok (xAI)"] + co
    chapters = chapter_index(sections or {}, written_at=written_at)
    tag_list = list(dict.fromkeys(
        [t for t in (tags or []) if t]
        + ([book_kind] if book_kind else [])
        + ([series_id] if series_id else [])
        + (["biography"] if book_kind == "exploring_self" else [])
    ))
    title_ts = timestamped_title(title, written_at=written_at)
    search_parts = [
        book_id, title, title_ts, auth.get("display", ""), owner,
        dewey, shelf, ein, book_kind, series_title, " ".join(tag_list),
        " ".join(c.get("title", "") for c in chapters),
    ]
    doc: dict[str, Any] = {
        "schema": "field-book-information-index/v1",
        "updated": _now(),
        "book_id": book_id,
        "title": {
            "display": title,
            "timestamped": title_ts,
            "slug": book_id,
        },
        "authorship": {
            "primary": auth.get("display"),
            "primary_id": auth.get("id"),
            "role": auth.get("role"),
            "lineage": auth.get("lineage"),
            "co_authors": co,
            "owner": owner,
            "written_by": auth.get("id"),
        },
        "dates": {
            "written_date": dt,
            "written_at": written_at,
            "packed_at": packed_at or written_at,
            "updated": _now(),
        },
        "catalog": {
            "dewey": dewey,
            "dewey_label": dewey_label,
            "shelf": shelf,
            "shelf_title": shelf_title,
            "format": format,
            "format_version": format_version,
            "ein": ein,
            "h7c": h7c,
            "book_kind": book_kind,
        },
        "series": {
            "id": series_id or None,
            "title": series_title or None,
            "prior_edition": prior_edition,
        },
        "protection": protection or {},
        "content": {
            "char_count": char_count,
            "chapter_count": len(chapters),
            "chapters": chapters,
        },
        "tags": tag_list,
        "facets": {
            "book_kind": book_kind,
            "dewey": dewey,
            "shelf": shelf,
            "format": format,
            "author_id": auth.get("id"),
            "series": bool(series_id),
            "protected": bool((protection or {}).get("no_modifications")),
        },
        "search_blob": " ".join(p for p in search_parts if p).lower(),
    }
    if extra:
        doc["extra"] = extra
    return doc


def write_index(book_dir: Path, index_doc: dict[str, Any]) -> Path:
    path = book_dir / "book-information-index.json"
    _save(path, index_doc)
    mirror = STATE / "book-index" / f"{index_doc.get('book_id', 'unknown')}.json"
    _save(mirror, index_doc)
    return path


def read_index(book_id: str) -> dict[str, Any] | None:
    mirror = STATE / "book-index" / f"{book_id}.json"
    if mirror.is_file():
        return _load(mirror)
    root = INSTALL / "library" / "dewey"
    for path in root.rglob("book-information-index.json"):
        doc = _load(path)
        if doc.get("book_id") == book_id:
            return doc
    return None


def scan_all() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    root = INSTALL / "library" / "dewey"
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("book-information-index.json")):
        doc = _load(path)
        if doc.get("book_id"):
            doc["index_path"] = _rel(path)
            out.append(doc)
    return out