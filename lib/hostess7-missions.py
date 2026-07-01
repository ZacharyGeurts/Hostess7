#!/usr/bin/env pythong
"""Hostess 7 dynamic missions — KILL priority (locational/amassed) + plans + communications."""
from __future__ import annotations

import importlib.util
import json
import os
import re
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-missions-doctrine.json"
PANEL = STATE / "hostess7-missions-panel.json"
TARGETS_REG = STATE / "hostess7-targets-registry.json"
TASKLIST = STATE / "hostess7-tasklist.json"
INBOX = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "agents7" / "inbox.jsonl"
UPDATE_ADVISORY = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "update_advisory.json"
SELF_BRIEF = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "self_update_brief.json"

AMASSED_RE = re.compile(r"\b(amass|cluster|massed|concentrat|swarm|botnet|campaign)\b", re.I)


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location("sovereign_clock_missions", _LIB / "sovereign-clock.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "utc_z"):
                return mod.utc_z()
    except Exception:
        pass
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default if default is not None else {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception:
        return None
    return mod


def _has_location(row: dict[str, Any]) -> bool:
    geo = row.get("geo")
    if isinstance(geo, dict):
        if geo.get("lat") is not None and geo.get("lon") is not None:
            return True
        if geo.get("latitude") is not None and geo.get("longitude") is not None:
            return True
        if any(geo.get(k) for k in ("city", "region", "country", "census_tract", "place")):
            return True
    gov = row.get("government") if isinstance(row.get("government"), dict) else {}
    if isinstance(gov.get("geo"), dict) and any(gov["geo"].values()):
        return True
    if gov.get("location"):
        return True
    census = gov.get("census") if isinstance(gov.get("census"), dict) else {}
    if census.get("hits"):
        return True
    for key in ("gov_dossiers", "human_dossier", "angel"):
        hits = gov.get(key)
        if isinstance(hits, list) and hits:
            return True
    if row.get("ip") and gov.get("country"):
        return True
    meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
    if isinstance(meta.get("geo"), dict) and any(meta["geo"].values()):
        return True
    if meta.get("location"):
        return True
    return False


def _is_amassed(row: dict[str, Any], *, kill_count: int) -> bool:
    if kill_count >= 2:
        return True
    score = float(row.get("final_threat_score") or row.get("threat_score") or 0)
    if score >= 0.85:
        return True
    blob = f"{row.get('subject', '')} {row.get('counsel', '')} {row.get('lane', '')}"
    if AMASSED_RE.search(blob):
        return True
    return False


def _mission_row(
    *,
    lane: str,
    rank: int,
    title: str,
    detail: str = "",
    source: str = "",
    mechanism: str = "",
    priority: int = 5,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "lane": lane,
        "rank": rank,
        "priority": priority,
        "title": title,
        "detail": (detail or "")[:500],
        "source": source,
        "mechanism": mechanism,
        "meta": meta or {},
    }


def _kill_missions(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active_kill = [
        t for t in targets
        if isinstance(t, dict)
        and str(t.get("mechanism") or t.get("TARGET") or "").upper() == "KILL"
        and t.get("status") in ("active", None, "dead")
    ]
    kill_count = len([t for t in active_kill if t.get("status") == "active"])
    out: list[dict[str, Any]] = []

    for row in active_kill:
        if row.get("status") != "active":
            continue
        loc = _has_location(row)
        amassed = _is_amassed(row, kill_count=kill_count)
        if loc:
            lane, rank, pri = "kill_locational", 0, 0
        elif amassed:
            lane, rank, pri = "kill_amassed", 1, 0
        else:
            lane, rank, pri = "kill_other", 2, 1

        subj = str(row.get("subject") or row.get("ip") or row.get("target_id") or "KILL target")[:120]
        detail_parts = [
            f"IP: {row['ip']}" if row.get("ip") else "",
            f"Threat: {row.get('final_threat_score', row.get('threat_score', '—'))}",
            f"Status: {row.get('status', 'active')}",
        ]
        if loc:
            detail_parts.append("LOCATIONAL — priority KILL")
        if amassed:
            detail_parts.append("AMASSED — priority KILL")
        if row.get("kill_law"):
            detail_parts.append(f"Law: {row.get('kill_law')}")

        out.append(_mission_row(
            lane=lane,
            rank=rank,
            priority=pri,
            title=f"KILL — {subj}",
            detail=" · ".join(x for x in detail_parts if x),
            source="hostess7-targets",
            mechanism="KILL",
            meta={
                "target_id": row.get("target_id"),
                "ip": row.get("ip"),
                "locational": loc,
                "amassed": amassed,
                "geo": row.get("geo"),
            },
        ))

    out.sort(key=lambda m: (m["rank"], -float(m.get("meta", {}).get("threat_score") or 0)))
    return out


def _interact_monitor_missions(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in targets:
        if not isinstance(row, dict):
            continue
        mech = str(row.get("mechanism") or row.get("TARGET") or "").upper()
        if mech not in ("INTERACT", "MONITOR", "OBSERVE"):
            continue
        if row.get("status") not in ("active", None):
            continue
        subj = str(row.get("subject") or row.get("ip") or "target")[:100]
        out.append(_mission_row(
            lane="interact_monitor",
            rank=3,
            priority=2,
            title=f"{mech} — {subj}",
            detail=str(row.get("counsel") or "")[:200],
            source="hostess7-targets",
            mechanism=mech,
            meta={"target_id": row.get("target_id"), "ip": row.get("ip")},
        ))
    return out


def _tasklist_missions() -> list[dict[str, Any]]:
    tl = _import_mod("tasklist", "lib/hostess7-tasklist.py")
    if not tl or not hasattr(tl, "list_open"):
        doc = _load(TASKLIST, {"tasks": []})
        open_tasks = [t for t in doc.get("tasks") or [] if t.get("status") in ("pending", "in_progress")]
    else:
        open_tasks = tl.list_open(limit=40)

    out: list[dict[str, Any]] = []
    for t in open_tasks:
        pri = int(t.get("priority") or 5)
        out.append(_mission_row(
            lane="tasklist",
            rank=5,
            priority=pri,
            title=str(t.get("title") or t.get("id") or "task"),
            detail=str(t.get("detail") or "")[:300],
            source="hostess7-tasklist",
            mechanism="TASK",
            meta={
                "task_id": t.get("id"),
                "status": t.get("status"),
                "tags": t.get("tags") or [],
            },
        ))
    out.sort(key=lambda m: m["priority"])
    return out


def _plan_missions() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    advisory = _load(UPDATE_ADVISORY, {})
    updates = advisory.get("updates") or []
    for item in updates[:12]:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "plan")
        if action in ("skip", "defer", "done"):
            continue
        out.append(_mission_row(
            lane="plans",
            rank=4,
            priority=int(item.get("priority") or 3) if str(item.get("priority", "")).isdigit() else 3,
            title=f"Plan — {item.get('id', 'update')}",
            detail=f"{action} · truth={item.get('truth_score', '—')}% · {str(item.get('reason') or '')[:180]}",
            source="update_advisory",
            mechanism="PLAN",
            meta={"advisory_id": item.get("id"), "priority_label": item.get("priority")},
        ))

    brief = _load(SELF_BRIEF, {})
    headline = str(brief.get("headline") or brief.get("summary") or "").strip()
    if headline:
        out.insert(0, _mission_row(
            lane="plans",
            rank=4,
            priority=2,
            title=f"Self brief — {headline[:80]}",
            detail=str(brief.get("body") or brief.get("note") or "")[:300],
            source="self_update_brief",
            mechanism="PLAN",
        ))

    try:
        reach = _import_mod("reach", "Hostess7/scripts/field_reach.py")
        if reach and hasattr(reach, "self_update_steps"):
            steps = reach.self_update_steps(apply=False)
            for step in (steps or [])[:8]:
                if not isinstance(step, dict):
                    continue
                out.append(_mission_row(
                    lane="plans",
                    rank=4,
                    priority=4,
                    title=f"Reach — {step.get('id', step.get('label', 'step'))}",
                    detail=str(step.get("detail") or step.get("action") or "")[:200],
                    source="field_reach",
                    mechanism="PLAN",
                ))
    except Exception:
        pass

    return out


def _positional_identify_missions() -> list[dict[str, Any]]:
    pos = _import_mod("positional_awareness", "lib/hostess7-positional-awareness.py")
    if not pos or not hasattr(pos, "gather_awareness"):
        return []
    try:
        aw = pos.gather_awareness()
        return list(aw.get("identify_missions") or [])
    except Exception:
        return []


def _communication_missions(*, limit: int = 16) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not INBOX.is_file():
        return rows
    try:
        lines = INBOX.read_text(encoding="utf-8").splitlines()
    except OSError:
        return rows

    for line in lines[-80:]:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = str(
            row.get("message")
            or row.get("query")
            or row.get("content")
            or row.get("text")
            or ""
        ).strip()
        if not msg:
            continue
        event = str(row.get("event") or row.get("schema") or "communique")
        if event in ("task_completed",):
            continue
        rows.append(_mission_row(
            lane="communications",
            rank=6,
            priority=3 if event == "owner_message" else 5,
            title=f"Comm — {event}"[:80],
            detail=msg[:320],
            source="inbox",
            mechanism="COMM",
            meta={
                "event": event,
                "from": row.get("from") or row.get("operator"),
                "ts": row.get("ts"),
            },
        ))

    return rows[-limit:]


def build_missions(*, include_dead_kill: bool = False) -> dict[str, Any]:
    reg = _load(TARGETS_REG, {"targets": {}})
    targets = list((reg.get("targets") or {}).values())
    if not include_dead_kill:
        targets = [t for t in targets if t.get("status") != "dead" or str(t.get("mechanism", "")).upper() != "KILL"]

    missions: list[dict[str, Any]] = []
    missions.extend(_kill_missions(targets))
    missions.extend(_positional_identify_missions())
    missions.extend(_interact_monitor_missions(targets))
    missions.extend(_plan_missions())
    missions.extend(_tasklist_missions())
    missions.extend(_communication_missions())

    missions.sort(key=lambda m: (m.get("rank", 9), m.get("priority", 9), m.get("title", "")))

    by_lane: dict[str, list[dict[str, Any]]] = {}
    for m in missions:
        by_lane.setdefault(m["lane"], []).append(m)

    kill_priority = [m for m in missions if m["lane"].startswith("kill_")]
    positional_priority = [m for m in missions if m["lane"] == "positional_identify"]
    other = [
        m for m in missions
        if not m["lane"].startswith("kill_") and m["lane"] != "positional_identify"
    ]

    return {
        "schema": "hostess7-missions/v1",
        "updated": _now(),
        "ok": True,
        "motto": "KILL first when locational or amassed — IDENTIFY positionals P1 until familiar — then plans, tasks, communications.",
        "mission_count": len(missions),
        "kill_count": len(kill_priority),
        "kill_locational_count": len(by_lane.get("kill_locational", [])),
        "kill_amassed_count": len(by_lane.get("kill_amassed", [])),
        "positional_identify_count": len(by_lane.get("positional_identify", [])),
        "missions": missions,
        "by_lane": {k: len(v) for k, v in by_lane.items()},
        "ordered": {
            "kill_priority": kill_priority,
            "positional_identify": positional_priority,
            "other_missions": other,
        },
    }


def format_output(doc: dict[str, Any] | None = None) -> str:
    doc = doc or build_missions()
    lines = [
        "=== Hostess 7 — Assigned Missions (dynamic) ===",
        f"Updated: {doc.get('updated', '—')}",
        f"Total: {doc.get('mission_count', 0)} · KILL priority: {doc.get('kill_count', 0)}",
        "",
        "— KILL PRIORITY (locational · amassed · terminal) —",
    ]
    kill = (doc.get("ordered") or {}).get("kill_priority") or []
    if not kill:
        lines.append("  (no active KILL missions)")
    for m in kill:
        flags = []
        meta = m.get("meta") or {}
        if meta.get("locational"):
            flags.append("LOCATIONAL")
        if meta.get("amassed"):
            flags.append("AMASSED")
        flag = f" [{' · '.join(flags)}]" if flags else ""
        lines.append(f"  [P{m.get('priority', 0)}] {m.get('title')}{flag}")
        if m.get("detail"):
            lines.append(f"       {m['detail'][:200]}")

    positional = (doc.get("ordered") or {}).get("positional_identify") or []
    if positional:
        lines.extend(["", "— POSITIONAL IDENTIFY (P1 until familiar) —"])
        for m in positional[:16]:
            lines.append(f"  [P{m.get('priority', 1)}] {m.get('title')}")
            if m.get("detail"):
                lines.append(f"       {m['detail'][:180]}")

    lines.extend(["", "— Other missions (plans · tasklist · communications) —"])
    other = (doc.get("ordered") or {}).get("other_missions") or []
    if not other:
        lines.append("  (none)")
    for m in other:
        lines.append(f"  [{m.get('lane')}] {m.get('title')}")
        if m.get("detail"):
            lines.append(f"       {m['detail'][:160]}")

    lines.append("")
    lines.append("Doctrine: data/hostess7-missions-doctrine.json")
    return "\n".join(lines)


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = build_missions()
    doc["output_text"] = format_output(doc)
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Hostess 7 dynamic missions")
    parser.add_argument("cmd", nargs="?", default="panel")
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("missions", "list", "build"):
        print(json.dumps(build_missions(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("output", "text", "report"):
        print(format_output())
        return 0
    print(json.dumps({
        "usage": "hostess7-missions.py [panel|missions|output]",
        "api": "/api/hostess7/missions",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())