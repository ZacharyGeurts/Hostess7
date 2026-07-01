#!/usr/bin/env pythong
"""Honorability database — 5 gold-star trust for domains/sites.

Default: 3 stars (moderate). Stars ≤4 require operator acceptance only when
actively visiting that site in a browser — never nag otherwise.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "honorability-seed.json"
USER_DB = STATE / "honorability.json"
ACCEPTED = STATE / "honorability-accepted.json"

DEFAULT_STARS = 3
GOLD_STARS = 5
ACCEPT_BELOW = 5  # stars < 5 may need visit-time acceptance


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


def _registrable_domain(host: str) -> str:
    host = (host or "").lower().strip().rstrip(".")
    if not host or host.replace(".", "").isdigit():
        return host
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    if parts[-2] in ("co", "com", "org", "net", "gov", "ac") and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _seed_entries() -> dict[str, dict[str, Any]]:
    doc = _load_json(SEED, {"entries": [], "default_stars": DEFAULT_STARS})
    out: dict[str, dict[str, Any]] = {}
    for row in doc.get("entries") or []:
        dom = _registrable_domain(str(row.get("domain") or ""))
        if dom:
            out[dom] = {
                "domain": dom,
                "stars": int(row.get("stars") or DEFAULT_STARS),
                "category": row.get("category") or "site",
                "note": row.get("note") or "",
                "source": "seed",
            }
    return out


def _user_entries() -> dict[str, dict[str, Any]]:
    doc = _load_json(USER_DB, {"entries": {}})
    entries = doc.get("entries") or {}
    if isinstance(entries, list):
        entries = {str(r.get("domain")): r for r in entries if r.get("domain")}
    return {k.lower(): v for k, v in entries.items()}


def _accepted_set() -> set[str]:
    doc = _load_json(ACCEPTED, {"domains": [], "updated": None})
    return {str(d).lower() for d in (doc.get("domains") or [])}


def lookup(domain: str) -> dict[str, Any]:
    dom = _registrable_domain(domain)
    seed = _seed_entries()
    user = _user_entries()
    accepted = _accepted_set()
    row = dict(user.get(dom) or seed.get(dom) or {})
    stars = int(row.get("stars") or DEFAULT_STARS)
    stars = max(1, min(GOLD_STARS, stars))
    needs_acceptance = stars < ACCEPT_BELOW and dom not in accepted
    gold = stars >= GOLD_STARS
    protection_level = "extreme" if stars >= 4 else "standard"
    return {
        "domain": dom,
        "stars": stars,
        "gold": gold,
        "protection_level": protection_level,
        "extreme_endpoint_protection": protection_level == "extreme",
        "category": row.get("category") or "unknown",
        "note": row.get("note") or "",
        "source": row.get("source") or ("seed" if dom in seed else "default"),
        "default_moderate": stars == DEFAULT_STARS and dom not in seed and dom not in user,
        "needs_acceptance": needs_acceptance,
        "accepted": dom in accepted,
        "stars_label": _stars_label(stars),
    }


def _stars_label(stars: int) -> str:
    if stars >= GOLD_STARS:
        return "5 gold — full trust · EXTREME protection"
    if stars == 4:
        return "4 stars — trusted on visit · EXTREME protection"
    if stars == 3:
        return "3 stars — moderate default"
    if stars == 2:
        return "2 stars — caution"
    return "1 star — explicit acceptance required"


def set_rating(domain: str, stars: int, note: str = "") -> bool:
    dom = _registrable_domain(domain)
    if not dom:
        return False
    stars = max(1, min(GOLD_STARS, int(stars)))
    doc = _load_json(USER_DB, {"entries": {}, "updated": None})
    entries = doc.get("entries") or {}
    if not isinstance(entries, dict):
        entries = {}
    entries[dom] = {
        "domain": dom,
        "stars": stars,
        "note": note,
        "source": "operator",
        "updated": _now(),
    }
    doc["entries"] = entries
    doc["updated"] = _now()
    _save_json(USER_DB, doc)
    return True


def accept_domain(domain: str) -> bool:
    dom = _registrable_domain(domain)
    if not dom:
        return False
    doc = _load_json(ACCEPTED, {"domains": [], "updated": None})
    domains = list(doc.get("domains") or [])
    if dom not in domains:
        domains.append(dom)
    doc["domains"] = domains[-500:]
    doc["updated"] = _now()
    _save_json(ACCEPTED, doc)
    return True


def all_entries(limit: int = 80) -> list[dict[str, Any]]:
    seed = _seed_entries()
    user = _user_entries()
    merged: dict[str, dict[str, Any]] = {}
    for dom, row in seed.items():
        merged[dom] = lookup(dom)
    for dom in user:
        merged[dom] = lookup(dom)
    rows = sorted(merged.values(), key=lambda r: (-int(r["stars"]), r["domain"]))
    return rows[:limit]


def panel_json(active_sites: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    seed_doc = _load_json(SEED, {})
    sites = active_sites or []
    enriched = []
    pending = []
    for site in sites:
        host = site.get("host") or site.get("domain") or ""
        info = lookup(host)
        row = {**site, **info, "active": True}
        enriched.append(row)
        if info.get("needs_acceptance"):
            pending.append(row)
    return {
        "motto": "Low-level data researchers — honorability at onset, stars not nagging.",
        "tagline": "5 gold stars pass silently — safe signal, no human touch. Music, normal traffic, and animals are different.",
        "default_stars": int(seed_doc.get("default_stars") or DEFAULT_STARS),
        "gold_stars": GOLD_STARS,
        "accept_below_stars": ACCEPT_BELOW,
        "entry_count": len(all_entries(200)),
        "entries": all_entries(60),
        "active_browser_sites": enriched,
        "pending_acceptance": pending,
        "updated": _now(),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "lookup" and len(sys.argv) >= 3:
        print(json.dumps(lookup(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "rate" and len(sys.argv) >= 4:
        ok = set_rating(sys.argv[2], int(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else "")
        print(json.dumps({"ok": ok}))
        return 0
    if cmd == "accept" and len(sys.argv) >= 3:
        ok = accept_domain(sys.argv[2])
        print(json.dumps({"ok": ok, "domain": sys.argv[2]}))
        return 0
    print(json.dumps({"error": "usage: honorability-db.py [json|lookup DOM|rate DOM STARS|accept DOM]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())