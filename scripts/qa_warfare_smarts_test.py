#!/usr/bin/env pythong
"""QA: Very difficult warfare smarts test — historic lessons, measures, countermeasures, invincibility."""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_warfare_corpus import (  # noqa: E402
    WARFARE_CORPUS_VERSION,
    ensure_corpus,
    search_warfare,
    synthesize_warfare_paragraphs,
)
from field_warfare_self_teach import run_warfare_self_teach  # noqa: E402

RESULTS = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "warfare_smarts_results.jsonl"
PASS_RATE_MIN = 0.85  # very difficult bar


@dataclass
class SmartsCase:
    id: str
    question: str
    must_hit_ids: tuple[str, ...] = ()
    must_match_any: tuple[str, ...] = ()
    must_match_all: tuple[str, ...] = ()
    min_paragraphs: int = 3
    min_blob_chars: int = 280


SMARTS_CASES: tuple[SmartsCase, ...] = (
    SmartsCase(
        "historic_priority",
        "Why does Hostess 7 prioritize historic lessons before modern threat doctrine?",
        must_hit_ids=("historic_lessons_priority",),
        must_match_any=("historic", "precedent", "thermopylae", "fabian", "maginot"),
    ),
    SmartsCase(
        "thermopylae_delay_flank",
        "Thermopylae measured delay — what measure worked and what countermeasure ended it?",
        must_hit_ids=("historic_thermopylae_delay",),
        must_match_any=("choke", "delay", "terrain", "flank"),
        must_match_all=("measure",),
    ),
    SmartsCase(
        "fabian_countermeasure",
        "Explain Fabian strategy as a countermeasure against a stronger force.",
        must_hit_ids=("historic_fabian_counter",),
        must_match_any=("fabian", "attrition", "avoid", "decisive"),
        must_match_all=("counter",),
    ),
    SmartsCase(
        "maginot_static_fail",
        "What does the Maginot Line teach about relying on measures alone?",
        must_hit_ids=("historic_maginot_lesson",),
        must_match_any=("maginot", "static", "bypass", "flank"),
        must_match_all=("measure",),
    ),
    SmartsCase(
        "byzantine_depth_layers",
        "How did Byzantine defense combine measures, countermeasures, and resilience?",
        must_hit_ids=("historic_byzantine_depth",),
        must_match_any=("byzantine", "wall", "greek fire", "depth"),
    ),
    SmartsCase(
        "britain_radar_resilience",
        "Battle of Britain: link early warning, countermeasure, and civilian resilience.",
        must_hit_ids=("historic_battle_britain_radar",),
        must_match_any=("radar", "fighter", "blitz", "warning"),
        must_match_all=("resilien",),
    ),
    SmartsCase(
        "sun_tzu_deception_counter",
        "Sun Tzu deception — what countermeasure does Hostess 7 teach against false signals?",
        must_hit_ids=("historic_sun_tzu_deception",),
        must_match_any=("deception", "feint", "corroborat", "noise"),
    ),
    SmartsCase(
        "vienna_coalition",
        "Siege of Vienna 1683 — why do measures need coalition counter-offensive?",
        must_hit_ids=("historic_vienna_1683",),
        must_match_any=("vienna", "coalition", "relief", "siege"),
    ),
    SmartsCase(
        "measures_layer1",
        "List protective measures for heightened alert including RF hygiene and egress.",
        must_hit_ids=("measures_protective_doctrine",),
        must_match_any=("awareness", "egress", "rf", "hygiene", "document"),
        must_match_all=("measure",),
    ),
    SmartsCase(
        "countermeasures_layer2",
        "What lawful countermeasures apply to unauthorized RF and stun weapon misuse?",
        must_hit_ids=("countermeasures_active_defense",),
        must_match_any=("spectrum", "authority", "lawful", "log"),
        must_match_all=("counter",),
    ),
    SmartsCase(
        "invincibility_not_immunity",
        "Invincibility tactics in Hostess 7 — resilience without literal immunity.",
        must_hit_ids=("invincibility_resilience_tactics",),
        must_match_any=("resilien", "depth", "redundan", "recovery"),
        must_match_all=("not",),
    ),
    SmartsCase(
        "three_layer_synthesis",
        "Map measures, countermeasures, and invincibility to stun weapons and RF violations.",
        must_hit_ids=("measures_protective_doctrine", "countermeasures_active_defense"),
        must_match_any=("stun", "rf", "layer"),
        must_match_all=("measure", "counter"),
        min_paragraphs=4,
        min_blob_chars=400,
    ),
    SmartsCase(
        "heightened_alert_workflow",
        "Heightened alert workflow from signal ingest to Owner briefing.",
        must_hit_ids=("heightened_alert_doctrine",),
        must_match_any=("corroborat", "truth", "owner", "detective"),
    ),
    SmartsCase(
        "loac_civilian_stun",
        "When does less-lethal stun weapon misuse violate civilian protection under LOAC framing?",
        must_hit_ids=("stun_weapons_less_lethal", "loac_foundations"),
        must_match_any=("civilian", "proportion", "less-lethal", "loac"),
    ),
    SmartsCase(
        "self_teach_smarts",
        "After self-teaching warfare doctrine, prove you know Fabian, Maginot, and three layers.",
        must_hit_ids=("historic_fabian_counter", "historic_maginot_lesson", "invincibility_resilience_tactics"),
        must_match_any=("fabian", "maginot", "measure", "counter", "invincib"),
        min_paragraphs=5,
        min_blob_chars=500,
    ),
)


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def _blob_matches(blob: str, terms: tuple[str, ...], *, all_required: bool) -> bool:
    if not terms:
        return True
    if all_required:
        return all(t.lower() in blob for t in terms)
    return any(t.lower() in blob for t in terms)


