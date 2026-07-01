#!/usr/bin/env python3
"""Generate NEXUS Field icons — Queen icon kit from local Amouranth branding."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "Queen" / "scripts" / "queen-icon-kit.py"


def main() -> None:
    if not KIT.is_file():
        raise SystemExit(f"queen-icon-kit.py missing: {KIT}")
    subprocess.run([sys.executable, str(KIT)], check=True)
    print(f"wrote Queen-branded taskbar icons via {KIT}")


if __name__ == "__main__":
    main()