#!/usr/bin/env pythong
"""Lie detection method catalog — past, present, and emerging future techniques.

Educational synthesis for Hostess 7 people registry and truth scoring.
Not licensed polygraph, courtroom expert testimony, or definitive deception proof.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LIE_METHODS_PATH = ROOT / "cache" / "fieldstorage" / "brain" / "people" / "lie_methods.json"
LIE_METHODS_VERSION = 1

METHODS: tuple[dict[str, Any], ...] = (
    # ── Past / classical ────────────────────────────────────────────────
    {
        "id": "scan_statement_analysis",
        "era": "past",
        "name": "SCAN — Scientific Content Analysis",
        "category": "verbal",
        "reliability": "moderate",
        "body": (
            "Linguistic structure analysis: unexpected shifts, missing affect, altered time order, "
            "extraneous detail, passive distancing. Trained analysts; not single-cue proof."
        ),
    },
    {
        "id": "cbca",
        "era": "past",
        "name": "CBCA — Criteria-Based Content Analysis",
        "category": "verbal",
        "reliability": "moderate",
        "body": "Structured credibility criteria for statements; used in some European jurisdictions.",
    },
    {
        "id": "polygraph",
        "era": "past",
        "name": "Polygraph (psychophysiological arousal)",
        "category": "physiological",
        "reliability": "low_court",
        "body": (
            "Measures GSR, BP, respiration under questioning. Arousal ≠ lie. "
            "Generally inadmissible in US federal criminal trials (Daubert)."
        ),
    },
    {
        "id": "ekman_microexpressions",
        "era": "past",
        "name": "Ekman microexpression leakage",
        "category": "nonverbal",
        "reliability": "moderate",
        "body": "Fleeting universal affect; training improves detection modestly; context-dependent.",
    },
    {
        "id": "reid_interrogation",
        "era": "past",
        "name": "Reid technique behavioral cues",
        "category": "interview",
        "reliability": "contested",
        "body": "Behavioral symptom analysis during accusatory interrogation — high false-confession risk.",
    },
    {
        "id": "voice_stress_analysis",
        "era": "past",
        "name": "Voice stress analysis (VSA)",
        "category": "acoustic",
        "reliability": "weak",
        "body": "Fundamental frequency perturbation claims; weak scientific support for courtroom use.",
    },
    # ── Present / computational ─────────────────────────────────────────
    {
        "id": "hostess_corroboration",
        "era": "present",
        "name": "Hostess 7 computational corroboration",
        "category": "computational",
        "reliability": "high_local",
        "body": (
            "94% noise / 6% truth filter. Cross-check claim against local files, QA GREEN, "
            "infinite drive index, git HEAD, hash verification. truth_score floor 30."
        ),
    },
    {
        "id": "nlp_inconsistency_flags",
        "era": "present",
        "name": "NLP inconsistency heuristics",
        "category": "computational",
        "reliability": "moderate",
        "body": (
            "Absolute language, credibility appeals, hearsay without source, confidence mismatch, "
            "long claims without evidence anchors."
        ),
    },
    {
        "id": "osint_triangulation",
        "era": "present",
        "name": "OSINT triangulation",
        "category": "digital",
        "reliability": "moderate",
        "body": "Independent public sources, archived pages, WHOIS, metadata vs content, timeline alignment.",
    },
    {
        "id": "digital_forensics_hash",
        "era": "present",
        "name": "Digital forensics + hash chain",
        "category": "digital",
        "reliability": "high",
        "body": "SHA-256 verification, write-blocked imaging, chain of custody, log correlation UTC.",
    },
    {
        "id": "multimodal_baseline",
        "era": "present",
        "name": "Multimodal baseline deviation",
        "category": "multimodal",
        "reliability": "moderate",
        "body": "Compare speech rate, pause pattern, gesture rate under low-stakes vs high-stakes topics.",
    },
    {
        "id": "bayesian_claim_fusion",
        "era": "present",
        "name": "Bayesian claim fusion",
        "category": "statistical",
        "reliability": "moderate",
        "body": "Combine independent evidence channels with base-rate priors; output posterior deception risk.",
    },
    # ── Future / emerging ───────────────────────────────────────────────
    {
        "id": "llm_self_consistency",
        "era": "future",
        "name": "LLM self-consistency probing",
        "category": "computational",
        "reliability": "emerging",
        "body": (
            "Re-ask claim variants; measure semantic drift, contradiction density, "
            "and evidence citation stability across paraphrases."
        ),
    },
    {
        "id": "multimodal_fusion_ai",
        "era": "future",
        "name": "Multimodal deception fusion (video+audio+text)",
        "category": "multimodal",
        "reliability": "emerging",
        "body": "Joint embedding of face, voice, transcript; calibrated on labeled datasets; human review gate.",
    },
    {
        "id": "blockchain_attestation",
        "era": "future",
        "name": "Blockchain / signed attestation trails",
        "category": "digital",
        "reliability": "emerging",
        "body": "Timestamped signed statements; detect retroactive edits; not truth alone — provenance only.",
    },
    {
        "id": "graph_contradiction",
        "era": "future",
        "name": "Knowledge-graph contradiction mining",
        "category": "computational",
        "reliability": "emerging",
        "body": "Entity-relationship graph over claims; flag cycles, impossible timelines, mutual exclusivity.",
    },
    {
        "id": "federated_lie_benchmark",
        "era": "future",
        "name": "Federated lie-detection benchmarks",
        "category": "research",
        "reliability": "emerging",
        "body": "Privacy-preserving cross-site calibration; reduces overfit to single lab polygraph datasets.",
    },
    {
        "id": "neuro_markers",
        "era": "future",
        "name": "Neuroimaging deception markers (fMRI/EEG)",
        "category": "physiological",
        "reliability": "research",
        "body": "Laboratory signal patterns; not portable field lie detection; ethical and consent barriers.",
    },
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_catalog() -> dict[str, Any]:
    by_era: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for m in METHODS:
        by_era[m["era"]] = by_era.get(m["era"], 0) + 1
        by_category[m["category"]] = by_category.get(m["category"], 0) + 1
    return {
        "version": LIE_METHODS_VERSION,
        "updated": _ts(),
        "method_count": len(METHODS),
        "by_era": by_era,
        "by_category": by_category,
        "methods": [dict(m) for m in METHODS],
        "disclaimer": (
            "Lie detection methods are educational. No method alone proves deception. "
            "Corroborate with independent evidence. Owner reviews all bad-person flags."
        ),
    }


def ensure_lie_methods() -> Path:
    LIE_METHODS_PATH.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if LIE_METHODS_PATH.is_file():
        try:
            data = json.loads(LIE_METHODS_PATH.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < LIE_METHODS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        LIE_METHODS_PATH.write_text(json.dumps(build_catalog(), indent=2) + "\n", encoding="utf-8")
    return LIE_METHODS_PATH


def list_methods(*, era: str | None = None) -> list[dict[str, Any]]:
    ensure_lie_methods()
    doc = json.loads(LIE_METHODS_PATH.read_text(encoding="utf-8"))
    methods = doc.get("methods") or []
    if era:
        methods = [m for m in methods if m.get("era") == era]
    return methods


def method_ids_for_assessment() -> list[str]:
    """Default stack Hostess applies when scoring a person claim."""
    return [
        "hostess_corroboration",
        "nlp_inconsistency_flags",
        "scan_statement_analysis",
        "osint_triangulation",
        "bayesian_claim_fusion",
        "llm_self_consistency",
    ]


def format_methods_summary() -> str:
    doc = json.loads(ensure_lie_methods().read_text(encoding="utf-8"))
    lines = [
        f"Lie detection catalog — {doc.get('method_count', 0)} methods",
        f"Past: {doc.get('by_era', {}).get('past', 0)} · "
        f"Present: {doc.get('by_era', {}).get('present', 0)} · "
        f"Future: {doc.get('by_era', {}).get('future', 0)}",
    ]
    for era in ("past", "present", "future"):
        for m in list_methods(era=era)[:4]:
            lines.append(f"  [{era}] {m.get('name')} ({m.get('reliability')})")
    return "\n".join(lines)