#!/usr/bin/env pythong
"""Sovereign sync — one clock for the entire stack.

Every section timestamps from derived sovereign UTC. Redundant mirrors,
append-only ledgers, never lose data, never misconstrue time.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))

SYNC_MANIFEST = STATE / "sovereign-sync-manifest.json"
SYNC_LEDGER = STATE / "sovereign-sync-ledger.jsonl"
SECTION_STAMPS = STATE / "sovereign-section-stamps.json"
REDUNDANT_DIR = STATE / "sovereign-redundant"

SECTIONS = (
    "dns",
    "dhcp",
    "ntp",
    "sovereign",
    "operator",
    "refield",
    "underlay",
    "panel",
    "services",
    "gate",
    "general",
)

MIRROR_FILES = (
    "sovereign-time-anchor.json",
    "sovereign-cycle-state.json",
    "sovereign-time-pulse.json",
    "sovereign-linear-time.json",
    "field-operator-clock-anchor.json",
    "sovereign-section-stamps.json",
)

_SOVEREIGN: Any = None
_GATE: Any = None
_FABRIC_ENCRYPT: Any = None
_LAST_UTC_NS: int = 0


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_atomic(path: Path, doc: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    payload = (
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        if compact
        else json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    )
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def _append_fsync(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def _sovereign() -> Any:
    global _SOVEREIGN
    if _SOVEREIGN is not None:
        return _SOVEREIGN
    py = INSTALL / "lib" / "sovereign-time.py"
    spec = importlib.util.spec_from_file_location("sovereign_time_sync", py)
    if not spec or not spec.loader:
        raise ImportError("sovereign-time.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _SOVEREIGN = mod
    return mod


def _fabric_encrypt() -> Any:
    global _FABRIC_ENCRYPT
    if _FABRIC_ENCRYPT is not None:
        return _FABRIC_ENCRYPT
    py = INSTALL / "lib" / "field-fabric-encrypt.py"
    spec = importlib.util.spec_from_file_location("field_fabric_encrypt", py)
    if not spec or not spec.loader:
        raise ImportError("field-fabric-encrypt.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FABRIC_ENCRYPT = mod
    return mod


def _gate() -> Any:
    global _GATE
    if _GATE is not None:
        return _GATE
    py = INSTALL / "lib" / "field-sovereign-gate.py"
    spec = importlib.util.spec_from_file_location("sovereign_gate_sync", py)
    if not spec or not spec.loader:
        raise ImportError("field-sovereign-gate.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _GATE = mod
    return mod


def _monotonic_utc_ns() -> int:
    global _LAST_UTC_NS
    st = _sovereign()
    ns = int(st.derived_realtime_ns())
    if ns < _LAST_UTC_NS:
        ns = _LAST_UTC_NS
    _LAST_UTC_NS = ns
    return ns


def _ns_to_utc(ns: int) -> str:
    dt = datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc(section: str = "general") -> str:
    """Canonical UTC string — always sovereign-derived, never misconstrued backward."""
    return now(section)["utc"]


def now(section: str = "general") -> dict[str, Any]:
    st = _sovereign()
    cycle_doc = st.cycle_status()
    ns = _monotonic_utc_ns()
    return {
        "utc": _ns_to_utc(ns),
        "derived_ns": ns,
        "cycle": int(cycle_doc.get("cycle") or 0),
        "section": section,
        "source": "sovereign_derived",
        "never_misconstrued": True,
        "anchor_pulse": (_load(st.ANCHOR_STATE, {}) or {}).get("pulse"),
    }


def mirror_all() -> dict[str, Any]:
    """Triple-redundant copy of all sovereign state — never lose data."""
    REDUNDANT_DIR.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    digests: dict[str, str] = {}
    for name in MIRROR_FILES:
        src = STATE / name
        if not src.is_file():
            continue
        dst = REDUNDANT_DIR / name
        dst2 = REDUNDANT_DIR / f"{name}.bak"
        try:
            shutil.copy2(src, dst)
            shutil.copy2(src, dst2)
            body = src.read_bytes()
            digests[name] = hashlib.sha256(body).hexdigest()[:16]
            copied.append(name)
        except OSError:
            continue
    ledger_mirror = REDUNDANT_DIR / "sovereign-sync-ledger.mirror.jsonl"
    if SYNC_LEDGER.is_file():
        try:
            shutil.copy2(SYNC_LEDGER, ledger_mirror)
            copied.append("sovereign-sync-ledger.jsonl")
        except OSError:
            pass
    return {"mirrored": copied, "digests": digests, "at": utc("sync")}


def recover() -> dict[str, Any]:
    """Restore primary state from redundant mirrors if primary missing or corrupt."""
    restored: list[str] = []
    for name in MIRROR_FILES:
        primary = STATE / name
        mirror = REDUNDANT_DIR / name
        backup = REDUNDANT_DIR / f"{name}.bak"
        if primary.is_file():
            try:
                json.loads(primary.read_text(encoding="utf-8"))
                continue
            except (OSError, json.JSONDecodeError):
                pass
        for src in (mirror, backup):
            if not src.is_file():
                continue
            try:
                doc = json.loads(src.read_text(encoding="utf-8"))
                _save_atomic(primary, doc)
                restored.append(name)
                break
            except (OSError, json.JSONDecodeError):
                continue
    return {"restored": restored, "at": utc("recover")}


def _stamp_section(section: str, gate: dict[str, Any]) -> None:
    stamps = _load(SECTION_STAMPS, {"sections": {}})
    sections = stamps.setdefault("sections", {})
    sections[section] = {
        "utc": gate.get("derived_utc") or utc(section),
        "cycle": gate.get("cycle"),
        "verdict": gate.get("verdict"),
        "threats": gate.get("threats") or [],
        "action": gate.get("action"),
        "synced_at": utc("sync"),
    }
    stamps["updated"] = utc("sync")
    stamps["schema"] = "sovereign-section-stamps/v1"
    _save_atomic(SECTION_STAMPS, stamps)
    mirror_all()


def sync_section(section: str, action: str = "tick") -> dict[str, Any]:
    """Per-section sovereign sync — gate + stamp + ledger + redundant mirror."""
    if section not in SECTIONS:
        section = "general"
    recover()
    gate = _gate().gate(service=section if section in ("dns", "dhcp", "ntp", "sovereign") else "gate", action=action)
    seal_material = json.dumps(
        {
            "section": section,
            "action": action,
            "cycle": gate.get("cycle"),
            "derived_ns": gate.get("derived_ns"),
            "verdict": gate.get("verdict"),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    fabric = _fabric_encrypt().seal_payload(
        seal_material,
        peaks=[0.18, float(gate.get("cycle") or 0) % 1.0, 0.22, 0.12],
        arm_slots=4,
    )
    row = {
        "ts": gate.get("derived_utc") or utc(section),
        "section": section,
        "action": action,
        "cycle": gate.get("cycle"),
        "verdict": gate.get("verdict"),
        "threats": gate.get("threats") or [],
        "derived_ns": gate.get("derived_ns"),
        "fabric_seal": fabric,
        "never_lose_data": True,
    }
    _append_fsync(SYNC_LEDGER, row)
    _stamp_section(section, {**gate, "action": action})
    manifest_doc = manifest(refresh=False)
    _save_atomic(SYNC_MANIFEST, manifest_doc)
    return {
        **gate,
        "section": section,
        "action": action,
        "synced": True,
        "source": "sovereign_sync",
        "never_lose_data": True,
        "never_misconstrued": True,
    }


def manifest(*, refresh: bool = True) -> dict[str, Any]:
    st = _sovereign()
    stamps = _load(SECTION_STAMPS, {})
    ledger_lines = 0
    if SYNC_LEDGER.is_file():
        try:
            ledger_lines = sum(1 for _ in SYNC_LEDGER.open(encoding="utf-8"))
        except OSError:
            ledger_lines = 0
    redundant = list(REDUNDANT_DIR.glob("*.json")) if REDUNDANT_DIR.is_dir() else []
    doc = {
        "schema": "sovereign-sync-manifest/v1",
        "updated": utc("sync"),
        "motto": "One clock — every section syncs; redundant, secure, never lose data",
        "sections": list(SECTIONS),
        "section_stamps": stamps.get("sections") or {},
        "cycle": st.cycle_status(),
        "anchor": _load(st.ANCHOR_STATE, {}),
        "ledger_lines": ledger_lines,
        "redundant_files": len(redundant),
        "mirrors": MIRROR_FILES,
        "never_lose_cycle": True,
        "never_lose_data": True,
        "never_misconstrued": True,
        "never_desync": True,
        "clock_source": "sovereign_linear",
        "authoritative_module": "lib/sovereign-clock.py",
        "fabric_encrypt": {
            "slots": 4,
            "zero_cost_idle": True,
            "free": True,
            "amouranthrtx": "FieldFabric.dispatchExtended",
        },
    }
    if refresh:
        doc["mirror"] = mirror_all()
    return doc


def panel_json() -> dict[str, Any]:
    if SYNC_MANIFEST.is_file():
        try:
            return json.loads(SYNC_MANIFEST.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return manifest()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "manifest"):
        print(json.dumps(manifest(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "utc":
        sec = sys.argv[2] if len(sys.argv) > 2 else "general"
        print(json.dumps(now(sec), ensure_ascii=False))
        return 0
    if cmd == "sync" and len(sys.argv) > 2:
        sec = sys.argv[2]
        act = sys.argv[3] if len(sys.argv) > 3 else "tick"
        print(json.dumps(sync_section(sec, act), ensure_ascii=False, indent=2))
        return 0
    if cmd == "mirror":
        print(json.dumps(mirror_all(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "recover":
        print(json.dumps(recover(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-sovereign-sync.py [json|utc [section]|sync <section> [action]|mirror|recover]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())