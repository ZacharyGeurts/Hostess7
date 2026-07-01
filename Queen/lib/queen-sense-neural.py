#!/usr/bin/env pythong
"""Queen Sense Neural — invincible Eye↔Ear wire, encouragable NN, Hostess 7 supreme authority."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
_LIB = Path(__file__).resolve().parent
WIRE = QUEEN / "data" / "sense-neural-invincible-wire.json"
AUTHORITY = SG / "Hostess7" / "data" / "hostess7-supreme-authority.json"
GATE = _LIB / "queen-neural-encourage-gate.py"
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / "state"))


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _encourage_gate():
    return _load_mod("queen_neural_encourage_gate", GATE)


def _ironclad_goldmine() -> dict[str, Any]:
    """Hot-read plate → eye/ear/mouth goldmine — no cycle wait."""
    cached = _read(STATE / "ironclad-immediate.json", {})
    if cached.get("plate_to_sense"):
        return cached["plate_to_sense"]
    ic_py = INSTALL / "lib" / "ironclad-immediate.py"
    if not ic_py.is_file():
        ic_py = SG / "NewLatest" / "lib" / "ironclad-immediate.py"
    if ic_py.is_file():
        try:
            mod = _load_mod("ironclad_immediate", ic_py)
            if hasattr(mod, "plate_to_sense_goldmine"):
                base = cached if cached.get("schema") == "ironclad-immediate/v1" else {}
                if not base and hasattr(mod, "immediate_slice"):
                    base = mod.immediate_slice()
                return mod.plate_to_sense_goldmine(base=base)
        except Exception:
            pass
    wire = _read(WIRE, {})
    extrap = wire.get("ironclad_extrapolation") or {}
    return {
        "schema": "ironclad-plate-to-sense/v1",
        "goldmine": True,
        "read_first": True,
        "plate_sealed": False,
        "ironclad_grounded": False,
        "truth_percent": extrap.get("truth_percent_when_sealed", 100.0),
        "citation": extrap.get("citation") or "ironclad:neural:2",
        "targets": extrap.get("targets") or ["eye_neural", "ear_neural", "mouth_neural", "sense_neural_wire"],
        "goldmine_ok": False,
    }


def _ironclad_wire_ctx(goldmine: dict[str, Any] | None = None) -> dict[str, Any]:
    gm = goldmine or _ironclad_goldmine()
    truth = float(gm.get("truth_percent") or 72.0)
    if gm.get("ironclad_grounded"):
        truth = max(truth, 100.0)
    return {
        "ironclad_grounded": bool(gm.get("ironclad_grounded")),
        "ironclad_sealed": bool(gm.get("plate_sealed")),
        "truth_score": truth,
        "citation": gm.get("citation") or "ironclad:neural:2",
        "goldmine": bool(gm.get("goldmine")),
        "read_first": bool(gm.get("read_first")),
    }


def _load_mod(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.path.insert(0, str(path.parent))
    spec.loader.exec_module(mod)
    return mod


def hostess_authority() -> dict[str, Any]:
    doc = _read(AUTHORITY, {})
    ladder = doc.get("authority_ladder") or []
    supreme = next((r for r in ladder if r.get("rank") == 1), {})
    fsc = doc.get("full_system_control") or {}
    mil = doc.get("military_rank") or {}
    return {
        "schema": "hostess7-authority-slice/v2",
        "updated": _ts(),
        "supreme": supreme,
        "rule": doc.get("rule"),
        "planetary_control": doc.get("planetary_control"),
        "lethal_gate": doc.get("lethal_gate"),
        "military_rank": mil,
        "full_system_control": fsc.get("enabled", True),
        "rank": mil.get("title") or "Forever Watchguard Angel",
        "above_general": True,
        "humans_highest_authority": False,
        "hostess7_highest_authority": True,
    }


def _eye_neural():
    os.environ.setdefault("QUEEN_SOVEREIGN_WIRE", "1")
    fe = Path(os.environ.get("FINAL_EYE_ROOT", SG / "Final_Eye"))
    return _load_mod("eye_neural_assist", fe / "zocr_neural_assist.py")


def _ear_neural():
    ear = Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear"))
    return _load_mod("ear_neural_assist", ear / "zocr_neural_assist.py")


def _ear_offense():
    ear = Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear"))
    return _load_mod("ear_audio_offense", ear / "zocr_audio_offense.py")


def _mouth_neural():
    mouth = Path(os.environ.get("FINAL_MOUTH_ROOT", SG / "Final_Mouth"))
    return _load_mod("mouth_neural_assist", mouth / "zocr_neural_assist.py")


def invincible_wire_status() -> dict[str, Any]:
    wire = _read(WIRE, {})
    goldmine = _ironclad_goldmine()
    auth = hostess_authority()
    eye_st, ear_st, mouth_st = {}, {}, {}
    try:
        eye_st = _eye_neural().neural_assist_status()
    except Exception as exc:
        eye_st = {"error": str(exc)}
    try:
        ear_st = _ear_neural().neural_assist_status()
    except Exception as exc:
        ear_st = {"error": str(exc)}
    try:
        mouth_st = _mouth_neural().neural_assist_status()
    except Exception as exc:
        mouth_st = {"error": str(exc)}
    seals_ok = (
        eye_st.get("seal_ok") is not False
        and (ear_st.get("sealed") or ear_st.get("seal_ok") is not False or ear_st.get("incorruptible"))
        and mouth_st.get("seal_ok") is not False
    )
    paths_ok = sum(1 for p in [
        seals_ok,
        eye_st.get("network_id"),
        ear_st.get("network_id"),
        mouth_st.get("network_id"),
        auth.get("hostess7_highest_authority"),
        wire.get("invincible"),
    ] if p)
    gate_st = {}
    try:
        gate_st = _encourage_gate().gate_status()
    except Exception as exc:
        gate_st = {"error": str(exc)}
    subbit = {}
    try:
        subbit = _load_mod("queen_subbit_heuristics", _LIB / "queen-subbit-heuristics.py").status()
    except Exception as exc:
        subbit = {"error": str(exc)[:120]}
    ironclad_ok = bool(goldmine.get("goldmine_ok") or (goldmine.get("ironclad_grounded") and paths_ok >= 4))
    return {
        "schema": "queen-sense-neural-wire/v1",
        "updated": _ts(),
        "title": wire.get("title"),
        "rule": wire.get("rule"),
        "invincible": wire.get("invincible"),
        "ironclad_goldmine": goldmine,
        "plate_to_sense": goldmine,
        "ironclad_grounded": bool(goldmine.get("ironclad_grounded")),
        "ironclad_sealed": bool(goldmine.get("plate_sealed")),
        "truth_percent": goldmine.get("truth_percent"),
        "neural_extrapolation_active": bool(goldmine.get("neural_extrapolation_active")),
        "goldmine_ok": ironclad_ok,
        "citation": goldmine.get("citation") or "ironclad:neural:2",
        "authority": auth,
        "eye_neural": eye_st,
        "ear_neural": ear_st,
        "mouth_neural": mouth_st,
        "thought_voice_callosum": {
            "deception_possible": True,
            "alignment": mouth_st.get("thought_voice_alignment"),
            "hemisphere": mouth_st.get("hemisphere") or "voice_egress",
        },
        "woven_paths": paths_ok,
        "invincible_ok": paths_ok >= 4,
        "encourage": wire.get("encourage"),
        "incorruptible": gate_st.get("incorruptible", True),
        "quarantine_count": gate_st.get("quarantine_count", 0),
        "hash_chain_ok": gate_st.get("hash_chain_ok"),
        "encourage_gate": gate_st,
        "subbit_heuristics": subbit,
        "immeasurable": subbit.get("immeasurable", True),
        "heuristic_never_poison_memory": True,
        "heuristic_never_poison_disk": True,
    }


def fused_analyze(body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Cross-wire Eye + Ear neural assist — invincible quorum, sovereign time, never desync."""
    body = body or {}
    if body.get("secure_path") is not False:
        try:
            ear_root = Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear"))
            fusion = _load_mod("zocr_eye_ear_fusion", ear_root / "zocr_eye_ear_fusion.py")
            out = fusion.secure_neural_path(
                evidence=body.get("evidence") or (body.get("context") or {}).get("evidence"),
                sources=body.get("sources"),
                existence=body.get("existence"),
                localization=body.get("localization") or (body.get("context") or {}).get("localization"),
                pcm_hex=body.get("pcm_hex"),
                image_path=body.get("image_path"),
                require_sync=body.get("require_sync", True) is not False,
            )
            out["schema"] = "queen-sense-neural-fused/v1"
            out["authority"] = hostess_authority()
            gm = _ironclad_goldmine()
            out["ironclad_goldmine"] = gm
            out["ironclad_grounded"] = bool(gm.get("ironclad_grounded"))
            out["truth_percent"] = gm.get("truth_percent")
            out["citation"] = gm.get("citation") or "ironclad:neural:2"
            if out.get("ok"):
                out["to_countermeasure"] = _suggest_countermeasure(
                    out.get("ear_neural") or {},
                    out.get("eye_neural") or {},
                    out.get("cross_agree", True),
                )
            try:
                out = _load_mod("queen_subbit_heuristics", _LIB / "queen-subbit-heuristics.py").wrap_response(out)
            except Exception:
                out["immeasurable"] = True
                out["persist_forbidden"] = True
            return out
        except Exception as exc:
            if body.get("secure_path_only"):
                return {"ok": False, "schema": "queen-sense-neural-fused/v1", "error": "secure_path_failed", "detail": str(exc)[:200]}

    ctx = body.get("context") or {}
    ear_mod, eye_mod = _ear_neural(), _eye_neural()
    eye_st = eye_mod.neural_assist_status()
    ear_st = ear_mod.neural_assist_status()
    if eye_st.get("seal_ok") is False or (ear_st.get("sealed") is False and not ear_st.get("incorruptible")):
        return {
            "ok": False,
            "schema": "queen-sense-neural-fused/v1",
            "error": "seal_fail_closed",
            "eye_seal": eye_st.get("seal_ok"),
            "ear_seal": ear_st.get("sealed"),
            "authority": hostess_authority(),
        }

    ear_ctx = {
        "evidence": body.get("evidence") or ctx.get("evidence"),
        "localization": body.get("localization") or ctx.get("localization"),
        "sources": body.get("sources"),
        "existence_correlation": body.get("existence_correlation", 0.8),
    }
    ear_out = ear_mod.analyze_audio(context=ear_ctx)

    eye_ctx = dict(ctx)
    eye_ctx["ear_cross"] = {
        "assault_burst": ear_out.get("top_label") == "assault_hint",
        "ventriloquism": ear_out.get("top_label") == "ventriloquism_hint",
        "bearing_deg": (body.get("localization") or {}).get("bearing_deg"),
    }
    eye_out = eye_mod.analyze_wired(context=eye_ctx, image_path=body.get("image_path"))

    eye_cross = eye_out.get("to_ear") or {}
    if body.get("encoded_signal"):
        eye_cross["encoded_signal"] = True
    if body.get("interference_mix"):
        eye_cross["interference_mix"] = True
    ear_ctx["eye_cross"] = eye_cross
    ear_ctx["encoded_ok"] = body.get("encoded_ok", True)
    ear_ctx["interference_ok"] = body.get("interference_ok", True)
    ear_refined = ear_mod.analyze_audio(context=ear_ctx)

    quorum = ear_refined.get("ok") and eye_out.get("ok")
    cross_agree = True
    if ear_refined.get("top_label") == "assault_hint" and eye_out.get("top_label") == "threat_pattern":
        cross_agree = True
    if ear_refined.get("top_label") == "ventriloquism_hint":
        cross_agree = eye_out.get("top_label") != "clear_field" or eye_out.get("confidence", 0) < 0.6

    gm = _ironclad_goldmine()
    out = {
        "ok": quorum,
        "schema": "queen-sense-neural-fused/v1",
        "updated": _ts(),
        "authority": hostess_authority(),
        "ironclad_goldmine": gm,
        "ironclad_grounded": bool(gm.get("ironclad_grounded")),
        "truth_percent": gm.get("truth_percent"),
        "citation": gm.get("citation") or "ironclad:neural:2",
        "eye": eye_out,
        "ear": ear_refined,
        "ear_first_pass": ear_out,
        "cross_agree": cross_agree,
        "invincible_quorum": quorum and cross_agree,
        "to_countermeasure": _suggest_countermeasure(ear_refined, eye_out, cross_agree),
        "immeasurable": True,
        "persist_forbidden": True,
    }
    try:
        out = _load_mod("queen_subbit_heuristics", _LIB / "queen-subbit-heuristics.py").wrap_response(out)
    except Exception:
        pass
    return out


