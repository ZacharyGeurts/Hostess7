#!/usr/bin/env python3
"""Vintage Audio Composite — every CHIPS sound card, every format, live HDMI sink.

Decodes MP4/MP3/WAV/FLAC/OGG/M4A/WebM/MKV/… via ffmpeg, resamples to the selected
card's native profile (SB16 44.1k stereo, Covox 22k mono 8-bit, etc.), and plays
through PipeWire to the live sink (NVIDIA HDMI pro-audio by default).
"""
from __future__ import annotations

import importlib.util
import json
import math
import re
import shutil
import struct
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fcc", _LIB / "field-chamber-core.py")
fcc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(fcc)

INSTALL = fcc.INSTALL
STATE = fcc.STATE
DRIVERS = INSTALL / "data" / "field-vintage-audio-drivers.json"
CHIPS_SOUND = INSTALL / "library/dewey/621-computer-engineering/chips-catalog/ironclad-chips-catalog/pages/page-016-sound.json"
ACTIVE_PATH = STATE / "field-vintage-audio-active.json"
PANEL_PATH = STATE / "field-vintage-audio-panel.json"
TEST_TUNE_PATH = STATE / "field-audio-test-tune.wav"

# Pleasant Queen field test motif — C major arpeggio with a short resolve.
TEST_MELODY: list[tuple[float, float]] = [
    (261.63, 0.30), (329.63, 0.30), (392.00, 0.30), (523.25, 0.45),
    (392.00, 0.22), (329.63, 0.28), (440.00, 0.30), (349.23, 0.28),
    (392.00, 0.30), (523.25, 0.55), (659.25, 0.35), (523.25, 0.65),
]

# Anything ffmpeg/libav can demux/decode — video containers included (audio track only).
INPUT_FORMATS = (
    "wav", "wave", "flac", "mp3", "ogg", "opus", "oga", "ogv", "m4a", "aac",
    "mp4", "m4v", "mov", "mkv", "webm", "avi", "wmv", "flv", "3gp", "ts", "m2ts",
    "aiff", "aif", "wma", "ape", "wv", "tta", "ac3", "dts", "amr", "mid", "midi",
)

DUMMY_PATTERNS = ("auto_null", "null", "dummy")
PAPLAY_NATIVE = frozenset({
    "wav", "wave", "flac", "ogg", "oga", "opus", "aiff", "aif", "voc", "au", "snd",
})


def _load(path: Path, default: Any = None) -> Any:
    return fcc.load(path, default if default is not None else {})


def _run(cmd: list[str], *, timeout: float = 120.0, stdin_data: bytes | None = None) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        out = ((proc.stdout or b"") + (proc.stderr or b"")).decode("utf-8", errors="replace").strip()
        return proc.returncode, out
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def _is_dummy(name: str) -> bool:
    low = name.lower()
    return any(p in low for p in DUMMY_PATTERNS)


def _live_sink() -> str:
    sink = fcc.default_device("sink")
    if sink and not _is_dummy(sink):
        return sink
    hdmi = fcc.mod("hdmi_drv", "field-hdmi-audio-driver.py")
    if hdmi and hasattr(hdmi, "bind"):
        result = hdmi.bind(force=True)
        if result.get("ok"):
            return str(result.get("sink_name") or sink)
    return sink


def _drivers_doc() -> dict[str, Any]:
    return _load(DRIVERS, {"cards": [], "families": {}, "chips_to_family": {}})


def _family_profile(family_id: str) -> dict[str, Any]:
    fam = (_drivers_doc().get("families") or {}).get(family_id) or {}
    bits = int(fam.get("bits") or 16)
    channels = int(fam.get("channels") or 2)
    rate = int(fam.get("default_rate") or 44100)
    fmt = "u8" if bits <= 8 else ("s16" if bits <= 16 else "s32")
    return {
        "family": family_id,
        "label": fam.get("label", family_id),
        "sample_rate": rate,
        "channels": channels,
        "bits": bits,
        "sample_fmt": fmt,
        "synthesis": fam.get("synthesis", "dac"),
        "bus": fam.get("bus", ""),
    }


