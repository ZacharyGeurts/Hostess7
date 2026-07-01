#!/usr/bin/env pythong
"""Hostess 7 — one talk window. Scrollable text + graphics, question bar below."""
from __future__ import annotations

import curses
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_brain_core import active_workspace, load_workspace  # noqa: E402
from field_brain_chemistry import chemistry_status  # noqa: E402
from field_storage_check import scan_storage  # noqa: E402
from hostess7_graphics import hemisphere_diagram, storage_bars  # noqa: E402
from hostess7_curses_safe import ascii_bar, safe_addch, safe_hline  # noqa: E402
from hostess7_talk import HELP_TEXT, TalkResult, dispatch  # noqa: E402

# Transcript line: (kind, text) — kinds: user, label, response, system, sep, graphic
TranscriptLine = tuple[str, str]


class HostessUI:
    def __init__(self, stdscr: curses.window) -> None:
        self.stdscr = stdscr
        self.transcript: list[TranscriptLine] = []
        self.scroll = 0
        self.input_buf = ""
        self.storage_cache = scan_storage()
        curses.curs_set(1)
        curses.use_default_colors()
        self._init_colors()
        self._layout()
        ws = load_workspace(active_workspace())
        bias = ws.get("bias", "both")
        hemi = "L↔R" if bias == "both" else ("L" if bias == "left" else "R")
        agents_line = ""
        try:
            from field_agents7 import is_daemon_running  # noqa: WPS433

            if is_daemon_running():
                agents_line = " · 13 agents ON · internet ON"
                os.environ["HOSTESS7_AGENTS"] = "13"
                os.environ["HOSTESS7_INTERNET"] = "1"
                os.environ["HOSTESS7_OUTPUT_WINDOW"] = "1"
                os.environ["HOSTESS7_HUMAN_FACING"] = "1"
                os.environ["HOSTESS7_GFX_WINDOW"] = "1"
        except ImportError:
            pass
        try:
            from field_memes_corpus import ensure_corpus, format_status  # noqa: WPS433

            os.environ.setdefault("HOSTESS7_INTERNET", "1")
            ensure_corpus(seed_if_missing=True)
            memes_line = f" · {format_status()}"
        except ImportError:
            memes_line = ""
        os.environ.setdefault("HOSTESS7_GFX_WINDOW", "1")
        gfx_line = ""
        try:
            from field_gfx_canvas import is_window_running  # noqa: WPS433

            gfx_line = " · Graphics ON" if is_window_running() else " · Graphics (run ./Hostess7Graphics.sh)"
        except ImportError:
            gfx_line = ""
        self._append_system(
            f"Hostess 7 — one being · talk window · {hemi}{agents_line}{gfx_line}\n"
            f"Talk scroll = language only · pixels in Graphics window · /help · /gfx{memes_line}"
        )
        try:
            from field_gfx_canvas import open_canvas, present_scene_for_query  # noqa: WPS433

            present_scene_for_query("hostess7 startup brain hemispheres", storage_report=self.storage_cache)
        except ImportError:
            for line in hemisphere_diagram():
                self._append_graphic(line)

    def _init_colors(self) -> None:
        if not curses.has_colors():
            return
        curses.init_pair(1, curses.COLOR_CYAN, -1)
        curses.init_pair(2, curses.COLOR_WHITE, -1)
        curses.init_pair(3, curses.COLOR_GREEN, -1)
        curses.init_pair(4, curses.COLOR_YELLOW, -1)
        curses.init_pair(5, 252, -1)
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)
        curses.init_pair(7, curses.COLOR_MAGENTA, -1)  # graphics

    def _layout(self) -> None:
        h, w = self.stdscr.getmaxyx()
        self.h = h
        self.w = w
        self.header_h = 2
        self.input_h = 3
        self.body_h = max(4, h - self.header_h - self.input_h)

    def _append_system(self, text: str) -> None:
        for line in text.splitlines():
            self.transcript.append(("system", line))
        self._scroll_bottom()

    def _append_graphic(self, text: str) -> None:
        self.transcript.append(("graphic", text))
        self._scroll_bottom()

    def _append_user(self, text: str) -> None:
        self.transcript.append(("user", f"You: {text}"))
        self._scroll_bottom()

    def _append_talk_result(self, result: TalkResult) -> None:
        if result.kind == "response":
            self.transcript.append(("label", "Hostess 7:"))
        for line in result.text.splitlines():
            kind = "response" if result.kind == "response" else "system"
            self.transcript.append((kind, line))
        # Pixels live in Graphics window — only show pointer line in talk scroll
        for g in result.graphics:
            if g.startswith("(Graphics window"):
                self.transcript.append(("system", g))
            elif os.environ.get("HOSTESS7_GFX_ASCII") == "1":
                self._append_graphic(g)
        if result.kind == "response":
            self.transcript.append(("sep", ""))
        self._scroll_bottom()

    def _scroll_bottom(self) -> None:
        self.scroll = max(0, len(self._wrap_transcript()) - self.body_h)

    def _wrap_transcript(self) -> list[TranscriptLine]:
        wrapped: list[TranscriptLine] = []
        width = max(20, self.w - 2)
        import textwrap

        for kind, text in self.transcript:
            if not text:
                wrapped.append((kind, ""))
                continue
            if kind == "graphic":
                wrapped.append((kind, text[: width - 1]))
                continue
            for wl in textwrap.wrap(text, width=width) or [""]:
                wrapped.append((kind, wl))
        return wrapped

    def _draw(self) -> None:
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        self.h, self.w = h, w
        self.body_h = max(4, h - self.header_h - self.input_h)

        ws = active_workspace()
        ws_data = load_workspace(ws)
        bias = ws_data.get("bias", "both")
        hemi = "L↔R" if bias == "both" else ("L" if bias == "left" else "R")
        chem_top = chemistry_status().get("top", [])
        chem_tag = chem_top[0][0][:4] if chem_top else "syn"
        title = f" HOSTESS 7 | one being | {ws} | {hemi} | lossless | talk "
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(0, 0, title.ljust(w - 1)[: w - 1])
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.attron(curses.color_pair(5))
        hint = " PgUp/PgDn · Enter · /help /storage /gfx · /quit "
        self.stdscr.addstr(1, 0, hint.ljust(w - 1)[: w - 1])
        self.stdscr.attroff(curses.color_pair(5))

        lines = self._wrap_transcript()
        max_scroll = max(0, len(lines) - self.body_h)
        self.scroll = min(self.scroll, max_scroll)
        body_top = self.header_h
        for i in range(self.body_h):
            y = body_top + i
            if y >= h - self.input_h:
                break
            idx = self.scroll + i
            if idx >= len(lines):
                continue
            kind, text = lines[idx]
            attr = curses.color_pair(2)
            if kind == "user":
                attr = curses.color_pair(3) | curses.A_BOLD
            elif kind == "label":
                attr = curses.color_pair(1) | curses.A_BOLD
            elif kind == "system":
                attr = curses.color_pair(4)
            elif kind == "graphic":
                attr = curses.color_pair(7)
            elif kind == "sep":
                text = ascii_bar(min(w - 2, 60))
                attr = curses.color_pair(5)
            try:
                self.stdscr.attron(attr)
                self.stdscr.addstr(y, 0, text.ljust(w - 1)[: w - 1])
                self.stdscr.attroff(attr)
            except curses.error:
                pass

        if len(lines) > self.body_h and w > 4:
            track_x = w - 2
            track_h = self.body_h
            thumb_h = max(1, int(track_h * self.body_h / len(lines)))
            thumb_y = body_top + int((track_h - thumb_h) * self.scroll / max(1, max_scroll))
            self.stdscr.attron(curses.color_pair(5))
            for i in range(track_h):
                y = body_top + i
                ch = "#" if thumb_y <= i < thumb_y + thumb_h else "|"
                safe_addch(self.stdscr, y, track_x, ch)
            pct = int(100 * self.scroll / max(1, max_scroll))
            self.stdscr.addstr(body_top, w - 12, f"{pct:>3}%")
            self.stdscr.attroff(curses.color_pair(5))

        sep_y = h - self.input_h
        self.stdscr.attron(curses.color_pair(5))
        safe_hline(self.stdscr, sep_y, 0, "-", w - 1)
        self.stdscr.attroff(curses.color_pair(5))

        prompt = " Talk: "
        self.stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
        self.stdscr.addstr(h - 2, 0, prompt.ljust(w - 1)[: w - 1])
        self.stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)

        avail = w - len(prompt) - 1
        show = self.input_buf[-avail:] if avail > 0 else ""
        self.stdscr.attron(curses.color_pair(6))
        self.stdscr.addstr(h - 2, len(prompt), show.ljust(avail)[:avail])
        self.stdscr.attroff(curses.color_pair(6))

        self.stdscr.move(h - 2, min(len(prompt) + len(show), w - 2))
        self.stdscr.refresh()

    def _submit(self) -> None:
        q = self.input_buf.strip()
        self.input_buf = ""
        if not q:
            return
        if q.lower() in ("/quit", "/exit", "/q", "quit", "exit"):
            raise SystemExit(0)
        if q.lower() in ("/help", "/?"):
            self._append_system(HELP_TEXT)
            return

        if not q.startswith("/"):
            self._append_user(q)

        self._draw()
        if not q.startswith("/"):
            self.transcript.append(("system", "Processing…"))
            self._draw()
            self.stdscr.refresh()

        result = dispatch(q, storage_cache=self.storage_cache)
        if q.startswith("/") and q.lower() not in ("/help", "/?"):
            self._append_talk_result(result)
        else:
            if self.transcript and self.transcript[-1] == ("system", "Processing…"):
                self.transcript.pop()
            self._append_talk_result(result)

        if q.lower() in ("/storage", "/drive", "/lossless"):
            self.storage_cache = scan_storage()

        if os.environ.get("HOSTESS7_VOICE", "0") == "1" and result.text:
            voice = ROOT / "scripts" / "hostess7_voice.py"
            if voice.is_file():
                import subprocess
                subprocess.run(
                    [sys.executable, str(voice), "speak", result.text[:800]],
                    cwd=ROOT, check=False,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )

    def run(self) -> None:
        self._draw()
        while True:
            try:
                ch = self.stdscr.getch()
            except KeyboardInterrupt:
                break
            if ch == curses.KEY_RESIZE:
                self._layout()
                self._draw()
                continue
            if ch == curses.KEY_PPAGE:
                self.scroll = max(0, self.scroll - self.body_h // 2)
                self._draw()
                continue
            if ch == curses.KEY_NPAGE:
                lines = self._wrap_transcript()
                max_scroll = max(0, len(lines) - self.body_h)
                self.scroll = min(max_scroll, self.scroll + self.body_h // 2)
                self._draw()
                continue
            if ch == curses.KEY_UP:
                self.scroll = max(0, self.scroll - 1)
                self._draw()
                continue
            if ch == curses.KEY_DOWN:
                lines = self._wrap_transcript()
                max_scroll = max(0, len(lines) - self.body_h)
                self.scroll = min(max_scroll, self.scroll + 1)
                self._draw()
                continue
            if ch in (10, 13, curses.KEY_ENTER):
                self._submit()
                self._draw()
                continue
            if ch in (127, curses.KEY_BACKSPACE, 8):
                self.input_buf = self.input_buf[:-1]
                self._draw()
                continue
            if ch == 27:
                break
            if 32 <= ch <= 126:
                self.input_buf += chr(ch)
                self._draw()


def main() -> int:
    os.environ.setdefault("HOSTESS7_VOICE", "0")
    os.environ.setdefault("HOSTESS7_GFX", "1")
    os.environ.setdefault("AMOURANTHRTX_HOSTESS", "1")
    os.environ.setdefault("HOSTESS7_PRO", "1")
    try:
        curses.wrapper(lambda s: HostessUI(s).run())
    except SystemExit:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())