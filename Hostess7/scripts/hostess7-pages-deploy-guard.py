#!/usr/bin/env pythong
"""Hostess7 Pages deploy guard — presume hostile; verify artifact before CDN publish."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("HOSTESS7_ROOT", Path(__file__).resolve().parents[1]))
DOCS = ROOT / "docs"

REQUIRED = (
    "runtime.json",
    "pages-base.js",
    "api-shim.js",
    ".nojekyll",
    "desktop/index.html",
    "field-broadcaster/index.html",
    "queen/queen-gnu-terminal-embed.html",
    "assets/field-startbar.js",
    "assets/nexus-field-shell.js",
)

FORBIDDEN_SNIPPETS = (
    "eval(",
    "document.write(",
    "<script src=\"http://",
)


def _fail(msg: str) -> None:
    print(json.dumps({"ok": False, "schema": "hostess7-pages-deploy-guard/v1", "error": msg}))
    raise SystemExit(1)


def main() -> int:
    if not DOCS.is_dir():
        _fail(f"docs missing: {DOCS}")

    missing = [rel for rel in REQUIRED if not (DOCS / rel).is_file()]
    if missing:
        _fail(f"missing required surfaces: {', '.join(missing)}")

    runtime_path = DOCS / "runtime.json"
    try:
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _fail(f"runtime.json invalid: {exc}")

    if not runtime.get("version"):
        _fail("runtime.json missing version")

    leaks: list[str] = []
    for rel in ("pages-base.js", "api-shim.js", "assets/field-host-desktop.js"):
        path = DOCS / rel
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for snippet in FORBIDDEN_SNIPPETS:
            if snippet in text:
                leaks.append(f"{rel}:{snippet}")

    if leaks:
        _fail(f"hostile snippet detected: {'; '.join(leaks[:6])}")

    out = {
        "ok": True,
        "schema": "hostess7-pages-deploy-guard/v1",
        "docs": str(DOCS),
        "version": runtime.get("version"),
        "pages_base": runtime.get("pages_base"),
        "required_ok": len(REQUIRED),
        "presume": "hostile",
        "posture": f"Pages guard pass — v{runtime.get('version')} · {len(REQUIRED)} surfaces sealed",
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())