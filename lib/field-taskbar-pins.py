#!/usr/bin/env pythong
"""Taskbar pin preferences — Start + folder · terminal · browser · broadcaster."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PINS = STATE / "field-taskbar-pins.json"
DEFAULT_QUICK = (
    "view",
    "queen-terminal",
    "queen-browser",
    "field-broadcaster",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load() -> dict[str, Any]:
    try:
        return json.loads(PINS.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(doc: dict[str, Any]) -> None:
    PINS.parent.mkdir(parents=True, exist_ok=True)
    tmp = PINS.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PINS)


def get_pins() -> dict[str, Any]:
    doc = _load()
    if not doc.get("quick"):
        doc = {
            "schema": "field-taskbar-pins/v1",
            "updated": _now(),
            "quick": list(DEFAULT_QUICK),
            "unpinned": [],
            "folder_pinned": True,
        }
        _save(doc)
    return doc


def _doctrine_quick_ids(doctrine_quick: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for row in doctrine_quick:
        if isinstance(row, dict) and row.get("id"):
            ids.append(str(row["id"]))
    return ids


def apply_quick(doctrine_quick: list[dict[str, Any]], apps_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    pins = get_pins()
    unpinned = set(pins.get("unpinned") or [])
    doctrine_ids = _doctrine_quick_ids(doctrine_quick)
    if doctrine_ids:
        quick_ids = [q for q in doctrine_ids if q not in unpinned]
    else:
        quick_ids = [q for q in (pins.get("quick") or list(DEFAULT_QUICK)) if q not in unpinned]
    if pins.get("folder_pinned") is False and "view" in quick_ids:
        quick_ids = [q for q in quick_ids if q != "view"]
    out: list[dict[str, Any]] = []
    doctrine_map = {str(r.get("id")): r for r in doctrine_quick if isinstance(r, dict) and r.get("id")}
    for app_id in quick_ids:
        app = apps_by_id.get(app_id)
        if not app:
            continue
        row = dict(app)
        extra = doctrine_map.get(app_id) or {}
        if extra.get("live"):
            row["live"] = True
        if extra.get("unpinnable"):
            row["unpinnable"] = True
        elif app_id in ("view", "queen-files"):
            row["unpinnable"] = True
        out.append(row)
    return out


def set_pin(app_id: str, *, pinned: bool = True) -> dict[str, Any]:
    doc = get_pins()
    unpinned: set[str] = set(doc.get("unpinned") or [])
    quick: list[str] = list(doc.get("quick") or list(DEFAULT_QUICK))
    if app_id in ("view", "queen-files"):
        doc["folder_pinned"] = pinned
        if pinned and "view" not in quick:
            quick.insert(0, "view")
    if pinned:
        unpinned.discard(app_id)
        if app_id not in quick:
            quick.append(app_id)
    else:
        unpinned.add(app_id)
    doc["quick"] = quick
    doc["unpinned"] = sorted(unpinned)
    doc["updated"] = _now()
    _save(doc)
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "get").strip().lower()
    if action in ("get", "json", "status"):
        return get_pins()
    if action == "pin":
        return set_pin(str(body.get("id") or ""), pinned=True)
    if action == "unpin":
        return set_pin(str(body.get("id") or ""), pinned=False)
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    import sys
    if len(sys.argv) > 2:
        print(json.dumps(dispatch(json.loads(sys.argv[2])), indent=2))
    else:
        print(json.dumps(get_pins(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())