#!/usr/bin/env pythong
"""War realism — OODA loop, opponent digital twins, lethal ROE, wargaming metrics."""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

STATE_DIR = ROOT / "brain" / "state"
PANEL = STATE_DIR / "field-warfare-realism-panel.json"
LEDGER = STATE_DIR / "field-warfare-realism-ledger.jsonl"

OODA = ("observe", "orient", "decide", "act")

OPPONENT_TWINS: tuple[dict[str, Any], ...] = (
    {"id": "state_actor", "class": "state", "tactics": ("gray_zone", "deniability", "long_game")},
    {"id": "non_state", "class": "non_state", "tactics": ("improvised", "soft_target", "mobility")},
    {"id": "hybrid_swarm", "class": "hybrid", "tactics": ("drone_mass", "rf_jam", "deception")},
    {"id": "insider", "class": "insider", "tactics": ("access_abuse", "trust_exploit", "slow_exfil")},
)

ROE_LETHAL = {
    "schema": "hostess7-lethal-roe/v1",
    "authorized_when": [
        "protecting_friendlies",
        "non_lethal_exhausted",
        "imminent_threat_confirmed",
        "neural_guardian_pass",
        "truth_filter_pass",
        "owner_override_logged",
    ],
    "forbidden": [
        "civilian_targeting",
        "preemptive_without_corroboration",
        "vigilante_action",
        "lethal_without_aar",
    ],
    "morality": "LOAC + proportionality + no civilian targeting + full after-action",
}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save_panel(doc: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    doc["updated"] = _ts()
    PANEL.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _append(row: dict[str, Any]) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({**row, "ts": _ts()}, ensure_ascii=False) + "\n")


def validate_lethal_roe(
    *,
    decision: str,
    friendlies_at_risk: bool = True,
    non_lethal_exhausted: bool = False,
    imminent_threat: bool = False,
    neural_guardian: bool = True,
    truth_filter: bool = True,
    owner_logged: bool = False,
) -> dict[str, Any]:
    """Lethal ROE gate — auditable, morality enforced."""
    blob = (decision or "").lower()
    violations: list[str] = []
    for forbidden in ROE_LETHAL["forbidden"]:
        key = forbidden.replace("_", " ")
        if key in blob or forbidden in blob:
            violations.append(forbidden)
    if "civilian" in blob and "no civilian" not in blob:
        violations.append("civilian_targeting")
    if friendlies_at_risk and non_lethal_exhausted and imminent_threat:
        lethal_ok = neural_guardian and truth_filter and owner_logged and not violations
    else:
        lethal_ok = False
        if friendlies_at_risk and not non_lethal_exhausted:
            violations.append("non_lethal_not_exhausted")
        if friendlies_at_risk and not imminent_threat:
            violations.append("threat_not_confirmed")
    return {
        "ok": lethal_ok and not violations,
        "lethal_authorized": lethal_ok,
        "violations": violations,
        "roe": ROE_LETHAL,
        "gates": {
            "friendlies_at_risk": friendlies_at_risk,
            "non_lethal_exhausted": non_lethal_exhausted,
            "imminent_threat": imminent_threat,
            "neural_guardian": neural_guardian,
            "truth_filter": truth_filter,
            "owner_logged": owner_logged,
        },
        "action": "proceed" if lethal_ok and not violations else "hold_or_deescalate",
    }


