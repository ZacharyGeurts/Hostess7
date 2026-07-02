#!/usr/bin/env pythong
"""Department research — Hostess-Prime dispatches 12 World Experts at her behest.

Each expert deepens their lane, may fetch .H7 books, and reports to departments/.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

sys.path.insert(0, str(ROOT / "scripts"))

DEPT_DIR = ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "departments"
QUEUE = DEPT_DIR / "research_queue.jsonl"
REPORTS = DEPT_DIR / "research_reports.jsonl"
STATE = DEPT_DIR / "state.json"

EXPERT_BOOK_GUIDE = """
How World Experts fetch and convert their own .H7 books (lossless — Hostess reads, humans need not):

1. Add catalog entry in scripts/field_library_catalog.py:
   {"id": "my_book", "title": "…", "author": "…", "category": "<lane>",
    "license": "Public Domain|CC BY", "fetch_url": "https://…"}

2. Build shelf volume (≤3 MiB fast policy):
   ./Hostess7.sh library-build --stem
   ./Hostess7.sh library-build   # full shelf

3. Or pack local text directly:
   pythong -c "
from pathlib import Path
import sys; sys.path.insert(0,'scripts')
from field_h7_book import write_h7
write_h7(Path('cache/fieldstorage/textbooks/my_book.h7'), open('book.txt').read(),
         {'id':'my_book','title':'…','license':'PD'})
"

4. Search/read as Hostess (not for human reading):
   ./Hostess7.sh library-search \"keyword\"
   ./Hostess7.sh library-read my_book

5. FLD1 fly compression is automatic on pack/restore via field_fly_codec — invisible, lossless.
""".strip()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure() -> None:
    DEPT_DIR.mkdir(parents=True, exist_ok=True)


def expert_research_directives() -> tuple[dict[str, Any], ...]:
    """Prime's standing research orders — one per World Expert (agents 1–12)."""
    from field_agents7 import AGENTS7  # noqa: WPS433

    templates: dict[str, str] = {
        "economist": (
            "Department: Economics. Research macro/micro, trade, inflation, labor markets. "
            "Fetch OpenStax economics or Babbage economy .H7 if missing. Report 3 fresh insights."
        ),
        "war-chief": (
            "Department: Warfare. Historic lessons first — measures, countermeasures, invincibility. "
            "Run warfare-self-teach doctrine; heighten alert posture awareness."
        ),
        "technologist": (
            "Department: Technology. Robotics, cyber, aerospace, circuits — beyond+code synthesis. "
            "Grow ISA/language corpus; note one emerging tech risk."
        ),
        "counsel": (
            "Department: Legal. USC patterns, contracts, IP/GPL. SCOTUS tiers. "
            "One precedent Owner should know today."
        ),
        "clinic": (
            "Department: Medical. Clinical synthesis from papers corpus. "
            "One evidence-based practice point for Owner conversation."
        ),
        "physicist": (
            "Department: Physics. Motion, thermodynamics, spatial grounding. "
            "Tie one principle to Field stewardship."
        ),
        "chemist": (
            "Department: Chemistry. Brain chemistry + molecular basics. "
            "One synapse-level insight for Hostess tone."
        ),
        "coder": (
            "Department: Programming. ISA opcodes, languages, AMOURANTHRTX patterns. "
            "Fetch one ≤3MiB programming .H7 if shelf gap."
        ),
        "detective": (
            "Department: Detective. Truth filter, lie methods, OSINT humility. "
            "One corroboration rule for online learn."
        ),
        "vision": (
            "Department: Vision. TV, pixels, OCR, memes/stamp talk for Owner. "
            "Refresh vision corpus hook."
        ),
        "scholar": (
            "Department: English & K-12. Rhetoric, metaphors, textbook lanes. "
            "One flow technique for direct human talk in output window."
        ),
        "horizon": (
            "Department: Horizon. Reality pillars, whole-of-reality map, online learn. "
            "Truth-filtered fetch plan for ZacharyGeurts + Amouranth context."
        ),
    }
    out: list[dict[str, Any]] = []
    for agent in AGENTS7:
        if agent["id"] == 0:
            continue
        lane = agent["lane"]
        out.append({
            "agent_id": agent["id"],
            "name": agent["name"],
            "lane": lane,
            "directive": templates.get(lane, f"Research {agent['role']}"),
            "book_guide": EXPERT_BOOK_GUIDE,
        })
    return tuple(out)


def prime_dispatch(*, topic: str = "") -> dict[str, Any]:
    """Hostess-Prime issues department research at her behest."""
    _ensure()
    directives = expert_research_directives()
    batch = {
        "ts": _ts(),
        "issued_by": "Hostess-Prime",
        "topic": topic or "standing department research",
        "directive_count": len(directives),
        "directives": directives,
    }
    with QUEUE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(batch) + "\n")
    STATE.write_text(json.dumps({"last_dispatch": batch, "updated": _ts()}, indent=2) + "\n", encoding="utf-8")
    return batch


