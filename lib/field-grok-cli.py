#!/usr/bin/env pythong
"""Field Grok CLI — secure JSON surface for the operator UI (loopback ACP + launch)."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
GROK_HOME = Path(os.environ.get("GROK_HOME", Path.home() / ".grok"))
TOKEN_PATH = Path(os.environ.get("FIELD_GROK_TOKEN_PATH", Path.home() / ".config/sg/field-grok-token"))
MANDATE_PATHS = (
    INSTALL / "data" / "grok-build-mandate.json",
    INSTALL / "Queen" / "data" / "grok-build-mandate.json",
    STATE / "grok-build-mandate.json",
)
PANEL = STATE / "field-grok-cli-panel.json"
VERSION = "1.0.0"
SCHEMA = "field-grok-cli/v1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _env_ok(key: str) -> bool:
    return os.environ.get(key, "") in ("1", "true", "yes", "on")


def load_mandate() -> dict[str, Any]:
    for p in MANDATE_PATHS:
        doc = _load_json(p, {})
        if doc.get("schema") == "grok-build-mandate/v1":
            return doc
    return {}


def _secure_env_keys() -> list[str]:
    mandate = load_mandate()
    return list(mandate.get("secure_channel", {}).get("required_env") or [
        "NEXUS_AI_SECURE_CHANNEL",
        "QUEEN_AI_TELEMETRY_OK",
        "QUEEN_GROK_BUILD",
        "QUEEN_GROK_BUILD_SECURE",
    ])


def secure_channel_active() -> bool:
    return all(_env_ok(k) for k in _secure_env_keys())


def _apply_secure_env() -> None:
    for k in _secure_env_keys():
        os.environ[k] = "1"
    os.environ.setdefault("GROK_SECURE_CHANNEL", "1")
    os.environ.setdefault("GROK_MAX_SOCKETS", "5")
    os.environ.setdefault("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt")
    os.environ.setdefault("REQUESTS_CA_BUNDLE", os.environ["SSL_CERT_FILE"])
    for proxy in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        os.environ.pop(proxy, None)


def _operator_token() -> str:
    env = os.environ.get("FIELD_GROK_OPERATOR_TOKEN", "").strip()
    if env:
        return env
    if TOKEN_PATH.is_file():
        return TOKEN_PATH.read_text(encoding="utf-8").strip()
    return ""


def ensure_operator_token() -> str:
    token = _operator_token()
    if token:
        return token
    token = secrets.token_urlsafe(32)
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(token + "\n", encoding="utf-8")
    os.chmod(TOKEN_PATH, 0o600)
    return token


def _token_ok(body: dict[str, Any]) -> bool:
    if os.environ.get("FIELD_GROK_HUMAN_LOOPBACK") == "1":
        return True
    mandate = load_mandate()
    if not mandate.get("secure_channel", {}).get("operator_token_required", True):
        return True
    supplied = str(body.get("token") or body.get("operator_token") or "").strip()
    if not supplied:
        supplied = str(os.environ.get("FIELD_GROK_OPERATOR_TOKEN", "")).strip()
    expected = _operator_token()
    if not expected:
        expected = ensure_operator_token()
    return secrets.compare_digest(supplied, expected)


def _acp_port_open(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _grok_real() -> str | None:
    real = os.environ.get("GROK_REAL_BIN", "").strip()
    if real and Path(real).is_file():
        return real
    home = GROK_HOME
    for candidate in (
        home / "downloads" / "grok-0.2.67-linux-x86_64",
        home / "bin" / "grok.real",
    ):
        if candidate.is_file():
            return str(candidate)
    for candidate in sorted(home.glob("downloads/grok-*-linux-x86_64")):
        if candidate.is_file():
            return str(candidate)
    return None


def _socket_limit_status() -> dict[str, Any]:
    log = GROK_HOME / "socket-limit.log"
    tail: list[str] = []
    if log.is_file():
        try:
            tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-8:]
        except OSError:
            pass
    return {
        "max_sockets": int(os.environ.get("GROK_MAX_SOCKETS", "5") or "5"),
        "log": str(log),
        "tail": tail,
    }


def posture() -> dict[str, Any]:
    mandate = load_mandate()
    acp = mandate.get("acp") or {}
    host = str(acp.get("bind") or "127.0.0.1")
    port = int(acp.get("port") or 2419)
    secure = secure_channel_active()
    binary = INSTALL / "lib" / "bin" / "field-grok"
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "updated": _now(),
        "title": "Field Grok — secure operator CLI",
        "motto": "Loopback ACP · system CA · socket cap · operator token",
        "binary": str(binary) if binary.is_file() else "lib/bin/field-grok",
        "grok_real": _grok_real(),
        "secure_channel": secure,
        "secure_channel_env": {k: _env_ok(k) for k in _secure_env_keys()},
        "operator_token_present": bool(_operator_token()),
        "operator_token_path": str(TOKEN_PATH),
        "allowed_hosts": mandate.get("allowed_hosts") or [],
        "acp": {
            **acp,
            "reachable": _acp_port_open(host, port) if secure else False,
            "ws_url": f"ws://{host}:{port}" if secure else None,
        },
        "socket_limit": _socket_limit_status(),
        "api": "/api/field-grok",
        "cli": {
            "json": "field-grok json",
            "dispatch": "field-grok dispatch",
            "launch": "field-grok launch",
        },
    }


def _write_panel(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = posture()
    if extra:
        doc.update(extra)
    _save_json(PANEL, doc)
    return doc


def _run_launch(extra_args: list[str] | None = None) -> dict[str, Any]:
    launch = INSTALL / "lib" / "grok-launch.sh"
    if not launch.is_file():
        return {"ok": False, "error": "grok_launch_missing", "path": str(launch)}
    _apply_secure_env()
    cmd = ["bash", str(launch), *(extra_args or [])]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(INSTALL),
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        out, err = proc.communicate(timeout=8)
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": (out or "").strip()[-2000:],
            "stderr": (err or "").strip()[-2000:],
            "cmd": cmd,
            "posture": posture(),
        }
    except subprocess.TimeoutExpired:
        return {"ok": True, "launched": True, "async": True, "cmd": cmd, "posture": posture()}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}


def _acp_start(body: dict[str, Any]) -> dict[str, Any]:
    if not secure_channel_active():
        _apply_secure_env()
    if not secure_channel_active():
        return {
            "ok": False,
            "error": "secure_channel_inactive",
            "hint": "Set NEXUS_AI_SECURE_CHANNEL + QUEEN_GROK_BUILD_SECURE or action enable-secure",
        }
    mandate = load_mandate()
    acp = mandate.get("acp") or {}
    cli = str(acp.get("cli") or "grok agent serve --bind 127.0.0.1:2419")
    secret = str(body.get("secret") or os.environ.get("GROK_AGENT_SECRET") or "")
    cmd = cli.split()
    if secret and "--secret" not in cmd:
        cmd.extend(["--secret", secret])
    if cmd and cmd[0] == "grok":
        real = _grok_real()
        if real:
            cmd[0] = real
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(INSTALL),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL)},
        )
        return {"ok": True, "pid": proc.pid, "cmd": cmd, "posture": posture()}
    except FileNotFoundError:
        return {"ok": False, "error": "grok_cli_missing", "cmd": cmd}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    sensitive = action in {
        "launch", "acp_start", "start", "message", "chat", "enable_secure",
    }
    if sensitive and not _token_ok(body):
        return {"ok": False, "error": "operator_token_required", "token_path": str(TOKEN_PATH)}

    if action in ("status", "json", "posture"):
        return {"ok": True, **_write_panel()}
    if action in ("enable_secure",):
        _apply_secure_env()
        return {"ok": True, "secure_channel": secure_channel_active(), **posture()}
    if action in ("token", "operator_token"):
        token = ensure_operator_token()
        return {
            "ok": True,
            "token_path": str(TOKEN_PATH),
            "token_hint": token[:6] + "…" if token else "",
            "posture": posture(),
        }
    if action in ("launch",):
        args = body.get("args") or []
        if not isinstance(args, list):
            args = []
        return _run_launch([str(a) for a in args])
    if action in ("acp_start", "start"):
        return _acp_start(body)
    if action in ("message", "chat", "selftalk", "self_talk", "ping"):
        text = str(body.get("message") or body.get("text") or "").strip()
        if action in ("ping",) and not text:
            text = "Reply with exactly: FIELD_GROK_PONG"
        if not text:
            return {"ok": False, "error": "message_required"}
        _apply_secure_env()
        try:
            from field_grok_selftalk import selftalk as _selftalk
        except ImportError:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "field_grok_selftalk",
                INSTALL / "lib" / "field-grok-selftalk.py",
            )
            if not spec or not spec.loader:
                return {"ok": False, "error": "selftalk_module_missing"}
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _selftalk = mod.selftalk
        result = _selftalk(text, cwd=str(body.get("cwd") or INSTALL))
        return {"ok": result.get("ok", False), **result, "posture": posture()}
    if action in ("socket_status", "socket"):
        return {"ok": True, "socket_limit": _socket_limit_status(), "posture": posture()}
    return {"ok": False, "error": "unknown_action", "action": action}


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
        print(json.dumps(_write_panel(), ensure_ascii=False))
        return 0
    if cmd == "token":
        ensure_operator_token()
        print(json.dumps({"ok": True, "token_path": str(TOKEN_PATH)}, ensure_ascii=False))
        return 0
    if cmd == "version":
        print(json.dumps({"schema": SCHEMA, "version": VERSION, "sha": hashlib.sha256(VERSION.encode()).hexdigest()[:12]}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-grok-cli.py [json|dispatch|token|version]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())