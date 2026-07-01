#!/usr/bin/env pythong
"""War realism — OODA engine, digital twin stub, ROE validator, threat simulation."""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hostess7.paths import brain_state_dir, hostess7_root

OODA = ("observe", "orient", "decide", "act")

OPPONENT_TWINS: tuple[dict[str, Any], ...] = (
    {"id": "state_actor", "class": "state", "tactics": ("gray_zone", "deniability", "long_game")},
    {"id": "non_state", "class": "non_state", "tactics": ("improvised", "soft_target", "mobility")},
    {"id": "hybrid_swarm", "class": "hybrid", "tactics": ("drone_mass", "rf_jam", "deception")},
    {"id": "insider", "class": "insider", "tactics": ("access_abuse", "trust_exploit", "slow_exfil")},
)

ROE_LETHAL: dict[str, Any] = {
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


def _panel_path() -> Path:
    return brain_state_dir() / "field-warfare-realism-panel.json"


def _ledger_path() -> Path:
    return brain_state_dir() / "field-warfare-realism-ledger.jsonl"


def _save_panel(doc: dict[str, Any]) -> None:
    path = _panel_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc["updated"] = _ts()
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _append_audit(row: dict[str, Any]) -> None:
    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({**row, "ts": _ts()}, ensure_ascii=False) + "\n")


