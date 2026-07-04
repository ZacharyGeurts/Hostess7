#!/usr/bin/env pythong
"""Field Audio Settings — shell music icon facade over Audio DAC chamber."""
from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("fcc", _LIB / "field-chamber-core.py")
fcc = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(fcc)

INSTALL = fcc.INSTALL
STATE_DIR = fcc.STATE
SETTINGS_PATH = STATE_DIR / "field-audio-settings.json"
PANEL_PATH = STATE_DIR / "field-audio-settings-panel.json"

DEFAULT_SETTINGS = {
    "advanced": False,
    "quality": "high",
    "format_profile": "surround_8ch",
    "soundcard_id": "host-live",
    "subwoofer": True,
    "dolby_emu": True,
    "default_sink": "",
    "default_source": "",
    "sink_volume": 1.0,
    "source_volume": 1.0,
    "sink_muted": False,
    "source_muted": False,
    "latency_ms": 0,
    "resample_method": "speex-float-10",
    "channel_map": "default",
    "jack_bridge": False,
    "echo_cancel": False,
    "noise_suppression": False,
    "agc": False,
    "sample_rate": 48000,
    "buffer_size": 1024,
    "periods": 3,
    "alsa_card": "default",
    "pipewire_quantum": 1024,
    "pipewire_rate": 48000,
    "monitor_sources": True,
    "flat_volumes": True,
    "rtp_latency": 200,
    "network_audio": False,
}


def _load_settings() -> dict[str, Any]:
    saved = fcc.load(SETTINGS_PATH, {})
    merged = dict(DEFAULT_SETTINGS)
    if isinstance(saved, dict):
        merged.update(saved)
    return merged


def _save_settings(data: dict[str, Any]) -> dict[str, Any]:
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    fcc.save_atomic(SETTINGS_PATH, merged)
    return merged


def _dac_mod() -> Any | None:
    return fcc.mod("fa_settings_dac", "field-audio-dac-chamber.py")


def _vintage_mod() -> Any | None:
    return fcc.mod("fa_vintage_audio", "field-vintage-audio-composite.py")


def _hdmi_mod() -> Any | None:
    return fcc.mod("fa_hdmi_audio", "field-hdmi-audio-driver.py")


def _advanced_block(settings: dict[str, Any], backend: dict[str, Any]) -> dict[str, Any]:
    return {
        "latency_ms": settings.get("latency_ms", 0),
        "resample_method": settings.get("resample_method"),
        "channel_map": settings.get("channel_map"),
        "sample_rate": settings.get("sample_rate"),
        "buffer_size": settings.get("buffer_size"),
        "periods": settings.get("periods"),
        "alsa_card": settings.get("alsa_card"),
        "pipewire_quantum": settings.get("pipewire_quantum"),
        "pipewire_rate": settings.get("pipewire_rate"),
        "jack_bridge": settings.get("jack_bridge"),
        "echo_cancel": settings.get("echo_cancel"),
        "noise_suppression": settings.get("noise_suppression"),
        "agc": settings.get("agc"),
        "monitor_sources": settings.get("monitor_sources"),
        "flat_volumes": settings.get("flat_volumes"),
        "rtp_latency": settings.get("rtp_latency"),
        "network_audio": settings.get("network_audio"),
        "resample_methods": ["speex-float-10", "speex-float-5", "ffmpeg", "soxr", "copy"],
        "pipewire_config_hint": str(STATE_DIR / "pipewire-pulse.conf.d"),
        "jack_detected": backend.get("jack", False),
    }


