#!/usr/bin/env pythong
"""Hostess7 Graphics window — GTK3 pixel framebuffer (not ASCII)."""
from __future__ import annotations

import json
import os
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

os.environ.setdefault("NO_AT_BRIDGE", "1")
os.environ.setdefault("GTK_A11Y", "none")

from field_gfx_canvas import FRAME_PNG, GFX_DIR, PID_FILE, STATE_FILE, _load_state  # noqa: E402

try:
    import gi

    gi.require_version("Gtk", "3.0")
    from gi.repository import GdkPixbuf, GLib, Gtk  # noqa: E402
except ImportError as exc:
    print(f"BLOCKER: GTK3 required for Graphics window: {exc}", file=sys.stderr)
    raise SystemExit(1)


class HostessGfxWindow:
    def __init__(self) -> None:
        self._last_version = -1
        self.window = Gtk.Window(title="Hostess 7 Graphics")
        self.window.set_default_size(1024, 640)
        self.window.connect("destroy", Gtk.main_quit)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.label = Gtk.Label(label="Hostess 7 — pixel canvas")
        self.label.set_margin_start(8)
        self.image = Gtk.Image()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.image)

        box.pack_start(self.label, False, False, 0)
        box.pack_start(scroll, True, True, 0)
        self.window.add(box)

        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

        GLib.timeout_add(33, self._tick)
        self._tick()

    def _tick(self) -> bool:
        state = _load_state()
        ver = int(state.get("version", 0))
        if ver != self._last_version and FRAME_PNG.is_file():
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file(str(FRAME_PNG))
                self.image.set_from_pixbuf(pix)
                label = state.get("label") or ""
                w = state.get("width", "?")
                h = state.get("height", "?")
                self.label.set_text(
                    f"Hostess 7 Graphics · {w}×{h} · v{ver}"
                    + (f" · {label[:60]}" if label else "")
                )
                self._last_version = ver
            except GLib.Error:
                pass
        return True

    def run(self) -> None:
        self.window.show_all()
        Gtk.main()


def _shutdown(*_args: object) -> None:
    PID_FILE.unlink(missing_ok=True)
    Gtk.main_quit()


def main() -> int:
    GFX_DIR.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    try:
        HostessGfxWindow().run()
    finally:
        PID_FILE.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())