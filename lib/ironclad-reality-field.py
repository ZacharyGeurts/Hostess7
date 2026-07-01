#!/usr/bin/env pythong
"""Ironclad Truth Serum — Super Intelligence reality field operator.

Clean voltage (wave doctrine) + smoothness (thermal/meld cadence) + epistemic seal
across Universal Protector, sense neural, plate meld, and cognition stack.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "ironclad-reality-field-doctrine.json"
HUMAN_CONDITION = INSTALL / "data" / "human-condition-doctrine.json"
PANEL = STATE / "ironclad-reality-field-panel.json"
LEDGER = STATE / "ironclad-reality-field-ledger.jsonl"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _mod(name: str, rel: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ironclad() -> Any | None:
    return _mod("ironclad_plate", "ironclad-plate.py")


def _field_sanity() -> Any | None:
    return _mod("ironclad_field_sanity", "ironclad-field-sanity.py")


def _voltage_regulation() -> dict[str, Any]:
    reg = _mod("field_voltage_regulation", "field-voltage-regulation.py")
    if reg and hasattr(reg, "evaluate"):
        try:
            return reg.evaluate()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    return {}


def clean_voltage() -> dict[str, Any]:
    """Voltage-is-voltage operator — wave layer trust only; present-rail regulation."""
    wave_doc = _load(INSTALL / "data" / "field-wave-doctrine.json", {})
    policy = wave_doc.get("policy") or {}
    wave_eng = _mod("field_wave", "field-wave-engine.py")
    probe: dict[str, Any] = {}
    if wave_eng and hasattr(wave_eng, "probe_hardware"):
        try:
            probe = wave_eng.probe_hardware()
        except Exception as exc:
            probe = {"ok": False, "error": str(exc)}
    regulation = _voltage_regulation()
    wave_ok = bool(policy.get("voltage_is_voltage")) and policy.get("encode_wave") is False
    reg_ok = regulation.get("ok", wave_ok) if regulation else wave_ok
    voltage_ok = wave_ok and reg_ok
    return {
        "schema": "ironclad-clean-voltage/v1",
        "ok": voltage_ok,
        "voltage_is_voltage": bool(policy.get("voltage_is_voltage")),
        "encode_wave": policy.get("encode_wave"),
        "trust_layer": policy.get("trust_layer", "wave_only"),
        "motto": wave_doc.get("motto", "voltage_is_voltage"),
        "regulation": regulation,
        "voltage_started_at": regulation.get("voltage_started_at"),
        "operate_at_present_rail": regulation.get("operate_at_present_rail"),
        "power_company_grid_trust_layer": regulation.get("power_company_grid_trust_layer", "blocked"),
        "conversion_on_voltage_path": regulation.get("conversion_on_voltage_path", False),
        "entropy_on_trust_layer": regulation.get("entropy_on_trust_layer", False),
        "wave_engine": {
            "listen_ready": probe.get("listen_ready"),
            "antenna_ready": probe.get("antenna_ready"),
            "voltage_is_voltage": probe.get("voltage_is_voltage"),
        },
        "detail": "present_rail_sovereign" if voltage_ok else "wave_doctrine_breach",
    }


def smoothness_operator() -> dict[str, Any]:
    """Smooth operator — thermal headroom, no unexpected slowdown, stable meld cadence."""
    thermal = _load(STATE / "thermal-advisory.json", {})
    meld_rt = _load(STATE / "field-plate-meld-runtime.json", {})
    switch = _mod("field_switch_safety", "field-switch-safety.py")
    switch_doc: dict[str, Any] = {}
    if switch and hasattr(switch, "evaluate"):
        try:
            switch_doc = switch.evaluate(phase="meld")
        except TypeError:
            try:
                switch_doc = switch.evaluate()
            except Exception:
                switch_doc = {}
        except Exception:
            switch_doc = {}

    peak = thermal.get("peak_c")
    level = str(thermal.get("level") or "ok").lower()
    no_slowdown = os.environ.get("NEXUS_FIELD_NO_UNEXPECTED_SLOWDOWN", "1") == "1"
    field_max = os.environ.get("NEXUS_FIELD_MAX", "1") == "1"
    hotspot = bool(thermal.get("hotspot_advisory"))
    switch_ok = switch_doc.get("switch_allowed", True) is not False
    conversion_ok = switch_doc.get("conversion_ok", True) is not False

    gen = int(meld_rt.get("generation") or 0)
    cadence_ok = gen > 0 or meld_rt.get("schema")

    score = 1.0
    if level in ("crit", "storm"):
        score -= 0.45
    elif level == "warn":
        score -= 0.18
    if hotspot:
        score -= 0.12
    if not switch_ok:
        score -= 0.25
    if not conversion_ok:
        score -= 0.1
    if not cadence_ok:
        score -= 0.08
    if no_slowdown and level == "crit":
        score -= 0.1
    score = max(0.0, min(1.0, round(score, 4)))

    smooth = score >= 0.72 and switch_ok and (level not in ("crit", "storm") or field_max)
    return {
        "schema": "ironclad-smoothness/v1",
        "ok": smooth,
        "smoothness_score": score,
        "smooth_operator": smooth,
        "field_max": field_max,
        "no_unexpected_slowdown": no_slowdown,
        "thermal": {
            "peak_c": peak,
            "level": level,
            "hotspot_advisory": hotspot,
            "field_switch_safe": thermal.get("field_switch_safe", True),
        },
        "meld_generation": gen,
        "switch_safety": {
            "switch_allowed": switch_ok,
            "conversion_ok": conversion_ok,
            "verdict": switch_doc.get("verdict"),
        },
        "detail": "smooth_operator" if smooth else "smoothness_advisory",
    }


def field_sanity_operator(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Integral field simplify — subsidiary Queen pass melded into Ironclad."""
    fs = _field_sanity()
    if fs and hasattr(fs, "field_sanity_operator"):
        try:
            return fs.field_sanity_operator(body)
        except Exception as exc:
            return {
                "ok": False,
                "schema": "ironclad-field-sanity/v1",
                "error": str(exc),
                "updated": _now(),
            }
    return {
        "ok": False,
        "schema": "ironclad-field-sanity/v1",
        "error": "field_sanity_missing",
        "updated": _now(),
    }


