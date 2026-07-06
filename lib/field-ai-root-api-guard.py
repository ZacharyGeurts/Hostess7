#!/usr/bin/env python3
"""AI root & API guard — full root for AI work only; cannot break system via root or APIs."""
from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-ai-root-api-guard-doctrine.json"
PANEL = STATE / "field-ai-root-api-guard-panel.json"
LEDGER = STATE / "field-ai-root-api-guard-ledger.jsonl"

_LOOPBACK = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1"})
_AI_CHANNELS = frozenset({"ai", "grok", "compiler", "machine", "secure_channel"})
_HUMAN_CHANNELS = frozenset({
    "keystroke", "voice", "typed", "paste", "human", "operator",
    "interject", "comment", "operator_comment", "user_message",
})
_FOREIGN_CHANNELS = frozenset({"c2", "malware", "bot", "automated", "scan"})
# ai_injection cooked — was stealing operator interjects from comments.
_STOLEN_INTERJECT_CHANNELS = frozenset({"ai_injection", "grok_injection", "harness_injection"})


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _is_loopback(peer: str) -> bool:
    if peer in _LOOPBACK or str(peer).startswith("127."):
        return True
    try:
        return ipaddress.ip_address(peer).is_loopback
    except ValueError:
        return False


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _secure_channel_active() -> bool:
    ai = _mod("lib/ai-integration-hook.py", "ai_hook")
    if ai and hasattr(ai, "secure_channel_active"):
        try:
            return bool(ai.secure_channel_active())
        except Exception:
            pass
    keys = (
        "NEXUS_AI_SECURE_CHANNEL",
        "QUEEN_AI_TELEMETRY_OK",
        "QUEEN_GROK_BUILD",
        "QUEEN_GROK_BUILD_SECURE",
    )
    return all(os.environ.get(k, "").strip().lower() in ("1", "true", "yes", "on") for k in keys)


def _verify_ai_token(body: dict[str, Any] | None, headers: dict[str, str] | None) -> bool:
    ai = _mod("lib/ai-integration-hook.py", "ai_hook")
    if not ai or not hasattr(ai, "_verify_ai_token"):
        return False
    try:
        return bool(ai._verify_ai_token(body or {}, headers))
    except Exception:
        return False


def classify_actor(
    *,
    channel: str = "machine",
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    peer: str = "127.0.0.1",
) -> dict[str, Any]:
    doc = doctrine()
    actors = doc.get("actor_channels") or {}
    hdrs = {k.lower(): v for k, v in (headers or {}).items()}
    ch = str(channel or "machine").lower()
    if hdrs.get("x-human-input") in ("1", "true", "yes"):
        ch = "keystroke"
    if hdrs.get("x-nexus-ai-actor") in ("1", "true", "yes", "ai", "grok"):
        ch = "ai"
    if ch in _FOREIGN_CHANNELS or ch in (actors.get("foreign") or []):
        kind = "foreign"
    elif ch in _HUMAN_CHANNELS or ch in (actors.get("human") or []):
        kind = "human"
    elif ch in _AI_CHANNELS or ch in (actors.get("ai") or []):
        kind = "ai"
    else:
        kind = "machine"
    ai_token_ok = _verify_ai_token(body, headers) if kind in ("ai", "machine") else False
    secure = _secure_channel_active()
    return {
        "channel": ch,
        "kind": kind,
        "loopback": _is_loopback(peer),
        "secure_channel": secure,
        "ai_token_ok": ai_token_ok,
        "ai_work_scope": kind == "ai" and secure and ai_token_ok and _is_loopback(peer),
    }


def _blocked_root(cmd: str) -> str | None:
    doc = doctrine()
    for pat in doc.get("blocked_root_patterns") or []:
        try:
            if re.search(pat, cmd, re.I):
                return pat
        except re.error:
            continue
    return None


def _blocked_api(*, path: str, method: str, body: dict[str, Any] | None) -> str | None:
    doc = doctrine()
    p = str(path or "").split("?", 1)[0]
    for prefix in doc.get("blocked_api_path_prefixes") or []:
        if p.startswith(str(prefix)):
            return f"path:{prefix}"
    action = str((body or {}).get("action") or "").lower()
    if action in frozenset(doc.get("blocked_api_actions") or []):
        return f"action:{action}"
    text = json.dumps(body or {}, default=str)
    for prot in doc.get("protected_system_paths") or []:
        if prot and prot in text and method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            return f"protected:{prot}"
    return None


