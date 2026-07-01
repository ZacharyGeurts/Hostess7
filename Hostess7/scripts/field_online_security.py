#!/usr/bin/env pythong
"""GitHub Pages / online security checklist for Hostess7."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CHECKLIST = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "online_security.json"

POLICY = {
    "pages_url": "https://zacharygeurts.github.io/Hostess7",
    "rules": [
        "HTTPS only — GitHub Pages enforces TLS; no http:// embeds",
        "Demo mode on Pages — brain API optional; fallback replies offline-safe",
        "Sanitize user chat input — strip script tags, max length 2000 chars",
        "No secrets in docs/ or committed JSON — use Codespaces secrets",
        "Content-Security-Policy meta in index.html",
        "X-Frame-Options DENY on any local API server",
        "Truth-filter all fetches: ./Hostess7.sh fetch <url>",
        "Full control (NEXUS, sudo, TEAM mount) — local/Codespaces only",
        "Field 1 sync fieldstorage — lossless, verify before git push",
    ],
    "hostess7_commands": (
        "./Hostess7.sh internet",
        "./Hostess7.sh fetch <url>",
        "./Hostess7.sh nexus status",
        "./Hostess7.sh sg-hub",
    ),
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def audit_docs() -> dict[str, bool]:
    index = DOCS / "index.html"
    app = DOCS / "app.js"
    checks = {
        "index_exists": index.is_file(),
        "app_exists": app.is_file(),
        "csp_meta": False,
        "sanitize_fn": False,
    }
    if index.is_file():
        text = index.read_text(encoding="utf-8", errors="replace")
        checks["csp_meta"] = "Content-Security-Policy" in text
    if app.is_file():
        text = app.read_text(encoding="utf-8", errors="replace")
        checks["sanitize_fn"] = "sanitize" in text
    return checks


def run_checklist() -> int:
    checks = audit_docs()
    doc = {"updated": _ts(), **POLICY, "audit": checks}
    CHECKLIST.parent.mkdir(parents=True, exist_ok=True)
    CHECKLIST.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    print("Hostess 7 — online security (GitHub Pages)")
    print("=" * 40)
    print(f"Pages: {POLICY['pages_url']}")
    for rule in POLICY["rules"]:
        print(f"  · {rule}")
    print("\nDocs audit:")
    for k, v in checks.items():
        print(f"  {'OK' if v else 'FIX'} {k}")
    print(f"\nSaved: {CHECKLIST}")
    print("METRIC online_security=1")
    ok = all(checks.values())
    print("OK online-security" if ok else "WARN online-security (see FIX items)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(run_checklist())