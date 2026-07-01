"""Queen Forge — GrokPy field runtime tools (native Grok VM + optional G16 CPython)."""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forge.common import fail_result, ok_result
from forge.engine import ForgeContext, ForgeEngine, ForgeResult
from forge.field_paths import sg_root

MANIFEST_NAME = "grokpy-toolchain.json"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def grokpy_root_from_sg(sg: Path) -> Path:
    env = os.environ.get("GROKPY_ROOT", os.environ.get("PYTHONG_ROOT", "")).strip()
    return Path(env).resolve() if env else (sg / "GrokPy").resolve()


def grokpy_root(ctx: ForgeContext) -> Path:
    return grokpy_root_from_sg(sg_root(ctx.queen))


def grokpy_toolchain_script(ctx: ForgeContext) -> Path:
    return grokpy_root(ctx) / "scripts/grokpy-toolchain.sh"


def grokpy_bin(ctx: ForgeContext) -> Path:
    return grokpy_root(ctx) / "bin/grokpy"


def prefix_python(ctx: ForgeContext) -> Path:
    return grokpy_root(ctx) / "prefix/bin/pythong"


def _run_sh(ctx: ForgeContext, engine: ForgeEngine, step: str, timeout: int = 7200) -> tuple[bool, str]:
    script = grokpy_toolchain_script(ctx)
    if not script.is_file():
        return False, "grokpy-toolchain.sh missing"
    env = {
        **os.environ,
        "SG_ROOT": str(sg_root(ctx.queen)),
        "QUEEN_ROOT": str(ctx.queen),
        "GROKPY_ROOT": str(grokpy_root(ctx)),
        "PYTHONG_ROOT": str(grokpy_root(ctx)),
        "GROK16_ROOT": os.environ.get("GROK16_ROOT", str(sg_root(ctx.queen) / "Grok16")),
    }
    engine.log(f"=== forge:grokpy — {step} ===")
    proc = subprocess.run(
        ["bash", str(script), step],
        cwd=str(grokpy_root(ctx)),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    tail = (proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:]
    if proc.returncode != 0:
        engine.log(f"grokpy {step} failed rc={proc.returncode}")
        engine.log(tail)
        return False, tail
    engine.log(tail[-800:])
    return True, tail


def write_manifest(ctx: ForgeContext) -> Path:
    root = grokpy_root(ctx)
    pref = prefix_python(ctx)
    ver_path = root / "data/grokpy-version.json"
    try:
        ver = json.loads(ver_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        ver = {"grokpy_version": "3.12.8-grok1"}
    ready_prefix = pref.is_file() and os.access(pref, os.X_OK)
    cpy = ""
    if ready_prefix:
        try:
            proc = subprocess.run([str(pref), "-V"], capture_output=True, text=True, timeout=10)
            cpy = (proc.stderr or proc.stdout or "").strip().split()[-1]
        except (OSError, subprocess.TimeoutExpired):
            pass
    doc = {
        "schema": "grokpy-toolchain/v1",
        "updated": _ts(),
        "ready_grokpy": grokpy_bin(ctx).is_file(),
        "ready_prefix": ready_prefix,
        "ready_runtime": grokpy_bin(ctx).is_file(),
        "grok_vm_ready": True,
        "bootstrap": not ready_prefix,
        "toolchain": {
            "product": "GrokPy",
            "grokpy_version": ver.get("grokpy_version"),
            "cpython_version": cpy or "bootstrap",
            "prefix": str(root / "prefix"),
            "grokpy_root": str(root),
            "profile": os.environ.get("GROKPY_PROFILE", "field_opt"),
            "build_with": "Grok16/g16",
            "driver": str(grokpy_bin(ctx)),
            "bytecode_magic": "GROKPY12",
        },
        "field_mandate": {
            "id": "GROKPY_FIELD_MANDATE_v1",
            "mandate_json": str(root / "data/grokpy-field-mandate.json"),
        },
        "hostess7": {
            "lane": "hostess_brain",
            "truth_floor": 58,
            "neural_stack": str(sg_root(ctx.queen) / "Hostess7/data/hostess7-neural-stack.json"),
        },
    }
    out = ctx.queen / "data" / MANIFEST_NAME
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    (root / "data" / MANIFEST_NAME).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    compat = {**doc, "schema": "pythong-toolchain/v1", "ready_pythong": doc["ready_runtime"]}
    (ctx.queen / "data" / "pythong-toolchain.json").write_text(json.dumps(compat, indent=2) + "\n", encoding="utf-8")
    return out


def check_grokpy_fetch(ctx: ForgeContext) -> bool:
    return (grokpy_root(ctx) / "vendor/cpython/.git").is_dir()


def run_grokpy_fetch(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    ok, tail = _run_sh(ctx, engine, "fetch", timeout=1800)
    if not ok:
        return fail_result(engine, "grokpy_fetch", tail)
    return ok_result(engine, "grokpy_fetch", "vendor/cpython")


def check_grokpy_build(ctx: ForgeContext) -> bool:
    return prefix_python(ctx).is_file()


def run_grokpy_configure(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    if not check_grokpy_fetch(ctx):
        r = run_grokpy_fetch(ctx, engine)
        if not r.ok:
            return r
    ok, tail = _run_sh(ctx, engine, "configure", timeout=3600)
    if not ok:
        return fail_result(engine, "grokpy_configure", tail)
    return ok_result(engine, "grokpy_configure")


def run_grokpy_build(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    ok, tail = _run_sh(ctx, engine, "build", timeout=7200)
    if not ok:
        return fail_result(engine, "grokpy_build", tail)
    write_manifest(ctx)
    return ok_result(engine, "grokpy_build", str(prefix_python(ctx)))


def check_grokpy_probe(ctx: ForgeContext) -> bool:
    return grokpy_bin(ctx).is_file()


def run_grokpy_probe(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    ok, _ = _run_sh(ctx, engine, "probe", timeout=120)
    write_manifest(ctx)
    st = json.loads((ctx.queen / "data" / MANIFEST_NAME).read_text(encoding="utf-8"))
    return ok_result(engine, "grokpy_probe", st.get("toolchain", {}).get("grokpy_version", ""))


def run_grokpy_rebuild(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    ok, tail = _run_sh(ctx, engine, "rebuild", timeout=14400)
    if not ok:
        return fail_result(engine, "grokpy_rebuild", tail)
    write_manifest(ctx)
    return ok_result(engine, "grokpy_rebuild", str(prefix_python(ctx)))


def run_grokpy(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    write_manifest(ctx)
    if not check_grokpy_build(ctx):
        for step, runner in (
            ("grokpy_fetch", run_grokpy_fetch),
            ("grokpy_configure", run_grokpy_configure),
            ("grokpy_build", run_grokpy_build),
        ):
            r = runner(ctx, engine)
            if not r.ok:
                return r
    return run_grokpy_probe(ctx, engine)


GROKPY_TOOLS: dict[str, tuple[str, str, object, object, str | None]] = {
    "grokpy_fetch": ("Fetch CPython vendor for GrokPy prefix", "runtime", run_grokpy_fetch, check_grokpy_fetch, None),
    "grokpy_configure": ("Configure GrokPy prefix with G16", "runtime", run_grokpy_configure, check_grokpy_build, None),
    "grokpy_build": ("Build + install GrokPy CPython prefix", "runtime", run_grokpy_build, check_grokpy_build, None),
    "grokpy_probe": ("Probe GrokPy manifest + Grok VM", "runtime", run_grokpy_probe, check_grokpy_probe, None),
    "grokpy_rebuild": ("Full GrokPy prefix rebuild", "runtime", run_grokpy_rebuild, check_grokpy_build, "grokpy_build"),
    "grokpy": ("GrokPy pipeline (fetch→build→probe)", "runtime", run_grokpy, check_grokpy_probe, None),
}

GROKPY_ORDER = ["grokpy_fetch", "grokpy_configure", "grokpy_build", "grokpy_probe"]