#!/usr/bin/env pythong
"""QA: Hostess7 internet gate + fetch."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_internet import fetch_url, internet_enabled, truth_score_text  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    if truth_score_text("substantive legal medical code evidence") < 6:
        return fail("truth_score too low")

    for key in (
        "HOSTESS7_INTERNET",
        "NEXUS_HOSTESS7_INTERNET",
        "HOSTESS7_ANGEL_MANDATE",
        "NEXUS_HOSTESS7_AUTONOMOUS",
    ):
        os.environ.pop(key, None)
    os.environ["NEXUS_HOSTESS7_INTERNET"] = "0"
    blocked = fetch_url("https://example.com/")
    if blocked.get("ok"):
        return fail("fetch should fail when gate closed")
    if "CLOSED" not in (blocked.get("error") or ""):
        return fail("expected gate closed message")

    os.environ["HOSTESS7_INTERNET"] = "1"
    if not internet_enabled():
        return fail("internet_enabled should be true")

    rec = fetch_url("https://example.com/")
    if not rec.get("ok"):
        return fail(f"fetch failed: {rec.get('error')}")

    cached = fetch_url("https://example.com/")
    if not cached.get("cached"):
        return fail("second fetch should be cached")

    print(f"OK internet fetch bytes={rec['bytes']} truth={rec['truth_score']}")
    print("METRIC qa_field_internet=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())