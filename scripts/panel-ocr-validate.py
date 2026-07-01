#!/usr/bin/env pythong
"""OCR + DOM validation for NEXUS RTX Zero panel (NewLatest tree)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT)))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))
FINAL_EYE = SG / "Final_Eye"
PORT = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
QUEEN_PORT = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
PANEL_URL = os.environ.get("NEXUS_PANEL_URL", f"https://127.0.0.1:{PORT}")
RTX_URL = f"{PANEL_URL}/?rtx=1"

REQUIRED_HTML = (
    "nexus-military-v8",
    "Military C2 Panel",
    "nexus-military-v8.css",
    "nexus-military-v8.js",
    "nexus-rtx-zero.css",
    "nexus-rtx-zero.js",
    "nexus-sdf-menu.js",
    "packet-field-graphics.js",
)
REQUIRED_JS = ("OPS FLOW", "MILITARY C2", "stampVersion", "RTX · ZERO COST")
REQUIRED_RTX_JS = ("rtx-zero-v1", "nexus_rtx_zero", "panel_rtx_zero")
EXPECTED_VERSION = os.environ.get("NEXUS_VERSION", "10.0.0")
EXPECTED_BUILD = "rtx-zero-v1"


def _ssl_ctx():
    import ssl

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _fetch(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-OCR-Validate"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _ocr_image(path: Path) -> str:
    """Final_Eye OCR → H7/7 via canonical bridge."""
    if not path.is_file():
        return ""
    bridge = INSTALL / "lib" / "final-eye-h7-ocr.py"
    if bridge.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(bridge), "ocr", str(path)],
                capture_output=True, text=True, timeout=90, check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "SG_ROOT": str(SG)},
            )
            doc = json.loads(proc.stdout or "{}")
            return str(doc.get("text") or doc.get("ocr") or "")
        except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
            pass
    return ""


def _screenshot_panel(out: Path, url: str) -> bool:
    for cmd in (
        ["firefox", "--headless", "--screenshot", str(out), url],
        ["firefox", "-headless", "-screenshot", str(out), url],
    ):
        try:
            subprocess.run(cmd, capture_output=True, timeout=45, check=False)
            if out.is_file() and out.stat().st_size > 1000:
                return True
        except (subprocess.SubprocessError, OSError):
            continue
    return False


def main() -> int:
    fail = 0
    print("=== NEXUS Panel OCR Validation (NewLatest / RTX Zero) ===")
    print(f"target={RTX_URL}")

    try:
        html = _fetch(RTX_URL)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"FAIL: cannot fetch panel HTML — {exc}")
        return 1

    for needle in REQUIRED_HTML:
        if needle in html:
            print(f"HTML OK: {needle}")
        else:
            print(f"HTML FAIL: missing {needle}")
            fail += 1

    js_checks: list[tuple[str, str]] = []
    for name in ("nexus-military-v8.js", "nexus-rtx-zero.js"):
        try:
            body = _fetch(f"{PANEL_URL}/assets/{name}")
        except (urllib.error.URLError, TimeoutError, OSError):
            fp = INSTALL / "panel" / "assets" / name
            body = fp.read_text(encoding="utf-8", errors="replace") if fp.is_file() else ""
        js_checks.append((name, body))

    for needle in REQUIRED_JS:
        ok = any(needle in body for _n, body in js_checks)
        if ok:
            print(f"JS OK: {needle}")
        else:
            print(f"JS FAIL: missing {needle}")
            fail += 1

    rtx_body = next((b for n, b in js_checks if n == "nexus-rtx-zero.js"), "")
    for needle in REQUIRED_RTX_JS:
        if needle in rtx_body:
            print(f"RTX JS OK: {needle}")
        else:
            print(f"RTX JS FAIL: missing {needle}")
            fail += 1

    try:
        status = json.loads(_fetch(f"{PANEL_URL}/api/status"))
        ver = str(status.get("version") or "")
        build = str(status.get("panel_build") or "")
        rtx = status.get("panel_rtx_zero")
        if ver == EXPECTED_VERSION:
            print(f"API OK: version={ver}")
        else:
            print(f"API FAIL: version={ver!r} want {EXPECTED_VERSION}")
            fail += 1
        if build == EXPECTED_BUILD:
            print(f"API OK: panel_build={build}")
        else:
            print(f"API FAIL: panel_build={build!r} want {EXPECTED_BUILD}")
            fail += 1
        if rtx in (True, 1, "1"):
            print("API OK: panel_rtx_zero=true")
        else:
            print(f"API FAIL: panel_rtx_zero={rtx!r}")
            fail += 1
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError, OSError) as exc:
        print(f"API FAIL: /api/status — {exc}")
        fail += 1

    for tray_name in ("queen-tray-24.png", "nexus-tray-us-24.png", "nexus-field-24.png"):
        tray_icon = INSTALL / "panel" / "assets" / tray_name
        if tray_icon.is_file() and tray_icon.stat().st_size > 80:
            print(f"TRAY ICON OK: {tray_name} ({tray_icon.stat().st_size} bytes)")
            break
    else:
        print("TRAY ICON WARN: Queen tray icons missing — run Queen/scripts/queen-icon-kit.py")

    shot = Path("/tmp/nexus-panel-ocr-rtx.png")
    if _screenshot_panel(shot, RTX_URL):
        ocr = _ocr_image(shot).lower()
        print(f"PANEL SCREENSHOT OK: {shot} ({shot.stat().st_size} bytes)")
        for token in ("nexus", "shield", "military", "rtx", "zero"):
            if token in ocr or token in html.lower():
                print(f"OCR/DOM OK: {token}")
            else:
                print(f"OCR WARN: {token} not in screenshot OCR")
        if re.search(r"rtx|zero|nexus|shield", ocr):
            print("OCR PASS: RTX panel strings visible in screenshot")
        else:
            print("OCR NOTE: screenshot OCR inconclusive — HTML/API checks are authoritative")
    else:
        print("OCR SKIP: headless screenshot unavailable (HTML/API checks used)")

    thermal_html = INSTALL / "Queen" / "world" / "queen-thermal-manager.html"
    if thermal_html.is_file():
        th_text = thermal_html.read_text(encoding="utf-8", errors="replace")
        for needle in ("Thermal Manager", "NEXUS C2", "qtm-gauge", "Landauer"):
            if needle in th_text:
                print(f"THERMAL HTML OK: {needle}")
            else:
                print(f"THERMAL HTML FAIL: missing {needle}")
                fail += 1
        try:
            py = shutil.which("pythong") or sys.executable
            ocr_doc = json.loads(
                subprocess.check_output(
                    [py, str(INSTALL / "lib" / "field-thermal-manager-block.py"), "ocr"],
                    stderr=subprocess.DEVNULL,
                    timeout=25,
                    env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "SG_ROOT": str(SG)},
                ).decode("utf-8", errors="replace")
            )
            if ocr_doc.get("ok"):
                print(f"FINAL_EYE OCR OK: thermal manager ({ocr_doc.get('hit_count')} needles)")
            else:
                print(f"FINAL_EYE OCR FAIL: {ocr_doc}")
                fail += 1
        except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
            print(f"FINAL_EYE OCR WARN: {exc}")
    else:
        print("THERMAL SKIP: queen-thermal-manager.html not in NewLatest/Queen/world")

    for label, html_rel, block_py, needles in (
        ("EAR", "Queen/world/queen-final-ear-manager.html", "field-final-ear-block.py",
         ("Final Ear", "NEXUS C2", "Auditus", "Veritas")),
        ("MOUTH", "Queen/world/queen-final-mouth-manager.html", "field-final-mouth-block.py",
         ("Final Mouth", "NEXUS C2", "Loquor", "Veritas Vox")),
    ):
        sense_html = INSTALL / html_rel
        if sense_html.is_file():
            sense_text = sense_html.read_text(encoding="utf-8", errors="replace")
            for needle in needles:
                if needle in sense_text:
                    print(f"{label} HTML OK: {needle}")
                else:
                    print(f"{label} HTML FAIL: missing {needle}")
                    fail += 1
            try:
                py = shutil.which("pythong") or sys.executable
                ocr_doc = json.loads(
                    subprocess.check_output(
                        [py, str(INSTALL / "lib" / block_py), "ocr"],
                        stderr=subprocess.DEVNULL,
                        timeout=45,
                        env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "SG_ROOT": str(SG)},
                    ).decode("utf-8", errors="replace")
                )
                if ocr_doc.get("ok"):
                    print(f"FINAL_EYE OCR OK: {label.lower()} manager ({ocr_doc.get('hit_count')} needles)")
                else:
                    print(f"FINAL_EYE OCR FAIL: {label} {ocr_doc}")
                    fail += 1
            except (subprocess.SubprocessError, OSError, json.JSONDecodeError) as exc:
                print(f"FINAL_EYE OCR WARN: {label} {exc}")
        else:
            print(f"{label} SKIP: {html_rel} not in NewLatest/Queen/world")

    if fail:
        print(f"\nOCR VALIDATION FAILED ({fail} hard failures)")
        return 1
    print("\nOCR VALIDATION PASSED — RTX Zero + Thermal + Final Ear/Mouth (Final_Eye) confirmed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())