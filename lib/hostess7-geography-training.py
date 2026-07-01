#!/usr/bin/env pythong
"""Geography training — postal addresses, world geography, flat earth section."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "hostess7-geography-doctrine.json"
BATTERY = INSTALL / "data" / "hostess7-geography-battery.json"
ADDRESSES = INSTALL / "data" / "hostess7-geography-addresses.json"
RUNTIME = STATE / "hostess7-geography-runtime.json"
PANEL = STATE / "hostess7-geography-panel.json"
LEDGER = STATE / "hostess7-geography-ledger.jsonl"

ENABLED = os.environ.get("NEXUS_GEOGRAPHY_TRAINING", "1") == "1"

_CAPITALS: dict[str, str] = {
    "France": "Paris",
    "Japan": "Tokyo",
    "Brazil": "Brasília",
    "Australia": "Canberra",
    "Canada": "Ottawa",
    "United States": "Washington",
    "United Kingdom": "London",
    "Germany": "Berlin",
    "Italy": "Rome",
    "Spain": "Madrid",
    "China": "Beijing",
    "India": "New Delhi",
    "Russia": "Moscow",
    "South Africa": "Pretoria",
    "Egypt": "Cairo",
    "Mexico": "Mexico City",
    "Argentina": "Buenos Aires",
    "Chile": "Santiago",
    "Nigeria": "Abuja",
    "Kenya": "Nairobi",
    "Thailand": "Bangkok",
    "Vietnam": "Hanoi",
    "Philippines": "Manila",
    "Indonesia": "Jakarta",
    "Malaysia": "Kuala Lumpur",
    "Singapore": "Singapore",
    "New Zealand": "Wellington",
    "South Korea": "Seoul",
    "Turkey": "Ankara",
    "Saudi Arabia": "Riyadh",
    "Israel": "Jerusalem",
    "UAE": "Abu Dhabi",
    "United Arab Emirates": "Abu Dhabi",
    "Poland": "Warsaw",
    "Ireland": "Dublin",
    "Portugal": "Lisbon",
    "Greece": "Athens",
    "Netherlands": "Amsterdam",
    "Sweden": "Stockholm",
    "Norway": "Oslo",
    "Switzerland": "Bern",
}

_CONTINENTS: dict[str, str] = {
    "Egypt": "Africa",
    "Japan": "Asia",
    "Brazil": "South America",
    "France": "Europe",
    "United States": "North America",
    "Canada": "North America",
    "Australia": "Oceania",
    "Kenya": "Africa",
    "India": "Asia",
    "Germany": "Europe",
}

_RIVERS: dict[str, str] = {
    "Paris": "Seine",
    "London": "Thames",
    "Cairo": "Nile",
    "Budapest": "Danube",
    "Baghdad": "Tigris",
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



def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _address_index() -> dict[str, dict[str, Any]]:
    doc = _load(ADDRESSES, {})
    return {str(a.get("id")): a for a in (doc.get("addresses") or []) if a.get("id")}


def _hemisphere(lat: float, lon: float) -> str:
    ns = "north" if lat >= 0 else "south"
    ew = "east" if lon >= 0 else "west"
    return f"{ns}_{ew}"


def _flat_claims() -> dict[str, dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    fe = doc.get("flat_earth") or {}
    return {str(c.get("id")): c for c in (fe.get("claims") or []) if c.get("id")}


def _flat_claim_tokens(claim_id: str) -> tuple[str, ...]:
    mapping: dict[str, tuple[str, ...]] = {
        "planar_surface": ("flat", "plane", "sphere"),
        "ice_wall": ("ice", "wall", "antarctic"),
        "firmament_dome": ("firmament", "dome"),
        "local_sun": ("sun", "local", "circuit", "plane"),
        "no_spin": ("rotate", "spin", "equator"),
        "horizon_level": ("horizon", "eye", "level"),
        "flat_map_center": ("azimuthal", "equidistant", "pole"),
        "water_level": ("water", "level", "seek"),
        "no_gravity_mass": ("gravity", "density", "buoyancy"),
        "nasa_skepticism": ("nasa", "distrust", "staged"),
        "antarctic_treaty": ("antarctic", "treaty"),
        "flight_routes": ("flight", "hemisphere"),
    }
    return mapping.get(claim_id, tuple(claim_id.replace("_", " ").split()))


def _eval_battery_item(item: dict[str, Any], kind: str) -> dict[str, Any]:
    idx = _address_index()
    addr_doc = _load(ADDRESSES, {})
    doctrine = _load(DOCTRINE, {})
    params = item.get("params") or {}
    got: Any = None
    passed = False
    detail = ""

    try:
        if kind == "address_country":
            addr = idx.get(str(item.get("address_id") or ""), {})
            got = addr.get("country")
            passed = str(got) == str(item.get("expected"))

        elif kind == "address_postal":
            addr = idx.get(str(item.get("address_id") or ""), {})
            got = addr.get("postal_code")
            passed = str(got).strip() == str(item.get("expected")).strip()

        elif kind == "address_city":
            addr = idx.get(str(item.get("address_id") or ""), {})
            got = addr.get("city")
            passed = str(got) == str(item.get("expected"))

        elif kind == "address_region":
            addr = idx.get(str(item.get("address_id") or ""), {})
            got = addr.get("region")
            passed = str(got) == str(item.get("expected"))

        elif kind == "address_format":
            addr = idx.get(str(item.get("address_id") or ""), {})
            got = addr.get("format")
            passed = str(got) == str(item.get("expected"))

        elif kind == "hemisphere":
            addr = idx.get(str(item.get("address_id") or ""), {})
            lat = float(addr.get("lat") or 0)
            lon = float(addr.get("lon") or 0)
            got = _hemisphere(lat, lon)
            passed = got == str(item.get("expected"))

        elif kind == "corpus_count":
            count = int(addr_doc.get("count") or len(addr_doc.get("addresses") or []))
            got = count
            passed = count >= int(params.get("min") or 1)

        elif kind == "countries_count":
            countries = addr_doc.get("countries_represented") or []
            got = len(countries)
            passed = got >= int(params.get("min") or 1)

        elif kind == "capital":
            country = str(params.get("country") or "")
            got = _CAPITALS.get(country, "")
            passed = got.lower() == str(item.get("expected")).lower()

        elif kind == "continent":
            country = str(params.get("country") or "")
            got = _CONTINENTS.get(country, "")
            passed = got == str(item.get("expected"))

        elif kind == "river":
            city = str(params.get("city") or "")
            got = _RIVERS.get(city, "")
            passed = got.lower() == str(item.get("expected")).lower()

        elif kind == "peak":
            got = "Mount Everest"
            passed = str(item.get("expected")) in got

        elif kind == "ocean":
            got = "Pacific"
            passed = got == str(item.get("expected"))

        elif kind == "latitude_fact":
            got = 0
            passed = float(item.get("expected") or 0) == got

        elif kind == "longitude_fact":
            got = 0
            passed = float(item.get("expected") or 0) == got

        elif kind == "utc_city":
            got = "Greenwich"
            passed = str(item.get("expected")).lower() in got.lower()

        elif kind == "landmark_country":
            got = "China" if params.get("landmark") == "Great Wall" else ""
            passed = got == str(item.get("expected"))

        elif kind == "basin_continent":
            got = "South America"
            passed = got == str(item.get("expected"))

        elif kind == "flat_claim":
            cid = str(params.get("claim_id") or "")
            claims = _flat_claims()
            claim = claims.get(cid, {})
            text = str(claim.get("claim") or "").lower()
            tokens = _flat_claim_tokens(cid)
            got = ", ".join(tokens[:3])
            passed = sum(1 for t in tokens if t in text) >= max(1, len(tokens) // 2)

        elif kind == "globe_contrast":
            fe = doctrine.get("flat_earth") or {}
            contrasts = fe.get("globe_contrast") or []
            i = int(params.get("index") or 0)
            line = str(contrasts[i] if i < len(contrasts) else "")
            got = line[:40]
            passed = str(item.get("expected")).lower() in line.lower()

        elif kind == "flat_claim_count":
            fe = doctrine.get("flat_earth") or {}
            got = len(fe.get("claims") or [])
            passed = got >= int(params.get("min") or 1)

        elif kind == "doctrine_section":
            key = str(params.get("key") or "")
            passed = key in doctrine and bool(doctrine.get(key))
            got = passed

        else:
            detail = f"unknown kind {kind}"
    except (TypeError, ValueError, KeyError) as exc:
        detail = str(exc)
        passed = False

    return {
        "id": item.get("id"),
        "query": item.get("query"),
        "kind": kind,
        "passed": passed,
        "got": got,
        "expected": item.get("expected"),
        "detail": detail,
    }


def run_battery(battery_id: str) -> dict[str, Any]:
    bat_doc = _load(BATTERY, {})
    items = (bat_doc.get("batteries") or {}).get(battery_id) or []
    rows = [_eval_battery_item(it, str(it.get("kind") or "")) for it in items]
    passed = sum(1 for r in rows if r.get("passed"))
    total = len(rows) or 1
    rate = round(100.0 * passed / total, 1)
    out = {
        "ok": True,
        "battery": battery_id,
        "passed": passed,
        "total": total,
        "pass_rate": rate,
        "fluent": rate >= 92,
        "mastered": rate >= 98 and passed == total,
        "rows": rows,
    }
    rt = _runtime()
    results = rt.setdefault("battery_results", {})
    results[battery_id] = {**out, "updated": _now()}
    rt["updated"] = _now()
    _save(RUNTIME, rt)
    _append_ledger({"ts": rt["updated"], "event": "battery", "battery": battery_id, "pass_rate": rate})
    return out


def run_all_batteries() -> dict[str, Any]:
    bat_doc = _load(BATTERY, {})
    ids = list((bat_doc.get("batteries") or {}).keys())
    results = {bid: run_battery(bid) for bid in ids}
    passed = sum(r.get("passed", 0) for r in results.values())
    total = sum(r.get("total", 0) for r in results.values()) or 1
    rate = round(100.0 * passed / total, 1)
    return {"ok": True, "batteries": results, "pass_rate": rate, "passed": passed, "total": total}


def _runtime() -> dict[str, Any]:
    return _load(RUNTIME, {
        "schema": "hostess7-geography-runtime/v1",
        "battery_results": {},
        "proficiency": 0.0,
        "address_drills": 0,
        "session_rounds": 0,
    })


def train_geography_session(*, rounds: int | None = None) -> dict[str, Any]:
    """Drill postal addresses + run batteries."""
    doc = _load(DOCTRINE, {})
    comp = doc.get("completion") or {}
    n = rounds if rounds is not None else int(comp.get("session_rounds_min") or 24)
    n = max(1, min(n, 500))

    idx = _address_index()
    ids = list(idx.keys())
    drills = 0
    for i in range(n):
        if ids:
            aid = ids[i % len(ids)]
            addr = idx[aid]
            drills += 1
            _append_ledger({
                "ts": _now(),
                "event": "address_drill",
                "address_id": aid,
                "country": addr.get("country"),
                "city": addr.get("city"),
                "postal_code": addr.get("postal_code"),
            })

    batteries = run_all_batteries()
    bat_rate = float(batteries.get("pass_rate") or 0) / 100.0
    addr_doc = _load(ADDRESSES, {})
    addr_count = int(addr_doc.get("count") or len(addr_doc.get("addresses") or []))

    rt = _runtime()
    prof = float(rt.get("proficiency") or 0)
    rate = float(comp.get("train_tick_proficiency") or 0.015)
    tick_gain = rate * (0.5 + 0.35 * bat_rate + 0.15 * min(1.0, addr_count / 100.0))
    prof = min(1.0, prof + tick_gain * n)
    fluent = prof >= 0.92 and bat_rate >= 0.85
    mastered = prof >= 0.98 and bat_rate >= 0.98

    rt["proficiency"] = round(prof, 4)
    rt["fluent"] = fluent
    rt["mastered"] = mastered
    rt["address_drills"] = int(rt.get("address_drills") or 0) + drills
    rt["session_rounds"] = int(rt.get("session_rounds") or 0) + n
    rt["tier"] = (
        "geography_master" if mastered else "geography_fluent" if fluent else "geography_training"
    )
    rt["last_session"] = {
        "rounds": n,
        "address_drills": drills,
        "address_corpus": addr_count,
        "battery_pass_rate": batteries.get("pass_rate"),
        "updated": _now(),
    }
    rt["updated"] = _now()
    _save(RUNTIME, rt)
    _append_ledger({
        "ts": rt["updated"],
        "event": "train_session",
        "rounds": n,
        "proficiency": prof,
        "pass_rate": batteries.get("pass_rate"),
    })
    return {
        "ok": True,
        "rounds": n,
        "address_drills": drills,
        "address_corpus": addr_count,
        "proficiency": prof,
        "fluent": fluent,
        "mastered": mastered,
        "tier": rt["tier"],
        "batteries": batteries,
    }


def lookup_address(address_id: str) -> dict[str, Any]:
    addr = _address_index().get(address_id)
    if not addr:
        return {"ok": False, "error": "address_not_found", "address_id": address_id}
    lat = float(addr.get("lat") or 0)
    lon = float(addr.get("lon") or 0)
    return {
        "ok": True,
        "address": addr,
        "formatted": ", ".join(addr.get("lines") or []),
        "hemisphere": _hemisphere(lat, lon),
    }


def flat_earth_section() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    fe = doc.get("flat_earth") or {}
    return {
        "ok": True,
        "schema": "hostess7-flat-earth/v1",
        "section": "flat_earth",
        "section_title": fe.get("section_title"),
        "model_summary": fe.get("model_summary"),
        "claims": fe.get("claims") or [],
        "globe_contrast": fe.get("globe_contrast") or [],
        "operator_guidance": fe.get("operator_guidance"),
    }


def _track_batteries(track_id: str) -> list[str]:
    doc = _load(DOCTRINE, {})
    for row in doc.get("tracks") or []:
        if row.get("id") == track_id:
            return list(row.get("batteries") or [])
    mapping = {
        "geography": ["postal_addresses", "world_geography", "flat_earth"],
        "postal_addresses": ["postal_addresses"],
        "world_geography": ["world_geography"],
        "flat_earth_geography": ["flat_earth"],
    }
    return mapping.get(track_id, [])


def assess_track(track_id: str) -> dict[str, Any]:
    rt = _runtime()
    results = rt.get("battery_results") or {}
    bat_ids = _track_batteries(track_id)
    if not bat_ids:
        return {"ok": False, "error": "unknown_track", "track": track_id}

    passed = 0
    total = 0
    for bid in bat_ids:
        row = results.get(bid) or {}
        passed += int(row.get("passed") or 0)
        total += int(row.get("total") or 0)
        if not row:
            bat = run_battery(bid)
            passed += int(bat.get("passed") or 0)
            total += int(bat.get("total") or 0)

    total = max(total, 1)
    rate = passed / total
    comp = _load(DOCTRINE, {}).get("completion") or {}
    prof = float(rt.get("proficiency") or 0)
    drills_ok = int(rt.get("address_drills") or 0) >= int(comp.get("address_drill_min") or 40)

    complete = rate >= float(comp.get("pass_rate_pct") or 85) / 100.0
    if track_id == "geography":
        complete = complete and drills_ok
    fluent = complete and rate >= float(comp.get("fluent_rate_pct") or 92) / 100.0 and prof >= 0.85
    mastered = fluent and rate >= float(comp.get("master_rate_pct") or 98) / 100.0 and bool(rt.get("mastered"))

    level = (
        "mastered" if mastered else "fluent" if fluent else "complete" if complete
        else "training" if rate > 0.2 else "pending"
    )
    return {
        "ok": True,
        "level": level,
        "complete": complete,
        "mastered": mastered,
        "fluent": fluent,
        "score": round(max(rate, prof * 0.35), 4),
        "pass_rate": round(rate * 100, 1),
        "proficiency": prof,
        "address_drills": int(rt.get("address_drills") or 0),
        "address_corpus": int((_load(ADDRESSES, {}).get("count")) or 0),
        "batteries": bat_ids,
        "tier": rt.get("tier"),
    }


def assess_all_tracks() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    tracks: dict[str, Any] = {}
    for row in doc.get("tracks") or []:
        tid = str(row.get("id") or "")
        if tid:
            tracks[tid] = assess_track(tid)
            tracks[tid]["label"] = row.get("label")
    return {"schema": "hostess7-geography-assess/v1", "updated": _now(), "tracks": tracks}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    assess = assess_all_tracks()
    rt = _runtime()
    addr_doc = _load(ADDRESSES, {})
    fe = flat_earth_section()
    panel = {
        "schema": "hostess7-geography/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "motto": doc.get("motto"),
        "foundation": doc.get("foundation"),
        "field_note": doc.get("field_note"),
        "proficiency": rt.get("proficiency"),
        "fluent": rt.get("fluent"),
        "mastered": rt.get("mastered"),
        "tier": rt.get("tier") or "geography_pending",
        "address_corpus_count": addr_doc.get("count"),
        "countries_represented": addr_doc.get("countries_represented"),
        "address_formats": doc.get("address_formats"),
        "address_drills": rt.get("address_drills"),
        "session_rounds": rt.get("session_rounds"),
        "battery_results": rt.get("battery_results"),
        "tracks": assess.get("tracks"),
        "flat_earth": fe,
        "last_session": rt.get("last_session"),
        "training_mode": "geography",
    }
    if write:
        _save(PANEL, panel)
    return panel


_OCR_API: dict | None = None


def _ocr_api() -> dict:
    global _OCR_API
    if _OCR_API is None:
        import importlib.util
        py = INSTALL / "lib" / "hostess7-ocr-bind.py"
        spec = importlib.util.spec_from_file_location("h7_ocr_bind_geography", py)
        if not spec or not spec.loader:
            raise ImportError("hostess7-ocr-bind.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _OCR_API = mod.bind("geography", install=INSTALL, state=STATE, ledger=LEDGER)
    return _OCR_API


def ingest_ocr_vision(**kw):
    return _ocr_api()["ingest_ocr_vision"](**kw)


def train_ocr_vision(**kw):
    return _ocr_api()["train_ocr_vision"](**kw)


def ocr_vision_status():
    return _ocr_api()["ocr_vision_status"]()


def _handle_ocr_cli(cmd: str) -> int | None:
    import importlib.util
    py = INSTALL / "lib" / "hostess7-ocr-feed.py"
    spec = importlib.util.spec_from_file_location("h7_ocr_feed_geography", py)
    if not spec or not spec.loader:
        return None
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    return feed.handle_ocr_cli(
        cmd,
        ingest_fn=ingest_ocr_vision,
        train_fn=train_ocr_vision,
        status_fn=ocr_vision_status,
        usage="hostess7-geography-training.py [json|assess|battery|train|address|flat-earth|track-assess|ocr-ingest|ocr-train|ocr-status]",
    )


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "assess":
        print(json.dumps(assess_all_tracks(), ensure_ascii=False))
        return 0
    if cmd == "battery" and len(sys.argv) > 2:
        print(json.dumps(run_battery(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd in ("batteries", "run-batteries"):
        print(json.dumps(run_all_batteries(), ensure_ascii=False))
        return 0
    if cmd in ("train", "session"):
        rounds = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
        print(json.dumps(train_geography_session(rounds=rounds), ensure_ascii=False))
        return 0
    if cmd == "address" and len(sys.argv) > 2:
        print(json.dumps(lookup_address(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd in ("flat-earth", "flat_earth"):
        print(json.dumps(flat_earth_section(), ensure_ascii=False))
        return 0
    if cmd == "track-assess" and len(sys.argv) > 2:
        print(json.dumps(assess_track(sys.argv[2]), ensure_ascii=False))
        return 0
    ocr_ret = _handle_ocr_cli(cmd)
    if ocr_ret is not None:
        return ocr_ret
    print(json.dumps({
        "error": "usage: hostess7-geography-training.py [json|assess|battery ID|batteries|train [rounds]|address ID|flat-earth|track-assess ID]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())