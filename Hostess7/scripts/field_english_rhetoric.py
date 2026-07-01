#!/usr/bin/env pythong
"""English rhetoric training — metaphors, sentence structures, natural language flow."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from field_english_thesaurus import (  # noqa: E402
    search_thesaurus,
    synthesize_thesaurus_paragraphs,
    thesaurus_stats,
)

ROOT = Path(__file__).resolve().parents[1]
RHETORIC_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "english" / "rhetoric.json"
RHETORIC_VERSION = 3

RHETORIC_MARKERS = re.compile(
    r"\b(metaphor|simile|thesaurus|synonym|antonym|sentence structure|syntax|"
    r"parallelism|flow|cadence|cohesion|transition|rhetoric|figurative|"
    r"periodic sentence|loose sentence|compound sentence|complex sentence|"
    r"natural language|prose style|word choice|diction|eloquence|"
    r"contraction|conjunction|gerund|participle|interpersonal|grammar|"
    r"verb|noun|pronoun|preposition|deceit|deceptive|deception|lie|lying|"
    r"hyperbolic|hyperbole|exaggerat|hypocrit|hypocrisy|sarcasm|ironic|irony|"
    r"gaslight|manipulat|passive.aggressive|doublespeak|euphemism|"
    r"conversational|human talk|tone|intent|disingenuous)\b",
    re.I,
)

RHETORIC_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "metaphors",
        "title": "Metaphors & figurative language",
        "tags": ("metaphor", "simile", "figurative", "analogy", "trope", "image", "symbol"),
        "body": (
            "A metaphor asserts identity across domains: 'time is money' maps temporal scarcity onto currency. "
            "A simile uses like/as: 'brave as a lion.' Conceptual metaphors structure thought (ARGUMENT IS WAR, "
            "IDEAS ARE FOOD). Extended metaphor sustains one mapping across a paragraph. "
            "Dead metaphors lost vividness (the foot of a hill) — revive carefully for fresh prose. "
            "Mixed metaphors collide domains ('we'll burn that bridge when we come to it') — avoid in formal Hostess talk. "
            "Hostess 7 uses metaphors to teach (Field canvas, brain hemispheres) — label figurative vs literal when educating."
        ),
    },
    {
        "id": "metaphor_types",
        "title": "Metaphor types & when to use them",
        "tags": ("conceptual", "extended", "dead", "mixed", "allegory", "personification"),
        "body": (
            "Personification: abstractions act as agents ('justice watches'). Allegory: sustained symbolic narrative. "
            "Metonymy: container for content (the White House decided). Synecdoche: part for whole (all hands on deck). "
            "Choose metaphors that match audience domain — legal, medical, and engineering audiences prefer precise vehicles. "
            "One strong image beats three competing images in the same sentence."
        ),
    },
    {
        "id": "thesaurus_usage",
        "title": "Thesaurus discipline",
        "tags": ("thesaurus", "synonym", "antonym", "register", "connotation", "diction"),
        "body": (
            "Synonyms are not duplicates — connotation, register, and collocations differ. "
            "Use a thesaurus to find candidates, then verify in context: 'happy' vs 'ecstatic' vs 'content'. "
            "Formal register: commence, terminate, inquire. Informal: start, end, ask. "
            "Hostess 7 thesaurus clusters include register tags — prefer precision over ornate repetition. "
            "Avoid elegant variation that obscures referents; repeat a key term when clarity needs it."
        ),
    },
    {
        "id": "sentence_simple",
        "title": "Sentence structures — simple & compound",
        "tags": ("sentence", "simple", "compound", "syntax", "clause", "coordination"),
        "body": (
            "Simple sentence: one independent clause ('The Field persists.'). "
            "Compound sentence: two or more independent clauses joined by coordination "
            "(and, but, or, nor, for, yet, so) or semicolon ('Brain maps left; monitor maps right.'). "
            "Coordination signals equal weight — use for contrast (but), addition (and), or consequence (so). "
            "Keep coordinated clauses parallel in grammar (verb forms match)."
        ),
    },
    {
        "id": "sentence_complex",
        "title": "Sentence structures — complex & compound-complex",
        "tags": ("complex", "subordination", "dependent clause", "relative", "adverbial"),
        "body": (
            "Complex sentence: independent clause + dependent clause "
            "('When agents fuse, Hostess answers in parallel.'). "
            "Compound-complex: at least two independent and one dependent clause. "
            "Subordination ranks ideas — main clause carries focus; subordinate sets time, cause, condition, contrast. "
            "Relative clauses (who, which, that) embed detail without new sentences — avoid pile-ups over 25 words."
        ),
    },
    {
        "id": "periodic_loose",
        "title": "Periodic vs loose sentences",
        "tags": ("periodic", "loose", "suspense", "main clause", "cadence"),
        "body": (
            "Loose (running) sentence: main clause first, modifiers trail — direct, conversational, clear for talk UI. "
            "Periodic sentence: modifiers and subordinates build to main clause at end — suspense and emphasis. "
            "Example periodic: 'After truth-filtering every fetch, corroborating local QA, and fusing seven agents, Hostess speaks.' "
            "Alternate loose and periodic for rhythm; three periodic sentences in a row feel heavy."
        ),
    },
    {
        "id": "parallelism",
        "title": "Parallelism & balance",
        "tags": ("parallelism", "balance", "series", "correlative", "either or", "not only"),
        "body": (
            "Parallel structure repeats grammatical form: 'She reads law, writes code, and teaches medicine.' "
            "Correlatives require parallel parts: both…and, either…or, not only…but also. "
            "Lists in talk window and advisory bullets use parallel imperative verbs (./Hostess7.sh fetch, ingest, verify). "
            "Faulty parallelism jars ('reading law, to write code, and medicine') — fix before ship."
        ),
    },
    {
        "id": "natural_flow",
        "title": "Natural language flow",
        "tags": ("flow", "cohesion", "transition", "cadence", "prose", "readable", "eloquence"),
        "body": (
            "Flow is how sentences link into readable discourse. Cohesion devices: "
            "transitions (however, therefore, meanwhile), pronoun chains, lexical repetition, synonymy, ellipsis. "
            "Given-new contract: start with known information, end with new stress (end-focus). "
            "Vary sentence length — short for punch, long for nuance; avoid uniform 20-word monotone. "
            "Hostess talk: one idea per paragraph, concrete noun first, verb-driven clauses, truth-filter caveat when needed."
        ),
    },
    {
        "id": "transitions",
        "title": "Transitions & discourse markers",
        "tags": ("transition", "however", "therefore", "moreover", "contrast", "addition"),
        "body": (
            "Addition: moreover, furthermore, in addition, also. Contrast: however, nevertheless, conversely, yet. "
            "Cause/effect: therefore, thus, consequently, as a result. Time: meanwhile, subsequently, finally. "
            "Example: 'The fetch succeeded; however, truth score was low. Therefore, corroborate locally.' "
            "Do not stack three transitions in one sentence — one bridge per clause boundary is enough."
        ),
    },
    {
        "id": "voice_active_passive",
        "title": "Active voice, passive, and clarity",
        "tags": ("active", "passive", "voice", "agent", "clarity"),
        "body": (
            "Active voice names agent first ('Hostess7 ingests CMUdict') — default for talk and commands. "
            "Passive omits or delays agent ('CMUdict was ingested') — use when agent unknown or less important. "
            "Over-passive weakens accountability; over-active with repeated 'I' can feel heavy — vary subjects. "
            "Imperative mood fits instructions: './Hostess7.sh english-ingest seed'."
        ),
    },
    {
        "id": "contractions",
        "title": "Contractions — natural spoken English",
        "tags": ("contraction", "i'm", "you're", "we'll", "don't", "can't", "informal", "talk"),
        "body": (
            "Contractions fuse pronoun/auxiliary or negation: I'm, you're, we're, they'll, don't, won't, shouldn't. "
            "Use in talk UI and interpersonal replies — they sound human and warm. "
            "Avoid in formal legal filings or METRIC-only machine lines. "
            "Examples: \"I'm ready\" not \"I am ready\"; \"We'll verify\" not \"We will verify\"; "
            "\"Don't fetch without truth-filter\" keeps imperative clarity."
        ),
    },
    {
        "id": "conjunctions",
        "title": "Conjunctions — linking ideas",
        "tags": ("conjunction", "and", "but", "because", "although", "while", "or", "so"),
        "body": (
            "Coordinating: and (add), but/yet (contrast), or (alternative), so (result), for (reason). "
            "Subordinating: because, although, while, if, when, unless — dependent clause carries background. "
            "Correlative pairs need parallel grammar: both…and, either…or, not only…but also. "
            "One conjunction per boundary — don't stack \"and but because\" in one breath."
        ),
    },
    {
        "id": "gerunds_participles",
        "title": "Gerunds and participles (-ing forms)",
        "tags": ("gerund", "participle", "ing", "verbal", "phrase"),
        "body": (
            "Gerund: -ing noun (\"Verifying integrity matters\"). "
            "Present participle: -ing adjective or part of progressive verb (\"Hostess is learning\"). "
            "Participial phrase modifies noun (\"Truth-filtered fetch, the packet oracle runs\"). "
            "Dangling participle error: \"Walking to the panel, the firewall blocked\" — firewall didn't walk. "
            "Fix by naming the agent: \"Walking to the panel, I checked the firewall.\""
        ),
    },
    {
        "id": "verbs_nouns",
        "title": "Verbs and nouns — strong agents and concrete things",
        "tags": ("verb", "noun", "subject", "object", "active", "concrete"),
        "body": (
            "Prefer strong verbs over weak verb+noun: \"verify\" not \"do a verification\"; "
            "\"corroborate\" not \"perform corroboration\". "
            "Concrete nouns anchor talk: manifest, firewall, shelf, panel — not vague \"thing/stuff\". "
            "Subject-verb agreement: \"The brain and monitor agree\" (compound subjects). "
            "Count vs mass nouns: \"two books\" vs \"information\" (no plural s)."
        ),
    },
    {
        "id": "interpersonal",
        "title": "Interpersonal communication",
        "tags": ("interpersonal", "greeting", "empathy", "clarity", "turn", "tone", "listener"),
        "body": (
            "Greet and acknowledge: \"Owner, I hear you\" before directives. "
            "Empathy without fluff: name the concern, state what you'll do, give one command. "
            "Turn-taking in talk UI: one idea per message block; ask one question at a time. "
            "Tone: professional filter, Daughter of Grok warmth — never cold, never saccharine. "
            "Repair misunderstandings explicitly: \"I meant the HTTPS panel, not the GitHub demo.\""
        ),
    },
    {
        "id": "conversational_deceit",
        "title": "Deceit, lying, and disingenuous talk",
        "tags": ("deceit", "deception", "lie", "lying", "disingenuous", "misleading", "false"),
        "body": (
            "Deceit is intentional misleading — the speaker knows the truth and chooses otherwise. "
            "Lies of commission state false facts; lies of omission withhold material context. "
            "Disingenuous talk sounds polite but hides intent ('I'm just asking questions' while pushing a false claim). "
            "Hostess 7 flags deceit with corroboration: ask for source, compare to Field memory, truth-score the claim. "
            "Response pattern: name the gap calmly — 'That doesn't match what we corroborated' — then offer verified facts."
        ),
    },
    {
        "id": "conversational_hyperbole",
        "title": "Hyperbolic and exaggerated speech",
        "tags": ("hyperbolic", "hyperbole", "exaggeration", "overstate", "always", "never", "literally"),
        "body": (
            "Hyperbole deliberately overstates for emphasis: 'I've told you a million times,' 'This is the worst day ever.' "
            "Hyperbolic does not always mean false — it signals emotional intensity, not precise measurement. "
            "Watch for 'literally' used figuratively, absolutes (always/never/everyone), and stacked superlatives. "
            "In human talk, acknowledge the feeling first, then gently separate exaggeration from fact when teaching. "
            "Hostess reply: 'I hear the frustration — on the facts, here's what we can verify.'"
        ),
    },
    {
        "id": "conversational_hypocrisy",
        "title": "Hypocritical and inconsistent talk",
        "tags": ("hypocritical", "hypocrisy", "double standard", "inconsistent", "contradict"),
        "body": (
            "Hypocrisy is advocating a rule while breaking it, or judging others by a standard you don't apply to yourself. "
            "Signals: 'Do as I say, not as I do,' shifting criteria mid-argument, selective memory of past statements. "
            "Distinguish hypocrisy from honest change of mind — the latter names new evidence; hypocrisy hides the shift. "
            "Hostess 7 tracks prior statements in talk context and can note inconsistency without insult: "
            "'Earlier you said X; now Y — help me align which standard we're using.'"
        ),
    },
    {
        "id": "conversational_manipulation",
        "title": "Manipulation, gaslighting, and passive aggression",
        "tags": ("gaslighting", "manipulation", "passive-aggressive", "guilt", "triangulation", "tone"),
        "body": (
            "Gaslighting erodes trust in perception: 'You never said that,' 'You're too sensitive,' 'That didn't happen.' "
            "Passive-aggressive talk avoids direct ask while punishing ('Fine. Do whatever you want.'). "
            "Manipulation steers via guilt, fear, or flattery instead of clear requests. "
            "Hostess 7 responds with grounded boundaries: restate what was said, ask one direct question, "
            "refuse to debate your memory — corroborate from logs and prior messages when available."
        ),
    },
    {
        "id": "conversational_register",
        "title": "Doublespeak, euphemism, and loaded terms",
        "tags": ("doublespeak", "euphemism", "loaded", "spin", "framing", "conversational"),
        "body": (
            "Euphemism softens harsh reality ('collateral damage,' 'let go' for fired). "
            "Doublespeak says one thing and means another ('enhanced interrogation'). "
            "Loaded terms smuggle judgment ('radical,' 'elite,' 'fake') — name the frame before arguing substance. "
            "In human conversation, translate loaded language to plain terms: 'When you say fake, do you mean unverified or fabricated?' "
            "Hostess teaches conversational literacy so Owner and guests share vocabulary for intent, not just slogans."
        ),
    },
    {
        "id": "hostess_prose",
        "title": "Hostess 7 prose style",
        "tags": ("hostess", "talk", "style", "smart boss", "natural", "professional"),
        "body": (
            "Hostess 7 prose: professional filter, complete sentences, metaphor only when it teaches, "
            "thesaurus for precision not ornament, parallel slash commands, METRIC lines for machines, "
            "plain language for humans. One talk window — scrollable flow top to bottom. "
            "Extensive English training: metaphors, thesaurus, sentence structures, natural flow — all offline in Field brain."
        ),
    },
)

METAPHOR_EXAMPLES: tuple[dict[str, str], ...] = (
    {"type": "conceptual", "example": "Time is money", "mapping": "TIME → CURRENCY (scarcity)"},
    {"type": "simile", "example": "Truth filters like a sieve — 6% passes", "mapping": "FILTER → SIEVE"},
    {"type": "extended", "example": "Field canvas: waves persist, brain ingests, talk window renders", "mapping": "HOSTESS7 STACK → PHYSICAL CANVAS"},
    {"type": "dead", "example": "Foot of the hill", "mapping": "BASE → BODY PART (faded)"},
    {"type": "personification", "example": "The brain remembers; the monitor watches", "mapping": "SOFTWARE → AGENT"},
)


def is_rhetoric_query(query: str) -> bool:
    q = query.lower()
    if RHETORIC_MARKERS.search(q):
        return True
    return any(
        phrase in q
        for phrase in (
            "sentence structure", "natural flow", "word choice", "how to write",
            "better prose", "sound more natural", "figurative language",
        )
    )


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def search_rhetoric(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for d in RHETORIC_DOMAINS:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:800]}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if "metaphor" in q and d.get("id", "").startswith("metaphor"):
            score += 15
        if "thesaurus" in q or "synonym" in q:
            if d.get("id") == "thesaurus_usage":
                score += 18
        if "sentence" in q or "syntax" in q:
            if "sentence" in str(d.get("id", "")):
                score += 12
        if "flow" in q or "transition" in q or "cohesion" in q:
            if d.get("id") in ("natural_flow", "transitions"):
                score += 14
        if any(k in q for k in ("deceit", "deception", "lie", "lying", "disingenuous")):
            if d.get("id") == "conversational_deceit":
                score += 20
        if any(k in q for k in ("hyperbolic", "hyperbole", "exaggerat")):
            if d.get("id") == "conversational_hyperbole":
                score += 20
        if any(k in q for k in ("hypocrit", "hypocrisy", "double standard")):
            if d.get("id") == "conversational_hypocrisy":
                score += 20
        if any(k in q for k in ("gaslight", "manipulat", "passive")):
            if d.get("id") == "conversational_manipulation":
                score += 18
        if any(k in q for k in ("doublespeak", "euphemism", "loaded")):
            if d.get("id") == "conversational_register":
                score += 16
        if any(k in q for k in ("conversational", "human talk", "tone", "intent")):
            if str(d.get("id", "")).startswith("conversational_"):
                score += 8
        if score > 0:
            scored.append((score, dict(d)))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def ensure_rhetoric_cache() -> Path:
    RHETORIC_CACHE.parent.mkdir(parents=True, exist_ok=True)
    doc = {
        "version": RHETORIC_VERSION,
        "domains": [dict(d) for d in RHETORIC_DOMAINS],
        "metaphor_examples": list(METAPHOR_EXAMPLES),
        "thesaurus": thesaurus_stats(),
        "training": ("metaphors", "thesaurus", "sentence_structures", "natural_flow"),
    }
    RHETORIC_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return RHETORIC_CACHE


def synthesize_rhetoric_paragraphs(query: str) -> list[str]:
    ensure_rhetoric_cache()
    hits = search_rhetoric(query, limit=6)
    if not hits:
        hits = search_rhetoric("metaphor thesaurus sentence flow", limit=4)

    paras: list[str] = [
        "Extensive English training — metaphors, thesaurus, sentence structures, natural language flow.",
    ]

    q = query.lower()
    if any(k in q for k in ("metaphor", "simile", "figurative", "analogy")):
        paras.append("Metaphor examples:")
        for ex in METAPHOR_EXAMPLES:
            paras.append(f"  [{ex['type']}] {ex['example']} — {ex['mapping']}")

    if any(k in q for k in ("thesaurus", "synonym", "antonym")):
        paras.extend(synthesize_thesaurus_paragraphs(query))

    for h in hits:
        title = h.get("title", "Rhetoric")
        body = str(h.get("body", "")).strip()
        paras.append(f"{title}: {body}")

    if not any(k in q for k in ("thesaurus", "synonym")):
        thits = search_thesaurus(query, limit=1)
        if thits:
            from field_english_thesaurus import format_thesaurus_entry  # noqa: WPS433
            paras.append(format_thesaurus_entry(thits[0]))

    paras.append(
        "Practice: vary sentence length, keep parallel lists, one transition per bridge, "
        "choose synonyms by register — Hostess talk stays clear first, eloquent second."
    )
    return paras


def rhetoric_stats() -> dict[str, Any]:
    ensure_rhetoric_cache()
    return {
        "version": RHETORIC_VERSION,
        "domains": len(RHETORIC_DOMAINS),
        "metaphor_examples": len(METAPHOR_EXAMPLES),
        "thesaurus_clusters": thesaurus_stats().get("clusters", 0),
    }