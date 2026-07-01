#!/usr/bin/env pythong
"""AmmoOS OS keybindings — kernel evdev listener tied to Ironclad desktop dispatch."""
from __future__ import annotations

import glob
import json
import os
import select
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-os-keybindings-doctrine.json"
PANEL = STATE / "field-os-keybindings-panel.json"
LEDGER = STATE / "field-os-keybindings-ledger.jsonl"
KERNEL_QUEUE = STATE / "field-os-keybindings-kernel-queue.json"

EV_KEY = 0x01
KEY_CODES: dict[str, int] = {
    "Escape": 1, "1": 2, "2": 3, "3": 4, "4": 5, "5": 6, "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
    "Tab": 15, "q": 16, "w": 17, "e": 18, "r": 19, "t": 20, "y": 21, "u": 22, "i": 23, "o": 24, "p": 25,
    "a": 30, "s": 31, "d": 32, "f": 33, "g": 34, "h": 35, "j": 36, "k": 37, "l": 38,
    "z": 44, "x": 45, "c": 46, "v": 47, "b": 48, "n": 49, "m": 50,
    "Control": 29, "Alt": 56, "Shift": 42, "Meta": 125, "Delete": 111, "F4": 62,
    "F1": 59, "F2": 60, "F3": 61, "F5": 63, "F6": 64, "F7": 65, "F8": 66, "F9": 67,
    "F10": 68, "F11": 87, "F12": 88,
}


def _now() -> str:
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
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _log(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def doctrine_doc() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    if doc.get("bindings"):
        return doc
    return {"schema": "field-os-keybindings/v1", "bindings": [], "launch_targets": {}}


def panel_doc() -> dict[str, Any]:
    doc = doctrine_doc()
    return {
        "schema": "field-os-keybindings-panel/v1",
        "ok": True,
        "updated": _now(),
        "bindings": doc.get("bindings") or [],
        "launch_targets": doc.get("launch_targets") or {},
        "kernel_queue": _load(KERNEL_QUEUE, {}),
        "motto": doc.get("motto"),
    }


def _engage_keyboard_sovereign() -> None:
    kb = INSTALL / "lib" / "field-keyboard-sovereign.py"
    if kb.is_file():
        subprocess.run([sys.executable, str(kb), "engage"], check=False, timeout=8)


def _dispatch_kernel_action(binding: dict[str, Any]) -> None:
    action = str(binding.get("action") or "")
    bid = str(binding.get("id") or "")
    _log({"op": "kernel_dispatch", "id": bid, "action": action})
    _save(
        KERNEL_QUEUE,
        {
            "schema": "field-os-keybindings-kernel-queue/v1",
            "updated": _now(),
            "pending": {"id": bid, "action": action, "target": binding.get("target"), "binding": binding},
        },
    )
    if action == "kilroy_browser":
        f9 = INSTALL / "lib" / "field-queen-browser-open.py"
        if f9.is_file():
            subprocess.run([sys.executable, str(f9), "f9"], check=False, timeout=90)
        return
    if action == "launch":
        target = str(binding.get("target") or "")
        targets = doctrine_doc().get("launch_targets") or {}
        app = targets.get(target) if target else None
        if app and app.get("exec"):
            exec_url = str(app["exec"])
            if exec_url.startswith("/"):
                opener = INSTALL / "lib" / "queen-panel-open.py"
                if opener.is_file():
                    subprocess.run([sys.executable, str(opener), "url", exec_url], check=False, timeout=25)
            else:
                browser = INSTALL / "lib" / "field-queen-browser-open.py"
                if browser.is_file():
                    subprocess.run([sys.executable, str(browser), "open", exec_url], check=False, timeout=60)
        return
    if action == "show_desktop":
        return
    if action == "monster":
        return


def _binding_codes(binding: dict[str, Any]) -> tuple[frozenset[int], int | None]:
    keys = [str(k) for k in (binding.get("keys") or [])]
    mods: set[int] = set()
    main: int | None = None
    for key in keys:
        code = KEY_CODES.get(key) or KEY_CODES.get(key.lower()) or KEY_CODES.get(key.capitalize())
        if code is None:
            continue
        if key in ("Control", "Alt", "Shift", "Meta"):
            mods.add(code)
        else:
            main = code
    return frozenset(mods), main


def _keyboard_fds() -> dict[int, str]:
    fds: dict[int, str] = {}
    for path in sorted(glob.glob("/dev/input/event*")):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            fds[fd] = path
        except OSError:
            continue
    return fds


def kernel_listen() -> None:
    if os.environ.get("AMMOOS_KERNEL_KEYBINDINGS", "1") in ("0", "false", "off"):
        return
    _engage_keyboard_sovereign()
    kernel_bindings = [b for b in (doctrine_doc().get("bindings") or []) if b.get("kernel")]
    parsed = [(b, *_binding_codes(b)) for b in kernel_bindings]
    pressed_mods: set[int] = set()
    last_fire = 0.0
    while True:
        fds = _keyboard_fds()
        if not fds:
            time.sleep(5)
            continue
        try:
            readable, _, _ = select.select(list(fds.keys()), [], [], 2.0)
        except (ValueError, OSError):
            time.sleep(2)
            continue
        for fd in readable:
            try:
                data = os.read(fd, 24)
            except OSError:
                continue
            if len(data) < 24:
                continue
            _sec, _usec, ev_type, code, value = struct.unpack("llHHI", data)
            if ev_type != EV_KEY:
                continue
            if code in (29, 42, 56, 125, 126):
                if value == 1:
                    pressed_mods.add(code)
                elif value == 0:
                    pressed_mods.discard(code)
                continue
            if value != 1:
                continue
            now = time.monotonic()
            if now - last_fire < 0.35:
                continue
            for binding, mods, main in parsed:
                if main is None or code != main:
                    continue
                if mods and not mods.issubset(pressed_mods):
                    continue
                last_fire = now
                _dispatch_kernel_action(binding)
                break


def handle_api(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "panel").lower().replace("-", "_")
    if action in ("panel", "json", "status"):
        return panel_doc()
    if action == "doctrine":
        return {"ok": True, **doctrine_doc()}
    if action == "ack_kernel":
        try:
            KERNEL_QUEUE.unlink(missing_ok=True)
        except OSError:
            pass
        return {"ok": True}
    if action == "dispatch":
        bid = str(body.get("id") or body.get("binding_id") or "")
        for row in doctrine_doc().get("bindings") or []:
            if str(row.get("id")) == bid:
                _log({"op": "desktop_dispatch", "id": bid, "action": row.get("action")})
                return {"ok": True, "binding": row}
        return {"ok": False, "error": "binding_not_found"}
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel_doc(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("doctrine", "bindings"):
        print(json.dumps(doctrine_doc(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(handle_api(body), ensure_ascii=False))
        return 0
    if cmd in ("listen", "kernel", "daemon"):
        try:
            kernel_listen()
        except KeyboardInterrupt:
            return 0
        return 0
    print(json.dumps({"error": "usage: panel|doctrine|dispatch|listen"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())