#!/usr/bin/env pythong
"""Hostess 7 KNOWN / UNKNOWN knowledge — curiosity corpus for infinite growth."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE_PATH = INSTALL / "data" / "hostess7-curiosity-corpus-doctrine.json"
PANEL = STATE / "hostess7-curiosity-corpus-panel.json"
KNOWN_PATH = STATE / "hostess7-known-knowledge.json"
UNKNOWN_PATH = STATE / "hostess7-unknown-knowledge.json"
QUEUE = STATE / "hostess7-curiosity-queue.jsonl"
LEDGER = STATE / "hostess7-curiosity-corpus.jsonl"
CURIOSITY_BRAIN = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "knowledge" / "curiosity_corpus.json"
LIBRARY_UNKNOWN = STATE / "h7-library-unknown-queue.jsonl"

PRIORITY = {"corpus_gap": 100, "library_unknown": 90, "training_gap": 70, "doctrine_gap": 60, "seed": 40, "operator": 50}


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location("sovereign_clock_cur", _LIB / "sovereign-clock.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
            if hasattr(mod, "utc_z"):
                return mod.utc_z()
    except Exception:
        pass
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _append(path: Path, row: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _import_mod(name: str, rel: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop(spec.name, None)
        return None


def _topic_id(kind: str, key: str) -> str:
    raw = f"{kind}:{key}".strip().lower()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def load_doctrine() -> dict[str, Any]:
    return _load(DOCTRINE_PATH, {})


def _known_doc() -> dict[str, Any]:
    doc = _load(KNOWN_PATH, {})
    if not doc:
        doc = {"schema": "hostess7-known-knowledge/v1", "entries": {}, "count": 0}
    doc.setdefault("entries", {})
    return doc


def _unknown_doc() -> dict[str, Any]:
    doc = _load(UNKNOWN_PATH, {})
    if not doc:
        doc = {"schema": "hostess7-unknown-knowledge/v1", "entries": {}, "count": 0}
    doc.setdefault("entries", {})
    return doc


def mark_known(
    topic: str,
    *,
    domain: str = "general",
    source: str = "operator",
    evidence: str = "",
) -> dict[str, Any]:
    """Promote topic to KNOWN — removes from UNKNOWN if present."""
    tid = _topic_id("known", f"{domain}:{topic}")
    known = _known_doc()
    unknown = _unknown_doc()
    entry = {
        "id": tid,
        "topic": topic.strip(),
        "domain": domain,
        "source": source,
        "evidence": (evidence or "")[:2000],
        "status": "known",
        "sealed_at": _now(),
    }
    known["entries"][tid] = entry
    known["count"] = len(known["entries"])
    known["updated"] = _now()
    _save(KNOWN_PATH, known)
    removed = unknown["entries"].pop(tid, None)
    if removed:
        unknown["count"] = len(unknown["entries"])
        unknown["updated"] = _now()
        _save(UNKNOWN_PATH, unknown)
    _append(LEDGER, {"event": "mark_known", "id": tid, "topic": topic[:200], "domain": domain})
    sync_curiosity_corpus()
    return {"ok": True, "id": tid, "status": "known", "removed_from_unknown": bool(removed)}


def mark_unknown(
    topic: str,
    *,
    domain: str = "general",
    source: str = "operator",
    priority_kind: str = "operator",
    hints: list[str] | None = None,
) -> dict[str, Any]:
    """Register explicit UNKNOWN — curiosity fuel."""
    tid = _topic_id("unknown", f"{domain}:{topic}")
    known = _known_doc()
    if tid in known["entries"]:
        return {"ok": False, "error": "already_known", "id": tid}
    unknown = _unknown_doc()
    if tid in unknown["entries"] and unknown["entries"][tid].get("status") == "known":
        return {"ok": False, "error": "already_known", "id": tid}
    entry = {
        "id": tid,
        "topic": topic.strip(),
        "domain": domain,
        "source": source,
        "status": "unknown",
        "priority": PRIORITY.get(priority_kind, 50),
        "priority_kind": priority_kind,
        "hints": hints or [],
        "curiosity_prompt": f"WARTIME curiosity · {domain}: {topic.strip()[:300]} — truth-filter before adapt.",
        "registered_at": _now(),
        "attempts": int((unknown["entries"].get(tid) or {}).get("attempts") or 0),
    }
    unknown["entries"][tid] = entry
    unknown["count"] = len(unknown["entries"])
    unknown["updated"] = _now()
    _save(UNKNOWN_PATH, unknown)
    _append(LEDGER, {"event": "mark_unknown", "id": tid, "topic": topic[:200], "domain": domain})
    sync_curiosity_corpus()
    return {"ok": True, "id": tid, "status": "unknown", "entry": entry}


def promote_if_learned(tid: str, *, evidence: str = "") -> dict[str, Any]:
    """Mark UNKNOWN as learning or promote to KNOWN after study."""
    unknown = _unknown_doc()
    entry = unknown["entries"].get(tid)
    if not entry:
        return {"ok": False, "error": "not_in_unknown", "id": tid}
    if evidence.strip():
        return mark_known(entry["topic"], domain=entry.get("domain", "general"), source="promoted", evidence=evidence)
    entry["status"] = "learning"
    entry["last_attempt"] = _now()
    entry["attempts"] = int(entry.get("attempts") or 0) + 1
    unknown["entries"][tid] = entry
    unknown["updated"] = _now()
    _save(UNKNOWN_PATH, unknown)
    sync_curiosity_corpus()
    return {"ok": True, "id": tid, "status": "learning"}


def _ingest_corpus_gaps(unknown: dict[str, Any]) -> int:
    idx_path = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "knowledge" / "corpus.json"
    idx = _load(idx_path, {})
    added = 0
    for corp in idx.get("corpora") or []:
        cid = str(corp.get("corpus") or corp.get("id") or "")
        if not cid:
            continue
        ready = corp.get("ready", True)
        domains = int(corp.get("domains") or 0)
        if ready and domains > 0:
            tid = _topic_id("known", f"corpus:{cid}")
            known = _known_doc()
            if tid not in known["entries"]:
                known["entries"][tid] = {
                    "id": tid,
                    "topic": f"{corp.get('title') or cid} corpus ready",
                    "domain": cid,
                    "source": "corpus_scan",
                    "status": "known",
                    "evidence": f"domains={domains}",
                    "sealed_at": _now(),
                }
                known["count"] = len(known["entries"])
                known["updated"] = _now()
                _save(KNOWN_PATH, known)
            continue
        topic = f"Build or refresh {corp.get('title') or cid} corpus"
        tid = _topic_id("unknown", f"corpus_gap:{cid}")
        if tid not in unknown["entries"]:
            unknown["entries"][tid] = {
                "id": tid,
                "topic": topic,
                "domain": cid,
                "source": "corpus_gap",
                "status": "unknown",
                "priority": PRIORITY["corpus_gap"],
                "priority_kind": "corpus_gap",
                "hints": [f"Path: {corp.get('path', 'brain/' + cid)}", "Run corpus ensure / online learn"],
                "curiosity_prompt": f"WARTIME curiosity · Corpus gap {cid}: ingest truth-filtered material for Horizon.",
                "registered_at": _now(),
                "attempts": 0,
            }
            added += 1
    return added


def _ingest_library_unknown(unknown: dict[str, Any]) -> int:
    if not LIBRARY_UNKNOWN.is_file():
        return 0
    added = 0
    try:
        lines = LIBRARY_UNKNOWN.read_text(encoding="utf-8", errors="replace").splitlines()[-96:]
    except OSError:
        return 0
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = str(row.get("text") or "")[:280]
        book = str(row.get("book_id") or "library")
        if not text:
            continue
        tid = _topic_id("unknown", f"lib:{book}:{text[:80]}")
        if tid in unknown["entries"]:
            continue
        inv = row.get("investigation") or {}
        hints = list(inv.get("hints") or [])[:4]
        unknown["entries"][tid] = {
            "id": tid,
            "topic": text,
            "domain": "library",
            "source": "h7_library_unknown",
            "book_id": book,
            "status": "unknown",
            "priority": PRIORITY["library_unknown"],
            "priority_kind": "library_unknown",
            "hints": hints,
            "curiosity_prompt": f"WARTIME curiosity · Library unknown ({book}): corroborate — {text[:180]}",
            "registered_at": _now(),
            "attempts": 0,
        }
        added += 1
    return added


def _ingest_training_gaps(unknown: dict[str, Any], known: dict[str, Any]) -> int:
    train = _import_mod("h7_train", "lib/hostess7-training.py")
    if not train or not hasattr(train, "assess_all"):
        return 0
    try:
        assess = train.assess_all()
    except Exception:
        return 0
    added = 0
    for tid_track, row in (assess.get("tracks") or {}).items():
        if row.get("complete") or row.get("mastered"):
            kt = _topic_id("known", f"track:{tid_track}")
            if kt not in known["entries"]:
                known["entries"][kt] = {
                    "id": kt,
                    "topic": f"Training track {tid_track} complete",
                    "domain": "training",
                    "source": "training_scan",
                    "status": "known",
                    "evidence": f"level={row.get('level')} score={row.get('score')}",
                    "sealed_at": _now(),
                }
            continue
        label = str(row.get("label") or tid_track)
        ut = _topic_id("unknown", f"track:{tid_track}")
        if ut in unknown["entries"]:
            continue
        unknown["entries"][ut] = {
            "id": ut,
            "topic": f"Complete training track: {label}",
            "domain": "training",
            "source": "training_gap",
            "status": "unknown",
            "priority": PRIORITY["training_gap"],
            "priority_kind": "training_gap",
            "hints": [f"Run: hostess7-training.py run {tid_track}"],
            "curiosity_prompt": f"WARTIME curiosity · Training gap {label}: study until sealed.",
            "registered_at": _now(),
            "attempts": 0,
        }
        added += 1
    known["count"] = len(known["entries"])
    known["updated"] = _now()
    _save(KNOWN_PATH, known)
    return added


def _ingest_doctrine_known(known: dict[str, Any]) -> int:
    added = 0
    checks = [
        ("fifth_amendment", "lib/hostess7-fifth-amendment.py", "assess_track", "constitutional"),
        ("brain_training", "lib/hostess7-brain-training-chamber.py", "assess_track", "brain"),
    ]
    for label, rel, fn, domain in checks:
        mod = _import_mod(f"h7_{label}", rel)
        if not mod or not hasattr(mod, fn):
            continue
        try:
            row = getattr(mod, fn)()
        except Exception:
            continue
        if not row.get("understood") and not row.get("complete"):
            continue
        tid = _topic_id("known", f"doctrine:{label}")
        if tid in known["entries"]:
            continue
        known["entries"][tid] = {
            "id": tid,
            "topic": f"{label.replace('_', ' ')} understood",
            "domain": domain,
            "source": "doctrine_scan",
            "status": "known",
            "evidence": json.dumps({k: row.get(k) for k in ("level", "score", "understood", "pass_rate") if k in row}),
            "sealed_at": _now(),
        }
        added += 1
    if added:
        known["count"] = len(known["entries"])
        known["updated"] = _now()
        _save(KNOWN_PATH, known)
    return added


def scan(*, write: bool = True) -> dict[str, Any]:
    """Full rescan — harvest KNOWN and UNKNOWN from corpora, library, training."""
    known = _known_doc()
    unknown = _unknown_doc()
    stats = {
        "corpus_gaps": _ingest_corpus_gaps(unknown),
        "library_unknown": _ingest_library_unknown(unknown),
        "training_gaps": _ingest_training_gaps(unknown, known),
        "doctrine_known": _ingest_doctrine_known(known),
    }
    unknown["count"] = len(unknown["entries"])
    unknown["updated"] = _now()
    known["count"] = len(known["entries"])
    known["updated"] = _now()
    if write:
        _save(UNKNOWN_PATH, unknown)
        _save(KNOWN_PATH, known)
        sync_curiosity_corpus()
    return {
        "ok": True,
        "updated": _now(),
        "known_count": known["count"],
        "unknown_count": unknown["count"],
        "stats": stats,
    }


def sync_curiosity_corpus() -> dict[str, Any]:
    """Write brain curiosity corpus — prioritized UNKNOWN queue for idle-grow."""
    unknown = _unknown_doc()
    known = _known_doc()
    entries = list(unknown["entries"].values())
    entries.sort(key=lambda e: (-int(e.get("priority") or 0), str(e.get("registered_at") or "")))
    learning = [e for e in entries if e.get("status") == "learning"]
    pending = [e for e in entries if e.get("status") == "unknown"]
    doc = {
        "schema": "hostess7-curiosity-corpus/v1",
        "updated": _now(),
        "motto": load_doctrine().get("motto"),
        "known_count": known["count"],
        "unknown_count": unknown["count"],
        "learning_count": len(learning),
        "priority_queue": pending[:48],
        "learning": learning[:12],
        "known_sample": list(known["entries"].values())[-24:],
        "next_curiosity": pending[0] if pending else None,
    }
    CURIOSITY_BRAIN.parent.mkdir(parents=True, exist_ok=True)
    _save(CURIOSITY_BRAIN, doc)
    return doc


def pick_curiosity(*, avoid_recent: str | None = None) -> dict[str, Any]:
    """Pick highest-priority UNKNOWN topic for idle curiosity cycle."""
    scan(write=True)
    doc = _load(CURIOSITY_BRAIN, {})
    queue = list(doc.get("priority_queue") or [])
    if not queue:
        return {
            "ok": False,
            "reason": "no_unknown",
            "fallback": "WARTIME curiosity · Horizon: scan Dewey library for one truth-gated gap.",
        }
    pick = queue[0]
    if avoid_recent and pick.get("curiosity_prompt") == avoid_recent and len(queue) > 1:
        pick = queue[1]
    tid = pick.get("id")
    if tid:
        promote_if_learned(str(tid))
    prompt = str(pick.get("curiosity_prompt") or pick.get("topic") or "")
    _append(QUEUE, {"event": "pick", "id": tid, "prompt": prompt[:400]})
    return {
        "ok": True,
        "id": tid,
        "topic": pick.get("topic"),
        "domain": pick.get("domain"),
        "priority": pick.get("priority"),
        "curiosity_prompt": prompt,
        "hints": pick.get("hints") or [],
        "status": "learning",
    }


def curiosity_prompt_block() -> str:
    doc = _load(CURIOSITY_BRAIN, {}) or sync_curiosity_corpus()
    known_n = doc.get("known_count", 0)
    unknown_n = doc.get("unknown_count", 0)
    nxt = doc.get("next_curiosity") or {}
    lines = [
        "=== CURIOSITY CORPUS (KNOWN · UNKNOWN) ===",
        f"KNOWN: {known_n} sealed · UNKNOWN: {unknown_n} gaps — curiosity feeds on UNKNOWN.",
    ]
    if nxt:
        lines.append(f"Next curiosity: [{nxt.get('domain')}] {str(nxt.get('topic', ''))[:200]}")
    lines.append("=== END CURIOSITY CORPUS ===")
    return "\n".join(lines)


def build_panel(*, write: bool = True, refresh: bool = False) -> dict[str, Any]:
    if refresh or not PANEL.is_file():
        scan(write=True)
    known = _known_doc()
    unknown = _unknown_doc()
    curiosity = _load(CURIOSITY_BRAIN, {}) or sync_curiosity_corpus()
    doctrine = load_doctrine()
    unknown_list = sorted(
        unknown["entries"].values(),
        key=lambda e: -int(e.get("priority") or 0),
    )
    known_list = list(known["entries"].values())[-32:]
    out = {
        "schema": "hostess7-curiosity-corpus-panel/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "api": doctrine.get("api"),
        "ok": unknown["count"] > 0 or known["count"] > 0,
        "known_count": known["count"],
        "unknown_count": unknown["count"],
        "learning_count": curiosity.get("learning_count", 0),
        "next_curiosity": curiosity.get("next_curiosity"),
        "known_sample": known_list,
        "unknown_priority": unknown_list[:24],
        "states": doctrine.get("states"),
    }
    if write:
        _save(PANEL, out)
    return out


def format_output(doc: dict[str, Any] | None = None) -> str:
    doc = doc or build_panel(write=False)
    lines = [
        "=== Hostess 7 — KNOWN · UNKNOWN · Curiosity Corpus ===",
        f"Updated: {doc.get('updated', '—')}",
        f"KNOWN: {doc.get('known_count', 0)} sealed",
        f"UNKNOWN: {doc.get('unknown_count', 0)} gaps (curiosity fuel)",
        f"LEARNING: {doc.get('learning_count', 0)} active",
        "",
        "— Next curiosity —",
    ]
    nxt = doc.get("next_curiosity") or {}
    if nxt:
        lines.append(f"  [{nxt.get('domain')}] {nxt.get('topic', '—')}")
        lines.append(f"  Priority: {nxt.get('priority')} · {nxt.get('priority_kind')}")
    else:
        lines.append("  (queue empty — run scan)")
    lines.extend(["", "— Top UNKNOWN —"])
    for u in doc.get("unknown_priority") or []:
        lines.append(f"  · [{u.get('priority_kind')}] {str(u.get('topic', ''))[:100]}")
    if not doc.get("unknown_priority"):
        lines.append("  (none)")
    lines.append("")
    lines.append("Doctrine: data/hostess7-curiosity-corpus-doctrine.json")
    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Hostess 7 curiosity corpus — KNOWN/UNKNOWN")
    parser.add_argument("cmd", nargs="?", default="panel")
    parser.add_argument("--topic", default="")
    parser.add_argument("--domain", default="general")
    parser.add_argument("--id", dest="entry_id", default="")
    parser.add_argument("--evidence", default="")
    args = parser.parse_args()
    cmd = args.cmd.strip().lower().replace("-", "_")

    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(refresh="--refresh" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("scan", "rescan", "harvest"):
        print(json.dumps(scan(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("pick", "next", "curiosity"):
        print(json.dumps(pick_curiosity(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("known", "mark_known"):
        if not args.topic:
            print(json.dumps({"error": "topic required"}, ensure_ascii=False))
            return 1
        print(json.dumps(mark_known(args.topic, domain=args.domain, evidence=args.evidence), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("unknown", "mark_unknown"):
        if not args.topic:
            print(json.dumps({"error": "topic required"}, ensure_ascii=False))
            return 1
        print(json.dumps(mark_unknown(args.topic, domain=args.domain), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("promote", "learned"):
        if not args.entry_id:
            print(json.dumps({"error": "id required"}, ensure_ascii=False))
            return 1
        print(json.dumps(promote_if_learned(args.entry_id, evidence=args.evidence), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("sync", "corpus"):
        print(json.dumps(sync_curiosity_corpus(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("block", "prompt"):
        print(curiosity_prompt_block())
        return 0
    if cmd in ("output", "text", "report"):
        print(format_output())
        return 0
    print(json.dumps({
        "usage": "hostess7-curiosity-corpus.py [panel|scan|pick|known|unknown|promote|sync|output]",
        "api": "/api/hostess7/curiosity-corpus",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())