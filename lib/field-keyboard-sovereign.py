#!/usr/bin/env pythong
"""C2 keyboard sovereignty — inhibit host WM shortcuts while NEXUS C2 is active; restore on release."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
STATE_FILE = STATE / "keyboard-sovereign.json"
BACKUP_FILE = STATE / "keyboard-sovereign-backup.json"

# Host desktop shortcuts that bleed through fullscreen AmmoOS C2 — cleared on engage, restored on release.
GSETTINGS_INHIBIT: list[tuple[str, str, str]] = [
    ("org.gnome.mutter", "overlay-key", ""),
    ("org.gnome.desktop.wm.keybindings", "switch-applications", "[]"),
    ("org.gnome.desktop.wm.keybindings", "switch-applications-backward", "[]"),
    ("org.gnome.desktop.wm.keybindings", "switch-windows", "[]"),
    ("org.gnome.desktop.wm.keybindings", "switch-windows-backward", "[]"),
    ("org.gnome.shell.keybindings", "toggle-application-view", "[]"),
    ("org.gnome.shell.keybindings", "show-desktop", "[]"),
    ("org.gnome.settings-daemon.plugins.media-keys", "screensaver", "[]"),
]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _enabled() -> bool:
    return os.environ.get("NEXUS_KEYBOARD_SOVEREIGN", "1") not in ("0", "false", "no", "off")


def _gsettings_get(schema: str, key: str) -> str | None:
    try:
        proc = subprocess.run(
            ["gsettings", "get", schema, key],
            capture_output=True,
            text=True,
            timeout=4,
        )
        if proc.returncode == 0:
            return (proc.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


def _gsettings_set(schema: str, key: str, value: str) -> bool:
    try:
        proc = subprocess.run(
            ["gsettings", "set", schema, key, value],
            capture_output=True,
            text=True,
            timeout=4,
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def status() -> dict[str, Any]:
    doc = _load(STATE_FILE, {})
    backup = _load(BACKUP_FILE, {})
    return {
        "schema": "field-keyboard-sovereign/v1",
        "ok": True,
        "enabled": _enabled(),
        "active": bool(doc.get("active")),
        "engaged_at": doc.get("engaged_at"),
        "released_at": doc.get("released_at"),
        "display": os.environ.get("DISPLAY", ""),
        "backup_keys": len(backup.get("keys") or []),
        "policy": "engage_inhibits_host_wm_shortcuts_release_restores",
    }


def engage() -> dict[str, Any]:
    if not _enabled():
        return {**status(), "ok": True, "skipped": "disabled"}
    doc = _load(STATE_FILE, {})
    if doc.get("active"):
        return {**status(), "ok": True, "already": True}

    backup_keys: list[dict[str, str]] = []
    applied: list[str] = []
    for schema, key, inhibit_val in GSETTINGS_INHIBIT:
        current = _gsettings_get(schema, key)
        if current is None:
            continue
        backup_keys.append({"schema": schema, "key": key, "value": current})
        if _gsettings_set(schema, key, inhibit_val):
            applied.append(f"{schema}/{key}")

    _save_atomic(
        BACKUP_FILE,
        {"schema": "keyboard-sovereign-backup/v1", "keys": backup_keys, "saved_at": _now()},
    )
    _save_atomic(
        STATE_FILE,
        {
            "schema": "field-keyboard-sovereign/v1",
            "active": True,
            "engaged_at": _now(),
            "released_at": None,
            "applied": applied,
            "owner": "kilroy-f9-hook" if os.environ.get("F9_SOVEREIGN_HOOK") == "1" else "nexus-c2",
        },
    )
    out = status()
    out["engaged"] = True
    out["applied"] = applied
    return out


def release(*, reason: str = "operator") -> dict[str, Any]:
    doc = _load(STATE_FILE, {})
    backup = _load(BACKUP_FILE, {})
    restored: list[str] = []
    for entry in backup.get("keys") or []:
        schema = str(entry.get("schema") or "")
        key = str(entry.get("key") or "")
        value = str(entry.get("value") or "")
        if schema and key and value and _gsettings_set(schema, key, value):
            restored.append(f"{schema}/{key}")

    _save_atomic(
        STATE_FILE,
        {
            "schema": "field-keyboard-sovereign/v1",
            "active": False,
            "engaged_at": doc.get("engaged_at"),
            "released_at": _now(),
            "release_reason": reason,
            "restored": restored,
        },
    )
    if BACKUP_FILE.is_file():
        try:
            BACKUP_FILE.unlink()
        except OSError:
            pass
    out = status()
    out["released"] = True
    out["restored"] = restored
    out["reason"] = reason
    return out


def main() -> int:
    cmd = (os.sys.argv[1] if len(os.sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(status(), ensure_ascii=False))
    elif cmd == "engage":
        print(json.dumps(engage(), ensure_ascii=False))
    elif cmd == "release":
        reason = os.sys.argv[2] if len(os.sys.argv) > 2 else "cli"
        print(json.dumps(release(reason=reason), ensure_ascii=False))
    else:
        print(json.dumps({"ok": False, "error": "usage: field-keyboard-sovereign.py [json|engage|release]"}, ensure_ascii=False))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())