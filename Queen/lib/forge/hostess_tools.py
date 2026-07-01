#!/usr/bin/env pythong
"""Queen Forge — Hostess7 redata, textbook ZAC, compiler probe, QA tests."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from forge.common import fail_result, ok_result
from forge.engine import ForgeContext, ForgeEngine, ForgeResult
from forge.field_paths import sg_root


def _hostess_root(ctx: ForgeContext) -> Path:
    env = os.environ.get("HOSTESS7_ROOT")
    if env:
        return Path(env)
    return sg_root(ctx.queen) / "Hostess7"


def _textbook_root(ctx: ForgeContext) -> Path:
    return sg_root(ctx.queen) / "NewLatest" / "Textbook"


def _run_py(engine: ForgeEngine, script: Path, *args: str, cwd: Path | None = None) -> tuple[int, str]:
    if not script.is_file():
        engine.log(f"MISSING {script}")
        return 127, ""
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(cwd or script.parent),
        capture_output=True,
        text=True,
        timeout=600,
    )
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-3000:]
    if tail:
        for line in tail.splitlines()[-20:]:
            engine.log(line)
    return proc.returncode, tail


def _run_h7sh(engine: ForgeEngine, h7: Path, cmd: str, *args: str) -> tuple[int, str]:
    sh = h7 / "Hostess7.sh"
    if not sh.is_file():
        return 127, "Hostess7.sh missing"
    proc = subprocess.run(
        [str(sh), cmd, *args],
        cwd=str(h7),
        capture_output=True,
        text=True,
        timeout=300,
    )
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-3000:]
    return proc.returncode, tail


def probe_compilers(ctx: ForgeContext) -> dict[str, Any]:
    from forge.compiler_tools import probe_compilers as _probe
    return _probe(ctx)


def check_compiler_probe(ctx: ForgeContext) -> bool:
    from forge.compiler_tools import check_compiler_probe as _check
    p = probe_compilers(ctx)
    return _check(ctx) and p["ready_shaders"]


def run_compiler_probe(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    from forge.compiler_tools import run_compiler_probe as _run
    r = _run(ctx, engine)
    if r.ok and not probe_compilers(ctx)["ready_shaders"]:
        return fail_result(engine, "compiler_probe", "glslc or QueenBoot.spv required")
    return r


def check_hostess_teach(ctx: ForgeContext) -> bool:
    h7 = _hostess_root(ctx)
    return (h7 / "cache" / "fieldstorage" / "brain" / "sdf" / "queen_redata_brief.json").is_file()


def run_hostess_teach(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:hostess_teach — Queen comfort + build tools ===")
    bridge = ctx.queen / "lib" / "queen-hostess-brain.py"
    if bridge.is_file():
        rc, _ = _run_py(engine, bridge, "teach", cwd=ctx.queen)
        if rc == 0:
            return ok_result(engine, "hostess_teach")
    h7 = _hostess_root(ctx)
    rc, _ = _run_py(engine, h7 / "scripts" / "field_queen_redata_teach.py", cwd=h7)
    return ok_result(engine, "hostess_teach") if rc == 0 else fail_result(engine, "hostess_teach", "teach failed", rc)


def check_hostess_verify(ctx: ForgeContext) -> bool:
    stamp = _hostess_root(ctx) / "cache" / "fieldstorage" / "brain" / "sdf" / "truth_filter.jsonl"
    return stamp.is_file()


def run_hostess_verify(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:hostess_verify — QA + redata ===")
    h7 = _hostess_root(ctx)
    failures: list[str] = []
    for script, label in (
        ("scripts/qa_redata_truth_test.py", "qa_redata_truth"),
        ("scripts/qa_sdf_redata_test.py", "qa_sdf_redata"),
    ):
        rc, tail = _run_py(engine, h7 / script, cwd=h7)
        if rc != 0:
            failures.append(label)
            engine.log(f"FAIL {label}")
    seg_dir = h7 / "cache" / "fieldstorage" / "brain" / "sdf" / "segments"
    if seg_dir.is_dir() and any(seg_dir.glob("seg-*.json")):
        rc, _ = _run_h7sh(engine, h7, "sdf-verify-redata")
        if rc != 0:
            failures.append("sdf-verify-redata")
    else:
        engine.log("SKIP sdf-verify-redata — no segments in Hostess7 brain (run textbook_zac or sdf-segment)")
    if failures:
        return fail_result(engine, "hostess_verify", ", ".join(failures))
    return ok_result(engine, "hostess_verify")


def check_textbook_zac(ctx: ForgeContext) -> bool:
    zac = _textbook_root(ctx) / "field-technology-v5.zac"
    return zac.is_file() and zac.stat().st_size > 1000


def run_textbook_zac(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:textbook_zac — Field Technology monolith ===")
    tb = _textbook_root(ctx)
    build = tb / "build-field-technology-zac.py"
    if not build.is_file():
        return fail_result(engine, "textbook_zac", f"missing {build}")
    if check_textbook_zac(ctx) and os.environ.get("QUEEN_FORGE_REBUILD_TEXTBOOK", "0") != "1":
        engine.log("ZAC present — verify-only")
        rc, _ = _run_py(engine, build, "--verify-only", cwd=tb)
    else:
        rc, _ = _run_py(engine, build, cwd=tb)
    return ok_result(engine, "textbook_zac") if rc == 0 else fail_result(engine, "textbook_zac", "build/verify failed", rc)


def check_forge_test(ctx: ForgeContext) -> bool:
    report = ctx.queen / "data" / "forge-test-report.json"
    if not report.is_file():
        return False
    try:
        doc = json.loads(report.read_text(encoding="utf-8"))
        return doc.get("ok") is True
    except (OSError, json.JSONDecodeError):
        return False


def check_textbook_ingest(ctx: ForgeContext) -> bool:
    seg = _hostess_root(ctx) / "cache" / "fieldstorage" / "brain" / "sdf" / "segments"
    return seg.is_dir() and len(list(seg.glob("seg-*.json"))) >= 100


def run_textbook_ingest(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:textbook_ingest — staging → Hostess7 brain ===")
    bridge = ctx.queen / "lib" / "queen-hostess-brain.py"
    rc, tail = _run_py(engine, bridge, "ingest-textbook", cwd=ctx.queen)
    if rc != 0:
        return fail_result(engine, "textbook_ingest", "ingest failed", rc)
    rc, _ = _run_h7sh(engine, _hostess_root(ctx), "sdf-verify-redata")
    return ok_result(engine, "textbook_ingest") if rc == 0 else fail_result(engine, "textbook_ingest", "verify-redata failed", rc)


def _final_eye_root(ctx: ForgeContext) -> Path:
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env and Path(env).is_dir():
        return Path(env)
    sg = sg_root(ctx.queen)
    fe = sg / "Final_Eye"
    if (fe / "zocr_product.py").is_file() or (fe / "VERSION").is_file():
        return fe
    zocr_env = os.environ.get("ZOCR_ROOT", "").strip()
    if zocr_env and Path(zocr_env).is_dir():
        return Path(zocr_env)
    zocr = sg / "ZOCR"
    if (zocr / "zocr_product.py").is_file():
        return zocr
    return fe


def _final_ear_root(ctx: ForgeContext) -> Path:
    env = os.environ.get("FINAL_EAR_ROOT", "").strip()
    if env and Path(env).is_dir():
        return Path(env)
    sg = sg_root(ctx.queen)
    ear = sg / "Final_Ear"
    if (ear / "zocr_product.py").is_file():
        return ear
    return ear


def check_queen_zocr(ctx: ForgeContext) -> bool:
    fe = _final_eye_root(ctx)
    smoke = fe / "queen_browser_smoke.py"
    out = fe / "out"
    return smoke.is_file() and out.is_dir()


def check_queen_eyeball(ctx: ForgeContext) -> bool:
    bridge = ctx.queen / "lib" / "queen-eyeball.py"
    product = _final_eye_root(ctx) / "zocr_product.py"
    return bridge.is_file() and product.is_file()


def run_queen_eyeball(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:queen_eyeball — Final_Eye verify for Hostess 7 ===")
    bridge = ctx.queen / "lib" / "queen-eyeball.py"
    if not bridge.is_file():
        return fail_result(engine, "queen_eyeball", "queen-eyeball.py missing")
    lib = str(ctx.queen / "lib")
    py = lib + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
    proc = subprocess.run(
        [sys.executable, str(bridge), "verify"],
        cwd=str(ctx.queen),
        capture_output=True,
        text=True,
        timeout=240,
        env={
            **os.environ,
            "PYTHONPATH": py,
            "NEXUS_INSTALL_ROOT": str(ctx.queen),
            "SG_ROOT": str(sg_root(ctx.queen)),
            "FINAL_EYE_ROOT": str(_final_eye_root(ctx)),
        },
    )
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-3000:]
    for line in tail.splitlines()[-12:]:
        engine.log(line)
    try:
        doc = json.loads(proc.stdout)
        ok = bool(doc.get("ok"))
    except json.JSONDecodeError:
        ok = proc.returncode == 0
    return ok_result(engine, "queen_eyeball", "assistive verify") if ok else fail_result(
        engine, "queen_eyeball", tail[-200:], proc.returncode,
    )


def check_queen_earball(ctx: ForgeContext) -> bool:
    bridge = ctx.queen / "lib" / "queen-earball.py"
    product = _final_ear_root(ctx) / "zocr_product.py"
    return bridge.is_file() and product.is_file()


def run_queen_earball(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:queen_earball — Final_Ear verify for Hostess 7 ===")
    bridge = ctx.queen / "lib" / "queen-earball.py"
    if not bridge.is_file():
        return fail_result(engine, "queen_earball", "queen-earball.py missing")
    lib = str(ctx.queen / "lib")
    py = lib + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else "")
    proc = subprocess.run(
        [sys.executable, str(bridge), "verify"],
        cwd=str(ctx.queen),
        capture_output=True,
        text=True,
        timeout=240,
        env={
            **os.environ,
            "PYTHONPATH": py,
            "NEXUS_INSTALL_ROOT": str(ctx.queen),
            "SG_ROOT": str(sg_root(ctx.queen)),
            "FINAL_EAR_ROOT": str(_final_ear_root(ctx)),
            "FINAL_EYE_ROOT": str(_final_eye_root(ctx)),
        },
    )
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-3000:]
    for line in tail.splitlines()[-12:]:
        engine.log(line)
    try:
        doc = json.loads(proc.stdout)
        ok = bool(doc.get("ok"))
    except json.JSONDecodeError:
        ok = proc.returncode == 0
    return ok_result(engine, "queen_earball", "assistive verify") if ok else fail_result(
        engine, "queen_earball", tail[-200:], proc.returncode,
    )


def run_queen_zocr(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:queen_zocr — browser smoke → Final_Eye/out ===")
    bridge = ctx.queen / "lib" / "queen-zocr.py"
    if not bridge.is_file():
        return fail_result(engine, "queen_zocr", "queen-zocr.py missing")
    proc = subprocess.run(
        [sys.executable, str(bridge), "browser-smoke"],
        cwd=str(ctx.queen),
        capture_output=True,
        text=True,
        timeout=120,
        env={
            **os.environ,
            "NEXUS_INSTALL_ROOT": str(ctx.queen),
            "SG_ROOT": str(sg_root(ctx.queen)),
            "FINAL_EYE_ROOT": str(_final_eye_root(ctx)),
        },
    )
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-3000:]
    for line in tail.splitlines()[-15:]:
        engine.log(line)
    try:
        doc = json.loads(proc.stdout)
        ok = doc.get("ok") or doc.get("looks_like_engine") or doc.get("looks_like_browser")
    except json.JSONDecodeError:
        ok = proc.returncode == 0
    zocr_root = _final_eye_root(ctx) / "out"
    engine.log(f"Final_Eye out: {zocr_root}")
    return ok_result(engine, "queen_zocr", str(zocr_root)) if ok else fail_result(engine, "queen_zocr", tail[-200:], proc.returncode)


def run_forge_test(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    """Port + test all forge-routed tools (compilers, hostess, textbook, doctrine)."""
    engine.log("=== forge:forge_test — full toolchain matrix ===")
    results: list[dict[str, Any]] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        results.append({"tool": name, "ok": ok, "detail": detail[:200]})
        engine.log(f"{'OK' if ok else 'FAIL'}: {name}" + (f" — {detail[:80]}" if detail else ""))

    compilers = probe_compilers(ctx)
    record("compiler_probe", compilers["ready_rtx"], f"{len(compilers['found'])} bins")
    record("shader_toolchain", compilers["ready_shaders"])

    root = ctx.queen
    for label, path in (
        ("queen-brain-manifest", root / "data/queen-brain-manifest.json"),
        ("queen-hostess-brain", root / "lib/queen-hostess-brain.py"),
        ("queen-forge", root / "lib/queen-forge.py"),
        ("Hostess7.sh", _hostess_root(ctx) / "Hostess7.sh"),
        ("textbook_build", _textbook_root(ctx) / "build-field-technology-zac.py"),
    ):
        record(label, path.is_file(), str(path))

    bridge = root / "lib" / "queen-hostess-brain.py"
    if bridge.is_file():
        rc, _ = _run_py(engine, bridge, "json", cwd=root)
        record("queen_hostess_brain_json", rc == 0)

    h7 = _hostess_root(ctx)
    for script in ("qa_redata_truth_test.py", "qa_sdf_redata_test.py"):
        p = h7 / "scripts" / script
        if p.is_file():
            rc, _ = _run_py(engine, p, cwd=h7)
            record(script.replace(".py", ""), rc == 0)

    tb = _textbook_root(ctx)
    if (tb / "field-technology-v5.zac").is_file():
        rc, _ = _run_py(engine, tb / "build-field-technology-zac.py", "--verify-only", cwd=tb)
        record("textbook_zac_verify", rc == 0)
    else:
        record("textbook_zac_verify", False, "zac missing — run forge textbook_zac")

    record("textbook_ingest", check_textbook_ingest(ctx), "Hostess7 brain segments")
    record("final_eye_sink", (_final_eye_root(ctx) / "zocr.py").is_file())
    zocr_bridge = root / "lib" / "queen-zocr.py"
    record("queen_zocr_bridge", zocr_bridge.is_file())
    eyeball_bridge = root / "lib" / "queen-eyeball.py"
    record("queen_eyeball_bridge", eyeball_bridge.is_file())
    earball_bridge = root / "lib" / "queen-earball.py"
    record("queen_earball_bridge", earball_bridge.is_file())
    record("final_ear_sink", (_final_ear_root(ctx) / "zocr_ear.py").is_file())

    from forge.tools import TOOL_REGISTRY
    for tid in ("inside", "shaders", "verify"):
        t = TOOL_REGISTRY.get(tid)
        if t:
            record(f"check_{tid}", t.check(ctx))

    ok = all(r["ok"] for r in results)
    report = {
        "ok": ok,
        "compilers": compilers,
        "results": results,
        "failed": [r["tool"] for r in results if not r["ok"]],
    }
    out = root / "data" / "forge-test-report.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    engine.log(f"=== forge_test {'PASSED' if ok else 'FAILED'}: {out} ===")
    msg = json.dumps({"report_path": str(out), "failed": report["failed"]})
    return ok_result(engine, "forge_test", msg) if ok else fail_result(engine, "forge_test", msg)


HOSTESS_TOOLS: dict[str, tuple[str, str, Any, Any, str | None]] = {
    "compiler_probe": ("Probe G16 + host tools → g16-toolchain.json", "hostess", run_compiler_probe, check_compiler_probe, None),
    "hostess_teach": ("Teach Hostess Queen redata + build tools", "hostess", run_hostess_teach, check_hostess_teach, "Hostess7.sh queen-teach-redata"),
    "textbook_ingest": ("Ingest textbook SDF brain into Hostess7", "hostess", run_textbook_ingest, check_textbook_ingest, "lib/queen-hostess-brain.py ingest-textbook"),
    "hostess_verify": ("QA redata truth + sdf verify", "hostess", run_hostess_verify, check_hostess_verify, "Hostess7.sh sdf-verify-redata"),
    "textbook_zac": ("Field Technology ZAC monolith build/verify", "hostess", run_textbook_zac, check_textbook_zac, "NewLatest/Textbook/build-field-technology-zac.py"),
    "queen_zocr": ("Browser smoke OCR → Final_Eye/out", "hostess", run_queen_zocr, check_queen_zocr, "lib/queen-zocr.py browser-smoke"),
    "queen_eyeball": ("Final_Eye assist verify — offense mesh + Hostess 7", "hostess", run_queen_eyeball, check_queen_eyeball, "lib/queen-eyeball.py verify"),
    "queen_earball": ("Final_Ear assist verify — truth filter + Hostess 7", "hostess", run_queen_earball, check_queen_earball, "lib/queen-earball.py verify"),
    "forge_test": ("Test all ported forge + hostess tools", "hostess", run_forge_test, check_forge_test, "lib/queen-forge.py run forge_test"),
}

HOSTESS_ORDER = [
    "compiler_probe", "hostess_teach", "textbook_zac", "textbook_ingest",
    "hostess_verify", "queen_zocr", "queen_eyeball", "queen_earball", "forge_test",
]