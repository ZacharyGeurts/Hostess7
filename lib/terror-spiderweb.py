#!/usr/bin/env pythong
"""Global terror Spiderweb — identify every home and every internet endpoint everywhere."""
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
DOCTRINE = INSTALL / "data" / "terror-spiderweb-doctrine.json"
SEED_TSV = INSTALL / "data" / "home-gps-correlation.tsv"
GPS_TABLE = STATE / "home-gps-correlation.json"
UNIVERSAL_REGISTRY = STATE / "universal-field-registry.json"
PANEL_CACHE = STATE / "terror-spiderweb-panel.json"
HOST_ATTACKS = STATE / "host-attacks.json"
PANEL_JSON = STATE / "threat-panel.json"
GOV_DOSSIERS = STATE / "gov-dossiers.json"
HUMAN_DOSSIER = STATE / "human-dossier.json"
GEO_CACHE = STATE / "geo-intel-cache.json"
VECTOR_CACHE = STATE / "vector-intel-cache.json"
HOSTILE_TSV = STATE / "field-hostile.tsv"
FIREWALL_BLOCKS = STATE / "firewall-blocks.tsv"
TRUSTED_TSV = STATE / "firewall-trusted.tsv"

EDGE_COLORS = {
    "terror": "#ff3a4a",
    "neighbor": "#3dd68c",
    "pipe_up": "#4d9bff",
    "pipe_down": "#b06cff",
    "trusted": "#3dd68c",
    "hostile": "#ff3a4a",
}

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)
IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

NODE_COLORS = {
    "home": "#d4af37",
    "neighbor": "#3dd68c",
    "lan": "#7ec8a4",
    "tagged": "#c9a0dc",
    "gov": "#9fd4b8",
    "terror": "#ff3a4a",
    "internet": "#9aa8be",
    "trusted": "#3dd68c",
    "hostile": "#ff5c7a",
    "pipe": "#4d9bff",
    "cellphone": "#5ec8ff",
    "mobile": "#5ec8ff",
    "battery": "#ffb84d",
}

MOBILE_HOTSPOT_RE = re.compile(
    r"iphone|androidap|galaxy|pixel[_\s]?\d|mobile[\s_-]?hotspot|xfinitywifi|verizon|jetpack|"
    r"attwi|tmobile|samsung[\s_-]?ap|huawei[\s_-]?ap",
    re.I,
)
MOBILE_VENDOR_RE = re.compile(
    r"apple|samsung|google|motorola|xiaomi|huawei|oneplus|lg electronics|sony|nokia|oppo|vivo|"
    r"qualcomm|htc|zte|fairphone|nothing",
    re.I,
)
MOBILE_IFACE_TYPES = frozenset({"gsm", "cdma", "wwan", "lte", "5g", "bluetooth", "bt"})


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



def _deep_harvest() -> bool:
    return os.environ.get("NEXUS_SPIDERWEB_DEEP", "0").strip().lower() in ("1", "true", "yes")


def _idle_panel() -> dict[str, Any]:
    return {
        "schema": "terror-spiderweb/v2",
        "mode": "idle",
        "auto_run": False,
        "updated": None,
        "motto": "Operator-triggered only — press Rebuild web when you want a fresh survey.",
        "tagline": "No automatic probe storms. Cached sections shown when available.",
        "nodes": [],
        "edges": [],
        "focus": {"label": "Idle — awaiting operator rebuild", "lat": 20.0, "lon": 0.0, "zoom": 2},
        "registry": {"homes": [], "internet": [], "mobile": [], "batteries": [], "unplaced_internet": []},
        "stats": {"idle": True, "identified_everywhere": 0},
        "sections_diagram": _sections_diagram({}),
    }


def _section_samples(registry: dict[str, Any], key: str, *, limit: int = 3) -> list[str]:
    rows = registry.get(key) or []
    out: list[str] = []
    for row in rows[:limit]:
        if not isinstance(row, dict):
            continue
        label = row.get("label") or row.get("ip") or row.get("id") or row.get("address")
        if label:
            out.append(str(label)[:48])
    return out


def _sections_diagram(doc: dict[str, Any]) -> dict[str, Any]:
    stats = doc.get("stats") or {}
    reg = doc.get("registry") or {}
    sources = stats.get("sources") or {}
    sections: list[dict[str, Any]] = [
        {
            "id": "homes",
            "title": "Homes & neighbors",
            "total": int(stats.get("total_homes") or len(reg.get("homes") or [])),
            "placed": int(stats.get("homes_placed") or 0),
            "samples": _section_samples(reg, "homes"),
        },
        {
            "id": "internet",
            "title": "Internet catalog",
            "total": int(stats.get("total_internet") or len(reg.get("internet") or [])),
            "placed": int(stats.get("internet_placed") or 0),
            "unplaced": int(stats.get("internet_unplaced") or 0),
            "samples": _section_samples(reg, "internet"),
        },
        {
            "id": "mobile",
            "title": "Cellphones & radios",
            "total": int(stats.get("total_mobile") or len(reg.get("mobile") or [])),
            "placed": int(stats.get("mobile_placed") or 0),
            "moving": int(stats.get("mobile_moving") or 0),
            "samples": _section_samples(reg, "mobile"),
        },
        {
            "id": "batteries",
            "title": "Batteries",
            "total": int(stats.get("total_battery") or len(reg.get("batteries") or [])),
            "placed": int(stats.get("battery_placed") or 0),
            "samples": _section_samples(reg, "batteries"),
        },
        {
            "id": "edges",
            "title": "Spiderweb edges",
            "total": int(stats.get("edges") or len(doc.get("edges") or [])),
            "pipe_up": int(stats.get("pipe_up") or 0),
            "pipe_down": int(stats.get("pipe_down") or 0),
        },
        {
            "id": "terror",
            "title": "Terror / hostile",
            "total": int(stats.get("terror_nodes") or 0) + int(stats.get("hostile_nodes") or 0),
            "terror": int(stats.get("terror_nodes") or 0),
            "hostile": int(stats.get("hostile_nodes") or 0),
        },
    ]
    idle = bool(stats.get("idle"))
    h = sections[0]["placed"] if not idle else 0
    i = sections[1]["placed"] if not idle else 0
    m = sections[2]["placed"] if not idle else 0
    b = sections[3]["placed"] if not idle else 0
    e = sections[4]["total"] if not idle else 0
    t = sections[5]["terror"] if not idle else 0
    ascii_lines = [
        "┌─ HOME (" + str(h) + ") ────────────────┐",
        "│  ├─ neighbor / LAN                     │",
        "│  ├─ internet (" + str(i) + ") ── terror (" + str(t) + ")   │",
        "│  ├─ mobile (" + str(m) + ") · battery (" + str(b) + ")      │",
        "│  └─ edges (" + str(e) + ") pipe↑" + str(sections[4].get("pipe_up", 0)) + " pipe↓" + str(sections[4].get("pipe_down", 0)) + " │",
        "└────────────────────────────────────────┘",
    ]
    if idle:
        ascii_lines.insert(0, "[ idle — operator rebuild required ]")
    return {
        "schema": "terror-spiderweb-sections/v1",
        "sections": sections,
        "ascii": "\n".join(ascii_lines),
        "sources": sources,
        "idle": idle,
    }


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


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _parse_float(raw: Any) -> float | None:
    try:
        v = float(str(raw or "").strip())
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _clamp_coords(lat: float, lon: float) -> tuple[float, float] | None:
    if lat < -90 or lat > 90:
        return None
    while lon > 180:
        lon -= 360
    while lon < -180:
        lon += 360
    try:
        gp = _mod("gps_precision", "gps-precision.py")
        return float(gp.format_deg(lat)), float(gp.format_deg(lon))
    except Exception:
        return round(lat, 6), round(lon, 6)