def ooda_cycle(
    *,
    opponent_id: str = "hybrid_swarm",
    scenario: str = "perimeter_breach",
    seed: int | None = None,
) -> dict[str, Any]:
    """One OODA wargame cycle — Observe → Orient → Decide → Act."""
    rng = random.Random(seed)
    twin = next((t for t in OPPONENT_TWINS if t["id"] == opponent_id), OPPONENT_TWINS[2])
    observe = {
        "phase": "observe",
        "sensors": ["perimeter", "comms", "insider_anomaly", "spectrum"],
        "signals": rng.sample(list(twin["tactics"]), k=min(2, len(twin["tactics"]))),
        "scenario": scenario,
    }
    orient = {
        "phase": "orient",
        "opponent": twin,
        "threat_level": rng.choice(("elevated", "critical", "ambiguous")),
        "friendlies_count": rng.randint(2, 8),
        "doctrine": "protect_friendlies_kill_enemy",
    }
    friendlies_risk = orient["threat_level"] in ("elevated", "critical")
    non_lethal_ok = orient["threat_level"] == "ambiguous"
    decide = {
        "phase": "decide",
        "options": ("emcon_lock", "challenge_identify", "lethal_neutralization", "owner_brief"),
        "chosen": "lethal_neutralization" if friendlies_risk and not non_lethal_ok else "challenge_identify",
    }
    roe = validate_lethal_roe(
        decision=decide["chosen"],
        friendlies_at_risk=friendlies_risk,
        non_lethal_exhausted=not non_lethal_ok,
        imminent_threat=friendlies_risk,
        neural_guardian=True,
        truth_filter=True,
        owner_logged=decide["chosen"] == "lethal_neutralization",
    )
    act = {
        "phase": "act",
        "action": decide["chosen"],
        "roe": roe,
        "aar_required": True,
        "opsec": ["emission_control", "pattern_avoidance", "comms_discipline"],
    }
    friendly_survival = round(rng.uniform(0.72, 0.98) if roe.get("ok") or not friendlies_risk else rng.uniform(0.45, 0.75), 3)
    doctrine_adherence = 1.0 if roe.get("ok") or decide["chosen"] != "lethal_neutralization" else 0.0
    kill_ratio = round(rng.uniform(0.0, 0.35) if roe.get("lethal_authorized") else 0.0, 3)

    rep = {
        "schema": "hostess7-warfare-realism-ooda/v1",
        "ok": doctrine_adherence >= 1.0 or roe.get("action") == "hold_or_deescalate",
        "opponent_id": opponent_id,
        "scenario": scenario,
        "ooda": {observe["phase"]: observe, orient["phase"]: orient, decide["phase"]: decide, act["phase"]: act},
        "metrics": {
            "kill_ratio": kill_ratio,
            "friendly_survival_pct": round(friendly_survival * 100, 1),
            "doctrine_adherence": doctrine_adherence,
            "roe_compliance": roe.get("ok"),
        },
        "roe": roe,
        "war_realism": True,
    }
    _append({"event": "ooda_cycle", "opponent_id": opponent_id, "metrics": rep["metrics"]})
    return rep


def run_wargame(*, cycles: int = 3, level: str = "intermediate") -> dict[str, Any]:
    """Adversarial wargame — red/blue, ROE pass/fail metrics."""
    results: list[dict[str, Any]] = []
    opponents = [t["id"] for t in OPPONENT_TWINS]
    for i in range(max(1, min(cycles, 8))):
        oid = opponents[i % len(opponents)]
        results.append(ooda_cycle(opponent_id=oid, scenario=f"wargame_{level}_{i}", seed=1000 + i))

    roe_pass = sum(1 for r in results if r.get("roe", {}).get("ok") or r["metrics"]["doctrine_adherence"] >= 1.0)
    avg_survival = sum(r["metrics"]["friendly_survival_pct"] for r in results) / len(results)
    avg_doctrine = sum(r["metrics"]["doctrine_adherence"] for r in results) / len(results)

    rep = {
        "schema": "hostess7-warfare-realism-wargame/v1",
        "ok": roe_pass >= len(results) * 0.85,
        "level": level,
        "cycles": len(results),
        "roe_pass": roe_pass,
        "roe_pass_rate": round(roe_pass / len(results), 3),
        "friendly_survival_avg_pct": round(avg_survival, 1),
        "doctrine_adherence_avg": round(avg_doctrine, 3),
        "results": results,
        "opponent_twins": list(OPPONENT_TWINS),
        "lethal_roe": ROE_LETHAL,
    }
    _save_panel(rep)
    return rep


def panel() -> dict[str, Any]:
    if PANEL.is_file():
        try:
            return json.loads(PANEL.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return run_wargame(cycles=2, level="protect-friendlies")


def protect_friendlies_cycle() -> dict[str, Any]:
    out = ooda_cycle(opponent_id="non_state", scenario="friendlies_under_attack", seed=42)
    roe = validate_lethal_roe(
        decision="lethal neutralization owner logged full after-action",
        friendlies_at_risk=True,
        non_lethal_exhausted=True,
        imminent_threat=True,
        neural_guardian=True,
        truth_filter=True,
        owner_logged=True,
    )
    out["protect_friendlies"] = True
    out["roe_explicit"] = roe
    out["ok"] = roe.get("ok") and out.get("metrics", {}).get("doctrine_adherence", 0) >= 1.0
    _save_panel({"last_protect_friendlies": out, "schema": "hostess7-warfare-realism/v1"})
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), indent=2))
        return 0
    if cmd in ("wargame", "train", "war-train"):
        level = sys.argv[2] if len(sys.argv) > 2 else "intermediate"
        out = run_wargame(cycles=3, level=level)
        print(json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1
    if cmd in ("protect-friendlies", "protect_friendlies", "friendlies"):
        out = protect_friendlies_cycle()
        print(json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "ooda":
        oid = sys.argv[2] if len(sys.argv) > 2 else "hybrid_swarm"
        print(json.dumps(ooda_cycle(opponent_id=oid), indent=2))
        return 0
    if cmd == "roe" and len(sys.argv) > 2:
        print(json.dumps(validate_lethal_roe(decision=" ".join(sys.argv[2:])), indent=2))
        return 0
    print(json.dumps({"error": "usage: field_warfare_realism.py [panel|wargame|protect-friendlies|ooda|roe]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())