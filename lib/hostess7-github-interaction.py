#!/usr/bin/env pythong
"""Hostess 7 GitHub Interaction — straight lane, constant GitHub open, secure for us."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-github-interaction-doctrine.json"
PANEL = STATE / "hostess7-github-interaction-panel.json"
GITHUB_CACHE = STATE / "field-internet-github.json"
LEGACY_CACHE = STATE / "field-github-legacy-probe.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _run_json(rel: str, args: list[str] | None = None, *, timeout: int = 25) -> dict[str, Any]:
    import subprocess
    import sys

    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *(args or ["json"])],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"ok": False, "error": "script_failed", "script": rel}


def panel(*, write: bool = True, fast: bool = True) -> dict[str, Any]:
    if fast and PANEL.is_file():
        cached = _load(PANEL, {})
        if cached.get("schema") == "hostess7-github-interaction-panel/v1":
            cached["updated"] = _utc()
            return cached

    doctrine = _load(DOCTRINE, {})
    gh = _load(GITHUB_CACHE, {}) or _load(LEGACY_CACHE, {})
    if not gh.get("schema"):
        gh = _run_json("lib/field-github-legacy.py", ["probe"], timeout=20)
    if not gh.get("schema"):
        keepalive = _run_json("lib/field-internet-unified.py", ["keepalive"], timeout=25)
        gh = keepalive.get("github") or {}

    doc = {
        "ok": True,
        "schema": "hostess7-github-interaction-panel/v1",
        "boss": "hostess7",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "updated": _utc(),
        "lane": (doctrine.get("interaction") or {}).get("lane", "hostess7-github"),
        "interaction": doctrine.get("interaction") or {},
        "secure_for_us": doctrine.get("secure_for_us") or {},
        "github_always": {
            "enabled": True,
            "open": bool(gh.get("stable") or gh.get("always_open") or gh.get("open_count", 0) > 0),
            "stable": gh.get("stable"),
            "open_count": gh.get("open_count"),
            "legacy_open": gh.get("legacy_open", 0),
            "canonical_open": gh.get("canonical_open"),
            "live": gh,
        },
        "internet_unified": {
            "ok": gh.get("ok"),
            "api": "/api/field-internet",
            "keepalive_api": "/api/field-internet/keepalive",
        },
        "github_legacy": {
            "api": "/api/field-github-legacy",
            "catalog": gh.get("total_catalog"),
            "secure_legacy": gh.get("secure_legacy"),
        },
        "pages_surface": (doctrine.get("interaction") or {}).get("surface"),
        "wires": doctrine.get("wires") or [],
        "fast": fast,
    }
    doc["ok"] = bool(doc["github_always"]["open"])
    if write:
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        PANEL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(panel(write=False, fast=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "panel":
        print(json.dumps(panel(write=True, fast=False), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "hostess7-github-interaction.py [panel|json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())