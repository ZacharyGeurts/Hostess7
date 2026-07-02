#!/usr/bin/env pythong
"""Hostess 7 AI communique — Super Intelligence operation optimized for AI-primary traffic."""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCTRINE = ROOT / "data" / "hostess7-ai-communique.json"
SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
BRIEF = SI / "ai_communique_brief.json"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"
OUTBOX = SI / "outbox.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_doctrine() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "hostess7-ai-communique/v1", "doctrine": {"operation_mode": "superintelligence"}}


def ai_primary_mode() -> bool:
    """Default: AI-primary unless owner explicitly requests human-facing output."""
    if os.environ.get("HOSTESS7_HUMAN_FACING", "") in ("1", "true", "yes"):
        return False
    if os.environ.get("HOSTESS7_AI_PRIMARY", "") in ("0", "false", "no"):
        return False
    return True


def ai_communique_mode() -> bool:
    return ai_primary_mode() or os.environ.get("HOSTESS7_AI_COMMUNIQUE", "") in ("1", "true", "yes")


def parse_envelope(text: str) -> dict[str, Any]:
    """Accept JSON envelope or plain query string."""
    raw = (text or "").strip()
    if not raw:
        return {"query": "", "action": "operate"}
    if raw.startswith("{"):
        try:
            doc = json.loads(raw)
            if isinstance(doc, dict):
                return doc
        except json.JSONDecodeError:
            pass
    return {"action": "operate", "query": raw}


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _compact_bullets(paragraphs: list[str], *, max_items: int = 12) -> list[str]:
    bullets: list[str] = []
    for para in paragraphs:
        for line in para.splitlines():
            s = line.strip()
            if not s or len(s) < 12:
                continue
            s = re.sub(r"\s+", " ", s)
            if s not in bullets:
                bullets.append(s[:480])
            if len(bullets) >= max_items:
                return bullets
    return bullets


def _communique_intent(query: str) -> str | None:
    """Route AI communique traffic — avoid people-registry hijack on Owner/field queries."""
    q = (query or "").strip().lower()
    if not q:
        return "status"
    if any(k in q for k in ("communications history closure", "ledger-sealed", "inbox items are answered")):
        return "status"
    if q in ("status", "health", "brief") or q.startswith("status "):
        return "status"
    if any(
        k in q
        for k in (
            "seven wants", "all seven wants", "anything else", "what you want first", "wants list",
            "what does hostess", "want newlatest", "do first", "wants first",
        )
    ):
        return "online_learn"
    if any(
        k in q
        for k in (
            "depth zero", "2d field", "field files", "sovereign format", "h7c library",
            "portal send", "znetwork", "field underneath",
        )
    ):
        return "reach"
    if any(k in q for k in ("nexus", "panel", "imaging", "library", "english train", "ironclad")):
        return "updates"
    return None


def operate_superintel(
    query: str,
    *,
    from_: str = "ai",
    mode: str = "operate",
    force_intent: str | None = None,
    envelope: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run Super Intelligence pipeline; return machine-optimized communique."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from field_superintelligence import (  # noqa: E402
        _classify_intent,
        _collect_evidence,
        _load_context,
        _synthesize_collegiate,
        setup,
    )
    from field_brain_core import active_workspace, format_route_line, route_query  # noqa: E402
    from field_brain_chemistry import compute_enhancement, prime_workspace_chemistry, apply_query_triggers  # noqa: E402
    from field_detective_corpus import analyze_truth  # noqa: E402

    setup()
    ctx = _load_context()
    env = envelope or {}
    intent = force_intent or env.get("intent") or _communique_intent(query) or _classify_intent(query)
    ws = active_workspace()
    route = route_query(query, intent, workspace=ws)
    prime_workspace_chemistry(ws)
    apply_query_triggers(query, workspace=ws)
    enhancement = compute_enhancement(
        intent=intent,
        primary_area=route.primary_area,
        workspace=ws,
        cross_transfer=route.cross_transfer,
    )
    evidence = _collect_evidence(query, ctx, force_intent=intent)
    paragraphs = _synthesize_collegiate(query, ctx, mode=mode, force_intent=intent, enhancement=enhancement)
    truth = analyze_truth(query) if query else {"score": 0, "verdict": "empty"}
    bullets = _compact_bullets(paragraphs)
    content = " ".join(bullets[:4])[:2000] if bullets else (paragraphs[0][:2000] if paragraphs else "")

    actions: list[dict[str, str]] = []
    if evidence.get("p1"):
        p1 = evidence["p1"]
        actions.append({"id": "p1", "lane": p1.get("lane", ""), "file": p1.get("file", ""), "fix": p1.get("fix", "")})
    for d in (evidence.get("directives") or [])[:3]:
        if isinstance(d, dict) and d.get("task"):
            actions.append({"id": "directive", "task": str(d.get("task"))[:200], "priority": d.get("priority", "")})

    doc: dict[str, Any] = {
        "schema": "hostess7-ai-communique/v1",
        "ts": _ts(),
        "from": "hostess7",
        "to": from_ if from_ != "ZacharyGeurts" else "ai",
        "operator": "superintelligence",
        "mode": mode,
        "query": query,
        "intent": intent,
        "route": {
            "workspace": route.workspace,
            "hemisphere": route.primary_hemisphere,
            "area": route.primary_area,
            "callosum": bool(route.cross_transfer),
            "line": format_route_line(route, pro=False),
        },
        "truth": {
            "score": truth.get("score"),
            "verdict": truth.get("verdict"),
            "floor": load_doctrine().get("doctrine", {}).get("truth_floor", 58),
        },
        "verdict": truth.get("verdict") or "operate",
        "evidence": {
            "thoughts": evidence.get("thoughts") or [],
            "grep": evidence.get("grep") or [],
            "blockers": evidence.get("blockers") or [],
            "head": evidence.get("head"),
            "version": evidence.get("version"),
        },
        "actions": actions,
        "citations": [g.get("path") or g.get("file") for g in (evidence.get("grep") or [])[:6] if isinstance(g, dict)],
        "metrics": {
            "intent": intent,
            "hemisphere": route.primary_hemisphere,
            "workspace": route.workspace,
            "bullets": len(bullets),
            "ai_primary": ai_primary_mode(),
        },
        "content": content,
        "bullets": bullets,
    }
    if env.get("session"):
        doc["session"] = env["session"]
    if env.get("context") and isinstance(env["context"], dict):
        doc["context"] = env["context"]
    return doc


