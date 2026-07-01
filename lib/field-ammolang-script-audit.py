#!/usr/bin/env python3
"""AmmoLang script audit — one script at a time, agent repair reports, no batching."""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "ammolang-script-audit-panel.json"
STATE_FILE = STATE / "ammolang-script-audit-state.json"
REPAIRS = STATE / "ammolang-script-audit-repairs.json"
LEDGER = STATE / "ammolang-script-audit.jsonl"
AML_MARKER = "# AmmoLang boundary route"


def _now() -> str:
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


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": row.get("ts") or _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _boundary_mod() -> Any | None:
    path = INSTALL / "lib" / "field-ammolang-boundary.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_ammolang_boundary_audit", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _build_mod() -> Any | None:
    path = INSTALL / "lib" / "field-ammolang-build.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_ammolang_build_audit", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_queue(*, refresh: bool = False) -> list[dict[str, Any]]:
    boundary = _boundary_mod()
    if not boundary or not hasattr(boundary, "scan_registry"):
        return []
    reg = boundary.scan_registry(refresh=refresh)
    entries = list(reg.get("entries") or [])
    return sorted(entries, key=lambda e: (str(e.get("kind", "")), str(e.get("id", ""))))


def _audit_state() -> dict[str, Any]:
    doc = _load(STATE_FILE, {})
    if doc.get("schema") != "ammolang-script-audit-state/v1":
        doc = {"schema": "ammolang-script-audit-state/v1", "results": {}, "index": 0}
    doc.setdefault("results", {})
    doc.setdefault("index", 0)
    return doc