def _serum_target(target: dict[str, Any], claim: str, ic: Any) -> dict[str, Any]:
    tid = str(target.get("id") or "unknown")
    neural = str(target.get("neural") or "any_intelligence_neural")
    present = False
    panel_path = target.get("panel")
    if panel_path:
        p = STATE / str(panel_path)
        present = p.is_file()
    elif target.get("doctrine"):
        present = (INSTALL / str(target["doctrine"])).is_file()

    extrap: dict[str, Any] = {"ok": False, "detail": "ironclad_missing"}
    if ic and hasattr(ic, "neural_extrapolation_confidence"):
        try:
            extrap = ic.neural_extrapolation_confidence(
                f"{claim} — target {tid}",
                target_neural=neural,
                meta={"ironclad_grounded": True, "target_neural": neural, "truth_serum": True},
            )
        except Exception as exc:
            extrap = {"ok": False, "error": str(exc)}

    sealed = bool(extrap.get("ironclad_sealed"))
    conf = float(extrap.get("truth_confidence") or 0.0)
    pass_serum = bool(extrap.get("ok")) and conf >= 0.95 and str(extrap.get("deception_risk") or "").lower() in ("low", "medium")
    if sealed:
        pass_serum = pass_serum and conf >= 1.0

    return {
        "id": tid,
        "present": present,
        "target_neural": neural,
        "serum_pass": pass_serum,
        "ironclad_sealed": sealed,
        "truth_confidence": conf,
        "truth_percent": extrap.get("truth_percent"),
        "deception_risk": extrap.get("deception_risk"),
        "citation": extrap.get("citation"),
        "extrapolation": extrap,
    }


