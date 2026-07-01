#!/usr/bin/env pythong
"""Queen Field Tools — canonical build toolchain for Hostess 7 (g16 + field cmake + forge)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
_LIB = Path(__file__).resolve().parent
SG = QUEEN.parent.parent
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", SG / "Hostess7"))
_SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_SG_PATHS_LIB) not in sys.path:
    sys.path.insert(0, str(_SG_PATHS_LIB))
from sg_paths import grok16_root

GROK16 = grok16_root()
FORGE = _LIB / "queen-forge.py"
MANIFEST_PATH = QUEEN / "data" / "queen-field-tools.json"

if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from forge.engine import ForgeContext  # noqa: E402
from forge.tools import TOOL_REGISTRY  # noqa: E402
from forge.compiler_tools import g16_status, grok16_root  # noqa: E402
from forge.field_cmake_tools import field_cmake_status  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_essential_status() -> dict[str, Any]:
    path = GROK16 / "data" / "grok16-build-essential-toolchain.json"
    if not path.is_file():
        return {"ready": False, "manifest": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ready": False, "manifest": str(path)}


def _field_build_status() -> dict[str, Any]:
    path = GROK16 / "data" / "grok16-field-build-toolchain.json"
    if not path.is_file():
        return {"ready": False, "manifest": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"ready": False, "manifest": str(path)}


# Canonical field build tools Hostess 7 may invoke (forge id → metadata)
FIELD_TOOL_CATALOG: tuple[dict[str, str], ...] = (
    {"id": "field_cmake", "track": "field-cmake", "label": "Grok16 Field CMake (configure + Ninja build)",
     "role": "g16 owns RTX cmake — replaces Queen cmake glue", "hostess_cmd": "./Hostess7.sh queen-field-build rtx"},
    {"id": "field_cmake_configure", "track": "field-cmake", "label": "Field CMake configure (queen-rtx preset)",
     "role": "Ninja + grok16-field.cmake + 4K@120Hz preset", "hostess_cmd": "./Hostess7.sh queen-field-build configure"},
    {"id": "field_cmake_build", "track": "field-cmake", "label": "Field CMake build amouranth_engine",
     "role": "Incremental Ninja compile via g16", "hostess_cmd": "./Hostess7.sh queen-field-build compile"},
    {"id": "compiler_probe", "track": "toolchain", "label": "Probe g16 + cmake + ninja → manifest",
     "role": "Sync g16-toolchain.json for Hostess brain", "hostess_cmd": "./Hostess7.sh queen-grok16-probe"},
    {"id": "gcc", "track": "toolchain", "label": "Grok16 g16 toolchain pipeline",
     "role": "Unified g16 @ 16.1.1 field_opt", "hostess_cmd": "pythong Queen/lib/queen-forge.py run gcc"},
    {"id": "binutils_fetch", "track": "toolchain", "label": "Grok16 field binutils fetch",
     "role": "g16-as / g16-ld vendor", "hostess_cmd": "pythong Queen/lib/queen-forge.py run binutils_fetch"},
    {"id": "binutils_build", "track": "toolchain", "label": "Grok16 field binutils build",
     "role": "Field assembler + linker", "hostess_cmd": "pythong Queen/lib/queen-forge.py run binutils_build"},
    {"id": "build_essential_install", "track": "build-essential", "label": "Grok16 build-essential (Ubuntu parity+)",
     "role": "g16 + binutils + cmake/ninja + autotools + utilities — all in NewLatest/Grok16", "hostess_cmd": "./Grok16/scripts/grok16-build-essential.sh install"},
    {"id": "build_essential_verify", "track": "build-essential", "label": "Grok16 build-essential verify",
     "role": "Compile+link smoke with g16-build-env", "hostess_cmd": "./Grok16/scripts/grok16-build-essential.sh verify"},
    {"id": "field_build_install", "track": "field-build", "label": "Grok16 field build fabric install",
     "role": "g16-cmake/ninja/make/bison/flex wrappers + compat symlinks", "hostess_cmd": "./Grok16/scripts/grok16-field-build.sh install"},
    {"id": "field_build_verify", "track": "field-build", "label": "Grok16 field build verify",
     "role": "cmake/ninja/make/bison/flex + minimal example", "hostess_cmd": "./Grok16/scripts/grok16-field-build.sh verify"},
    {"id": "shaders", "track": "compile", "label": "QueenBoot SPIR-V (glslc)",
     "role": "Boot comp shader for RTX", "hostess_cmd": "pythong Queen/lib/queen-forge.py run shaders"},
    {"id": "deps", "track": "compile", "label": "Stage inside deps (SDL, glm)",
     "role": "No network fetch — Queen/vendor/deps", "hostess_cmd": "pythong Queen/lib/queen-forge.py run deps"},
    {"id": "rtx", "track": "compile", "label": "Queen-browser RTX exe",
     "role": "Sovereign browser — field_opt + mandate", "hostess_cmd": "bash Queen/build-all.sh"},
    {"id": "rtx_configure", "track": "compile", "label": "RTX cmake configure",
     "role": "Delegates to field-cmake.sh", "hostess_cmd": "pythong Queen/lib/queen-forge.py run rtx_configure"},
    {"id": "rtx_build", "track": "compile", "label": "RTX compile queen-browser",
     "role": "Ninja incremental via field cmake", "hostess_cmd": "pythong Queen/lib/queen-forge.py run rtx_build"},
    {"id": "gpu_probe", "track": "probe", "label": "Vulkan + PCI GPU probe",
     "role": "RTX vendor selection for Queen", "hostess_cmd": "pythong Queen/lib/queen-forge.py run gpu_probe"},
    {"id": "verify", "track": "qa", "label": "Queen doctrine + GUI verify",
     "role": "Post-build QA gate", "hostess_cmd": "pythong Queen/lib/queen-forge.py run verify"},
    {"id": "field_tech", "track": "operator", "label": "Field Technology full core pipeline",
     "role": "Optimized forge drop order", "hostess_cmd": "pythong Queen/lib/queen-forge.py run field_tech"},
    {"id": "field", "track": "sovereign", "label": "Seal one sovereign field package",
     "role": "field/sovereign publish", "hostess_cmd": "pythong Queen/lib/queen-forge.py run field"},
    {"id": "hostess_teach", "track": "hostess", "label": "Teach Hostess Queen redata + build tools",
     "role": "Comfort brief + BUILD_TOOLS sync", "hostess_cmd": "./Hostess7.sh queen-teach-redata"},
    {"id": "textbook_zac", "track": "hostess", "label": "Field Technology ZAC monolith",
     "role": "22 chapters → brain", "hostess_cmd": "pythong Queen/lib/queen-forge.py run textbook_zac"},
    {"id": "forge_watch", "track": "operator", "label": "Forge log watch (ZOCR + senses)",
     "role": "Catch build hangups", "hostess_cmd": "pythong Queen/lib/queen-forge.py run forge_watch"},
)


def _tool_row(ctx: ForgeContext, meta: dict[str, str]) -> dict[str, Any]:
    tid = meta["id"]
    reg = TOOL_REGISTRY.get(tid)
    if tid == "build_essential_install":
        ready = bool(_build_essential_status().get("ready"))
    elif tid == "build_essential_verify":
        ready = (GROK16 / "scripts/g16-build-env.sh").is_file()
    elif tid == "field_build_install":
        ready = bool(_field_build_status().get("ready"))
    elif tid == "field_build_verify":
        ready = (GROK16 / "bin/g16-cmake").is_file() and (GROK16 / "bin/g16-ninja").is_file()
    else:
        ready = reg.check(ctx) if reg else False
    return {
        **meta,
        "ready": ready,
        "optional": reg.optional if reg else False,
        "forge": "lib/queen-forge.py",
        "replaces": reg.replaces if reg else "",
    }


def field_tools_status(*, write_manifest: bool = True) -> dict[str, Any]:
    ctx = ForgeContext.from_env()
    g16 = g16_status(ctx)
    fcmake = field_cmake_status(ctx)
    tools = [_tool_row(ctx, dict(m)) for m in FIELD_TOOL_CATALOG]
    by_track: dict[str, list[dict[str, Any]]] = {}
    for t in tools:
        by_track.setdefault(t["track"], []).append(t)
    doc = {
        "schema": "queen-field-tools/v1",
        "updated": _now(),
        "product": "Queen Field Tools",
        "doctrine": "All build tools are field-native — Grok16 g16 + field cmake + Queen forge. Hostess 7 invokes via ./Hostess7.sh queen-field-tools or /api/field-tools.",
        "queen_root": str(QUEEN),
        "grok16_root": str(grok16_root(ctx)),
        "hostess7_root": str(HOSTESS),
        "g16": {
            "version": g16.get("g16_version"),
            "ready": g16.get("ready"),
            "unified_driver": g16.get("unified_driver"),
            "paths": g16.get("paths"),
        },
        "field_cmake": fcmake,
        "build_essential": _build_essential_status(),
        "field_build": _field_build_status(),
        "display_default": {"width": 3840, "height": 2160, "refresh_hz": 120},
        "api": {
            "field_tools": "/api/field-tools",
            "queen_build": "/api/queen-build",
            "hostess_brain": "/api/field-brain",
            "forge": "/api/queen-forge",
        },
        "hostess_commands": {
            "status": "./Hostess7.sh queen-field-tools",
            "probe": "./Hostess7.sh queen-field-tools probe",
            "run": "./Hostess7.sh queen-field-tools run <tool_id>",
            "build_rtx": "./Hostess7.sh queen-field-build rtx",
            "build_essential": "./Grok16/scripts/grok16-build-essential.sh status",
            "build_env": "eval \"$(./Grok16/scripts/grok16-build-essential.sh env)\"",
            "field_build": "./Grok16/scripts/grok16-field-build.sh status",
            "g16_probe": "./Hostess7.sh queen-grok16-probe",
        },
        "tools": tools,
        "by_track": by_track,
        "ready_count": sum(1 for t in tools if t.get("ready")),
        "tool_count": len(tools),
    }
    if write_manifest:
        MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return doc


def probe_field_tools() -> dict[str, Any]:
    doc = field_tools_status(write_manifest=True)
    missing = [t["id"] for t in doc["tools"] if not t.get("ready") and t["id"] in (
        "compiler_probe", "field_cmake_configure", "shaders", "deps", "rtx",
    )]
    doc["probe"] = {
        "ok": len(missing) == 0,
        "missing_core": missing,
        "g16_ready": doc["g16"].get("ready"),
        "field_cmake_script": (GROK16 / "scripts/field-cmake.sh").is_file(),
    }
    return doc


def run_field_tool(tool_id: str, *, force: bool = False) -> dict[str, Any]:
    if tool_id not in TOOL_REGISTRY:
        return {"ok": False, "error": "unknown_tool", "tool": tool_id, "known": list(TOOL_REGISTRY)}
    args = [sys.executable, str(FORGE), "run", tool_id]
    if force:
        args.append("--force")
    proc = subprocess.run(
        args,
        cwd=str(QUEEN),
        capture_output=True,
        text=True,
        timeout=7200,
        env={**os.environ, "QUEEN_ROOT": str(QUEEN), "GROK16_ROOT": str(GROK16)},
    )
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        out = {"ok": proc.returncode == 0, "tool": tool_id, "tail": (proc.stdout or "")[-3000:]}
    out["field_tools"] = field_tools_status(write_manifest=False)
    return out


def teach_hostess_field_tools() -> dict[str, Any]:
    doc = field_tools_status(write_manifest=True)
    brief_path = HOSTESS / "cache/fieldstorage/brain/sdf/queen_field_tools_brief.json"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief = {
        "schema": "queen-field-tools-brief/v1",
        "updated": doc["updated"],
        "source": str(MANIFEST_PATH),
        "tools": doc["tools"],
        "hostess_commands": doc["hostess_commands"],
        "g16": doc["g16"],
        "field_cmake": doc["field_cmake"],
    }
    brief_path.write_text(json.dumps(brief, indent=2) + "\n", encoding="utf-8")
    teach_script = HOSTESS / "scripts" / "field_queen_redata_teach.py"
    hostess_ok = False
    if teach_script.is_file():
        proc = subprocess.run(
            [sys.executable, str(teach_script)],
            cwd=str(HOSTESS),
            capture_output=True,
            text=True,
            timeout=180,
        )
        hostess_ok = proc.returncode == 0
    return {
        "ok": True,
        "manifest": str(MANIFEST_PATH),
        "hostess_brief": str(brief_path),
        "hostess_teach_ok": hostess_ok,
        "tool_count": doc["tool_count"],
        "ready_count": doc["ready_count"],
    }


def dispatch(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json", "list"):
        return {"ok": True, **field_tools_status()}
    if action in ("probe", "compiler_probe", "refresh"):
        return {"ok": True, **probe_field_tools()}
    if action in ("teach", "sync", "hostess-teach"):
        return teach_hostess_field_tools()
    if action in ("run", "build", "forge"):
        tool_id = str(body.get("tool") or body.get("id") or body.get("stage") or "rtx")
        return run_field_tool(tool_id, force=bool(body.get("force")))
    if action in ("run-all", "field-tech", "field_tech"):
        return run_field_tool("field_tech")
    if action in ("rtx", "queen-browser"):
        return run_field_tool("rtx")
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("json", "status"):
        print(json.dumps(field_tools_status(), indent=2))
        return 0
    if args[0] == "probe":
        print(json.dumps(probe_field_tools(), indent=2))
        return 0
    if args[0] == "teach":
        print(json.dumps(teach_hostess_field_tools(), indent=2))
        return 0
    if args[0] == "run" and len(args) >= 2:
        print(json.dumps(run_field_tool(args[1]), indent=2))
        return 0
    if args[0] == "dispatch":
        body = json.loads(sys.stdin.read() or "{}")
        print(json.dumps(dispatch(body), indent=2))
        return 0
    print(json.dumps({"ok": False, "usage": "queen-field-tools.py [json|probe|teach|run TOOL|dispatch]"}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())