#!/usr/bin/env pythong
"""Census & public government field population — operator home, geographies, open records.

Geocodes operator address (Census geocoder + Nominatim), binds home_operator GPS table,
merges geography dossiers into gov-dossiers.json. ACS population when NEXUS_CENSUS_API_KEY set.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SOURCES_SEED = INSTALL / "data" / "census-sources-seed.json"
HOME_SEED_TSV = INSTALL / "data" / "home-gps-correlation.tsv"
LOC_FILE = STATE / "operator-location.json"
GPS_TABLE = STATE / "home-gps-correlation.json"
GOV_DOSSIERS = STATE / "gov-dossiers.json"
CENSUS_CACHE = STATE / "census-field-cache.json"

UA = "NEXUS-Shield/5.9.5"
ZIP_RE = re.compile(r"\b(\d{5})(?:-\d{4})?\b")
STATE_ABBR_RE = re.compile(
    r"\b(AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|MT|"
    r"NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)\b",
    re.I,
)


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


def _http_json(url: str, *, timeout: float = 12.0) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _normalize_addr(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _seed_address_hit(address: str) -> dict[str, Any] | None:
    if not HOME_SEED_TSV.is_file():
        return None
    try:
        lines = HOME_SEED_TSV.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if len(lines) < 2:
        return None
    header = [h.strip() for h in lines[0].split("\t")]
    needle = _normalize_addr(address)
    best: dict[str, Any] | None = None
    best_score = 0
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        row = {header[i]: (parts[i] if i < len(parts) else "") for i in range(len(header))}
        seed_addr = _normalize_addr(row.get("address") or "")
        if not seed_addr:
            continue
        lat = row.get("lat") or ""
        lon = row.get("lon") or ""
        try:
            lat_f = float(lat)
            lon_f = float(lon)
        except (TypeError, ValueError):
            continue
        score = 0
        if needle == seed_addr:
            score = 100
        elif needle in seed_addr or seed_addr in needle:
            score = 80
        else:
            overlap = len(set(needle.split()) & set(seed_addr.split()))
            score = overlap * 10
        if score > best_score:
            best_score = score
            best = {
                "lat": lat_f,
                "lon": lon_f,
                "label": row.get("label") or row.get("address") or address,
                "seed_id": row.get("id") or "",
                "seed_address": row.get("address") or "",
                "score": score,
            }
    return best if best_score >= 50 else None


def _parse_us_address(address: str) -> dict[str, str]:
    text = address.strip()
    parts = [p.strip() for p in text.split(",") if p.strip()]
    street = parts[0] if parts else text
    city = state = zip_code = ""
    if len(parts) >= 2:
        city = parts[1]
    tail = parts[-1] if parts else ""
    zm = ZIP_RE.search(tail)
    if zm:
        zip_code = zm.group(1)
    sm = STATE_ABBR_RE.search(tail)
    if sm:
        state = sm.group(1).upper()
    if not city and len(parts) >= 3:
        city = parts[-2]
    if not state:
        sm2 = STATE_ABBR_RE.search(text)
        if sm2:
            state = sm2.group(1).upper()
    return {"street": street, "city": city, "state": state, "zip": zip_code}


def _geocode_census_address(address: str) -> dict[str, Any] | None:
    parsed = _parse_us_address(address)
    if not parsed.get("street"):
        return None
    params: dict[str, str] = {
        "street": parsed["street"],
        "benchmark": "4",
        "format": "json",
    }
    if parsed.get("city"):
        params["city"] = parsed["city"]
    if parsed.get("state"):
        params["state"] = parsed["state"]
    if parsed.get("zip"):
        params["zip"] = parsed["zip"]
    url = (
        "https://geocoding.geo.census.gov/geocoder/geographies/address?"
        + urllib.parse.urlencode(params)
        + "&vintage=4"
    )
    try:
        data = _http_json(url)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None
    matches = (data.get("result") or {}).get("addressMatches") or []
    if not matches:
        oneline = urllib.parse.urlencode({
            "address": address.strip(),
            "benchmark": "4",
            "format": "json",
        })
        try:
            data2 = _http_json(
                f"https://geocoding.geo.census.gov/geocoder/geographies/onelineaddress?{oneline}&vintage=4"
            )
            matches = (data2.get("result") or {}).get("addressMatches") or []
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
            return None
    if not matches:
        return None
    hit = matches[0]
    coords = hit.get("coordinates") or {}
    return {
        "lat": float(coords.get("y")),
        "lon": float(coords.get("x")),
        "label": hit.get("matchedAddress") or address,
        "source": "us_census_geocoder",
        "geographies": hit.get("geographies") or {},
        "address_components": hit.get("addressComponents") or {},
    }


def _geocode_nominatim(address: str) -> dict[str, Any] | None:
    q = urllib.parse.quote(address.strip())
    if not q:
        return None
    url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&addressdetails=1&q={q}"
    try:
        rows = _http_json(url, timeout=14.0)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None
    if not rows:
        return None
    row = rows[0]
    return {
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
        "label": row.get("display_name", address)[:240],
        "source": "osm_nominatim",
        "address_details": row.get("address") or {},
        "country_code": (row.get("address") or {}).get("country_code", "").upper(),
    }


def _geographies_for_coords(lat: float, lon: float) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "x": str(lon),
        "y": str(lat),
        "benchmark": "4",
        "vintage": "4",
        "format": "json",
    })
    url = f"https://geocoding.geo.census.gov/geocoder/geographies/coordinates?{params}"
    try:
        data = _http_json(url)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return {}
    matches = (data.get("result") or {}).get("geographies") or {}
    return matches if isinstance(matches, dict) else {}


def _fetch_acs_tract(geographies: dict[str, Any]) -> dict[str, Any] | None:
    api_key = os.environ.get("NEXUS_CENSUS_API_KEY", "").strip()
    if not api_key:
        return None
    tracts = geographies.get("Census Tracts") or []
    states = geographies.get("States") or []
    counties = geographies.get("Counties") or []
    if not tracts or not states or not counties:
        return None
    tract = tracts[0]
    state = str(tract.get("STATE") or states[0].get("STATE") or "")
    county = str(tract.get("COUNTY") or counties[0].get("COUNTY") or "")
    tract_id = str(tract.get("TRACT") or "")
    if not (state and county and tract_id):
        return None
    variables = "NAME,B01003_001E,B19013_001E,B25077_001E"
    path = (
        f"https://api.census.gov/data/2022/acs/acs5?get={variables}"
        f"&for=tract:{tract_id}&in=state:{state}%20county:{county}&key={urllib.parse.quote(api_key)}"
    )
    try:
        rows = _http_json(path)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None
    if not isinstance(rows, list) or len(rows) < 2:
        return None
    header = rows[0]
    values = rows[1]
    return dict(zip(header, values))


def _flatten_geographies(geographies: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for layer, items in geographies.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            out.append({
                "layer": layer,
                "name": item.get("NAME") or item.get("BASENAME") or "",
                "geoid": item.get("GEOID") or "",
                "state": item.get("STATE") or "",
                "county": item.get("COUNTY") or "",
                "tract": item.get("TRACT") or "",
                "place": item.get("PLACE") or "",
            })
    return out


def _merge_gov_record(key: str, record: dict[str, Any]) -> None:
    gdoc = _load_json(GOV_DOSSIERS, {"records": {}, "import_log": [], "updated": None})
    records = gdoc.setdefault("records", {})
    prev = records.get(key) if isinstance(records.get(key), dict) else {}
    merged = dict(prev)
    for k, v in record.items():
        if v in (None, ""):
            continue
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k] = {**merged[k], **v}
        elif k in merged and isinstance(merged[k], list) and isinstance(v, list):
            seen = {json.dumps(x, sort_keys=True, default=str) for x in merged[k]}
            for item in v:
                sig = json.dumps(item, sort_keys=True, default=str)
                if sig not in seen:
                    merged[k].append(item)
                    seen.add(sig)
        else:
            merged[k] = v
    merged["updated"] = _now()
    records[key] = merged
    log = list(gdoc.get("import_log") or [])
    log.append({
        "agency_id": "census_field",
        "format_id": "auto_populate",
        "merged": 1,
        "imported_at": _now(),
        "record_key": key,
    })
    gdoc["import_log"] = log[-300:]
    gdoc["updated"] = _now()
    _save_json(GOV_DOSSIERS, gdoc)


def _sync_operator_location(geo: dict[str, Any], address: str = "") -> dict[str, Any]:
    doc = _load_json(LOC_FILE, {
        "lat": None, "lon": None, "label": "", "source": "unset", "updated": None,
    })
    doc.update({
        "lat": round(float(geo["lat"]), 6),
        "lon": round(float(geo["lon"]), 6),
        "label": geo.get("label") or doc.get("label") or "",
        "source": geo.get("source") or "census_populate",
        "updated": _now(),
    })
    if address:
        doc["address"] = address
    if geo.get("geographies"):
        doc["census_geographies"] = _flatten_geographies(geo["geographies"])
    if geo.get("acs"):
        doc["census_acs"] = geo["acs"]
    if geo.get("country_code"):
        doc["country_code"] = geo["country_code"]
    _save_json(LOC_FILE, doc)
    return doc


def _sync_home_operator(op_doc: dict[str, Any]) -> dict[str, Any]:
    gps = _load_json(GPS_TABLE, {"homes": [], "operator": {}, "updated": None})
    homes = list(gps.get("homes") or [])
    lat = op_doc.get("lat")
    lon = op_doc.get("lon")
    found = False
    for h in homes:
        if h.get("id") == "home_operator":
            h["lat"] = lat
            h["lon"] = lon
            h["address"] = op_doc.get("address") or h.get("address") or ""
            h["label"] = op_doc.get("label") or h.get("label") or "Operator home"
            h["source"] = op_doc.get("source") or "operator"
            h.setdefault("sources", []).append("census_populate")
            h["correlated"] = True
            if op_doc.get("census_geographies"):
                h["census_geographies"] = op_doc["census_geographies"]
            found = True
            break
    if not found:
        homes.insert(0, {
            "id": "home_operator",
            "label": op_doc.get("label") or "Operator home",
            "address": op_doc.get("address") or "",
            "lat": lat,
            "lon": lon,
            "role": "home",
            "notes": "Operator address — census field populate",
            "source": op_doc.get("source") or "census_populate",
            "sources": ["operator", "census_populate"],
            "correlated": True,
            "census_geographies": op_doc.get("census_geographies") or [],
        })
    gps["homes"] = homes
    gps["operator"] = op_doc
    gps["updated"] = _now()
    gps["schema"] = "home-gps-correlation/v2"
    gps["with_coords"] = sum(1 for h in homes if h.get("lat") is not None)
    _save_json(GPS_TABLE, gps)
    return gps


def geocode_address(address: str) -> dict[str, Any]:
    """Full geocode chain: seed TSV → Census address → Nominatim → Census coord lookup."""
    seed = _seed_address_hit(address)
    geo = _geocode_census_address(address)
    if not geo:
        enriched = address
        if "port huron" in _normalize_addr(address) and "saint clair" not in _normalize_addr(address):
            enriched = f"{address}, Saint Clair County, Michigan 48060"
        geo = _geocode_nominatim(enriched)
    if not geo and seed:
        geo = {
            "lat": seed["lat"],
            "lon": seed["lon"],
            "label": seed.get("label") or address,
            "source": "home_seed_tsv",
            "seed_id": seed.get("seed_id"),
        }
    if not geo:
        return {"ok": False, "error": "geocode_failed", "address": address}
    if seed and geo.get("source", "").startswith("osm"):
        try:
            dist = abs(float(geo["lat"]) - seed["lat"]) + abs(float(geo["lon"]) - seed["lon"])
        except (TypeError, ValueError, KeyError):
            dist = 999
        if dist > 0.5:
            geo = {
                "lat": seed["lat"],
                "lon": seed["lon"],
                "label": seed.get("label") or geo.get("label") or address,
                "source": "home_seed_tsv_corrected",
                "seed_id": seed.get("seed_id"),
                "nominatim_reject": geo.get("label"),
            }
    if not geo.get("geographies") and geo.get("lat") is not None:
        geogs = _geographies_for_coords(float(geo["lat"]), float(geo["lon"]))
        if geogs:
            geo["geographies"] = geogs
            if geo.get("source") == "osm_nominatim":
                geo["source"] = "osm_nominatim+census_geographies"
    acs = _fetch_acs_tract(geo.get("geographies") or {})
    if acs:
        geo["acs"] = acs
    geo["ok"] = True
    geo["address"] = address
    return geo


def populate_from_operator(*, address: str = "", force: bool = False) -> dict[str, Any]:
    op = _load_json(LOC_FILE, {})
    addr = address.strip() or str(op.get("address") or "").strip()
    lat = op.get("lat")
    lon = op.get("lon")

    if addr and (force or lat is None or op.get("source") in ("unset", "", None)):
        geo = geocode_address(addr)
        if not geo.get("ok"):
            return geo
    elif lat is not None and lon is not None:
        geo = {
            "ok": True,
            "lat": float(lat),
            "lon": float(lon),
            "label": op.get("label") or "",
            "source": op.get("source") or "operator",
            "geographies": {},
            "address": addr,
        }
        geogs = _geographies_for_coords(float(lat), float(lon))
        if geogs:
            geo["geographies"] = geogs
            geo["source"] = f"{geo['source']}+census_geographies"
        acs = _fetch_acs_tract(geogs)
        if acs:
            geo["acs"] = acs
    elif addr:
        geo = geocode_address(addr)
        if not geo.get("ok"):
            return geo
    else:
        return {"ok": False, "error": "no_operator_address", "hint": "Set address in Honor panel"}

    op_doc = _sync_operator_location(geo, addr)
    gps_doc = _sync_home_operator(op_doc)

    geog_rows = _flatten_geographies(geo.get("geographies") or {})
    record = {
        "agency_id": "census_field",
        "name": op_doc.get("label") or "Operator home",
        "address": addr or op_doc.get("label"),
        "lat": op_doc.get("lat"),
        "lon": op_doc.get("lon"),
        "role": "home",
        "category": "census",
        "source": geo.get("source"),
        "locations": [{
            "label": op_doc.get("label"),
            "address": addr,
            "lat": op_doc.get("lat"),
            "lon": op_doc.get("lon"),
            "place": geog_rows[0]["name"] if geog_rows else "",
        }],
        "census_geographies": geog_rows,
        "census_acs": geo.get("acs"),
        "public_records": True,
        "notes": "Auto-populated from free public census / government geocoder records.",
    }
    _merge_gov_record("census:home_operator", record)

    for i, row in enumerate(geog_rows[:12]):
        if not row.get("geoid"):
            continue
        _merge_gov_record(
            f"census:geo:{row.get('layer','layer')}:{row.get('geoid')}",
            {
                "agency_id": "census_field",
                "name": row.get("name") or row.get("geoid"),
                "category": "census",
                "geoid": row.get("geoid"),
                "layer": row.get("layer"),
                "source": "us_census_geocoder",
                "public_records": True,
                "lat": op_doc.get("lat"),
                "lon": op_doc.get("lon"),
                "notes": f"Public geography layer near operator — {row.get('layer')}",
            },
        )

    out = {
        "ok": True,
        "updated": _now(),
        "operator": op_doc,
        "gps_table": {"count": gps_doc.get("with_coords", 0), "homes": len(gps_doc.get("homes") or [])},
        "geographies": len(geog_rows),
        "acs_populated": bool(geo.get("acs")),
        "source": geo.get("source"),
        "address": addr,
        "census_api_key_set": bool(os.environ.get("NEXUS_CENSUS_API_KEY", "").strip()),
    }
    cache = _load_json(CENSUS_CACHE, {"runs": []})
    runs = list(cache.get("runs") or [])
    runs.append(out)
    cache["runs"] = runs[-50:]
    cache["updated"] = _now()
    cache["last"] = out
    _save_json(CENSUS_CACHE, cache)
    return out


def panel_json() -> dict[str, Any]:
    seed = _load_json(SOURCES_SEED, {"sources": []})
    cache = _load_json(CENSUS_CACHE, {})
    op = _load_json(LOC_FILE, {})
    return {
        "motto": "Current census & public government records — operator home bound, geographies merged.",
        "sources": seed.get("sources") or [],
        "operator_gps_ready": op.get("lat") is not None,
        "operator_address": op.get("address") or "",
        "census_geographies": op.get("census_geographies") or [],
        "census_acs": op.get("census_acs"),
        "census_api_key_set": bool(os.environ.get("NEXUS_CENSUS_API_KEY", "").strip()),
        "last_run": cache.get("last"),
        "updated": cache.get("updated") or _now(),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "populate":
        address = " ".join(sys.argv[2:]).strip() if len(sys.argv) > 2 else ""
        force = os.environ.get("NEXUS_CENSUS_FORCE", "") == "1"
        print(json.dumps(populate_from_operator(address=address, force=force), ensure_ascii=False))
        return 0
    if cmd == "geocode" and len(sys.argv) >= 3:
        print(json.dumps(geocode_address(" ".join(sys.argv[2:])), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: census-field-populate.py [json|populate [ADDRESS]|geocode TEXT]",
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())