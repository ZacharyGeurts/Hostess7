#!/usr/bin/env pythong
"""Browser site awareness — active tab hosts + honorability + X.com CDN mapping."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))

# Known CDN / peer prefixes → registrable site (X.com works fine at 5 stars)
SITE_IP_HINTS: dict[str, str] = {
    "104.244.": "x.com",
    "199.16.": "x.com",
    "199.59.": "x.com",
    "192.133.": "x.com",
    "151.101.": "reddit.com",
    "151.101.193.": "github.com",
    "140.82.": "github.com",
    "142.250.": "google.com",
    "172.217.": "google.com",
    "216.58.": "google.com",
}

HOST_ALIASES = {
    "twitter.com": "x.com",
    "mobile.twitter.com": "x.com",
    "t.co": "x.com",
    "pbs.twimg.com": "x.com",
    "video.twimg.com": "x.com",
}


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _honor():
    return _load_module("honorability_db", INSTALL / "lib" / "honorability-db.py")


def _fair_guardian():
    return _load_module("fair_ad_guardian", INSTALL / "lib" / "fair-ad-guardian.py")


def _infer_site_from_ip(ip: str) -> str:
    for prefix, site in SITE_IP_HINTS.items():
        if ip.startswith(prefix):
            return site
    return ""


def _normalize_host(host: str) -> str:
    h = (host or "").lower().strip()
    return HOST_ALIASES.get(h, h)


def detect_active_sites() -> list[dict[str, Any]]:
    honor = _honor()
    try:
        guardian = _fair_guardian()
        raw = guardian.detect_browser_page_hosts()
    except Exception:
        raw = []
    seen: dict[str, dict[str, Any]] = {}
    for row in raw:
        host = _normalize_host(row.get("host") or "")
        if not host or host.replace(".", "").isdigit():
            hint = _infer_site_from_ip(str(row.get("remote_ip") or ""))
            if hint:
                host = hint
            else:
                continue
        if host not in seen:
            info = honor.lookup(host)
            seen[host] = {
                **row,
                "host": host,
                "honor_stars": info["stars"],
                "honor_gold": info["gold"],
                "needs_acceptance": info["needs_acceptance"],
                "honor_label": info["stars_label"],
                "protection_level": info.get("protection_level") or "standard",
                "extreme_endpoint_protection": bool(info.get("extreme_endpoint_protection")),
            }
    return list(seen.values())


def enrich_connection(conn: dict[str, Any]) -> dict[str, Any]:
    honor = _honor()
    proc = (conn.get("process") or "").lower()
    intel = conn.get("intel") or {}
    label = intel.get("hostname") or intel.get("label") or ""
    host = ""
    if label and "." in str(label):
        host = str(label).split()[0].lower()
    rip = str(conn.get("remote_ip") or "")
    if not host or host.replace(".", "").isdigit():
        host = _infer_site_from_ip(rip) or host
    host = _normalize_host(host)
    if not host:
        return conn
    info = honor.lookup(host)
    out = dict(conn)
    out["active_site"] = host
    out["honor_stars"] = info["stars"]
    out["honor_gold"] = info["gold"]
    out["honor_needs_acceptance"] = info["needs_acceptance"]
    out["honor_label"] = info["stars_label"]
    out["protection_level"] = info.get("protection_level") or "standard"
    out["extreme_endpoint_protection"] = bool(info.get("extreme_endpoint_protection"))
    if info["gold"] and proc in getattr(_fair_guardian(), "BROWSER_PROCS", set()):
        out["browser_trusted_site"] = True
    return out


def _queen_slice() -> dict[str, Any]:
    path = INSTALL / "lib" / "field-queen-browser.py"
    if not path.is_file():
        return {}
    try:
        return _load_module("field_queen_browser", path).panel_json()
    except Exception:
        return {}


def panel_json() -> dict[str, Any]:
    honor = _honor()
    sites = detect_active_sites()
    queen = _queen_slice()
    out = {
        "active_sites": sites,
        "honorability": honor.panel_json(sites),
        "x_com_active": any(s.get("host") == "x.com" for s in sites),
        "browser_site_count": len(sites),
    }
    if queen:
        out["queen"] = {
            "verdict": queen.get("queen_verdict"),
            "gates_held": (queen.get("gates") or {}).get("all_held"),
            "mp4_mandatory": (queen.get("codecs") or {}).get("mp4_mandatory"),
            "motto": queen.get("motto"),
        }
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "sites":
        print(json.dumps(detect_active_sites(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: browser-awareness.py [json|sites]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())