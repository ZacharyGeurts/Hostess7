#!/usr/bin/env pythong
"""Hostess 7 presume — sovereign timing layer (separate from AML boundary)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT.parent if ROOT.name == "Hostess7" else ROOT
MOD_PATH = INSTALL / "lib" / "hostess7-presume.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("hostess7_presume", MOD_PATH)
    if not spec or not spec.loader:
        raise ImportError(f"missing {MOD_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = _load_mod()
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    sys.argv = [str(MOD_PATH), cmd, *sys.argv[2:]]
    return mod.main()


if __name__ == "__main__":
    raise SystemExit(main())