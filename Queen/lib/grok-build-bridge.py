#!/usr/bin/env pythong
"""Queen Grok Build bridge — secure ACP channel + branded in-engine page."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
MANDATE_PATHS = (
    QUEEN / "data" / "grok-build-mandate.json",
    INSTALL / "data" / "grok-build-mandate.json",
    STATE / "grok-build-mandate.json",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def load_mandate() -> dict[str, Any]:
    for p in MANDATE_PATHS:
        doc = _load_json(p, {})
        if doc.get("schema") == "grok-build-mandate/v1":
            return doc
    return {}


def _env_ok(key: str) -> bool:
    return os.environ.get(key, "") in ("1", "true", "yes", "on")


def secure_channel_active() -> bool:
    mandate = load_mandate()
    required = mandate.get("secure_channel", {}).get("required_env") or [
        "NEXUS_AI_SECURE_CHANNEL",
        "QUEEN_AI_TELEMETRY_OK",
        "QUEEN_GROK_BUILD",
        "QUEEN_GROK_BUILD_SECURE",
    ]
    return all(_env_ok(k) for k in required)


def _acp_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _load_theme() -> dict[str, Any]:
    for p in (QUEEN / "gui" / "queen-theme-2026.json", INSTALL / "Queen/gui/queen-theme-2026.json"):
        doc = _load_json(p, {})
        if doc.get("schema") == "queen-gui/v1":
            return doc
    return {}


def branded_page() -> dict[str, Any]:
    mandate = load_mandate()
    bp = dict(mandate.get("branded_page") or {})
    theme = _load_theme()
    qr = str(QUEEN)
    embed = (bp.get("embed_panel") or "").replace("{queen_root}", qr)
    return {
        **bp,
        "queen_root": qr,
        "embed_panel": embed,
        "colors": theme.get("colors") or {},
        "partner": mandate.get("partner", "xAI / X"),
        "title": bp.get("title", "Queen · Grok Build"),
    }


def posture() -> dict[str, Any]:
    mandate = load_mandate()
    acp = mandate.get("acp") or {}
    host = str(acp.get("bind") or "127.0.0.1")
    port = int(acp.get("port") or 2419)
    secure = secure_channel_active()
    return {
        "schema": "grok-build-bridge/v1",
        "updated": _now(),
        "title": mandate.get("title", "Queen · Grok Build Secure Channel"),
        "partner": mandate.get("partner"),
        "motto": mandate.get("motto"),
        "secure_channel": secure,
        "secure_channel_env": {
            k: _env_ok(k)
            for k in (mandate.get("secure_channel", {}).get("required_env") or [])
        },
        "allowed_hosts": mandate.get("allowed_hosts") or [],
        "iff": mandate.get("iff") or {},
        "acp": {
            **acp,
            "reachable": _acp_port_open(host, port) if secure else False,
            "ws_url": f"ws://{host}:{port}" if secure else None,
        },
        "branded_page": branded_page(),
        "in_engine": True,
        "zero_telemetry_elsewhere": mandate.get("secure_channel", {}).get("zero_telemetry_elsewhere", True),
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json", "posture"):
        return {"ok": True, **posture()}
    if action in ("branded-page", "branded_page", "page"):
        return {"ok": True, "page": branded_page(), "posture": posture()}
    if action in ("enable-secure", "enable_secure"):
        for k in ("NEXUS_AI_SECURE_CHANNEL", "QUEEN_AI_TELEMETRY_OK", "QUEEN_GROK_BUILD", "QUEEN_GROK_BUILD_SECURE"):
            os.environ[k] = "1"
        return {"ok": True, "secure_channel": secure_channel_active(), "posture": posture()}
    if action in ("acp-status", "acp_status"):
        p = posture()
        return {"ok": True, "acp": p["acp"], "secure_channel": p["secure_channel"]}
    if action in ("acp-start", "acp_start", "start"):
        if not secure_channel_active():
            return {"ok": False, "error": "secure_channel_inactive", "hint": "Set NEXUS_AI_SECURE_CHANNEL + QUEEN_AI_TELEMETRY_OK + QUEEN_GROK_BUILD_SECURE"}
        mandate = load_mandate()
        acp = mandate.get("acp") or {}
        cli = str(acp.get("cli") or "grok agent serve --bind 127.0.0.1:2419")
        secret = body.get("secret") or os.environ.get("GROK_AGENT_SECRET") or ""
        cmd = cli.split()
        if secret and "--secret" not in cmd:
            cmd.extend(["--secret", str(secret)])
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(QUEEN),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "QUEEN_ROOT": str(QUEEN)},
            )
            return {"ok": True, "pid": proc.pid, "cmd": cmd, "posture": posture()}
        except FileNotFoundError:
            return {"ok": False, "error": "grok_cli_missing", "cmd": cmd}
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(posture(), ensure_ascii=False))
        return 0
    if cmd == "page":
        print(json.dumps(branded_page(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: grok-build-bridge.py [json|page|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())