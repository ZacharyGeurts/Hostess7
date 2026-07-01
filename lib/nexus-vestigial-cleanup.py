#!/usr/bin/env pythong
"""NEXUS vestigial cleanup — remove our old start-menu entries and duplicates; never harm the OS."""
from __future__ import annotations

import json
import os
import pwd
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent if INSTALL.name == "nexus-shield" else INSTALL.parent)))
LEDGER = STATE / "nexus-vestigial-cleanup.jsonl"
PANEL = STATE / "nexus-vestigial-cleanup-panel.json"
SCHEMA = "nexus-vestigial-cleanup/v1"

# Old start-menu / launcher names superseded by nexus-field.desktop
VESTIGIAL_DESKTOPS = (
    "nexus-shield.desktop",
    "nexus-tristate-installer.desktop",
    "nexus-threat-panel.desktop",
    "nexus-panel.desktop",
    "nexus-shield-panel.desktop",
    "nexus-shield-tray.desktop",
    "nexus-genius.desktop",
    "queen-shield.desktop",
    "ammocode-stack.desktop",
    "amouranthrtx.desktop",
    "amouranthrtx-comp.desktop",
    "amouranthrtx-engine.desktop",
    "amouranthrtx-spv.desktop",
    "sg-code-open.desktop",
    "world-repack.desktop",
    "queen-browser.desktop",
    "ammoos-c2.desktop",
    "ammoos-field.desktop",
    "ammoos.desktop",
)

VESTIGIAL_DESKTOP_PREFIXES = (
    "ammocode",
    "amouranth",
    "ammoos",
    "sg-code",
    "world-repack",
)

# Duplicate autostart — keep nexus-panel-tray.desktop only
VESTIGIAL_AUTOSTART = (
    "nexus-shield-tray.desktop",
    "nexus-shield.desktop",
    "nexus-tristate-installer.desktop",
    "nexus-threat-panel.desktop",
    "nexus-queen-world.desktop",
)

def _never_harm_os() -> bool:
    return os.environ.get("NEXUS_NEVER_HARM_OS", os.environ.get("ZNETWORK_NEVER_HARM_OS", "1")) != "0"


# Our vestigial field panels only — never OS processes
LEGACY_PROCESS_PATTERNS = (
    r"/Latest/NEXUS-Shield/lib/threat-panel-http\.py",
    r"/Latest/NEXUS-Shield/lib/nexus-daemon",
    r"Latest/NEXUS-Shield.*threat-panel",
    r"field-antenna",
    r"field_antenna",
    r"field-antenna-catch",
    r"field-antenna-orchestrator",
    r"field-antenna-launcher",
    r"field-spectrum-demod.*catch",
)

