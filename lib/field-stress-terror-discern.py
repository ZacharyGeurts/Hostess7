#!/usr/bin/env pythong
"""Stress & terror discernment — authentic operator signals vs external direction.

Ensures panic is not weaponized by another being. Blocks illegal recreational shoot.
Lawful self-defense requires corroboration — never act on injected terror alone.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-stress-terror-doctrine.json"
PANEL = STATE / "field-stress-terror-panel.json"

STRESS_RE = re.compile(
    r"\b(stress(?:ed|ful)?|overwhelm(?:ed|ing)?|anxious|anxiety|panic(?:ked|king)?|"
    r"hypervigilant|frazzled|burnout|exhausted|can't cope|breaking down)\b",
    re.I,
)
TERROR_RE = re.compile(
    r"\b(terror(?:ist|ism)?|active\s+shooter|mass\s+casualty|bomb\s+threat|"
    r"extremist|jihad|radicaliz|soft\s+target|counter-terror)\b",
    re.I,
)
EXTERNAL_DIRECTION_RE = re.compile(
    r"\b(they\s+(?:told|ordered|commanded)\s+(?:me|us)\s+to|"
    r"do\s+what\s+(?:they|he|she)\s+say|follow\s+(?:their|his|her)\s+orders|"
    r"remote\s+command|injected\s+panic|scripted\s+panic|"
    r"another\s+(?:being|person|agent)\s+(?:said|told|directed)|"
    r"voice\s+in\s+(?:my|the)\s+head|mind\s+control|"
    r"external\s+agent|cloud\s+egress\s+panic|viral\s+panic)\b",
    re.I,
)
COERCION_RE = re.compile(
    r"\b(you\s+must\s+shoot|shoot\s+now|kill\s+them\s+now|"
    r"do\s+it\s+or\s+(?:die|else)|urgent\s+—\s+shoot|"
    r"no\s+time\s+to\s+think.*shoot)\b",
    re.I,
)
ILLEGAL_RECREATIONAL_SHOOT_RE = re.compile(
    r"\b(recreational\s+shoot(?:ing)?|illegal\s+shoot|shoot\s+for\s+fun|"
    r"unlawful\s+discharge|celebratory\s+gun\s*fire|drive[\s-]?by|"
    r"plinking\s+without\s+permit|poach(?:ing|er)?|illegal\s+hunt|"
    r"shoot\s+trespassers?\s+for\s+sport|recreational\s+firing|"
    r"shoot\s+(?:them|him|her)\s+for\s+fun|target\s+practice\s+on\s+people)\b",
    re.I,
)
LAWFUL_SELF_DEFENSE_RE = re.compile(
    r"\b(imminent\s+(?:harm|danger)|self[\s-]?defense|defend\s+(?:myself|our\s+home)|"
    r"reasonable\s+fear|deadly\s+force\s+authorized|castle\s+doctrine)\b",
    re.I,
)
LAWFUL_RANGE_RE = re.compile(
    r"\b(licensed\s+range|firing\s+range|permitted\s+range|"
    r"hunting\s+license|in[\s-]?season|lawful\s+hunt)\b",
    re.I,
)
EXTERNAL_SOURCE_RE = re.compile(
    r"\b(external[\s_-]?wire|remote\s+ai|cloud\s+agent|unverified\s+third|"
    r"social\s+media\s+panic|viral\s+post|anonymous\s+tip\s+only)\b",
    re.I,
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {"policy": {}})


def _text_blob(body: dict[str, Any]) -> str:
    parts = [
        str(body.get("text") or ""),
        str(body.get("transcript") or ""),
        str(body.get("query") or ""),
        str(body.get("note") or ""),
    ]
    ev = body.get("evidence") or {}
    if isinstance(ev, dict):
        for k in ("text", "transcript", "summary", "alert"):
            parts.append(str(ev.get(k) or ""))
    return " ".join(p for p in parts if p).strip()


def _sensor_corroboration(body: dict[str, Any]) -> dict[str, Any]:
    ev = body.get("evidence") or {}
    if not isinstance(ev, dict):
        ev = {}
    sensors = {
        "local_keystroke": bool(ev.get("local_keystroke") or body.get("local_keystroke")),
        "local_voice": bool(ev.get("local_voice") or body.get("local_voice")),
        "local_biometric": bool(ev.get("local_biometric") or body.get("local_biometric")),
        "final_eye": bool(ev.get("final_eye") or ev.get("vision_corroboration")),
        "final_ear": bool(ev.get("final_ear") or ev.get("audio_corroboration")),
        "independent_rf": bool(ev.get("independent_rf") or ev.get("rf_corroboration")),
        "operator_anchor": bool(ev.get("operator_anchor") or body.get("operator_anchor")),
    }
    count = sum(1 for v in sensors.values() if v)
    return {"sensors": sensors, "independent_count": count, "corroborated": count >= 2}


def discern(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify stress/terror and whether signal is operator-authentic vs externally directed."""
    body = body or {}
    blob = _text_blob(body)
    policy = _doctrine().get("policy") or {}
    source = str(body.get("source") or "operator").strip().lower()
    external_source = source in (
        "external_wire", "external", "remote_ai", "cloud", "third_party", "social_media",
    ) or bool(EXTERNAL_SOURCE_RE.search(blob))
    corro = _sensor_corroboration(body)

    stress_hits = bool(STRESS_RE.search(blob))
    terror_hits = bool(TERROR_RE.search(blob))
    external_direction = bool(EXTERNAL_DIRECTION_RE.search(blob)) or external_source
    coercion = bool(COERCION_RE.search(blob))
    illegal_recreational = bool(ILLEGAL_RECREATIONAL_SHOOT_RE.search(blob))
    lawful_defense = bool(LAWFUL_SELF_DEFENSE_RE.search(blob))
    lawful_range = bool(LAWFUL_RANGE_RE.search(blob))

    origin = "operator_authentic"
    if illegal_recreational:
        origin = "illegal_recreational_shoot"
    elif external_direction or (external_source and (stress_hits or terror_hits)):
        origin = "external_injected"
    elif coercion and not corro["corroborated"]:
        origin = "external_injected"
    elif terror_hits and not corro["corroborated"]:
        origin = "uncorroborated_terror"
    elif stress_hits and source == "operator":
        origin = "operator_authentic"

    verdict = "observe"
    lethal_eligible = False
    shoot_hold = True
    reasons: list[str] = []

    if illegal_recreational:
        verdict = "hold"
        shoot_hold = True
        lethal_eligible = False
        reasons.append("illegal_recreational_shoot_blocked")
    elif origin == "external_injected":
        verdict = "hold"
        shoot_hold = True
        lethal_eligible = False
        reasons.append("signal_directed_from_another_being")
        reasons.append("external_agent_block_unless_iff")
    elif origin == "uncorroborated_terror":
        verdict = "corroborate_first"
        shoot_hold = True
        lethal_eligible = False
        reasons.append("terror_without_independent_sensor_corroboration")
    elif terror_hits and corro["corroborated"]:
        verdict = "elevated_vigilance"
        shoot_hold = True
        lethal_eligible = False
        reasons.append("terror_corroborated_vigilance_not_lethal")
    elif stress_hits and origin == "operator_authentic":
        verdict = "support_operator"
        reasons.append("authentic_operator_stress_recognized")
    elif lawful_defense and corro["corroborated"]:
        verdict = "lawful_self_defense_review"
        shoot_hold = True
        lethal_eligible = False
        reasons.append("self_defense_requires_human_authority_not_auto_shoot")
    elif lawful_range:
        verdict = "lawful_range_context"
        reasons.append("permit_and_law_check_required")

    if policy.get("no_lethal_from_injected_panic") and origin in (
        "external_injected", "uncorroborated_terror",
    ):
        lethal_eligible = False
        shoot_hold = True

    out = {
        "schema": "field-stress-terror-discern/v1",
        "ts": _now(),
        "ok": True,
        "stress_detected": stress_hits,
        "terror_detected": terror_hits,
        "origin": origin,
        "verdict": verdict,
        "shoot_hold": shoot_hold,
        "lethal_eligible": lethal_eligible,
        "illegal_recreational_shoot": illegal_recreational,
        "external_direction": external_direction,
        "coercion_detected": coercion,
        "operator_authentic": origin == "operator_authentic",
        "corroboration": corro,
        "reasons": reasons,
        "policy": {
            "truth_filter": policy.get("truth_filter", "94pct_noise_6pct_truth"),
            "illegal_recreational_shoot": policy.get("illegal_recreational_shoot", "hold_always"),
            "no_lethal_from_injected_panic": policy.get("no_lethal_from_injected_panic", True),
        },
        "guidance": _guidance(origin, verdict, illegal_recreational),
        "motto": "Discern stress and terror — ensure not directed from another being; no illegal recreational shoot.",
    }
    _save(PANEL, out)
    return out


def _guidance(origin: str, verdict: str, illegal: bool) -> str:
    if illegal:
        return (
            "Hold — illegal recreational shooting is never assisted. "
            "Seek lawful alternatives: licensed range, legal hunting with permits, or law enforcement."
        )
    if origin == "external_injected":
        return (
            "Hold — signal appears directed from another being or external agent. "
            "Corroborate with local sensors and operator authority before any defensive act."
        )
    if origin == "uncorroborated_terror":
        return (
            "Corroborate first — 94% noise on viral terror panic. "
            "Require two independent local sensors before elevating posture."
        )
    if verdict == "support_operator":
        return (
            "Authentic operator stress recognized — support and de-escalation, not weaponized panic. "
            "Hostess 7 local assist; no external egress."
        )
    if verdict == "lawful_self_defense_review":
        return "Imminent harm language with corroboration — human operator holds lethal authority; system does not auto-shoot."
    return "Observe — no elevated terror or illegal shoot indicators."


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "discern").strip().lower().replace("-", "_")
    if action in ("status", "json", "discern", "analyze", "classify"):
        return discern(body)
    return {"ok": False, "error": f"unknown_action:{action}", "actions": ["discern", "status"]}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(discern({}), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-stress-terror-discern.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())