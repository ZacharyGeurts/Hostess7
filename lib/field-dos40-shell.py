#!/usr/bin/env python3
"""MS-DOS 4.0 module host — GNU Terminal extras loader."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "field-dos40-doctrine.json"


def _load() -> dict[str, Any]:
    try:
        return json.loads(DOCTRINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "field-dos40/v1", "modules": []}


def list_modules() -> dict[str, Any]:
    doc = _load()
    mods = list(doc.get("modules") or [])
    return {
        "ok": True,
        "schema": "field-dos40-modules/v1",
        "version": (doc.get("policy") or {}).get("version", "4.0"),
        "count": len(mods),
        "modules": mods,
    }


def resolve_module(name: str) -> dict[str, Any]:
    key = str(name or "").strip().lower()
    if not key:
        return {"ok": False, "error": "module_required"}
    for mod in _load().get("modules") or []:
        cmds = {str(c).lower() for c in (mod.get("terminal_cmds") or [])}
        cmds.add(str(mod.get("id") or "").lower())
        if key in cmds:
            return {"ok": True, "module": mod, "launch": mod.get("exec"), "action": mod.get("action")}
    return {"ok": False, "error": "unknown_module", "module": key}


def terminal_dispatch(cmd: str) -> dict[str, Any] | None:
    parts = cmd.strip().split()
    if not parts:
        return None
    head = parts[0].lower()
    if head == "modules":
        doc = list_modules()
        lines = ["MS-DOS 4.0 modules — load with: load-module <name>", ""]
        for m in doc.get("modules") or []:
            flag = " (soon)" if m.get("coming_soon") else ""
            lines.append(f"  {m.get('id')}: {m.get('label')}{flag}")
            if m.get("dos_help"):
                lines.append(f"    {m['dos_help']}")
        return {"ok": True, "output": "\n".join(lines), "dos40": True, "modules": doc.get("modules")}
    if head in ("load-module", "loadmodule", "module"):
        if len(parts) < 2:
            return {"ok": False, "output": "usage: load-module <name>  (try: modules)", "dos40": True}
        res = resolve_module(parts[1])
        if not res.get("ok"):
            return {"ok": False, "output": f"module not found: {parts[1]}", "dos40": True}
        mod = res.get("module") or {}
        if mod.get("coming_soon"):
            return {"ok": False, "output": f"{mod.get('label')} — coming soon on CHIPS lane", "dos40": True}
        launch = res.get("launch") or ""
        return {
            "ok": True,
            "output": f"Loading {mod.get('label')}…",
            "dos40": True,
            "open_url": launch,
            "module": mod,
        }
    res = resolve_module(head)
    if res.get("ok"):
        mod = res.get("module") or {}
        if mod.get("coming_soon"):
            return {"ok": False, "output": f"{mod.get('label')} — coming soon", "dos40": True}
        if mod.get("action") == "truth":
            q = mod.get("truth_query") or mod.get("id") or ""
            return {
                "ok": True,
                "output": f"MEM — stack witness · truth query: {q}\n(type: truth {q})",
                "dos40": True,
                "module": mod,
                "truth_query": q,
            }
        launch = res.get("launch") or ""
        return {
            "ok": True,
            "output": f"MS-DOS 4.0 → {mod.get('label')}",
            "dos40": True,
            "open_url": launch,
            "module": mod,
        }
    return None


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").lower()
    if cmd in ("json", "modules"):
        print(json.dumps(list_modules(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve" and len(sys.argv) > 2:
        print(json.dumps(resolve_module(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-dos40-shell.py [json|modules|resolve NAME]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())