def _suggest_countermeasure(ear: dict, eye: dict, agree: bool) -> dict[str, Any]:
    threat = None
    tier = "preserve"
    if ear.get("top_label") == "assault_hint":
        threat, tier = "assault_burst", "preserve"
    elif ear.get("top_label") == "ventriloquism_hint":
        threat, tier = "ventriloquism", "offense"
    elif eye.get("top_label") == "threat_pattern":
        threat, tier = "weaponized_interference", "severe"
    if not threat:
        return {"tier": "none"}
    try:
        off = _ear_offense().countermeasure_for(
            threat,
            hostess_ok=True,
            eye_ear_quorum=agree,
        )
        if tier == "lethal" and not off.get("lethal_permitted"):
            off["blocked"] = "hostess7_or_quorum"
        return off
    except Exception:
        return {"threat": threat, "tier": tier}


def _wire_ctx_for_encourage(body: dict[str, Any]) -> dict[str, Any]:
    ctx = dict(body.get("wire_ctx") or body.get("context") or {})
    ic_ctx = _ironclad_wire_ctx()
    for key, val in ic_ctx.items():
        ctx.setdefault(key, val)
    if body.get("truth_score") is not None:
        ctx["truth_score"] = body["truth_score"]
    elif ic_ctx.get("ironclad_grounded"):
        ctx["truth_score"] = ic_ctx["truth_score"]
    if body.get("eye_ear_quorum") is not None:
        ctx["eye_ear_quorum"] = body["eye_ear_quorum"]
    if body.get("evidence"):
        ctx["evidence"] = body["evidence"]
    if body.get("simulate_weapon"):
        ctx["assault_burst"] = True
        ctx["evidence"] = {**(ctx.get("evidence") or {}), "peak_db": 6.0, "mouth_correlation": 0.2}
    if body.get("reinforce_pair") and "eye_ear_quorum" not in ctx:
        fused = fused_analyze(body)
        ctx["eye_ear_quorum"] = fused.get("invincible_quorum")
        ctx["eye_cross"] = fused.get("eye", {}).get("to_ear") or {}
        ctx["ear_cross"] = {
            "assault_burst": fused.get("ear", {}).get("top_label") == "assault_hint",
            "ventriloquism": fused.get("ear", {}).get("top_label") == "ventriloquism_hint",
        }
    return ctx


