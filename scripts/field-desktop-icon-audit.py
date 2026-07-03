#!/usr/bin/env pythong
"""Final_Eye desktop icon audit — 4 cartoony PNGs + tray kit; store manifest in SG/ZACS."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZACS = Path(os.environ.get("SG_ZACS_ROOT", str(ROOT.parent / "ZACS")))
DESKTOP_ICONS = (
    ("view", "queen-prog-view.png"),
    ("queen-terminal", "queen-prog-terminal.png"),
    ("queen-browser", "queen-prog-browser.png"),
    ("field-broadcaster", "queen-prog-field.png"),
)
TRAY_ICONS = (
    "nexus-tray-us-24.png",
    "queen-tray-24.png",
    "nexus-field-48.png",
)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ocr(path: Path) -> dict:
    bridge = ROOT / "lib" / "final-eye-h7-ocr.py"
    if not bridge.is_file() or not path.is_file():
        return {"ok": False, "text": ""}
    try:
        proc = subprocess.run(
            [sys.executable, str(bridge), "ocr", str(path)],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(ROOT)},
        )
        doc = json.loads(proc.stdout or "{}")
        return {"ok": bool(doc.get("ok", True)), "text": str(doc.get("text") or doc.get("ocr") or "")[:200]}
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": type(exc).__name__, "text": ""}


def main() -> int:
    ZACS.mkdir(parents=True, exist_ok=True)
    assets = ROOT / "panel" / "assets"
    rows: list[dict] = []
    fail = 0

    for app_id, fname in DESKTOP_ICONS:
        path = assets / fname
        ok = path.is_file() and path.stat().st_size > 80
        ocr = _ocr(path) if ok else {"ok": False, "text": ""}
        row = {
            "id": app_id,
            "file": f"panel/assets/{fname}",
            "bytes": path.stat().st_size if ok else 0,
            "ok": ok,
            "final_eye": ocr,
        }
        rows.append(row)
        if not ok:
            fail += 1
        print(f"{'OK' if ok else 'FAIL'} desktop {app_id}: {fname}")

    for fname in TRAY_ICONS:
        path = assets / fname
        ok = path.is_file() and path.stat().st_size > 80
        ocr = _ocr(path) if ok else {"ok": False, "text": ""}
        rows.append({"id": fname, "file": f"panel/assets/{fname}", "bytes": path.stat().st_size if ok else 0, "ok": ok, "final_eye": ocr})
        if not ok:
            fail += 1
        print(f"{'OK' if ok else 'FAIL'} tray {fname}")

    manifest = {
        "schema": "sg-zacs-field-desktop-icon-audit/v1",
        "product": "AmmoOS",
        "auditor": "Final_Eye",
        "exported": _ts(),
        "install_root": str(ROOT),
        "zacs_root": str(ZACS),
        "desktop_icon_ids": [r["id"] for r in rows[:4]],
        "ok": fail == 0,
        "failures": fail,
        "icons": rows,
    }
    out = ZACS / "field-desktop-icon-audit.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    latest = ZACS / "field-desktop-icon-audit-latest.json"
    latest.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"ok": fail == 0, "failures": fail, "zacs": str(out)}))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())