#!/usr/bin/env pythong
"""Hostess 7 hang & freeze detection — heartbeat, stall verdict, guarded subprocess."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
PANEL = STATE / "hostess7-hang-guard-panel.json"
LEDGER = STATE / "hostess7-hang-guard-ledger.jsonl"

DEFAULT_STALL_SEC = float(os.environ.get("HOSTESS7_HANG_STALL_SEC", "45"))
DEFAULT_TIMEOUT_SEC = float(os.environ.get("HOSTESS7_HANG_TIMEOUT_SEC", "600"))


def _ts() -> str:
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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _ts()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


class HangGuard:
    """Context manager — ticks heartbeat; records stall if gap exceeds stall_sec."""

    def __init__(
        self,
        label: str,
        *,
        stall_sec: float = DEFAULT_STALL_SEC,
        heartbeat_path: Path | None = None,
        on_stall: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.label = (label or "operation").strip()[:120]
        self.stall_sec = max(5.0, float(stall_sec))
        self.heartbeat_path = heartbeat_path or (STATE / f"hang-{self.label.replace(' ', '_')[:48]}.json")
        self.on_stall = on_stall
        self._started = 0.0
        self._last_tick = 0.0
        self._stalls = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _write(self, extra: dict[str, Any] | None = None) -> None:
        doc = {
            "schema": "hostess7-hang-heartbeat/v1",
            "updated": _ts(),
            "label": self.label,
            "epoch": time.time(),
            "stall_sec": self.stall_sec,
            "stall_count": self._stalls,
            "alive": not self._stop.is_set(),
            **(extra or {}),
        }
        _save(self.heartbeat_path, doc)

    def tick(self, *, note: str = "") -> None:
        self._last_tick = time.time()
        self._write({"note": note[:200] if note else None})

    def _watch(self) -> None:
        while not self._stop.wait(5.0):
            now = time.time()
            gap = now - self._last_tick
            if gap >= self.stall_sec:
                self._stalls += 1
                verdict = {
                    "schema": "hostess7-hang-verdict/v1",
                    "updated": _ts(),
                    "label": self.label,
                    "verdict": "stall",
                    "gap_sec": round(gap, 2),
                    "stall_count": self._stalls,
                }
                _append_ledger(verdict)
                if self.on_stall:
                    try:
                        self.on_stall(verdict)
                    except Exception:
                        pass
            self._write({"gap_sec": round(now - self._last_tick, 2)})

    def __enter__(self) -> HangGuard:
        self._started = time.time()
        self._last_tick = self._started
        self._write({"phase": "start"})
        self._thread = threading.Thread(target=self._watch, name=f"hang-guard-{self.label[:24]}", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        elapsed = time.time() - self._started
        self._write({"phase": "done", "elapsed_sec": round(elapsed, 2), "error": type(exc).__name__ if exc else None})


def is_stale(path: Path | str, *, max_age_sec: float = DEFAULT_STALL_SEC) -> bool:
    p = Path(path)
    doc = _load(p, {})
    epoch = float(doc.get("epoch") or 0)
    if epoch <= 0:
        return True
    return (time.time() - epoch) > max_age_sec


def run_subprocess_guarded(
    args: list[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SEC,
    stall_sec: float = DEFAULT_STALL_SEC,
    label: str = "",
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    input_text: str | None = None,
    kill_on_stall: bool = True,
) -> dict[str, Any]:
    """Run subprocess with timeout + stdout progress stall detection."""
    lbl = label or (args[-1] if args else "subprocess")
    proc = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(cwd) if cwd else None,
    )
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    last_progress = time.time()
    deadline = time.time() + max(5.0, float(timeout))

    def _reader(stream, bucket: list[str], name: str) -> None:
        nonlocal last_progress
        if stream is None:
            return
        for line in iter(stream.readline, ""):
            bucket.append(line)
            if line.strip():
                last_progress = time.time()
        stream.close()

    t_out = threading.Thread(target=_reader, args=(proc.stdout, stdout_chunks, "stdout"), daemon=True)
    t_err = threading.Thread(target=_reader, args=(proc.stderr, stderr_chunks, "stderr"), daemon=True)
    t_out.start()
    t_err.start()

    if input_text is not None and proc.stdin:
        try:
            proc.stdin.write(input_text)
            proc.stdin.close()
        except OSError:
            pass

    hung = False
    exit_code: int | None = None
    while proc.poll() is None:
        now = time.time()
        if now > deadline:
            hung = True
            try:
                proc.kill()
            except OSError:
                pass
            break
        if (now - last_progress) >= stall_sec and kill_on_stall:
            hung = True
            _append_ledger({
                "event": "hang_kill",
                "label": lbl,
                "gap_sec": round(now - last_progress, 2),
                "pid": proc.pid,
            })
            try:
                proc.send_signal(signal.SIGTERM)
                time.sleep(2.0)
                if proc.poll() is None:
                    proc.kill()
            except OSError:
                pass
            break
        time.sleep(0.25)

    try:
        exit_code = proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        exit_code = -9

    t_out.join(timeout=3)
    t_err.join(timeout=3)
    stdout = "".join(stdout_chunks)
    stderr = "".join(stderr_chunks)

    out: dict[str, Any] = {
        "ok": exit_code == 0 and not hung,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "label": lbl,
        "hung": hung,
        "timeout_sec": timeout,
        "stall_sec": stall_sec,
    }
    if hung:
        out["error"] = "hang_or_timeout"
        out["verdict"] = "freeze_detected"
    _append_ledger({"event": "subprocess_done", "label": lbl, "ok": out["ok"], "hung": hung, "exit": exit_code})
    return out


def parse_json_output(guarded: dict[str, Any]) -> dict[str, Any]:
    raw = (guarded.get("stdout") or "").strip()
    if not raw:
        return {"ok": False, "error": guarded.get("error") or "empty_stdout", **guarded}
    try:
        doc = json.loads(raw)
        if isinstance(doc, dict):
            doc.setdefault("hang_guard", {"hung": guarded.get("hung"), "label": guarded.get("label")})
        return doc
    except json.JSONDecodeError:
        return {"ok": False, "error": "json_parse_failed", "detail": raw[:300], **guarded}


def run_py_json(
    script: Path,
    argv: list[str],
    *,
    timeout: float = DEFAULT_TIMEOUT_SEC,
    stall_sec: float = DEFAULT_STALL_SEC,
    label: str = "",
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "script_missing", "path": str(script)}
    args = [sys.executable, str(script), *argv]
    guarded = run_subprocess_guarded(
        args,
        timeout=timeout,
        stall_sec=stall_sec,
        label=label or script.name,
        env=env,
        cwd=cwd,
    )
    return parse_json_output(guarded)


def build_panel(*, write: bool = True) -> dict[str, Any]:
    recent: list[dict[str, Any]] = []
    if LEDGER.is_file():
        try:
            for line in LEDGER.read_text(encoding="utf-8").splitlines()[-20:]:
                if line.strip():
                    recent.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    panel = {
        "schema": "hostess7-hang-guard-panel/v1",
        "updated": _ts(),
        "motto": "No silent freeze — heartbeat, stall verdict, guarded subprocess.",
        "default_stall_sec": DEFAULT_STALL_SEC,
        "default_timeout_sec": DEFAULT_TIMEOUT_SEC,
        "ledger": str(LEDGER),
        "recent": recent[-8:],
        "ironclad_cite": "ironclad:hang_guard:1",
    }
    if write:
        _save(PANEL, panel)
    return panel


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return {"ok": True, **build_panel(write=action == "panel")}
    if action == "stale":
        path = body.get("path") or body.get("heartbeat")
        return {"ok": True, "stale": is_stale(str(path), max_age_sec=float(body.get("max_age_sec") or DEFAULT_STALL_SEC))}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps({"ok": True, **build_panel(write=cmd == "panel")}, ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-hang-guard.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())