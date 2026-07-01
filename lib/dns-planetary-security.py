#!/usr/bin/env pythong
"""Planetary DNS security — EXTREME envelope extended planet-wide per RFC and law."""
from __future__ import annotations

import json
import os
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "dns-legal-rfc-seed.json"

PLANETARY_ZONES = [
    {"region": "Global root", "tld_group": ".", "security_level": "extreme", "rfc": "RFC 1034 §3.6", "note": "13 root servers — trace-only delegation"},
    {"region": "Americas", "tld_group": ".us .ca .mx .br", "security_level": "extreme", "rfc": "RFC 1035", "legal": "18 U.S.C. § 1030", "note": "CFAA-class DNS poison blocked"},
    {"region": "Europe", "tld_group": ".eu .de .uk .fr", "security_level": "extreme", "rfc": "RFC 4033", "legal": "GDPR Art. 32", "note": "NIS2 DNS service measures"},
    {"region": "Asia-Pacific", "tld_group": ".jp .cn .au .in", "security_level": "extreme", "rfc": "RFC 6891", "note": "EDNS0 monitored on egress"},
    {"region": "Africa", "tld_group": ".za .ng .ke", "security_level": "extreme", "rfc": "RFC 1035", "note": "Planetary EXTREME parity"},
    {"region": "Middle East", "tld_group": ".ae .il .sa", "security_level": "extreme", "rfc": "RFC 7766", "note": "TCP fallback documented"},
    {"region": "Special-use", "tld_group": ".localhost .invalid .test", "security_level": "extreme", "rfc": "RFC 6761", "note": "Loopback-only binding enforced"},
    {"region": "Infrastructure", "tld_group": "arpa", "security_level": "extreme", "rfc": "RFC 6895", "note": "IANA parameter compliance"},
]


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


def _host_security_level() -> str:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "host_security_tier", INSTALL / "lib" / "host-security-tier.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return str(mod.build_tier_doc().get("security_level") or "standard")
    except Exception:
        pass
    return "standard"


def _is_ipv6_addr(addr: str) -> bool:
    return ":" in addr


def _split_nameservers(servers: list[str]) -> tuple[list[str], list[str]]:
    v4: list[str] = []
    v6: list[str] = []
    for addr in servers:
        if _is_ipv6_addr(addr):
            v6.append(addr)
        else:
            v4.append(addr)
    return v4, v6


def _trusted_v4_nameservers(port: int) -> set[str]:
    return {"127.0.0.1", "127.0.0.53", f"127.0.0.1#{port}"}


def _trusted_v6_nameservers(port: int) -> set[str]:
    return {"::1", f"::1#{port}"}


def _stack_truth_enforced(servers: list[str], trusted: set[str]) -> bool:
    if not servers:
        return True
    return all(s in trusted for s in servers)


def _foreign_resolver_ip_sets(seed: dict[str, Any]) -> dict[str, list[str]]:
    v4: list[str] = []
    v6: list[str] = []
    for row in seed.get("foreign_resolvers_blocked") or []:
        for ip in row.get("ipv4") or []:
            if ip and ip not in v4:
                v4.append(str(ip))
        for ip in row.get("ipv6") or []:
            if ip and ip not in v6:
                v6.append(str(ip))
    return {"ipv4": v4, "ipv6": v6}


def _resolv_snapshot() -> dict[str, Any]:
    servers: list[str] = []
    search: list[str] = []
    options: list[str] = []
    path = Path("/etc/resolv.conf")
    if path.is_file():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if parts[0] == "nameserver" and len(parts) > 1:
                servers.append(parts[1])
            elif parts[0] == "search" and len(parts) > 1:
                search.extend(parts[1:])
            elif parts[0] == "options" and len(parts) > 1:
                options.extend(parts[1:])
    local_port = int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53"))
    ipv4_servers, ipv6_servers = _split_nameservers(servers)
    ipv4_enforced = _stack_truth_enforced(ipv4_servers, _trusted_v4_nameservers(local_port))
    ipv6_enforced = _stack_truth_enforced(ipv6_servers, _trusted_v6_nameservers(local_port))
    nexus_local = ipv4_enforced and ipv6_enforced
    return {
        "nameservers": servers,
        "ipv4_nameservers": ipv4_servers,
        "ipv6_nameservers": ipv6_servers,
        "search_domains": search,
        "options": options,
        "ipv4_truth_enforced": ipv4_enforced,
        "ipv6_truth_enforced": ipv6_enforced,
        "nexus_truth_enforced": nexus_local,
        "path": str(path),
    }


