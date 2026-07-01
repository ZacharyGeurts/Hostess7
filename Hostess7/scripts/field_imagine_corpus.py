#!/usr/bin/env pythong
"""Grok Imagine + live talking-video corpus — papers, GitHub, API paths for Hostess7."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "imagine" / "corpus.json"
REGISTRY = ROOT / "cache" / "fieldstorage" / "brain" / "imagine" / "live_video_registry.json"
CORPUS_VERSION = 3

# Grok Imagine workflow (from xAI docs + Imagine skill)
IMAGINE_WORKFLOW: tuple[dict[str, str], ...] = (
    {
        "id": "imagine_overview",
        "title": "Grok Imagine API",
        "body": (
            "xAI Imagine: image generation, image edit (up to 3 references), image-to-video, "
            "text-to-video, video edit, reference-to-video, video extension. "
            "Models: grok-imagine-image-quality, grok-imagine-video-1.5, grok-imagine-video. "
            "Docs: https://docs.x.ai/docs/guides/image-generation · API: https://api.x.ai/v1"
        ),
    },
    {
        "id": "imagine_image_gen",
        "title": "Image generation",
        "body": (
            "POST /v1/images/generations — text prompt → image. "
            "Use for invented subjects, scenes, base frames. "
            "Named real people: reference-first with image edit, not pure generation."
        ),
    },
    {
        "id": "imagine_image_edit",
        "title": "Image editing",
        "body": (
            "POST /v1/images/edits — source URL or base64 + prompt. "
            "Up to 3 reference images for compositing. "
            "Reuse one base image for character consistency across shots."
        ),
    },
    {
        "id": "imagine_image_to_video",
        "title": "Image-to-video (shot workflow)",
        "body": (
            "Video starts from an image — no text-only video. "
            "Plan shots: image_gen/edit per shot → image_to_video (6s or 10s). "
            "Prompt: one vivid moment, present tense, single camera move. "
            "Async: poll request_id until status=done. "
            "Assemble with ffmpeg concat -c copy (no re-encode)."
        ),
    },
    {
        "id": "imagine_video_gen",
        "title": "Text-to-video",
        "body": (
            "Generate video from text with duration (up to 15s), aspect ratio, resolution. "
            "grok-imagine-video-1.5 for image-to-video; grok-imagine-video for reference-to-video."
        ),
    },
    {
        "id": "imagine_hostess7_path",
        "title": "Hostess7 + Imagine path",
        "body": (
            "Talk window = language (Scholar). Graphics window = pixels. "
            "Live video path: (1) Hostess portrait base via image_edit with Owner-approved ref, "
            "(2) TTS audio per reply, (3) LivePortrait/MuseTalk/Ditto lip-sync frames, "
            "(4) present frames to Graphics window OR grok-imagine-video for cinematic shots. "
            "Charts/diagrams with exact text: build with HTML/CSS code, not image models."
        ),
    },
)

# Papers + GitHub for real-time / efficient talking heads
LIVE_VIDEO_ENTRIES: tuple[dict[str, Any], ...] = (
    {
        "id": "liveportrait",
        "title": "LivePortrait",
        "type": "github",
        "tags": ("real-time", "portrait", "audio-driven", "efficient", "lip-sync"),
        "arxiv": "2407.03168",
        "url": "https://github.com/KlingTeam/LivePortrait",
        "paper": "https://arxiv.org/abs/2407.03168",
        "speed": "~12.8ms/frame RTX 4090",
        "body": (
            "Efficient portrait animation — implicit keypoints, stitching/retargeting. "
            "Driving: video, audio, text, or template .pkl. Gradio app.py, inference.py. "
            "Best open path for Hostess7 live face on Graphics window."
        ),
    },
    {
        "id": "ditto",
        "title": "Ditto Talking Head",
        "type": "github",
        "tags": ("real-time", "streaming", "talking-head", "diffusion"),
        "arxiv": "2411.19509",
        "url": "https://github.com/antgroup/ditto-talkinghead",
        "paper": "https://arxiv.org/abs/2411.19509",
        "body": "Ant Group — real-time streaming talking head; diffusion-based, low latency for live conversation.",
    },
    {
        "id": "musetalk",
        "title": "MuseTalk",
        "type": "github",
        "tags": ("real-time", "lip-sync", "audio-driven"),
        "url": "https://github.com/TMElyralab/MuseTalk",
        "body": "Real-time high quality lip sync — audio in, talking face out. Good TTS→face bridge.",
    },
    {
        "id": "wav2lip",
        "title": "Wav2Lip",
        "type": "github",
        "tags": ("lip-sync", "audio", "classic"),
        "arxiv": "2008.10010",
        "url": "https://github.com/Rudrabha/Wav2Lip",
        "paper": "https://arxiv.org/abs/2008.10010",
        "body": "Accurate lip-sync to any speech audio — baseline for Hostess7 voice+face pipeline.",
    },
    {
        "id": "sadtalker",
        "title": "SadTalker",
        "type": "github",
        "tags": ("talking-head", "audio", "3dmm"),
        "url": "https://github.com/OpenTalker/SadTalker",
        "body": "Single image + audio → talking head video. 3D motion coefficients; slower than LivePortrait.",
    },
    {
        "id": "omnitalker",
        "title": "OmniTalker",
        "type": "paper",
        "tags": ("real-time", "text-driven", "unified"),
        "arxiv": "2501.14646",
        "url": "https://humanaigc.github.io/omnitalker/",
        "paper": "https://arxiv.org/abs/2501.14646",
        "body": "Real-time text-driven talking head — unified framework for live speech synthesis + face.",
    },
    {
        "id": "liveavatar",
        "title": "LiveAvatar (Quark)",
        "type": "github",
        "tags": ("avatar", "streaming", "alibaba"),
        "url": "https://github.com/Alibaba-Quark/LiveAvatar",
        "body": "Alibaba Quark live avatar stack — streaming digital human for conversation UIs.",
    },
    {
        "id": "awesome_thg",
        "title": "Awesome Talking Head Generation",
        "type": "index",
        "tags": ("survey", "papers", "github-list"),
        "url": "https://github.com/harlanhong/awesome-talking-head-generation",
        "body": "Curated papers and repos for talking-head generation — keep Hostess7 registry updated from here.",
    },
    {
        "id": "grok_imagine_video_15",
        "title": "Grok Imagine Video 1.5",
        "type": "api",
        "tags": ("cloud", "image-to-video", "xai"),
        "url": "https://docs.x.ai/docs/guides/image-generation",
        "body": (
            "xAI grok-imagine-video-1.5 — animate still → video, 6–15s, async poll. "
            "Hostess cinematic shots; not sub-100ms live lip-sync — pair with LivePortrait for talk."
        ),
    },
    {
        "id": "faster_liveportrait",
        "title": "FasterLivePortrait",
        "type": "github",
        "tags": ("real-time", "portrait", "tensorrt", "onnx", "streaming"),
        "url": "https://github.com/warmshao/FasterLivePortrait",
        "speed": "30+ FPS RTX 3090 (full pipeline)",
        "body": (
            "TensorRT/ONNX LivePortrait — real-time camera + audio drive (JoyVASA, Kokoro TTS). "
            "Best GPU path when sub-100ms lip-sync matters for Hostess7 Graphics window."
        ),
    },
    {
        "id": "teller",
        "title": "Teller",
        "type": "paper",
        "tags": ("real-time", "streaming", "audio-driven", "autoregressive"),
        "arxiv": "2503.18429",
        "paper": "https://arxiv.org/abs/2503.18429",
        "speed": "25 FPS streaming",
        "body": (
            "CVPR 2025 — first autoregressive real-time streaming audio-driven portrait. "
            "0.92s per second of video vs Hallo 20.93s. Facial + body detail via ETM."
        ),
    },
    {
        "id": "livatar",
        "title": "Livatar-1",
        "type": "paper",
        "tags": ("real-time", "audio-driven", "flow-matching", "hedra"),
        "arxiv": "2507.18649",
        "paper": "https://arxiv.org/abs/2507.18649",
        "url": "https://h-liu1997.github.io/Livatar-1/",
        "speed": "141 FPS · 0.17s latency A10",
        "body": "Hedra flow-matching talking heads — strong lip-sync (8.50 confidence HDTF) at real-time throughput.",
    },
    {
        "id": "rest",
        "title": "REST",
        "type": "paper",
        "tags": ("real-time", "streaming", "diffusion", "audio-driven"),
        "arxiv": "2512.11229",
        "paper": "https://arxiv.org/abs/2512.11229",
        "body": (
            "Diffusion-based real-time end-to-end streaming THG — ID-Context Cache + "
            "Asynchronous Streaming Distillation. State-of-the-art speed for diffusion talking heads."
        ),
    },
    {
        "id": "egstalkler",
        "title": "EGSTalker",
        "type": "paper",
        "tags": ("real-time", "audio-driven", "3dgs", "gaussian-splatting"),
        "arxiv": "2510.08587",
        "paper": "https://arxiv.org/abs/2510.08587",
        "body": "3D Gaussian Splatting talking head — 3–5 min training video, ESAA audio-spatial fusion, fast inference.",
    },
    {
        "id": "hallo",
        "title": "Hallo",
        "type": "github",
        "tags": ("audio-driven", "diffusion", "high-quality"),
        "arxiv": "2406.08801",
        "url": "https://github.com/fudan-generative-vision/hallo",
        "paper": "https://arxiv.org/abs/2406.08801",
        "body": "Fudan diffusion portrait animation — high quality but slower; baseline Teller/REST compare against.",
    },
    {
        "id": "hallo_live",
        "title": "Hallo-Live",
        "type": "github",
        "tags": ("real-time", "streaming", "audio-driven"),
        "url": "https://github.com/fudan-generative-vision/Hallo-Live",
        "body": "Fudan streaming variant of Hallo — closer to live conversation than batch Hallo.",
    },
    {
        "id": "personalive",
        "title": "PersonaLive",
        "type": "github",
        "tags": ("real-time", "portrait", "live-streaming", "expression"),
        "arxiv": "2512.11253",
        "url": "https://github.com/GVCLab/PersonaLive",
        "paper": "https://arxiv.org/abs/2512.11253",
        "body": "CVPR 2026 — expressive portrait animation for live streaming; image-driven reenactment at speed.",
    },
    {
        "id": "hunyuan_portrait",
        "title": "HunyuanPortrait",
        "type": "github",
        "tags": ("portrait", "animation", "implicit-control"),
        "arxiv": "2503.18860",
        "url": "https://github.com/kkakkkka/HunyuanPortrait",
        "paper": "https://arxiv.org/abs/2503.18860",
        "body": "CVPR 2025 implicit condition portrait animation — Tencent Hunyuan family.",
    },
    {
        "id": "flash_portrait",
        "title": "FlashPortrait",
        "type": "paper",
        "tags": ("real-time", "portrait", "infinite", "fast"),
        "arxiv": "2512.16900",
        "paper": "https://arxiv.org/abs/2512.16900",
        "body": "6× faster infinite portrait animation with adaptive latent prediction — long-form live sessions.",
    },
    {
        "id": "joyvasa",
        "title": "JoyVASA",
        "type": "github",
        "tags": ("audio-driven", "lip-sync", "liveportrait-addon"),
        "url": "https://github.com/jdh-algo/JoyVASA",
        "body": "Audio drives portrait via LivePortrait motion — used inside FasterLivePortrait for real-time talk.",
    },
    {
        "id": "actalker",
        "title": "ACTalker",
        "type": "paper",
        "tags": ("audio-driven", "expression", "portrait"),
        "url": "https://harlanhong.github.io/publications/actalker/index.html",
        "body": "ICCV 2025 — simultaneous audio + expression control for portrait video generation.",
    },
    {
        "id": "thg_survey_2025",
        "title": "Talking Head Survey 2025",
        "type": "survey",
        "tags": ("survey", "papers", "metrics"),
        "arxiv": "2507.02900",
        "paper": "https://arxiv.org/abs/2507.02900",
        "body": "Comprehensive survey of multi-modal talking-head methods, datasets, metrics — map the field.",
    },
    {
        "id": "kedreamix_awesome",
        "title": "Awesome Talking Head Synthesis",
        "type": "index",
        "tags": ("survey", "papers", "github-list"),
        "url": "https://github.com/Kedreamix/Awesome-Talking-Head-Synthesis",
        "body": "Alternate curated paper/repo list — cross-check with harlanhong awesome-talking-head-generation.",
    },
    {
        "id": "arxiv_daily_thg",
        "title": "Talking Face arXiv Daily",
        "type": "index",
        "tags": ("papers", "daily", "rss"),
        "url": "https://github.com/liutaocode/talking-face-arxiv-daily",
        "body": "Daily arXiv talking-face paper feed — keep Hostess7 registry current.",
    },
    {
        "id": "grok_imagine_reference_video",
        "title": "Grok reference-to-video",
        "type": "api",
        "tags": ("cloud", "reference-to-video", "xai"),
        "url": "https://docs.x.ai/docs/guides/image-generation",
        "body": (
            "grok-imagine-video (not 1.5) — guide video with reference images without fixing frame 1. "
            "Cinematic Hostess shots; pair with open-source lip-sync for sub-second talk."
        ),
    },
    {
        "id": "grok_imagine_text_video",
        "title": "Grok text-to-video",
        "type": "api",
        "tags": ("cloud", "text-to-video", "xai"),
        "url": "https://docs.x.ai/docs/guides/image-generation",
        "body": "Text prompt → video up to 15s, aspect ratio + resolution. B-roll and scene cuts, not live lip-sync.",
    },
    {
        "id": "heygen_alternate",
        "title": "Open-source live pipeline pattern",
        "type": "pattern",
        "tags": ("pipeline", "tts", "webrtc", "real-time"),
        "body": (
            "Live talk pattern: mic/text → LLM reply → TTS (piper/coqui/edge-tts/kokoro) → "
            "lip-sync (FasterLivePortrait/MuseTalk/LivePortrait) → frame stream → Graphics/GTK window. "
            "Hostess7: HOSTESS7_VOICE=1 + HOSTESS7_LIVE_VIDEO_BACKEND + field_live_video.sync_talk_reply()."
        ),
    },
)

CURATED_FETCH: tuple[dict[str, str], ...] = (
    {"id": "xai-imagine-docs", "lane": "imagine", "url": "https://docs.x.ai/docs/guides/image-generation", "why": "Grok Imagine API official"},
    {"id": "liveportrait-readme", "lane": "imagine", "url": "https://raw.githubusercontent.com/KlingTeam/LivePortrait/main/readme.md", "why": "LivePortrait install + inference"},
    {"id": "awesome-thg", "lane": "imagine", "url": "https://raw.githubusercontent.com/harlanhong/awesome-talking-head-generation/master/readme.md", "why": "Paper/github index (lowercase readme)"},
    {"id": "arxiv-liveportrait", "lane": "imagine", "url": "https://arxiv.org/abs/2407.03168", "why": "LivePortrait paper"},
    {"id": "musetalk-readme", "lane": "imagine", "url": "https://raw.githubusercontent.com/TMElyralab/MuseTalk/main/README.md", "why": "MuseTalk real-time lip sync"},
    {"id": "faster-liveportrait-readme", "lane": "imagine", "url": "https://raw.githubusercontent.com/warmshao/FasterLivePortrait/master/README.md", "why": "Real-time TensorRT LivePortrait"},
    {"id": "ditto-readme", "lane": "imagine", "url": "https://raw.githubusercontent.com/antgroup/ditto-talkinghead/main/README.md", "why": "Ditto streaming talking head"},
    {"id": "arxiv-teller", "lane": "imagine", "url": "https://arxiv.org/abs/2503.18429", "why": "Teller CVPR 2025 streaming"},
    {"id": "arxiv-livatar", "lane": "imagine", "url": "https://arxiv.org/abs/2507.18649", "why": "Livatar-1 real-time flow matching"},
    {"id": "arxiv-rest", "lane": "imagine", "url": "https://arxiv.org/abs/2512.11229", "why": "REST diffusion streaming THG"},
    {"id": "arxiv-thg-survey", "lane": "imagine", "url": "https://arxiv.org/abs/2507.02900", "why": "2025 talking-head survey"},
    {"id": "hallo-readme", "lane": "imagine", "url": "https://raw.githubusercontent.com/fudan-generative-vision/hallo/main/README.md", "why": "Hallo diffusion baseline"},
)


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        doc = {
            "version": CORPUS_VERSION,
            "imagine_workflow": list(IMAGINE_WORKFLOW),
            "live_video": list(LIVE_VIDEO_ENTRIES),
            "curated_fetch": list(CURATED_FETCH),
            "hostess7_integration": {
                "talk": "Language Expert — output window prose only",
                "graphics": "field_gfx_canvas — RGB pixels + text",
                "live_video": "field_live_video — TTS + lip-sync frame → Graphics window",
                "imagine_api": "XAI_API_KEY → grok-imagine-image / grok-imagine-video-1.5",
                "recommended_backend": recommend_live_backend(),
                "realtime_count": len(list_realtime_entries()),
                "nexus_imaging_teach": "field_imagine_nexus_teach.py",
                "nexus_imaging_chamber": "lib/hostess7-imaging.py",
            },
        }
        CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
        REGISTRY.write_text(
            json.dumps({"version": 1, "entries": list(LIVE_VIDEO_ENTRIES)}, indent=2) + "\n",
            encoding="utf-8",
        )
    return CORPUS_CACHE


_REALTIME_HINTS = frozenset({
    "live", "real-time", "realtime", "streaming", "talk", "face", "lip", "sync", "conversation",
})


def list_realtime_entries() -> list[dict[str, Any]]:
    """Entries tagged for sub-second / streaming talk — Hostess7 face-to-face path."""
    return [e for e in LIVE_VIDEO_ENTRIES if "real-time" in e.get("tags", ()) or "streaming" in e.get("tags", ())]


def recommend_live_backend(*, gpu: bool = True, quality: str = "balanced") -> dict[str, str]:
    """Pick open-source backend for Hostess7 live talk."""
    if gpu and quality in ("speed", "balanced"):
        return {
            "primary": "faster_liveportrait",
            "fallback": "musetalk",
            "cinematic": "grok_imagine_video_15",
            "why": "FasterLivePortrait: 30+ FPS TensorRT; MuseTalk if no NVIDIA TRT.",
        }
    if quality == "quality":
        return {
            "primary": "liveportrait",
            "fallback": "ditto",
            "cinematic": "grok_imagine_reference_video",
            "why": "LivePortrait quality + stitching; Ditto for diffusion streaming.",
        }
    return {
        "primary": "musetalk",
        "fallback": "wav2lip",
        "cinematic": "grok_imagine_text_video",
        "why": "CPU-friendly lip-sync; Wav2Lip baseline.",
    }


def search_imagine(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    ensure_corpus()
    data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    items = list(data.get("imagine_workflow", [])) + list(data.get("live_video", []))
    q = query.lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 2]
    want_realtime = bool(_REALTIME_HINTS & set(tokens)) or "real time" in q or "real-time" in q
    scored: list[tuple[int, dict]] = []
    for item in items:
        tags = item.get("tags", ())
        blob = f"{item.get('title','')} {item.get('body','')} {' '.join(tags)} {item.get('speed','')}".lower()
        score = sum(5 if t in blob else 0 for t in tokens)
        if q in blob:
            score += 10
        if want_realtime and ("real-time" in tags or "streaming" in tags):
            score += 15
        if item.get("type") == "github" and want_realtime:
            score += 3
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    return [x[1] for x in scored[:limit]]


def synthesize_imagine_paragraphs(query: str) -> list[str]:
    hits = search_imagine(query, limit=6)
    rec = recommend_live_backend()
    rt_count = len(list_realtime_entries())
    paras = [
        (
            f"Imagine + live video — {len(LIVE_VIDEO_ENTRIES)} papers/repos indexed "
            f"({rt_count} real-time). Grok Imagine for cinematic shots; "
            f"{rec['primary']} recommended for face-to-face talk."
        ),
    ]
    for h in hits:
        title = h.get("title", "")
        body = str(h.get("body", ""))[:320]
        speed = h.get("speed", "")
        url = h.get("url") or h.get("paper") or ""
        line = f"{title}"
        if speed:
            line += f" ({speed})"
        line += f": {body}"
        if url:
            line += f" · {url}"
        paras.append(line)
    if len(paras) == 1:
        paras.append(
            "Start: ./Hostess7.sh imagine-learn · FasterLivePortrait · LivePortrait · "
            "xAI docs.x.ai/docs/guides/image-generation"
        )
    return paras


def format_registry() -> str:
    ensure_corpus()
    lines = ["=== Live video registry (papers + GitHub) ===", ""]
    for e in LIVE_VIDEO_ENTRIES:
        tags = ", ".join(e.get("tags", ()))
        arx = e.get("arxiv", "")
        lines.append(f"· {e['title']} [{e.get('type','')}] — {tags}")
        if arx:
            lines.append(f"    arXiv:{arx} · {e.get('paper','')}")
        if e.get("url"):
            lines.append(f"    {e['url']}")
        lines.append(f"    {str(e.get('body',''))[:200]}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_corpus()
    print(format_registry())
    print(f"METRIC imagine_domains={len(IMAGINE_WORKFLOW)}")
    print(f"METRIC live_video_entries={len(LIVE_VIDEO_ENTRIES)}")
    print("OK imagine-corpus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())