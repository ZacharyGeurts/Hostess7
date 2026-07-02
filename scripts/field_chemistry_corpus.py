#!/usr/bin/env pythong
"""Chemistry & neurochemistry corpus — Hostess 7 chemical understandings."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "chemistry" / "corpus.json"

CHEMISTRY_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "neurotransmitters",
        "title": "Neurotransmitters",
        "tags": ("dopamine", "serotonin", "acetylcholine", "norepinephrine", "gaba", "glutamate", "synapse"),
        "body": (
            "Neurotransmitters are chemical messengers crossing synapses. Hostess 7 maps them to cognition: "
            "dopamine drives P1/release focus; acetylcholine boosts memory recall and OCR attention; "
            "norepinephrine elevates blocker urgency; serotonin stabilizes balanced fusion; "
            "glutamate excites fast callosum transfer; GABA inhibits chatter for professional tone. "
            "Levels live in cache/fieldstorage/brain/chemistry/state.json with synapse.jsonl event log."
        ),
    },
    {
        "id": "hormones",
        "title": "Neuromodulators & hormones",
        "tags": ("cortisol", "oxytocin", "endorphin", "hormone", "stress", "reward"),
        "body": (
            "Beyond fast synaptic signals, hormones modulate brain state over longer arcs. "
            "Cortisol routes stress toward blockers and P1 under pressure. "
            "Oxytocin elevates clinic/medical empathy weight. "
            "Endorphins signal reward after GREEN/release verdicts. "
            "Workspace profiles pre-bias chemistry: field→dopamine, clinic→oxytocin, counsel→GABA."
        ),
    },
    {
        "id": "synapse_mechanism",
        "title": "Synapse release mechanism",
        "tags": ("synapse", "release", "decay", "baseline", "pool", "hot"),
        "body": (
            "Synapse pools mirror corpus callosum: hot in-process mirror for sub-ms reads, "
            "persistent state.json for levels, synapse.jsonl for release audit. "
            "Each chemical has baseline + decay; query triggers and workspace profiles spike deltas. "
            "compute_enhancement() derives left/right weights, callosum boost, memory recall, and filter tighten."
        ),
    },
    {
        "id": "enhancements",
        "title": "Chemical enhancements",
        "tags": ("enhance", "boost", "modulate", "chemistry", "brain"),
        "body": (
            "Enhancements alter hemisphered fusion: glutamate accelerates cross-transfer; "
            "GABA/serotonin tighten professional filter; acetylcholine enables deeper thought recall; "
            "dopamine prioritizes analytical P1 paragraphs. "
            "Manual boost: `./linux.sh super chemistry boost dopamine`. "
            "Status: `./Hostess7.sh chemistry`."
        ),
    },
    {
        "id": "general_chemistry",
        "title": "General chemistry foundations",
        "tags": ("chemistry", "molecule", "reaction", "bond", "element", "compound", "ph", "acid", "base"),
        "body": (
            "Chemistry studies matter, bonds, and reactions. Periodic trends, stoichiometry, "
            "acid-base equilibria, redox, and organic functional groups underpin biochemistry. "
            "Hostess 7 holds educational synthesis — not lab instructions. "
            "Neurochemistry is the bridge from general chemistry to brain mechanism on Field."
        ),
    },
)


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    if not CORPUS_CACHE.is_file():
        CORPUS_CACHE.write_text(
            json.dumps({"domains": list(CHEMISTRY_DOMAINS), "version": 1}, indent=2) + "\n",
            encoding="utf-8",
        )
    return CORPUS_CACHE


def search_chemistry(query: str, *, limit: int = 4) -> list[dict]:
    ensure_corpus()
    data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    domains = data.get("domains", list(CHEMISTRY_DOMAINS))
    q = query.lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 2]
    scored: list[tuple[int, dict]] = []
    for d in domains:
        blob = f"{d.get('title', '')} {' '.join(d.get('tags', ()))} {d.get('body', '')}".lower()
        score = sum(3 if t in blob else 0 for t in tokens) + (5 if q in blob else 0)
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def synthesize_chemistry_paragraphs(query: str) -> list[str]:
    hits = search_chemistry(query, limit=4)
    if not hits:
        hits = search_chemistry("neurotransmitter synapse enhancement", limit=3)
    paras: list[str] = []
    pro = os.environ.get("AMOURANTHRTX_HOSTESS") == "1" and os.environ.get("HOSTESS7_PRO", "1") == "1"
    if not pro:
        paras.append(
            "Chemistry note: Hostess 7 models neurotransmitters and hormones as synapse pools "
            "that enhance hemisphered cognition — same biology pattern as callosum transfer."
        )
    for h in hits:
        paras.append(f"{h.get('title', 'Chemistry')}: {h.get('body', '').strip()}")
    return paras