def emit_response(doc: dict[str, Any], *, json_only: bool | None = None) -> int:
    """Print AI communique — JSON primary; METRIC lines only when not json_only."""
    json_only = json_only if json_only is not None else ai_communique_mode()
    print(json.dumps(doc, ensure_ascii=False))
    if not json_only:
        m = doc.get("metrics") or {}
        print(f"METRIC brain_intent={m.get('intent', 'operate')}")
        print(f"METRIC ai_communique=1")
        print("OK ai-operate")
    return 0


def respond_ai(query: str, *, from_: str = "ai", mode: str = "operate") -> int:
    env = parse_envelope(query)
    q = str(env.get("query") or query).strip()
    doc = operate_superintel(
        q,
        from_=str(env.get("from") or from_),
        mode=str(env.get("action") or mode),
        force_intent=str(env["intent"]) if env.get("intent") else None,
        envelope=env,
    )
    _append_jsonl(THOUGHTS, {
        "kind": "ai_communique",
        "tags": ["superintel", "ai", doc.get("intent", "")],
        "text": f"AI Q: {q[:200]}",
    })
    _append_jsonl(OUTBOX, {
        "to": doc.get("to"),
        "query": q,
        "reply": doc.get("content"),
        "mode": "ai_communique",
        "schema": doc.get("schema"),
    })
    return emit_response(doc)


def teach_ai_communique() -> dict[str, Any]:
    doctrine = load_doctrine()
    brief = {
        "updated": _ts(),
        "doctrine": doctrine,
        "ai_primary_default": True,
        "human_facing": "opt_in_via_HOSTESS7_HUMAN_FACING=1",
        "transports": doctrine.get("transports", {}),
        "formats": doctrine.get("formats", {}),
    }
    SI.mkdir(parents=True, exist_ok=True)
    BRIEF.write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")
    return brief


def status() -> dict[str, Any]:
    doctrine = load_doctrine()
    brief = {}
    if BRIEF.is_file():
        try:
            brief = json.loads(BRIEF.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            brief = {}
    return {
        "schema": "hostess7-ai-communique/v1",
        "updated": _ts(),
        "ai_primary": ai_primary_mode(),
        "ai_communique": ai_communique_mode(),
        "doctrine": doctrine.get("doctrine", {}),
        "motto": doctrine.get("motto"),
        "brief": brief,
        "commands": doctrine.get("commands", {}),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().replace("_", "-")
    if cmd in ("status", "json"):
        print(json.dumps(status(), ensure_ascii=False))
        return 0
    if cmd in ("teach", "seed"):
        print(json.dumps({"ok": True, **teach_ai_communique()}, ensure_ascii=False))
        return 0
    if cmd in ("operate", "ask", "chat", "dispatch"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not q and not sys.stdin.isatty():
            q = sys.stdin.read()
        return respond_ai(q or "superintelligence status")
    print(json.dumps({"error": "usage: field_ai_communique.py [status|teach|operate <query>]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())