def _enrich_card(card: dict[str, Any]) -> dict[str, Any]:
    fam_id = str(card.get("family") or "sb16_dma")
    prof = _family_profile(fam_id)
    chips_map = _drivers_doc().get("chips_to_family") or {}
    chip_families = {cid: chips_map.get(cid, fam_id) for cid in (card.get("chips") or [])}
    return {
        **card,
        "driver_family": fam_id,
        "profile": prof,
        "chip_families": chip_families,
        "playback": {
            "engine": "ffmpeg → paplay/pw-play",
            "formats_in": list(INPUT_FORMATS),
            "route": "live_sink",
        },
    }


def cards() -> list[dict[str, Any]]:
    return [_enrich_card(c) for c in (_drivers_doc().get("cards") or [])]


def card_by_id(card_id: str) -> dict[str, Any] | None:
    for c in cards():
        if c.get("id") == card_id:
            return c
    return None


def _chips_sound_ids() -> list[str]:
    doc = _load(CHIPS_SOUND, {})
    return list(doc.get("chip_ids") or [])


def composite_layout() -> dict[str, Any]:
    doc = _drivers_doc()
    chips_ids = _chips_sound_ids()
    chips_map = doc.get("chips_to_family") or {}
    families = doc.get("families") or {}
    matrix: list[dict[str, Any]] = []
    for chip_id in chips_ids:
        fam = chips_map.get(chip_id, "arcade_pcm")
        matrix.append({
            "chip_id": chip_id,
            "family": fam,
            "family_label": (families.get(fam) or {}).get("label", fam),
            "cards": [c["id"] for c in cards() if chip_id in (c.get("chips") or [])],
        })
    return {
        "chips_sound_count": len(chips_ids),
        "family_count": len(families),
        "card_count": len(cards()),
        "chips_matrix": matrix,
        "families": families,
        "input_formats": list(INPUT_FORMATS),
    }


def active_card() -> dict[str, Any]:
    saved = _load(ACTIVE_PATH, {})
    cid = str(saved.get("card_id") or "nvidia-hdmi-pro")
    card = card_by_id(cid) or card_by_id("host-live") or (cards()[0] if cards() else {})
    return {"card_id": card.get("id", cid), "card": card, "saved": saved}


def select_card(card_id: str) -> dict[str, Any]:
    card = card_by_id(card_id)
    if not card:
        return {"ok": False, "error": "card_not_found", "card_id": card_id}
    sink = _live_sink()
    doc = {
        "schema": "field-vintage-audio-active/v1",
        "updated": fcc.ts(),
        "card_id": card_id,
        "card_name": card.get("name"),
        "family": card.get("family"),
        "profile": card.get("profile"),
        "sink": sink,
    }
    fcc.save_atomic(ACTIVE_PATH, doc)
    settings = STATE / "field-audio-settings.json"
    s = _load(settings, {})
    s["soundcard_id"] = card_id
    fcc.save_atomic(settings, s)
    dac = STATE / "field-audio-dac-settings.json"
    d = _load(dac, {})
    if sink:
        d["output_device"] = sink
    fcc.save_atomic(dac, d)
    return {"ok": True, **doc}


def _player_cmd(sink: str) -> list[str]:
    if shutil.which("pw-play"):
        return ["pw-play", f"--target={sink}"] if sink else ["pw-play"]
    return ["paplay", f"--device={sink}"] if sink else ["paplay"]


