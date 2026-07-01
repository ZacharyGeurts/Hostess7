"""Queen Forge — Grok16 field build (g16 + Ninja; configure once, no cmake --build)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from forge.compiler_tools import field_cmake_script, grok16_field_cmake_path, grok16_root
from forge.engine import ForgeContext, ForgeEngine, ForgeResult


def _grok16_forge(ctx: ForgeContext) -> Path:
    return grok16_root(ctx) / "forge" / "grok16-forge.py"


def _run_grok16_forge(ctx: ForgeContext, engine: ForgeEngine, tool_id: str) -> ForgeResult:
    script = _grok16_forge(ctx)
    if not script.is_file():
        return ForgeResult(False, tool_id, f"missing {script}")
    env = {
        **ctx.env(),
        "GROK16_ROOT": str(grok16_root(ctx)),
        "QUEEN_ROOT": str(ctx.queen),
        "GROK16_SG_ROOT": os.environ.get("SG_ROOT", str(ctx.queen.parent.parent)),
    }
    engine.log(f"=== queen→grok16:{tool_id} ===")
    rc = engine.run_stream(
        [sys.executable, str(script), "run", tool_id],
        env=env,
        timeout=7200,
    )
    if rc != 0:
        return ForgeResult(False, tool_id, "grok16 forge failed", rc, engine.tail_buffer())
    return ForgeResult(True, tool_id, engine.tail_buffer()[-500:])


def _run_field_cmake_sh(ctx: ForgeContext, engine: ForgeEngine, *args: str) -> ForgeResult:
    script = field_cmake_script(ctx)
    if not script.is_file():
        return ForgeResult(False, "field_cmake", f"missing {script}")
    env = {
        **ctx.env(),
        "GROK16_ROOT": str(grok16_root(ctx)),
        "QUEEN_ROOT": str(ctx.queen),
        "GROK16_FIELD_PROFILE": "queen_rtx",
        "GROK16_CMAKE_SOURCE": str(ctx.rtx),
        "GROK16_CMAKE_BUILD": str(ctx.build),
        "GROK16_BUILD_JOBS": str(ctx.jobs),
    }
    rc = engine.run_stream(["bash", str(script), *args], env=env, timeout=7200)
    if rc != 0:
        return ForgeResult(False, "field_cmake", f"field-cmake.sh {' '.join(args)} failed", rc)
    return ForgeResult(True, "field_cmake", str(ctx.build))


def field_cmake_status(ctx: ForgeContext) -> dict[str, Any]:
    script = _grok16_forge(ctx)
    if script.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(script), "status"],
                capture_output=True,
                text=True,
                timeout=30,
                env={**os.environ, "GROK16_ROOT": str(grok16_root(ctx)), "QUEEN_ROOT": str(ctx.queen)},
            )
            if proc.returncode == 0:
                doc = json.loads(proc.stdout)
                return doc.get("field_cmake") or {}
        except (json.JSONDecodeError, subprocess.TimeoutExpired):
            pass
    return {
        "grok16_root": str(grok16_root(ctx)),
        "field_cmake": str(grok16_field_cmake_path(ctx)),
        "script": str(field_cmake_script(ctx)),
        "rtx_build": str(ctx.build),
    }


def check_field_cmake_configure(ctx: ForgeContext) -> bool:
    from forge.tools import _rtx_configure_ok, _rtx_needs_ninja_migrate

    return _rtx_configure_ok(ctx) and not _rtx_needs_ninja_migrate(ctx)


def check_field_cmake_build(ctx: ForgeContext) -> bool:
    from forge.tools import check_rtx

    return check_rtx(ctx)


def run_field_cmake_configure(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    if check_field_cmake_configure(ctx):
        engine.log("field_cmake_configure — cache valid, skip")
        return ForgeResult(True, "field_cmake_configure", "cached")
    return _run_field_cmake_sh(ctx, engine, "configure")


def run_field_cmake_build(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    if not check_field_cmake_configure(ctx):
        r = run_field_cmake_configure(ctx, engine)
        if not r.ok:
            return r
    return _run_field_cmake_sh(ctx, engine, "g16-build")


def run_field_cmake(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    r = run_field_cmake_configure(ctx, engine)
    if not r.ok:
        return r
    return run_field_cmake_build(ctx, engine)


FIELD_CMAKE_TOOLS: dict[str, tuple] = {
    "field_cmake_configure": (run_field_cmake_configure, check_field_cmake_configure),
    "field_cmake_build": (run_field_cmake_build, check_field_cmake_build),
    "field_cmake": (run_field_cmake, check_field_cmake_build),
}