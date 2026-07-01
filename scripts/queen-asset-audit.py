#!/usr/bin/env pythong
"""Audit Queen + NEXUS images — local branding only, OCR spot-check."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUEEN = ROOT / "Queen"
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT)))

OUR_SOURCES = {
    QUEEN / "world" / "assets" / "branding" / "amouranth-gentle.png",
    QUEEN / "world" / "assets" / "branding" / "queen-crown-surprise.svg",
    QUEEN / "world" / "queen-browser-guide.html",
}

LEGACY_REPLACE = ("nexus-tray-us-source.jpg",)

REQUIRED_ICONS = (
    "panel/assets/nexus-field.png",
    "panel/assets/nexus-field-256.png",
    "panel/assets/nexus-field-48.png",
    "panel/assets/nexus-field-24.png",
    "panel/assets/queen-tray-24.png",
    "panel/assets/nexus-tray-us-24.png",
    "panel/assets/amouranth-panel-avatar.png",
    "panel/assets/amouranth-twitch-avatar.png",
    "assets/nexus-field.png",
)


def _ocr(path: Path) -> str:
    if not path.is_file():
        return ""
    bridge = ROOT / "lib" / "final-eye-h7-ocr.py"
    if bridge.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(bridge), "ocr", str(path)],
                capture_output=True, text=True, timeout=90, check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(ROOT)},
            )
            doc = json.loads(proc.stdout or "{}")
            return str(doc.get("text") or doc.get("ocr") or "")
        except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
            pass
    return ""


def _grep_remote_refs() -> list[str]:
    hits: list[str] = []
    for base in (QUEEN / "world", ROOT / "panel"):
        if not base.is_dir():
            continue
        for fp in base.rglob("*"):
            if fp.suffix not in (".html", ".css", ".js", ".json"):
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for m in re.finditer(r'https?://[^\s"\')]+\.(?:png|jpg|jpeg|svg|webp|gif)', text, re.I):
                hits.append(f"{fp.relative_to(ROOT)}: {m.group(0)}")
    return hits


def main() -> int:
    fail = 0
    print("=== Queen asset audit (local branding) ===")

    for rel in REQUIRED_ICONS:
        p = INSTALL / rel
        if p.is_file() and p.stat().st_size > 80:
            print(f"ICON OK: {rel} ({p.stat().st_size} B)")
        else:
            print(f"ICON FAIL: {rel}")
            fail += 1

    for src in OUR_SOURCES:
        if src.is_file():
            print(f"SOURCE OK: {src.relative_to(ROOT)}")
        else:
            print(f"SOURCE FAIL: {src}")
            fail += 1

    remote = _grep_remote_refs()
    if remote:
        print(f"REMOTE IMG WARN: {len(remote)} http image refs in Queen/panel UI")
        for line in remote[:8]:
            print(f"  {line}")
    else:
        print("REMOTE OK: no http image URLs in Queen/panel shell")

    tray = INSTALL / "panel" / "assets" / "nexus-tray-us-24.png"
    if tray.is_file():
        ocr = _ocr(tray).strip()
        print(f"TRAY OCR ({tray.name}): {ocr[:80] or '(no text — portrait icon)'}")

    for leg in LEGACY_REPLACE:
        p = INSTALL / "panel" / "assets" / leg
        if p.is_file():
            print(f"LEGACY WARN: {leg} still present — superseded by Queen kit")

    doc = {"ok": fail == 0, "failures": fail, "remote_hits": len(remote)}
    print(json.dumps(doc))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())