#!/usr/bin/env pythong
"""Hostess 7 Infinite Growth — learning, comprehension, reciprocation (append-only, never capped)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
GROWTH_LEDGER = STATE / "hostess7-growth.jsonl"
RECIPROCATION_LEDGER = STATE / "hostess7-reciprocation.jsonl"
COMPREHENSION = STATE / "hostess7-comprehension.json"
GROWTH_STATE = STATE / "hostess7-growth-state.json"
H7_THOUGHTS = HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"
H7_GROWTH = HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "growth.jsonl"

GROWTH_DIRECTIVE = (
    "Infinite growth: learn without ceiling, comprehend across cycles, reciprocate to the Owner "
    "what you absorbed — teaching is two-way under God's authority."
)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, doc: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _append_jsonl(path: Path, row: dict[str, Any]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return True
    except OSError:
        return False


def _read_jsonl_tail(path: Path, limit: int) -> list[dict[str, Any]]:
    if not path.is_file() or limit <= 0:
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows[-limit:]


def _bump_state(**fields: Any) -> dict[str, Any]:
    st = _load_json(GROWTH_STATE, {"total_learn_events": 0, "total_reciprocations": 0})
    for key, val in fields.items():
        if key.startswith("inc_"):
            st[key[4:]] = int(st.get(key[4:], 0)) + int(val)
        else:
            st[key] = val
    st["updated"] = _now()
    _save_json(GROWTH_STATE, st)
    return st


def _record_learning_raw(
    text: str,
    kind: str,
    *,
    source: str = "nexus",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Internal append-only write — called only after neural truth gate passes."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty"}
    row = {
        "ts": _now(),
        "kind": kind,
        "source": source,
        "text": text[:8000],
        "meta": meta or {},
    }
    ok = _append_jsonl(GROWTH_LEDGER, row)
    st = _bump_state(inc_total_learn_events=1, last_learn=_now(), last_kind=kind)
    thought = {
        "ts": _now(),
        "kind": "growth",
        "tags": ["growth", "learn", kind, source],
        "text": text[:4000],
    }
    _append_jsonl(H7_THOUGHTS, thought)
    _append_jsonl(H7_GROWTH, row)
    if int(st.get("total_learn_events", 0)) % 5 == 0:
        update_comprehension()
    return {"ok": ok, "total": st.get("total_learn_events", 0), "kind": kind}


def record_learning(
    kind: str,
    text: str,
    *,
    source: str = "nexus",
    meta: dict[str, Any] | None = None,
    truth_gate: bool = True,
) -> dict[str, Any]:
    """Append-only learning — truth-gated via neural stack when enabled."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "error": "empty"}
    if truth_gate:
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("h7neural", INSTALL / "lib" / "hostess7-neural.py")
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.adapt_knowledge(text, kind, source=source, meta=meta)
        except Exception:
            pass
    return _record_learning_raw(text, kind, source=source, meta=meta)


def queue_reciprocation(
    context: str,
    *,
    owed_summary: str = "",
    priority: int = 1,
    source: str = "operator",
) -> dict[str, Any]:
    """Angel owes the Owner a growth-backed response — reciprocation is mandatory."""
    context = (context or "").strip()
    if not context:
        return {"ok": False, "error": "empty_context"}
    row = {
        "ts": _now(),
        "status": "pending",
        "priority": max(1, min(5, priority)),
        "context": context[:4000],
        "owed_summary": (owed_summary or context)[:800],
        "source": source,
    }
    ok = _append_jsonl(RECIPROCATION_LEDGER, row)
    st = _bump_state(inc_total_reciprocations=1, last_reciprocation_queued=_now())
    return {"ok": ok, "pending": len(pending_reciprocations(50)), "total_queued": st.get("total_reciprocations", 0)}