def snapshot(advanced: bool | None = None) -> dict[str, Any]:
    settings = _load_settings()
    if advanced is not None:
        settings["advanced"] = bool(advanced)
    dac = _dac_mod()
    backend = fcc.detect_backend()
    devs = dac.enumerate_devices() if dac and hasattr(dac, "enumerate_devices") else fcc.enumerate_audio_devices()
    default_sink = devs.get("default_sink") or fcc.default_device("sink")
    default_source = devs.get("default_source") or fcc.default_device("source")
    sinks = devs.get("sinks") or fcc.parse_pactl_short("sink")
    sources = devs.get("sources") or fcc.parse_pactl_short("source")
    if dac and hasattr(dac, "load_settings"):
        dac_settings = dac.load_settings()
        settings.setdefault("default_sink", dac_settings.get("output_device"))
        settings.setdefault("default_source", dac_settings.get("input_device"))
    sink_detail = fcc.parse_pactl_detail("sink", default_sink) if default_sink else {}
    source_detail = fcc.parse_pactl_detail("source", default_source) if default_source else {}
    payload: dict[str, Any] = {
        "ok": True,
        "settings": settings,
        "backend": backend,
        "default_sink": default_sink,
        "default_source": default_source,
        "sinks": sinks,
        "sources": sources,
        "sink_detail": sink_detail,
        "source_detail": source_detail,
        "alsa_cards": devs.get("alsa_cards") or fcc.alsa_cards(),
        "volume": {
            "sink_percent": sink_detail.get("volume_percent", int(settings.get("sink_volume", 1.0) * 100)),
            "source_percent": source_detail.get("volume_percent", int(settings.get("source_volume", 1.0) * 100)),
            "sink_muted": sink_detail.get("muted", settings.get("sink_muted")),
            "source_muted": source_detail.get("muted", settings.get("source_muted")),
        },
    }
    if settings.get("advanced"):
        payload["advanced"] = _advanced_block(settings, backend)
    sc_mod = fcc.mod("fa_soundcards", "field-soundcards-catalog.py")
    payload["soundcards"] = sc_mod.catalog() if sc_mod and hasattr(sc_mod, "catalog") else {}
    vac = _vintage_mod()
    if vac:
        try:
            active = vac.active_card() if hasattr(vac, "active_card") else {}
            cat = vac.catalog() if hasattr(vac, "catalog") else {}
            groups = vac.cards_by_vendor() if hasattr(vac, "cards_by_vendor") else []
            tune_path = ""
            if hasattr(vac, "ensure_test_tune"):
                tune_path = str(vac.ensure_test_tune())
            payload["vintage"] = {
                "active": active,
                "groups": groups,
                "card_count": cat.get("card_count", 0),
                "default_sink": cat.get("default_sink"),
                "playback": cat.get("playback"),
                "gstreamer": cat.get("gstreamer_available"),
                "ffmpeg": cat.get("ffmpeg_available"),
                "test_tune_path": tune_path,
                "api": "/api/field-vintage-audio",
            }
            card_id = settings.get("soundcard_id") or active.get("card_id")
            if card_id and hasattr(vac, "card_by_id"):
                payload["active_soundcard"] = vac.card_by_id(str(card_id))
        except Exception as exc:
            payload["vintage"] = {"ok": False, "error": str(exc)[:120]}
    hdmi = _hdmi_mod()
    if hdmi and hasattr(hdmi, "probe"):
        try:
            payload["hdmi"] = hdmi.probe()
        except Exception:
            payload["hdmi"] = {"ok": False}
    if dac:
        probe = dac.dac_probe() if hasattr(dac, "dac_probe") else {}
        profiles = dac.format_profiles() if hasattr(dac, "format_profiles") else []
        if not profiles:
            profiles = fcc.load(INSTALL / "data" / "field-audio-dac-doctrine.json", {}).get("format_profiles") or []
        payload["dac_chamber"] = {
            "ui": "/field-audio-dac",
            "api": "/api/field-audio-dac",
            "format_profiles": profiles,
            "active_profile": probe.get("active_profile") or {},
            "soundcards": payload.get("soundcards"),
        }
    return payload


def posture(*, advanced: bool | None = None) -> dict[str, Any]:
    snap = snapshot(advanced=advanced)
    backend = snap.get("backend") or {}
    sinks = snap.get("sinks") or []
    doc = {
        "schema": "field-audio-settings/v1",
        "ts": fcc.ts(),
        "ok": bool(snap.get("ok")),
        "title": "Audio Settings",
        "backend": backend.get("name") or backend.get("id") or "unknown",
        "sink_count": len(sinks),
        "default_sink": snap.get("default_sink"),
        "default_source": snap.get("default_source"),
        "settings": snap.get("settings") or {},
        "routes": {"panel": "/field-audio-settings", "api": "/api/field-audio-settings"},
        "posture": (
            f"Audio — {backend.get('name') or backend.get('id') or 'backend'} · "
            f"{len(sinks)} sinks · advanced={'on' if (snap.get('settings') or {}).get('advanced') else 'off'}"
        ),
        "snapshot": snap,
    }
    fcc.save_atomic(PANEL_PATH, doc)
    return doc


def _filter_audio_patch(patch: dict[str, Any]) -> dict[str, Any]:
    surface = fcc.mod("queen_settings_surface", "queen-settings-surface.py")
    if surface and hasattr(surface, "audio_patch_allowed"):
        try:
            return surface.audio_patch_allowed(patch)
        except Exception:
            pass
    return dict(patch or {})


def test_tune(*, card_id: str = "") -> dict[str, Any]:
    vac = _vintage_mod()
    if not vac or not hasattr(vac, "test_tune"):
        return {"ok": False, "error": "vintage_composite_missing"}
    cid = card_id or _load_settings().get("soundcard_id") or "nvidia-hdmi-pro"
    result = vac.test_tune(card_id=str(cid))
    settings = _load_settings()
    settings["soundcard_id"] = str(cid)
    _save_settings(settings)
    card = vac.card_by_id(str(cid)) if hasattr(vac, "card_by_id") else None
    ok = bool(result.get("ok"))
    return {
        "ok": ok,
        "action": "test_tune",
        "test_result": result,
        "settings": settings,
        "soundcard_id": cid,
        "active_soundcard": card,
        "default_sink": result.get("sink") or fcc.default_device("sink"),
        "message": (
            f"Test tune — {result.get('card_name') or cid}"
            if ok
            else f"Test failed — {result.get('error') or 'playback_error'}"
        ),
        "error": None if ok else (result.get("error") or "test_tune_failed"),
        "refresh_recommended": True,
    }


