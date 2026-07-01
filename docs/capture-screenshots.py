#!/usr/bin/env pythong
"""Capture NEXUS panel screenshots for README/wiki (localhost HTTPS)."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
URL = os.environ.get("NEXUS_PANEL_URL", "https://127.0.0.1:9477/")
VIEWS = [
    ("panel-monitor.png", "monitor"),
    ("panel-settings.png", "settings"),
    ("panel-logs.png", "logs"),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", "playwright"])
        subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
        from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )
        page = ctx.new_page()
        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(2000)
        for filename, view in VIEWS:
            page.click(f'nav.menu button[data-view="{view}"]')
            if view == "monitor":
                page.wait_for_selector(".axis-grid-prominent", timeout=15000)
            page.wait_for_timeout(1500 if view != "logs" else 2500)
            page.screenshot(path=str(OUT / filename), full_page=False)
            print(f"wrote {OUT / filename}")
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())