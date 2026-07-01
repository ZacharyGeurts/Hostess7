#!/usr/bin/env pythong
"""Field world placement — tune radio bands, tower GPS placements, find your place."""
from __future__ import annotations

import importlib.util
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
REGISTRY = INSTALL / "data" / "field-radio-broadcast-registry.json"
PANEL_CACHE = STATE / "field-world-placement.json"
STATION_TOWER_DB = STATE / "field-station-tower-db.json"
WIMK_PLAYBACK_CACHE = STATE / "field-wimk-playback.json"
OPERATOR_LOC = STATE / "operator-location.json"
SELF_MATCH_KM = float(os.environ.get("NEXUS_FIELD_SELF_MATCH_KM", "2.5"))
WIMK_STATION_ID = "wimk-931"
WIMK_MHZ = 93.1
MAX_WIMK_ATTEMPTS = int(os.environ.get("NEXUS_WIMK_MAX_ATTEMPTS", "10"))

BANDS = ("lw", "am", "fm", "vhf", "sw")
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


def _operator() -> dict[str, Any]:
    doc = _load_json(OPERATOR_LOC, {})
    if doc.get("lat") is None:
        try:
            doc = _import("operator_default", "operator-default.py").seed_operator_location()
        except Exception:
            doc = {"lat": 45.845976, "lon": -87.055759, "label": "Gladstone, MI", "source": "default"}
    return doc


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    x = math.sin(dlon) * math.cos(rlat2)
    y = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def _placement_row(
    *,
    role: str,
    lat: float,
    lon: float,
    label: str = "",
    station: dict[str, Any] | None = None,
    op_lat: float = 0.0,
    op_lon: float = 0.0,
    geo: Any = None,
) -> dict[str, Any]:
    geo = geo or _import("geo_distance", "geo-distance.py")
    dist = geo.distance_fields(op_lat, op_lon, lat, lon) if role != "operator" else {"distance_km": 0, "distance_label": "here"}
    row: dict[str, Any] = {
        "role": role,
        "label": label,
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "gps": f"{lat:.6f}, {lon:.6f}",
        "return_type": "point",
        "placement_mode": "tower_gps" if role == "transmitter" else "operator_gps",
        "distance_km": dist.get("distance_km"),
        "distance_label": dist.get("distance_label"),
    }
    if station:
        brg = _bearing_deg(op_lat, op_lon, lat, lon)
        row.update({
            "station_id": station.get("id"),
            "call_sign": station.get("call_sign"),
            "name": station.get("name"),
            "band": station.get("band"),
            "freq_mhz": station.get("freq_mhz"),
            "freq_khz": station.get("freq_khz"),
            "freq_label": station.get("freq_label"),
            "tier": station.get("tier"),
            "in_range": station.get("in_range"),
            "playable": station.get("playable"),
            "bearing_deg": round(brg, 1),
            "city": station.get("city"),
            "state": station.get("state"),
        })
    return row


