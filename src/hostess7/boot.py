#!/usr/bin/env pythong
"""Package entry — delegates to hostess7_boot.py with unified state."""
from __future__ import annotations

import os
import subprocess
import sys

from hostess7.paths import brain_state_dir, hostess7_root, scripts_dir
from hostess7.state import snapshot


def main() -> int:
    brain_state_dir()
    script = scripts_dir() / "hostess7_boot.py"
    if not script.is_file():
        print(f"missing {script}", file=sys.stderr)
        return 1
    proc = subprocess.run(
        [sys.executable, str(script), *sys.argv[1:]],
        cwd=str(hostess7_root()),
        env={**os.environ, "HOSTESS7_ROOT": str(hostess7_root())},
        check=False,
    )
    if proc.returncode == 0:
        try:
            snapshot("boot")
        except OSError:
            pass
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())