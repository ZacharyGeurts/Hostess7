#!/usr/bin/env pythong
"""Monster — secure shell. Every program launches here. Invisible · debug · never crash."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-monster-shell-doctrine.json"
SESSIONS = STATE / "monster-sessions.json"
PANEL = STATE / "monster-shell-panel.json"
LEDGER = STATE / "monster-shell-ledger.jsonl"
HANG_QUEUE = STATE / "monster-hang-queue.json"
HANG_RESPONSE = STATE / "monster-hang-response.json"


def _now() -> str:
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
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _log(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _doctrine_defaults() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    return doc.get("defaults") if isinstance(doc.get("defaults"), dict) else {}


def _cfg_float(key: str, env_key: str, fallback: float) -> float:
    env = os.environ.get(env_key, "").strip()
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    val = _doctrine_defaults().get(key)
    if val is not None:
        try:
            return float(val)
        except (TypeError, ValueError):
            pass
    return fallback


def _cfg_bool(key: str, env_key: str, *, fallback: bool = True) -> bool:
    env = os.environ.get(env_key, "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    val = _doctrine_defaults().get(key)
    if isinstance(val, bool):
        return val
    return fallback


def _doctrine_doc() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    return doc if isinstance(doc, dict) else {}


GRACE_SEC = _cfg_float("grace_sec", "MONSTER_GRACE_SEC", 8.0)
DEFAULT_STALL = _cfg_float("stall_sec", "MONSTER_STALL_SEC", 180.0)
DEFAULT_TIMEOUT = _cfg_float("timeout_sec", "MONSTER_TIMEOUT_SEC", 7200.0)
POLL_MS = _cfg_float("poll_ms", "MONSTER_POLL_MS", 500.0)
SMART_VITALS = _cfg_bool("smart_vitals", "MONSTER_SMART_VITALS", fallback=True)
PROMPT_ONLY_IDLE = _cfg_bool("prompt_only_when_idle", "MONSTER_PROMPT_ONLY_IDLE", fallback=True)
VITALS_QUIET_SEC = _cfg_float("vitals_quiet_sec", "MONSTER_VITALS_QUIET_SEC", 15.0)
MAX_PROMPTS = int(_cfg_float("max_prompts_per_session", "MONSTER_MAX_PROMPTS", 2.0))
DESKTOP_HANG_WAIT_SEC = _cfg_float("desktop_hang_wait_sec", "MONSTER_DESKTOP_HANG_WAIT_SEC", 300.0)
HANG_QUEUE_TTL_SEC = _cfg_float("hang_queue_ttl_sec", "MONSTER_HANG_QUEUE_TTL_SEC", 900.0)
WATCH_LOG_THROTTLE_SEC = _cfg_float("watch_log_throttle_sec", "MONSTER_WATCH_LOG_THROTTLE_SEC", 90.0)
RE_PROMPT_COOLDOWN_SEC = _cfg_float("re_prompt_cooldown_sec", "MONSTER_RE_PROMPT_COOLDOWN_SEC", 120.0)
_WATCH_LOG_PHASES = frozenset(
    str(x).lower()
    for x in (_doctrine_doc().get("defaults") or {}).get("watch_log_phases") or ["prompt", "busy"]
)
_SLOW_MARKERS = tuple(
    str(x).lower()
    for x in (_doctrine_doc().get("slow_markers") or [
        "gcc", "g16", "cc1", "lto", "ld", "ninja", "cmake", "make", "qemu",
        "pack-ammoos", "rsync", "tar", "integrate", "compile", "chips",
        "wire-stack", "field-ammolang", "grok16", "python3", "pythong",
    ])
)
_SLOW_STALL_FLOOR = _cfg_float("slow_stall_floor_sec", "MONSTER_SLOW_STALL_FLOOR_SEC", 300.0)


def _import_popup() -> Any:
    try:
        import importlib.util

        py = INSTALL / "lib" / "field-monster-popup.py"
        spec = importlib.util.spec_from_file_location("monster_popup", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _import_h7() -> Any:
    try:
        import importlib.util

        py = INSTALL / "lib" / "hostess7-hang-guard.py"
        spec = importlib.util.spec_from_file_location("h7_hang", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def nuke_process_tree(pid: int, *, label: str = "") -> dict[str, Any]:
    """All measures to end a hung program — process group, children, SIGKILL."""
    killed: list[int] = []
    errors: list[str] = []
    try:
        pid_i = int(pid)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_pid"}

    if pid_i <= 1:
        return {"ok": False, "error": "protected_pid"}

    def _kill_one(target: int, sig: int) -> None:
        try:
            os.kill(target, sig)
            killed.append(target)
        except OSError as exc:
            errors.append(f"{target}:{exc}")

    def _children_of(ppid: int) -> list[int]:
        out: list[int] = []
        try:
            for entry in Path("/proc").iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    stat = (entry / "stat").read_text(encoding="utf-8")
                    parts = stat.split()
                    if len(parts) > 3 and int(parts[3]) == ppid:
                        out.append(int(entry.name))
                except (OSError, ValueError):
                    continue
        except OSError:
            pass
        return out

    try:
        pgid = os.getpgid(pid_i)
        if pgid > 0:
            _kill_one(pgid, signal.SIGTERM)
    except OSError:
        _kill_one(pid_i, signal.SIGTERM)

    time.sleep(1.5)
    queue = [pid_i, *_children_of(pid_i)]
    seen: set[int] = set()
    while queue:
        cur = queue.pop(0)
        if cur in seen or cur <= 1:
            continue
        seen.add(cur)
        _kill_one(cur, signal.SIGKILL)
        queue.extend(_children_of(cur))

    try:
        subprocess.run(
            ["pkill", "-9", "-P", str(pid_i)],
            capture_output=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass

    _log({"op": "nuke", "pid": pid_i, "label": label, "killed": killed})
    return {"ok": True, "pid": pid_i, "killed": killed, "errors": errors[:8]}


def _normalize_pending(doc: dict[str, Any]) -> list[dict[str, Any]]:
    pending = doc.get("pending")
    if isinstance(pending, list):
        return [p for p in pending if isinstance(p, dict) and p.get("id")]
    if isinstance(pending, dict) and pending.get("id"):
        return [pending]
    return []


def _pid_alive(pid: int) -> bool:
    try:
        pid_i = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_i <= 1:
        return False
    return Path(f"/proc/{pid_i}").is_dir()


def _hang_row_age_sec(row: dict[str, Any]) -> float:
    ts = str(row.get("queued") or row.get("updated") or "").strip()
    if not ts:
        return 0.0
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds())
    except ValueError:
        return 0.0


def _prune_hang_queue(*, write: bool = True) -> list[dict[str, Any]]:
    """Drop stale hang rows — dead pid, expired TTL, or acknowledged wait."""
    doc = _load(HANG_QUEUE, {})
    pending = _normalize_pending(doc)
    if not pending:
        return []
    kept: list[dict[str, Any]] = []
    pruned: list[str] = []
    for row in pending:
        pid = int(row.get("pid") or 0)
        age = _hang_row_age_sec(row)
        if pid and not _pid_alive(pid):
            pruned.append(f"{row.get('id')}:dead_pid")
            continue
        if age > HANG_QUEUE_TTL_SEC:
            pruned.append(f"{row.get('id')}:ttl")
            continue
        if row.get("acknowledged"):
            pruned.append(f"{row.get('id')}:acked")
            continue
        kept.append(row)
    if pruned and write:
        if kept:
            doc["pending"] = kept
            doc["updated"] = _now()
            _save(HANG_QUEUE, doc)
        else:
            try:
                HANG_QUEUE.unlink(missing_ok=True)
            except OSError:
                pass
        _log({"op": "hang_prune", "pruned": pruned[:8], "kept": len(kept)})
    return kept


def _clear_hang_queue_entry(session_id: str) -> None:
    doc = _load(HANG_QUEUE, {})
    pending = _normalize_pending(doc)
    kept = [p for p in pending if p.get("id") != session_id]
    if len(kept) == len(pending):
        return
    if kept:
        doc["pending"] = kept
        doc["updated"] = _now()
        _save(HANG_QUEUE, doc)
    else:
        try:
            HANG_QUEUE.unlink(missing_ok=True)
        except OSError:
            pass


def _queue_hang_for_desktop(session_id: str, label: str, detail: str, pid: int, *, stall_sec: float) -> None:
    _prune_hang_queue(write=True)
    now = _now()
    row = {
        "id": session_id,
        "label": label,
        "detail": detail,
        "pid": pid,
        "stall_sec": int(stall_sec),
        "queued": now,
        "updated": now,
        "pid_alive": _pid_alive(pid),
        "phase": "prompt",
        "choices": ["wait", "quit"],
    }
    doc = _load(HANG_QUEUE, {})
    pending = [p for p in _normalize_pending(doc) if p.get("id") != session_id]
    pending.append(row)
    _save(HANG_QUEUE, {"schema": "monster-hang-queue/v1", "updated": now, "pending": pending})
    try:
        HANG_RESPONSE.unlink(missing_ok=True)
    except OSError:
        pass


def _read_hang_response(session_id: str, *, timeout_sec: float = 300.0) -> str:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        doc = _load(HANG_RESPONSE, {})
        if doc.get("id") == session_id and doc.get("choice"):
            choice = str(doc["choice"])
            if choice in ("wait", "dismiss"):
                _clear_hang_queue_entry(session_id)
            return choice
        if os.environ.get("MONSTER_USE_DESKTOP_HANG", "1") == "0":
            break
        time.sleep(0.4)
    return ""


def _proc_stat(pid: int) -> dict[str, Any] | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        rparen = raw.rfind(")")
        if rparen < 0:
            return None
        parts = raw[rparen + 2 :].split()
        if len(parts) < 13:
            return None
        return {
            "state": parts[0],
            "utime": int(parts[11]),
            "stime": int(parts[12]),
        }
    except (OSError, ValueError):
        return None


def _proc_io(pid: int) -> tuple[int, int]:
    try:
        rb = wb = 0
        for line in Path(f"/proc/{pid}/io").read_text(encoding="utf-8").splitlines():
            if line.startswith("read_bytes:"):
                rb = int(line.split()[1])
            elif line.startswith("write_bytes:"):
                wb = int(line.split()[1])
        return rb, wb
    except (OSError, ValueError):
        return 0, 0


def _child_pids(ppid: int) -> list[int]:
    out: list[int] = []
    try:
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            try:
                stat = (entry / "stat").read_text(encoding="utf-8")
                parts = stat.rfind(")")
                if parts < 0:
                    continue
                rest = stat[parts + 2 :].split()
                if len(rest) > 1 and int(rest[1]) == ppid:
                    out.append(int(entry.name))
            except (OSError, ValueError):
                continue
    except OSError:
        pass
    return out


def _proc_tree_pids(root_pid: int, *, limit: int = 64) -> list[int]:
    """BFS descendants — gcc/cc1/lto hide work below the launcher."""
    if root_pid <= 1:
        return []
    seen: set[int] = {root_pid}
    queue = [root_pid]
    ordered = [root_pid]
    while queue and len(ordered) < limit:
        cur = queue.pop(0)
        for child in _child_pids(cur):
            if child in seen or child <= 1:
                continue
            seen.add(child)
            ordered.append(child)
            queue.append(child)
    return ordered


def _pids_in_pgid(pgid: int, *, limit: int = 48) -> list[int]:
    if pgid <= 1:
        return []
    out: list[int] = []
    try:
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit() or len(out) >= limit:
                continue
            try:
                if os.getpgid(int(entry.name)) == pgid:
                    out.append(int(entry.name))
            except (OSError, ProcessLookupError):
                continue
    except OSError:
        pass
    return out


def _effective_stall(label: str, cmd: list[str], base: float, prompt_count: int) -> float:
    blob = f"{label} {' '.join(cmd)}".lower()
    stall = float(base)
    if any(marker in blob for marker in _SLOW_MARKERS):
        stall = max(stall, _SLOW_STALL_FLOOR)
    if prompt_count > 0:
        stall *= 1.5 ** prompt_count
    return min(stall, DEFAULT_TIMEOUT)


def _sample_vitals(pid: int, prev: dict[str, Any] | None) -> dict[str, Any]:
    """CPU, IO, and scheduler state — busy work without stdout still counts as progress."""
    stat = _proc_stat(pid)
    if not stat:
        return {"alive": False, "busy": False, "reason": "gone"}
    rb, wb = _proc_io(pid)
    row: dict[str, Any] = {
        "alive": True,
        "state": stat["state"],
        "utime": stat["utime"],
        "stime": stat["stime"],
        "read_bytes": rb,
        "write_bytes": wb,
        "ts": time.time(),
        "busy": False,
        "reason": "",
    }
    reasons: list[str] = []
    if stat["state"] in ("R", "D"):
        row["busy"] = True
        reasons.append(f"state:{stat['state']}")
    if prev and prev.get("alive"):
        cpu_delta = (row["utime"] + row["stime"]) - int(prev.get("utime", 0) + prev.get("stime", 0))
        if cpu_delta > 0:
            row["busy"] = True
            reasons.append(f"cpu:+{cpu_delta}")
        if rb > int(prev.get("read_bytes", 0)) or wb > int(prev.get("write_bytes", 0)):
            row["busy"] = True
            reasons.append("io:active")
    row["reason"] = ",".join(reasons[:4])
    return row


def _sample_tree_vitals(
    root_pid: int,
    prev_map: dict[int, dict[str, Any]] | None,
) -> dict[str, Any]:
    """Aggregate vitals across process tree + process group — silence ≠ stall."""
    pids = _proc_tree_pids(root_pid)
    try:
        pgid = os.getpgid(root_pid)
        for pid in _pids_in_pgid(pgid):
            if pid not in pids:
                pids.append(pid)
    except OSError:
        pass
    pmap = prev_map or {}
    cur_map: dict[int, dict[str, Any]] = {}
    busy = False
    reasons: list[str] = []
    alive = False
    for pid in pids[:64]:
        snap = _sample_vitals(pid, pmap.get(pid))
        cur_map[pid] = snap
        if snap.get("alive"):
            alive = True
        if snap.get("busy"):
            busy = True
            reasons.append(f"{pid}:{snap.get('reason', '')}")
    return {
        "alive": alive,
        "busy": busy,
        "reason": ",".join(reasons[:6]),
        "map": cur_map,
        "pids": pids[:64],
    }


def _vitals_idle_for_tree(
    pid: int,
    prev_map: dict[int, dict[str, Any]] | None,
    idle_since: float | None,
) -> tuple[bool, dict[int, dict[str, Any]], float | None]:
    """True when the whole process tree has been resource-idle for vitals_quiet_sec."""
    cur = _sample_tree_vitals(pid, prev_map)
    now = time.time()
    if cur.get("busy"):
        return False, cur.get("map") or {}, None
    if idle_since is None:
        return False, cur.get("map") or {}, now
    if (now - idle_since) >= VITALS_QUIET_SEC:
        return True, cur.get("map") or {}, idle_since
    return False, cur.get("map") or {}, idle_since


def _should_prompt_hang(
    *,
    output_gap: float,
    stall: float,
    pid: int,
    vitals_prev_map: dict[int, dict[str, Any]] | None,
    vitals_idle_since: float | None,
    prompt_count: int,
) -> tuple[bool, dict[int, dict[str, Any]], float | None, str]:
    """
    Grace after output stops, then vitals-aware stall.
    Popup only when the whole tree is idle long enough.
    """
    if output_gap < GRACE_SEC:
        return False, vitals_prev_map or {}, vitals_idle_since, "grace"

    cur = _sample_tree_vitals(pid, vitals_prev_map)
    if SMART_VITALS and cur.get("busy"):
        return False, cur.get("map") or {}, None, f"busy:{cur.get('reason', '')}"

    idle_ok, new_map, idle_since = _vitals_idle_for_tree(pid, vitals_prev_map, vitals_idle_since)

    if not idle_ok:
        return False, new_map, idle_since, "vitals_warming"

    if output_gap < stall:
        return False, new_map, idle_since, "under_stall"

    if PROMPT_ONLY_IDLE and not idle_ok:
        return False, new_map, idle_since, "not_idle"

    if prompt_count >= MAX_PROMPTS:
        return False, new_map, idle_since, "max_prompts"

    return True, new_map, idle_since, "prompt"


def _active_hang_labels() -> set[str]:
    doc = _load(HANG_QUEUE, {})
    pending = doc.get("pending") or []
    if isinstance(pending, dict):
        pending = [pending]
    labels: set[str] = set()
    for row in pending:
        if isinstance(row, dict) and row.get("label"):
            labels.add(str(row["label"]))
    return labels


def _native_hang_enabled() -> bool:
    env = os.environ.get("MONSTER_NATIVE_HANG", "").strip().lower()
    if env in ("1", "true", "yes", "on"):
        return True
    if env in ("0", "false", "no", "off"):
        return False
    return bool(_doctrine_doc().get("defaults", {}).get("native_hang_popup", False))


def _resolve_hang(session_id: str, label: str, detail: str, pid: int, *, stall_sec: float) -> str:
    """wait | quit — desktop queue first; native zenity only when explicitly enabled."""
    use_desktop = os.environ.get("MONSTER_USE_DESKTOP_HANG", "1") != "0"
    if use_desktop:
        existing = _active_hang_labels()
        if label not in existing:
            _queue_hang_for_desktop(session_id, label, detail, pid, stall_sec=stall_sec)
        picked = _read_hang_response(session_id, timeout_sec=DESKTOP_HANG_WAIT_SEC)
        if picked in ("wait", "quit", "dismiss"):
            return "wait" if picked == "dismiss" else picked
        return "wait"

    if not _native_hang_enabled():
        return "wait"

    popup = _import_popup()
    if popup and hasattr(popup, "hang_prompt"):
        try:
            return str(popup.hang_prompt(label, detail))
        except Exception:
            pass
    return "wait"


def run_guarded(
    cmd: list[str],
    *,
    label: str = "",
    timeout: float | None = None,
    stall_sec: float | None = None,
    env: dict[str, str] | None = None,
    cwd: str | Path | None = None,
    use_desktop_hang: bool = True,
) -> dict[str, Any]:
    """Launch through Monster — stall prompts, full kill on quit. Never raises."""
    session_id = uuid.uuid4().hex[:12]
    lbl = (label or (cmd[-1] if cmd else "program"))[:120]
    to = float(timeout or DEFAULT_TIMEOUT)
    stall = float(stall_sec or DEFAULT_STALL)
    env = {**os.environ, **(env or {})}
    env.setdefault("MONSTER_SESSION", session_id)
    env.setdefault("LAUNCHED_BY_MONSTER", "1")

    h7 = _import_h7()
    if h7 and hasattr(h7, "run_subprocess_guarded") and os.environ.get("MONSTER_H7_DELEGATE", "0") == "1":
        try:
            row = h7.run_subprocess_guarded(
                cmd,
                timeout=to,
                stall_sec=stall,
                label=lbl,
                env=env,
                cwd=cwd,
                kill_on_stall=False,
            )
            row["session_id"] = session_id
            row["monster"] = True
            return row
        except Exception as exc:
            _log({"op": "h7_fallback", "error": str(exc)})

    proc: subprocess.Popen[str] | None = None
    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []
    last_progress = time.time()
    deadline = time.time() + to
    quit_requested = False
    hung = False
    exit_code: int | None = None

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            cwd=str(cwd) if cwd else None,
            start_new_session=True,
        )
    except OSError as exc:
        return {"ok": False, "error": str(exc), "label": lbl, "session_id": session_id, "monster": True}

    pid = proc.pid
    _log({"op": "launch", "session_id": session_id, "label": lbl, "pid": pid, "cmd": cmd[:6]})

    def _reader(stream, bucket: list[str]) -> None:
        nonlocal last_progress
        if stream is None:
            return
        try:
            for line in iter(stream.readline, ""):
                bucket.append(line)
                if line.strip():
                    last_progress = time.time()
        except Exception:
            pass
        try:
            stream.close()
        except Exception:
            pass

    t_out = threading.Thread(target=_reader, args=(proc.stdout, stdout_chunks), daemon=True)
    t_err = threading.Thread(target=_reader, args=(proc.stderr, stderr_chunks), daemon=True)
    t_out.start()
    t_err.start()

    vitals_prev_map: dict[int, dict[str, Any]] | None = None
    vitals_idle_since: float | None = None
    prompt_count = 0
    last_watch_phase = ""
    last_watch_log_at = 0.0
    last_prompt_at = 0.0
    while proc.poll() is None:
        now = time.time()
        if now > deadline:
            hung = True
            quit_requested = True
            break
        output_gap = now - last_progress
        stall_now = _effective_stall(lbl, cmd, stall, prompt_count)

        # Resource activity without stdout — treat as progress (compile, QEMU, etc.)
        if SMART_VITALS and output_gap >= GRACE_SEC:
            snap = _sample_tree_vitals(pid, vitals_prev_map)
            vitals_prev_map = snap.get("map") or {}
            if snap.get("busy"):
                last_progress = now
                vitals_idle_since = None
                output_gap = 0.0

        should_prompt, vitals_prev_map, vitals_idle_since, phase = _should_prompt_hang(
            output_gap=output_gap,
            stall=stall_now,
            pid=pid,
            vitals_prev_map=vitals_prev_map,
            vitals_idle_since=vitals_idle_since,
            prompt_count=prompt_count,
        )
        if should_prompt and prompt_count > 0 and (now - last_prompt_at) < RE_PROMPT_COOLDOWN_SEC:
            should_prompt = False
            phase = "cooldown"
        if should_prompt:
            tree = _sample_tree_vitals(pid, vitals_prev_map)
            vitals_prev_map = tree.get("map") or vitals_prev_map
            detail = (
                f"No output for {int(output_gap)}s (grace {int(GRACE_SEC)}s · stall {int(stall_now)}s).\n"
                f"Process tree idle — vitals quiet {int(VITALS_QUIET_SEC)}s+; pids {len(tree.get('pids') or [])}."
            )
            if stderr_chunks:
                detail += "\n" + "".join(stderr_chunks[-3:])[:200]
            choice = _resolve_hang(session_id, lbl, detail, pid, stall_sec=stall)
            prompt_count += 1
            last_prompt_at = now
            _log({
                "op": "hang_prompt",
                "session_id": session_id,
                "choice": choice,
                "gap": output_gap,
                "phase": phase,
                "prompt_count": prompt_count,
                "vitals": {"busy": tree.get("busy"), "reason": tree.get("reason")},
            })
            if choice == "quit":
                quit_requested = True
                hung = True
                break
            last_progress = time.time()
            vitals_idle_since = None
        elif (
            phase in _WATCH_LOG_PHASES
            and phase != last_watch_phase
            and (now - last_watch_log_at) >= WATCH_LOG_THROTTLE_SEC
        ):
            last_watch_phase = phase
            last_watch_log_at = now
            _log({"op": "hang_watch", "session_id": session_id, "phase": phase, "gap": int(output_gap)})
        time.sleep(POLL_MS / 1000.0)

    if quit_requested and proc.poll() is None:
        nuke_process_tree(pid, label=lbl)

    try:
        exit_code = proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        nuke_process_tree(pid, label=lbl)
        exit_code = -9

    t_out.join(timeout=2)
    t_err.join(timeout=2)
    stdout = "".join(stdout_chunks)
    stderr = "".join(stderr_chunks)

    row: dict[str, Any] = {
        "ok": exit_code == 0 and not hung,
        "rc": exit_code,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "label": lbl,
        "session_id": session_id,
        "pid": pid,
        "hung": hung,
        "quit": quit_requested,
        "monster": True,
        "wall_ms": int((time.time() - (deadline - to)) * 1000),
    }
    if hung:
        row["detail"] = "hang_or_quit"
    _log({"op": "done", **{k: row[k] for k in ("session_id", "label", "ok", "rc", "hung", "quit")}})
    _save(
        PANEL,
        {
            "schema": "monster-shell-panel/v1",
            "updated": _now(),
            "last": row,
            "motto": "Monster secure shell — invisible until hang",
        },
    )
    try:
        doc = _load(HANG_QUEUE, {})
        if any(p.get("id") == session_id for p in _normalize_pending(doc)):
            HANG_QUEUE.unlink(missing_ok=True)
    except OSError:
        pass
    return row


def handle_api(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "").lower().replace("-", "_")
    if action in ("hang_pending", "hang-pending"):
        pending = _prune_hang_queue(write=True)
        doc = _load(HANG_QUEUE, {})
        return {"ok": True, "pending": pending, "updated": doc.get("updated"), "pruned": True}
    if action == "hang_respond":
        sid = str(body.get("id") or "")
        choice = str(body.get("choice") or "wait")
        if choice not in ("wait", "quit", "dismiss"):
            choice = "wait"
        _save(HANG_RESPONSE, {"id": sid, "choice": choice, "updated": _now()})
        if choice in ("wait", "dismiss"):
            _clear_hang_queue_entry(sid)
        return {"ok": True, "id": sid, "choice": choice}
    if action == "nuke":
        return nuke_process_tree(int(body.get("pid") or 0), label=str(body.get("label") or ""))
    if action == "sessions":
        return {"ok": True, "sessions": _load(SESSIONS, {"active": []})}
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print(json.dumps({"error": "usage: run|dispatch|json", "monster": True}))
        return 1

    cmd = args[0].lower()
    if cmd in ("json", "status", "panel"):
        print(json.dumps({"ok": True, **_load(PANEL, {})}, ensure_ascii=False, indent=2))
        return 0

    if cmd in ("hang-pending", "hang_pending"):
        pending = _prune_hang_queue(write=True)
        doc = _load(HANG_QUEUE, {})
        print(json.dumps({"ok": True, "pending": pending, "updated": doc.get("updated")}, ensure_ascii=False))
        return 0

    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(handle_api(body), ensure_ascii=False))
        return 0

    if cmd in ("run", "launch", "exec"):
        rest = args[1:]
        label = os.environ.get("MONSTER_LABEL", "")
        stall: float | None = None
        timeout: float | None = None
        parsed: list[str] = []
        i = 0
        while i < len(rest):
            tok = rest[i]
            if tok == "--":
                parsed = rest[i + 1 :]
                break
            if tok == "--label" and i + 1 < len(rest):
                label = rest[i + 1]
                i += 2
                continue
            if tok == "--stall" and i + 1 < len(rest):
                stall = float(rest[i + 1])
                i += 2
                continue
            if tok == "--timeout" and i + 1 < len(rest):
                timeout = float(rest[i + 1])
                i += 2
                continue
            parsed.append(tok)
            i += 1
        if not label and parsed:
            label = Path(parsed[0]).name
        row = run_guarded(
            parsed,
            label=label,
            stall_sec=stall,
            timeout=timeout,
        )
        print(json.dumps(row, ensure_ascii=False))
        return 0 if row.get("ok") else 1

    if cmd == "nuke" and len(args) > 1:
        print(json.dumps(nuke_process_tree(int(args[1])), ensure_ascii=False))
        return 0

    print(json.dumps({"error": "unknown_cmd", "cmd": cmd}))
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc), "monster": True, "never_crash": True}))
        raise SystemExit(1)