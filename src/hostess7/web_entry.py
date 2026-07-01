#!/usr/bin/env pythong
from __future__ import annotations

import runpy
import sys

from hostess7.paths import brain_state_dir, scripts_dir


def main() -> int:
    brain_state_dir()
    script = scripts_dir() / "hostess7_web.py"
    if not script.is_file():
        print(f"missing {script}", file=sys.stderr)
        return 1
    runpy.run_path(str(script), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())