"""ZOCR vocal spectrum v1 — voice profiles, TTS, viseme, mouth-ear-eye fusion."""
from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent
_SG = _ROOT.parent
DOCTRINE_PATH = _ROOT / "data" / "vocal-spectrum.json"
FINAL_PATH = _ROOT / "data" / "final-mouth.json"
FCC_ACOUSTIC_PATH = _SG / "NewLatest" / "data" / "final-mouth-fcc-acoustic.json"
if not FCC_ACOUSTIC_PATH.is_file():
    FCC_ACOUSTIC_PATH = _SG / "data" / "final-mouth-fcc-acoustic.json"
STATE_PATH = _ROOT / "data" / "mouth-state.json"
ENGINE = "glottis_v1"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-vocal-spectrum/v1", "default_profile": "human_neutral", "profiles": {}}


def load_fcc_acoustic() -> dict[str, Any]:
    for path in (FCC_ACOUSTIC_PATH, _ROOT / "data" / "final-mouth-fcc-acoustic.json"):
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return {
        "schema": "final-mouth-fcc-acoustic/v1",
        "synthesis_range_hz": [20, 20000],
        "default_audience": "human",
        "audiences": {"human": {"intelligibility_hz": [300, 3400], "fundamental_hz": [85, 255]}},
    }


def _audience_spec(audience: str | None = None) -> dict[str, Any]:
    doc = load_fcc_acoustic()
    aud = audience or doc.get("default_audience") or "human"
    return (doc.get("audiences") or {}).get(aud) or (doc.get("audiences") or {}).get("human") or {}


def clamp_spectrum_fcc_safe(
    bins: list[dict[str, Any]],
    *,
    audience: str | None = None,
) -> dict[str, Any]:
    """Model any frequency internally; clamp air egress to audience intelligibility bands."""
    spec = _audience_spec(audience)
    intel = spec.get("intelligibility_hz") or [300, 3400]
    lo_i, hi_i = float(intel[0]), float(intel[1])
    fund = spec.get("fundamental_hz") or [85, 255]
    lo_f, hi_f = float(fund[0]), float(fund[1])
    fcc = load_fcc_acoustic()
    syn = fcc.get("synthesis_range_hz") or [20, 20000]
    clamped: list[dict[str, Any]] = []
    for b in bins:
        hz = float(b.get("hz") or 0)
        db = float(b.get("db") or -60)
        egress_db = db
        note = "pass"
        if hz < syn[0] or hz > syn[1]:
            egress_db = -96
            note = "reject_outside_synthesis"
        elif hz < lo_i or hz > hi_i:
            egress_db = db - 12
            note = "attenuate_outside_intelligibility"
        elif hz < lo_f or hz > hi_f:
            egress_db = db - 3
            note = "fundamental_edge"
        clamped.append({**b, "egress_db": round(egress_db, 2), "clamp": note})
    peak = max(clamped, key=lambda x: x.get("egress_db", -96)) if clamped else {}
    return {
        "ok": True,
        "schema": "zocr-fcc-acoustic-clamp/v1",
        "audience": audience or fcc.get("default_audience", "human"),
        "intelligibility_hz": intel,
        "fundamental_hz": fund,
        "synthesis_range_hz": syn,
        "spoken_word_first": bool(fcc.get("spoken_word_first", True)),
        "bins": clamped,
        "peak_egress_hz": peak.get("hz"),
        "peak_egress_db": peak.get("egress_db"),
        "max_spl_db": spec.get("max_spl_db"),
    }


