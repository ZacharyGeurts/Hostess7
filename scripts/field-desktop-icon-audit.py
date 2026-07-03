#!/usr/bin/env pythong
"""Final_Eye desktop icon audit — Military EOL inspect; PNG + manifest in SG/ZACS."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SG = Path(os.environ.get("SG_ROOT", str(ROOT.parent)))
ZACS = Path(os.environ.get("SG_ZACS_ROOT", str(SG / "ZACS")))
ZACS_PNG = ZACS / "png"
FINAL_EYE_OUT = Path(os.environ.get("FINAL_EYE_ROOT", str(SG / "Final_Eye"))) / "out"
FINAL_EYE_PRESERVE = Path(os.environ.get("FINAL_EYE_ROOT", str(SG / "Final_Eye"))) / "data" / "preserve"
DESKTOP_ICONS = (
    ("view", "queen-prog-view.png"),
    ("queen-terminal", "queen-prog-terminal.png"),
    ("field-popcorn", "queen-prog-popcorn.png"),
    ("ammocode", "queen-prog-ammocode.png"),
    ("hostess7-folder", "queen-prog-hostess.png"),
    ("queen-browser", "queen-prog-browser.png"),
    ("field-broadcaster", "queen-prog-broadcaster.png"),
)
TRAY_ICONS = (
    "nexus-tray-us-24.png",
    "queen-tray-24.png",
    "nexus-field-48.png",
)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _latest_final_eye_capture(basename: str) -> Path | None:
    """Newest Final_Eye/out PNG whose name ends with the panel asset basename."""
    if not FINAL_EYE_OUT.is_dir():
        return None
    hits = sorted(
        (p for p in FINAL_EYE_OUT.glob("*.png") if p.name.endswith(f"_{basename}") or p.name.endswith(basename)),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return hits[0] if hits else None


def _export_png(src: Path, dest_name: str, *, subdir: str = "") -> dict:
    ZACS_PNG.mkdir(parents=True, exist_ok=True)
    dest_dir = ZACS_PNG / subdir if subdir else ZACS_PNG
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / dest_name
    if not src.is_file():
        return {"ok": False, "src": str(src), "dest": str(dest)}
    shutil.copy2(src, dest)
    return {
        "ok": True,
        "src": str(src),
        "dest": str(dest),
        "bytes": dest.stat().st_size,
        "sha256": None,
    }


def _inspect(path: Path) -> dict:
    bridge = ROOT / "lib" / "hostess7-military-eol-ocr.py"
    if not bridge.is_file() or not path.is_file():
        return {"ok": False, "text": ""}
    try:
        proc = subprocess.run(
            [sys.executable, str(bridge), "inspect", str(path)],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(ROOT), "SG_ROOT": str(ROOT.parent)},
        )
        doc = json.loads(proc.stdout or "{}")
        neural = doc.get("neural") or {}
        text = doc.get("text") or neural.get("top_label") or ""
        return {
            "ok": bool(doc.get("ok")),
            "engine": doc.get("engine", "Hostess7/MilitaryEOL"),
            "glyph_icon": doc.get("glyph_icon"),
            "width": doc.get("width"),
            "height": doc.get("height"),
            "sha256": doc.get("sha256"),
            "neural_label": neural.get("top_label"),
            "text": str(text)[:200],
        }
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": type(exc).__name__, "text": ""}


def main() -> int:
    ZACS.mkdir(parents=True, exist_ok=True)
    ZACS_PNG.mkdir(parents=True, exist_ok=True)
    assets = ROOT / "panel" / "assets"
    rows: list[dict] = []
    png_exports: list[dict] = []
    fail = 0
    eye_fail = 0

    def _row_for(path: Path, row_id: str, rel_file: str) -> dict:
        nonlocal fail, eye_fail
        fname = path.name
        ok = path.is_file() and path.stat().st_size > 80
        inspect = _inspect(path) if ok else {"ok": False, "text": ""}
        zacs_png = _export_png(path, fname)
        if zacs_png.get("ok"):
            png_exports.append(zacs_png)
        capture = _latest_final_eye_capture(fname)
        capture_export: dict | None = None
        if capture is not None:
            capture_export = _export_png(capture, capture.name, subdir="final-eye-captures")
            if capture_export.get("ok"):
                png_exports.append(capture_export)
        row = {
            "id": row_id,
            "file": rel_file,
            "bytes": path.stat().st_size if ok else 0,
            "ok": ok and inspect.get("ok"),
            "final_eye": inspect,
            "zacs_png": str(ZACS_PNG / fname) if zacs_png.get("ok") else None,
            "final_eye_capture": str(capture) if capture else None,
            "zacs_capture_png": capture_export.get("dest") if capture_export and capture_export.get("ok") else None,
        }
        if not ok:
            fail += 1
        elif not inspect.get("ok"):
            eye_fail += 1
        return row

    for app_id, fname in DESKTOP_ICONS:
        path = assets / fname
        row = _row_for(path, app_id, f"panel/assets/{fname}")
        rows.append(row)
        print(f"{'OK' if row['ok'] else 'FAIL'} desktop {app_id}: {fname}")

    for fname in TRAY_ICONS:
        path = assets / fname
        row = _row_for(path, fname, f"panel/assets/{fname}")
        rows.append(row)
        print(f"{'OK' if row['ok'] else 'FAIL'} tray {fname}")

    preserve_png = FINAL_EYE_PRESERVE / "last-good.png"
    if preserve_png.is_file():
        pe = _export_png(preserve_png, "preserve-last-good.png", subdir="preserve")
        if pe.get("ok"):
            png_exports.append(pe)
            rows.append({
                "id": "preserve-last-good",
                "file": str(preserve_png.relative_to(FINAL_EYE_PRESERVE.parent.parent)),
                "bytes": preserve_png.stat().st_size,
                "ok": True,
                "final_eye": _inspect(preserve_png),
                "zacs_png": pe.get("dest"),
            })

    manifest = {
        "schema": "sg-zacs-field-desktop-icon-audit/v3",
        "product": "AmmoOS",
        "auditor": "Final_Eye",
        "engine": "Hostess7/MilitaryEOL",
        "exported": _ts(),
        "install_root": str(ROOT),
        "zacs_root": str(ZACS),
        "zacs_png_dir": str(ZACS_PNG),
        "final_eye_out": str(FINAL_EYE_OUT),
        "png_count": len(png_exports),
        "desktop_icon_ids": [r["id"] for r in rows if r["id"] in {
            "view", "queen-terminal", "field-popcorn", "ammocode", "hostess7-folder",
            "queen-browser", "field-broadcaster",
        }],
        "ok": fail == 0 and eye_fail == 0,
        "failures": fail + eye_fail,
        "icons": rows,
        "png_exports": png_exports,
    }
    out = ZACS / "field-desktop-icon-audit.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    latest = ZACS / "field-desktop-icon-audit-latest.json"
    latest.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({
        "ok": manifest["ok"],
        "failures": manifest["failures"],
        "png_count": manifest["png_count"],
        "zacs": str(out),
        "zacs_png_dir": str(ZACS_PNG),
    }))
    return 1 if manifest["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())