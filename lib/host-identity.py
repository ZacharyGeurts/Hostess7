#!/usr/bin/env pythong
"""NEXUS Host Identity — precise same-host validation for RE-KILL.

Archives fingerprint at KILL; online check re-probes and validates markers
that matter: PTR, TLS, ASN/org, MAC OUI, HTTP server, banner, CIDR.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
DOSSIER_FILE = os.environ.get("NEXUS_TARGET_DOSSIER_FILE", "nexus-target-dossiers.jsonl")

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)

MARKER_WEIGHTS: dict[str, int] = {
    "tls_subject": 30,
    "ptr_hostname": 25,
    "mac_oui": 25,
    "asn": 20,
    "http_server": 15,
    "org": 15,
    "banner": 15,
    "network_handle": 15,
    "tls_issuer": 10,
    "cidr": 10,
    "target_os_family": 5,
}
STRONG_MARKERS = frozenset({"tls_subject", "ptr_hostname", "mac_oui", "asn"})
SAME_HOST_MIN_SCORE = 40
SAME_HOST_STRONG_MIN = 1


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



def _norm(s: Any) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _norm_host(s: Any) -> str:
    return _norm(s).rstrip(".")


def _dossier_paths() -> list[Path]:
    return [
        HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "security" / DOSSIER_FILE,
        HOSTESS7_TEAM_FIELD / "brain" / "security" / DOSSIER_FILE,
        STATE / "field-storage" / DOSSIER_FILE,
    ]


def load_archived_dossier(ip: str) -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    latest_ts = ""
    for path in _dossier_paths():
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if row.get("kind") != "nexus_target_dossier":
                    continue
                if str(row.get("ip") or "") != ip:
                    continue
                ts = str(row.get("ts") or "")
                if ts >= latest_ts:
                    latest_ts = ts
                    latest = row.get("dossier") if isinstance(row.get("dossier"), dict) else row
        except OSError:
            continue
    return latest


def extract_identity_fingerprint(source: dict[str, Any]) -> dict[str, Any]:
    """Build precise identity markers from archived dossier or live point."""
    ip = str(source.get("ip") or "")
    intel = source.get("intel") or {}
    geo = source.get("geo") or {}
    bleed = source.get("target_bleed") or {}
    tb = bleed.get("target") if isinstance(bleed.get("target"), dict) else {}
    tls = tb.get("tls") if isinstance(tb.get("tls"), dict) else {}
    http = tb.get("http") if isinstance(tb.get("http"), dict) else {}
    banner = tb.get("banner") if isinstance(tb.get("banner"), dict) else {}

    markers: dict[str, str] = {
        "ptr_hostname": _norm_host(
            source.get("ptr_hostname")
            or tb.get("ptr_hostname")
            or intel.get("hostname")
            or source.get("hostname")
            or (tb.get("reverse_dns") or {}).get("hostname")
        ),
        "tls_subject": _norm(tls.get("subject") or source.get("target_tls_subject")),
        "tls_issuer": _norm(tls.get("issuer")),
        "http_server": _norm(http.get("server") or source.get("target_http_server")),
        "banner": _norm(banner.get("banner") or source.get("target_banner"))[:200],
        "asn": _norm(source.get("asn") or geo.get("asn")),
        "org": _norm(source.get("org") or geo.get("org")),
        "registrar": _norm(source.get("registrar") or geo.get("registrar")),
        "network_handle": _norm(source.get("network_handle")),
        "cidr": _norm(source.get("cidr") or geo.get("cidr")),
        "mac_oui": _norm(source.get("mac_oui") or intel.get("mac_oui")),
        "mac_vendor": _norm(source.get("mac_vendor") or intel.get("mac_vendor")),
        "target_os_family": _norm(source.get("target_os_family") or tb.get("os_family")),
        "geo_city": _norm(source.get("city") or geo.get("city")),
        "geo_country_code": _norm(source.get("country_code") or geo.get("country_code")),
    }
    markers = {k: v for k, v in markers.items() if v}
    ports = source.get("target_ports") or tb.get("ports_seen") or []
    if isinstance(ports, list):
        ports = [int(p) for p in ports if str(p).isdigit()]
    blob = json.dumps({"ip": ip, "markers": markers, "ports": sorted(ports)}, sort_keys=True)
    identity_hash = hashlib.sha256(blob.encode()).hexdigest()[:24]
    return {
        "ip": ip,
        "identity_hash": identity_hash,
        "markers": markers,
        "ports": ports,
        "marker_count": len(markers),
    }


def fingerprint_from_point_or_dossier(ip: str, point: dict[str, Any] | None = None) -> dict[str, Any]:
    if point and point.get("ip") == ip:
        return extract_identity_fingerprint({**point, "ip": ip})
    archived = load_archived_dossier(ip)
    if archived:
        return extract_identity_fingerprint({**archived, "ip": ip})
    if point:
        return extract_identity_fingerprint({**point, "ip": ip})
    return {"ip": ip, "identity_hash": "", "markers": {}, "ports": [], "marker_count": 0}


def _ping_online(ip: str) -> bool:
    if PRIVATE_RE.match(ip):
        return False
    try:
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _tcp_online(ip: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except OSError:
        return False


def _ss_active(ip: str) -> bool:
    try:
        proc = subprocess.run(
            ["ss", "-H", "-tunap"],
            capture_output=True,
            text=True,
            timeout=6,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return ip in proc.stdout


def _live_probe(ip: str, ports: list[int]) -> dict[str, Any]:
    import importlib.util

    probe: dict[str, Any] = {
        "ip": ip,
        "checked": _now(),
        "ping": _ping_online(ip),
        "ss_active": _ss_active(ip),
        "tcp_ports": {},
        "online": False,
    }
    for port in ports[:6]:
        probe["tcp_ports"][str(port)] = _tcp_online(ip, port)
    probe["online"] = bool(
        probe["ping"]
        or probe["ss_active"]
        or any(probe["tcp_ports"].values())
    )

    bleed_script = INSTALL / "lib" / "target-bleed.py"
    if bleed_script.is_file() and probe["online"]:
        spec = importlib.util.spec_from_file_location("target_bleed_id", bleed_script)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        fresh = mod.bleed_target(ip, online=True)
        tb = fresh.get("target") or {}
        probe["ptr_hostname"] = _norm_host(
            fresh.get("ptr_hostname") or (tb.get("reverse_dns") or {}).get("hostname")
        )
        probe["target_os_family"] = _norm(tb.get("os_family"))
        probe["tls_subject"] = _norm((tb.get("tls") or {}).get("subject"))
        probe["tls_issuer"] = _norm((tb.get("tls") or {}).get("issuer"))
        probe["http_server"] = _norm((tb.get("http") or {}).get("server"))
        probe["banner"] = _norm((tb.get("banner") or {}).get("banner"))[:200]

    geo_script = INSTALL / "lib" / "geo-intel-standards.py"
    if geo_script.is_file():
        spec = importlib.util.spec_from_file_location("geo_id", geo_script)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        geo = mod.enrich_ip(ip, online=probe["online"])
        probe["asn"] = _norm(geo.get("asn"))
        probe["org"] = _norm(geo.get("org"))
        probe["registrar"] = _norm(geo.get("registrar"))
        probe["network_handle"] = _norm(geo.get("network_handle"))
        probe["cidr"] = _norm(geo.get("cidr"))
        probe["mac_oui"] = _norm(geo.get("mac_oui"))
        probe["mac_vendor"] = _norm(geo.get("mac_vendor"))
        probe["geo_city"] = _norm(geo.get("city"))
        probe["geo_country_code"] = _norm(geo.get("country_code"))

    return probe


def validate_same_host(archived: dict[str, Any], live: dict[str, Any]) -> dict[str, Any]:
    ip = str(archived.get("ip") or "")
    if ip != str(live.get("ip") or ""):
        return {
            "same_host": False,
            "score": 0,
            "required_ip_match": False,
            "matches": [],
            "mismatches": [{"marker": "ip", "archived": ip, "live": live.get("ip")}],
            "reason": "ip_mismatch",
        }

    archived_markers = archived.get("markers") or {}
    live_map = {
        "ptr_hostname": live.get("ptr_hostname"),
        "tls_subject": live.get("tls_subject"),
        "tls_issuer": live.get("tls_issuer"),
        "http_server": live.get("http_server"),
        "banner": live.get("banner"),
        "asn": live.get("asn"),
        "org": live.get("org"),
        "registrar": live.get("registrar"),
        "network_handle": live.get("network_handle"),
        "cidr": live.get("cidr"),
        "mac_oui": live.get("mac_oui"),
        "mac_vendor": live.get("mac_vendor"),
        "target_os_family": live.get("target_os_family"),
        "geo_city": live.get("geo_city"),
        "geo_country_code": live.get("geo_country_code"),
    }

    matches: list[dict[str, str]] = []
    mismatches: list[dict[str, str]] = []
    score = 0
    strong_hits = 0

    for key, weight in MARKER_WEIGHTS.items():
        a_val = _norm(archived_markers.get(key))
        if not a_val:
            continue
        l_val = _norm(live_map.get(key))
        if not l_val:
            continue
        if a_val == l_val or (key in ("org", "ptr_hostname") and (a_val in l_val or l_val in a_val)):
            score += weight
            matches.append({"marker": key, "value": a_val[:120]})
            if key in STRONG_MARKERS:
                strong_hits += 1
        else:
            mismatches.append({"marker": key, "archived": a_val[:80], "live": l_val[:80]})

    same_host = (
        score >= SAME_HOST_MIN_SCORE
        and strong_hits >= SAME_HOST_STRONG_MIN
        and len(mismatches) <= max(1, len(matches) // 2)
    )
    reason = "validated" if same_host else "identity_mismatch"
    if not archived_markers:
        reason = "no_archived_markers"

    return {
        "same_host": same_host,
        "score": score,
        "strong_hits": strong_hits,
        "required_ip_match": True,
        "matches": matches,
        "mismatches": mismatches,
        "archived_hash": archived.get("identity_hash", ""),
        "reason": reason,
    }


def check_target_online(ip: str, point: dict[str, Any] | None = None) -> dict[str, Any]:
    if not ip or PRIVATE_RE.match(ip):
        return {"ok": False, "ip": ip, "error": "invalid_ip"}
    archived_fp = fingerprint_from_point_or_dossier(ip, point)
    ports = list(archived_fp.get("ports") or [])
    if not ports:
        ports = [443, 80]
    live = _live_probe(ip, ports)
    validation = validate_same_host(archived_fp, live)
    return {
        "ok": True,
        "ip": ip,
        "online": live.get("online", False),
        "archived_fingerprint": archived_fp,
        "live_probe": live,
        "validation": validation,
        "same_host": validation.get("same_host", False),
        "rekill_eligible": bool(live.get("online") and validation.get("same_host")),
        "checked": _now(),
    }


def main() -> int:
    import sys

    if len(sys.argv) < 3:
        print("usage: host-identity.py check <ip>", file=sys.stderr)
        return 1
    if sys.argv[1] == "check":
        json.dump(check_target_online(sys.argv[2]), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())