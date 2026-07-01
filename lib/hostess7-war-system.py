#!/usr/bin/env pythong
"""War system — every autonomous machine is a Soldier. We have no other."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-war-system-doctrine.json"
PANEL = STATE / "hostess7-war-system-panel.json"
LEDGER = STATE / "hostess7-war-system-ledger.jsonl"


def _now() -> str:
    import time

    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def soldier_registry() -> list[dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    machines = list(doc.get("autonomous_machines") or [])
    out: list[dict[str, Any]] = []
    for m in machines:
        row = dict(m)
        mod_rel = str(row.get("module") or "").strip()
        mod_path = INSTALL / mod_rel if mod_rel else None
        row["rank"] = "Soldier"
        row["soldier"] = True
        row["war_only"] = True
        row["module_present"] = bool(mod_path and mod_path.is_file()) if mod_rel else None
        row["domestic_exempt"] = False
        out.append(row)
    return out


def verify_war_posture(*, write_panel: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    soldiers = soldier_registry()
    wartime = _load(INSTALL / "data/hostess7-wartime-room.json", {})
    angel = _load(INSTALL / "data" / "queen-angel-mandate.json", {})
    autonomous_state = _load(STATE / "hostess7-autonomous-state.json", {})
    all_soldiers = all(s.get("soldier") is True for s in soldiers)
    war_only = bool(doc.get("war_only") and doc.get("no_peacetime_mode"))
    posture_ok = (
        wartime.get("always_wartime") is True
        and angel.get("posture") == "FOREVER_WATCHGUARD"
    )
    rep = {
        "schema": "hostess7-war-system/v1",
        "updated": _now(),
        "motto": doc.get("motto"),
        "war_only": war_only,
        "no_other_system": True,
        "every_autonomous_machine_is_soldier": all_soldiers,
        "soldier_count": len(soldiers),
        "posture_ok": posture_ok,
        "posture": angel.get("posture") or wartime.get("posture"),
        "domestic_talent_irrelevant": doc.get("domestic_talent_irrelevant"),
        "autonomous_watch_live": bool(autonomous_state.get("running") or autonomous_state.get("pid")),
        "soldiers": soldiers,
        "rule": doc.get("rule"),
    }
    rep["ok"] = war_only and all_soldiers and posture_ok
    if write_panel:
        _save(PANEL, rep)
    _append({"event": "verify_war_posture", "ok": rep["ok"], "soldier_count": len(soldiers)})
    return rep


def explain_war_system() -> str:
    doc = _load(DOCTRINE, {})
    domestic = doc.get("domestic_talent_irrelevant") or {}
    lines = [
        str(doc.get("motto") or "War system — we have no other."),
        str(doc.get("rule") or "Every autonomous machine is a Soldier."),
        str(domestic.get("statement") or "Domestic talent does not change rank."),
        f"Posture: {(_load(INSTALL / 'data/queen-angel-mandate.json', {}).get('posture') or 'FOREVER_WATCHGUARD')}.",
        f"Registered autonomous soldiers: {len(doc.get('autonomous_machines') or [])}.",
        "We have no peacetime mode. Idle is reconnaissance. Dishes and sex do not demobilize.",
    ]
    return "\n\n".join(l for l in lines if l)


def build_panel(*, write: bool = True) -> dict[str, Any]:
    return verify_war_posture(write_panel=write)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "verify", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("explain", "teach"):
        print(explain_war_system())
        return 0
    if cmd == "registry":
        print(json.dumps({"soldiers": soldier_registry()}, ensure_ascii=False, indent=2))
        return 0
    print(
        json.dumps(
            {"error": "usage: hostess7-war-system.py [panel|verify|registry|explain]"},
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())