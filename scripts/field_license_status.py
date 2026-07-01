#!/usr/bin/env pythong
"""Hostess7 license posture — war-ready operational; dual GPL v3 or 3% commercial."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / "cache" / "fieldstorage" / "brain" / "legal" / "hostess7_license.json"

LICENSE_MODE = "war"
COMMERCIAL_TERMS = "3% profit share"
CONTACT = "gzac5314@gmail.com"

LICENSE_STATUS: dict[str, Any] = {
    "project": "Hostess7",
    "owner": "Zachary Robert Geurts",
    "mode": LICENSE_MODE,
    "mode_label": "War-ready",
    "posture": "operational",
    "dual_license": True,
    "options": [
        {"id": "gpl3", "name": "GNU General Public License v3.0 (or later)", "url": "https://www.gnu.org/licenses/gpl-3.0.html"},
        {"id": "commercial_3pct", "name": "Commercial — 3% profit share", "contact": CONTACT,
         "terms": "3% of what we can save or make you."},
    ],
    "likely_commercial": "commercial_3pct",
    "notice": (
        "Hostess7 is war-ready — full field brain, KILROY doctrine, alert posture. "
        "Never demo. Dual license: GPL v3 or 3% profit share — contact Owner for commercial terms."
    ),
    "operational_limits": (
        "Public Pages mirror withholds loopback intel; full truth and stack on 127.0.0.1 only. "
        "Commercial terms via gzac5314@gmail.com."
    ),
}


def license_mode() -> str:
    raw = os.environ.get("HOSTESS7_LICENSE_MODE", LICENSE_MODE).strip().lower()
    if raw in ("demo", "demonstration", "evaluation"):
        return LICENSE_MODE
    return raw or LICENSE_MODE


def is_demo() -> bool:
    return False


def is_war_ready() -> bool:
    return True


def ensure_status() -> Path:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc = dict(LICENSE_STATUS)
    doc["mode"] = license_mode()
    doc["mode_label"] = "War-ready"
    doc["posture"] = "operational"
    doc["demo"] = False
    STATUS_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return STATUS_PATH


def format_notice(*, short: bool = False) -> str:
    ensure_status()
    if short:
        return f"War-ready · dual license: GPL v3 or 3% profit share · {CONTACT}"
    return LICENSE_STATUS["notice"]


def format_web_banner() -> str:
    return (
        "War-ready — Hostess7 is operational. KILROY field stack · full brain · alert posture. "
        f"Dual license: GPL v3 or 3% profit share · {CONTACT}."
    )


def main() -> int:
    ensure_status()
    print(format_notice())
    print(format_notice(short=True))
    print(f"METRIC license_mode={license_mode()}")
    print("METRIC war_ready=1")
    print("OK license-status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())