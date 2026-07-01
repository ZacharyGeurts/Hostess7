#!/usr/bin/env pythong
"""Unified brain state — cortex index + snapshots."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hostess7.paths import brain_state_dir, cortex_file, hostess7_root, storage_dir


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_cortex() -> dict[str, Any]:
    path = cortex_file()
    if not path.is_file():
        return {
            "schema": "hostess7-cortex/v1",
            "version": "1.0.7e",
            "root": str(hostess7_root()),
            "memory": {},
            "boots": [],
        }
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "hostess7-cortex/v1", "error": "corrupt_cortex"}


def save_cortex(doc: dict[str, Any]) -> Path:
    path = cortex_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    doc["updated"] = _now()
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return path


def snapshot(label: str = "boot") -> dict[str, Any]:
    state = brain_state_dir()
    snap_dir = state / "snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = f"{ts}-{label}.json"
    cortex = load_cortex()
    brain = storage_dir() / "brain"
    doc = {
        "schema": "hostess7-snapshot/v1",
        "ts": _now(),
        "label": label,
        "cortex": cortex,
        "brain_json_count": len(list(brain.rglob("*.json"))) if brain.is_dir() else 0,
        "state_dir": str(state),
    }
    out = snap_dir / name
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    boots = list(cortex.get("boots") or [])
    boots.append({"ts": doc["ts"], "file": name, "label": label})
    cortex["boots"] = boots[-32:]
    save_cortex(cortex)
    return {"ok": True, "snapshot": str(out), **doc}


def restore_latest() -> dict[str, Any]:
    snap_dir = brain_state_dir() / "snapshots"
    if not snap_dir.is_dir():
        return {"ok": False, "error": "no snapshots"}
    snaps = sorted(snap_dir.glob("*.json"), reverse=True)
    if not snaps:
        return {"ok": False, "error": "no snapshots"}
    try:
        doc = json.loads(snaps[0].read_text(encoding="utf-8"))
        cortex = doc.get("cortex") or {}
        save_cortex(cortex)
        return {"ok": True, "restored": snaps[0].name, "cortex": cortex}
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)}


def status() -> dict[str, Any]:
    cortex = load_cortex()
    state = brain_state_dir()
    brain = storage_dir() / "brain"
    return {
        "ok": True,
        "schema": "hostess7-state/v1",
        "version": "1.0.7e",
        "root": str(hostess7_root()),
        "state_dir": str(state),
        "cortex": cortex,
        "brain_ready": brain.is_dir() and any(brain.rglob("*.json")),
        "snapshots": len(list((state / "snapshots").glob("*.json"))) if (state / "snapshots").is_dir() else 0,
    }