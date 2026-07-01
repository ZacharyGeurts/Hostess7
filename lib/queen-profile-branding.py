#!/usr/bin/env pythong
"""Shim — Queen profile branding lives in Queen/lib/queen-profile-branding.py."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_INSTALL = Path(__file__).resolve().parent.parent
_QUEEN = _INSTALL / "Queen"
_SRC = _QUEEN / "lib" / "queen-profile-branding.py"

if not _SRC.is_file():
    raise SystemExit(f"FAIL missing {_SRC}")

_spec = importlib.util.spec_from_file_location("queen_profile_branding", _SRC)
if not _spec or not _spec.loader:
    raise SystemExit("FAIL queen-profile-branding load")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
sys.modules["queen_profile_branding"] = _mod

if __name__ == "__main__":
    raise SystemExit(_mod.main())
else:
    seed_all = _mod.seed_all
    write_profile = _mod.write_profile
    user_js_lines = _mod.user_js_lines