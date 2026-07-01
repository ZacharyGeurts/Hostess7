#!/usr/bin/env pythong
"""Broadcaster Chamber — Final_Eye display+camera, all codecs, all platforms, threat-gated live."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fcc", _LIB / "field-chamber-core.py")
fcc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(fcc)

INSTALL = fcc.INSTALL
STATE = fcc.STATE
DOCTRINE = INSTALL / "data" / "field-broadcaster-chamber-doctrine.json"
PLATFORMS = INSTALL / "data" / "field-broadcaster-platforms.json"
PANEL = STATE / "field-broadcaster-chamber-panel.json"


def program_meta() -> dict[str, Any]:
    doc = fcc.load(DOCTRINE, {})
    return {
        "schema": "field-broadcaster-chamber-program/v1",
        "id": "field-broadcaster",
        "title": doc.get("title") or "AmmoOS Broadcaster",
        "motto": doc.get("motto"),
        "icon": "/assets/queen-prog-broadcaster.png",
        "ui": "/field-broadcaster",
        "api": "/api/field-broadcaster/chamber",
        "queen_browser": True,
        "consolidates": doc.get("consolidates") or [],
    }


def platforms_doc() -> dict[str, Any]:
    return fcc.load(PLATFORMS, {"platforms": [], "default_platform": "kick"})


def codecs_posture() -> dict[str, Any]:
    codecs = fcc.mod("bc_codecs", "field-broadcaster-codecs.py")
    if codecs and hasattr(codecs, "posture"):
        return codecs.posture()
    return {"ok": False, "error": "codecs_missing"}


def final_eye_posture(*, refresh: bool = False) -> dict[str, Any]:
    eye = fcc.mod("bc_eye", "field-broadcaster-final-eye.py")
    if not refresh and eye and hasattr(eye, "eye_probe"):
        return eye.eye_probe()
    if eye and hasattr(eye, "vision_posture"):
        return eye.vision_posture()
    if eye and hasattr(eye, "posture"):
        return eye.posture()
    return {"ok": False, "error": "final_eye_missing"}


def studio_posture(*, refresh: bool = False) -> dict[str, Any]:
    cached = fcc.load(STATE / "field-broadcaster-studio-panel.json", {})
    if cached and not refresh:
        return cached
    studio = fcc.mod("bc_studio", "field-broadcaster-studio.py")
    if studio and hasattr(studio, "posture"):
        return studio.posture()
    return cached


def audio_posture() -> dict[str, Any]:
    dac = fcc.mod("bc_audio_dac", "field-audio-dac-chamber.py")
    if dac and hasattr(dac, "dac_probe"):
        probe = dac.dac_probe()
        audio = fcc.mod("bc_audio", "field-broadcaster-audio.py")
        chain = audio.snapshot() if audio and hasattr(audio, "snapshot") else {}
        return {**probe, "chain": chain, "layer": "audio_dac"}
    audio = fcc.mod("bc_audio", "field-broadcaster-audio.py")
    if audio and hasattr(audio, "snapshot"):
        return audio.snapshot()
    return {}


def canvas_posture(*, refresh: bool = False) -> dict[str, Any]:
    canvas = fcc.mod("bc_canvas", "field-final-eye-canvas-bridge.py")
    if canvas and hasattr(canvas, "canvas_probe") and not refresh:
        return canvas.canvas_probe()
    if canvas and hasattr(canvas, "posture"):
        return canvas.posture()
    return fcc.load(STATE / "field-final-eye-canvas-panel.json", {})


def chamber_probe() -> dict[str, Any]:
    """Lightweight chamber status — cached studio panel, eye health only."""
    studio = fcc.load(STATE / "field-broadcaster-studio-panel.json", {})
    canvas = fcc.load(STATE / "field-final-eye-canvas-panel.json", {})
    eye = fcc.mod("bp_eye", "field-broadcaster-final-eye.py")
    health = eye.probe_health() if eye and hasattr(eye, "probe_health") else {"reachable": False}
    return {
        "ok": True,
        "schema": "field-broadcaster-chamber-probe/v1",
        "updated": fcc.ts(),
        "streaming": studio.get("streaming"),
        "scene_count": studio.get("scene_count"),
        "platform": studio.get("platform"),
        "canvas_connected": bool(canvas.get("connected")),
        "eye_reachable": health.get("reachable"),
        "routing": {
            "default": "straight_path",
            "look_on_demand": True,
        },
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = fcc.load(DOCTRINE, {})
    refresh = write
    studio = studio_posture(refresh=refresh)
    eye = final_eye_posture(refresh=refresh)
    codecs = codecs_posture()
    plats = platforms_doc()
    canvas = canvas_posture(refresh=refresh)
    doc = {
        "schema": "field-broadcaster-chamber-panel/v1",
        "updated": fcc.ts(),
        "ok": True,
        "ironclad_cite": doctrine.get("ironclad_cite"),
        "program": program_meta(),
        "motto": doctrine.get("motto"),
        "vision": doctrine.get("vision") or {},
        "routing": {
            "default": (doctrine.get("vision") or {}).get("default_route", "straight_path"),
            "look_on_demand": (doctrine.get("vision") or {}).get("look_on_demand", True),
            "hostess7_share_on_look": (doctrine.get("vision") or {}).get("hostess7_share_on_look", True),
            "truth_before_permanency": (doctrine.get("vision") or {}).get("truth_before_permanency", True),
        },
        "truth_gate": fcc.truth_gate(),
        "final_eye": eye,
        "canvas_wire": canvas,
        "codecs": codecs,
        "platforms": plats,
        "default_platform": plats.get("default_platform", "kick"),
        "studio": studio,
        "audio": audio_posture(),
        "streaming": studio.get("streaming"),
        "recording": studio.get("recording"),
        "active_scene": studio.get("active_scene"),
        "scene_count": studio.get("scene_count"),
        "devices": studio.get("devices"),
        "encoder": studio.get("encoder"),
        "platform": studio.get("platform"),
        "threat": studio.get("threat"),
        "routes": {
            "panel": "/field-broadcaster",
            "chamber": "/api/field-broadcaster/chamber",
            "platforms": "/api/field-broadcaster/platforms",
            "codecs": "/api/field-broadcaster/codecs",
            "final_eye": "/api/field-broadcaster/final-eye",
            "canvas": "/api/field-final-eye-canvas",
            "audio_dac": "/api/field-audio-dac",
            "go_live": "/api/field-broadcaster/go-live",
            "recordings": "/api/field-broadcaster/recordings",
            "playback": "/api/field-broadcaster/playback",
            "desktop_preview": "/api/field-broadcaster/desktop-preview",
        },
        "posture": (
            f"Broadcaster Chamber — Final_Eye→CANVAS {'linked' if canvas.get('connected') else 'standby'} · "
            f"{'live' if eye.get('reachable') else 'eye down'} · "
            f"{studio.get('scene_count', 0)} scenes · "
            f"{'ON AIR' if studio.get('streaming') else 'ready'}"
        ),
    }
    if write:
        doc["permanency"] = fcc.save_permanent(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("subaction") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel", "posture"):
        return {"ok": True, **build_panel(write=action == "panel")}

    if action in ("platforms", "list_platforms"):
        return {"ok": True, **platforms_doc()}

    if action in ("codecs", "codec_registry"):
        return codecs_posture()

    if action in ("final_eye", "vision", "eye"):
        eye = fcc.mod("bc_eye", "field-broadcaster-final-eye.py")
        if not eye:
            return {"ok": False, "error": "final_eye_missing"}
        if body.get("ensure_stream"):
            if body.get("straight") or body.get("mode") in ("straight", "straight_path"):
                fn = getattr(eye, "ensure_stream_straight", eye.ensure_stream)
                return fn(profile=str(body.get("profile") or "watch"))
            return eye.ensure_stream(profile=str(body.get("profile") or "watch"))
        return eye.vision_posture() if hasattr(eye, "vision_posture") else eye.posture()

    if action in ("look", "eye_look", "look_share"):
        eye = fcc.mod("bc_eye_look", "field-broadcaster-final-eye.py")
        if eye and hasattr(eye, "look_and_share_hostess7"):
            return eye.look_and_share_hostess7(
                prefer=str(body.get("prefer") or body.get("profile") or "auto"),
                label=str(body.get("label") or "broadcaster_look"),
            )
        canvas = fcc.mod("bc_canvas_look", "field-final-eye-canvas-bridge.py")
        if canvas and hasattr(canvas, "look_and_share_hostess7"):
            return canvas.look_and_share_hostess7(
                prefer=str(body.get("prefer") or "auto"),
                label=str(body.get("label") or "broadcaster_look"),
            )
        return {"ok": False, "error": "look_unavailable"}

    if action in ("straight_path", "straight", "path"):
        canvas = fcc.mod("bc_canvas_straight", "field-final-eye-canvas-bridge.py")
        if canvas and hasattr(canvas, "connect"):
            return canvas.connect(profile=str(body.get("profile") or "watch"), mode="straight_path")
        eye = fcc.mod("bc_eye_straight", "field-broadcaster-final-eye.py")
        if eye and hasattr(eye, "ensure_stream_straight"):
            return eye.ensure_stream_straight(profile=str(body.get("profile") or "watch"))
        return {"ok": False, "error": "straight_path_unavailable"}

    if action in ("canvas", "canvas_wire", "canvas_connect"):
        canvas = fcc.mod("bc_canvas_d", "field-final-eye-canvas-bridge.py")
        if not canvas:
            return {"ok": False, "error": "canvas_bridge_missing"}
        if action == "canvas_connect" or body.get("connect"):
            mode = str(body.get("mode") or body.get("route") or "straight_path")
            return canvas.connect(profile=str(body.get("profile") or "watch"), mode=mode)
        return canvas.posture()

    if action in ("set_platform", "platform"):
        studio = fcc.mod("bc_studio", "field-broadcaster-studio.py")
        if studio and hasattr(studio, "set_platform"):
            return studio.set_platform(
                str(body.get("platform_id") or body.get("id") or "kick"),
                stream_key=str(body.get("stream_key") or ""),
                rtmp_url=str(body.get("rtmp_url") or ""),
            )
        return {"ok": False, "error": "studio_missing"}

    if action in ("set_encoder", "encoder"):
        studio = fcc.mod("bc_studio", "field-broadcaster-studio.py")
        if studio and hasattr(studio, "set_encoder"):
            return studio.set_encoder(body)
        return {"ok": False, "error": "studio_missing"}

    if action in ("audio", "audio_dac", "dac"):
        dac = fcc.mod("bc_dac", "field-audio-dac-chamber.py")
        if dac and hasattr(dac, "dispatch"):
            return dac.dispatch(body)
        return {"ok": False, "error": "audio_dac_missing"}

    studio = fcc.mod("bc_studio", "field-broadcaster-studio.py")
    if studio and hasattr(studio, "dispatch"):
        out = studio.dispatch(body)
        if action in ("go_live", "golive", "record", "stop") and out.get("ok"):
            build_panel(write=True)
        return out

    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False))
        return 0
    if cmd == "platforms":
        print(json.dumps({"ok": True, **platforms_doc()}, ensure_ascii=False))
        return 0
    if cmd == "codecs":
        print(json.dumps(codecs_posture(), ensure_ascii=False))
        return 0
    if cmd == "meta":
        print(json.dumps({"ok": True, **program_meta()}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-broadcaster-chamber.py [json|platforms|codecs|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())