#!/usr/bin/env pythong
"""Hostess 7 muscle memory — procedural operator habits (nav, shortcuts, imports, sequences)."""
from __future__ import annotations

import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ENABLED = os.environ.get("NEXUS_HOSTESS7_MUSCLE_MEMORY", "1") == "1"

_MUSCLE_KEYS = (
    "muscle memory", "muscle-memory", "procedural memory", "operator habit",
    "browser habit", "browser habits", "navigation habit", "my habits",
    "what do i usually", "what sites do i", "remember my shortcuts", "habit recall",
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



def _install_root() -> Path:
    for candidate in (
        Path(os.environ.get("NEXUS_INSTALL_ROOT", "")),
        Path(__file__).resolve().parent.parent,
        Path(os.environ.get("SG_ROOT", "")) / "NewLatest",
    ):
        if candidate and (candidate / "data" / "hostess7-muscle-memory-doctrine.json").is_file():
            return candidate
    return Path(__file__).resolve().parent.parent


INSTALL = _install_root()
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "hostess7-muscle-memory-doctrine.json"
STORE = STATE / "hostess7-muscle-memory.json"
PANEL = STATE / "hostess7-muscle-memory-panel.json"
RUNTIME = STATE / "hostess7-muscle-memory-runtime.json"
LEDGER = STATE / "hostess7-muscle-memory-ledger.jsonl"
NAV_LOG = STATE / "queen-browser-nav.jsonl"


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {"schema": "hostess7-muscle-memory-doctrine/v1", "tiers": {}})


def _tier_for_count(count: int) -> str:
    tiers = _doctrine().get("tiers") or {}
    order = ("reflex", "habit", "forming", "trace")
    best = "trace"
    for tid in order:
        spec = tiers.get(tid) or {}
        if count >= int(spec.get("min_count") or 1):
            return tid
    return best


def _parse_ts(ts: str) -> datetime:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


def _recency_factor(last_seen: str) -> float:
    half_life = float(_doctrine().get("recency_half_life_days") or 14)
    age_days = max(0.0, (_parse_ts(_now()) - _parse_ts(last_seen)).total_seconds() / 86400.0)
    return math.pow(0.5, age_days / max(half_life, 0.5))


def _strength(count: int, last_seen: str) -> float:
    tiers = _doctrine().get("tiers") or {}
    habit_floor = int((tiers.get("habit") or {}).get("min_count") or 8)
    base = min(1.0, count / max(habit_floor, 1))
    return round(min(1.0, base * (0.55 + 0.45 * _recency_factor(last_seen))), 4)


def _normalize_host(url: str) -> str:
    try:
        host = (urlparse(url).hostname or "").lower().strip()
        if host.startswith("www."):
            host = host[4:]
        return host or "local"
    except Exception:
        return "local"


def _pattern_id(kind: str, key: str) -> str:
    key = re.sub(r"\s+", " ", (key or "").strip().lower())[:240]
    return f"{kind}:{key}"


def load_store() -> dict[str, Any]:
    doc = _load(STORE, {})
    if doc.get("patterns") is not None:
        doc.setdefault("rooms", {})
        doc.setdefault("sequences", {})
        doc.setdefault("recent_actions", [])
        return doc
    return {
        "schema": "hostess7-muscle-memory/v1",
        "updated": _now(),
        "patterns": {},
        "sequences": {},
        "recent_actions": [],
        "rooms": {},
    }


def _room_id(track_id: str) -> str:
    prefix = (_doctrine().get("rooms") or {}).get("room_prefix") or "room:understanding"
    tid = re.sub(r"[^a-z0-9_]+", "_", (track_id or "").strip().lower())
    return f"{prefix}:{tid}"