def bind_hdmi() -> dict[str, Any]:
    hdmi = _hdmi_mod()
    if not hdmi or not hasattr(hdmi, "bind"):
        return {"ok": False, "error": "hdmi_driver_missing"}
    result = hdmi.bind(force=True)
    out = snapshot()
    out["hdmi_bind"] = result
    out["ok"] = bool(result.get("ok"))
    return out


def dispatch_settings(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "apply").strip().lower().replace("-", "_")
    if action in ("test_tune", "test_card", "play_test", "tune"):
        return test_tune(card_id=str(body.get("card_id") or body.get("soundcard_id") or ""))
    if action in ("select_card", "select_soundcard"):
        cid = str(body.get("card_id") or body.get("soundcard_id") or "")
        vac = _vintage_mod()
        if vac and cid and hasattr(vac, "select_card"):
            vac.select_card(cid)
        return apply_settings({"soundcard_id": cid} if cid else {})
    if action in ("bind_hdmi", "hdmi_bind", "hdmi"):
        return bind_hdmi()
    if action == "refresh":
        return snapshot()
    clean = {k: v for k, v in body.items() if k != "action"}
    return apply_settings(clean)


def apply_settings(patch: dict[str, Any]) -> dict[str, Any]:
    patch = _filter_audio_patch(patch or {})
    if patch.get("soundcard_id"):
        vac = _vintage_mod()
        if vac and hasattr(vac, "select_card"):
            try:
                vac.select_card(str(patch["soundcard_id"]))
            except Exception:
                pass
    dac = _dac_mod()
    if dac and hasattr(dac, "apply_routing"):
        dac_patch: dict[str, Any] = {}
        if patch.get("default_sink"):
            dac_patch["output_device"] = patch["default_sink"]
        if patch.get("default_source"):
            dac_patch["input_device"] = patch["default_source"]
        if patch.get("format_profile"):
            dac_patch["format_profile"] = patch["format_profile"]
        if patch.get("soundcard_id"):
            dac_patch["soundcard_id"] = patch["soundcard_id"]
        if patch.get("quality"):
            dac_patch["quality"] = patch["quality"]
        if patch.get("sink_volume") is not None:
            dac_patch["output_gain_db"] = 20.0 * math.log10(max(0.01, float(patch["sink_volume"])))
        if patch.get("source_volume") is not None:
            dac_patch["input_gain_db"] = 20.0 * math.log10(max(0.01, float(patch["source_volume"])))
        for key in ("echo_cancel", "noise_suppression"):
            if key in patch:
                dac_patch["echo_cancel" if key == "echo_cancel" else "noise_gate"] = patch[key]
        if dac_patch:
            dac.apply_routing(dac_patch)
    settings = _load_settings()
    settings["advanced"] = False
    allowed = set(DEFAULT_SETTINGS.keys())
    for key, val in patch.items():
        if key in allowed:
            settings[key] = val
    _save_settings(settings)

    if settings.get("default_sink"):
        fcc.run(["pactl", "set-default-sink", str(settings["default_sink"])])
    if settings.get("default_source"):
        fcc.run(["pactl", "set-default-source", str(settings["default_source"])])

    sink_vol = max(0, min(100, int(float(settings.get("sink_volume", 1.0)) * 100)))
    src_vol = max(0, min(100, int(float(settings.get("source_volume", 1.0)) * 100)))
    sink = settings.get("default_sink") or fcc.default_device("sink")
    source = settings.get("default_source") or fcc.default_device("source")
    if sink:
        fcc.run(["pactl", "set-sink-volume", sink, f"{sink_vol}%"])
        fcc.run(["pactl", "set-sink-mute", sink, "1" if settings.get("sink_muted") else "0"])
    if source:
        fcc.run(["pactl", "set-source-volume", source, f"{src_vol}%"])
        fcc.run(["pactl", "set-source-mute", source, "1" if settings.get("source_muted") else "0"])

    return snapshot()


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: field-audio-settings.py [json|apply JSON]")
        return 0
    cmd = args[0]
    if cmd in ("json", "status"):
        advanced = None
        if len(args) > 1 and args[1] in ("0", "1", "true", "false"):
            advanced = args[1] in ("1", "true")
        print(json.dumps(snapshot(advanced=advanced), indent=2))
        return 0
    if cmd == "posture":
        advanced = None
        if len(args) > 1 and args[1] in ("0", "1", "true", "false"):
            advanced = args[1] in ("1", "true")
        print(json.dumps(posture(advanced=advanced), indent=2))
        return 0
    if cmd == "apply" and len(args) > 1:
        try:
            patch = json.loads(args[1])
        except json.JSONDecodeError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}))
            return 1
        print(json.dumps(dispatch_settings(patch), indent=2))
        return 0
    if cmd in ("test_tune", "tune"):
        cid = args[1] if len(args) > 1 else ""
        print(json.dumps(test_tune(card_id=cid), indent=2))
        return 0
    if cmd == "bind_hdmi":
        print(json.dumps(bind_hdmi(), indent=2))
        return 0
    print(json.dumps({"ok": False, "error": f"unknown command: {cmd}"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())