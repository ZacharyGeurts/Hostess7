#!/usr/bin/env pythong
"""Generate icons — delegates to Queen icon kit."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1] / "Queen" / "scripts" / "queen-icon-kit.py"

if __name__ == "__main__":
    if not KIT.is_file():
        raise SystemExit(f"missing {KIT}")
    subprocess.run([sys.executable, str(KIT)], check=True)