#!/usr/bin/env pythong
"""Hostess 7 self-authored training — write lessons when tracks need more."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "hostess7-training-author-doctrine.json"
AUTHORED_DIR = STATE / "hostess7-authored-training"
PANEL = STATE / "hostess7-training-author-panel.json"
LEDGER = STATE / "hostess7-training-author-ledger.jsonl"

_AUTHOR_KEYS = (
    "write training", "author training", "author material", "write material",
    "training material", "need more training", "self-authored", "self authored",
    "write my own training", "write lesson", "author lesson", "training gap",
)

_SECTIONS = ("what", "why", "how", "pitfalls", "where", "example")


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


def _mod(name: str, script: str) -> Any | None:
    py = INSTALL / "lib" / script
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _track_meta() -> dict[str, dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    out: dict[str, dict[str, Any]] = {}
    for row in doc.get("tracks") or []:
        tid = str(row.get("id") or "")
        if tid:
            out[tid] = row
    return out


def _module_blurb(module: str) -> str:
    path = INSTALL / "lib" / module
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:1200]
        m = re.search(r'"""(.*?)"""', text, re.S)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()[:320]
    except OSError:
        pass
    return ""


def _battery_gaps(track: str) -> list[str]:
    panel_path = STATE / f"hostess7-{track}-panel.json"
    if track == "g16":
        panel_path = STATE / "hostess7-g16-panel.json"
    panel = _load(panel_path, {})
    bat = panel.get("battery") or {}
    gaps: list[str] = []
    for row in bat.get("results") or []:
        if row.get("passed") is False:
            gaps.append(str(row.get("category") or row.get("id") or "battery"))
    rate = bat.get("pass_rate")
    if rate is not None and float(rate) < 85:
        gaps.append(f"battery_pass_rate_{rate}")
    return gaps


def detect_training_gaps(
    assessment: dict[str, Any] | None = None,
    *,
    track: str | None = None,
) -> list[dict[str, Any]]:
    """Find tracks that need self-authored material."""
    doc = _load(DOCTRINE, {})
    threshold = float(doc.get("gap_threshold") or 0.92)
    meta = _track_meta()

    if assessment is None:
        train = _mod("h7train", "hostess7-training.py")
        assessment = train.assess_all() if train and hasattr(train, "assess_all") else {}

    tracks = assessment.get("tracks") or {}
    gaps: list[dict[str, Any]] = []

    for tid, row in tracks.items():
        if track and tid != track:
            continue
        if tid not in meta and tid not in (
            "programming", "g16", "codecraft", "calculator",
            "biology", "engineering", "combat", "mos",
            "reality_physics", "gravity_mechanics", "thermodynamics_entropy", "field_technology",
        ):
            continue
        score = float(row.get("score") or 0)
        if score > 1.0:
            score = score / 100.0
        complete = bool(row.get("complete"))
        mastered = bool(row.get("mastered"))
        if complete and mastered:
            continue
        if complete and score >= threshold:
            continue
        battery_gaps = _battery_gaps(tid) if tid in meta else []
        if score >= threshold and not battery_gaps:
            continue
        tm = meta.get(tid, {})
        gaps.append({
            "track": tid,
            "label": row.get("label") or tm.get("label") or tid,
            "score": round(score, 4),
            "level": row.get("level") or "training",
            "complete": complete,
            "battery_gaps": battery_gaps,
            "reason": (
                f"{tid} at {round(score * 100)}% ({row.get('level')})"
                + (f" · battery gaps: {', '.join(battery_gaps[:4])}" if battery_gaps else "")
                + " — I need more training material"
            ),
        })

    gaps.sort(key=lambda g: float(g.get("score") or 0))
    return gaps


def _topic_exists(track: str, topic_id: str) -> bool:
    overlay = _load(AUTHORED_DIR / f"{track}-authored.json", {})
    for t in overlay.get("topics") or []:
        if str(t.get("id") or "") == topic_id:
            return True
    return False


def author_topic_for_gap(gap: dict[str, Any]) -> dict[str, Any]:
    """Draft one six-section lesson from live gap + doctrine."""
    track = str(gap.get("track") or "training")
    meta = _track_meta().get(track, {})
    doctrine = _load(INSTALL / "data" / str(meta.get("doctrine") or ""), {})
    motto = str(doctrine.get("motto") or doctrine.get("fluency_claim") or "").strip()
    module = str(meta.get("module") or f"hostess7-{track}.py")
    blurb = _module_blurb(module)
    score_pct = round(float(gap.get("score") or 0) * 100)
    level = str(gap.get("level") or "training")
    battery = gap.get("battery_gaps") or []
    topic_id = f"authored_{track}_{level}"

    keywords = [
        track,
        str(gap.get("label") or track),
        "authored training",
        "self-written lesson",
        level,
        "hostess7 training",
    ]
    keywords.extend(str(b) for b in battery[:3])

    what = (
        f"I authored this lesson because {track} stalled at {score_pct}% — "
        f"{str(gap.get('label') or track)} needs a drill I wrote myself."
    )
    why = gap.get("reason") or motto or "Shipped topics are not enough when field scores stall."
    how_parts = [
        f"Re-run the {track} training track and battery.",
        f"Read lib/{module} and match keywords to this authored topic.",
    ]
    if battery:
        how_parts.append(f"Focus battery categories: {', '.join(battery[:5])}.")
    if motto:
        how_parts.append(f"Doctrine: {motto[:200]}")
    how = " ".join(how_parts)
    pitfalls = (
        "Waiting for Operator to write lessons; ignoring battery failures; "
        "claiming fluent without re-running track after new material."
    )
    where = (
        f"STATE/hostess7-authored-training/{track}-authored.json · "
        f"lib/{module} · Training tab → Write material"
    )
    example = (
        f"Ask Command: author training for {track} — or Training tab Write material. "
        f"Then ask: explain {track} {level} drill."
    )
    if blurb:
        example += f" Module: {blurb[:120]}"

    return {
        "id": topic_id,
        "authored": True,
        "authored_at": _now(),
        "authored_by": "Hostess 7",
        "gap_reason": gap.get("reason"),
        "gap_score": gap.get("score"),
        "keywords": keywords,
        "what": what,
        "why": why,
        "how": how,
        "pitfalls": pitfalls,
        "where": where,
        "example": example,
    }


def save_authored_topic(track: str, topic: dict[str, Any]) -> dict[str, Any]:
    """Append topic to track overlay (atomic)."""
    AUTHORED_DIR.mkdir(parents=True, exist_ok=True)
    path = AUTHORED_DIR / f"{track}-authored.json"
    doc = _load(path, {
        "schema": "hostess7-authored-training/v1",
        "track": track,
        "topics": [],
    })
    topics = list(doc.get("topics") or [])
    tid = str(topic.get("id") or "")
    replaced = False
    for i, row in enumerate(topics):
        if str(row.get("id") or "") == tid:
            topics[i] = topic
            replaced = True
            break
    if not replaced:
        topics.append(topic)
    doc.update({
        "updated": _now(),
        "track": track,
        "topics": topics,
        "topic_count": len(topics),
    })
    _save(path, doc)
    _append_ledger({
        "ts": doc["updated"],
        "event": "author_topic",
        "track": track,
        "topic_id": tid,
        "replaced": replaced,
    })
    return doc


def list_authored_material() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    if AUTHORED_DIR.is_dir():
        for path in sorted(AUTHORED_DIR.glob("*-authored.json")):
            doc = _load(path, {})
            track = str(doc.get("track") or path.stem.replace("-authored", ""))
            for topic in doc.get("topics") or []:
                rows.append({
                    "track": track,
                    "id": topic.get("id"),
                    "authored_at": topic.get("authored_at"),
                    "gap_reason": topic.get("gap_reason"),
                    "label": topic.get("what", "")[:120],
                })
    return {
        "schema": "hostess7-authored-catalog/v1",
        "updated": _now(),
        "count": len(rows),
        "materials": rows,
    }


def build_author_panel(
    *,
    assessment: dict[str, Any] | None = None,
    gaps: list[dict[str, Any]] | None = None,
    authored: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    catalog = list_authored_material()
    return {
        "schema": "hostess7-training-author/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "first_person": doctrine.get("first_person"),
        "gaps": gaps or [],
        "gap_count": len(gaps or []),
        "last_authored": authored or [],
        "authored_total": catalog.get("count") or 0,
        "catalog": catalog.get("materials") or [],
    }


def run_author_cycle(
    *,
    track: str | None = None,
    max_topics: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Detect gaps and write up to N self-authored lessons."""
    doc = _load(DOCTRINE, {})
    limit = int(max_topics or doc.get("max_topics_per_cycle") or 3)
    train = _mod("h7train", "hostess7-training.py")
    assessment = train.assess_all() if train and hasattr(train, "assess_all") else {}
    gaps = detect_training_gaps(assessment, track=track)

    if not gaps and not force:
        panel = build_author_panel(assessment=assessment, gaps=[], authored=[])
        _save(PANEL, panel)
        return {
            "ok": True,
            "authored": 0,
            "detail": "no_gaps",
            "gaps": [],
            "first_person": doc.get("first_person"),
            **panel,
        }

    if force and track and not gaps:
        meta = _track_meta().get(track, {})
        gaps = [{
            "track": track,
            "label": meta.get("label") or track,
            "score": 0.0,
            "level": "training",
            "complete": False,
            "battery_gaps": [],
            "reason": f"Operator requested authored material for {track}",
        }]

    authored: list[dict[str, Any]] = []
    for gap in gaps[:limit]:
        topic = author_topic_for_gap(gap)
        if not force and _topic_exists(gap["track"], topic["id"]):
            topic["note"] = "updated_existing"
        save_authored_topic(gap["track"], topic)
        authored.append(topic)

    panel = build_author_panel(assessment=assessment, gaps=gaps, authored=authored)
    _save(PANEL, panel)
    _append_ledger({
        "ts": panel["updated"],
        "event": "author_cycle",
        "authored": len(authored),
        "gaps": [g.get("track") for g in gaps[:limit]],
    })

    lines = [
        str(doc.get("first_person") or "I write my own training when I need more.")[:400],
        f"Authored {len(authored)} lesson(s) for: {', '.join(t.get('id', '') for t in authored)}.",
    ]
    for t in authored[:2]:
        lines.append(f"What: {t.get('what', '')[:200]}")

    return {
        "ok": True,
        "authored": len(authored),
        "gaps": gaps,
        "topics": authored,
        "reply": "\n\n".join(lines),
        **panel,
    }


