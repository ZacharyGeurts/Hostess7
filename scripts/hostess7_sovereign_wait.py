#!/usr/bin/env pythong
"""Hostess 7 waits — sovereign linear time only; no wall timers or arbitrary sleep."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", ROOT.parent if ROOT.parent.name == "NewLatest" else ROOT.parent / "NewLatest"))


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ImportError(f"missing {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mono_us() -> int:
    presume_py = INSTALL / "lib" / "hostess7-presume.py"
    if presume_py.is_file():
        return int(_load_module(presume_py, "hostess7_presume_mono").mono_us())
    clock = INSTALL / "lib" / "sovereign-clock.py"
    if clock.is_file():
        return int(_load_module(clock, "sovereign_clock_wait").mono_ns() // 1000)
    st = INSTALL / "lib" / "sovereign-time.py"
    if st.is_file():
        return int(_load_module(st, "sovereign_time_wait").linear_time_ns() // 1000)
    raise RuntimeError("sovereign clock unavailable — set NEXUS_INSTALL_ROOT")


def _ping(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return 200 <= getattr(resp, "status", 200) < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def wait_until(predicate: Callable[[], bool], *, wait_us: int = 1_200_000, label: str = "hostess7_wait") -> bool:
    """Cooperative wait on sovereign mono until predicate true or linear budget spent."""
    if predicate():
        return True
    presume_py = INSTALL / "lib" / "hostess7-presume.py"
    if presume_py.is_file():
        presume = _load_module(presume_py, "hostess7_presume_wait")
        done = {"ok": False}

        def _alt() -> None:
            if predicate():
                done["ok"] = True

        presume.presume(max(0, int(wait_us)), label=label, alternate_fn=_alt)
        return done["ok"] or predicate()

    deadline = _mono_us() + max(0, int(wait_us))
    while _mono_us() < deadline:
        if predicate():
            return True
    return predicate()


def sovereign_status() -> dict[str, Any]:
    st_py = INSTALL / "lib" / "sovereign-time.py"
    if st_py.is_file():
        mod = _load_module(st_py, "sovereign_time_status")
        return mod.status()
    return {"ok": False, "error": "sovereign-time unavailable"}


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args or args[0] in ("-h", "--help", "help"):
        print("Usage: hostess7_sovereign_wait.py status|wait-us US [--ping URL]")
        return 0
    if args[0] in ("status", "json"):
        print(json.dumps(sovereign_status(), indent=2))
        return 0
    if args[0] == "wait-us":
        wait_us = int(args[1]) if len(args) > 1 else 800_000
        url = ""
        if "--ping" in args:
            url = args[args.index("--ping") + 1]
        pred = (lambda: _ping(url)) if url else (lambda: False)
        ok = wait_until(pred, wait_us=wait_us, label="cli_wait")
        print(json.dumps({"ok": ok, "wait_us": wait_us, "ping": url or None}))
        return 0 if ok or not url else 1
    print(f"unknown: {args[0]}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())