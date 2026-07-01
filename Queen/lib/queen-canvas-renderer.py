#!/usr/bin/env pythong
"""Queen CANVAS backend renderer — AMOURANTHRTX display technology above ZNetwork, below Queen shell."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "AmmoOS"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _sg_root() -> Path:
    env = os.environ.get("SG_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return SG.resolve()


def amouranthrtx_root() -> Path:
    env = os.environ.get("AMOURANTHRTX_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    sg = _sg_root()
    for candidate in (
        QUEEN / "engine" / "AMOURANTHRTX",
        sg / "AMOURANTHRTX",
        sg / "NewLatest" / "AMOURANTHRTX",
    ):
        if candidate.is_dir() and (candidate / "CMakeLists.txt").is_file():
            return candidate.resolve()
    return (sg / "AMOURANTHRTX").resolve()


def _doctrine_path() -> Path:
    for candidate in (
        INSTALL / "data" / "field-rtx-display-doctrine.json",
        _sg_root() / "AmmoOS" / "data" / "field-rtx-display-doctrine.json",
    ):
        if candidate.is_file():
            return candidate
    return INSTALL / "data" / "field-rtx-display-doctrine.json"


def _shader_stat(rtx: Path, rel: str) -> dict[str, Any]:
    path = rtx / rel
    if not path.is_file():
        return {"path": str(path), "exists": False}
    try:
        st = path.stat()
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"path": str(path), "exists": False}
    return {
        "path": str(path.resolve()),
        "exists": True,
        "bytes": st.st_size,
        "lines": text.count("\n") + (1 if text else 0),
    }


def _demo_shaders(rtx: Path, doctrine: dict[str, Any]) -> list[dict[str, Any]]:
    demo = doctrine.get("demo_shaders") or {}
    demo_dir = demo.get("directory") or "demos/shaders/compute"
    out: list[dict[str, Any]] = []
    for name in demo.get("modules") or []:
        rel = f"{demo_dir}/{name}.comp"
        row = _shader_stat(rtx, rel)
        row["id"] = name
        row["demos_only"] = True
        out.append(row)
    return out


def _os_shaders(rtx: Path, doctrine: dict[str, Any]) -> list[dict[str, Any]]:
    os_doc = doctrine.get("os_shaders") or {}
    out: list[dict[str, Any]] = []
    for mod in os_doc.get("modules") or []:
        rel = str(mod.get("file") or "")
        row = _shader_stat(rtx, rel)
        row["id"] = mod.get("id", "")
        row["role"] = mod.get("role", "")
        row["os"] = True
        out.append(row)
    return out


def _import_kilroy_rtx() -> dict[str, Any] | None:
    kilroy = QUEEN / "lib" / "queen-kilroy.py"
    if not kilroy.is_file():
        kilroy = INSTALL / "Queen" / "lib" / "queen-kilroy.py"
    if not kilroy.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("queen_kilroy_canvas", kilroy)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "amouranthrtx_status"):
            return mod.amouranthrtx_status()
    except Exception:
        return None
    return None


def posture() -> dict[str, Any]:
    doctrine = _load(_doctrine_path(), {})
    rtx = amouranthrtx_root()
    os_shaders = _os_shaders(rtx, doctrine)
    demo_shaders = _demo_shaders(rtx, doctrine)
    default = (
        os.environ.get("QUEEN_CANVAS_SHADER", "").strip()
        or os.environ.get("AMOURANTHRTX_CANVAS", "").strip()
        or (doctrine.get("os_shaders") or {}).get("default")
        or "CANVAS"
    )
    demo_gate = os.environ.get("AMOURANTHRTX_DEMO", "0").strip() not in ("", "0", "false", "False")
    os_default = _shader_stat(
        rtx,
        f"Navigator/shaders/compute/{default}.comp"
        if not str(default).endswith(".comp")
        else f"Navigator/shaders/compute/{default}",
    )
    engines_ok = all(
        (rtx / eng).is_file()
        for eng in (doctrine.get("os_shaders") or {}).get("engines") or []
    )
    os_present = all(s.get("exists") for s in os_shaders)
    stack = doctrine.get("stack_layer") or {}
    queen_backend = doctrine.get("queen_backend") or {}

    return {
        "schema": "queen-canvas-renderer/v1",
        "ok": rtx.is_dir() and os_present and engines_ok,
        "ts": _now(),
        "role": doctrine.get("role", "display_technology"),
        "is_gui": doctrine.get("is_gui", False),
        "motto": doctrine.get("motto", ""),
        "stack_layer": stack,
        "stack_position": "above_znetwork_below_queen",
        "amouranthrtx_root": str(rtx),
        "amouranthrtx_present": rtx.is_dir() and (rtx / "CMakeLists.txt").is_file(),
        "default_canvas": default,
        "default_shader": os_default,
        "desktop_comp_shader": queen_backend.get("desktop_comp_shader", False),
        "layout_version": (doctrine.get("os_shaders") or {}).get("layout_version", 5),
        "os_shaders": os_shaders,
        "demo_shaders": demo_shaders,
        "demo_gate_open": demo_gate,
        "demo_env": "AMOURANTHRTX_DEMO",
        "os_boot_shader": (doctrine.get("os_shaders") or {}).get("dispatch", "CANVAS.comp"),
        "engines_present": engines_ok,
        "pipeline": (rtx / "Navigator" / "engine" / "Pipeline.hpp").is_file(),
        "field_fabric": (rtx / "Navigator" / "engine" / "FieldFabric.hpp").is_file(),
        "field_thermal_guard": (rtx / "Navigator" / "engine" / "FieldThermalGuard.hpp").is_file(),
        "field_gpu_launch": (rtx / "Navigator" / "engine" / "FieldGpuLaunch.hpp").is_file(),
        "operator_surface": queen_backend.get("operator_surface"),
        "doctrine": str(_doctrine_path()),
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "posture"):
        return {"ok": True, **posture()}
    if action == "demo_list":
        doc = posture()
        return {
            "ok": True,
            "demos_only": True,
            "demo_gate": doc.get("demo_env"),
            "shaders": doc.get("demo_shaders") or [],
        }
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-canvas-renderer.py [json|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())