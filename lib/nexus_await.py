#!/usr/bin/env pythong
"""Event-driven waits — no time.sleep; capped at NEXUS_AWAIT_MAX_SEC (default 5)."""
from __future__ import annotations

import os
import select
import shutil
import subprocess
import sys
from pathlib import Path

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
AWAIT_MAX = float(os.environ.get("NEXUS_AWAIT_MAX_SEC", "5"))


def _clamp(seconds: float) -> float:
    sec = max(0.0, float(seconds))
    return min(sec if sec >= 1.0 else 1.0, AWAIT_MAX)


def await_seconds(seconds: float, watch_dir: Path | None = None) -> None:
    sec = _clamp(seconds)
    watch = watch_dir if watch_dir and watch_dir.is_dir() else STATE
    if not watch.is_dir():
        watch = Path("/tmp")
    if shutil.which("inotifywait"):
        subprocess.run(
            [
                "inotifywait",
                "-r",
                "-t",
                str(int(sec)),
                "-e",
                "modify,create,delete,move,close_write",
                str(watch),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    select.select([], [], [], sec)


def await_pid_exit(pid: int, timeout: float = 5.0) -> None:
    import time

    limit = _clamp(timeout)
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except OSError:
            return
        select.select([], [], [], min(0.25, limit))


def await_lock_release(lock_path: Path, timeout: float = 5.0) -> None:
    import time

    limit = _clamp(timeout)
    deadline = time.monotonic() + limit
    while lock_path.exists() and time.monotonic() < deadline:
        await_seconds(1.0, lock_path.parent)


if __name__ == "__main__":
    await_seconds(float(sys.argv[1]) if len(sys.argv) > 1 else 1.0)
