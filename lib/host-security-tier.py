#!/usr/bin/env pythong
"""Host security tier — EXTREME protection envelope for 4★ and 5★ hosts."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PROFILE = STATE / "hostess-profile.json"
TIER_STATE = STATE / "host-security-tier.json"

EXTREME_STAR_MIN = 4
GOLD_STARS = 5

# Every hardened control from secure profile + field modules at maximum vigilance.
EXTREME_PROTECTIONS: tuple[str, ...] = (
    "shadow_watch",
    "entropy_watch",
    "behavior_watch",
    "privacy_guard",
    "paranoia_block",
    "paranoia_mode",
    "firewall_auto_block",
    "autosanitize",
    "adblock",
    "adblock_relaxed_fair",
    "connection_gatekeeper",
    "packet_oracle",
    "packet_permission",
    "gatekeeper_strict_trust",
    "shutdown_guard",
    "hostess7_corroborate",
    "attack_kit_auto_crush",
    "field_auto_rekill",
    "home_protector",
    "heavyboi_autokill",
    "kill_detect",
    "seal_vault",
    "tamper_guard",
    "self_defense",
    "signals_field",
    "field_dns_planetary",
    "dns_admin_portal_readonly",
    "dns_multipoint_local_capture",
    "packet_field_dpi",
    "endpoint_corroboration",
    "friendly_guard_v3",
    "lockdown_first",
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


def protection_level_for_stars(stars: int) -> str:
    return "extreme" if int(stars) >= EXTREME_STAR_MIN else "standard"


def _domain_from_url(url: str) -> str:
    s = str(url or "").strip()
    if not s:
        return ""
    if not re.match(r"^https?://", s, re.I):
        s = "https://" + s
    try:
        return (urlparse(s).hostname or "").lower().strip()
    except ValueError:
        return ""


def _honor_lookup(domain: str) -> dict[str, Any]:
    if not domain:
        return {"stars": 3, "gold": False}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "honorability_db", INSTALL / "lib" / "honorability-db.py",
        )
        if not spec or not spec.loader:
            return {"stars": 3, "gold": False}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.lookup(domain)
    except Exception:
        return {"stars": 3, "gold": False}


def compute_local_host_tier(profile: dict[str, Any]) -> int:
    """1–5★ local operator host from Hostess US profile completeness."""
    name = str(profile.get("display_name") or "").strip()
    address = str(profile.get("address") or "").strip()
    kind = str(profile.get("profile_kind") or "person").lower()
    urls = profile.get("urls") or []
    remember = bool((profile.get("host_machine") or {}).get("remember"))

    score = 1
    if name:
        score = max(score, 2)
    if address:
        score = max(score, 3)
    if name and address and kind in ("business", "family", "person"):
        score = max(score, 4)
    if urls:
        score = max(score, 4)
    if name and address and urls and remember:
        score = 5
    if kind in ("business", "family") and name and address and urls:
        score = max(score, 5)
    return min(GOLD_STARS, max(1, score))


def url_star_ratings(profile: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in profile.get("urls") or []:
        url = str(raw.get("url") if isinstance(raw, dict) else raw or "").strip()
        dom = _domain_from_url(url)
        if not dom:
            continue
        # Operator-declared URLs are treated as 5★ endpoints for extreme envelope.
        honor = _honor_lookup(dom)
        stars = max(int(honor.get("stars") or 3), GOLD_STARS if url else 3)
        rows.append({
            "url": url,
            "domain": dom,
            "stars": stars,
            "protection_level": protection_level_for_stars(stars),
            "operator_declared": True,
        })
    return rows


def build_tier_doc(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    prof = profile if profile is not None else _load_json(PROFILE, {})
    if not prof.get("schema"):
        prof = {}
    host_stars = compute_local_host_tier(prof)
    url_rows = url_star_ratings(prof)
    url_extreme = any(r["protection_level"] == "extreme" for r in url_rows)
    level = "extreme" if host_stars >= EXTREME_STAR_MIN or url_extreme else "standard"
    return {
        "schema": "host-security-tier/v1",
        "updated": _now(),
        "host_star_tier": host_stars,
        "security_level": level,
        "extreme_star_min": EXTREME_STAR_MIN,
        "extreme_active": level == "extreme",
        "host_machine_explicit": bool((prof.get("host_machine") or {}).get("remember")),
        "operator_urls": url_rows,
        "extreme_protections": list(EXTREME_PROTECTIONS) if level == "extreme" else [],
        "protection_points": len(EXTREME_PROTECTIONS) if level == "extreme" else 0,
        "motto": (
            "EXTREME envelope — every protection point at maximum for 4★ and 5★ hosts."
            if level == "extreme"
            else "Standard secure profile — complete US profile for 4★+ EXTREME tier."
        ),
    }


def enrich_profile(profile: dict[str, Any]) -> dict[str, Any]:
    tier = build_tier_doc(profile)
    out = dict(profile)
    out["host_star_tier"] = tier["host_star_tier"]
    out["security_level"] = tier["security_level"]
    out["extreme_active"] = tier["extreme_active"]
    out["extreme_protections"] = tier["extreme_protections"]
    out["operator_url_ratings"] = tier["operator_urls"]
    return out


def publish_tier(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = build_tier_doc(profile)
    _save_json(TIER_STATE, doc)
    return doc


def endpoint_extreme_meta(stars: int, *, operator_declared: bool = False) -> dict[str, Any]:
    eff = GOLD_STARS if operator_declared else int(stars)
    level = protection_level_for_stars(eff)
    if level != "extreme":
        return {"security_level": level, "extreme_endpoint_protection": False}
    return {
        "security_level": "extreme",
        "extreme_endpoint_protection": True,
        "extreme_host_stars": eff,
        "extreme_protections": list(EXTREME_PROTECTIONS),
        "extreme_watch": True,
        "extreme_dpi": True,
        "endpoint_corroboration": True,
    }


def attach_to_us_field(doc: dict[str, Any]) -> dict[str, Any]:
    prof = _load_json(PROFILE, {})
    tier = publish_tier(prof if prof.get("schema") else None)
    doc["host_security"] = tier
    if tier.get("extreme_active"):
        prot = dict(doc.get("protection") or {})
        prot["security_level"] = "extreme"
        prot["extreme_protections"] = tier.get("extreme_protections") or []
        prot["host_star_tier"] = tier.get("host_star_tier")
        doc["protection"] = prot
        obs = list(doc.get("observations") or [])
        obs.insert(0, {
            "label": "EXTREME security envelope",
            "text": (
                f"This host is {tier.get('host_star_tier')}★ — "
                f"{tier.get('protection_points')} protection points at EXTREME level "
                f"(shadow, entropy, privacy, paranoia, firewall, DPI, Home Protector, HeavyBoi, Hostess7 corroboration). "
                f"Adblock stays relaxed (fair) — trusted 4★/5★ hosts are not choked by strict lists."
            ),
        })
        doc["observations"] = obs
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(build_tier_doc(), ensure_ascii=False))
        return 0
    if cmd == "publish":
        print(json.dumps(publish_tier(), ensure_ascii=False))
        return 0
    if cmd == "level" and len(sys.argv) >= 3:
        stars = int(sys.argv[2])
        print(json.dumps({
            "stars": stars,
            "protection_level": protection_level_for_stars(stars),
            **endpoint_extreme_meta(stars),
        }, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: host-security-tier.py [json|publish|level STARS]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())