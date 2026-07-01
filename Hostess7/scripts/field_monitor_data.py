#!/usr/bin/env pythong
"""Hostess7 monitor data — live snapshot of learning, agents, brain activity."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_paths import ROOT

BRAIN = ROOT / "cache" / "fieldstorage" / "brain"
SI = BRAIN / "superintel"
AGENTS7 = SI / "agents7"

AREA_KEYWORDS: dict[str, tuple[str, ...]] = {
    "prefrontal": ("update", "self", "plan", "priority", "release", "verdict", "hostess"),
    "broca": ("code", "terminal", "shell", "isa", "assembly", "field-dev"),
    "wernicke": ("legal", "law", "counsel", "english", "lexicon", "contract", "judge", "scotus", "bench", "certiorari"),
    "parietal_l": ("grep", "evidence", "architecture", "general"),
    "occipital": ("vision", "pixel", "image", "meme", "stamp", "tv", "ocr", "gfx"),
    "temporal": ("medical", "clinic", "medicine", "paper", "health"),
    "limbic": ("storage", "field", "wave", "persist", "lossless"),
    "insula": ("detective", "truth", "lie", "investigate", "corroborat"),
    "beyond": ("reach", "internet", "fetch", "github", "outside", "os "),
    "hypothalamus": ("chemistry", "synapse", "dopamine", "neuro"),
}


@dataclass
class LearningEvent:
    ts: str
    kind: str
    text: str
    area: str = "parietal_l"
    source: str = ""


@dataclass
class MonitorSnapshot:
    updated: str
    agents_running: bool
    agents_pid: int | None
    internet: bool
    storage_mb: float
    brain_mb: float
    memes_n: int
    thoughts_n: int
    outbox_n: int
    area_glow: dict[str, float] = field(default_factory=dict)
    agent_pulse: dict[str, float] = field(default_factory=dict)
    events: list[LearningEvent] = field(default_factory=list)
    appearance: str = "Unified"
    callosum_us: int = 0
    top_learn: str = ""


def _load_jsonl(path: Path, limit: int = 40) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _classify_area(text: str) -> str:
    low = text.lower()
    best = "parietal_l"
    best_score = 0
    for area, keys in AREA_KEYWORDS.items():
        score = sum(2 if k in low else 0 for k in keys)
        if score > best_score:
            best_score = score
            best = area
    return best


def _parse_ts(ts: str) -> float:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _agents_running() -> tuple[bool, int | None]:
    pid_path = AGENTS7 / "daemon.pid"
    if not pid_path.is_file():
        return False, None
    try:
        pid = int(pid_path.read_text().strip())
        import os
        os.kill(pid, 0)
        return True, pid
    except (ValueError, OSError):
        return False, None


def collect_snapshot() -> MonitorSnapshot:
    now = datetime.now(timezone.utc)
    running, pid = _agents_running()

    state: dict[str, Any] = {}
    state_path = AGENTS7 / "state.json"
    if state_path.is_file():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    storage_total = 0
    brain_total = 0
    storage_root = ROOT / "cache" / "fieldstorage"
    if storage_root.is_dir():
        for p in storage_root.rglob("*"):
            if p.is_file():
                storage_total += p.stat().st_size
                if "brain" in p.parts:
                    brain_total += p.stat().st_size

    memes_n = 0
    memes_path = BRAIN / "memes" / "manifest.json"
    if memes_path.is_file():
        try:
            memes_n = int(json.loads(memes_path.read_text()).get("downloaded", 0))
        except (OSError, json.JSONDecodeError, TypeError):
            pass

    thoughts = _load_jsonl(BRAIN / "thoughts.jsonl", 30)
    outbox = _load_jsonl(AGENTS7 / "outbox.jsonl", 20)
    transfers = _load_jsonl(BRAIN / "callosum" / "transfer.jsonl", 10)
    fetches = _load_jsonl(BRAIN / "internet" / "fetch_log.jsonl", 8)
    learn_log = _load_jsonl(BRAIN / "internet" / "learn_log.jsonl", 10)

    events: list[LearningEvent] = []
    area_glow: dict[str, float] = {a: 0.0 for a in AREA_KEYWORDS}

    for row in thoughts[-12:]:
        text = str(row.get("text", ""))[:120]
        area = _classify_area(text)
        events.append(LearningEvent(
            ts=str(row.get("ts", ""))[:19],
            kind=str(row.get("kind", "thought")),
            text=text,
            area=area,
            source="thoughts",
        ))
        area_glow[area] = min(1.0, area_glow.get(area, 0) + 0.35)

    for row in outbox[-10:]:
        q = str(row.get("query", row.get("fused_preview", "")))[:100]
        area = _classify_area(q)
        events.append(LearningEvent(
            ts=str(row.get("ts", ""))[:19],
            kind="agent",
            text=q,
            area=area,
            source="agents7",
        ))
        area_glow[area] = min(1.0, area_glow.get(area, 0) + 0.5)

    for row in fetches[-5:]:
        url = str(row.get("url", ""))[:80]
        events.append(LearningEvent(
            ts=str(row.get("ts", ""))[:19],
            kind="fetch",
            text=url,
            area="beyond",
            source="internet",
        ))
        area_glow["beyond"] = min(1.0, area_glow.get("beyond", 0) + 0.4)

    for row in learn_log[-6:]:
        kind = str(row.get("kind", "learn"))
        lane = str(row.get("lane", row.get("id", "")))
        if kind == "fetch":
            text = f"{lane}: {str(row.get('url', ''))[:60]}"
            area = "beyond"
        elif kind == "ingest":
            text = f"{lane} ingest · ok={row.get('ok', row.get('downloaded', '?'))}"
            area = _classify_area(lane)
        elif kind == "start":
            text = "Online learn pass started"
            area = "beyond"
        else:
            text = f"{kind}: {lane}"[:80]
            area = _classify_area(text)
        events.append(LearningEvent(
            ts=str(row.get("ts", ""))[:19],
            kind=kind,
            text=text,
            area=area,
            source="learn",
        ))
        area_glow[area] = min(1.0, area_glow.get(area, 0) + 0.45)

    events.sort(key=lambda e: e.ts, reverse=True)
    events = events[:18]

    agent_pulse: dict[str, float] = {}
    for ag in state.get("agents") or []:
        name = str(ag.get("name", ""))
        lane = str(ag.get("lane", ""))
        glow = 0.2
        for ev in events[:6]:
            if lane in ev.text.lower() or name.split("-")[0].lower() in ev.text.lower():
                glow = 0.9
                break
        agent_pulse[name] = glow if running else 0.1

    callosum_us = 0
    if transfers:
        last = transfers[-1]
        try:
            callosum_us = int(last.get("elapsed_us", 0))
        except (TypeError, ValueError):
            callosum_us = 0

    ws_path = BRAIN / "workspaces" / "default" / "state.json"
    appearance = "Unified"
    if ws_path.is_file():
        try:
            for ws in json.loads(ws_path.read_text()).get("areas") or []:
                appearance = str(ws)
        except json.JSONDecodeError:
            pass

    # decay idle areas slightly toward baseline
    for a in area_glow:
        if area_glow[a] < 0.15:
            area_glow[a] = 0.08

    top_learn = events[0].text[:70] if events else "Awaiting Field input..."

    return MonitorSnapshot(
        updated=now.strftime("%H:%M:%S"),
        agents_running=running,
        agents_pid=pid,
        internet=bool(state.get("internet")),
        storage_mb=storage_total / (1024 * 1024),
        brain_mb=brain_total / (1024 * 1024),
        memes_n=memes_n,
        thoughts_n=len(thoughts),
        outbox_n=len(outbox),
        area_glow=area_glow,
        agent_pulse=agent_pulse,
        events=events,
        appearance=appearance,
        callosum_us=callosum_us,
        top_learn=top_learn,
    )


def format_snapshot_text(snap: MonitorSnapshot) -> str:
    lines = [
        f"Hostess7 Monitor {snap.updated} | agents={'ON' if snap.agents_running else 'OFF'} | "
        f"brain {snap.brain_mb:.1f} MiB | memes {snap.memes_n}",
        "Learning:",
    ]
    for ev in snap.events[:8]:
        lines.append(f"  [{ev.kind}] {ev.area}: {ev.text[:60]}")
    return "\n".join(lines)