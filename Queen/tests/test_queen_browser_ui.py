#!/usr/bin/env pythong
"""Queen Browser UI E2E — Playwright headless standard browser flows."""
from __future__ import annotations

import os
import sys
import time

HOST = os.environ.get("QUEEN_WORLD_HOST", "127.0.0.1")
PORT = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
URL = f"http://{HOST}:{PORT}/world/browser.html"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("SKIP: playwright not installed")
        return 0

    results: list[tuple[str, str]] = []

    def check(cond: bool, msg: str) -> None:
        results.append(("PASS" if cond else "FAIL", msg))
        if not cond:
            raise AssertionError(msg)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=30000)

        # Boot overlay clears
        page.wait_for_selector(".qb-tabs .qb-tab", timeout=15000)

        check(page.locator(".qb-chrome").is_visible(), "browser chrome visible")
        check(page.locator("#qb-url").is_visible(), "address bar visible")
        check(page.locator("#qb-frame").is_visible(), "content frame visible")

        # Tabs render from API
        page.wait_for_function("document.querySelectorAll('.qb-tab').length >= 1", timeout=10000)
        check(page.locator(".qb-tab").count() >= 1, "tab bar populated")

        # Gate pill shows QUEEN_READY
        pill = page.locator("#qb-gate-pill")
        page.wait_for_function(
            "document.getElementById('qb-gate-pill')?.textContent?.includes('QUEEN_READY')",
            timeout=15000,
        )
        check("QUEEN_READY" in (pill.text_content() or ""), "gate pill QUEEN_READY")

        # Bookmarks render
        page.wait_for_selector(".qb-bookmark", timeout=10000)
        check(page.locator(".qb-bookmark").count() >= 3, "bookmarks rendered")

        # Navigate via address bar
        page.fill("#qb-url", "https://example.com")
        page.click("#qb-go")
        page.wait_for_function(
            "() => document.getElementById('qb-frame')?.src?.includes('example.com')",
            timeout=15000,
        )
        frame_src = page.locator("#qb-frame").get_attribute("src") or ""
        check("example.com" in frame_src, "navigate loads example.com in frame")

        # Back
        page.click("#qb-back")
        page.wait_for_function(
            "() => { const s = document.getElementById('qb-frame')?.src || ''; return s.includes('kilroy-home') || s.includes('queen-field-home') || s.includes('Field_Primer') || s.includes('zacharygeurts'); }",
            timeout=15000,
        )
        back_src = page.locator("#qb-frame").get_attribute("src") or ""
        check(
            "kilroy-home" in back_src or "queen-field-home" in back_src or "Field_Primer" in back_src or "zacharygeurts" in back_src,
            "back returns home",
        )

        # Forward
        page.click("#qb-forward")
        page.wait_for_function(
            "() => document.getElementById('qb-frame')?.src?.includes('example.com')",
            timeout=15000,
        )
        check("example.com" in (page.locator("#qb-frame").get_attribute("src") or ""), "forward works")

        # New tab
        tabs_before = page.locator(".qb-tab").count()
        page.click("#qb-new-tab")
        page.wait_for_function(
            f"document.querySelectorAll('.qb-tab').length > {tabs_before}",
            timeout=10000,
        )
        check(page.locator(".qb-tab").count() > tabs_before, "new tab adds tab button")

        # Home
        page.click("#qb-home")
        page.wait_for_function(
            "() => { const s = document.getElementById('qb-frame')?.src || ''; return s.includes('kilroy-home') || s.includes('queen-field-home') || s.includes('Field_Primer') || s.includes('zacharygeurts'); }",
            timeout=15000,
        )
        check(
            "kilroy-home" in (page.locator("#qb-frame").get_attribute("src") or "")
            or "Field_Primer" in (page.locator("#qb-url").input_value() or "")
            or "zacharygeurts" in (page.locator("#qb-frame").get_attribute("src") or ""),
            "home button",
        )

        # Bookmark click
        page.locator(".qb-bookmark", has_text="Field Primer").click()
        page.wait_for_function(
            "() => { const s = document.getElementById('qb-frame')?.src || ''; return s.includes('kilroy-home') || s.includes('queen-field-home') || s.includes('Field_Primer') || s.includes('zacharygeurts'); }",
            timeout=15000,
        )
        check(True, "bookmark navigation")

        # Proxy toggle + proxy load
        page.click("#qb-proxy")
        check(page.locator("#qb-proxy").evaluate("el => el.classList.contains('active')"), "proxy toggle active")
        page.fill("#qb-url", "https://example.com")
        page.click("#qb-go")
        page.wait_for_function(
            "() => document.getElementById('qb-frame')?.src?.includes('/browse/view')",
            timeout=15000,
        )
        check("/browse/view" in (page.locator("#qb-frame").get_attribute("src") or ""), "proxy frame URL")

        # Gate drawer
        page.click("#qb-gates")
        check(page.locator("#qb-gate-drawer").evaluate("el => el.classList.contains('open')"), "gate drawer opens")

        # OS dock — switch to World panel
        page.locator(".qw-dock-btn", has_text="World").click()
        check(page.locator(".qw-os-panel[data-pane='overview']").is_visible(), "OS World panel opens")
        check(page.locator(".qb-viewport").evaluate("el => el.hidden"), "browser viewport hidden in OS mode")

        # Back to Web
        page.locator(".qw-dock-btn", has_text="Web").click()
        check(page.locator(".qb-viewport").is_visible(), "return to browser view")

        browser.close()

    passed = sum(1 for s, _ in results if s == "PASS")
    failed = sum(1 for s, _ in results if s == "FAIL")
    for status, msg in results:
        print(f"  [{status}] {msg}")
    print(f"\nQueen Browser UI tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())