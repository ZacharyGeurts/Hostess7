#!/usr/bin/env pythong
"""Broadcaster codec registry — all Field media codecs with FFmpeg encoder maps."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
CODEC_DOCTRINE = INSTALL / "data" / "field-media-codec-doctrine.json"

# FFmpeg encoder map — video id → (lib, extra flags)
VIDEO_FFMPEG: dict[str, dict[str, Any]] = {
    "h264": {"vcodec": "libx264", "preset": "veryfast", "tune": "zerolatency", "pix_fmt": "yuv420p"},
    "h265": {"vcodec": "libx265", "preset": "medium", "pix_fmt": "yuv420p"},
    "vp8": {"vcodec": "libvpx", "deadline": "realtime"},
    "vp9": {"vcodec": "libvpx-vp9", "deadline": "realtime", "cpu-used": "5"},
    "av1": {"vcodec": "libsvtav1", "preset": "8"},
    "theora": {"vcodec": "libtheora"},
    "mpeg2": {"vcodec": "mpeg2video"},
    "mpeg4": {"vcodec": "mpeg4"},
    "nvenc_h264": {"vcodec": "h264_nvenc", "preset": "p4", "tune": "ll"},
    "nvenc_hevc": {"vcodec": "hevc_nvenc", "preset": "p4", "tune": "ll"},
}

AUDIO_FFMPEG: dict[str, dict[str, Any]] = {
    "aac": {"acodec": "aac", "ar": "48000", "b:a": "160k"},
    "mp3": {"acodec": "libmp3lame", "ar": "48000", "b:a": "192k"},
    "opus": {"acodec": "libopus", "ar": "48000", "b:a": "128k"},
    "vorbis": {"acodec": "libvorbis", "ar": "48000", "b:a": "160k"},
    "flac": {"acodec": "flac", "ar": "48000"},
    "pcm": {"acodec": "pcm_s16le", "ar": "48000"},
    "ac3": {"acodec": "ac3", "ar": "48000", "b:a": "192k"},
}

CONTAINER_FFMPEG: dict[str, str] = {
    "mkv": "matroska",
    "mp4": "mp4",
    "webm": "webm",
    "flv": "flv",
    "mpeg": "mpegts",
    "ogg": "ogg",
    "mov": "mov",
}


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


def _nvenc_available() -> bool:
    if not shutil.which("ffmpeg"):
        return False
    try:
        proc = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return "h264_nvenc" in (proc.stdout or "")
    except (OSError, subprocess.TimeoutExpired):
        return False


def registry() -> dict[str, Any]:
    doc = _load(CODEC_DOCTRINE, {})
    nvenc = _nvenc_available()
    video = list(doc.get("video_codecs") or [])
    if nvenc:
        video = video + [
            {"id": "nvenc_h264", "label": "H.264 NVENC (RTX)", "browser_native": False, "containers": ["mp4", "mkv", "flv"]},
            {"id": "nvenc_hevc", "label": "HEVC NVENC (RTX)", "browser_native": False, "containers": ["mp4", "mkv"]},
        ]
    return {
        "schema": "field-broadcaster-codecs/v1",
        "doctrine": doc.get("schema"),
        "video_codecs": video,
        "audio_codecs": doc.get("audio_codecs") or [],
        "containers": doc.get("containers") or [],
        "nvenc_available": nvenc,
        "ffmpeg_present": bool(shutil.which("ffmpeg")),
        "streaming_default": {"video": "h264", "audio": "aac", "container": "flv"},
        "recording_default": {"video": "h264", "audio": "aac", "container": "mkv"},
    }


def video_encoder_args(codec_id: str, *, bitrate_kbps: int = 4500, keyframe_sec: int = 2) -> list[str]:
    cid = codec_id if codec_id in VIDEO_FFMPEG else "h264"
    spec = VIDEO_FFMPEG[cid]
    args = ["-c:v", str(spec["vcodec"])]
    if spec.get("preset"):
        args += ["-preset", str(spec["preset"])]
    if spec.get("tune"):
        args += ["-tune", str(spec["tune"])]
    if spec.get("pix_fmt"):
        args += ["-pix_fmt", str(spec["pix_fmt"])]
    if spec.get("deadline"):
        args += ["-deadline", str(spec["deadline"])]
    if spec.get("cpu-used"):
        args += ["-cpu-used", str(spec["cpu-used"])]
    if cid.startswith("nvenc"):
        args += ["-b:v", f"{bitrate_kbps}k", "-maxrate", f"{bitrate_kbps}k", "-bufsize", f"{bitrate_kbps * 2}k"]
    else:
        args += ["-b:v", f"{bitrate_kbps}k", "-maxrate", f"{bitrate_kbps}k", "-bufsize", f"{bitrate_kbps * 2}k"]
    args += ["-g", str(max(30, keyframe_sec * 30)), "-keyint_min", str(max(30, keyframe_sec * 30))]
    return args


def audio_encoder_args(codec_id: str) -> list[str]:
    cid = codec_id if codec_id in AUDIO_FFMPEG else "aac"
    spec = AUDIO_FFMPEG[cid]
    args: list[str] = []
    for key in ("acodec", "ar", "b:a"):
        if spec.get(key):
            flag = "-c:a" if key == "acodec" else f"-{key.replace(':', ':')}"
            if key == "acodec":
                args += ["-c:a", str(spec[key])]
            elif key == "ar":
                args += ["-ar", str(spec[key])]
            elif key == "b:a":
                args += ["-b:a", str(spec[key])]
    return args or ["-c:a", "aac", "-b:a", "160k", "-ar", "48000"]


def output_format_args(container: str) -> list[str]:
    fmt = CONTAINER_FFMPEG.get(container, container)
    return ["-f", fmt]


def posture() -> dict[str, Any]:
    return {"ok": True, **registry()}


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "registry"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-broadcaster-codecs.py [json|registry]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())