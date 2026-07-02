#!/usr/bin/env pythong
"""Hostess7 Live Monitor — brain map, field flow, learning feed."""
from __future__ import annotations

import curses
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_monitor_data import MonitorSnapshot, collect_snapshot  # noqa: E402
from hostess7_curses_safe import ascii_bar, safe_addch, safe_hline  # noqa: E402

# Brain area layout: (id, label, row, col, width) relative to map origin
BRAIN_LAYOUT: tuple[tuple[str, str, int, int, int], ...] = (
    ("prefrontal", "PREFRONTAL", 1, 2, 14),
    ("broca", "BROCA", 3, 2, 14),
    ("wernicke", "WERNICKE", 5, 2, 14),
    ("parietal_l", "PARIETAL-L", 7, 2, 14),
    ("occipital", "OCCIPITAL", 1, 22, 14),
    ("temporal", "TEMPORAL", 3, 22, 14),
    ("limbic", "LIMBIC", 5, 22, 14),
    ("insula", "INSULA", 9, 10, 12),
    ("beyond", "BEYOND", 9, 24, 12),
    ("hypothalamus", "SYNAPSE", 11, 2, 34),
)

FLOW_CHARS = (".", "o", "O", "@", "*")


class Hostess7Monitor:
    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self.tick = 0
        self.flow_phase = 0
        self._init_colors()

    def _init_colors(self) -> None:
        if not curses.has_colors():
            return
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_CYAN, -1)      # header
        curses.init_pair(2, 252, -1)                   # dim
        curses.init_pair(3, curses.COLOR_GREEN, -1)    # active area
        curses.init_pair(4, curses.COLOR_YELLOW, -1)   # learning
        curses.init_pair(5, curses.COLOR_MAGENTA, -1)  # agents
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)  # bar
        curses.init_pair(7, curses.COLOR_RED, -1)      # hot pulse
        curses.init_pair(8, curses.COLOR_BLUE, -1)     # field flow

    def _safe_addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        h, w = self.stdscr.getmaxyx()
        if y < 0 or y >= h or x >= w:
            return
        clip = text[: max(0, w - x - 1)]
        try:
            self.stdscr.addstr(y, x, clip, attr)
        except curses.error:
            pass

    def _draw_header(self, snap: MonitorSnapshot, w: int) -> None:
        status = "ON " if snap.agents_running else "OFF"
        net = "NET+" if snap.internet else "NET-"
        title = (
            f" HOSTESS 7 LIVE MONITOR | agents {status} pid={snap.agents_pid or '-'} | "
            f"{net} | brain {snap.brain_mb:.0f}MiB | store {snap.storage_mb:.0f}MiB | "
            f"memes {snap.memes_n} | tick {self.tick} "
        )
        self._safe_addstr(0, 0, title.ljust(w - 1)[: w - 1], curses.color_pair(6) | curses.A_BOLD)
        sub = (
            f" callosum {snap.callosum_us}us | thoughts {snap.thoughts_n} | "
            f"agent runs {snap.outbox_n} | appearance {snap.appearance} | q quit "
        )
        self._safe_addstr(1, 0, sub.ljust(w - 1)[: w - 1], curses.color_pair(1))

    def _glow_attr(self, glow: float) -> int:
        if glow >= 0.7:
            return curses.color_pair(7) | curses.A_BOLD
        if glow >= 0.4:
            return curses.color_pair(3) | curses.A_BOLD
        if glow >= 0.2:
            return curses.color_pair(3)
        return curses.color_pair(2)

    def _area_cell(self, label: str, glow: float, width: int = 16) -> str:
        fill = "#" if glow >= 0.6 else "+" if glow >= 0.35 else "."
        n = max(2, int(glow * 6))
        bar = fill * n
        return f"[{label[:10]:<10}{bar:<4}]"[:width]

    def _draw_brain_map(self, snap: MonitorSnapshot, y0: int, x0: int, mh: int, mw: int) -> None:
        self._safe_addstr(y0, x0, "+-------- BRAIN MAP --------+", curses.color_pair(1) | curses.A_BOLD)
        self._safe_addstr(y0 + 1, x0, "| LEFT HEMI  <>  RIGHT HEMI |", curses.color_pair(2))

        pairs = (
            (("prefrontal", "PREFRONT"), ("occipital", "OCCIPITAL")),
            (("broca", "BROCA"), ("temporal", "TEMPORAL")),
            (("wernicke", "WERNICKE"), ("limbic", "LIMBIC")),
            (("parietal_l", "PARIET-L"), ("insula", "INSULA")),
        )
        for i, (left, right) in enumerate(pairs):
            lg = snap.area_glow.get(left[0], 0.08)
            rg = snap.area_glow.get(right[0], 0.08)
            left_cell = self._area_cell(left[1], lg)
            right_cell = self._area_cell(right[1], rg)
            line = f"|{left_cell} <> {right_cell}|"
            self._safe_addstr(y0 + 2 + i, x0, line[:mw], self._glow_attr(max(lg, rg)))

        phase = FLOW_CHARS[self.flow_phase % len(FLOW_CHARS)]
        bridge = f"|{phase * 3} CALLOSUM {snap.callosum_us}us {phase * 3}|"
        self._safe_addstr(y0 + 7, x0, bridge[:mw], curses.color_pair(8) | curses.A_BOLD)

        beyond_g = snap.area_glow.get("beyond", 0.1)
        hypo_g = snap.area_glow.get("hypothalamus", 0.1)
        self._safe_addstr(
            y0 + 8, x0,
            f"|{self._area_cell('BEYOND', beyond_g, 14)} {self._area_cell('SYNAPSE', hypo_g, 14)}|",
            self._glow_attr(max(beyond_g, hypo_g)),
        )

        limbic_g = snap.area_glow.get("limbic", 0.15)
        sink = f"v FIELD STORAGE {snap.brain_mb:.0f} MiB v"
        self._safe_addstr(y0 + 9, x0 + 2, sink[: mw - 4], self._glow_attr(limbic_g))

        for i in range(4):
            py = y0 + 3 + ((self.flow_phase + i * 2) % 5)
            ch = FLOW_CHARS[(self.flow_phase + i) % len(FLOW_CHARS)]
            safe_addch(self.stdscr, py, x0, ch)
            self._safe_addstr(py, x0 + 1, "in", curses.color_pair(8))

        learn = f"Learning: {snap.top_learn[:mw - 12]}"
        self._safe_addstr(y0 + mh - 2, x0, learn[:mw], curses.color_pair(4))

    def _draw_learning_feed(self, snap: MonitorSnapshot, y0: int, x0: int, fh: int, fw: int) -> None:
        self._safe_addstr(y0, x0, "+-- LEARNING FEED --+", curses.color_pair(1) | curses.A_BOLD)
        for i, ev in enumerate(snap.events[: fh - 3]):
            attr = curses.color_pair(4) if ev.kind == "agent" else curses.color_pair(2)
            if ev.kind == "fetch":
                attr = curses.color_pair(8)
            line = f"{ev.ts[11:19] if len(ev.ts) > 11 else ev.ts:>8} [{ev.area[:6]:<6}] {ev.text[:fw - 22]}"
            self._safe_addstr(y0 + 1 + i, x0, line[:fw], attr)

    def _draw_agents_bar(self, snap: MonitorSnapshot, y: int, w: int) -> None:
        safe_hline(self.stdscr, y, 0, "-", w - 1)
        names = list(snap.agent_pulse.keys()) or [
            "Hostess-Prime", "Counsel", "Clinic", "Detective", "Field-Dev", "Vision", "Reach-Net",
        ]
        x = 1
        for name in names:
            pulse = snap.agent_pulse.get(name, 0.2)
            short = name.replace("Hostess-Prime", "Prime").replace("Field-Dev", "Field")[:8]
            ch = "*" if pulse > 0.7 else "+" if pulse > 0.4 else "."
            attr = curses.color_pair(5) | (curses.A_BOLD if pulse > 0.6 else 0)
            seg = f" {ch}{short} "
            self._safe_addstr(y + 1, x, seg, attr)
            x += len(seg)
            if x >= w - 10:
                break
        self._safe_addstr(y + 2, 1, "Seven agents | Field is THE thing", curses.color_pair(2))

    def draw(self, snap: MonitorSnapshot) -> None:
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        if h < 12 or w < 60:
            self._safe_addstr(0, 0, "Terminal too small — need 60x12+", curses.color_pair(7))
            self.stdscr.refresh()
            return

        self._draw_header(snap, w)
        safe_hline(self.stdscr, 2, 0, "-", w - 1)

        map_w = max(38, int(w * 0.46))
        feed_x = map_w + 1
        feed_w = w - feed_x - 1
        body_h = h - 6

        self._draw_brain_map(snap, 3, 1, body_h, map_w)
        if feed_w > 20:
            self._draw_learning_feed(snap, 3, feed_x, body_h, feed_w)

        self._draw_agents_bar(snap, h - 3, w)
        self.stdscr.refresh()

    def run(self, *, interval: float = 0.6) -> None:
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(int(interval * 1000))
        while True:
            snap = collect_snapshot()
            self.draw(snap)
            self.tick += 1
            self.flow_phase += 1
            ch = self.stdscr.getch()
            if ch in (ord("q"), ord("Q"), 27):
                break
            if ch == curses.KEY_RESIZE:
                continue


def main() -> int:
    if "--once" in sys.argv:
        from field_monitor_data import format_snapshot_text  # noqa: WPS433

        print(format_snapshot_text(collect_snapshot()))
        print("OK monitor-once")
        return 0

    try:
        curses.wrapper(lambda stdscr: Hostess7Monitor(stdscr).run())
    except KeyboardInterrupt:
        pass
    print("OK monitor")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())