def _track_fully_learned(track: dict[str, Any]) -> bool:
    if not track:
        return False
    if track.get("mastered"):
        return True
    score = float(track.get("score") or 0)
    if score > 1:
        score /= 100.0
    min_lock = float((_doctrine().get("rooms") or {}).get("min_lock_score") or 0.92)
    level = str(track.get("level") or "").lower()
    fully_levels = (_doctrine().get("rooms") or {}).get("fully_levels") or ["mastered", "fluent", "complete"]
    if level in fully_levels and score >= min_lock and (track.get("complete") or track.get("fluent")):
        return True
    return bool(track.get("complete") and track.get("fluent") and score >= min_lock)


def _procedures_for_track(track_id: str, label: str) -> list[dict[str, str]]:
    lid = label or track_id
    return [
        {"step": "recall", "pattern": f"understanding:{track_id}"},
        {"step": "assist", "pattern": f"Hostess 7 applies sealed procedure for {lid}"},
        {"step": "verify", "pattern": f"truth-gate before adapt on {track_id}"},
    ]


def create_room_from_understanding(
    track_id: str,
    *,
    label: str = "",
    level: str = "pending",
    score: float = 0.0,
    source: str = "training",
    lock: bool | None = None,
) -> dict[str, Any]:
    if not ENABLED or not track_id:
        return {"ok": False, "error": "disabled_or_empty_track"}
    doc = load_store()
    rooms = doc.setdefault("rooms", {})
    rid = _room_id(track_id)
    existing = rooms.get(rid) or {}
    if existing.get("locked"):
        return {"ok": True, "room": existing, "unchanged": True, "reason": "room_locked"}

    track_stub = {
        "mastered": level == "mastered",
        "complete": level in ("complete", "mastered", "fluent"),
        "fluent": level in ("fluent", "mastered"),
        "level": level,
        "score": score,
    }
    fully = _track_fully_learned(track_stub)
    should_lock = lock if lock is not None else fully

    row = {
        "id": rid,
        "kind": "understanding",
        "track_id": track_id,
        "label": label or track_id,
        "understanding_level": level,
        "score": round(float(score), 4),
        "fully_learned": fully,
        "locked": bool(should_lock and fully),
        "created_at": existing.get("created_at") or _now(),
        "updated": _now(),
        "source": source,
        "procedures": _procedures_for_track(track_id, label or track_id),
    }
    if row["locked"]:
        row["locked_at"] = existing.get("locked_at") or _now()
        row["sealed"] = True
    rooms[rid] = row
    save_store(doc)
    _append_ledger({
        "ts": _now(),
        "event": "room_create" if not existing else "room_update",
        "room_id": rid,
        "track_id": track_id,
        "locked": row["locked"],
        "fully_learned": fully,
    })
    return {"ok": True, "room": row, "locked": row["locked"]}


def lock_room(track_id: str) -> dict[str, Any]:
    doc = load_store()
    rooms = doc.get("rooms") or {}
    rid = _room_id(track_id)
    room = rooms.get(rid)
    if not room:
        return {"ok": False, "error": "room_missing", "room_id": rid}
    if room.get("locked"):
        return {"ok": True, "room": room, "unchanged": True}
    if not room.get("fully_learned"):
        return {"ok": False, "error": "not_fully_learned", "room_id": rid}
    room["locked"] = True
    room["locked_at"] = _now()
    room["sealed"] = True
    room["updated"] = _now()
    rooms[rid] = room
    doc["rooms"] = rooms
    save_store(doc)
    _append_ledger({"ts": _now(), "event": "room_lock", "room_id": rid, "track_id": track_id})
    return {"ok": True, "room": room}


def list_rooms(*, locked_only: bool = False) -> list[dict[str, Any]]:
    rooms = list((load_store().get("rooms") or {}).values())
    if locked_only:
        rooms = [r for r in rooms if r.get("locked")]
    rooms.sort(key=lambda r: (not r.get("locked"), -float(r.get("score") or 0), r.get("label") or ""))
    return rooms


