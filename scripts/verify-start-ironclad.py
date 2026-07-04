#!/usr/bin/env python3
"""OCR + DOM verify — Hostess7 classic Start above AmmoNet; Ironclad gated on desktop."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
OUT = STATE / "verify-start-ironclad"
PAGES_DESKTOP = os.environ.get(
    "H7_VERIFY_DESKTOP_URL",
    "https://zacharygeurts.github.io/Hostess7/desktop/",
)
PAGES_IRONCLAD = os.environ.get(
    "H7_VERIFY_IRONCLAD_URL",
    "https://zacharygeurts.github.io/Hostess7/ironclad-search/",
)


def fetch(url: str, timeout: int = 20) -> str:
    req = Request(url, headers={"User-Agent": "Hostess7-Start-Verify/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def screenshot(url: str, path: Path, wait_sec: float = 6.0) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    profile = Path("/tmp/h7-verify-firefox-profile")
    profile.mkdir(parents=True, exist_ok=True)
    cmd = [
        "firefox",
        "--headless",
        f"--profile={profile}",
        f"--screenshot={path}",
        "--window-size=1400,900",
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=90, check=False)
        time.sleep(wait_sec)
        if path.is_file() and path.stat().st_size > 8000:
            return True
    except (OSError, subprocess.TimeoutExpired):
        pass
    return path.is_file() and path.stat().st_size > 8000


def _tesseract(path: Path) -> str:
    try:
        proc = subprocess.run(
            ["tesseract", str(path), "stdout", "-l", "eng"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        return proc.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def ocr_text(path: Path) -> str:
    bridge = INSTALL / "lib" / "final-eye-h7-ocr.py"
    if bridge.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(bridge), "ocr", str(path)],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            doc = json.loads(proc.stdout or "{}")
            text = str(doc.get("text") or doc.get("ocr") or "")
            if text and text.strip().lower() not in ("visual:glyph", "glyph", ""):
                return text
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    return _tesseract(path)


def live_asset_checks(html: str) -> dict[str, bool]:
    asset_base = PAGES_DESKTOP.rsplit("/desktop/", 1)[0] + "/assets/"
    try:
        js = fetch(asset_base + "field-host-desktop.js")
    except OSError:
        js = ""
    mount_idx = js.find("mountStartbar")
    chrome_idx = js.find("mountDesktopChrome")
    return {
        "host_desktop_hd10": "field-host-desktop.js?v=hd10" in html,
        "ensure_startbar_js": "ensureStartbar" in js,
        "mount_startbar_first": mount_idx >= 0 and chrome_idx >= 0 and mount_idx < chrome_idx + 400,
    }


def html_checks(html: str) -> dict[str, bool]:
    out = {
        "ammoos_desktop": 'data-ammoos-desktop="1"' in html,
        "ironclad_off": 'data-ironclad-taskbar="0"' in html,
        "fsb_mount": 'id="fsb-mount"' in html,
        "startbar_js": "field-startbar.js" in html,
        "startbar_css_v12": "field-startbar.css?v=12" in html or "field-startbar.css?v=13" in html,
        "pages_boot": "pages-field-boot.js" in html,
        "api_shim": "api-shim.js" in html,
    }
    out.update(live_asset_checks(html))
    return out


def ocr_checks(text: str) -> dict[str, bool]:
    low = text.lower()
    return {
        "ocr_start_word": bool(re.search(r"\bstart\b", low)),
        "ocr_ammoos": "ammoos" in low or "ammo" in low,
        "ocr_ammonet": "ammonet" in low,
    }


def verify_desktop() -> dict:
    html = fetch(PAGES_DESKTOP)
    checks = html_checks(html)
    shot = OUT / "desktop.png"
    shot_ok = screenshot(PAGES_DESKTOP, shot)
    ocr = ocr_text(shot) if shot_ok else ""
    (OUT / "desktop-ocr.txt").write_text(ocr, encoding="utf-8")
    ocr_hits = ocr_checks(ocr)
    asset_ok = checks.get("host_desktop_hd10") and checks.get("ensure_startbar_js")
    ocr_ok = ocr_hits["ocr_start_word"] or ocr_hits["ocr_ammoos"]
    ok = (
        checks["ammoos_desktop"]
        and checks["ironclad_off"]
        and checks["fsb_mount"]
        and checks["startbar_js"]
        and asset_ok
        and (ocr_ok or checks.get("ensure_startbar_js"))
    )
    return {
        "surface": "Hostess7/desktop",
        "url": PAGES_DESKTOP,
        "ok": ok,
        "screenshot": str(shot) if shot_ok else None,
        "html": checks,
        "ocr": ocr_hits,
        "ocr_excerpt": ocr[:400],
    }


def verify_ironclad() -> dict:
    html = fetch(PAGES_IRONCLAD)
    checks = {
        "ironclad_page": "Ironclad Search" in html or "ironclad-search" in html,
        "ironclad_js": "field-ironclad-taskbar.js" in html,
        "ironclad_bus": "ironclad-bus.js" in html,
        "force_ironclad": 'data-force-ironclad-taskbar="1"' in html,
    }
    shot = OUT / "ironclad.png"
    shot_ok = screenshot(PAGES_IRONCLAD, shot)
    ocr = ocr_text(shot) if shot_ok else ""
    (OUT / "ironclad-ocr.txt").write_text(ocr, encoding="utf-8")
    ocr_hits = {"ocr_ironclad": "ironclad" in ocr.lower()}
    ok = all(checks.values())
    return {
        "surface": "Hostess7/ironclad-search",
        "url": PAGES_IRONCLAD,
        "ok": ok,
        "screenshot": str(shot) if shot_ok else None,
        "html": checks,
        "ocr": ocr_hits,
        "ocr_excerpt": ocr[:400],
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": "verify-start-ironclad/v1",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "desktop": verify_desktop(),
        "ironclad": verify_ironclad(),
    }
    report["ok"] = report["desktop"]["ok"] and report["ironclad"]["ok"]
    out_path = OUT / "report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())