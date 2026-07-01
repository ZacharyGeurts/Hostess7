#!/usr/bin/env pythong
"""Fast threat-panel.json assembly from .nexus-state fragments (no RF cycle)."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    audit = ROOT / "scripts" / "panel-tab-audit.py"
    if not audit.is_file():
        print("panel-tab-audit.py missing", file=sys.stderr)
        return 1
    os.environ.setdefault("NEXUS_INSTALL_ROOT", str(ROOT))
    os.environ.setdefault("NEXUS_STATE_DIR", str(ROOT / ".nexus-state"))
    spec = importlib.util.spec_from_file_location("panel_tab_audit", audit)
    if spec is None or spec.loader is None:
        return 1
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    doc = mod._assemble_from_state(write=True)
    if not doc:
        print("assemble: insufficient state fragments", file=sys.stderr)
        return 1
    print(f"assembled threat-panel.json keys={len(doc)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())