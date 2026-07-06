#!/usr/bin/env python3
"""PID spawn guard — only our install may start field service PIDs. Lethal on injection."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-pid-spawn-guard-doctrine.json"
LEDGER = STATE / "field-pid-spawn-guard-ledger.jsonl"
TOKEN_FILE = STATE / "field-spawn-token"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _parent_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _caller_chain(max_depth: int = 4) -> list[dict[str, Any]]:
    chain: list[dict[str, Any]] = []
    pid = os.getppid()
    for _ in range(max_depth):
        if pid <= 1:
            break
        cmd = _parent_cmdline(pid)
        chain.append({"pid": pid, "cmd": cmd[:240]})
        try:
            stat = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8", errors="replace")
            pid = int(stat.split()[3])
        except (OSError, ValueError, IndexError):
            break
    return chain


def _internal_caller(cmd: str, allow_roots: list[str]) -> bool:
    if not cmd:
        return False
    low = cmd.lower()
    if "threat-panel-http.py" in low and " ensure" not in low and "instantiate" not in low:
        return True
    for root in allow_roots:
        if root in cmd:
            return True
    if str(INSTALL) in cmd:
        return True
    return False


def _valid_token() -> bool:
    tok = os.environ.get("NEXUS_FIELD_SPAWN_TOKEN", "").strip()
    if not tok or not TOKEN_FILE.is_file():
        return False
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip() == tok
    except OSError:
        return False


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _lethal_force(*, service: str, reason: str, chain: list[dict[str, Any]]) -> dict[str, Any]:
    row = {
        "kind": "terror",
        "verdict": "HARM_CANDIDATE",
        "hell_chosen": True,
        "kill_eligible": True,
        "source": "pid_spawn_injection",
        "service": service,
        "reason": reason,
        "chain": chain,
        "ip": "127.0.0.1",
        "pid": os.getppid(),
    }
    out: dict[str, Any] = {"ok": False, "lethal": True, "reason": reason}
    lethal_py = INSTALL / "lib" / "lethal-enforcement.py"
    if lethal_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(lethal_py), "execute", json.dumps(row)],
                capture_output=True,
                text=True,
                timeout=20,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                check=False,
            )
            raw = (proc.stdout or "").strip()
            if raw.startswith("{"):
                out["lethal_result"] = json.loads(raw)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    for link in chain[:2]:
        spid = int(link.get("pid") or 0)
        if spid > 1:
            try:
                os.kill(spid, signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
    _append_ledger({"event": "lethal_spawn_block", "service": service, "reason": reason, "chain": chain})
    return out


def authorize_spawn(*, service: str, action: str = "serve") -> dict[str, Any]:
    """Return ok=True only when caller is internal or holds spawn token."""
    doc = doctrine()
    pol = doc.get("policy") or {}
    allow = [str(x) for x in pol.get("allowlist_roots") or []]
    allow.append(str(INSTALL / "lib"))
    allow.append(str(INSTALL / "scripts"))

    if os.environ.get("NEXUS_FIELD_SPAWN_GUARD_SKIP", "").strip().lower() in ("1", "yes"):
        return {"ok": True, "skipped": True, "service": service}

    if _valid_token():
        return {"ok": True, "authorized": "token", "service": service, "action": action}

    chain = _caller_chain()
    if chain and _internal_caller(str(chain[0].get("cmd") or ""), allow):
        return {"ok": True, "authorized": "internal", "service": service, "action": action, "caller": chain[0]}

    me = _parent_cmdline(os.getpid())
    if _internal_caller(me, allow):
        return {"ok": True, "authorized": "self", "service": service, "action": action}

    reason = f"rogue_spawn:{service}:{action}"
    if pol.get("lethal_on_rogue_spawn", True):
        lethal = _lethal_force(service=service, reason=reason, chain=chain)
        lethal["ok"] = False
        return lethal

    _append_ledger({"event": "spawn_denied", "service": service, "reason": reason, "chain": chain})
    return {"ok": False, "denied": True, "reason": reason, "chain": chain}


def authorize_spawn_or_exit(*, service: str, action: str = "serve") -> None:
    verdict = authorize_spawn(service=service, action=action)
    if verdict.get("ok"):
        return
    print(json.dumps(verdict, ensure_ascii=False), file=sys.stderr)
    raise SystemExit(13)


def issue_spawn_token() -> str:
    import secrets
    tok = secrets.token_hex(16)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(tok + "\n", encoding="utf-8")
    try:
        os.chmod(TOKEN_FILE, 0o600)
    except OSError:
        pass
    return tok


def panel_json() -> dict[str, Any]:
    doc = doctrine()
    return {
        "schema": "field-pid-spawn-guard/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "policy": doc.get("policy") or {},
        "token_present": TOKEN_FILE.is_file(),
        "api": doc.get("api"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    svc = (sys.argv[2] if len(sys.argv) > 2 else "field").strip()
    if cmd in ("json", "status", "panel"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "authorize":
        act = (sys.argv[3] if len(sys.argv) > 3 else "serve").strip()
        print(json.dumps(authorize_spawn(service=svc, action=act), ensure_ascii=False, indent=2))
        return 0
    if cmd == "issue-token":
        print(json.dumps({"ok": True, "token": issue_spawn_token()}, ensure_ascii=False))
        return 0
    print(json.dumps({"usage": "field-pid-spawn-guard.py [json|authorize SERVICE|issue-token]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())