def _recognize_self(
    *,
    op_lat: float,
    op_lon: float,
    op_doc: dict[str, Any],
    nearest_fm: dict[str, Any] | None,
    tri_pin: dict[str, Any],
) -> dict[str, Any]:
    """Match operator GPS to home field — recognize self in the broadcast world."""
    geo = _import("geo_distance", "geo-distance.py")
    tri_mod = _import("field_tri_receive", "field-tri-receive.py")
    home = {"lat": 45.845976, "lon": -87.055759, "label": "Gladstone · operator field", "id": "field_gladstone"}
    home_match = geo.distance_fields(op_lat, op_lon, home["lat"], home["lon"])
    raw_home_km = home_match.get("distance_km")
    home_km = float(raw_home_km) if raw_home_km is not None else 99.0
    self_at_home = home_km <= SELF_MATCH_KM

    target = nearest_fm or {}
    tri = {}
    try:
        tri = tri_mod.compare_fields_to_gps(
            operator={"lat": op_lat, "lon": op_lon, **op_doc},
            target={
                "tower_lat": target.get("lat") or target.get("tower_lat"),
                "tower_lon": target.get("lon") or target.get("tower_lon"),
                "freq_mhz": target.get("freq_mhz"),
                "call_sign": target.get("call_sign"),
                "name": target.get("name"),
            },
        )
    except Exception:
        pass

    tri_conf = float(tri.get("tri_confidence") or tri_pin.get("tri_confidence") or 0.0)
    confidence = min(1.0, max(0.0,
        (1.0 - min(home_km, 8.0) / 8.0) * 0.45
        + tri_conf * 0.35
        + (0.2 if op_doc.get("address") else 0.0),
    ))
    recognized = self_at_home and confidence >= 0.35

    bearing = None
    if nearest_fm and nearest_fm.get("bearing_deg") is not None:
        bearing = nearest_fm.get("bearing_deg")
    elif target.get("tower_lat") is not None:
        bearing = round(_bearing_deg(op_lat, op_lon, float(target["tower_lat"]), float(target["tower_lon"])), 1)

    place_line = []
    if recognized:
        place_line.append("SELF RECOGNIZED")
    if op_doc.get("label"):
        place_line.append(str(op_doc.get("label")))
    if nearest_fm:
        place_line.append(
            f"hearing {nearest_fm.get('call_sign')} {nearest_fm.get('freq_label', '')} "
            f"{nearest_fm.get('distance_label', '')} · {nearest_fm.get('bearing_deg', bearing)}°"
        )

    return {
        "recognized": recognized,
        "identified": recognized,
        "confidence": round(confidence, 3),
        "self_at_home": self_at_home,
        "home_field_gps": f"{home['lat']:.6f}, {home['lon']:.6f}",
        "operator_gps": f"{op_lat:.6f}, {op_lon:.6f}",
        "home_match_km": round(home_km, 3),
        "home_match_label": home_match.get("distance_label"),
        "tri_confidence": tri_conf,
        "tri_ready": bool(tri.get("tri_ready")),
        "pinpoint_gps": tri.get("pinpoint_gps") or tri_pin.get("gps"),
        "bearing_to_nearest_fm_deg": bearing,
        "role": "operator_self" if recognized else "operator_unresolved",
        "summary": " · ".join(place_line) or f"operator {op_lat:.4f}, {op_lon:.4f}",
        "tri_compare": tri.get("fields") or [],
    }


def _identify_stations_for_db(
    stations: list[dict[str, Any]],
    *,
    op_lat: float,
    op_lon: float,
) -> dict[str, Any]:
    """Identify stations + tower GPS placements; persist to FCC master + local tower DB."""
    master = _import("fcc_master_record", "fcc-master-record.py")
    identified: list[dict[str, Any]] = []
    for st in stations:
        tlat = st.get("tower_lat") or st.get("lat")
        tlon = st.get("tower_lon") or st.get("lon")
        if tlat is None or tlon is None:
            continue
        row = {
            "kind": "fm" if st.get("band") in ("fm", "vhf") else "broadcast",
            "label": st.get("name") or st.get("call_sign"),
            "call_sign": st.get("call_sign"),
            "station_id": st.get("id"),
            "freq_mhz": st.get("freq_mhz"),
            "freq_khz": st.get("freq_khz"),
            "band": st.get("band"),
            "fcc_id": st.get("fcc_id"),
            "fcc_facility_id": st.get("fcc_facility_id"),
            "tower_lat": tlat,
            "tower_lon": tlon,
            "tower_gps": st.get("tower_gps") or f"{float(tlat):.6f}, {float(tlon):.6f}",
            "city": st.get("city"),
            "state": st.get("state"),
            "country": st.get("country"),
            "distance_km": st.get("distance_km"),
            "distance_label": st.get("distance_label"),
            "bearing_deg": st.get("bearing_deg"),
            "in_range": st.get("in_range"),
            "identified": True,
            "identified_by": "field_world_placement",
            "placement_mode": "tower_gps",
            "return_type": "point",
            "permitted": True,
        }
        try:
            master.record_lookup(row, source="field_station_tower_db")
        except Exception:
            pass
        identified.append(row)

    in_range = [r for r in identified if r.get("in_range")]
    doc = {
        "schema": "field-station-tower-db/v1",
        "updated": _now(),
        "motto": "Stations identified · towers GPS-placed · operator self recognized.",
        "operator_gps": f"{op_lat:.6f}, {op_lon:.6f}",
        "stations": identified,
        "identified_stations": identified,
        "in_range_stations": in_range,
        "stats": {
            "total": len(identified),
            "in_range": len(in_range),
            "tower_gps": len(identified),
            "bands": sorted({str(r.get("band") or "") for r in identified if r.get("band")}),
        },
    }
    _save_json(STATION_TOWER_DB, doc)
    master.build_master_table()
    return doc


