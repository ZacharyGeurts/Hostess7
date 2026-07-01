#!/usr/bin/env pythong
"""Hostess7 license posture — Demo now; dual GPL v3 or 3% commercial."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "cache" / "fieldstorage" / "brain" / "legal" / "hostess7_license.json"

# Current shipping posture
LICENSE_MODE = "demo"  # demo | production
COMMERCIAL_TERMS = "3% profit share"
CONTACT = "gzac5314@gmail.com"

LICENSE_STATUS: dict[str, Any] = {
    "project": "Hostess7",
    "owner": "Zachary Robert Geurts",
    "mode": LICENSE_MODE,
    "mode_label": "Demo",
    "dual_license": True,
    "options": [
        {"id": "gpl3", "name": "GNU General Public License v3.0 (or later)", "url": "https://www.gnu.org/licenses/gpl-3.0.html"},
        {"id": "commercial_3pct", "name": "Commercial — 3% profit share", "contact": CONTACT,
         "terms": "3% of what we can save or make you."},
    ],
    "likely_commercial": "commercial_3pct",
    "notice": (
        "Hostess7 is currently offered as a Demo. Production/commercial use will likely use "
        "the 3% profit-share license (or GPL v3 at your choice). Contact Owner for terms."
    ),
    "demo_limits": (
        "Demo: evaluation, GitHub Pages/Codespaces, talk window — not a production SLA. "
        "Full commercial terms via gzac5314@gmail.com."
    ),
}


def license_mode() -> str:
    return os.environ.get("HOSTESS7_LICENSE_MODE", LICENSE_MODE)


def is_demo() -> bool:
    return license_mode().lower() in ("demo", "demonstration", "evaluation")


def ensure_status() -> Path:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = dict(LICENSE_STATUS)
    doc["mode"] = license_mode()
    doc["mode_label"] = "Demo" if is_demo() else doc.get("mode_label", "Demo")
    STATUS_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return STATUS_PATH


def format_notice(*, short: bool = False) -> str:
    ensure_status()
    if short:
        return f"Demo · dual license: GPL v3 or 3% profit share · {CONTACT}"
    return LICENSE_STATUS["notice"]


def format_web_banner() -> str:
    return (
        "Demo — Hostess7 is in demonstration mode. "
        "Likely production license: 3% profit share (or GPL v3). "
        f"Contact {CONTACT}."
    )


def main() -> int:
    ensure_status()
    print(format_notice())
    print(format_notice(short=True))
    print(f"METRIC license_mode={license_mode()}")
    print("OK license-status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())