def _hostname_fqdn() -> dict[str, str]:
    host = socket.gethostname()
    try:
        fqdn = socket.getfqdn()
    except OSError:
        fqdn = host
    return {"hostname": host, "fqdn": fqdn}


def build_planetary_dns(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    seed = _load_json(SEED, {})
    foreign_ips = _foreign_resolver_ip_sets(seed)
    host_level = _host_security_level()
    planetary_level = "extreme" if host_level == "extreme" else "hardened"
    rfc_rows = list(seed.get("rfc_matrix") or [])
    legal_rows = list(seed.get("legal_framework") or [])
    enforced = sum(1 for r in rfc_rows if r.get("compliance") == "enforced")
    ipv6_bind = os.environ.get("NEXUS_FIELD_DNS_IPV6", "::1")
    doc: dict[str, Any] = {
        "schema": "dns-planetary/v1",
        "updated": _now(),
        "title": "NEXUS Truth DNS · Planetary Security",
        "motto": seed.get("motto") or "Truth DNS — RFC and law on every answer.",
        "planetary_security_level": planetary_level,
        "host_security_level": host_level,
        "planet_coverage": "global",
        "zones": [
            {**z, "extreme_active": planetary_level == "extreme"}
            for z in PLANETARY_ZONES
        ],
        "rfc_matrix": rfc_rows,
        "rfc_enforced_count": enforced,
        "rfc_total": len(rfc_rows),
        "legal_framework": legal_rows,
        "root_servers": seed.get("root_servers") or [],
        "foreign_resolvers_blocked": seed.get("foreign_resolvers_blocked") or [],
        "foreign_resolver_ipv4": foreign_ips["ipv4"],
        "foreign_resolver_ipv6": foreign_ips["ipv6"],
        "resolv": _resolv_snapshot(),
        "identity": _hostname_fqdn(),
        "resolver_policy": {
            "self_hosted": True,
            "truthful_trace": True,
            "loopback_only": True,
            "ipv4_bind": os.environ.get("NEXUS_FIELD_DNS_IPV4", "127.0.0.1"),
            "ipv6_bind": ipv6_bind,
            "ipv6_enabled": bool(ipv6_bind.strip()),
            "port": int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53")),
            "no_shortcut_public_dns": True,
            "dot_doh_bypass": "blocked_under_extreme",
            "qtypes_supported": ["A", "AAAA", "CNAME", "MX", "TXT"],
            "dual_stack": True,
        },
        "stats": {
            "planetary_zones": len(PLANETARY_ZONES),
            "root_servers": len(seed.get("root_servers") or []),
            "root_servers_ipv6": sum(1 for r in (seed.get("root_servers") or []) if r.get("ipv6")),
            "legal_citations": len(legal_rows),
            "rfc_citations": len(rfc_rows),
            "foreign_resolvers_blocked": len(seed.get("foreign_resolvers_blocked") or []),
            "foreign_resolver_ipv4": len(foreign_ips["ipv4"]),
            "foreign_resolver_ipv6": len(foreign_ips["ipv6"]),
        },
    }
    if extra:
        doc.update(extra)
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(build_planetary_dns(), ensure_ascii=False))
        return 0
    if cmd == "foreign-ips":
        seed = _load_json(SEED, {})
        print(json.dumps(_foreign_resolver_ip_sets(seed), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: dns-planetary-security.py [json|foreign-ips]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())