#!/usr/bin/env pythong
"""F9 underlay hotkey — boot KILROY field stack; Queen sovereign browser."""
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

EV_KEY = 0x01
KEY_F9 = 67  # F1=59 … F12=70
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
F9_PY = INSTALL / "lib" / "field-queen-browser-open.py"
DEBOUNCE_SEC = 1.2
LOG = STATE / "f9-hotkey.log"
SOVEREIGN_MARKER = STATE / "f9-sovereign-hook.json"


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "DISPLAY": os.environ.get("DISPLAY", ":0"),
    }


def _log(msg: str) -> None:
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")
    except OSError:
        pass


def _stamp_sovereign_hook() -> None:
    """F9 hook overrides host WM shortcuts — we own the keyboard."""
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        doc = {
            "schema": "f9-sovereign-hook/v1",
            "active": True,
            "owner": "kilroy_f9_hook",
            "override": "all_host_shortcuts",
            "policy": "F9 built-in overrides everyone — we got the hook",
            "module": "lib/field-underlay-hotkey.py",
            "stack": "lib/field-queen-browser-open.py f9",
            "boot_order": ["kilroy", "ammoos"],
            "kilroy_includes": ["nexus_c2", "network_lane", "defense_offense"],
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        SOVEREIGN_MARKER.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def _engage_keyboard_sovereign() -> None:
    kb = INSTALL / "lib" / "field-keyboard-sovereign.py"
    if not kb.is_file():
        return
    env = {**_env(), "NEXUS_KEYBOARD_SOVEREIGN": "1", "F9_SOVEREIGN_HOOK": "1"}
    subprocess.run(
        [sys.executable, str(kb), "engage"],
        env=env,
        timeout=10,
        check=False,
    )


def _open_f9() -> None:
    _log("F9 pressed — sovereign hook overrides host → KILROY PC core (NEXUS C2 inside) → AmmoOS")
    _stamp_sovereign_hook()
    _engage_keyboard_sovereign()
    if F9_PY.is_file():
        subprocess.run(
            [sys.executable, str(F9_PY), "f9"],
            env=_env(),
            timeout=120,
            check=False,
        )
        return
    switch = INSTALL / "lib" / "field-underlay-switch.py"
    if switch.is_file():
        subprocess.run([sys.executable, str(switch), "hotkey"], env=_env(), timeout=30, check=False)
    opener = INSTALL / "lib" / "queen-panel-open.py"
    if opener.is_file():
        subprocess.run(
            [sys.executable, str(opener), "nexus", "tristate-installer"],
            env=_env(),
            timeout=25,
            check=False,
        )


def _keyboard_fds() -> dict[int, str]:
    fds: dict[int, str] = {}
    for path in sorted(glob.glob("/dev/input/event*")):
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
            fds[fd] = path
        except OSError:
            continue
    return fds


def listen_loop() -> None:
    last = 0.0
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
            if ev_type == EV_KEY and code == KEY_F9 and value == 1:
                now = time.monotonic()
                if now - last < DEBOUNCE_SEC:
                    continue
                last = now
                _open_f9()


def _x11_listen_loop() -> None:
    from Xlib import X, display
    from Xlib import XK

    disp = display.Display()
    root = disp.screen().root
    keycode = disp.keysym_to_keycode(XK.XK_F9)
    if not keycode:
        raise RuntimeError("F9 keycode unavailable")

    modifiers = [0, X.LockMask, X.Mod2Mask, X.Mod3Mask, X.Mod4Mask, X.Mod5Mask]
    for mod in modifiers:
        root.grab_key(keycode, mod, True, X.GrabModeAsync, X.GrabModeAsync)
        for mod2 in modifiers:
            root.grab_key(keycode, mod | mod2, True, X.GrabModeAsync, X.GrabModeAsync)
    disp.sync()
    _log(f"X11 F9 grab active display={os.environ.get('DISPLAY', ':0')} keycode={keycode}")

    last = 0.0
    while True:
        ev = disp.next_event()
        if ev.type != X.KeyPress or ev.detail != keycode:
            continue
        now = time.monotonic()
        if now - last < DEBOUNCE_SEC:
            continue
        last = now
        _open_f9()


def run_listener() -> None:
    display = os.environ.get("DISPLAY", "").strip()
    if display:
        try:
            _x11_listen_loop()
            return
        except Exception as exc:
            _log(f"X11 listener failed: {exc} — falling back to evdev")
    fds = _keyboard_fds()
    if fds:
        _log(f"evdev listener on {list(fds.values())}")
        listen_loop()
        return
    _log("no input backend — retry in 5s")
    while True:
        time.sleep(5)
        if os.environ.get("DISPLAY", "").strip():
            try:
                _x11_listen_loop()
                return
            except Exception:
                pass
        if _keyboard_fds():
            listen_loop()
            return


def install_autostart() -> int:
    """Write ~/.config/autostart desktop entry for F9 listener."""
    home = Path(os.environ.get("HOME") or Path.home())
    autostart = home / ".config" / "autostart"
    autostart.mkdir(parents=True, exist_ok=True)
    py = sys.executable
    script = INSTALL / "lib" / "field-underlay-hotkey.py"
    display = os.environ.get("DISPLAY", ":0")
    desktop = autostart / "nexus-underlay-hotkey.desktop"
    desktop.write_text(
        f"""[Desktop Entry]
Type=Application
Name=NEXUS Underlay Hotkey (F9)
Comment=F9 — AmmoOS: KILROY field stack + Queen Browser + ZNetwork
Exec=env DISPLAY={display} NEXUS_INSTALL_ROOT={INSTALL} NEXUS_STATE_DIR={STATE} {py} {script}
Hidden=false
NoDisplay=true
X-GNOME-Autostart-enabled=true
""",
        encoding="utf-8",
    )
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "once":
        _open_f9()
        return 0
    if cmd in ("install", "install-autostart"):
        return install_autostart()
    if os.environ.get("NEXUS_UNDERLAY_HOTKEY") == "0":
        return 0
    try:
        run_listener()
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())