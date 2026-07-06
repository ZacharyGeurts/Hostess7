#!/usr/bin/env python3
"""Root status — telnet/SSH/CSS safe read-only posture. No PID spawn. No PID fields."""
from __future__ import annotations

import json
import os
import re
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-root-status-panel.json"
_PID_KEYS = re.compile(r"^(pid|pids|.*_pid|parent_pid|spawn_pid)$", re.I)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _strip_pids(obj: Any) -> Any:
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if _PID_KEYS.match(str(k)):
                continue
            out[k] = _strip_pids(v)
        return out
    if isinstance(obj, list):
        return [_strip_pids(x) for x in obj]
    return obj


def _port_open(port: int, host: str = "127.0.0.1") -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.settimeout(0.4)
        sock.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _service_posture() -> dict[str, Any]:
    dns_panel = _load(STATE / "field-dns-panel.json", _load(STATE / "field-dns.json", {}))
    dhcp_panel = _load(STATE / "field-dhcp-panel.json", {})
    watch_panel = _load(STATE / "field-watch-dhcp-panel.json", {})
    never_panel = _load(STATE / "field-never-down-panel.json", {})
    takeover = _load(STATE / "dns-takeover-state.json", {})
    return _strip_pids({
        "dns": {
            "running": bool(dns_panel.get("running")),
            "healthy": bool(dns_panel.get("running")) and _port_open(53),
            "listeners": dns_panel.get("listeners") or [],
            "truthful": dns_panel.get("truthful", True),
        },
        "dhcp": {
            "running": bool(dhcp_panel.get("running")),
            "may_serve": bool(dhcp_panel.get("may_serve")),
            "port_67": bool(dhcp_panel.get("port_67")),
            "takeover_phase": dhcp_panel.get("takeover_phase") or takeover.get("phase"),
        },
        "dhcp_watch": {
            "observe_only": True,
            "automated": bool(watch_panel.get("automated")),
            "ok": bool(watch_panel.get("ok")),
        },
        "field_one": {
            "hub_id": (never_panel.get("services") or {}).get("hub_id") or "field-1",
            "never_go_down": bool(never_panel.get("never_go_down")),
            "ok": bool(never_panel.get("ok")),
        },
        "takeover": {
            "phase": takeover.get("phase") or "unknown",
            "motto": takeover.get("motto"),
        },
    })


def status(*, write: bool = True) -> dict[str, Any]:
    host = socket.gethostname()
    services = _service_posture()
    out = {
        "ok": True,
        "schema": "field-root-status/v1",
        "updated": _utc(),
        "motto": "Root is status only — telnet · SSH · CSS. No PID spawn. No PID fields.",
        "host": host,
        "field_one": "field-1",
        "mode": "status_only",
        "spawn_guard": True,
        "services": services,
        "channels": {
            "telnet": "GET / Accept: text/plain",
            "ssh": "field-root-status.py telnet",
            "json": "/api/root-status",
            "css": "/field-root-status",
        },
        "api": "/api/root-status",
    }
    if write:
        tmp = PANEL.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL)
    return out


def telnet_text() -> str:
    doc = status(write=False)
    svc = doc.get("services") or {}
    dns = svc.get("dns") or {}
    dhcp = svc.get("dhcp") or {}
    lines = [
        "╔══════════════════════════════════════════════════════╗",
        "║  FIELD ROOT STATUS — read-only · no PID spawn        ║",
        "╚══════════════════════════════════════════════════════╝",
        f" host .......... {doc.get('host')}",
        f" field ......... {doc.get('field_one')}",
        f" updated ....... {doc.get('updated')}",
        "",
        " DNS",
        f"   running ..... {'YES' if dns.get('running') else 'NO'}",
        f"   healthy ..... {'YES' if dns.get('healthy') else 'NO'}",
        f"   listeners ... {', '.join(dns.get('listeners') or []) or '—'}",
        "",
        " DHCP",
        f"   running ..... {'YES' if dhcp.get('running') else 'NO'}",
        f"   port 67 ..... {'YES' if dhcp.get('port_67') else 'NO'}",
        f"   may_serve ... {'YES' if dhcp.get('may_serve') else 'NO'}",
        f"   takeover .... {dhcp.get('takeover_phase') or '—'}",
        "",
        " channels: telnet · ssh · json · css",
        " spawn guard: ON — nothing outside us starts PIDs",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("telnet", "text", "motd", "status"):
        print(telnet_text())
        return 0
    if cmd in ("json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-root-status.py [telnet|json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())