#!/usr/bin/env pythong
"""Field secure email — Apache rewrite lane; sovereign SMTP/IMAP on AmmoNet domains."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-secure-email-doctrine.json"
APACHE_CONF = INSTALL / "config" / "field-secure-email-apache.conf"
PANEL = STATE / "field-secure-email-panel.json"
LEDGER = STATE / "field-secure-email.jsonl"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _ammonet_zones() -> dict[str, Any]:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("ammonet_dns_zones", INSTALL / "lib" / "ammonet-dns-zones.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "panel"):
                return mod.panel(write=False)
    except Exception:
        pass
    return {}


def apache_rewrite_status() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    conf_ok = APACHE_CONF.is_file()
    text = APACHE_CONF.read_text(encoding="utf-8", errors="replace") if conf_ok else ""
    return {
        "ok": conf_ok,
        "config": str(APACHE_CONF),
        "rewrite_enabled": "RewriteEngine On" in text,
        "mail_proxy": "ProxyPass" in text or "mod_proxy" in text,
        "human_web_disabled": bool((doc.get("posture") or {}).get("human_web_disabled")),
        "ports": (doc.get("apache") or {}).get("ports") or {},
        "install_hint": "Include config/field-secure-email-apache.conf in Apache sites-enabled",
    }


def panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    zones = _ammonet_zones()
    out = {
        "ok": True,
        "schema": "field-secure-email-panel/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "domains": doc.get("domains") or [],
        "bind": doc.get("bind", "127.0.0.1"),
        "posture": doc.get("posture") or {},
        "apache": apache_rewrite_status(),
        "ammonet_dns": {
            "zone_count": zones.get("zone_count"),
            "mail_host": zones.get("mail_host"),
            "dhcp_domain": zones.get("dhcp_domain"),
        },
        "api": doc.get("api"),
    }
    if write:
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        tmp = PANEL.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL)
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "panel", "json"):
        return panel(write=True)
    if action == "apache":
        return {"ok": True, **apache_rewrite_status()}
    return {"ok": False, "error": "unknown_action", "actions": ["status", "apache"]}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "apache":
        print(json.dumps(apache_rewrite_status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-secure-email.py [panel|apache]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())