def _precision_enrich(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("lat") is None or row.get("lon") is None:
        return row
    try:
        gp = _mod("gps_precision", "gps-precision.py")
        return gp.enrich_entity(row)
    except Exception:
        return row


def _extract_ips(text: str) -> list[str]:
    return list(dict.fromkeys(IPV4_RE.findall(str(text or ""))))


def _is_public_ip(ip: str) -> bool:
    return bool(ip) and not PRIVATE_RE.match(ip) and bool(IPV4_RE.match(ip))


def _load_merged_geo() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for path in (GEO_CACHE, VECTOR_CACHE):
        doc = _load_json(path, {"ips": {}})
        for ip, row in (doc.get("ips") or {}).items():
            if not isinstance(row, dict):
                continue
            prev = out.get(ip) or {}
            merged = {**prev, **{k: v for k, v in row.items() if v not in (None, "", [])}}
            out[ip] = merged
    return out


def _geo_for_ip(ip: str, geo_map: dict[str, dict[str, Any]], fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    g = dict(geo_map.get(ip) or {})
    if fallback:
        for key in ("lat", "lon", "city", "country", "country_code", "org", "label"):
            if g.get(key) in (None, "") and fallback.get(key) not in (None, ""):
                g[key] = fallback[key]
    return g


def _coords_from_geo(geo: dict[str, Any]) -> tuple[float, float] | None:
    lat = _parse_float(geo.get("lat"))
    lon = _parse_float(geo.get("lon"))
    if lat is None or lon is None:
        return None
    return _clamp_coords(lat, lon)


def _load_seed_homes() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not SEED_TSV.is_file():
        return rows
    try:
        lines = SEED_TSV.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return rows
    if not lines:
        return rows
    header = [h.strip() for h in lines[0].split("\t")]
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split("\t")
        row = {header[i]: (parts[i] if i < len(parts) else "") for i in range(len(header))}
        rows.append({
            "id": row.get("id") or f"home_{len(rows)}",
            "label": row.get("label") or "Home",
            "address": row.get("address") or "",
            "lat": _parse_float(row.get("lat")),
            "lon": _parse_float(row.get("lon")),
            "role": (row.get("role") or "home").strip().lower(),
            "notes": row.get("notes") or "",
            "source": "seed",
            "sources": ["seed"],
        })
    return rows


def _correlate_operator(homes: list[dict[str, Any]], op: dict[str, Any]) -> list[dict[str, Any]]:
    out = [dict(h) for h in homes]
    lat = _parse_float(op.get("lat"))
    lon = _parse_float(op.get("lon"))
    if lat is None or lon is None:
        return out
    found = False
    for h in out:
        if h.get("id") == "home_operator" or (h.get("role") == "home" and not h.get("lat")):
            h["lat"] = lat
            h["lon"] = lon
            h["address"] = h.get("address") or op.get("address") or op.get("label") or ""
            h["label"] = op.get("label") or h.get("label") or "Operator home"
            h["source"] = op.get("source") or "operator"
            h.setdefault("sources", []).append("operator")
            h["correlated"] = True
            found = True
    if not found:
        out.insert(0, {
            "id": "home_operator",
            "label": op.get("label") or "Operator home",
            "address": op.get("address") or op.get("label") or "",
            "lat": lat,
            "lon": lon,
            "role": "home",
            "notes": "Live operator GPS",
            "source": op.get("source") or "operator",
            "sources": ["operator"],
            "correlated": True,
        })
    return out


def _harvest_homes(panel_doc: dict[str, Any], op: dict[str, Any]) -> list[dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}

    def add_home(row: dict[str, Any]) -> None:
        hid = str(row.get("id") or f"home_{len(index)}")
        if hid in index:
            prev = index[hid]
            for src in row.get("sources") or [row.get("source")]:
                if src and src not in (prev.get("sources") or []):
                    prev.setdefault("sources", []).append(src)
            for k, v in row.items():
                if v not in (None, "") and k not in ("sources",):
                    if prev.get(k) in (None, ""):
                        prev[k] = v
            return
        row = dict(row)
        row["id"] = hid
        row.setdefault("sources", [row.get("source") or "unknown"])
        index[hid] = row

    for h in _correlate_operator(_load_seed_homes(), op):
        add_home(h)

    if op.get("census_geographies"):
        for i, row in enumerate(op.get("census_geographies") or []):
            if not isinstance(row, dict):
                continue
            add_home({
                "id": f"census_geo:{row.get('geoid') or i}",
                "label": row.get("name") or row.get("layer") or "Census geography",
                "address": row.get("layer") or "census",
                "lat": _parse_float(op.get("lat")),
                "lon": _parse_float(op.get("lon")),
                "role": "gov",
                "source": "census_field",
                "sources": ["census_field", "operator"],
                "census_layer": row.get("layer"),
                "geoid": row.get("geoid"),
            })

    # Program tag + gov dossier location pins
    gdoc = _load_json(GOV_DOSSIERS, {"records": {}})
    for key, rec in (gdoc.get("records") or {}).items():
        if not isinstance(rec, dict):
            continue
        for i, loc in enumerate(rec.get("locations") or []):
            if not isinstance(loc, dict):
                continue
            lat = _parse_float(loc.get("lat"))
            lon = _parse_float(loc.get("lon"))
            add_home({
                "id": f"gov_loc:{key}:{i}",
                "label": loc.get("label") or loc.get("place") or str(key),
                "address": loc.get("address") or loc.get("place") or "",
                "lat": lat,
                "lon": lon,
                "role": "tagged",
                "source": "program_tags",
                "sources": ["program_tags", "gov_dossiers"],
                "record_key": key,
            })
        for field in ("lat", "longitude", "lon"):
            pass
        geo = rec.get("geo") if isinstance(rec.get("geo"), dict) else {}
        lat = _parse_float(rec.get("lat") or geo.get("lat"))
        lon = _parse_float(rec.get("lon") or geo.get("lon"))
        if lat is not None and lon is not None:
            add_home({
                "id": f"gov_rec:{key}",
                "label": rec.get("name") or rec.get("label") or str(key),
                "address": rec.get("address") or rec.get("city") or "",
                "lat": lat,
                "lon": lon,
                "role": "gov",
                "source": "gov_dossiers",
                "sources": ["gov_dossiers"],
                "record_key": key,
            })

    # LAN neighbors at home vicinity (ARP)
    primary_lat = _parse_float(op.get("lat"))
    primary_lon = _parse_float(op.get("lon"))
    if primary_lat is not None and primary_lon is not None:
        try:
            geo_mod = _mod("geo_intel", "geo-intel-standards.py")
            arp = geo_mod.load_arp_table()
            for i, (lip, mac) in enumerate(sorted(arp.items())):
                if PRIVATE_RE.match(lip):
                    jitter = ((hash(lip) % 1000) - 500) / 80000.0
                    add_home({
                        "id": f"lan:{lip}",
                        "label": f"LAN {lip}",
                        "address": f"local network · {mac or 'mac?'}",
                        "lat": round(primary_lat + jitter, 6),
                        "lon": round(primary_lon + jitter * 1.3, 6),
                        "role": "lan",
                        "source": "arp",
                        "sources": ["arp", "operator"],
                        "mac": mac,
                        "ip": lip,
                    })
        except Exception:
            pass

    # Trusted sites as friendly "homes" when geocoded
    geo_map = _load_merged_geo()
    for row in panel_doc.get("trusted") or []:
        ip = str(row.get("ip") or row if isinstance(row, str) else "")
        if not _is_public_ip(ip):
            continue
        g = _geo_for_ip(ip, geo_map)
        coords = _coords_from_geo(g)
        if not coords:
            continue
        add_home({
            "id": f"trusted_home:{ip}",
            "label": row.get("label") if isinstance(row, dict) else f"Trusted {ip}",
            "address": g.get("city") or g.get("org") or ip,
            "lat": coords[0],
            "lon": coords[1],
            "role": "neighbor",
            "source": "trusted",
            "sources": ["trusted", "geo_cache"],
            "ip": ip,
        })

    return list(index.values())


def _add_ip(catalog: dict[str, dict[str, Any]], ip: str, source: str, meta: dict[str, Any] | None = None) -> None:
    if not _is_public_ip(ip):
        return
    row = catalog.setdefault(ip, {"ip": ip, "sources": [], "meta": {}})
    if source not in row["sources"]:
        row["sources"].append(source)
    if meta:
        row["meta"].update({k: v for k, v in meta.items() if v not in (None, "")})


def _harvest_internet_catalog(panel_doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    catalog: dict[str, dict[str, Any]] = {}

    for c in (panel_doc.get("gatekeeper") or {}).get("connections") or []:
        ip = str(c.get("remote_ip") or "")
        _add_ip(catalog, ip, "gatekeeper", {
            "process": c.get("process"),
            "verdict": c.get("verdict"),
            "traffic_direction": c.get("traffic_direction"),
            "trust_rank": c.get("trust_rank"),
        })

    for c in (panel_doc.get("internet") or {}).get("connections") or []:
        if isinstance(c, str):
            for ip in _extract_ips(c):
                _add_ip(catalog, ip, "internet_snapshot")
        elif isinstance(c, dict):
            ip = str(c.get("remote_ip") or c.get("ip") or "")
            _add_ip(catalog, ip, "internet_snapshot", c)

    ha = panel_doc.get("host_attacks") or _load_json(HOST_ATTACKS, {})
    for p in ha.get("points") or []:
        ip = str(p.get("ip") or "")
        _add_ip(catalog, ip, "host_attacks", {
            "heat": p.get("heat"),
            "verdict": p.get("verdict"),
            "lat": p.get("lat"),
            "lon": p.get("lon"),
            "city": p.get("city"),
            "country": p.get("country"),
        })

    for row in panel_doc.get("human_dossier", {}).get("ips") or _load_json(HUMAN_DOSSIER, {}).get("ips") or []:
        if isinstance(row, dict):
            ip = str(row.get("ip") or "")
            geo = row.get("geo") if isinstance(row.get("geo"), dict) else {}
            _add_ip(catalog, ip, "human_dossier", {**row, **geo})

    for t in panel_doc.get("threats") or []:
        if isinstance(t, dict):
            for ip in _extract_ips(str(t.get("detail") or "")):
                _add_ip(catalog, ip, "threats", {"vector": t.get("vector"), "severity": t.get("severity")})

    for row in panel_doc.get("trusted") or []:
        ip = str(row.get("ip") if isinstance(row, dict) else row or "")
        _add_ip(catalog, ip, "trusted")

    for row in panel_doc.get("blocked") or []:
        ip = str(row.get("ip") if isinstance(row, dict) else row or "")
        _add_ip(catalog, ip, "blocked")

    for ip, cached in _load_merged_geo().items():
        _add_ip(catalog, ip, "geo_cache", {"org": cached.get("org"), "city": cached.get("city")})

    for table_key in ("ip_intel",):
        for row in ((panel_doc.get("angel_research") or {}).get("tables") or {}).get(table_key) or []:
            if isinstance(row, dict):
                ip = str(row.get("ip") or row.get("peer") or "")
                _add_ip(catalog, ip, "angel_research", row)

    if HOSTILE_TSV.is_file():
        try:
            for line in HOSTILE_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
                parts = line.split("\t")
                if len(parts) >= 2:
                    _add_ip(catalog, parts[1].strip(), "field_hostile", {"reason": parts[4] if len(parts) > 4 else ""})
        except OSError:
            pass

    if FIREWALL_BLOCKS.is_file():
        try:
            for line in FIREWALL_BLOCKS.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
                parts = line.split("\t")
                if len(parts) >= 2:
                    _add_ip(catalog, parts[1].strip(), "firewall_blocks")
        except OSError:
            pass

    pf = panel_doc.get("packet_field") or {}
    for pkt in (pf.get("recent") or pf.get("inspect") or [])[:200]:
        if isinstance(pkt, dict):
            for ip in _extract_ips(str(pkt.get("endpoints") or pkt.get("remote") or "")):
                _add_ip(catalog, ip, "packet_field")

    return catalog


def _classify_internet(ip: str, entry: dict[str, Any], geo: dict[str, Any]) -> str:
    meta = entry.get("meta") or {}
    if "field_hostile" in entry.get("sources") or "blocked" in entry.get("sources"):
        return "hostile"
    if "trusted" in entry.get("sources"):
        return "trusted"
    try:
        heat = float(meta.get("heat") or 0)
    except (TypeError, ValueError):
        heat = 0.0
    if heat >= 0.45 or "host_attacks" in entry.get("sources") and meta.get("verdict") in (
        "HARM_CANDIDATE", "BLOCK_RECOMMENDED", "SUSPICIOUS",
    ):
        return "terror"
    if "human_dossier" in entry.get("sources"):
        return "terror"
    return "internet"


def _internet_registry(catalog: dict[str, dict[str, Any]], geo_map: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ip, entry in sorted(catalog.items()):
        geo = _geo_for_ip(ip, geo_map, entry.get("meta"))
        coords = _coords_from_geo(geo)
        if coords is None:
            coords = _coords_from_geo(entry.get("meta") or {})
        kind = _classify_internet(ip, entry, geo)
        row = {
            "id": f"inet:{ip}",
            "kind": kind,
            "ip": ip,
            "label": geo.get("label") or geo.get("hostname") or geo.get("city") or ip,
            "lat": coords[0] if coords else None,
            "lon": coords[1] if coords else None,
            "placed": coords is not None,
            "color": NODE_COLORS.get(kind, NODE_COLORS["internet"]),
            "sources": entry.get("sources") or [],
            "org": geo.get("org") or geo.get("asname") or "",
            "city": geo.get("city") or entry.get("meta", {}).get("city") or "",
            "country": geo.get("country") or geo.get("country_code") or "",
            "meta": entry.get("meta") or {},
        }
        if coords:
            row = _precision_enrich(row)
        rows.append(row)
    return rows


def _home_registry(homes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for h in homes:
        lat = _parse_float(h.get("lat"))
        lon = _parse_float(h.get("lon"))
        coords = _clamp_coords(lat, lon) if lat is not None and lon is not None else None
        role = h.get("role") or "home"
        kind = "home" if role == "home" else ("neighbor" if role in ("neighbor", "lan") else role)
        row = {
            **h,
            "kind": kind,
            "placed": coords is not None,
            "lat": coords[0] if coords else None,
            "lon": coords[1] if coords else None,
            "color": NODE_COLORS.get(kind, NODE_COLORS["home"]),
            "pushpin": True,
        }
        if coords:
            row = _precision_enrich(row)
        rows.append(row)
    return rows


def _load_oui_table() -> dict[str, dict[str, str]]:
    try:
        geo_mod = _mod("geo_intel", "geo-intel-standards.py")
        return geo_mod.load_oui_table()
    except Exception:
        return {}


def _vendor_for_mac(mac: str, oui_db: dict[str, dict[str, str]]) -> str:
    if not mac:
        return ""
    try:
        geo_mod = _mod("geo_intel", "geo-intel-standards.py")
        hit = geo_mod.lookup_mac_ieee_oui(mac, oui_db)
        return str(hit.get("vendor") or "")
    except Exception:
        prefix = ":".join(mac.upper().replace("-", ":").split(":")[:3])
        return (oui_db.get(prefix) or {}).get("vendor") or ""


def _is_mobile_vendor(vendor: str) -> bool:
    return bool(vendor and MOBILE_VENDOR_RE.search(vendor))


def _jitter_near(lat: float, lon: float, seed: str, *, scale: float = 80000.0) -> tuple[float, float]:
    h = hash(seed) % 10000
    jitter_lat = ((h % 1000) - 500) / scale
    jitter_lon = (((h // 1000) % 1000) - 500) / (scale * 0.77)
    coords = _clamp_coords(lat + jitter_lat, lon + jitter_lon)
    return coords if coords else (lat, lon)


def _offset_from_signal(lat: float, lon: float, signal: Any, seed: str) -> tuple[float, float]:
    try:
        s = int(signal or 0)
    except (TypeError, ValueError):
        s = 0
    reach_km = max(0.05, min(8.0, (100 - max(0, min(100, s))) / 18.0))
    angle = (hash(seed) % 360) * math.pi / 180.0
    dlat = reach_km / 111.0 * math.cos(angle)
    dlon = reach_km / (111.0 * max(0.3, abs(math.cos(math.radians(lat))))) * math.sin(angle)
    coords = _clamp_coords(lat + dlat, lon + dlon)
    return coords if coords else (lat, lon)


def _primary_coords(op: dict[str, Any], home_rows: list[dict[str, Any]]) -> tuple[float, float] | None:
    lat = _parse_float(op.get("lat"))
    lon = _parse_float(op.get("lon"))
    if lat is not None and lon is not None:
        return _clamp_coords(lat, lon)
    for h in home_rows:
        if h.get("placed"):
            return float(h["lat"]), float(h["lon"])
    return None


def _harvest_batteries(op: dict[str, Any], primary: tuple[float, float] | None) -> list[dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    psys = Path("/sys/class/power_supply")

    def add_battery(row: dict[str, Any]) -> None:
        bid = str(row.get("id") or f"battery_{len(index)}")
        if bid in index:
            prev = index[bid]
            for src in row.get("sources") or [row.get("source")]:
                if src and src not in (prev.get("sources") or []):
                    prev.setdefault("sources", []).append(src)
            return
        row = dict(row)
        row["id"] = bid
        row.setdefault("sources", [row.get("source") or "unknown"])
        index[bid] = row

    if psys.is_dir():
        for entry in sorted(psys.iterdir()):
            if not entry.is_dir():
                continue
            try:
                bat_type = (entry / "type").read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                continue
            if bat_type.lower() not in ("battery", "ups"):
                continue
            name = entry.name
            meta: dict[str, Any] = {"type": bat_type, "path": str(entry)}
            for key, fname in (
                ("capacity_pct", "capacity"),
                ("status", "status"),
                ("present", "present"),
                ("manufacturer", "manufacturer"),
                ("model_name", "model_name"),
                ("technology", "technology"),
            ):
                fpath = entry / fname
                if fpath.is_file():
                    try:
                        meta[key] = fpath.read_text(encoding="utf-8", errors="replace").strip()
                    except OSError:
                        pass
            try:
                meta["capacity_pct"] = int(meta.get("capacity_pct") or 0)
            except (TypeError, ValueError):
                meta["capacity_pct"] = None
            placed = primary is not None
            lat = lon = None
            if primary:
                lat, lon = _jitter_near(primary[0], primary[1], f"bat:{name}")
            moving = name.lower() not in ("bat0", "battery0", "acpi") and bat_type.lower() == "battery"
            add_battery({
                "id": f"battery:{name}",
                "label": meta.get("model_name") or meta.get("manufacturer") or f"Battery {name}",
                "kind": "battery",
                "role": "battery",
                "source": "power_supply",
                "sources": ["power_supply", "sysfs"],
                "device": name,
                "capacity_pct": meta.get("capacity_pct"),
                "status": meta.get("status") or "",
                "moving": moving,
                "placed": placed,
                "lat": lat,
                "lon": lon,
                "color": NODE_COLORS["battery"],
                "meta": meta,
            })

    if not index and primary:
        add_battery({
            "id": "battery:operator_field",
            "label": "Field power reserve",
            "kind": "battery",
            "role": "battery",
            "source": "operator_field",
            "sources": ["operator_field"],
            "capacity_pct": None,
            "status": "unknown",
            "moving": True,
            "placed": True,
            "lat": primary[0],
            "lon": primary[1],
            "color": NODE_COLORS["battery"],
        })

    return list(index.values())


def _harvest_mobile_devices(
    panel_doc: dict[str, Any],
    op: dict[str, Any],
    primary: tuple[float, float] | None,
) -> list[dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    oui_db = _load_oui_table()

    def add_mobile(row: dict[str, Any]) -> None:
        mid = str(row.get("id") or f"mobile_{len(index)}")
        if mid in index:
            prev = index[mid]
            for src in row.get("sources") or [row.get("source")]:
                if src and src not in (prev.get("sources") or []):
                    prev.setdefault("sources", []).append(src)
            for k, v in row.items():
                if v not in (None, "") and k not in ("sources",):
                    if prev.get(k) in (None, ""):
                        prev[k] = v
            return
        row = dict(row)
        row["id"] = mid
        row.setdefault("kind", "cellphone")
        row.setdefault("sources", [row.get("source") or "unknown"])
        row.setdefault("moving", True)
        row.setdefault("color", NODE_COLORS["cellphone"])
        index[mid] = row

    op_lat = _parse_float(op.get("lat"))
    op_lon = _parse_float(op.get("lon"))
    if op_lat is not None and op_lon is not None:
        coords = _clamp_coords(op_lat, op_lon)
        if coords:
            add_mobile({
                "id": "mobile:operator",
                "label": op.get("label") or "Operator cellphone",
                "address": op.get("address") or op.get("label") or "",
                "kind": "cellphone",
                "role": "operator",
                "source": "operator_gps",
                "sources": ["operator_gps", "operator"],
                "moving": True,
                "placed": True,
                "lat": coords[0],
                "lon": coords[1],
                "mac": op.get("mac") or "",
                "signal": op.get("signal"),
            })

    fr = panel_doc.get("field_rf") or {}
    for iface in fr.get("interfaces") or []:
        if not isinstance(iface, dict):
            continue
        itype = str(iface.get("type") or "").lower()
        dev = str(iface.get("device") or "")
        if not dev:
            continue
        if itype in MOBILE_IFACE_TYPES or itype in ("wifi", "wifi-p2p"):
            is_cell = itype in MOBILE_IFACE_TYPES
            placed = primary is not None
            lat = lon = None
            if primary:
                lat, lon = _jitter_near(primary[0], primary[1], f"iface:{dev}", scale=60000.0)
            add_mobile({
                "id": f"mobile:iface:{dev}",
                "label": f"{itype.upper()} {dev}" if is_cell else f"Radio {dev}",
                "kind": "cellphone" if is_cell else "mobile",
                "role": itype,
                "source": "field_rf_iface",
                "sources": ["field_rf_iface", "field_rf"],
                "device": dev,
                "state": iface.get("state") or "",
                "connection": iface.get("connection") or "",
                "moving": is_cell or "connected" in str(iface.get("state") or "").lower(),
                "placed": placed,
                "lat": lat,
                "lon": lon,
            })

    active = (fr.get("antenna") or {}).get("active_connection") or {}
    if active:
        bssid = str(active.get("bssid") or "")
        vendor = _vendor_for_mac(bssid, oui_db)
        placed = primary is not None
        lat = lon = None
        if primary:
            lat, lon = _offset_from_signal(primary[0], primary[1], active.get("signal_dbm"), bssid or active.get("ssid") or "active")
        add_mobile({
            "id": f"mobile:active:{bssid or active.get('ssid') or 'wifi'}",
            "label": active.get("ssid") or "Active Wi‑Fi link",
            "kind": "cellphone" if _is_mobile_vendor(vendor) else "mobile",
            "role": "wifi_active",
            "source": "field_rf_active",
            "sources": ["field_rf_active", "field_rf"],
            "bssid": bssid,
            "mac": bssid,
            "vendor": vendor,
            "signal": active.get("signal_dbm"),
            "moving": True,
            "placed": placed,
            "lat": lat,
            "lon": lon,
        })

    scans: list[dict[str, Any]] = []
    hist_scans = _load_json(STATE / "field-rf-history.json", {}).get("scans") or {}
    if isinstance(hist_scans, dict):
        for dev_scan in hist_scans.values():
            if isinstance(dev_scan, list):
                scans.extend(dev_scan)
    antenna = fr.get("antenna") or {}
    for field in antenna.get("antenna_fields") or []:
        for ap in field.get("scan_sample") or []:
            if isinstance(ap, dict):
                scans.append(ap)
    seen_bssids: set[str] = set()
    for ap in scans:
        if not isinstance(ap, dict):
            continue
        bssid = str(ap.get("bssid") or "")
        bnorm = bssid.upper().replace("-", ":")
        if not bnorm or bnorm in seen_bssids:
            continue
        ssid = str(ap.get("ssid") or "")
        vendor = ap.get("bssid_oui") or _vendor_for_mac(bssid, oui_db)
        if isinstance(vendor, dict):
            vendor = vendor.get("vendor") or ""
        is_hotspot = bool(MOBILE_HOTSPOT_RE.search(ssid) or _is_mobile_vendor(str(vendor)))
        if not is_hotspot:
            continue
        seen_bssids.add(bnorm)
        placed = primary is not None
        lat = lon = None
        if primary:
            lat, lon = _offset_from_signal(primary[0], primary[1], ap.get("signal_dbm"), bnorm)
        add_mobile({
            "id": f"mobile:ap:{bnorm}",
            "label": ssid or f"Mobile AP {bnorm[:8]}",
            "kind": "cellphone",
            "role": "mobile_hotspot",
            "source": "field_rf_scan",
            "sources": ["field_rf_scan", "field_rf"],
            "bssid": bssid,
            "mac": bssid,
            "vendor": str(vendor),
            "signal": ap.get("signal_dbm"),
            "ssid": ssid,
            "moving": True,
            "placed": placed,
            "lat": lat,
            "lon": lon,
        })

    if primary:
        try:
            geo_mod = _mod("geo_intel", "geo-intel-standards.py")
            for lip, mac in sorted(geo_mod.load_arp_table().items()):
                if not PRIVATE_RE.match(lip):
                    continue
                vendor = _vendor_for_mac(mac, oui_db)
                if not _is_mobile_vendor(vendor):
                    continue
                lat, lon = _jitter_near(primary[0], primary[1], f"arp:{lip}", scale=90000.0)
                add_mobile({
                    "id": f"mobile:lan:{lip}",
                    "label": f"LAN mobile {lip}",
                    "kind": "cellphone",
                    "role": "lan_mobile",
                    "source": "arp",
                    "sources": ["arp", "oui"],
                    "ip": lip,
                    "mac": mac,
                    "vendor": vendor,
                    "moving": True,
                    "placed": True,
                    "lat": lat,
                    "lon": lon,
                })
        except Exception:
            pass

    us_net = (panel_doc.get("us_field") or {}).get("network") or {}
    for row in us_net.get("arp_neighbors") or []:
        line = str(row.get("line") or row if isinstance(row, str) else "")
        ips = _extract_ips(line)
        mac_m = re.search(r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})", line)
        mac = mac_m.group(1) if mac_m else ""
        vendor = _vendor_for_mac(mac, oui_db)
        if not ips and not mac:
            continue
        if mac and not _is_mobile_vendor(vendor):
            continue
        lip = ips[0] if ips else ""
        placed = primary is not None
        lat = lon = None
        if primary:
            lat, lon = _jitter_near(primary[0], primary[1], f"us:{lip or mac}", scale=85000.0)
        add_mobile({
            "id": f"mobile:us:{lip or mac or len(index)}",
            "label": vendor or f"Neighbor {lip or mac}",
            "kind": "cellphone",
            "role": "us_arp",
            "source": "us_field",
            "sources": ["us_field", "arp"],
            "ip": lip,
            "mac": mac,
            "vendor": vendor,
            "moving": True,
            "placed": placed,
            "lat": lat,
            "lon": lon,
        })

    for row in fr.get("rfkill") or []:
        if not isinstance(row, dict):
            continue
        rtype = str(row.get("type") or "").lower()
        if rtype not in ("bluetooth", "wlan"):
            continue
        dev = str(row.get("name") or row.get("device") or rtype)
        placed = primary is not None
        lat = lon = None
        if primary:
            lat, lon = _jitter_near(primary[0], primary[1], f"rfkill:{dev}", scale=70000.0)
        add_mobile({
            "id": f"mobile:rfkill:{dev}",
            "label": f"{rtype.upper()} radio {dev}",
            "kind": "mobile",
            "role": rtype,
            "source": "rfkill",
            "sources": ["rfkill", "field_rf"],
            "device": dev,
            "soft": row.get("soft"),
            "hard": row.get("hard"),
            "moving": rtype == "bluetooth",
            "placed": placed,
            "lat": lat,
            "lon": lon,
        })

    return list(index.values())


def build_gps_table(op: dict[str, Any] | None = None) -> dict[str, Any]:
    op = op if isinstance(op, dict) else {}
    if not op:
        try:
            op = _mod("operator_location", "operator-location.py").panel_json()
        except Exception:
            op = {}
    homes = _harvest_homes({}, op)
    doc = {
        "updated": _now(),
        "schema": "home-gps-correlation/v2",
        "operator": op,
        "homes": homes,
        "count": len(homes),
        "with_coords": sum(1 for h in homes if h.get("lat") is not None),
    }
    _save_json(GPS_TABLE, doc)
    return doc


def _panel_doc() -> dict[str, Any]:
    if PANEL_JSON.is_file():
        doc = _load_json(PANEL_JSON, {})
        if isinstance(doc, dict) and doc.get("updated"):
            return doc
    return {}


def _find_hottest_cluster(nodes: list[dict[str, Any]], *, grid: float = 8.0) -> dict[str, Any]:
    buckets: dict[str, dict[str, Any]] = {}
    for n in nodes:
        if n.get("kind") not in ("terror", "hostile"):
            continue
        if n.get("lat") is None:
            continue
        lat = float(n["lat"])
        lon = float(n["lon"])
        key = f"{round(lat * grid) / grid:.2f},{round(lon * grid) / grid:.2f}"
        b = buckets.setdefault(key, {"heat": 0.0, "lats": [], "lons": [], "count": 0})
        h = float(n.get("heat") or n.get("meta", {}).get("heat") or 0.7)
        b["heat"] += h
        b["lats"].append(lat)
        b["lons"].append(lon)
        b["count"] += 1
    if not buckets:
        return {"lat": 20.0, "lon": 0.0, "zoom": 2, "heat_sum": 0.0, "label": "World view — surveying everywhere"}
    best = max(buckets.values(), key=lambda x: x["heat"])
    lat = sum(best["lats"]) / len(best["lats"])
    lon = sum(best["lons"]) / len(best["lons"])
    zoom = 4 if best["count"] < 3 else (6 if best["heat"] < 2 else 8)
    return {
        "lat": round(lat, 5),
        "lon": round(lon, 5),
        "zoom": zoom,
        "heat_sum": round(best["heat"], 3),
        "node_count": best["count"],
        "label": f"Hottest red cluster — heat {best['heat']:.2f} · {best['count']} endpoint(s)",
    }


def build_spiderweb(panel_doc: dict[str, Any] | None = None) -> dict[str, Any]:
    panel_doc = panel_doc if isinstance(panel_doc, dict) else _panel_doc()
    deep = _deep_harvest()
    census_doc: dict[str, Any] = {}
    if deep:
        try:
            census_mod = _mod("census_field_populate", "census-field-populate.py")
            census_doc = census_mod.populate_from_operator()
        except Exception:
            pass
    op = panel_doc.get("operator_location") or {}
    if deep:
        try:
            live_op = _mod("operator_location", "operator-location.py").panel_json()
            if live_op.get("gps_ready"):
                op = {**live_op, **op}
        except Exception:
            pass
    if not op:
        op = _load_json(STATE / "operator-location.json", {})

    gps_doc = build_gps_table(op)
    home_rows = _home_registry(_harvest_homes(panel_doc, op))
    catalog = _harvest_internet_catalog(panel_doc)
    geo_map = _load_merged_geo()
    internet_rows = _internet_registry(catalog, geo_map)
    try:
        hp = _mod("hostility_priority", "hostility-priority.py")
        internet_rows = [hp.enrich_internet_node(r) for r in internet_rows]
        internet_rows = hp.sort_hell_first(internet_rows)
    except Exception:
        pass
    primary_coords = _primary_coords(op, home_rows)
    mobile_rows = _harvest_mobile_devices(panel_doc, op, primary_coords)
    try:
        st = _mod("safe_signal_touch", "safe-signal-touch.py")
        for row in mobile_rows:
            hostile = row.get("kind") in ("terror", "hostile") or "field_hostile" in (row.get("sources") or [])
            row.update(st.field_entity_touch(
                kind=str(row.get("kind") or "mobile"),
                role=str(row.get("role") or ""),
                label=str(row.get("label") or ""),
                moving=bool(row.get("moving")),
                hostile=hostile,
            ))
    except Exception:
        pass
    battery_rows = _harvest_batteries(op, primary_coords)

    primary = next((h for h in home_rows if h.get("role") == "home" and h.get("placed")), None)
    if not primary:
        primary = next((h for h in home_rows if h.get("placed")), None)

    node_index: dict[str, dict[str, Any]] = {}
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []

    for h in home_rows:
        if not h.get("placed"):
            continue
        nodes.append(h)
        node_index[h["id"]] = h

    for inet in internet_rows:
        if not inet.get("placed"):
            continue
        n = {k: v for k, v in inet.items() if k != "meta"}
        n["heat"] = float((inet.get("meta") or {}).get("heat") or (0.8 if inet["kind"] == "terror" else 0.0))
        nodes.append(n)
        node_index[n["id"]] = n

    for mob in mobile_rows:
        if not mob.get("placed"):
            continue
        n = {k: v for k, v in mob.items() if k != "meta"}
        n.setdefault("pushpin", False)
        nodes.append(n)
        node_index[n["id"]] = n

    for bat in battery_rows:
        if not bat.get("placed"):
            continue
        n = {k: v for k, v in bat.items() if k != "meta"}
        n.setdefault("pushpin", False)
        nodes.append(n)
        node_index[n["id"]] = n

    if primary:
        for nh in home_rows:
            if nh.get("role") in ("neighbor", "lan", "tagged", "gov") and nh.get("placed") and nh["id"] in node_index:
                edges.append({
                    "id": f"e-neighbor-{nh['id']}",
                    "from": primary["id"],
                    "to": nh["id"],
                    "kind": "neighbor",
                    "color": EDGE_COLORS["neighbor"],
                    "weight": 2.0,
                })

        for inet in internet_rows:
            if not inet.get("placed") or inet["id"] not in node_index:
                continue
            kind = inet["kind"]
            if kind in ("terror", "hostile"):
                edges.append({
                    "id": f"e-terror-{inet['ip']}",
                    "from": primary["id"],
                    "to": inet["id"],
                    "kind": "terror",
                    "color": EDGE_COLORS["terror"],
                    "weight": max(1.0, float((inet.get("meta") or {}).get("heat") or 0.6) * 3),
                })
            elif kind == "trusted":
                edges.append({
                    "id": f"e-trusted-{inet['ip']}",
                    "from": primary["id"],
                    "to": inet["id"],
                    "kind": "neighbor",
                    "color": EDGE_COLORS["trusted"],
                    "weight": 1.2,
                })

        for c in (panel_doc.get("gatekeeper") or {}).get("connections") or []:
            ip = str(c.get("remote_ip") or "")
            nid = f"inet:{ip}"
            if not _is_public_ip(ip) or nid not in node_index:
                continue
            direction = str(c.get("traffic_direction") or "from_us")
            if direction == "at_us":
                edges.append({
                    "id": f"e-pipe-down-{ip}",
                    "from": nid,
                    "to": primary["id"],
                    "kind": "pipe_down",
                    "color": EDGE_COLORS["pipe_down"],
                    "weight": 1.5,
                    "process": c.get("process"),
                })
            else:
                edges.append({
                    "id": f"e-pipe-up-{ip}",
                    "from": primary["id"],
                    "to": nid,
                    "kind": "pipe_up",
                    "color": EDGE_COLORS["pipe_up"],
                    "weight": 1.5,
                    "process": c.get("process"),
                })

    focus = _find_hottest_cluster(nodes)
    if primary and focus.get("heat_sum", 0) <= 0:
        focus = {
            "lat": primary["lat"],
            "lon": primary["lon"],
            "zoom": 6,
            "heat_sum": 0.0,
            "label": f"Home focus — {primary.get('label') or 'operator'}",
            "node_count": 0,
        }

    placed_homes = [h for h in home_rows if h.get("placed")]
    placed_inet = [i for i in internet_rows if i.get("placed")]
    unplaced_inet = [i for i in internet_rows if not i.get("placed")]
    placed_mobile = [m for m in mobile_rows if m.get("placed")]
    placed_battery = [b for b in battery_rows if b.get("placed")]
    moving_mobile = [m for m in mobile_rows if m.get("moving")]

    mobile_focus = {
        "lat": primary_coords[0] if primary_coords else (placed_mobile[0]["lat"] if placed_mobile else 20.0),
        "lon": primary_coords[1] if primary_coords else (placed_mobile[0]["lon"] if placed_mobile else 0.0),
        "zoom": 14 if primary_coords else (10 if placed_mobile else 2),
        "label": "Mobile & battery field — operator vicinity",
        "moving_count": len(moving_mobile),
    }

    hostility_doc: dict[str, Any] = {}
    try:
        hostility_doc = _mod("hostility_priority", "hostility-priority.py").aggregate_field_hostility(panel_doc)
    except Exception:
        pass

    thermal_doc: dict[str, Any] = {}
    if deep:
        try:
            thermal_mod = _mod("thermal_earth_field", "thermal-earth-field.py")
            thermal_doc = thermal_mod.build_thermal_field()
            op_loc = _load_json(STATE / "operator-location.json", {})
            if op_loc.get("lat") is not None:
                thermal_doc["operator_focus"] = {
                    "lat": op_loc.get("lat"),
                    "lon": op_loc.get("lon"),
                    "label": op_loc.get("label") or "Operator",
                }
        except Exception:
            pass
    else:
        thermal_doc = _load_json(STATE / "thermal-earth-field.json", {})

    stats = {
        "total_homes": len(home_rows),
        "homes_placed": len(placed_homes),
        "total_internet": len(internet_rows),
        "internet_placed": len(placed_inet),
        "internet_unplaced": len(unplaced_inet),
        "total_mobile": len(mobile_rows),
        "mobile_placed": len(placed_mobile),
        "mobile_moving": len(moving_mobile),
        "total_battery": len(battery_rows),
        "battery_placed": len(placed_battery),
        "identified_everywhere": (
            len(placed_homes) + len(placed_inet) + len(placed_mobile) + len(placed_battery)
        ),
        "catalog_ips": len(catalog),
        "terror_nodes": sum(1 for i in internet_rows if i["kind"] == "terror"),
        "hostile_nodes": sum(1 for i in internet_rows if i["kind"] == "hostile"),
        "trusted_nodes": sum(1 for i in internet_rows if i["kind"] == "trusted"),
        "edges": len(edges),
        "pipe_up": sum(1 for e in edges if e.get("kind") == "pipe_up"),
        "pipe_down": sum(1 for e in edges if e.get("kind") == "pipe_down"),
        "gps_correlated": gps_doc.get("with_coords", 0),
        "hostility_priority": "hell_first",
        "field_hostility_score": hostility_doc.get("field_hostility_score", 0),
        "census_geographies": len((op.get("census_geographies") or [])),
        "census_populated": bool(census_doc.get("ok")),
        "thermal_warm_bodies": (thermal_doc.get("stats") or {}).get("warm_bodies", 0),
        "thermal_cold_bodies": (thermal_doc.get("stats") or {}).get("cold_bodies", 0),
        "sources": {
            "gatekeeper": sum(1 for e in catalog.values() if "gatekeeper" in e.get("sources", [])),
            "host_attacks": sum(1 for e in catalog.values() if "host_attacks" in e.get("sources", [])),
            "human_dossier": sum(1 for e in catalog.values() if "human_dossier" in e.get("sources", [])),
            "geo_cache": sum(1 for e in catalog.values() if "geo_cache" in e.get("sources", [])),
            "threats": sum(1 for e in catalog.values() if "threats" in e.get("sources", [])),
            "field_rf": sum(1 for m in mobile_rows if "field_rf" in (m.get("sources") or [])),
            "power_supply": sum(1 for b in battery_rows if "power_supply" in (b.get("sources") or [])),
        },
    }

    registry_doc = {
        "updated": _now(),
        "schema": "universal-field-registry/v2",
        "homes": home_rows,
        "internet": internet_rows,
        "mobile": mobile_rows,
        "batteries": battery_rows,
        "stats": stats,
    }
    _save_json(UNIVERSAL_REGISTRY, registry_doc)

    precision_doc: dict[str, Any] = {}
    if deep:
        try:
            precision_doc = _mod("precision_field", "precision-field.py").build_precision_field()
            stats["precision_placed"] = (precision_doc.get("stats") or {}).get("placed", 0)
            stats["precision_sub_micron"] = (precision_doc.get("stats") or {}).get("sub_micron", 0)
        except Exception:
            pass
    else:
        precision_doc = _load_json(STATE / "precision-field-panel.json", {})

    existence_doc: dict[str, Any] = {}
    if deep:
        try:
            ex_mod = _mod("existence_identity", "existence-identity.py")
            existence_doc = ex_mod.build_existence_registry(registry_doc)
            stats["existence_total"] = (existence_doc.get("stats") or {}).get("total", 0)
            stats["existence_existing"] = (existence_doc.get("stats") or {}).get("existing", 0)
            stats["existence_vision"] = (existence_doc.get("stats") or {}).get("vision_corroborated", 0)
            stats["existence_ocr"] = (existence_doc.get("stats") or {}).get("ocr_corroborated", 0)
        except Exception:
            pass

    out = {
        "schema": "terror-spiderweb/v2",
        "updated": _now(),
        "motto": "Every home. Every internet endpoint. Every moving cellphone & battery. Everywhere identified.",
        "tagline": "Universal field registry — homes, internet catalog, mobile radios, and batteries on three live maps.",
        "focus": focus,
        "mobile_focus": mobile_focus,
        "nodes": nodes,
        "edges": edges,
        "homes": placed_homes,
        "registry": {
            "homes": home_rows,
            "internet": internet_rows,
            "mobile": mobile_rows,
            "batteries": battery_rows,
            "unplaced_internet": unplaced_inet[:120],
        },
        "gps_table": gps_doc,
        "legend": {
            "terror": {"label": "Terror / hot threat", "color": EDGE_COLORS["terror"]},
            "neighbor": {"label": "Neighbor / LAN / trusted", "color": EDGE_COLORS["neighbor"]},
            "pipe_up": {"label": "Pipe up (outbound)", "color": EDGE_COLORS["pipe_up"]},
            "pipe_down": {"label": "Pipe down (inbound)", "color": EDGE_COLORS["pipe_down"]},
            "home_pin": {"label": "Home pushpin", "color": NODE_COLORS["home"]},
            "internet": {"label": "Internet everywhere", "color": NODE_COLORS["internet"]},
            "cellphone": {"label": "Moving cellphone / hotspot", "color": NODE_COLORS["cellphone"]},
            "battery": {"label": "Battery anywhere", "color": NODE_COLORS["battery"]},
        },
        "stats": stats,
        "existence_identity": {
            "stats": existence_doc.get("stats") or {},
            "table": (existence_doc.get("table") or [])[:240],
            "toolkit": existence_doc.get("toolkit") or {},
            "updated": existence_doc.get("updated"),
        } if existence_doc else {},
        "hostility": hostility_doc,
        "census_field": census_doc if census_doc.get("ok") else panel_doc.get("census_field") or {},
        "thermal_earth": thermal_doc,
        "precision_field": precision_doc,
        "tempered": not deep,
        "auto_run": False,
    }
    out["sections_diagram"] = _sections_diagram(out)
    return out


def panel_json(*, force: bool = False) -> dict[str, Any]:
    """Cache-only read — never rebuild on json probe (stops probe storms)."""
    if PANEL_CACHE.is_file():
        doc = _load_json(PANEL_CACHE, {})
        if isinstance(doc, dict) and doc.get("schema"):
            if "sections_diagram" not in doc:
                doc = {**doc, "sections_diagram": _sections_diagram(doc)}
            doc.setdefault("auto_run", False)
            doc.setdefault("_probe", {"cached": True})
            return doc
    if force:
        doc = build_spiderweb()
        _save_json(PANEL_CACHE, doc)
        return doc
    idle = _idle_panel()
    idle["_probe"] = {"cached": False, "idle": True}
    return idle


def _cached_gps_table() -> dict[str, Any]:
    if GPS_TABLE.is_file():
        doc = _load_json(GPS_TABLE, {})
        if isinstance(doc, dict) and doc.get("schema"):
            return doc
    panel = panel_json()
    gps = panel.get("gps_table")
    if isinstance(gps, dict) and gps.get("schema"):
        return gps
    return {"schema": "home-gps-correlation/v2", "homes": [], "count": 0, "with_coords": 0, "idle": True}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        doc = build_spiderweb()
        _save_json(PANEL_CACHE, doc)
        print(json.dumps(doc, ensure_ascii=False))
        return 0
    if cmd == "gps-table":
        if _deep_harvest():
            print(json.dumps(build_gps_table(), ensure_ascii=False))
        else:
            print(json.dumps(_cached_gps_table(), ensure_ascii=False))
        return 0
    if cmd == "registry":
        doc = panel_json()
        print(json.dumps(doc.get("registry") or {}, ensure_ascii=False))
        return 0
    if cmd == "sections":
        doc = panel_json()
        print(json.dumps(doc.get("sections_diagram") or _sections_diagram(doc), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: terror-spiderweb.py [json|build|gps-table|registry|sections]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())