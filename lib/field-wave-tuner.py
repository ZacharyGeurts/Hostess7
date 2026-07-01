#!/usr/bin/env pythong
"""Field wave tuner — OTA MHz lock via field-wave-engine + 3-field pinpoint. No URLs."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_CACHE = STATE / "field-wave-tuner.json"
CATCH_AUDIO = STATE / "field-antenna-catch.wav"
REGISTRY = INSTALL / "data" / "field-radio-broadcast-registry.json"
OPERATOR_LOC = STATE / "operator-location.json"

DEFAULT_MHZ = float(os.environ.get("NEXUS_FIELD_CATCH_MHZ", "93.1"))


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _engine() -> Any:
    return _import("field_wave_engine", "field-wave-engine.py")


def _operator() -> dict[str, Any]:
    doc = _load_json(OPERATOR_LOC, {})
    if doc.get("lat") is None:
        try:
            doc = _import("operator_default", "operator-default.py").seed_operator_location()
        except Exception:
            pass
    return doc


def _station(freq_mhz: float, station_id: str = "", call_sign: str = "") -> dict[str, Any]:
    reg = _load_json(REGISTRY, {"stations": []})
    for st in reg.get("stations") or []:
        if station_id and st.get("id") == station_id:
            return st
        if call_sign and str(st.get("call_sign") or "").lower() == call_sign.lower():
            return st
        fm = st.get("freq_mhz")
        if fm is not None and abs(float(fm) - freq_mhz) < 0.05:
            return st
    return {
        "id": f"catch-{int(freq_mhz * 10)}",
        "call_sign": "FIELD",
        "name": f"{freq_mhz} MHz field wave",
        "freq_mhz": freq_mhz,
        "tower_lat": 45.845976,
        "tower_lon": -87.055759,
        "band": "fm",
    }


def _endpoints(station: dict[str, Any], tri: dict[str, Any]) -> dict[str, Any]:
    op = _operator()
    op_lat = float(op.get("lat") or 45.845976)
    op_lon = float(op.get("lon") or -87.055759)
    tlat = float(station.get("tower_lat") or op_lat)
    tlon = float(station.get("tower_lon") or op_lon)
    pin = tri.get("pinpoint") or {}
    return {
        "start_point": {
            "role": "transmitter",
            "label": station.get("call_sign") or station.get("name"),
            "lat": tlat,
            "lon": tlon,
            "gps": f"{tlat:.6f}, {tlon:.6f}",
            "freq_mhz": station.get("freq_mhz"),
        },
        "end_point": {
            "role": "our_line",
            "label": "operator_antenna",
            "lat": op_lat,
            "lon": op_lon,
            "gps": f"{op_lat:.6f}, {op_lon:.6f}",
        },
        "pinpoint": {
            "lat": pin.get("lat"),
            "lon": pin.get("lon"),
            "gps": tri.get("pinpoint_gps"),
        },
    }


def _rtl_capture(
    freq_mhz: float,
    seconds: float = 10.0,
    *,
    freq_hz: int | None = None,
    ppm: int = 0,
) -> dict[str, Any]:
    eng = _engine()
    eng.ensure_ported_backends(build_asm=False)
    out = eng.capture_wbfm(
        freq_mhz,
        out_path=CATCH_AUDIO,
        seconds=seconds,
        freq_hz=freq_hz,
        ppm=ppm,
    )
    out["method"] = "field_wave_tuner"
    return out


def _live_play(
    freq_mhz: float,
    seconds: float = 45.0,
    *,
    freq_hz: int | None = None,
    ppm: int = 0,
) -> dict[str, Any]:
    eng = _engine()
    out = eng.live_play_wbfm(freq_mhz, seconds=seconds, freq_hz=freq_hz, ppm=ppm)
    if out.get("ok"):
        out["method"] = "field_wave_tuner_live"
    return out


def _play_wav(path: Path) -> dict[str, Any]:
    return _engine().play_wav(path)


def tune(
    *,
    freq_mhz: float | None = None,
    station_id: str = "",
    call_sign: str = "",
    live_play: bool = True,
    capture_seconds: float = 10.0,
) -> dict[str, Any]:
    """OTA field wave tune — field-wave-engine only, never web stream."""
    mhz = float(freq_mhz if freq_mhz is not None else DEFAULT_MHZ)
    _engine().ensure_ported_backends()
    field_read: dict[str, Any] = {}
    try:
        reader = _import("field_signal_reader", "field-signal-reader.py")
        field_read = reader.read_frequency(mhz, station_id=station_id)
    except Exception as exc:
        field_read = {"ok": False, "error": str(exc)}
    st = _station(mhz, station_id, call_sign)
    tri_mod = _import("field_tri_receive", "field-tri-receive.py")
    tri = tri_mod.compare_fields_to_gps(
        target={
            "tower_lat": st.get("tower_lat"),
            "tower_lon": st.get("tower_lon"),
            "freq_mhz": mhz,
            "name": st.get("name"),
            "call_sign": st.get("call_sign"),
        },
    )
    endpoints = _endpoints(st, tri)
    instability: dict[str, Any] = {}
    try:
        inst_mod = _import("field_instability", "field-instability.py")
        instability = inst_mod.analyze_fields(tri_compare=tri, freq_mhz=mhz)
        inst_mod.record_sample(instability)
    except Exception as exc:
        instability = {"ok": False, "error": str(exc)}

    tune_hz = int(instability.get("freq_hz") or round(mhz * 1_000_000))
    ppm = int(instability.get("ppm_correction") or (instability.get("physics") or {}).get("ppm") or 0)
    hw = _engine().probe_hardware()
    hw_listen = bool(hw.get("listen_ready"))
    field_play: dict[str, Any] = {"ok": False}
    try:
        demod_mod = _import("field_spectrum_demod", "field-spectrum-demod.py")
        field_play = demod_mod.play_station_from_fields(
            freq_mhz=mhz,
            station_id=station_id,
            play=live_play,
            seconds=max(capture_seconds, 25.0),
        )
    except Exception as exc:
        field_play = {"ok": False, "error": str(exc)}

    capture = field_play.get("hardware_capture") or field_play.get("capture") or {"ok": False}
    if hw_listen and not capture.get("ok"):
        capture = _rtl_capture(mhz, seconds=capture_seconds, freq_hz=tune_hz, ppm=ppm)
    playback = field_play.get("playback") or {"ok": False}
    if capture.get("ok") and CATCH_AUDIO.is_file() and not playback.get("ok"):
        playback = _play_wav(CATCH_AUDIO)
    live = (
        _live_play(mhz, freq_hz=tune_hz, ppm=ppm)
        if live_play and hw_listen and field_play.get("ota_source") == "ota_rtl_fm"
        else field_play if field_play.get("playing") or field_play.get("heard") else {"ok": False}
    )
    heard = bool(playback.get("ok") or live.get("ok") or field_play.get("heard"))
    actual_radio = bool(field_play.get("actual_radio") or heard)
    doc = {
        "schema": "field-wave-tuner/v1",
        "updated": _now(),
        "ok": heard or tri.get("tri_ready"),
        "field_read": field_read,
        "fidelity_pct": field_read.get("fidelity_pct"),
        "heard": heard,
        "actual_radio": actual_radio,
        "playing": bool(playback.get("ok") or live.get("ok")),
        "method": "field_wave_tuner",
        "ota_only": True,
        "freq_mhz": mhz,
        "freq_label": f"{mhz:.1f} MHz",
        "station": {
            "id": st.get("id"),
            "call_sign": st.get("call_sign"),
            "name": st.get("name"),
            "band": st.get("band"),
        },
        "line": endpoints,
        "start_point": endpoints["start_point"],
        "end_point": endpoints["end_point"],
        "tri_compare": tri,
        "tri_confidence": tri.get("tri_confidence"),
        "tri_ready": tri.get("tri_ready"),
        "capture": capture,
        "playback": playback,
        "live_play": live,
        "audio_url": "/api/field-antenna/catch-audio" if capture.get("ok") else "",
        "instability": instability,
        "engine": _engine().probe_hardware(),
        "hardware": {
            "field_wave_fm": bool((instability.get("hardware") or {}).get("field_wave_fm")),
            "field_wave_play": bool((instability.get("hardware") or {}).get("field_wave_play")),
            "field_wave_wav": bool((instability.get("hardware") or {}).get("field_wave_wav")),
            "dongle_present": bool((instability.get("hardware") or {}).get("dongle_present")),
            "listen_ready": bool(instability.get("listen_anyway")),
        },
        "field_play": field_play,
        "we_are_the_antenna": True,
        "next_steps": [] if heard else [
            "pythong lib/field-antenna-prototype.py play_radio",
            "./scripts/play-wimk-ota.sh",
            "Signals tab → Play WIMK 93.1 OTA",
        ],
    }
    _save_json(PANEL_CACHE, doc)
    return doc


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("schema") == "field-wave-tuner/v1":
        return cached
    return {"schema": "field-wave-tuner/v1", "updated": _now(), "freq_mhz": DEFAULT_MHZ, "method": "field_wave_tuner"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "tune":
        payload: dict[str, Any] = {}
        if len(sys.argv) > 2:
            try:
                payload = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                payload = {"freq_mhz": float(sys.argv[2])}
        out = tune(
            freq_mhz=float(payload.get("freq_mhz", DEFAULT_MHZ)),
            station_id=str(payload.get("station_id") or ""),
            call_sign=str(payload.get("call_sign") or ""),
            live_play=payload.get("live_play", True) is not False,
        )
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("heard") or out.get("tri_ready") else 1
    print(json.dumps({"error": "usage: field-wave-tuner.py [json|tune JSON]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())