"""Queen Forge — pythong aliases → GrokPy (compat layer)."""
from __future__ import annotations

from pathlib import Path

from forge.engine import ForgeContext, ForgeEngine, ForgeResult
from forge.grokpy_tools import (
    GROKPY_ORDER,
    GROKPY_TOOLS,
    grokpy_bin,
    grokpy_root,
    grokpy_root_from_sg,
    grokpy_toolchain_script,
    prefix_python,
    run_grokpy,
    run_grokpy_build,
    run_grokpy_configure,
    run_grokpy_fetch,
    run_grokpy_probe,
    run_grokpy_rebuild,
    write_manifest,
    check_grokpy_build,
    check_grokpy_fetch,
    check_grokpy_probe,
)

MANIFEST_NAME = "pythong-toolchain.json"
PYTHONG_CC = "grokpy"

pythong_root_from_sg = grokpy_root_from_sg
pythong_root = grokpy_root
pythong_toolchain_script = grokpy_toolchain_script
pythong_bin = grokpy_bin

check_pythong_fetch = check_grokpy_fetch
check_pythong_build = check_grokpy_build
check_pythong_probe = check_grokpy_probe
run_pythong_fetch = run_grokpy_fetch
run_pythong_configure = run_grokpy_configure
run_pythong_build = run_grokpy_build
run_pythong_probe = run_grokpy_probe
run_pythong_rebuild = run_grokpy_rebuild
run_pythong = run_grokpy

PYTHONG_TOOLS: dict[str, tuple[str, str, object, object, str | None]] = {
    **{k.replace("grokpy", "pythong"): (v[0].replace("GrokPy", "GrokPy/pythong"), *v[1:]) for k, v in GROKPY_TOOLS.items()},
    **GROKPY_TOOLS,
}

PYTHONG_ORDER = GROKPY_ORDER