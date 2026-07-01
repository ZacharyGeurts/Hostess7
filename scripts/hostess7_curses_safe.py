#!/usr/bin/env pythong
"""ASCII-safe curses helpers — avoids OverflowError on addch/hline with Unicode."""
from __future__ import annotations

import curses


def safe_hline(win: curses.window, y: int, x: int, ch: str, n: int) -> None:
    """Draw horizontal line using ASCII only (hline requires byte-sized ch)."""
    line_ch = ch if len(ch) == 1 and ord(ch) < 128 else "-"
    try:
        win.hline(y, x, line_ch, n)
    except (curses.error, OverflowError):
        try:
            win.addstr(y, x, line_ch * max(0, n))
        except curses.error:
            pass


def safe_addch(win: curses.window, y: int, x: int, ch: str) -> None:
    """addch one ASCII character; fallback to addstr."""
    if len(ch) != 1:
        ch = "#"
    if ord(ch) > 127:
        ch = {"█": "#", "│": "|", "─": "-", "▓": "#", "░": "."}.get(ch, "#")
    try:
        win.addch(y, x, ch)
    except (curses.error, OverflowError):
        try:
            win.addstr(y, x, ch)
        except curses.error:
            pass


def ascii_bar(width: int, ch: str = "-") -> str:
    c = ch if len(ch) == 1 and ord(ch) < 128 else "-"
    return c * max(0, width)