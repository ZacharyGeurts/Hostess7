#!/usr/bin/env pythong
"""Operator location — GPS, address geocode, wireless-fast egress geo."""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
LOC_FILE = STATE / "operator-location.json"


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



def _seed_from_default() -> dict[str, Any] | None:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "operator_default", INSTALL / "lib" / "operator-default.py",
        )
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        doc = mod.seed_operator_location()
        return doc if doc.get("lat") is not None else None
    except Exception:
        return None


def _load() -> dict[str, Any]:
    if LOC_FILE.is_file():
        try:
            doc = json.loads(LOC_FILE.read_text(encoding="utf-8"))
            lat, lon = doc.get("lat"), doc.get("lon")
            if lat is not None and lon is not None and not (float(lat) == 0.0 and float(lon) == 0.0):
                return doc
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass
    seeded = _seed_from_default()
    if seeded:
        return seeded
    return {
        "lat": None,
        "lon": None,
        "label": "",
        "source": "unset",
        "updated": None,
        "wireless": False,
    }


def _save(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = LOC_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(LOC_FILE)


def _default_route_iface() -> str:
    try:
        out = subprocess.check_output(["ip", "-4", "route", "show", "default"], text=True, timeout=3)
        m = re.search(r"dev\s+(\S+)", out)
        return m.group(1) if m else ""
    except (subprocess.SubprocessError, OSError):
        return ""


def _is_wireless(iface: str) -> bool:
    if not iface:
        return False
    if iface.startswith(("wlan", "wlp", "wl")):
        return True
    path = Path(f"/sys/class/net/{iface}/wireless")
    return path.is_dir()


def _fetch_egress_geo() -> dict[str, Any] | None:
    req = urllib.request.Request(
        "http://ip-api.com/json/?fields=status,lat,lon,city,regionName,country,query",
        headers={"User-Agent": "NEXUS-Shield-Operator-Geo"},
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None
    if data.get("status") != "success":
        return None
    return data


def _geocode_address(address: str) -> dict[str, Any] | None:
    q = urllib.parse.quote(address.strip())
    if not q:
        return None
    url = f"https://nominatim.openstreetmap.org/search?format=json&limit=1&q={q}"
    req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Shield/4.2"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            rows = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError):
        return None
    if not rows:
        return None
    row = rows[0]
    return {
        "lat": float(row["lat"]),
        "lon": float(row["lon"]),
        "label": row.get("display_name", address)[:200],
    }


def set_gps(lat: float, lon: float, label: str = "") -> dict[str, Any]:
    doc = _load()
    doc.update({
        "lat": round(float(lat), 6),
        "lon": round(float(lon), 6),
        "label": label or f"{lat:.5f}°, {lon:.5f}°",
        "source": "gps",
        "wireless": _is_wireless(_default_route_iface()),
    })
    _save(doc)
    return {"ok": True, **doc}


def _geocode_chain(address: str) -> dict[str, Any] | None:
    """Census geocoder + Nominatim + census geography lookup."""
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "census_field_populate", INSTALL / "lib" / "census-field-populate.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        hit = mod.geocode_address(address)
        if hit.get("ok"):
            return hit
    except Exception:
        pass
    geo = _geocode_address(address)
    if not geo:
        return None
    return {**geo, "source": "address", "ok": True}


def set_address(address: str) -> dict[str, Any]:
    geo = _geocode_chain(address)
    if not geo:
        return {"ok": False, "error": "geocode_failed", "address": address}
    doc = _load()
    doc.update({
        "lat": geo["lat"],
        "lon": geo["lon"],
        "label": geo.get("label") or address,
        "source": geo.get("source") or "address",
        "address": address,
        "wireless": _is_wireless(_default_route_iface()),
    })
    if geo.get("census_geographies") or geo.get("geographies"):
        flat = geo.get("census_geographies")
        if not flat and geo.get("geographies"):
            try:
                import importlib.util

                spec = importlib.util.spec_from_file_location(
                    "census_field_populate", INSTALL / "lib" / "census-field-populate.py",
                )
                mod = importlib.util.module_from_spec(spec)
                assert spec and spec.loader
                spec.loader.exec_module(mod)
                flat = mod._flatten_geographies(geo["geographies"])
            except Exception:
                flat = []
        if flat:
            doc["census_geographies"] = flat
    if geo.get("acs"):
        doc["census_acs"] = geo["acs"]
    if geo.get("country_code"):
        doc["country_code"] = geo["country_code"]
    _save(doc)
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "census_field_populate", INSTALL / "lib" / "census-field-populate.py",
        )
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        mod.populate_from_operator(address=address, force=True)
    except Exception:
        pass
    return {"ok": True, **doc}


def wireless_immediate() -> dict[str, Any]:
    iface = _default_route_iface()
    wireless = _is_wireless(iface)
    geo = _fetch_egress_geo()
    if not geo:
        return {"ok": False, "error": "egress_geo_failed", "wireless": wireless, "iface": iface}
    label = ", ".join(
        x for x in (geo.get("city"), geo.get("regionName"), geo.get("country")) if x
    ) or geo.get("query", "")
    doc = _load()
    doc.update({
        "lat": float(geo["lat"]),
        "lon": float(geo["lon"]),
        "label": label,
        "source": "wireless_egress" if wireless else "egress_geo",
        "wireless": wireless,
        "iface": iface,
        "egress_ip": geo.get("query"),
    })
    _save(doc)
    return {"ok": True, **doc}


def panel_json() -> dict[str, Any]:
    doc = _load()
    iface = _default_route_iface()
    profile: dict[str, Any] = {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "operator_default", INSTALL / "lib" / "operator-default.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            profile = mod.panel_operator()
    except Exception:
        profile = {}
    return {
        "lat": doc.get("lat"),
        "lon": doc.get("lon"),
        "label": doc.get("label") or profile.get("label") or "",
        "source": doc.get("source") or "unset",
        "updated": doc.get("updated"),
        "address": doc.get("address") or profile.get("address") or "",
        "display_name": doc.get("display_name") or profile.get("display_name") or "",
        "urls": doc.get("urls") or profile.get("urls") or [],
        "github": doc.get("github") or profile.get("github") or "",
        "x": doc.get("x") or profile.get("x") or "",
        "remember": bool(doc.get("remember", profile.get("remember", True))),
        "wireless": bool(doc.get("wireless")) or _is_wireless(iface),
        "iface": iface,
        "gps_ready": doc.get("lat") is not None and doc.get("lon") is not None,
        "census_geographies": doc.get("census_geographies") or [],
        "census_acs": doc.get("census_acs"),
        "country_code": doc.get("country_code") or "",
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "wireless":
        print(json.dumps(wireless_immediate(), ensure_ascii=False))
        return 0
    if cmd == "gps" and len(sys.argv) >= 4:
        print(json.dumps(set_gps(float(sys.argv[2]), float(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else ""), ensure_ascii=False))
        return 0
    if cmd == "address" and len(sys.argv) >= 3:
        print(json.dumps(set_address(" ".join(sys.argv[2:])), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: operator-location.py [json|wireless|gps LAT LON [label]|address TEXT]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())