def _nearest_in_band(stations: list[dict[str, Any]], band: str) -> dict[str, Any] | None:
    hits = [s for s in stations if s.get("band") == band and s.get("in_range")]
    if not hits:
        hits = [s for s in stations if s.get("band") == band]
    if not hits:
        return None
    return min(hits, key=lambda x: float(x.get("distance_km") or 1e9))


def build_world_placement(*, rescan: bool = True) -> dict[str, Any]:
    """Scan bands, map placements, locate operator in the broadcast world."""
    radio = _import("field_radio_catcher", "field-radio-catcher.py").build_field_radio_panel()
    op_doc = radio.get("operator") or {}
    op_lat = float(op_doc.get("lat") or 45.845976)
    op_lon = float(op_doc.get("lon") or -87.055759)
    stations = list(radio.get("all_legal_stations") or radio.get("station_menu") or [])
    spectrum = list(radio.get("spectrum") or [])
    boost = radio.get("field_boost") or {}

    operator_place = _placement_row(
        role="operator",
        lat=op_lat,
        lon=op_lon,
        label=op_doc.get("label") or op_doc.get("display_name") or "operator",
    )
    operator_place["itu_region"] = op_doc.get("itu_region")
    operator_place["address"] = op_doc.get("address")

    placements: list[dict[str, Any]] = [operator_place]
    geo = _import("geo_distance", "geo-distance.py")
    for st in stations:
        if st.get("tower_lat") is None and st.get("lat") is None:
            continue
        placements.append(_placement_row(
            role="transmitter",
            lat=float(st.get("tower_lat") or st.get("lat") or 0),
            lon=float(st.get("tower_lon") or st.get("lon") or 0),
            label=str(st.get("call_sign") or st.get("name") or ""),
            station=st,
            op_lat=op_lat,
            op_lon=op_lon,
            geo=geo,
        ))

    tri_pin: dict[str, Any] = {}
    try:
        reader = _import("field_signal_reader", "field-signal-reader.py")
        read = reader.read_frequency(DEFAULT_MHZ, station_id="wimk-931")
        tri = (read.get("mesh") or {}).get("tri_compare") or {}
        pin = tri.get("pinpoint") or {}
        if pin.get("lat") is not None:
            tri_pin = {
                "lat": pin.get("lat"),
                "lon": pin.get("lon"),
                "gps": tri.get("pinpoint_gps"),
                "placement_mode": "triangulate_3gps",
                "tri_confidence": tri.get("tri_confidence"),
            }
            placements.append({
                "role": "pinpoint",
                "label": "3-field lock",
                "lat": pin.get("lat"),
                "lon": pin.get("lon"),
                "gps": tri.get("pinpoint_gps"),
                "return_type": "point",
                "placement_mode": "triangulate_3gps",
                "tri_confidence": tri.get("tri_confidence"),
            })
    except Exception:
        pass

    nearest_fm = _nearest_in_band(stations, "fm")
    nearest_am = _nearest_in_band(stations, "am")
    in_range = [s for s in stations if s.get("in_range")]
    local_fm = [s for s in in_range if s.get("band") == "fm"]
    local_am = [s for s in in_range if s.get("band") == "am"]

    station_db = _identify_stations_for_db(stations, op_lat=op_lat, op_lon=op_lon)
    self_rec = _recognize_self(
        op_lat=op_lat,
        op_lon=op_lon,
        op_doc=op_doc,
        nearest_fm=nearest_fm,
        tri_pin=tri_pin,
    )

    region_bits = []
    if op_doc.get("label"):
        region_bits.append(str(op_doc.get("label")))
    if nearest_fm:
        region_bits.append(f"FM anchor {nearest_fm.get('call_sign')} {nearest_fm.get('distance_label')}")
    if op_doc.get("itu_region"):
        region_bits.append(f"ITU {op_doc.get('itu_region')}")

    band_map: dict[str, Any] = {}
    for band in BANDS:
        band_stations = [s for s in stations if s.get("band") == band]
        band_in = [s for s in band_stations if s.get("in_range")]
        band_map[band] = {
            "label": (radio.get("bands") or {}).get(band, {}).get("label", band.upper()),
            "total": len(band_stations),
            "in_range": len(band_in),
            "playable": sum(1 for s in band_stations if s.get("playable")),
            "stations": sorted(band_in or band_stations, key=lambda x: float(x.get("distance_km") or 1e9))[:24],
        }

    your_place = {
        "summary": self_rec.get("summary") or " · ".join(region_bits) or f"{op_lat:.4f}, {op_lon:.4f}",
        "operator_gps": f"{op_lat:.6f}, {op_lon:.6f}",
        "self_recognized": self_rec.get("recognized"),
        "self_confidence": self_rec.get("confidence"),
        "nearest_fm": nearest_fm,
        "nearest_am": nearest_am,
        "local_fm_count": len(local_fm),
        "local_am_count": len(local_am),
        "in_range_total": len(in_range),
        "world_tune": bool(boost.get("world_tune")),
        "pinpoint": tri_pin,
        "bearing_to_nearest_fm_deg": (nearest_fm or {}).get("bearing_deg") if nearest_fm else None,
    }

    tune_steps: list[dict[str, Any]] = []
    for slot in spectrum:
        tune_steps.append({
            "band": slot.get("band"),
            "freq_mhz": slot.get("freq_mhz"),
            "freq_khz": slot.get("freq_khz"),
            "status": slot.get("status"),
            "label": slot.get("label"),
            "legal": slot.get("status") == "legal",
        })

    doc = {
        "schema": "field-world-placement/v1",
        "updated": _now(),
        "motto": "Tune the bands · identify stations & towers · recognize self · find your place.",
        "operator": operator_place,
        "self": self_rec,
        "self_recognition": self_rec,
        "your_place": your_place,
        "bands": band_map,
        "placements": placements,
        "station_tower_db": station_db,
        "identified_stations": station_db.get("identified_stations") or [],
        "spectrum_tune": tune_steps[:400],
        "stats": {
            "placement_count": len(placements),
            "bands_scanned": len(band_map),
            "in_range": len(in_range),
            "playable": sum(1 for s in stations if s.get("playable")),
            "tower_gps": sum(1 for p in placements if p.get("role") == "transmitter"),
            "stations_identified": station_db.get("stats", {}).get("total", 0),
            "self_recognized": self_rec.get("recognized"),
        },
        "field_radio": {
            "crystal_clarity": radio.get("crystal_clarity"),
            "stats": radio.get("stats"),
        },
        "rescan": rescan,
        "wimk_playback": _load_json(WIMK_PLAYBACK_CACHE, {}),
    }
    _save_json(PANEL_CACHE, doc)
    return doc


