#!/usr/bin/env pythong
"""Field Services 2026 — Grok rewrite manifest for public DNS, DHCP, and time.

Unifies secure defaults, retired-vuln list, and panel slice for threat-panel.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
SEED = INSTALL / "data" / "field-services-2026-seed.json"
PANEL = STATE / "field-services-2026-panel.json"


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


def _mod(name: str, rel: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, INSTALL / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _slice(name: str, rel: str, cmd: str = "json") -> dict[str, Any]:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return {"error": f"missing:{rel}"}
    try:
        return _mod(name, rel).panel_json()
    except Exception as exc:
        return {"error": str(exc), "module": rel}


def build_panel() -> dict[str, Any]:
    seed = _load_json(SEED, {"schema": "field-services-2026/v1"})
    dns = _slice("field_dns", "field-dns.py")
    dhcp = _slice("field_dhcp", "field-dhcp.py")
    ntp = _slice("field_ntp", "field-ntp-2026.py")
    sovereign = _slice("sovereign_time", "sovereign-time.py")
    clock = _mod("sovereign_clock", "sovereign-clock.py").know()
    gate = _slice("sovereign_gate", "field-sovereign-gate.py")
    sync = _slice("sovereign_sync", "field-sovereign-sync.py")
    ellie = _slice("ellie_last_host", "ellie-last-host.py")
    doc = {
        "schema": "field-services-2026/v1",
        "updated": _now(),
        "edition": seed.get("edition") or "Grok rewrite 2026",
        "motto": seed.get("motto"),
        "vulnerabilities_retired": seed.get("vulnerabilities_retired") or [],
        "public_exposure": seed.get("public_exposure") or {},
        "policy": seed,
        "dns": dns,
        "dhcp": dhcp,
        "ntp": ntp,
        "sovereign_time": sovereign,
        "sovereign_clock": clock,
        "sovereign_gate": gate,
        "sovereign_sync": sync,
        "never_desync": True,
        "synced": bool(clock.get("synced")) if isinstance(clock, dict) else False,
        "security_model": seed.get("security_model") or {},
        "sync_doctrine": _load_json(INSTALL / "data" / "field-sovereign-sync-doctrine.json", {}),
        "ellie_last_host": ellie,
        "posture": {
            "loopback_dns_default": os.environ.get("NEXUS_FIELD_DNS_BINDS_IPV4", "127.0.0.1").startswith("127."),
            "dhcp_lan_only": os.environ.get("NEXUS_FIELD_SERVICES_PUBLIC", "0") != "1",
            "sovereign_first": os.environ.get("NEXUS_SOVEREIGN_TIME_FIRST", "1") == "1",
            "never_lose_cycle": True,
            "pool_ntp_fallback": os.environ.get("NEXUS_POOL_NTP_FALLBACK", "0") == "1",
            "last_host": os.environ.get("NEXUS_LAST_HOST", "0") == "1",
        },
        "servers": {
            "dns": (dns.get("servers") or {}).get("dns") or dns.get("ipv4"),
            "dhcp": (dns.get("servers") or {}).get("dhcp") or dhcp,
            "ntp": ntp,
            "sovereign_udp": sovereign.get("port") or int(os.environ.get("NEXUS_SOVEREIGN_TIME_PORT", "9123")),
        },
    }
    _save_json(PANEL, doc)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL.is_file():
        try:
            return json.loads(PANEL.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return build_panel()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-services-2026.py [build|json]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())