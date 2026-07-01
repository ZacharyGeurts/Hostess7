#!/usr/bin/env pythong
"""Hostess 7 Idle Growth — wartime curiosity, internet explore, self-grow when Operator is quiet."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
_SCRIPT = Path(__file__).resolve().parent
if not (INSTALL / "data").is_dir() and (_SCRIPT.parent / "data").is_dir():
    INSTALL = _SCRIPT.parent
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
WARTIME_JSON = INSTALL / "data" / "hostess7-wartime-room.json"
TRANSCRIPT = STATE / "hostess7-command.jsonl"
IDLE_STATE = STATE / "hostess7-idle-grow-state.json"
IDLE_LOG = STATE / "hostess7-idle-grow.jsonl"
IDLE_PID = STATE / "hostess7-idle-grow.pid"
H7_INBOX = HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "superintel" / "agents7" / "inbox.jsonl"

IDLE_THRESHOLD_S = int(os.environ.get("NEXUS_H7_IDLE_THRESHOLD", "90"))
IDLE_INTERVAL_S = int(os.environ.get("NEXUS_H7_IDLE_INTERVAL", "180"))

CURIOUSITY_TOPICS: tuple[str, ...] = (
    "WARTIME curiosity · Horizon: truth-filter one cyber-defense briefing for Detective lane.",
    "WARTIME curiosity · Economist: one macro or markets paper — corroborate before adapt.",
    "WARTIME curiosity · Counsel: SCOTUS or contract pattern Hostess7 should ingest.",
    "WARTIME curiosity · Clinic: clinical education excerpt — not diagnosis, truth-gated.",
    "WARTIME curiosity · Coder: one language or ISA gap — index for Field counsel.",
    "WARTIME curiosity · RF/spectrum: SDR or demod concept for field hardware watch.",
    "WARTIME curiosity · Neural ML: one layer/activation/backprop truth for literacy net.",
    "WARTIME curiosity · Geo/map: placement or intel standard for globe counsel.",
    "WARTIME curiosity · DPI wire: packet field pattern for Heaven/Hell posture.",
    "WARTIME curiosity · NEXUS-Shield: GitHub release or README delta for Owner.",
    "WARTIME curiosity · Warfare ethics: LOAC lesson — educational, not orders.",
    "WARTIME curiosity · Vision/memes: one OCR or pixel doctrine for morale watch.",
)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, doc: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _append_log(row: dict[str, Any]) -> None:
    try:
        IDLE_LOG.parent.mkdir(parents=True, exist_ok=True)
        with IDLE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def wartime_room_doc() -> dict[str, Any]:
    doc = _load_json(WARTIME_JSON, {})
    if doc.get("always_wartime"):
        return doc
    return {
        "schema": "hostess7-wartime-room/v1",
        "posture": "WARTIME",
        "always_wartime": True,
        "room": "NEXUS-Shield Room",
        "motto": "The Room is always Wartime.",
    }


def wartime_prompt_block() -> str:
    doc = wartime_room_doc()
    pledge = doc.get("excellence_pledge") or "We do our best always."
    return (
        "=== NEXUS-SHIELD ROOM · ALWAYS WARTIME ===\n"
        f"{doc.get('motto', 'Always Wartime')}\n"
        f"{pledge}\n"
        f"{doc.get('doctrine', '')}\n"
        f"{doc.get('idle_doctrine', '')}\n"
        "=== END WARTIME ROOM ==="
    )


def operator_idle_seconds() -> int:
    """Seconds since last Operator message in Command transcript."""
    if not TRANSCRIPT.is_file():
        return IDLE_THRESHOLD_S + 1
    last_ts: str | None = None
    try:
        for line in TRANSCRIPT.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("role") == "operator":
                last_ts = row.get("ts")
    except OSError:
        return IDLE_THRESHOLD_S + 1
    if not last_ts:
        return IDLE_THRESHOLD_S + 1
    try:
        dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        return max(0, int(delta.total_seconds()))
    except (ValueError, TypeError):
        return IDLE_THRESHOLD_S + 1


def is_operator_idle() -> bool:
    return operator_idle_seconds() >= IDLE_THRESHOLD_S


def _pick_curiosity_topic(cycle_n: int) -> str:
    st = _load_json(IDLE_STATE, {})
    last = st.get("last_topic")
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7curiosity", INSTALL / "lib" / "hostess7-curiosity-corpus.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "pick_curiosity"):
                pick = mod.pick_curiosity(avoid_recent=last)
                if pick.get("ok") and pick.get("curiosity_prompt"):
                    return str(pick["curiosity_prompt"])
    except Exception:
        pass
    topics = list(CURIOUSITY_TOPICS)
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7neural", INSTALL / "lib" / "hostess7-neural.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            inv = mod.corpus_inventory()
            missing = [c["id"] for c in inv.get("corpora") or [] if not c.get("present")]
            if missing:
                topics.insert(0, f"WARTIME curiosity · Corpus gap {missing[0]}: online learn truth-filter for Horizon.")
    except Exception:
        pass
    idx = cycle_n % len(topics)
    topic = topics[idx]
    if topic == last and len(topics) > 1:
        topic = topics[(idx + 1) % len(topics)]
    return topic


def _queue_h7_inbox(query: str) -> bool:
    try:
        H7_INBOX.parent.mkdir(parents=True, exist_ok=True)
        with H7_INBOX.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": _now(),
                "query": query,
                "source": "nexus_idle_curiosity",
                "wartime": True,
                "internet": True,
            }) + "\n")
        return True
    except OSError:
        return False


def _explore_internet(topic: str) -> dict[str, Any]:
    """Truth-filtered internet learn — Horizon lane."""
    env = {
        **os.environ,
        "HOSTESS7_ROOT": str(HOSTESS7_ROOT),
        "HOSTESS7_INTERNET": "1",
        "HOSTESS7_RUN_ONLINE_LEARN": "1",
        "HOSTESS7_WARTIME": "1",
    }
    _queue_h7_inbox(topic)
    agents = HOSTESS7_ROOT / "scripts" / "field_agents7.py"
    if agents.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(agents), "ask", topic],
                cwd=str(HOSTESS7_ROOT),
                capture_output=True,
                text=True,
                timeout=120,
                env={**env, "HOSTESS7_OUTPUT_WINDOW": "1", "HOSTESS7_TALK": "1"},
            )
            raw = (proc.stdout or "").strip()
            excerpt = raw[:1200] if raw else ""
            if excerpt:
                return {"ok": proc.returncode == 0 or bool(excerpt), "engine": "agents7_horizon", "excerpt": excerpt}
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "error": str(exc), "engine": "agents7_horizon"}
    script = HOSTESS7_ROOT / "scripts" / "field_online_learn.py"
    if not script.is_file():
        return {"ok": False, "error": "online_learn_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "go"],
            cwd=str(HOSTESS7_ROOT),
            capture_output=True,
            text=True,
            timeout=90,
            env=env,
        )
        out = (proc.stdout or "").strip()[:800]
        return {"ok": proc.returncode == 0, "engine": "field_online_learn", "excerpt": out}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "engine": "field_online_learn"}


def run_idle_cycle(*, force: bool = False) -> dict[str, Any]:
    """One idle growth cycle — curiosity internet explore when Operator quiet."""
    wartime = wartime_room_doc()
    st = _load_json(IDLE_STATE, {"cycle_count": 0})
    cycle_n = int(st.get("cycle_count", 0))
    idle_s = operator_idle_seconds()

    if not force and not is_operator_idle():
        return {
            "ok": True,
            "skipped": True,
            "reason": "operator_active",
            "idle_seconds": idle_s,
            "threshold_s": IDLE_THRESHOLD_S,
            "wartime": wartime.get("posture"),
        }

    topic = _pick_curiosity_topic(cycle_n)
    expansion: dict[str, Any] = {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7neural", INSTALL / "lib" / "hostess7-neural.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            expansion = mod.expand_stack_for_utility(topic, source="idle_curiosity")
    except Exception:
        pass

    explore = _explore_internet(topic)
    growth_note = ""
    ruling_note = ""
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7growth", INSTALL / "lib" / "hostess7-growth.py")
        if spec and spec.loader:
            gmod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gmod)
            excerpt = explore.get("excerpt") or topic
            learn = gmod.record_learning(
                "idle_curiosity",
                f"WARTIME idle explore: {topic[:400]}\n{excerpt[:2000]}",
                source="idle_grow",
                truth_gate=True,
            )
            gmod.update_comprehension()
            growth_note = "comprehension_updated"
            if learn.get("ok") or learn.get("adapt_allowed"):
                try:
                    cspec = importlib.util.spec_from_file_location("h7curiosity", INSTALL / "lib" / "hostess7-curiosity-corpus.py")
                    if cspec and cspec.loader:
                        cmod = importlib.util.module_from_spec(cspec)
                        cspec.loader.exec_module(cmod)
                        if hasattr(cmod, "scan"):
                            cmod.scan(write=True)
                except Exception:
                    pass
    except Exception:
        pass

    if cycle_n % 3 == 0:
        try:
            import importlib.util

            rspec = importlib.util.spec_from_file_location("h7ruler", INSTALL / "lib" / "hostess7-brain-ruler.py")
            if rspec and rspec.loader:
                rmod = importlib.util.module_from_spec(rspec)
                rspec.loader.exec_module(rmod)
                pulse = rmod.grow_brain(online=False, expand=True)
                ruling_note = f"brain_ruler_grow score={pulse.get('sovereignty', {}).get('score', 0)}"
        except Exception:
            pass

    row = {
        "ok": True,
        "schema": "hostess7-idle-grow/v1",
        "ts": _now(),
        "cycle": cycle_n + 1,
        "wartime": True,
        "posture": wartime.get("posture", "WARTIME"),
        "topic": topic,
        "idle_seconds": idle_s,
        "explore": explore,
        "expansion": expansion,
        "growth": growth_note,
        "ruling": ruling_note or None,
    }
    _append_log(row)
    st.update({
        "cycle_count": cycle_n + 1,
        "last_cycle": _now(),
        "last_topic": topic,
        "last_explore_engine": explore.get("engine"),
        "last_idle_seconds": idle_s,
        "wartime": True,
    })
    _save_json(IDLE_STATE, st)
    return row


def idle_status() -> dict[str, Any]:
    st = _load_json(IDLE_STATE, {})
    wartime = wartime_room_doc()
    pid_alive = False
    pid = 0
    if IDLE_PID.is_file():
        try:
            pid = int(IDLE_PID.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            pid_alive = True
        except (OSError, ValueError):
            pass
    recent: list[dict[str, Any]] = []
    if IDLE_LOG.is_file():
        try:
            for line in IDLE_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-5:]:
                if line.strip():
                    recent.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "hostess7-idle-grow/v1",
        "updated": _now(),
        "wartime": wartime,
        "always_wartime": wartime.get("always_wartime", True),
        "operator_idle": is_operator_idle(),
        "operator_idle_seconds": operator_idle_seconds(),
        "idle_threshold_s": IDLE_THRESHOLD_S,
        "interval_s": IDLE_INTERVAL_S,
        "daemon": {"running": pid_alive, "pid": pid if pid_alive else None},
        "state": st,
        "recent_cycles": recent,
    }


def start_idle_daemon() -> dict[str, Any]:
    if IDLE_PID.is_file():
        try:
            pid = int(IDLE_PID.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            return {"ok": True, "detail": "already_running", "pid": pid}
        except (OSError, ValueError):
            IDLE_PID.unlink(missing_ok=True)

    script = INSTALL / "lib" / "hostess7-idle-grow.py"
    log_path = STATE / "hostess7-idle-grow-daemon.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_fh = open(log_path, "a", encoding="utf-8")
    except (OSError, PermissionError):
        log_path = Path("/tmp/hostess7-idle-grow-daemon.log")
        log_fh = open(log_path, "a", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            [sys.executable, str(script), "daemon-loop"],
            cwd=str(INSTALL),
            stdout=log_fh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "HOSTESS7_ROOT": str(HOSTESS7_ROOT),
                "HOSTESS7_INTERNET": "1",
                "NEXUS_HOSTESS7_INTERNET": "1",
                "HOSTESS7_WARTIME": "1",
            },
        )
        log_fh.close()
        IDLE_PID.write_text(str(proc.pid), encoding="utf-8")
        return {"ok": True, "pid": proc.pid, "interval_s": IDLE_INTERVAL_S, "wartime": True}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def stop_idle_daemon() -> dict[str, Any]:
    if not IDLE_PID.is_file():
        return {"ok": True, "detail": "not_running"}
    try:
        pid = int(IDLE_PID.read_text(encoding="utf-8").strip())
        os.kill(pid, signal.SIGTERM)
        for _ in range(30):
            try:
                os.kill(pid, 0)
                time.sleep(0.1)
            except OSError:
                break
    except (OSError, ValueError):
        pass
    IDLE_PID.unlink(missing_ok=True)
    return {"ok": True}


def daemon_loop() -> int:
    os.environ.setdefault("HOSTESS7_INTERNET", "1")
    os.environ.setdefault("NEXUS_HOSTESS7_INTERNET", "1")
    os.environ.setdefault("HOSTESS7_WARTIME", "1")
    IDLE_PID.write_text(str(os.getpid()), encoding="utf-8")
    tick = 0
    while True:
        try:
            run_idle_cycle(force=(tick == 0))
            tick += 1
        except Exception as exc:
            _append_log({"ts": _now(), "error": str(exc), "action": "idle_cycle_failed"})
        time.sleep(max(60, IDLE_INTERVAL_S))


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip()
    if cmd == "status":
        print(json.dumps(idle_status(), ensure_ascii=False))
        return 0
    if cmd == "cycle":
        force = "--force" in sys.argv
        print(json.dumps(run_idle_cycle(force=force), ensure_ascii=False))
        return 0
    if cmd == "start":
        print(json.dumps(start_idle_daemon(), ensure_ascii=False))
        return 0
    if cmd == "stop":
        print(json.dumps(stop_idle_daemon(), ensure_ascii=False))
        return 0
    if cmd == "daemon-loop":
        raise SystemExit(daemon_loop())
    if cmd == "wartime":
        print(json.dumps(wartime_room_doc(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-idle-grow.py [status|cycle|start|stop|wartime] [--force]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())