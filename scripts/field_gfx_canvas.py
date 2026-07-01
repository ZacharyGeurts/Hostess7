#!/usr/bin/env pythong
"""Hostess7 Graphics canvas — lossless RGB pixels + text for the Graphics window.

Agents and Vision use this instead of ASCII. Commands queue to gfx/inbox.jsonl;
framebuffer writes gfx/frame.png — the GTK Graphics window presents it.

  from field_gfx_canvas import GfxCanvas, open_canvas, present_scene_for_query

  c = open_canvas()
  c.fill(18, 22, 30)
  c.pixel(100, 50, 255, 128, 64)
  c.text(24, 40, "Hostess 7", (230, 235, 245), size=22)
  c.blit_image(200, 120, "cache/fieldstorage/brain/memes/images/stamp.png")
  c.present()
"""
from __future__ import annotations

import json
import os
import struct
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

GFX_DIR = ROOT / "cache" / "fieldstorage" / "brain" / "gfx"
FRAME_PNG = GFX_DIR / "frame.png"
FRAME_RAW = GFX_DIR / "frame.raw"
STATE_FILE = GFX_DIR / "state.json"
INBOX = GFX_DIR / "inbox.jsonl"
PID_FILE = GFX_DIR / "window.pid"

DEFAULT_W = 1024
DEFAULT_H = 576


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure() -> None:
    GFX_DIR.mkdir(parents=True, exist_ok=True)


def gfx_window_enabled() -> bool:
    return os.environ.get("HOSTESS7_GFX_WINDOW", "1") != "0"


def _load_state() -> dict[str, Any]:
    _ensure()
    if not STATE_FILE.is_file():
        return {"version": 0, "width": DEFAULT_W, "height": DEFAULT_H}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"version": 0, "width": DEFAULT_W, "height": DEFAULT_H}


def _save_state(state: dict[str, Any]) -> None:
    _ensure()
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def _log_ops(ops: list[dict[str, Any]]) -> None:
    if not ops:
        return
    _ensure()
    with INBOX.open("a", encoding="utf-8") as f:
        for cmd in ops[-32:]:
            f.write(json.dumps({"ts": _ts(), **cmd}) + "\n")


