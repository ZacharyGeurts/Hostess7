#!/usr/bin/env pythong
"""NEXUS Geo Intel — industry-standard enrichment for host attack placement.

Standards pipeline (no single vendor lock-in):
  - IEEE 802 OUI / MA-L (MAC vendor registry)
  - RFC 7483 RDAP (IP registrar, network, entities)
  - GeoIP enrichment (ip-api.com cache + city-level lat/lon)
  - RFC 7946 GeoJSON feature output for map consumers
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
DATA = INSTALL / "data"
CACHE_PATH = STATE / "geo-intel-cache.json"

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)

RDAP_TTL = 86400 * 3
GEO_TTL = 86400


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
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def load_oui_table() -> dict[str, dict[str, str]]:
    path = DATA / "oui-vendors.tsv"
    out: dict[str, dict[str, str]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        prefix, vendor = parts[0].strip().upper(), parts[1].strip()
        out[prefix] = {"vendor": vendor, "category": parts[2].strip() if len(parts) > 2 else ""}
    return out


def normalize_mac(mac: str) -> str:
    mac = mac.upper().replace("-", ":")
    parts = [p.zfill(2) for p in mac.split(":") if p]
    if len(parts) >= 3:
        return ":".join(parts[:3])
    return mac


def load_arp_table() -> dict[str, str]:
    """ip -> mac from neigh snapshot."""
    out: dict[str, str] = {}
    snap = STATE / "arp.snapshot"
    if not snap.is_file():
        return out
    for line in snap.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("IP"):
            continue
        parts = line.split()
        if len(parts) >= 4 and re.match(r"^\d+\.\d+\.\d+\.\d+$", parts[0]):
            out[parts[0]] = parts[3] if len(parts) > 3 else parts[2]
    return out


def lookup_mac_ieee_oui(mac: str, oui_db: dict[str, dict[str, str]]) -> dict[str, Any]:
    prefix = normalize_mac(mac)
    hit = oui_db.get(prefix)
    if hit:
        return {
            "mac": mac,
            "oui": prefix,
            "vendor": hit.get("vendor", ""),
            "category": hit.get("category", ""),
            "standard": "IEEE-802-OUI",
            "source": "oui-table",
        }
    return {"mac": mac, "oui": prefix, "vendor": "", "standard": "IEEE-802-OUI", "source": "unresolved"}


def _parse_rdap_entities(doc: dict[str, Any]) -> dict[str, str]:
    registrar = ""
    org = ""
    abuse = ""
    for ent in doc.get("entities") or []:
        roles = ent.get("roles") or []
        vcard = ent.get("vcardArray")
        name = ""
        if isinstance(vcard, list) and len(vcard) > 1:
            for field in vcard[1]:
                if isinstance(field, list) and len(field) >= 4 and field[0] == "fn":
                    name = str(field[3])
        if "registrar" in roles and name:
            registrar = name
        if "registrant" in roles and name:
            org = org or name
        if "abuse" in roles:
            for item in ent.get("vcardArray", [[], []])[1] if isinstance(ent.get("vcardArray"), list) else []:
                if isinstance(item, list) and item[0] == "email":
                    abuse = str(item[3])
    return {"registrar": registrar, "org": org, "abuse_contact": abuse}


def lookup_rdap(ip: str, timeout: float = 6.0) -> dict[str, Any]:
    """RFC 7483 RDAP lookup via rdap.org aggregator."""
    url = f"https://rdap.org/ip/{urllib.parse.quote(ip)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Shield/2.9 geo-intel RDAP", "Accept": "application/rdap+json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            doc = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc), "standard": "RFC7483-RDAP"}

    entities = _parse_rdap_entities(doc)
    cidr = ""
    if doc.get("cidr0_cidrs"):
        cidr = doc["cidr0_cidrs"][0].get("v4prefix", "") or doc["cidr0_cidrs"][0].get("v6prefix", "")
    return {
        "ok": True,
        "standard": "RFC7483-RDAP",
        "handle": str(doc.get("handle") or ""),
        "name": str(doc.get("name") or ""),
        "type": str(doc.get("type") or ""),
        "country": str(doc.get("country") or ""),
        "start_address": str(doc.get("startAddress") or ""),
        "end_address": str(doc.get("endAddress") or ""),
        "cidr": cidr,
        "registrar": entities.get("registrar") or "",
        "registrant_org": entities.get("org") or "",
        "abuse_contact": entities.get("abuse_contact") or "",
        "rdap_url": url,
        "updated": _now(),
    }


def _geo_from_intel_cache(ip: str) -> dict[str, Any]:
    cache = _load_json(STATE / "vector-intel-cache.json", {"ips": {}})
    entry = (cache.get("ips") or {}).get(ip) or {}
    return {
        "lat": entry.get("lat"),
        "lon": entry.get("lon"),
        "city": entry.get("city") or "",
        "region": entry.get("region") or entry.get("regionName") or "",
        "country": entry.get("country") or "",
        "country_code": entry.get("country_code") or entry.get("countryCode") or "",
        "org": entry.get("org") or "",
        "as": entry.get("as") or "",
        "asname": entry.get("asname") or "",
        "hostname": entry.get("hostname") or entry.get("label") or "",
        "geo_source": entry.get("source") or "cache",
        "standard": "GeoIP",
    }


def enrich_ip(ip: str, cache: dict[str, Any] | None = None, online: bool = True) -> dict[str, Any]:
    """Full standards enrichment for one IP."""
    if not ip or PRIVATE_RE.match(ip):
        return {"ip": ip, "private": True, "standards": []}

    cache = cache if cache is not None else _load_json(CACHE_PATH, {"ips": {}})
    now = time.time()
    cached = (cache.get("ips") or {}).get(ip)
    if cached:
        age = now - float(cached.get("_ts", 0))
        if age < RDAP_TTL and cached.get("rdap", {}).get("ok"):
            return cached

    geo = _geo_from_intel_cache(ip)
    oui_db = load_oui_table()
    arp = load_arp_table()
    mac = arp.get(ip, "")
    mac_info = lookup_mac_ieee_oui(mac, oui_db) if mac else {}

    rdap: dict[str, Any] = (cached or {}).get("rdap") or {"ok": False}
    if online and not rdap.get("ok"):
        rdap = lookup_rdap(ip)

    standards = ["GeoIP"]
    if rdap.get("ok"):
        standards.append("RFC7483-RDAP")
    if mac_info.get("vendor"):
        standards.append("IEEE-802-OUI")

    out: dict[str, Any] = {
        "ip": ip,
        "lat": geo.get("lat"),
        "lon": geo.get("lon"),
        "city": geo.get("city"),
        "region": geo.get("region"),
        "country": geo.get("country"),
        "country_code": geo.get("country_code"),
        "org": geo.get("org") or rdap.get("registrant_org") or rdap.get("name") or "",
        "asn": geo.get("as") or "",
        "asname": geo.get("asname") or "",
        "hostname": geo.get("hostname") or "",
        "registrar": rdap.get("registrar") or "",
        "network_handle": rdap.get("handle") or "",
        "cidr": rdap.get("cidr") or "",
        "abuse_contact": rdap.get("abuse_contact") or "",
        "mac": mac_info.get("mac") or "",
        "mac_vendor": mac_info.get("vendor") or "",
        "mac_oui": mac_info.get("oui") or "",
        "geo_source": geo.get("geo_source") or "",
        "rdap": rdap,
        "standards": standards,
        "updated": _now(),
        "_ts": now,
    }
    cache.setdefault("ips", {})[ip] = out
    _save_json(CACHE_PATH, cache)
    return out


def to_geojson_feature(point: dict[str, Any]) -> dict[str, Any]:
    """RFC 7946 GeoJSON feature for map layer."""
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [point.get("lon"), point.get("lat")]},
        "properties": {k: v for k, v in point.items() if k not in ("lat", "lon")},
    }


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: geo-intel-standards.py enrich <ip>", file=sys.stderr)
        return 1
    if sys.argv[1] == "enrich":
        json.dump(enrich_ip(sys.argv[2]), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())