#!/usr/bin/env pythong
"""Underlay surface — rise field OS in Queen browser, drop beneath host desktop."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SURFACE_STATE = STATE / "field-underlay-surface.json"
SURFACE_LOG = STATE / "field-underlay-surface.jsonl"
PANEL_PORT = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
WORLD_PORT = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save(doc: dict[str, Any]) -> None:
    SURFACE_STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = SURFACE_STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(SURFACE_STATE)


def _log(row: dict[str, Any]) -> None:
    try:
        with SURFACE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _urls() -> dict[str, str]:
    return {
        "field_desktop": f"http://127.0.0.1:{PANEL_PORT}/field",
        "kilroy_home": f"http://127.0.0.1:{WORLD_PORT}/world/kilroy-home.html",
        "command": f"http://127.0.0.1:{PANEL_PORT}/command",
        "underlay_f9": f"http://127.0.0.1:{PANEL_PORT}/underlay-f9",
        "queen_browser": f"http://127.0.0.1:{WORLD_PORT}/world/browser.html",
    }


def posture() -> dict[str, Any]:
    cur = _load(SURFACE_STATE, {"schema": "field-underlay-surface/v1", "mode": "field_surface"})
    return {
        "schema": "field-underlay-surface/v1",
        "ts": _now(),
        "ok": True,
        "mode": cur.get("mode", "field_surface"),
        "under_host": cur.get("mode") == "under_host",
        "field_surface": cur.get("mode", "field_surface") != "under_host",
        "last_transition": cur.get("last_transition"),
        "urls": _urls(),
        "actions": {"rise": "POST /api/field-underlay-surface/rise", "drop": "POST /api/field-underlay-surface/drop"},
        "posture": "Drop under host desktop or rise field OS inside Queen browser",
    }


def _minimize_queen_best_effort() -> dict[str, Any]:
    """Best-effort — field stays running beneath; no wm hook required."""
    hints: list[str] = []
    for cmd, args in (
        (["wmctrl", "-x", "-r", "QueenBrowser", "-b", "add,hidden"], "wmctrl"),
        (["xdotool", "search", "--class", "QueenBrowser", "windowminimize"], "xdotool"),
    ):
        try:
            proc = subprocess.run(cmd if isinstance(cmd, list) else args, capture_output=True, text=True, timeout=4)
            if proc.returncode == 0:
                return {"ok": True, "via": args if isinstance(args, str) else cmd[0]}
        except (OSError, subprocess.TimeoutExpired):
            hints.append(str(args))
    return {"ok": False, "soft_drop": True, "hint": "Use host desktop — field panel keeps running on loopback"}


def drop(*, beneath: bool = True) -> dict[str, Any]:
    """Drop field underlay beneath incumbent host desktop."""
    minimize = _minimize_queen_best_effort() if beneath else {"ok": True, "skipped": True}
    doc = {
        "schema": "field-underlay-surface/v1",
        "mode": "under_host",
        "dropped_at": _now(),
        "last_transition": "drop",
        "minimize": minimize,
        "panel_port": PANEL_PORT,
        "world_port": WORLD_PORT,
    }
    _save(doc)
    _log({"ts": _now(), "event": "drop", "minimize": minimize})
    return {
        "ok": True,
        "dropped": True,
        "mode": "under_host",
        "minimize": minimize,
        "message": "Field underlay beneath host desktop — panel and Queen world keep running",
        "rise_hint": "F9 or POST /api/field-underlay-surface/rise",
    }


def rise(*, open_browser: bool = True) -> dict[str, Any]:
    """Rise field OS surface inside Queen browser."""
    doc = {
        "schema": "field-underlay-surface/v1",
        "mode": "field_surface",
        "rose_at": _now(),
        "last_transition": "rise",
        "panel_port": PANEL_PORT,
        "world_port": WORLD_PORT,
    }
    _save(doc)
    _log({"ts": _now(), "event": "rise"})

    browser: dict[str, Any] = {"ok": False, "skipped": not open_browser}
    if open_browser:
        opener = INSTALL / "lib" / "field-queen-browser-open.py"
        if opener.is_file():
            env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
            env.setdefault("QUEEN_BROWSER_START", _urls()["kilroy_home"])
            env.setdefault("QUEEN_BROWSER_HOME", _urls()["kilroy_home"])
            try:
                proc = subprocess.run(
                    [sys.executable, str(opener), "f9"],
                    capture_output=True,
                    text=True,
                    timeout=45,
                    env=env,
                )
                browser = json.loads(proc.stdout or "{}") if proc.stdout.strip() else {"ok": proc.returncode == 0}
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
                browser = {"ok": False, "error": str(exc)}

    return {
        "ok": True,
        "rose": True,
        "mode": "field_surface",
        "browser": browser,
        "urls": _urls(),
        "message": "Field OS risen inside Queen browser — host desktop underneath",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "drop":
        print(json.dumps(drop(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "rise":
        print(json.dumps(rise(), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-underlay-surface.py [json|drop|rise]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())