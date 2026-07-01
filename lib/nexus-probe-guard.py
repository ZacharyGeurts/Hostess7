#!/usr/bin/env pythong
"""Break circular json subprocess probes — cached panels + depth guard."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

_PANEL_BY_SCRIPT: dict[str, str] = {
    "native-layer.py": "native-layer.json",
    "field-substrate-takeover.py": "field-substrate-takeover.json",
    "field-underlay.py": "field-underlay-panel.json",
    "cpu-vulnerability-shield.py": "cpu-vulnerability-shield.json",
    "field-polkit.py": "field-polkit.json",
    "terror-spiderweb.py": "terror-spiderweb-panel.json",
    "precision-field.py": "precision-field-panel.json",
}

# Circular json probes — never subprocess if panel exists (prevents fork bomb).
_CIRCULAR_JSON: frozenset[str] = frozenset({
    "native-layer.py",
    "field-substrate-takeover.py",
    "field-underlay.py",
    "terror-spiderweb.py",
    "precision-field.py",
})


def probe_depth() -> int:
    try:
        return max(0, int(os.environ.get("NEXUS_PROBE_DEPTH", "0") or "0"))
    except ValueError:
        return 0


def child_env(install: Path, state: Path) -> dict[str, str]:
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(install), "NEXUS_STATE_DIR": str(state)}
    env["NEXUS_PROBE_DEPTH"] = str(probe_depth() + 1)
    return env


def cached_panel(state: Path, script_rel: str) -> dict[str, Any] | None:
    name = _PANEL_BY_SCRIPT.get(script_rel)
    if not name:
        return None
    path = state / name
    if not path.is_file():
        return None
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(doc, dict):
        doc = {**doc, "_probe": {"cached": True, "panel": name}}
    return doc


def depth_stub(script_rel: str) -> dict[str, Any]:
    return {
        "ok": True,
        "probe_skipped": True,
        "script": script_rel,
        "reason": "depth_guard",
        "depth": probe_depth(),
    }


def run_json_probe(
    install: Path,
    state: Path,
    script_rel: str,
    *,
    mode: str = "json",
    timeout: float = 35,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    """Spawn lib/<script> once; never recurse into circular probes."""
    depth = probe_depth()
    if mode == "json" and script_rel in _CIRCULAR_JSON:
        cached = cached_panel(state, script_rel)
        if cached is not None:
            return cached
    if depth >= 1:
        cached = cached_panel(state, script_rel)
        return cached if cached is not None else depth_stub(script_rel)

    py = install / "lib" / script_rel
    if not py.is_file():
        return {"ok": False, "error": "missing", "path": str(py)}
    args = [sys.executable, str(py), mode, *(extra_args or [])]
    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=child_env(install, state),
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        cached = cached_panel(state, script_rel)
        if cached is not None:
            cached["_probe"]["fallback"] = True
            return cached
        return {"ok": False, "error": "probe_failed", "script": script_rel}