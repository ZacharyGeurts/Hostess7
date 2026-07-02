#!/usr/bin/env pythong
"""English thesaurus clusters — synonyms, antonyms, register for Hostess 7 rhetoric training."""
from __future__ import annotations

import re
from typing import Any

THESAURUS_VERSION = 1

# Educational seed clusters — expand via english_bulk staging later
THESAURUS_CLUSTERS: tuple[dict[str, Any], ...] = (
    {"lemma": "happy", "synonyms": ("joyful", "content", "pleased", "glad", "cheerful", "delighted"), "antonyms": ("sad", "miserable", "unhappy", "gloomy"), "register": {"formal": ("elated", "jubilant"), "informal": ("stoked", "psyched")}},
    {"lemma": "sad", "synonyms": ("unhappy", "sorrowful", "melancholy", "downcast", "gloomy"), "antonyms": ("happy", "joyful", "elated"), "register": {"formal": ("despondent",), "informal": ("bummed",)}},
    {"lemma": "big", "synonyms": ("large", "huge", "enormous", "vast", "substantial", "immense"), "antonyms": ("small", "tiny", "minute", "slight"), "register": {"formal": ("considerable", "prodigious"), "informal": ("ginormous",)}},
    {"lemma": "small", "synonyms": ("little", "tiny", "minute", "compact", "slight", "modest"), "antonyms": ("big", "large", "huge"), "register": {"formal": ("diminutive", "minuscule"), "informal": ("teeny",)}},
    {"lemma": "fast", "synonyms": ("quick", "rapid", "swift", "speedy", "hasty", "brisk"), "antonyms": ("slow", "sluggish", "leisurely"), "register": {"formal": ("expeditious",), "informal": ("zippy",)}},
    {"lemma": "slow", "synonyms": ("sluggish", "leisurely", "gradual", "unhurried", "languid"), "antonyms": ("fast", "quick", "rapid"), "register": {"formal": ("deliberate",), "informal": ("snail-paced",)}},
    {"lemma": "good", "synonyms": ("excellent", "fine", "superior", "worthy", "sound", "adept"), "antonyms": ("bad", "poor", "inferior", "deficient"), "register": {"formal": ("exemplary", "meritorious"), "informal": ("solid", "decent")}},
    {"lemma": "bad", "synonyms": ("poor", "inferior", "deficient", "faulty", "substandard"), "antonyms": ("good", "excellent", "superior"), "register": {"formal": ("deleterious", "pernicious"), "informal": ("lousy", "crummy")}},
    {"lemma": "beautiful", "synonyms": ("lovely", "gorgeous", "stunning", "elegant", "radiant", "comely"), "antonyms": ("ugly", "hideous", "unsightly"), "register": {"formal": ("exquisite", "resplendent"), "informal": ("drop-dead",)}},
    {"lemma": "ugly", "synonyms": ("hideous", "unsightly", "unattractive", "homely", "grotesque"), "antonyms": ("beautiful", "lovely", "attractive"), "register": {"formal": ("repugnant",), "informal": ("fugly",)}},
    {"lemma": "smart", "synonyms": ("intelligent", "clever", "bright", "astute", "sharp", "wise"), "antonyms": ("stupid", "dull", "foolish", "obtuse"), "register": {"formal": ("erudite", "sagacious"), "informal": ("brainy",)}},
    {"lemma": "stupid", "synonyms": ("foolish", "dull", "obtuse", "senseless", "unwise"), "antonyms": ("smart", "intelligent", "clever"), "register": {"formal": ("inane",), "informal": ("dumb",)}},
    {"lemma": "important", "synonyms": ("significant", "crucial", "vital", "essential", "pivotal", "paramount"), "antonyms": ("trivial", "minor", "insignificant"), "register": {"formal": ("consequential",), "informal": ("big-deal",)}},
    {"lemma": "difficult", "synonyms": ("hard", "challenging", "arduous", "demanding", "tough", "onerous"), "antonyms": ("easy", "simple", "effortless"), "register": {"formal": ("formidable",), "informal": ("tricky",)}},
    {"lemma": "easy", "synonyms": ("simple", "effortless", "straightforward", "uncomplicated", "painless"), "antonyms": ("difficult", "hard", "arduous"), "register": {"formal": ("elementary",), "informal": ("a breeze",)}},
    {"lemma": "speak", "synonyms": ("talk", "say", "utter", "declare", "state", "articulate"), "antonyms": ("silence", "mute", "withhold"), "register": {"formal": ("proclaim", "enunciate"), "informal": ("yak", "chat")}},
    {"lemma": "write", "synonyms": ("compose", "draft", "pen", "author", "inscribe", "record"), "antonyms": ("erase", "delete", "obliterate"), "register": {"formal": ("indite",), "informal": ("jot",)}},
    {"lemma": "think", "synonyms": ("consider", "ponder", "reflect", "contemplate", "reason", "deliberate"), "antonyms": ("ignore", "neglect", "disregard"), "register": {"formal": ("cogitate", "ruminate"), "informal": ("mull over",)}},
    {"lemma": "show", "synonyms": ("display", "reveal", "demonstrate", "exhibit", "present", "illustrate"), "antonyms": ("hide", "conceal", "obscure"), "register": {"formal": ("manifest",), "informal": ("flash",)}},
    {"lemma": "hide", "synonyms": ("conceal", "obscure", "cover", "mask", "veil", "bury"), "antonyms": ("show", "reveal", "expose"), "register": {"formal": ("secrete",), "informal": ("stash",)}},
    {"lemma": "metaphor", "synonyms": ("figure of speech", "analogy", "symbol", "image", "comparison"), "antonyms": ("literalism", "plain statement"), "register": {"formal": ("trope", "figurative language"), "informal": ("word picture",)}},
    {"lemma": "flow", "synonyms": ("rhythm", "cadence", "movement", "continuity", "smoothness", "cohesion"), "antonyms": ("jolt", "disruption", "staccato", "choppiness"), "register": {"formal": ("euphony", "coherence"), "informal": ("vibe",)}},
    {"lemma": "clear", "synonyms": ("plain", "lucid", "transparent", "evident", "distinct", "coherent"), "antonyms": ("opaque", "murky", "vague", "obscure"), "register": {"formal": ("perspicuous",), "informal": ("crystal-clear",)}},
    {"lemma": "vague", "synonyms": ("unclear", "ambiguous", "indistinct", "fuzzy", "nebulous"), "antonyms": ("clear", "precise", "explicit"), "register": {"formal": ("equivocal",), "informal": ("wishy-washy",)}},
    {"lemma": "strong", "synonyms": ("powerful", "robust", "sturdy", "forceful", "potent", "resilient"), "antonyms": ("weak", "feeble", "fragile"), "register": {"formal": ("stalwart",), "informal": ("beefy",)}},
    {"lemma": "weak", "synonyms": ("feeble", "fragile", "frail", "delicate", "flimsy"), "antonyms": ("strong", "powerful", "robust"), "register": {"formal": ("enervated",), "informal": ("wimpy",)}},
    {"lemma": "begin", "synonyms": ("start", "commence", "initiate", "launch", "open", "inaugurate"), "antonyms": ("end", "finish", "conclude", "terminate"), "register": {"formal": ("embark",), "informal": ("kick off",)}},
    {"lemma": "end", "synonyms": ("finish", "conclude", "terminate", "close", "complete", "cease"), "antonyms": ("begin", "start", "commence"), "register": {"formal": ("culminate",), "informal": ("wrap up",)}},
    {"lemma": "help", "synonyms": ("assist", "aid", "support", "facilitate", "serve", "relieve"), "antonyms": ("hinder", "obstruct", "impede"), "register": {"formal": ("abet", "succor"), "informal": ("lend a hand",)}},
    {"lemma": "change", "synonyms": ("alter", "modify", "transform", "shift", "vary", "adapt"), "antonyms": ("preserve", "maintain", "keep"), "register": {"formal": ("transmute",), "informal": ("switch up",)}},
    {"lemma": "truth", "synonyms": ("fact", "verity", "accuracy", "honesty", "reality", "candor"), "antonyms": ("lie", "falsehood", "deception", "fiction"), "register": {"formal": ("veracity",), "informal": ("real talk",)}},
    {"lemma": "lie", "synonyms": ("falsehood", "deception", "fabrication", "untruth", "fiction"), "antonyms": ("truth", "fact", "honesty"), "register": {"formal": ("prevarication", "mendacity"), "informal": ("whopper",)}},
)

