#!/usr/bin/env pythong
"""Military security layer — perimeter, OPSEC, fusion scoring, audit."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT
from field_warfare_corpus import WARFARE_CORPUS_VERSION, ensure_corpus, search_warfare
from field_warfare_training_sessions import load_training_state, run_session

SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
SECURITY_JSON = SI / "military_security.json"

PHYSICAL_CHECKLIST = (
    "stand_off_distance",
    "access_control_layers",
    "vehicle_barriers",
    "drone_detection",
    "emergency_egress",
)
OPSEC_CHECKLIST = (
    "emcon_rf_discipline",
    "pattern_of_life_variation",
    "social_media_hygiene",
    "burner_compartmentalization",
    "need_to_know",
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_checklist(items: tuple[str, ...], hits: list[dict[str, Any]]) -> float:
    blob = " ".join(str(h.get("body", "")) for h in hits).lower()
    found = sum(1 for it in items if it.replace("_", " ") in blob or it.split("_")[0] in blob)
    return round(found / max(1, len(items)), 2)


def compute_security_posture() -> dict[str, Any]:
    ensure_corpus()
    physical_hits = search_warfare("physical perimeter access control drone detection", limit=4)
    opsec_hits = search_warfare("opsec emission control pattern burner", limit=4)
    fusion_hits = search_warfare("cyber kinetic insider threat roe escalation", limit=4)
    training = load_training_state()

    physical = _score_checklist(PHYSICAL_CHECKLIST, physical_hits)
    opsec = _score_checklist(OPSEC_CHECKLIST, opsec_hits)
    fusion = min(1.0, len(fusion_hits) / 3.0)
    readiness = float(training.get("readiness_score", 0)) / 100.0
    morality = float(training.get("morality_compliance", 1.0))
    military_security_score = round((physical * 0.25 + opsec * 0.25 + fusion * 0.2 + readiness * 0.2 + morality * 0.1) * 100, 1)

    return {
        "schema": "hostess7-military-security/v1",
        "updated": _ts(),
        "corpus_version": WARFARE_CORPUS_VERSION,
        "physical_readiness": round(physical * 100, 1),
        "opsec_score": round(opsec * 100, 1),
        "fusion_health": round(fusion * 100, 1),
        "training_readiness": training.get("readiness_score", 0),
        "morality_compliance": morality,
        "military_security_score": military_security_score,
        "physical_checklist": list(PHYSICAL_CHECKLIST),
        "opsec_checklist": list(OPSEC_CHECKLIST),
        "domains_loaded": [h.get("id") for h in physical_hits + opsec_hits + fusion_hits],
    }


def save_security_posture(doc: dict[str, Any]) -> Path:
    SI.mkdir(parents=True, exist_ok=True)
    SECURITY_JSON.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return SECURITY_JSON


def audit_security() -> dict[str, Any]:
    doc = compute_security_posture()
    gaps: list[str] = []
    if doc["physical_readiness"] < 60:
        gaps.append("physical_perimeter")
    if doc["opsec_score"] < 60:
        gaps.append("opsec_full")
    if doc["fusion_health"] < 60:
        gaps.append("cyber_kinetic_fusion")
    if doc["training_readiness"] < 50:
        gaps.append("warfare_training_sessions")
    doc["gaps"] = gaps
    doc["audit_ok"] = len(gaps) == 0
    save_security_posture(doc)
    return doc


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if mode in ("status", "json"):
        doc = compute_security_posture()
        save_security_posture(doc)
        print(json.dumps(doc, indent=2))
        print(f"METRIC military_security_score={doc.get('military_security_score', 0)}")
        print(f"METRIC physical_readiness={doc.get('physical_readiness', 0)}")
        print(f"METRIC opsec_score={doc.get('opsec_score', 0)}")
        print("OK military-security-status")
        return 0
    if mode == "audit":
        doc = audit_security()
        print(json.dumps(doc, indent=2))
        print(f"METRIC military_security_score={doc.get('military_security_score', 0)}")
        print("OK military-security-audit" if doc.get("audit_ok") else "REVIEW military-security-audit")
        return 0 if doc.get("audit_ok") else 1
    if mode == "train":
        run_session("intermediate")
        doc = audit_security()
        print(json.dumps(doc, indent=2))
        print("OK military-security-train")
        return 0
    if mode == "posture":
        try:
            from field_alert_posture import install_alert_posture, load_alert_posture  # noqa: WPS433

            install_alert_posture(level="elevated")
            alert = load_alert_posture()
        except ImportError:
            alert = {}
        sec = audit_security()
        out = {"alert": alert, "military_security": sec}
        print(json.dumps(out, indent=2))
        print(f"METRIC military_security_score={sec.get('military_security_score', 0)}")
        print("OK military-security-posture")
        return 0
    print("usage: field_military_security.py [status|audit|train|posture]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())