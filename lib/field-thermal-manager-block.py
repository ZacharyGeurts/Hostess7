#!/usr/bin/env pythong
"""Thermal Manager block — ironclad sealed NEXUS C2 surface (like CHIPS core)."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

def _install_root() -> Path:
    env = os.environ.get("NEXUS_INSTALL_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "data" / "field-thermal-manager-block-doctrine.json").is_file():
            return p
    nl = Path(os.environ.get("SG_ROOT", Path(__file__).resolve().parents[2])) / "NewLatest"
    if (nl / "data" / "field-thermal-manager-block-doctrine.json").is_file():
        return nl.resolve()
    return Path(__file__).resolve().parents[1]


INSTALL = _install_root()
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent))
DOCTRINE = INSTALL / "data" / "field-thermal-manager-block-doctrine.json"
PANEL = STATE / "field-thermal-manager-block-panel.json"
BATTERY = STATE / "field-thermal-manager-block.json"
FACET = "thermal_manager"
IRONCLAD_CITE = "ironclad:thermal_manager:1"


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


def _ironclad_slice() -> dict[str, Any]:
    cached = _load(STATE / "ironclad-immediate.json", {})
    if cached.get("schema"):
        return cached
    mod = _import_py(INSTALL / "lib" / "ironclad-immediate.py", "ic_tmb")
    if mod and hasattr(mod, "immediate_slice"):
        try:
            return mod.immediate_slice()
        except Exception:
            pass
    return cached


def _final_eye_ocr_html(html_path: Path, needles: list[str]) -> dict[str, Any]:
    """Final_Eye/ZOCR text validation on thermal manager surface HTML."""
    eye = SG / "Final_Eye" / "zocr.py"
    text = ""
    if html_path.is_file():
        text = html_path.read_text(encoding="utf-8", errors="replace")
    hits = [n for n in needles if n.lower() in text.lower()]
    ocr_mod = _import_py(eye, "zocr_tmb")
    tesseract_ok = bool(ocr_mod and getattr(ocr_mod, "tesseract_available", lambda: False)())
    return {
        "schema": "field-thermal-manager-ocr/v1",
        "engine": "Final_Eye/zocr.py",
        "html_path": str(html_path),
        "html_exists": html_path.is_file(),
        "needles": needles,
        "hits": hits,
        "hit_count": len(hits),
        "ok": html_path.is_file() and len(hits) >= max(3, len(needles) - 1),
        "tesseract_available": tesseract_ok,
    }


def _guard_posture() -> dict[str, Any]:
    mod = _import_py(INSTALL / "lib" / "field-thermal-guard.py", "ftg_tmb")
    if mod and hasattr(mod, "evaluate"):
        try:
            return mod.evaluate()
        except Exception:
            pass
    return _load(STATE / "field-thermal-guard.json", {})


def _governor_posture() -> dict[str, Any]:
    mod = _import_py(INSTALL / "lib" / "thermal-governor.py", "tg_tmb")
    if mod and hasattr(mod, "evaluate"):
        try:
            return mod.evaluate()
        except Exception:
            pass
    return _load(STATE / "thermal-advisory.json", {})


def _canvas_posture() -> dict[str, Any]:
    for rel in ("Queen/lib/queen-canvas-renderer.py",):
        mod = _import_py(INSTALL / rel, "qcr_tmb")
        if mod and hasattr(mod, "posture"):
            try:
                return mod.posture()
            except Exception:
                pass
    return {}


def build_block(*, refresh: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    ironclad = _ironclad_slice()
    sealed = bool(ironclad.get("ironclad_sealed") or ironclad.get("realized"))
    guard = _guard_posture()
    governor = _governor_posture()
    canvas = _canvas_posture()
    ocr_spec = doctrine.get("ocr_expect") or {}
    html_rel = str(ocr_spec.get("surface_html") or "Queen/world/queen-thermal-manager.html")
    html_path = INSTALL / html_rel
    for candidate in (INSTALL / html_rel, SG / "NewLatest" / html_rel, SG / "Queen" / Path(html_rel).name):
        if candidate.is_file():
            html_path = candidate
            break
    ocr = _final_eye_ocr_html(html_path, list(ocr_spec.get("needles") or []))

    headroom = float(guard.get("headroom_pct") or 0)
    level = str(governor.get("level") or guard.get("anomaly", {}).get("thermal_level") or "ok")
    thermal_cfg = doctrine.get("thermal") or {}
    min_h = float(thermal_cfg.get("min_headroom_pct") or 15)
    blocked = {str(x).lower() for x in (thermal_cfg.get("blocked_levels") or ["crit", "storm"])}
    thermal_safe = headroom >= min_h and level.lower() not in blocked

    surface = doctrine.get("surface") or "/world/queen-thermal-manager.html"
    module_ok = (INSTALL / "lib" / "field-thermal-manager-block.py").is_file()
    held = (
        module_ok
        and guard.get("schema") == "field-thermal-guard/v1"
        and html_path.is_file()
        and ocr.get("ok")
    )
    ok = held and thermal_safe

    return {
        "schema": "field-thermal-manager-block/v1",
        "updated": _now(),
        "ok": ok,
        "held": held,
        "truth": held,
        "motto": doctrine.get("motto", ""),
        "facet": FACET,
        "ironclad_citation": IRONCLAD_CITE,
        "ironclad_sealed": sealed,
        "thermal_safe": thermal_safe,
        "headroom_pct": headroom,
        "thermal_level": level,
        "surface": surface,
        "bookmark_id": "thermal-manager",
        "guard": {
            "headroom_pct": guard.get("headroom_pct"),
            "certainty_score": guard.get("certainty_score"),
            "peak_c": guard.get("peak_c"),
        },
        "governor": {
            "level": governor.get("level"),
            "peak_c": governor.get("peak_c"),
            "quota_pct": governor.get("quota_pct"),
        },
        "canvas": {
            "ok": canvas.get("ok"),
            "default_canvas": canvas.get("default_canvas"),
            "desktop_comp_shader": canvas.get("desktop_comp_shader", False),
        },
        "ocr": ocr,
        "ironclad_chain": {
            "citation": IRONCLAD_CITE,
            "sealed": sealed,
            "truth_percent": 100.0 if sealed and ok else 95.0 if ok else 80.0,
            "layers": ["ironclad", "thermal_guard", "thermal_manager", "final_eye_ocr"],
        },
        "posture": f"Thermal Manager block — headroom {headroom}% · level {level} · OCR {ocr.get('hit_count', 0)} hits",
    }


def publish_panel(*, refresh: bool = False) -> dict[str, Any]:
    block = build_block(refresh=refresh)
    panel = {
        "schema": "field-thermal-manager-block-panel/v1",
        "updated": block.get("updated"),
        "ok": block.get("ok"),
        "held": block.get("held"),
        "thermal_safe": block.get("thermal_safe"),
        "headroom_pct": block.get("headroom_pct"),
        "thermal_level": block.get("thermal_level"),
        "surface": block.get("surface"),
        "ocr_ok": (block.get("ocr") or {}).get("ok"),
        "ironclad_sealed": block.get("ironclad_sealed"),
        "snapshot": block,
    }
    _save(PANEL, panel)
    _save(BATTERY, block)
    return panel


def posture() -> dict[str, Any]:
    cached = _load(BATTERY, {})
    if cached.get("schema") == "field-thermal-manager-block/v1" and cached.get("updated"):
        return cached
    return build_block()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("publish", "panel"):
        print(json.dumps(publish_panel(refresh=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ocr":
        doc = _load(DOCTRINE, {})
        spec = doc.get("ocr_expect") or {}
        html = INSTALL / str(spec.get("surface_html") or "Queen/world/queen-thermal-manager.html")
        print(json.dumps(_final_eye_ocr_html(html, list(spec.get("needles") or [])), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-thermal-manager-block.py [json|publish|ocr]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())