_LEMMA_INDEX: dict[str, dict[str, Any]] = {c["lemma"]: c for c in THESAURUS_CLUSTERS}
_WORD_TO_LEMMA: dict[str, str] = {}
for c in THESAURUS_CLUSTERS:
    _WORD_TO_LEMMA[c["lemma"]] = c["lemma"]
    for w in c.get("synonyms", ()) + c.get("antonyms", ()):
        _WORD_TO_LEMMA[str(w).lower()] = c["lemma"]


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 1]


def lookup_thesaurus(word: str) -> dict[str, Any] | None:
    w = word.strip().lower()
    lemma = _WORD_TO_LEMMA.get(w, w)
    return _LEMMA_INDEX.get(lemma)


def search_thesaurus(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for c in THESAURUS_CLUSTERS:
        lemma = c["lemma"]
        syns = " ".join(c.get("synonyms", ()))
        ants = " ".join(c.get("antonyms", ()))
        blob = f"{lemma} {syns} {ants}".lower()
        score = sum(6 if t == lemma else 4 if t in blob else 0 for t in toks)
        if lemma in q:
            score += 10
        if any(k in q for k in ("synonym", "antonym", "thesaurus")) and score > 0:
            score += 8
        if score > 0:
            scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:limit]]


def format_thesaurus_entry(entry: dict[str, Any]) -> str:
    lemma = entry.get("lemma", "")
    syns = ", ".join(entry.get("synonyms", ()))
    ants = ", ".join(entry.get("antonyms", ()))
    reg = entry.get("register") or {}
    formal = ", ".join(reg.get("formal", ()))
    informal = ", ".join(reg.get("informal", ()))
    parts = [f"Thesaurus — {lemma}: synonyms ({syns}); antonyms ({ants})"]
    if formal:
        parts.append(f"formal register: {formal}")
    if informal:
        parts.append(f"informal register: {informal}")
    return ". ".join(parts) + "."


