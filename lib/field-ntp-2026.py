#!/usr/bin/env pythong
"""NEXUS Field NTP 2026 — operator timeserver on UDP/123, sovereign-first.

Serves RFC 5905 mode-4 responses from signed sovereign-time pulses.
No pool NTP dependency when NEXUS_SOVEREIGN_TIME_FIRST=1.
"""
from __future__ import annotations

import atexit
import fcntl
import json
import os
import socket
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL = STATE / "field-ntp-2026-panel.json"
PID_FILE = STATE / "field-ntp-2026.pid"
LOCK_FILE = STATE / "field-ntp-2026.lock"
_SERVE_LOCK: Any = None

NTP_PORT = int(os.environ.get("NEXUS_FIELD_NTP_PORT", "123"))
BIND = os.environ.get("NEXUS_FIELD_NTP_BIND", "127.0.0.1")
STRATUM = int(os.environ.get("NEXUS_FIELD_NTP_STRATUM", "1" if os.environ.get("NEXUS_LAST_HOST", "0") == "1" else "2"))
RATE_MAX = int(os.environ.get("NEXUS_FIELD_NTP_RATE_MAX", "30"))
RATE_WINDOW = float(os.environ.get("NEXUS_FIELD_NTP_RATE_WINDOW", "60"))
NTP_EPOCH = 2208988800  # 1970-01-01 to 1900-01-01

_rate: dict[str, list[float]] = {}
_stats = {"requests": 0, "replies": 0, "rejected": 0, "squidgie_blocks": 0}
_sovereign_cache: tuple[float, bool, str, dict[str, Any]] = (0.0, True, "init", {})


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


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _sovereign_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("sovereign_time", INSTALL / "lib" / "sovereign-time.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _gate_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("sovereign_gate", INSTALL / "lib" / "field-sovereign-gate.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _unix_to_ntp(ts: float) -> tuple[int, int]:
    ntp = ts + NTP_EPOCH
    sec = int(ntp)
    frac = int((ntp - sec) * 2**32) & 0xFFFFFFFF
    return sec, frac


def _parse_ntp_request(data: bytes) -> dict[str, Any] | None:
    if len(data) < 48:
        return None
    first = data[0]
    version = (first >> 3) & 0x07
    mode = first & 0x07
    if mode not in (1, 3):  # client or symmetric active
        return None
    return {"version": version, "mode": mode, "raw": data}


def _build_reply(req: bytes, *, realtime_ns: int) -> bytes:
    ts = realtime_ns / 1_000_000_000.0
    ref_s, ref_f = _unix_to_ntp(ts)
    recv_s, recv_f = _unix_to_ntp(time.time())
    tx_s, tx_f = _unix_to_ntp(time.time())
    orig = req[24:32] if len(req) >= 32 else b"\x00" * 8
    return struct.pack(
        "!BBBBIII4sIIIIII",
        0x24,
        STRATUM,
        6,
        0xFA,
        0,
        0,
        b"ELLI" if os.environ.get("NEXUS_LAST_HOST", "0") == "1" else b"NEXU",
        ref_s,
        ref_f,
        struct.unpack("!II", orig)[0],
        struct.unpack("!II", orig)[1],
        recv_s,
        recv_f,
        tx_s,
        tx_f,
    )


def _rate_ok(client: str) -> bool:
    now = time.time()
    hits = [t for t in _rate.get(client, []) if now - t <= RATE_WINDOW]
    if len(hits) >= RATE_MAX:
        return False
    hits.append(now)
    _rate[client] = hits
    return True


def _sovereign_ok() -> tuple[bool, str, dict[str, Any]]:
    """Never lose a cycle — always serve derived time; threats log only."""
    global _sovereign_cache
    if os.environ.get("NEXUS_SOVEREIGN_TIME_FIRST", "1") != "1":
        return True, "pool_fallback_allowed", {}
    now = time.time()
    if now - _sovereign_cache[0] < 0.5 and len(_sovereign_cache) > 3:
        return _sovereign_cache[1], _sovereign_cache[2], _sovereign_cache[3]
    try:
        gate = _gate_mod().gate(service="ntp", action="reply")
        reason = "sovereign_ok"
        if gate.get("threats"):
            _stats["squidgie_blocks"] += 1
            reason = "threat_logged_time_serves"
        if gate.get("verdict") == "SQUIDGIE":
            _stats["squidgie_blocks"] += 1
            reason = "squidgie_logged_time_serves"
        _sovereign_cache = (now, True, reason, gate)
        return True, reason, gate
    except Exception as exc:
        gate = {"ok": True, "never_lose_cycle": True, "error": str(exc)}
        _sovereign_cache = (now, True, f"gate_fallback:{exc}", gate)
        return True, _sovereign_cache[2], gate


def _handle(data: bytes, addr: tuple[str, int]) -> bytes | None:
    _stats["requests"] += 1
    client = f"{addr[0]}:{addr[1]}"
    if not _rate_ok(client):
        _stats["rejected"] += 1
        return None
    if _parse_ntp_request(data) is None:
        _stats["rejected"] += 1
        return None
    ok, reason, gate = _sovereign_ok()
    _stats["replies"] += 1
    realtime_ns = int(gate.get("derived_ns") or _sovereign_mod().derived_realtime_ns())
    return _build_reply(data, realtime_ns=realtime_ns)


def _release_lock() -> None:
    global _SERVE_LOCK
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    if _SERVE_LOCK is not None:
        try:
            fcntl.flock(_SERVE_LOCK.fileno(), fcntl.LOCK_UN)
            _SERVE_LOCK.close()
        except OSError:
            pass
        _SERVE_LOCK = None


def _acquire_lock() -> bool:
    global _SERVE_LOCK
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        fh = open(LOCK_FILE, "w", encoding="utf-8")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        return False
    fh.write(f"{os.getpid()}\n")
    fh.flush()
    _SERVE_LOCK = fh
    atexit.register(_release_lock)
    return True


def serve() -> int:
    if not _acquire_lock():
        return 0
    PID_FILE.write_text(f"{os.getpid()}\n", encoding="utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((BIND, NTP_PORT))
    while True:
        try:
            data, addr = sock.recvfrom(2048)
        except OSError:
            continue
        resp = _handle(data, addr)
        if resp:
            try:
                sock.sendto(resp, addr)
            except OSError:
                pass


def build_panel() -> dict[str, Any]:
    running = False
    if PID_FILE.is_file():
        try:
            os.kill(int(PID_FILE.read_text().strip().split()[0]), 0)
            running = True
        except (OSError, ValueError):
            pass
    sovereign_status: dict[str, Any] = {}
    try:
        sovereign_status = _sovereign_mod().status()
    except Exception:
        sovereign_status = {"error": "sovereign-time unavailable"}
    doc = {
        "schema": "field-ntp-2026/v1",
        "updated": _now(),
        "running": running,
        "bind": f"{BIND}:{NTP_PORT}",
        "stratum": STRATUM,
        "sovereign_first": os.environ.get("NEXUS_SOVEREIGN_TIME_FIRST", "1") == "1",
        "stats": dict(_stats),
        "sovereign": sovereign_status,
        "security_model": "field-sovereign-gate",
        "never_lose_cycle": True,
        "motto": "Operator NTP — sovereign-gated; never lose a cycle; derived time always serves.",
    }
    _save_json(PANEL, doc)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL.is_file():
        try:
            return json.loads(PANEL.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return build_panel()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "serve":
        serve()
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-ntp-2026.py [serve|build|json]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())