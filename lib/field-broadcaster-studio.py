#!/usr/bin/env pythong
"""AmmoOS Broadcaster Studio — Final_Eye vision, all codecs, all platforms, threat-gated live."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fcc", _LIB / "field-chamber-core.py")
fcc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(fcc)

INSTALL = fcc.INSTALL
STATE = fcc.STATE
DOCTRINE = INSTALL / "data" / "field-broadcaster-studio-doctrine.json"
PLATFORMS = INSTALL / "data" / "field-broadcaster-platforms.json"
STUDIO = STATE / "field-broadcaster-studio.json"
PANEL = STATE / "field-broadcaster-studio-panel.json"
RECORDINGS = STATE / "field-broadcaster-portable" / "recordings"
PROC = STATE / "field-broadcaster-studio-proc.json"


def _uid() -> str:
    return uuid.uuid4().hex[:12]


def _save(path: Path, doc: dict[str, Any]) -> dict[str, Any]:
    return fcc.save_permanent(path, doc)


def _platforms() -> dict[str, Any]:
    return fcc.load(PLATFORMS, {"platforms": [], "default_platform": "kick"})


def _platform_by_id(pid: str) -> dict[str, Any] | None:
    for p in _platforms().get("platforms") or []:
        if p.get("id") == pid:
            return p
    return None


def _default_studio() -> dict[str, Any]:
    plats = _platforms()
    default_pid = plats.get("default_platform", "kick")
    plat = _platform_by_id(default_pid) or {}
    rec = plat.get("recommended") or {}
    return {
        "schema": "field-broadcaster-studio/v2",
        "updated": fcc.ts(),
        "collection": "AmmoOS Default",
        "profile": "Streaming",
        "active_scene": "scene_main",
        "preview_scene": "scene_main",
        "studio_mode": True,
        "streaming": False,
        "recording": False,
        "virtualcam": False,
        "platform": {
            "id": default_pid,
            "label": plat.get("label", "Kick"),
            "rtmp_url": plat.get("rtmp_url", ""),
            "stream_key": "",
        },
        "scenes": [
            {"id": "scene_main", "name": "Main", "order": 0},
            {"id": "scene_brb", "name": "BRB", "order": 1},
        ],
        "sources": {
            "scene_main": [
                {"id": "src_final_eye_display", "name": "Final_Eye Display", "kind": "final_eye_display", "driver": "Final_Eye", "visible": True, "primary": True},
                {"id": "src_final_eye_cam", "name": "Final_Eye Camera", "kind": "final_eye", "driver": "Final_Eye", "visible": True},
                {"id": "src_mic", "name": "Microphone", "kind": "audio_input", "device": "default", "visible": True, "muted": False},
            ],
            "scene_brb": [
                {"id": "src_text", "name": "Be Right Back", "kind": "text", "text": "AmmoOS · BRB", "visible": True},
            ],
        },
        "encoder": {
            "video": rec.get("video", "h264"),
            "audio": rec.get("audio", "aac"),
            "container_record": "mkv",
            "container_stream": rec.get("container", "flv"),
            "bitrate_kbps": rec.get("bitrate_kbps", 4500),
            "keyframe_sec": rec.get("keyframe_sec", 2),
        },
        "output": {"path": str(RECORDINGS), "format": "mkv"},
        "canvas_wire": True,
    }


def load_studio() -> dict[str, Any]:
    doc = fcc.load(STUDIO, {})
    if not doc.get("scenes"):
        doc = _default_studio()
        fcc.save_permanent(STUDIO, doc)
    return doc


def _run_cmd(argv: list[str], *, timeout: int = 8) -> str:
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _ensure_canvas_wire() -> dict[str, Any]:
    bridge = fcc.mod("bc_canvas", "field-final-eye-canvas-bridge.py")
    if bridge and hasattr(bridge, "connect"):
        return bridge.connect(profile="watch", mode="straight_path")
    return {"ok": False, "error": "canvas_bridge_missing"}


def enumerate_devices() -> dict[str, Any]:
    eye = fcc.mod("bc_eye", "field-broadcaster-final-eye.py")
    displays: list[dict[str, Any]] = []
    cameras: list[dict[str, Any]] = []
    if eye:
        if hasattr(eye, "list_displays"):
            displays = eye.list_displays()
        if hasattr(eye, "list_cameras"):
            cameras = eye.list_cameras()
    audio_in: list[dict[str, Any]] = []
    audio_out: list[dict[str, Any]] = []
    pout = _run_cmd(["pactl", "list", "short", "sources"])
    for line in pout.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            audio_in.append({"id": parts[1], "name": parts[-1] if len(parts) > 3 else parts[1], "kind": "audio_input"})
    pout2 = _run_cmd(["pactl", "list", "short", "sinks"])
    for line in pout2.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            audio_out.append({"id": parts[1], "name": parts[-1] if len(parts) > 3 else parts[1], "kind": "audio_output"})
    if not audio_in:
        audio_in = [{"id": "default", "name": "Default Input", "kind": "audio_input"}]
    if not audio_out:
        audio_out = [{"id": "default", "name": "Default Output", "kind": "audio_output"}]
    return {
        "displays": displays[:8],
        "cameras": cameras[:12],
        "audio_inputs": audio_in[:12],
        "audio_outputs": audio_out[:12],
        "final_eye_primary": True,
    }


def _threat_gate() -> dict[str, Any]:
    bridge = INSTALL / "lib" / "obs-threat-posterity-bridge.py"
    if bridge.is_file():
        try:
            spec = importlib.util.spec_from_file_location("bc_threat", bridge)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "panel_json"):
                    doc = mod.panel_json()
                    summary = (doc.get("threat_ledger") or {}).get("summary") or doc.get("threat_summary") or {}
                    blocked = int(summary.get("harm_candidate") or summary.get("blocked") or 0)
                    return {"ok": blocked == 0, "blocked": blocked, "summary": summary, "scene_guard": True, "product": "Broadcaster"}
        except Exception:
            pass
    return {"ok": True, "scene_guard": True, "blocked": 0, "summary": {}}


def _proc_state() -> dict[str, Any]:
    return fcc.load(PROC, {"streaming": False, "recording": False, "pids": {}})


def _set_proc(**kwargs: Any) -> None:
    doc = _proc_state()
    doc.update(kwargs)
    doc["updated"] = fcc.ts()
    fcc.save_permanent(PROC, doc)


def _capture_mod() -> Any | None:
    return fcc.mod("bc_capture", "field-broadcaster-capture.py")


def _primary_video_source(scene_id: str) -> dict[str, Any]:
    studio = load_studio()
    for src in (studio.get("sources") or {}).get(scene_id) or []:
        if not src.get("visible", True):
            continue
        kind = str(src.get("kind") or "")
        if kind in ("final_eye_display", "final_eye", "display", "camera", "desktop_capture"):
            return src
    return {"kind": "final_eye_display", "driver": "Final_Eye", "profile": "watch"}


def _program_feed(studio: dict[str, Any]) -> dict[str, Any]:
    sid = str(studio.get("active_scene") or "scene_main")
    src = _primary_video_source(sid)
    kind = str(src.get("kind") or "final_eye_display")
    if kind == "desktop_capture":
        mid = str(src.get("device") or src.get("id") or "")
        return {
            "type": "desktop_preview",
            "url": f"/api/field-broadcaster/desktop-preview?monitor={mid}",
            "refresh_ms": 2000,
            "monitor": mid,
            "label": src.get("name") or "Desktop",
        }
    eye = fcc.mod("bc_eye_feed", "field-broadcaster-final-eye.py")
    mjpeg = eye.mjpeg_url(profile="watch") if eye and hasattr(eye, "mjpeg_url") else ""
    return {
        "type": "mjpeg",
        "url": mjpeg,
        "refresh_ms": 0,
        "label": src.get("name") or "Final_Eye",
        "source_kind": kind,
    }


def _build_ffmpeg_argv(*, scene_id: str, output: str, stream: bool = False) -> list[str]:
    eye = fcc.mod("bc_eye_ff", "field-broadcaster-final-eye.py")
    codecs = fcc.mod("bc_codecs", "field-broadcaster-codecs.py")
    studio = load_studio()
    enc = studio.get("encoder") or {}
    src = _primary_video_source(scene_id)
    argv = ["ffmpeg", "-y"]
    if eye and hasattr(eye, "ffmpeg_video_input"):
        argv.extend(eye.ffmpeg_video_input(src))
    else:
        argv.extend(["-f", "x11grab", "-framerate", "30", "-i", ":0.0"])
    dac = fcc.mod("bc_dac_audio", "field-audio-dac-chamber.py")
    if dac and hasattr(dac, "broadcaster_audio_args"):
        ba = dac.broadcaster_audio_args()
        argv.extend(ba.get("ffmpeg_input") or ["-f", "pulse", "-i", "default"])
        af = str(ba.get("ffmpeg_audio_filter") or "").strip()
        if af:
            argv.extend(["-af", af])
    else:
        argv.extend(["-f", "pulse", "-i", "default"])
    vcodec = str(enc.get("video") or "h264")
    acodec = str(enc.get("audio") or "aac")
    bitrate = int(enc.get("bitrate_kbps") or 4500)
    kf = int(enc.get("keyframe_sec") or 2)
    if codecs:
        if hasattr(codecs, "video_encoder_args"):
            argv.extend(codecs.video_encoder_args(vcodec, bitrate_kbps=bitrate, keyframe_sec=kf))
        if hasattr(codecs, "audio_encoder_args"):
            argv.extend(codecs.audio_encoder_args(acodec))
    else:
        argv.extend(["-c:v", "libx264", "-preset", "veryfast", "-b:v", f"{bitrate}k", "-c:a", "aac"])
    if stream:
        argv.extend(["-f", "flv", output])
    else:
        container = str(enc.get("container_record") or "mkv")
        if codecs and hasattr(codecs, "output_format_args"):
            argv.extend(codecs.output_format_args(container))
        argv.append(output)
    return argv


def _ffmpeg_record_start(scene_id: str) -> dict[str, Any]:
    _ensure_canvas_wire()
    RECORDINGS.mkdir(parents=True, exist_ok=True)
    out = RECORDINGS / f"ammoos-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}.mkv"
    try:
        argv = _build_ffmpeg_argv(scene_id=scene_id, output=str(out), stream=False)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        _set_proc(recording=True, record_pid=proc.pid, record_path=str(out), scene_id=scene_id)
        return {"ok": True, "pid": proc.pid, "path": str(out), "argv_head": argv[:12]}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def _ffmpeg_stream_start(scene_id: str) -> dict[str, Any]:
    studio = load_studio()
    plat = studio.get("platform") or {}
    rtmp = str(plat.get("rtmp_url") or "").strip()
    key = str(plat.get("stream_key") or "").strip()
    if not rtmp:
        pid = plat.get("id") or "kick"
        preset = _platform_by_id(str(pid))
        rtmp = str((preset or {}).get("rtmp_url") or "")
    if not rtmp:
        return {"ok": False, "error": "rtmp_url_missing", "hint": "set platform stream key in Broadcaster"}
    if not key:
        return {"ok": False, "error": "stream_key_missing", "platform": plat.get("id")}
    dest = rtmp.rstrip("/") + ("" if rtmp.endswith(key) else f"/{key}")
    canvas = _ensure_canvas_wire()
    try:
        argv = _build_ffmpeg_argv(scene_id=scene_id, output=dest, stream=True)
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        _set_proc(streaming=True, stream_pid=proc.pid, rtmp_dest=dest.split("/")[2] if "/" in dest else "", scene_id=scene_id)
        return {"ok": True, "pid": proc.pid, "platform": plat.get("id"), "canvas_wire": canvas.get("connected"), "argv_head": argv[:10]}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def _stop_proc() -> dict[str, Any]:
    doc = _proc_state()
    for key in ("record_pid", "stream_pid"):
        pid = doc.get(key)
        if pid:
            try:
                os.kill(int(pid), 15)
            except (OSError, ProcessLookupError, ValueError):
                pass
    _set_proc(recording=False, streaming=False, record_pid=None, stream_pid=None)
    return {"ok": True}


def set_platform(platform_id: str, *, stream_key: str = "", rtmp_url: str = "") -> dict[str, Any]:
    studio = load_studio()
    plat = _platform_by_id(platform_id) or {"id": platform_id, "label": platform_id}
    rec = plat.get("recommended") or {}
    studio["platform"] = {
        "id": platform_id,
        "label": plat.get("label", platform_id),
        "rtmp_url": rtmp_url or plat.get("rtmp_url", ""),
        "stream_key": stream_key,
        "recommended": rec,
    }
    enc = studio.setdefault("encoder", {})
    enc["video"] = rec.get("video", enc.get("video", "h264"))
    enc["audio"] = rec.get("audio", enc.get("audio", "aac"))
    enc["bitrate_kbps"] = rec.get("bitrate_kbps", enc.get("bitrate_kbps", 4500))
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    return {"ok": True, "platform": studio["platform"], "encoder": enc}


def set_encoder(patch: dict[str, Any]) -> dict[str, Any]:
    studio = load_studio()
    enc = studio.setdefault("encoder", {})
    for key in ("video", "audio", "container_record", "container_stream", "bitrate_kbps", "keyframe_sec"):
        if key in patch:
            enc[key] = patch[key]
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    return {"ok": True, "encoder": enc}


def scene_add(name: str) -> dict[str, Any]:
    studio = load_studio()
    sid = f"scene_{_uid()}"
    studio.setdefault("scenes", []).append({"id": sid, "name": name or "Scene", "order": len(studio["scenes"])})
    studio.setdefault("sources", {})[sid] = []
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    return {"ok": True, "scene_id": sid, "scenes": studio["scenes"]}


def scene_remove(scene_id: str) -> dict[str, Any]:
    studio = load_studio()
    studio["scenes"] = [s for s in studio.get("scenes") or [] if s.get("id") != scene_id]
    sources = studio.get("sources") or {}
    sources.pop(scene_id, None)
    studio["sources"] = sources
    if studio.get("active_scene") == scene_id:
        studio["active_scene"] = (studio["scenes"][0]["id"] if studio["scenes"] else "")
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    return {"ok": True, "scenes": studio["scenes"]}


def scene_set_active(scene_id: str, *, preview: bool = False) -> dict[str, Any]:
    studio = load_studio()
    if preview:
        studio["preview_scene"] = scene_id
    else:
        studio["active_scene"] = scene_id
        studio.pop("transition", None)
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    return {
        "ok": True,
        "active_scene": studio.get("active_scene"),
        "preview_scene": studio.get("preview_scene"),
        "program_feed": _program_feed(studio),
    }


def scene_transition(
    to_scene: str,
    *,
    from_scene: str = "",
    kind: str = "fade",
    ms: int = 500,
) -> dict[str, Any]:
    studio = load_studio()
    scene_ids = {s.get("id") for s in studio.get("scenes") or []}
    if to_scene not in scene_ids:
        return {"ok": False, "error": "scene_not_found"}
    src_scene = from_scene or studio.get("preview_scene") or studio.get("active_scene") or ""
    if src_scene not in scene_ids:
        src_scene = studio.get("active_scene") or to_scene
    ms = max(0, min(3000, int(ms)))
    if kind == "cut" or ms <= 0:
        return scene_set_active(to_scene, preview=False)
    studio["transition"] = {
        "kind": "fade",
        "ms": ms,
        "from_scene": src_scene,
        "to_scene": to_scene,
        "started": fcc.ts(),
    }
    studio["preview_scene"] = to_scene
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    return {"ok": True, "transition": studio["transition"], "program_feed": _program_feed(studio)}


def list_desktops() -> dict[str, Any]:
    cap = _capture_mod()
    if not cap:
        return {"ok": False, "error": "desktop_capture_unavailable"}
    gate = cap.capture_gate() if hasattr(cap, "capture_gate") else {"ok": True}
    monitors = cap.enumerate_monitors() if hasattr(cap, "enumerate_monitors") else []
    return {"ok": gate.get("ok", True), "gate": gate, "monitors": monitors}


def source_add(scene_id: str, *, kind: str, name: str = "", device: str = "") -> dict[str, Any]:
    studio = load_studio()
    sid = f"src_{_uid()}"
    if kind in ("display", "final_eye_display"):
        src = {"id": sid, "name": name or "Final_Eye Display", "kind": "final_eye_display", "driver": "Final_Eye", "visible": True}
    elif kind in ("camera", "final_eye"):
        src = {"id": sid, "name": name or "Final_Eye Camera", "kind": "final_eye", "driver": "Final_Eye", "visible": True}
    elif kind in ("desktop", "desktop_capture"):
        cap = _capture_mod()
        if not cap or not hasattr(cap, "validate_monitor"):
            return {"ok": False, "error": "desktop_capture_unavailable"}
        gate = cap.capture_gate() if hasattr(cap, "capture_gate") else {"ok": True}
        if not gate.get("ok"):
            return {"ok": False, "error": "threat_blocked", "gate": gate}
        monitors = cap.enumerate_monitors() if hasattr(cap, "enumerate_monitors") else []
        mid = str(device or "").strip() or (monitors[0]["id"] if monitors else "")
        mon = cap.validate_monitor(mid)
        if not mon:
            return {"ok": False, "error": "invalid_desktop_monitor", "monitors": monitors}
        src = {
            "id": sid,
            "name": name or mon.get("name") or "Desktop",
            "kind": "desktop_capture",
            "driver": "secure_capture",
            "device": mon["id"],
            "backend": mon.get("backend"),
            "geometry": mon.get("geometry"),
            "visible": True,
        }
    else:
        src = {"id": sid, "name": name or kind.title(), "kind": kind, "device": device or "default", "visible": True}
    studio.setdefault("sources", {}).setdefault(scene_id, []).append(src)
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    out: dict[str, Any] = {"ok": True, "source": src}
    if kind in ("desktop", "desktop_capture"):
        out["gate"] = gate
    return out


def source_remove(scene_id: str, source_id: str) -> dict[str, Any]:
    studio = load_studio()
    rows = studio.setdefault("sources", {}).get(scene_id) or []
    studio["sources"][scene_id] = [r for r in rows if r.get("id") != source_id]
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    return {"ok": True}


def source_move(scene_id: str, source_id: str, direction: str) -> dict[str, Any]:
    studio = load_studio()
    rows = studio.setdefault("sources", {}).get(scene_id) or []
    idx = next((i for i, r in enumerate(rows) if r.get("id") == source_id), -1)
    if idx < 0:
        return {"ok": False, "error": "source_not_found"}
    j = idx - 1 if direction == "up" else idx + 1
    if 0 <= j < len(rows):
        rows[idx], rows[j] = rows[j], rows[idx]
    studio["sources"][scene_id] = rows
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    return {"ok": True, "sources": rows}


def go_live(*, scene_id: str = "") -> dict[str, Any]:
    gate = _threat_gate()
    if not gate.get("ok"):
        return {"ok": False, "error": "threat_blocked", "threat": gate}
    studio = load_studio()
    sid = scene_id or studio.get("active_scene") or "scene_main"
    stream = _ffmpeg_stream_start(sid)
    if not stream.get("ok"):
        return stream
    studio["streaming"] = True
    studio["active_scene"] = sid
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    return {**stream, "streaming": True, "scene_id": sid, "threat": gate, "engine": "studio", "platform": studio.get("platform")}


def start_record(*, scene_id: str = "") -> dict[str, Any]:
    gate = _threat_gate()
    studio = load_studio()
    sid = scene_id or studio.get("active_scene") or "scene_main"
    rec = _ffmpeg_record_start(sid)
    if rec.get("ok"):
        studio["recording"] = True
        studio["updated"] = fcc.ts()
        _save(STUDIO, studio)
    return {**rec, "threat": gate, "engine": "studio"}


def stop_all() -> dict[str, Any]:
    studio = load_studio()
    studio["streaming"] = False
    studio["recording"] = False
    studio["updated"] = fcc.ts()
    _save(STUDIO, studio)
    _stop_proc()
    return {"ok": True}


def posture() -> dict[str, Any]:
    studio = load_studio()
    proc = _proc_state()
    devices = enumerate_devices()
    threat = _threat_gate()
    codecs = fcc.mod("bc_codec_p", "field-broadcaster-codecs.py")
    codec_doc = codecs.posture() if codecs and hasattr(codecs, "posture") else {}
    canvas = fcc.mod("bc_canvas_p", "field-final-eye-canvas-bridge.py")
    canvas_doc = canvas.posture() if canvas and hasattr(canvas, "posture") else {}
    comb: dict[str, Any] = {}
    seq_py = INSTALL / "lib" / "field-combinatorics-sequence.py"
    if seq_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("bc_seq", seq_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "publish_panel"):
                    comb = (mod.publish_panel().get("panel") or {})
        except Exception:
            pass
    panel = {
        "schema": "field-broadcaster-studio-panel/v2",
        "updated": fcc.ts(),
        "ok": True,
        "engine": "studio",
        "product": "Broadcaster",
        "collection": studio.get("collection"),
        "profile": studio.get("profile"),
        "active_scene": studio.get("active_scene"),
        "preview_scene": studio.get("preview_scene"),
        "studio_mode": studio.get("studio_mode", True),
        "streaming": proc.get("streaming") or studio.get("streaming"),
        "recording": proc.get("recording") or studio.get("recording"),
        "scene_count": len(studio.get("scenes") or []),
        "scenes": studio.get("scenes") or [],
        "sources": studio.get("sources") or {},
        "devices": devices,
        "encoder": studio.get("encoder"),
        "platform": studio.get("platform"),
        "platforms": _platforms(),
        "codecs": codec_doc,
        "canvas_wire": canvas_doc,
        "threat": threat,
        "combinatorics": {"sequence_length": comb.get("sequence_length"), "gapless": comb.get("gapless")},
        "transition": studio.get("transition"),
        "program_feed": _program_feed(studio),
        "preview_feed": _program_feed({**studio, "active_scene": studio.get("preview_scene") or studio.get("active_scene")}),
    }
    _save(PANEL, panel)
    return panel


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "posture").strip().lower().replace("-", "_")
    if action in ("posture", "json", "status"):
        return posture()
    if action in ("go_live", "golive", "stream_start"):
        return go_live(scene_id=str(body.get("scene_id") or ""))
    if action in ("record", "record_start"):
        return start_record(scene_id=str(body.get("scene_id") or ""))
    if action in ("stop", "stream_stop", "record_stop"):
        return stop_all()
    if action == "scene_add":
        return scene_add(str(body.get("name") or "Scene"))
    if action == "scene_remove":
        return scene_remove(str(body.get("scene_id") or ""))
    if action == "scene_activate":
        return scene_set_active(str(body.get("scene_id") or ""), preview=bool(body.get("preview")))
    if action in ("transition", "scene_transition"):
        return scene_transition(
            str(body.get("to_scene") or body.get("scene_id") or ""),
            from_scene=str(body.get("from_scene") or ""),
            kind=str(body.get("kind") or body.get("type") or "fade"),
            ms=int(body.get("ms") or body.get("duration_ms") or 500),
        )
    if action in ("desktops", "list_desktops", "desktop_monitors"):
        return list_desktops()
    if action == "source_add":
        return source_add(str(body.get("scene_id") or ""), kind=str(body.get("kind") or "final_eye_display"), name=str(body.get("name") or ""), device=str(body.get("device") or ""))
    if action == "source_remove":
        return source_remove(str(body.get("scene_id") or ""), str(body.get("source_id") or ""))
    if action == "source_move":
        return source_move(str(body.get("scene_id") or ""), str(body.get("source_id") or ""), str(body.get("direction") or "up"))
    if action in ("set_platform", "platform"):
        return set_platform(str(body.get("platform_id") or body.get("id") or "kick"), stream_key=str(body.get("stream_key") or ""), rtmp_url=str(body.get("rtmp_url") or ""))
    if action in ("set_encoder", "encoder"):
        return set_encoder(body)
    if action in ("canvas_connect", "canvas_wire"):
        return _ensure_canvas_wire()
    if action in ("look", "eye_look", "look_share"):
        eye = fcc.mod("bc_eye_look_st", "field-broadcaster-final-eye.py")
        if eye and hasattr(eye, "look_and_share_hostess7"):
            return eye.look_and_share_hostess7(
                prefer=str(body.get("prefer") or "auto"),
                label=str(body.get("label") or "studio_look"),
            )
        return {"ok": False, "error": "look_unavailable"}
    if action in ("straight_path", "straight"):
        return _ensure_canvas_wire()
    if action == "devices":
        return {"ok": True, "devices": enumerate_devices()}
    if action == "platforms":
        return {"ok": True, **_platforms()}
    if action == "codecs":
        codecs = fcc.mod("bc_codec_d", "field-broadcaster-codecs.py")
        return codecs.posture() if codecs else {"ok": False}
    if action == "threat":
        return _threat_gate()
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture", "panel"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() if len(sys.argv) <= 2 else sys.argv[2])
        except json.JSONDecodeError:
            body = {}
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0
    if cmd == "devices":
        print(json.dumps(enumerate_devices(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-broadcaster-studio.py [json|devices|dispatch]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())