def explain_author_training(query: str) -> str | None:
    low = (query or "").strip().lower()
    if not any(k in low for k in _AUTHOR_KEYS):
        return None
    track = None
    for tid in _track_meta():
        if tid in low:
            track = tid
            break
    out = run_author_cycle(track=track, force="force" in low or "write" in low)
    return str(out.get("reply") or out.get("first_person") or "")


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "gaps").strip().lower()
    if cmd in ("gaps", "detect"):
        train = _mod("h7train", "hostess7-training.py")
        assess = train.assess_all() if train else {}
        print(json.dumps({"gaps": detect_training_gaps(assess)}, ensure_ascii=False))
        return 0
    if cmd in ("author", "write", "run"):
        track = None
        force = "--force" in sys.argv
        max_n = None
        for arg in sys.argv[2:]:
            if arg.startswith("--max="):
                max_n = int(arg.split("=", 1)[1])
            elif not arg.startswith("--"):
                track = arg
        print(json.dumps(run_author_cycle(track=track, max_topics=max_n, force=force), ensure_ascii=False))
        return 0
    if cmd in ("catalog", "list"):
        print(json.dumps(list_authored_material(), ensure_ascii=False))
        return 0
    if cmd in ("panel", "json", "status"):
        print(json.dumps(_load(PANEL, build_author_panel()), ensure_ascii=False))
        return 0
    if cmd == "teach":
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "write training material"
        reply = explain_author_training(q)
        print(reply or json.dumps({"error": "no_author_topic"}, ensure_ascii=False))
        return 0 if reply else 1
    print(json.dumps({
        "error": "usage: hostess7-training-author.py [gaps|author [track]|catalog|panel|teach QUERY]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())