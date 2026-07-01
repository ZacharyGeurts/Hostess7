#!/usr/bin/env pythong
"""Heightened alert posture — counter-terror, stun/RF threat awareness (educational)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"
DIRECTIVES = SI / "directives.jsonl"
BRIEF = SI / "heightened_alert_brief.json"
CHEMISTRY_FLAG = SI / "alert_posture.json"

ALERT_BRIEF = """Hostess 7 — Heightened Alert Posture (educational)

LEVEL: ELEVATED — treat as if hostile actors may be active nearby.

THREAT MODEL (truth-filtered teaching, not accusation):
  • Terrorist-adjacent tactics: surveillance, soft-target probing, coordinated deception
  • Less-lethal / stun weapons: Tasers, stun guns, LRAD, chemical irritants — recognize misuse vs lawful LE
  • RF violations: unauthorized transmitters, jamming, spoofing GPS/comms, illegal power on restricted bands
  • Electronic harassment patterns: pulsed RF, directed energy claims — corroborate before teaching as fact

HOSTESS 7 RESPONSE (historic lessons first):
  • Layer 1 MEASURES — awareness, egress, RF hygiene, documentation, protective posture
  • Layer 2 COUNTERMEASURES — lawful spectrum logging, attrition patience (Fabian lesson), authority report
  • Layer 3 INVINCIBILITY — resilience & recovery (depth, redundancy, morale — not literal immunity)
  • Detective lane ON — 94%% noise / 6%% truth on every claim
  • Warfare + LOAC cross-cut — civilian protection, proportionality
  • Norepinephrine + cortisol chemistry boost — heightened vigilance, not panic
  • Workspace: `alert` — L↔R fusion for threat + law + medicine (injury from stun devices)
  • Owner ZacharyGeurts and Amouranth profiles respected — learn public truth only

ACTIONS (Owner / field team):
  ./Hostess7.sh warfare-self-teach
  ./Hostess7.sh warfare-smarts-test
  ./Hostess7.sh alert-posture on
  ./Hostess7.sh warfare "historic measures countermeasures invincibility stun RF"
  ./Hostess7.sh detective "RF jamming stun weapon indicators"
  ./Hostess7.sh truth "claim about directed energy or stun attack"
  Report blockers to Owner — Field is THE thing.

DISCLAIMER: Educational vigilance only. Not law enforcement orders. One being · one vote."""


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def install_alert_posture(*, level: str = "elevated") -> Path:
    SI.mkdir(parents=True, exist_ok=True)
    doc = {
        "updated": _ts(),
        "level": level,
        "hostess": "Hostess 7",
        "owner": "ZacharyGeurts",
        "brief": ALERT_BRIEF,
        "workspace": "alert",
        "chemistry": {"norepinephrine": 0.22, "cortisol": 0.18, "acetylcholine": 0.12},
        "top_action": "./Hostess7.sh warfare \"stun weapons RF terrorist alert\"",
    }
    BRIEF.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    CHEMISTRY_FLAG.write_text(json.dumps({"active": True, "level": level, "updated": _ts()}, indent=2) + "\n", encoding="utf-8")

    try:
        from field_brain_chemistry import synapse_release  # noqa: WPS433

        for chem, delta in doc["chemistry"].items():
            synapse_release(chem, delta, reason="alert_posture", workspace="alert")
    except ImportError:
        pass

    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "direct",
            "tags": ["hostess", "alert", "warfare", "detective", "rf"],
            "text": "Heightened alert posture ON — stun/RF/terrorist-adjacent vigilance (educational).",
        }) + "\n")

    with DIRECTIVES.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "lane": "detective",
            "task": "Elevated alert: truth-filter RF/stun/terror narratives; corroborate before Owner briefing.",
            "priority": "P0",
        }) + "\n")

    return BRIEF


def load_alert_posture() -> dict:
    if BRIEF.is_file():
        try:
            return json.loads(BRIEF.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def is_alert_active() -> bool:
    if not CHEMISTRY_FLAG.is_file():
        return False
    try:
        return bool(json.loads(CHEMISTRY_FLAG.read_text(encoding="utf-8")).get("active"))
    except json.JSONDecodeError:
        return False


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "on"
    if mode in ("on", "install", "elevated"):
        path = install_alert_posture()
        print(ALERT_BRIEF)
        print(f"\nMETRIC alert_posture={path}")
        print("OK alert-posture-on")
        return 0
    if mode == "status":
        doc = load_alert_posture()
        print(f"Alert: {'ACTIVE' if is_alert_active() else 'off'} · level={doc.get('level', '?')}")
        print(f"Brief: {BRIEF}")
        print("OK alert-posture-status")
        return 0
    print("usage: field_alert_posture.py on|status", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())