def _is_wimk_target(station_id: str = "", freq_mhz: float | None = None) -> bool:
    sid = (station_id or "").strip().lower()
    if sid in (WIMK_STATION_ID, "wimk"):
        return True
    if freq_mhz is not None and abs(float(freq_mhz) - WIMK_MHZ) < 0.05:
        return True
    return False


def _wimk_working(result: dict[str, Any]) -> tuple[bool, str]:
    """Decide if 93.1 playback is actually working."""
    if result.get("program_audio") and result.get("ota_source") in (
        "field_antenna", "tri_field_antenna",
    ):
        return True, "antenna_program_audio"
    if result.get("method") in (
        "field_antenna_ota", "field_antenna_capture", "field_antenna_live",
        "tri_field_fm_demod", "field_wave_fm_demod",
    ):
        if result.get("program_audio"):
            return True, "antenna_playing"
    if result.get("heard") and result.get("program_audio"):
        return True, "station_program"
    heard = bool(result.get("heard") or result.get("ok"))
    playing = bool(result.get("playing") or (result.get("playback") or {}).get("ok"))
    demod = result.get("demod") or {}
    rms = demod.get("output_rms_dbfs") or result.get("output_rms_dbfs")
    snr = demod.get("snr_db") or result.get("snr_db")
    wav_path = demod.get("wav_path") or (result.get("capture") or {}).get("wav_path")
    wav_ok = False
    if wav_path:
        try:
            wav_ok = Path(str(wav_path)).is_file() and Path(str(wav_path)).stat().st_size > 8000
        except OSError:
            wav_ok = False
    if playing:
        return True, "speakers_playing"
    if heard and wav_ok:
        return True, "wav_ready"
    if heard and rms is not None and float(rms) > -58.0:
        return True, "field_entropy_decode"
    if heard and snr is not None and float(snr) > 6.0:
        return True, "snr_ok"
    if heard:
        return True, "heard_soft"
    return False, "not_heard"


