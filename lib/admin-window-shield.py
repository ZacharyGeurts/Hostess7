#!/usr/bin/env pythong
"""Admin window shield — block keyboard/OS hooks and screen capture near operator admin surfaces."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from proc_threat_match import proc_hits_any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_JSON = STATE / "admin-window-shield.json"
ALERTS = STATE / "admin-window-shield-alerts.jsonl"

BLOCKED_OS_HOOK_PROCS = frozenset({
    "wmctrl", "xdotool", "ydotool", "dotool", "xte", "xmacro", "xvkbd",
})
BLOCKED_KEYBOARD_HOOK_PROCS = frozenset({
    "keylogger", "logkeys", "lkl", "kidlogger", "xinput", "showkey", "evtest",
    "intercept", "xbindkeys", "xbindkey", "xhotkey", "autokey", "skey",
    "keysniffer", "logkey", "pykeylogger", "lantern", "berkeley-express",
})
BLOCKED_CAPTURE_PROCS = frozenset({
    "obs", "obs-studio", "obs-ffmpeg-mux", "wf-recorder", "gpu-screen-recorder",
    "kooha", "simplescreenrecorder", "recordmydesktop", "grim", "slurp", "wayshot",
    "spectacle", "peek", "scrot", "import", "maim", "flameshot", "gnome-screenshot",
    "ksnip", "deepin-screenshot", "screengrab",
})

HOOK_CMD_MARKERS = (
    "keyboard", "keylog", "key log", "x11grab", "gdigrab", "avfoundation",
    "record", "screenshot", "screen capture", "display capture",
)


def _enabled() -> bool:
    return os.environ.get("NEXUS_ADMIN_WINDOW_SHIELD", "1") not in ("0", "false", "no", "off")


def _keyboard_block() -> bool:
    return os.environ.get("NEXUS_NO_KEYBOARD_HOOK", "1") not in ("0", "false", "no", "off")


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


def _proc_line(line: str) -> dict[str, str] | None:
    line = line.strip()
    if not line:
        return None
    parts = line.split(None, 1)
    if not parts:
        return None
    pid = parts[0]
    cmd = parts[1] if len(parts) > 1 else ""
    comm = cmd.split()[0].rsplit("/", 1)[-1].lower() if cmd else ""
    return {"pid": pid, "comm": comm, "cmd": cmd}


def _classify(proc: dict[str, str]) -> dict[str, Any] | None:
    comm = proc.get("comm", "")
    cmd = proc.get("cmd") or ""
    blob = f"{comm} {cmd}".lower()
    os_hit = proc_hits_any(BLOCKED_OS_HOOK_PROCS, comm, cmd)
    if os_hit:
        return {"kind": "os_hook", "reason": f"os_window_hook:{os_hit}", "iff": "HOSTILE"}
    if _keyboard_block():
        kb_hit = proc_hits_any(BLOCKED_KEYBOARD_HOOK_PROCS, comm, cmd)
        if kb_hit:
            return {"kind": "keyboard_hook", "reason": f"keyboard_hook:{kb_hit}", "iff": "HOSTILE"}
    if any(h in blob for h in BLOCKED_CAPTURE_PROCS):
        if "queen-browser" in blob or "fieldfox" in blob:
            return None
        return {"kind": "screen_capture", "reason": "screen_capture", "iff": "HOSTILE"}
    if any(m in cmd for m in HOOK_CMD_MARKERS) and any(
        x in cmd for x in ("ffmpeg", "ffplay", "gst-launch", "python", "python3", "pythong")
    ):
        return {"kind": "capture_cmdline", "reason": "capture_cmdline", "iff": "HOSTILE"}
    return None


def scan_processes() -> list[dict[str, Any]]:
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,args", "--no-headers"],
            capture_output=True,
            text=True,
            timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    hits: list[dict[str, Any]] = []
    for line in (proc.stdout or "").splitlines():
        parsed = _proc_line(line)
        if not parsed:
            continue
        verdict = _classify(parsed)
        if not verdict:
            continue
        hits.append({
            **parsed,
            **verdict,
            "ts": _now(),
            "enforcement": "INTERDICT — admin window shield",
        })
    return hits


def _log_alert(hit: dict[str, Any]) -> None:
    ALERTS.parent.mkdir(parents=True, exist_ok=True)
    with ALERTS.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(hit, ensure_ascii=False) + "\n")


def enforce(*, kill: bool | None = None) -> dict[str, Any]:
    if not _enabled():
        return {"schema": "admin-window-shield/v1", "enabled": False, "hits": []}
    if kill is None:
        kill = os.environ.get("NEXUS_ADMIN_HOOK_KILL", "1") == "1" and os.geteuid() == 0
    hits = scan_processes()
    acted = []
    for hit in hits:
        _log_alert(hit)
        if kill:
            try:
                os.kill(int(hit["pid"]), 9)
                hit["killed"] = True
                acted.append(hit)
            except (OSError, ValueError):
                hit["killed"] = False
        else:
            hit["killed"] = False
            acted.append(hit)
    doc = {
        "schema": "admin-window-shield/v1",
        "updated": _now(),
        "enabled": True,
        "keyboard_hooks_blocked": _keyboard_block(),
        "no_os_hook": os.environ.get("NEXUS_NO_WM_HOOK", "1") == "1",
        "no_screen_capture": os.environ.get("NEXUS_NO_SCREEN_CAPTURE", "1") == "1",
        "hit_count": len(hits),
        "hits": hits[:32],
        "blocked_keyboard_hook_procs": sorted(BLOCKED_KEYBOARD_HOOK_PROCS),
        "blocked_os_hook_procs": sorted(BLOCKED_OS_HOOK_PROCS),
        "blocked_capture_procs": sorted(BLOCKED_CAPTURE_PROCS),
        "front_hook": os.environ.get("NEXUS_FRONT_HOOK", "1") == "1",
        "pass_through": os.environ.get("NEXUS_HOOK_PASS_THROUGH", "0") == "1",
        "policy": "Front hook on board — never pass keyboard/display hooks downstream",
    }
    _save_json(PANEL_JSON, doc)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL_JSON.is_file():
        doc = _load_json(PANEL_JSON, {})
        if doc.get("schema") == "admin-window-shield/v1":
            return doc
    return enforce(kill=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "enforce":
        print(json.dumps(enforce(), ensure_ascii=False))
        return 0
    if cmd == "scan":
        print(json.dumps({"hits": scan_processes()}, ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: admin-window-shield.py [json|scan|enforce]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())