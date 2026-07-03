#!/usr/bin/env pythong
"""Broadcaster sense drivers — Final_Eye · Final_Ear · Final_Mouth → OBS source catalog."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-broadcaster-senses-doctrine.json"
STACK = STATE / "field-broadcaster-senses-stack.json"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _eye_slice() -> dict[str, Any]:
    eye = _mod("bc_senses_eye", "lib/field-broadcaster-final-eye.py")
    if not eye:
        return {"ok": False, "driver": "final_eye", "error": "eye_module_missing"}
    health = eye.probe_health() if hasattr(eye, "probe_health") else {}
    posture = eye.vision_posture() if hasattr(eye, "vision_posture") else {}
    mjpeg = eye.mjpeg_url() if hasattr(eye, "mjpeg_url") else ""
    return {
        "ok": bool(health.get("reachable") or posture.get("ok")),
        "driver": "final_eye",
        "product": "Final_Eye",
        "role": "camera_and_display",
        "reachable": bool(health.get("reachable")),
        "base_url": getattr(eye, "final_eye_base_url", lambda: "")(),
        "port": getattr(eye, "final_eye_port", lambda: 9479)(),
        "mjpeg": mjpeg,
        "preview": eye.preview_url() if hasattr(eye, "preview_url") else "",
        "obs": {
            "id": "browser_source",
            "name": "Final_Eye · Vision",
            "settings": {
                "url": mjpeg or "http://127.0.0.1:9479/api/stream/mjpeg?profile=watch",
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "shutdown": False,
            },
        },
        "cameras": eye.list_cameras() if hasattr(eye, "list_cameras") else [],
        "displays": eye.list_displays() if hasattr(eye, "list_displays") else [],
    }


def _default_pulse(kind: str) -> str:
    fcc = _mod("bc_senses_fcc", "lib/field-chamber-core.py")
    if fcc and hasattr(fcc, "default_device"):
        return str(fcc.default_device(kind) or "")
    return ""


def _ear_slice() -> dict[str, Any]:
    ear_block = _mod("bc_senses_ear", "lib/field-final-ear-block.py")
    earball = None
    queen_ear = INSTALL / "Queen" / "lib" / "queen-earball.py"
    if queen_ear.is_file():
        try:
            earball = _mod("bc_senses_earball", str(queen_ear.relative_to(INSTALL)))
        except Exception as exc:
            earball = None
            earball_load_error = str(exc)
        else:
            earball_load_error = ""
    else:
        earball_load_error = ""
    present = bool(
        (SG / "Final_Ear").is_dir()
        or (INSTALL / "Final_Ear").is_dir()
        or os.environ.get("FINAL_EAR_ROOT", "").strip()
    )
    device = _default_pulse("source")
    slice_doc: dict[str, Any] = {
        "ok": present,
        "driver": "final_ear",
        "product": "Final_Ear",
        "role": "audio_input",
        "present": present,
        "pulse_device": device,
        "obs": {
            "id": "pulse_input_capture",
            "name": "Final_Ear · Hear",
            "settings": {"device_id": device or "default"},
        },
    }
    if ear_block and hasattr(ear_block, "publish_panel"):
        try:
            panel = ear_block.publish_panel()
            slice_doc["block"] = {"sealed": panel.get("sealed"), "facet": panel.get("facet")}
        except Exception as exc:
            slice_doc["block_error"] = str(exc)
    if earball_load_error:
        slice_doc["earball_error"] = earball_load_error
    if earball and hasattr(earball, "dispatch"):
        try:
            st = earball.dispatch({"action": "status"})
            slice_doc["earball"] = {"ok": st.get("ok", True), "schema": st.get("schema")}
        except Exception as exc:
            slice_doc["earball_error"] = str(exc)
    return slice_doc


def _mouth_slice() -> dict[str, Any]:
    present = bool(
        (SG / "Final_Mouth").is_dir()
        or (INSTALL / "Final_Mouth").is_dir()
        or os.environ.get("FINAL_MOUTH_ROOT", "").strip()
    )
    sink = _default_pulse("sink")
    slice_doc: dict[str, Any] = {
        "ok": present,
        "driver": "final_mouth",
        "product": "Final_Mouth",
        "role": "voice_output_monitor",
        "present": present,
        "pulse_sink": sink,
        "obs": {
            "id": "pulse_output_capture",
            "name": "Final_Mouth · Voice",
            "settings": {"device_id": sink or "default"},
        },
    }
    mouth = _mod("bc_senses_mouth", "lib/hostess7-mouth-neural.py")
    if mouth and hasattr(mouth, "posture"):
        try:
            slice_doc["neural"] = mouth.posture()
        except Exception as exc:
            slice_doc["neural_error"] = str(exc)
    return slice_doc


def _sense_wire() -> dict[str, Any]:
    core = _mod("bc_senses_core", "lib/hostess7-sense-core.py")
    if core and hasattr(core, "invincible_wire_status"):
        try:
            return core.invincible_wire_status()
        except Exception:
            pass
    return {"ok": False, "error": "sense_wire_missing"}


def obs_source_catalog() -> list[dict[str, Any]]:
    eye = _eye_slice()
    ear = _ear_slice()
    mouth = _mouth_slice()
    out: list[dict[str, Any]] = []
    if eye.get("obs"):
        out.append({**eye["obs"], "driver": "final_eye", "enabled": eye.get("reachable", True)})
    if ear.get("obs"):
        out.append({**ear["obs"], "driver": "final_ear", "enabled": ear.get("present", False)})
    if mouth.get("obs"):
        out.append({**mouth["obs"], "driver": "final_mouth", "enabled": mouth.get("present", False)})
    return out


def posture() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    eye = _eye_slice()
    ear = _ear_slice()
    mouth = _mouth_slice()
    wire = _sense_wire()
    sources = obs_source_catalog()
    return {
        "schema": "field-broadcaster-senses/v1",
        "ts": _ts(),
        "ok": True,
        "product": doc.get("product") or "Broadcaster",
        "motto": doc.get("motto"),
        "fork": doc.get("fork") or {},
        "final_eye": eye,
        "final_ear": ear,
        "final_mouth": mouth,
        "sense_wire": wire,
        "obs_sources": sources,
        "security": doc.get("security") or {},
        "localhost_only": True,
    }


def write_stack(*, portable_dir: Path | None = None) -> dict[str, Any]:
    doc = posture()
    portable = portable_dir or Path(
        os.environ.get("FIELD_BROADCASTER_PORTABLE_DIR", str(STATE / "field-broadcaster-portable"))
    )
    portable.mkdir(parents=True, exist_ok=True)
    stack_path = portable / "field-broadcaster-senses-stack.json"
    stack_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STACK.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    doc["stack_path"] = str(stack_path)
    doc["written"] = True
    return doc


def launch_env() -> dict[str, str]:
    eye = _eye_slice()
    return {
        "FINAL_EYE_HOST": os.environ.get("FINAL_EYE_HOST", "127.0.0.1"),
        "FINAL_EYE_PORT": str(eye.get("port") or os.environ.get("FINAL_EYE_PORT", "9479")),
        "FINAL_EYE_ROOT": os.environ.get("FINAL_EYE_ROOT", str(SG / "Final_Eye")),
        "FINAL_EAR_ROOT": os.environ.get("FINAL_EAR_ROOT", str(SG / "Final_Ear")),
        "FINAL_MOUTH_ROOT": os.environ.get("FINAL_MOUTH_ROOT", str(SG / "Final_Mouth")),
        "BROADCASTER_PRODUCT": "Broadcaster",
        "FIELD_BROADCASTER_SENSES": "1",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("write", "stack", "publish"):
        print(json.dumps(write_stack(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sources":
        print(json.dumps({"ok": True, "sources": obs_source_catalog()}, ensure_ascii=False, indent=2))
        return 0
    print("usage: field-broadcaster-senses.py [json|write|sources]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())