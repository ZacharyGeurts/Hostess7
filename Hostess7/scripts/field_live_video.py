#!/usr/bin/env pythong
"""Hostess7 live video — TTS + talking-head frames → Graphics window.

Pairs Language Expert replies with pixel frames (not ASCII).
Backends: local frame/GIF, future LivePortrait/MuseTalk, Grok Imagine for cinematic shots.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))

VIDEO_DIR = ROOT / "cache" / "fieldstorage" / "brain" / "imagine" / "video"
FRAMES_DIR = VIDEO_DIR / "frames"
STATE = VIDEO_DIR / "live_state.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure() -> None:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)


def live_video_plan() -> dict[str, Any]:
    """Pipeline Hostess7 uses to talk with video."""
    try:
        from field_imagine_corpus import (  # noqa: WPS433
            LIVE_VIDEO_ENTRIES,
            list_realtime_entries,
            recommend_live_backend,
        )
        rec = recommend_live_backend()
        realtime = list_realtime_entries()
        entry_count = len(LIVE_VIDEO_ENTRIES)
    except ImportError:
        rec = {"primary": "faster_liveportrait", "fallback": "musetalk", "why": ""}
        realtime = []
        entry_count = 0

    return {
        "pipeline": [
            "1. Owner speaks in Talk window",
            "2. Language Expert shapes text reply (field_talk_language)",
            "3. TTS audio — HOSTESS7_VOICE=1 / hostess7_voice.py (kokoro/piper/edge-tts)",
            "4. Lip-sync — HOSTESS7_LIVE_VIDEO_BACKEND (default: faster_liveportrait → MuseTalk → gfx_placeholder)",
            "5. Frames → field_gfx_canvas.present() — Graphics window (GTK pixels, not ASCII)",
            "6. Cinematic B-roll — Grok text_to_video / image_to_video (async, XAI_API_KEY)",
        ],
        "recommended": rec,
        "grok_imagine": {
            "image": "grok-imagine-image-quality — Hostess portrait base frame",
            "image_to_video": "grok-imagine-video-1.5 — animate still → video (6–15s), async poll",
            "text_to_video": "grok-imagine-video — text prompt → video up to 15s",
            "reference_to_video": "grok-imagine-video — reference images guide motion (not frame-1 lock)",
            "env": "XAI_API_KEY",
            "docs": "https://docs.x.ai/docs/guides/image-generation",
        },
        "open_source_realtime": {
            "faster_liveportrait": "https://github.com/warmshao/FasterLivePortrait — 30+ FPS TensorRT, JoyVASA audio",
            "liveportrait": "https://github.com/KlingTeam/LivePortrait — ~12.8ms/frame, stitching/retarget",
            "musetalk": "https://github.com/TMElyralab/MuseTalk — real-time lip sync",
            "ditto": "https://github.com/antgroup/ditto-talkinghead — diffusion streaming",
            "teller": "arXiv:2503.18429 — 25 FPS autoregressive streaming (CVPR 2025)",
            "livatar": "arXiv:2507.18649 — 141 FPS flow matching (Hedra)",
            "rest": "arXiv:2512.11229 — diffusion streaming THG",
        },
        "papers_indexed": entry_count,
        "realtime_entries": [e.get("id") for e in realtime[:12]],
        "graphics": "Hostess7Graphics.sh — GTK pixel window (not ASCII)",
    }


def present_talk_frame(
    text: str,
    *,
    label: str = "Hostess 7",
    mood_rgb: tuple[int, int, int] = (140, 200, 255),
) -> dict[str, Any] | None:
    """Show a talk frame on Graphics window — text bubble + Hostess palette."""
    try:
        from field_gfx_canvas import open_canvas  # noqa: WPS433
    except ImportError:
        return None
    c = open_canvas()
    c.fill(12, 16, 24)
    # Face placeholder circle (until LivePortrait wired)
    cx, cy, r = c.width // 2, c.height // 3, min(120, c.width // 6)
    for y in range(cy - r, cy + r):
        for x in range(cx - r, cx + r):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                c.pixel(x, y, 220, 190, 170)
    c.rect(24, cy + r + 20, c.width - 48, 120, 28, 34, 48)
    c.text(40, cy + r + 36, label, mood_rgb, size=20)
    # Word-wrap-ish via multiple text lines
    words = text.split()
    line, y_t = "", cy + r + 64
    for w in words:
        trial = (line + " " + w).strip()
        if len(trial) > 48:
            c.text(40, y_t, line, (230, 235, 245), size=15)
            line = w
            y_t += 22
        else:
            line = trial
    if line:
        c.text(40, y_t, line[:80], (230, 235, 245), size=15)
    c.text(16, c.height - 28, "LIVE · Graphics window · Imagine + lip-sync path", (100, 110, 130), size=12)
    return c.present(label=f"talk: {text[:40]}")


def present_image_frame(path: Path, *, caption: str = "") -> dict[str, Any] | None:
    """Blit a video frame or image to Graphics window."""
    try:
        from field_gfx_canvas import open_canvas  # noqa: WPS433
    except ImportError:
        return None
    if not path.is_file():
        return present_talk_frame(f"(missing {path.name})")
    c = open_canvas()
    c.fill(8, 10, 14)
    c.blit_image(0, 0, path, max_w=c.width)
    if caption:
        c.text(16, 16, caption[:80], (255, 255, 255), size=16)
    return c.present(label=caption or path.name)


def extract_video_frame(video: Path, *, frame_index: int = 0) -> Path | None:
    """ffmpeg single frame → PNG for Graphics window."""
    _ensure()
    out = FRAMES_DIR / f"{video.stem}_f{frame_index}.png"
    if out.is_file():
        return out
    try:
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(video),
                "-vf", f"select=eq(n\\,{frame_index})",
                "-vframes", "1", str(out),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        return out if out.is_file() else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _voice_enabled() -> bool:
    if os.environ.get("HOSTESS7_VOICE", "") in ("0", "false", "no"):
        return False
    if os.environ.get("NEXUS_HOSTESS7_VOICE", "") in ("0", "false", "no"):
        return False
    if os.environ.get("HOSTESS7_TALK", "") in ("1", "true", "yes"):
        return True
    return os.environ.get("HOSTESS7_VOICE", os.environ.get("NEXUS_HOSTESS7_VOICE", "1")) not in (
        "0",
        "false",
        "no",
    )


def _polish_for_speak(text: str) -> str:
    polish_py = ROOT.parent / "lib" / "hostess7-voice-polish.py"
    if not polish_py.is_file():
        return text[:500]
    try:
        proc = subprocess.run(
            [sys.executable, str(polish_py), text[:1200]],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(ROOT.parent),
                "NEXUS_STATE_DIR": str(ROOT.parent / ".nexus-state"),
            },
        )
        doc = json.loads(proc.stdout or "{}")
        return str(doc.get("utterance") or text)[:500]
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return text[:500]


def sync_talk_reply(text: str) -> dict[str, Any]:
    """Called after Language Expert reply — push frame + sovereign voice speak."""
    _ensure()
    frame_state = present_talk_frame(text)
    voice = _voice_enabled()
    if voice:
        voice_script = ROOT / "scripts" / "hostess7_voice.py"
        if voice_script.is_file():
            try:
                spoken = _polish_for_speak(text)
                subprocess.Popen(
                    [sys.executable, str(voice_script), "speak", spoken],
                    cwd=ROOT,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env={
                        **os.environ,
                        "NEXUS_INSTALL_ROOT": str(ROOT.parent),
                        "NEXUS_STATE_DIR": str(ROOT.parent / ".nexus-state"),
                        "HOSTESS7_VOICE": "1",
                    },
                )
            except OSError:
                pass
    state = {
        "updated": _ts(),
        "text_preview": text[:200],
        "frame": frame_state,
        "voice": voice,
        "backend": os.environ.get("HOSTESS7_LIVE_VIDEO_BACKEND", "gfx_placeholder"),
    }
    STATE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return state


def format_plan() -> str:
    plan = live_video_plan()
    lines = ["=== Hostess7 live video plan ===", ""]
    for step in plan["pipeline"]:
        lines.append(step)
    lines.append("")
    lines.append("Grok Imagine:")
    for k, v in plan["grok_imagine"].items():
        lines.append(f"  {k}: {v}")
    lines.append("")
    lines.append("Open-source realtime:")
    for k, v in plan["open_source_realtime"].items():
        lines.append(f"  {k}: {v}")
    return "\n".join(lines)


def main() -> int:
    _ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if cmd in ("plan", "pipeline"):
        print(format_plan())
        print("OK live-video-plan")
        return 0
    if cmd == "demo":
        st = sync_talk_reply(
            "Hi — I'm learning Grok Imagine and live video so I can talk with you face-to-face in the Graphics window."
        )
        print(json.dumps(st, indent=2))
        print("OK live-video-demo")
        return 0
    if cmd == "frame" and len(sys.argv) > 2:
        st = present_image_frame(Path(sys.argv[2]))
        print(json.dumps(st or {}, indent=2))
        return 0
    print("Usage: field_live_video.py [plan|demo|frame path]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())