#!/usr/bin/env pythong
"""Signals field — gorgeous antenna + RF + audio pulse payload for Signals tab."""
from __future__ import annotations

import importlib.util
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_CACHE = STATE / "signals-field-panel.json"
RF_PANEL = STATE / "field-rf-panel.json"
AUDIO_PANEL = STATE / "audio-train-panel.json"
HOME_PANEL = STATE / "home-protector-panel.json"
ANTENNA_PANEL = STATE / "field-antenna-panel.json"
RADIO_PANEL = STATE / "field-radio-panel.json"
SECURE_LINE_DOCTRINE = INSTALL / "data" / "signals-field-secure-line-doctrine.json"
SENSE_PANEL = STATE / "field-sense-package-panel.json"


def _secure_signal_line() -> dict[str, Any]:
    """Plated secure line in/out — melded to Hostess7; witness only, never system corrupt."""
    doctrine = _load_json(SECURE_LINE_DOCTRINE, {})
    sense = _load_json(SENSE_PANEL, {})
    h7 = (sense.get("members") or {}).get("hostess7") or {}
    policy = doctrine.get("policy") or {}
    plate = sense.get("plate_link") or {}
    return {
        "schema": "secure-signal-line/v1",
        "motto": doctrine.get("motto")
        or "One secure signal line in and out — plated, melded to Hostess7, never system corrupt.",
        "plated": True,
        "meld_to_hostess7": True,
        "system_corrupt": False,
        "ingress": {
            "sealed": policy.get("ingress_sealed", True),
            "witness": "hostess7",
            "brain_witness_only": h7.get("brain_witness_only", True),
            "relocate": h7.get("brain_relocate", False),
        },
        "egress": {
            "sealed": policy.get("egress_sealed", True),
            "witness": "hostess7",
            "chain_hash": sense.get("chain_hash"),
            "plate_generation": plate.get("plate_generation"),
        },
        "hostess7": {
            "brain_protected": h7.get("brain_protected"),
            "smart_one": (h7.get("smart_one") or {}).get("label"),
            "brain_score": h7.get("brain_score"),
            "brain_relocate": False,
            "destructive_sync": False,
        },
        "sense_package_generation": sense.get("generation"),
        "shared_program_comms": True,
    }