# Duplicate state roots (migrate away, do not delete panels)
DUPLICATE_STATE_HINTS = (
    ".nexus-state",
    "Latest/NEXUS-Shield/.nexus-state",
)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _append_ledger(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")


def _home_dirs() -> list[Path]:
    homes: list[Path] = []
    try:
        homes.append(Path.home())
    except RuntimeError:
        pass
    for key in ("SUDO_USER", "USER"):
        user = os.environ.get(key, "").strip()
        if not user or user == "root":
            continue
        try:
            homes.append(Path(pwd.getpwnam(user).pw_dir))
        except KeyError:
            continue
    seen: set[str] = set()
    out: list[Path] = []
    for h in homes:
        s = str(h)
        if s not in seen:
            seen.add(s)
            out.append(h)
    return out


def _desktop_dirs() -> list[Path]:
    dirs: list[Path] = [Path("/usr/share/applications")]
    for home in _home_dirs():
        dirs.extend([
            home / ".local" / "share" / "applications",
            home / "Desktop",
            home / ".config" / "autostart",
        ])
    return [d for d in dirs if d.is_dir()]


def _remove_file(path: Path, *, kind: str, results: dict[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        path.unlink()
        results["removed"].append({"kind": kind, "path": str(path)})
        _append_ledger({"action": "remove", "kind": kind, "path": str(path)})
        return True
    except OSError as exc:
        results["errors"].append({"kind": kind, "path": str(path), "error": str(exc)})
        return False


def _is_vestigial_desktop_name(name: str) -> bool:
    if name == "nexus-field.desktop":
        return False
    if name in VESTIGIAL_DESKTOPS:
        return True
    stem = name.removesuffix(".desktop").lower()
    return any(stem.startswith(p) for p in VESTIGIAL_DESKTOP_PREFIXES)


def _clean_desktop_entries(results: dict[str, Any]) -> int:
    count = 0
    for base in _desktop_dirs():
        for name in VESTIGIAL_DESKTOPS:
            if _remove_file(base / name, kind="desktop", results=results):
                count += 1
        for path in base.glob("*.desktop"):
            if _is_vestigial_desktop_name(path.name) and _remove_file(path, kind="desktop_pattern", results=results):
                count += 1
        if base.name == "autostart":
            for name in VESTIGIAL_AUTOSTART:
                if name == "nexus-panel-tray.desktop":
                    continue
                if _remove_file(base / name, kind="autostart", results=results):
                    count += 1
    return count


def _read_cmdline(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\x00", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def _stop_legacy_processes(results: dict[str, Any]) -> int:
    if _never_harm_os() and os.environ.get("NEXUS_VESTIGIAL_STOP_PROCESSES", "0") != "1":
        results["skipped_process_stop"] = "never_harm_os"
        return 0
    count = 0
    try:
        pids = [int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit()]
    except OSError:
        return 0
    compiled = [re.compile(p) for p in LEGACY_PROCESS_PATTERNS]
    for pid in pids:
        if pid <= 1:
            continue
        cmd = _read_cmdline(pid)
        if not cmd:
            continue
        if not any(c.search(cmd) for c in compiled):
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            results["stopped"].append({"pid": pid, "cmd": cmd[:200]})
            _append_ledger({"action": "stop_process", "pid": pid, "cmd": cmd[:200]})
            count += 1
        except ProcessLookupError:
            pass
        except OSError as exc:
            results["errors"].append({"kind": "process", "pid": pid, "error": str(exc)})
    return count


def _prune_duplicate_tray_autostart(results: dict[str, Any]) -> int:
    """Keep one nexus-panel-tray.desktop — remove extras with stale Exec paths."""
    count = 0
    canonical = None
    for home in _home_dirs():
        tray = home / ".config" / "autostart" / "nexus-panel-tray.desktop"
        if not tray.is_file():
            continue
        text = tray.read_text(encoding="utf-8", errors="replace")
        if "Latest/NEXUS-Shield" in text or "nexus-shield.desktop" in text:
            if _remove_file(tray, kind="stale_tray_autostart", results=results):
                count += 1
            continue
        if canonical is None:
            canonical = str(tray)
        elif str(tray) != canonical:
            if _remove_file(tray, kind="duplicate_tray_autostart", results=results):
                count += 1
    return count


def _note_duplicate_locations(results: dict[str, Any]) -> int:
    notes = 0
    candidates = [
        SG / "Latest" / "NEXUS-Shield",
        INSTALL.parent / "Latest" / "NEXUS-Shield",
        Path("/usr/local/lib/nexus-shield-old"),
    ]
    for path in candidates:
        if path.is_dir():
            results["vestigial_dirs"].append(str(path))
            _append_ledger({"action": "note_vestigial_dir", "path": str(path)})
            notes += 1
    for hint in DUPLICATE_STATE_HINTS:
        p = SG / hint if not hint.startswith("/") else Path(hint)
        if p.is_dir() and p != STATE:
            results["duplicate_state"].append(str(p))
            notes += 1
    return notes


def _invoke_znetwork_handler_retire(results: dict[str, Any]) -> bool:
    retire_py = INSTALL / "lib" / "znetwork-handler-retire.py"
    if not retire_py.is_file():
        retire_py = Path(__file__).resolve().parent / "znetwork-handler-retire.py"
    if not retire_py.is_file():
        return False
    try:
        proc = subprocess.run(
            [sys.executable, str(retire_py), "retire"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        ok = proc.returncode == 0
        results["znetwork_retire"] = {"ok": ok, "stdout": (proc.stdout or "")[:400]}
        _append_ledger({"action": "znetwork_handler_retire", "ok": ok})
        return ok
    except (OSError, subprocess.TimeoutExpired) as exc:
        results["errors"].append({"kind": "znetwork_retire", "error": str(exc)})
        return False


def cleanup(*, retire_handlers: bool = False) -> dict[str, Any]:
    """Run vestigial cleanup — files only by default; never harm the host OS."""
    results: dict[str, Any] = {
        "schema": SCHEMA,
        "updated": _now(),
        "ok": True,
        "never_harm_os": _never_harm_os(),
        "motto": "Our vestigial menus and duplicates cleaned — OS networking never killed or harmed.",
        "removed": [],
        "stopped": [],
        "vestigial_dirs": [],
        "duplicate_state": [],
        "errors": [],
        "counts": {},
    }
    results["counts"]["desktops"] = _clean_desktop_entries(results)
    results["counts"]["legacy_processes"] = _stop_legacy_processes(results)
    results["counts"]["tray_autostart"] = _prune_duplicate_tray_autostart(results)
    results["counts"]["vestigial_notes"] = _note_duplicate_locations(results)
    if retire_handlers:
        _invoke_znetwork_handler_retire(results)
    results["counts"]["total_removed"] = len(results["removed"])
    results["counts"]["total_stopped"] = len(results["stopped"])
    if results["errors"]:
        results["ok"] = len(results["errors"]) < 3
    try:
        PANEL.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return results


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "run").strip().lower()
    if cmd in ("run", "cleanup", "json"):
        print(json.dumps(cleanup(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "desktops":
        r: dict[str, Any] = {"removed": [], "errors": [], "stopped": [], "vestigial_dirs": [], "duplicate_state": []}
        n = _clean_desktop_entries(r)
        print(json.dumps({"removed": r["removed"], "count": n}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["run", "cleanup", "json", "desktops"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())