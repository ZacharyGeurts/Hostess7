#!/usr/bin/env python3
"""Grok agent spawner instakill — sudo mememe, lethal on rogue harness spawners."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PATTERNS = INSTALL / "data" / "field-grok-spawner-patterns.json"
PANEL = STATE / "field-grok-spawner-kill-panel.json"
LEDGER = STATE / "field-grok-spawner-kill-ledger.jsonl"
ME = os.getpid()


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _sudo_pw() -> str:
    return os.environ.get("HOSTESS7_SUDO_PW", "mememe")


def _is_shell(cmdline: str) -> bool:
    low = cmdline.lower()
    return any(x in low for x in ("bash", "/sh", "dash", "zsh", "pwsh", "cmd.exe"))


def _is_orphan(ppid: int) -> bool:
    return ppid == 1


def _grok_parent_pids(rows: list[tuple[int, int, str]]) -> set[int]:
    parents: set[int] = set()
    for pid, _, cmdline in rows:
        base = Path(cmdline.split()[0]).name if cmdline else ""
        if base == "grok" and "agent serve" not in cmdline and "dump_bash_state" not in cmdline:
            parents.add(pid)
    return parents


def _iter_proc() -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    if not sys.platform.startswith("linux"):
        return rows
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid <= 1 or pid == ME:
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
            rp = stat.rfind(")")
            ppid = int(stat[rp + 2 :].split()[1]) if rp >= 0 else 0
            raw = (entry / "cmdline").read_bytes()
            cmdline = raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()
            rows.append((pid, ppid, cmdline))
        except (OSError, ValueError, IndexError):
            continue
    return rows


def _excluded(cmdline: str, excludes: list[str]) -> bool:
    return any(x in cmdline for x in excludes)


def _instakill(pids: list[int], *, sudo_pw: str) -> int:
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


def _targets_for_pattern(
    pat: dict[str, Any],
    rows: list[tuple[int, int, str]],
    excludes: list[str],
    grok_parents: set[int],
) -> list[int]:
    match = str(pat.get("match") or "")
    if not match:
        return []
    keep = int(pat.get("keep", 0))
    shell_only = bool(pat.get("shell_only"))
    hits: list[tuple[int, int, str]] = []
    for pid, ppid, cmdline in rows:
        if not cmdline or _excluded(cmdline, excludes):
            continue
        if match not in cmdline:
            continue
        if shell_only and not _is_shell(cmdline):
            continue
        hits.append((pid, ppid, cmdline))
    if not hits:
        return []
    hits.sort(key=lambda row: row[0])
    victims: list[int] = []
    if keep <= 0:
        victims = [pid for pid, ppid, _ in hits if ppid not in grok_parents]
    else:
        protected = {pid for pid, ppid, _ in hits if ppid in grok_parents}
        extras = hits[:-keep] if len(hits) > keep else []
        victims = [pid for pid, _, _ in extras if pid not in protected]
        for pid, ppid, _ in hits[-keep:]:
            if pid in protected:
                continue
            if _is_orphan(ppid):
                victims.append(pid)
    return victims


def instakill(*, write: bool = True) -> dict[str, Any]:
    doc = _load(PATTERNS, {})
    patterns = doc.get("patterns") or []
    excludes = [str(x) for x in (doc.get("exclude_cmd") or [])]
    pw = _sudo_pw()
    rows = _iter_proc()
    grok_parents = _grok_parent_pids(rows)
    cooked: dict[str, int] = {}
    victims: list[dict[str, Any]] = []

    for pat in patterns:
        if not isinstance(pat, dict):
            continue
        pids = _targets_for_pattern(pat, rows, excludes, grok_parents)
        if not pids:
            continue
        n = _instakill(pids, sudo_pw=pw)
        key = str(pat.get("id") or pat.get("match", ""))[:36]
        cooked[key] = n
        all_pids.extend(pids)
        victims.append({"id": pat.get("id"), "pids": pids, "killed": n, "reason": pat.get("reason")})

    remaining: dict[str, int] = {}
    rows_after = _iter_proc()
    for pat in patterns[:6]:
        if not isinstance(pat, dict):
            continue
        match = str(pat.get("match") or "")
        if not match:
            continue
        remaining[str(pat.get("id") or match)[:28]] = sum(1 for _, _, c in rows_after if match in c)

    out = {
        "ok": True,
        "schema": "field-grok-spawner-kill/v1",
        "updated": _utc(),
        "motto": "Instakill Grok agent spawners — sudo mememe, zero grace.",
        "cooked": cooked,
        "cooked_total": sum(cooked.values()),
        "victims": victims[:24],
        "remaining": remaining,
        "api": "/api/field-grok-spawner-kill",
    }
    if write:
        STATE.mkdir(parents=True, exist_ok=True)
        tmp = PANEL.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(PANEL)
        try:
            with LEDGER.open("a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {"ts": _utc(), "cooked": cooked, "remaining": remaining},
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        except OSError:
            pass
    return out


def serve() -> int:
    doc = _load(PATTERNS, {})
    interval_ms = max(50, int(doc.get("interval_ms", 250)))
    while True:
        try:
            instakill(write=True)
        except Exception as exc:
            err = {"ok": False, "error": str(exc)[:200], "ts": _utc()}
            try:
                tmp = PANEL.with_suffix(".tmp")
                tmp.write_text(json.dumps(err, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                tmp.replace(PANEL)
            except OSError:
                pass
        time.sleep(interval_ms / 1000.0)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "instakill").strip().lower()
    if cmd in ("instakill", "kill", "cook", "json", "once"):
        print(json.dumps(instakill(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("serve", "watch", "daemon"):
        serve()
        return 0
    print(
        json.dumps(
            {"usage": "field-grok-spawner-kill.py [instakill|serve]"},
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())