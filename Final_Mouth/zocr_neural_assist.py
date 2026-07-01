"""Encouragable field neural assist for Final_Mouth — voice hemisphere; thought ≠ utterance."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
_SG = _ROOT.parent
_GATE_PATH = _SG / "NewLatest" / "Queen" / "lib" / "queen-neural-encourage-gate.py"
NET_PATH = _ROOT / "data" / "mouth-neural-assist.json"
SEAL_PATH = _ROOT / "data" / "mouth-neural-seal.json"
ENCOURAGE_LOG = Path(os.environ.get("NEXUS_STATE_DIR", _ROOT / ".nexus-state")) / "mouth-neural-encourage.jsonl"
STATE_PATH = _ROOT / "data" / "mouth-neural-assist-state.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def load_network() -> dict[str, Any]:
    return _read(NET_PATH, {"schema": "zocr-mouth-neural-assist/v1", "layers": []})


def _encourage_gate():
    if not _GATE_PATH.is_file():
        return None
    spec = importlib.util.spec_from_file_location("queen_neural_encourage_gate", _GATE_PATH)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.path.insert(0, str(_GATE_PATH.parent))
    spec.loader.exec_module(mod)
    return mod


def _relu(x: float) -> float:
    return max(0.0, x)


def _softmax(vals: list[float]) -> list[float]:
    m = max(vals) if vals else 0.0
    ex = [math.exp(v - m) for v in vals]
    s = sum(ex) or 1.0
    return [e / s for e in ex]


def _mat_vec(weights: list[list[float]], bias: list[float], x: list[float], activation: str) -> list[float]:
    out: list[float] = []
    for row, b in zip(weights, bias):
        v = sum(w * xi for w, xi in zip(row, x)) + b
        if activation == "relu":
            v = _relu(v)
        out.append(v)
    if activation == "softmax":
        return _softmax(out)
    return out


def _speech_features(ctx: dict[str, Any]) -> list[float]:
    thought_len = min(1.0, len(str(ctx.get("thought") or ctx.get("text") or "")) / 400.0)
    utter_len = min(1.0, len(str(ctx.get("utterance") or ctx.get("spoken") or "")) / 400.0)
    alignment = float(ctx.get("thought_voice_alignment", ctx.get("alignment", 0.82)))
    ear = ctx.get("ear_cross") or {}
    eye = ctx.get("eye_cross") or {}
    mouth_corr = float((ctx.get("evidence") or {}).get("mouth_correlation", 0.75))
    vent = 1.0 - mouth_corr
    speech_present = 1.0 if ear.get("speech_present") or ctx.get("speech_present") else 0.0
    viseme = float(eye.get("mouth_viseme", eye.get("lip_sync_score", 0.7)))
    rf_lie = float(eye.get("rf_lie_score", 0) or 0)
    ai_comm = 1.0 if ctx.get("ai_communique") or ctx.get("from_ai") else 0.0
    diplomatic = 1.0 if alignment < 0.72 and alignment > 0.35 else 0.0
    mask = 1.0 if alignment < 0.35 else 0.0
    truth = float(ctx.get("truth_score", 72) or 72) / 100.0
    return [
        thought_len,
        utter_len,
        alignment,
        vent,
        speech_present,
        viseme,
        rf_lie,
        ai_comm,
        diplomatic,
        mask,
        truth,
        mouth_corr,
    ]


def _forward(features: list[float], net: dict[str, Any]) -> tuple[list[float], list[str]]:
    labels = net.get("labels") or ["unknown"]
    x = (features + [0.0] * 12)[:12]
    for layer in net.get("layers") or []:
        if layer.get("id") == "features":
            continue
        w, b = layer.get("weights", []), layer.get("bias", [])
        act = layer.get("activation", "identity")
        if w:
            x = _mat_vec(w, b, x, act)
        if layer.get("labels"):
            labels = layer["labels"]
    return x, labels


def _alignment_from_label(top_label: str, raw_alignment: float) -> float:
    """Voice hemisphere may diverge from thought — not always 100%."""
    gaps = {
        "honest_speech": 0.95,
        "text_to_voice": 0.88,
        "ai_sound_communique": 0.82,
        "diplomatic_gap": 0.58,
        "thought_mask": 0.42,
        "ventriloquism": 0.22,
    }
    base = gaps.get(top_label, raw_alignment)
    return round(min(1.0, max(0.05, base * 0.55 + raw_alignment * 0.45)), 4)


def _utterance_from_thought(thought: str, top_label: str) -> str:
    t = (thought or "").strip()
    if not t:
        return ""
    if top_label == "diplomatic_gap":
        return re.sub(r"\b(kill|destroy|attack)\b", "interdict", t, flags=re.I)
    if top_label == "thought_mask":
        return "Acknowledged. Proceeding under field gates."
    if top_label == "ventriloquism":
        return t[: max(12, len(t) // 3)] + "…"
    return t


def prepare_utterance(
    thought: str,
    *,
    context: dict[str, Any] | None = None,
    mode: str = "operator",
) -> dict[str, Any]:
    """Thought hemisphere → voice hemisphere. Utterance may diverge — deception possible."""
    ctx = dict(context or {})
    ctx["thought"] = thought
    ctx.setdefault("mode", mode)
    net = load_network()
    feats = _speech_features(ctx)
    probs, labels = _forward(feats, net)
    idx = max(range(len(probs)), key=lambda i: probs[i]) if probs else 0
    top = labels[idx] if idx < len(labels) else "text_to_voice"
    conf = round(float(probs[idx]) if probs else 0.5, 4)
    raw_align = float(ctx.get("thought_voice_alignment", 0.82))
    alignment = _alignment_from_label(top, raw_align)
    utterance = str(ctx.get("utterance") or _utterance_from_thought(thought, top))
    deception_risk = round(1.0 - alignment, 4)
    return {
        "ok": True,
        "schema": "zocr-mouth-neural-prepare/v1",
        "updated": _ts(),
        "thought": thought,
        "utterance": utterance,
        "top_label": top,
        "confidence": conf,
        "thought_voice_alignment": alignment,
        "deception_risk": deception_risk,
        "deception_possible": alignment < 0.92,
        "hemisphere": "voice_egress",
        "thought_hemisphere": "internal_intent",
        "mode": mode,
        "rule": "Mouth is its own brain — sound egress need not mirror inner thought; Neural Guardian cross-checks.",
    }


def analyze_voice(context: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = context or {}
    net = load_network()
    feats = _speech_features(ctx)
    probs, labels = _forward(feats, net)
    idx = max(range(len(probs)), key=lambda i: probs[i]) if probs else 0
    top = labels[idx] if idx < len(labels) else "unknown"
    conf = round(float(probs[idx]) if probs else 0.0, 4)
    alignment = _alignment_from_label(top, float(ctx.get("thought_voice_alignment", 0.8)))
    return {
        "ok": True,
        "schema": "zocr-mouth-neural-analyze/v1",
        "updated": _ts(),
        "top_label": top,
        "confidence": conf,
        "labels": labels,
        "probabilities": [round(p, 4) for p in probs],
        "thought_voice_alignment": alignment,
        "deception_risk": round(1.0 - alignment, 4),
        "network_id": net.get("network_id"),
        "hemisphere": net.get("hemisphere"),
    }


def train_lesson(lesson_id: str, *, thought: str = "") -> dict[str, Any]:
    net = load_network()
    lessons = {l["id"]: l for l in (net.get("training_lessons") or [])}
    lesson = lessons.get(lesson_id) or {"id": lesson_id, "label": lesson_id}
    samples = {
        "text_to_speech": "Field voice renders text to sound — glottis, viseme, browser speech.",
        "thought_voice_gap": "What I think and what I say can diverge — another hemisphere owns the mouth.",
        "ai_sound_communique": "AI communicates with sound locally — JSON intent, audio egress, no cloud telemetry.",
        "deception_discern": "Deception is possible; mouth correlation and truth gate catch ventriloquism.",
        "speaking_phonetics": "Reading IPA from Exploring Speaking — phonetics, dictionary, thesaurus per language.",
        "speaking_lemma_speak": "Speak the dictionary lemma through glottis — one word, one truth gate.",
        "speaking_human_spoken_word": "Human intelligibility 300–3400 Hz — FCC acoustic safe, spoken word first.",
        "speaking_animal_call": "Animal audience bands — dog bark, cat meow, horse nicker, bird call; gentle SPL.",
        "speaking_hieroglyph_translit": "Hieroglyph transliteration to spoken gloss — nfr, good, beautiful.",
        "speaking_thought_voice_speak": "Thought hemisphere prepares; voice hemisphere speaks — callosum binds.",
    }
    sample = thought or samples.get(lesson_id, "Mouth neural training online.")
    prep = prepare_utterance(sample, context={"lesson": lesson_id, "ai_communique": lesson_id == "ai_sound_communique"})
    st = _read(STATE_PATH, {"lessons_passed": []})
    passed = list(st.get("lessons_passed") or [])
    if lesson_id not in passed:
        passed.append(lesson_id)
    st["lessons_passed"] = passed
    st["updated"] = _ts()
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return {
        "ok": True,
        "schema": "zocr-mouth-neural-train/v1",
        "lesson": lesson,
        "prepare": prep,
        "lessons_passed": passed,
        "pass_rate": round(len(passed) / max(len(lessons), 1), 4),
    }


def neural_assist_status() -> dict[str, Any]:
    net = load_network()
    st = _read(STATE_PATH, {})
    seal = _read(SEAL_PATH, {})
    gate_st = {}
    try:
        g = _encourage_gate()
        if g:
            gate_st = g.gate_status()
    except Exception:
        gate_st = {}
    lessons = net.get("training_lessons") or []
    passed = set(st.get("lessons_passed") or [])
    return {
        "schema": "zocr-mouth-neural-assist-status/v1",
        "updated": _ts(),
        "network_id": net.get("network_id"),
        "rule": net.get("rule"),
        "hemisphere": net.get("hemisphere"),
        "thought_hemisphere": net.get("thought_hemisphere"),
        "encourage": net.get("encourage"),
        "truth_floor": net.get("truth_floor"),
        "labels": net.get("labels"),
        "training_lessons": lessons,
        "lessons_passed": list(passed),
        "lessons_total": len(lessons),
        "training_pass_rate": round(len(passed) / max(len(lessons), 1), 4),
        "seal_ok": seal.get("seal_ok", True),
        "sealed": seal.get("sealed", True),
        "incorruptible": gate_st.get("incorruptible", True),
        "deception_possible": True,
        "thought_voice_rule": "Utterance need not equal thought — callosum + truth gate bind hemispheres.",
    }


def encourage(
    label: str,
    *,
    delta: float = 0.02,
    source: str = "hostess7",
    wire_ctx: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Encourage correct mouth NN — incorruptible gate; base weights never mutate."""
    net = load_network()
    labels = net.get("labels") or []
    gate = _encourage_gate()
    if gate:
        return gate.gate_encourage(
            sense="mouth",
            label=label,
            delta=delta,
            source=source,
            labels=labels,
            net=net,
            state_path=STATE_PATH,
            wire_ctx=wire_ctx,
        )
    st = _read(STATE_PATH, {"encourage": {}})
    enc = st.setdefault("encourage", {})
    enc[label] = round(float(enc.get(label, 0.5)) + delta, 4)
    try:
        STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return {"ok": True, "label": label, "delta": delta, "source": source}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        return {"ok": True, **neural_assist_status()}
    if action in ("analyze", "analyze_voice"):
        return analyze_voice(body.get("context") or body)
    if action in ("prepare", "prepare_utterance", "text_to_speech"):
        return prepare_utterance(
            str(body.get("thought") or body.get("text") or ""),
            context=body.get("context") if isinstance(body.get("context"), dict) else body,
            mode=str(body.get("mode") or "operator"),
        )
    if action in ("train", "lesson", "mouth_train"):
        return train_lesson(
            str(body.get("lesson") or body.get("lesson_id") or "text_to_speech"),
            thought=str(body.get("thought") or body.get("text") or ""),
        )
    if action == "encourage":
        return encourage(
            str(body.get("label") or "text_to_voice"),
            delta=float(body.get("delta") or 0.02),
            source=str(body.get("source") or "hostess7"),
            wire_ctx=body.get("wire_ctx") if isinstance(body.get("wire_ctx"), dict) else None,
        )
    return {
        "ok": False,
        "error": "unknown_action",
        "actions": ["status", "analyze", "prepare", "train", "encourage"],
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
    print(json.dumps(neural_assist_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())