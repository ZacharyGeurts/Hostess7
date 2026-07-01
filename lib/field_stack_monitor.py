#!/usr/bin/env pythong
"""AmmoLang monitor hook — Hostess7 field stack live status."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

INSTALL = Path(__file__).resolve().parents[1]
H7_SCRIPT = INSTALL.parent / "Hostess7" / "scripts" / "field_stack_corpus.py"


def _load_corpus():
    if not H7_SCRIPT.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_stack_corpus", H7_SCRIPT)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    action = (args[0] if args else "stack_status").strip().lower()
    mod = _load_corpus()
    if not mod:
        print(f"FAIL missing {H7_SCRIPT}", file=sys.stderr)
        return 1
    if action in ("stack_status", "status", "health"):
        report = mod.stack_status_report()
        print(report)
        return 0 if "OK field-stack-status" in report else 1
    print("usage: field-stack-monitor.py [stack_status|status]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())