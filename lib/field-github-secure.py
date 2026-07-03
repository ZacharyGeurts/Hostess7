#!/usr/bin/env pythong
"""Field GitHub secure — panel-facing pinned GitHub connect (AmmoNet / Ironclad lane)."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-github-secure-panel.json"


def _import_py(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def panel_json(*, write: bool = False) -> dict[str, Any]:
    gh = _import_py(INSTALL / "Queen" / "lib" / "queen-github-secure.py", "queen_github_secure")
    secure = _import_py(INSTALL / "Hostess7" / "scripts" / "hostess7_secure_git.py", "hostess7_secure_git")
    mcp = _import_py(INSTALL / "lib" / "field-github-mcp-transport.py", "field_github_mcp")
    verify: dict[str, Any] = {}
    cached = {}
    cache_path = STATE / "queen-github-secure-cache.json"
    if cache_path.is_file():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8")).get("verify") or {}
        except (OSError, json.JSONDecodeError):
            cached = {}
    if gh and hasattr(gh, "panel_json"):
        try:
            verify = gh.panel_json()
        except Exception as exc:
            verify = cached or {"ok": False, "error": str(exc)[:120]}
    elif cached:
        verify = cached
    route = None
    if secure and hasattr(secure, "verify"):
        try:
            route = secure.verify()
        except Exception as exc:
            route = {"ok": False, "error": str(exc)[:120], "cached": bool(cached)}
    transport = None
    if mcp and hasattr(mcp, "mcp_ready"):
        try:
            transport = mcp.mcp_ready()
        except Exception as exc:
            transport = {"ok": False, "error": str(exc)[:120]}
    doc = {
        "ok": True,
        "schema": "field-github-secure/v1",
        "github_secure": verify,
        "secure_git": route,
        "mcp_transport": transport,
        "ammonet_api": "/api/ammonet",
        "push_lane": "Hostess7/scripts/hostess7_secure_git.py push",
        "transport_default": os.environ.get("AML_GITHUB_TRANSPORT", "mcp_secure"),
    }
    if write:
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        PANEL.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(write=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-github-secure.py [json|panel]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())