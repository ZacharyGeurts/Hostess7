#!/usr/bin/env python3
"""Turbo orphan watch — no sleep, cook duplicate PIDs and rogue spawners fast."""
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
PANEL = STATE / "field-turbo-orphan-watch-panel.json"
LEDGER = STATE / "field-turbo-orphan-watch-ledger.jsonl"
ME = os.getpid()

# Rogue spawners — Grok harness sleepers, fix storms, ensure piles, interject stealers.
COOK_PATTERNS = [
    f"{INSTALL}/lib/field-watch-dhcp.py serve",
    f"{INSTALL}/lib/field-never-down.py ensure",
    f"{INSTALL}/lib/field-dns-dhcp-fix.py",
    f"{INSTALL}/lib/field-local-dns-connect.py connect",
    f"{INSTALL}/lib/field-always-optimal.py apply",
    f"{INSTALL}/lib/field-truth-keepalive.py keepalive",
    f"{INSTALL}/lib/hostess7-lab-sovereign.py boot",
    "dig @127.0.0.1",
]

KEEP_ONE = {
    f"{INSTALL}/lib/field-dns.py": 1,
    f"{INSTALL}/lib/field-dhcp.py serve": 1,
}


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pids(pat: str) -> list[int]:
    try:
        proc = subprocess.run(["pgrep", "-f", pat], capture_output=True, text=True, timeout=2)
        if proc.returncode != 0:
            return []
        out = []
        for line in (proc.stdout or "").splitlines():
            try:
                pid = int(line.strip())
            except ValueError:
                continue
            if pid != ME:
                out.append(pid)
        return out
    except (OSError, subprocess.TimeoutExpired):
        return []


def _batch_kill(pids: list[int], *, sudo_pw: str) -> int:
    if not pids:
        return 0
    killed = 0
    need: list[int] = []
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            killed += 1
        except PermissionError:
            need.append(pid)
        except ProcessLookupError:
            killed += 1
        except OSError:
            need.append(pid)
    if need:
        try:
            proc = subprocess.run(
                ["sudo", "-S", "kill", "-9", *[str(p) for p in need]],
                input=f"{sudo_pw}\n",
                capture_output=True,
                timeout=8,
                check=False,
            )
            if proc.returncode == 0:
                killed += len(need)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return killed


def cook(*, write: bool = True) -> dict[str, Any]:
    pw = os.environ.get("HOSTESS7_SUDO_PW", "mememe")
    cooked: dict[str, int] = {}
    targets: list[int] = []

    for pat in COOK_PATTERNS:
        pids = _pids(pat)
        if pids:
            n = _batch_kill(pids, sudo_pw=pw)
            cooked[pat.rsplit("/", 1)[-1][:36]] = n
            targets.extend(pids)

    for pat, keep in KEEP_ONE.items():
        pids = _pids(pat)
        if len(pids) > keep:
            extra = pids[keep:]
            n = _batch_kill(extra, sudo_pw=pw)
            cooked[f"extra_{pat.split('/')[-1]}"] = n

    remaining = {pat.rsplit("/", 1)[-1][:28]: len(_pids(pat)) for pat in COOK_PATTERNS[:4]}

    out = {
        "ok": True,
        "schema": "field-turbo-orphan-watch/v1",
        "updated": _utc(),
        "motto": "Turbo watch — cook orphans, no sleep, lethal on injection spawners.",
        "cooked": cooked,
        "cooked_total": sum(cooked.values()),
        "remaining": remaining,
        "api": "/api/field-turbo-orphan-watch",
    }
    if write:
        tmp = PANEL.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL)
        try:
            with LEDGER.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": _utc(), "cooked": cooked, "remaining": remaining}, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "cook").strip().lower()
    if cmd in ("cook", "watch", "turbo", "json"):
        print(json.dumps(cook(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-turbo-orphan-watch.py [cook|turbo]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())