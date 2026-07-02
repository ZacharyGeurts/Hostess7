#!/usr/bin/env pythong
"""Hostess 7 ↔ Queen Final_Ear bridge — GAC1, secure identify, eye↔ear fusion."""
from __future__ import annotations

import json
import os
import struct
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SG = ROOT.parent


def queen_base() -> str:
    return os.environ.get("QUEEN_WORLD_URL", "http://127.0.0.1:9481").rstrip("/")


def earball_post(body: dict[str, Any], *, timeout: int = 120) -> dict[str, Any]:
    url = f"{queen_base()}/api/queen-earball"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, OSError):
            return {"ok": False, "error": f"http_{exc.code}"}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": "queen_unreachable", "detail": str(exc.reason)[:120]}


def sense_neural_post(body: dict[str, Any], *, timeout: int = 120) -> dict[str, Any]:
    url = f"{queen_base()}/api/sense-neural"
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        return {"ok": False, "error": "sense_neural_unreachable", "detail": str(exc.reason)[:120]}


def wav_to_pcm_hex(wav_path: Path) -> tuple[str, int, int]:
    with wave.open(str(wav_path), "rb") as wf:
        channels = wf.getnchannels()
        rate = wf.getframerate()
        if wf.getsampwidth() != 2:
            raise ValueError("wav_must_be_int16")
        frames = wf.readframes(wf.getnframes())
    return frames.hex(), rate, channels


def secure_identify_wav(
    wav_path: Path,
    *,
    mouth_correlation: float = 0.88,
    existence_correlation: float = 0.82,
) -> dict[str, Any]:
    pcm_hex, rate, channels = wav_to_pcm_hex(wav_path)
    return earball_post({
        "action": "eye_ear_fusion",
        "pcm_hex": pcm_hex,
        "evidence": {
            "mouth_correlation": mouth_correlation,
            "speech_present": True,
            "sovereign_time_ok": True,
            "provenance_weave_ok": True,
            "channels": channels,
            "sample_rate": rate,
        },
        "existence": {"correlation": existence_correlation},
        "localization": {"bearing_deg": 0},
    })


def listen_and_identify(*, seconds: int = 6) -> dict[str, Any]:
    """Capture via hostess7_voice, then secure identify through Queen."""
    from hostess7_voice import listen_once_capture  # noqa: WPS433

    cap = listen_once_capture(seconds=seconds)
    if not cap.get("ok"):
        return cap
    wav = Path(cap["wav_path"])
    try:
        out = secure_identify_wav(wav, mouth_correlation=0.9)
        out["hostess7"] = {"captured": True, "seconds": seconds, "whisper": cap.get("whisper_text")}
        return out
    finally:
        wav.unlink(missing_ok=True)


def gac1_status() -> dict[str, Any]:
    return earball_post({"action": "gac1"})


def sovereign_sync() -> dict[str, Any]:
    return earball_post({"action": "sovereign_time", "verify_sync": True})


def track_all_sounds(*, learn: bool = True) -> dict[str, Any]:
    return earball_post({"action": "sense_all", "learn": learn})


def follow_desktop(*, learn: bool = True) -> dict[str, Any]:
    return earball_post({"action": "desktop_audio", "follow": True, "learn": learn})


def bridge_status() -> dict[str, Any]:
    gac = gac1_status()
    sync = sovereign_sync()
    wire = sense_neural_post({"action": "status"})
    track = earball_post({"action": "sound_track"})
    return {
        "schema": "hostess7-final-ear-bridge/v1",
        "queen_base": queen_base(),
        "gac1": gac,
        "sovereign_sync": sync,
        "sense_neural": wire,
        "sound_tracker": track,
        "ok": gac.get("ok") is not False and sync.get("ok") is not False,
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip()
    if cmd == "status":
        print(json.dumps(bridge_status(), indent=2))
        return 0
    if cmd == "gac1":
        print(json.dumps(gac1_status(), indent=2))
        return 0
    if cmd == "sync":
        print(json.dumps(sovereign_sync(), indent=2))
        return 0
    if cmd == "identify" and len(sys.argv) > 2:
        print(json.dumps(secure_identify_wav(Path(sys.argv[2])), indent=2))
        return 0
    if cmd == "listen":
        print(json.dumps(listen_and_identify(seconds=int(sys.argv[2]) if len(sys.argv) > 2 else 6), indent=2))
        return 0
    if cmd == "track":
        print(json.dumps(track_all_sounds(), indent=2))
        return 0
    if cmd == "desktop":
        print(json.dumps(follow_desktop(), indent=2))
        return 0
    print("usage: field_final_ear_bridge.py status|gac1|sync|identify <wav>|listen [seconds]|track|desktop", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())