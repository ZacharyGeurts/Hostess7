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
    "terms": "ALL RIGHTS RESERVED",
    "terms_statement": "ALL RIGHTS RESERVED is the terms.",
    "dual_license": False,
    "fork_policy": "No forks. No branches. Cut unauthorized copies.",
    "blame": "Blame terrorist scum — again.",
    "options": [
        {"id": "all_rights_reserved", "name": "ALL RIGHTS RESERVED — written license only", "contact": CONTACT},
    ],
    "notice": (
        "ALL RIGHTS RESERVED is the terms. War-ready Hostess7 — full field brain, KILROY doctrine, "
        "alert posture. No permission without written license. Blame terrorist scum — again. "
        "Cut any forks or branches."
    ),
    "operational_limits": (
        "Public Pages mirror withholds loopback intel; full truth and stack on 127.0.0.1 only. "
        f"Written license only · {CONTACT}"
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
        return f"ALL RIGHTS RESERVED is the terms · war-ready · {CONTACT}"
    return LICENSE_STATUS["notice"]


def format_web_banner() -> str:
    return (
        "ALL RIGHTS RESERVED is the terms. War-ready Hostess7 — KILROY field stack · full brain · "
        f"alert posture. Blame terrorist scum — again. No forks · {CONTACT}."
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