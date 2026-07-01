#!/usr/bin/env pythong
"""Sovereign clock — one import for every NEXUS module.

Everyone everything everywhere timestamps from sovereign linear time.
Wall clock is witness-only; desync is flagged, never authoritative.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
MAX_DESYNC_MS = float(os.environ.get("NEXUS_MAX_DESYNC_MS", "250"))
SCHEMA = "sovereign-clock/v1"
MOTTO = "Everyone everything everywhere knows sovereign time — never desync"

_SOVEREIGN: Any = None
_SYNC: Any = None


def _load(py: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        raise ImportError(f"{py.name} missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sovereign() -> Any:
    global _SOVEREIGN
    if _SOVEREIGN is None:
        _SOVEREIGN = _load(INSTALL / "lib" / "sovereign-time.py", "sovereign_time_clock")
    return _SOVEREIGN


def _sync() -> Any:
    global _SYNC
    if _SYNC is None:
        _SYNC = _load(INSTALL / "lib" / "field-sovereign-sync.py", "sovereign_sync_clock")
    return _SYNC


def utc_z(section: str = "general") -> str:
    """Canonical receipt timestamp — sovereign-derived, Z suffix, second precision."""
    raw = _sync().utc(section)
    if raw.endswith("Z"):
        return raw[:19] + "Z" if len(raw) > 20 else raw
    return raw


def utc_full(section: str = "general") -> str:
    """Sovereign UTC with fractional seconds."""
    return _sync().utc(section)


def utc_compact(section: str = "general") -> str:
    """Compact stamp — 20260626T223716Z."""
    ns = ns_linear()
    dt = datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)
    return dt.strftime("%Y%m%dT%H%M%SZ")


def utc_iso(section: str = "general") -> str:
    """ISO-8601 sovereign UTC."""
    ns = ns_linear()
    return datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def ns_linear() -> int:
    """Authoritative sovereign linear nanoseconds."""
    return int(_sovereign().linear_time_ns())


def mono_ns() -> int:
    return int(time.monotonic_ns())


def wall_ns() -> int:
    """Witness only — never used for receipts."""
    return int(time.time_ns())


def desync_status() -> dict[str, Any]:
    """Compare wall witness to sovereign linear — flag desync, never adjust sovereign."""
    st = _sovereign()
    sovereign_ns = int(st.linear_time_ns())
    witness_ns = wall_ns()
    skew_ms = abs(witness_ns - sovereign_ns) / 1_000_000.0
    linear = st._load_linear() if hasattr(st, "_load_linear") else {}
    red_flag = bool(linear.get("red_flag_active"))
    desynced = red_flag or skew_ms > MAX_DESYNC_MS
    return {
        "schema": "sovereign-desync/v1",
        "synced": not desynced,
        "never_desync_policy": True,
        "authoritative": "sovereign_linear",
        "witness": "wall_realtime_ns",
        "skew_ms": round(skew_ms, 3),
        "max_desync_ms": MAX_DESYNC_MS,
        "sovereign_ns": sovereign_ns,
        "wall_ns": witness_ns,
        "red_flag_active": red_flag,
        "gap_count": int(linear.get("gap_count") or 0),
        "red_flag_count": int(linear.get("red_flag_count") or 0),
        "clock_paused": False,
        "temperature_affects_linear": False,
    }


def ensure_sync(section: str = "general", *, action: str = "know") -> dict[str, Any]:
    """Stamp section on sovereign clock; take time out on desync — clock keeps advancing."""
    doc = _sync().sync_section(section, action)
    desync = desync_status()
    if not desync.get("synced"):
        st = _sovereign()
        st.take_time_out(
            kind="red_flag",
            reason="desync_detected",
            evidence=desync,
        )
        doc["desync"] = desync
        doc["take_time_out"] = True
    else:
        doc["desync"] = desync
        doc["take_time_out"] = False
    doc["never_desync"] = True
    doc["authoritative"] = "sovereign_linear"
    return doc


def know() -> dict[str, Any]:
    """Broadcast — every consumer must read this; sovereign time is the only clock."""
    st = _sovereign()
    sync_doc = _sync().manifest(refresh=False)
    desync = desync_status()
    return {
        "schema": SCHEMA,
        "motto": MOTTO,
        "utc": utc_z(),
        "utc_full": utc_full(),
        "derived_ns": ns_linear(),
        "linear_ns": ns_linear(),
        "cycle": int((sync_doc.get("cycle") or {}).get("cycle") or 0),
        "anchor_pulse": (sync_doc.get("anchor") or {}).get("pulse"),
        "desync": desync,
        "synced": bool(desync.get("synced")),
        "never_desync": True,
        "immutable_linear": True,
        "clock_paused": False,
        "take_time_out_means": "gap or red_flag only",
        "temperature_affects_linear": False,
        "ntp_affects_linear": False,
        "sections": list(_sync().SECTIONS),
        "doctrine": str(INSTALL / "data" / "sovereign-time-doctrine.json"),
        "status": st.linear_status(),
    }


def stamp_everywhere() -> dict[str, Any]:
    """Sync every section — stack-wide sovereign time awareness."""
    results: dict[str, Any] = {}
    for section in _sync().SECTIONS:
        results[section] = ensure_sync(section, action="stamp_everywhere")
    return {
        "schema": "sovereign-clock-stamp/v1",
        "motto": MOTTO,
        "sections": results,
        "utc": utc_z(),
        "desync": desync_status(),
        "never_desync": True,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "know").strip().lower()
    if cmd in ("json", "know", "status"):
        print(json.dumps(know(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "utc":
        sec = sys.argv[2] if len(sys.argv) > 2 else "general"
        print(json.dumps({"utc": utc_z(sec), "derived_ns": ns_linear(), "section": sec}, ensure_ascii=False))
        return 0
    if cmd == "desync":
        print(json.dumps(desync_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sync":
        sec = sys.argv[2] if len(sys.argv) > 2 else "general"
        print(json.dumps(ensure_sync(sec), ensure_ascii=False, indent=2))
        return 0
    if cmd == "stamp-everywhere":
        print(json.dumps(stamp_everywhere(), ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {
                "error": "usage: sovereign-clock.py [know|utc [section]|desync|sync [section]|stamp-everywhere]",
                "motto": MOTTO,
            },
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())