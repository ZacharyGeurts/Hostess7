#!/usr/bin/env pythong
"""CHIPs program usage — map Queen programs to ironclad chip facets and KILROY."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-chips-program-usage-doctrine.json"
SEED = INSTALL / "data" / "field-chips-program-usage-seed.json"
REGISTRY = INSTALL / "data" / "field-chips-program-usage-registry.json"
PANEL = STATE / "field-chips-program-usage-panel.json"


def _now() -> str:
    from datetime import datetime, timezone
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
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def resolve_program(program_id: str) -> dict[str, Any]:
    seed = _load(SEED, {})
    programs = seed.get("programs") or {}
    row = programs.get(program_id)
    if not row:
        return {"schema": "field-chips-program-usage/v1", "ok": False, "error": "unknown_program", "program_id": program_id}
    doctrine = _load(DOCTRINE, {})
    defaults = doctrine.get("resolve_defaults") or {}
    return {
        "schema": "field-chips-program-usage/v1",
        "ok": True,
        "generated": _now(),
        "program_id": program_id,
        "label": row.get("label"),
        "chip_facet": row.get("chip_facet"),
        "usage_pct": row.get("usage_pct"),
        "url": defaults.get(program_id),
        "kilroy": bool(row.get("kilroy")),
    }


def kilroy_usage() -> dict[str, Any]:
    doc = resolve_program("kilroy")
    doc["kilroy_integration"] = (_load(DOCTRINE, {}).get("kilroy_integration") or {})
    return doc


def build_registry() -> dict[str, Any]:
    seed = _load(SEED, {})
    programs = list((seed.get("programs") or {}).values())
    doc = {
        "schema": "field-chips-program-usage-registry/v1",
        "generated": _now(),
        "program_count": len(programs),
        "programs": programs,
        "ok": True,
    }
    _save(REGISTRY, doc)
    return doc


def publish_panel() -> dict[str, Any]:
    registry = build_registry()
    panel = {
        "schema": "field-chips-program-usage-panel/v1",
        "generated": registry["generated"],
        "program_count": registry["program_count"],
        "registry": str(REGISTRY),
        "ok": True,
    }
    _save(PANEL, panel)
    return {"ok": True, "panel": panel, "registry": registry}


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached:
        return cached
    return publish_panel().get("panel") or {}


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "json"
    if cmd == "resolve" and len(sys.argv) > 2:
        print(json.dumps(resolve_program(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "kilroy":
        print(json.dumps(kilroy_usage(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "publish":
        print(json.dumps(publish_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "hint": "resolve <id> | kilroy | publish | json"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())