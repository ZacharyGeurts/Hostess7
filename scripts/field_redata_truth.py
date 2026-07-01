#!/usr/bin/env pythong
"""Redata truth filter — 94% noise / 6% truth before SDF imaging sticks.

Runs on every Mayer segment at redata time. Lossless bytes always kept; rejected
segments land in brain/sdf/quarantine/ with full audit trail in truth_filter.jsonl.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_detective_corpus import _deception_flags  # noqa: E402
from field_internet import NOISE_RATIO, TRUTH_RATIO, truth_score_text  # noqa: E402

TRUTH_FLOOR = int(os.environ.get("HOSTESS7_REDATA_TRUTH_FLOOR", "28"))
MIN_WORDS = int(os.environ.get("HOSTESS7_REDATA_MIN_WORDS", "120"))

OPERATOR_MARKERS = re.compile(
    r"\b(field|grep|binding|dispatch|oracle|entropy|thermo|phi|flow|nexus|queen|"
    r"gpu|fabric|jsonl|stderr|operator|implemented|metaphor|philosophy|visual|"
    r"chapter|objective|drill|receipt|perimeter|packet|die|socket)\b",
    re.I,
)

HONESTY_MARKERS = re.compile(
    r"\b(implemented|metaphor|philosophy|visual|honest|label|rocks?|grep)\b",
    re.I,
)

NOISE_MARKERS = re.compile(
    r"\b(cookie|subscribe|newsletter|sign up|advertisement|click here|buy now|"
    r"javascript required|access denied|404 not found|limited time offer)\b",
    re.I,
)

MARKETING_MARKERS = re.compile(
    r"\b(best in class|world[- ]class|revolutionary|game[- ]changing|"
    r"industry[- ]leading|unparalleled|cutting[- ]edge solution)\b",
    re.I,
)

OWNER_SOURCES = (
    "field_primer",
    "field technology",
    "content/chapters",
    "textbook",
    "hostess7",
    "field",
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def score_redata_text(
    text: str,
    *,
    source: str = "",
    title: str = "",
) -> dict[str, Any]:
    """Truth-score a redata segment — operator signal up, noise/marketing down."""
    if not text or not text.strip():
        return {
            "truth_score": 0.0,
            "accepted": False,
            "reason": "empty segment",
            "word_count": 0,
            "operator_hits": 0,
            "honesty_hits": 0,
            "noise_hits": 0,
            "marketing_hits": 0,
            "deception_flags": [],
            "noise_ratio": NOISE_RATIO,
            "truth_ratio": TRUTH_RATIO,
            "truth_floor": TRUTH_FLOOR,
        }

    words = [w for w in re.split(r"\W+", text) if len(w) > 1]
    word_count = len(words)
    base = truth_score_text(text)
    operator_hits = len(OPERATOR_MARKERS.findall(text))
    honesty_hits = len(HONESTY_MARKERS.findall(text))
    noise_hits = len(NOISE_MARKERS.findall(text))
    marketing_hits = len(MARKETING_MARKERS.findall(text))
    flags = _deception_flags(text)

    score = base + min(22.0, operator_hits * 1.8) + min(12.0, honesty_hits * 2.0)
    score -= min(24.0, noise_hits * 10.0)
    score -= min(18.0, marketing_hits * 6.0)
    score -= len(flags) * 5.0

    low_source = source.lower()
    if any(s in low_source for s in OWNER_SOURCES):
        score += 8.0
    if title and any(t in text.lower() for t in title.lower().split()[:4] if len(t) > 3):
        score += 4.0

    score = max(0.0, min(100.0, round(score, 1)))

    min_words = MIN_WORDS
    if operator_hits >= 8:
        min_words = max(80, MIN_WORDS - 40)

    noise_cap = 2
    if operator_hits >= 10 and honesty_hits >= 2:
        noise_cap = 4

    accepted = (
        score >= TRUTH_FLOOR
        and word_count >= min_words
        and noise_hits < noise_cap
        and marketing_hits < 3
    )

    reason = "ok"
    if not accepted:
        if word_count < min_words:
            reason = f"too short ({word_count} < {min_words})"
        elif score < TRUTH_FLOOR:
            reason = f"truth_score {score} < floor {TRUTH_FLOOR}"
        elif noise_hits >= noise_cap:
            reason = "noise markers"
        elif marketing_hits >= 3:
            reason = "marketing fluff"
        else:
            reason = "rejected"

    risk = "low" if score >= 70 else "medium" if score >= 40 else "high"

    return {
        "truth_score": score,
        "accepted": accepted,
        "reason": reason,
        "deception_risk": risk,
        "deception_flags": flags,
        "word_count": word_count,
        "operator_hits": operator_hits,
        "honesty_hits": honesty_hits,
        "noise_hits": noise_hits,
        "marketing_hits": marketing_hits,
        "noise_ratio": NOISE_RATIO,
        "truth_ratio": TRUTH_RATIO,
        "truth_floor": TRUTH_FLOOR,
        "recommended_action": "redata" if accepted else "quarantine",
    }


def append_truth_log(path: Path, entry: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")