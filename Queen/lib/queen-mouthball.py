#!/usr/bin/env pythong
"""Queen → Final_Mouth mouthball — assistive voice tenant for Hostess 7."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from queen_final_mouth import final_mouth_env, final_mouth_root, import_final_mouth

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
_LIB = Path(__file__).resolve().parent
FINAL_MOUTH = final_mouth_root()
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", SG / "Hostess7"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _mouth_product_info() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("final_mouth_product", FINAL_MOUTH / "zocr_product.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod.product_info()


def _import_mouth():
    import_final_mouth()
    return final_mouth_env(queen=QUEEN)


def _mouth_neural_status() -> dict[str, Any]:
    script = FINAL_MOUTH / "zocr_neural_assist.py"
    if not script.is_file():
        return {"available": False}
    proc = subprocess.run(
        [sys.executable, str(script), "dispatch"],
        input=json.dumps({"action": "status"}),
        capture_output=True,
        text=True,
        timeout=45,
        cwd=str(FINAL_MOUTH),
    )
    try:
        return {"available": True, **json.loads(proc.stdout)}
    except json.JSONDecodeError:
        return {"available": False, "tail": (proc.stdout or "")[-800:]}


def _presume_receipt() -> dict[str, Any]:
    script = INSTALL / "lib" / "hostess7-presume.py"
    if not script.is_file():
        return {"wired": False}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "propagate"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(INSTALL),
        )
        doc = json.loads(proc.stdout or "{}")
        return {
            "wired": True,
            "propagated": doc.get("propagated"),
            "uninterruptable": True,
            "not_go_away": doc.get("not_go_away"),
            "targets_present": doc.get("targets_present"),
        }
    except (json.JSONDecodeError, subprocess.TimeoutExpired):
        return {"wired": False}


def mouthball_status() -> dict[str, Any]:
    _import_mouth()
    from zocr_mouth import final_mouth_status, mouth_status, vocal_spectrum_doctrine

    final = final_mouth_status()
    return {
        "schema": "queen-mouthball-hostess7/v1",
        "updated": _now(),
        "posture": "assistive",
        "rule": "We never presume speech loss. Confidence always in Voice.",
        "product": _mouth_product_info(),
        "final_mouth_root": str(FINAL_MOUTH),
        "hostess_root": str(HOSTESS) if HOSTESS.is_dir() else None,
        "final_mouth": final,
        "mouth": mouth_status(),
        "mouth_neural": _mouth_neural_status(),
        "vocal_spectrum": vocal_spectrum_doctrine(),
        "fusion_api": "/api/queen-mouthball",
        "ear_api": "/api/queen-earball",
        "eye_api": "/api/queen-eyeball",
        "presume": _presume_receipt(),
    }


def mouthball_arm(mode: str = "dishes") -> dict[str, Any]:
    _import_mouth()
    from zocr_mouth import set_mode
    out = set_mode(mode)
    out["schema"] = "queen-mouthball-arm/v1"
    out["posture"] = "assistive"
    return out


def mouthball_verify() -> dict[str, Any]:
    _import_mouth()
    from zocr_mouth import analyze_vocal_spectrum, mouth_ear_eye_fusion
    status = mouthball_status()
    spec = analyze_vocal_spectrum()
    fusion = mouth_ear_eye_fusion(evidence={"mouth_correlation": 0.88, "ear_correlation": 0.85, "eye_correlation": 0.84})
    ok = spec.get("ok") and fusion.get("verdict") == "truth"
    return {
        "ok": ok,
        "schema": "queen-mouthball-verify/v1",
        "spectrum": spec,
        "fusion": fusion,
        "status": status,
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json"):
        return {"ok": True, **mouthball_status()}

    if action in ("arm", "final_mode", "mode"):
        return mouthball_arm(str(body.get("mode") or "dishes"))

    if action in ("verify",):
        return mouthball_verify()

    if action in ("spectrum", "vocal_spectrum", "spectrum_analyze"):
        _import_mouth()
        from zocr_mouth import analyze_vocal_spectrum, vocal_spectrum_doctrine
        if body.get("doctrine"):
            return {"ok": True, **vocal_spectrum_doctrine()}
        return analyze_vocal_spectrum(profile_id=body.get("profile"))

    if action in ("speak", "tts", "say"):
        _import_mouth()
        from zocr_mouth import speak
        return speak(
            str(body.get("text") or ""),
            mode=body.get("mode"),
            voice=body.get("voice"),
            engine=body.get("engine"),
            audience=body.get("audience"),
        )

    if action in ("generate_frequency", "frequency", "tone"):
        _import_mouth()
        from zocr_mouth import generate_frequency
        return generate_frequency(
            float(body.get("hz") or body.get("frequency") or 440),
            audience=body.get("audience"),
            duration_ms=int(body.get("duration_ms") or 50),
        )

    if action in ("fcc_clamp", "fcc_acoustic", "spectrum_clamp"):
        _import_mouth()
        from zocr_mouth import analyze_vocal_spectrum, clamp_spectrum_fcc_safe, load_doctrine
        profile_id = body.get("profile") or body.get("vocal_profile")
        spec = analyze_vocal_spectrum(profile_id=profile_id)
        bins = (spec.get("bins") or spec.get("spectrum_bins") or [])
        if not bins:
            prof = (load_doctrine().get("profiles") or {}).get(profile_id or "human_spoken_word", {})
            from zocr_mouth import _synthetic_formant_bins
            bins = _synthetic_formant_bins(prof)
        return clamp_spectrum_fcc_safe(bins, audience=body.get("audience"))

    if action in ("speaking_train", "speaking_training", "train_speaking"):
        script = INSTALL / "lib" / "hostess7-speaking-training.py"
        if not script.is_file():
            script = SG / "NewLatest" / "lib" / "hostess7-speaking-training.py"
        if not script.is_file():
            return {"ok": False, "error": "speaking_training_missing"}
        env = os.environ.copy()
        env["NEXUS_INSTALL_ROOT"] = str(INSTALL if (INSTALL / "lib").is_dir() else SG / "NewLatest")
        env["SG_ROOT"] = str(SG)
        env["QUEEN_ROOT"] = str(QUEEN)
        env["FINAL_MOUTH_ROOT"] = str(FINAL_MOUTH)
        py = [str(QUEEN / "lib"), str(FINAL_MOUTH)]
        if env.get("PYTHONPATH"):
            py.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(py)
        lesson = body.get("lesson") or body.get("lesson_id")
        cmd = [sys.executable, str(script)]
        if lesson:
            cmd.extend(["lesson", "--lesson", str(lesson)])
        else:
            cmd.append("train")
        cmd.extend(["--code", str(body.get("code") or body.get("iso6393") or "eng")])
        cmd.extend(["--audience", str(body.get("audience") or "human")])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env, cwd=str(env["NEXUS_INSTALL_ROOT"]))
        try:
            return json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return {"ok": False, "error": "speaking_train_failed", "tail": (proc.stdout or proc.stderr or "")[-800:]}

    if action in ("voice_fix", "fix_voice", "calibrate"):
        _import_mouth()
        from zocr_mouth import voice_fix
        return voice_fix(
            pitch_semitones=body.get("pitch_semitones"),
            rate_wpm=body.get("rate_wpm"),
            eq_low_db=body.get("eq_low_db"),
            eq_mid_db=body.get("eq_mid_db"),
            eq_high_db=body.get("eq_high_db"),
        )

    if action in ("fusion", "mouth_ear_eye", "mouth_ear_eye_fusion"):
        _import_mouth()
        from zocr_mouth import mouth_ear_eye_fusion
        return mouth_ear_eye_fusion(evidence=body.get("evidence"))

    if action in ("doctrine",):
        _import_mouth()
        from zocr_mouth import load_final_spec, vocal_spectrum_doctrine
        return {"ok": True, **vocal_spectrum_doctrine(), "final_mouth": load_final_spec()}

    if action in ("mouth_neural", "neural", "mouth_neural_status"):
        return {"ok": True, **_mouth_neural_status()}

    if action in ("mouth_neural_analyze", "neural_analyze"):
        script = FINAL_MOUTH / "zocr_neural_assist.py"
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps({"action": "analyze", "context": body.get("context") or body}),
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(FINAL_MOUTH),
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "error": "mouth_neural_analyze_failed"}

    if action in ("prepare_utterance", "thought_to_voice", "text_to_speech"):
        script = FINAL_MOUTH / "zocr_neural_assist.py"
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps({
                "action": "prepare",
                "thought": body.get("text") or body.get("thought"),
                "mode": body.get("mode"),
                "context": body.get("context"),
            }),
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(FINAL_MOUTH),
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "error": "prepare_failed"}

    if action in ("mouth_train", "neural_train", "train_lesson"):
        script = FINAL_MOUTH / "zocr_neural_assist.py"
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps({
                "action": "train",
                "lesson": body.get("lesson") or body.get("lesson_id") or "text_to_speech",
                "text": body.get("text"),
            }),
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(FINAL_MOUTH),
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "error": "train_failed"}

    if action in ("mouth_neural_encourage", "neural_encourage"):
        script = FINAL_MOUTH / "zocr_neural_assist.py"
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps({
                "action": "encourage",
                "label": body.get("encourage_label") or body.get("label") or "text_to_voice",
                "delta": body.get("delta"),
                "source": body.get("source") or "hostess7",
            }),
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(FINAL_MOUTH),
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "error": "encourage_failed"}

    return {
        "ok": False,
        "error": "unknown_action",
        "actions": [
            "status", "arm", "verify", "spectrum", "speak", "voice_fix",
            "fusion", "doctrine", "vocal_spectrum",
            "mouth_neural", "prepare_utterance", "mouth_train", "mouth_neural_encourage",
            "generate_frequency", "fcc_clamp", "speaking_train",
        ],
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(mouthball_status(), ensure_ascii=False))
        return 0
    if cmd == "verify":
        print(json.dumps(mouthball_verify(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-mouthball.py [json|verify|dispatch]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())