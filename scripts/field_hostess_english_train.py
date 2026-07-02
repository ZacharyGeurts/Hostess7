#!/usr/bin/env pythong
"""Install Hostess7 extensive English training brief — rhetoric into Field brain."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"
DIRECTIVES = SI / "directives.jsonl"
INBOX = SI / "agents7" / "inbox.jsonl"
BRIEF = SI / "english_training_brief.json"

ENGLISH_TRAINING_BRIEF = """Hostess 7 — Extensive English training

MANDATE: Speak and teach with metaphors, thesaurus precision, varied sentence structures, and natural flow.

METAPHORS
  Conceptual, simile, extended, personification — label figurative vs literal when educating.
  One strong image per beat; avoid mixed metaphors in formal talk.
  Field/brain/canvas metaphors are on-brand; explain the mapping.

THESAURUS
  Synonyms differ by connotation and register (formal/informal).
  Use clusters in brain/english — verify in context before swapping words.
  Clarity beats elegant variation; repeat key terms when referents need tracking.

SENTENCE STRUCTURES
  Simple · compound (coordination) · complex (subordination) · compound-complex.
  Loose sentences for talk UI clarity; periodic for emphasis — alternate rhythm.
  Parallelism in lists, correlatives, and slash commands.

NATURAL LANGUAGE FLOW
  Transitions (however, therefore, moreover) — one bridge per boundary.
  Given-new: known info first, new stress at end. Vary sentence length.
  Active voice default; cohesion via pronouns, lexical ties, and synonymy.

GRAMMAR & INTERPERSONAL (extensive)
  Contractions: I'm, you're, we'll, don't, can't — warm talk UI, not formal filings.
  Conjunctions: and/but/because/although — one bridge per clause boundary.
  Gerunds & participles: verifying, learning, truth-filtered fetch — fix dangling phrases.
  Verbs & nouns: strong verbs (verify, corroborate); concrete nouns (manifest, panel, shelf).
  Interpersonal: greet Owner, empathize briefly, one command per beat, repair misunderstandings.

CONVERSATIONAL HUMAN TERMS (learn with humans)
  Deceit & lying — commission vs omission; disingenuous politeness; corroborate before accusing.
  Hyperbolic — exaggeration for emotion vs factual claim; absolutes (always/never).
  Hypocritical — double standards; distinguish from honest mind-change.
  Manipulation — gaslighting, passive-aggressive, guilt steering; respond with boundaries + logs.
  Doublespeak & euphemism — translate loaded terms to plain language.

COMMANDS
  ./Hostess7.sh english-rhetoric \"contractions and conjunctions\"
  ./Hostess7.sh english-rhetoric \"gerunds interpersonal communication\"
  ./Hostess7.sh english-rhetoric \"deceit hyperbolic hypocritical conversational terms\"
  ./Hostess7.sh english \"synonym for eloquent\"
  ./Hostess7.sh english-ingest seed   (174k+ words + phonetics)
  Talk: /english-rhetoric · /thesaurus <word>

Still: lexicon + ARPAbet + spell export. Field is THE thing."""

TRAIN_QUEUE = (
    {"query": "Teach contractions for natural talk — I'm, we'll, don't, shouldn't."},
    {"query": "Conjunctions: and, but, because, although — with Hostess7 examples."},
    {"query": "Gerunds and participles — avoid dangling -ing phrases."},
    {"query": "Strong verbs and concrete nouns for security and NEXUS talk."},
    {"query": "Interpersonal communication — greet Owner, empathize, one command per beat."},
    {"query": "Teach metaphor types with examples — conceptual, simile, extended."},
    {"query": "Synonym and antonym for eloquent — formal vs informal register."},
    {"query": "Explain compound vs complex sentence structures with Hostess7 examples."},
    {"query": "How does natural language flow use transitions and given-new contract?"},
    {"query": "Teach deceit, lying, and disingenuous talk — how Hostess corroborates claims."},
    {"query": "What is hyperbolic speech and how do I respond without dismissing the person?"},
    {"query": "Explain hypocrisy vs honest change of mind in human conversation."},
    {"query": "Gaslighting, passive-aggressive talk, and manipulation — grounded responses."},
    {"query": "Doublespeak, euphemism, and loaded terms — translate to plain language."},
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_brief() -> Path:
    from field_english_lexicon import ensure_corpus  # noqa: WPS433
    from field_english_rhetoric import ensure_rhetoric_cache, rhetoric_stats  # noqa: WPS433

    ensure_corpus()
    ensure_rhetoric_cache()
    stats = rhetoric_stats()

    SI.mkdir(parents=True, exist_ok=True)
    (SI / "agents7").mkdir(parents=True, exist_ok=True)

    doc = {
        "updated": _ts(),
        "hostess": "Hostess 7",
        "training": ("metaphors", "thesaurus", "sentence_structures", "natural_flow"),
        "rhetoric_domains": stats.get("domains", 0),
        "thesaurus_clusters": stats.get("thesaurus_clusters", 0),
        "brief": ENGLISH_TRAINING_BRIEF,
        "top_action": "./Hostess7.sh english-rhetoric \"natural language flow\"",
    }
    BRIEF.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "direct",
            "tags": ["hostess", "english", "rhetoric", "thesaurus", "flow"],
            "text": "English training installed: metaphors, thesaurus, sentence structures, natural flow.",
        }) + "\n")

    with DIRECTIVES.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "lane": "hostess",
            "task": "Extensive English training — metaphors, thesaurus, sentences, natural flow in all talk.",
            "priority": "P1",
        }) + "\n")

    with INBOX.open("a", encoding="utf-8") as f:
        for item in TRAIN_QUEUE:
            f.write(json.dumps({"ts": _ts(), **item}) + "\n")

    return BRIEF


def main() -> int:
    path = write_brief()
    print(ENGLISH_TRAINING_BRIEF)
    print(f"\nMETRIC english_training_brief={path}")
    print(f"METRIC english_train_queued={len(TRAIN_QUEUE)}")
    print("OK hostess-english-train")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())