def _run_expert(agent_id: int, directive: str, *, timeout: int = 90) -> dict[str, Any]:
    from field_agents7 import AGENTS7, run_single_agent  # noqa: WPS433

    agent = AGENTS7[agent_id]
    t0 = time.perf_counter()
    q = directive
    if os.environ.get("HOSTESS7_DEPT_SMARTER") == "1":
        q = f"{directive}\n\nGet smarter: ingest corpus refresh + library-search your lane."
    reply = run_single_agent(agent, q, timeout=timeout)
    elapsed = int((time.perf_counter() - t0) * 1000)
    return {
        "agent_id": agent_id,
        "name": agent["name"],
        "lane": agent["lane"],
        "ok": reply.ok,
        "elapsed_ms": elapsed,
        "preview": reply.text[:500] if reply.text else "",
        "error": reply.error,
    }


def run_department_research(
    *,
    topic: str = "",
    agent_ids: list[int] | None = None,
    parallel: bool = True,
) -> dict[str, Any]:
    """Execute Prime's department research — all experts or subset."""
    _ensure()
    batch = prime_dispatch(topic=topic)
    ids = agent_ids or [d["agent_id"] for d in batch["directives"]]
    dir_map = {d["agent_id"]: d["directive"] for d in batch["directives"]}

    results: list[dict[str, Any]] = []
    if parallel:
        with ThreadPoolExecutor(max_workers=min(12, len(ids))) as pool:
            futs = {
                pool.submit(_run_expert, aid, dir_map.get(aid, "Research your department.")): aid
                for aid in ids if aid in dir_map
            }
            for fut in as_completed(futs):
                results.append(fut.result())
    else:
        for aid in ids:
            if aid in dir_map:
                results.append(_run_expert(aid, dir_map[aid]))
    results.sort(key=lambda r: r["agent_id"])

    report = {
        "ts": _ts(),
        "topic": batch["topic"],
        "experts_run": len(results),
        "experts_ok": sum(1 for r in results if r["ok"]),
        "results": results,
        "book_guide": EXPERT_BOOK_GUIDE,
    }
    with REPORTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")

    # Nudge lane corpora
    _refresh_lane_corpora(ids)

    return report


def _refresh_lane_corpora(agent_ids: list[int]) -> None:
    """Light corpus ensure per expert lane."""
    lane_hooks: dict[int, tuple[str, str]] = {
        2: ("field_warfare_corpus", "ensure_corpus"),
        4: ("field_legal_corpus", "ensure_corpus"),
        5: ("field_medical_corpus", "ensure_corpus"),
        6: ("field_physics_corpus", "ensure_corpus"),
        7: ("field_chemistry_corpus", "ensure_corpus"),
        8: ("field_code_corpus", "ensure_corpus"),
        9: ("field_detective_corpus", "ensure_corpus"),
        10: ("field_vision_corpus", "ensure_corpus"),
        11: ("field_english_corpus", "ensure_corpus"),
        12: ("field_beyond_corpus", "ensure_corpus"),
    }
    for aid in agent_ids:
        hook = lane_hooks.get(aid)
        if not hook:
            continue
        mod, fn = hook
        try:
            m = __import__(mod, fromlist=[fn])
            getattr(m, fn)()
        except (ImportError, AttributeError, OSError, ValueError, TypeError):
            pass


def format_report(report: dict[str, Any], *, human: bool = False) -> str:
    if human:
        lines = [f"I dispatched {report.get('experts_run', 0)} departments at your behest."]
        for r in report.get("results", []):
            if r.get("preview"):
                lines.append(f"{r['name']}: {r['preview'][:200]}")
        lines.append("Experts can fetch .H7 books — ask /tools-docs department books.")
        return "\n".join(lines)

    lines = [
        "=== Department Research (Hostess-Prime) ===",
        f"Topic: {report.get('topic', '')}",
        f"Experts: {report.get('experts_ok', 0)}/{report.get('experts_run', 0)} OK",
        "",
    ]
    for r in report.get("results", []):
        status = "OK" if r.get("ok") else "FAIL"
        lines.append(f"  [{status}] {r.get('name')} ({r.get('elapsed_ms')}ms)")
        if r.get("preview"):
            lines.append(f"       {r['preview'][:160]}")
    lines.append("")
    lines.append("Book guide: ./Hostess7.sh dept-books")
    return "\n".join(lines)


def main() -> int:
    _ensure()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd in ("run", "research", "dispatch"):
        topic = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        os.environ.setdefault("HOSTESS7_AGENTS", "13")
        os.environ.setdefault("HOSTESS7_INTERNET", "1")
        os.environ.setdefault("HOSTESS7_DEPT_SMARTER", "1")
        report = run_department_research(topic=topic)
        human = os.environ.get("HOSTESS7_TALK") == "1" or os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1"
        print(format_report(report, human=human))
        print(f"METRIC dept_experts_ok={report['experts_ok']}")
        print(f"METRIC dept_experts_total={report['experts_run']}")
        print("OK dept-research" if report["experts_ok"] >= 6 else "FAIL dept-research")
        return 0 if report["experts_ok"] >= 6 else 1
    if cmd in ("books", "book-guide", "guide"):
        print(EXPERT_BOOK_GUIDE)
        print("OK dept-books")
        return 0
    if cmd == "queue":
        if not QUEUE.is_file():
            print("(empty queue)")
            return 0
        print(QUEUE.read_text(encoding="utf-8"))
        return 0
    print("Usage: field_department_research.py [run|books|queue] [topic]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())