#!/usr/bin/env pythong
"""Hostess 7 operator — Brief · Evaluate · Task · catalog (knows what each task does)."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
DOCTRINE = INSTALL / "data" / "hostess7-operator-doctrine.json"
PRINCIPLES = INSTALL / "data" / "ammoos-core-principles-doctrine.json"
AML_DOCTRINE = INSTALL / "data" / "field-ammolang-build-doctrine.json"
PANEL = STATE / "hostess7-operator-panel.json"


def _now() -> str:
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


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _py_json(rel: str, args: list[str], *, timeout: int = 60) -> dict[str, Any]:
    py = os.environ.get("NEXUS_PYTHONG", sys.executable)
    path = INSTALL / rel
    if not path.is_file():
        return {"ok": False, "error": "missing", "path": rel}
    try:
        proc = subprocess.run(
            [py, str(path), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)[:200]}


def task_catalog() -> dict[str, Any]:
    op = _load(DOCTRINE, {})
    aml = _load(AML_DOCTRINE, {})
    registry = aml.get("task_registry") or {}
    descriptions = op.get("ammolang_tasks") or {}
    tasks: list[dict[str, Any]] = []
    seen: set[str] = set()
    for alias, route in registry.items():
        if route in seen:
            continue
        seen.add(route)
        tasks.append({
            "id": route,
            "aliases": [k for k, v in registry.items() if v == route],
            "route": f"lib/ammolang-run.sh {alias}",
            "description": descriptions.get(route) or descriptions.get(alias) or f"AmmoLang task route: {route}",
            "aml_script": (aml.get("script_routes") or {}).get(route),
        })
    tasks.sort(key=lambda t: t["id"])
    return {
        "ok": True,
        "schema": "hostess7-task-catalog/v1",
        "ts": _now(),
        "count": len(tasks),
        "tasks": tasks,
        "router": "lib/ammolang-run.sh",
        "never_bypass": "Route field tasks through AmmoLang — Monster shell + hang guard.",
    }


def brief(message: str = "") -> dict[str, Any]:
    msg = (message or "").strip() or (
        "Hostess 7 operator brief — virtual workspace first; AmmoLang for field tasks; "
        "AmmoOS principles: simple, informative, secure, protecting, no hostility."
    )
    inbox: dict[str, Any] = {"ok": False}
    brain = HOSTESS7 / "scripts" / "field_superintelligence.py"
    if brain.is_file():
        py = os.environ.get("NEXUS_PYTHONG", sys.executable)
        try:
            proc = subprocess.run(
                [py, str(brain), "inbox", msg[:480]],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(HOSTESS7),
            )
            inbox = {"ok": proc.returncode == 0, "rc": proc.returncode}
        except (subprocess.TimeoutExpired, OSError) as exc:
            inbox = {"ok": False, "error": str(exc)}
    self_view = _py_json("lib/hostess7-self-view.py", ["json"], timeout=45)
    tasklist = _py_json("lib/hostess7-tasklist.py", ["json"], timeout=20)
    virtual = _py_json("lib/hostess7-virtual-workspace.py", ["json"], timeout=15)
    principles = _load(PRINCIPLES, {})
    catalog = task_catalog()
    doc = {
        "schema": "hostess7-operator-brief/v1",
        "ok": True,
        "ts": _now(),
        "message": msg,
        "inbox": inbox,
        "principles": principles.get("principles"),
        "self_view_ok": self_view.get("ok"),
        "open_tasks": (tasklist.get("open_count") if tasklist.get("ok") else None),
        "virtual_files": virtual.get("file_count"),
        "task_count": catalog.get("count"),
        "mandate": principles.get("hostess7_mandate"),
        "virtual_first": True,
    }
    return doc


def evaluate() -> dict[str, Any]:
    brain = _py_json("lib/hostess7-brain-guard.py", ["verify"], timeout=30)
    training = _py_json("lib/hostess7-training.py", ["assess"], timeout=60)
    codecraft = _py_json("lib/hostess7-codecraft.py", ["battery"], timeout=45)
    virtual = _py_json("lib/hostess7-virtual-workspace.py", ["json"], timeout=15)
    programming = _py_json("lib/hostess7-programming.py", ["json"], timeout=20)
    gates = {
        "brain_guard": bool(brain.get("ok") or brain.get("verified")),
        "training": bool(training.get("ok")),
        "codecraft": bool(codecraft.get("ok") or (codecraft.get("battery") or {}).get("passed")),
        "virtual_ready": virtual.get("ok"),
        "programming": programming.get("ok"),
    }
    ok = all(gates.values()) if gates else False
    return {
        "schema": "hostess7-operator-evaluate/v1",
        "ok": ok,
        "ts": _now(),
        "gates": gates,
        "brain_guard": brain,
        "training": {"ok": training.get("ok"), "gaps": training.get("gaps")},
        "codecraft": {"ok": codecraft.get("ok"), "score": codecraft.get("score")},
        "virtual": {"file_count": virtual.get("file_count"), "test_before_apply": True},
        "verdict": "ready" if ok else "gaps_remain",
        "virtual_first_reminder": "Edit in hostess7-virtual before live INSTALL.",
    }


def task_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    tl = _import_mod("hostess7_tasklist_op", "lib/hostess7-tasklist.py")
    if not tl or not hasattr(tl, "dispatch"):
        return _py_json("lib/hostess7-tasklist.py", ["dispatch"], timeout=30)
    return tl.dispatch(body)


def build_panel() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    cat = task_catalog()
    ev = evaluate()
    change_awareness: dict[str, Any] = {}
    ca_py = INSTALL / "lib" / "hostess7-change-awareness.py"
    if ca_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_ca_op", ca_py)
            if spec and spec.loader:
                cam = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cam)
                if hasattr(cam, "build_panel"):
                    change_awareness = cam.build_panel(write=False)
        except Exception:
            pass
    panel = {
        "schema": "hostess7-operator-panel/v1",
        "ok": True,
        "ts": _now(),
        "motto": doc.get("motto"),
        "capabilities": doc.get("capabilities"),
        "evaluate_verdict": ev.get("verdict"),
        "gates": ev.get("gates"),
        "task_catalog_count": cat.get("count"),
        "principles": (_load(PRINCIPLES, {}).get("principles") or [])[:5],
        "virtual_first": True,
        "change_awareness": {
            "hostess7_knows_changes": change_awareness.get("hostess7_knows_changes", True),
            "presume_verdict": change_awareness.get("presume_verdict"),
            "presume_timing": change_awareness.get("presume_timing"),
            "recent_change_count": len(change_awareness.get("recent_changes") or []),
        },
        "apis": {
            "brief": "/api/hostess7/operator/brief",
            "evaluate": "/api/hostess7/operator/evaluate",
            "catalog": "/api/hostess7/operator/catalog",
            "tasklist": "/api/hostess7/tasklist",
            "virtual": "/api/hostess7/virtual-workspace",
            "chips_coding": "/api/hostess7/chips-coding/explain",
        },
    }
    _save(PANEL, panel)
    return panel


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "panel").lower().replace("-", "_")
    if action in ("panel", "json", "status"):
        return {"ok": True, **build_panel()}
    if action == "brief":
        return brief(str(body.get("message") or body.get("query") or ""))
    if action in ("evaluate", "assess", "verify"):
        return evaluate()
    if action in ("catalog", "tasks", "task_catalog"):
        return task_catalog()
    if action in ("task", "tasklist"):
        sub = body.get("task_action") or body.get("sub") or "report"
        tb = dict(body)
        tb["action"] = sub
        return task_dispatch(tb)
    if action == "teach_chips":
        vw = _import_mod("h7_vw", "lib/hostess7-virtual-workspace.py")
        if vw and hasattr(vw, "explain_chips"):
            return vw.explain_chips(str(body.get("query") or ""))
        return {"ok": False, "error": "virtual_workspace_missing"}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if args[0] == "brief":
        print(json.dumps(brief(" ".join(args[1:]) if len(args) > 1 else ""), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "evaluate":
        print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "catalog":
        print(json.dumps(task_catalog(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(dispatch({"action": args[0], **dict(zip(args[1::2], args[2::2]))}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())