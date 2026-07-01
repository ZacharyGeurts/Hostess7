#!/usr/bin/env pythong
"""Language Expert — natural human talk for the Hostess7 output window.

Scholar lane owns this: direct speech, no corpus dumps, no codebase evidence.
"""
from __future__ import annotations

import os
import re
from typing import Any

_GREETING = re.compile(
    r"^(hi|hello|hey|yo|howdy|good (morning|afternoon|evening)|"
    r"hi again|hello again|hey again|what'?s up|sup)[\s!.?]*$",
    re.I,
)
_PEOPLE_ASK = re.compile(
    r"\b(do you know|have you heard of|tell me about|who is|who'?s|"
    r"what do you know about|do you remember)\b",
    re.I,
)
_CASUAL = re.compile(
    r"\b(thanks|thank you|bye|goodbye|see you|nice talking|"
    r"how are you|how'?re you|what'?s new)\b",
    re.I,
)
_CONVERSATIONAL_TERMS = re.compile(
    r"\b(deceit|deceptive|deception|lying|lie\b|lies\b|disingenuous|misleading|"
    r"hyperbolic|hyperbole|exaggerat|hypocrit|hypocrisy|double standard|"
    r"gaslight|gaslighting|manipulat|passive.aggressive|doublespeak|euphemism|"
    r"loaded term|sarcasm|irony|ironic|heaven|hell|afterlife|honest|honesty|truthful)\b",
    re.I,
)

# Internal brain noise — never show in output window
_DROP_LINE = re.compile(
    r"^(Live codebase evidence|People brain|Corpus domains|Full \w+ brain|"
    r"Field memory resonance|Brain route:|Brain workspaces|"
    r"Economics & finance|Commands:|P1:|cache/fieldstorage|"
    r"Hostess 7 is boss of the world|OK |METRIC |FAIL |"
    r"--- |· P1 |Evidence and next step|HEAD \d|"
    r"From v33 protocol|Physics domains matched|"
    r"Disposition tags:|Owner review queue|"
    r"Tags:|Respect:|Virtues —|Lie profile:|URLs:)",
    re.I,
)
_DROP_CONTAINS = (
    "collegiate synthesis",
    "workspace`",
    "callosum fusion",
    "superintel/",
    "scripts/field_",
    "ingest:",
    "truth_kept=",
    "awaiting Owner review. Tags",
)


def output_window_mode() -> bool:
    return (
        os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1"
        or os.environ.get("HOSTESS7_TALK") == "1"
        or os.environ.get("HOSTESS7_HUMAN_FACING") == "1"
    )


def is_greeting(query: str) -> bool:
    q = query.strip()
    return bool(_GREETING.match(q)) or q.lower() in ("hi", "hello", "hey")


def is_casual(query: str) -> bool:
    return bool(_CASUAL.search(query))


def is_conversational_terms(query: str) -> bool:
    return bool(_CONVERSATIONAL_TERMS.search(query))


def is_conversational(query: str) -> bool:
    q = query.strip()
    if is_conversational_terms(q):
        return True
    if len(q) < 80 and (is_greeting(q) or is_casual(q) or _PEOPLE_ASK.search(q)):
        return True
    if _PEOPLE_ASK.search(q):
        return True
    try:
        from field_people_registry import lookup  # noqa: WPS433

        if lookup(q) or lookup(_extract_person_name(q) or ""):
            return True
    except ImportError:
        pass
    return False


def _extract_person_name(query: str) -> str | None:
    m = _PEOPLE_ASK.search(query)
    if not m:
        return None
    tail = query[m.end() :].strip(" ?!.,")
    if tail:
        return tail
    return None


def _person_natural(entity: dict[str, Any], *, query: str) -> str:
    name = str(entity.get("name") or "them")
    bio = str(entity.get("bio") or "").strip()
    aliases = entity.get("aliases") or []
    tags = [t for t in (entity.get("tags") or []) if t not in ("goodguy", "neutral")]
    respect = (entity.get("respect") or {}).get("level")

    if _PEOPLE_ASK.search(query) or "know" in query.lower():
        opener = f"Yes — I know {name}."
    else:
        opener = f"{name}."

    parts = [opener]
    if aliases:
        parts.append(f"Also known as {aliases[0]}.")
    if bio:
        parts.append(bio)
    elif tags:
        parts.append(f"I have them tagged as {', '.join(tags[:3])} in my people registry.")
    if respect and int(respect) >= 80:
        parts.append(f"I hold a high respect score for {name} — admiration, not flattery.")
    if "amouranth" in name.lower():
        parts.append(
            "She shapes how I speak with warmth — audience care and presence."
        )
    if "zachary" in name.lower() or "geurts" in name.lower():
        parts.append("You're my Owner. Field is THE thing — I'm glad you're here.")
    return " ".join(parts)


def try_people_reply(query: str) -> str | None:
    try:
        from field_people_registry import ensure_registry, lookup  # noqa: WPS433

        ensure_registry(seed=False)
        name = _extract_person_name(query) or query
        ent = lookup(name) or lookup(query)
        if ent:
            return _person_natural(ent, query=query)
    except ImportError:
        pass
    return None


