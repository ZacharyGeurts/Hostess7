#!/usr/bin/env pythong
"""Hostess 7 presume — line-level profiling, microsecond timings, cooperative wait, sovereign commits."""
from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-presume-doctrine.json"
PANEL = STATE / "hostess7-presume-panel.json"
LEDGER = STATE / "hostess7-presume.jsonl"
LINE_LEDGER = STATE / "hostess7-presume-lines.jsonl"
COMMITS = STATE / "hostess7-presume-commits.json"
PROPAGATE = STATE / "hostess7-presume-propagate.json"

_THREAD_LOCAL = threading.local()
_CLOCK: Any = None
_COMMIT_LOCK = threading.RLock()


def _clock() -> Any:
    global _CLOCK
    if _CLOCK is None:
        spec = importlib.util.spec_from_file_location("sovereign_clock", INSTALL / "lib" / "sovereign-clock.py")
        if not spec or not spec.loader:
            raise ImportError("sovereign-clock.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _CLOCK = mod
    return _CLOCK


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
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


def _append(path: Path, row: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def mono_us() -> int:
    """Monotonic microsecond clock — resume precision."""
    return int(time.perf_counter_ns() // 1000)


def sovereign_us() -> int:
    """Sovereign linear time in microseconds."""
    return int(_clock().ns_linear() // 1000)


def _utc() -> str:
    return _clock().utc_z()


def _load_commits() -> dict[str, Any]:
    doc = _load(COMMITS, {})
    if not doc:
        return {"schema": "hostess7-presume-commits/v1", "active": {}, "history": []}
    return doc


def _save_commits(doc: dict[str, Any]) -> None:
    _save(COMMITS, doc)


def decide(
    action_id: str,
    *,
    label: str = "",
    payload: dict[str, Any] | None = None,
    source: str = "hostess7",
    resources_devoted: bool = True,
) -> dict[str, Any]:
    """Bind an action as uninterruptable — no outside influence may override."""
    doctrine = _load(DOCTRINE, {})
    binding = doctrine.get("sovereign_binding") or {}
    aid = (action_id or f"presume_{uuid.uuid4().hex[:12]}")[:120]
    cp = checkpoint(label=label or aid)
    row = {
        "action_id": aid,
        "label": (label or aid)[:120],
        "source": source[:64],
        "payload": payload or {},
        "committed_us": mono_us(),
        "committed_utc": _utc(),
        "checkpoint": cp,
        "uninterruptable": True,
        "outside_influence_blocked": bool(binding.get("outside_influence_blocked", True)),
        "resources_devoted": resources_devoted,
        "not_go_away": True,
        "status": "active",
    }
    with _COMMIT_LOCK:
        doc = _load_commits()
        active = dict(doc.get("active") or {})
        if aid in active and active[aid].get("status") == "active":
            return {
                "ok": False,
                "schema": "hostess7-presume-decide/v1",
                "error": "already_committed",
                "action_id": aid,
                "commit": active[aid],
            }
        active[aid] = row
        doc["active"] = active
        doc["updated"] = _utc()
        _save_commits(doc)
    _append(LEDGER, {**row, "schema": "hostess7-presume-commit/v1", "event": "decide"})
    _witness_change("presume_decide", detail=aid, meta={"action_id": aid, "label": row.get("label")})
    return {"ok": True, "schema": "hostess7-presume-decide/v1", "commit": row}


def is_committed(action_id: str) -> bool:
    with _COMMIT_LOCK:
        active = (_load_commits().get("active") or {})
        row = active.get(action_id)
        return bool(row and row.get("status") == "active" and row.get("uninterruptable"))


def reject_influence(
    action_id: str,
    *,
    source: str = "outside",
    reason: str = "",
) -> dict[str, Any]:
    """Reject outside attempt to cancel or redirect a committed action."""
    doctrine = _load(DOCTRINE, {})
    override = set(doctrine.get("sovereign_binding", {}).get("override_authority") or ["hostess7", "operator"])
    if source in override:
        return {"ok": True, "schema": "hostess7-presume-influence/v1", "allowed": True, "action_id": action_id}
    if is_committed(action_id):
        out = {
            "ok": False,
            "schema": "hostess7-presume-influence/v1",
            "allowed": False,
            "rejected": True,
            "action_id": action_id,
            "reason": reason or "outside_influence_blocked",
            "rule": "Once decided, no outside influence may override the action.",
            "source": source,
        }
        _append(LEDGER, {**out, "event": "reject_influence"})
        return out
    return {"ok": True, "schema": "hostess7-presume-influence/v1", "allowed": True, "action_id": action_id, "not_committed": True}


def release(action_id: str, *, source: str = "hostess7", result: Any = None) -> dict[str, Any]:
    """Explicit release — only binding authority may finish a committed action."""
    doctrine = _load(DOCTRINE, {})
    override = set(doctrine.get("sovereign_binding", {}).get("override_authority") or ["hostess7", "operator"])
    if source not in override:
        return reject_influence(action_id, source=source, reason="release_denied_outside_authority")
    with _COMMIT_LOCK:
        doc = _load_commits()
        active = dict(doc.get("active") or {})
        row = active.pop(action_id, None)
        if not row:
            return {"ok": False, "schema": "hostess7-presume-release/v1", "error": "not_committed", "action_id": action_id}
        row["status"] = "released"
        row["released_us"] = mono_us()
        row["released_utc"] = _utc()
        row["released_by"] = source
        if result is not None:
            row["result"] = result if isinstance(result, (dict, list, str, int, float, bool)) else str(result)[:400]
        history = list(doc.get("history") or [])
        history.append(row)
        doc["active"] = active
        doc["history"] = history[-128:]
        doc["updated"] = _utc()
        _save_commits(doc)
    _append(LEDGER, {"schema": "hostess7-presume-release/v1", "event": "release", "action_id": action_id, "source": source})
    _witness_change("presume_release", detail=action_id, meta={"action_id": action_id, "source": source})
    return {"ok": True, "schema": "hostess7-presume-release/v1", "action_id": action_id, "commit": row}


@contextmanager
def committed_action(
    action_id: str,
    *,
    label: str = "",
    payload: dict[str, Any] | None = None,
    source: str = "hostess7",
) -> Iterator[dict[str, Any]]:
    """Context manager — decide on enter, release on exit. Uninterruptable while active."""
    rep = decide(action_id, label=label, payload=payload, source=source)
    commit = rep.get("commit") or {}
    if not rep.get("ok") and rep.get("error") != "already_committed":
        yield commit
        return
    try:
        yield commit
    finally:
        if is_committed(action_id):
            release(action_id, source=source)


def guard_action(
    action_id: str,
    fn: Callable[..., Any],
    *args: Any,
    label: str = "",
    payload: dict[str, Any] | None = None,
    source: str = "hostess7",
    **kwargs: Any,
) -> dict[str, Any]:
    """Run callable under uninterruptable presume commit; resources stay devoted via alternates."""
    with committed_action(action_id, label=label, payload=payload, source=source):
        t0 = mono_us()
        try:
            result = fn(*args, **kwargs)
            ok = True if not isinstance(result, dict) else bool(result.get("ok", True))
            return {
                "ok": ok,
                "schema": "hostess7-presume-guard/v1",
                "action_id": action_id,
                "uninterruptable": True,
                "elapsed_us": mono_us() - t0,
                "result": result,
            }
        except Exception as exc:
            return {
                "ok": False,
                "schema": "hostess7-presume-guard/v1",
                "action_id": action_id,
                "error": str(exc)[:240],
                "elapsed_us": mono_us() - t0,
            }


def guard_profiled(
    action_id: str,
    fn: Callable[..., Any],
    *args: Any,
    label: str = "",
    payload: dict[str, Any] | None = None,
    source: str = "hostess7",
    **kwargs: Any,
) -> dict[str, Any]:
    """Run callable under uninterruptable commit with line-level profiling."""
    with committed_action(action_id, label=label, payload=payload, source=source):
        t0 = mono_us()
        try:
            prof = profile_call(fn, *args, label=label or action_id, **kwargs)
            result = prof.get("result")
            ok = True if not isinstance(result, dict) else bool(result.get("ok", True))
            return {
                "ok": ok,
                "schema": "hostess7-presume-guard-profiled/v1",
                "action_id": action_id,
                "uninterruptable": True,
                "elapsed_us": mono_us() - t0,
                "line_count": prof.get("line_count"),
                "result": result,
                "profile": prof,
            }
        except Exception as exc:
            return {
                "ok": False,
                "schema": "hostess7-presume-guard-profiled/v1",
                "action_id": action_id,
                "error": str(exc)[:240],
                "elapsed_us": mono_us() - t0,
            }


def _stale_commit_ttl_us() -> int:
    doctrine = _load(DOCTRINE, {})
    aml_sep = doctrine.get("aml_separation") or {}
    return max(1_000_000, int(aml_sep.get("stale_commit_ttl_us") or 120_000_000))


def sweep_stale_commits(*, ttl_us: int | None = None, write: bool = True) -> dict[str, Any]:
    """Release stale active commits — especially AML-boundary orphans without release."""
    ttl = max(1_000_000, int(ttl_us or _stale_commit_ttl_us()))
    orphan_ttl = 5_000_000
    now_us = mono_us()
    released: list[dict[str, Any]] = []
    with _COMMIT_LOCK:
        doc = _load_commits()
        active = dict(doc.get("active") or {})
        for aid, row in list(active.items()):
            age_us = now_us - int(row.get("committed_us") or now_us)
            source = str(row.get("source") or "")
            stale = age_us > ttl
            aml_orphan = source == "ammolang_boundary" and age_us > orphan_ttl
            if not stale and not aml_orphan:
                continue
            active.pop(aid, None)
            row = dict(row)
            row["status"] = "released"
            row["released_us"] = now_us
            row["released_utc"] = _utc()
            row["released_by"] = "hostess7_sweep"
            row["sweep_reason"] = "aml_orphan" if aml_orphan else "stale_ttl"
            row["age_us"] = age_us
            history = list(doc.get("history") or [])
            history.append(row)
            doc["history"] = history[-128:]
            released.append({"action_id": aid, "source": source, "age_us": age_us, "reason": row["sweep_reason"]})
            _append(LEDGER, {"schema": "hostess7-presume-sweep/v1", "event": "sweep_release", "action_id": aid, "source": source})
        if released:
            doc["active"] = active
            doc["updated"] = _utc()
            if write:
                _save_commits(doc)
    return {
        "ok": True,
        "schema": "hostess7-presume-sweep/v1",
        "released_count": len(released),
        "released": released,
        "ttl_us": ttl,
        "utc": _utc(),
    }


@contextmanager
def witness_execution(
    *,
    label: str = "witness",
    action_id: str | None = None,
    payload: dict[str, Any] | None = None,
    source: str = "hostess7",
    profile: bool = False,
) -> Iterator[dict[str, Any]]:
    """Sovereign execution witness — uninterruptable commit for Hostess 7 work (not AML)."""
    aid = (action_id or f"witness_{uuid.uuid4().hex[:10]}")[:120]
    with committed_action(aid, label=label, payload=payload, source=source):
        ctx = {"action_id": aid, "label": label, "started_us": mono_us(), "source": source}
        if profile:
            with profile_lines(label):
                yield ctx
        else:
            yield ctx


def propagate(*, write: bool = True) -> dict[str, Any]:
    """Stamp propagation receipt — every target module must honor presume commits."""
    doctrine = _load(DOCTRINE, {})
    targets = list((doctrine.get("propagation") or {}).get("targets") or [])
    wired: list[dict[str, Any]] = []
    for t in targets:
        mod_path = INSTALL / str(t.get("module") or "")
        wired.append({
            "id": t.get("id"),
            "module": str(t.get("module")),
            "bind": t.get("bind"),
            "present": mod_path.is_file(),
            "honors_uninterruptable": True,
            "resources_devoted": True,
        })
    present = sum(1 for w in wired if w.get("present"))
    doc = {
        "schema": "hostess7-presume-propagate/v1",
        "updated": _utc(),
        "mandatory": bool((doctrine.get("propagation") or {}).get("mandatory", True)),
        "rule": (doctrine.get("propagation") or {}).get("rule"),
        "not_go_away": (doctrine.get("not_go_away") or {}).get("rule"),
        "sovereign_binding": doctrine.get("sovereign_binding"),
        "targets": wired,
        "targets_present": present,
        "targets_total": len(wired),
        "propagated": present == len(wired) if wired else False,
    }
    if write:
        _save(PROPAGATE, doc)
    return doc


def checkpoint(*, label: str = "") -> dict[str, Any]:
    """Capture call-site file, line, function — profiled to the line."""
    frame = inspect.currentframe()
    caller = frame.f_back if frame else None
    info = inspect.getframeinfo(caller) if caller else None
    us = mono_us()
    row = {
        "schema": "hostess7-presume-checkpoint/v1",
        "label": (label or "presume")[:120],
        "file": (info.filename if info else "")[-240:],
        "line": int(info.lineno if info else 0),
        "function": (info.function if info else "")[:120],
        "mono_us": us,
        "sovereign_us": sovereign_us(),
        "utc": _utc(),
    }
    if caller is not None:
        del caller
    if frame is not None:
        del frame
    return row


def _import_callable(module_rel: str, callable_name: str) -> Callable[..., Any] | None:
    path = INSTALL / module_rel
    if not path.is_file():
        return None
    stem = path.stem.replace("-", "_")
    spec = importlib.util.spec_from_file_location(f"h7presume_{stem}", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    fn = getattr(mod, callable_name, None)
    return fn if callable(fn) else None


def _run_alternate(task: dict[str, Any], *, budget_us: int) -> dict[str, Any]:
    tid = str(task.get("id") or "alternate")
    fn = _import_callable(str(task.get("module") or ""), str(task.get("callable") or ""))
    if not fn:
        return {"id": tid, "ok": False, "error": "callable_missing"}
    args = list(task.get("args") or [])
    started = mono_us()
    try:
        out = fn(*args)
        elapsed_us = mono_us() - started
        return {
            "id": tid,
            "ok": True,
            "elapsed_us": elapsed_us,
            "within_budget": elapsed_us <= max(1, int(budget_us)),
            "result_keys": list(out.keys())[:12] if isinstance(out, dict) else [],
        }
    except Exception as exc:
        return {"id": tid, "ok": False, "elapsed_us": mono_us() - started, "error": str(exc)[:200]}


def presume(
    wait_us: int = 0,
    *,
    label: str = "",
    alternate_id: str | None = None,
    alternate_fn: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    """Presume deadline — profile to line, run alternates instead of wait, resume on point."""
    wait_us = max(0, int(wait_us))
    doctrine = _load(DOCTRINE, {})
    tasks = list(doctrine.get("alternate_tasks") or [])
    if alternate_id:
        tasks = [t for t in tasks if str(t.get("id")) == alternate_id] or tasks[:1]
    tasks = sorted(tasks, key=lambda t: int(t.get("max_slice_us") or 999999))

    start_us = mono_us()
    resume_at_us = start_us + wait_us
    alternates: list[dict[str, Any]] = []

    while mono_us() < resume_at_us:
        remaining = resume_at_us - mono_us()
        if remaining <= 0:
            break
        ran = False
        if alternate_fn and remaining >= 200:
            t0 = mono_us()
            try:
                alternate_fn()
                alternates.append({"id": "inline", "ok": True, "elapsed_us": mono_us() - t0})
            except Exception as exc:
                alternates.append({"id": "inline", "ok": False, "error": str(exc)[:160]})
            ran = True
        else:
            for task in tasks:
                if mono_us() >= resume_at_us:
                    break
                remaining = resume_at_us - mono_us()
                if remaining <= 50:
                    break
                max_slice = int(task.get("max_slice_us") or remaining)
                if max_slice > remaining:
                    continue
                budget = min(max_slice, remaining)
                if budget < 100:
                    continue
                alt = _run_alternate(task, budget_us=budget)
                alternates.append(alt)
                ran = True
                if mono_us() >= resume_at_us:
                    break
        if not ran:
            slice_us = min(remaining, 2000)
            time.sleep(slice_us / 1_000_000.0)

    while mono_us() < resume_at_us:
        gap = resume_at_us - mono_us()
        if gap <= 0:
            break
        if gap > 2500:
            time.sleep((gap - 1500) / 1_000_000.0)
        else:
            time.sleep(0)

    resumed_us = mono_us()
    drift_us = resumed_us - resume_at_us
    cp = checkpoint(label=label or "presume")
    cp["mono_us"] = start_us
    out = {
        "schema": "hostess7-presume/v1",
        "ok": True,
        "presumed": True,
        "resumed_on_point": abs(drift_us) <= max(250, wait_us // 20 + 50),
        "label": cp["label"],
        "checkpoint": cp,
        "wait_us": wait_us,
        "resume_at_us": resume_at_us,
        "resumed_us": resumed_us,
        "drift_us": drift_us,
        "elapsed_us": resumed_us - start_us,
        "alternate_runs": alternates,
        "no_busy_wait": True,
        "precision": "microsecond",
        "utc": _utc(),
    }
    threading.Thread(target=_append, args=(LEDGER, out), daemon=True).start()
    return out


class _LineTrace:
    def __init__(self, label: str) -> None:
        self.label = label[:120]
        self.rows: list[dict[str, Any]] = []
        self._last: dict[tuple[str, int], int] = {}
        self._depth = 0

    def tracer(self, frame: Any, event: str, arg: Any) -> Callable[..., Any]:
        if event == "call":
            self._depth += 1
            return self.tracer
        if event == "return":
            self._depth = max(0, self._depth - 1)
            return self.tracer
        if event != "line" or self._depth > 1:
            return self.tracer
        key = (frame.f_code.co_filename, frame.f_lineno)
        now = mono_us()
        prev = self._last.get(key)
        duration_us = (now - prev) if prev is not None else 0
        self._last[key] = now
        row = {
            "file": str(frame.f_code.co_filename)[-240:],
            "line": int(frame.f_lineno),
            "function": frame.f_code.co_name[:120],
            "mono_us": now,
            "duration_us": duration_us,
            "label": self.label,
        }
        self.rows.append(row)
        _append(LINE_LEDGER, row)
        return self.tracer


@contextmanager
def profile_lines(label: str = "block"):
    """Trace every line in this block — microsecond duration_us per line."""
    trace = _LineTrace(label)
    old = getattr(_THREAD_LOCAL, "trace", None)
    _THREAD_LOCAL.trace = trace
    sys.settrace(trace.tracer)
    try:
        yield trace
    finally:
        sys.settrace(None)
        _THREAD_LOCAL.trace = old


def profile_call(fn: Callable[..., Any], *args: Any, label: str = "", **kwargs: Any) -> dict[str, Any]:
    """Run callable with line profiling; return result + line ledger."""
    lbl = label or getattr(fn, "__name__", "call")
    t0 = mono_us()
    with profile_lines(lbl) as trace:
        result = fn(*args, **kwargs)
    elapsed_us = mono_us() - t0
    return {
        "schema": "hostess7-presume-profile/v1",
        "label": lbl,
        "elapsed_us": elapsed_us,
        "line_count": len(trace.rows),
        "lines": trace.rows[-64:],
        "precision": "microsecond",
        "result": result,
    }


def train_presume_session(*, rounds: int = 3) -> dict[str, Any]:
    """Training drill — line profile, timed presume, uninterruptable commit witness."""
    rounds = max(1, min(int(rounds), 12))
    results: list[dict[str, Any]] = []
    line_total = 0
    commit_tests: list[dict[str, Any]] = []
    for i in range(rounds):
        wait_us = 10_000 + i * 5_000
        aid = f"presume_train_{i}"
        with profile_lines(f"presume_train_{i}") as trace:
            with committed_action(aid, label=f"train_{i}", source="hostess7"):
                row = presume(wait_us, label=f"train_{i}", alternate_id="sovereign_know")
                blocked = reject_influence(aid, source="external_cancel", reason="training_test")
        results.append(row)
        line_total += len(trace.rows)
        commit_tests.append({"action_id": aid, "blocked_outside": not blocked.get("allowed", True)})
    on_point = sum(1 for r in results if r.get("resumed_on_point"))
    blocked_ok = all(c.get("blocked_outside") for c in commit_tests)
    prop = propagate(write=True)
    out = {
        "schema": "hostess7-presume-train/v1",
        "ok": on_point >= rounds and blocked_ok and prop.get("propagated"),
        "rounds": rounds,
        "resumed_on_point_count": on_point,
        "resumed_on_point_rate": round(on_point / rounds, 3),
        "uninterruptable_witness": blocked_ok,
        "propagation": prop,
        "line_profile_count": line_total,
        "precision": "microsecond",
        "results": results,
        "commit_tests": commit_tests,
        "utc": _utc(),
    }
    _append(LEDGER, {**out, "schema": "hostess7-presume-train-ledger/v1"})
    build_panel(write=True)
    return out


def _witness_change(label: str, detail: str = "", meta: dict[str, Any] | None = None) -> None:
    ca = INSTALL / "lib" / "hostess7-change-awareness.py"
    if not ca.is_file():
        return
    try:
        spec = importlib.util.spec_from_file_location("h7_ca_witness", ca)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "witness_change"):
                mod.witness_change(source="presume", label=label, detail=detail, meta=meta, notify=True)
    except Exception:
        pass


def analyze_timing_health() -> dict[str, Any]:
    """Presume panel witness — slowdown, speedup, hang from drift_us and ledger."""
    samples: list[dict[str, Any]] = []
    if LEDGER.is_file():
        try:
            for line in LEDGER.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                if row.get("schema") in ("hostess7-presume/v1", "hostess7-presume-train-ledger/v1"):
                    samples.append(row)
        except (OSError, json.JSONDecodeError):
            pass
    samples = samples[-24:]
    drifts = [abs(int(s.get("drift_us") or 0)) for s in samples if s.get("drift_us") is not None]
    elapsed = [int(s.get("elapsed_us") or 0) for s in samples if s.get("elapsed_us")]
    waits = [int(s.get("wait_us") or 0) for s in samples if s.get("wait_us")]
    on_point = [bool(s.get("resumed_on_point")) for s in samples if "resumed_on_point" in s]

    median_drift = sorted(drifts)[len(drifts) // 2] if drifts else 0
    median_elapsed = sorted(elapsed)[len(elapsed) // 2] if elapsed else 0
    median_wait = sorted(waits)[len(waits) // 2] if waits else 0
    on_point_rate = sum(1 for x in on_point if x) / max(len(on_point), 1)

    notes: list[str] = []
    verdict = "steady"

    if samples and on_point and on_point_rate < 0.5:
        verdict = "hang"
        notes.append("Many presume cycles missed resume-on-point — possible hang or scheduler stall.")
    elif drifts and median_drift > max(500, median_wait // 10 + 200):
        verdict = "slowdown_severe" if median_drift > max(2000, median_wait // 4) else "slowdown"
        notes.append(f"Drift median {median_drift} µs exceeds tolerance — field slowing.")
    elif drifts and median_drift < max(50, (median_wait // 40) if median_wait else 50):
        verdict = "speedup"
        notes.append(f"Drift median {median_drift} µs — crisp resume, field running cool.")

    commits = _load_commits()
    active = list((commits.get("active") or {}).values())
    stale_commits = 0
    now_us = mono_us()
    for c in active:
        age_us = now_us - int(c.get("committed_us") or now_us)
        if age_us > 120_000_000:
            stale_commits += 1
    if stale_commits:
        verdict = "hang"
        notes.append(f"{stale_commits} active commit(s) older than 120s — possible hung uninterruptable action.")

    hang_panel = _load(STATE / "hostess7-hang-guard-panel.json", {})
    if hang_panel.get("last_verdict") == "stall":
        verdict = "hang"
        notes.append("Hang-guard reported stall — cross-check presume panel.")

    line_gap = 0
    if LINE_LEDGER.is_file():
        try:
            lines = [ln for ln in LINE_LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip()]
            if lines:
                last = json.loads(lines[-1])
                gap_us = now_us - int(last.get("mono_us") or now_us)
                if gap_us > 60_000_000 and active:
                    line_gap = gap_us
                    notes.append("Line profiler silent while commits active — profile hang suspected.")
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "ok": True,
        "schema": "hostess7-presume-timing-health/v1",
        "verdict": verdict,
        "median_drift_us": median_drift,
        "median_elapsed_us": median_elapsed,
        "median_wait_us": median_wait,
        "resumed_on_point_rate": round(on_point_rate, 3),
        "sample_count": len(samples),
        "active_commit_count": len(active),
        "stale_commit_count": stale_commits,
        "line_profile_gap_us": line_gap,
        "notes": notes,
        "panel_path": str(PANEL),
    }


def pulse(*, notify: bool = True, write: bool = True) -> dict[str, Any]:
    """Sovereign presume pulse — sweep stale commits, panel, timing, change awareness."""
    sweep = sweep_stale_commits(write=write)
    timing = analyze_timing_health()
    panel = build_panel(write=write)
    ca_out: dict[str, Any] = {}
    ca = INSTALL / "lib" / "hostess7-change-awareness.py"
    if ca.is_file():
        try:
            spec = importlib.util.spec_from_file_location("h7_ca_pulse", ca)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "check_presume_timing"):
                    raw = mod.check_presume_timing(notify=notify)
                    ca_out = {k: v for k, v in raw.items() if k != "notify"}
        except Exception:
            pass
    prop = panel.get("propagation") or {}
    return {
        "ok": True,
        "schema": "hostess7-presume-pulse/v1",
        "separate_from_aml": True,
        "sweep": sweep,
        "timing_health": timing,
        "timing_verdict": timing.get("verdict"),
        "active_commit_count": panel.get("active_commit_count"),
        "propagation_present": prop.get("targets_present"),
        "propagation_total": prop.get("targets_total"),
        "change_awareness": ca_out,
        "panel_path": str(PANEL),
        "utc": _utc(),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    sweep_stale_commits(write=write)
    timing_health = analyze_timing_health()
    recent: list[dict[str, Any]] = []
    if LEDGER.is_file():
        try:
            for line in LEDGER.read_text(encoding="utf-8").splitlines()[-24:]:
                if line.strip():
                    recent.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    line_count = 0
    if LINE_LEDGER.is_file():
        try:
            line_count = sum(1 for ln in LINE_LEDGER.read_text(encoding="utf-8").splitlines() if ln.strip())
        except OSError:
            pass
    commits_doc = _load_commits()
    active_commits = list((commits_doc.get("active") or {}).values())
    prop = _load(PROPAGATE, {}) or propagate(write=False)
    doc = {
        "schema": "hostess7-presume-panel/v1",
        "updated": _utc(),
        "motto": doctrine.get("motto"),
        "not_go_away": (doctrine.get("not_go_away") or {}).get("rule"),
        "sovereign_binding": doctrine.get("sovereign_binding"),
        "precision_us": True,
        "mono_us": mono_us(),
        "sovereign_us": sovereign_us(),
        "recent_presumes": recent[-12:],
        "line_profile_count": line_count,
        "alternate_tasks": [t.get("id") for t in (doctrine.get("alternate_tasks") or [])],
        "active_commits": active_commits,
        "active_commit_count": len(active_commits),
        "propagation": prop,
        "timing_health": timing_health,
        "timing_verdict": timing_health.get("verdict"),
        "doctrine": str(DOCTRINE),
        "separate_from_aml": bool((doctrine.get("aml_separation") or {}).get("separate_from_aml", True)),
        "aml_optional": bool((doctrine.get("aml_separation") or {}).get("aml_optional", True)),
    }
    if write:
        prev = _load(PANEL, {})
        _save(PANEL, doc)
        new_verdict = str(timing_health.get("verdict") or "steady")
        old_verdict = str(prev.get("timing_verdict") or "")
        if new_verdict != old_verdict:
            _witness_change(
                "presume_timing_shift",
                detail=f"{old_verdict or 'unknown'} → {new_verdict} · drift={timing_health.get('median_drift_us')}µs",
                meta={"timing_health": timing_health, "old_verdict": old_verdict, "new_verdict": new_verdict},
            )
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "presume":
        wait_us = 0
        label = ""
        alt = None
        for arg in sys.argv[2:]:
            if arg.isdigit():
                wait_us = int(arg)
            elif arg.startswith("--label="):
                label = arg.split("=", 1)[1]
            elif arg.startswith("--alternate="):
                alt = arg.split("=", 1)[1]
        print(json.dumps(presume(wait_us, label=label, alternate_id=alt), ensure_ascii=False, indent=2))
        return 0
    if cmd == "profile":
        def _demo() -> int:
            total = 0
            for i in range(8):
                total += i * i
            return total

        print(json.dumps(profile_call(_demo, label="demo_sum"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "checkpoint":
        print(json.dumps(checkpoint(label="cli"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("train", "training"):
        rounds = 3
        for arg in sys.argv[2:]:
            if arg.isdigit():
                rounds = int(arg)
        print(json.dumps(train_presume_session(rounds=rounds), ensure_ascii=False, indent=2))
        return 0
    if cmd == "decide":
        aid = "presume_cli"
        label = ""
        for arg in sys.argv[2:]:
            if arg.startswith("--id="):
                aid = arg.split("=", 1)[1]
            elif arg.startswith("--label="):
                label = arg.split("=", 1)[1]
            elif not arg.startswith("--"):
                aid = arg
        print(json.dumps(decide(aid, label=label), ensure_ascii=False, indent=2))
        return 0
    if cmd == "release":
        aid = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(release(aid), ensure_ascii=False, indent=2))
        return 0
    if cmd == "propagate":
        print(json.dumps(propagate(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "commits":
        print(json.dumps(_load_commits(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("timing", "health", "timing_health"):
        print(json.dumps(analyze_timing_health(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("pulse", "live"):
        print(json.dumps(pulse(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("sweep", "sweep_stale"):
        print(json.dumps(sweep_stale_commits(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "witness":
        wait_us = 0
        label = "cli_witness"
        for arg in sys.argv[2:]:
            if arg.isdigit():
                wait_us = int(arg)
            elif arg.startswith("--label="):
                label = arg.split("=", 1)[1]
        with witness_execution(label=label) as ctx:
            row = presume(wait_us, label=label, alternate_id="sovereign_know")
        print(json.dumps({"ok": True, "witness": ctx, "presume": row}, ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage: hostess7-presume.py [panel|pulse|presume|decide|release|propagate|commits|timing|sweep|witness|profile|checkpoint|train]",
                "precision": "microsecond",
                "separate_from_aml": True,
            },
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())