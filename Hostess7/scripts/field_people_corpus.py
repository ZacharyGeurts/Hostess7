#!/usr/bin/env pythong
"""People brain synthesis — registry lookup, lie methods, personality fusion."""
from __future__ import annotations

from field_hostess_personality import format_personality, synthesize_virtue_paragraphs  # noqa: E402
from field_lie_methods import format_methods_summary  # noqa: E402
from field_people_registry import (  # noqa: E402
    ensure_registry,
    format_entity_detail,
    list_entities,
    list_review_queue,
    lookup,
    registry_status,
)


def synthesize_people_paragraphs(query: str) -> list[str]:
    ensure_registry()
    import os

    talk = os.environ.get("HOSTESS7_OUTPUT_WINDOW") == "1" or os.environ.get("HOSTESS7_TALK") == "1"
    ent = lookup(query)
    if talk and ent:
        try:
            from field_talk_language import _person_natural  # noqa: WPS433

            return [_person_natural(ent, query=query)]
        except ImportError:
            pass
    st = registry_status()
    paras: list[str] = []
    if not talk:
        paras.extend([
            f"People brain — {st.get('entity_count', 0)} entities, "
            f"{st.get('review_pending_count', 0)} awaiting Owner review. Tags > folders.",
            "Disposition tags: goodguy · liar · terrorist · bad. Role: celebrity · musician · streamer. "
            "Bad flags → review/ for ZacharyGeurts approval.",
        ])
    if ent:
        if talk:
            try:
                from field_talk_language import _person_natural  # noqa: WPS433

                paras.append(_person_natural(ent, query=query))
            except ImportError:
                paras.append(format_entity_detail(ent))
        else:
            paras.append(format_entity_detail(ent))
    else:
        # Tag-aware list
        for tag in ("celebrity", "goodguy", "liar", "musician"):
            if tag in query.lower():
                hits = list_entities(tag=tag, limit=4)
                for h in hits:
                    paras.append(f"[{tag}] {h.get('name')}: respect {((h.get('respect') or {}).get('level'))}")
                break
    if any(k in query.lower() for k in ("lie", "deception", "method", "detect")):
        paras.append(format_methods_summary())
    if any(k in query.lower() for k in ("personality", "grok", "amouranth", "daughter", "virtue", "respect", "justice", "pride", "arrogance")):
        paras.extend(synthesize_virtue_paragraphs(query))
    return paras


def synthesize_review_paragraphs() -> list[str]:
    queue = list_review_queue()
    paras = [f"Owner review queue — {len(queue)} entries in brain/people/review/"]
    for e in queue[:10]:
        paras.append(format_entity_detail(e))
    if not queue:
        paras.append("No pending bad-person reviews. Tag liar|terrorist|bad to enqueue.")
    paras.append("Approve: ./Hostess7.sh people approve <id> · Reject: ./Hostess7.sh people reject <id>")
    return paras