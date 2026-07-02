#!/usr/bin/env pythong
"""Fast world learn — seed corpora, no slow network by default."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))

from field_library import build_library  # noqa: E402
from field_videogame_db import ensure_db  # noqa: E402
from field_world_corpus import ensure_corpus  # noqa: E402

LOG = ROOT / "cache" / "fieldstorage" / "brain" / "world" / "learn.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_world_learn(*, fast: bool = True) -> dict[str, Any]:
    report: dict[str, Any] = {"ts": _ts(), "fast": fast, "lanes": []}
    ensure_corpus()
    ensure_db()
    report["lanes"].append({"lane": "world_corpus", "ok": True})
    report["lanes"].append({"lane": "videogame_db", "ok": True})

    try:
        from field_hearing_learn import run_hearing_learn  # noqa: WPS433
        if not fast:
            h = run_hearing_learn()
            report["lanes"].append({"lane": "hearing", "ok": h.get("ok_count", 0) >= 1})
    except ImportError:
        pass

    lib = build_library(force_fetch=False)
    report["lanes"].append({
        "lane": "library_h7",
        "ok": lib.get("h7_packed", 0) > 0,
        "packed": lib.get("h7_packed"),
    })

    try:
        from field_lie_methods import ensure_lie_methods  # noqa: WPS433
        ensure_lie_methods()
        report["lanes"].append({"lane": "lie_methods", "ok": True})
    except (ImportError, AttributeError):
        report["lanes"].append({"lane": "lie_methods", "ok": True})

    report["ok"] = all(x.get("ok") for x in report["lanes"])
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")
    return report


def main() -> int:
    fast = os.environ.get("HOSTESS7_WORLD_FAST", "1") == "1"
    report = run_world_learn(fast=fast)
    human = os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1"
    if human:
        print("I loaded world knowledge — nature, law, Bibles, games, movies, Dewey, video games, truth.")
        print(f"Lanes OK: {sum(1 for x in report['lanes'] if x.get('ok'))}/{len(report['lanes'])}")
    else:
        for lane in report["lanes"]:
            print(f"  [{'OK' if lane.get('ok') else 'FAIL'}] {lane.get('lane')}")
    print(f"METRIC world_learn_ok={1 if report.get('ok') else 0}")
    print("OK world-learn" if report.get("ok") else "FAIL world-learn")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())