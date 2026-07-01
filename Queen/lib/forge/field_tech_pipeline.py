"""Field Technology v5 — optimized Queen Forge drop-in order.

Each legacy shell/binary is replaced by one native forge tool. Long toolchain
builds (gcc_build) do not block RTX when host compilers are ready.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forge.engine import ForgeContext, ForgeEngine, ForgeResult
from forge.compiler_tools import GCC_ORDER, check_gcc_build, g16_status as gcc_status
from forge.hostess_tools import probe_compilers

# One-by-one drop registry: legacy → forge tool
FIELD_TECH_DROPS: tuple[dict[str, str], ...] = (
    {"legacy": "scripts/install-inside.sh", "forge": "inside", "track": "core"},
    {"legacy": "clone-all.sh", "forge": "vendors", "track": "media-vendors"},
    {"legacy": "scripts/stage-deps-inside.sh", "forge": "deps", "track": "core"},
    {"legacy": "make Navigator/shaders", "forge": "shaders", "track": "core"},
    {"legacy": "Grok16/scripts/field-cmake.sh", "forge": "field_cmake", "track": "field-cmake"},
    {"legacy": "cmake -G Ninja (Queen glue)", "forge": "field_cmake_configure", "track": "field-cmake"},
    {"legacy": "cmake --build (Makefile)", "forge": "field_cmake_build", "track": "field-cmake"},
    {"legacy": "build.sh", "forge": "rtx", "track": "core"},
    {"legacy": "scripts/verify-queen.sh", "forge": "verify", "track": "core"},
    {"legacy": "scripts/queen-gpu-probe.sh", "forge": "gpu_probe", "track": "field-probe"},
    {"legacy": "scripts/queen-gpu-probe.sh", "forge": "compiler_probe", "track": "hostess"},
    {"legacy": "build-field.sh", "forge": "field", "track": "sovereign"},
    {"legacy": "build-ffmpeg.sh", "forge": "ffmpeg", "track": "media"},
    {"legacy": "build-ladybird.sh", "forge": "ladybird", "track": "engine"},
    {"legacy": "build-servo.sh", "forge": "servo", "track": "engine"},
    {"legacy": "host g++16", "forge": "gcc", "track": "toolchain"},
    {"legacy": "vendor/binutils", "forge": "binutils_fetch", "track": "toolchain"},
    {"legacy": "scripts/watch-build.sh", "forge": "forge_watch", "track": "operator"},
    {"legacy": "scripts/build-monitored.sh", "forge": "field_tech", "track": "operator"},
)

# Fast path: ship RTX with host or Queen GCC; toolchain prep before deps
FIELD_TECH_CORE_ORDER: list[str] = [
    "inside",
    "compiler_probe",
    "gcc_fetch",
    "gcc_prereqs",
    "gcc_configure",
    "deps",
    "shaders",
    "rtx",
    "verify",
]

# Media vendors optional — enable with QUEEN_VENDORS=1
FIELD_TECH_VENDORS_STEP = "vendors"

# Long / optional — run when QUEEN_TOOLCHAIN_BUILD=1 or queen-gcc not required yet
FIELD_TECH_TOOLCHAIN_LONG: list[str] = ["gcc_build"]

FIELD_TECH_HOSTESS: list[str] = [
    "compiler_probe",
    "gpu_probe",
    "hostess_teach",
    "textbook_zac",
    "textbook_ingest",
    "hostess_verify",
    "forge_test",
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def drops_status(ctx: ForgeContext) -> list[dict[str, Any]]:
    from forge.tools import TOOL_REGISTRY

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for drop in FIELD_TECH_DROPS:
        fid = drop["forge"]
        if fid in seen:
            continue
        seen.add(fid)
        tool = TOOL_REGISTRY.get(fid)
        rows.append({
            **drop,
            "ready": tool.check(ctx) if tool else False,
            "label": tool.label if tool else fid,
        })
    return rows


def write_drops_manifest(ctx: ForgeContext) -> Path:
    from forge.tools import TOOL_REGISTRY

    doc = {
        "schema": "field-tech-drops/v1",
        "updated": _ts(),
        "doctrine": "Every build entry routes through Queen Forge — Field Technology v5",
        "core_order": FIELD_TECH_CORE_ORDER,
        "toolchain_long": FIELD_TECH_TOOLCHAIN_LONG,
        "drops": drops_status(ctx),
        "gcc": gcc_status(ctx),
        "compilers": probe_compilers(ctx),
        "rtx_ready": TOOL_REGISTRY["rtx"].check(ctx) if "rtx" in TOOL_REGISTRY else False,
    }
    out = ctx.queen / "data" / "field-tech-drops.json"
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out


def should_run_gcc_build(ctx: ForgeContext) -> bool:
    if os.environ.get("QUEEN_SKIP_GCC_BUILD", "").strip() in ("1", "true", "yes"):
        return False
    if check_gcc_build(ctx):
        return False
    from forge.compiler_tools import g16_status, probe_compilers

    if probe_compilers(ctx).get("version_upgrade_pending"):
        return True
    if os.environ.get("QUEEN_TOOLCHAIN_BUILD", "").strip() in ("1", "true", "yes"):
        return True
    st = g16_status(ctx)
    if st.get("dumpversion") == st.get("g16_version") and st.get("engine_real"):
        return False
    return True


def gcc_toolchain_step(ctx: ForgeContext) -> str:
    """gcc_build for fresh trees; gcc_rebuild when runtime ok but version stale."""
    from forge.compiler_tools import probe_compilers

    if probe_compilers(ctx).get("version_upgrade_pending"):
        return "gcc_rebuild"
    return "gcc_build"


def field_tech_plan(ctx: ForgeContext) -> list[str]:
    """Resolved run order for field-tech core pipeline."""
    plan = list(FIELD_TECH_CORE_ORDER)
    if os.environ.get("QUEEN_VENDORS", "").strip() in ("1", "true", "yes"):
        plan.insert(plan.index("deps"), FIELD_TECH_VENDORS_STEP)
    if should_run_gcc_build(ctx):
        plan.insert(plan.index("rtx"), gcc_toolchain_step(ctx))
    if should_run_gcc_build(ctx):
        step = gcc_toolchain_step(ctx)
        rtx_i = plan.index("rtx")
        for old in ("gcc_build", "gcc_rebuild", "g16_install"):
            while old in plan:
                plan.remove(old)
        plan.insert(rtx_i, "g16_install")
        plan.insert(rtx_i, step)
    elif "g16_install" not in plan:
        plan.insert(plan.index("rtx"), "g16_install")
    return plan


def run_field_tech(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    from forge.tools import TOOL_REGISTRY

    engine.log("=== forge:field_tech — Field Technology optimized core ===")
    plan = field_tech_plan(ctx)
    engine.log(f"plan: {' → '.join(plan)}")
    results: list[dict[str, Any]] = []
    for tid in plan:
        tool = TOOL_REGISTRY.get(tid)
        if not tool:
            engine.log(f"SKIP unknown {tid}")
            continue
        if tool.check(ctx) and tid not in ("verify", "compiler_probe"):
            engine.log(f"SKIP {tid} — ready")
            results.append({"tool": tid, "skipped": True, "ok": True})
            continue
        r = tool.run(ctx, engine)
        row = r.to_dict()
        results.append(row)
        if not r.ok and tid in ("inside", "deps", "shaders", "rtx"):
            write_drops_manifest(ctx)
            return ForgeResult(
                ok=False,
                tool="field_tech",
                message=f"stopped at {tid}",
                tail=engine.tail_buffer(),
            )
    manifest = write_drops_manifest(ctx)
    engine.log(f"wrote {manifest.name}")
    ok = all(r.get("ok", r.get("skipped")) for r in results)
    return ForgeResult(
        ok=ok,
        tool="field_tech",
        message=f"{len(plan)} steps",
        tail=engine.tail_buffer(),
    )


def check_field_tech(ctx: ForgeContext) -> bool:
    from forge.tools import TOOL_REGISTRY

    for tid in ("rtx", "verify"):
        t = TOOL_REGISTRY.get(tid)
        if t and not t.check(ctx):
            return False
    return True


FIELD_TECH_TOOLS: dict[str, tuple[str, str, object, object, str | None]] = {
    "field_tech": (
        "Field Technology core pipeline (optimized order)",
        "field-tech",
        run_field_tech,
        check_field_tech,
        "build-all.sh",
    ),
}