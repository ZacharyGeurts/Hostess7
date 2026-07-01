#!/usr/bin/env pythong
"""Final_Eye → Queen CANVAS secure wire — sealed localhost egress, threat-gated."""
from __future__ import annotations

import importlib.util
import json
import os
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
DOCTRINE = INSTALL / "data" / "field-final-eye-canvas-doctrine.json"
LINK = STATE / "field-final-eye-canvas-link.json"
PANEL = STATE / "field-final-eye-canvas-panel.json"


def egress_allowed() -> dict[str, Any]:
    """Final_Eye egress mandate — localhost only unless operator explicitly opens."""
    host = os.environ.get("ZOCR_STREAM_EGRESS", os.environ.get("FINAL_EYE_EGRESS_HOST", "127.0.0.1")).strip()
    localhost = host in ("127.0.0.1", "localhost", "::1")
    kill = os.environ.get("ZOCR_KILL_EGRESS", "0") in ("1", "true", "yes")
    return {
        "ok": localhost and not kill,
        "host": host,
        "localhost_only": localhost,
        "kill_tripped": kill,
        "policy": "sealed_localhost_egress",
    }


def _canvas_posture() -> dict[str, Any]:
    paths = [
        INSTALL / "Queen" / "lib" / "queen-canvas-renderer.py",
        INSTALL.parent / "Queen" / "lib" / "queen-canvas-renderer.py",
    ]
    for path in paths:
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("qcanvas_bridge", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "posture"):
                    return mod.posture()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": "queen_canvas_renderer_missing"}


def _final_eye_probe() -> dict[str, Any]:
    eye = fcc.mod("fec_eye", "field-broadcaster-final-eye.py")
    if eye and hasattr(eye, "eye_probe"):
        return eye.eye_probe()
    if eye and hasattr(eye, "probe_health"):
        health = eye.probe_health()
        return {"ok": health.get("reachable"), "reachable": health.get("reachable")}
    return {"ok": False, "error": "final_eye_module_missing"}


def canvas_probe() -> dict[str, Any]:
    """Lightweight wire status — no recursive eye/canvas posture."""
    link = fcc.load(LINK, {})
    eye = _final_eye_probe()
    egress = egress_allowed()
    feed = feed_descriptor(mode=str(link.get("mode") or "straight_path"))
    return {
        "ok": bool(eye.get("reachable") and egress.get("ok")),
        "schema": "field-final-eye-canvas-probe/v1",
        "updated": fcc.ts(),
        "connected": bool(link.get("connected")),
        "mode": link.get("mode") or "straight_path",
        "look_in_path": bool(link.get("look_in_path")),
        "final_eye": eye,
        "feed": feed,
        "egress": egress,
    }


def _threat_gate() -> dict[str, Any]:
    bridge = INSTALL / "lib" / "obs-threat-posterity-bridge.py"
    if not bridge.is_file():
        return {"ok": True, "skipped": True}
    try:
        spec = importlib.util.spec_from_file_location("fec_threat", bridge)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "panel_json"):
                doc = mod.panel_json()
                summary = (doc.get("threat_ledger") or {}).get("summary") or {}
                blocked = int(summary.get("harm_candidate") or summary.get("blocked") or 0)
                return {"ok": blocked == 0, "blocked": blocked, "summary": summary}
    except Exception:
        pass
    return {"ok": True}


def feed_descriptor(*, profile: str = "watch", mode: str = "straight_path") -> dict[str, Any]:
    eye = fcc.mod("fec_eye2", "field-broadcaster-final-eye.py")
    mjpeg = eye.mjpeg_url(profile=profile) if eye and hasattr(eye, "mjpeg_url") else ""
    port = eye.final_eye_port() if eye and hasattr(eye, "final_eye_port") else 9479
    canvas = _canvas_posture()
    egress = egress_allowed()
    route = "straight_path" if mode in ("straight", "straight_path", "default", "") else "look_path"
    return {
        "schema": "field-final-eye-canvas-feed/v1",
        "mode": route,
        "look_in_path": route == "look_path",
        "ingress": {
            "product": "Final_Eye",
            "mjpeg": mjpeg,
            "preview": eye.preview_url() if eye and hasattr(eye, "preview_url") else "",
            "port": port,
        },
        "egress": {
            "product": "Queen CANVAS",
            "shader": canvas.get("default_canvas", "CANVAS"),
            "api": "/api/queen-canvas-renderer",
            "stack_layer": (canvas.get("stack_layer") or {}).get("id", "queen_canvas"),
        },
        "secure": {
            "localhost_only": egress.get("localhost_only"),
            "egress_host": egress.get("host"),
            "seal": "GVC1+aes_gcm_or_hmac",
            "kill_respected": not egress.get("kill_tripped"),
        },
    }


def look_and_share_hostess7(*, prefer: str = "auto", label: str = "broadcaster_look") -> dict[str, Any]:
    """Final_Eye look on demand — truth-gated share with Hostess 7 (not on the hot path)."""
    eye = fcc.mod("fec_eye_look", "field-broadcaster-final-eye.py")
    if eye and hasattr(eye, "look_and_share_hostess7"):
        return eye.look_and_share_hostess7(prefer=prefer, label=label)
    ocr = fcc.mod("fec_ocr_look", "final-eye-ocr-core.py")
    if ocr and hasattr(ocr, "ocr_via_hostess7"):
        look = ocr.ocr_via_hostess7(
            {"action": "final_eye", "subaction": "look", "prefer": prefer, "label": label}
        )
        return {
            "ok": bool(look.get("ok")),
            "mode": "look_path",
            "look": look,
            "hostess7": {"shared": bool(look.get("ok")), "consumer": "Hostess7", "handshake_only": True},
        }
    return {"ok": False, "error": "look_unavailable", "hostess7": {"shared": False, "reason": "h7_lane_missing"}}


