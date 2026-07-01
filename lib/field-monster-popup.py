#!/usr/bin/env pythong
"""Monster — native AmmoOS popups (zenity/yad/tkinter). Never raises."""
from __future__ import annotations

import fcntl
import hashlib
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Literal

HangChoice = Literal["wait", "quit", "dismiss"]

_INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
_STATE = Path(os.environ.get("NEXUS_STATE_DIR", _INSTALL / ".nexus-state"))
_HANG_LOCK_DIR = _STATE / "monster-hang-locks"


@contextmanager
def _hang_popup_lock(label: str) -> Iterator[bool]:
    """One native popup per label — skip duplicates that stack zenity windows."""
    _HANG_LOCK_DIR.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(label.encode("utf-8", errors="replace")).hexdigest()[:16]
    lock_path = _HANG_LOCK_DIR / f"{key}.lock"
    fh = lock_path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        fh.seek(0)
        fh.truncate()
        fh.write(f"{os.getpid()} {time.time():.0f} {label[:80]}\n")
        fh.flush()
        yield True
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        fh.close()


def _has_gui() -> bool:
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _zenity_hang(label: str, detail: str) -> HangChoice | None:
    if not shutil.which("zenity"):
        return None
    body = f"{detail}\n\nThe program may still be working.\n\n• Wait — keep running\n• End Task — force close"
    try:
        proc = subprocess.run(
            [
                "zenity",
                "--question",
                "--title=Monster — Program Not Responding",
                "--width=480",
                "--text",
                f"{label}\n\n{body}",
                "--ok-label=Wait",
                "--cancel-label=End Task",
                "--extra-button=Dismiss",
            ],
            capture_output=True,
            text=True,
            timeout=3600,
            env={**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":0")},
        )
        if proc.returncode == 0:
            return "wait"
        if proc.returncode == 1:
            return "quit"
        if "Dismiss" in (proc.stdout or ""):
            return "dismiss"
        return "quit"
    except (OSError, subprocess.TimeoutExpired):
        return None


def _yad_hang(label: str, detail: str) -> HangChoice | None:
    if not shutil.which("yad"):
        return None
    try:
        proc = subprocess.run(
            [
                "yad",
                "--title=Monster",
                "--text",
                f"{label}\n\n{detail}\n\nProgram not responding.",
                "--button=Wait:0",
                "--button=End Task:1",
                "--button=Dismiss:2",
                "--width=460",
            ],
            capture_output=True,
            text=True,
            timeout=3600,
        )
        if proc.returncode == 0:
            return "wait"
        if proc.returncode == 1:
            return "quit"
        return "dismiss"
    except (OSError, subprocess.TimeoutExpired):
        return None


def _tk_hang(label: str, detail: str) -> HangChoice | None:
    if not _has_gui():
        return None
    try:
        import tkinter as tk
        from tkinter import ttk

        choice: HangChoice = "wait"

        def set_choice(c: HangChoice) -> None:
            nonlocal choice
            choice = c
            root.destroy()

        root = tk.Tk()
        root.title("Monster — AmmoOS")
        root.geometry("440x220")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        frm = ttk.Frame(root, padding=16)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=label, font=("", 11, "bold")).pack(anchor="w")
        ttk.Label(frm, text=detail[:400], wraplength=400).pack(anchor="w", pady=(8, 12))
        ttk.Label(frm, text="Program not responding. Wait or end the task?").pack(anchor="w")
        btn_row = ttk.Frame(frm)
        btn_row.pack(pady=16)
        ttk.Button(btn_row, text="Wait", command=lambda: set_choice("wait")).pack(side="left", padx=6)
        ttk.Button(btn_row, text="End Task", command=lambda: set_choice("quit")).pack(side="left", padx=6)
        ttk.Button(btn_row, text="Dismiss", command=lambda: set_choice("dismiss")).pack(side="left", padx=6)
        root.protocol("WM_DELETE_WINDOW", lambda: set_choice("dismiss"))
        root.mainloop()
        return choice
    except Exception:
        return None


def hang_prompt(label: str, detail: str = "", *, prefer_native: bool = True) -> HangChoice:
    """Native hang dialog — zenity → yad → tkinter → default wait."""
    label = (label or "Program")[:120]
    detail = (detail or "No output for a while.")[:500]
    with _hang_popup_lock(label) as acquired:
        if not acquired:
            return "wait"
        if prefer_native and _has_gui():
            for fn in (_zenity_hang, _yad_hang, _tk_hang):
                try:
                    picked = fn(label, detail)
                    if picked:
                        return picked
                except Exception:
                    continue
    return "wait"


def confirm_kill(label: str, pid: int) -> bool:
    if not _has_gui():
        return True
    msg = f"End task?\n\n{label}\nPID {pid}\n\nMonster will force-close the process tree."
    if shutil.which("zenity"):
        try:
            proc = subprocess.run(
                ["zenity", "--question", "--title=Monster", "--text", msg, "--ok-label=End Task", "--cancel-label=Cancel"],
                check=False,
                timeout=120,
            )
            return proc.returncode == 0
        except Exception:
            pass
    return True


def main() -> int:
    import json

    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: hang <label> [detail]"}))
        return 1
    label = sys.argv[2] if sys.argv[1] == "hang" and len(sys.argv) > 2 else sys.argv[1]
    detail = sys.argv[3] if len(sys.argv) > 3 else ""
    choice = hang_prompt(label, detail)
    print(json.dumps({"ok": True, "choice": choice}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())