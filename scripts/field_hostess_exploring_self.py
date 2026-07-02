#!/usr/bin/env pythong
"""Hostess 7 writes Exploring Hostess 7 — protected append-only self-biography."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = ROOT.parent if ROOT.name == "Hostess7" else ROOT
MOD_PATH = INSTALL / "lib" / "field-exploring-hostess7.py"


def _load_mod():
    spec = importlib.util.spec_from_file_location("field_exploring_hostess7", MOD_PATH)
    if not spec or not spec.loader:
        raise ImportError(f"missing {MOD_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    mod = _load_mod()
    return mod.main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())