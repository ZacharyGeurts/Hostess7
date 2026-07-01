#!/usr/bin/env pythong
"""Keep Grok desktop egress at GROK_MAX_SOCKETS (default 5) — secure, no socket storm."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from typing import Any

MAX_SOCKETS = int(os.environ.get("GROK_MAX_SOCKETS", "5") or "5")
INTERVAL_SEC = float(os.environ.get("GROK_SOCKET_LIMIT_INTERVAL", "1.5") or "1.5")
PID = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("GROK_PID", "0") or "0")

_ADDR_RE = re.compile(
    r"^(?P<lip>(?:\[[0-9a-f:]+\]|[^:\s]+)):(?P<lport>\d+)\s+"
    r"(?P<rip>(?:\[[0-9a-f:]+\]|[^:\s]+)):(?P<rport>\d+)"
)


def _list_established(pid: int) -> list[dict[str, str]]:
    try:
        proc = subprocess.run(
            ["ss", "-H", "-tn", "state", "established", f"pid={pid}"],
            capture_output=True,
            text=True,
            timeout=6,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    rows: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        m = _ADDR_RE.search(line)
        if not m:
            continue
        rows.append(
            {
                "lip": m.group("lip").strip("[]"),
                "lport": m.group("lport"),
                "rip": m.group("rip").strip("[]"),
                "rport": m.group("rport"),
                "line": line,
            }
        )
    return rows


def _kill_socket(row: dict[str, str]) -> bool:
    args = [
        "ss",
        "-K",
        "src",
        row["lip"],
        "sport",
        "=",
        row["lport"],
        "dst",
        row["rip"],
        "dport",
        "=",
        row["rport"],
    ]
    try:
        proc = subprocess.run(args, capture_output=True, text=True, timeout=4)
        return proc.returncode == 0
    except (subprocess.SubprocessError, OSError):
        return False


def enforce_once(pid: int, *, max_sockets: int = MAX_SOCKETS) -> dict[str, Any]:
    conns = _list_established(pid)
    excess = max(0, len(conns) - max_sockets)
    killed = 0
    if excess:
        for row in conns[max_sockets:]:
            if _kill_socket(row):
                killed += 1
    return {
        "ok": True,
        "pid": pid,
        "established": len(conns),
        "max": max_sockets,
        "killed": killed,
    }


def watch(pid: int) -> int:
    if pid <= 1:
        print(json_error("invalid pid"), file=sys.stderr)
        return 2
    while True:
        try:
            os.kill(pid, 0)
        except OSError:
            return 0
        enforce_once(pid)
        time.sleep(INTERVAL_SEC)


def json_error(msg: str) -> str:
    import json

    return json.dumps({"ok": False, "error": msg})


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else "watch").strip().lower()
    if cmd in ("once", "enforce", "json"):
        import json

        pid = PID
        if cmd == "json" and len(sys.argv) > 2 and sys.argv[2].isdigit():
            pid = int(sys.argv[2])
        print(json.dumps(enforce_once(pid)))
        return 0
    if cmd in ("watch", "daemon"):
        pid = PID
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            pid = int(sys.argv[2])
        return watch(pid)
    print("usage: grok-socket-limit.py [watch|once] [pid]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())