#!/usr/bin/env pythong
"""Change awareness — Hostess 7 knows every change; presume panel for slowdown/speedup/hang."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
DOCTRINE = INSTALL / "data" / "hostess7-change-awareness-doctrine.json"
PANEL = STATE / "hostess7-change-awareness-panel.json"
LEDGER = STATE / "hostess7-change-awareness.jsonl"
SNAPSHOT = STATE / "hostess7-change-snapshot.json"
INBOX = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "agents7" / "inbox.jsonl"
THOUGHTS = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
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
            fh.write(json.dumps({**row, "ts": row.get("ts") or _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _fingerprint(path: Path) -> dict[str, Any]:
    rel = str(path.relative_to(INSTALL)) if path.is_relative_to(INSTALL) else str(path)
    if not path.is_file():
        return {"path": rel, "present": False, "fp": "missing"}
    try:
        st = path.stat()
        raw = path.read_bytes()[:65536]
        return {
            "path": rel,
            "present": True,
            "size": st.st_size,
            "mtime": int(st.st_mtime),
            "fp": hashlib.sha256(raw).hexdigest()[:16],
        }
    except OSError:
        return {"path": rel, "present": False, "fp": "error"}


def _watch_paths() -> list[Path]:
    doc = _load(DOCTRINE, {})
    paths: list[Path] = []
    for rel in doc.get("watch_paths") or []:
        p = INSTALL / str(rel)
        if p not in paths:
            paths.append(p)
    return paths


def _notify_hostess7(
    event: str,
    *,
    message: str,
    meta: dict[str, Any] | None = None,
    speak: bool = False,
) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    notify = doc.get("notify") or {}
    row = {
        "schema": "hostess7-change-awareness/v1",
        "event": event,
        "message": message[:800],
        "meta": meta or {},
        "hostess7_knows": True,
    }
    if notify.get("inbox", True):
        _append(INBOX, row)
    if notify.get("thoughts", True):
        _append(THOUGHTS, {
            "ts": _now(),
            "kind": "change_awareness",
            "tags": ["hostess7", "change", event],
            "text": message[:500],
        })
    spoken = False
    if speak and event in (notify.get("speak_on") or []):
        noti = INSTALL / "lib" / "hostess7-noti.py"
        if noti.is_file():
            try:
                spec = importlib.util.spec_from_file_location("h7_noti_ca", noti)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "relay_event"):
                        rep = mod.relay_event(event, message=message, meta=meta)
                        spoken = bool(rep.get("spoken"))
            except Exception:
                pass
    return {"ok": True, "notified": True, "spoken": spoken, **row}


def witness_change(
    *,
    source: str,
    label: str,
    detail: str = "",
    meta: dict[str, Any] | None = None,
    notify: bool = True,
) -> dict[str, Any]:
    """Record a change Hostess 7 should know about — call when panels/doctrine/actions update."""
    change = {
        "schema": "hostess7-change-event/v1",
        "source": source[:120],
        "label": label[:120],
        "detail": detail[:400],
        "meta": meta or {},
    }
    _append(LEDGER, change)
    out = {"ok": True, **change}
    if notify:
        msg = f"Change — {label}" + (f": {detail}" if detail else "")
        out["notify"] = _notify_hostess7("change_witnessed", message=msg, meta={"source": source, **(meta or {})})
    return out


def scan_changes(*, notify: bool = True) -> dict[str, Any]:
    """Compare watched paths to snapshot; Hostess 7 learns every diff."""
    paths = _watch_paths()
    prior = _load(SNAPSHOT, {}).get("fingerprints") or {}
    current: dict[str, Any] = {}
    changes: list[dict[str, Any]] = []
    for p in paths:
        fp = _fingerprint(p)
        key = fp["path"]
        current[key] = fp
        old = prior.get(key)
        if old is None and fp.get("present"):
            changes.append({"path": key, "kind": "appeared", "fp": fp})
        elif old and not fp.get("present"):
            changes.append({"path": key, "kind": "removed", "old": old})
        elif old and fp.get("present") and old.get("fp") != fp.get("fp"):
            changes.append({"path": key, "kind": "modified", "old_fp": old.get("fp"), "new_fp": fp.get("fp")})

    for ch in changes:
        witness_change(
            source="scan",
            label=ch["path"],
            detail=f"{ch['kind']} — Hostess 7 should know.",
            meta=ch,
            notify=notify,
        )

    _save(SNAPSHOT, {"schema": "hostess7-change-snapshot/v1", "updated": _now(), "fingerprints": current})
    return {"ok": True, "changes": changes, "change_count": len(changes), "watched": len(paths)}


def check_presume_timing(*, notify: bool = True) -> dict[str, Any]:
    """Read presume panel + ledger — detect slowdown, speedup, hang."""
    presume_py = INSTALL / "lib" / "hostess7-presume.py"
    if not presume_py.is_file():
        return {"ok": False, "error": "presume_missing"}
    try:
        spec = importlib.util.spec_from_file_location("h7_presume_ca", presume_py)
        if not spec or not spec.loader:
            return {"ok": False, "error": "presume_import_failed"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "analyze_timing_health"):
            health = mod.analyze_timing_health()
        else:
            health = {"ok": False, "error": "analyze_timing_health_missing"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}

    verdict = str(health.get("verdict") or "unknown")
    if notify and verdict in ("slowdown", "speedup", "hang", "slowdown_severe"):
        drift = health.get("median_drift_us")
        msg = (
            f"Presume panel — {verdict}. "
            f"Median drift {drift} µs. "
            f"Active commits: {health.get('active_commit_count', 0)}. "
            "Check hostess7-presume-panel for timing witness."
        )
        health["notify"] = _notify_hostess7(
            verdict if verdict != "slowdown_severe" else "slowdown",
            message=msg,
            meta=health,
            speak=verdict in ("hang", "slowdown_severe"),
        )
    return health


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    scan = scan_changes(notify=False)
    timing = check_presume_timing(notify=False)
    recent: list[dict[str, Any]] = []
    if LEDGER.is_file():
        try:
            for line in LEDGER.read_text(encoding="utf-8").splitlines()[-32:]:
                if line.strip():
                    recent.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    hang_panel = _load(STATE / "hostess7-hang-guard-panel.json", {})
    out = {
        "schema": "hostess7-change-awareness-panel/v1",
        "updated": _now(),
        "motto": doc.get("motto"),
        "hostess7_knows_changes": True,
        "presume_timing": timing,
        "presume_verdict": timing.get("verdict"),
        "scan": scan,
        "pending_changes": scan.get("change_count", 0),
        "recent_changes": recent[-16:],
        "hang_guard": {
            "stall_count": hang_panel.get("stall_count"),
            "last_verdict": hang_panel.get("last_verdict"),
        },
        "check_commands": [
            "python3 lib/hostess7-change-awareness.py pulse",
            "python3 lib/hostess7-presume.py panel",
            "python3 lib/hostess7-presume.py timing",
        ],
    }
    if write:
        _save(PANEL, out)
    return out


def pulse(*, notify: bool = True) -> dict[str, Any]:
    """Full awareness pulse — scan file changes + presume timing; Hostess 7 learns all."""
    scan = scan_changes(notify=notify)
    timing = check_presume_timing(notify=notify)
    panel = build_panel(write=True)
    timing_out = {k: v for k, v in timing.items() if k != "notify"}
    return {
        "ok": True,
        "schema": "hostess7-change-awareness-pulse/v1",
        "scan": {
            "ok": scan.get("ok", True),
            "change_count": scan.get("change_count", 0),
            "watched": scan.get("watched", 0),
            "changes": scan.get("changes") or [],
        },
        "presume_timing": timing_out,
        "presume_verdict": timing_out.get("verdict"),
        "panel_path": str(PANEL),
        "pending_changes": panel.get("pending_changes", 0),
    }


def explain_awareness(query: str) -> str | None:
    low = (query or "").lower()
    keys = (
        "change awareness", "changes when", "know all changes", "presume panel",
        "slowdown", "speedup", "hang", "timing health", "drift_us",
    )
    if not any(k in low for k in keys):
        return None
    panel = build_panel(write=False)
    timing = panel.get("presume_timing") or {}
    lines = [
        str(_load(DOCTRINE, {}).get("motto") or "Hostess 7 knows every change when it happens."),
        "Check the presume panel for slowdowns, speedups, and hangs — drift_us and resumed_on_point are the witness.",
        f"Current presume verdict: {timing.get('verdict', 'unknown')}. Median drift: {timing.get('median_drift_us')} µs.",
        f"Recent changes logged: {len(panel.get('recent_changes') or [])}. Pending scan diff: {panel.get('pending_changes', 0)}.",
        "Pulse: hostess7-change-awareness.py pulse · Presume panel: hostess7-presume.py panel · Timing: hostess7-presume.py timing",
    ]
    for note in timing.get("notes") or []:
        lines.append(str(note))
    return "\n".join(lines)


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "pulse":
        print(json.dumps(pulse(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        print(json.dumps(scan_changes(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "timing":
        timing = check_presume_timing()
        timing_out = {k: v for k, v in timing.items() if k != "notify"}
        print(json.dumps(timing_out, ensure_ascii=False, indent=2))
        return 0
    if cmd == "witness" and len(sys.argv) > 2:
        print(json.dumps(witness_change(source="cli", label=sys.argv[2], detail=" ".join(sys.argv[3:])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "explain" and len(sys.argv) > 2:
        text = explain_awareness(" ".join(sys.argv[2:]))
        print(json.dumps({"ok": bool(text), "text": text or ""}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: hostess7-change-awareness.py [panel|pulse|scan|timing|witness LABEL|explain QUERY]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())