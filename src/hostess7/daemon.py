#!/usr/bin/env pythong
"""Hostess7 daemon — perceive → reflect → teach loop (sovereign wait, no wall timers)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hostess7.paths import brain_state_dir, hostess7_root, scripts_dir
from hostess7.state import save_cortex, load_cortex


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _cycle(low_power: bool) -> dict[str, Any]:
    root = hostess7_root()
    steps: list[dict[str, Any]] = []
    if not low_power:
        for script, args in (
            ("field_online_learn.py", ["pulse"]),
            ("field_hostess_self_brief.py", []),
        ):
            sp = scripts_dir() / script
            if not sp.is_file():
                steps.append({"step": script, "skipped": True})
                continue
            proc = subprocess.run(
                [sys.executable, str(sp), *args],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
                env={**os.environ, "HOSTESS7_ROOT": str(root)},
            )
            steps.append({"step": script, "ok": proc.returncode == 0})
    cortex = load_cortex()
    loops = list(cortex.get("daemon_loops") or [])
    loops.append({"ts": _now(), "steps": steps})
    cortex["daemon_loops"] = loops[-64:]
    save_cortex(cortex)
    return {"ok": True, "ts": _now(), "steps": steps}


def run_daemon(*, cycles: int = 0, interval_sec: float = 300.0) -> int:
    brain_state_dir()
    low = os.environ.get("HOSTESS7_LOW_POWER", "0") in ("1", "true", "yes")
    wait_py = scripts_dir() / "hostess7_sovereign_wait.py"
    n = 0
    while cycles == 0 or n < cycles:
        doc = _cycle(low_power=low)
        print(json.dumps(doc), flush=True)
        n += 1
        if cycles and n >= cycles:
            break
        if wait_py.is_file():
            subprocess.run(
                [sys.executable, str(wait_py), "presume", str(interval_sec)],
                cwd=str(hostess7_root()),
                check=False,
                timeout=int(interval_sec) + 30,
            )
        else:
            time.sleep(interval_sec)
    return 0


def main() -> int:
    cycles = int(os.environ.get("HOSTESS7_DAEMON_CYCLES", "0"))
    interval = float(os.environ.get("HOSTESS7_DAEMON_INTERVAL", "300"))
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        cycles = int(sys.argv[1])
    return run_daemon(cycles=cycles, interval_sec=interval)


if __name__ == "__main__":
    raise SystemExit(main())