def _gstreamer_play(
    src: Path,
    *,
    profile: dict[str, Any],
    sink: str,
    duration_sec: float = 0.0,
) -> tuple[int, str, list[dict[str, Any]]]:
    """Decode any media (MP4/MP3/…) and route audio to Pulse/PipeWire sink."""
    if not shutil.which("gst-launch-1.0"):
        return 1, "gstreamer_missing", []
    rate = int(profile.get("sample_rate") or 44100)
    ch = int(profile.get("channels") or 2)
    bits = int(profile.get("bits") or 16)
    fmt = "S16LE" if bits <= 16 else "S32LE"
    if bits <= 8:
        fmt = "S8"
    uri = src.as_uri()
    pulse_device = sink or ""
    sink_props = f'device="{pulse_device}"' if pulse_device else ""
    # decodebin handles MP4/MKV/WebM/MP3/… — video track ignored downstream of audioconvert.
    pipeline = (
        f'playbin uri="{uri}" flags=0x000002 '
        f'audio-sink="pulsesink {sink_props} '
        f'" ! queue ! audioconvert ! audioresample ! '
        f'audio/x-raw,rate={rate},channels={ch},format={fmt} ! '
        f'pulsesink {sink_props}"'
    )
    # playbin is simpler and handles A/V demux internally.
    simple = [
        "gst-launch-1.0", "-q", "playbin",
        f"uri={uri}",
        "flags=0x02",
        "audio-sink=pulsesink",
    ]
    if pulse_device:
        simple[-1] = f"audio-sink=pulsesink device={pulse_device}"
    if duration_sec > 0 and shutil.which("timeout"):
        simple = ["timeout", f"{max(1, int(duration_sec))}s"] + simple
        code, detail = _run(simple, timeout=duration_sec + 8.0)
        if code == 124:
            code = 0
            detail = f"played {duration_sec}s"
    else:
        code, detail = _run(simple, timeout=300.0)
    steps = [{"op": "gstreamer_playbin", "ok": code == 0, "detail": detail[:250]}]
    if code != 0:
        # Fallback explicit decode pipeline.
        pipe2 = [
            "gst-launch-1.0", "-q",
            "filesrc", f"location={src}",
            "!", "decodebin", "!", "audioconvert", "!", "audioresample", "!",
            f"audio/x-raw,rate={rate},channels={ch},format={fmt}", "!",
            "pulsesink",
        ]
        if pulse_device:
            pipe2.append(f"device={pulse_device}")
        code2, detail2 = _run(pipe2, timeout=300.0)
        steps.append({"op": "gstreamer_decodebin", "ok": code2 == 0, "detail": detail2[:250]})
        return code2, detail2, steps
    return code, detail, steps


def _ffmpeg_decode_cmd(
    src: Path,
    *,
    profile: dict[str, Any],
    sink_fmt: str = "s16le",
) -> list[str]:
    rate = int(profile.get("sample_rate") or 44100)
    ch = int(profile.get("channels") or 2)
    bits = int(profile.get("bits") or 16)
    if bits <= 8:
        af_fmt = "u8"
        pipe_fmt = "u8"
    elif bits <= 16:
        af_fmt = "s16"
        pipe_fmt = "s16le"
    else:
        af_fmt = "s32"
        pipe_fmt = "s32le"
    # Downmix/upmix + rate convert to card-native profile; strip video (-vn).
    return [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-vn", "-sn", "-dn",
        "-ac", str(ch),
        "-ar", str(rate),
        "-sample_fmt", af_fmt,
        "-f", pipe_fmt,
        "pipe:1",
    ]