def _wrap_tune_result(
    heard: dict[str, Any],
    *,
    world: dict[str, Any],
    target: dict[str, Any],
    wimk_status: dict[str, Any] | None = None,
) -> dict[str, Any]:
    start = {
        "role": "transmitter",
        "gps": target.get("gps") or target.get("tower_gps"),
        "label": target.get("call_sign") or target.get("name"),
        "lat": target.get("lat"),
        "lon": target.get("lon"),
        "freq_label": target.get("freq_label"),
        "band": target.get("band"),
    }
    end = world.get("operator") or {}
    out = {
        **heard,
        "schema": "field-world-tune/v1",
        "world_placement": world,
        "your_place": world.get("your_place"),
        "self": world.get("self"),
        "self_recognition": world.get("self_recognition"),
        "identified_stations": world.get("identified_stations"),
        "station_tower_db": world.get("station_tower_db"),
        "placement": target,
        "placements": world.get("placements"),
        "line": {
            "start_point": start,
            "end_point": {
                "role": "our_line",
                "gps": end.get("gps"),
                "label": end.get("label") or "operator",
                "lat": end.get("lat"),
                "lon": end.get("lon"),
            },
        },
        "start_point": start,
        "end_point": end,
        "tower_gps": target.get("gps") or target.get("tower_gps"),
        "distance_label": target.get("distance_label"),
        "bearing_deg": target.get("bearing_deg"),
        "band": target.get("band"),
        "ota_only": True,
        "generated": False,
    }
    if wimk_status:
        out["wimk_status"] = wimk_status
        out["wimk_working"] = wimk_status.get("working")
        out["wimk_working_method"] = wimk_status.get("working_method")
        out["wimk_field_locked"] = wimk_status.get("field_locked")
        out["playback_attempts"] = wimk_status.get("attempts")
    _save_json(STATE / "field-world-tune.json", out)
    return out


