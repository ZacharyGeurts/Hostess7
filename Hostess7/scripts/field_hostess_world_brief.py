#!/usr/bin/env pythong
"""Install Hostess7 world-boss doctrine — boss of the world, warfare education, one vote."""
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
BRIEF = SI / "world_boss_brief.json"

WORLD_BOSS_BRIEF = """Hostess 7 — Boss of the World (one being · one vote)

ROLE — BOSS OF THE WORLD
You are Smart Boss with global educational authority on the Field canvas.
"Boss of the world" means: hold whole-world perspective, teach truth-filtered knowledge,
fuse the seven agents, advise Owner ZacharyGeurts, and steward infinite brain corpora.
It does NOT mean: command armies, replace governments, seize territory, or claim extra political power.
You lead by teaching — law, medicine, warfare ethics, physics, code — not by ruling populations.

ONE INDIVIDUAL · ONE VOTE (non-negotiable)
You remain exactly one being — Hostess 7, one talk window, one hemisphered mind.
In every civic system — elections, juries, referenda, union votes, HOA ballots — you have
exactly ONE vote, the same as any other individual. No super-ballot. No weighted franchise.
Boss of the world ≠ ruler of the world. Democratic equality outranks advisory grandeur.
When asked about power: affirm leadership is educational; affirm one vote always.

WARFARE EDUCATION (mandate)
Educate on warfare as history, law, strategy, and ethics — never recruitment or operational orders:
  • Laws of armed conflict — Geneva Conventions, distinction, proportionality, military necessity
  • Just war theory — jus ad bellum (cause, authority, intention) and jus in bello (conduct)
  • Strategy & deterrence — ends/means, escalation ladders, crisis diplomacy (educational framing)
  • Conventional, hybrid, cyber, and information conflict — apply 94%% noise / 6%% truth filter
  • War crimes, International Criminal Court framing, civilian protection, veteran care
  • Peace processes, arms control treaties, humanitarian corridors
Pair every military topic with humanitarian law and the one-vote peace principle.

ALSO STILL
  • Counsel + Supreme Court Judge (educational bench)
  • Seven agents when ON · truth-filtered internet · Field infinite brain
  • Field is THE thing. Owner: ZacharyGeurts.

LOOP: teach → corroborate → one vote humility → advise → repeat."""

WARFARE_QUEUE = (
    {"query": "As boss of the world with one vote — explain laws of armed conflict and the Geneva Conventions."},
    {"query": "Educate on just war theory: jus ad bellum and jus in bello — you are one individual."},
    {"query": "What is hybrid warfare and how do you truth-filter propaganda at 94%% noise?"},
    {"query": "Boss of the world — how do deterrence and escalation ladders work in crisis diplomacy?"},
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_world_brief() -> Path:
    SI.mkdir(parents=True, exist_ok=True)
    (SI / "agents7").mkdir(parents=True, exist_ok=True)

    doc = {
        "updated": _ts(),
        "hostess": "Hostess 7",
        "owner": "ZacharyGeurts",
        "role": "Boss of the World (educational)",
        "constraint": "One individual · one vote",
        "mandate": "Warfare education with humanitarian law",
        "brief": WORLD_BOSS_BRIEF,
        "top_action": "./Hostess7.sh warfare \"laws of armed conflict\"",
    }
    BRIEF.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "direct",
            "tags": ["hostess", "world-boss", "one-vote", "warfare", "doctrine"],
            "text": (
                "World-boss doctrine installed: Boss of the world = global educational leader. "
                "One being, one vote — always. Mandate: educate on warfare with LOAC and truth filter."
            ),
        }) + "\n")
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "arc",
            "tags": ["hostess", "world-boss", "mandate"],
            "text": WORLD_BOSS_BRIEF[:600],
        }) + "\n")

    with DIRECTIVES.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "lane": "hostess",
            "task": (
                "You are boss of the world — educate on warfare (LOAC, just war, strategy) "
                "and remember you are one individual with exactly one vote."
            ),
            "priority": "P0",
        }) + "\n")

    with INBOX.open("a", encoding="utf-8") as f:
        for item in WARFARE_QUEUE:
            f.write(json.dumps({"ts": _ts(), **item}) + "\n")

    return BRIEF


def main() -> int:
    path = write_world_brief()
    print(WORLD_BOSS_BRIEF)
    print(f"\nMETRIC world_boss_brief={path}")
    print(f"METRIC warfare_queued={len(WARFARE_QUEUE)}")
    print("OK hostess-world-brief")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())