"""Shared forge helpers."""
from __future__ import annotations

import os
from pathlib import Path

from forge.engine import ForgeContext, ForgeEngine, ForgeResult


def ok_result(engine: ForgeEngine, tool: str, msg: str = "") -> ForgeResult:
    return ForgeResult(ok=True, tool=tool, message=msg, tail=engine.tail_buffer())


def fail_result(engine: ForgeEngine, tool: str, msg: str, rc: int = 1) -> ForgeResult:
    return ForgeResult(ok=False, tool=tool, message=msg, returncode=rc, tail=engine.tail_buffer())


def rtx_bin(ctx: ForgeContext) -> Path | None:
    for p in (ctx.build / "bin/Linux/queen-browser", ctx.build / "bin/queen-browser"):
        if p.is_file():
            return p
    return None


def rtx_ready(ctx: ForgeContext) -> bool:
    p = rtx_bin(ctx)
    return p is not None and os.access(p, os.X_OK)