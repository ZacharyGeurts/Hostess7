#!/usr/bin/env pythong
"""Field English lexicon — full dictionary + phonetics for Hostess 7 and AmmoText."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from field_english_catalog import ARPABET_CONSONANTS, ARPABET_VOWELS, catalog_count  # noqa: E402
from field_english_domains import ENGLISH_CORPUS_VERSION, ENGLISH_DOMAINS  # noqa: E402
from field_english_rhetoric import (  # noqa: E402
    RHETORIC_DOMAINS,
    ensure_rhetoric_cache,
    is_rhetoric_query,
    rhetoric_stats,
    search_rhetoric,
    synthesize_rhetoric_paragraphs,
)
from field_english_thesaurus import search_thesaurus, synthesize_thesaurus_paragraphs  # noqa: E402
from field_english_infinite import (  # noqa: E402
    INDEX,
    WORDS_SORTED,
    ingest_catalog,
    infinite_status,
    lookup_word,
    search_infinite,
)

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "english" / "corpus.json"


def build_corpus() -> dict:
    ensure_rhetoric_cache()
    return {
        "version": ENGLISH_CORPUS_VERSION,
        "domains": [dict(d) for d in ENGLISH_DOMAINS],
        "rhetoric_domains": [dict(d) for d in RHETORIC_DOMAINS],
        "domain_count": len(ENGLISH_DOMAINS) + len(RHETORIC_DOMAINS),
        "arpabet": {
            "consonants": list(ARPABET_CONSONANTS),
            "vowels": list(ARPABET_VOWELS),
        },
        "infinite_drive": True,
        "catalog_seed_count": catalog_count(),
        "disclaimer": (
            "Hostess 7 English lexicon is educational — dictionary lookup and ARPAbet phonetics "
            "from public word lists and CMUdict. Not a pronunciation coach for clinical speech therapy."
        ),
    }


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < ENGLISH_CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh or not INDEX.is_file():
        ingest_catalog(vacuum=True)
    doc = build_corpus()
    CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return CORPUS_CACHE


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 1]


def _score_domains(query: str, domains: list[dict]) -> list[tuple[int, dict]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for d in domains:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:1500]}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("phonetic", "arpabet", "pronunciation", "cmudict", "ipa")):
            if d.get("id") in ("phonetics_arpabet", "phonetics_ipa"):
                score += 20
        if any(k in q for k in ("spell", "orthograph", "dictionary", "lexicon")):
            if d.get("id") in ("orthography", "lexicon_policy"):
                score += 18
        if any(k in q for k in ("morphology", "prefix", "suffix", "etymology")):
            if d.get("id") == "morphology":
                score += 15
        if any(k in q for k in ("metaphor", "simile", "figurative", "analogy")):
            if d.get("id") in ("rhetoric_training",) or "metaphor" in str(d.get("id", "")):
                score += 18
        if any(k in q for k in ("thesaurus", "synonym", "antonym")):
            if d.get("id") in ("rhetoric_training", "thesaurus_usage"):
                score += 18
        if any(k in q for k in ("sentence", "syntax", "parallel", "clause")):
            if "sentence" in str(d.get("id", "")) or d.get("id") == "rhetoric_training":
                score += 14
        if any(k in q for k in ("flow", "transition", "cohesion", "cadence", "prose")):
            if d.get("id") in ("rhetoric_training", "natural_flow", "transitions"):
                score += 14
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return scored


def search_english(query: str, *, limit: int = 6) -> list[dict]:
    ensure_corpus()
    out: list[dict] = []
    seen: set[str] = set()
    q = query.lower()

    # Direct word lookup — "pronounce hello", "phonetics of world"
    word_hits: list[str] = []
    for m in re.finditer(r"\b(?:pronounc\w*|phonetic\w*|arpabet|spell(?:ing)?)\s+(?:of\s+)?([a-z']{2,})\b", q):
        word_hits.append(m.group(1))
    for m in re.finditer(r"\b([a-z']{2,})\s+pronunciation\b", q):
        word_hits.append(m.group(1))
    if not word_hits:
        bare = [t for t in _tokens(query) if t.isalpha() and len(t) <= 24]
        if len(bare) == 1:
            word_hits.append(bare[0])

    for w in word_hits:
        hit = lookup_word(w)
        if hit:
            hid = str(hit.get("id", w))
            if hid not in seen:
                seen.add(hid)
                out.append({**hit, "source": "lookup"})

    for row in search_infinite(query, limit=limit):
        wid = str(row.get("id", row.get("word", "")))
        if wid in seen:
            continue
        seen.add(wid)
        out.append({**row, "source": "infinite_drive"})
        if len(out) >= limit:
            break

    try:
        doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        doc = build_corpus()
    all_domains = list(doc.get("domains") or []) + list(doc.get("rhetoric_domains") or RHETORIC_DOMAINS)
    domain_scored = _score_domains(query, all_domains)
    for _, d in domain_scored:
        did = str(d.get("id", ""))
        if did in seen:
            continue
        seen.add(did)
        row = dict(d)
        row["source"] = "domain"
        out.append(row)
        if len(out) >= limit:
            break
    return out[:limit]


def synthesize_english_paragraphs(query: str) -> list[str]:
    if is_rhetoric_query(query):
        return synthesize_rhetoric_paragraphs(query)
    q = query.lower()
    if any(k in q for k in ("thesaurus", "synonym", "antonym")) and "pronounc" not in q:
        return synthesize_thesaurus_paragraphs(query) + synthesize_rhetoric_paragraphs(query)[:2]
    hits = search_english(query, limit=5)
    if not hits:
        hits = search_english("english orthography phonetics dictionary lexicon", limit=3)
    paras: list[str] = []
    pro = os.environ.get("AMOURANTHRTX_HOSTESS") == "1" and os.environ.get("HOSTESS7_PRO", "1") == "1"
    st = infinite_status()
    if pro:
        paras.append(
            f"English lexicon: {st.get('word_count', 0)} words indexed, "
            f"{st.get('phonetic_count', 0)} with ARPAbet, "
            f"spell list {st.get('spell_words', 0)} → {WORDS_SORTED.name}."
        )
    else:
        paras.append(
            "English lexicon note: full American + British word lists merged with CMUdict ARPAbet phonetics. "
            f"Indexed words: {st.get('word_count', 0)}; spell export: cache/fieldstorage/brain/english/spell/."
        )

    for h in hits:
        if h.get("source") == "domain":
            title = h.get("title", "English")
            body = str(h.get("body", "")).strip()
            paras.append(f"{title}: {body}")
        elif h.get("phonetic_arpabet"):
            w = h.get("word", h.get("full_name", ""))
            ph = h.get("phonetic_arpabet", "")
            paras.append(f"Pronunciation — {w}: ARPAbet /{ph}/")
        else:
            w = h.get("word", h.get("full_name", ""))
            body = str(h.get("body", h.get("blob", ""))).strip()[:500]
            paras.append(f"Lexicon — {w}: {body}")

    return paras


def corpus_stats() -> dict:
    ensure_corpus()
    doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    inf = infinite_status()
    rh = rhetoric_stats()
    return {
        "version": doc.get("version", ENGLISH_CORPUS_VERSION),
        "domains": doc.get("domain_count", len(ENGLISH_DOMAINS)),
        "rhetoric_domains": rh.get("domains", 0),
        "thesaurus_clusters": rh.get("thesaurus_clusters", 0),
        "word_count": inf.get("word_count", 0),
        "phonetic_count": inf.get("phonetic_count", 0),
        "spell_words": inf.get("spell_words", 0),
        "infinite_indexed": inf.get("indexed", 0),
        "spell_path": str(WORDS_SORTED),
    }


if __name__ == "__main__":
    ensure_corpus()
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "phonetics pronunciation hello dictionary"
    for p in synthesize_english_paragraphs(q):
        print(p)
        print()