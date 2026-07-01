#!/usr/bin/env pythong
"""NEXUS AI Integration Hook — field compiler + Grok build; human integration forbidden."""
from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
QUEEN = INSTALL.parent / "Queen"
HOOK_FILE = STATE / "ai-integration-hook.json"
TOKEN_FILE = STATE / "ai-integration.token"

AI_REQUIRED_ENV = (
    "NEXUS_AI_SECURE_CHANNEL",
    "QUEEN_AI_TELEMETRY_OK",
    "QUEEN_GROK_BUILD",
    "QUEEN_GROK_BUILD_SECURE",
)

HUMAN_FORBIDDEN_ACTIONS = frozenset({
    "integrate", "hook", "board", "drive", "ocr_click", "click", "tab", "navigate",
    "inject", "synthetic", "xdotool", "keyboard_hook", "pointer_hook",
})


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



def _env_ok(key: str) -> bool:
    return os.environ.get(key, "").strip().lower() in ("1", "true", "yes", "on")


def secure_channel_active() -> bool:
    return all(_env_ok(k) for k in AI_REQUIRED_ENV)


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


def _integration_token() -> str:
    if TOKEN_FILE.is_file():
        try:
            tok = TOKEN_FILE.read_text(encoding="utf-8").strip()
            if len(tok) >= 32:
                return tok
        except OSError:
            pass
    tok = secrets.token_hex(32)
    try:
        TOKEN_FILE.write_text(tok + "\n", encoding="utf-8")
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    return tok


def human_forbidden(reason: str, *, detail: str = "") -> dict[str, Any]:
    return {
        "ok": False,
        "error": "human_integration_forbidden",
        "reason": reason,
        "detail": detail,
        "policy": "ai_only_integration",
        "human_allowed": False,
        "ai_required_env": list(AI_REQUIRED_ENV),
    }


def hook_default() -> dict[str, Any]:
    return {
        "schema": "nexus-ai-integration-hook/v1",
        "owner": "nexus",
        "boarded": True,
        "policy": "ai_only_never_human",
        "secure_channel": secure_channel_active(),
        "field_compiler": True,
        "grok_build": True,
        "human_integration": False,
        "updated": _now(),
    }


def read_hook() -> dict[str, Any]:
    doc = hook_default()
    if HOOK_FILE.is_file():
        raw = _load_json(HOOK_FILE, {})
        if isinstance(raw, dict):
            doc.update(raw)
    doc["secure_channel"] = secure_channel_active()
    doc["human_integration"] = False
    doc["updated"] = _now()
    return doc


def board_once() -> dict[str, Any]:
    doc = read_hook()
    doc["boarded"] = True
    doc["token_hint"] = "loopback_ai_only"
    _save_json(HOOK_FILE, doc)
    _integration_token()
    return doc


def _verify_ai_token(body: dict[str, Any], headers: dict[str, str] | None = None) -> bool:
    if not secure_channel_active():
        return False
    expected = _integration_token()
    hdrs = headers or {}
    supplied = (
        str(body.get("ai_token") or body.get("token") or "").strip()
        or str(hdrs.get("X-Nexus-AI-Token") or hdrs.get("x-nexus-ai-token") or "").strip()
    )
    if not supplied:
        return False
    return secrets.compare_digest(supplied, expected)


def _run_py(script: Path, mode: str, body: dict[str, Any] | None = None, timeout: int = 120) -> dict[str, Any]:
    import subprocess

    if not script.is_file():
        return {"ok": False, "error": "script_missing", "path": str(script)}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    if mode == "dispatch":
        proc = subprocess.run(
            [sys.executable, str(script), "dispatch"],
            input=json.dumps(body or {}, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    else:
        proc = subprocess.run(
            [sys.executable, str(script), mode],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    try:
        out = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        out = {"ok": False, "error": (proc.stderr or proc.stdout or "bad_json")[:400]}
    if isinstance(out, dict):
        out.setdefault("ok", proc.returncode == 0)
    return out


def integrate(
    body: dict[str, Any],
    *,
    peer: str = "127.0.0.1",
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "posture"):
        doc = read_hook()
        doc["ok"] = True
        return doc

    if action in HUMAN_FORBIDDEN_ACTIONS:
        return human_forbidden("human_action_blocked", detail=action)

    if not str(peer).startswith("127.") and peer not in ("::1", "::ffff:127.0.0.1"):
        return human_forbidden("non_loopback")

    if not secure_channel_active():
        return human_forbidden("secure_channel_inactive")

    if not _verify_ai_token(body, headers):
        return human_forbidden("ai_token_required", detail="loopback AI secure channel token only")

    if action in ("compiler", "field_compiler", "compiler_probe", "probe"):
        dispatch_body = dict(body.get("dispatch") or body.get("compiler") or {})
        if not dispatch_body.get("action"):
            dispatch_body["action"] = str(body.get("compiler_action") or "probe").strip().lower()
        script = QUEEN / "lib" / "queen-field-compiler.py"
        if not script.is_file():
            script = INSTALL / "Queen" / "lib" / "queen-field-compiler.py"
        result = _run_py(script, "dispatch", dispatch_body, timeout=300)
        return {"ok": result.get("ok", False), "integration": "field_compiler", "result": result, "updated": _now()}

    if action in ("grok_build", "grok", "acp"):
        dispatch_body = dict(body.get("dispatch") or body.get("grok") or {})
        if not dispatch_body.get("action"):
            dispatch_body["action"] = str(body.get("grok_action") or "posture").strip().lower()
        for script in (
            QUEEN / "lib" / "grok-build-bridge.py",
            INSTALL / "lib" / "grok-build-bridge.py",
            INSTALL.parent / "Queen" / "lib" / "grok-build-bridge.py",
        ):
            if script.is_file():
                result = _run_py(script, "dispatch", dispatch_body, timeout=120)
                return {"ok": result.get("ok", False), "integration": "grok_build", "result": result, "updated": _now()}
        return {"ok": False, "error": "grok_build_bridge_missing"}

    return human_forbidden("unknown_action", detail=action)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "board":
        print(json.dumps(board_once(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps(human_forbidden("bad_json"), ensure_ascii=False))
            return 1
        peer = str(body.pop("_peer", "127.0.0.1"))
        headers = body.pop("_headers", None)
        print(json.dumps(integrate(body, peer=peer, headers=headers), ensure_ascii=False))
        return 0
    print(json.dumps(read_hook(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())