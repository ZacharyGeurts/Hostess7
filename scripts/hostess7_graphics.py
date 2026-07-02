#!/usr/bin/env pythong
"""Hostess 7 graphics routing — pixel Graphics window (default) or legacy ASCII."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

# Legacy ASCII helpers kept for monitor / headless fallback only
BRAILLE_BASE = 0x2800


def _use_pixel_window() -> bool:
    return os.environ.get("HOSTESS7_GFX_ASCII", "0") != "1" and os.environ.get(
        "HOSTESS7_GFX_WINDOW", "1"
    ) != "0"


def graphics_for_query(query: str, *, storage_report: dict[str, Any] | None = None) -> list[str]:
    """Route graphics — pixels go to Graphics window; returns status lines for talk scroll."""
    if _use_pixel_window():
        try:
            from field_gfx_canvas import present_scene_for_query  # noqa: WPS433

            st = present_scene_for_query(query, storage_report=storage_report)
            if st:
                return [f"(Graphics window · {st.get('width')}×{st.get('height')} · v{st.get('version')})"]
        except ImportError:
            pass
    return _ascii_graphics_for_query(query, storage_report=storage_report)


def push_pixels_for_query(query: str, *, storage_report: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Direct pixel push — agents and Vision call this."""
    try:
        from field_gfx_canvas import present_scene_for_query  # noqa: WPS433

        return present_scene_for_query(query, storage_report=storage_report)
    except ImportError:
        return None


# --- Legacy ASCII (HOSTESS7_GFX_ASCII=1 or no Pillow/GTK) ---

def tv_smpte_bars(width: int = 64, height: int = 8) -> list[str]:
    bars = [("█", "white"), ("█", "yellow"), ("█", "cyan"), ("█", "green"),
            ("█", "magenta"), ("█", "red"), ("█", "blue")]
    w_each = max(4, width // len(bars))
    row = "".join(ch * w_each for ch, _ in bars)[:width]
    lines = [f"TV SMPTE bars ({width}×{height}):"]
    for _ in range(height):
        lines.append(row)
    return lines


def pixel_grid(width: int = 32, height: int = 16, *, checker: bool = True) -> list[str]:
    lines = [f"Pixel grid {width}×{height} (ASCII fallback):"]
    for y in range(height):
        row = []
        for x in range(width):
            on = (x // 4 + y // 2) % 2 == 0 if checker else ((x * 7 + y * 13) % 17) < 9
            row.append("██" if on else "  ")
        lines.append("".join(row)[: width * 2])
    return lines


def storage_bars(report: dict[str, Any], width: int = 48) -> list[str]:
    total = max(1, int(report.get("total_bytes") or 1))
    parts = [
        ("brain", int(report.get("brain_bytes") or 0), "█"),
        ("wave", int(report.get("field_wave_bytes") or 0), "▓"),
        ("staging", int(report.get("staging_bytes") or 0), "░"),
        ("team", int(report.get("team_drive_bytes") or 0), "▒"),
    ]
    lines = ["Storage (ASCII fallback):"]
    for label, nbytes, ch in parts:
        frac = nbytes / total
        bar_len = max(0, int(frac * width))
        mb = nbytes / (1024 * 1024)
        lines.append(f"{label:8} {ch * bar_len:<{width}} {mb:6.1f} MiB")
    return lines


def hemisphere_diagram() -> list[str]:
    return [
        "Hostess 7 — one being (hemispheres):",
        "    ┌──────── LEFT ────────┐     ═══ callosum ═══     ┌────── RIGHT ───────┐",
        "    │ code · legal · shell │ ◄──────────────────────► │ vision · TV · pixel │",
        "    └──────────────────────┘                          └─────────────────────┘",
    ]


def chroma_subsampling_diagram() -> list[str]:
    return [
        "Chroma / lossless priority:",
        "  4:4:4 lossless PNG/PPM  full pixel truth",
        "  Hostess 7 Graphics window = authoritative pixels (not ASCII)",
    ]


def _ascii_graphics_for_query(query: str, *, storage_report: dict[str, Any] | None = None) -> list[str]:
    q = query.lower()
    gfx: list[str] = []
    if any(k in q for k in ("meme", "memes", "tarot", "stamp")):
        try:
            from field_memes_corpus import graphics_for_memes_query  # noqa: WPS433
            gfx.extend(graphics_for_memes_query(query))
        except ImportError:
            pass
    if storage_report and any(k in q for k in ("storage", "drive", "lossless")):
        gfx.extend(storage_bars(storage_report))
    if any(k in q for k in ("tv", "smpte", "broadcast")):
        gfx.extend(tv_smpte_bars())
    if any(k in q for k in ("pixel", "grid")):
        gfx.extend(pixel_grid(28, 10))
    if any(k in q for k in ("brain", "hemisphere")):
        gfx.extend(hemisphere_diagram())
    return gfx


if __name__ == "__main__":
    import sys
    from field_storage_check import scan_storage  # noqa: E402

    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "tv pixel storage"
    for line in graphics_for_query(q, storage_report=scan_storage()):
        print(line)