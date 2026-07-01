#!/usr/bin/env pythong
"""Hostess 7 virtual workspace — test in virtual die before promoting to live INSTALL."""
from __future__ import annotations

import hashlib
import json
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-virtual-workspace-doctrine.json"
VROOT = STATE / "hostess7-virtual"
VINSTALL = VROOT / "install"
VSTATE = VROOT / "state"
MANIFEST = VROOT / "manifest.json"
PANEL = STATE / "hostess7-virtual-workspace-panel.json"
LEDGER = STATE / "hostess7-virtual-workspace-ledger.jsonl"
EXPLAIN = INSTALL / "data" / "hostess7-chips-coding-explain.json"


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


def _log(event: str, **fields: Any) -> None:
    row = {"schema": "hostess7-virtual-workspace-ledger/v1", "ts": _now(), "event": event, **fields}
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _normalize_rel(path: str) -> str:
    p = str(path or "").strip().lstrip("/")
    if p.startswith("NewLatest/"):
        p = p.split("NewLatest/", 1)[-1]
    return p


def _live_path(rel: str) -> Path:
    rel = _normalize_rel(rel)
    return INSTALL / rel


def _virtual_path(rel: str) -> Path:
    rel = _normalize_rel(rel)
    return VINSTALL / rel


def _allowed(rel: str) -> bool:
    doc = _doctrine()
    rel = _normalize_rel(rel)
    forbidden = {str(x) for x in (doc.get("forbidden_live_write") or [])}
    if rel in forbidden:
        return False
    prefixes = [str(x) for x in (doc.get("editable_prefixes") or [])]
    if prefixes:
        return any(rel.startswith(p) or rel.endswith(p.replace("lib/", "")) for p in prefixes) or rel.startswith("lib/hostess7")
    return rel.startswith("lib/hostess7") or rel.startswith("data/hostess7")


def ensure_workspace() -> dict[str, Any]:
    VINSTALL.mkdir(parents=True, exist_ok=True)
    VSTATE.mkdir(parents=True, exist_ok=True)
    if not MANIFEST.is_file():
        _save(MANIFEST, {"schema": "hostess7-virtual-manifest/v1", "files": {}, "updated": _now()})
    return {"ok": True, "root": str(VROOT), "install": str(VINSTALL)}


def _manifest() -> dict[str, Any]:
    ensure_workspace()
    return _load(MANIFEST, {"files": {}})


def _sha(path: Path) -> str:
    if not path.is_file():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def mirror(rel: str) -> dict[str, Any]:
    rel = _normalize_rel(rel)
    if not _allowed(rel):
        return {"ok": False, "error": "path_not_allowed", "path": rel}
    src = _live_path(rel)
    if not src.is_file():
        return {"ok": False, "error": "source_missing", "path": rel}
    dst = _virtual_path(rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    man = _manifest()
    files = man.setdefault("files", {})
    files[rel] = {"mirrored": _now(), "live_sha": _sha(src), "virtual_sha": _sha(dst)}
    man["updated"] = _now()
    _save(MANIFEST, man)
    _log("mirror", path=rel)
    return {"ok": True, "mirrored": rel, "virtual": str(dst)}


def write_virtual(rel: str, content: str) -> dict[str, Any]:
    rel = _normalize_rel(rel)
    if not _allowed(rel):
        return {"ok": False, "error": "path_not_allowed", "path": rel}
    dst = _virtual_path(rel)
    if not dst.is_file():
        mirror(rel)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content, encoding="utf-8")
    man = _manifest()
    files = man.setdefault("files", {})
    entry = files.setdefault(rel, {})
    entry["edited"] = _now()
    entry["virtual_sha"] = _sha(dst)
    man["updated"] = _now()
    _save(MANIFEST, man)
    _log("write", path=rel, bytes=len(content.encode("utf-8")))
    return {"ok": True, "path": rel, "virtual_sha": entry.get("virtual_sha")}


def _py_compile_ok(path: Path) -> dict[str, Any]:
    try:
        py_compile.compile(str(path), doraise=True)
        return {"ok": True}
    except py_compile.PyCompileError as exc:
        return {"ok": False, "error": str(exc)}


def _smoke_module(rel: str, argv: list[str] | None = None) -> dict[str, Any]:
    rel = _normalize_rel(rel)
    vpath = _virtual_path(rel)
    if not vpath.is_file():
        return {"ok": False, "error": "virtual_missing", "path": rel}
    comp = _py_compile_ok(vpath)
    if not comp.get("ok"):
        return {"ok": False, "stage": "py_compile", **comp}
    py = os.environ.get("NEXUS_PYTHONG", sys.executable)
    args = argv or ["json"]
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(VINSTALL),
        "NEXUS_STATE_DIR": str(VSTATE),
        "HOSTESS7_VIRTUAL": "1",
        "HOSTESS7_VIRTUAL_ROOT": str(VROOT),
    }
    try:
        proc = subprocess.run(
            [py, str(vpath), *args],
            capture_output=True,
            text=True,
            timeout=45,
            env=env,
            cwd=str(VINSTALL),
        )
        ok = proc.returncode == 0
        out = (proc.stdout or "").strip()[:2000]
        err = (proc.stderr or "").strip()[:1200]
        return {"ok": ok, "stage": "smoke", "rc": proc.returncode, "stdout": out, "stderr": err, "die": "gpy16_python"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "stage": "smoke", "error": "timeout"}


