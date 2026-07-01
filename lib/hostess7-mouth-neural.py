#!/usr/bin/env pythong
"""Hostess 7 mouth field neural — voice hemisphere, thought≠utterance, mouth training."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent)))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL / "Queen"))
FINAL_MOUTH = Path(os.environ.get("FINAL_MOUTH_ROOT", INSTALL / "Final_Mouth"))
DOCTRINE = INSTALL / "data" / "hostess7-mouth-neural-doctrine.json"
PANEL = STATE / "hostess7-mouth-neural-panel.json"
LEDGER = STATE / "hostess7-mouth-neural-ledger.jsonl"
MOUTH_NEURAL = FINAL_MOUTH / "zocr_neural_assist.py"
MOUTHBALL = QUEEN / "lib" / "queen-mouthball.py"

ENABLED = os.environ.get("NEXUS_HOSTESS7_MOUTH_NEURAL", "1") == "1"


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


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    env["NEXUS_STATE_DIR"] = str(STATE)
    env["SG_ROOT"] = str(SG)
    env["QUEEN_ROOT"] = str(QUEEN)
    env["FINAL_MOUTH_ROOT"] = str(FINAL_MOUTH)
    env["QUEEN_ROOT"] = str(QUEEN)
    py = [
        str(QUEEN / "lib"),
        str(FINAL_MOUTH),
    ]
    if env.get("PYTHONPATH"):
        py.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(py)
    return env


def _sense_core() -> Any | None:
    py = INSTALL / "lib" / "hostess7-sense-core.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("hostess7_sense_core_mouth", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_mouth_neural(body: dict[str, Any], *, timeout: int = 60) -> dict[str, Any]:
    core = _sense_core()
    if core and hasattr(core, "mouth_neural_dispatch"):
        return core.mouth_neural_dispatch(body)
    if not MOUTH_NEURAL.is_file():
        return {"ok": False, "error": "mouth_neural_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(MOUTH_NEURAL), "dispatch"],
            input=json.dumps(body, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
            cwd=str(FINAL_MOUTH),
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def _run_mouthball(body: dict[str, Any], *, timeout: int = 90) -> dict[str, Any]:
    core = _sense_core()
    if core and hasattr(core, "sense_ball_dispatch"):
        return core.sense_ball_dispatch("mouth", body)
    if not MOUTHBALL.is_file():
        return {"ok": False, "error": "mouthball_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(MOUTHBALL), "dispatch"],
            input=json.dumps(body, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
            cwd=str(QUEEN),
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def speak_field_neural(
    text: str,
    *,
    mode: str = "operator",
    audience: str | None = None,
) -> dict[str, Any]:
    """Thought → voice hemisphere → optional TTS."""
    if not ENABLED:
        return {"ok": False, "error": "disabled"}
    aud = audience or ("human" if mode in ("speaking", "operator", "dishes") else None)
    prep = _run_mouth_neural({"action": "prepare", "thought": text, "mode": mode})
    if not prep.get("ok"):
        return prep
    utterance = str(prep.get("utterance") or text)
    speak_body: dict[str, Any] = {"action": "speak", "text": utterance, "mode": mode}
    if aud:
        speak_body["audience"] = aud
    spoken = _run_mouthball(speak_body)
    voice = {}
    vpath = INSTALL / "lib" / "hostess7-voice.py"
    if vpath.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(vpath), "speak", utterance],
                capture_output=True,
                text=True,
                timeout=120,
                env=_env(),
            )
            voice = json.loads(proc.stdout or "{}")
        except (json.JSONDecodeError, subprocess.TimeoutExpired):
            voice = {"ok": False}
    out = {
        "ok": prep.get("ok") and (spoken.get("ok") or voice.get("ok")),
        "schema": "hostess7-mouth-neural-speak/v1",
        "thought": prep.get("thought"),
        "utterance": utterance,
        "thought_voice_alignment": prep.get("thought_voice_alignment"),
        "deception_risk": prep.get("deception_risk"),
        "deception_possible": prep.get("deception_possible"),
        "top_label": prep.get("top_label"),
        "mouthball": spoken,
        "hostess_voice": voice,
    }
    _append_ledger({"ts": _now(), "event": "speak", "alignment": prep.get("thought_voice_alignment"), "label": prep.get("top_label")})
    return out


def _speaking_training_mod() -> Any | None:
    script = INSTALL / "lib" / "hostess7-speaking-training.py"
    if not script.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("h7_speaking_train", script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _run_speaking_training(
    *,
    iso6393: str = "eng",
    audience: str = "human",
) -> dict[str, Any]:
    mod = _speaking_training_mod()
    if mod and hasattr(mod, "run_speaking_training"):
        return mod.run_speaking_training(iso6393=iso6393, audience=audience)
    return {"ok": False, "error": "speaking_training_missing"}


def _run_mouth_training_body(
    *,
    iso6393: str = "eng",
    audience: str = "human",
) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    training = doc.get("training") or {}
    lessons = training.get("lessons") or []
    speaking_track = training.get("speaking_track") or {}
    steps: list[dict[str, Any]] = []
    passed = 0
    sp_mod = _speaking_training_mod()
    for lid in lessons:
        if str(lid).startswith("speaking_"):
            lesson_key = str(lid).replace("speaking_", "", 1)
            if sp_mod and hasattr(sp_mod, "run_lesson"):
                result = sp_mod.run_lesson(lesson_key, iso6393=iso6393, audience=audience)
            else:
                result = _run_mouthball({
                    "action": "speaking_train",
                    "lesson": lesson_key,
                    "code": iso6393,
                    "audience": audience,
                })
            ok = bool(result.get("ok"))
            _run_mouth_neural({"action": "train", "lesson": lid, "thought": str(result.get("lemma") or "")})
        else:
            result = _run_mouth_neural({"action": "train", "lesson": lid})
            ok = bool(result.get("ok"))
        if ok:
            passed += 1
        steps.append({
            "id": lid,
            "label": (result.get("lesson") or {}).get("label") or lid,
            "ok": ok,
            "alignment": (result.get("prepare") or {}).get("thought_voice_alignment"),
            "track": "speaking" if str(lid).startswith("speaking_") else "mouth_neural",
        })
    speaking_panel = _run_speaking_training(
        iso6393=iso6393 or speaking_track.get("default_code", "eng"),
        audience=audience or speaking_track.get("default_audience", "human"),
    )
    verify = _run_mouthball({"action": "verify"})
    neural = _run_mouth_neural({"action": "status"})
    total = len(lessons) or 1
    rate = passed / total
    threshold = float(training.get("pass_threshold") or 0.75)
    complete = rate >= threshold and verify.get("ok")
    panel = {
        "schema": "hostess7-mouth-neural-panel/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "passed": passed,
        "total": total,
        "pass_rate": round(rate * 100, 1),
        "complete": complete,
        "mastered": complete and passed == total and verify.get("ok"),
        "level": "mastered" if complete and passed == total else "complete" if complete else "training" if passed else "pending",
        "score": round(rate, 4),
        "steps": steps,
        "neural": neural,
        "verify": verify,
        "speaking_training": speaking_panel,
        "fcc_acoustic_safe": bool(speaking_panel.get("fcc_acoustic") or speaking_panel.get("complete")),
        "spoken_word_first": True,
        "default_audience": audience,
        "iso6393": iso6393,
        "hemispheres": doc.get("hemispheres"),
        "callosum": doc.get("callosum"),
    }
    _save(PANEL, panel)
    _append_ledger({
        "ts": _now(),
        "event": "mouth_train",
        "passed": passed,
        "total": total,
        "speaking_complete": speaking_panel.get("complete"),
    })
    ca = INSTALL / "lib" / "hostess7-change-awareness.py"
    if ca.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_ca_mouth", ca)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "witness_change"):
                    mod.witness_change(
                        source="mouth_neural",
                        label="mouth_training",
                        detail=f"level={panel.get('level')} passed={passed}/{total}",
                        meta={"complete": complete, "fcc_acoustic_safe": panel.get("fcc_acoustic_safe")},
                    )
        except Exception:
            pass
    return {"ok": complete, **panel}


def run_mouth_training(
    *,
    iso6393: str = "eng",
    audience: str = "human",
) -> dict[str, Any]:
    aid = f"mouth_training_{iso6393}"
    pg = INSTALL / "lib" / "hostess7-presume.py"
    if pg.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_presume_mouth", pg)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "guard_action"):
                    guarded = mod.guard_action(
                        aid,
                        _run_mouth_training_body,
                        iso6393=iso6393,
                        audience=audience,
                        label=aid,
                    )
                    result = guarded.get("result") or {}
                    if isinstance(result, dict):
                        result["presume_guard"] = {
                            "action_id": aid,
                            "uninterruptable": guarded.get("uninterruptable"),
                            "elapsed_us": guarded.get("elapsed_us"),
                        }
                        return result
        except Exception:
            pass
    return _run_mouth_training_body(iso6393=iso6393, audience=audience)


def _ironclad_goldmine() -> dict[str, Any]:
    cached = _load(STATE / "ironclad-immediate.json", {})
    if cached.get("plate_to_sense"):
        return cached["plate_to_sense"]
    ic_py = INSTALL / "lib" / "ironclad-immediate.py"
    if ic_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("ironclad_immediate", ic_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "for_self"):
                    doc = mod.for_self("hostess7")
                    return doc.get("plate_to_sense") or {}
                if hasattr(mod, "plate_to_sense_goldmine"):
                    return mod.plate_to_sense_goldmine()
        except Exception:
            pass
    return {}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    cached = _load(PANEL, {})
    neural = _run_mouth_neural({"action": "status"})
    goldmine = _ironclad_goldmine()
    mouth_receipt = (goldmine.get("members") or {}).get("mouth_neural") or {}
    if not cached.get("steps"):
        run_mouth_training()
        cached = _load(PANEL, {})
    out = {
        "schema": "hostess7-mouth-neural-panel/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "motto": doc.get("motto"),
        "hemispheres": doc.get("hemispheres"),
        "callosum": doc.get("callosum"),
        "neural_status": neural,
        "passed": cached.get("passed"),
        "total": cached.get("total"),
        "pass_rate": cached.get("pass_rate"),
        "complete": cached.get("complete"),
        "mastered": cached.get("mastered"),
        "level": cached.get("level"),
        "score": cached.get("score"),
        "steps": cached.get("steps") or [],
        "lessons_passed": neural.get("lessons_passed"),
        "training_pass_rate": neural.get("training_pass_rate"),
        "deception_possible": True,
        "ironclad_goldmine": goldmine,
        "plate_to_sense": goldmine,
        "ironclad_grounded": bool(goldmine.get("ironclad_grounded")),
        "truth_percent": mouth_receipt.get("truth_percent") or goldmine.get("truth_percent"),
        "citation": mouth_receipt.get("citation") or goldmine.get("citation") or "ironclad:neural:2",
        "read_first": bool(mouth_receipt.get("read_first") or goldmine.get("read_first")),
    }
    if write:
        _save(PANEL, out)
    return out


def explain_mouth_neural(query: str) -> str | None:
    low = (query or "").lower()
    keys = (
        "mouth neural", "voice hemisphere", "thought voice", "mouth brain",
        "mouth training", "speech hemisphere", "deception voice", "field neural voice",
    )
    if not any(k in low for k in keys):
        return None
    panel = build_panel(write=False)
    neural = panel.get("neural_status") or {}
    lines = [
        "The mouth has its own field neural brain — a voice hemisphere separate from thought.",
        "What I think and what I say can diverge; deception is possible and alignment is not always 100%.",
        f"Training: {panel.get('passed', 0)}/{panel.get('total', 4)} lessons · pass {panel.get('pass_rate', 0)}%.",
        "Text becomes speech through glottis, viseme, and browser TTS — AI communique uses sound locally only.",
        "Ear and eye cross-check mouth_correlation; Neural Guardian holds the callosum gap honest.",
    ]
    if neural.get("lessons_passed"):
        lines.append(f"Lessons sealed: {', '.join(neural.get('lessons_passed') or [])}.")
    return "\n".join(lines)


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}
    if action in ("speak", "field_speak"):
        return speak_field_neural(
            str(body.get("text") or body.get("thought") or ""),
            mode=str(body.get("mode") or "operator"),
            audience=body.get("audience"),
        )
    if action in ("train", "mouth_train", "run_training"):
        return run_mouth_training(
            iso6393=str(body.get("code") or body.get("iso6393") or "eng"),
            audience=str(body.get("audience") or "human"),
        )
    if action in ("speaking_train", "speaking_training"):
        return _run_speaking_training(
            iso6393=str(body.get("code") or body.get("iso6393") or "eng"),
            audience=str(body.get("audience") or "human"),
        )
    if action == "prepare":
        return _run_mouth_neural({"action": "prepare", "thought": body.get("text"), "mode": body.get("mode")})
    if action == "explain":
        reply = explain_mouth_neural(str(body.get("query") or ""))
        return {"ok": bool(reply), "reply": reply or ""}
    return {"ok": False, "error": "unknown_action"}


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
        print(json.dumps(build_panel(write=False), ensure_ascii=False))
        return 0
    if cmd == "train":
        print(json.dumps(run_mouth_training(), ensure_ascii=False))
        return 0
    if cmd == "speak" and len(sys.argv) > 2:
        print(json.dumps(speak_field_neural(" ".join(sys.argv[2:])), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-mouth-neural.py [json|train|speak TEXT|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())