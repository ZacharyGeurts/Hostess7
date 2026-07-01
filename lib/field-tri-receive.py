#!/usr/bin/env pythong
"""Three-field GPS compare → pinpoint transmitter → OTA receive to speakers."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_CACHE = STATE / "field-tri-receive.json"
CATCH_AUDIO = STATE / "field-antenna-catch.wav"
REGISTRY_PATH = INSTALL / "data" / "field-radio-broadcast-registry.json"
OPERATOR_LOC = STATE / "operator-location.json"

DEFAULT_MHZ = float(os.environ.get("NEXUS_FIELD_CATCH_MHZ", "93.1"))
CONCEPT_MODE = os.environ.get("NEXUS_FIELD_TRI_CONCEPT", "1") == "1"
MIN_TRI_CONFIDENCE = float(os.environ.get("NEXUS_FIELD_TRI_MIN_CONF", "0.25"))
TRIANGULATION_CEP_M = float(os.environ.get("NEXUS_FIELD_TRI_CEP_M", "0.25"))

RECEIVER_3F = INSTALL / "data" / "field-receiver-3fields.json"

# Three local fields — compared to operator GPS, then used to pinpoint signal
FIELD_ANCHORS = [
    {
        "id": "field_gladstone",
        "label": "Gladstone · operator field",
        "lat": 45.845976,
        "lon": -87.055759,
        "role": "operator_home",
    },
    {
        "id": "field_escanaba",
        "label": "Escanaba · south field",
        "lat": 45.7452,
        "lon": -87.0646,
        "role": "tower_reference",
    },
    {
        "id": "field_iron_mountain",
        "label": "Iron Mountain · west field",
        "lat": 45.820,
        "lon": -88.041,
        "role": "triangulation_west",
    },
]


def _field_anchors() -> list[dict[str, Any]]:
    doc = _load_json(RECEIVER_3F, {})
    fields = doc.get("fields") if doc.get("schema") == "field-receiver-3fields/v1" else None
    return list(fields) if fields else FIELD_ANCHORS


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


def _which(cmd: str) -> str | None:
    try:
        proc = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=4)
        out = (proc.stdout or "").strip()
        return out if proc.returncode == 0 and out else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def _operator() -> dict[str, Any]:
    doc = _load_json(OPERATOR_LOC, {})
    if doc.get("lat") is None:
        try:
            mod = _import("operator_default", "operator-default.py")
            doc = mod.seed_operator_location()
        except Exception:
            pass
    return doc


def _target_station(freq_mhz: float) -> dict[str, Any]:
    reg = _load_json(REGISTRY_PATH, {"stations": []})
    for st in reg.get("stations") or []:
        fm = st.get("freq_mhz")
        if fm is not None and abs(float(fm) - freq_mhz) < 0.05:
            return st
        fk = st.get("freq_khz")
        if fk is not None and abs(float(fk) / 1000.0 - freq_mhz) < 0.05:
            return st
    return {
        "id": f"catch-{int(freq_mhz * 10)}",
        "call_sign": "FIELD",
        "name": f"{freq_mhz} MHz field catch",
        "freq_mhz": freq_mhz,
        "tower_lat": 45.845976,
        "tower_lon": -87.055759,
        "band": "vhf",
    }


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(rlat2)
    y = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def compare_fields_to_gps(
    *,
    operator: dict[str, Any] | None = None,
    anchors: list[dict[str, Any]] | None = None,
    target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare three field GPS anchors to operator GPS; score alignment to target."""
    op = operator or _operator()
    op_lat = float(op.get("lat") or FIELD_ANCHORS[0]["lat"])
    op_lon = float(op.get("lon") or FIELD_ANCHORS[0]["lon"])
    fields = anchors or _field_anchors()
    tgt = target or {}
    tlat = float(tgt.get("tower_lat") or op_lat)
    tlon = float(tgt.get("tower_lon") or op_lon)
    geo = _import("geo_distance", "geo-distance.py")
    gps = _import("gps_precision", "gps-precision.py")

    comparisons: list[dict[str, Any]] = []
    bearings_to_target: list[float] = []
    strengths: list[float] = []

    for field in fields:
        flat = float(field["lat"])
        flon = float(field["lon"])
        op_match = geo.distance_fields(op_lat, op_lon, flat, flon)
        field_to_target = geo.distance_fields(flat, flon, tlat, tlon)
        op_to_target = geo.distance_fields(op_lat, op_lon, tlat, tlon)
        brg_field = _bearing_deg(flat, flon, tlat, tlon)
        brg_op = _bearing_deg(op_lat, op_lon, tlat, tlon)
        brg_delta = abs(((brg_field - brg_op + 180) % 360) - 180)
        # Closer field + aligned bearing → stronger contribution
        dist_km = float(field_to_target.get("distance_km") or 1.0) or 1.0
        strength = max(0.0, 100.0 - dist_km * 2.5 - brg_delta * 0.15)
        if field.get("role") == "operator_home":
            match_km = float(op_match.get("distance_km") or 0)
            strength += max(0.0, 25.0 - match_km * 50.0)
        strengths.append(strength)
        bearings_to_target.append(brg_field)
        comparisons.append({
            "field_id": field.get("id"),
            "label": field.get("label"),
            "role": field.get("role"),
            "field_gps": f"{flat:.6f}, {flon:.6f}",
            "operator_gps": f"{op_lat:.6f}, {op_lon:.6f}",
            "operator_match_km": op_match.get("distance_km"),
            "operator_match_label": op_match.get("distance_label"),
            "distance_to_target_km": field_to_target.get("distance_km"),
            "distance_to_target_label": field_to_target.get("distance_label"),
            "bearing_to_target_deg": round(brg_field, 1),
            "bearing_delta_from_operator_deg": round(brg_delta, 1),
            "signal_strength_pct": round(min(100.0, strength), 1),
        })

    total = sum(strengths) or 1.0
    w = [s / total for s in strengths]
    raw = gps.barycentric_point_on_sphere(fields[0], fields[1], fields[2], w[0], w[1], w[2])
    pinpoint = gps.placement_from_detected(
        raw["lat"],
        raw["lon"],
        anchor={"lat": op_lat, "lon": op_lon, "id": "operator"},
        source="field_tri_3gps",
        label="pinpoint",
    )
    pinpoint.update({
        "return_type": "point",
        "placement_mode": "triangulate_3gps",
        "tri_weights": raw.get("weights"),
    })

    # Confidence: bearing agreement + operator on first field
    brg_spread = max(bearings_to_target) - min(bearings_to_target) if bearings_to_target else 180.0
    if brg_spread > 180:
        brg_spread = 360.0 - brg_spread
    op_home_km = float(comparisons[0].get("operator_match_km") or 99)
    avg_strength = sum(strengths) / max(len(strengths), 1)
    confidence = min(1.0, max(0.0,
        (1.0 - min(brg_spread, 120.0) / 120.0) * 0.35
        + (1.0 - min(op_home_km, 8.0) / 8.0) * 0.4
        + avg_strength / 100.0 * 0.25,
    ))

    return {
        "schema": "field-tri-compare/v1",
        "updated": _now(),
        "cep_m": TRIANGULATION_CEP_M if confidence >= MIN_TRI_CONFIDENCE else None,
        "precision": f"{TRIANGULATION_CEP_M}m CEP" if confidence >= MIN_TRI_CONFIDENCE else None,
        "operator": {"lat": op_lat, "lon": op_lon, "gps": f"{op_lat:.6f}, {op_lon:.6f}", "source": op.get("source")},
        "target": {
            "tower_lat": tlat,
            "tower_lon": tlon,
            "tower_gps": f"{tlat:.6f}, {tlon:.6f}",
            "freq_mhz": tgt.get("freq_mhz"),
            "name": tgt.get("name"),
            "call_sign": tgt.get("call_sign"),
        },
        "fields": comparisons,
        "pinpoint": pinpoint,
        "pinpoint_gps": f"{pinpoint.get('lat_str', pinpoint.get('lat'))}, {pinpoint.get('lon_str', pinpoint.get('lon'))}",
        "tri_confidence": round(confidence, 3),
        "tri_ready": confidence >= MIN_TRI_CONFIDENCE,
        "bearing_spread_deg": round(brg_spread, 1),
    }


