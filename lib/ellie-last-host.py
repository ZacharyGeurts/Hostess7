#!/usr/bin/env pythong
"""ELLIE Last Host — survivor DNS+DHCP+TIME posture (feeds ELLIE security authority)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def last_host_posture() -> dict[str, Any]:
    enabled = os.environ.get("NEXUS_LAST_HOST", "0").strip() in ("1", "true", "yes")
    services = _load(STATE / "field-services-2026-panel.json", {})
    dns = services.get("dns") or {}
    dhcp = services.get("dhcp") or {}
    ntp = services.get("ntp") or {}
    sync = services.get("sovereign_sync") or {}
    live = bool(dns.get("ok") or dhcp.get("ok") or ntp.get("ok"))
    return {
        "schema": "ellie-last-host/v1",
        "ok": enabled or live,
        "enabled": enabled,
        "role": "ELLIE survivor perimeter — loopback-first DNS · DHCP · sovereign time",
        "dns_ok": bool(dns.get("ok")),
        "dhcp_ok": bool(dhcp.get("ok")),
        "ntp_ok": bool(ntp.get("ok")),
        "sync_ok": bool(sync.get("ok")),
        "loopback_dns": (services.get("posture") or {}).get("loopback_dns_default"),
        "public_blocked": not (services.get("posture") or {}).get("dhcp_lan_only") is False,
        "verdict": "armed" if enabled and live else ("watch" if enabled else "standby"),
        "ellie_feed": "sovereign.last_host",
    }


def main() -> int:
    print(json.dumps(last_host_posture(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())