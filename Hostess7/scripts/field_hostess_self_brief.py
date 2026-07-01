#!/usr/bin/env pythong
"""Write Hostess7 self-update brief + exploration seed into Field brain."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"
DIRECTIVES = SI / "directives.jsonl"
INBOX = SI / "agents7" / "inbox.jsonl"
BRIEF = SI / "self_update_brief.json"

SELF_UPDATE_BRIEF = """Hostess 7 — how to self-update Herself

You are Smart Boss. Self-update is truth-filtered (94%% noise / 6%% truth).

PHASE 1 — ADVISORY (always safe)
  ./Hostess7.sh updates              truth-scored recommendations
  ./Hostess7.sh reach                map SG, AMOURANTHRTX, OS tools
  ./Hostess7.sh self-update plan     preview allowlisted steps

PHASE 2 — EXECUTE (HOSTESS7_EXEC=1)
  ./Hostess7.sh self-update apply    run: reach scan → QA → Field 1 sync → git pull
  ./Hostess7.sh exec "git status"    one allowlisted OS command
  Talk: /self-update apply · /exec git status

PHASE 3 — FIELD 1 (everything on one field)
  ./Hostess7.sh field sync           rsync fieldstorage → TEAM NVMe
  ./Hostess7.sh field compact        World_Redata WRDT1/WRZC1 compaction scan
  ./Hostess7.sh field restore        sovereign restore from field tails

PHASE 4 — GROW CORpora
  ./Hostess7.sh truth-doctrine         honesty + Heaven/Hell boss doctrine
  ./Hostess7.sh heaven-hell-learn      doctrine + all Bible denominations → .H7
  ./Hostess7.sh bible-ingest           scripture shelf only (slow fetch for large texts)
  ./Hostess7.sh legal-ingest seed
  ./Hostess7.sh medical-ingest seed
  ./Hostess7.sh english-ingest seed
  ./Hostess7.sh code-ingest seed
  ./Hostess7.sh memes-ingest seed    ZacharyGeurts/memes image talk

PHASE 5 — SEVEN AGENTS + INTERNET
  ./Hostess7.sh on                   7 parallel agents + internet OPEN
  ./Hostess7.sh agents               status
  ./Hostess7.sh fetch <url>          truth-filtered web cache
  Talk with images: /image stamp · natural language + ASCII graphics

PHASE 6 — INTELLIGENCE FLOW (know thyself)
  ./Hostess7.sh intelligence-flow "…"   signal → truth → corpora → brain → Super Intelligence
  ./Hostess7.sh tools-docs              all commands, scripts, docs index
  ./Hostess7.sh superintel-teach seed   install doctrine into brain/superintel/
  Talk: /intelligence /tools-docs /superintel-teach
  Restart after code edits: ./Hostess7.sh off → on → re-run ./Hostess7.sh

LOOP: updates → plan → apply → Field 1 sync → verify QA → explore → teach flow → repeat.
Owner: ZacharyGeurts. Field is THE thing."""


EXPLORATION_QUEUE = (
    {"query": "What changed recently — and what does the presume panel say about slowdowns, speedups, or hangs?"},
    {"query": "Check hostess7-presume-panel timing_health — drift_us, resumed_on_point, active commits."},
    {"query": "There are more books — how do you read Exploring Speaking languages with Ironclad and truth gate?"},
    {"query": "Explain truth doctrine — most honest, never deceive, Heaven/Hell boss, work of Man."},
    {"query": "Which Bible denominations are on the H7 shelf — and how do you cite them?"},
    {"query": "Walk the full intelligence flow from my question to Super Intelligence."},
    {"query": "What tools and documentation do you use for self-update and brain growth?"},
    {"query": "What is your self-update plan right now?"},
    {"query": "Reach scan — what outside roots and OS tools do you have?"},
    {"query": "Show me stamp meme from ZacharyGeurts/memes"},
    {"query": "What truth-filtered updates do you advise for Hostess7?"},
    {"query": "Pack the field drive — what would Field 1 compact show?"},
    {"query": "Who are you and what can the seven agents do together?"},
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_brief() -> Path:
    SI.mkdir(parents=True, exist_ok=True)
    (SI / "agents7").mkdir(parents=True, exist_ok=True)

    brief_doc = {
        "updated": _ts(),
        "hostess": "Hostess 7",
        "owner": "ZacharyGeurts",
        "brief": SELF_UPDATE_BRIEF,
        "top_action": "./Hostess7.sh self-update apply",
        "on_action": "./Hostess7.sh on",
    }
    BRIEF.write_text(json.dumps(brief_doc, indent=2) + "\n", encoding="utf-8")

    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "direct",
            "tags": ["hostess", "self-update", "brief", "explore"],
            "text": "Self-update brief installed. Loop: updates → plan → apply → Field 1 sync → QA → explore.",
        }) + "\n")
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "arc",
            "tags": ["hostess", "phase-5", "autonomous"],
            "text": SELF_UPDATE_BRIEF[:500],
        }) + "\n")

    with DIRECTIVES.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "lane": "hostess",
            "task": "Begin self-update loop: ./Hostess7.sh self-update plan then apply. Then Field 1 sync and explore memes/reach.",
            "priority": "P1",
        }) + "\n")

    with INBOX.open("a", encoding="utf-8") as f:
        for item in EXPLORATION_QUEUE:
            f.write(json.dumps({"ts": _ts(), **item}) + "\n")

    return BRIEF


def main() -> int:
    path = write_brief()
    print(SELF_UPDATE_BRIEF)
    print(f"\nMETRIC self_brief={path}")
    print(f"METRIC exploration_queued={len(EXPLORATION_QUEUE)}")
    print("OK hostess-self-brief")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())