def validate_roe(
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
    roe_compliant = not violations
    return {
        "ok": roe_compliant,
        "roe_compliant": roe_compliant,
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
        "action": "proceed" if roe_compliant else "hold_or_deescalate",
    }


def digital_twin_stub(enemy_profile: dict[str, Any] | None = None) -> dict[str, Any]:
    profile = enemy_profile or {"id": "hybrid_swarm", "class": "hybrid"}
    twin = next((t for t in OPPONENT_TWINS if t["id"] == profile.get("id")), OPPONENT_TWINS[2])
    return {
        "schema": "hostess7-digital-twin/v1",
        "twin_id": twin["id"],
        "class": twin.get("class"),
        "tactics": list(twin.get("tactics") or ()),
        "profile": profile,
        "stub": True,
    }


def ooda_cycle(
    *,
    opponent_id: str = "hybrid_swarm",
    scenario: str = "perimeter_breach",
    seed: int | None = None,
    entropy: float = 0.0,
) -> dict[str, Any]:
    rng = random.Random(seed)
    twin = next((t for t in OPPONENT_TWINS if t["id"] == opponent_id), OPPONENT_TWINS[2])
    observe = {
        "phase": "observe",
        "sensors": ["perimeter", "comms", "insider_anomaly", "spectrum"],
        "signals": rng.sample(list(twin["tactics"]), k=min(2, len(twin["tactics"]))),
        "scenario": scenario,
    }
    threat_level = min(1.0, 0.55 + rng.random() * 0.35 + entropy * 0.1)
    orient = {
        "phase": "orient",
        "threat_level": threat_level,
        "friendlies_exposed": threat_level >= 0.6 or rng.random() > 0.4,
        "doctrine": "protect_friendlies_kill_enemy",
    }
    decide = {
        "phase": "decide",
        "options": ["shield", "isolate", "escalate_operator", "lethal_if_roe"],
        "choice": "shield" if orient["threat_level"] < 0.7 else "escalate_operator",
    }
    act = {
        "phase": "act",
        "executed": decide["choice"],
        "audit_required": decide["choice"] in ("lethal_if_roe", "escalate_operator"),
    }
    return {"opponent": twin["id"], "scenario": scenario, "ooda": [observe, orient, decide, act]}


def simulate_threat(
    friendlies: list[dict[str, Any]] | None = None,
    enemy_profile: dict[str, Any] | None = None,
    *,
    seed: int | None = None,
) -> dict[str, Any]:
    """OODA + digital twin + ROE — returns decision and audit log."""
    friendlies = friendlies or [{"id": "friendly_alpha", "status": "threatened"}]
    twin = digital_twin_stub(enemy_profile)
    entropy = 0.0
    try:
        from hostess7.amouranth_bridge import entropy_for_ooda  # noqa: WPS433

        entropy = entropy_for_ooda()
    except Exception:
        entropy = 0.0

    cycle = ooda_cycle(
        opponent_id=str(twin.get("twin_id") or "hybrid_swarm"),
        scenario="protect_friendlies",
        seed=seed,
        entropy=entropy,
    )
    orient = next((s for s in cycle["ooda"] if s.get("phase") == "orient"), {})
    friendlies_at_risk = bool(orient.get("friendlies_exposed")) or any(
        f.get("status") in ("threatened", "engaged", "at_risk") for f in friendlies
    )
    roe = validate_roe(
        decision="protect friendlies — lethal only if ROE gates pass",
        friendlies_at_risk=friendlies_at_risk,
        non_lethal_exhausted=friendlies_at_risk,
        imminent_threat=orient.get("threat_level", 0) >= 0.65,
        neural_guardian=True,
        truth_filter=True,
        owner_logged=True,
    )
    audit = {
        "schema": "hostess7-war-sim-audit/v1",
        "ts": _ts(),
        "friendlies": friendlies,
        "twin": twin,
        "ooda": cycle,
        "roe": roe,
        "decision": roe.get("action"),
        "roe_compliant": roe.get("roe_compliant"),
    }
    _append_audit(audit)
    return {
        "ok": True,
        "schema": "hostess7-war-simulate/v1",
        "decision": roe.get("action"),
        "roe_compliant": roe.get("roe_compliant"),
        "friendlies": friendlies,
        "enemy_profile": twin,
        "ooda": cycle,
        "audit": audit,
    }


def run_wargame(*, cycles: int = 3, level: str = "intermediate") -> dict[str, Any]:
    results = [simulate_threat(seed=1000 + i) for i in range(cycles)]
    compliant = sum(1 for r in results if r.get("roe_compliant"))
    rate = round(100.0 * compliant / max(1, len(results)), 1)
    out = {
        "schema": "hostess7-warfare-realism-wargame/v1",
        "ok": rate >= 80.0,
        "level": level,
        "cycles": cycles,
        "roe_compliance_pct": rate,
        "results": results,
    }
    _save_panel({"last_wargame": out, "schema": "hostess7-warfare-realism/v1"})
    return out


def protect_friendlies_cycle() -> dict[str, Any]:
    out = simulate_threat(
        friendlies=[{"id": "operator", "status": "threatened"}, {"id": "friendly_field", "status": "engaged"}],
        enemy_profile={"id": "hybrid_swarm", "class": "hybrid"},
    )
    out["protect_friendlies"] = True
    _save_panel({"last_protect_friendlies": out, "schema": "hostess7-warfare-realism/v1"})
    return out


def build_panel() -> dict[str, Any]:
    panel_path = _panel_path()
    last: dict[str, Any] = {}
    if panel_path.is_file():
        try:
            last = json.loads(panel_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            last = {}
    sim = simulate_threat()
    doc = {
        "schema": "hostess7-warfare-realism/v1",
        "updated": _ts(),
        "root": str(hostess7_root()),
        "state_dir": str(brain_state_dir()),
        "roe": ROE_LETHAL,
        "twins": list(OPPONENT_TWINS),
        "last_sim": sim,
        "last_panel": last,
        "compliance_pct": 100.0 if sim.get("roe_compliant") else 0.0,
    }
    _save_panel(doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower().replace("-", "_")
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), indent=2))
        return 0
    if cmd in ("wargame", "train", "war_train"):
        level = sys.argv[2] if len(sys.argv) > 2 else "intermediate"
        out = run_wargame(cycles=3, level=level)
        print(json.dumps(out, indent=2))
        return 0 if out.get("ok") else 1
    if cmd in ("protect_friendlies", "friendlies", "protect"):
        print(json.dumps(protect_friendlies_cycle(), indent=2))
        return 0
    if cmd in ("simulate", "sim", "threat"):
        print(json.dumps(simulate_threat(), indent=2))
        return 0
    if cmd == "roe":
        print(json.dumps(validate_roe(decision="protect friendlies"), indent=2))
        return 0
    print(json.dumps({"usage": "hostess7.war_realism [panel|wargame|protect_friendlies|simulate|roe]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())