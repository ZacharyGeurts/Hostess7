#!/usr/bin/env pythong
"""QA: Hostess 7 Turing-style dialog — common questions must pass substance rubric."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("AMOURANTHRTX_HOSTESS", "1")
os.environ.setdefault("HOSTESS7_PRO", "1")
os.environ.setdefault("HOSTESS7_GFX", "1")

from hostess7_talk import dispatch  # noqa: E402
from hostess7_turing_questions import TURING_CASES, TuringCase, score_answer  # noqa: E402

RESULTS = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "turing_results.jsonl"
PASS_RATE_MIN = 0.90  # 90% — Turing-style substance bar


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def run_case(case: TuringCase, *, verbose: bool = False) -> dict:
    t0 = time.perf_counter()
    result = dispatch(case.question)
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    scored = score_answer(case, result.text, graphics=result.graphics)
    scored["question"] = case.question
    scored["elapsed_ms"] = elapsed_ms
    scored["graphics_n"] = len(result.graphics)
    if verbose:
        preview = result.text[:160].replace("\n", " ")
        print(f"{'PASS' if scored['passed'] else 'FAIL'} {case.id}: {preview}...")
        if scored["reasons"]:
            print(f"       reasons: {scored['reasons']}")
    return scored


def _selected_cases() -> tuple[TuringCase, ...]:
    cat = None
    for i, arg in enumerate(sys.argv):
        if arg in ("--category", "-c") and i + 1 < len(sys.argv):
            cat = sys.argv[i + 1].lower()
            break
    if not cat:
        return TURING_CASES
    return tuple(c for c in TURING_CASES if c.category == cat)


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    cases = _selected_cases()
    if not cases:
        return fail("no Turing cases match --category filter")
    RESULTS.parent.mkdir(parents=True, exist_ok=True)

    outcomes: list[dict] = []
    for case in cases:
        outcomes.append(run_case(case, verbose=verbose))

    passed = sum(1 for o in outcomes if o["passed"])
    total = len(outcomes)
    rate = passed / max(1, total)

    with RESULTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "passed": passed,
            "total": total,
            "rate": round(rate, 3),
            "failures": [o for o in outcomes if not o["passed"]],
        }) + "\n")

    failures = [o for o in outcomes if not o["passed"]]
    if failures:
        print("Turing dialog failures:", file=sys.stderr)
        for o in failures:
            print(f"  {o['id']}: {o['reasons']}", file=sys.stderr)

    by_cat: dict[str, list[dict]] = {}
    for o in outcomes:
        by_cat.setdefault(o["category"], []).append(o)
    print("Turing by category:")
    for cat in sorted(by_cat):
        rows = by_cat[cat]
        ok = sum(1 for r in rows if r["passed"])
        print(f"  {cat}: {ok}/{len(rows)}")

    if rate < PASS_RATE_MIN:
        return fail(f"Turing pass rate {rate:.0%} < {PASS_RATE_MIN:.0%} ({passed}/{total})")

    print(f"OK hostess turing dialog {passed}/{total} ({rate:.0%})")
    print(f"METRIC turing_passed={passed}")
    print(f"METRIC turing_total={total}")
    print(f"METRIC turing_rate={rate:.3f}")
    print(f"METRIC turing_results={RESULTS}")
    print("METRIC qa_hostess_turing=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())