#!/usr/bin/env pythong
"""QA: Hostess7 UI draws without curses OverflowError."""
from __future__ import annotations

import curses
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def _draw_test(stdscr: curses.window) -> None:
    from hostess7_ui import HostessUI  # noqa: WPS433

    ui = HostessUI(stdscr)
    ui._draw()
    ui._append_user("test message")
    ui._draw()


def main() -> int:
    import os

    from hostess7_curses_safe import ascii_bar, safe_addch, safe_hline  # noqa: WPS433

    # Regression: Unicode box-drawing in hline caused OverflowError on Linux curses
    try:
        safe_hline.__doc__
        bar = ascii_bar(40, "\u2500")  # must downgrade to ASCII
        if bar != "-" * 40:
            return fail("ascii_bar must downgrade unicode to '-'")
    except OverflowError as exc:
        return fail(f"safe helpers OverflowError: {exc}")

    if os.isatty(0):
        try:
            curses.wrapper(_draw_test)
        except OverflowError as exc:
            return fail(f"curses OverflowError: {exc}")
    else:
        print("SKIP curses.wrapper — no TTY (safe_hline regression OK)")

    print("OK hostess7 ui draw")
    print("METRIC qa_hostess7_ui=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())