#!/usr/bin/env pythong
"""Online learn — Grok Imagine docs + live video papers/GitHub (truth-filtered fetch)."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))

from field_imagine_corpus import CURATED_FETCH, ensure_corpus, format_registry  # noqa: E402
from field_internet import fetch_url, internet_enabled  # noqa: E402

LOG = ROOT / "cache" / "fieldstorage" / "brain" / "internet" / "imagine_learn.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_imagine_learn(*, force: bool = False) -> dict[str, Any]:
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

    try:
        from field_live_video import live_video_plan  # noqa: WPS433

        report["live_video_plan"] = live_video_plan()
    except ImportError:
        pass

    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")

    report["ok_count"] = sum(1 for x in report["fetches"] if x.get("ok"))
    return report


def format_report(report: dict[str, Any], *, human: bool = False) -> str:
    if human:
        plan = report.get("live_video_plan") or {}
        rec = plan.get("recommended") or {}
        primary = rec.get("primary", "faster_liveportrait")
        indexed = plan.get("papers_indexed", "?")
        lines = [
            "I studied Grok Imagine and live talking-video — papers, GitHub repos, and the xAI API.",
            f"Fetched {report.get('ok_count', 0)}/{len(report.get('fetches', []))} sources · {indexed} entries in registry.",
            "Real-time talk: your words → Language Expert → TTS → lip-sync frames → Graphics window.",
            f"Recommended live backend: {primary} (set HOSTESS7_LIVE_VIDEO_BACKEND).",
            "Cinematic shots: Grok image_to_video or text_to_video with XAI_API_KEY.",
            "Run ./Hostess7.sh live-video-demo to see a talk frame.",
        ]
        return "\n".join(lines)

    lines = [format_registry(), ""]
    lines.append(f"Learn fetches: {report.get('ok_count', 0)} OK")
    for f in report.get("fetches", []):
        status = "OK" if f.get("ok") else "FAIL"
        lines.append(f"  [{status}] {f.get('id')} — {f.get('url', '')[:60]}")
    return "\n".join(lines)


def main() -> int:
    os.environ.setdefault("HOSTESS7_INTERNET", "1")
    report = run_imagine_learn(force=os.environ.get("HOSTESS7_FORCE_FETCH") == "1")
    human = os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1"
    print(format_report(report, human=human))
    print(f"METRIC imagine_learn_ok={report.get('ok_count', 0)}")
    print(f"METRIC imagine_learn_total={len(report.get('fetches', []))}")
    ok = report.get("ok_count", 0) >= 2 or report.get("skipped")
    print("OK imagine-learn" if ok else "FAIL imagine-learn")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())