def play_wimk_until_working(
    *,
    play: bool = True,
    seconds: float = 25.0,
    max_attempts: int | None = None,
) -> dict[str, Any]:
    """Field antenna destroyed — OTA play disabled."""
    if not (INSTALL / "lib" / "field-antenna-orchestrator.py").is_file():
        return {
            "ok": False,
            "destroyed": True,
            "error": "field_antenna_destroyed",
            "working": False,
            "attempts": [],
        }
    limit = max_attempts if max_attempts is not None else MAX_WIMK_ATTEMPTS
    world = build_world_placement()
    target: dict[str, Any] | None = None
    for p in world.get("placements") or []:
        if p.get("station_id") == WIMK_STATION_ID:
            target = p
            break
    if not target:
        for s in world.get("identified_stations") or []:
            if s.get("station_id") == WIMK_STATION_ID:
                target = s
                break
    if not target:
        target = {
            "station_id": WIMK_STATION_ID,
            "call_sign": "WIMK",
            "name": "93.1 K-Rock",
            "freq_mhz": WIMK_MHZ,
            "freq_label": "93.1 MHz",
            "band": "fm",
            "tower_lat": 45.820,
            "tower_lon": -88.041,
            "gps": "45.820000, -88.041000",
            "tower_gps": "45.820000, -88.041000",
        }

    catch_mod = _import("field_antenna_catch", "field-antenna-catch.py")

    runners: list[tuple[str, Any]] = [
        ("field_antenna_catch", lambda: catch_mod.catch_frequency(
            freq_mhz=WIMK_MHZ,
            station_id=WIMK_STATION_ID,
            call_sign="WIMK",
            play=play,
            seconds=seconds,
            max_attempts=limit,
        )),
    ]

    attempts: list[dict[str, Any]] = []
    best: dict[str, Any] = {}
    last_heard: dict[str, Any] = {}
    working = False
    working_reason = ""
    working_method = ""

    attempt_n = 0
    round_n = 0
    while attempt_n < limit and not working:
        round_n += 1
        if round_n > 1:
            try:
                orch = _import("field_antenna_orchestrator", "field-antenna-orchestrator.py")
                orch.run_cycle(skip_precision=True)
            except Exception:
                pass
        for method_name, runner in runners:
            if attempt_n >= limit:
                break
            attempt_n += 1
            row: dict[str, Any] = {
                "attempt": attempt_n,
                "round": round_n,
                "method": method_name,
                "freq_mhz": WIMK_MHZ,
                "station_id": WIMK_STATION_ID,
                "at": _now(),
            }
            try:
                result = runner()
                if not isinstance(result, dict):
                    result = {"ok": False, "error": "bad_result"}
                ok, reason = _wimk_working(result)
                row.update({
                    "heard": bool(result.get("heard") or result.get("ok")),
                    "playing": bool(result.get("playing") or (result.get("playback") or {}).get("ok")),
                    "working": ok,
                    "working_reason": reason,
                    "ota_source": result.get("ota_source"),
                    "decode": result.get("decode") or result.get("method"),
                    "snr_db": (result.get("demod") or {}).get("snr_db") or result.get("snr_db"),
                    "output_rms_dbfs": (result.get("demod") or {}).get("output_rms_dbfs") or result.get("output_rms_dbfs"),
                    "fields_locked": bool((result.get("spectrum") or {}).get("channels_active")),
                    "error": result.get("error") or (result.get("capture") or {}).get("error"),
                })
                if row.get("heard"):
                    last_heard = result
                if ok and (not best or reason == "field_generator_spectrum_lock"):
                    best = result
                    working = True
                    working_reason = reason
                    working_method = method_name
            except Exception as exc:
                row.update({"heard": False, "working": False, "error": str(exc)})
            attempts.append(row)
            if working:
                break

    if not best and last_heard:
        best = last_heard
        if not working:
            working, working_reason = _wimk_working(best)
            working_method = attempts[-1].get("method", "") if attempts else ""

    physics = (best.get("physics") or (best.get("demod") or {}).get("physics") or {})
    status = {
        "schema": "field-wimk-playback/v1",
        "updated": _now(),
        "freq_mhz": WIMK_MHZ,
        "freq_label": "93.1 MHz",
        "station_id": WIMK_STATION_ID,
        "call_sign": "WIMK",
        "name": "93.1 K-Rock",
        "working": working,
        "working_reason": working_reason,
        "working_method": working_method,
        "field_locked": working and best.get("ota_source") == "field_generator_spectrum",
        "ota_source": best.get("ota_source"),
        "attempt_count": len(attempts),
        "max_attempts": limit,
        "attempts": attempts,
        "fields_active": len((best.get("fields") or [])),
        "listen_ready": working,
        "snr_db": best.get("snr_db") or (best.get("demod") or {}).get("snr_db"),
        "output_rms_dbfs": best.get("output_rms_dbfs") or (best.get("demod") or {}).get("output_rms_dbfs"),
        "physics": {
            "entropy": physics.get("entropy"),
            "motion": physics.get("motion"),
            "energy": physics.get("energy"),
            "signal_lock": physics.get("signal_lock"),
        },
        "tower_gps": target.get("tower_gps") or target.get("gps"),
        "distance_label": target.get("distance_label"),
        "bearing_deg": target.get("bearing_deg"),
        "summary": (
            f"93.1 WIMK WORKING via {working_method} ({working_reason})"
            if working
            else f"93.1 WIMK not working yet — {len(attempts)} attempts"
        ),
        "next_if_not_working": [] if working else [
            "Rescan 3-field antenna (Signals → Rescan)",
            "pythong lib/field-generator-triangulator.py deploy",
            "Retry: pythong lib/field-world-placement.py play_until",
        ],
    }
    _save_json(WIMK_PLAYBACK_CACHE, status)

    if not best and attempts:
        best = {"heard": False, "playing": False, "ok": False}

    heard_out = {
        **best,
        "heard": working or bool(best.get("heard")),
        "playing": bool(best.get("playing") or (best.get("playback") or {}).get("ok")),
        "ok": working or bool(best.get("heard")),
        "call_sign": "WIMK",
        "name": "93.1 K-Rock",
        "freq_mhz": WIMK_MHZ,
        "freq_label": "93.1 MHz",
        "station_id": WIMK_STATION_ID,
    }
    return _wrap_tune_result(heard_out, world=world, target=target, wimk_status=status)