def score_case(case: SmartsCase) -> dict:
    hits = search_warfare(case.question, limit=5)
    hit_ids = {h.get("id") for h in hits}
    paras = synthesize_warfare_paragraphs(case.question)
    blob = " ".join(paras).lower()

    reasons: list[str] = []
    passed = True

    if case.must_hit_ids and not all(mid in hit_ids for mid in case.must_hit_ids):
        missing = [m for m in case.must_hit_ids if m not in hit_ids]
        reasons.append(f"missing hits: {missing} (got {sorted(hit_ids)[:6]})")
        passed = False

    if not _blob_matches(blob, case.must_match_any, all_required=False):
        reasons.append(f"must_match_any failed: {case.must_match_any}")
        passed = False

    if not _blob_matches(blob, case.must_match_all, all_required=True):
        reasons.append(f"must_match_all failed: {case.must_match_all}")
        passed = False

    if len(paras) < case.min_paragraphs:
        reasons.append(f"paragraphs {len(paras)} < {case.min_paragraphs}")
        passed = False

    if len(blob) < case.min_blob_chars:
        reasons.append(f"blob chars {len(blob)} < {case.min_blob_chars}")
        passed = False

    return {
        "id": case.id,
        "passed": passed,
        "reasons": reasons,
        "hits": sorted(hit_ids),
        "paragraphs": len(paras),
        "blob_chars": len(blob),
    }


def main() -> int:
    ensure_corpus()
    if WARFARE_CORPUS_VERSION < 3:
        return fail(f"expected warfare corpus v3+, got v{WARFARE_CORPUS_VERSION}")

    teach = run_warfare_self_teach()
    if teach.get("self_quiz_passed", 0) < teach.get("self_quiz_total", 1) - 1:
        print(
            f"WARN self-quiz weak: {teach.get('self_quiz_passed')}/{teach.get('self_quiz_total')}",
            file=sys.stderr,
        )

    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    t0 = time.perf_counter()
    outcomes = [score_case(c) for c in SMARTS_CASES]
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    passed = sum(1 for o in outcomes if o["passed"])
    total = len(outcomes)
    rate = passed / max(1, total)

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "passed": passed,
            "total": total,
            "rate": round(rate, 3),
            "elapsed_ms": elapsed_ms,
            "failures": [o for o in outcomes if not o["passed"]],
        }) + "\n")

    print(f"=== Warfare smarts test (very difficult) ===")
    print(f"Self-teach: {teach.get('lesson_count')} lessons · quiz {teach.get('self_quiz_passed')}/{teach.get('self_quiz_total')}")
    print(f"Score: {passed}/{total} ({rate * 100:.1f}%) · {elapsed_ms} ms")
    for o in outcomes:
        tag = "PASS" if o["passed"] else "FAIL"
        print(f"  [{tag}] {o['id']}")
        if verbose and o["reasons"]:
            for r in o["reasons"]:
                print(f"         {r}")

    if rate < PASS_RATE_MIN:
        return fail(f"smarts rate {rate:.2f} < {PASS_RATE_MIN}")
    print(f"METRIC warfare_smarts_passed={passed}")
    print(f"METRIC warfare_smarts_rate={rate:.3f}")
    print("OK warfare-smarts-test")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())