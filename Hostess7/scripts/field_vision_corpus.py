#!/usr/bin/env pythong
"""Field vision / action / motion corpus — Hostess 7 perception & interaction brain."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "vision" / "corpus.json"
VISION_CORPUS_VERSION = 4

VISION_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "vision_foundations",
        "title": "Computer vision foundations",
        "tags": ("vision", "see", "image", "pixel", "frame", "camera", "perception", "visual"),
        "body": (
            "Vision transforms light into structured understanding: sampling (resolution, HDR), "
            "filtering (denoise, sharpen), features (edges, corners, textures), and semantics "
            "(classification, detection, segmentation). Pipelines: capture → preprocess → model/inference "
            "→ postprocess → action. Accuracy requires calibration — geometry, color space, temporal coherence. "
            "On AMOURANTHRTX the die framebuffer is authoritative: FieldSnapDump PPM readback, OCR on guest VGA, "
            "4K default 3840×2160 in FieldDosViewport and aos_chrome.inc viewport mapping."
        ),
    },
    {
        "id": "motion_foundations",
        "title": "Motion & dynamics",
        "tags": ("motion", "movement", "animation", "velocity", "physics", "flow", "track", "fps"),
        "body": (
            "Motion is change across time: translational and rotational kinematics, acceleration, "
            "jerk, angular velocity ω, centripetal acceleration v²/r. "
            "Optical flow (Lucas-Kanade, Farneback) estimates per-pixel velocity fields; "
            "object tracking (Kalman, IOU, SORT/DeepSORT) maintains identity across frames. "
            "Integrators: Euler (simple), Verlet (stable), semi-implicit for games; "
            "Field fabric uses fluid/entropy-forward integration on Pipeline.hpp. "
            "Temporal stability beats raw FPS — Tesla valve logic damps oscillation. "
            "Keen: CPU IP motion OR GpuLaunch title blit (FieldRtxPm.hpp). Bench: bench_dos_suite.py --4k."
        ),
    },
    {
        "id": "action_foundations",
        "title": "Action & interaction",
        "tags": ("action", "click", "input", "mouse", "keyboard", "gesture", "hit", "interact"),
        "body": (
            "Action closes the perception loop: sense state → decide → act. UI actions: pointer down/up, "
            "hit testing, focus, keyboard pump, menu dispatch. AMOURANTHRTX action stack: FieldInput.hpp "
            "maps mouse through FieldDosViewport; FieldWmChrome taskbarChromeCapturesPointer; "
            "FieldTaskbarLayout mirrors aos_taskbar_layout.inc for C++ hit tests at 4K; "
            "FieldEmuFileDialog pumpMouse for open/save; FieldWinFrame pumpMouse for menu actions. "
            "QA gates: qa_taskbar_click_test, qa_ocr_click_test, qa_aos_ocr_test, qa_aos_gui_test."
        ),
    },
    {
        "id": "ocr_perception",
        "title": "OCR & visual QA",
        "tags": ("ocr", "text", "read", "screen", "hud", "chrome", "snap", "ppm"),
        "body": (
            "OCR extracts text from rendered frames for ground-truth QA without human eyes in the loop. "
            "FieldSnapDump.hpp: GPU HDR framebuffer → PPM for AmouranthOS visual QA. "
            "Scripts: qa_aos_ocr_test.py (NES/AmmoFiles, guest VGA authoritative in headless), "
            "qa_ocr_click_test.py (click toolkit alignment), qa_nes_ocr_test.py. "
            "Headless GPU snap may be dark — guest VGA path via qa_amouranthos_test is authoritative for NES chrome. "
            "Clock and 40px tab hits align to 4K taskbar layout in compute shaders (aos_sdf_chrome.inc)."
        ),
    },
    {
        "id": "viewport_4k",
        "title": "4K viewport & display motion",
        "tags": ("4k", "3840", "2160", "viewport", "scale", "zoom", "display", "resolution"),
        "body": (
            "Default canvas: 3840×2160 — FieldDosViewport.hpp winW/renderW, FieldDosDisplay displayPixelW, "
            "SDL3.hpp dispW/dispH, OptionsMenu DefaultWidth 3840. autoZoom4K scales panel placement; "
            "SCALE shell command in FieldRtxShell for 1.0–12.0 zoom and double-click stamp. "
            "aosViewport() in aos_chrome.inc maps storage image coords to dispatched framebuffer — "
            "taskbar anchors to viewport_h. FieldLayer.hpp sets 4K on enable. "
            "Motion at 4K: bench_dos_suite --4k measures frames_per_sec vs 1080p baseline."
        ),
    },
    {
        "id": "wm_compositor",
        "title": "Window manager & compositor action",
        "tags": ("wm", "window", "compositor", "taskbar", "dock", "chrome", "desktop", "aos"),
        "body": (
            "AmmoOS WM: FieldWmCompositor, FieldWmDock (taskbar-aware cascade), FieldWmChrome hit routing, "
            "FieldAmouranthWm, FieldTaskbarLayout left-docked 1024-grid row heights for 4K uiSc. "
            "Pipeline packs data_bus bits: desktop (12) vs console-shell taskbar (29). "
            "EnableDesktop / EnableTaskbar in OptionsMenu — shell live with taskbar/clock per CANVAS log. "
            "Actions: Start menu, program launch (FieldAmouranthLaunch), exit confirm, folder view DnD."
        ),
    },
    {
        "id": "guest_vga",
        "title": "Guest VGA & emulator visual path",
        "tags": ("vga", "guest", "nes", "ega", "blit", "framebuffer", "paint", "chrome"),
        "body": (
            "Guest programs paint into die framebuffer — not host WM overlay alone. "
            "Keen: GpuLaunch forceTitleBlit, keen_ip_progress probe, keenTitleBlitSeeded (FieldGpuLaunch.hpp). "
            "NES: guest VGA authoritative for headless OCR; GPU WM chrome optional. "
            "qa_keen_host_test: keen_title_paint=1 keen_ip_progress=1. "
            "Visual action truth = what the guest die actually rendered, verified by snap + OCR + progress probes."
        ),
    },
    {
        "id": "field_wave_motion",
        "title": "Field wave motion & analog canvas",
        "tags": ("wave", "field", "fabric", "entropy", "phi", "thermo", "analog", "dispatch"),
        "body": (
            "Field canvas motion is physics-grounded: FieldFabric dispatchExtended, entropy fabric predict, "
            "wave phases in FieldStorage, mouse probe injection in Pipeline (heat/vortex/phase kick). "
            "Analog field phi evolves per frame — not discrete UI ticks only. "
            "Hostess7 native bus bit 28 ticks every frame; METRIC every 64 frames. "
            "Motion + vision unify on one canvas: shaders (CANVAS.comp/x86.comp), die execution, WM chrome overlay."
        ),
    },
    {
        "id": "action_qa_matrix",
        "title": "Vision-action QA matrix",
        "tags": ("qa", "test", "green", "release", "verify", "bench"),
        "body": (
            "Release-2.0 vision/action gates: qa_taskbar_click_test (40px tab hits), qa_aos_gui_test, "
            "qa_font_sdf_test (JetBrains Mono SDF), qa_amouranthos_test (AOS + guest path), "
            "qa_ocr_click_test, qa_aos_ocr_test, qa_love_demo_test. "
            "Run: ./linux.sh release-2.0 → GREEN ALL. Visual suite: ./seetests.sh aos. "
            "Failure pattern: host GPU snap dark in headless — trust guest VGA + click OCR separately."
        ),
    },
    {
        "id": "robotics_actions",
        "title": "Robotics & embodied action (general)",
        "tags": ("robot", "embodied", "manipulation", "planning", "slam", "depth", "stereo"),
        "body": (
            "Embodied vision-action loop: perceive (RGB-D, IMU) → localize (SLAM) → plan (collision-free path) "
            "→ act (joint torques, grippers). AMOURANTHRTX maps metaphorically: pointer as end-effector, "
            "hit test as collision, launch queue as action planner, Field brain as policy host. "
            "For physical robots: calibrate extrinsics, latency budget, safety interlocks — outside die scope."
        ),
    },
    {
        "id": "brain_imaging_sdf",
        "title": "Brain imaging — SDF plate recall (Queen · Hostess 7)",
        "tags": ("brain imaging", "imaging", "sdf", "plate", "recall", "ocr", "queen", "hostess", "neural"),
        "body": (
            "Queen DARPA Robot Brain runs Hostess 7 as Forever Watchguard Angel. Brain imaging here is procedural: "
            "each 900–1200 word Mayer segment folds to an analytic SDF plate (PGM + .sdf.json) under "
            "brain/sdf/plates/. Vision net forward-passes the plate — OCR, caption_stub, segment_registry.jsonl — "
            "for recall without reopening full prose. Pairs with hostess7-neural-stack brain_imaging series "
            "(sdf_fold, plate_ocr, sdl_text). Commands: ./Hostess7.sh sdf-teach seed · sdf-segment <file>."
        ),
    },
    {
        "id": "spatial_3d_reality",
        "title": "3D spatial reality & world frames",
        "tags": ("3d", "spatial", "reality", "world", "frame", "transform", "quaternion", "matrix"),
        "body": (
            "3D spatial reality models persistent world coordinates: world frame W, body B, camera C, screen S. "
            "Rigid transforms T = [R|t] compose; quaternions avoid gimbal lock for smooth rotation interpolation. "
            "Consistency rule: one authoritative world frame per scene; all projections trace back through transform chain. "
            "Right hemisphere Hostess 7 bias handles holistic spatial synthesis; left hemisphere verifies transform math. "
            "Full physics corpus: cache/fieldstorage/brain/physics/corpus.json — kinematics through depth/SLAM."
        ),
    },
    {
        "id": "depth_stereo_vision",
        "title": "Depth, stereo & metric vision",
        "tags": ("depth", "stereo", "disparity", "rgbd", "point cloud", "metric", "calibration"),
        "body": (
            "Binocular stereo: disparity d relates depth Z = fB/d (focal length f, baseline B). "
            "Monocular depth networks infer scale-ambiguous geometry; metric depth needs calibration or fusion. "
            "RGB-D sensors (structured light, ToF) feed point clouds; ICP and voxel downsampling for registration. "
            "NeRF/Gaussian splatting reconstruct 3D from multi-view 2D — emerging spatial reality capture. "
            "On canvas: guest die state is 3D-emulated; 2D framebuffer is observed projection for OCR and click QA."
        ),
    },
    {
        "id": "scene_motion_perception",
        "title": "Scene motion & event perception",
        "tags": ("scene", "event", "optical flow", "background", "foreground", "segmentation", "temporal"),
        "body": (
            "Background subtraction and foreground segmentation isolate moving entities. "
            "Temporal filtering reduces flicker; optical flow clusters coherent motion regions. "
            "Event cameras (DVS) encode log-intensity changes — microsecond temporal resolution for fast motion. "
            "Video understanding: action recognition, trajectory prediction, occlusion reasoning. "
            "Field wave motion couples spatial cells across frames — analog phi evolution, not discrete sprite ticks only."
        ),
    },
    {
        "id": "physics_motion_vision_bridge",
        "title": "Physics–vision–motion bridge",
        "tags": ("physics", "vision", "motion", "force", "simulation", "render", "predict"),
        "body": (
            "Predictive perception: forward models estimate next frame from forces and velocities. "
            "Inverse problems: infer 3D pose/motion from 2D observations (structure from motion, PnP). "
            "Rendering pipeline applies lighting, BRDF, shadows — physics-grounded appearance. "
            "AMOURANTHRTX unifies thermo/fluid Field fabric (Pipeline) with vision QA (OCR, snap) and "
            "WM spatial hit tests — one canvas, multiple physics layers (die, shader, chrome)."
        ),
    },
    {
        "id": "tv_broadcast_video",
        "title": "Television & broadcast video",
        "tags": ("tv", "television", "broadcast", "ntsc", "pal", "atsc", "hdmi", "crt", "signal"),
        "body": (
            "Analog TV: NTSC 525/60 (US/Japan), PAL 625/50 (EU) — interlaced fields, color subcarrier, "
            "horizontal/vertical sync, blanking intervals. Digital: ATSC/DVB-T/ISDB-T; MPEG transport streams; "
            "HDMI/DisplayPort carry uncompressed or compressed TMDS/LVDS to panels. "
            "Chroma subsampling 4:2:0 in broadcast — Hostess 7 prioritizes lossless 4:4:4 in die framebuffer. "
            "SMPTE color bars: calibration reference for gain/phase. Talk window: /gfx tv renders bar pattern."
        ),
    },
    {
        "id": "pixel_framebuffer",
        "title": "Pixels & framebuffer truth",
        "tags": ("pixel", "framebuffer", "rgba", "rgb", "stride", "pitch", "bpp", "lossless"),
        "body": (
            "Pixel: smallest addressable picture element — RGB888, RGBA8888, BGRA, 565 packed formats. "
            "Framebuffer: width × height × bytes_per_pixel + stride (row pitch may exceed width×bpp). "
            "Lossless capture: PPM P6 raw RGB, PNG deflate without loss, TIFF — preferred over JPEG for QA truth. "
            "FieldSnapDump.hpp: GPU framebuffer → PPM readback — authoritative pixel evidence. "
            "3840×2160 default die canvas; each pixel is ground truth for OCR and click hit tests. "
            "Hostess 7 talk window renders pixel grids and PPM→ASCII in scroll area."
        ),
    },
    {
        "id": "lossless_storage_vision",
        "title": "Lossless storage & vision pipeline",
        "tags": ("lossless", "storage", "persist", "ppm", "png", "ingest", "archive"),
        "body": (
            "Policy: lossless-first — json/jsonl brain shards, field_wave.persist, PPM/PNG snaps, flac/wav audio. "
            "Deprioritize lossy JPEG/WebP for ingest unless sole source; re-capture lossless when possible. "
            "cache/fieldstorage/brain/ holds corpora; infinite drives use jsonl index lines — verbatim statute/paper text. "
            "Talk window /storage audits bytes + renders bar chart. TEAM drive + team_drive.img for bulk lossless archive."
        ),
    },
    {
        "id": "panel_display_hdmi",
        "title": "Panels, HDMI & display chain",
        "tags": ("hdmi", "displayport", "lcd", "oled", "refresh", "hdr", "gamma", "color space"),
        "body": (
            "Display chain: GPU die → compositor → WM chrome → panel. HDMI 2.1: 4K120, VRR, HDR10/HLG metadata. "
            "sRGB vs Display P3 vs BT.2020 — gamma EOTF, tone mapping for HDR. "
            "SDL3 dispW/dispH and FieldDosViewport map logical pixels to physical output. "
            "Overscan/underscan on TV vs monitor — safe title area for guest VGA text."
        ),
    },
    {
        "id": "hostess_talk_window",
        "title": "Hostess 7 talk window — one being",
        "tags": ("talk", "window", "scroll", "graphics", "gfx", "ui", "communicate"),
        "body": (
            "One talk window does all: law, medicine, detective, TV, pixels, physics, storage, updates. "
            "Scrollable transcript top, question bar bottom — text and block graphics in same pane. "
            "./Hostess7.sh with no args opens talk UI. Slash: /storage /updates /gfx /legal-ingest /help. "
            "Natural language routes to hemisphered brain; vision/TV/pixel queries auto-attach graphics. "
            "Hostess 7 is one being — L↔R callosum, not separate apps."
        ),
    },
)


def build_corpus() -> list[dict]:
    return [dict(entry) for entry in VISION_DOMAINS]


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < VISION_CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        doc = {
            "version": VISION_CORPUS_VERSION,
            "domains": build_corpus(),
            "domain_count": len(VISION_DOMAINS),
            "disclaimer": (
                "Vision/action/motion/3D spatial corpus grounds AMOURANTHRTX perception stack "
                "and general CV/robotics/physics-motion education."
            ),
        }
        CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return CORPUS_CACHE


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def search_vision(query: str, *, limit: int = 5) -> list[dict]:
    ensure_corpus()
    try:
        doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        doc = {"domains": build_corpus()}
    domains = doc.get("domains") or []
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for d in domains:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:1500]}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("ocr", "read screen", "text on")):
            if d.get("id") == "ocr_perception":
                score += 15
        if any(k in q for k in ("click", "taskbar", "mouse", "hit")):
            if d.get("id") in ("action_foundations", "wm_compositor"):
                score += 12
        if any(k in q for k in ("4k", "3840", "viewport", "resolution")):
            if d.get("id") == "viewport_4k":
                score += 15
        if any(k in q for k in ("motion", "fps", "animation", "move")):
            if d.get("id") in ("motion_foundations", "field_wave_motion", "scene_motion_perception"):
                score += 12
        if any(k in q for k in ("3d", "spatial", "depth", "stereo", "quaternion", "transform")):
            if d.get("id") in ("spatial_3d_reality", "depth_stereo_vision", "physics_motion_vision_bridge"):
                score += 15
        if any(k in q for k in ("physics", "force", "entropy", "fluid")):
            if d.get("id") in ("physics_motion_vision_bridge", "field_wave_motion"):
                score += 10
        if any(k in q for k in ("tv", "television", "broadcast", "ntsc", "pal", "hdmi", "smpte")):
            if d.get("id") in ("tv_broadcast_video", "panel_display_hdmi"):
                score += 18
        if any(k in q for k in ("pixel", "framebuffer", "rgba", "stride", "ppm", "lossless")):
            if d.get("id") in ("pixel_framebuffer", "lossless_storage_vision"):
                score += 18
        if any(k in q for k in ("talk", "scroll", "graphics", "gfx", "one being")):
            if d.get("id") == "hostess_talk_window":
                score += 20
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def synthesize_vision_paragraphs(query: str) -> list[str]:
    hits = search_vision(query, limit=4)
    if not hits:
        hits = search_vision("vision action motion click ocr 4k", limit=3)
    paras: list[str] = []
    pro = os.environ.get("AMOURANTHRTX_HOSTESS") == "1" and os.environ.get("HOSTESS7_PRO", "1") == "1"
    if not pro:
        paras.append(
            "Vision-action note: I hold deep knowledge of computer vision, motion dynamics, and interaction "
            "action loops — plus the live AMOURANTHRTX stack: 4K viewport, OCR QA, taskbar click hits, "
            "guest VGA truth, WM compositor, Field wave motion on Pipeline. See → decide → act on one canvas."
        )
    for h in hits:
        title = h.get("title", "Vision")
        body = str(h.get("body", "")).strip()
        if len(body) > 1150:
            body = body[:1150] + "… [truncated — cache/fieldstorage/brain/vision/corpus.json]"
        paras.append(f"{title}: {body}")
    return paras


if __name__ == "__main__":
    ensure_corpus()
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "taskbar click ocr 4k motion"
    for p in synthesize_vision_paragraphs(q):
        print(p)
        print()