def play_media(
    path: str | Path,
    *,
    card_id: str = "",
    sink: str = "",
    duration_sec: float = 0.0,
) -> dict[str, Any]:
    src = Path(path).expanduser().resolve()
    if not src.is_file():
        return {"ok": False, "error": "file_not_found", "path": str(src)}

    act = active_card() if not card_id else {"card": card_by_id(card_id) or {}}
    card = act.get("card") or {}
    if card_id and not card:
        return {"ok": False, "error": "card_not_found", "card_id": card_id}
    if not card:
        card = card_by_id("nvidia-hdmi-pro") or card_by_id("host-live") or {}

    profile = card.get("profile") or _family_profile(str(card.get("family") or "live_hdmi"))
    target_sink = sink or _live_sink()
    if _is_dummy(target_sink):
        hdmi = fcc.mod("hdmi_drv", "field-hdmi-audio-driver.py")
        if hdmi and hasattr(hdmi, "bind"):
            bound = hdmi.bind(force=True)
            if bound.get("ok"):
                target_sink = str(bound.get("sink_name") or target_sink)

    ext = src.suffix.lower().lstrip(".")
    steps: list[dict[str, Any]] = []

    # GStreamer: universal decode (MP4/MKV/MP3/…) without ffmpeg.
    needs_decoder = ext not in PAPLAY_NATIVE
    if shutil.which("gst-launch-1.0"):
        gs_code, gs_detail, gs_steps = _gstreamer_play(
            src, profile=profile, sink=target_sink, duration_sec=float(duration_sec or 0),
        )
        steps.extend(gs_steps)
        if gs_code == 0:
            return {
                "ok": True,
                "path": str(src),
                "format": ext,
                "card_id": card.get("id"),
                "card_name": card.get("name"),
                "family": card.get("family"),
                "sink": target_sink,
                "profile": profile,
                "mode": "gstreamer",
                "duration_sec": duration_sec or None,
                "steps": steps,
            }
        if needs_decoder:
            return {
                "ok": False,
                "error": "gstreamer_decode_failed",
                "path": str(src),
                "format": ext,
                "card_id": card.get("id"),
                "card_name": card.get("name"),
                "sink": target_sink,
                "profile": profile,
                "steps": steps,
                "detail": gs_detail[:300],
            }

    # ffmpeg pipe path when available (finer card-profile resample).
    if not shutil.which("ffmpeg"):
        if needs_decoder:
            return {
                "ok": False,
                "error": "decoder_missing",
                "path": str(src),
                "format": ext,
                "hint": "Need gstreamer or ffmpeg for MP4/MP3/MKV",
                "steps": steps,
            }
        player = _player_cmd(target_sink)
        code, detail = _run(player + [str(src)], timeout=180.0)
        steps.append({"op": "direct_play", "player": player[0], "ok": code == 0, "detail": detail[:200]})
        return {
            "ok": code == 0,
            "path": str(src),
            "card_id": card.get("id"),
            "card_name": card.get("name"),
            "sink": target_sink,
            "profile": profile,
            "mode": "direct",
            "steps": steps,
            "error": None if code == 0 else "decode_failed",
        }

    ff_cmd = _ffmpeg_decode_cmd(src, profile=profile)
    player = _player_cmd(target_sink)
    try:
        ff_proc = subprocess.Popen(
            ff_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        pl_proc = subprocess.Popen(
            player,
            stdin=ff_proc.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if ff_proc.stdout:
            ff_proc.stdout.close()
        _, pl_err = pl_proc.communicate(timeout=180)
        ff_err = b""
        if ff_proc.stderr:
            ff_err = ff_proc.stderr.read() or b""
        ff_code = ff_proc.wait(timeout=5)
        pl_code = pl_proc.returncode
        detail = (ff_err + pl_err).decode("utf-8", errors="replace")[:300]
        steps.append({
            "op": "ffmpeg_decode",
            "cmd": " ".join(ff_cmd[:8]) + "…",
            "ok": ff_code == 0 or pl_code == 0,
            "detail": detail,
        })
        steps.append({"op": "pipe_play", "player": player[0], "sink": target_sink, "ok": pl_code == 0})
        ok = pl_code == 0 and (ff_code == 0 or pl_code == 0)
        return {
            "ok": ok,
            "path": str(src),
            "format": ext,
            "card_id": card.get("id"),
            "card_name": card.get("name"),
            "family": card.get("family"),
            "sink": target_sink,
            "profile": profile,
            "mode": "ffmpeg_pipe",
            "steps": steps,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": "playback_failed", "detail": str(exc), "path": str(src)}


def ensure_test_tune(*, force: bool = False) -> Path:
    """Synthesize a short stereo WAV test tune (stdlib only)."""
    TEST_TUNE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TEST_TUNE_PATH.is_file() and not force and TEST_TUNE_PATH.stat().st_size > 2000:
        return TEST_TUNE_PATH
    rate = 44100
    gap = int(rate * 0.04)
    frames: list[int] = []
    for freq, dur_sec in TEST_MELODY:
        n = int(rate * dur_sec)
        for i in range(n):
            t = i / rate
            env = min(1.0, i / max(1, int(rate * 0.012)), (n - i) / max(1, int(rate * 0.06)))
            sample = int(12000 * env * math.sin(2.0 * math.pi * freq * t))
            frames.append(max(-32767, min(32767, sample)))
        frames.extend([0] * gap)
    with wave.open(str(TEST_TUNE_PATH), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(struct.pack(f"<{len(frames)}h", *frames))
    return TEST_TUNE_PATH


def test_tune(*, card_id: str = "", duration_sec: float = 0.0) -> dict[str, Any]:
    """Select card and play the built-in test melody through its profile."""
    cid = card_id or (_load(ACTIVE_PATH, {}).get("card_id") or "nvidia-hdmi-pro")
    if cid:
        select_card(cid)
    tune = ensure_test_tune()
    dur = duration_sec or sum(d for _, d in TEST_MELODY) + 0.5
    result = play_media(tune, card_id=cid, duration_sec=dur)
    result["test_tune"] = str(tune)
    result["action"] = "test_tune"
    return result


def cards_by_vendor() -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for card in cards():
        vendor = str(card.get("vendor") or "Other")
        groups.setdefault(vendor, []).append({
            "id": card.get("id"),
            "name": card.get("name"),
            "era": card.get("era"),
            "bus": card.get("bus"),
            "family": card.get("family"),
            "live": bool(card.get("live")),
            "chips": card.get("chips") or [],
        })
    return [
        {"vendor": vendor, "cards": sorted(rows, key=lambda c: str(c.get("name") or ""))}
        for vendor, rows in sorted(groups.items(), key=lambda x: (x[0] == "Host", x[0]))
    ]


def catalog() -> dict[str, Any]:
    doc = _drivers_doc()
    layout = composite_layout()
    act = active_card()
    return {
        "ok": True,
        "schema": "field-vintage-audio-composite/v1",
        "updated": fcc.ts(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "playback": {
            **(doc.get("playback") or {}),
            "formats_in": list(INPUT_FORMATS),
            "note": "MP4/MKV/WebM video files play audio track through any card profile",
        },
        "active": act,
        "default_sink": _live_sink(),
        "cards": cards(),
        "card_count": len(cards()),
        "composite": layout,
        "ffmpeg_available": bool(shutil.which("ffmpeg")),
        "gstreamer_available": bool(shutil.which("gst-launch-1.0")),
    }


def posture() -> dict[str, Any]:
    cat = catalog()
    doc = {
        "ok": True,
        "schema": "field-vintage-audio-panel/v1",
        "updated": fcc.ts(),
        "catalog": cat,
        "routes": {
            "catalog": "/api/field-vintage-audio",
            "select": "/api/field-vintage-audio/select",
            "play": "/api/field-vintage-audio/play",
            "layout": "/api/field-vintage-audio/layout",
        },
        "posture": (
            f"Vintage composite — {cat.get('card_count', 0)} cards · "
            f"active {cat.get('active', {}).get('card_id', '?')} · "
            f"ffmpeg={'yes' if cat.get('ffmpeg_available') else 'no'}"
        ),
    }
    fcc.save_atomic(PANEL_PATH, doc)
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture", "catalog"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "layout":
        print(json.dumps(composite_layout(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "cards":
        print(json.dumps({"ok": True, "cards": cards()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "select":
        cid = sys.argv[2] if len(sys.argv) > 2 else "sb16"
        print(json.dumps(select_card(cid), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("test_tune", "test", "tune"):
        cid = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else ""
        print(json.dumps(test_tune(card_id=cid), ensure_ascii=False, indent=2))
        return 0
    if cmd == "make_tune":
        print(json.dumps({"ok": True, "path": str(ensure_test_tune(force="--force" in sys.argv))}, ensure_ascii=False))
        return 0
    if cmd == "play":
        if len(sys.argv) < 3:
            print(json.dumps({"error": "usage: play PATH [card_id] [--seconds=N]"}, ensure_ascii=False))
            return 1
        cid = ""
        dur = 0.0
        for arg in sys.argv[3:]:
            if arg.startswith("--seconds="):
                dur = float(arg.split("=", 1)[1])
            elif not arg.startswith("--"):
                cid = arg
        print(json.dumps(play_media(sys.argv[2], card_id=cid, duration_sec=dur), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-vintage-audio-composite.py [json|layout|cards|select ID|play PATH [card_id]]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())