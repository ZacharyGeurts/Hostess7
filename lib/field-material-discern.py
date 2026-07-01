#!/usr/bin/env pythong
"""Field material discernment — infer wall/path materials from RF direction, interference, fall-off.

Passive WiFi field only: multi-antenna signal deltas → bearing sectors, multipath interference,
path-loss fall-off exponents, and material classification (concrete gray, wood brown, etc.).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
CACHE = STATE / "field-material-discern.json"

SECTOR_COUNT = 8
SECTOR_WIDTH = 360.0 / SECTOR_COUNT

MATERIALS: dict[str, dict[str, Any]] = {
    "concrete": {"label": "Concrete", "color": "#8a8a8a", "attenuation": "high"},
    "metal": {"label": "Metal", "color": "#b8c0c8", "attenuation": "very_high"},
    "wood": {"label": "Wood", "color": "#8b5a2b", "attenuation": "medium"},
    "drywall": {"label": "Drywall", "color": "#c8b8a0", "attenuation": "medium_low"},
    "glass": {"label": "Glass", "color": "#6ec8e8", "attenuation": "low"},
    "brick": {"label": "Brick", "color": "#a04838", "attenuation": "high"},
    "water": {"label": "Moisture", "color": "#3a68a8", "attenuation": "selective"},
    "unknown": {"label": "Unknown", "color": "#5a6070", "attenuation": "unknown"},
}


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _std(vals: list[float]) -> float:
    if len(vals) < 2:
        return 0.0
    m = _mean(vals)
    return math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))


def _antenna_bearings(antenna_fields: list[dict[str, Any]]) -> dict[str, float]:
    """Assign pseudo-bearing per antenna (evenly spaced when orientation unknown)."""
    active = [f for f in antenna_fields if f.get("scanned")]
    if not active:
        return {}
    n = len(active)
    step = 360.0 / n
    return {str(f.get("device") or f"ant{i}"): i * step for i, f in enumerate(active)}


def _sector_index(bearing: float) -> int:
    return int((bearing % 360.0) // SECTOR_WIDTH) % SECTOR_COUNT


def _primary_bearing(ap: dict[str, Any], bearings: dict[str, float]) -> tuple[float, str | None]:
    sigs = ap.get("antenna_signals") or {}
    if not sigs:
        dev = ap.get("source_antenna")
        if dev and dev in bearings:
            return bearings[dev], dev
        return 0.0, None
    best_dev = max(sigs, key=lambda d: int(sigs.get(d) or 0))
    return bearings.get(best_dev, 0.0), best_dev


def _interference_index(ap: dict[str, Any]) -> float:
    sigs = [float(v) for v in (ap.get("antenna_signals") or {}).values() if v is not None]
    if len(sigs) < 2:
        return 0.15
    spread = max(sigs) - min(sigs)
    rel = spread / max(max(sigs), 1.0)
    multi = min(1.0, int(ap.get("antenna_count") or 1) / 3.0)
    sightings = min(1.0, int(ap.get("sightings") or 1) / 4.0)
    return _clamp(0.35 * rel + 0.35 * multi + 0.3 * sightings)


def _falloff_db(ap: dict[str, Any], sector_signals: list[int]) -> float:
    """Estimate path-loss steepness from relative signal rank in sector."""
    sig = int(ap.get("signal_dbm") or 0)
    if not sector_signals:
        return 20.0
    ranked = sorted(sector_signals, reverse=True)
    if sig <= 0:
        return 32.0
    try:
        rank = ranked.index(sig)
    except ValueError:
        rank = len(ranked) // 2
    frac = rank / max(len(ranked) - 1, 1)
    return 18.0 + frac * 22.0


def _band_ratio(ap: dict[str, Any], scan: list[dict[str, Any]]) -> float:
    band = str(ap.get("band") or "")
    ssid = ap.get("ssid")
    if not ssid or ssid == "(hidden)":
        return 0.5
    peers = [a for a in scan if a.get("ssid") == ssid and a.get("band")]
    sig_24 = [int(a.get("signal_dbm") or 0) for a in peers if "2.4" in str(a.get("band"))]
    sig_5 = [int(a.get("signal_dbm") or 0) for a in peers if "5" in str(a.get("band"))]
    if not sig_24 or not sig_5:
        if "5" in band:
            return 0.65
        if "2.4" in band:
            return 0.35
        return 0.5
    return _clamp(_mean(sig_5) / max(_mean(sig_24), 1.0))


def _classify_material(
    interference: float,
    falloff_db: float,
    band_ratio: float,
    mean_signal: float,
) -> tuple[str, float]:
    scores = {k: 0.0 for k in MATERIALS}
    scores["concrete"] += (falloff_db - 24.0) * 0.04 + interference * 0.35
    scores["metal"] += interference * 0.55 + (0.4 if mean_signal > 75 else 0.0)
    scores["wood"] += max(0.0, 1.0 - interference) * 0.35 + max(0.0, 28.0 - falloff_db) * 0.03
    scores["drywall"] += max(0.0, 26.0 - falloff_db) * 0.04 + max(0.0, 0.45 - interference) * 0.25
    scores["glass"] += band_ratio * 0.55 + max(0.0, 22.0 - falloff_db) * 0.02
    scores["brick"] += (falloff_db - 26.0) * 0.03 + interference * 0.2
    scores["water"] += max(0.0, 0.42 - band_ratio) * 0.6
    best = max(scores, key=scores.get)
    raw = scores[best]
    total = sum(scores.values()) or 1.0
    conf = _clamp(raw / total + 0.15)
    if conf < 0.28:
        return "unknown", conf
    return best, conf


def _sector_stats(
    scan: list[dict[str, Any]],
    antenna_fields: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    bearings = _antenna_bearings(antenna_fields)
    buckets: dict[int, list[dict[str, Any]]] = {i: [] for i in range(SECTOR_COUNT)}

    for ap in scan:
        bearing, _ = _primary_bearing(ap, bearings)
        buckets[_sector_index(bearing)].append({**ap, "_bearing": bearing})

    sectors: list[dict[str, Any]] = []
    for idx in range(SECTOR_COUNT):
        aps = buckets[idx]
        bearing_center = idx * SECTOR_WIDTH + SECTOR_WIDTH / 2.0
        if not aps:
            sectors.append({
                "sector": idx,
                "bearing_deg": round(bearing_center, 1),
                "width_deg": round(SECTOR_WIDTH, 1),
                "material": "unknown",
                "color": MATERIALS["unknown"]["color"],
                "label": MATERIALS["unknown"]["label"],
                "confidence": 0.0,
                "interference": 0.0,
                "falloff_db": None,
                "source_count": 0,
                "mean_signal": 0,
                "band_ratio": 0.5,
            })
            continue

        signals = [int(a.get("signal_dbm") or 0) for a in aps]
        interferences = [_interference_index(a) for a in aps]
        falloffs = [_falloff_db(a, signals) for a in aps]
        band_ratios = [_band_ratio(a, scan) for a in aps]
        mean_sig = _mean([float(s) for s in signals])
        mean_int = _mean(interferences)
        mean_fall = _mean(falloffs)
        mean_br = _mean(band_ratios)
        material, conf = _classify_material(mean_int, mean_fall, mean_br, mean_sig)
        meta = MATERIALS[material]
        antennas = sorted({
            d for a in aps for d in (a.get("antenna_sources") or [a.get("source_antenna")] or [])
            if d
        })
        sectors.append({
            "sector": idx,
            "bearing_deg": round(bearing_center, 1),
            "width_deg": round(SECTOR_WIDTH, 1),
            "material": material,
            "color": meta["color"],
            "label": meta["label"],
            "confidence": round(conf, 3),
            "interference": round(mean_int, 3),
            "falloff_db": round(mean_fall, 1),
            "source_count": len(aps),
            "mean_signal": round(mean_sig, 1),
            "band_ratio": round(mean_br, 3),
            "dominant_antennas": antennas[:4],
            "top_sources": [
                {
                    "ssid": a.get("ssid"),
                    "bssid": a.get("bssid"),
                    "signal_dbm": a.get("signal_dbm"),
                    "band": a.get("band"),
                    "bearing_deg": round(float(a.get("_bearing") or bearing_center), 1),
                }
                for a in sorted(aps, key=lambda x: int(x.get("signal_dbm") or 0), reverse=True)[:4]
            ],
        })
    return sectors


def _annotate_scan(scan: list[dict[str, Any]], sectors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sector_by_idx = {s["sector"]: s for s in sectors}
    out: list[dict[str, Any]] = []
    bearings = {}
    for s in sectors:
        for src in s.get("top_sources") or []:
            b = src.get("bssid")
            if b:
                bearings[b] = s
    for ap in scan:
        row = dict(ap)
        bssid = ap.get("bssid")
        sec = None
        if bssid and bssid in bearings:
            sec = bearings[bssid]
        else:
            sig = int(ap.get("signal_dbm") or 0)
            for s in sectors:
                for src in s.get("top_sources") or []:
                    if src.get("signal_dbm") == sig:
                        sec = s
                        break
        if sec:
            row["path_material"] = sec.get("material")
            row["path_color"] = sec.get("color")
            row["path_bearing_deg"] = sec.get("bearing_deg")
            row["path_interference"] = _interference_index(ap)
        out.append(row)
    return out


def build_material_field(
    scan: list[dict[str, Any]] | None = None,
    antenna_fields: list[dict[str, Any]] | None = None,
    *,
    persist: bool = True,
) -> dict[str, Any]:
    scan = scan or []
    antenna_fields = antenna_fields or []
    sectors = _sector_stats(scan, antenna_fields)
    known = [s for s in sectors if s.get("source_count", 0) > 0 and s.get("material") != "unknown"]
    dominant = max(known, key=lambda s: s["confidence"] * s["source_count"], default=None) if known else None
    doc = {
        "schema": "field-material-discern/v1",
        "motto": "Discern field directions, interference, and fall-offs — color materials from passive RF.",
        "tagline": "Multi-antenna bearing · multipath interference · path-loss fall-off → concrete, wood, metal, glass.",
        "sector_count": SECTOR_COUNT,
        "sectors": sectors,
        "legend": {k: {"label": v["label"], "color": v["color"]} for k, v in MATERIALS.items()},
        "stats": {
            "active_sectors": sum(1 for s in sectors if s.get("source_count", 0) > 0),
            "classified_sectors": len(known),
            "scan_sources": len(scan),
            "antenna_fields": len(antenna_fields),
            "dominant_material": dominant.get("material") if dominant else "unknown",
            "dominant_bearing_deg": dominant.get("bearing_deg") if dominant else None,
            "mean_interference": round(_mean([s["interference"] for s in sectors if s.get("source_count")]), 3),
            "mean_falloff_db": round(
                _mean([s["falloff_db"] for s in sectors if s.get("falloff_db") is not None]) or 0.0, 1
            ),
        },
        "annotated_scan_count": len(scan),
    }
    if persist:
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def annotate_scan(scan: list[dict[str, Any]], material_doc: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    material_doc = material_doc or build_material_field(scan, persist=False)
    return _annotate_scan(scan, material_doc.get("sectors") or [])


def panel_json(
    scan: list[dict[str, Any]] | None = None,
    antenna_fields: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if scan is not None:
        return build_material_field(scan, antenna_fields or [], persist=True)
    if CACHE.is_file():
        try:
            return json.loads(CACHE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return build_material_field([], [], persist=False)


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-material-discern.py [json]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())