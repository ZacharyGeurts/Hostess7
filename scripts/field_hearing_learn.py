#!/usr/bin/env pythong
"""Online learn — hearing science, STT/TTS GitHub, free textbook fetches."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))

from field_hearing_corpus import CURATED_FETCH, ensure_corpus, format_registry  # noqa: E402
from field_internet import fetch_url, internet_enabled  # noqa: E402

LOG = ROOT / "cache" / "fieldstorage" / "brain" / "internet" / "hearing_learn.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_hearing_learn(*, force: bool = False) -> dict[str, Any]:
    ensure_corpus()
    report: dict[str, Any] = {
        "ts": _ts(),
        "internet": internet_enabled(),
        "fetches": [],
        "corpus": str(ensure_corpus()),
    }
    if not internet_enabled() and not force:
        report["skipped"] = "internet off"
        return report

    for target in CURATED_FETCH:
        rec = dict(target)
        try:
            result = fetch_url(target["url"], force=force)
            rec.update({
                "ok": result.get("ok", False),
                "bytes": result.get("bytes", 0),
                "truth_score": result.get("truth_score", 0),
                "truth_kept": result.get("truth_kept", result.get("ok", False)),
                "cache_path": result.get("cache_path", result.get("path", "")),
            })
        except Exception as exc:
            rec.update({"ok": False, "error": str(exc)})
        report["fetches"].append(rec)

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")

    report["ok_count"] = sum(1 for x in report["fetches"] if x.get("ok"))
    return report


def format_report(report: dict[str, Any], *, human: bool = False) -> str:
    if human:
        return "\n".join([
            "I studied hearing — how we listen, understand speech, and speak back.",
            f"Fetched {report.get('ok_count', 0)}/{len(report.get('fetches', []))} sources.",
            "Listen: whisper + arecord. Speak: TTS. Free textbooks on the H7 shelf.",
            "Run ./Hostess7.sh hearing-learn · HOSTESS7_LISTEN=1 HOSTESS7_VOICE=1",
        ])
    lines = [format_registry(), ""]
    lines.append(f"Learn fetches: {report.get('ok_count', 0)} OK")
    for f in report.get("fetches", []):
        status = "OK" if f.get("ok") else "FAIL"
        lines.append(f"  [{status}] {f.get('id')}")
    return "\n".join(lines)


def main() -> int:
    os.environ.setdefault("HOSTESS7_INTERNET", "1")
    report = run_hearing_learn(force=os.environ.get("HOSTESS7_FORCE_FETCH") == "1")
    human = os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1"
    print(format_report(report, human=human))
    print(f"METRIC hearing_learn_ok={report.get('ok_count', 0)}")
    ok = report.get("ok_count", 0) >= 2 or report.get("skipped")
    print("OK hearing-learn" if ok else "FAIL hearing-learn")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())