def generate_frequency(
    hz: float,
    *,
    audience: str | None = None,
    duration_ms: int = 50,
) -> dict[str, Any]:
    """Generate any in-band frequency; return FCC-safe egress spec for listeners."""
    fcc = load_fcc_acoustic()
    syn = fcc.get("synthesis_range_hz") or [20, 20000]
    hz = float(hz)
    if hz < syn[0] or hz > syn[1]:
        return {"ok": False, "error": "outside_synthesis_range", "hz": hz, "range_hz": syn}
    profile = (load_doctrine().get("profiles") or {}).get("human_spoken_word", {})
    lo, hi = profile.get("range_hz", [85, 3400])[:2]
    bins = _synthetic_formant_bins({**profile, "pitch_hz": hz if hz < 500 else profile.get("pitch_hz", 120)}, bins=32)
    clamp = clamp_spectrum_fcc_safe(bins, audience=audience)
    return {
        "ok": True,
        "schema": "zocr-frequency-generate/v1",
        "requested_hz": hz,
        "duration_ms": duration_ms,
        "audience": clamp.get("audience"),
        "fcc_safe": True,
        "clamp": clamp,
        "rule": "Synthesize any audible Hz — egress prioritizes spoken-word intelligibility for humans/animals.",
    }


def load_final_spec() -> dict[str, Any]:
    try:
        return json.loads(FINAL_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "zocr-final-mouth/v1", "modes": {}}


def _load_state() -> dict[str, Any]:
    if STATE_PATH.is_file():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    doc = load_doctrine()
    return {
        "schema": "zocr-mouth-state/v1",
        "active_profile": doc.get("default_profile", "human_neutral"),
        "active_mode": "dishes",
        "active_voice": "robotics_brief",
        "voice_fix": {"pitch_semitones": 0, "rate_wpm": 140, "eq_low_db": 0, "eq_mid_db": 0, "eq_high_db": 0},
    }