def connect(*, profile: str = "watch", force: bool = False, mode: str = "straight_path") -> dict[str, Any]:
    """Establish secure Final_Eye → CANVAS wire — straight path by default (no look in hot path)."""
    doctrine = fcc.load(DOCTRINE, {})
    route = "straight_path" if mode in ("straight", "straight_path", "default", "") else "look_path"
    egress = egress_allowed()
    if not egress.get("ok") and not force:
        return {"ok": False, "error": "egress_denied", "egress": egress}
    threat = _threat_gate()
    if not threat.get("ok"):
        return {"ok": False, "error": "threat_blocked", "threat": threat}
    eye = fcc.mod("fec_eye3", "field-broadcaster-final-eye.py")
    stream_out: dict[str, Any] = {}
    look_out: dict[str, Any] = {}
    if route == "look_path":
        look_out = look_and_share_hostess7(prefer=str(profile), label="canvas_connect_look")
        if eye and hasattr(eye, "ensure_stream"):
            stream_out = eye.ensure_stream(profile=profile)
    elif eye and hasattr(eye, "ensure_stream_straight"):
        stream_out = eye.ensure_stream_straight(profile=profile)
    elif eye and hasattr(eye, "ensure_stream"):
        stream_out = eye.ensure_stream(profile=profile)
    canvas = _canvas_posture()
    feed = feed_descriptor(profile=profile, mode=route)
    link = {
        "schema": "field-final-eye-canvas-link/v1",
        "updated": fcc.ts(),
        "connected": bool(stream_out.get("ok", True) and canvas.get("ok")),
        "profile": profile,
        "mode": route,
        "look_in_path": route == "look_path",
        "feed": feed,
        "final_eye_stream": stream_out,
        "final_eye_look": look_out if route == "look_path" else None,
        "canvas": {
            "ok": canvas.get("ok"),
            "default_canvas": canvas.get("default_canvas"),
            "stack_layer": canvas.get("stack_layer"),
        },
        "egress": egress,
        "threat": threat,
        "ironclad_cite": doctrine.get("ironclad_cite"),
    }
    persist = fcc.save_permanent(LINK, link)
    link["permanency"] = persist
    if not persist.get("saved"):
        link["ephemeral"] = True
    return {"ok": link["connected"], **link}


def posture() -> dict[str, Any]:
    doctrine = fcc.load(DOCTRINE, {})
    link = fcc.load(LINK, {})
    eye = _final_eye_probe()
    canvas = _canvas_posture()
    egress = egress_allowed()
    threat = _threat_gate()
    feed = feed_descriptor()
    route = link.get("mode") or (doctrine.get("policy") or {}).get("default_mode", "straight_path")
    doc = {
        "schema": "field-final-eye-canvas-panel/v1",
        "updated": fcc.ts(),
        "ok": bool(eye.get("reachable") and canvas.get("ok") and egress.get("ok")),
        "motto": doctrine.get("motto"),
        "connected": bool(link.get("connected")),
        "mode": route,
        "look_in_path": bool(link.get("look_in_path")),
        "routing": doctrine.get("routing") or {},
        "link": link,
        "feed": feed,
        "final_eye": eye,
        "canvas": canvas,
        "egress": egress,
        "threat": threat,
        "truth_gate": fcc.truth_gate(),
        "policy": doctrine.get("policy") or {},
        "routes": {
            "connect": "/api/field-final-eye-canvas/connect",
            "feed": "/api/field-final-eye-canvas/feed",
            "look": "/api/field-broadcaster/chamber",
            "canvas": "/api/queen-canvas-renderer",
            "final_eye_mjpeg": feed.get("ingress", {}).get("mjpeg"),
        },
        "posture": (
            f"{'straight path' if route == 'straight_path' else 'look path'} → CANVAS — "
            f"{'linked' if link.get('connected') else 'standby'} · "
            f"egress {egress.get('host')} · shader {canvas.get('default_canvas', 'CANVAS')}"
        ),
    }
    persist = fcc.save_permanent(PANEL, doc)
    doc["permanency"] = persist
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "posture", "panel"):
        return {"ok": True, **posture()}
    if action in ("connect", "link", "wire"):
        mode = str(body.get("mode") or body.get("route") or "straight_path")
        return connect(profile=str(body.get("profile") or "watch"), force=bool(body.get("force")), mode=mode)
    if action in ("feed", "descriptor", "straight_path", "straight"):
        mode = "look_path" if action == "look" else str(body.get("mode") or "straight_path")
        return {"ok": True, **feed_descriptor(profile=str(body.get("profile") or "watch"), mode=mode)}
    if action in ("look", "eye_look", "look_share"):
        return look_and_share_hostess7(
            prefer=str(body.get("prefer") or body.get("profile") or "auto"),
            label=str(body.get("label") or "broadcaster_look"),
        )
    if action == "egress":
        return {"ok": True, **egress_allowed()}
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
    if cmd in ("json", "posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "connect":
        print(json.dumps(connect(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "feed":
        print(json.dumps(feed_descriptor(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-final-eye-canvas-bridge.py [json|connect|feed|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())