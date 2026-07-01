#!/usr/bin/env pythong
"""Queen → Final_Eye eyeball — assistive vision tenant for Hostess 7."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from queen_final_eye import final_eye_env, final_eye_root, import_final_eye

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
FINAL_EYE = final_eye_root()
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", SG / "Hostess7"))
NEXUS_LIB = QUEEN.parent / "lib"
FINAL_EYE_PORT = int(os.environ.get("ZOCR_PORT", os.environ.get("FINAL_EYE_PORT", "9479")))
COMFORT_PATH = QUEEN / "data" / "queen-eye-comfort-doctrine.json"


def _load_queen_comfort() -> dict[str, Any]:
    if COMFORT_PATH.is_file():
        try:
            return json.loads(COMFORT_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {"schema": "queen-eye-comfort/v1", "rule": "stereo for faces; monocular for media"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _zocr_env() -> dict[str, str]:
    return final_eye_env(queen=QUEEN)


def _import_zocr():
    import_final_eye()
    return _zocr_env()


def _nexus_posture() -> dict[str, Any]:
    """NewLatest defensive posture — corroborates eyeball, does not own vision."""
    out: dict[str, Any] = {"available": False, "role": "egress_defense"}
    strike = NEXUS_LIB / "trust-strike-engine.py"
    if strike.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(strike), "json"],
                capture_output=True,
                text=True,
                timeout=12,
                env=_zocr_env(),
            )
            if proc.returncode == 0:
                out = {"available": True, **json.loads(proc.stdout)}
        except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
            pass
    panel = NEXUS_LIB / "field-queen-browser.py"
    if panel.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(panel), "json"],
                capture_output=True,
                text=True,
                timeout=10,
                env=_zocr_env(),
            )
            doc = json.loads(proc.stdout or "{}")
            out["queen_gates"] = {
                "verdict": doc.get("queen_verdict"),
                "all_held": (doc.get("gates") or {}).get("all_held"),
            }
        except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
            pass
    return out


def eyeball_status() -> dict[str, Any]:
    """Final_Eye stack for Hostess 7 — assistive posture, offense/defense mesh."""
    _import_zocr()
    from zocr_contract import contract_status
    from zocr_eye import eye_status, final_eyeball_status
    from zocr_kill import kill_status
    from zocr_offense import offense_doctrine, offense_status
    from zocr_pattern import pattern_status
    from zocr_product import product_info
    from zocr_trust import trust_network_status, verify_trust_mesh

    from zocr_entity_eyeball import twin_eyeball_status
    from zocr_eye_operations import eye_operations_status
    from zocr_stereo import comfort_doctrine, rig_status

    mesh = verify_trust_mesh()
    final = final_eyeball_status()
    twins = twin_eyeball_status()
    sovereign = final.get("sovereign_time") or {}
    redundancy = final.get("redundancy") or {}
    out: dict[str, Any] = {
        "schema": "queen-eyeball-hostess7/v1",
        "updated": _now(),
        "posture": "assistive",
        "rule": "One tenant in Hostess 7 — bounded usage, weaponized offense on ingress, never overflow",
        "always": {"sovereign_time": True, "redundancy": True, "twins": True, "forward": True},
        "twins": twins,
        "living": twins.get("living"),
        "truth": twins.get("truth"),
        "product": product_info(),
        "final_eye_root": str(FINAL_EYE),
        "final_eye_port": FINAL_EYE_PORT,
        "zocr_root": str(FINAL_EYE),
        "hostess_root": str(HOSTESS) if HOSTESS.is_dir() else None,
        "contract": contract_status(),
        "final_eyeball": final,
        "eye": eye_status(),
        "sovereign_time": sovereign,
        "sovereign_verdict": sovereign.get("verdict"),
        "sealed_mono_ns": sovereign.get("sealed_mono_ns"),
        "redundancy": redundancy,
        "woven_paths": redundancy.get("woven_paths"),
        "offense": offense_status(),
        "offense_doctrine": offense_doctrine(),
        "pattern": pattern_status(),
        "kill": kill_status(),
        "trust": trust_network_status(),
        "trust_mesh": mesh,
        "mesh_ok": mesh.get("ok"),
        "nexus": _nexus_posture(),
        "eye_comfort": _load_queen_comfort(),
        "rig": rig_status(),
        "comfort_doctrine": comfort_doctrine(),
        "eye_operations": eye_operations_status(),
    }
    try:
        from zocr_eye_stoard import stoard_status
        out["eye_stoard"] = stoard_status()
    except ImportError:
        pass
    try:
        from zocr_virtual_eye import virtual_eye_status
        virtual = virtual_eye_status()
        out["virtual_eyes"] = virtual
        out["virtual_rule"] = virtual.get("rule")
    except ImportError:
        pass
    return out


def eyeball_arm(
    mode: str = "dishes",
    *,
    voice: str | None = None,
    start_stream: bool = False,
    context: str | None = None,
) -> dict[str, Any]:
    """Arm twin entity eyeballs — Living makes live; Truth guards forward."""
    _import_zocr()
    from zocr_entity_eyeball import make_living_live
    from zocr_stereo import configure_rig, preset_for_context

    ctx_preset = preset_for_context(context)
    if ctx_preset:
        configure_rig(preset=ctx_preset, source="queen_comfort")
    elif mode == "person_present":
        configure_rig(preset="stereo_human", source="queen_person_present")

    out = make_living_live(
        mode,
        voice=voice,
        start_stream=start_stream,
        vigilance=mode in ("war", "patrol", "night_watch", "preserve"),
    )
    out["schema"] = "queen-eyeball-arm/v1"
    out["eye_comfort"] = _load_queen_comfort()
    out["comfort_context"] = context or (mode if mode == "person_present" else None)
    if ctx_preset or mode == "person_present":
        from zocr_stereo import rig_status
        out["rig"] = rig_status()
    out["posture"] = "assistive"
    out["hostess_root"] = str(HOSTESS)
    return out


def eyeball_verify(*, bench: bool = True) -> dict[str, Any]:
    """Seal + trust mesh + offense stack — Queen/Hostess corroboration."""
    _import_zocr()
    from zocr_security import seal_codebase, verify_code_seal
    from zocr_trust import verify_trust_mesh

    seal = seal_codebase()
    verify = verify_code_seal()
    mesh = verify_trust_mesh()
    status = eyeball_status()

    bench_out: dict[str, Any] | None = None
    if bench:
        watch = FINAL_EYE / "zocr_watch.py"
        if watch.is_file():
            proc = subprocess.run(
                [sys.executable, str(watch), "bench-low-end"],
                capture_output=True,
                text=True,
                timeout=180,
                env=_zocr_env(),
            )
            try:
                bench_out = json.loads(proc.stdout)
            except json.JSONDecodeError:
                bench_out = {"ok": False, "tail": (proc.stdout or "")[-1500:]}

    sovereign = status.get("sovereign_time") or {}
    redundancy = status.get("redundancy") or {}
    sovereign_ok = sovereign.get("ok", sovereign.get("verdict") == "USER_OK")
    redundancy_ok = redundancy.get("ok", redundancy.get("woven_paths", 0) >= 1)

    ok = bool(verify.get("ok")) and bool(mesh.get("ok")) and sovereign_ok and redundancy_ok
    if bench_out is not None:
        ok = ok and bench_out.get("summary", {}).get("ok", bench_out.get("ok", False))

    return {
        "ok": ok,
        "schema": "queen-eyeball-verify/v1",
        "posture": "assistive",
        "always": {"sovereign_time": True, "redundancy": True},
        "seal": seal,
        "verify": verify,
        "trust_mesh": mesh,
        "sovereign_time": sovereign,
        "sovereign_ok": sovereign_ok,
        "redundancy": redundancy,
        "redundancy_ok": redundancy_ok,
        "bench": bench_out,
        "status": status,
    }


def eyeball_weaponize(*, mode: str = "war") -> dict[str, Any]:
    """Weaponize eyeball — war prescription + offense mesh + Hostess corroboration."""
    armed = eyeball_arm(mode, start_stream=False)
    verify = eyeball_verify(bench=False)
    status = eyeball_status()
    vision_path = next(
        (p for p in status.get("trust_mesh", {}).get("paths", []) if p.get("id") == "vision_assist"),
        {},
    )
    return {
        "ok": armed.get("ok") and verify.get("ok"),
        "schema": "queen-eyeball-weaponize/v1",
        "mode": mode,
        "armed": armed,
        "verify": verify,
        "vision_assist_woven": vision_path.get("woven") or vision_path.get("ok"),
        "offense_rule": status.get("offense_doctrine", {}).get("rule"),
        "posture": "assistive",
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json"):
        return {"ok": True, **eyeball_status()}
    if action in ("arm", "final-mode", "final_mode"):
        return eyeball_arm(
            str(body.get("mode") or "dishes"),
            voice=body.get("voice"),
            context=body.get("context"),
            start_stream=bool(body.get("start_stream")),
        )
    if action in ("verify", "verify-eyeball"):
        return eyeball_verify(bench=body.get("bench", True) is not False)
    if action in ("weaponize", "weapon", "war"):
        return eyeball_weaponize(mode=str(body.get("mode") or "war"))
    if action in ("live", "make-live", "living-live"):
        _import_zocr()
        from zocr_entity_eyeball import make_living_live
        return make_living_live(
            str(body.get("mode") or "dishes"),
            voice=body.get("voice"),
            start_stream=bool(body.get("start_stream")),
            vigilance=bool(body.get("vigilance")),
        )
    if action in ("forward", "truth-forward", "truth_forward"):
        _import_zocr()
        from zocr_entity_eyeball import truth_forward
        return truth_forward(
            speak=body.get("speak", True) is not False,
            scan=body.get("scan", True) is not False,
            fire_weapons=body.get("fire_weapons", True) is not False,
        )
    if action in ("fire-weapon", "fire_weapon", "weapon"):
        _import_zocr()
        from zocr_entity_eyeball import fire_entity_weapon
        threat = body.get("threat")
        weapon = body.get("weapon") or body.get("id")
        if weapon is None and threat:
            weapon = "auto"
        return fire_entity_weapon(
            str(weapon or "forward_truth"),
            threat=threat,
        )
    if action in ("teach", "teach-doctrine", "teach_doctrine"):
        _import_zocr()
        from zocr_entity_eyeball import eye_teach
        lesson = body.get("lesson")
        out = eye_teach(lesson=lesson)
        if (lesson or "").strip().lower() in ("comfort", "stereo"):
            out["queen_comfort"] = _load_queen_comfort()
        return out
    if action in ("comfort", "eye-comfort", "eye_comfort"):
        _import_zocr()
        from zocr_stereo import comfort_doctrine, rig_status
        qc = _load_queen_comfort()
        return {
            "ok": True,
            "schema": "queen-eye-comfort/v1",
            "queen": qc,
            "rig": rig_status(),
            "teach": comfort_doctrine(),
            "speak": qc.get("speak"),
        }
    if action in ("operations", "eye-operations", "eye_operations"):
        _import_zocr()
        from zocr_eye_operations import eye_operations_status, load_operations_doctrine
        return {
            "ok": True,
            "operations": eye_operations_status(),
            "doctrine": load_operations_doctrine(),
        }
    if action in ("authority", "weapon-authority", "weapon_authority"):
        _import_zocr()
        from zocr_entity_eyeball import eye_weapon_authority
        return eye_weapon_authority()
    if action in ("targets", "eye-targets"):
        _import_zocr()
        from zocr_entity_eyeball import eye_targets_know
        return eye_targets_know()
    if action in ("understand", "understand-target", "understand_target"):
        _import_zocr()
        from zocr_entity_eyeball import eye_understand_target
        threat = str(body.get("threat") or body.get("target") or "").strip()
        if not threat:
            return {"ok": False, "error": "missing_threat"}
        return eye_understand_target(threat)
    if action in ("twins", "twin", "entity"):
        _import_zocr()
        from zocr_entity_eyeball import twin_eyeball_status
        return {"ok": True, **twin_eyeball_status()}
    if action in ("virtual", "virtual_status", "virtual_eyes"):
        _import_zocr()
        from zocr_virtual_eye import virtual_eye_status
        return {"ok": True, **virtual_eye_status()}

    if action in ("virtual_spawn", "spawn_virtual", "spawn_eye", "point_eye"):
        _import_zocr()
        from zocr_virtual_eye import spawn_virtual_eye
        return spawn_virtual_eye(
            mechanism=str(body.get("mechanism") or "wifi_rf"),
            point=body.get("point"),
            x_m=body.get("x_m"),
            y_m=body.get("y_m"),
            z_m=body.get("z_m"),
            bearing_deg=body.get("bearing_deg"),
            elevation_deg=body.get("elevation_deg"),
            distance_m=body.get("distance_m"),
            profile=body.get("profile"),
            label=body.get("label"),
            truth_bound=body.get("truth_bound", True) is not False,
            pair_ear_id=body.get("pair_ear_id"),
        )

    if action in ("virtual_observe", "observe_virtual", "see_point"):
        _import_zocr()
        from zocr_virtual_eye import observe_virtual_eye
        eid = str(body.get("eye_id") or body.get("id") or "")
        if not eid:
            return {"ok": False, "error": "missing_eye_id"}
        return observe_virtual_eye(eid)

    if action in ("virtual_remove", "remove_virtual"):
        _import_zocr()
        from zocr_virtual_eye import remove_virtual_eye
        eid = str(body.get("eye_id") or body.get("id") or "")
        if not eid:
            return {"ok": False, "error": "missing_eye_id"}
        return remove_virtual_eye(eid)

    if action in ("virtual_grid", "spawn_eye_grid"):
        _import_zocr()
        from zocr_virtual_eye import spawn_eye_grid
        return spawn_eye_grid(
            mechanism=str(body.get("mechanism") or "wifi_rf"),
            count=int(body.get("count") or 6),
            radius_m=float(body.get("radius_m") or 3.0),
            height_m=float(body.get("height_m") or 2.0),
        )

    if action in ("pair_anchor", "kinetic_wifi_anchor", "virtual_anchor"):
        _import_zocr()
        from zocr_virtual_eye import pair_kinetic_wifi_anchor
        return pair_kinetic_wifi_anchor(
            x_m=float(body.get("x_m") or 0),
            y_m=float(body.get("y_m") or 0),
            z_m=float(body.get("z_m") or 1.2),
            bearing_deg=float(body.get("bearing_deg") or 0),
        )

    if action in ("neural", "neural_assist", "neural_analyze", "neural_wired"):
        _import_zocr()
        from zocr_neural_assist import analyze_wired, encourage, neural_assist_status
        if body.get("analyze") or action == "neural_analyze":
            return analyze_wired(context=body.get("context"), image_path=body.get("image_path"))
        return {"ok": True, **neural_assist_status()}

    if action in ("encourage", "neural_encourage"):
        _import_zocr()
        from zocr_neural_assist import encourage
        return encourage(label=str(body.get("label") or "clear_field"), delta=float(body.get("delta") or 0.02), source=str(body.get("source") or "hostess7"))

    if action in ("wire", "invincible_wire", "fused_analyze"):
        qlib = Path(__file__).resolve().parent
        proc = subprocess.run(
            [sys.executable, str(qlib / "queen-sense-neural.py"), "dispatch"],
            input=json.dumps(body if body.get("action") else {**body, "action": "analyze"}),
            capture_output=True, text=True, timeout=120, env=_zocr_env(),
        )
        try:
            return json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return {"ok": False, "error": "wire_failed"}

    if action in ("field_manual", "field-manual", "manual", "textbook"):
        sense = str(body.get("sense") or "vision")
        if sense == "audio":
            ear = _LIB / "queen-earball.py"
            if ear.is_file():
                proc = subprocess.run(
                    [sys.executable, str(ear), "dispatch"],
                    input=json.dumps({"action": "field_manual", "sense": "audio"}),
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env=_zocr_env(),
                )
                try:
                    return json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    return {"ok": False, "error": "ear_field_manual_failed"}
        manual = FINAL_EYE / "data" / "field-manual-vision.json"
        if manual.is_file():
            doc = json.loads(manual.read_text(encoding="utf-8"))
            return {"ok": True, **doc, "sense": "vision"}
        return {"ok": False, "error": "field_manual_missing"}
    if action in ("bench", "bench-low-end"):
        watch = FINAL_EYE / "zocr_watch.py"
        if not watch.is_file():
            return {"ok": False, "error": "zocr_watch_missing"}
        proc = subprocess.run(
            [sys.executable, str(watch), "bench-low-end"],
            capture_output=True,
            text=True,
            timeout=180,
            env=_zocr_env(),
        )
        try:
            doc = json.loads(proc.stdout)
        except json.JSONDecodeError:
            doc = {"ok": False, "tail": (proc.stdout or "")[-2000:]}
        doc["returncode"] = proc.returncode
        return doc
    return {
        "ok": False,
        "error": "unknown_action",
        "actions": [
            "status", "arm", "verify", "weaponize", "bench", "live", "forward",
            "fire-weapon", "twins", "teach", "authority", "targets", "understand",
            "comfort", "eye-comfort", "virtual", "virtual_spawn", "virtual_observe",
            "virtual_remove", "virtual_grid", "pair_anchor",
        ],
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(eyeball_status(), ensure_ascii=False))
        return 0
    if cmd == "arm":
        mode = sys.argv[2] if len(sys.argv) > 2 else "dishes"
        print(json.dumps(eyeball_arm(mode), ensure_ascii=False))
        return 0
    if cmd == "verify":
        print(json.dumps(eyeball_verify(), ensure_ascii=False))
        return 0
    if cmd == "weaponize":
        mode = sys.argv[2] if len(sys.argv) > 2 else "war"
        print(json.dumps(eyeball_weaponize(mode=mode), ensure_ascii=False))
        return 0
    if cmd == "bench":
        print(json.dumps(dispatch({"action": "bench"}), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: queen-eyeball.py [json|arm MODE|verify|weaponize [MODE]|bench|dispatch]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())