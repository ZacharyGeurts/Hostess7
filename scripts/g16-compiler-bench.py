#!/usr/bin/env python3
"""Entry point — G16 compiler & interpreter benchmark for all 57 languages."""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

INSTALL = Path(__file__).resolve().parents[1]
BENCH = INSTALL / "lib" / "g16-compiler-bench.py"

os.environ.setdefault("NEXUS_INSTALL_ROOT", str(INSTALL))
os.environ.setdefault("GROK16_ROOT", str(INSTALL / "Grok16"))
os.environ.setdefault("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state"))


def _load():
    spec = importlib.util.spec_from_file_location("g16_compiler_bench", BENCH)
    if not spec or not spec.loader:
        raise SystemExit("g16-compiler-bench.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


if __name__ == "__main__":
    raise SystemExit(_load().main())