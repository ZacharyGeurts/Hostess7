#!/usr/bin/env pythong
"""Hostess 7 self-familiarization — register all domains, map whole of reality."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT
from field_reality_registry import (
    REALITY_PILLARS,
    REGISTRY_VERSION,
    build_registry,
    ensure_all_corpora,
    search_reality,
    synthesize_reality_paragraphs,
    write_registry,
)

SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
BRIEF = SI / "reality_familiarization.json"
LOG = SI / "reality_familiarize_log.jsonl"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"

FAMILIARITY_PROBES: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "pillar": "physical",
        "question": "What is physical reality in Hostess 7 — physics, space, motion?",
        "must_hit": ("physical", "physics"),
    },
    {
        "pillar": "biological",
        "question": "How does Hostess 7 model biological and medical reality?",
        "must_hit": ("biological", "medical", "life"),
    },
    {
        "pillar": "mental",
        "question": "Mental reality — brain hemispheres, chemistry, consciousness education?",
        "must_hit": ("mental", "brain", "cognition"),
    },
    {
        "pillar": "social",
        "question": "Social reality — law, warfare, people, history?",
        "must_hit": ("social", "law", "people"),
    },
    {
        "pillar": "informational",
        "question": "Informational reality — code, english, truth filter, signals?",
        "must_hit": ("informational", "information", "truth"),
    },
    {
        "pillar": "normative",
        "question": "Normative reality — ethics, justice, LOAC, virtues?",
        "must_hit": ("normative", "ethics", "justice"),
    },
    {
        "pillar": "experiential",
        "question": "Experiential reality — vision, perception, art, rhetoric?",
        "must_hit": ("experiential", "vision", "perception"),
    },
    {
        "pillar": "spiritual_educational",
        "question": "Ultimate meaning and spiritual questions — educational framing?",
        "must_hit": ("spiritual", "meaning", "god"),
    },
    {
        "pillar": "whole",
        "question": "Familiarize with the whole of reality — all Hostess domains?",
        "must_hit": ("whole", "reality", "beyond"),
    },
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _probe_familiarity() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for probe in FAMILIARITY_PROBES:
        q = str(probe["question"])
        hits = search_reality(q, limit=5)
        paras = synthesize_reality_paragraphs(q)
        blob = " ".join(paras).lower()
        must = tuple(str(m) for m in probe.get("must_hit", ()))
        ok = any(m in blob for m in must) and len(hits) >= 2
        rows.append({
            "pillar": probe.get("pillar"),
            "question": q,
            "hits": [h.get("id") for h in hits],
            "paragraphs": len(paras),
            "familiar": ok,
        })
    return rows


def _self_teach_lanes(registry: dict[str, Any]) -> list[dict[str, Any]]:
    """Hostess teaches herself each owned lane — one-line lesson per lane."""
    lessons: list[dict[str, Any]] = []
    for lane in registry.get("lanes") or []:
        lid = lane.get("id", "")
        title = lane.get("title", lid)
        n = lane.get("domain_count", 0)
        cat = lane.get("category", "")
        lesson = f"{title}: {n} domains · category={cat} · corpus={lane.get('corpus_path', '')}"
        lessons.append({"lane": lid, "lesson": lesson, "taught": _ts()})
    return lessons


def run_reality_familiarize(*, teach: bool = True) -> dict[str, Any]:
    ensured = ensure_all_corpora()

    try:
        from field_beyond_corpus import ensure_corpus  # noqa: WPS433

        ensure_corpus()
    except ImportError:
        pass

    try:
        from field_warfare_self_teach import run_warfare_self_teach  # noqa: WPS433

        run_warfare_self_teach()
        ensured["warfare_self_teach"] = True
    except Exception:
        ensured["warfare_self_teach"] = False

    try:
        from field_intelligence_flow import seed_doctrine  # noqa: WPS433
        from field_tools_docs import ensure_index  # noqa: WPS433

        seed_doctrine()
        ensure_index()
        ensured["superintel_doctrine"] = True
    except Exception:
        ensured["superintel_doctrine"] = False

    reg_path = write_registry(ensured=ensured)
    registry = build_registry()
    probes = _probe_familiarity()
    familiar_n = sum(1 for p in probes if p.get("familiar"))
    lessons = _self_teach_lanes(registry) if teach else []

    brief = {
        "updated": _ts(),
        "hostess": "Hostess 7",
        "registry_version": REGISTRY_VERSION,
        "registry_path": str(reg_path),
        "mission": "Add all owned domains · familiarize with whole of reality",
        "lanes": registry.get("lane_count"),
        "domains_total": registry.get("domain_count_total"),
        "pillars": len(REALITY_PILLARS),
        "corpora_ok": sum(1 for v in ensured.values() if v),
        "corpora_total": len(ensured),
        "familiarity_probes": probes,
        "familiarity_passed": familiar_n,
        "familiarity_total": len(probes),
        "self_teach_lessons": lessons,
        "synthesis": synthesize_reality_paragraphs("whole of reality all domains familiarize")[:6],
    }

    SI.mkdir(parents=True, exist_ok=True)
    BRIEF.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "lanes": brief["lanes"],
            "domains": brief["domains_total"],
            "familiar": f"{familiar_n}/{len(probes)}",
        }) + "\n")
    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "arc",
            "tags": ["hostess", "reality", "domains", "familiarize", "whole"],
            "text": (
                f"Reality familiarization — {registry.get('lane_count')} lanes, "
                f"{registry.get('domain_count_total')} domains, "
                f"{familiar_n}/{len(probes)} pillar probes."
            ),
        }) + "\n")

    return brief


def format_report(brief: dict[str, Any]) -> str:
    lines = [
        "=== Hostess 7 — Reality familiarization (whole of reality) ===",
        f"Lanes: {brief.get('lanes')} · domains: {brief.get('domains_total')} · pillars: {brief.get('pillars')}",
        f"Corpora refreshed: {brief.get('corpora_ok')}/{brief.get('corpora_total')}",
        f"Familiarity probes: {brief.get('familiarity_passed')}/{brief.get('familiarity_total')}",
        "",
        "Reality pillars:",
    ]
    for p in REALITY_PILLARS:
        lines.append(f"  • {p.get('title')}")
    lines.append("")
    lines.append("Self-teach lanes (sample):")
    for lesson in (brief.get("self_teach_lessons") or [])[:12]:
        lines.append(f"  • {lesson.get('lesson', '')[:88]}")
    more = len(brief.get("self_teach_lessons") or []) - 12
    if more > 0:
        lines.append(f"  … +{more} more lanes")
    lines.append("")
    lines.append(f"Registry: `{brief.get('registry_path')}`")
    lines.append(f"Brief: `{BRIEF}`")
    return "\n".join(lines)


def main() -> int:
    brief = run_reality_familiarize()
    print(format_report(brief))
    print(f"METRIC reality_lanes={brief.get('lanes')}")
    print(f"METRIC reality_domains={brief.get('domains_total')}")
    print(f"METRIC reality_familiar={brief.get('familiarity_passed')}/{brief.get('familiarity_total')}")
    ok = brief.get("familiarity_passed", 0) >= brief.get("familiarity_total", 1) - 1
    print("OK reality-familiarize" if ok else "PARTIAL reality-familiarize")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())