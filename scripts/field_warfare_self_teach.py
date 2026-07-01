#!/usr/bin/env pythong
"""Hostess 7 warfare self-teach — historic lessons first, measures/countermeasures/invincibility."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT
from field_warfare_corpus import (
    WARFARE_CORPUS_VERSION,
    WARFARE_DOMAINS,
    ensure_corpus,
    search_warfare,
    synthesize_warfare_paragraphs,
)

SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
SELF_BRIEF = SI / "warfare_self_teach.json"
SELF_LOG = SI / "warfare_self_teach_log.jsonl"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"

HISTORIC_PREFIX = "historic_"
CORE_LAYERS = (
    "measures_protective_doctrine",
    "countermeasures_active_defense",
    "invincibility_resilience_tactics",
)

SELF_QUIZ_PROMPTS: tuple[str, ...] = (
    "What historic lesson does Fabian strategy teach about countermeasures?",
    "Why did the Maginot Line fail as a sole measure?",
    "How do measures, countermeasures, and invincibility tactics layer in Byzantine defense?",
    "What three layers apply to stun weapons and RF violations under heightened alert?",
    "Thermopylae delay — what went wrong when flanking bypassed the measure?",
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ordered_domains() -> list[dict[str, str | tuple[str, ...]]]:
    historic = [d for d in WARFARE_DOMAINS if str(d.get("id", "")).startswith(HISTORIC_PREFIX)]
    core = [d for d in WARFARE_DOMAINS if d.get("id") in CORE_LAYERS]
    rest = [
        d for d in WARFARE_DOMAINS
        if d not in historic and d not in core
    ]
    return historic + core + rest


def _lesson_card(domain: dict[str, Any]) -> dict[str, Any]:
    did = str(domain.get("id", ""))
    layer = "historic"
    if did in CORE_LAYERS:
        layer = did.split("_")[0] if did != "invincibility_resilience_tactics" else "invincibility"
    elif did.startswith(HISTORIC_PREFIX):
        layer = "historic"
    else:
        layer = "support"
    return {
        "id": did,
        "title": domain.get("title", ""),
        "layer": layer,
        "tags": list(domain.get("tags") or ()),
        "body": str(domain.get("body", "")).strip(),
        "taught": _ts(),
    }


def _self_quiz_results() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for prompt in SELF_QUIZ_PROMPTS:
        hits = search_warfare(prompt, limit=3)
        paras = synthesize_warfare_paragraphs(prompt)
        blob = " ".join(paras).lower()
        ok = len(hits) >= 2 and len(blob) > 200
        rows.append({
            "prompt": prompt,
            "hits": [h.get("id") for h in hits],
            "paragraphs": len(paras),
            "self_grade": "pass" if ok else "review",
        })
    return rows


def run_warfare_self_teach() -> dict[str, Any]:
    ensure_corpus()
    lessons = [_lesson_card(d) for d in _ordered_domains()]
    quiz = _self_quiz_results()
    passed = sum(1 for q in quiz if q.get("self_grade") == "pass")

    brief = {
        "updated": _ts(),
        "hostess": "Hostess 7",
        "corpus_version": WARFARE_CORPUS_VERSION,
        "priority": "historic lessons → measures → countermeasures → invincibility (resilience)",
        "lesson_count": len(lessons),
        "historic_count": sum(1 for l in lessons if l.get("layer") == "historic"),
        "layers": {
            "measures": "Protective measures — awareness, hardening, RF hygiene, egress",
            "countermeasures": "Active response — attrition, lawful neutralization, spectrum logging",
            "invincibility": "Resilience & recovery — depth, redundancy, morale, not literal immunity",
        },
        "lessons": lessons,
        "self_quiz": quiz,
        "self_quiz_passed": passed,
        "self_quiz_total": len(quiz),
        "synthesis_sample": synthesize_warfare_paragraphs(
            "historic measures countermeasures invincibility stun RF terrorist alert"
        )[:4],
    }

    SI.mkdir(parents=True, exist_ok=True)
    SELF_BRIEF.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with SELF_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "self_teach",
            "lessons": len(lessons),
            "quiz_passed": passed,
            "quiz_total": len(quiz),
        }) + "\n")
    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "arc",
            "tags": ["hostess", "warfare", "self-teach", "historic", "alert"],
            "text": (
                f"Warfare self-teach complete — {len(lessons)} lessons "
                f"({brief['historic_count']} historic-first), self-quiz {passed}/{len(quiz)}."
            ),
        }) + "\n")

    return brief


def format_self_teach_report(brief: dict[str, Any]) -> str:
    lines = [
        "=== Hostess 7 — Warfare self-teach (historic priority) ===",
        f"Corpus v{brief.get('corpus_version')} · lessons: {brief.get('lesson_count')} "
        f"(historic: {brief.get('historic_count')})",
        f"Priority: {brief.get('priority')}",
        "",
        "Three layers:",
    ]
    for k, v in (brief.get("layers") or {}).items():
        lines.append(f"  • {k}: {v}")
    lines.append("")
    lines.append(f"Self-quiz: {brief.get('self_quiz_passed')}/{brief.get('self_quiz_total')} internal passes")
    for q in brief.get("self_quiz") or []:
        tag = "PASS" if q.get("self_grade") == "pass" else "REVIEW"
        lines.append(f"  • [{tag}] {q.get('prompt', '')[:72]}")
    lines.append("")
    lines.append(f"Brief: `{SELF_BRIEF}`")
    return "\n".join(lines)


def main() -> int:
    brief = run_warfare_self_teach()
    print(format_self_teach_report(brief))
    print(f"METRIC warfare_self_teach_lessons={brief.get('lesson_count')}")
    print(f"METRIC warfare_self_quiz={brief.get('self_quiz_passed')}/{brief.get('self_quiz_total')}")
    print("OK warfare-self-teach")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())