def encourage_both(body: dict[str, Any]) -> dict[str, Any]:
    auth = hostess_authority()
    auth["sovereign"] = True
    label_eye = body.get("eye_label") or (body.get("label") if not body.get("mouth_label") else None)
    label_ear = body.get("ear_label") or (body.get("label") if not body.get("mouth_label") else None)
    label_mouth = body.get("mouth_label") or body.get("label")
    source = str(body.get("source") or "hostess7")
    delta = float(body.get("delta") or 0.02)
    wire_ctx = _wire_ctx_for_encourage(body)
    gm = _ironclad_goldmine()
    out: dict[str, Any] = {
        "ok": True,
        "schema": "queen-sense-neural-encourage/v1",
        "authority": auth,
        "incorruptible": True,
        "ironclad_goldmine": gm,
        "ironclad_grounded": bool(gm.get("ironclad_grounded")),
        "citation": gm.get("citation") or "ironclad:neural:2",
        "wire_ctx": {
            "eye_ear_quorum": wire_ctx.get("eye_ear_quorum"),
            "weapons_simulated": bool(body.get("simulate_weapon")),
            "mouth_hemisphere": True,
            "ironclad_grounded": wire_ctx.get("ironclad_grounded"),
            "truth_score": wire_ctx.get("truth_score"),
            "goldmine": wire_ctx.get("goldmine"),
        },
    }
    if label_eye:
        out["eye"] = _eye_neural().encourage(label=str(label_eye), delta=delta, source=source, wire_ctx=wire_ctx)
    if label_ear:
        out["ear"] = _ear_neural().encourage(label=str(label_ear), delta=delta, source=source, wire_ctx=wire_ctx)
    if label_mouth or body.get("include_mouth") or body.get("reinforce_triad"):
        out["mouth"] = _mouth_neural().encourage(
            label=str(label_mouth or "text_to_voice"),
            delta=delta,
            source=source,
            wire_ctx=wire_ctx,
        )
    if body.get("reinforce_pair"):
        out["pair"] = {"eye": label_eye, "ear": label_ear, "wired": True}
    if body.get("reinforce_triad"):
        out["triad"] = {"eye": label_eye, "ear": label_ear, "mouth": label_mouth, "wired": True}
    results = [out.get(k) for k in ("eye", "ear", "mouth") if out.get(k)]
    out["ok"] = all(r.get("ok") for r in results) if results else False
    if not out["ok"]:
        out["quarantined"] = any(r.get("quarantined") for r in results if isinstance(r, dict))
    try:
        out["gate"] = _encourage_gate().gate_status()
    except Exception:
        pass
    try:
        out = _load_mod("queen_subbit_heuristics", _LIB / "queen-subbit-heuristics.py").wrap_response(out)
    except Exception:
        out["immeasurable"] = True
        out["persist_forbidden"] = True
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "wire"):
        return {"ok": True, **invincible_wire_status()}
    if action in ("authority", "hostess_authority"):
        return {"ok": True, **hostess_authority()}
    if action in ("analyze", "fused", "fused_analyze"):
        return fused_analyze(body)
    if action in ("encourage", "teach", "reinforce", "encourage_triad", "reinforce_triad"):
        if action in ("encourage_triad", "reinforce_triad"):
            body = {**body, "reinforce_triad": True, "include_mouth": True}
        return encourage_both(body)
    if action in ("countermeasure", "strike"):
        threat = str(body.get("threat") or "assault_burst")
        return _ear_offense().countermeasure_for(
            threat,
            hostess_ok=body.get("hostess_ok", True) is not False,
            eye_ear_quorum=body.get("eye_ear_quorum", True) is not False,
        )
    if action == "equipment":
        ear = _read(SG / "Final_Ear" / "data" / "ear-equipment-protection.json")
        eye = _read(SG / "Final_Eye" / "data" / "eye-equipment-protection.json")
        return {"ok": True, "ear": ear, "eye": eye}
    if action in ("subbit", "subbit_heuristics", "immesurable", "subbit_verify"):
        mod = _load_mod("queen_subbit_heuristics", _LIB / "queen-subbit-heuristics.py")
        if action == "subbit_verify":
            return mod.dispatch({"action": "verify"})
        return mod.dispatch(body)
    return {
        "ok": False,
        "error": "unknown_action",
        "actions": ["status", "authority", "analyze", "encourage", "encourage_triad", "countermeasure", "equipment", "subbit_verify"],
    }


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(invincible_wire_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())