#!/usr/bin/env pythong
"""RTX CANVAS block — AMOURANTHRTX display technology sealed like CHIPS."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-rtx-canvas-block-doctrine.json"
PANEL = STATE / "field-rtx-canvas-block-panel.json"
BATTERY = STATE / "field-rtx-canvas-block.json"
FACET = "rtx_canvas"
IRONCLAD_CITE = "ironclad:rtx_canvas:1"


def _now() -> str:
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


def _canvas_posture() -> dict[str, Any]:
    path = INSTALL / "Queen" / "lib" / "queen-canvas-renderer.py"
    if not path.is_file():
        return {"ok": False, "error": "queen_canvas_renderer_missing"}
    try:
        spec = importlib.util.spec_from_file_location("rtx_canvas_block", path)
        if not spec or not spec.loader:
            return {"ok": False}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "posture"):
            return mod.posture()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False}


def build_block() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    display_doc = _load(INSTALL / "data" / "field-rtx-display-doctrine.json", {})
    canvas = _canvas_posture()
    os_shaders = canvas.get("os_shaders") or []
    os_ok = all(s.get("exists") for s in os_shaders if isinstance(s, dict)) if os_shaders else False
    ok = bool(canvas.get("ok")) and os_ok and not display_doc.get("is_gui", False)

    return {
        "schema": "field-rtx-canvas-block/v1",
        "updated": _now(),
        "ok": ok,
        "held": ok,
        "truth": ok,
        "facet": FACET,
        "ironclad_citation": IRONCLAD_CITE,
        "role": display_doc.get("role", "display_technology"),
        "is_gui": False,
        "stack_layer": (display_doc.get("stack_layer") or {}).get("id", "queen_canvas"),
        "default_canvas": canvas.get("default_canvas", "CANVAS"),
        "desktop_comp_shader": canvas.get("desktop_comp_shader", False),
        "os_shaders_ok": os_ok,
        "engines_present": canvas.get("engines_present"),
        "canvas_posture": canvas,
        "posture": f"RTX CANVAS block — {canvas.get('default_canvas', 'CANVAS')} · technology layer above ZNetwork",
    }


def publish_panel() -> dict[str, Any]:
    block = build_block()
    panel = {
        "schema": "field-rtx-canvas-block-panel/v1",
        "updated": block.get("updated"),
        "ok": block.get("ok"),
        "held": block.get("held"),
        "snapshot": block,
    }
    _save(PANEL, panel)
    _save(BATTERY, block)
    return panel


def posture() -> dict[str, Any]:
    cached = _load(BATTERY, {})
    if cached.get("schema") == "field-rtx-canvas-block/v1":
        return cached
    return build_block()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "publish":
        print(json.dumps(publish_panel(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-rtx-canvas-block.py [json|publish]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())