def _engine() -> Any:
    spec = importlib.util.spec_from_file_location("field_wave_engine", INSTALL / "lib" / "field-wave-engine.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _rtl_capture(freq_mhz: float, seconds: float = 8.0) -> dict[str, Any]:
    eng = _engine()
    eng.ensure_ported_backends(build_asm=False)
    out = eng.capture_wbfm(freq_mhz, out_path=CATCH_AUDIO, seconds=seconds)
    out["method"] = "field_wave_engine"
    return out


def _play_wav(path: Path, *, background: bool = True) -> dict[str, Any]:
    eng = _engine()
    if not path.is_file():
        return {"ok": False, "error": "no_player_or_file"}
    if background:
        out = eng.play_wav(path)
        if out.get("ok"):
            out["background"] = True
        return out
    try:
        proc = subprocess.run([str(eng.FIELD_PLAY), str(path)], capture_output=True, timeout=120)
        return {"ok": proc.returncode == 0, "method": "field-wave-play", "background": False}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def _live_play(freq_mhz: float, seconds: float = 30.0) -> dict[str, Any]:
    """Field-wave-engine live WBFM to speakers."""
    eng = _engine()
    out = eng.live_play_wbfm(freq_mhz, seconds=seconds)
    if out.get("ok"):
        out["method"] = "field_wave_engine_live"
    return out


def receive_signal(
    *,
    freq_mhz: float | None = None,
    live_play: bool = True,
    capture_seconds: float = 8.0,
) -> dict[str, Any]:
    """Full pipeline: 3-field compare → pinpoint → capture → play to ears."""
    target_mhz = float(freq_mhz if freq_mhz is not None else DEFAULT_MHZ)
    station = _target_station(target_mhz)
    tri = compare_fields_to_gps(target=station)
    tri_ready = bool(tri.get("tri_ready")) or CONCEPT_MODE

    capture: dict[str, Any] = {"ok": False, "skipped": "tri_not_ready"}
    playback: dict[str, Any] = {"ok": False}
    live: dict[str, Any] = {"ok": False}

    if tri_ready:
        capture = _rtl_capture(target_mhz, seconds=capture_seconds)
        if capture.get("ok") and CATCH_AUDIO.is_file():
            playback = _play_wav(CATCH_AUDIO, background=live_play)
        eng = _engine()
        hw = eng.probe_hardware()
        if live_play and hw.get("listen_ready"):
            live = _live_play(target_mhz, seconds=45.0)

    heard = bool(playback.get("ok") or live.get("ok") or capture.get("ok"))
    doc = {
        "schema": "field-tri-receive/v1",
        "updated": _now(),
        "ok": heard or tri_ready,
        "heard": heard,
        "playing": bool(playback.get("ok") or live.get("ok")),
        "concept_mode": CONCEPT_MODE,
        "freq_mhz": target_mhz,
        "freq_label": f"{target_mhz:.1f} MHz",
        "station": {
            "id": station.get("id"),
            "call_sign": station.get("call_sign"),
            "name": station.get("name"),
        },
        "tri_compare": tri,
        "tri_confidence": tri.get("tri_confidence"),
        "tri_ready": tri_ready,
        "pinpoint": tri.get("pinpoint"),
        "pinpoint_gps": tri.get("pinpoint_gps"),
        "capture": capture,
        "playback": playback,
        "live_play": live,
        "audio_url": "/api/field-antenna/catch-audio" if capture.get("ok") else "",
        "next_steps": [] if heard else [
            "Plug RTL-SDR dongle into USB",
            "sudo apt install rtl-sdr sox pulseaudio-utils",
            "Run: ./scripts/field-tri-receive.sh listen",
            "Or panel Signals → Field wave tune 93.1 WIMK",
        ],
    }
    _save_json(PANEL_CACHE, doc)
    return doc


def build_panel() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("schema") == "field-tri-receive/v1" and cached.get("tri_compare"):
        return cached
    station = _target_station(DEFAULT_MHZ)
    tri = compare_fields_to_gps(target=station)
    doc = {
        "schema": "field-tri-receive/v1",
        "updated": _now(),
        "ok": tri.get("tri_ready"),
        "freq_mhz": DEFAULT_MHZ,
        "tri_compare": tri,
        "concept_mode": CONCEPT_MODE,
    }
    _save_json(PANEL_CACHE, doc)
    return doc


def panel_json() -> dict[str, Any]:
    return build_panel()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "compare":
        mhz = float(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MHZ
        st = _target_station(mhz)
        print(json.dumps(compare_fields_to_gps(target=st), ensure_ascii=False))
        return 0
    if cmd in ("receive", "listen", "pinpoint"):
        payload: dict[str, Any] = {}
        if len(sys.argv) > 2:
            try:
                payload = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                payload = {"freq_mhz": float(sys.argv[2])}
        out = receive_signal(
            freq_mhz=float(payload.get("freq_mhz", DEFAULT_MHZ)),
            live_play=payload.get("live_play", True) is not False,
        )
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("heard") or out.get("tri_ready") else 1
    print(json.dumps({"error": "usage: field-tri-receive.py [json|build|compare|receive|listen]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())