def _check_bash_syntax(path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return {
            "id": "bash_syntax",
            "ok": proc.returncode == 0,
            "detail": (proc.stderr or proc.stdout or "").strip()[-400:],
        }
    except Exception as exc:
        return {"id": "bash_syntax", "ok": False, "detail": str(exc)[:200]}


def _check_py_syntax(path: Path) -> dict[str, Any]:
    try:
        src = path.read_text(encoding="utf-8", errors="replace")
        ast.parse(src, filename=str(path))
        return {"id": "py_syntax", "ok": True}
    except SyntaxError as exc:
        return {"id": "py_syntax", "ok": False, "detail": f"line {exc.lineno}: {exc.msg}"}
    except OSError as exc:
        return {"id": "py_syntax", "ok": False, "detail": str(exc)[:200]}


def _check_aml_boundary(path: Path) -> dict[str, Any]:
    try:
        head = path.read_text(encoding="utf-8", errors="replace")[:2048]
    except OSError as exc:
        return {"id": "aml_boundary", "ok": False, "detail": str(exc)[:120]}
    wired = AML_MARKER in head or ("ammolang-run.sh" in head and "AML_BOUNDARY" in head)
    return {"id": "aml_boundary", "ok": wired, "detail": "wired" if wired else "missing AML boundary shim"}


def _check_resolve(entry: dict[str, Any], boundary: Any) -> dict[str, Any]:
    eid = str(entry.get("id", ""))
    kind = str(entry.get("kind", ""))
    target = ""
    if kind == "route":
        target = f"route:{entry.get('route', eid)}"
    elif kind == "py":
        mod = str(entry.get("module") or Path(str(entry.get("path", ""))).stem)
        target = f"py:{mod}"
    elif kind == "script":
        target = f"script:{entry.get('path', '')}"
    elif kind == "hostess7":
        target = "hostess7:status"
    else:
        return {"id": "resolve", "ok": True, "detail": "skipped_unknown_kind"}
    try:
        spec = boundary.resolve_target(target, [])
        ok = bool(spec.get("kind") and spec.get("kind") != "unknown" and not spec.get("error"))
        if spec.get("warning"):
            ok = ok or spec.get("kind") == "bash"
        return {
            "id": "resolve",
            "ok": ok,
            "detail": spec.get("error") or spec.get("via") or spec.get("kind"),
            "target": target,
        }
    except Exception as exc:
        return {"id": "resolve", "ok": False, "detail": str(exc)[:200], "target": target}


def _check_aml_file(rel: str) -> dict[str, Any]:
    path = INSTALL / rel
    if not path.is_file():
        return {"id": "aml_file", "ok": False, "detail": f"missing {rel}"}
    build = _build_mod()
    if build and hasattr(build, "execute_build_script"):
        try:
            doc = build.execute_build_script(path, live=False, verbose=False)
            return {"id": "aml_compile", "ok": bool(doc.get("ok")), "detail": doc.get("error") or "dry_compile_ok"}
        except Exception as exc:
            return {"id": "aml_compile", "ok": False, "detail": str(exc)[:200]}
    return {"id": "aml_file", "ok": True, "detail": "present"}


def audit_one(entry: dict[str, Any]) -> dict[str, Any]:
    """Check a single registry entry — never batches with others."""
    eid = str(entry.get("id", ""))
    kind = str(entry.get("kind", ""))
    rel = str(entry.get("path") or entry.get("aml") or "")
    checks: list[dict[str, Any]] = []
    boundary = _boundary_mod()

    if kind == "route":
        checks.append(_check_aml_file(str(entry.get("aml") or rel)))
        if boundary:
            checks.append(_check_resolve(entry, boundary))
    elif kind == "script":
        path = INSTALL / rel
        checks.append({"id": "exists", "ok": path.is_file(), "detail": rel})
        if path.is_file():
            checks.append(_check_bash_syntax(path))
            checks.append(_check_aml_boundary(path))
            if boundary:
                checks.append(_check_resolve(entry, boundary))
    elif kind == "py":
        path = INSTALL / rel
        checks.append({"id": "exists", "ok": path.is_file(), "detail": rel})
        if path.is_file():
            checks.append(_check_py_syntax(path))
            if boundary:
                checks.append(_check_resolve(entry, boundary))
    elif kind == "hostess7":
        path = INSTALL / "Hostess7" / "Hostess7.sh"
        checks.append({"id": "exists", "ok": path.is_file(), "detail": "Hostess7/Hostess7.sh"})
        if path.is_file():
            checks.append(_check_bash_syntax(path))
            if boundary:
                checks.append(_check_resolve(entry, boundary))
    else:
        checks.append({"id": "kind", "ok": False, "detail": f"unknown kind {kind}"})

    failed = [c for c in checks if not c.get("ok")]
    ok = not failed
    rep = {
        "schema": "ammolang-script-audit-entry/v1",
        "id": eid,
        "kind": kind,
        "path": rel,
        "ok": ok,
        "checks": checks,
        "failed": [c["id"] for c in failed],
        "checked_at": _now(),
    }
    _append({"event": "audit_one", "id": eid, "ok": ok, "failed": rep["failed"]})
    return rep


def _repair_hints(entry: dict[str, Any], result: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    rel = str(entry.get("path") or entry.get("aml") or "")
    for check in result.get("checks") or []:
        if check.get("ok"):
            continue
        cid = check.get("id")
        if cid == "aml_boundary" and rel:
            hints.append(f"./lib/ammolang-run.sh ensure_protection  # or: python3 lib/field-ammolang-boundary.py wire-all --apply")
        elif cid == "bash_syntax":
            hints.append(f"Fix bash syntax in {rel}: {check.get('detail', '')}")
        elif cid == "py_syntax":
            hints.append(f"Fix Python syntax in {rel}: {check.get('detail', '')}")
        elif cid == "exists":
            hints.append(f"Restore or remove registry entry for missing file: {rel}")
        elif cid in ("aml_file", "aml_compile"):
            hints.append(f"Repair AML route file: {entry.get('aml') or rel}")
        elif cid == "resolve":
            hints.append(f"Fix boundary resolution for {entry.get('id')}: {check.get('detail', '')}")
    if not hints:
        hints.append("Inspect checks[] in repair report and fix manually.")
    return hints


def write_repair_report(entry: dict[str, Any], result: dict[str, Any], *, queue: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
    pending = sum(1 for e in queue if not (state.get("results") or {}).get(str(e.get("id")), {}).get("ok"))
    doc = {
        "schema": "ammolang-script-audit-repair/v1",
        "updated": _now(),
        "agent_action": "fix_script_then_rerun_master",
        "master_command": "./lib/ammolang-run.sh script_audit",
        "alt_command": "python3 lib/field-ammolang-script-audit.py run",
        "stop_policy": "one_script_per_pass_no_batch",
        "current": {
            "id": result.get("id"),
            "kind": result.get("kind"),
            "path": result.get("path"),
            "failed_checks": result.get("failed"),
            "checks": result.get("checks"),
            "hints": _repair_hints(entry, result),
        },
        "remaining_pending": pending,
        "progress": {
            "passed": sum(1 for r in (state.get("results") or {}).values() if r.get("ok")),
            "failed": sum(1 for r in (state.get("results") or {}).values() if not r.get("ok")),
            "total": len(queue),
        },
    }
    _save(REPAIRS, doc)
    return doc


def write_panel(*, queue: list[dict[str, Any]], state: dict[str, Any], last: dict[str, Any] | None = None) -> dict[str, Any]:
    results = state.get("results") or {}
    passed = sum(1 for e in queue if results.get(str(e.get("id")), {}).get("ok"))
    failed = sum(1 for e in queue if str(e.get("id")) in results and not results[str(e.get("id"))].get("ok"))
    pending = len(queue) - passed - failed
    doc = {
        "schema": "ammolang-script-audit-panel/v1",
        "updated": _now(),
        "motto": "One script per pass — sequential audit, agent repair queue, no batching",
        "total": len(queue),
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "complete": pending == 0 and failed == 0,
        "next_index": state.get("index", 0),
        "last": last,
        "repairs_path": str(REPAIRS),
        "state_path": str(STATE_FILE),
    }
    _save(PANEL, doc)
    return doc


def _next_pending(queue: list[dict[str, Any]], state: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
    results = state.get("results") or {}
    start = int(state.get("index") or 0)
    for i in range(start, len(queue)):
        eid = str(queue[i].get("id", ""))
        prev = results.get(eid)
        if not prev or not prev.get("ok"):
            return i, queue[i]
    for i, entry in enumerate(queue):
        eid = str(entry.get("id", ""))
        prev = results.get(eid)
        if not prev or not prev.get("ok"):
            return i, entry
    return None


def run_one(*, force_id: str | None = None) -> dict[str, Any]:
    queue = load_queue(refresh=False)
    if not queue:
        return {"ok": False, "error": "empty_queue", "hint": "python3 lib/field-ammolang-boundary.py scan"}

    state = _audit_state()
    if force_id:
        entry = next((e for e in queue if str(e.get("id")) == force_id), None)
        if not entry:
            return {"ok": False, "error": "unknown_id", "id": force_id}
        idx = queue.index(entry)
    else:
        nxt = _next_pending(queue, state)
        if not nxt:
            panel = write_panel(queue=queue, state=state)
            return {"ok": True, "complete": True, "message": "all_scripts_clean", "panel": panel}
        idx, entry = nxt

    result = audit_one(entry)
    eid = str(entry.get("id", ""))
    state["results"][eid] = result
    state["index"] = idx + 1 if result.get("ok") else idx
    state["last_id"] = eid
    state["updated"] = _now()
    _save(STATE_FILE, state)

    panel = write_panel(queue=queue, state=state, last=result)
    out: dict[str, Any] = {
        "ok": result.get("ok"),
        "complete": False,
        "mode": "one_script",
        "index": idx,
        "total": len(queue),
        "entry": entry,
        "result": result,
        "panel": panel,
    }
    if not result.get("ok"):
        out["repair"] = write_repair_report(entry, result, queue=queue, state=state)
        out["agent_note"] = "STOP — fix current script, then rerun ./lib/ammolang-run.sh script_audit"
    else:
        pending = panel.get("pending", 0) + panel.get("failed", 0)
        out["complete"] = pending == 0
        if out["complete"]:
            out["message"] = "all_scripts_clean"
    return out


def run_drain() -> dict[str, Any]:
    """Sequential one-by-one in a single process — still not parallel/batch."""
    steps: list[dict[str, Any]] = []
    while True:
        rep = run_one()
        steps.append({"id": rep.get("entry", {}).get("id"), "ok": rep.get("ok")})
        if not rep.get("ok"):
            rep["drain_stopped"] = True
            rep["steps"] = steps
            return rep
        if rep.get("complete"):
            rep["drain_complete"] = True
            rep["steps"] = steps
            return rep


def cmd_queue() -> dict[str, Any]:
    queue = load_queue(refresh=False)
    state = _audit_state()
    results = state.get("results") or {}
    rows = []
    for i, entry in enumerate(queue):
        eid = str(entry.get("id", ""))
        prev = results.get(eid)
        rows.append({
            "index": i,
            "id": eid,
            "kind": entry.get("kind"),
            "path": entry.get("path") or entry.get("aml"),
            "status": "pass" if prev and prev.get("ok") else "fail" if prev else "pending",
        })
    return {"ok": True, "count": len(rows), "queue": rows}


def cmd_reset() -> dict[str, Any]:
    _save(STATE_FILE, {"schema": "ammolang-script-audit-state/v1", "results": {}, "index": 0, "reset_at": _now()})
    if REPAIRS.is_file():
        REPAIRS.unlink(missing_ok=True)
    queue = load_queue(refresh=False)
    panel = write_panel(queue=queue, state=_audit_state())
    return {"ok": True, "reset": True, "panel": panel}


def cmd_report() -> dict[str, Any]:
    doc = _load(REPAIRS, {})
    if not doc:
        queue = load_queue(refresh=False)
        state = _audit_state()
        nxt = _next_pending(queue, state)
        if not nxt:
            return {"ok": True, "message": "no_repairs_needed", "complete": True}
        return {"ok": True, "message": "no_failure_report_yet", "next_id": queue[nxt[0]].get("id")}
    return doc


def main() -> int:
    args = sys.argv[1:]
    cmd = (args[0] if args else "status").strip().lower()

    if cmd in ("status", "panel"):
        queue = load_queue(refresh=False)
        panel = write_panel(queue=queue, state=_audit_state())
        print(json.dumps(panel, ensure_ascii=False, indent=2))
        return 0
    if cmd == "queue":
        print(json.dumps(cmd_queue(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "reset":
        print(json.dumps(cmd_reset(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "report":
        print(json.dumps(cmd_report(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        queue = load_queue(refresh=True)
        print(json.dumps({"ok": True, "count": len(queue)}, indent=2))
        return 0
    if cmd == "check" and len(args) > 1:
        rep = run_one(force_id=args[1])
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1
    if cmd == "run":
        if "--drain" in args:
            rep = run_drain()
        else:
            rep = run_one()
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok") else 1

    print(json.dumps({
        "error": "usage",
        "hint": "field-ammolang-script-audit.py [status|queue|run|run --drain|check ID|report|reset|scan]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())