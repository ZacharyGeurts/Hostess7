#!/usr/bin/env pythong
"""Field Grok self-talk — secure loopback ACP stdio ping (talk to yourself)."""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
GROK_HOME = Path(os.environ.get("GROK_HOME", Path.home() / ".grok"))
TIMEOUT_SEC = int(os.environ.get("FIELD_GROK_SELFTALK_TIMEOUT", "45"))


def _grok_bin() -> str:
    seen: set[str] = set()
    candidates: list[str] = []
    for candidate in (
        os.environ.get("GROK_REAL_BIN", ""),
        str(GROK_HOME / "downloads" / "grok-linux-x86_64"),
    ):
        if candidate and candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)
    for candidate in sorted(GROK_HOME.glob("downloads/grok-*-linux-x86_64"), reverse=True):
        p = str(candidate)
        if p not in seen:
            candidates.append(p)
            seen.add(p)
    for candidate in (str(GROK_HOME / "bin" / "grok"), "grok"):
        if candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)
    for candidate in candidates:
        if candidate == "grok" or Path(candidate).is_file():
            return candidate
    return "grok"


def _secure_env() -> dict[str, str]:
    env = os.environ.copy()
    for k in (
        "NEXUS_AI_SECURE_CHANNEL",
        "QUEEN_AI_TELEMETRY_OK",
        "QUEEN_GROK_BUILD",
        "QUEEN_GROK_BUILD_SECURE",
        "GROK_SECURE_CHANNEL",
    ):
        env[k] = "1"
    env.setdefault("GROK_MAX_SOCKETS", "5")
    env.setdefault("SSL_CERT_FILE", "/etc/ssl/certs/ca-certificates.crt")
    for proxy in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"):
        env.pop(proxy, None)
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    return env


def _read_until(proc: subprocess.Popen[str], deadline: float, *, want_id: int | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    assert proc.stdout is not None
    while time.monotonic() < deadline:
        ready, _, _ = select.select([proc.stdout], [], [], 0.5)
        if not ready:
            if proc.poll() is not None:
                break
            continue
        line = proc.stdout.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            row = {"_raw": line[:500]}
        rows.append(row)
        if want_id is not None and row.get("id") == want_id:
            return rows
    return rows


def _send(proc: subprocess.Popen[str], payload: dict[str, Any]) -> None:
    assert proc.stdin is not None
    proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
    proc.stdin.flush()


def _extract_text(rows: list[dict[str, Any]]) -> str:
    chunks: list[str] = []
    for row in rows:
        if row.get("method") == "session/update":
            params = row.get("params") or {}
            update = params.get("update") or {}
            kind = str(update.get("sessionUpdate") or "")
            if kind in ("agent_message_chunk", "agent_message"):
                content = update.get("content") or {}
                if isinstance(content, dict) and content.get("text"):
                    chunks.append(str(content["text"]))
            for part in params.get("content") or []:
                if isinstance(part, dict) and part.get("type") == "text" and part.get("text"):
                    chunks.append(str(part["text"]))
        result = row.get("result")
        if isinstance(result, dict):
            for key in ("content", "message", "text"):
                val = result.get(key)
                if isinstance(val, str) and val.strip():
                    chunks.append(val.strip())
                elif isinstance(val, list):
                    for part in val:
                        if isinstance(part, dict) and part.get("text"):
                            chunks.append(str(part["text"]))
    return "".join(chunks).strip()


def selftalk(message: str, *, cwd: str | None = None) -> dict[str, Any]:
    text = (message or "Reply with exactly: FIELD_GROK_PONG").strip()[:4000]
    work = cwd or str(INSTALL)
    grok = _grok_bin()
    cmd = [grok, "agent", "--model", "grok-build", "stdio"]
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            cwd=work,
            env=_secure_env(),
        )
    except OSError as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}

    deadline = time.monotonic() + TIMEOUT_SEC
    try:
        _send(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "clientInfo": {"name": "field-grok-selftalk", "version": "1.0.0"},
            },
        })
        rows = _read_until(proc, min(deadline, time.monotonic() + 12), want_id=1)
        if not any(r.get("id") == 1 and r.get("result") for r in rows):
            proc.terminate()
            return {"ok": False, "error": "initialize_failed", "tail": rows[-4:], "cmd": cmd}
        _send(proc, {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "session/new",
            "params": {"cwd": work, "mcpServers": []},
        })
        rows += _read_until(proc, min(deadline, time.monotonic() + 12), want_id=2)
        session_id = ""
        for row in rows:
            if row.get("id") == 2 and isinstance(row.get("result"), dict):
                session_id = str(row["result"].get("sessionId") or row["result"].get("session_id") or "")
        if not session_id:
            proc.terminate()
            return {
                "ok": False,
                "error": "session_new_failed",
                "tail": rows[-6:],
                "cmd": cmd,
            }
        _send(proc, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "session/prompt",
            "params": {
                "sessionId": session_id,
                "prompt": [{"type": "text", "text": text}],
            },
        })
        rows += _read_until(proc, deadline, want_id=3)
        if not any(r.get("id") == 3 for r in rows):
            rows += _read_until(proc, deadline)
        reply = _extract_text(rows)
        stopped = any(
            isinstance(r.get("result"), dict) and r["result"].get("stopReason") == "end_turn"
            for r in rows if r.get("id") == 3
        )
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        return {
            "ok": bool(reply) or stopped,
            "reply": reply or ("(turn complete)" if stopped else "(no reply text)"),
            "session_id": session_id,
            "message": text,
            "transport": "acp_stdio",
            "secure": True,
            "events": len(rows),
            "stop_reason": "end_turn" if stopped else None,
        }
    except Exception as exc:
        proc.kill()
        return {"ok": False, "error": str(exc), "cmd": cmd}


def main() -> int:
    msg = " ".join(sys.argv[1:]).strip() or "Reply with exactly: FIELD_GROK_PONG"
    print(json.dumps(selftalk(msg), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())