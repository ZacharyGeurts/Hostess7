#!/usr/bin/env pythong
"""AmmoNet DNS zones — Truth DNS + Field DHCP integration for all ammonet TLDs."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "ammonet-dns-zones.json"
PANEL = STATE / "ammonet-dns-zones-panel.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def dhcp_domain() -> str:
    return str(doctrine().get("dhcp_domain") or "ammonet.net")


def dhcp_search_domains() -> list[str]:
    doc = doctrine()
    search = list(doc.get("dhcp_search") or [])
    if search:
        return search
    zones = [str(z.get("zone") or "") for z in (doc.get("zones") or []) if z.get("zone")]
    return zones or ["ammonet.net", "ammonet.com"]


def all_zones() -> list[dict[str, Any]]:
    return list(doctrine().get("zones") or [])


def record_count() -> int:
    return sum(len(z.get("records") or []) for z in all_zones())


def resolve_local(qname: str) -> dict[str, Any] | None:
    """Match qname against AmmoNet static zones (loopback truth)."""
    q = (qname or "").strip().lower().rstrip(".")
    if not q:
        return None
    for zone in all_zones():
        zname = str(zone.get("zone") or "").lower()
        for rec in zone.get("records") or []:
            rname = str(rec.get("name") or "@").lower()
            fq = zname if rname == "@" else f"{rname}.{zname}"
            if q == fq or q == zname and rname == "@":
                return {
                    "ok": True,
                    "qname": q,
                    "zone": zname,
                    "type": rec.get("type"),
                    "value": rec.get("value"),
                    "ttl": rec.get("ttl", 300),
                    "authority": "ammonet_truth_dns",
                }
    return None


def planetary_slice() -> dict[str, Any]:
    doc = doctrine()
    return {
        "region": "AmmoNet sovereign",
        "tld_group": " ".join(doc.get("tlds") or [".com", ".net", ".org"]),
        "security_level": "extreme",
        "rfc": "RFC 1035 · field-sovereign",
        "legal": "Operator-owned · All Rights Reserved",
        "note": "Truth DNS hosts ammonet.* — DHCP option 6 + domain search wired",
        "zones": len(all_zones()),
        "records": record_count(),
    }


def panel(*, write: bool = True) -> dict[str, Any]:
    doc = doctrine()
    out = {
        "ok": True,
        "schema": "ammonet-dns-zones-panel/v1",
        "updated": _utc(),
        "product": doc.get("product", "AmmoNet"),
        "motto": doc.get("motto"),
        "dhcp_domain": dhcp_domain(),
        "dhcp_search": dhcp_search_domains(),
        "mail_host": doc.get("mail_host"),
        "zones": all_zones(),
        "zone_count": len(all_zones()),
        "record_count": record_count(),
        "planetary": planetary_slice(),
        "api": "/api/ammonet/dns-zones",
    }
    if write:
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        tmp = PANEL.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL)
    return out


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve" and len(sys.argv) > 2:
        print(json.dumps(resolve_local(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dhcp":
        print(json.dumps({
            "domain": dhcp_domain(),
            "search": dhcp_search_domains(),
        }, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "ammonet-dns-zones.py [panel|resolve QNAME|dhcp]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())