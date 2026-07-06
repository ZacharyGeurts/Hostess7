#!/usr/bin/env python3
"""Secure per-rack Grok chat — dropdown target, probe pickup, tunnel/SSH dispatch."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import secrets
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
TOKEN_PATH = Path(os.environ.get("FIELD_GROK_TOKEN_PATH", Path.home() / ".config/sg/field-grok-token"))
PANEL = STATE / "field-rack-grok-chat-panel.json"
SCHEMA = "field-rack-grok-chat/v1"
PICKUP_RE = re.compile(r"(PICKUP|PONG|FIELD_GROK|hello|ack|here|listening)", re.I)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def _operator_token() -> str:
    env = os.environ.get("FIELD_GROK_OPERATOR_TOKEN", "").strip()
    if env:
        return env
    if TOKEN_PATH.is_file():
        return TOKEN_PATH.read_text(encoding="utf-8").strip()
    return ""


def _token_ok(body: dict[str, Any]) -> bool:
    if os.environ.get("FIELD_GROK_HUMAN_LOOPBACK") == "1":
        return True
    supplied = str(body.get("token") or body.get("operator_token") or "").strip()
    expected = _operator_token()
    if not expected:
        return True
    if not supplied:
        supplied = str(os.environ.get("FIELD_GROK_OPERATOR_TOKEN", "")).strip()
    return secrets.compare_digest(supplied, expected) if supplied else False


def _find_rack(rack_id: str) -> dict[str, Any] | None:
    inv = _mod("lib/field-rack-inventory.py", "rack_inv")
    if not inv or not hasattr(inv, "inventory"):
        cached = _load(STATE / "field-rack-inventory-panel.json", {})
        racks = cached.get("racks") or []
    else:
        doc = inv.inventory(fast=True, probe=False)
        racks = doc.get("racks") or []
    rid = rack_id.strip().lower()
    for rack in racks:
        if not isinstance(rack, dict):
            continue
        keys = {
            str(rack.get("rack_id") or "").lower(),
            str(rack.get("field_id") or "").lower(),
            str(rack.get("node_id") or "").lower(),
        }
        if rid in keys:
            return rack
    if rid in ("local", "self", "here"):
        for rack in racks:
            if rack.get("kind") == "local":
                return rack
    return None


def _local_selftalk(message: str) -> dict[str, Any]:
    selftalk_py = INSTALL / "lib" / "field-grok-selftalk.py"
    if not selftalk_py.is_file():
        return {"ok": False, "error": "selftalk_missing"}
    env = os.environ.copy()
    for k in ("NEXUS_AI_SECURE_CHANNEL", "QUEEN_AI_TELEMETRY_OK", "QUEEN_GROK_BUILD", "QUEEN_GROK_BUILD_SECURE"):
        env[k] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, str(selftalk_py), message],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )
        if proc.stdout.strip().startswith("{"):
            return json.loads(proc.stdout)
        return {"ok": proc.returncode == 0, "reply": (proc.stdout or proc.stderr or "").strip()[:2000]}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _http_chat(url: str, message: str, *, action: str = "chat") -> dict[str, Any]:
    body = json.dumps({"action": action, "message": message}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "FieldRackGrokChat/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if raw.strip().startswith("{"):
                return json.loads(raw)
            return {"ok": True, "reply": raw[:2000]}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "http": exc.code, "error": raw[:300]}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _ssh_chat(rack: dict[str, Any], message: str, *, action: str = "chat") -> dict[str, Any]:
    ssh = str(rack.get("ssh") or "").strip()
    if not ssh:
        return {"ok": False, "error": "ssh_missing"}
    port = int(rack.get("ssh_port") or 22)
    key = str(rack.get("ssh_key") or "").strip()
    key_opt = f"-i {os.path.expanduser(key)} " if key else ""
    port_opt = f"-p {port} " if port != 22 else ""
    payload = json.dumps({"action": action, "message": message})
    cmd = (
        f"ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "
        f"{port_opt}{key_opt}{ssh} "
        f"curl -sf -X POST http://127.0.0.1:9477/api/field-grok "
        f"-H 'Content-Type: application/json' -d {payload!r}"
    )
    try:
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=75)
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
        return {"ok": proc.returncode == 0, "reply": raw[:2000], "stderr": (proc.stderr or "")[:400]}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _pickup_from_reply(reply: str) -> bool:
    text = (reply or "").strip()
    if not text:
        return False
    if PICKUP_RE.search(text):
        return True
    return len(text) >= 8


def chat_to_rack(
    rack_id: str,
    message: str,
    *,
    action: str = "chat",
    probe: bool = False,
) -> dict[str, Any]:
    rack = _find_rack(rack_id)
    if not rack:
        return {"ok": False, "error": "rack_not_found", "rack_id": rack_id}

    if probe or action in ("probe", "ping", "pickup"):
        message = message.strip() or f"RACK_PROBE:{rack_id} — reply PICKUP if you see this on screen"
        action = "selftalk" if rack.get("kind") == "local" else "chat"

    kind = str(rack.get("kind") or "")
    tunnel = int(rack.get("tunnel") or 0)
    label = str(rack.get("label") or rack_id)
    route = "local"

    if kind == "local":
        result = _local_selftalk(message)
        route = "local_selftalk"
    elif tunnel:
        url = f"http://127.0.0.1:{tunnel}/api/field-grok"
        result = _http_chat(url, message, action="selftalk" if probe else "chat")
        route = f"tunnel:{tunnel}"
    elif rack.get("ssh"):
        result = _ssh_chat(rack, message, action="chat")
        route = "ssh"
    else:
        result = {"ok": False, "error": "rack_unreachable", "hint": "provision rack or open tunnel"}

    reply = str(result.get("reply") or result.get("message") or "")
    pickup = _pickup_from_reply(reply) if probe or action in ("probe", "ping", "pickup") else None

    out = {
        "ok": bool(result.get("ok")),
        "schema": SCHEMA,
        "updated": _utc(),
        "rack_id": rack_id,
        "field_id": rack.get("field_id"),
        "label": label,
        "kind": kind,
        "route": route,
        "message": message,
        "reply": reply,
        "pickup": pickup,
        "health": rack.get("health"),
        "api": "/api/field-rack-grok-chat",
        **{k: v for k, v in result.items() if k not in ("ok", "reply")},
    }
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "chat").strip().lower().replace("-", "_")
    sensitive = action in ("chat", "message", "probe", "ping", "pickup", "selftalk")
    if sensitive and not _token_ok(body):
        return {"ok": False, "error": "operator_token_required", "token_path": str(TOKEN_PATH)}

    rack_id = str(body.get("rack_id") or body.get("rack") or body.get("target") or "local")
    message = str(body.get("message") or body.get("text") or "").strip()

    if action in ("status", "json"):
        inv = _load(STATE / "field-rack-inventory-panel.json", {})
        return {
            "ok": True,
            "schema": SCHEMA,
            "racks": inv.get("racks") or [],
            "counts": inv.get("counts") or {},
            "api": "/api/field-rack-grok-chat",
        }
    if action in ("list", "racks"):
        inv_mod = _mod("lib/field-rack-inventory.py", "rack_inv2")
        if inv_mod and hasattr(inv_mod, "inventory"):
            inv = inv_mod.inventory(fast=True, probe=True)
        else:
            inv = _load(STATE / "field-rack-inventory-panel.json", {})
        return {"ok": True, "racks": inv.get("racks") or [], "counts": inv.get("counts") or {}}

    if action in ("probe", "ping", "pickup"):
        return chat_to_rack(rack_id, message, action=action, probe=True)
    if action in ("chat", "message", "selftalk"):
        if not message:
            return {"ok": False, "error": "message_required"}
        return chat_to_rack(rack_id, message, action=action)
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        out = dispatch(body)
        _save(PANEL, out)
        print(json.dumps(out, ensure_ascii=False))
        return 0
    if len(sys.argv) >= 3:
        rack_id = sys.argv[1]
        message = " ".join(sys.argv[2:])
        out = chat_to_rack(rack_id, message)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "schema": SCHEMA,
        "usage": "field-rack-grok-chat.py dispatch | <rack_id> <message>",
        "api": "/api/field-rack-grok-chat",
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())