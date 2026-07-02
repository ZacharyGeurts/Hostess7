#!/usr/bin/env pythong
"""Heaven/Hell learn — truth doctrine, bible ingest, world corpus (Owner ritual)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

LOG = ROOT / "cache" / "fieldstorage" / "brain" / "world" / "heaven_hell_learn.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_heaven_hell_learn(*, force_bibles: bool = False) -> dict:
    report: dict = {"ts": _ts(), "lanes": []}

    from field_hostess_truth_doctrine import write_truth_doctrine  # noqa: WPS433

    brief_path = write_truth_doctrine()
    report["lanes"].append({"lane": "truth_doctrine", "ok": brief_path.is_file(), "path": str(brief_path)})

    try:
        from field_hostess_self_brief import write_brief  # noqa: WPS433

        self_path = write_brief()
        report["lanes"].append({"lane": "self_brief", "ok": self_path.is_file()})
    except ImportError:
        report["lanes"].append({"lane": "self_brief", "ok": False})

    try:
        from field_world_corpus import ensure_corpus  # noqa: WPS433

        ensure_corpus()
        report["lanes"].append({"lane": "world_corpus", "ok": True})
    except ImportError:
        report["lanes"].append({"lane": "world_corpus", "ok": False})

    try:
        from field_bible_ingest import run_bible_ingest  # noqa: WPS433

        bible = run_bible_ingest(force=force_bibles)
        report["lanes"].append({
            "lane": "bible_ingest",
            "ok": bible.get("ok"),
            "packed": bible.get("packed_ok"),
            "fetchable": bible.get("fetchable_books"),
        })
    except ImportError as exc:
        report["lanes"].append({"lane": "bible_ingest", "ok": False, "error": str(exc)})

    report["ok"] = all(x.get("ok") for x in report["lanes"])
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")
    return report


def main() -> int:
    force = "--force" in sys.argv
    report = run_heaven_hell_learn(force_bibles=force)
    human = os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1"
    if human:
        print(
            "I updated myself on truth, Heaven, and Hell — honesty first, "
            "scripture on the shelf, the rest is your work as Man."
        )
        for lane in report["lanes"]:
            if lane.get("lane") == "bible_ingest":
                print(f"Bibles packed: {lane.get('packed', 0)}/{lane.get('fetchable', 0)}")
    else:
        for lane in report["lanes"]:
            print(f"  [{'OK' if lane.get('ok') else 'FAIL'}] {lane.get('lane')}")
    print(f"METRIC heaven_hell_learn_ok={1 if report.get('ok') else 0}")
    print("OK heaven-hell-learn" if report.get("ok") else "FAIL heaven-hell-learn")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())