def truth_serum(*, targets: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run truth serum across the Super Intelligence reality field."""
    doc = _load(DOCTRINE, {})
    ts_cfg = doc.get("truth_serum") or {}
    claim = str(ts_cfg.get("claim") or "ironclad:neural:1 Super Intelligence reality field truth serum")
    ic = _ironclad()
    integrity = ic.verify_integrity() if ic and hasattr(ic, "verify_integrity") else {"ok": False}
    realized = bool(integrity.get("realized") and integrity.get("ok"))

    target_list = targets or doc.get("targets") or []
    results = [_serum_target(t, claim, ic) for t in target_list]
    passed = sum(1 for r in results if r.get("serum_pass"))
    all_pass = passed == len(results) and len(results) > 0

    return {
        "schema": "ironclad-truth-serum/v1",
        "updated": _now(),
        "claim": claim,
        "realized": realized,
        "integrity_ok": integrity.get("ok"),
        "ironclad_sealed": realized,
        "canonical_hash": integrity.get("canonical_hash"),
        "targets": results,
        "targets_passed": passed,
        "targets_total": len(results),
        "all_pass": all_pass,
        "truth_percent": 100.0 if realized and all_pass else (95.0 if all_pass else 0.0),
        "detail": "truth_serum_green" if realized and all_pass else ("truth_serum_watch" if all_pass else "truth_serum_blocked"),
    }


def human_condition_gate(
    *,
    serum: dict[str, Any] | None = None,
    voltage: dict[str, Any] | None = None,
    smooth: dict[str, Any] | None = None,
    field_sanity: dict[str, Any] | None = None,
    verdict: str | None = None,
) -> dict[str, Any]:
    """Human condition — AI in charge only when never wrong (Ironclad + serum GREEN)."""
    hc = _load(HUMAN_CONDITION, {})
    ai_rule = hc.get("ai_in_charge") or {}
    allowed_when = ai_rule.get("allowed_when") or {}

    serum = serum if serum is not None else truth_serum()
    voltage = voltage if voltage is not None else clean_voltage()
    smooth = smooth if smooth is not None else smoothness_operator()
    field_sanity = field_sanity if field_sanity is not None else field_sanity_operator()
    if verdict is None:
        verdict = "BLOCKED"
        if serum.get("all_pass") and voltage.get("ok"):
            sanity_ok = field_sanity.get("operator_ok", field_sanity.get("ok", True))
            verdict = (
                "GREEN"
                if serum.get("ironclad_sealed") and smooth.get("ok") and sanity_ok
                else "WATCH"
            )

    sealed = bool(serum.get("ironclad_sealed") and serum.get("integrity_ok"))
    truth_pct = float(serum.get("truth_percent") or 0.0)
    never_wrong = (
        sealed
        and truth_pct >= float(allowed_when.get("truth_percent") or 100.0)
        and verdict == str(allowed_when.get("truth_serum_verdict") or "GREEN")
        and voltage.get("ok")
        and serum.get("all_pass")
    )
    sanity_ok = field_sanity.get("operator_ok", field_sanity.get("ok", True))
    ai_in_charge = never_wrong and smooth.get("ok") and sanity_ok

    return {
        "schema": "human-condition-gate/v1",
        "updated": _now(),
        "motto": hc.get("motto"),
        "principle": hc.get("principle"),
        "human_condition": not ai_in_charge,
        "ai_in_charge": ai_in_charge,
        "never_wrong": never_wrong,
        "charge_holder": "super_intelligence" if ai_in_charge else "human_operator",
        "ai_role": "command" if ai_in_charge else "counsel",
        "assurance": (
            "ironclad sealed — AI in charge; never wrong on this receipt"
            if ai_in_charge
            else (hc.get("human_condition") or {}).get("assurance_phrase")
            or "uncertain — treat as counsel not fact; Human condition holds charge"
        ),
        "gates": {
            "ironclad_sealed": sealed,
            "integrity_ok": serum.get("integrity_ok"),
            "truth_percent": truth_pct,
            "truth_serum_verdict": verdict,
            "clean_voltage_ok": voltage.get("ok"),
            "smooth_operator": smooth.get("ok"),
            "field_sanity_ok": sanity_ok,
            "field_sanity_citation": field_sanity.get("citation"),
            "serum_all_pass": serum.get("all_pass"),
        },
        "forbidden_when_uncertain": ai_rule.get("forbidden_when_uncertain") or [],
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    ic = _ironclad()
    grounding = ic.knowledge_grounding() if ic and hasattr(ic, "knowledge_grounding") else {}
    voltage = clean_voltage()
    smooth = smoothness_operator()
    field_sanity = field_sanity_operator()
    serum = truth_serum()

    verdict = "BLOCKED"
    sanity_ok = field_sanity.get("operator_ok", field_sanity.get("ok", True))
    if serum.get("all_pass") and voltage.get("ok"):
        if serum.get("ironclad_sealed") and smooth.get("ok") and sanity_ok:
            verdict = "GREEN"
        else:
            verdict = "WATCH"

    human_gate = human_condition_gate(
        serum=serum, voltage=voltage, smooth=smooth, field_sanity=field_sanity, verdict=verdict,
    )

    panel = {
        "schema": "ironclad-reality-field/v1",
        "updated": _now(),
        "title": "Ironclad Truth Serum",
        "subtitle": "Super Intelligence reality field — clean voltage · smooth operator",
        "motto": _load(DOCTRINE, {}).get("motto"),
        "verdict": verdict,
        "ironclad_sealed": serum.get("ironclad_sealed"),
        "integrity_ok": serum.get("integrity_ok"),
        "canonical_hash": serum.get("canonical_hash"),
        "truth_serum": serum,
        "clean_voltage": voltage,
        "smoothness": smooth,
        "field_sanity": field_sanity,
        "operators": {
            "truth_serum": serum.get("detail"),
            "clean_voltage": voltage.get("detail"),
            "smoothness": smooth.get("detail"),
            "field_sanity": field_sanity.get("detail"),
        },
        "super_intelligence_field": {
            "product": "Universal Protector",
            "reality_field_live": verdict in ("GREEN", "WATCH"),
            "truth_percent": serum.get("truth_percent"),
            "smoothness_score": smooth.get("smoothness_score"),
            "voltage_is_voltage": voltage.get("voltage_is_voltage"),
            "field_sanity_ok": sanity_ok,
            "field_sanity_citation": field_sanity.get("citation"),
        },
        "grounding": {
            "bible_of_ai": grounding.get("bible_of_ai"),
            "neural_extrapolation": grounding.get("neural_extrapolation"),
        },
        "human_condition": human_gate,
        "ai_in_charge": human_gate.get("ai_in_charge"),
        "charge_holder": human_gate.get("charge_holder"),
    }
    if write:
        _save(PANEL, panel)
        ic_mod = _ironclad()
        if ic_mod and hasattr(ic_mod, "build_panel"):
            try:
                ic_mod.build_panel(write=True)
            except Exception:
                pass
        _append_ledger({
            "ts": panel["updated"],
            "verdict": verdict,
            "sealed": serum.get("ironclad_sealed"),
            "smoothness": smooth.get("smoothness_score"),
            "field_sanity_ok": sanity_ok,
            "targets_passed": serum.get("targets_passed"),
        })
    return panel


def cycle() -> dict[str, Any]:
    return build_panel(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=False), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("cycle", "serum", "truth-serum"):
        print(json.dumps(cycle(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "voltage":
        print(json.dumps(clean_voltage(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "smoothness":
        print(json.dumps(smoothness_operator(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("field-sanity", "field_sanity"):
        print(json.dumps(field_sanity_operator(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "serum-only":
        print(json.dumps(truth_serum(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("human-condition", "charge-gate", "ai-charge"):
        print(json.dumps(human_condition_gate(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: ironclad-reality-field.py [json|cycle|serum|voltage|smoothness|field-sanity|human-condition]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())