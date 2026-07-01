#!/usr/bin/env pythong
"""Canonical operator default — Gladstone MI anchor, name, address, GitHub + X URLs."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
LOC_FILE = STATE / "operator-location.json"
PROFILE_FILE = STATE / "hostess-profile.json"

_FALLBACK: dict[str, Any] = {
    "schema": "operator-default/v1",
    "display_name": "Zachary Geurts",
    "address": "8259 W Burntwood P.15 Drive, Gladstone, MI 49837",
    "lat": 45.845976,
    "lon": -87.055759,
    "label": "8259 W BURNTWOOD P 15 DR, GLADSTONE, MI, 49837",
    "remember": True,
    "default_for_all": True,
    "urls": [
        "https://github.com/ZacharyGeurts",
        "https://x.com/ZacharyGeurts",
    ],
    "github": "https://github.com/ZacharyGeurts",
    "x": "https://x.com/ZacharyGeurts",
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



def default_path() -> Path:
    env = os.environ.get("NEXUS_OPERATOR_DEFAULT", "").strip()
    if env:
        return Path(env)
    return INSTALL / "data" / "operator-default.json"


def load_default() -> dict[str, Any]:
    path = default_path()
    if path.is_file():
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            if doc.get("lat") is not None and doc.get("lon") is not None:
                return {**_FALLBACK, **doc}
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return dict(_FALLBACK)


def _save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _location_unset(doc: dict[str, Any]) -> bool:
    lat, lon = doc.get("lat"), doc.get("lon")
    if lat is None or lon is None:
        return True
    try:
        return float(lat) == 0.0 and float(lon) == 0.0
    except (TypeError, ValueError):
        return True


def seed_operator_location(force: bool = False) -> dict[str, Any]:
    cur: dict[str, Any] = {}
    if LOC_FILE.is_file():
        try:
            cur = json.loads(LOC_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cur = {}
    if not force and not _location_unset(cur):
        return cur

    d = load_default()
    out = {
        **cur,
        "lat": round(float(d["lat"]), 6),
        "lon": round(float(d["lon"]), 6),
        "label": d.get("label") or d.get("address") or "Operator",
        "address": d.get("address") or "",
        "display_name": d.get("display_name") or "",
        "source": "operator_default",
        "remember": bool(d.get("remember", True)),
        "default_for_all": bool(d.get("default_for_all", True)),
        "urls": list(d.get("urls") or []),
        "github": d.get("github") or "",
        "x": d.get("x") or "",
        "updated": _now(),
    }
    _save_json(LOC_FILE, out)
    return out


def seed_hostess_profile(force: bool = False) -> dict[str, Any]:
    cur: dict[str, Any] = {}
    if PROFILE_FILE.is_file():
        try:
            cur = json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            cur = {}
    if not force and cur.get("display_name") and cur.get("address"):
        return cur

    d = load_default()
    urls = list(d.get("urls") or [])
    out = {
        "schema": "hostess-profile/v1",
        "updated": _now(),
        "display_name": str(d.get("display_name") or cur.get("display_name") or "")[:120],
        "address": str(d.get("address") or cur.get("address") or "")[:240],
        "profile_kind": cur.get("profile_kind") or "person",
        "urls": urls[:64],
        "notes": cur.get("notes") or "",
        "host_machine": {
            **(cur.get("host_machine") or {}),
            "remember": bool(d.get("remember", True)),
        },
    }
    _save_json(PROFILE_FILE, out)
    return out


def seed_all(force: bool = False) -> dict[str, Any]:
    loc = seed_operator_location(force=force)
    prof = seed_hostess_profile(force=force)
    return {"ok": True, "operator_location": loc, "hostess_profile": prof}


def panel_operator() -> dict[str, Any]:
    d = load_default()
    loc: dict[str, Any] = {}
    if LOC_FILE.is_file():
        try:
            loc = json.loads(LOC_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            loc = {}
    if _location_unset(loc):
        loc = seed_operator_location()
    return {
        "display_name": loc.get("display_name") or d.get("display_name") or "",
        "address": loc.get("address") or d.get("address") or "",
        "lat": loc.get("lat") if loc.get("lat") is not None else d.get("lat"),
        "lon": loc.get("lon") if loc.get("lon") is not None else d.get("lon"),
        "label": loc.get("label") or d.get("label") or "",
        "source": loc.get("source") or "operator_default",
        "remember": bool(loc.get("remember", d.get("remember", True))),
        "urls": list(loc.get("urls") or d.get("urls") or []),
        "github": loc.get("github") or d.get("github") or "",
        "x": loc.get("x") or d.get("x") or "",
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(load_default(), ensure_ascii=False))
        return 0
    if cmd == "panel":
        print(json.dumps(panel_operator(), ensure_ascii=False))
        return 0
    if cmd == "seed":
        force = "--force" in sys.argv[2:]
        print(json.dumps(seed_all(force=force), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: operator-default.py [json|panel|seed [--force]]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())