def sync_understandings_from_training(tracks: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create/update muscle memory rooms from training track understandings; lock when fully learned."""
    if tracks is None:
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("h7train", INSTALL / "lib" / "hostess7-training.py")
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                tracks = (mod.assess_all() or {}).get("tracks") or {}
        except Exception:
            tracks = {}
    created = 0
    updated = 0
    locked = 0
    rooms_out: list[dict[str, Any]] = []
    for tid, track in (tracks or {}).items():
        if not isinstance(track, dict):
            continue
        score = float(track.get("score") or 0)
        if score > 1:
            score /= 100.0
        out = create_room_from_understanding(
            str(tid),
            label=str(track.get("label") or tid),
            level=str(track.get("level") or "pending"),
            score=score,
            source="training",
        )
        if not out.get("ok"):
            continue
        room = out.get("room") or {}
        rooms_out.append(room)
        if out.get("unchanged"):
            if room.get("locked"):
                locked += 1
            continue
        if room.get("created_at") == room.get("updated"):
            created += 1
        else:
            updated += 1
        if room.get("locked"):
            locked += 1
    return {
        "ok": True,
        "schema": "hostess7-muscle-memory-sync/v1",
        "created": created,
        "updated": updated,
        "locked": locked,
        "rooms_total": len(list_rooms()),
        "rooms_locked": len(list_rooms(locked_only=True)),
        "rooms": list_rooms(),
    }


def save_store(doc: dict[str, Any]) -> None:
    doc["schema"] = "hostess7-muscle-memory/v1"
    doc["updated"] = _now()
    _save(STORE, doc)


def _touch_sequence(doc: dict[str, Any], kind: str, key: str) -> None:
    window = int(_doctrine().get("sequence_window") or 8)
    recent = list(doc.get("recent_actions") or [])
    recent.append({"kind": kind, "key": key, "ts": _now()})
    doc["recent_actions"] = recent[-window:]
    if len(recent) < 3:
        return
    tail = recent[-3:]
    seq_key = "→".join(f"{r['kind']}:{r['key']}" for r in tail)
    sequences = doc.setdefault("sequences", {})
    row = sequences.get(seq_key) or {
        "steps": [{"kind": r["kind"], "key": r["key"]} for r in tail],
        "count": 0,
        "first_seen": _now(),
        "last_seen": _now(),
    }
    row["count"] = int(row.get("count") or 0) + 1
    row["last_seen"] = _now()
    row["tier"] = _tier_for_count(int(row["count"]))
    row["strength"] = _strength(int(row["count"]), row["last_seen"])
    sequences[seq_key] = row


def record(
    kind: str,
    key: str,
    *,
    url: str = "",
    source: str = "operator",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not ENABLED:
        return {"ok": False, "error": "disabled"}
    kind = (kind or "command").strip().lower()
    key = (key or "").strip()
    if not key:
        return {"ok": False, "error": "empty_key"}

    doc = load_store()
    pid = _pattern_id(kind, key)
    patterns = doc.setdefault("patterns", {})
    row = patterns.get(pid) or {
        "id": pid,
        "kind": kind,
        "key": key,
        "url": url or "",
        "host": _normalize_host(url) if url else key.split(":")[0][:80],
        "count": 0,
        "first_seen": _now(),
        "last_seen": _now(),
        "sources": [],
    }
    row["count"] = int(row.get("count") or 0) + 1
    row["last_seen"] = _now()
    if url:
        row["url"] = url
        row["host"] = _normalize_host(url)
    srcs = list(row.get("sources") or [])
    if source and source not in srcs:
        srcs.append(source)
        row["sources"] = srcs[-6:]
    if meta:
        row["meta"] = {**(row.get("meta") or {}), **meta}
    row["tier"] = _tier_for_count(int(row["count"]))
    row["strength"] = _strength(int(row["count"]), row["last_seen"])
    patterns[pid] = row
    _touch_sequence(doc, kind, key)
    save_store(doc)
    _append_ledger({"ts": _now(), "event": "record", "kind": kind, "key": key, "source": source, "tier": row["tier"]})
    return {"ok": True, "pattern": row}


def record_nav(url: str, *, action: str = "navigate", source: str = "queen-browser", meta: dict[str, Any] | None = None) -> dict[str, Any]:
    host = _normalize_host(url)
    return record("navigate", host, url=url, source=source, meta={"action": action, **(meta or {})})


def record_shortcut(combo: str, *, context: str = "", source: str = "queen-os") -> dict[str, Any]:
    key = combo.strip().lower()
    if context:
        key = f"{key}@{context.strip().lower()[:80]}"
    return record("shortcut", key, source=source, meta={"combo": combo, "context": context})


def ingest_nav_log(*, limit: int = 400) -> dict[str, Any]:
    if not NAV_LOG.is_file():
        return {"ok": True, "ingested": 0, "reason": "nav_log_missing"}
    ingested = 0
    try:
        lines = NAV_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = str(row.get("url") or "").strip()
            if not url:
                continue
            out = record_nav(url, action=str(row.get("action") or "navigate"), source="nav-log")
            if out.get("ok"):
                ingested += 1
    except OSError as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "ingested": ingested, "metrics": metrics()}


def recall(*, limit: int = 12, kind: str = "") -> list[dict[str, Any]]:
    doc = load_store()
    patterns = list((doc.get("patterns") or {}).values())
    if kind:
        patterns = [p for p in patterns if p.get("kind") == kind]
    patterns.sort(key=lambda p: (float(p.get("strength") or 0), int(p.get("count") or 0)), reverse=True)
    return patterns[: max(1, limit)]


def suggest(*, host: str = "", kind: str = "", partial: str = "", limit: int = 6) -> list[dict[str, Any]]:
    host = (host or "").lower().strip()
    partial = (partial or "").lower().strip()
    kind = (kind or "").strip().lower()
    hits: list[tuple[float, dict[str, Any]]] = []
    for row in recall(limit=96):
        if kind and row.get("kind") != kind:
            continue
        key = str(row.get("key") or "").lower()
        url = str(row.get("url") or "").lower()
        score = float(row.get("strength") or 0)
        if host and host not in key and host not in url:
            continue
        if partial and partial not in key and partial not in url:
            continue
        if host and host in key:
            score += 0.15
        hits.append((score, row))
    hits.sort(key=lambda x: x[0], reverse=True)
    return [row for _, row in hits[: max(1, limit)]]


def metrics() -> dict[str, Any]:
    doc = load_store()
    patterns = list((doc.get("patterns") or {}).values())
    sequences = list((doc.get("sequences") or {}).values())
    tier_counts = {"trace": 0, "forming": 0, "habit": 0, "reflex": 0}
    for p in patterns:
        tier_counts[str(p.get("tier") or "trace")] = tier_counts.get(str(p.get("tier") or "trace"), 0) + 1
    strengths = [float(p.get("strength") or 0) for p in patterns] or [0.0]
    strength_score = round(sum(strengths) / len(strengths), 4)
    habit_count = tier_counts.get("habit", 0) + tier_counts.get("reflex", 0)
    reflex_count = tier_counts.get("reflex", 0)
    if reflex_count >= 1:
        tier = "reflex"
    elif habit_count >= 3:
        tier = "habit"
    elif tier_counts.get("forming", 0) >= 2:
        tier = "forming"
    elif patterns:
        tier = "trace"
    else:
        tier = "pending"
    return {
        "patterns_total": len(patterns),
        "sequences_total": len(sequences),
        "tier_counts": tier_counts,
        "habit_count": habit_count,
        "reflex_count": reflex_count,
        "strength_score": strength_score,
        "tier": tier,
        "top_hosts": [p.get("host") for p in recall(limit=5, kind="navigate")],
    }


def assess_track() -> dict[str, Any]:
    m = metrics()
    doc = _doctrine()
    complete_floor = doc.get("complete_floor") or {}
    mastered_floor = doc.get("mastered_floor") or {}
    score = float(m.get("strength_score") or 0)
    habit_n = int(m.get("habit_count") or 0)
    reflex_n = int(m.get("reflex_count") or 0)
    complete = (
        habit_n >= int(complete_floor.get("habit_patterns") or 3)
        or score >= float(complete_floor.get("strength_score") or 0.72)
    )
    mastered = (
        reflex_n >= int(mastered_floor.get("reflex_patterns") or 1)
        or (
            habit_n >= int(mastered_floor.get("habit_patterns") or 8)
            and score >= float(mastered_floor.get("strength_score") or 0.88)
        )
    )
    return {
        "track": "muscle_memory",
        "label": "Muscle memory",
        "score": score,
        "complete": complete,
        "mastered": mastered,
        "fluent": complete,
        "tier": m.get("tier"),
        "patterns_total": m.get("patterns_total"),
        "habit_count": habit_n,
        "reflex_count": reflex_n,
        "top_hosts": m.get("top_hosts"),
        "pass_rate": round(score * 100, 1),
    }


def build_panel(*, write: bool = True, sync_training: bool = True) -> dict[str, Any]:
    m = metrics()
    assess = assess_track()
    room_doc = (_doctrine().get("rooms") or {})
    sync_result = sync_understandings_from_training() if sync_training else {}
    rooms = list_rooms()
    doc = {
        "schema": "hostess7-muscle-memory/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "motto": _doctrine().get("motto"),
        "definition": _doctrine().get("definition"),
        "rooms_motto": room_doc.get("motto"),
        "tier": m.get("tier"),
        "strength_score": m.get("strength_score"),
        "patterns_total": m.get("patterns_total"),
        "habit_count": m.get("habit_count"),
        "reflex_count": m.get("reflex_count"),
        "tier_counts": m.get("tier_counts"),
        "top_habits": recall(limit=8),
        "top_sequences": sorted(
            (load_store().get("sequences") or {}).values(),
            key=lambda s: float(s.get("strength") or 0),
            reverse=True,
        )[:5],
        "rooms": rooms,
        "rooms_total": len(rooms),
        "rooms_locked": sum(1 for r in rooms if r.get("locked")),
        "rooms_fully": sum(1 for r in rooms if r.get("fully_learned")),
        "last_sync": sync_result if sync_training else {},
        "complete": assess.get("complete"),
        "mastered": assess.get("mastered"),
        "fluent": assess.get("fluent"),
    }
    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "hostess7-muscle-memory-runtime/v1",
            "updated": doc["updated"],
            "tier": doc["tier"],
            "strength_score": doc["strength_score"],
        })
    return doc


def explain_muscle_memory(query: str) -> str | None:
    low = (query or "").strip().lower()
    if not any(k in low for k in _MUSCLE_KEYS):
        return None
    m = metrics()
    habits = recall(limit=5, kind="navigate")
    lines = [
        "Muscle memory is procedural recall — I watch what you repeat locally (navigation, shortcuts, imports) and strengthen patterns into habits.",
        f"Right now I hold {m.get('patterns_total', 0)} patterns — {m.get('habit_count', 0)} at habit/reflex tier, strength {float(m.get('strength_score') or 0):.0%}.",
    ]
    if habits:
        hosts = ", ".join(str(h.get("host") or h.get("key")) for h in habits[:4])
        lines.append(f"Your strongest navigation habits: {hosts}.")
    else:
        lines.append("No strong habits yet — browse, import, and use shortcuts; I learn from repetition on this machine only.")
    rooms = list_rooms()
    locked = [r for r in rooms if r.get("locked")]
    if locked:
        names = ", ".join(str(r.get("label") or r.get("track_id")) for r in locked[:5])
        lines.append(f"Locked understanding rooms ({len(locked)}): {names} — fully learned tasks sealed inside.")
    elif rooms:
        lines.append(f"{len(rooms)} understanding room(s) forming — complete a training track fully to lock a room.")
    lines.append("Nothing leaves loopback. You stay authoritative; I assist recall.")
    return "\n".join(lines)


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}
    if action == "record":
        return record(
            str(body.get("kind") or "command"),
            str(body.get("key") or body.get("label") or ""),
            url=str(body.get("url") or ""),
            source=str(body.get("source") or "operator"),
            meta=body.get("meta") if isinstance(body.get("meta"), dict) else None,
        )
    if action in ("record_nav", "nav"):
        return record_nav(
            str(body.get("url") or ""),
            action=str(body.get("browser_action") or body.get("nav_action") or "navigate"),
            source=str(body.get("source") or "queen-browser"),
        )
    if action == "record_shortcut":
        return record_shortcut(
            str(body.get("combo") or body.get("key") or ""),
            context=str(body.get("context") or ""),
            source=str(body.get("source") or "queen-os"),
        )
    if action in ("ingest_nav", "ingest"):
        return ingest_nav_log(limit=int(body.get("limit") or 400))
    if action == "recall":
        return {"ok": True, "patterns": recall(limit=int(body.get("limit") or 12), kind=str(body.get("kind") or ""))}
    if action == "suggest":
        return {
            "ok": True,
            "suggestions": suggest(
                host=str(body.get("host") or ""),
                kind=str(body.get("kind") or ""),
                partial=str(body.get("partial") or body.get("q") or ""),
                limit=int(body.get("limit") or 6),
            ),
        }
    if action == "assess":
        return {"ok": True, **assess_track()}
    if action == "explain":
        reply = explain_muscle_memory(str(body.get("query") or body.get("text") or ""))
        return {"ok": bool(reply), "reply": reply or ""}
    if action in ("sync_training", "sync_understandings", "sync"):
        tracks = body.get("tracks") if isinstance(body.get("tracks"), dict) else None
        return sync_understandings_from_training(tracks)
    if action == "create_room":
        return create_room_from_understanding(
            str(body.get("track_id") or body.get("track") or ""),
            label=str(body.get("label") or ""),
            level=str(body.get("level") or "pending"),
            score=float(body.get("score") or 0),
            lock=body.get("lock"),
        )
    if action == "lock_room":
        return lock_room(str(body.get("track_id") or body.get("track") or ""))
    if action == "list_rooms":
        return {
            "ok": True,
            "rooms": list_rooms(locked_only=bool(body.get("locked_only"))),
            "rooms_total": len(list_rooms()),
            "rooms_locked": len(list_rooms(locked_only=True)),
        }
    return {"ok": False, "error": "unknown_action", "actions": [
        "status", "panel", "record", "record_nav", "record_shortcut",
        "ingest_nav", "recall", "suggest", "assess", "explain",
        "sync_training", "create_room", "lock_room", "list_rooms",
    ]}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(build_panel(write=False), ensure_ascii=False))
        return 0
    if cmd == "panel":
        print(json.dumps(build_panel(write=True), ensure_ascii=False))
        return 0
    if cmd == "ingest":
        print(json.dumps(ingest_nav_log(), ensure_ascii=False))
        return 0
    if cmd == "assess":
        print(json.dumps(assess_track(), ensure_ascii=False))
        return 0
    if cmd == "sync":
        print(json.dumps(sync_understandings_from_training(), ensure_ascii=False))
        return 0
    if cmd == "rooms":
        print(json.dumps({"ok": True, "rooms": list_rooms()}, ensure_ascii=False))
        return 0
    if len(sys.argv) > 2 and cmd == "explain":
        print(json.dumps({"ok": True, "reply": explain_muscle_memory(" ".join(sys.argv[2:]))}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-muscle-memory.py [json|panel|ingest|assess|dispatch|explain TEXT]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())