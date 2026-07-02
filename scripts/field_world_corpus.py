#!/usr/bin/env pythong
"""World knowledge corpus — nature, law, faith, games, movies, dewey, truth."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from field_videogame_db import ensure_db, search_games  # noqa: E402
from field_world_catalog import (  # noqa: E402
    ALL_WORLD_ENTRIES,
    DOMAIN_INDEX,
    WORLD_VERSION,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "world" / "corpus.json"


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    ensure_db()
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < WORLD_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        domains = sorted({e.get("domain", "") for e in ALL_WORLD_ENTRIES})
        CORPUS_CACHE.write_text(
            json.dumps({
                "version": WORLD_VERSION,
                "domains": domains,
                "entries": list(ALL_WORLD_ENTRIES),
                "domain_index": DOMAIN_INDEX,
                "videogame_db": str(ROOT / "cache/fieldstorage/brain/videogames/database.json"),
            }, indent=2) + "\n",
            encoding="utf-8",
        )
    return CORPUS_CACHE


def search_world(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    ensure_corpus()
    q = query.lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 2]
    scored: list[tuple[int, dict]] = []
    for item in ALL_WORLD_ENTRIES:
        tags = item.get("tags", ())
        blob = f"{item.get('title','')} {item.get('body','')} {item.get('domain','')} {' '.join(tags)}".lower()
        score = sum(5 if t in blob else 0 for t in tokens)
        if q in blob:
            score += 12
        for kw, dom in DOMAIN_INDEX.items():
            if kw in q and item.get("domain") == dom:
                score += 10
        if score > 0:
            scored.append((score, item))
    vg_hits = search_games(query, limit=4)
    for g in vg_hits:
        scored.append((20, {"domain": "videogames", "title": g.get("title", g.get("name", "")), **g}))
    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    return [x[1] for x in scored[:limit]]


def synthesize_world_paragraphs(query: str) -> list[str]:
    hits = search_world(query, limit=7)
    paras = [
        f"World knowledge — {len(ALL_WORLD_ENTRIES)} entries across nature, law, faith, games, movies, Dewey, truth.",
    ]
    for h in hits:
        title = h.get("title", h.get("name", ""))
        body = str(h.get("body", h.get("description", "")))[:280]
        url = h.get("url", "")
        dom = h.get("domain", "")
        line = f"[{dom}] {title}"
        if body:
            line += f": {body}"
        if url:
            line += f" · {url}"
        paras.append(line)
    if "lie" in query.lower() or "liar" in query.lower():
        paras.append(
            "Shut down lies before they start: truth-score claims, lie-method catalog, "
            "no fabrication in talk window — cite sources or say unknown."
        )
    return paras


def main() -> int:
    ensure_corpus()
    print(f"World entries: {len(ALL_WORLD_ENTRIES)}")
    print(f"METRIC world_entries={len(ALL_WORLD_ENTRIES)}")
    print("OK world-corpus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())