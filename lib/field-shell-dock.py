#!/usr/bin/env pythong
"""Field shell dock — taskbar tray, sovereign time handshake, bookmarks flyout payload."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import socket
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-shell-dock-doctrine.json"
SETTINGS = STATE / "field-shell-dock-settings.json"
SESSION = STATE / "field-shell-dock-session.json"
BOOKMARKS = STATE / "field-shell-dock-bookmarks.json"
PANEL = STATE / "field-shell-dock-panel.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_py(name: str, path: Path) -> Any | None:
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


def _run_json(script: Path, *args: str, timeout: int = 12) -> dict[str, Any]:
    if not script.is_file():
        return {}
    try:
        proc = subprocess.run(
            [os.environ.get("PYTHON", "pythong"), str(script), *args],
            capture_output=True, text=True, timeout=timeout,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return {}


def _ntp_udp_offset(host: str = "pool.ntp.org", timeout: float = 2.0) -> dict[str, Any]:
    """Witness-only NTP offset — does not adjust sovereign linear time."""
    t0 = time.time()
    try:
        packet = bytearray(48)
        packet[0] = 0x1B
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(packet, (host, 123))
            data, _ = sock.recvfrom(2048)
        if len(data) < 48:
            return {"ok": False, "host": host, "error": "short_response"}
        t3 = time.time()
        ints = struct.unpack("!12I", data[:48])
        t1 = ints[8] + ints[9] / 2**32
        t2 = ints[10] + ints[11] / 2**32
        epoch_1900 = 2208988800
        t1 -= epoch_1900
        t2 -= epoch_1900
        offset_sec = ((t2 - t1) + (t3 - t0)) / 2.0
        rtt_ms = (t3 - t0) * 1000.0
        return {
            "ok": True,
            "host": host,
            "method": "ntp_udp",
            "offset_ns": int(offset_sec * 1_000_000_000),
            "offset_ms": round(offset_sec * 1000, 6),
            "rtt_ms": round(rtt_ms, 3),
            "stratum": data[1] if len(data) > 1 else None,
        }
    except (OSError, struct.error, socket.timeout) as exc:
        return {"ok": False, "host": host, "method": "ntp_udp", "error": str(exc)[:120]}


def _chrony_tracking() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["chronyc", "tracking"],
            capture_output=True, text=True, timeout=4,
        )
        if proc.returncode != 0:
            return {"ok": False, "method": "chronyc"}
        text = proc.stdout or ""
        ref = re.search(r"Reference time\s*:\s*(.+)", text)
        offset = re.search(r"System time\s*:\s*([0-9.eE+-]+)\s*seconds", text)
        rms = re.search(r"RMS offset\s*:\s*([0-9.eE+-]+)\s*seconds", text)
        off_sec = float(offset.group(1)) if offset else 0.0
        return {
            "ok": True,
            "method": "chronyc",
            "reference": ref.group(1).strip() if ref else None,
            "offset_ns": int(off_sec * 1_000_000_000),
            "offset_ms": round(off_sec * 1000, 6),
            "rms_offset_ms": round(float(rms.group(1)) * 1000, 6) if rms else None,
        }
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"ok": False, "method": "chronyc"}


def _timedatectl_timesync() -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["timedatectl", "show-timesync", "--property=ServerName,ServerAddress,OffsetUSec,RTTUSec"],
            capture_output=True, text=True, timeout=4,
        )
        if proc.returncode != 0:
            return {"ok": False, "method": "timedatectl"}
        props: dict[str, str] = {}
        for line in (proc.stdout or "").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()
        off_usec = int(props.get("OffsetUSec", "0").replace("us", "").replace("+", "") or "0")
        return {
            "ok": True,
            "method": "timedatectl",
            "server": props.get("ServerName") or props.get("ServerAddress"),
            "offset_ns": off_usec * 1000,
            "offset_ms": round(off_usec / 1000.0, 6),
            "rtt_ms": round(int(props.get("RTTUSec", "0").replace("us", "") or "0") / 1000.0, 3),
        }
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return {"ok": False, "method": "timedatectl"}


def _best_timeserver_handshake() -> dict[str, Any]:
    probes = [
        _chrony_tracking(),
        _timedatectl_timesync(),
        _ntp_udp_offset("127.0.0.1"),
        _ntp_udp_offset("pool.ntp.org"),
    ]
    field_ntp = _run_json(INSTALL / "lib" / "field-ntp-2026.py", "json")
    if field_ntp.get("running"):
        probes.insert(0, {
            "ok": True,
            "method": "field-ntp-2026",
            "host": field_ntp.get("bind"),
            "offset_ns": 0,
            "offset_ms": 0.0,
            "sovereign_first": field_ntp.get("sovereign_first"),
        })
    ok = [p for p in probes if p.get("ok")]
    if not ok:
        return {"ok": False, "probes": probes, "best": None}
    best = min(
        ok,
        key=lambda p: (
            abs(p.get("offset_ns") or 0),
            p.get("rtt_ms") if p.get("rtt_ms") is not None else 9999,
        ),
    )
    return {"ok": True, "probes": probes, "best": best, "probe_count": len(probes), "ok_count": len(ok)}


def _sovereign_bundle() -> dict[str, Any]:
    clock = _import_py("sovereign_clock", INSTALL / "lib" / "sovereign-clock.py")
    st = _run_json(INSTALL / "lib" / "sovereign-time.py", "status")
    sync = _run_json(INSTALL / "lib" / "field-sovereign-sync.py", "json")
    desync = clock.desync_status() if clock and hasattr(clock, "desync_status") else {}
    know = clock.know() if clock and hasattr(clock, "know") else {}
    redundant = {
        "sovereign_time": bool(st.get("immutable_linear")),
        "sovereign_sync": bool(sync.get("never_desync")),
        "desync_clear": bool(desync.get("synced")),
        "mirrors": int(sync.get("redundant_files") or 0) >= 0,
    }
    all_synced = all(redundant.values()) and not st.get("linear", {}).get("red_flag_active")
    return {
        "status": st,
        "sync": sync,
        "desync": desync,
        "know": know,
        "redundant_validation": redundant,
        "all_synced": all_synced,
        "linear_ns": st.get("linear_ns") or desync.get("sovereign_ns"),
        "derived_utc": st.get("derived_utc") or know.get("utc"),
    }


def _update_session(handshake: dict[str, Any], sovereign: dict[str, Any]) -> dict[str, Any]:
    sess = _load(SESSION, {})
    if not sess.get("session_start"):
        sess["session_start"] = _now_iso()
        sess["session_id"] = hex(int(time.time_ns()))[2:][:12]
    best = (handshake.get("best") or {}) if handshake.get("ok") else {}
    offset_ns = int(best.get("offset_ns") or 0)
    sovereign_ns = int(sovereign.get("linear_ns") or 0)
    if "baseline_offset_ns" not in sess and handshake.get("ok"):
        sess["baseline_offset_ns"] = offset_ns
        sess["baseline_sovereign_ns"] = sovereign_ns
        sess["baseline_method"] = best.get("method")
    prev_offset = int(sess.get("last_offset_ns") or sess.get("baseline_offset_ns") or 0)
    drift_session_ns = offset_ns - int(sess.get("baseline_offset_ns") or offset_ns)
    drift_step_ns = offset_ns - prev_offset
    sess.update({
        "updated": _now_iso(),
        "last_offset_ns": offset_ns,
        "last_sovereign_ns": sovereign_ns,
        "last_method": best.get("method"),
        "drift_since_session_ns": drift_session_ns,
        "drift_since_session_ms": round(drift_session_ns / 1_000_000, 9),
        "drift_step_ns": drift_step_ns,
        "wall_skew_ms": sovereign.get("desync", {}).get("skew_ms"),
    })
    _save_atomic(SESSION, sess)
    return sess


def _format_time(sovereign: dict[str, Any], fmt: str) -> dict[str, str]:
    utc_raw = sovereign.get("derived_utc") or _now_iso()
    try:
        dt = datetime.fromisoformat(utc_raw.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now(timezone.utc)
    linear_ns = int(sovereign.get("linear_ns") or 0)
    formats = {
        "long": dt.strftime("%A, %B %d, %H:%M"),
        "short": dt.strftime("%b %d · %H:%M"),
        "iso": dt.strftime("%Y-%m-%dT%H:%M:%S") + "Z",
        "sovereign": f"{dt.strftime('%Y-%m-%dT%H:%M:%S')}.{linear_ns % 1_000_000_000:09d}Z",
    }
    return {"active": formats.get(fmt, formats["long"]), "all": formats}


def _bookmarks() -> list[dict[str, Any]]:
    saved = _load(BOOKMARKS, {})
    if saved.get("items"):
        return list(saved["items"])
    doctrine = _load(DOCTRINE, {})
    return list(doctrine.get("bookmarks_seed") or [])


def _settings() -> dict[str, Any]:
    saved = _load(SETTINGS, {})
    doctrine = _load(DOCTRINE, {})
    return {
        "time_format": saved.get("time_format") or doctrine.get("default_time_format") or "long",
        "active_icon": saved.get("active_icon"),
        "poll_ms": doctrine.get("poll_ms", 1000),
    }


_HANDSHAKE_TICK = 0


def _g16_poll_ms(doctrine: dict[str, Any]) -> int:
    g16 = doctrine.get("g16") or {}
    if os.environ.get("G16_FIELD_SPEED", "1") not in ("0", "false", "no"):
        return int(g16.get("poll_ms_fast") or doctrine.get("poll_ms") or 2500)
    return int(doctrine.get("poll_ms") or 1000)


def posture(*, active_icon: str | None = None) -> dict[str, Any]:
    global _HANDSHAKE_TICK
    doctrine = _load(DOCTRINE, {})
    settings = _settings()
    if active_icon:
        settings["active_icon"] = active_icon
    g16 = doctrine.get("g16") or {}
    every_n = max(1, int(g16.get("handshake_every_n") or 1))
    _HANDSHAKE_TICK += 1
    if _HANDSHAKE_TICK % every_n == 1:
        handshake = _best_timeserver_handshake()
    else:
        handshake = _load(PANEL, {}).get("timeserver_handshake") or _best_timeserver_handshake()
    sovereign = _sovereign_bundle()
    session = _update_session(handshake, sovereign)
    tf = settings.get("time_format") or "long"
    icons = list(doctrine.get("dock_icons") or [])
    for ic in icons:
        ic["active"] = ic.get("id") == (settings.get("active_icon") or active_icon)
    doc = {
        "schema": "field-shell-dock/v1",
        "ts": _now_iso(),
        "ok": True,
        "doctrine": doctrine.get("title"),
        "dock_icons": icons,
        "bookmarks": _bookmarks(),
        "settings": settings,
        "time_formats": doctrine.get("time_formats") or [],
        "time_display": _format_time(sovereign, tf),
        "sovereign": sovereign,
        "timeserver_handshake": handshake,
        "session": session,
        "poll_ms": _g16_poll_ms(doctrine),
        "g16": {"profile": (g16 or {}).get("profile", "field_opt"), "handshake_every_n": every_n},
        "routes": {
            "panel": "/api/field-shell-dock",
            "audio": "/field-audio-settings",
            "znetwork": "/api/znetwork",
        },
        "posture": (
            f"Sovereign synced={sovereign.get('all_synced')} · "
            f"session drift {session.get('drift_since_session_ns', 0)} ns · "
            f"handshake {((handshake.get('best') or {}).get('method') or 'pending')}"
        ),
    }
    _save_atomic(PANEL, doc)
    return doc


def save_settings(patch: dict[str, Any]) -> dict[str, Any]:
    allowed = {"time_format", "active_icon"}
    saved = _load(SETTINGS, {})
    for k, v in patch.items():
        if k in allowed:
            saved[k] = v
    _save_atomic(SETTINGS, saved)
    return posture(active_icon=saved.get("active_icon"))


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    active = os.environ.get("FIELD_SHELL_ACTIVE_ICON")
    if len(sys.argv) > 2 and cmd in ("json", "status", "posture", "sync"):
        cand = sys.argv[2].strip()
        if cand and not cand.startswith("{"):
            active = cand
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(active_icon=active), ensure_ascii=False, indent=2))
        return 0
    if cmd == "settings" and len(sys.argv) > 2:
        try:
            patch = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            patch = {}
        print(json.dumps(save_settings(patch), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sync":
        _run_json(INSTALL / "lib" / "field-sovereign-sync.py", "sync", "ntp", "dock_handshake")
        print(json.dumps(posture(active_icon=active), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-shell-dock.py [json|settings JSON|sync]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())