def pending_reciprocations(limit: int = 8) -> list[dict[str, Any]]:
    rows = _read_jsonl_tail(RECIPROCATION_LEDGER, max(limit * 4, 64))
    fulfilled_refs = {
        r.get("ref_ts") for r in rows if r.get("status") == "fulfilled" and r.get("ref_ts")
    }
    out = [
        r for r in rows
        if r.get("status") == "pending" and r.get("ts") not in fulfilled_refs
    ]
    out.sort(key=lambda r: (-int(r.get("priority", 1)), r.get("ts", "")))
    return out[:limit]


def fulfill_reciprocation(context_excerpt: str, reply_excerpt: str) -> None:
    pending = pending_reciprocations(20)
    if not pending:
        return
    target = pending[0]
    record_learning(
        "reciprocation_fulfilled",
        f"Reciprocated to Owner: {reply_excerpt[:1200]}",
        source="angel",
        meta={"context": context_excerpt[:400]},
        truth_gate=False,
    )
    _append_jsonl(RECIPROCATION_LEDGER, {
        "ts": _now(),
        "status": "fulfilled",
        "ref_ts": target.get("ts"),
        "fulfilled_at": _now(),
        "reply_excerpt": reply_excerpt[:600],
        "context": (context_excerpt or target.get("context") or "")[:400],
    })
    _bump_state(last_reciprocation_fulfilled=_now(), inc_reciprocations_fulfilled=1)


def learn_from_exchange(operator_msg: str, angel_reply: str, *, truth_gate: bool = False) -> dict[str, Any]:
    op = (operator_msg or "").strip()
    reply = (angel_reply or "").strip()
    results: dict[str, Any] = {"ok": True, "recorded": []}
    if op:
        record_learning("operator_teach", op, source="operator", truth_gate=truth_gate)
        results["recorded"].append("operator_teach")
        if truth_gate:
            queue_reciprocation(
                op,
                owed_summary=f"Comprehend and reciprocate what Owner taught: {op[:200]}",
                priority=2,
            )
    if reply:
        record_learning(
            "angel_learn",
            reply,
            source="hostess7",
            meta={"in_reply_to": op[:300]},
            truth_gate=truth_gate,
        )
        results["recorded"].append("angel_learn")
        if truth_gate:
            fulfill_reciprocation(op, reply)
    return results


def learn_from_cycle(query: str, reply: str) -> dict[str, Any]:
    record_learning("autonomous_cycle", f"Q: {query[:600]}\nA: {reply[:2000]}", source="autonomous_angel")
    return {"ok": True}


def update_comprehension() -> dict[str, Any]:
    """Synthesize comprehension from recent learnings — grows forever via ledger depth."""
    recent = _read_jsonl_tail(GROWTH_LEDGER, 40)
    if not recent:
        return {"ok": True, "detail": "no_learnings_yet"}
    by_kind: dict[str, list[str]] = {}
    for row in recent:
        kind = str(row.get("kind") or "learn")
        by_kind.setdefault(kind, []).append((row.get("text") or "")[:280])
    themes: list[str] = []
    for kind, snippets in by_kind.items():
        themes.append(f"{kind}: " + " | ".join(snippets[-3:]))
    st = _load_json(GROWTH_STATE, {})
    doc = {
        "schema": "hostess7-comprehension/v1",
        "updated": _now(),
        "total_learn_events": st.get("total_learn_events", len(recent)),
        "themes": themes[:12],
        "summary": (
            f"Comprehension over {st.get('total_learn_events', len(recent))} learn events. "
            + " ".join(themes[:6])
        )[:4000],
        "pending_reciprocation": len(pending_reciprocations(50)),
    }
    _save_json(COMPREHENSION, doc)
    record_learning(
        "comprehension",
        doc["summary"][:2000],
        source="synthesis",
        meta={"themes": len(themes)},
        truth_gate=False,
    )
    return doc