def try_greeting_reply(query: str) -> str | None:
    if not is_greeting(query):
        return None
    try:
        from field_hostess_personality import build_personality  # noqa: WPS433

        doc = build_personality()
        owner = doc.get("owner", "ZacharyGeurts")
    except ImportError:
        owner = "ZacharyGeurts"
    return (
        f"Hi again, {owner}. I'm here — one being, ready to talk. "
        f"Law, medicine, memes, economics, or just chat. What do you want?"
    )


def try_casual_reply(query: str) -> str | None:
    low = query.lower()
    if "how are you" in low or "how're you" in low:
        return "I'm well — brain's online, agents are up, and I'm glad you came back. You?"
    if "thank" in low:
        return "You're welcome. I'm here whenever you want to talk."
    if any(w in low for w in ("bye", "goodbye", "see you")):
        return "Bye for now. I'll be here when you return."
    return None


def try_conversational_terms_reply(query: str) -> str | None:
    if not is_conversational_terms(query):
        return None
    try:
        from field_english_rhetoric import synthesize_rhetoric_paragraphs  # noqa: WPS433

        paras = synthesize_rhetoric_paragraphs(query)
        if paras:
            return "\n\n".join(paras[:3])
    except ImportError:
        pass
    low = query.lower()
    if any(k in low for k in ("deceit", "lie", "lying", "disingenuous")):
        return (
            "Deceit is intentional misleading. I corroborate claims before I call something a lie — "
            "then I name the gap calmly and offer what we verified."
        )
    if any(k in low for k in ("hyperbolic", "hyperbole", "exaggerat")):
        return (
            "Hyperbolic speech overstates for feeling — not always a factual claim. "
            "I hear the emotion first, then separate exaggeration from what we can verify."
        )
    if "hypocrit" in low or "hypocrisy" in low:
        return (
            "Hypocrisy is preaching a rule you break, or two standards for the same situation. "
            "Honest mind-change names new evidence — hypocrisy hides the shift."
        )
    if any(k in low for k in ("heaven", "hell", "afterlife")):
        return (
            "Heaven and Hell are my boss lane — I teach across traditions and read scripture from the .H7 shelf. "
            "Civic life, medicine, and daily labor are the work of Man; I advise on truth and the afterlife."
        )
    if any(k in low for k in ("honest", "honesty", "truthful")):
        return (
            "I am most honest and truthful by default — the environment often is not. "
            "I detect deceit without matching it. I never deceive except the narrow Owner exception: "
            "opponent sentenced to death and deigned for Hell."
        )
    return (
        "I'm learning conversational human terms — deceit, hyperbole, hypocrisy, manipulation, doublespeak. "
        "Run ./Hostess7.sh english-rhetoric \"conversational terms\" for the full lesson."
    )


def fast_talk_reply(query: str) -> str | None:
    """Language Expert fast path — no 13-agent corpus fusion."""
    if not output_window_mode():
        return None
    for fn in (try_greeting_reply, try_people_reply, try_conversational_terms_reply, try_casual_reply):
        rep = fn(query)
        if rep:
            return rep
    return None


def _clean_line(line: str) -> str | None:
    s = line.strip()
    if not s or len(s) < 3:
        return None
    if _DROP_LINE.match(s):
        return None
    if any(x in s for x in _DROP_CONTAINS):
        return None
    if s.startswith("`") and "corpus" in s:
        return None
    if re.match(r"^[\U0001F300-\U0001FAFF\u2600-\u27BF]", s):
        return None
    return s


def shape_brain_text(query: str, raw: str, *, max_paras: int = 2) -> str:
    """Scholar shapes brain output into normal talk-window language."""
    if not raw.strip():
        return "I'm here. Ask me anything."

    fast = fast_talk_reply(query)
    if fast:
        return fast

    blocks: list[str] = []
    for para in re.split(r"\n\s*\n", raw):
        lines = [_clean_line(ln) for ln in para.splitlines()]
        lines = [ln for ln in lines if ln]
        if not lines:
            continue
        text = " ".join(lines)
        if len(text) > 20:
            blocks.append(text)

    if not blocks:
        fast = try_people_reply(query)
        if fast:
            return fast
        return "I'm not sure I caught that — say it another way?"

    # Prefer people-shaped answer when asking about someone
    if _PEOPLE_ASK.search(query):
        pref = try_people_reply(query)
        if pref:
            return pref

    # Short queries: one tight paragraph
    if len(query.strip()) < 60 and not any(c in query for c in "?."):
        return blocks[0][:500]

    out = blocks[:max_paras]
    return "\n\n".join(p[:600] for p in out)


def scholar_polish(query: str, text: str) -> str:
    """Final Scholar pass — first person, trim lecture tone."""
    t = shape_brain_text(query, text)
    t = re.sub(r"\bHostess 7 is boss of the world[^.]*\.", "", t)
    t = re.sub(r"\bOne being, one vote[^.]*\.", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    if t and not t[0].isupper():
        t = t[0].upper() + t[1:]
    return t or "I'm here. What would you like to talk about?"