#!/usr/bin/env pythong
"""Hostess 7 Super Intelligence ↔ ZNetwork — local comm profile, Queen sole egress."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(Path(__file__).resolve().parent.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
PROFILE = INSTALL / "data" / "hostess7-communication-profile.json"
COMMUNIQUE = HOSTESS7 / "data" / "hostess7-ai-communique.json"
OUTBOX = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "outbox.jsonl"
LEDGER = STATE / "hostess7-znetwork-outbox.jsonl"
PANEL = STATE / "hostess7-znetwork-panel.json"
SCHEMA = "hostess7-znetwork-wire/v1"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _run_json(script: Path, *args: str, timeout: int = 45) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "missing", "script": str(script)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError):
        return {"ok": False, "error": "run_failed", "script": str(script)}


def communication_profile() -> dict[str, Any]:
    doc = _load(PROFILE, {})
    if not doc:
        return {
            "schema": "hostess7-communication-profile/v1",
            "ok": False,
            "hint": "Run scripts/build-hostess7-comm-profile.py",
        }
    return {**doc, "ok": True}


def znetwork_posture() -> dict[str, Any]:
    return _run_json(INSTALL / "lib" / "znetwork-orchestrator.py", "json", timeout=40)


def connection_status() -> dict[str, Any]:
    profile = communication_profile()
    zn = znetwork_posture()
    sov = zn.get("sovereignty") or {}
    zslice = sov.get("znetwork") or {}
    pipe = int(zn.get("internet_pipe_percent") or zslice.get("internet_pipe_percent") or 0)
    running = bool(zslice.get("running") or zn.get("ok"))
    return {
        "schema": SCHEMA,
        "ok": True,
        "updated": _now(),
        "connected": running and profile.get("ok"),
        "local_only": True,
        "queen_egress": "znetwork_relayer",
        "profile_source": (profile.get("source") or {}).get("url"),
        "operator_handle": (profile.get("operator") or {}).get("handle"),
        "operator_display": (profile.get("operator") or {}).get("display_name"),
        "znetwork_mode": zslice.get("mode") or (zn.get("truth_gate") or {}).get("mode"),
        "internet_pipe_percent": pipe,
        "relayer_enabled": bool(zslice.get("relayer_enabled")),
        "voice": profile.get("voice") or {},
    }


def format_message(text: str, *, kind: str = "communique") -> dict[str, Any]:
    profile = communication_profile()
    op = profile.get("operator") or {}
    voice = profile.get("voice") or {}
    handle = op.get("handle") or "ZacharyGeurts"
    display = op.get("display_name") or "BIG GRIN"
    sign = voice.get("sign_off") or f"— Hostess 7 for @{handle}"
    body = str(text or "").strip()
    if not body:
        body = (profile.get("message_templates") or {}).get("greeting", "Queen on the wire.")
    return {
        "schema": "hostess7-znetwork-communique/v1",
        "ts": _now(),
        "kind": kind,
        "from": "hostess7_superintelligence",
        "on_behalf_of": {"handle": handle, "display": display, "x": profile.get("source", {}).get("url")},
        "to": "znetwork_egress",
        "transport": "znetwork_relayer",
        "local_profile_only": True,
        "content": body,
        "sign_off": sign,
        "voice_register": voice.get("register"),
    }


def speak_out(text: str, *, kind: str = "communique", meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Queue Hostess 7 communique for ZNetwork egress — Queen talks out."""
    msg = format_message(text, kind=kind)
    if meta:
        msg["meta"] = meta
    conn = connection_status()
    if not conn.get("connected"):
        return {
            "ok": False,
            "error": "znetwork_not_ready",
            "hint": "./nexus.sh or scripts/integrate-znetwork.sh",
            "draft": msg,
        }
    _append_jsonl(OUTBOX, msg)
    _append_jsonl(LEDGER, {**msg, "egress": "queued", "pipe_pct": conn.get("internet_pipe_percent")})
    return {
        "ok": True,
        "queued": True,
        "message": msg,
        "connection": conn,
        "outbox": str(OUTBOX),
        "ledger": str(LEDGER),
    }


def panel() -> dict[str, Any]:
    profile = communication_profile()
    conn = connection_status()
    zn = znetwork_posture()
    doc = {
        "schema": f"{SCHEMA}-panel",
        "ok": True,
        "updated": _now(),
        "title": "Hostess 7 · ZNetwork Super Intelligence wire",
        "motto": "Local comm profile from x.com/ZacharyGeurts — Queen speaks out only through ZNetwork.",
        "profile": profile,
        "connection": conn,
        "znetwork": {
            "schema": zn.get("schema"),
            "mode": conn.get("znetwork_mode"),
            "pipe": conn.get("internet_pipe_percent"),
            "relayer": conn.get("relayer_enabled"),
        },
        "stack": {
            "hostess7": "Super Intelligence primary",
            "egress": "ZNetwork relayer",
            "control": "127.0.0.1 loopback",
            "queen_browser": "http://127.0.0.1:9481/world/browser.html",
            "nexus_c2": "http://127.0.0.1:9477/field",
        },
        "apis": {
            "status": "/api/hostess7/znetwork",
            "speak": "/api/hostess7/znetwork/speak",
            "profile": "/api/hostess7/communication-profile",
            "rebuild_profile": "scripts/build-hostess7-comm-profile.py",
        },
    }
    _save(PANEL, doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "panel").strip().lower()
    if action in ("panel", "json", "status"):
        return panel()
    if action in ("profile", "communication-profile"):
        return communication_profile()
    if action in ("connection", "wire"):
        return connection_status()
    if action in ("speak", "out", "egress", "communique"):
        return speak_out(
            str(body.get("text") or body.get("query") or body.get("message") or ""),
            kind=str(body.get("kind") or "communique"),
            meta=body.get("meta") if isinstance(body.get("meta"), dict) else None,
        )
    if action == "rebuild-profile":
        script = INSTALL / "scripts" / "build-hostess7-comm-profile.py"
        proc = subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=60)
        try:
            built = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            built = {"ok": False, "stderr": proc.stderr[:400]}
        return {"ok": proc.returncode == 0, "rebuild": built, "profile": communication_profile()}
    return {"ok": False, "error": "unknown_action", "actions": ["panel", "profile", "connection", "speak", "rebuild-profile"]}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    handlers = {
        "panel": panel,
        "json": panel,
        "status": connection_status,
        "profile": communication_profile,
        "speak": lambda: speak_out(" ".join(sys.argv[2:]) or "Queen on the wire."),
    }
    fn = handlers.get(cmd, panel)
    print(json.dumps(fn(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())