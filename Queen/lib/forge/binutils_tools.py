"""Queen Forge — delegates field binutils to Grok16 (no redundant Queen build)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from forge.common import fail_result, ok_result
from forge.engine import ForgeContext, ForgeEngine, ForgeResult

_GROK16 = Path(os.environ.get("GROK16_ROOT", Path(__file__).resolve().parents[4] / "Grok16"))
_BINUTILS_SH = _GROK16 / "scripts" / "grok16-binutils.sh"


def _run_grok16_binutils(ctx: ForgeContext, engine: ForgeEngine, cmd: str) -> ForgeResult:
    if not _BINUTILS_SH.is_file():
        return fail_result(engine, cmd, f"missing {_BINUTILS_SH}")
    env = {**os.environ, "GROK16_ROOT": str(_GROK16), "G16_PREFIX": os.environ.get("G16_PREFIX", str(_GROK16))}
    rc = subprocess.call([str(_BINUTILS_SH), cmd], env=env)
    return ok_result(engine, cmd) if rc == 0 else fail_result(engine, cmd, f"exit {rc}", rc)


def check_binutils_fetch(ctx: ForgeContext) -> bool:
    src = _GROK16 / "vendor" / "binutils"
    return (src / ".git").is_dir() or (ctx.vendor / "binutils" / ".git").is_dir()


def run_binutils_fetch(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== queen→grok16:binutils_fetch ===")
    return _run_grok16_binutils(ctx, engine, "bootstrap")


def check_binutils_build(ctx: ForgeContext) -> bool:
    prefix = Path(os.environ.get("G16_PREFIX", _GROK16))
    return (prefix / "bin" / "g16-as").is_file() and (prefix / "bin" / "g16-objdump").is_file()


def run_binutils_build(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    return _run_grok16_binutils(ctx, engine, "bootstrap")


BINUTILS_TOOLS: dict[str, tuple[str, str, object, object, str | None]] = {
    "binutils_fetch": (
        "Grok16 field binutils fetch+build",
        "toolchain",
        run_binutils_fetch,
        check_binutils_fetch,
        None,
    ),
    "binutils_build": (
        "Grok16 field binutils install",
        "toolchain",
        run_binutils_build,
        check_binutils_build,
        None,
    ),
}