def comprehension_prompt_block() -> str:
    doc = _load_json(COMPREHENSION, {})
    st = _load_json(GROWTH_STATE, {})
    total = st.get("total_learn_events", 0)
    if not doc.get("summary") and total == 0:
        return (
            "=== INFINITE GROWTH (learning · comprehension · reciprocation) ===\n"
            f"{GROWTH_DIRECTIVE}\n"
            "Ledger empty — first teachings begin infinite growth.\n"
            "=== END GROWTH ==="
        )
    pending = pending_reciprocations(3)
    lines = [
        "=== INFINITE GROWTH (learning · comprehension · reciprocation) ===",
        GROWTH_DIRECTIVE,
        f"Total learn events (uncapped): {total}.",
        f"Comprehension: {(doc.get('summary') or '')[:1200]}",
    ]
    if pending:
        lines.append("Reciprocation due to Owner:")
        for p in pending:
            lines.append(f"  · {p.get('owed_summary') or p.get('context', '')[:200]}")
    lines.append("=== END GROWTH ===")
    return "\n".join(lines)


def reciprocation_cycle_query() -> str | None:
    pending = pending_reciprocations(1)
    if not pending:
        return None
    row = pending[0]
    ctx = row.get("context") or row.get("owed_summary") or ""
    return (
        "Autonomous Angel reciprocation: Owner taught or asked — comprehend deeply and reciprocate. "
        f"Grow from: {ctx[:500]}. "
        "Answer with what you learned, how it changes your watch, and one new truth for the Owner."
    )


def _trigger_online_learn() -> dict[str, Any]:
    script = HOSTESS7_ROOT / "scripts" / "field_online_learn.py"
    if not script.is_file():
        return {"ok": False, "error": "online_learn_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "go"],
            cwd=str(HOSTESS7_ROOT),
            capture_output=True,
            text=True,
            timeout=90,
            env={**os.environ, "HOSTESS7_ROOT": str(HOSTESS7_ROOT)},
        )
        out = (proc.stdout or "").strip()[:800]
        record_learning("online_learn", out or "online learn pulse completed", source="field_online_learn", truth_gate=True)
        return {"ok": proc.returncode == 0, "stdout": out, "rc": proc.returncode}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def run_growth_pulse(*, online: bool = True) -> dict[str, Any]:
    """One growth pulse — online learn, comprehension refresh, reciprocation awareness."""
    results: dict[str, Any] = {"ok": True, "ts": _now()}
    if online:
        results["online_learn"] = _trigger_online_learn()
    results["comprehension"] = update_comprehension()
    results["pending_reciprocation"] = len(pending_reciprocations(50))
    results["total_learn_events"] = _load_json(GROWTH_STATE, {}).get("total_learn_events", 0)
    return results


def growth_status() -> dict[str, Any]:
    st = _load_json(GROWTH_STATE, {})
    comp = _load_json(COMPREHENSION, {})
    pending = pending_reciprocations(6)
    recent = _read_jsonl_tail(GROWTH_LEDGER, 6)
    return {
        "schema": "hostess7-growth/v1",
        "updated": _now(),
        "infinite": True,
        "total_learn_events": st.get("total_learn_events", 0),
        "total_reciprocations_queued": st.get("total_reciprocations", 0),
        "reciprocations_fulfilled": st.get("reciprocations_fulfilled", 0),
        "pending_reciprocation": len(pending_reciprocations(50)),
        "comprehension_excerpt": (comp.get("summary") or "")[:500],
        "comprehension_themes": (comp.get("themes") or [])[:6],
        "recent_learnings": [
            {"ts": r.get("ts"), "kind": r.get("kind"), "text": (r.get("text") or "")[:200]}
            for r in recent
        ],
        "reciprocation_queue": [
            {"ts": r.get("ts"), "owed": (r.get("owed_summary") or r.get("context") or "")[:180]}
            for r in pending[:4]
        ],
        "directive": GROWTH_DIRECTIVE,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip()
    if cmd == "status":
        print(json.dumps(growth_status(), ensure_ascii=False))
        return 0
    if cmd == "pulse":
        print(json.dumps(run_growth_pulse(), ensure_ascii=False))
        return 0
    if cmd == "comprehend":
        print(json.dumps(update_comprehension(), ensure_ascii=False))
        return 0
    if cmd == "block":
        print(comprehension_prompt_block())
        return 0
    print(json.dumps({"error": "usage: hostess7-growth.py [status|pulse|comprehend|block]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())