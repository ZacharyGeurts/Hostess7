#!/usr/bin/env pythong
"""Field instability & frequency detection — 3-field physics before hardware tune."""
from __future__ import annotations

import json
import math
import os
import importlib.util
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_CACHE = STATE / "field-instability-panel.json"
HISTORY = STATE / "field-instability-history.jsonl"
RF_PANEL = STATE / "field-rf-panel.json"
ANTENNA_PANEL = STATE / "field-antenna-panel.json"

C_MPS = 299_792_458.0
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


def _wavelength_m(freq_mhz: float) -> float:
    return C_MPS / (freq_mhz * 1_000_000.0)


def _fspl_db(distance_km: float, freq_mhz: float) -> float:
    d = max(distance_km, 0.001)
    f = max(freq_mhz, 0.1)
    return 32.44 + 20.0 * math.log10(d) + 20.0 * math.log10(f)


def _engine() -> Any:
    spec = importlib.util.spec_from_file_location("field_wave_engine", INSTALL / "lib" / "field-wave-engine.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _probe_rtl_dongle() -> dict[str, Any]:
    eng = _engine()
    eng.ensure_ported_backends(build_asm=False)
    hw = eng.probe_hardware()
    return {
        "field_wave_fm": bool(hw.get("field_wave_fm")),
        "field_wave_play": bool(hw.get("field_wave_play")),
        "field_wave_wav": bool(hw.get("field_wave_wav")),
        "field_wave_asm": bool((eng.probe_asm() or {}).get("probe_path") == "asm"),
        "dongle_present": bool(hw.get("dongle_present")),
        "usb_id": hw.get("usb_id", ""),
        "probe_path": hw.get("probe_path", ""),
        "ppm_correction": int(hw.get("ppm_correction") or 0),
        "listen_ready": bool(hw.get("listen_ready")),
        "engine": "field-wave-engine",
        "ensure_hint": hw.get("ensure_hint", "pythong lib/field-wave-engine.py ensure"),
    }


def _history_drift(freq_mhz: float, limit: int = 12) -> float:
    if not HISTORY.is_file():
        return 0.0
    strengths: list[float] = []
    try:
        lines = HISTORY.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        for line in lines:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if abs(float(row.get("freq_mhz") or 0) - freq_mhz) > 0.2:
                continue
            if row.get("avg_field_strength") is not None:
                strengths.append(float(row["avg_field_strength"]))
    except OSError:
        return 0.0
    if len(strengths) < 2:
        return 0.0
    return statistics.pstdev(strengths)


def analyze_fields(
    *,
    tri_compare: dict[str, Any] | None = None,
    freq_mhz: float | None = None,
    target_distance_km: float | None = None,
) -> dict[str, Any]:
    """Detect field instability and lock broadcast frequency from 3-field physics."""
    mhz = float(freq_mhz if freq_mhz is not None else DEFAULT_MHZ)
    tri = tri_compare or {}
    fields = list(tri.get("fields") or [])
    strengths = [float(f.get("signal_strength_pct") or 0) for f in fields]
    bearings = [float(f.get("bearing_to_target_deg") or 0) for f in fields if f.get("bearing_to_target_deg") is not None]

    strength_var = statistics.pvariance(strengths) if len(strengths) >= 2 else 0.0
    strength_spread = (max(strengths) - min(strengths)) if strengths else 0.0
    brg_spread = float(tri.get("bearing_spread_deg") or 0)
    if bearings and not brg_spread:
        brg_spread = max(bearings) - min(bearings)
        if brg_spread > 180:
            brg_spread = 360.0 - brg_spread

    hist_drift = _history_drift(mhz)
    instability_index = min(1.0, max(0.0,
        (strength_var / 400.0) * 0.3
        + (strength_spread / 100.0) * 0.25
        + (brg_spread / 120.0) * 0.25
        + (hist_drift / 25.0) * 0.2,
    ))
    stable = instability_index < 0.45 and float(tri.get("tri_confidence") or 0) >= 0.25

    dist_km = target_distance_km
    if dist_km is None and fields:
        dists = [float(f.get("distance_to_target_km") or 0) for f in fields if f.get("distance_to_target_km")]
        dist_km = statistics.mean(dists) if dists else 50.0
    dist_km = float(dist_km or 50.0)

    hw = _probe_rtl_dongle()
    wavelength_m = _wavelength_m(mhz)
    path_loss_db = _fspl_db(dist_km, mhz)
    center_hz = int(round(mhz * 1_000_000))
    corrected_hz = int(round(center_hz * (1.0 + hw["ppm_correction"] / 1_000_000.0)))

    rf = _load_json(RF_PANEL, {})
    registry = rf.get("frequency_registry") or {}
    wifi_instability = 0.0
    reg_entries = list(registry.get("entries") or [])
    if reg_entries:
        active = [int(e.get("strength") or 0) for e in reg_entries if e.get("recognized")]
        if len(active) >= 2:
            wifi_instability = min(1.0, statistics.pvariance(active) / 2500.0)

    ant = _load_json(ANTENNA_PANEL, {})
    readiness = float((ant.get("readiness") or {}).get("score") or 0)

    if instability_index < 0.35:
        instability_class = "stable"
    elif instability_index < 0.65:
        instability_class = "moderate"
    else:
        instability_class = "unstable"

    blockers: list[str] = []
    if not hw.get("field_wave_play"):
        blockers.append("field-wave-play not ready — pythong lib/field-wave-engine.py ensure")
    if not stable:
        blockers.append("3-field instability high — warming tri lock")

    doc = {
        "schema": "field-instability/v1",
        "updated": _now(),
        "freq_mhz": mhz,
        "freq_mhz_corrected": round(corrected_hz / 1_000_000.0, 4),
        "freq_hz": center_hz,
        "freq_hz_corrected": corrected_hz,
        "ppm_correction": hw["ppm_correction"],
        "wavelength_m": round(wavelength_m, 4),
        "wavelength_cm": round(wavelength_m * 100.0, 2),
        "path_loss_db": round(path_loss_db, 2),
        "distance_km": round(dist_km, 2),
        "instability_index": round(instability_index, 3),
        "instability_class": instability_class,
        "wifi_field_instability": round(wifi_instability, 3),
        "stable_enough": stable,
        "tri_confidence": tri.get("tri_confidence"),
        "bearing_spread_deg": round(brg_spread, 1),
        "field_strength_variance": round(strength_var, 2),
        "field_strength_spread": round(strength_spread, 1),
        "history_drift": round(hist_drift, 2),
        "fields": fields,
        "physics": {
            "demod": "WBFM",
            "sample_rate_hz": 200_000,
            "deemphasis": True,
            "center_hz": center_hz,
            "ppm": hw["ppm_correction"],
            "corrected_hz": corrected_hz,
            "wavelength_m": round(wavelength_m, 4),
            "fspl_db": round(path_loss_db, 2),
            "antenna_readiness": readiness,
        },
        "hardware": hw,
        "listen_ready": stable or bool(fields),
        "listen_anyway": True,
        "ota_listen": True,
        "we_are_the_antenna": True,
        "no_dongle_required": True,
        "listen_blockers": blockers,
    }
    return doc


def record_sample(analysis: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    fields = analysis.get("fields") or []
    strengths = [float(f.get("signal_strength_pct") or 0) for f in fields]
    row = {
        "ts": _now(),
        "freq_mhz": analysis.get("freq_mhz"),
        "instability_index": analysis.get("instability_index"),
        "avg_field_strength": statistics.mean(strengths) if strengths else 0,
        "stable_enough": analysis.get("stable_enough"),
    }
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_panel(*, tri_compare: dict[str, Any] | None = None, freq_mhz: float | None = None) -> dict[str, Any]:
    doc = analyze_fields(tri_compare=tri_compare, freq_mhz=freq_mhz)
    record_sample(doc)
    _save_json(PANEL_CACHE, doc)
    return doc


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("schema") == "field-instability/v1" and cached.get("updated"):
        return cached
    return build_panel()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        tri = None
        if len(sys.argv) > 2:
            try:
                tri = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                pass
        print(json.dumps(build_panel(tri_compare=tri), ensure_ascii=False))
        return 0
    if cmd == "probe":
        print(json.dumps(_probe_rtl_dongle(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-instability.py [json|build|probe]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())