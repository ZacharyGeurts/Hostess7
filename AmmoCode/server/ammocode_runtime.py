#!/usr/bin/env python3
"""AmmoCode runtime paths — frozen executable vs dev tree."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False)) or os.environ.get("AMMOCODE_FROZEN", "").strip() in (
        "1", "true", "yes",
    )


def bundle_root() -> Path:
    if is_frozen() and getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parents[1]


def executable_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return bundle_root()


def settings_dir() -> Path:
    raw = os.environ.get("AMMOCODE_SETTINGS_DIR", "").strip()
    if raw:
        return Path(raw).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if xdg:
        return Path(xdg) / "ammocode"
    return Path.home() / ".config" / "ammocode"