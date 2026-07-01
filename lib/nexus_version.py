#!/usr/bin/env pythong
"""NEXUS-Shield version — read from lib/nexus-common.sh (single source of truth)."""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

_VERSION_RE = re.compile(r'NEXUS_VERSION="([^"]+)"')


def install_root() -> Path:
    return Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))


@lru_cache(maxsize=4)
def read_version(root: str | None = None) -> str:
    """Return NEXUS_VERSION from nexus-common.sh, else env, else 'unknown'."""
    base = Path(root) if root else install_root()
    common = base / "lib" / "nexus-common.sh"
    if common.is_file():
        try:
            m = _VERSION_RE.search(common.read_text(encoding="utf-8", errors="replace"))
            if m:
                return m.group(1)
        except OSError:
            pass
    return os.environ.get("NEXUS_VERSION", "unknown")


def clear_cache() -> None:
    read_version.cache_clear()