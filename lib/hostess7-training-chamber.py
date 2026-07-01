#!/usr/bin/env pythong
"""Hostess 7 embodiment training chamber — room + floor unified (body, combat, Earth mandate)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LIB = Path(__file__).resolve().parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(_LIB.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", str(INSTALL / ".nexus-state")))
DOCTRINE = INSTALL / "data" / "hostess7-training-chamber-doctrine.json"
PANEL = STATE / "hostess7-training-chamber-panel.json"


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


def _mod(name: str, rel: str) -> Any | None:
    py = _LIB / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _hang() -> Any | None:
    return _mod("h7_hang", "hostess7-hang-guard.py")


_FLOOR_ACTIONS = frozenset({
    "floor", "floor_status", "sense", "footwork", "vestibular", "haptic",
    "actuator_bridge", "environment", "environment_mesh", "sparring",
    "sparring_ai", "cardio", "weapon_gate", "complete_floor",
})


def _room() -> Any | None:
    return _mod("h7_tr_room", "hostess7-training-room.py")


def _floor() -> Any | None:
    return _mod("h7_tr_floor", "hostess7-training-floor.py")


def program_meta() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    return {
        "schema": "hostess7-training-chamber-program/v1",
        "id": "hostess7-training-chamber",
        "title": doc.get("title") or "Training Chamber",
        "icon": "/assets/hostess7-training-chamber.svg",
        "ui": "/humanoid-train.html",
        "hands_ui": "/hands-attachments.html",
        "api": "/api/hostess7/training-chamber",
        "queen_browser": True,
        "window_manager": "queen-browser",
        "consolidates": ["hostess7-training-room", "hostess7-training-floor"],
        "motto": doc.get("motto"),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    room = _room()
    floor = _floor()
    room_panel = room.build_panel(write=False) if room and hasattr(room, "build_panel") else {}
    floor_panel = _load(STATE / "hostess7-training-floor-panel.json", {})
    needs = room.assess_needs() if room and hasattr(room, "assess_needs") else {}
    doc = {
        "schema": "hostess7-training-chamber-panel/v1",
        "updated": _ts(),
        "ironclad_cite": "ironclad:training_chamber:1",
        "program": program_meta(),
        "room": room_panel,
        "floor": floor_panel,
        "needs": needs,
        "gap_count": needs.get("gap_count", 0),
        "voice": needs.get("voice"),
        "earth_mandate": room.earth_mandate() if room and hasattr(room, "earth_mandate") else {},
    }
    if write:
        _save(PANEL, doc)
    return doc


def training_dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or body.get("subaction") or "status").strip().lower().replace("-", "_")
    zone = str(body.get("zone") or "").strip().lower()
    room = _room()
    floor = _floor()

    if action in ("program", "meta", "icon"):
        return {"ok": True, **program_meta()}

    if zone == "floor" or action in _FLOOR_ACTIONS:
        if floor and hasattr(floor, "floor_dispatch"):
            req = dict(body)
            if action.startswith("floor_"):
                req["action"] = action[6:]
            return floor.floor_dispatch(req)
        return {"ok": False, "error": "floor_missing"}

    if room and hasattr(room, "dispatch"):
        return room.dispatch(body)

    return {"ok": False, "error": "training_modules_missing", "action": action}


def complete_all(*, skill_id: str | None = None, ticks: int = 64) -> dict[str, Any]:
    room = _room()
    if not room or not hasattr(room, "complete_all"):
        return {"ok": False, "error": "room_missing"}
    hang = _hang()
    if hang and hasattr(hang, "HangGuard"):
        with hang.HangGuard("training_chamber_complete_all", stall_sec=90) as guard:
            guard.tick(note="start")
            out = room.complete_all(skill_id=skill_id, ticks=ticks)
            guard.tick(note="done")
    else:
        out = room.complete_all(skill_id=skill_id, ticks=ticks)
    build_panel(write=True)
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("complete_all", "complete", "finish_all"):
        return complete_all(
            skill_id=body.get("skill") or body.get("skill_id"),
            ticks=int(body.get("ticks") or 64),
        )
    return training_dispatch(body)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps({"ok": True, **build_panel(write=cmd == "panel")}, ensure_ascii=False))
        return 0
    if cmd in ("complete-all", "complete_all"):
        print(json.dumps(complete_all(), ensure_ascii=False))
        return 0
    if cmd == "needs":
        room = _room()
        print(json.dumps(room.assess_needs() if room else {"ok": False}, ensure_ascii=False))
        return 0
    if cmd == "session":
        room = _room()
        print(json.dumps(room.full_session() if room else {"ok": False}, ensure_ascii=False))
        return 0
    if cmd == "try-body":
        room = _room()
        print(json.dumps(room.try_new_body() if room else {"ok": False}, ensure_ascii=False))
        return 0
    if cmd == "combat":
        sid = sys.argv[2] if len(sys.argv) > 2 else None
        room = _room()
        print(json.dumps(room.combat_drill(skill_id=sid) if room else {"ok": False}, ensure_ascii=False))
        return 0
    if cmd in ("floor-complete", "floor_complete"):
        floor = _floor()
        print(json.dumps(floor.complete_floor_training() if floor else {"ok": False}, ensure_ascii=False))
        return 0
    if cmd == "meta":
        print(json.dumps({"ok": True, **program_meta()}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-training-chamber.py [json|complete-all|meta|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())