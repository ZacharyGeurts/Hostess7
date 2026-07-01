#!/usr/bin/env python3
"""Kill Grok Orphans — cross-OS watchdog (Linux, macOS, Windows).

Requires elevated privileges to kill processes owned by other sessions.
Install via packaging/{linux,macos,windows}/ scripts.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

try:
    import psutil
except ImportError:
    psutil = None  # type: ignore

LOG = logging.getLogger("kgo")
VERSION = "1.1.0"

DEFAULT_CONFIG = Path("/etc/kgo/kgo-patterns.json")
LOCAL_CONFIG = Path(__file__).resolve().parent.parent / "data" / "kgo-patterns.json"


@dataclass
class Pattern:
    id: str
    match: str
    reason: str
    shell_only: bool = False


@dataclass
class Target:
    pid: int
    ppid: int
    cmdline: str
    reason: str


def default_config_path() -> Path:
    env = os.environ.get("KGO_CONFIG")
    if env:
        return Path(env)
    if DEFAULT_CONFIG.is_file():
        return DEFAULT_CONFIG
    return LOCAL_CONFIG


def load_config(path: Path) -> tuple[List[Pattern], int, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    patterns = [
        Pattern(
            id=p["id"],
            match=p["match"],
            reason=p.get("reason", p["id"]),
            shell_only=bool(p.get("shell_only", False)),
        )
        for p in data.get("patterns", [])
    ]
    return patterns, int(data.get("interval_sec", 5)), int(data.get("grace_sec", 3))


def is_orphan_ppid(ppid: int) -> bool:
    if sys.platform == "win32":
        # Services / System reparent orphans on Windows
        return ppid in (0, 4)
    return ppid == 1


def is_shell_cmd(cmdline: str) -> bool:
    low = cmdline.lower()
    return any(x in low for x in ("bash", "/sh", "dash", "zsh", "pwsh", "cmd.exe"))


def iter_processes_psutil() -> Iterable[tuple[int, int, str]]:
    assert psutil is not None
    for proc in psutil.process_iter(["pid", "ppid", "cmdline", "name"]):
        try:
            info = proc.info
            pid = int(info["pid"])
            ppid = int(info["ppid"] or 0)
            parts = info.get("cmdline") or []
            if not parts and info.get("name"):
                parts = [info["name"]]
            cmdline = " ".join(parts)
            yield pid, ppid, cmdline
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue


def iter_processes_proc() -> Iterable[tuple[int, int, str]]:
    proc_root = Path("/proc")
    my_pid = os.getpid()
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid <= 1 or pid == my_pid:
            continue
        try:
            stat = (entry / "stat").read_text()
            rp = stat.rfind(")")
            ppid = int(stat[rp + 2 :].split()[1]) if rp >= 0 else 0
            raw = (entry / "cmdline").read_bytes()
            cmdline = raw.replace(b"\0", b" ").decode("utf-8", "replace").strip()
            yield pid, ppid, cmdline
        except (OSError, ValueError, IndexError):
            continue


def iter_processes() -> Iterable[tuple[int, int, str]]:
    if psutil is not None:
        yield from iter_processes_psutil()
    elif sys.platform.startswith("linux"):
        yield from iter_processes_proc()
    else:
        raise RuntimeError("psutil required on this platform: pip install psutil")


def match_targets(patterns: List[Pattern]) -> List[Target]:
    my_pid = os.getpid()
    out: List[Target] = []
    for pid, ppid, cmdline in iter_processes():
        if pid == my_pid or not is_orphan_ppid(ppid):
            continue
        for pat in patterns:
            if pat.match not in cmdline:
                continue
            if pat.shell_only and not is_shell_cmd(cmdline):
                continue
            out.append(Target(pid=pid, ppid=ppid, cmdline=cmdline, reason=pat.reason))
            break
    return out


def kill_target(target: Target, grace_sec: int, dry_run: bool) -> bool:
    LOG.warning(
        "killing orphan pid=%s ppid=%s reason=%s cmd=%s",
        target.pid,
        target.ppid,
        target.reason,
        target.cmdline[:200],
    )
    if dry_run:
        return True
    try:
        if psutil is not None:
            proc = psutil.Process(target.pid)
            proc.terminate()
            try:
                proc.wait(timeout=grace_sec)
            except psutil.TimeoutExpired:
                proc.kill()
            return True
        os.kill(target.pid, signal.SIGTERM)
        for _ in range(grace_sec * 10):
            try:
                os.kill(target.pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.1)
        os.kill(target.pid, signal.SIGKILL)
        return True
    except (ProcessLookupError, PermissionError, OSError) as exc:
        LOG.error("failed to kill pid=%s: %s", target.pid, exc)
        return False


def run_once(patterns: List[Pattern], grace_sec: int, dry_run: bool) -> int:
    targets = match_targets(patterns)
    killed = sum(kill_target(t, grace_sec, dry_run) for t in targets)
    if targets:
        LOG.info("scan found %d orphan(s), acted on %d", len(targets), killed)
    return len(targets)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Kill Grok Orphans cross-OS watchdog")
    parser.add_argument("-c", "--config", type=Path, default=None)
    parser.add_argument("-f", "--foreground", action="store_true")
    parser.add_argument("-n", "--dry-run", action="store_true")
    parser.add_argument("-o", "--once", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    cfg_path = args.config or default_config_path()
    if not cfg_path.is_file():
        LOG.error("config not found: %s", cfg_path)
        return 1

    patterns, interval, grace = load_config(cfg_path)
    LOG.info(
        "Kill Grok Orphans v%s started (%d patterns, interval=%ds)",
        VERSION,
        len(patterns),
        interval,
    )

    stop = False

    def _stop(*_):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    while not stop:
        run_once(patterns, grace, args.dry_run)
        if args.once:
            break
        time.sleep(interval)

    LOG.info("kgo watchdog stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())