def _save_state(st: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    st["updated"] = _ts()
    STATE_PATH.write_text(json.dumps(st, indent=2) + "\n", encoding="utf-8")


def list_profiles() -> list[dict[str, Any]]:
    doc = load_doctrine()
    out: list[dict[str, Any]] = []
    for pid, p in (doc.get("profiles") or {}).items():
        out.append({
            "id": pid,
            "label": p.get("label", pid),
            "class": p.get("class", ""),
            "range_hz": p.get("range_hz", []),
            "formants_hz": p.get("formants_hz", []),
            "pitch_hz": p.get("pitch_hz"),
            "teach": p.get("teach", ""),
        })
    return sorted(out, key=lambda x: x["id"])


def list_modes() -> list[dict[str, Any]]:
    doc = load_final_spec()
    return [
        {"id": mid, "label": m.get("label", mid), "vocal_profile": m.get("vocal_profile")}
        for mid, m in sorted((doc.get("modes") or {}).items())
    ]


def vocal_spectrum_doctrine() -> dict[str, Any]:
    doc = load_doctrine()
    st = _load_state()
    return {
        "schema": "zocr-vocal-spectrum-doctrine/v1",
        "title": "Vocal spectrum — formant engine",
        "engine": ENGINE,
        "doctrine": doc.get("doctrine"),
        "profiles": list_profiles(),
        "visemes": doc.get("visemes", []),
        "tts_engines": doc.get("tts_engines", []),
        "active_profile": st.get("active_profile"),
        "active_mode": st.get("active_mode"),
    }


def _synthetic_formant_bins(profile: dict[str, Any], *, bins: int = 64) -> list[dict[str, Any]]:
    """Generate human-readable spectrum bins from profile formants."""
    lo, hi = profile.get("range_hz", [80, 8000])[:2]
    formants = [f for f in (profile.get("formants_hz") or []) if f]
    pitch = float(profile.get("pitch_hz") or 0)
    out: list[dict[str, Any]] = []
    for i in range(bins):
        f = lo + (hi - lo) * i / max(bins - 1, 1)
        energy = 0.02
        for fm in formants:
            sigma = max(fm * 0.12, 40.0)
            energy += math.exp(-0.5 * ((f - fm) / sigma) ** 2)
        if pitch > 0:
            for h in range(1, 6):
                hf = pitch * h
                if hf <= hi:
                    sigma = max(hf * 0.06, 25.0)
                    energy += 0.35 / h * math.exp(-0.5 * ((f - hf) / sigma) ** 2)
        db = round(20 * math.log10(max(energy, 1e-6)), 2)
        out.append({"hz": round(f, 1), "db": db, "band": i})
    return out


def analyze_vocal_spectrum(*, profile_id: str | None = None) -> dict[str, Any]:
    doc = load_doctrine()
    st = _load_state()
    pid = profile_id or st.get("active_profile") or doc.get("default_profile", "human_neutral")
    profile = (doc.get("profiles") or {}).get(pid, {})
    bins = _synthetic_formant_bins(profile)
    peak = max(bins, key=lambda b: b["db"]) if bins else {}
    return {
        "ok": True,
        "schema": "zocr-vocal-spectrum-analyze/v1",
        "updated": _ts(),
        "profile": pid,
        "label": profile.get("label", pid),
        "range_hz": profile.get("range_hz", []),
        "formants_hz": profile.get("formants_hz", []),
        "pitch_hz": profile.get("pitch_hz"),
        "bins": bins,
        "peak_hz": peak.get("hz"),
        "peak_db": peak.get("db"),
        "visemes": doc.get("visemes", []),
    }


def voice_fix(*, pitch_semitones: float | None = None, rate_wpm: int | None = None,
              eq_low_db: float | None = None, eq_mid_db: float | None = None,
              eq_high_db: float | None = None) -> dict[str, Any]:
    st = _load_state()
    fix = dict(st.get("voice_fix") or {})
    if pitch_semitones is not None:
        fix["pitch_semitones"] = round(float(pitch_semitones), 2)
    if rate_wpm is not None:
        fix["rate_wpm"] = int(rate_wpm)
    if eq_low_db is not None:
        fix["eq_low_db"] = round(float(eq_low_db), 2)
    if eq_mid_db is not None:
        fix["eq_mid_db"] = round(float(eq_mid_db), 2)
    if eq_high_db is not None:
        fix["eq_high_db"] = round(float(eq_high_db), 2)
    st["voice_fix"] = fix
    _save_state(st)
    spec = analyze_vocal_spectrum()
    return {
        "ok": True,
        "schema": "zocr-voice-fix/v1",
        "voice_fix": fix,
        "spectrum": spec,
        "hint": "Apply in browser via Web Speech API or espeak -p/-s flags",
    }


def _try_espeak(text: str, *, rate_wpm: int, pitch_semitones: float) -> dict[str, Any]:
    exe = shutil.which("espeak") or shutil.which("espeak-ng")
    if not exe:
        return {"ok": False, "engine": "espeak", "error": "espeak_not_found"}
    pitch = int(50 + pitch_semitones * 4)
    speed = max(80, min(450, rate_wpm))
    try:
        proc = subprocess.run(
            [exe, "-s", str(speed), "-p", str(pitch), text],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "ok": proc.returncode == 0,
            "engine": "espeak",
            "played": proc.returncode == 0,
            "stderr": (proc.stderr or "")[:200],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "engine": "espeak", "error": str(exc)}


def speak(
    text: str,
    *,
    mode: str | None = None,
    voice: str | None = None,
    engine: str | None = None,
    audience: str | None = None,
) -> dict[str, Any]:
    doc = load_final_spec()
    st = _load_state()
    mid = mode or st.get("active_mode", "dishes")
    voc = voice or st.get("active_voice", "robotics_brief")
    modes = doc.get("modes") or {}
    if mid not in modes:
        return {"ok": False, "error": "unknown_mode", "mode": mid}
    m = modes[mid]
    spoken = (m.get("speak") or {}).get(voc) or doc.get("rule", "")
    if text.strip():
        spoken = text.strip()
    fix = st.get("voice_fix") or {}
    rate = int(fix.get("rate_wpm") or m.get("rate_wpm") or 140)
    pitch = float(fix.get("pitch_semitones") or m.get("pitch_semitones") or 0)
    eng = engine or m.get("tts_engine") or "doctrine"
    aud = audience or m.get("audience") or load_doctrine().get("default_audience", "human")
    profile_id = m.get("vocal_profile") or st.get("active_profile")
    if aud.startswith("animal_") and aud == "animal_dog":
        profile_id = profile_id or "animal_dog_call"
    elif aud.startswith("animal_") and aud == "animal_cat":
        profile_id = profile_id or "animal_cat_call"
    elif aud == "human" or m.get("fcc_acoustic_safe"):
        profile_id = profile_id or "human_spoken_word"
    profile = (load_doctrine().get("profiles") or {}).get(profile_id, {})
    raw_bins = _synthetic_formant_bins(profile)
    fcc_clamp = clamp_spectrum_fcc_safe(raw_bins, audience=aud)
    tts: dict[str, Any] = {"engine": eng, "played": False}
    if eng == "espeak":
        tts = _try_espeak(spoken, rate_wpm=rate, pitch_semitones=pitch)
    return {
        "ok": True,
        "schema": "zocr-mouth-speak/v1",
        "mode": mid,
        "voice": voc,
        "text": spoken,
        "rate_wpm": rate,
        "pitch_semitones": pitch,
        "vocal_profile": profile_id,
        "audience": aud,
        "fcc_acoustic_safe": bool(m.get("fcc_acoustic_safe", True)),
        "spoken_word_first": bool(load_doctrine().get("spoken_word_first", True)),
        "fcc_clamp": fcc_clamp,
        "tts": tts,
        "browser_hint": "Use speechSynthesis in panel for doctrine/browser_speech engine",
    }


def set_mode(mode: str, *, voice: str | None = None) -> dict[str, Any]:
    doc = load_final_spec()
    if mode not in (doc.get("modes") or {}):
        return {"ok": False, "error": "unknown_mode", "available": list((doc.get("modes") or {}).keys())}
    st = _load_state()
    st["active_mode"] = mode
    m = doc["modes"][mode]
    st["active_profile"] = m.get("vocal_profile", st.get("active_profile"))
    if voice:
        st["active_voice"] = voice
    fix = st.get("voice_fix") or {}
    if m.get("rate_wpm") is not None:
        fix["rate_wpm"] = m["rate_wpm"]
    if m.get("pitch_semitones") is not None:
        fix["pitch_semitones"] = m["pitch_semitones"]
    st["voice_fix"] = fix
    _save_state(st)
    return {"ok": True, "mode": mode, "speak": speak("", mode=mode, voice=st.get("active_voice"))}


def mouth_ear_eye_fusion(*, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    ev = evidence or {}
    mouth = float(ev.get("mouth_correlation", ev.get("mouth_viseme", 0.75)))
    ear = float(ev.get("ear_correlation", 0.8))
    eye = float(ev.get("eye_correlation", ev.get("existence_correlation", 0.82)))
    ventriloquism = 1.0 - mouth
    score = mouth * 0.4 + ear * 0.3 + eye * 0.3
    verdict = "truth" if score >= 0.72 and mouth >= 0.55 else "hold"
    markers: list[str] = []
    if mouth < 0.55:
        markers.append("mouth_mismatch")
    if ventriloquism > 0.4:
        markers.append("ventriloquism")
    return {
        "ok": True,
        "schema": "zocr-mouth-fusion/v1",
        "mouth_correlation": round(mouth, 4),
        "ear_correlation": round(ear, 4),
        "eye_correlation": round(eye, 4),
        "fusion_score": round(score, 4),
        "verdict": verdict,
        "lie_markers": markers,
        "rule": "Voice must originate from visible mouth when camera present",
    }


def final_mouth_status() -> dict[str, Any]:
    doc = load_final_spec()
    st = _load_state()
    mid = st.get("active_mode", "dishes")
    return {
        "schema": "zocr-final-mouth-status/v1",
        "ts": _ts(),
        "title": doc.get("title"),
        "active_mode": mid,
        "active_profile": st.get("active_profile"),
        "active_voice": st.get("active_voice"),
        "modes": list_modes(),
        "voice_fix": st.get("voice_fix"),
        "spectrum": analyze_vocal_spectrum(),
        "twins": doc.get("twins"),
        "rule": doc.get("rule"),
    }


def mouth_status() -> dict[str, Any]:
    return {
        "schema": "zocr-mouth-status/v1",
        "ts": _ts(),
        "engine": ENGINE,
        "active_profile": _load_state().get("active_profile"),
        "profiles": len(list_profiles()),
        "final_mouth": final_mouth_status(),
    }