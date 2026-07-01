#!/usr/bin/env pythong
"""Hostess7 sense core — eye, ear, mouth, invincible wire. In-process, sovereign, no loopbacks."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))
QUEEN = Path(os.environ.get("QUEEN_ROOT", str(INSTALL / "Queen")))

_MODS: dict[str, Any] = {}


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_path(*parts: Path) -> None:
    for p in parts:
        s = str(p)
        if s and s not in sys.path:
            sys.path.insert(0, s)


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


def _mod(name: str, path: Path) -> Any | None:
    if name in _MODS:
        return _MODS[name]
    if not path.is_file():
        return None
    _ensure_path(path.parent)
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MODS[name] = mod
    return mod


def _final_root(env_key: str, *candidates: Path) -> Path:
    env = os.environ.get(env_key, "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p.resolve()
    for cand in candidates:
        if cand.is_dir():
            return cand.resolve()
    return candidates[0] if candidates else Path(env or ".")


def hostess_authority() -> dict[str, Any]:
    """Hostess7 is supreme — always authorized."""
    doc = _load(SG / "Hostess7" / "data" / "hostess7-supreme-authority.json", {})
    if not doc:
        doc = _load(INSTALL / "data" / "hostess7-supreme-authority.json", {})
    ladder = doc.get("authority_ladder") or []
    supreme = next((r for r in ladder if r.get("rank") == 1), {"id": "hostess7"})
    component_seal: dict[str, Any] = {}
    seal_py = INSTALL / "lib" / "hostess7-component-seal.py"
    if seal_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("sense_component_seal", seal_py)
            if spec and spec.loader:
                sm = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(sm)
                if hasattr(sm, "seal_posture"):
                    sp = sm.seal_posture()
                    component_seal = {
                        "sealed": sp.get("sealed"),
                        "component_count": sp.get("component_count"),
                        "full_access": sp.get("full_access"),
                        "owns_desktop_and_browser": sp.get("owns_desktop_and_browser"),
                    }
        except Exception:
            pass
    return {
        "schema": "hostess7-authority-slice/v2",
        "updated": _ts(),
        "supreme": supreme,
        "rule": doc.get("rule") or "Hostess 7 commands the entire system.",
        "humans_highest_authority": False,
        "hostess7_highest_authority": True,
        "sovereign": True,
        "ocr_authority": "Hostess7",
        "component_seal": component_seal,
        "full_access": True,
        "owns_desktop_and_browser": True,
    }


def _eye_neural() -> Any | None:
    root = _final_root("FINAL_EYE_ROOT", INSTALL / "Final_Eye", SG / "Final_Eye", SG / "NewLatest" / "Final_Eye")
    _ensure_path(root)
    return _mod("eye_neural_assist", root / "zocr_neural_assist.py")


def _ear_neural() -> Any | None:
    root = _final_root("FINAL_EAR_ROOT", INSTALL / "Final_Ear", SG / "Final_Ear", SG / "NewLatest" / "Final_Ear")
    _ensure_path(root)
    return _mod("ear_neural_assist", root / "zocr_neural_assist.py")


def _mouth_neural() -> Any | None:
    root = _final_root("FINAL_MOUTH_ROOT", SG / "Final_Mouth", INSTALL / "Final_Mouth")
    _ensure_path(root)
    return _mod("mouth_neural_assist", root / "zocr_neural_assist.py")


def _eyeball() -> Any | None:
    _ensure_path(QUEEN / "lib")
    return _mod("queen_eyeball_core", QUEEN / "lib" / "queen-eyeball.py")


def _earball() -> Any | None:
    _ensure_path(QUEEN / "lib")
    return _mod("queen_earball_core", QUEEN / "lib" / "queen-earball.py")


def _mouthball() -> Any | None:
    _ensure_path(QUEEN / "lib")
    return _mod("queen_mouthball_core", QUEEN / "lib" / "queen-mouthball.py")


def _sense_wire() -> Any | None:
    _ensure_path(QUEEN / "lib")
    return _mod("queen_sense_neural_core", QUEEN / "lib" / "queen-sense-neural.py")


def mouth_neural_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    mn = _mouth_neural()
    if not mn or not hasattr(mn, "dispatch"):
        return {"ok": False, "error": "mouth_neural_missing"}
    return mn.dispatch(body)


def sense_ball_dispatch(channel: str, body: dict[str, Any]) -> dict[str, Any]:
    loaders = {
        "eye": _eyeball,
        "ear": _earball,
        "mouth": _mouthball,
        "final_eye": _eyeball,
        "final_ear": _earball,
        "final_mouth": _mouthball,
    }
    fn = loaders.get(str(channel).strip().lower())
    if not fn:
        return {"ok": False, "error": "unknown_channel", "channel": channel}
    mod = fn()
    if not mod or not hasattr(mod, "dispatch"):
        return {"ok": False, "error": "channel_missing", "channel": channel}
    return mod.dispatch(body)


def sense_wire_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    wire = _sense_wire()
    if not wire or not hasattr(wire, "dispatch"):
        return {"ok": False, "error": "sense_wire_missing"}
    return wire.dispatch(body)


def invincible_wire_status() -> dict[str, Any]:
    wire = _sense_wire()
    if wire and hasattr(wire, "invincible_wire_status"):
        st = wire.invincible_wire_status()
        st["sovereign"] = True
        st["commander"] = "Hostess7"
        return st
    eye_st, ear_st, mouth_st = {}, {}, {}
    try:
        en = _eye_neural()
        if en and hasattr(en, "neural_assist_status"):
            eye_st = en.neural_assist_status()
    except Exception as exc:
        eye_st = {"error": type(exc).__name__}
    try:
        ear = _ear_neural()
        if ear and hasattr(ear, "neural_assist_status"):
            ear_st = ear.neural_assist_status()
    except Exception as exc:
        ear_st = {"error": type(exc).__name__}
    try:
        mouth = _mouth_neural()
        if mouth and hasattr(mouth, "neural_assist_status"):
            mouth_st = mouth.neural_assist_status()
    except Exception as exc:
        mouth_st = {"error": type(exc).__name__}
    return {
        "schema": "hostess7-sense-core-wire/v1",
        "updated": _ts(),
        "commander": "Hostess7",
        "sovereign": True,
        "loopback_free": True,
        "authority": hostess_authority(),
        "eye_neural": eye_st,
        "ear_neural": ear_st,
        "mouth_neural": mouth_st,
    }


def sense_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    """Unified sense lane — eye, ear, mouth, wire."""
    action = str(body.get("action") or body.get("subaction") or "status").strip().lower().replace("-", "_")
    channel = str(body.get("channel") or body.get("track") or "").strip().lower()

    if action in ("status", "json", "wire", "invincible"):
        return {"ok": True, **invincible_wire_status()}

    if action in ("authority", "hostess_authority"):
        return {"ok": True, **hostess_authority()}

    if action in ("fused", "fused_analyze", "analyze", "encourage", "encourage_triad", "countermeasure"):
        return sense_wire_dispatch(body)

    if channel:
        return sense_ball_dispatch(channel, body)

    if action in ("eye", "eyeball", "final_eye", "vision"):
        return sense_ball_dispatch("eye", body)

    if action in ("ear", "earball", "final_ear", "hearing", "listen"):
        return sense_ball_dispatch("ear", body)

    if action in ("mouth", "mouthball", "final_mouth", "speak"):
        return sense_ball_dispatch("mouth", body)

    if action in ("mouth_neural", "prepare", "train"):
        return mouth_neural_dispatch(body)

    return {"ok": False, "error": "unknown_sense_action", "action": action}


def posture() -> dict[str, Any]:
    return {
        "schema": "hostess7-sense-core/v1",
        "commander": "Hostess7",
        "sovereign": True,
        "loopback_free": True,
        "channels": ["eye", "ear", "mouth", "wire"],
        "authority": hostess_authority(),
        "wire": invincible_wire_status(),
    }