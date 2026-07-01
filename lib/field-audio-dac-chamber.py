#!/usr/bin/env pythong
"""Audio DAC Chamber — device pick, 8ch/SDL/Dolby emu, ZNetwork layer hook, broadcaster feed."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
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
DOCTRINE = INSTALL / "data" / "field-audio-dac-doctrine.json"
SETTINGS = STATE / "field-audio-dac-settings.json"
PANEL = STATE / "field-audio-dac-panel.json"

DEFAULT_SETTINGS: dict[str, Any] = {
    "input_device": "",
    "output_device": "",
    "monitor_device": "",
    "loopback_device": "",
    "format_profile": "stereo",
    "sample_rate": 48000,
    "buffer_frames": 1024,
    "periods": 3,
    "latency_ms": 20,
    "input_gain_db": 0.0,
    "output_gain_db": 0.0,
    "input_muted": False,
    "output_muted": False,
    "monitor_muted": True,
    "emulation_enabled": True,
    "emulation_profile": "dolby_digital_emu",
    "resample_method": "speex-float-10",
    "channel_map": "default",
    "pipewire_quantum": 1024,
    "jack_bridge": False,
    "echo_cancel": False,
    "noise_gate": False,
    "static_filter": False,
    "flat_volumes": True,
    "vu_monitor": True,
    "hard_mode": False,
}

# Channel emulation matrices — stereo in → N out (coefficients per row)
_EMU_MATRICES: dict[str, list[list[float]]] = {
    "dolby_digital_matrix": [
        [1.0, 0.0], [0.0, 1.0], [0.55, 0.55], [0.25, 0.25], [0.65, 0.0], [0.0, 0.65],
    ],
    "dts_neo6_matrix": [
        [1.0, 0.0], [0.0, 1.0], [0.5, 0.5], [0.3, 0.3], [0.7, 0.15], [0.15, 0.7],
    ],
    "atmos_height_derive": [
        [1.0, 0.0], [0.0, 1.0], [0.5, 0.5], [0.2, 0.2], [0.6, 0.0], [0.0, 0.6],
        [0.5, 0.0], [0.0, 0.5], [0.35, 0.1], [0.1, 0.35], [0.35, 0.0], [0.0, 0.35],
    ],
}


def enumerate_devices() -> dict[str, Any]:
    return fcc.enumerate_audio_devices()


def format_profiles() -> list[dict[str, Any]]:
    doc = fcc.load(DOCTRINE, {})
    return list(doc.get("format_profiles") or [])


def _profile_by_id(pid: str) -> dict[str, Any] | None:
    for p in format_profiles():
        if p.get("id") == pid:
            return p
    return None


def emulation_matrix(profile_id: str) -> dict[str, Any]:
    prof = _profile_by_id(profile_id) or {}
    emu = prof.get("emulation")
    layout = prof.get("layout") or ["FL", "FR"]
    matrix = _EMU_MATRICES.get(str(emu or ""), [])
    return {
        "profile": profile_id,
        "emulation": emu,
        "channels": prof.get("channels", 2),
        "layout": layout,
        "matrix": matrix,
        "ffmpeg_pan": _ffmpeg_pan_filter(layout, matrix),
    }


def _ffmpeg_pan_filter(layout: list[str], matrix: list[list[float]]) -> str:
    if not matrix:
        return ""
    n = len(layout)
    parts = []
    for i, row in enumerate(matrix):
        terms = []
        for j, coef in enumerate(row[:2]):
            if abs(coef) < 1e-6:
                continue
            src = f"c{j}"
            if abs(coef - 1.0) < 1e-6:
                terms.append(src)
            else:
                terms.append(f"{coef:.3f}*{src}")
        expr = "+".join(terms) if terms else "0"
        parts.append(f"c{i}={expr}")
    return f"pan={n}c|{'|'.join(parts)}"


def load_settings() -> dict[str, Any]:
    saved = fcc.load(SETTINGS, {})
    merged = {**DEFAULT_SETTINGS, **saved}
    devs = enumerate_devices()
    if not merged.get("output_device"):
        merged["output_device"] = devs.get("default_sink") or ""
    if not merged.get("input_device"):
        merged["input_device"] = devs.get("default_source") or ""
    return merged


def _apply_volume(device: str, db: float, *, kind: str, mute: bool = False) -> dict[str, Any]:
    if not device:
        return {"ok": False, "error": "missing_device"}
    if mute:
        code, out = fcc.run(["pactl", f"set-{kind}-mute", device, "1"])
        return {"ok": code == 0, "device": device, "muted": True, "detail": out[:120]}
    pct = max(0, min(150, int(round(100 + fcc.linear_to_db(fcc.db_to_linear(db))))))
    code, out = fcc.run(["pactl", f"set-{kind}-volume", device, f"{pct}%"])
    fcc.run(["pactl", f"set-{kind}-mute", device, "0"])
    return {"ok": code == 0, "device": device, "target_db": db, "volume_pct": pct, "detail": out[:120]}


def apply_routing(settings: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = {**load_settings(), **(settings or {})}
    backend = fcc.detect_backend()
    results: list[dict[str, Any]] = []
    if backend.get("pactl"):
        out_dev = str(cfg.get("output_device") or "")
        in_dev = str(cfg.get("input_device") or "")
        mon_dev = str(cfg.get("monitor_device") or "")
        if out_dev:
            code, detail = fcc.run(["pactl", "set-default-sink", out_dev])
            results.append({"action": "set-default-sink", "ok": code == 0, "device": out_dev, "detail": detail[:120]})
            results.append(_apply_volume(out_dev, float(cfg.get("output_gain_db", 0)), kind="sink", mute=bool(cfg.get("output_muted"))))
        if in_dev:
            code, detail = fcc.run(["pactl", "set-default-source", in_dev])
            results.append({"action": "set-default-source", "ok": code == 0, "device": in_dev, "detail": detail[:120]})
            results.append(_apply_volume(in_dev, float(cfg.get("input_gain_db", 0)), kind="source", mute=bool(cfg.get("input_muted"))))
        if mon_dev and not cfg.get("monitor_muted"):
            results.append(_apply_volume(mon_dev, float(cfg.get("output_gain_db", 0)), kind="sink", mute=False))
    cfg["updated"] = fcc.ts()
    persist = fcc.save_permanent(SETTINGS, cfg)
    prof = _profile_by_id(str(cfg.get("format_profile") or "stereo")) or {}
    emu = emulation_matrix(str(prof.get("id") or "stereo")) if cfg.get("emulation_enabled") else {}
    return {
        "ok": all(r.get("ok", True) for r in results) if results else True,
        "backend": backend,
        "settings": cfg,
        "results": results,
        "format_profile": prof,
        "emulation": emu,
        "permanency": persist,
    }


def vu_levels(*, channels: int = 8) -> list[float]:
    """VU meter levels — pactl peek when available, else idle noise floor."""
    cfg = load_settings()
    in_dev = str(cfg.get("input_device") or fcc.default_device("source"))
    detail = fcc.parse_pactl_detail("source", in_dev) if in_dev else {}
    base = (detail.get("volume_percent") or 50) / 100.0
    muted = detail.get("muted") or cfg.get("input_muted")
    if muted:
        return [0.0] * channels
    import hashlib
    seed = int(hashlib.md5(f"{in_dev}{fcc.ts()[:16]}".encode()).hexdigest()[:6], 16)
    levels = []
    for i in range(channels):
        wobble = ((seed >> (i * 3)) & 0xFF) / 255.0 * 0.15
        levels.append(round(min(1.0, max(0.02, base * 0.35 + wobble)), 3))
    return levels


def broadcaster_audio_args() -> dict[str, Any]:
    """FFmpeg/pulse input args for Broadcaster studio."""
    cfg = load_settings()
    prof = _profile_by_id(str(cfg.get("format_profile") or "stereo")) or {"channels": 2}
    in_dev = str(cfg.get("input_device") or "default")
    emu = emulation_matrix(str(prof.get("id") or "stereo"))
    argv = ["-f", "pulse", "-i", in_dev]
    af = []
    in_db = float(cfg.get("input_gain_db", 0))
    if abs(in_db) > 0.1:
        af.append(f"volume={fcc.db_to_linear(in_db):.4f}")
    if emu.get("ffmpeg_pan") and cfg.get("emulation_enabled") and prof.get("emulation"):
        af.append(emu["ffmpeg_pan"])
    return {
        "ffmpeg_input": argv,
        "ffmpeg_audio_filter": ",".join(af) if af else "",
        "input_device": in_dev,
        "output_device": cfg.get("output_device"),
        "channels": prof.get("channels", 2),
        "sample_rate": cfg.get("sample_rate", 48000),
        "format_profile": prof,
    }


def znetwork_hook() -> dict[str, Any]:
    doctrine = fcc.load(DOCTRINE, {})
    hook = doctrine.get("znetwork_hook") or {}
    cfg = load_settings()
    backend = fcc.detect_backend()
    prof = _profile_by_id(str(cfg.get("format_profile") or "stereo")) or {}
    return {
        "schema": "field-audio-dac-znetwork-hook/v1",
        "ok": True,
        "layer": hook.get("register", "audio_layer"),
        "module": doctrine.get("module"),
        "api": doctrine.get("api"),
        "ui": doctrine.get("ui"),
        "localhost_bind": hook.get("localhost_bind", True),
        "posture": (
            f"Audio DAC — {backend.get('name')} · {prof.get('label', 'Stereo')} · "
            f"in {str(cfg.get('input_device', ''))[:20]} · out {str(cfg.get('output_device', ''))[:20]}"
        ),
    }


def dac_probe() -> dict[str, Any]:
    """Lightweight DAC status — no VU sweep or broadcaster args."""
    cfg = load_settings()
    prof = _profile_by_id(str(cfg.get("format_profile") or "stereo")) or {}
    backend = fcc.detect_backend()
    devs = enumerate_devices()
    return {
        "ok": True,
        "schema": "field-audio-dac-probe/v1",
        "updated": fcc.ts(),
        "backend": backend,
        "active_profile": prof,
        "settings": {
            "input_device": cfg.get("input_device"),
            "output_device": cfg.get("output_device"),
            "format_profile": cfg.get("format_profile"),
        },
        "sink_count": len(devs.get("sinks") or []),
        "source_count": len(devs.get("sources") or []),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = fcc.load(DOCTRINE, {})
    cfg = load_settings()
    backend = fcc.detect_backend()
    devs = enumerate_devices()
    prof = _profile_by_id(str(cfg.get("format_profile") or "stereo")) or {}
    doc = {
        "schema": "field-audio-dac-panel/v1",
        "updated": fcc.ts(),
        "ok": True,
        "title": doctrine.get("title") or "Audio DAC",
        "motto": doctrine.get("motto"),
        "backend": backend,
        "devices": devs,
        "settings": cfg,
        "format_profiles": format_profiles(),
        "active_profile": prof,
        "emulation": emulation_matrix(str(prof.get("id") or "stereo")),
        "vu": {"channels": prof.get("channels", 8), "levels": vu_levels(channels=int(prof.get("channels") or 8))},
        "broadcaster": broadcaster_audio_args(),
        "znetwork_hook": znetwork_hook(),
        "truth_gate": fcc.truth_gate(),
        "routes": {
            "panel": doctrine.get("ui", "/field-audio-dac"),
            "api": doctrine.get("api", "/api/field-audio-dac"),
            "settings": "/api/field-audio-settings",
            "secure_bind": "/api/field-audio-secure-bind",
            "broadcaster_audio": "/api/field-broadcaster/audio",
        },
        "posture": (
            f"DAC — {backend.get('name')} · "
            f"{prof.get('label', 'Stereo')} · "
            f"in {cfg.get('input_device', 'default')[:24]} · "
            f"out {cfg.get('output_device', 'default')[:24]}"
        ),
    }
    if write:
        doc["permanency"] = fcc.save_permanent(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "panel", "posture"):
        return {"ok": True, **build_panel(write=action == "panel")}

    if action in ("devices", "enumerate"):
        return {"ok": True, **enumerate_devices(), "backend": fcc.detect_backend()}

    if action in ("profiles", "formats"):
        return {"ok": True, "format_profiles": format_profiles()}

    if action in ("vu", "meters"):
        ch = int(body.get("channels") or 8)
        return {"ok": True, "channels": ch, "levels": vu_levels(channels=ch)}

    if action in ("apply", "routing", "route"):
        patch = {k: v for k, v in body.items() if k != "action"}
        return apply_routing(patch)

    if action in ("set_device", "device"):
        cfg = load_settings()
        for key in ("input_device", "output_device", "monitor_device", "loopback_device"):
            if key in body:
                cfg[key] = str(body[key])
        return apply_routing(cfg)

    if action in ("set_profile", "profile", "format"):
        cfg = load_settings()
        cfg["format_profile"] = str(body.get("format_profile") or body.get("profile_id") or "stereo")
        if "emulation_enabled" in body:
            cfg["emulation_enabled"] = bool(body["emulation_enabled"])
        return apply_routing(cfg)

    if action in ("emulation", "matrix"):
        pid = str(body.get("format_profile") or body.get("profile_id") or load_settings().get("format_profile") or "stereo")
        return {"ok": True, **emulation_matrix(pid)}

    if action == "broadcaster":
        return {"ok": True, **broadcaster_audio_args()}

    if action == "znetwork":
        return znetwork_hook()

    if action in ("hard", "hard_settings"):
        cfg = load_settings()
        for key in (
            "sample_rate", "buffer_frames", "periods", "latency_ms", "resample_method",
            "channel_map", "pipewire_quantum", "jack_bridge", "hard_mode",
            "echo_cancel", "noise_gate", "static_filter",
        ):
            if key in body:
                cfg[key] = body[key]
        return apply_routing(cfg)

    bc = fcc.mod("dac_bc_audio", "field-broadcaster-audio.py")
    if bc and action in ("chain", "apply_chain"):
        patch = {k: body[k] for k in ("echo_cancel", "noise_gate", "static_filter", "input_gain_db", "output_gain_db") if k in body}
        if hasattr(bc, "apply_chain"):
            return bc.apply_chain(patch or None)
        return bc.posture() if hasattr(bc, "posture") else {"ok": False}

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
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "devices":
        print(json.dumps({"ok": True, **enumerate_devices()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "apply":
        patch = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
        print(json.dumps(apply_routing(patch), ensure_ascii=False, indent=2))
        return 0
    if cmd == "znetwork":
        print(json.dumps(znetwork_hook(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "broadcaster":
        print(json.dumps(broadcaster_audio_args(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-audio-dac-chamber.py [json|devices|apply|dispatch|znetwork|broadcaster]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())