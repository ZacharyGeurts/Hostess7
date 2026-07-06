#!/usr/bin/env python3
"""Inline sovereign — all panel tasks in-process; no outside screen capture. Just the user."""
from __future__ import annotations

import importlib.util
import json
import os
import pwd
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-inline-sovereign-doctrine.json"
PANEL = STATE / "field-inline-sovereign-panel.json"
LEDGER = STATE / "field-inline-sovereign.jsonl"
ME = os.getpid()


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _sudo_pw() -> str:
    return os.environ.get("HOSTESS7_SUDO_PW", "mememe")


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def operator_user() -> str:
    doc = doctrine()
    return (
        os.environ.get("FIELD_OPERATOR_USER", "").strip()
        or str(doc.get("operator_user") or "")
        or os.environ.get("USER", "default")
    )


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _proc_owner(pid: int) -> str:
    try:
        st = (Path("/proc") / str(pid) / "status").read_text(encoding="utf-8", errors="replace")
        for line in st.splitlines():
            if line.startswith("Uid:"):
                uid = int(line.split()[1])
                return pwd.getpwuid(uid).pw_name
    except (OSError, ValueError, KeyError):
        pass
    return ""


def _protected(cmdline: str, protected: list[str]) -> bool:
    return any(p in cmdline for p in protected)


def _kill_pids(pids: list[int]) -> int:
    if not pids:
        return 0
    pw = _sudo_pw()
    killed = 0
    need: list[int] = []
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
            killed += 1
        except PermissionError:
            need.append(pid)
        except ProcessLookupError:
            killed += 1
        except OSError:
            need.append(pid)
    if need:
        try:
            proc = subprocess.run(
                ["sudo", "-S", "kill", "-9", *[str(p) for p in need]],
                input=f"{pw}\n",
                text=True,
                capture_output=True,
                timeout=8,
                check=False,
            )
            if proc.returncode == 0:
                killed += len(need)
        except (OSError, subprocess.TimeoutExpired):
            pass
    return killed


def enforce_capture_shield(*, write: bool = True) -> dict[str, Any]:
    """No outside Print Screen or screen capture — just the user."""
    doc = doctrine()
    protected = list(doc.get("protected") or [])
    blocked = set(doc.get("blocked_capture_procs") or [])
    print_markers = list(doc.get("print_screen_markers") or [])
    op_user = operator_user()
    victims: list[dict[str, Any]] = []
    pids: list[int] = []

    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        if pid <= 1 or pid == ME:
            continue
        try:
            raw = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
        except OSError:
            continue
        if not raw or _protected(raw, protected):
            continue
        low = raw.lower()
        comm = Path(raw.split()[0]).name.lower() if raw.split() else ""
        hit = comm in blocked or any(f" {b} " in f" {low} " or comm == b for b in blocked)
        hit = hit or any(m.lower() in low for m in print_markers)
        if not hit:
            continue
        owner = _proc_owner(pid)
        reason = "outside_capture" if owner and owner != op_user else "screen_capture"
        victims.append({"pid": pid, "owner": owner, "cmd": raw[:160], "reason": reason})
        pids.append(pid)

    killed = _kill_pids(pids)
    out = {
        "ok": True,
        "schema": "field-inline-sovereign-capture/v1",
        "updated": _utc(),
        "operator_user": op_user,
        "just_the_user": bool(doc.get("just_the_user", True)),
        "no_print_screen": bool(doc.get("no_print_screen", True)),
        "no_screen_capture": bool(doc.get("no_screen_capture", True)),
        "scanned": True,
        "hits": len(victims),
        "killed": killed,
        "victims": victims[:24],
        "motto": "No outside Print Screen or screen capture — just the user.",
    }
    if write:
        panel = _load(PANEL, {})
        panel["capture_shield"] = out
        panel["updated"] = _utc()
        _save(PANEL, panel)
    return out


def run_lane_inline(lane: dict[str, Any]) -> dict[str, Any]:
    """Run one task inline via import — never subprocess."""
    lid = str(lane.get("id") or "lane")
    rel = str(lane.get("module") or "")
    fn_name = str(lane.get("fn") or "json")
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "id": lid, "error": "module_missing", "inline": True}
    mod = _mod(f"inline_{lid}", rel)
    if mod is None:
        return {"ok": False, "id": lid, "error": "import_failed", "inline": True}
    fn = getattr(mod, fn_name, None)
    if not callable(fn):
        return {"ok": False, "id": lid, "error": f"no_fn:{fn_name}", "inline": True}
    kwargs = dict(lane.get("kwargs") or {})
    try:
        result = fn(**kwargs) if kwargs else fn()
        ok = True
        if isinstance(result, dict):
            ok = bool(result.get("ok", True))
        return {"ok": ok, "id": lid, "fn": fn_name, "inline": True, "result": result if isinstance(result, dict) else {"ok": ok}}
    except (OSError, TypeError, ValueError, RuntimeError) as exc:
        return {"ok": False, "id": lid, "fn": fn_name, "inline": True, "error": str(exc)[:160]}


def inline_sweep(*, write: bool = True) -> dict[str, Any]:
    doc = doctrine()
    lanes = list(doc.get("inline_lanes") or [])
    sweep_n = int(_load(PANEL, {}).get("sweep_n") or 0) + 1
    results: list[dict[str, Any]] = []
    for lane in lanes:
        if not isinstance(lane, dict):
            continue
        every = max(1, int(lane.get("every_n") or 1))
        if sweep_n % every != 0:
            continue
        results.append(run_lane_inline(lane))
    ok_n = sum(1 for r in results if r.get("ok"))
    out = {
        "ok": ok_n >= max(1, len(results) - 1) if results else True,
        "schema": "field-inline-sovereign/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "no_subprocess_panels": bool(doc.get("no_subprocess_panels", True)),
        "operator_user": operator_user(),
        "sweep_n": sweep_n,
        "lanes_run": len(results),
        "lanes_ok": ok_n,
        "lanes": results,
        "api": doc.get("api"),
    }
    if write:
        prev = _load(PANEL, {})
        prev.update(out)
        _save(PANEL, prev)
        _append_ledger({"sweep_n": sweep_n, "lanes_ok": ok_n, "lanes_run": len(results)})
    return out


def serve() -> int:
    while True:
        try:
            inline_sweep(write=True)
        except Exception as exc:
            err = {"ok": False, "error": str(exc)[:200], "ts": _utc()}
            try:
                _save(PANEL, err)
            except OSError:
                pass


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    return inline_sweep(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("serve", "watch", "daemon"):
        serve()
        return 0
    if cmd in ("capture", "shield", "no-capture"):
        print(json.dumps(enforce_capture_shield(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("sweep", "run", "inline"):
        print(json.dumps(inline_sweep(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-inline-sovereign.py [serve|sweep|capture|json]",
        "motto": doctrine().get("motto"),
        "api": "/api/field-inline-sovereign",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())