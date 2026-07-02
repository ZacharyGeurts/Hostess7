#!/usr/bin/env pythong
"""K-12 ingest truth filter — 94%% noise / 6%% truth on textbook input."""
from __future__ import annotations

import re
from typing import Any

from field_internet import NOISE_RATIO, TRUTH_RATIO, truth_score_text  # noqa: E402

TRUTH_FLOOR = int(__import__("os").environ.get("HOSTESS7_TRUTH_FLOOR", "30"))
MIN_WORDS = int(__import__("os").environ.get("HOSTESS7_K12_MIN_WORDS", "80"))

EDU_MARKERS = re.compile(
    r"\b(chapter|section|lesson|unit|student|learn|learning|curriculum|grade|"
    r"exercise|problem|definition|theorem|equation|experiment|history|science|"
    r"algebra|biology|chemistry|physics|grammar|reading|writing|government|civics)\b",
    re.I,
)

NOISE_MARKERS = re.compile(
    r"\b(cookie|subscribe|newsletter|sign up|advertisement|click here|buy now|"
    r"javascript required|access denied|404 not found)\b",
    re.I,
)

_WIKI_BOILERPLATE = re.compile(
    r"(privacy policy|terms of use|donate to wikibooks|navigation menu|"
    r"printable version|permanent link|page information|cite this page)",
    re.I,
)


def _clean_fetch_text(text: str, *, publisher: str = "") -> str:
    if publisher.lower() == "wikibooks" or "wikibooks.org" in text[:200].lower():
        lines = []
        for line in text.splitlines():
            if _WIKI_BOILERPLATE.search(line):
                continue
            if NOISE_MARKERS.search(line) and len(line.split()) < 12:
                continue
            lines.append(line)
        return "\n".join(lines)
    return text


def score_k12_text(text: str, *, title: str = "", publisher: str = "") -> dict[str, Any]:
    """Truth-score textbook fetch body — educational signal boost, noise penalty."""
    if not text or not text.strip():
        return {
            "truth_score": 0.0,
            "accepted": False,
            "reason": "empty body",
            "word_count": 0,
            "edu_hits": 0,
            "noise_hits": 0,
        }

    text = _clean_fetch_text(text, publisher=publisher)
    words = [w for w in re.split(r"\W+", text) if len(w) > 1]
    word_count = len(words)
    base = truth_score_text(text)
    edu_hits = len(EDU_MARKERS.findall(text))
    noise_hits = len(NOISE_MARKERS.findall(text))

    score = base + min(25.0, edu_hits * 2.5)
    if title and any(t in text.lower() for t in title.lower().split()[:3] if len(t) > 3):
        score += 5.0
    score -= min(30.0, noise_hits * 8.0)
    if word_count < MIN_WORDS:
        score -= 15.0
    score = max(0.0, min(100.0, round(score, 1)))

    min_words = MIN_WORDS
    if edu_hits >= 6:
        min_words = max(50, MIN_WORDS - 30)
    noise_cap = 3
    if publisher.lower() == "wikibooks" and edu_hits >= 15:
        noise_cap = 8
    accepted = score >= TRUTH_FLOOR and word_count >= min_words and noise_hits < noise_cap

    reason = "ok"
    if not accepted:
        if word_count < MIN_WORDS:
            reason = f"too short ({word_count} words < {MIN_WORDS})"
        elif score < TRUTH_FLOOR:
            reason = f"truth_score {score} < floor {TRUTH_FLOOR}"
        elif noise_hits >= noise_cap:
            reason = "noise markers detected"
        else:
            reason = "rejected"

    return {
        "truth_score": score,
        "accepted": accepted,
        "reason": reason,
        "word_count": word_count,
        "edu_hits": edu_hits,
        "noise_hits": noise_hits,
        "noise_ratio": NOISE_RATIO,
        "truth_ratio": TRUTH_RATIO,
        "truth_floor": TRUTH_FLOOR,
    }