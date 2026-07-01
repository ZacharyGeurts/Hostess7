#!/usr/bin/env pythong
"""Beta 4 release monitor — tail AML progress + hang-freeze assist."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PROGRESS = STATE / "ammolang-release-progress.json"
BUILD_PANEL = STATE / "field-ammolang-build-panel.json"
HANG_PANEL = STATE / "ammolang-hang-freeze-assist.json"
LOG = STATE / "field-beta4-release-monitor.log"


def _load(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def snapshot() -> dict:
    prog = _load(PROGRESS)
    hang = _load(HANG_PANEL)
    build = _load(BUILD_PANEL)
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "phase": prog.get("phase") or prog.get("current_op"),
        "script": prog.get("script"),
        "ok": prog.get("ok"),
        "elapsed_ms": prog.get("elapsed_ms"),
        "updated": prog.get("updated"),
        "hang_events": len(hang.get("events") or []) if isinstance(hang, dict) else 0,
        "last_hang": (hang.get("events") or [{}])[-1] if isinstance(hang, dict) else {},
        "build_ok": build.get("ok"),
        "build_script": build.get("script"),
    }


def main() -> int:
    once = "--once" in sys.argv
    interval = 15
    for arg in sys.argv[1:]:
        if arg.startswith("--interval="):
            interval = max(5, int(arg.split("=", 1)[1]))
    prev = ""
    while True:
        row = snapshot()
        line = json.dumps(row, ensure_ascii=False)
        if line != prev:
            print(line, flush=True)
            try:
                LOG.parent.mkdir(parents=True, exist_ok=True)
                with LOG.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
            except OSError:
                pass
            prev = line
        if once:
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())