#!/usr/bin/env pythong
"""Beyond area corpus — well-rounded expert knowledge across all domains."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from field_beyond_domains import (  # noqa: E402
    BEYOND_CATEGORIES,
    BEYOND_DOMAINS,
    CATEGORY_INDEX,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "beyond" / "corpus.json"
CORPUS_VERSION = 5

# Strong keyword → category boost for broad expert routing
CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "science": (
        "physics", "math", "mathematics", "chemistry", "biology", "ecology", "climate",
        "astronomy", "cosmos", "materials", "quantum", "thermodynamics",
    ),
    "technology": (
        "robotics", "robot", "cyber", "security", "aerospace", "aircraft", "electrical",
        "circuit", "civil", "mechanical", "agriculture", "farming", "automation",
    ),
    "humanities": (
        "philosophy", "ethics", "history", "linguistics", "psychology", "education",
        "geopolitics", "economics", "finance", "sociology", "anthropology",
    ),
    "arts": ("music", "architecture", "literature", "narrative", "composition", "urban"),
    "applied": ("energy", "logistics", "supply", "startup", "business", "strategy"),
    "brain": ("workspace", "hemisphere", "callosum", "beyond", "brain area", "synapse", "reality", "domain registry"),
}


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        CORPUS_CACHE.write_text(
            json.dumps(
                {
                    "version": CORPUS_VERSION,
                    "domains": list(BEYOND_DOMAINS),
                    "categories": list(BEYOND_CATEGORIES),
                    "category_index": CATEGORY_INDEX,
                    "domain_count": len(BEYOND_DOMAINS),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return CORPUS_CACHE


def _query_tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def _category_hints(query: str) -> list[str]:
    q = query.lower()
    hints: list[str] = []
    for cat, keys in CATEGORY_KEYWORDS.items():
        if any(k in q for k in keys):
            hints.append(cat)
    return hints


def search_beyond(query: str, *, limit: int = 6, category: str | None = None) -> list[dict]:
    ensure_corpus()
    data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    domains = data.get("domains", list(BEYOND_DOMAINS))
    q = query.lower()
    tokens = _query_tokens(query)
    hints = [category] if category else _category_hints(query)
    scored: list[tuple[int, dict]] = []
    for d in domains:
        title = str(d.get("title", ""))
        body = str(d.get("body", ""))
        tags = " ".join(d.get("tags", ()))
        cat = str(d.get("category", ""))
        blob = f"{title} {tags} {body} {cat}".lower()
        score = sum(4 if t in blob else 0 for t in tokens)
        if q in blob:
            score += 8
        if cat in hints:
            score += 6
        for tag in d.get("tags", ()):
            tag_s = str(tag).lower()
            if len(tag_s) > 3 and re.search(rf"\b{re.escape(tag_s)}\b", q):
                score += 12
        if any(k in q for k in ("whole of reality", "whole of", "all domains", "familiarize", "reality map")):
            if d.get("id") in ("whole_of_reality", "hostess_domain_registry"):
                score += 28
        if "reality" in q and d.get("id") in ("whole_of_reality", "spatial_3d_reality", "physics_foundations"):
            score += 10
        for t in tokens:
            if t in tags.lower():
                score += 5
        if str(d.get("id", "")).replace("_", " ") in q:
            score += 10
        if str(d.get("id")) == "expansion" and not re.search(
            r"\b(expand|grow|corpus|add domain)\b", q
        ):
            score -= 10
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: (-x[0], x[1].get("id", "")))
    seen: set[str] = set()
    out: list[dict] = []
    for _, d in scored:
        did = str(d.get("id", ""))
        if did in seen:
            continue
        seen.add(did)
        out.append(d)
        if len(out) >= limit:
            break
    return out


def search_beyond_multi_category(query: str, *, per_category: int = 1) -> list[dict]:
    """Well-rounded retrieval — top expert hit per category when query is broad."""
    ensure_corpus()
    hints = _category_hints(query)
    if not hints:
        return search_beyond(query, limit=6)
    combined: list[dict] = []
    seen: set[str] = set()
    for cat in hints:
        for d in search_beyond(query, limit=per_category + 2, category=cat):
            did = str(d.get("id", ""))
            if did not in seen:
                seen.add(did)
                combined.append(d)
            if sum(1 for x in combined if x.get("category") == cat) >= per_category:
                break
    if len(combined) < 3:
        combined.extend(search_beyond(query, limit=6 - len(combined)))
    return combined[:8]


def list_categories() -> dict[str, str]:
    ensure_corpus()
    return dict(CATEGORY_INDEX)


def synthesize_beyond_paragraphs(query: str) -> list[str]:
    q_low = query.lower()
    broad = any(
        phrase in q_low
        for phrase in (
            "well rounded", "well-rounded", "overview", "breadth", "all domains",
            "what do you know", "expertise", "beyond knowledge", "everything beyond",
        )
    )
    hits = search_beyond_multi_category(query) if broad else search_beyond(query, limit=6)
    if not hits:
        hits = search_beyond("science technology humanities expert beyond", limit=5)

    if not re.search(r"\b(expand|grow|corpus|add domain)\b", q_low):
        hits = [h for h in hits if h.get("id") != "expansion"]

    paras: list[str] = []
    pro = os.environ.get("AMOURANTHRTX_HOSTESS") == "1" and os.environ.get("HOSTESS7_PRO", "1") == "1"

    if broad and not pro:
        index = "; ".join(f"{k}: {v}" for k, v in CATEGORY_INDEX.items())
        paras.append(f"Beyond index (expert per domain): {index}")

    if not pro and not broad:
        cats = sorted({str(h.get("category", "")) for h in hits if h.get("category")})
        if cats:
            paras.append(
                f"Beyond area — expert synthesis across {', '.join(cats)} "
                f"({len(hits)} domains matched)."
            )

    for h in hits:
        cat = h.get("category", "")
        title = h.get("title", "Beyond")
        body = str(h.get("body", "")).strip()
        prefix = f"[{cat}] " if cat and not pro else ""
        paras.append(f"{prefix}{title}: {body}")

    return paras


def domain_stats() -> dict[str, int]:
    ensure_corpus()
    counts: dict[str, int] = {c: 0 for c in BEYOND_CATEGORIES}
    for d in BEYOND_DOMAINS:
        cat = str(d.get("category", "brain"))
        counts[cat] = counts.get(cat, 0) + 1
    return {"total": len(BEYOND_DOMAINS), "by_category": counts, "version": CORPUS_VERSION}