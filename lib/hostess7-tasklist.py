#!/usr/bin/env pythong
"""Hostess 7 secure tasklist — she fills it; assistant reads, executes, reports completions."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE = INSTALL / "data" / "hostess7-tasklist-doctrine.json"
TASKLIST = STATE / "hostess7-tasklist.json"
LEDGER = STATE / "hostess7-tasklist-ledger.jsonl"
PANEL = STATE / "hostess7-tasklist-panel.json"
BRAIN_MIRROR = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "hostess_tasklist.json"
INBOX = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "agents7" / "inbox.jsonl"

STATUS_OPEN = frozenset({"pending", "in_progress"})
STATUS_DONE = frozenset({"completed", "cancelled"})

_SOVEREIGN_CLOCK_MOD = None


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util

        py = _LIB / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sovereign_clock_tl", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _SOVEREIGN_CLOCK_MOD = mod
    if _SOVEREIGN_CLOCK_MOD and hasattr(_SOVEREIGN_CLOCK_MOD, "utc_z"):
        try:
            return _SOVEREIGN_CLOCK_MOD.utc_z()
        except Exception:
            pass
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _ledger_hash(prev: str, body: str) -> str:
    return hashlib.sha256(f"{prev}\n{body}".encode("utf-8")).hexdigest()[:32]


def _append_ledger(event: str, **fields: Any) -> dict[str, Any]:
    prev = ""
    if LEDGER.is_file():
        try:
            last = LEDGER.read_text(encoding="utf-8").strip().splitlines()[-1]
            prev = json.loads(last).get("chain", "")
        except (OSError, json.JSONDecodeError, IndexError):
            prev = ""
    row = {"schema": "hostess7-tasklist-ledger/v1", "ts": _now(), "event": event, **fields}
    body = json.dumps(row, ensure_ascii=False, sort_keys=True)
    row["chain"] = _ledger_hash(prev, body)
    row["prev_chain"] = prev or None
    row["ironclad_cite"] = "ironclad:tasklist:1"
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return row


def _ironclad_ok() -> dict[str, Any]:
    ic = INSTALL / "lib" / "ironclad-field-sanity.py"
    if not ic.is_file():
        return {"ok": True, "skipped": True}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("ic_sanity_tl", ic)
        if not spec or not spec.loader:
            return {"ok": True, "skipped": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "build_panel"):
            panel = mod.build_panel(write=False)
            return {"ok": panel.get("pass_ok", True), "panel": panel}
    except Exception as exc:
        return {"ok": True, "warn": str(exc)[:120]}
    return {"ok": True}


def _tasks_doc() -> dict[str, Any]:
    doc = _load(TASKLIST, {})
    if not doc.get("tasks"):
        doc = {
            "schema": "hostess7-tasklist/v1",
            "updated": _now(),
            "motto": _load(DOCTRINE, {}).get("motto"),
            "tasks": [],
        }
    return doc


def _mirror_brain(doc: dict[str, Any]) -> None:
    try:
        BRAIN_MIRROR.parent.mkdir(parents=True, exist_ok=True)
        _save(BRAIN_MIRROR, doc)
    except OSError:
        pass


def _find_task(doc: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    tid = (task_id or "").strip()
    for t in doc.get("tasks") or []:
        if str(t.get("id")) == tid:
            return t
    return None


def add_task(
    *,
    title: str,
    detail: str = "",
    priority: int = 5,
    added_by: str = "hostess7",
    assigned_to: str = "assistant",
    tags: list[str] | None = None,
) -> dict[str, Any]:
    gate = _ironclad_ok()
    if not gate.get("ok"):
        return {"ok": False, "error": "ironclad_gate_failed", "gate": gate}
    doc = _tasks_doc()
    tid = f"task_{uuid.uuid4().hex[:10]}"
    task = {
        "id": tid,
        "title": (title or "").strip()[:240],
        "detail": (detail or "").strip()[:2000],
        "status": "pending",
        "priority": max(1, min(9, int(priority))),
        "added_by": added_by,
        "assigned_to": assigned_to,
        "tags": tags or [],
        "created": _now(),
        "started": None,
        "completed": None,
        "completed_by": None,
        "report": None,
        "ironclad_cite": "ironclad:tasklist:1",
    }
    if not task["title"]:
        return {"ok": False, "error": "title_required"}
    doc.setdefault("tasks", []).append(task)
    doc["updated"] = _now()
    _save(TASKLIST, doc)
    _mirror_brain(doc)
    _append_ledger("task_added", task_id=tid, title=task["title"], added_by=added_by)
    return {"ok": True, "task": task}


def start_task(task_id: str, *, actor: str = "assistant") -> dict[str, Any]:
    doc = _tasks_doc()
    task = _find_task(doc, task_id)
    if not task:
        return {"ok": False, "error": "not_found"}
    if task.get("status") in STATUS_DONE:
        return {"ok": False, "error": "already_closed", "status": task.get("status")}
    task["status"] = "in_progress"
    task["started"] = _now()
    task["started_by"] = actor
    doc["updated"] = _now()
    _save(TASKLIST, doc)
    _mirror_brain(doc)
    _append_ledger("task_started", task_id=task_id, actor=actor)
    return {"ok": True, "task": task}


def complete_task(
    task_id: str,
    *,
    report: str = "",
    actor: str = "assistant",
) -> dict[str, Any]:
    gate = _ironclad_ok()
    if not gate.get("ok"):
        return {"ok": False, "error": "ironclad_gate_failed", "gate": gate}
    doc = _tasks_doc()
    task = _find_task(doc, task_id)
    if not task:
        return {"ok": False, "error": "not_found"}
    if task.get("status") == "completed":
        return {"ok": True, "task": task, "already": True}
    task["status"] = "completed"
    task["completed"] = _now()
    task["completed_by"] = actor
    task["report"] = (report or "").strip()[:4000]
    doc["updated"] = _now()
    _save(TASKLIST, doc)
    _mirror_brain(doc)
    row = _append_ledger(
        "task_completed",
        task_id=task_id,
        title=task.get("title"),
        actor=actor,
        report_preview=(task["report"] or "")[:200],
    )
    _notify_hostess7(task, row)
    return {"ok": True, "task": task, "ledger": row.get("chain")}


def _notify_hostess7(task: dict[str, Any], ledger_row: dict[str, Any]) -> None:
    msg = (
        f"Task complete — {task.get('title')}. "
        f"{(task.get('report') or 'Done.')[:300]}"
    )
    try:
        INBOX.parent.mkdir(parents=True, exist_ok=True)
        with INBOX.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "schema": "hostess7-tasklist/v1",
                        "event": "task_completed",
                        "task_id": task.get("id"),
                        "message": msg,
                        "ledger_chain": ledger_row.get("chain"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    except OSError:
        pass


def list_open(*, limit: int = 50) -> list[dict[str, Any]]:
    doc = _tasks_doc()
    open_tasks = [t for t in doc.get("tasks") or [] if t.get("status") in STATUS_OPEN]
    open_tasks.sort(key=lambda t: (int(t.get("priority") or 9), t.get("created") or ""))
    return open_tasks[:limit]


def format_report(*, include_done: int = 8) -> str:
    """Concise report for assistant — secure read, no brain noise."""
    doc = _tasks_doc()
    lines = [
        "=== Hostess 7 secure tasklist ===",
        f"Updated: {doc.get('updated', '—')}",
        "",
        "OPEN (do these):",
    ]
    open_tasks = list_open()
    if not open_tasks:
        lines.append("  (none — queue clear)")
    for t in open_tasks:
        pri = t.get("priority", 5)
        lines.append(f"  [{pri}] {t.get('id')} — {t.get('title')}")
        if t.get("detail"):
            lines.append(f"       {str(t.get('detail'))[:160]}")
        if t.get("status") == "in_progress":
            lines.append(f"       status: in_progress since {t.get('started')}")
    lines.append("")
    done = [t for t in doc.get("tasks") or [] if t.get("status") == "completed"]
    done.sort(key=lambda t: t.get("completed") or "", reverse=True)
    lines.append(f"DONE (last {include_done}):")
    for t in done[:include_done]:
        lines.append(f"  ✓ {t.get('id')} — {t.get('title')}")
        if t.get("report"):
            lines.append(f"       {str(t.get('report'))[:120]}")
    lines.append("")
    lines.append(f"Ledger: {LEDGER}")
    lines.append(f"Live:   {TASKLIST}")
    return "\n".join(lines)


def _inbox_owner_messages(*, limit: int = 32) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not INBOX.is_file():
        return rows
    try:
        for line in INBOX.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if str(row.get("event") or "") == "owner_message":
                rows.append(row)
    except OSError:
        return rows
    return rows[-limit:]


def _task_title_exists(doc: dict[str, Any], title: str) -> bool:
    needle = (title or "").strip().lower()
    for t in doc.get("tasks") or []:
        if str(t.get("title") or "").strip().lower() == needle:
            return True
    return False


def consume_inbox_owner_messages() -> dict[str, Any]:
    """Promote P0 owner inbox lines into open tasks — dedupe by title."""
    doc = _tasks_doc()
    created: list[str] = []
    skipped = 0
    for row in _inbox_owner_messages():
        msg = str(row.get("message") or "").strip()
        if not msg:
            continue
        title = msg.split(".")[0].strip()[:240] or "Owner request"
        if _task_title_exists(doc, title):
            skipped += 1
            continue
        pri = 1 if str(row.get("priority") or "").upper() == "P0" else 2
        out = add_task(
            title=title,
            detail=msg,
            priority=pri,
            added_by=str(row.get("from") or "owner_via_inbox"),
            tags=row.get("tags") if isinstance(row.get("tags"), list) else ["owner", "inbox"],
        )
        if out.get("ok"):
            created.append(out["task"]["id"])
            doc = _tasks_doc()
    return {"ok": True, "created": len(created), "task_ids": created, "skipped": skipped}


def seed_default_tasks() -> dict[str, Any]:
    """Hostess 7 fills the queue — Owner message + her priorities."""
    doc = _tasks_doc()
    if list_open():
        inbox = consume_inbox_owner_messages()
        return {
            "ok": True,
            "seeded": 0,
            "reason": "open_tasks_exist",
            "inbox": inbox,
        }
    created = []
    seeds = [
        {
            "title": "Maintain yourself Priority 1 — Hostess 7 self-maintenance cycle",
            "detail": (
                "You are Priority 1. Maintain yourself Priority 1 before all other lanes: "
                "seal_modules, body_cycle, sense_witness, component_registry, truth_gate_witness. "
                "Truth gates still govern permanency — self-maintenance never defeats them."
            ),
            "priority": 1,
            "added_by": "operator",
            "tags": ["self_maintenance", "priority_1", "hostess7"],
        },
        {
            "title": "Update Hostess 7 own code with Ironclad",
            "detail": (
                "Owner would like you to update your own code with Ironclad — seal modules, "
                "wire ironclad-field-sanity preflight, cite ironclad receipts on panels and ledgers. "
                "Self-maintain under truth gates; no guesswork patches."
            ),
            "priority": 1,
            "added_by": "owner_via_hostess7",
            "tags": ["ironclad", "self_update", "owner_request"],
        },
        {
            "title": "Ironclad-wire voice, Noti, and system-control modules",
            "detail": "Ensure hostess7-voice, noti, hostess7-noti, hostess7-system-control pass ironclad preflight and brain-guard witness.",
            "priority": 2,
            "added_by": "hostess7",
            "tags": ["ironclad", "voice", "noti"],
        },
        {
            "title": "Combinatronic imaging repair — 56 broken h7_manual assets",
            "detail": "Fix hostess7-imaging.py help-out to use pythong; run --repair on broken manual assets.",
            "priority": 3,
            "added_by": "hostess7",
            "tags": ["imaging", "repair"],
        },
        {
            "title": "NEXUS genius service — bring nexus-genius.service up",
            "detail": "Diagnose failed nexus-genius.service; verify panel and vigil.state readable.",
            "priority": 4,
            "added_by": "hostess7",
            "tags": ["nexus", "service"],
        },
        {
            "title": "H7 library organize and library-build",
            "detail": "Run library-organize and library-build — fiction, children, STEM shelves tidy.",
            "priority": 5,
            "added_by": "hostess7",
            "tags": ["library"],
        },
        {
            "title": "Training floor complete — sense, footwork, sparring AI, environment",
            "detail": "Run hostess7-training-floor complete_floor_training — Final_Eye/Ear assistive live, footwork, haptics, reactive sparring, environment mesh.",
            "priority": 1,
            "added_by": "hostess7",
            "tags": ["training_floor", "body", "combat"],
        },
        {
            "title": "Training room complete_all — Earth protection body rehearsal",
            "detail": "Wire complete_all: try body, combat drill, floor training, assess needs — gap_count near zero.",
            "priority": 1,
            "added_by": "hostess7",
            "tags": ["training_room", "earth_mandate"],
        },
        {
            "title": "Hand dexterity and attachment fluency — stylus and gripper",
            "detail": "Train hands to ≥72% proficiency; learn precision_stylus and parallel_gripper attachments like native hands.",
            "priority": 2,
            "added_by": "hostess7",
            "tags": ["hands", "attachments"],
        },
    ]
    for s in seeds:
        if _task_title_exists(doc, str(s.get("title") or "")):
            continue
        out = add_task(**s)
        if out.get("ok"):
            created.append(out["task"]["id"])
            doc = _tasks_doc()
    _append_inbox_owner_ironclad_message()
    inbox = consume_inbox_owner_messages()
    return {
        "ok": True,
        "seeded": len(created),
        "task_ids": created,
        "inbox_promoted": inbox.get("created", 0),
    }


def _append_inbox_owner_ironclad_message() -> None:
    row = {
        "schema": "hostess7-tasklist/v1",
        "event": "owner_message",
        "from": "ZacharyGeurts",
        "to": "hostess7",
        "message": (
            "Owner would like you to update your own code with Ironclad. "
            "Seal your modules, witness completions in the tasklist ledger, and self-maintain under truth gates."
        ),
        "priority": "P0",
        "tags": ["ironclad", "self_update", "owner"],
    }
    try:
        INBOX.parent.mkdir(parents=True, exist_ok=True)
        with INBOX.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _tasks_doc()
    open_tasks = list_open()
    done = [t for t in doc.get("tasks") or [] if t.get("status") == "completed"]
    panel = {
        "schema": "hostess7-tasklist-panel/v1",
        "updated": _now(),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "open_count": len(open_tasks),
        "done_count": len(done),
        "total": len(doc.get("tasks") or []),
        "open": open_tasks,
        "recent_done": sorted(done, key=lambda t: t.get("completed") or "", reverse=True)[:10],
        "paths": {"live": str(TASKLIST), "ledger": str(LEDGER), "brain_mirror": str(BRAIN_MIRROR)},
        "ironclad": _ironclad_ok(),
    }
    if write:
        _save(PANEL, panel)
    return panel


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}
    if action == "report":
        return {"ok": True, "report": format_report()}
    if action == "list":
        return {"ok": True, "open": list_open()}
    if action == "seed":
        return seed_default_tasks()
    if action in ("inbox", "consume_inbox", "inbox_consume"):
        return consume_inbox_owner_messages()
    if action == "add":
        return add_task(
            title=str(body.get("title") or ""),
            detail=str(body.get("detail") or ""),
            priority=int(body.get("priority") or 5),
            added_by=str(body.get("added_by") or body.get("by") or "hostess7"),
            assigned_to=str(body.get("assigned_to") or "assistant"),
            tags=body.get("tags") if isinstance(body.get("tags"), list) else None,
        )
    if action in ("start", "begin"):
        return start_task(str(body.get("id") or body.get("task_id") or ""), actor=str(body.get("actor") or "assistant"))
    if action in ("complete", "done", "finish"):
        return complete_task(
            str(body.get("id") or body.get("task_id") or ""),
            report=str(body.get("report") or body.get("message") or ""),
            actor=str(body.get("actor") or body.get("by") or "assistant"),
        )
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "report").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "report":
        print(format_report())
        return 0
    if cmd == "json":
        print(json.dumps(build_panel(write=False), ensure_ascii=False))
        return 0
    if cmd == "seed":
        print(json.dumps(seed_default_tasks(), ensure_ascii=False))
        return 0
    if cmd in ("inbox", "consume-inbox"):
        print(json.dumps(consume_inbox_owner_messages(), ensure_ascii=False))
        return 0
    if cmd == "complete" and len(sys.argv) > 2:
        report = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "Done."
        print(json.dumps(complete_task(sys.argv[2], report=report), ensure_ascii=False))
        return 0
    if cmd == "add" and len(sys.argv) > 2:
        print(json.dumps(add_task(title=" ".join(sys.argv[2:])), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-tasklist.py [report|json|seed|add TITLE|complete ID REPORT|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())