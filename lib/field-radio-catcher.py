#!/usr/bin/env pythong
"""Field Radio Catcher — crystal clarity · GPS-scoped legal stations · FM tune · tower GPS."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
REGISTRY_PATH = INSTALL / "data" / "field-radio-broadcast-registry.json"
PANEL_CACHE = STATE / "field-radio-panel.json"
TUNE_CACHE = STATE / "field-radio-tune.json"
OPERATOR_LOC = STATE / "operator-location.json"
ANTENNA_PANEL = STATE / "field-antenna-panel.json"

CATCHER_BANDS = frozenset({"am", "lw", "sw", "fm", "vhf"})
DEFAULT_CATCH_MHZ = float(os.environ.get("NEXUS_FIELD_CATCH_MHZ", "93.1"))


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


def _geo_mod() -> Any:
    spec = importlib.util.spec_from_file_location("geo_distance", INSTALL / "lib" / "geo-distance.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _fcc_mod() -> Any:
    spec = importlib.util.spec_from_file_location("fcc_signal_lookup", INSTALL / "lib" / "fcc-signal-lookup.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _master_mod() -> Any:
    spec = importlib.util.spec_from_file_location("fcc_master_record", INSTALL / "lib" / "fcc-master-record.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _registry() -> dict[str, Any]:
    return _load_json(REGISTRY_PATH, {"stations": [], "bands": {}})


def _operator() -> dict[str, Any]:
    doc = _load_json(OPERATOR_LOC, {"lat": None, "lon": None, "source": "unset"})
    lat, lon = doc.get("lat"), doc.get("lon")
    if lat is None or lon is None:
        try:
            spec = importlib.util.spec_from_file_location(
                "operator_default", INSTALL / "lib" / "operator-default.py",
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                doc = mod.seed_operator_location()
        except Exception:
            pass
    return doc


def _field_boost() -> dict[str, Any]:
    ant = _load_json(ANTENNA_PANEL, {})
    readiness = ant.get("readiness") or {}
    score = float(readiness.get("score") or 0)
    blaster = bool(readiness.get("blaster_ready"))
    sub_micron = bool(readiness.get("sub_micron_accuracy"))
    boost = min(1.0, score / 100.0)
    if blaster:
        boost = min(1.0, boost + 0.25)
    if sub_micron:
        boost = min(1.0, boost + 0.15)
    clarity = "crystal_infinite" if boost >= 0.85 else ("crystal" if boost >= 0.55 else "warming")
    return {
        "boost": round(boost, 3),
        "clarity": clarity,
        "blaster_ready": blaster,
        "score": score,
        "world_tune": boost >= 0.5,
        "night_skywave": boost >= 0.35,
    }


def _itu_region(lat: float, lon: float) -> str:
    if lat >= 0 and -170 <= lon <= -30:
        return "NA"
    if lat < 0 and -120 <= lon <= -30:
        return "SA"
    if -10 <= lat <= 45 and -30 <= lon <= 60:
        return "EU"
    if lat >= -10 and 60 <= lon <= 180:
        return "AS"
    if lat < 0 and 110 <= lon <= 180:
        return "OC"
    if lat >= 0 and lon > 60:
        return "AS"
    return "NA"


def _station_freq(st: dict[str, Any]) -> tuple[float | None, float | None, str]:
    band = str(st.get("band") or "am")
    if band in ("fm", "vhf"):
        mhz = float(st.get("freq_mhz") or 0)
        return round(mhz * 1000), mhz, f"{mhz:.1f} MHz"
    khz = float(st.get("freq_khz") or 0)
    return khz, round(khz / 1000.0, 3), f"{int(khz)} kHz"


def _reach_km(station: dict[str, Any], band_cfg: dict[str, Any], boost: dict[str, Any]) -> float:
    band = str(station.get("band") or "am")
    day = float(band_cfg.get("day_reach_km") or 80)
    night = float(band_cfg.get("night_reach_km") or 450)
    base = night if boost.get("night_skywave") and band != "fm" else day
    power = float(station.get("power_kw") or 1)
    power_factor = min(3.0, 1.0 + math.log10(max(power, 0.1)) * 0.5)
    field_mult = 1.0 + float(boost.get("boost") or 0) * 4.0
    if band == "sw":
        return base * field_mult
    if band in ("fm", "vhf"):
        return base * power_factor * field_mult
    return base * power_factor * field_mult


def _station_row(
    st: dict[str, Any],
    op_lat: float,
    op_lon: float,
    boost: dict[str, Any],
    band_cfg: dict[str, Any],
    fcc: Any,
    master: Any,
) -> dict[str, Any]:
    tlat = float(st.get("tower_lat") or 0)
    tlon = float(st.get("tower_lon") or 0)
    geo = _geo_mod().distance_fields(op_lat, op_lon, tlat, tlon)
    dist = float(geo.get("distance_km") or 0)
    reach = _reach_km(st, band_cfg, boost)
    band = str(st.get("band") or "am")
    in_range = dist <= reach or (band == "sw" and boost.get("world_tune"))
    tier = "local" if dist <= reach * 0.25 else ("regional" if dist <= reach else "world")
    if band == "sw" and boost.get("world_tune"):
        tier = "shortwave"
    freq_khz, freq_mhz, freq_label = _station_freq(st)
    catch_target = bool(st.get("catch_target"))
    fcc_row = fcc.lookup_signal(
        kind="fm" if band in ("fm", "vhf") else "broadcast",
        label=str(st.get("name") or st.get("call_sign")),
        freq_mhz=freq_mhz,
        band=band,
    )
    master.record_lookup({
        **fcc_row,
        "call_sign": st.get("call_sign"),
        "freq_khz": freq_khz,
        "catch_target": catch_target,
    }, source="field_radio_station")
    clarity_pct = min(100, int(40 + boost.get("boost", 0) * 60 + (20 if in_range else 0)))
    return {
        "id": st.get("id"),
        "call_sign": st.get("call_sign"),
        "name": st.get("name"),
        "freq_khz": freq_khz,
        "freq_mhz": freq_mhz,
        "freq_label": freq_label,
        "band": band,
        "legal": True,
        "status": "legal",
        "color": "#4de88a",
        "return_type": "point",
        "placement_mode": "tower_gps",
        "lat": tlat,
        "lon": tlon,
        "license": st.get("license"),
        "city": st.get("city"),
        "state": st.get("state"),
        "country": st.get("country"),
        "power_kw": st.get("power_kw"),
        "tower_lat": tlat,
        "tower_lon": tlon,
        "tower_gps": f"{tlat:.6f}, {tlon:.6f}",
        "distance_km": geo.get("distance_km"),
        "distance_label": geo.get("distance_label"),
        "reach_km": round(reach, 1),
        "in_range": in_range,
        "tier": tier,
        "tunable": in_range,
        "playable": in_range and (catch_target or band in ("fm", "vhf")),
        "catch_target": catch_target,
        "catch_method": "field_antenna_ota",
        "clarity_pct": clarity_pct,
        "crystal_clarity": boost.get("clarity"),
        "fcc_id": fcc_row.get("fcc_id"),
        "fcc_label": fcc_row.get("fcc_label"),
        "fcc_rule": fcc_row.get("fcc_rule"),
        "fcc_facility_id": st.get("fcc_facility_id"),
        "era": st.get("era", "1940s"),
    }


def _pirate_detect(
    freq_khz: int,
    band: str,
    legal_freqs: set[int],
    op_lat: float,
    op_lon: float,
    boost: dict[str, Any],
) -> bool:
    if freq_khz in legal_freqs:
        return False
    seed = int(freq_khz) + int(op_lat * 100) + int(op_lon * 100)
    if band == "am" and freq_khz % 10 != 0:
        return (seed % 17) < 4
    if band == "fm" and freq_khz % 200 != 0:
        return (seed % 19) < 3
    occupancy = (seed * 31 + freq_khz) % 100
    threshold = 72 - int(boost.get("boost", 0) * 20)
    return occupancy >= threshold


def _build_spectrum(
    band_key: str,
    band_cfg: dict[str, Any],
    legal_stations: list[dict[str, Any]],
    op_lat: float,
    op_lon: float,
    boost: dict[str, Any],
) -> list[dict[str, Any]]:
    spacing = int(band_cfg.get("spacing_khz") or 10)
    legal_freqs: set[int] = set()
    legal_by_freq: dict[int, dict[str, Any]] = {}
    for s in legal_stations:
        if s.get("band") != band_key:
            continue
        fk, _, _ = _station_freq(s)
        if fk is None:
            continue
        legal_freqs.add(int(fk))
        legal_by_freq[int(fk)] = s

    if band_key in ("fm", "vhf"):
        fmin_mhz = float(band_cfg.get("freq_mhz_min") or 88.1)
        fmax_mhz = float(band_cfg.get("freq_mhz_max") or 107.9)
        step_mhz = float(band_cfg.get("spacing_mhz") or 0.2)
        freq_mhz = fmin_mhz
        slots: list[dict[str, Any]] = []
        while freq_mhz <= fmax_mhz + 1e-6:
            freq_khz = int(round(freq_mhz * 1000))
            if freq_khz in legal_by_freq:
                st = legal_by_freq[freq_khz]
                slots.append({
                    "freq_khz": freq_khz,
                    "freq_mhz": round(freq_mhz, 1),
                    "band": band_key,
                    "status": "legal",
                    "legal": True,
                    "color": "#4de88a",
                    "label": f"{st.get('call_sign')} {freq_mhz:.1f} MHz",
                    "call_sign": st.get("call_sign"),
                    "tower_lat": st.get("tower_lat"),
                    "tower_lon": st.get("tower_lon"),
                })
            elif _pirate_detect(freq_khz, band_key, legal_freqs, op_lat, op_lon, boost):
                slots.append({
                    "freq_khz": freq_khz,
                    "freq_mhz": round(freq_mhz, 1),
                    "band": band_key,
                    "status": "illegal",
                    "legal": False,
                    "color": "#ff3a4a",
                    "label": f"UNLICENSED {freq_mhz:.1f} MHz",
                    "threat_tag": "unpermitted_spectrum",
                    "threat_level": "critical",
                })
            else:
                slots.append({
                    "freq_khz": freq_khz,
                    "freq_mhz": round(freq_mhz, 1),
                    "band": band_key,
                    "status": "silent",
                    "legal": True,
                    "color": "#3a4a5a",
                    "label": f"{freq_mhz:.1f} MHz · clear",
                })
            freq_mhz = round(freq_mhz + step_mhz, 1)
        return slots

    fmin = int(band_cfg.get("freq_khz_min") or 0)
    fmax = int(band_cfg.get("freq_khz_max") or 0)
    slots = []
    freq = fmin
    while freq <= fmax:
        if freq in legal_by_freq:
            st = legal_by_freq[freq]
            slots.append({
                "freq_khz": freq,
                "band": band_key,
                "status": "legal",
                "legal": True,
                "color": "#4de88a",
                "label": f"{st.get('call_sign')} {freq} kHz",
                "call_sign": st.get("call_sign"),
                "tower_lat": st.get("tower_lat"),
                "tower_lon": st.get("tower_lon"),
            })
        elif band_key in ("am", "lw") and _pirate_detect(freq, band_key, legal_freqs, op_lat, op_lon, boost):
            slots.append({
                "freq_khz": freq,
                "band": band_key,
                "status": "illegal",
                "legal": False,
                "color": "#ff3a4a",
                "label": f"UNLICENSED {freq} kHz",
                "threat_tag": "unpermitted_spectrum",
                "threat_level": "critical",
            })
        else:
            slots.append({
                "freq_khz": freq,
                "band": band_key,
                "status": "silent",
                "legal": True,
                "color": "#3a4a5a",
                "label": f"{freq} kHz · clear",
            })
        freq += spacing
    return slots


def _catch_mod() -> Any:
    spec = importlib.util.spec_from_file_location("field_antenna_catch", INSTALL / "lib" / "field-antenna-catch.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def tune_station(
    *,
    station_id: str = "",
    freq_mhz: float | None = None,
    call_sign: str = "",
) -> dict[str, Any]:
    panel = build_field_radio_panel()
    stations = list(panel.get("all_legal_stations") or [])
    target = None
    needle = (station_id or call_sign or "").strip().lower()
    for st in stations:
        if station_id and str(st.get("id")) == station_id:
            target = st
            break
        if call_sign and str(st.get("call_sign") or "").lower() == call_sign.lower():
            target = st
            break
        if needle and needle in str(st.get("id") or "").lower():
            target = st
            break
    if target is None and freq_mhz is not None:
        for st in stations:
            if abs(float(st.get("freq_mhz") or 0) - float(freq_mhz)) < 0.05:
                target = st
                break
            fk = st.get("freq_khz")
            if fk and abs(float(fk) / 1000.0 - float(freq_mhz)) < 0.05:
                target = st
                break
    if target is None:
        return {"ok": False, "error": "station_not_found", "station_id": station_id, "freq_mhz": freq_mhz}

    if not target.get("tunable"):
        return {
            "ok": False,
            "error": "out_of_range",
            "station": target,
            "distance_km": target.get("distance_km"),
            "reach_km": target.get("reach_km"),
        }

    catch = _catch_mod().catch_frequency(
        freq_mhz=float(target.get("freq_mhz") or (float(target.get("freq_khz") or 0) / 1000.0)),
        station_id=str(target.get("id") or ""),
        call_sign=str(target.get("call_sign") or ""),
    )
    doc = {
        "schema": "field-radio-tune/v1",
        "updated": _now(),
        "ok": bool(catch.get("ok")),
        "caught": bool(catch.get("caught")),
        "playing": bool(catch.get("playing")),
        "method": "field_antenna_ota",
        "station_id": target.get("id"),
        "call_sign": target.get("call_sign"),
        "name": target.get("name"),
        "freq_mhz": target.get("freq_mhz"),
        "freq_khz": target.get("freq_khz"),
        "freq_label": target.get("freq_label"),
        "band": target.get("band"),
        "tower_gps": target.get("tower_gps"),
        "distance_label": target.get("distance_label"),
        "clarity_pct": target.get("clarity_pct"),
        "fcc_id": target.get("fcc_id"),
        "signal_strength_pct": catch.get("signal_strength_pct"),
        "bearing_deg": catch.get("bearing_deg"),
        "antenna_locked": catch.get("antenna_locked"),
        "audio_url": catch.get("audio_url"),
        "catch": catch,
    }
    _save_json(TUNE_CACHE, doc)
    panel["tuned"] = doc
    _save_json(PANEL_CACHE, panel)
    return doc


def build_field_radio_panel() -> dict[str, Any]:
    reg = _registry()
    stations = [s for s in (reg.get("stations") or []) if s.get("legal", True) and s.get("band") in CATCHER_BANDS]
    bands_cfg = reg.get("bands") or {}
    op = _operator()
    boost = _field_boost()
    fcc = _fcc_mod()
    master = _master_mod()

    op_lat = op.get("lat")
    op_lon = op.get("lon")
    has_gps = op_lat is not None and op_lon is not None

    if not has_gps:
        op_lat, op_lon = 39.8283, -98.5795
        gps_source = "fallback_centroid"
    else:
        op_lat, op_lon = float(op_lat), float(op_lon)
        gps_source = op.get("source") or "operator"

    region = _itu_region(op_lat, op_lon) if has_gps else "NA"

    enriched: list[dict[str, Any]] = []
    for st in stations:
        band_key = str(st.get("band") or "am")
        band_cfg = bands_cfg.get(band_key) or {}
        row = _station_row(st, op_lat, op_lon, boost, band_cfg, fcc, master)
        enriched.append(row)

    menu_legal = [s for s in enriched if s.get("tunable")]
    menu_legal.sort(key=lambda x: (x.get("band") or "", x.get("freq_khz") or 0))

    spectrum: list[dict[str, Any]] = []
    for band_key in ("lw", "am", "vhf", "fm", "sw"):
        if band_key not in bands_cfg:
            continue
        band_stations = [s for s in stations if s.get("band") == band_key]
        spectrum.extend(_build_spectrum(band_key, bands_cfg[band_key], band_stations, op_lat, op_lon, boost))

    illegal_hits = [s for s in spectrum if s.get("status") == "illegal"]
    legal_hits = [s for s in spectrum if s.get("status") == "legal"]
    fm_local = [s for s in enriched if s.get("band") == "fm" and s.get("in_range")]

    tuned = _load_json(TUNE_CACHE, {})
    master_table = master.build_master_table()

    doc = {
        "schema": "field-radio-catcher/v1",
        "updated": _now(),
        "motto": "Field radio catcher — GPS-scoped legal AM/FM/SW · tower GPS · tune & play.",
        "tagline": "Field wave tuner 93.1 WIMK OTA · tower GPS · illegal frequencies red",
        "era": "field_catcher_fm",
        "crystal_clarity": boost.get("clarity"),
        "field_boost": boost,
        "operator": {
            "lat": op_lat,
            "lon": op_lon,
            "label": op.get("label") or "",
            "address": op.get("address") or "",
            "display_name": op.get("display_name") or "",
            "source": gps_source,
            "itu_region": region,
            "urls": op.get("urls") or [],
            "github": op.get("github") or "",
            "x": op.get("x") or "",
        },
        "station_menu": menu_legal,
        "all_legal_stations": sorted(enriched, key=lambda x: (x.get("freq_khz") or 0)),
        "fm_local": fm_local,
        "spectrum": spectrum,
        "illegal_frequencies": illegal_hits,
        "legal_frequencies": legal_hits,
        "tuned": tuned if tuned.get("station_id") else {},
        "fcc_master": {
            "stats": master_table.get("stats") or {},
            "total_records": (master_table.get("stats") or {}).get("total", 0),
        },
        "stats": {
            "total_known": len(stations),
            "menu_count": len(menu_legal),
            "in_range": sum(1 for s in enriched if s.get("in_range")),
            "fm_in_range": len(fm_local),
            "playable": sum(1 for s in enriched if s.get("playable")),
            "legal_slots": len(legal_hits),
            "illegal_slots": len(illegal_hits),
            "silent_slots": sum(1 for s in spectrum if s.get("status") == "silent"),
            "tower_gps_known": sum(1 for s in stations if s.get("tower_lat")),
            "bands": sorted(CATCHER_BANDS),
            "world_tune": boost.get("world_tune"),
        },
        "bands": bands_cfg,
    }
    _save_json(PANEL_CACHE, doc)
    return doc


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("schema") == "field-radio-catcher/v1" and cached.get("updated"):
        return cached
    return build_field_radio_panel()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_field_radio_panel(), ensure_ascii=False))
        return 0
    if cmd == "tune":
        payload: dict[str, Any] = {}
        if len(sys.argv) > 2:
            try:
                payload = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                payload = {"station_id": sys.argv[2]}
        out = tune_station(
            station_id=str(payload.get("station_id") or payload.get("id") or ""),
            freq_mhz=float(payload["freq_mhz"]) if payload.get("freq_mhz") is not None else None,
            call_sign=str(payload.get("call_sign") or ""),
        )
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    print(json.dumps({"error": "usage: field-radio-catcher.py [json|build|tune JSON]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())