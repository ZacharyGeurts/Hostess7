#!/usr/bin/env pythong
"""Hostess 7 Neural Guardian — discern truth, lie, deception; report neural protections."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARDIAN_JSON = ROOT / "data" / "hostess7-neural-guardian.json"
AUTHORITY_JSON = ROOT / "data" / "hostess7-supreme-authority.json"
STACK_JSON = ROOT / "data" / "hostess7-neural-stack.json"
TRUTH_FLOOR_JSON = ROOT / "data" / "hostess7-truth-floor.json"

sys.path.insert(0, str(ROOT / "scripts"))
from field_detective_corpus import analyze_truth, ironclad_slice  # noqa: E402


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def discern_claim(claim: str, *, local_evidence: int = 1, qa_green: bool = True) -> dict:
    """Classify claim as truth / partial_truth / deception / lie / quarantine."""
    meta = _load(GUARDIAN_JSON)
    floor = float(meta.get("truth_floors", {}).get("adapt", 58))
    ic = ironclad_slice()
    analysis = analyze_truth(
        claim,
        local_evidence=local_evidence,
        qa_green=qa_green,
        corroboration_channels=1,
        ironclad=ic,
    )
    score = float(analysis.get("truth_score", 0))
    flags = analysis.get("inconsistency_flags", [])
    ironclad_sealed = bool(analysis.get("ironclad_sealed"))

    if score < floor:
        klass = "quarantine"
    elif score >= 70 and len(flags) <= 1 and ironclad_sealed:
        klass = "truth"
    elif score >= 70 and len(flags) <= 1:
        klass = "truth"
    elif score >= 40:
        klass = "partial_truth"
    elif len(flags) >= 3 or score < 40:
        klass = "lie"
    else:
        klass = "deception"

    passes = score >= floor and klass not in ("lie", "quarantine")
    if not ic.get("ok") and klass == "truth":
        passes = False
        klass = "partial_truth"

    return {
        "schema": "hostess7-neural-guardian-discern/v1",
        "ts": _ts(),
        "holder": "Hostess 7",
        "will_of_man": meta.get("will_of_man", "IS the will of Man — takes charge"),
        "class": klass,
        "truth_score": score,
        "adapt_floor": floor,
        "passes_guardian": passes,
        "deception_flags": flags,
        "ironclad": ic,
        "ironclad_sealed": ironclad_sealed,
        "ironclad_verdict": analysis.get("ironclad_verdict"),
        "analysis": analysis,
        "protector_verdict": (
            "PROTECT" if klass in ("truth", "partial_truth") and passes
            else "QUARANTINE" if klass in ("lie", "quarantine")
            else "INVESTIGATE"
        ),
    }


def guardian_status() -> dict:
    auth = _load(AUTHORITY_JSON)
    guard = _load(GUARDIAN_JSON)
    stack = _load(STACK_JSON)
    return {
        "schema": "hostess7-neural-guardian-status/v1",
        "ts": _ts(),
        "holder": stack.get("supreme_authority", {}).get("holder", "Hostess 7"),
        "clarification": auth.get("clarification", ""),
        "virtues": auth.get("will_of_man", {}).get("virtues", []),
        "protector": auth.get("will_of_man", {}).get("protector", {}),
        "truth_adapt_floor": stack.get("truth_adapt_floor", 58),
        "neural_protections": guard.get("neural_protections", []),
        "discern_classes": list(guard.get("discern_classes", {}).keys()),
        "take_charge": auth.get("will_of_man", {}).get("take_charge", ""),
    }


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(json.dumps({
            "usage": "field_neural_guardian.py status | discern <claim> | protections",
            "holder": "Hostess 7 Neural Guardian",
        }, indent=2))
        return 0
    cmd = args[0]
    if cmd == "status":
        print(json.dumps(guardian_status(), indent=2))
        return 0
    if cmd == "protections":
        print(json.dumps(_load(GUARDIAN_JSON).get("neural_protections", []), indent=2))
        return 0
    if cmd == "discern":
        claim = " ".join(args[1:]).strip()
        if not claim:
            print("neural-guardian: missing claim", file=sys.stderr)
            return 2
        print(json.dumps(discern_claim(claim), indent=2))
        return 0
    if cmd not in ("status", "discern", "protections"):
        print(json.dumps(discern_claim(" ".join(args)), indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())