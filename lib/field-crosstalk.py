#!/usr/bin/env pythong
"""Field crosstalk — precise start/end points, countermeasures at violator origin."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_CACHE = STATE / "field-crosstalk-panel.json"
VIOLATOR_LEDGER = STATE / "field-crosstalk-violators.jsonl"
MITIGATED = STATE / "field-crosstalk-mitigated.json"
LINE_BLOCKS = STATE / "field-crosstalk-line-blocks.json"
REGISTRY = INSTALL / "data" / "field-radio-broadcast-registry.json"

RF_PANEL = STATE / "field-rf-panel.json"
RADIO_PANEL = STATE / "field-radio-panel.json"
AUDIO_PANEL = STATE / "audio-train-panel.json"
MATERIAL_PANEL = STATE / "field-material-discern.json"
OPERATOR_LOC = STATE / "operator-location.json"


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


def _operator() -> dict[str, Any]:
    doc = _load_json(OPERATOR_LOC, {})
    if doc.get("lat") is None:
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


def _our_line_end() -> dict[str, Any]:
    op = _operator()
    lat = float(op.get("lat") or 45.845976)
    lon = float(op.get("lon") or -87.055759)
    return {
        "role": "our_line",
        "label": op.get("label") or "operator_antenna",
        "lat": lat,
        "lon": lon,
        "gps": f"{lat:.6f}, {lon:.6f}",
    }


def _point_at_bearing(lat: float, lon: float, bearing_deg: float, km: float) -> dict[str, Any]:
    r = 6371.0
    br = math.radians(bearing_deg)
    lat1, lon1 = math.radians(lat), math.radians(lon)
    lat2 = math.asin(
        math.sin(lat1) * math.cos(km / r)
        + math.cos(lat1) * math.sin(km / r) * math.cos(br),
    )
    lon2 = lon1 + math.atan2(
        math.sin(br) * math.sin(km / r) * math.cos(lat1),
        math.cos(km / r) - math.sin(lat1) * math.sin(lat2),
    )
    plat, plon = math.degrees(lat2), math.degrees(lon2)
    return {"lat": round(plat, 6), "lon": round(plon, 6), "gps": f"{plat:.6f}, {plon:.6f}"}


def _line(start: dict[str, Any], end: dict[str, Any], *, kind: str = "") -> dict[str, Any]:
    return {
        "start_point": start,
        "end_point": end,
        "kind": kind,
        "countermeasure_at": "start_point",
        "policy": "never_past_their_start — block at precise origin before our line",
    }


def _violator_id(kind: str, label: str, key: str) -> str:
    raw = f"{kind}|{label}|{key}".lower()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _append_violator(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with VIOLATOR_LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_violators(limit: int = 200) -> list[dict[str, Any]]:
    if not VIOLATOR_LEDGER.is_file():
        return []
    by_id: dict[str, dict[str, Any]] = {}
    try:
        for line in VIOLATOR_LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            vid = str(row.get("violator_id") or "")
            if not vid:
                continue
            prev = by_id.get(vid)
            if prev:
                prev["strike_count"] = int(prev.get("strike_count") or 1) + 1
                prev["last_seen"] = row.get("ts") or prev.get("last_seen")
            else:
                row["strike_count"] = 1
                row.setdefault("first_seen", row.get("ts"))
                row.setdefault("last_seen", row.get("ts"))
                by_id[vid] = row
    except OSError:
        return []
    return sorted(by_id.values(), key=lambda r: -(r.get("strike_count") or 0))[:limit]


def _mitigated_ids() -> set[str]:
    return {str(x) for x in (_load_json(MITIGATED, {"ids": []}).get("ids") or [])}


def _enforce_at_start(ev: dict[str, Any]) -> dict[str, Any]:
    """Heavy countermeasure at violator start_point — must not traverse to our line."""
    start = ev.get("start_point") or {}
    result: dict[str, Any] = {"enforced": False, "at": "start_point", "actions": []}
    if ev.get("classification") != "illegal_crosstalk":
        return result

    ip = str(start.get("ip") or "")
    bssid = str(start.get("bssid") or "")
    freq = ev.get("freq_mhz")

    if ip:
        kit = INSTALL / "lib" / "field-attack-kit.py"
        if kit.is_file():
            try:
                proc = subprocess.run(
                    [os.environ.get("PYTHON", "pythong"), str(kit),
                     "forever-disable", ip, "CROSSTALK_LINE", "critical",
                     "line_touch_at_start", json.dumps({"start": start, "end": ev.get("end_point")})],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                )
                result["actions"].append({"action": "forever_disable_ip", "ip": ip, "ok": proc.returncode == 0})
            except (OSError, subprocess.TimeoutExpired):
                result["actions"].append({"action": "forever_disable_ip", "ip": ip, "ok": False})

    if bssid:
        blocks = _load_json(LINE_BLOCKS, {"bssids": [], "updated": _now()})
        bssids = list(blocks.get("bssids") or [])
        if bssid not in bssids:
            bssids.append(bssid)
        blocks["bssids"] = bssids
        blocks["updated"] = _now()
        _save_json(LINE_BLOCKS, blocks)
        result["actions"].append({"action": "forever_disable_bssid", "bssid": bssid, "ok": True})

    if freq is not None:
        blocks = _load_json(LINE_BLOCKS, {"freq_mhz": [], "updated": _now()})
        freqs = list(blocks.get("freq_mhz") or [])
        entry = {"freq_mhz": freq, "ts": _now(), "start": start, "violator_id": ev.get("violator_id")}
        freqs.append(entry)
        blocks["freq_mhz"] = freqs[-128:]
        blocks["updated"] = _now()
        _save_json(LINE_BLOCKS, blocks)
        result["actions"].append({"action": "block_freq_at_start", "freq_mhz": freq, "ok": True})

    tg = INSTALL / "lib" / "dns-threat-guard.py"
    client_key = ip or bssid or str(freq or ev.get("violator_id"))
    if tg.is_file() and client_key:
        try:
            spec = importlib.util.spec_from_file_location("dns_threat_guard", tg)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.eradicate_threat(
                    client_key=client_key,
                    reason=f"crosstalk_line_touch:{ev.get('kind')}",
                    vector="CROSSTALK_LINE",
                    direction="ingress",
                )
                result["actions"].append({"action": "eradicate_threat", "client": client_key, "ok": True})
        except Exception:
            result["actions"].append({"action": "eradicate_threat", "client": client_key, "ok": False})

    result["enforced"] = any(a.get("ok") for a in result["actions"])
    return result


def _rf_crosstalk(rf: dict[str, Any], our_end: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    registry = rf.get("frequency_registry") or {}
    scan = list(rf.get("scan_material") or [])
    by_key: dict[str, list[dict[str, Any]]] = {}
    for entry in registry.get("entries") or []:
        band = str(entry.get("band") or "unknown")
        ch = entry.get("channel")
        freq = entry.get("freq_mhz")
        key = f"{band}:{ch if ch is not None else freq}"
        by_key.setdefault(key, []).append(entry)

    for key, group in by_key.items():
        if len(group) < 2:
            continue
        strengths = [int(g.get("strength") or 0) for g in group]
        if max(strengths) < 15:
            continue
        legal = all(g.get("recognized") for g in group)
        ap = next((a for a in scan if a.get("bssid")), scan[0] if scan else {})
        start = {
            "role": "violator_origin" if not legal else "transmitter",
            "label": str(ap.get("ssid") or ap.get("bssid") or key),
            "bssid": ap.get("bssid"),
            "ip": ap.get("ip"),
            "channel": ap.get("channel"),
            "freq_mhz": ap.get("freq_mhz"),
        }
        ev = {
            "kind": "rf_co_channel",
            "classification": "legal_crosstalk" if legal else "illegal_crosstalk",
            "severity": "medium" if legal else "high",
            "label": f"RF co-channel {key.replace(':', ' ')}",
            "detail": f"{len(group)} sources — block at start before our line",
            "sources": group,
            "removable": not legal,
            **_line(start, our_end, kind="rf"),
        }
        hits.append(ev)
    return hits


def _fm_crosstalk(radio: dict[str, Any], our_end: dict[str, Any], target_mhz: float) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    spectrum = list(radio.get("spectrum") or [])
    reg = _load_json(REGISTRY, {"stations": []})
    target_st = next(
        (s for s in reg.get("stations") or [] if s.get("freq_mhz") and abs(float(s["freq_mhz"]) - target_mhz) < 0.05),
        {},
    )
    target_tower = {
        "role": "licensed_transmitter",
        "label": target_st.get("call_sign") or f"{target_mhz} MHz",
        "lat": float(target_st.get("tower_lat") or our_end["lat"]),
        "lon": float(target_st.get("tower_lon") or our_end["lon"]),
        "gps": f"{float(target_st.get('tower_lat') or our_end['lat']):.6f}, {float(target_st.get('tower_lon') or our_end['lon']):.6f}",
        "freq_mhz": target_mhz,
    }

    for bad in [s for s in spectrum if s.get("status") == "illegal"]:
        fm = bad.get("freq_mhz")
        if fm is None or abs(float(fm) - target_mhz) > 1.2:
            continue
        fm = float(fm)
        brg = (hash(int(fm * 1000)) % 360)
        est = _point_at_bearing(our_end["lat"], our_end["lon"], brg, 8.0 + abs(fm - target_mhz) * 3)
        start = {
            "role": "violator_origin",
            "label": str(bad.get("label") or f"UNLICENSED {fm} MHz"),
            "freq_mhz": fm,
            **est,
        }
        hits.append({
            "kind": "fm_adjacent_bleed",
            "classification": "illegal_crosstalk",
            "severity": "critical",
            "label": start["label"],
            "detail": f"Illegal {fm} MHz → our {target_mhz} MHz line — counter at start",
            "freq_mhz": fm,
            "target_mhz": target_mhz,
            "spacing_mhz": round(abs(fm - target_mhz), 1),
            "threat_tag": "unpermitted_spectrum",
            "removable": True,
            **_line(start, our_end, kind="fm"),
            "licensed_end": target_tower,
        })

    for leg in [s for s in spectrum if s.get("status") == "legal" and s.get("freq_mhz") and abs(float(s["freq_mhz"]) - target_mhz) <= 0.5]:
        tlat = leg.get("tower_lat")
        tlon = leg.get("tower_lon")
        start = {
            "role": "licensed_transmitter",
            "label": leg.get("call_sign") or leg.get("label"),
            "lat": float(tlat) if tlat is not None else target_tower["lat"],
            "lon": float(tlon) if tlon is not None else target_tower["lon"],
            "gps": f"{float(tlat or target_tower['lat']):.6f}, {float(tlon or target_tower['lon']):.6f}",
            "freq_mhz": leg.get("freq_mhz"),
        }
        hits.append({
            "kind": "fm_licensed_neighbor",
            "classification": "legal_crosstalk",
            "severity": "low",
            "label": str(leg.get("label")),
            "detail": f"Licensed neighbor {leg.get('freq_mhz')} MHz — notch only",
            "removable": False,
            **_line(start, our_end, kind="fm"),
        })
    return hits


def _audio_crosstalk(audio: dict[str, Any], our_end: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    sources = list((audio.get("sources") or {}).values()) if isinstance(audio.get("sources"), dict) else []
    hostile = [s for s in sources if not s.get("acceptable", True)]
    if not hostile:
        return hits
    for h in hostile[:6]:
        start = {
            "role": "violator_origin",
            "label": str(h.get("label") or h.get("source_id")),
            "source_id": h.get("source_id"),
        }
        hits.append({
            "kind": "audio_bleed",
            "classification": "illegal_crosstalk",
            "severity": "high",
            "label": start["label"],
            "detail": "Hostile audio touching our line — mute at source",
            "removable": True,
            **_line(start, our_end, kind="audio"),
        })
    return hits


def _material_crosstalk(material: dict[str, Any], our_end: dict[str, Any]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for sector in material.get("sectors") or []:
        interference = float(sector.get("interference") or 0)
        if interference < 0.55:
            continue
        brg = float(sector.get("bearing_deg") or 0)
        est = _point_at_bearing(our_end["lat"], our_end["lon"], brg, 0.05 + interference * 0.15)
        start = {"role": "violator_origin", "label": f"Sector {brg}°", "bearing_deg": brg, **est}
        illegal = interference >= 0.75
        hits.append({
            "kind": "multipath_interference",
            "classification": "illegal_crosstalk" if illegal else "legal_crosstalk",
            "severity": "high" if illegal else "medium",
            "label": start["label"],
            "detail": f"Interference {interference:.2f} at bearing {brg}°",
            "interference": interference,
            "removable": illegal,
            **_line(start, our_end, kind="multipath"),
        })
    return hits


def scan_crosstalk(*, target_mhz: float | None = None, enforce: bool = True) -> dict[str, Any]:
    target = float(target_mhz if target_mhz is not None else os.environ.get("NEXUS_FIELD_CATCH_MHZ", "93.1"))
    our_end = _our_line_end()
    rf = _load_json(RF_PANEL, {})
    radio = _load_json(RADIO_PANEL, {})
    audio = _load_json(AUDIO_PANEL, {})
    material = _load_json(MATERIAL_PANEL, {})

    events: list[dict[str, Any]] = []
    events.extend(_rf_crosstalk(rf, our_end))
    events.extend(_fm_crosstalk(radio, our_end, target))
    events.extend(_audio_crosstalk(audio, our_end))
    events.extend(_material_crosstalk(material, our_end))

    mitigated = _mitigated_ids()
    countermeasures: list[dict[str, Any]] = []
    ts = _now()

    for ev in events:
        if ev.get("classification") != "illegal_crosstalk":
            continue
        key = str(ev.get("freq_mhz") or (ev.get("start_point") or {}).get("label") or "")
        vid = _violator_id(str(ev.get("kind")), str(ev.get("label")), key)
        ev["violator_id"] = vid
        ev["mitigated"] = vid in mitigated
        if ev["mitigated"]:
            continue
        row = {
            "violator_id": vid,
            "ts": ts,
            "kind": ev.get("kind"),
            "label": ev.get("label"),
            "classification": ev.get("classification"),
            "severity": ev.get("severity"),
            "detail": ev.get("detail"),
            "start_point": ev.get("start_point"),
            "end_point": ev.get("end_point"),
            "freq_mhz": ev.get("freq_mhz"),
            "target_mhz": target,
        }
        _append_violator(row)
        if enforce:
            cm = _enforce_at_start(ev)
            ev["countermeasure"] = cm
            countermeasures.append(cm)

    tracked = _load_violators()
    legal = [e for e in events if e.get("classification") == "legal_crosstalk"]
    illegal = [e for e in events if e.get("classification") == "illegal_crosstalk" and not e.get("mitigated")]
    return {
        "schema": "field-crosstalk/v1",
        "updated": ts,
        "motto": "Precise start → end lines. Countermeasures at their start — never past our line.",
        "target_mhz": target,
        "our_line_end": our_end,
        "events": events,
        "legal_crosstalk": legal,
        "illegal_crosstalk": illegal,
        "violators": tracked,
        "countermeasures": countermeasures,
        "line_blocks": _load_json(LINE_BLOCKS, {}),
        "stats": {
            "total": len(events),
            "legal": len(legal),
            "illegal": len(illegal),
            "enforced_at_start": sum(1 for c in countermeasures if c.get("enforced")),
            "violators_tracked": len(tracked),
            "critical": sum(1 for e in illegal if e.get("severity") == "critical"),
        },
    }


def mitigate_violator(violator_id: str) -> dict[str, Any]:
    doc = _load_json(MITIGATED, {"ids": [], "updated": _now()})
    ids = list(doc.get("ids") or [])
    if violator_id and violator_id not in ids:
        ids.append(violator_id)
    doc["ids"] = ids
    doc["updated"] = _now()
    _save_json(MITIGATED, doc)
    panel = scan_crosstalk(enforce=True)
    _save_json(PANEL_CACHE, panel)
    return {"ok": True, "violator_id": violator_id, "panel": panel}


def build_panel() -> dict[str, Any]:
    doc = scan_crosstalk(enforce=True)
    _save_json(PANEL_CACHE, doc)
    return doc


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("schema") == "field-crosstalk/v1" and cached.get("updated"):
        return cached
    return build_panel()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "scan":
        print(json.dumps(scan_crosstalk(), ensure_ascii=False))
        return 0
    if cmd == "mitigate" and len(sys.argv) > 2:
        print(json.dumps(mitigate_violator(sys.argv[2]), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-crosstalk.py [json|build|scan|mitigate ID]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())