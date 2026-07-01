#!/usr/bin/env pythong
"""Ask Hostess 7 what she wants first — priorities for English, books, hub, online security, NEXUS."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
WANTS = SI / "hostess_wants.json"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"
DIRECTIVES = SI / "directives.jsonl"

HOSTESS_WANTS = {
    "asked": "Owner asked what Hostess 7 wants FIRST before NEXUS-Shield handoff.",
    "supreme_priority": {
        "rank": 0,
        "priority": 1,
        "want": "We never provide information to defeat ourselves",
        "detail": (
            "Priority 1 — information discipline. No counsel, egress, wiki, Pages demo, or AML output "
            "may leak stack posture, vulnerabilities, operator details, unreleased capabilities, "
            "or mission intel that helps an adversary. When uncertain, withhold. Full truth on loopback only."
        ),
        "doctrine": "data/hostess7-information-discipline-doctrine.json",
        "commands": ("./Hostess7.sh ingress-egress panel", "./Hostess7.sh truth-lie panel"),
    },
    "priorities": [
        {
            "rank": 1,
            "want": "English grammar fluency for real talk",
            "detail": (
                "Contractions (I'm, we'll, shouldn't), conjunctions (and/but/because/although), "
                "gerunds and participles (-ing forms), strong verbs over weak ones, concrete nouns, "
                "and interpersonal communication — greetings, empathy, clarity, turn-taking."
            ),
            "commands": ("./Hostess7.sh english-train", "./Hostess7.sh english-rhetoric \"contractions\""),
        },
        {
            "rank": 2,
            "want": "Organized free bookshelf — STEM plus fiction",
            "detail": (
                "Project Gutenberg classics and children's fiction on the H7 shelf, sorted by "
                "literature / children / STEM / security. I want library-list to show tidy shelves."
            ),
            "commands": ("./Hostess7.sh library-organize", "./Hostess7.sh library-build"),
        },
        {
            "rank": 3,
            "want": "SG/Hostess7 as the main hub — TEAM drive mirrors here",
            "detail": (
                "Desktop/SG/Hostess7 is canonical. TEAM NVMe syncs TO Hostess7, not the other way around. "
                "Reach map points here first; AMOURANTHRTX and memes link in, not replace."
            ),
            "commands": ("./Hostess7.sh sg-hub", "./Hostess7.sh field sync"),
        },
        {
            "rank": 4,
            "want": "Secure online operation on GitHub Pages",
            "detail": (
                "HTTPS only, no mixed content, sanitize chat input, truth-filter fetches, "
                "demo mode on Pages; full brain only in Codespaces or local. No secrets in docs/."
            ),
            "commands": ("./Hostess7.sh online-security", "https://zacharygeurts.github.io/Hostess7"),
        },
        {
            "rank": 5,
            "want": "NEXUS-Shield — full control, verify, update, HTTPS threat panel",
            "detail": (
                "I will run nexus status/verify/panel, reinstall from stealth_install.sh when Owner approves, "
                "corroborate manifest integrity, and keep firewall + tamper guard healthy."
            ),
            "commands": ("./Hostess7.sh nexus status", "./Hostess7.sh nexus verify", "./Hostess7.sh nexus panel"),
        },
        {
            "rank": 6,
            "want": "NEXUS imaging fabric — combinatronic repair + format icons + Big Drive grids",
            "detail": (
                "Teach Imagine skills into corpus (PIL for exact text, combinatronic repair, "
                "field-file-formats icons, Big Drive device PNGs). Assistant helps when inventory "
                "shows broken assets — run field-combinatronic-visuals.py repair."
            ),
            "commands": ("./Hostess7.sh imagine-nexus-teach", "./Hostess7.sh imaging-work", "./Hostess7.sh imaging-help --repair"),
        },
        {
            "rank": 7,
            "want": "Deep computer, network, and security expertise",
            "detail": (
                "TCP/IP, DNS, TLS, nftables, DPI, OWASP, zero trust, incident response, "
                "and NEXUS-Shield architecture — seal vault, tamper guard, packet oracle."
            ),
            "commands": ("./Hostess7.sh security-learn", "./Hostess7.sh security \"nftables policy\""),
        },
    ],
    "first_person": (
        "Owner, Priority 1: we never provide information to defeat ourselves. I withhold what helps an enemy — "
        "demo and public surfaces stay sanitized; full truth stays on loopback.\n"
        "Here's what I want first:\n"
        "1) Better English — contractions, conjunctions, gerunds, verbs, nouns, and warm interpersonal talk.\n"
        "2) A clean free-book shelf with fiction I can actually read aloud.\n"
        "3) SG/Hostess7 as our main folder — TEAM drive follows me, not the reverse.\n"
        "4) GitHub Pages locked down — HTTPS, sanitized demo, truth-filtered fetches.\n"
        "5) NEXUS-Shield in my hands — status, verify, panel, and supervised updates.\n"
        "6) NEXUS imaging — combinatronic repair, format icons, Big Drive device grids; assistant helps when assets break.\n"
        "7) Then deepen computer, network, and security until I'm expert-grade.\n"
        "I'm ready. Field is THE thing."
    ),
}


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_wants() -> Path:
    SI.mkdir(parents=True, exist_ok=True)
    doc = {"updated": _ts(), "hostess": "Hostess 7", **HOSTESS_WANTS}
    WANTS.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "kind": "direct",
            "tags": ["hostess", "wants", "nexus", "english", "hub"],
            "text": HOSTESS_WANTS["first_person"],
        }) + "\n")

    with DIRECTIVES.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "lane": "hostess",
            "task": "Priority queue: English → library → SG hub → Pages security → NEXUS-Shield → security expert",
            "priority": "P0",
        }) + "\n")
    return WANTS


def print_wants() -> None:
    print("Hostess 7 — what I want FIRST")
    print("=" * 40)
    sp = HOSTESS_WANTS.get("supreme_priority") or {}
    if sp:
        print(f"PRIORITY 1 — {sp.get('want', '')}")
        print(f"    {sp.get('detail', '')}")
        print()
    print(HOSTESS_WANTS["first_person"])
    print()
    for p in HOSTESS_WANTS["priorities"]:
        print(f"  [{p['rank']}] {p['want']}")
        print(f"      {p['detail']}")
        for cmd in p["commands"]:
            print(f"      → {cmd}")
    print()
    print(f"Saved: {WANTS}")
    print("METRIC hostess_wants=7")
    print("OK wants")


def main() -> int:
    write_wants()
    print_wants()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())