def _operator_profile() -> dict[str, Any]:
    try:
        spec = importlib.util.spec_from_file_location(
            "operator_default", INSTALL / "lib" / "operator-default.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.panel_operator()
    except Exception:
        pass
    return {}


def _fcc_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "fcc_signal_lookup", INSTALL / "lib" / "fcc-signal-lookup.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod

BAND_COLORS = {
    "2.4GHz": "#4de88a",
    "5GHz": "#2ec96a",
    "6GHz": "#8af0b0",
    "unknown": "#5a9a70",
}

FIELD_GREEN = {
    "2.4GHz": "#4de88a",
    "5GHz": "#2ec96a",
    "6GHz": "#8af0b0",
    "unknown": "#3dd68c",
}

MODALITY_COLORS = {
    "rf": "#4de88a",
    "audio": "#e8c878",
    "wired": "#7ab8ff",
    "ble": "#b88af0",
    "laser": "#ff6eb4",
    "broadcast": "#8af0c8",
}


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


def _extra_modality_channels(
    antenna_doc: dict[str, Any],
    home: dict[str, Any],
) -> list[dict[str, Any]]:
    """Laser, BLE, wired pulse channels from field-antenna orchestrator."""
    channels: list[dict[str, Any]] = []
    fcc = _fcc_mod()
    modalities = antenna_doc.get("modalities") or {}

    laser = modalities.get("laser") or {}
    for band in list(laser.get("optical_bands") or [])[:6]:
        fcc_row = fcc.lookup_signal(kind="laser", label=str(band.get("label") or "laser"))
        strength = 60 if band.get("recognized") else 12
        channels.append({
            "id": f"laser_{band.get('id', 'opt')}",
            "label": str(band.get("label") or "laser"),
            "kind": "laser",
            "modality": "laser",
            "wavelength_nm": band.get("wavelength_nm"),
            "energy": round(min(1.0, strength / 100.0), 3),
            "strength": strength,
            "recognized": band.get("recognized", False),
            "color": MODALITY_COLORS["laser"],
            "fcc_id": fcc_row.get("fcc_id"),
            "fcc_label": fcc_row.get("fcc_label"),
            "threat_tag": fcc_row.get("threat_tag"),
            "threat_level": fcc_row.get("level", "none"),
        })

    ble = modalities.get("ble") or {}
    for dev in list(ble.get("devices") or [])[:8]:
        fcc_row = fcc.lookup_signal(kind="ble", label=str(dev.get("name") or "ble"))
        channels.append({
            "id": f"ble_{re.sub(r'[^0-9a-f]', '', str(dev.get('mac', '')).lower())[:12] or 'dev'}",
            "label": str(dev.get("name") or dev.get("mac") or "BLE"),
            "kind": "ble",
            "modality": "ble",
            "mac": dev.get("mac"),
            "energy": 0.42,
            "strength": 42,
            "recognized": True,
            "color": MODALITY_COLORS["ble"],
            "fcc_id": fcc_row.get("fcc_id"),
            "fcc_label": fcc_row.get("fcc_label"),
            "threat_tag": fcc_row.get("threat_tag"),
            "threat_level": fcc_row.get("level", "none"),
        })

    wired = modalities.get("wired") or {}
    for ent in list(wired.get("entities") or [])[:8]:
        fcc_row = fcc.lookup_signal(
            kind="wired",
            label=str(ent.get("label") or ent.get("entity_id") or "lan"),
            ip=str(ent.get("ip") or ""),
            permission=str(ent.get("permission") or ""),
        )
        channels.append({
            "id": f"wired_{ent.get('entity_id', 'lan')}",
            "label": str(ent.get("label") or ent.get("ip") or "LAN"),
            "kind": "wired",
            "modality": "wired",
            "ip": ent.get("ip"),
            "energy": 0.35,
            "strength": 35,
            "recognized": True,
            "color": MODALITY_COLORS["wired"],
            "fcc_id": fcc_row.get("fcc_id"),
            "fcc_label": fcc_row.get("fcc_label"),
            "threat_tag": fcc_row.get("threat_tag"),
            "threat_level": fcc_row.get("level", "none"),
        })

    if not channels and home:
        for ent in list(home.get("entities") or home.get("table") or [])[:4]:
            if not (ent.get("on_wire") or str(ent.get("kind", "")).lower() in ("lan", "wire", "ethernet")):
                continue
            fcc_row = fcc.lookup_signal(
                kind="wired",
                label=str(ent.get("label") or "lan"),
                ip=str(ent.get("ip") or ""),
            )
            channels.append({
                "id": f"wired_{ent.get('entity_id', 'lan')}",
                "label": str(ent.get("label") or ent.get("ip") or "LAN"),
                "kind": "wired",
                "modality": "wired",
                "energy": 0.3,
                "strength": 30,
                "recognized": True,
                "color": MODALITY_COLORS["wired"],
                "fcc_id": fcc_row.get("fcc_id"),
                "fcc_label": fcc_row.get("fcc_label"),
                "threat_tag": fcc_row.get("threat_tag"),
                "threat_level": fcc_row.get("level", "none"),
            })
    return channels


def _radio_pulse_channels(radio_doc: dict[str, Any]) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = []
    fcc = _fcc_mod()
    for st in list(radio_doc.get("station_menu") or [])[:24]:
        band = str(st.get("band") or "am")
        freq_mhz = st.get("freq_mhz")
        if freq_mhz is None:
            freq_mhz = round(float(st.get("freq_khz") or 0) / 1000.0, 3)
        fcc_row = fcc.lookup_signal(
            kind="fm" if band == "fm" else "broadcast",
            label=str(st.get("name") or st.get("call_sign")),
            freq_mhz=freq_mhz,
            band=band,
        )
        energy = round(min(1.0, (st.get("clarity_pct") or 50) / 100.0), 3)
        freq_label = st.get("freq_label") or (
            f"{st.get('freq_mhz')} MHz" if band == "fm" else f"{st.get('freq_khz')} kHz"
        )
        channels.append({
            "id": f"radio_{st.get('id', 'st')}",
            "label": f"{st.get('call_sign')} · {freq_label}",
            "kind": "broadcast",
            "modality": "broadcast",
            "freq_khz": st.get("freq_khz"),
            "band": st.get("band"),
            "energy": energy,
            "strength": st.get("clarity_pct") or 50,
            "recognized": True,
            "legal": True,
            "color": MODALITY_COLORS["broadcast"],
            "tower_gps": st.get("tower_gps"),
            "distance_label": st.get("distance_label"),
            "fcc_id": fcc_row.get("fcc_id"),
            "fcc_label": fcc_row.get("fcc_label"),
            "threat_tag": fcc_row.get("threat_tag"),
            "threat_level": fcc_row.get("level", "none"),
        })
    for bad in list(radio_doc.get("illegal_frequencies") or [])[:12]:
        fcc_row = fcc.lookup_signal(
            kind="broadcast",
            label=str(bad.get("label")),
            freq_mhz=round(float(bad.get("freq_khz") or 0) / 1000.0, 3),
            band=str(bad.get("band") or "am"),
            permission="unlicensed",
            hostile_intent=True,
        )
        channels.append({
            "id": f"pirate_{bad.get('freq_khz')}",
            "label": str(bad.get("label") or "UNLICENSED"),
            "kind": "broadcast",
            "modality": "broadcast",
            "freq_khz": bad.get("freq_khz"),
            "band": bad.get("band"),
            "energy": 0.88,
            "strength": 88,
            "recognized": True,
            "legal": False,
            "color": "#ff3a4a",
            "fcc_id": fcc_row.get("fcc_id"),
            "fcc_label": fcc_row.get("fcc_label"),
            "threat_tag": fcc_row.get("threat_tag"),
            "threat_level": fcc_row.get("level", "critical"),
        })
    return channels


def _pulse_channels(
    rf: dict[str, Any],
    audio: dict[str, Any],
    fcc_doc: dict[str, Any],
    frequency_registry: dict[str, Any] | None = None,
    antenna_doc: dict[str, Any] | None = None,
    home: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    channels: list[dict[str, Any]] = []
    registry = frequency_registry or rf.get("frequency_registry") or {}
    reg_entries = list(registry.get("entries") or [])

    if reg_entries:
        for entry in reg_entries:
            strength = int(entry.get("strength") or 0)
            band = str(entry.get("band") or "unknown")
            ch = entry.get("channel")
            freq = entry.get("freq_mhz")
            label = f"ch{ch}" if ch is not None else f"{freq} MHz"
            fcc = _fcc_mod().lookup_signal(
                kind="wifi",
                freq_mhz=freq,
                channel=ch,
                band=band,
                label=label,
            )
            energy = round(min(1.0, max(0.02, strength / 100.0)), 3)
            channels.append({
                "id": f"freq_{band.replace('.', '').replace('GHz', 'g')}_{ch or freq}",
                "label": label,
                "kind": "rf",
                "band": band,
                "channel": ch,
                "freq_mhz": freq,
                "energy": energy,
                "strength": strength,
                "recognized": entry.get("recognized", False),
                "color": FIELD_GREEN.get(band, FIELD_GREEN["unknown"]),
                "source_count": entry.get("source_count") or 0,
                "fcc_id": fcc.get("fcc_id"),
                "fcc_label": fcc.get("fcc_label"),
                "threat_tag": fcc.get("threat_tag"),
                "threat_level": fcc.get("level", "none"),
            })
    else:
        antenna = rf.get("antenna") or {}
        bands = list(antenna.get("bands_seen") or [])
        scan = rf.get("scan_material") or []
        for band in bands or ["2.4GHz", "5GHz"]:
            hits = [a for a in scan if str(a.get("band") or "") == band]
            energy = 0.0
            if hits:
                energy = sum(int(a.get("signal_dbm") or 0) for a in hits) / (len(hits) * 100.0)
            sample = hits[0] if hits else {}
            fcc = _fcc_mod().lookup_signal(
                kind="wifi",
                freq_mhz=sample.get("freq_mhz"),
                channel=sample.get("channel"),
                band=band,
                label=band,
            )
            channels.append({
                "id": f"rf_{band.replace('.', '').replace('GHz', 'g')}",
                "label": band,
                "kind": "rf",
                "energy": round(min(1.0, max(0.05, energy)), 3),
                "color": FIELD_GREEN.get(band, FIELD_GREEN["unknown"]),
                "source_count": len(hits),
                "fcc_id": fcc.get("fcc_id"),
                "fcc_label": fcc.get("fcc_label"),
                "threat_tag": fcc.get("threat_tag"),
                "threat_level": fcc.get("level", "none"),
            })
    for src in list((audio.get("sources") or {}).values())[:6]:
        fcc = _fcc_mod().lookup_signal(
            kind="audio",
            label=str(src.get("label") or src.get("source_id") or "audio"),
            hostile_intent=not src.get("acceptable", True),
        )
        channels.append({
            "id": f"audio_{src.get('source_id', 'src')}",
            "label": str(src.get("label") or src.get("source_id") or "audio"),
            "kind": "audio",
            "energy": round(min(1.0, (src.get("sample_count") or 1) / 20.0), 3),
            "color": fcc.get("color") or ("#e8c878" if src.get("acceptable", True) else "#ff5c7a"),
            "acceptable": src.get("acceptable", True),
            "fcc_id": fcc.get("fcc_id"),
            "fcc_label": fcc.get("fcc_label"),
            "threat_tag": fcc.get("threat_tag"),
            "threat_level": fcc.get("level", "none"),
        })
    channels.extend(_extra_modality_channels(antenna_doc or {}, home or {}))
    limit = max(len(channels), 12) if reg_entries else 24
    return channels[:limit]


def build_signals_field() -> dict[str, Any]:
    rf = _load_json(RF_PANEL, {})
    audio = _load_json(AUDIO_PANEL, {})
    home = _load_json(HOME_PANEL, {})
    antenna_doc = _load_json(ANTENNA_PANEL, {})
    radio_doc = _load_json(RADIO_PANEL, {})
    antenna = rf.get("antenna") or {}
    fields = list(antenna.get("antenna_fields") or [])
    resolution = antenna.get("resolution") or {}
    material = rf.get("material_field") or {}

    op = (radio_doc.get("operator") or {}) if radio_doc else {}
    profile = _operator_profile()
    if not op.get("display_name"):
        op = {**profile, **op}
    op_lat = op.get("lat")
    op_lon = op.get("lon")

    def _point_norm(lat: Any, lon: Any) -> dict[str, float] | None:
        if lat is None or lon is None or op_lat is None or op_lon is None:
            return None
        try:
            dlat = float(lat) - float(op_lat)
            dlon = float(lon) - float(op_lon)
            return {"lat": float(lat), "lon": float(lon), "norm_x": 0.5 + dlon * 4.0, "norm_y": 0.5 - dlat * 4.0}
        except (TypeError, ValueError):
            return None

    antennas = []
    for i, f in enumerate(fields):
        antennas.append({
            "device": f.get("device"),
            "state": f.get("state"),
            "mac": f.get("mac"),
            "phy": f.get("phy"),
            "tuned_band": f.get("tuned_band"),
            "tuned_channel": f.get("tuned_channel"),
            "scan_count": f.get("scan_count") or 0,
            "signal_max": f.get("signal_max") or 0,
            "signal_avg": f.get("signal_avg") or 0,
            "connected": f.get("connected"),
            "return_type": "point",
            "pulse_phase": round((i * 0.17) % 1.0, 3),
            "color": FIELD_GREEN.get(str(f.get("tuned_band") or ""), FIELD_GREEN["unknown"]),
        })

    fcc = _fcc_mod().identify_all(rf_doc=rf, audio_doc=audio, home_doc=home)
    try:
        spec = importlib.util.spec_from_file_location(
            "fcc_master_record", INSTALL / "lib" / "fcc-master-record.py",
        )
        if spec and spec.loader:
            _m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_m)
            master = _m.build_master_table()
            fcc["master_record"] = master
            fcc["identified"] = (master.get("records") or []) + list(fcc.get("identified") or [])
            fcc["stats"] = {
                **(fcc.get("stats") or {}),
                "total": len(fcc["identified"]),
                "master_total": (master.get("stats") or {}).get("total", 0),
                "jsonl_lines": (master.get("stats") or {}).get("jsonl_lines", 0),
            }
    except Exception:
        pass
    threat_idx = _fcc_mod().build_threat_index(rf)

    point_index: dict[str, dict[str, Any]] = {}
    for st in list(radio_doc.get("station_menu") or radio_doc.get("all_legal_stations") or []):
        if st.get("tower_lat") is not None and st.get("tower_lon") is not None:
            point_index[f"radio:{st.get('id')}"] = st
    ant_doc = _load_json(ANTENNA_PANEL, {})
    prec = (ant_doc.get("modalities") or {}).get("precision_gps") or {}
    for p in list(prec.get("placements") or (ant_doc.get("sub_micron") or {}).get("placements") or []):
        if p.get("lat") is not None and p.get("lon") is not None:
            point_index[str(p.get("id") or f"place_{len(point_index)}")] = p

    scan_dots = []
    tower_pts = list(point_index.values())[:48]
    for i, ap in enumerate((rf.get("scan_material") or [])[:48]):
        sig = int(ap.get("signal_dbm") or 0)
        if sig < 12:
            continue
        bnorm = str(ap.get("bssid") or "")
        threat = threat_idx.get(re.sub(r"[^0-9a-f]", "", bnorm.lower())[:12])
        ann = _fcc_mod().annotate_wifi_ap(ap, threat)
        fc = ann.get("fcc") or {}
        pt = tower_pts[i % len(tower_pts)] if tower_pts else {}
        plat = pt.get("tower_lat") or pt.get("lat")
        plon = pt.get("tower_lon") or pt.get("lon")
        norm = _point_norm(plat, plon)
        scan_dots.append({
            "ssid": ap.get("ssid"),
            "bssid": ap.get("bssid"),
            "band": ap.get("band"),
            "channel": ap.get("channel"),
            "freq_mhz": ap.get("freq_mhz"),
            "signal": sig,
            "return_type": "point",
            "lat": plat,
            "lon": plon,
            "tower_gps": pt.get("tower_gps"),
            "norm_x": (norm or {}).get("norm_x"),
            "norm_y": (norm or {}).get("norm_y"),
            "color": fc.get("color") or BAND_COLORS.get(str(ap.get("band") or ""), "#7a9ab8"),
            "fcc_id": fc.get("fcc_id"),
            "fcc_label": fc.get("fcc_label"),
            "fcc_rule": fc.get("fcc_rule"),
            "permitted": fc.get("permitted"),
            "threat_tag": fc.get("threat_tag"),
            "threat_label": fc.get("label"),
            "threat_level": fc.get("level", "none"),
            "shoot_to_kill": fc.get("shoot_to_kill", False),
        })

    frequency_registry = rf.get("frequency_registry") or {}
    if not frequency_registry.get("entries"):
        try:
            spec = importlib.util.spec_from_file_location(
                "field_rf_sentinel", INSTALL / "lib" / "field-rf-sentinel.py",
            )
            if spec and spec.loader:
                _rf = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(_rf)
                frequency_registry = _rf._build_frequency_registry(rf.get("scan_material") or [])
        except Exception:
            frequency_registry = {}

    pulse_channels = _pulse_channels(rf, audio, fcc, frequency_registry, antenna_doc, home)
    pulse_channels.extend(_radio_pulse_channels(radio_doc))
    pulse_channels = pulse_channels[:max(len(pulse_channels), 32)]
    freq_knowledge = antenna_doc.get("frequency_knowledge") or {}
    readiness = antenna_doc.get("readiness") or {}

    out = {
        "schema": "signals-field/v1",
        "updated": _now(),
        "motto": "Field antennas alive — RF, audio, laser, BLE, wired, sub-µm pulses.",
        "tagline": "Every signal FCC-identified · threats tagged · field antennas pulsing",
        "fcc": fcc,
        "resolution": resolution,
        "antenna": {
            "mode": antenna.get("mode"),
            "tier": antenna.get("resolution_tier"),
            "score": antenna.get("resolution_score"),
            "scan_count": antenna.get("scan_count") or 0,
            "passive_reach_km": antenna.get("passive_reach_km_max") or 0,
            "fcc_safe": antenna.get("fcc_safe", True),
        },
        "antennas": antennas,
        "pulse_channels": pulse_channels,
        "frequency_registry": frequency_registry,
        "scan_dots": scan_dots,
        "material_field": {
            "sectors": (material.get("sectors") or [])[:16],
            "legend": material.get("legend") or {},
            "stats": material.get("stats") or {},
        } if material else {},
        "audio_train": {
            "sources": (audio.get("stats") or {}).get("sources", 0),
            "hostile": (audio.get("stats") or {}).get("hostile", 0),
            "hostess_version": audio.get("hostess_version"),
        },
        "home_protector": {
            "acre_ft": (home.get("acre") or {}).get("radius_ft", 55),
            "total": (home.get("stats") or {}).get("total", 0),
            "unauthorized": (home.get("stats") or {}).get("unauthorized", 0),
        },
        "field_antenna": {
            "blaster_ready": readiness.get("blaster_ready", False),
            "score": readiness.get("score"),
            "tier": readiness.get("tier"),
            "sub_micron_accuracy": readiness.get("sub_micron_accuracy", False),
            "modalities": freq_knowledge.get("modalities") or [],
            "frequency_coverage_pct": freq_knowledge.get("coverage_pct"),
            "checks": readiness.get("checks") or [],
        },
        "field_radio": {
            "crystal_clarity": radio_doc.get("crystal_clarity"),
            "field_boost": radio_doc.get("field_boost"),
            "station_menu": radio_doc.get("station_menu") or [],
            "fm_local": radio_doc.get("fm_local") or [],
            "illegal_frequencies": radio_doc.get("illegal_frequencies") or [],
            "spectrum": radio_doc.get("spectrum") or [],
            "stats": radio_doc.get("stats") or {},
            "operator": op,
            "tuned": radio_doc.get("tuned") or {},
            "fcc_master": radio_doc.get("fcc_master") or {},
        },
        "operator_profile": profile,
        "stats": {
            "antenna_fields": len(antennas),
            "active_antennas": sum(1 for a in antennas if a.get("scan_count")),
            "scan_dots": len(scan_dots),
            "pulse_channels": len(pulse_channels),
            "frequency_slots": frequency_registry.get("total_slots", 0) or freq_knowledge.get("total_slots", 0),
            "frequency_recognized": frequency_registry.get("recognized_slots", 0) or freq_knowledge.get("recognized_slots", 0),
            "frequency_coverage_pct": frequency_registry.get("coverage_pct", 0) or freq_knowledge.get("coverage_pct", 0),
            "fcc_identified": (fcc.get("stats") or {}).get("total", 0),
            "fcc_threats": (fcc.get("stats") or {}).get("threats", 0),
            "resolution_score": resolution.get("score"),
            "blaster_ready": readiness.get("blaster_ready", False),
        },
        "sdf_assets": ["antenna-bloom", "field-wave", "ring-pulse"],
    }
    try:
        spec = importlib.util.spec_from_file_location(
            "field_crosstalk", INSTALL / "lib" / "field-crosstalk.py",
        )
        if spec and spec.loader:
            _ct = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_ct)
            out["crosstalk"] = _ct.build_panel()
    except Exception:
        out["crosstalk"] = {}
    try:
        spec = importlib.util.spec_from_file_location(
            "field_wave_tuner", INSTALL / "lib" / "field-wave-tuner.py",
        )
        if spec and spec.loader:
            _wt = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_wt)
            out["field_wave_tuner"] = _wt.panel_json()
    except Exception:
        out["field_wave_tuner"] = {}
    try:
        spec = importlib.util.spec_from_file_location(
            "field_instability", INSTALL / "lib" / "field-instability.py",
        )
        if spec and spec.loader:
            _fi = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_fi)
            out["field_instability"] = _fi.panel_json()
    except Exception:
        out["field_instability"] = {}
    try:
        spec = importlib.util.spec_from_file_location(
            "field_wave_engine", INSTALL / "lib" / "field-wave-engine.py",
        )
        if spec and spec.loader:
            _we = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_we)
            _we.ensure_ported_backends(build_asm=False)
            out["field_wave_engine"] = _we.probe_hardware()
    except Exception:
        out["field_wave_engine"] = {}
    try:
        spec = importlib.util.spec_from_file_location(
            "field_signal_reader", INSTALL / "lib" / "field-signal-reader.py",
        )
        if spec and spec.loader:
            _sr = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_sr)
            out["field_signal_reader"] = _sr.panel_json()
    except Exception:
        out["field_signal_reader"] = {}
    try:
        spec = importlib.util.spec_from_file_location(
            "field_antenna_prototype", INSTALL / "lib" / "field-antenna-prototype.py",
        )
        if spec and spec.loader:
            _ap = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_ap)
            out["field_antenna_prototype"] = _ap.panel_json()
    except Exception:
        out["field_antenna_prototype"] = {}
    try:
        spec = importlib.util.spec_from_file_location(
            "field_generator", INSTALL / "lib" / "field-generator-triangulator.py",
        )
        if spec and spec.loader:
            _fg = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_fg)
            out["field_generator"] = _fg.panel_json()
    except Exception:
        out["field_generator"] = {}
    try:
        spec = importlib.util.spec_from_file_location(
            "field_world_placement", INSTALL / "lib" / "field-world-placement.py",
        )
        if spec and spec.loader:
            _wp = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_wp)
            out["field_world_placement"] = _wp.panel_json()
    except Exception:
        out["field_world_placement"] = {}

    try:
        spec = importlib.util.spec_from_file_location(
            "field_hardware_probe", INSTALL / "lib" / "field-hardware-probe.py",
        )
        if spec and spec.loader:
            _hw = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_hw)
            out["field_hardware"] = _hw.probe_all()
    except Exception:
        out["field_hardware"] = _load_json(STATE / "field-hardware-panel.json", {})
    for key, rel in (
        ("field_hazard_onset", "field-hazard-onset.py"),
        ("lethal_enforcement", "lethal-enforcement.py"),
        ("hostess7_lethal_insight", "hostess7-lethal-insight.py"),
    ):
        try:
            spec = importlib.util.spec_from_file_location(key, INSTALL / "lib" / rel)
            if spec and spec.loader:
                _m = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(_m)
                out[key] = _m.panel_status() if hasattr(_m, "panel_status") else {}
        except Exception:
            panel_name = key.replace("_", "-")
            out[key] = _load_json(STATE / f"{panel_name}-panel.json", {})

    out["field_antenna_catch"] = _load_json(STATE / "field-antenna-catch.json", {})
    out["secure_signal_line"] = _secure_signal_line()
    out["field_source"] = "signals-field"
    _save_json(PANEL_CACHE, out)
    return out


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("updated"):
        return cached
    return build_signals_field()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(build_signals_field(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_signals_field(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: signals-field.py [json|build]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())