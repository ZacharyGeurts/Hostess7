#!/usr/bin/env pythong
"""Hostess 7 voice — American English female, high quality (delegates to lib/hostess7-voice.py)."""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT.parent)))


def voice_enabled() -> bool:
    return os.environ.get("HOSTESS7_VOICE", os.environ.get("NEXUS_HOSTESS7_VOICE", "1")) not in ("0", "false", "no")


def _voice_mod():
    py = INSTALL / "lib" / "hostess7-voice.py"
    if not py.is_file():
        py = ROOT.parent / "lib" / "hostess7-voice.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("h7voice", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def speak(text: str) -> int:
    if not voice_enabled():
        return 0
    mod = _voice_mod()
    if mod and hasattr(mod, "speak"):
        return 0 if mod.speak(text).get("ok") else 1
    return 1


def listen_once_capture(*, seconds: int = 6) -> dict:
    """Capture WAV; optional whisper transcript. Used by Final_Ear secure path."""
    if os.environ.get("HOSTESS7_LISTEN", "1") in ("0", "false", "no"):
        return {"ok": False, "error": "listen_disabled"}
    arecord = shutil.which("arecord")
    if not arecord:
        return {"ok": False, "error": "arecord_missing"}
    wav = Path(tempfile.gettempdir()) / f"hostess7_listen_{os.getpid()}.wav"
    try:
        subprocess.run(
            [arecord, "-q", "-d", str(seconds), "-f", "cd", "-t", "wav", str(wav)],
            check=False,
        )
        if not wav.is_file() or wav.stat().st_size < 1000:
            return {"ok": False, "error": "capture_empty"}
        whisper_text = None
        whisper = shutil.which("whisper")
        if whisper:
            subprocess.run(
                [whisper, str(wav), "--language", "en", "--output_format", "txt",
                 "--output_dir", str(wav.parent)],
                capture_output=True,
                text=True,
                check=False,
            )
            txt_path = wav.with_suffix(".txt")
            if txt_path.is_file():
                whisper_text = txt_path.read_text(encoding="utf-8").strip() or None
                txt_path.unlink(missing_ok=True)
        return {"ok": True, "wav_path": str(wav), "whisper_text": whisper_text, "seconds": seconds}
    except OSError as exc:
        return {"ok": False, "error": str(exc)[:120]}


def listen_once(*, seconds: int = 6) -> str | None:
    """Try offline-ish capture; whisper if installed, else None (caller uses typed input)."""
    cap = listen_once_capture(seconds=seconds)
    if not cap.get("ok"):
        return None
    text = cap.get("whisper_text")
    wav = Path(cap["wav_path"])
    final_ear = os.environ.get("HOSTESS7_FINAL_EAR", "0") not in ("0", "false", "no")
    if final_ear and wav.is_file():
        try:
            sys.path.insert(0, str(ROOT / "scripts"))
            from field_final_ear_bridge import secure_identify_wav  # noqa: WPS433

            secure_identify_wav(wav)
        except Exception:
            pass
    wav.unlink(missing_ok=True)
    return text


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: hostess7_voice.py speak <text> | listen", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "speak":
        return speak(" ".join(sys.argv[2:]))
    if cmd == "listen":
        text = listen_once()
        if text:
            print(text)
            return 0
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())