def test(rel: str) -> dict[str, Any]:
    rel = _normalize_rel(rel)
    smoke = _smoke_module(rel)
    _log("test", path=rel, ok=smoke.get("ok"))
    return {"ok": smoke.get("ok"), "path": rel, "results": smoke}


def debug(rel: str, argv: list[str] | None = None) -> dict[str, Any]:
    rel = _normalize_rel(rel)
    res = _smoke_module(rel, argv or ["json"])
    _log("debug", path=rel, ok=res.get("ok"), stderr=(res.get("stderr") or "")[:200])
    teach = explain_chips("debug virtual workspace chips")
    return {"ok": res.get("ok"), "path": rel, "run": res, "teach_hint": teach.get("matched")}


def _testing_center_fast() -> dict[str, Any]:
    cc = INSTALL / "lib" / "hostess7-codecraft.py"
    if not cc.is_file():
        return {"ok": True, "skipped": True}
    py = os.environ.get("NEXUS_PYTHONG", sys.executable)
    try:
        proc = subprocess.run(
            [py, str(cc), "testing-center", "--fast"],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(INSTALL),
        )
        try:
            doc = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            doc = {"ok": proc.returncode == 0}
        return {"ok": bool(doc.get("ok", proc.returncode == 0)), "panel": doc}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "testing_center_timeout"}


def promote(rel: str, *, confirm: str = "") -> dict[str, Any]:
    rel = _normalize_rel(rel)
    need = _doctrine().get("policy", {}).get("confirm_phrase", "PROMOTE")
    if confirm != need:
        return {"ok": False, "error": "confirm_required", "need": need}
    if not _allowed(rel):
        return {"ok": False, "error": "path_not_allowed"}
    vpath = _virtual_path(rel)
    lpath = _live_path(rel)
    if not vpath.is_file():
        return {"ok": False, "error": "virtual_missing"}
    test_res = test(rel)
    if not test_res.get("ok"):
        return {"ok": False, "error": "virtual_test_failed", "test": test_res}
    tc = _testing_center_fast()
    if not tc.get("ok"):
        return {"ok": False, "error": "testing_center_failed", "testing_center": tc}
    lpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(vpath, lpath)
    _log("promote", path=rel, live_sha=_sha(lpath))
    man = _manifest()
    files = man.setdefault("files", {})
    entry = files.setdefault(rel, {})
    entry["promoted"] = _now()
    entry["live_sha"] = _sha(lpath)
    man["updated"] = _now()
    _save(MANIFEST, man)
    return {"ok": True, "promoted": rel, "live": str(lpath), "testing_center": tc.get("ok")}


def explain_chips(query: str = "") -> dict[str, Any]:
    doc = _load(EXPLAIN, {})
    q = (query or "").lower()
    topics = doc.get("topics") or []
    matched = None
    for t in topics:
        keys = [str(k).lower() for k in (t.get("keywords") or [])]
        if any(k in q for k in keys) or (t.get("id") or "") in q:
            matched = t
            break
    if not matched and topics:
        matched = topics[0]
    sections = {}
    if matched:
        for key in ("what", "why", "how", "pitfalls", "where", "example"):
            if matched.get(key):
                sections[key] = matched[key]
    return {
        "ok": True,
        "schema": doc.get("schema"),
        "chosen_die": doc.get("chosen_die"),
        "workflow": doc.get("workflow"),
        "matched": matched.get("id") if matched else None,
        "sections": sections,
        "introduction": doc.get("introduction"),
    }


def build_panel() -> dict[str, Any]:
    ensure_workspace()
    man = _manifest()
    files = man.get("files") or {}
    return {
        "schema": "hostess7-virtual-workspace-panel/v1",
        "ok": True,
        "ts": _now(),
        "motto": _doctrine().get("motto"),
        "virtual_root": str(VROOT),
        "file_count": len(files),
        "files": files,
        "policy": _doctrine().get("policy"),
        "chips_die": _doctrine().get("chips_die"),
        "test_before_apply": True,
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel()}
    if action == "ensure":
        return ensure_workspace()
    if action == "mirror":
        return mirror(str(body.get("path") or body.get("rel") or ""))
    if action == "write":
        return write_virtual(str(body.get("path") or ""), str(body.get("content") or ""))
    if action in ("test", "compile"):
        return test(str(body.get("path") or ""))
    if action == "debug":
        argv = body.get("argv") if isinstance(body.get("argv"), list) else None
        return debug(str(body.get("path") or ""), argv)
    if action == "promote":
        return promote(str(body.get("path") or ""), confirm=str(body.get("confirm") or ""))
    if action in ("teach", "explain", "chips"):
        return explain_chips(str(body.get("query") or body.get("q") or ""))
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
    if args[0] == "teach":
        q = " ".join(args[1:]) if len(args) > 1 else ""
        print(json.dumps(explain_chips(q), ensure_ascii=False, indent=2))
        return 0
    if args[0] == "mirror" and len(args) > 1:
        print(json.dumps(mirror(args[1]), ensure_ascii=False))
        return 0
    if args[0] == "test" and len(args) > 1:
        print(json.dumps(test(args[1]), ensure_ascii=False))
        return 0
    if args[0] == "promote" and len(args) > 1:
        confirm = args[2] if len(args) > 2 else ""
        print(json.dumps(promote(args[1], confirm=confirm), ensure_ascii=False))
        return 0
    print(json.dumps(dispatch({"action": args[0], **dict(zip(args[1::2], args[2::2]))}), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())