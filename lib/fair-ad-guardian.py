#!/usr/bin/env pythong
"""NEXUS Fair Ad Guardian — non-intrusive, advertiser-fair ad control.

Blocks what people actually complain about (popups, lockouts, third-party junk).
Respects site ad-required policies — opt out means leave the site.
Browser-aware: uses live connections to tell first-party vs not-the-guy.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
DATA = INSTALL / "data"
CONN_INTENT = STATE / "connection-intent.json"
GUARDIAN_JSON = STATE / "adblock-guardian.json"
BLOCKLIST = STATE / "adblock" / "domains-block.txt"
USER_POLICIES = STATE / "adblock" / "site-policies.json"
ADBLOCK_DIR = STATE / "adblock"

BROWSER_PROCS = frozenset({
    "fieldfox", "field-queen", "queen-browser",
    "firefox", "chrome", "chromium", "brave", "brave-browser", "vivaldi", "opera",
    "msedge", "waterfox", "librewolf", "floorp", "google-chrome", "google-chrome-stable",
})

LOCKOUT_CATEGORIES = frozenset({"lockout", "popup", "content_spam"})
POLICY_VALUES = frozenset({"annoyance", "fair", "strict"})


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


def _read_settings_override() -> dict[str, str]:
    override = STATE / "settings.override"
    out: dict[str, str] = {}
    if not override.is_file():
        return out
    for line in override.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def get_policy() -> str:
    s = _read_settings_override()
    pol = s.get("NEXUS_ADBLOCK_POLICY", os.environ.get("NEXUS_ADBLOCK_POLICY", "annoyance"))
    return pol if pol in POLICY_VALUES else "annoyance"


def is_enabled() -> bool:
    s = _read_settings_override()
    return s.get("NEXUS_ADBLOCK", os.environ.get("NEXUS_ADBLOCK", "0")) == "1"


def respect_site_policy() -> bool:
    s = _read_settings_override()
    v = s.get("NEXUS_ADBLOCK_RESPECT_POLICY", os.environ.get("NEXUS_ADBLOCK_RESPECT_POLICY", "1"))
    return v != "0"


def load_complaint_domains() -> dict[str, dict[str, Any]]:
    path = DATA / "annoyance-complaints.tsv"
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        domain, category, score, reason = parts[0], parts[1], parts[2], parts[3]
        out[domain.lower()] = {
            "domain": domain.lower(),
            "category": category,
            "complaint_score": int(score) if score.isdigit() else 5,
            "reason": reason,
        }
    return out


def load_site_policies() -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for path in (DATA / "site-ad-policies.json", USER_POLICIES):
        doc = _load_json(path, {"sites": []})
        for site in doc.get("sites") or []:
            dom = (site.get("domain") or "").lower()
            if dom:
                merged[dom] = site
    return merged


def _registrable_domain(host: str) -> str:
    host = host.lower().strip(".")
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    # simple eTLD+1 heuristic
    if parts[-2] in ("co", "com", "org", "net", "gov", "ac") and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def _is_subdomain_of(child: str, parent: str) -> bool:
    child, parent = child.lower(), parent.lower()
    return child == parent or child.endswith("." + parent)


def detect_browser_page_hosts() -> list[dict[str, Any]]:
    data = _load_json(CONN_INTENT, {})
    hosts: dict[str, dict[str, Any]] = {}
    for c in data.get("connections") or []:
        proc = (c.get("process") or "").lower()
        if proc not in BROWSER_PROCS:
            continue
        if c.get("verdict") not in ("USER_OK", "EPHEMERAL", "MONITOR"):
            continue
        rip = c.get("remote_ip") or ""
        intel = c.get("intel") or {}
        label = intel.get("hostname") or intel.get("label") or ""
        host = ""
        if label and "." in label:
            host = label.split()[0].lower()
        if not host and rip:
            host = rip
        if not host:
            continue
        rd = _registrable_domain(host) if "." in host else host
        hosts[rd] = {
            "host": rd,
            "process": proc,
            "verdict": c.get("verdict"),
            "remote_ip": rip,
        }
    return list(hosts.values())


def load_fetched_domains() -> set[str]:
    domains: set[str] = set()
    adb = ADBLOCK_DIR
    if not adb.is_dir():
        return domains
    for f in adb.glob("*.txt"):
        if f.name == "domains-block.txt":
            continue
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\|\|([^/\s]+)\^", line)
            if m:
                domains.add(m.group(1).lower())
            elif re.match(r"^[a-z0-9.-]+\.[a-z]{2,}$", line.strip(), re.I):
                domains.add(line.strip().lower())
    legacy = adb / "domains.txt"
    if legacy.is_file():
        for line in legacy.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip():
                domains.add(line.strip().lower())
    return domains


def build_blocklist(policy: str | None = None) -> dict[str, Any]:
    policy = policy or get_policy()
    complaints = load_complaint_domains()
    site_policies = load_site_policies()
    page_hosts = detect_browser_page_hosts()
    active_sites = {h["host"] for h in page_hosts}

    block_domains: dict[str, dict[str, Any]] = {}
    skipped_first_party: list[dict[str, str]] = []

    def consider(domain: str, meta: dict[str, Any], source: str) -> None:
        domain = domain.lower()
        if policy == "fair" and respect_site_policy():
            for ph in active_sites:
                if _is_subdomain_of(domain, ph):
                    skipped_first_party.append({"domain": domain, "page": ph, "reason": "first_party_on_active_site"})
                    return
            sp = site_policies.get(_registrable_domain(domain)) or site_policies.get(domain)
            if sp and sp.get("policy") == "ads_required" and meta.get("category") in ("ad_network", "tracker"):
                if _is_subdomain_of(domain, sp["domain"]) or _registrable_domain(domain) == sp["domain"]:
                    skipped_first_party.append({"domain": domain, "page": sp["domain"], "reason": "site_ads_required_policy"})
                    return

        block_domains[domain] = {**meta, "source": source}

    if policy in ("annoyance", "fair"):
        for dom, meta in complaints.items():
            consider(dom, meta, "complaint_table")
    elif policy == "strict":
        for dom, meta in complaints.items():
            consider(dom, meta, "complaint_table")
        for dom in load_fetched_domains():
            if dom not in block_domains:
                consider(dom, {"category": "list", "complaint_score": 5, "reason": "Filter list"}, "fetched_list")

    # Always block lockouts and popups in fair/annoyance — not-the-guy
    for dom, meta in complaints.items():
        if meta.get("category") in LOCKOUT_CATEGORIES:
            block_domains[dom] = {**meta, "source": "always_nag_block"}

    ADBLOCK_DIR.mkdir(parents=True, exist_ok=True)
    lines = sorted(block_domains.keys())
    BLOCKLIST.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    return {
        "updated": _now(),
        "policy": policy,
        "enabled": is_enabled(),
        "domain_count": len(lines),
        "skipped_first_party": skipped_first_party[:20],
        "active_browser_sites": list(active_sites)[:15],
        "domains": lines[:100],
    }


def guardian_scan() -> dict[str, Any]:
    policy = get_policy()
    complaints = load_complaint_domains()
    page_hosts = detect_browser_page_hosts()
    site_policies = load_site_policies()
    events: list[dict[str, Any]] = []
    suggestions: list[dict[str, str]] = []

    data = _load_json(CONN_INTENT, {})
    for c in data.get("connections") or []:
        proc = (c.get("process") or "").lower()
        if proc not in BROWSER_PROCS:
            continue
        intel = c.get("intel") or {}
        label = (intel.get("label") or intel.get("hostname") or "").lower()
        rip = c.get("remote_ip") or ""
        for dom, meta in complaints.items():
            if dom in label or dom in rip:
                cat = meta.get("category", "")
                events.append({
                    "type": "complaint_match",
                    "domain": dom,
                    "category": cat,
                    "process": proc,
                    "peer": rip,
                    "reason": meta.get("reason", ""),
                    "action": "block" if cat in LOCKOUT_CATEGORIES or policy == "annoyance" else "review",
                })

    for ph in page_hosts:
        sp = site_policies.get(ph["host"])
        if sp and sp.get("policy") == "ads_required":
            suggestions.append({
                "site": ph["host"],
                "message": sp.get("note", "This site requires ads — opt out means leave."),
                "policy": "ads_required",
            })

    if not is_enabled():
        suggestions.append({
            "site": "",
            "message": "Fair Ad Guardian is off. Turn on Annoyance mode to block popups and lockouts only.",
            "policy": "off",
        })
    elif policy == "annoyance":
        suggestions.append({
            "site": "",
            "message": "Annoyance mode ON — blocking popups, lockouts, and complained-about third parties. First-party site ads respected.",
            "policy": "annoyance",
        })
    elif policy == "fair":
        suggestions.append({
            "site": "",
            "message": "Fair mode ON — we block nag-ware and third-party junk but honor sites that require ads.",
            "policy": "fair",
        })

    out = {
        "updated": _now(),
        "motto": "Fair to advertisers — block what everyone complains about, not the whole web.",
        "policy": policy,
        "enabled": is_enabled(),
        "respect_site_policy": respect_site_policy(),
        "browser_sites": page_hosts,
        "events": events[:30],
        "suggestions": suggestions,
        "site_policy_count": len(site_policies),
    }
    _save_json(GUARDIAN_JSON, out)
    return out


def add_site_policy(domain: str, policy: str, note: str = "") -> bool:
    domain = domain.lower().strip()
    if not domain or policy not in ("ads_required", "allow_all", "block_annoyances"):
        return False
    doc = _load_json(USER_POLICIES, {"sites": []})
    sites = [s for s in doc.get("sites", []) if s.get("domain") != domain]
    sites.append({"domain": domain, "policy": policy, "note": note or f"User policy: {policy}"})
    doc["sites"] = sites
    _save_json(USER_POLICIES, doc)
    return True


def guardian_status_json() -> dict[str, Any]:
    g = _load_json(GUARDIAN_JSON, {})
    bl = _load_json(STATE / "adblock" / "state.json", {})
    if not g:
        g = guardian_scan()
    return {
        **g,
        "blocklist_count": len(BLOCKLIST.read_text(encoding="utf-8").splitlines()) if BLOCKLIST.is_file() else 0,
        "ips_blocked": bl.get("ips_blocked", 0),
        "domains_loaded": bl.get("domains", 0),
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: fair-ad-guardian.py [scan|blocklist|status|site-policy <domain> <policy> [note]]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "scan":
        json.dump(guardian_scan(), sys.stdout, indent=2)
    elif cmd == "blocklist":
        pol = sys.argv[2] if len(sys.argv) > 2 else None
        json.dump(build_blocklist(pol), sys.stdout, indent=2)
    elif cmd == "status":
        json.dump(guardian_status_json(), sys.stdout, indent=2)
    elif cmd == "site-policy" and len(sys.argv) >= 4:
        ok = add_site_policy(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else "")
        json.dump({"ok": ok}, sys.stdout)
    else:
        print("usage: fair-ad-guardian.py [scan|blocklist|status|site-policy ...]", file=sys.stderr)
        return 1
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())