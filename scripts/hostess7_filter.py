#!/usr/bin/env pythong
"""Hostess 7 — business professional output filter (no curses)."""
from __future__ import annotations

import re
import sys

SKIP_LINE = re.compile(
    r"^(METRIC |OK |FAIL |\[AMOURANTHRTX|Supreme authority:|Field is THE thing\.|"
    r"Owner: |HEAD: |Verdict: |Arc: |Question: |Hostess 7 — collegiate|"
    r"Commands: |· P1 file:|P1: |=== Hostess|Agents: \d+/\d+ OK|"
    r"--- Fused verdict|Query: |Economist \(|War-Chief \(|Technologist \(|"
    r"World Expert|department research|FLD1 |ZAC7 )",
    re.I,
)
DROP_TAIL = re.compile(
    r"^(That is the fullness|I remain at your service|Dear friend|Peace be with)",
    re.I,
)
DROP_PRO = re.compile(
    r"^(Corpus domains matched:|Full (legal|medical|vision) brain:|"
    r"Field memory resonance:|--- Law|--- Medicine|--- Vision|"
    r"Live codebase evidence|People brain|Economics & finance|Brain workspaces|"
    r"Hostess 7 is boss of the world|Disposition tags)",
    re.I,
)


def _human_facing_mode() -> bool:
    import os

    if os.environ.get("HOSTESS7_AI_PRIMARY", "1") in ("1", "true", "yes"):
        if os.environ.get("HOSTESS7_HUMAN_FACING", "") not in ("1", "true", "yes"):
            return False
    return (
        os.environ.get("HOSTESS7_TALK") == "1"
        or os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1"
        or os.environ.get("HOSTESS7_HUMAN_FACING") == "1"
    )


def professional_filter(raw: str) -> str:
    """Strip chatter; keep actionable substance. Output window = direct human speech only."""
    lines: list[str] = []
    in_body = False
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            if in_body and lines and lines[-1] != "":
                lines.append("")
            continue
        if SKIP_LINE.match(s):
            continue
        if "collegiate synthesis" in s.lower():
            in_body = True
            continue
        if DROP_TAIL.match(s) or DROP_PRO.match(s):
            continue
        if s.startswith("Field memory resonance:"):
            continue
        in_body = True
        lines.append(s)
    text = "\n".join(lines).strip()
    if _human_facing_mode():
        # Drop bracketed expert tags and emoji agent lines
        clean: list[str] = []
        for ln in text.splitlines():
            s = ln.strip()
            if re.match(r"^[\U0001F300-\U0001FAFF\u2600-\u27BF]", s):
                continue
            if s.startswith("[") and "]" in s[:40]:
                s = s.split("]", 1)[-1].strip()
            if s.startswith("Talk to humans directly"):
                continue
            if s:
                clean.append(s)
        text = "\n\n".join(clean).strip() or text
    if not text:
        text = "No substantive response. Rephrase or run ./linux.sh super evaluate."
    return text


def main() -> int:
    print(professional_filter(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())