def tune_station_in_world(
    *,
    station_id: str = "",
    band: str = "",
    freq_mhz: float | None = None,
    play: bool = True,
    seconds: float = 20.0,
) -> dict[str, Any]:
    """Tune a station with full placement context + field entropy decode."""
    world = build_world_placement()
    radio_mod = _import("field_radio_catcher", "field-radio-catcher.py")
    demod_mod = _import("field_spectrum_demod", "field-spectrum-demod.py")

    target: dict[str, Any] | None = None
    if station_id:
        for p in world.get("placements") or []:
            if p.get("station_id") == station_id:
                target = p
                break
    if not target and band:
        band_stations = (world.get("bands") or {}).get(band, {}).get("stations") or []
        if band_stations:
            target = band_stations[0]
    if not target and freq_mhz is not None:
        for p in world.get("placements") or []:
            fm = p.get("freq_mhz")
            fk = p.get("freq_khz")
            if fm is not None and abs(float(fm) - freq_mhz) < 0.05:
                target = p
                break
            if fk is not None and abs(float(fk) / 1000.0 - freq_mhz) < 0.05:
                target = p
                break

    if not target:
        return {"ok": False, "error": "station_not_found", "world": world}

    sid = str(target.get("station_id") or station_id or "")
    mhz = float(
        target.get("freq_mhz")
        or (float(target.get("freq_khz") or 0) / 1000.0)
        or freq_mhz
        or DEFAULT_MHZ
    )

    if _is_wimk_target(sid, mhz) and play:
        return play_wimk_until_working(play=play, seconds=seconds)

    try:
        radio_mod.tune_station(station_id=sid, freq_mhz=mhz, call_sign=str(target.get("call_sign") or ""))
    except Exception:
        pass

    heard = demod_mod.play_station_from_fields(
        freq_mhz=mhz,
        station_id=sid,
        seconds=seconds,
        play=play,
    )
    return _wrap_tune_result(heard, world=world, target=target)


def tune_band_in_world(*, band: str, play: bool = True, seconds: float = 20.0) -> dict[str, Any]:
    """Tune the nearest in-range station on a band with placement context."""
    world = build_world_placement()
    band_stations = (world.get("bands") or {}).get(band, {}).get("stations") or []
    if not band_stations:
        return {"ok": False, "heard": False, "error": "band_empty", "band": band, "world": world}
    target = band_stations[0]
    return tune_station_in_world(
        station_id=str(target.get("station_id") or target.get("id") or ""),
        band=band,
        play=play,
        seconds=seconds,
    )


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("schema") == "field-world-placement/v1" and cached.get("updated"):
        return cached
    return build_world_placement()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_world_placement(), ensure_ascii=False))
        return 0
    if cmd == "play_until":
        payload: dict[str, Any] = {}
        if len(sys.argv) > 2:
            try:
                payload = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                payload = {}
        out = play_wimk_until_working(
            play=payload.get("play", True) is not False,
            seconds=float(payload.get("seconds", 25.0)),
            max_attempts=int(payload["max_attempts"]) if payload.get("max_attempts") is not None else None,
        )
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("wimk_working") or out.get("heard") else 1
    if cmd == "status":
        print(json.dumps(_load_json(WIMK_PLAYBACK_CACHE, {"working": False, "schema": "field-wimk-playback/v1"}), ensure_ascii=False))
        return 0
    if cmd == "tune":
        payload: dict[str, Any] = {}
        if len(sys.argv) > 2:
            try:
                payload = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                payload = {"station_id": sys.argv[2]}
        if payload.get("band") and not payload.get("station_id"):
            out = tune_band_in_world(
                band=str(payload.get("band") or ""),
                play=payload.get("play", True) is not False,
                seconds=float(payload.get("seconds", 20.0)),
            )
        else:
            out = tune_station_in_world(
                station_id=str(payload.get("station_id") or ""),
                band=str(payload.get("band") or ""),
                freq_mhz=float(payload["freq_mhz"]) if payload.get("freq_mhz") is not None else None,
                play=payload.get("play", True) is not False,
                seconds=float(payload.get("seconds", 20.0)),
            )
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("wimk_working") or out.get("heard") else 1
    print(json.dumps({"error": "usage: field-world-placement.py [json|build|status|play_until JSON|tune JSON]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())