def gate_access(
    *,
    system_id: str = "nexus",
    peer: str = "127.0.0.1",
    path: str = "",
    method: str = "GET",
    channel: str = "machine",
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    root_cmd: str = "",
) -> dict[str, Any]:
    """Fail-closed — AI cannot break the system via root or APIs anywhere."""
    doc = doctrine()
    policy = doc.get("policy") or {}
    actor = classify_actor(channel=channel, headers=headers, body=body, peer=peer)
    verdict_headers = doc.get("verdict_headers") or {}

    if policy.get("fail_closed") and actor["kind"] == "foreign":
        row = {
            "ok": False,
            "code": 403,
            "error": "foreign_actor_blocked",
            "actor": actor,
            "system_id": system_id,
            "fail_closed": True,
            "guard": "field-ai-root-api-guard/v1",
        }
        _append_ledger({"event": "block_foreign", **row})
        return row

    block_reason = _blocked_api(path=path, method=method, body=body)
    if block_reason and policy.get("destructive_blocked_everywhere", True):
        row = {
            "ok": False,
            "code": 403,
            "error": "destructive_api_blocked",
            "detail": block_reason,
            "actor": actor,
            "path": path,
            "method": method,
            "cannot_break_via_api": True,
            "guard": "field-ai-root-api-guard/v1",
        }
        _append_ledger({"event": "block_api", **row})
        return row

    if root_cmd:
        pat = _blocked_root(root_cmd)
        if pat and policy.get("cannot_break_via_root", True):
            row = {
                "ok": False,
                "code": 403,
                "error": "destructive_root_blocked",
                "detail": pat,
                "actor": actor,
                "cannot_break_via_root": True,
                "guard": "field-ai-root-api-guard/v1",
            }
            _append_ledger({"event": "block_root", **row})
            return row

    if actor["kind"] == "ai" or (actor["kind"] == "machine" and path.startswith("/api/")):
        if policy.get("loopback_ai_token_required") and not actor["loopback"]:
            return {
                "ok": False,
                "code": 403,
                "error": "ai_loopback_only",
                "actor": actor,
                "guard": "field-ai-root-api-guard/v1",
            }
        if actor["kind"] == "ai" and not actor["ai_work_scope"]:
            return {
                "ok": False,
                "code": 403,
                "error": "ai_work_scope_required",
                "detail": "secure_channel + ai_token + loopback",
                "actor": actor,
                "scope": policy.get("ai_root_scope"),
                "guard": "field-ai-root-api-guard/v1",
            }

    return {
        "ok": True,
        "code": 200,
        "actor": actor,
        "system_id": system_id,
        "path": path,
        "method": method,
        "ai_root_scope": policy.get("ai_root_scope"),
        "cannot_break_via_root": policy.get("cannot_break_via_root"),
        "cannot_break_via_api": policy.get("cannot_break_via_api"),
        "guard": "field-ai-root-api-guard/v1",
        "header_guard": verdict_headers.get("guard"),
        "header_scope": verdict_headers.get("scope"),
    }


def guard_root_command(cmd: str, *, channel: str = "machine", peer: str = "127.0.0.1") -> dict[str, Any]:
    return gate_access(peer=peer, channel=channel, root_cmd=cmd, system_id="root_shell")


def panel_json(*, write: bool = False) -> dict[str, Any]:
    doc = doctrine()
    out = {
        "ok": True,
        "schema": "field-ai-root-api-guard-panel/v1",
        "updated": _utc(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "policy": doc.get("policy"),
        "secure_channel": _secure_channel_active(),
        "blocked_api_actions": len(doc.get("blocked_api_actions") or []),
        "blocked_root_patterns": len(doc.get("blocked_root_patterns") or []),
        "protected_paths": len(doc.get("protected_system_paths") or []),
        "api": "/api/field-ai-root-api-guard",
    }
    if write:
        _save(PANEL, out)
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "gate").strip().lower()
    if action in ("gate", "check", "assess"):
        return gate_access(
            system_id=str(body.get("system_id") or "nexus"),
            peer=str(body.get("peer") or "127.0.0.1"),
            path=str(body.get("path") or ""),
            method=str(body.get("method") or "GET"),
            channel=str(body.get("channel") or "machine"),
            body=body.get("body") if isinstance(body.get("body"), dict) else body,
            headers=body.get("headers") if isinstance(body.get("headers"), dict) else None,
            root_cmd=str(body.get("root_cmd") or body.get("cmd") or ""),
        )
    if action in ("root", "root_cmd", "guard_root"):
        return guard_root_command(
            str(body.get("cmd") or body.get("root_cmd") or ""),
            channel=str(body.get("channel") or "machine"),
            peer=str(body.get("peer") or "127.0.0.1"),
        )
    if action in ("json", "panel", "posture", "status"):
        return panel_json(write=action == "panel")
    return {"ok": False, "error": "unknown_action", "guard": "field-ai-root-api-guard/v1"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            payload = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(payload), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "posture", "status"):
        print(json.dumps(panel_json(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "check-root" and len(sys.argv) > 2:
        print(json.dumps(guard_root_command(" ".join(sys.argv[2:])), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-ai-root-api-guard.py [json|panel|dispatch|check-root CMD...]",
        "api": "/api/field-ai-root-api-guard",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())