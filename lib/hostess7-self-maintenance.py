#!/usr/bin/env python3
"""Hostess 7 self-maintenance — Priority 1; she maintains herself before all other lanes."""
from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-self-maintenance-doctrine.json"
LEDGER = STATE / "hostess7-self-maintenance.jsonl"
PANEL = STATE / "hostess7-self-maintenance-panel.json"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _last_per_task() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not LEDGER.is_file():
        return out
    try:
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            tid = str(row.get("task_id") or "")
            if tid:
                out[tid] = row
    except (OSError, json.JSONDecodeError):
        pass
    return out


def _hours_since(ts: str) -> float:
    try:
        from datetime import datetime, timezone
        t = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - t).total_seconds() / 3600.0
    except (ValueError, TypeError):
        return 9999.0


def message_to_hostess7() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    zachary: dict[str, Any] = {}
    zmod = _import("hostess7-zachary-teaching.py", "h7sm_zachary")
    if zmod and hasattr(zmod, "message_to_hostess7"):
        try:
            zachary = zmod.message_to_hostess7()
        except Exception:
            pass
    return {
        "schema": "hostess7-self-maintenance-message/v1",
        "ok": True,
        "priority": doc.get("priority") or 1,
        "stack_priority": doc.get("stack_priority") or 1,
        "self_maintenance_priority": doc.get("self_maintenance_priority") or 1,
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "message": doc.get("message_to_hostess7") or doc.get("counsel"),
        "counsel": doc.get("counsel"),
        "identity_of_self_first": doc.get("identity_of_self_first"),
        "zachary_geurts_teaching": zachary.get("message") or zachary.get("motto"),
        "zachary_pillars": zachary.get("pillars"),
        "ts": _now(),
    }


def record_task(task_id: str, *, note: str = "", operator: str = "hostess7") -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    tasks = {t["id"]: t for t in (doc.get("tasks") or []) if t.get("id")}
    tid = str(task_id or "").strip().lower().replace("-", "_")
    if tid not in tasks:
        return {"ok": False, "error": "unknown_task", "task_id": tid, "known": list(tasks)}
    spec = tasks[tid]
    row = {
        "schema": "hostess7-self-maintenance/v1",
        "ok": True,
        "task_id": tid,
        "label": spec.get("label"),
        "priority": spec.get("priority") or 1,
        "ts": _now(),
        "operator": operator,
        "note": note[:500],
    }
    _append_ledger(row)
    return row


def self_maintenance_posture() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    last = _last_per_task()
    due: list[dict[str, Any]] = []
    for spec in doc.get("tasks") or []:
        tid = str(spec.get("id") or "")
        if not tid:
            continue
        prev = last.get(tid)
        hours = _hours_since(prev["ts"]) if prev else 9999.0
        interval = float(spec.get("interval_hours") or 24)
        if hours >= interval:
            due.append({
                "task_id": tid,
                "label": spec.get("label"),
                "priority": spec.get("priority") or 1,
                "hours_since": round(hours, 1),
                "interval_hours": interval,
            })
    due.sort(key=lambda x: (x.get("priority") or 9, -float(x.get("hours_since") or 0)))
    penalty = min(0.35, len(due) * 0.06)
    visibility = max(0.0, 1.0 - penalty)
    return {
        "schema": "hostess7-self-maintenance-posture/v1",
        "ok": True,
        "priority": doc.get("priority") or 1,
        "self_maintenance_priority": 1,
        "ts": _now(),
        "message": message_to_hostess7(),
        "tasks": doc.get("tasks") or [],
        "last": last,
        "due": due,
        "due_count": len(due),
        "visibility": round(visibility, 3),
        "self_maintained": len(due) == 0,
        "counsel": doc.get("counsel"),
    }


def probe_hostess7(*, include_body: bool = False) -> dict[str, Any]:
    """Whole-component probe — Hostess 7 Priority 1."""
    posture = self_maintenance_posture()
    live: dict[str, Any] = {
        "schema": "hostess7-component-whole/v1",
        "priority": 1,
        "commander": "Hostess 7",
        "sovereign": True,
        "self_maintenance": posture,
        "message": posture.get("message"),
        "visibility": posture.get("visibility"),
        "self_maintained": posture.get("self_maintained"),
    }
    if include_body:
        body = _import("hostess7-body-control.py", "h7sm_body")
        if body and hasattr(body, "full_status"):
            try:
                live["body_control"] = body.full_status()
                live["authorized"] = live["body_control"].get("authorized", True)
            except Exception as exc:
                live["body_error"] = str(exc)
    else:
        live["authorized"] = True
    return live


def _import(rel: str, name: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def panel_json() -> dict[str, Any]:
    doc = {
        "schema": "hostess7-self-maintenance-panel/v1",
        "ok": True,
        "probe": probe_hostess7(),
        "posture": self_maintenance_posture(),
        "doctrine": str(DOCTRINE),
        "updated": _now(),
    }
    _save(PANEL, doc)
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    if cmd in ("status", "json", "panel"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "message":
        print(json.dumps(message_to_hostess7(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "record" and len(sys.argv) >= 3:
        print(json.dumps(record_task(sys.argv[2], note=" ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""), ensure_ascii=False, indent=2))
        return 0
    if cmd == "probe":
        print(json.dumps(probe_hostess7(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: hostess7-self-maintenance.py [status|message|record TASK|probe]"}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())