def synthesize_thesaurus_paragraphs(query: str) -> list[str]:
    paras: list[str] = [
        "Thesaurus training — choose synonyms by register (formal/informal) and connotation, not interchangeability alone.",
    ]
    # Extract target word from query patterns
    targets: list[str] = []
    for m in re.finditer(r"\b(?:synonym|antonym|thesaurus)\s+(?:of|for)\s+([a-z]+)\b", query.lower()):
        targets.append(m.group(1))
    for m in re.finditer(r"\b([a-z]+)\s+synonyms?\b", query.lower()):
        targets.append(m.group(1))
    if not targets:
        targets = [t for t in _tokens(query) if t in _WORD_TO_LEMMA][:3]

    hits = search_thesaurus(query, limit=4)
    for w in targets:
        ent = lookup_thesaurus(w)
        if ent:
            paras.append(format_thesaurus_entry(ent))
    for h in hits:
        if h.get("lemma") not in targets:
            paras.append(format_thesaurus_entry(h))
    if len(paras) == 1:
        paras.append(format_thesaurus_entry(hits[0]) if hits else "Try: synonym for happy, antonym of fast.")
    return paras


def thesaurus_stats() -> dict[str, Any]:
    return {"version": THESAURUS_VERSION, "clusters": len(THESAURUS_CLUSTERS), "lemmas": len(_LEMMA_INDEX)}