class GfxCanvas:
    """Lossless RGB888 framebuffer — place pixels and text, then present()."""

    def __init__(self, width: int = DEFAULT_W, height: int = DEFAULT_H) -> None:
        self.width = max(64, int(width))
        self.height = max(64, int(height))
        self._buf = bytearray(self.width * self.height * 3)
        self._version = 0
        self._ops: list[dict[str, Any]] = []

    def _idx(self, x: int, y: int) -> int:
        if 0 <= x < self.width and 0 <= y < self.height:
            return (y * self.width + x) * 3
        return -1

    def fill(self, r: int, g: int, b: int) -> GfxCanvas:
        r, g, b = r & 255, g & 255, b & 255
        row = bytes([r, g, b]) * self.width
        for y in range(self.height):
            start = y * self.width * 3
            self._buf[start : start + self.width * 3] = row
        self._ops.append({"op": "fill", "color": [r, g, b]})
        return self

    def pixel(self, x: int, y: int, r: int, g: int, b: int) -> GfxCanvas:
        i = self._idx(x, y)
        if i >= 0:
            self._buf[i] = r & 255
            self._buf[i + 1] = g & 255
            self._buf[i + 2] = b & 255
        return self

    def rect(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        r: int,
        g: int,
        b: int,
        *,
        filled: bool = True,
    ) -> GfxCanvas:
        if filled:
            for dy in range(max(0, h)):
                for dx in range(max(0, w)):
                    self.pixel(x + dx, y + dy, r, g, b)
        else:
            for dx in range(w):
                self.pixel(x + dx, y, r, g, b)
                self.pixel(x + dx, y + h - 1, r, g, b)
            for dy in range(h):
                self.pixel(x, y + dy, r, g, b)
                self.pixel(x + w - 1, y + dy, r, g, b)
        self._ops.append({"op": "rect", "x": x, "y": y, "w": w, "h": h, "color": [r, g, b], "filled": filled})
        return self

    def text(
        self,
        x: int,
        y: int,
        string: str,
        color: tuple[int, int, int] = (230, 235, 245),
        *,
        size: int = 16,
    ) -> GfxCanvas:
        if not string:
            return self
        try:
            from PIL import Image, ImageDraw, ImageFont  # noqa: WPS433

            img = Image.frombytes("RGB", (self.width, self.height), bytes(self._buf))
            draw = ImageDraw.Draw(img)
            try:
                font = ImageFont.truetype("DejaVuSans.ttf", size)
            except OSError:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
                except OSError:
                    font = ImageFont.load_default()
            draw.text((x, y), string, fill=color, font=font)
            self._buf[:] = img.tobytes()
        except ImportError:
            # Fallback: block letter placeholders as 4x6 pixels per char
            for i, ch in enumerate(string[:120]):
                cx = x + i * (size // 2 + 2)
                self.rect(cx, y, size // 3, size // 2, *color)
        self._ops.append({"op": "text", "x": x, "y": y, "text": string[:500], "color": list(color), "size": size})
        return self

    def blit_image(self, x: int, y: int, path: str | Path, *, max_w: int | None = None) -> GfxCanvas:
        path = Path(path)
        if not path.is_file():
            self._ops.append({"op": "image", "x": x, "y": y, "path": str(path), "ok": False})
            return self
        try:
            from PIL import Image  # noqa: WPS433

            img = Image.open(path).convert("RGB")
            if max_w and img.width > max_w:
                ratio = max_w / img.width
                img = img.resize((max_w, max(1, int(img.height * ratio))))
            base = Image.frombytes("RGB", (self.width, self.height), bytes(self._buf))
            base.paste(img, (x, y))
            self._buf[:] = base.tobytes()
            self._ops.append({"op": "image", "x": x, "y": y, "path": str(path), "ok": True})
        except ImportError:
            self.text(x, y, f"[{path.name}]", (180, 180, 200))
        except OSError:
            self.text(x, y, f"(bad image {path.name})", (255, 100, 100))
        return self

    def smpte_bars(self, *, bar_h: int | None = None) -> GfxCanvas:
        colors = [
            (235, 235, 235),
            (235, 235, 0),
            (0, 235, 235),
            (0, 235, 0),
            (235, 0, 235),
            (235, 0, 0),
            (0, 0, 235),
        ]
        h = bar_h or self.height // 2
        bw = self.width // len(colors)
        for i, rgb in enumerate(colors):
            self.rect(i * bw, 40, bw, h, *rgb)
        self.text(16, 12, "SMPTE bars — lossless pixels", (200, 210, 220), size=18)
        return self

    def storage_chart(self, report: dict[str, Any]) -> GfxCanvas:
        self.fill(18, 22, 30)
        self.text(16, 12, "Field storage (lossless)", (180, 220, 255), size=20)
        total = max(1, int(report.get("total_bytes") or 1))
        parts = [
            ("brain", int(report.get("brain_bytes") or 0), (80, 180, 255)),
            ("wave", int(report.get("field_wave_bytes") or 0), (120, 200, 160)),
            ("staging", int(report.get("staging_bytes") or 0), (200, 180, 100)),
            ("team", int(report.get("team_drive_bytes") or 0), (180, 120, 220)),
        ]
        y = 56
        bar_max = self.width - 220
        for label, nbytes, rgb in parts:
            frac = nbytes / total
            w = max(2, int(frac * bar_max))
            self.text(16, y, f"{label}", (200, 200, 210), size=14)
            self.rect(120, y, w, 14, *rgb)
            mb = nbytes / (1024 * 1024)
            self.text(130 + w, y, f"{mb:.1f} MiB", (160, 170, 180), size=13)
            y += 28
        return self

    def to_png(self, path: Path | None = None) -> Path:
        path = path or FRAME_PNG
        _ensure()
        try:
            from PIL import Image  # noqa: WPS433

            img = Image.frombytes("RGB", (self.width, self.height), bytes(self._buf))
            img.save(path, format="PNG", compress_level=1)
        except ImportError:
            path.write_bytes(self._raw_bytes())
        return path

    def _raw_bytes(self) -> bytes:
        header = struct.pack("<II", self.width, self.height)
        return header + bytes(self._buf)

    def present(self, *, label: str = "") -> dict[str, Any]:
        """Flush framebuffer to disk — Graphics window picks it up."""
        _ensure()
        self._version += 1
        self.to_png(FRAME_PNG)
        FRAME_RAW.write_bytes(self._raw_bytes())
        state = {
            "version": self._version,
            "width": self.width,
            "height": self.height,
            "updated": _ts(),
            "label": label,
            "path": str(FRAME_PNG),
        }
        _save_state(state)
        self._ops.append({"op": "present", "version": self._version, "label": label})
        _log_ops(self._ops)
        self._ops.clear()
        return state


def open_canvas(width: int | None = None, height: int | None = None) -> GfxCanvas:
    st = _load_state()
    return GfxCanvas(width or st.get("width", DEFAULT_W), height or st.get("height", DEFAULT_H))


def present_scene_for_query(
    query: str,
    *,
    storage_report: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Vision/Language routing — build a pixel scene for the Graphics window."""
    if not gfx_window_enabled():
        return None
    q = query.lower()
    c = open_canvas()
    c.fill(18, 22, 30)
    c.text(16, 12, "Hostess 7 Graphics", (140, 200, 255), size=22)

    drew = False
    if storage_report and any(k in q for k in ("storage", "drive", "lossless", "field storage")):
        c.storage_chart(storage_report)
        drew = True
    elif any(k in q for k in ("tv", "smpte", "broadcast", "bars")):
        c.smpte_bars()
        drew = True
    elif any(k in q for k in ("meme", "stamp", "image", "picture", "photo", "tarot")):
        try:
            from field_image_talk import pick_local_image  # noqa: WPS433

            found = pick_local_image(
                query,
                [
                    ROOT / "cache" / "fieldstorage" / "brain" / "memes" / "images",
                    ROOT / "cache" / "fieldstorage" / "brain" / "internet" / "cache",
                ],
            )
            if found:
                c.text(16, 44, found.name, (200, 200, 210), size=14)
                c.blit_image(16, 72, found, max_w=c.width - 32)
                drew = True
        except ImportError:
            pass
    elif any(k in q for k in ("pixel", "framebuffer", "grid", "4k")):
        step = 8
        for y in range(0, c.height, step):
            for x in range(0, c.width, step):
                if ((x // step) + (y // step)) % 2 == 0:
                    c.rect(x, y, step, step, 40, 48, 62)
                else:
                    c.rect(x, y, step, step, 28, 34, 46)
        c.text(16, 44, f"Pixel grid {c.width}x{c.height}", (180, 190, 200), size=16)
        drew = True
    elif any(k in q for k in ("brain", "hemisphere", "callosum")):
        c.rect(40, 100, 360, 200, 50, 90, 140)
        c.rect(620, 100, 360, 200, 140, 70, 120)
        c.text(120, 120, "LEFT", (220, 230, 240), size=24)
        c.text(700, 120, "RIGHT", (220, 230, 240), size=24)
        c.text(430, 190, "callosum", (180, 200, 220), size=18)
        drew = True

    if not drew:
        c.text(16, 48, query[:80], (200, 210, 220), size=16)
        c.text(16, 80, "Place pixels: field_gfx_canvas.GfxCanvas", (140, 150, 160), size=13)

    return c.present(label=query[:120])


def format_gfx_api_help() -> str:
    return """
Hostess7 Graphics window API (pixels + text — not ASCII):
  from field_gfx_canvas import open_canvas
  c = open_canvas()
  c.fill(r,g,b) · c.pixel(x,y,r,g,b) · c.rect(x,y,w,h,r,g,b)
  c.text(x,y,"Hello", (230,235,245), size=18)
  c.blit_image(x,y, path) · c.present()
Commands: ./Hostess7.sh gfx · ./Hostess7Graphics.sh
""".strip()


def is_window_running() -> bool:
    if not PID_FILE.is_file():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError):
        return False


def main() -> int:
    import sys

    _ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if cmd == "demo":
        c = open_canvas()
        c.fill(18, 22, 30)
        c.smpte_bars()
        c.text(16, c.height - 36, "Hostess 7 — Graphics window ready", (200, 220, 255), size=18)
        st = c.present(label="demo")
        print(json.dumps(st, indent=2))
        print("OK gfx-demo")
        return 0
    if cmd == "status":
        print(json.dumps(_load_state(), indent=2))
        print(f"window_running={is_window_running()}")
        return 0
    if cmd == "help":
        print(format_gfx_api_help())
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())