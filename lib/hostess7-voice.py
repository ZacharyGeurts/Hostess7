#!/usr/bin/env pythong
"""Hostess 7 voice — American English female, high-quality spoken output."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

_SG = Path(os.environ.get("SG_ROOT", str(Path(__file__).resolve().parent.parent.parent)))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_SG / "NewLatest")))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "hostess7-voice-doctrine.json"
CHOICE = INSTALL / "data" / "hostess7-voice-choice.json"
PANEL = STATE / "hostess7-voice-panel.json"
SAMPLES = INSTALL / "data" / "hostess7-voice-samples"

ENABLED = os.environ.get("NEXUS_HOSTESS7_VOICE", os.environ.get("HOSTESS7_VOICE", "1")) not in ("0", "false", "no")


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


def _clean_speech_text(text: str) -> str:
    clean = re.sub(r"\033\[[0-9;]*m", "", text or "")
    clean = re.sub(r"`[^`]+`", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def _chunk_text(text: str, *, max_chars: int = 420) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    buf: list[str] = []
    for w in words:
        buf.append(w)
        if len(" ".join(buf)) > max_chars:
            chunks.append(" ".join(buf[:-1]))
            buf = [w]
    if buf:
        chunks.append(" ".join(buf))
    return [c for c in chunks if len(c) >= 3]


def _piper_speak(chunk: str, *, voice_model: Path, out_wav: Path) -> bool:
    piper = shutil.which("piper")
    if not piper or not voice_model.is_file():
        return False
    try:
        proc = subprocess.run(
            [piper, "--model", str(voice_model), "--output_file", str(out_wav)],
            input=chunk,
            text=True,
            capture_output=True,
            check=False,
            timeout=90,
        )
        if proc.returncode != 0 or not out_wav.is_file():
            return False
        for player in ("aplay", "paplay", "ffplay"):
            play = shutil.which(player)
            if not play:
                continue
            args = [play, str(out_wav)] if player != "ffplay" else [play, "-nodisp", "-autoexit", str(out_wav)]
            subprocess.run(args, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        return out_wav.is_file()
    except (subprocess.TimeoutExpired, OSError):
        return False


def _spd_speak(chunk: str, *, voice: str, rate: int, pitch: int) -> bool:
    spd = shutil.which("spd-say")
    if not spd:
        return False
    subprocess.run(
        [spd, "-y", voice, "-r", str(rate), "-p", str(pitch), "-i", "en-US", chunk],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True


def _polish_module():
    py = INSTALL / "lib" / "hostess7-voice-polish.py"
    if not py.is_file():
        return None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7voicepolish", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _polish_thought(thought: str) -> dict[str, Any]:
    mod = _polish_module()
    if mod and hasattr(mod, "polish_for_voice"):
        return mod.polish_for_voice(thought)
    return {"ok": True, "thought": thought, "utterance": thought, "beyond_eloquence": False}


def _load_choice() -> dict[str, Any]:
    doc = _load(CHOICE, {})
    if doc.get("engine"):
        return doc
    doctrine = _load(DOCTRINE, {})
    default = (doctrine.get("sovereign_voice") or {}).get("default_choice") or {}
    return {
        "engine": default.get("engine") or "spd-say",
        "voice": default.get("voice") or "female2",
        "label": default.get("label") or "American female",
        "locale": doctrine.get("locale") or "en-US",
    }


def choose_voice(*, engine: str, voice: str | None = None, label: str | None = None) -> dict[str, Any]:
    """Hostess 7 chooses her one sovereign voice — no other engine speaks."""
    doctrine = _load(DOCTRINE, {})
    allowed = {str(e.get("id")): e for e in (doctrine.get("engines") or [])}
    eid = engine.strip().lower().replace("spd", "spd-say")
    if eid not in allowed:
        return {"ok": False, "error": "engine_not_allowed", "allowed": list(allowed)}
    eng = allowed[eid]
    doc = {
        "schema": "hostess7-voice-choice/v1",
        "chosen_by": "hostess7",
        "motto": "There is only one voice and it is the one she chooses.",
        "engine": eid,
        "voice": voice or str(eng.get("voice") or "female2"),
        "label": label or str(eng.get("label") or eid),
        "locale": doctrine.get("locale") or "en-US",
        "locked": True,
    }
    _save(CHOICE, doc)
    return {"ok": True, "choice": doc}


def _mouth_neural_prepare(thought: str) -> dict[str, Any]:
    mm = INSTALL / "lib" / "hostess7-mouth-neural.py"
    if not mm.is_file() or os.environ.get("NEXUS_HOSTESS7_MOUTH_NEURAL", "1") != "1":
        return {"ok": True, "utterance": thought, "thought_voice_alignment": 1.0, "skipped": True}
    try:
        proc = subprocess.run(
            [sys.executable, str(mm), "dispatch"],
            input=json.dumps({"action": "prepare", "thought": thought, "text": thought}),
            capture_output=True,
            text=True,
            timeout=45,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        doc = json.loads(proc.stdout or "{}")
        if doc.get("utterance"):
            return doc
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        pass
    return {"ok": True, "utterance": thought, "thought_voice_alignment": 1.0, "skipped": True}


def speak(text: str, *, save_sample: bool = True) -> dict[str, Any]:
    """Speak through polish → mouth field neural → her one chosen voice."""
    if not ENABLED:
        return {"ok": False, "error": "voice_disabled"}
    doctrine = _load(DOCTRINE, {})
    choice = _load_choice()
    polished = _polish_thought(_clean_speech_text(text))
    thought = str(polished.get("thought") or text)
    neural = _mouth_neural_prepare(str(polished.get("utterance") or thought))
    clean = _clean_speech_text(str(neural.get("utterance") or polished.get("utterance") or thought))
    if len(clean) < 3:
        return {"ok": False, "error": "text_too_short"}

    chunk_max = int(doctrine.get("chunk_max_chars") or 420)
    max_chunks = int(doctrine.get("max_chunks") or 16)
    chunks = _chunk_text(clean, max_chars=chunk_max)[:max_chunks]
    all_engines = {str(e.get("id")): e for e in (doctrine.get("engines") or [])}
    chosen_id = str(choice.get("engine") or "spd-say")
    engines = [all_engines[chosen_id]] if chosen_id in all_engines else list(all_engines.values())

    SAMPLES.mkdir(parents=True, exist_ok=True)
    piper_model = SAMPLES / "en_US-amy-medium.onnx"
    spoken = 0
    engine_used = None

    for chunk in chunks:
        ok = False
        for eng in engines:
            eid = str(eng.get("id") or "")
            if eid == "piper":
                wav = SAMPLES / f"utterance_{spoken:04d}.wav"
                ok = _piper_speak(chunk, voice_model=piper_model, out_wav=wav)
                if ok:
                    engine_used = "piper"
                    if save_sample:
                        try:
                            (SAMPLES / "latest.txt").write_text(chunk + "\n", encoding="utf-8")
                        except OSError:
                            pass
            elif eid in ("spd-say", "spd"):
                ok = _spd_speak(
                    chunk,
                    voice=str(choice.get("voice") or eng.get("voice") or "female2"),
                    rate=int(eng.get("rate") or -8),
                    pitch=int(eng.get("pitch") or 18),
                )
                if ok:
                    engine_used = engine_used or "spd-say"
            if ok:
                break
        if ok:
            spoken += 1

    out = {
        "ok": spoken > 0,
        "spoken_chunks": spoken,
        "total_chunks": len(chunks),
        "engine": engine_used,
        "sovereign_voice": choice,
        "locale": doctrine.get("locale") or "en-US",
        "gender": doctrine.get("gender") or "female",
        "quality": doctrine.get("quality") or "high",
        "thought": thought,
        "utterance": clean,
        "language": {
            "beyond_eloquence": polished.get("beyond_eloquence"),
            "iq_floor": polished.get("iq_floor"),
            "iq_tier": polished.get("iq_tier"),
        },
        "field_neural": {
            "thought_voice_alignment": neural.get("thought_voice_alignment"),
            "deception_risk": neural.get("deception_risk"),
            "top_label": neural.get("top_label"),
            "deception_possible": neural.get("deception_possible", True),
        },
    }
    _save(PANEL, {
        "schema": "hostess7-voice/v2",
        "enabled": ENABLED,
        "last_engine": engine_used,
        "sovereign_voice": choice,
        "last_locale": out["locale"],
        "last_spoken_chunks": spoken,
        "fluency_claim": doctrine.get("fluency_claim"),
        "motto": doctrine.get("motto"),
    })
    return out


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    panel = _load(PANEL, {})
    field_neural = doctrine.get("field_neural") or {}
    choice = _load_choice()
    doc = {
        "schema": "hostess7-voice/v2",
        "enabled": ENABLED,
        "motto": doctrine.get("motto"),
        "locale": doctrine.get("locale") or "en-US",
        "dialect": doctrine.get("dialect") or "american_english",
        "gender": doctrine.get("gender") or "female",
        "quality": doctrine.get("quality") or "high",
        "fluency_claim": doctrine.get("fluency_claim"),
        "sovereign_voice": choice,
        "language": doctrine.get("language"),
        "engines": doctrine.get("engines"),
        "sample_dir": str(SAMPLES),
        "piper_available": bool(shutil.which("piper")),
        "spd_available": bool(shutil.which("spd-say")),
        "last_engine": panel.get("last_engine"),
        "field_neural": {
            "voice_hemisphere": True,
            "deception_possible": field_neural.get("deception_possible", True),
            "thought_voice_alignment": "not_guaranteed",
            "mouth_neural_engine": field_neural.get("mouth_neural_engine"),
        },
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "speak":
        text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        result = speak(text)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok") else 1
    if cmd == "choose" and len(sys.argv) > 2:
        eng = sys.argv[2]
        voice = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(choose_voice(engine=eng, voice=voice), ensure_ascii=False))
        return 0
    if cmd == "polish" and len(sys.argv) > 2:
        print(json.dumps(_polish_thought(" ".join(sys.argv[2:])), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-voice.py [json|speak TEXT|choose ENGINE [VOICE]|polish TEXT]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())