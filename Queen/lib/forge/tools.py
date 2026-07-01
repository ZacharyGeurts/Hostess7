"""Queen Forge tools — every build step native inside Queen."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from forge.common import fail_result, ok_result, rtx_bin, rtx_ready
from forge.field_paths import sg_root
from forge.engine import ForgeContext, ForgeEngine, ForgeResult, ForgeTool
from forge.field_tools import FIELD_ORDER, FIELD_TOOLS
from forge.binutils_tools import BINUTILS_TOOLS
from forge.field_tech_pipeline import FIELD_TECH_CORE_ORDER, FIELD_TECH_TOOLS, field_tech_plan
from forge.compiler_tools import (
    GCC_TOOLS,
    cmake_init_cache_args,
    field_cmake_script,
    grok16_field_cmake_path,
    grok16_root,
    queen_g16_bin,
)
from forge.grokpy_tools import GROKPY_TOOLS
from forge.pythong_tools import PYTHONG_TOOLS
from forge.hostess_tools import HOSTESS_ORDER, HOSTESS_TOOLS
from forge.operator_tools import OPERATOR_TOOLS
from forge.probe_tools import PROBE_TOOLS
from forge.field_cmake_tools import FIELD_CMAKE_TOOLS

if TYPE_CHECKING:
    pass

NATIVE_LIBS = {
    "queen-forge.py",
    "queen-build.py",
    "grok-build-bridge.py",
    "queen-field-boot.py",
    "queen-hostess-brain.py",
}


_ok = ok_result
_fail = fail_result


# ── inside ────────────────────────────────────────────────────────────────────

def check_inside(ctx: ForgeContext) -> bool:
    return (ctx.queen / ".queen-inside").is_file() and (ctx.queen / "panel").exists()


def run_inside(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:inside — install Queen slice ===")
    nl, root = ctx.nl, ctx.queen

    engine.link_or_copy(nl / "panel", root / "panel")

    (root / "data").mkdir(parents=True, exist_ok=True)
    for f in ("field-queen-gates-seed.json", "queen-angel-mandate.json", "hostess7-angel-mandate.json"):
        src = nl / "data" / f
        if src.is_file():
            dst = root / "data" / f
            if not dst.exists():
                shutil.copy2(src, dst)
                engine.log(f"  copy data/{f}")

    manifest = root / "plugins/builtin-manifest.json"
    dst_lib = root / "lib"
    dst_lib.mkdir(parents=True, exist_ok=True)
    mods: set[str] = set()
    if manifest.is_file():
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        for p in doc.get("plugins") or []:
            m = p.get("module")
            if m:
                mods.add(m)
    extras = [
        "threat-panel-http.py", "threat-panel.sh", "nexus-common.sh",
        "connection-gatekeeper.py", "hostess7-command.py", "hostess7-autonomous.py",
        "field-queen-browser.py", "panel-browser.sh",
        "field-host-desktop.py", "field-underlay-surface.py", "field-host-freeze.py",
        "queen-panel-open.py", "field-queen-browser-open.py",
        "grok-build-bridge.py", "queen-build.py", "queen-field-boot.py", "queen-forge.py",
        "queen-hostess-brain.py", "queen-zocr.py",
    ]
    for m in sorted(mods | set(extras)):
        native = dst_lib / m
        if native.is_file() and m in NATIVE_LIBS:
            engine.log(f"  ok native lib/{m}")
            continue
        src = nl / "lib" / m
        dst = dst_lib / m
        if not src.is_file():
            if native.is_file():
                engine.log(f"  ok lib/{m}")
                continue
            engine.log(f"  warn missing {src}")
            continue
        if dst.exists() or dst.is_symlink():
            engine.log(f"  ok lib/{m}")
            continue
        dst.symlink_to(src.resolve())
        engine.log(f"  link lib/{m}")

    for script in ("queen-forge.py", "queen-build.py"):
        p = dst_lib / script
        if p.is_file():
            p.chmod(p.stat().st_mode | 0o111)

    engine.link_or_copy(nl / "config", root / "config") or (root / "config").mkdir(exist_ok=True)
    (root / "engine").mkdir(parents=True, exist_ok=True)
    rtx_dst = root / "engine/AMOURANTHRTX"
    if not (rtx_dst.is_symlink() or rtx_dst.is_dir()):
        rtx_dst.symlink_to((nl / "AMOURANTHRTX").resolve())
        engine.log(f"link {rtx_dst}")

    # Active Hostess 7 (smart brain) lives inside Queen — symlink, never a stale copy.
    h7_src = sg_root(root) / "Hostess7"
    h7_dst = root / "hostess7"
    if h7_src.is_dir():
        if h7_dst.is_symlink() or h7_dst.is_dir():
            if h7_dst.is_symlink() and h7_dst.resolve() == h7_src.resolve():
                engine.log(f"  ok hostess7 → {h7_src}")
            elif h7_dst.is_dir() and not h7_dst.is_symlink():
                engine.log(f"  ok hostess7/ (materialized)")
            else:
                if h7_dst.is_dir():
                    shutil.rmtree(h7_dst)
                else:
                    h7_dst.unlink(missing_ok=True)
                h7_dst.symlink_to(h7_src.resolve())
                engine.log(f"  link hostess7 → {h7_src}")
        else:
            h7_dst.symlink_to(h7_src.resolve())
            engine.log(f"  link hostess7 → {h7_src}")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    (root / ".queen-inside").write_text(
        f"QUEEN_INSIDE=1\nQUEEN_ROOT={root}\nNEXUS_INSTALL_ROOT={root}\n"
        f"HOSTESS7_ROOT={h7_dst if h7_dst.exists() else h7_src}\nSTAGED={stamp}\nFORGE=1\n",
        encoding="utf-8",
    )
    engine.log(f"=== inside ready: {root} (Queen inside Queen, Hostess7 inside) ===")
    return _ok(engine, "inside", str(root))


# ── vendors ─────────────────────────────────────────────────────────────────

def check_vendors(ctx: ForgeContext) -> bool:
    return (ctx.vendor / "ffmpeg/.git").is_dir()


def _clone(engine: ForgeEngine, ctx: ForgeContext, name: str, url: str, extra: list[str] | None = None) -> bool:
    dest = ctx.vendor / name
    if (dest / ".git").is_dir():
        engine.log(f"[forge-clone] {name}: pull")
        engine.run(["git", "-C", str(dest), "pull", "--ff-only"], check=False)
        return True
    engine.log(f"[forge-clone] {name}: clone {url}")
    ctx.vendor.mkdir(parents=True, exist_ok=True)
    cmd = ["git", "clone", "--depth", os.environ.get("QUEEN_CLONE_DEPTH", "1")]
    if extra:
        cmd.extend(extra)
    cmd.extend([url, str(dest)])
    return engine.run(cmd).returncode == 0


def run_vendors(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:vendors — clone millennium vendors ===")
    ctx.queen.joinpath("assets/shaders/compute").mkdir(parents=True, exist_ok=True)

    ok = _clone(engine, ctx, "ffmpeg", "https://github.com/FFmpeg/FFmpeg.git")
    ok = _clone(engine, ctx, "ladybird", "https://github.com/LadybirdBrowser/ladybird.git",
                ["--recursive", "--shallow-submodules"]) and ok
    ok = _clone(engine, ctx, "servo", "https://github.com/servo/servo.git") and ok

    ammo = ctx.rtx
    if (ammo / "Navigator/shaders/compute").is_dir():
        inc_dir = ctx.queen / "shaders/compute/inc"
        inc_dir.mkdir(parents=True, exist_ok=True)
        for inc in ("rtx_font_render.inc", "aos_sdf.inc", "aos_taskbar_layout.inc"):
            src = ammo / "Navigator/shaders/compute" / inc
            if src.is_file():
                shutil.copy2(src, inc_dir / inc)
        spv = ammo / "assets/shaders/compute/aos_load.spv"
        if spv.is_file():
            shutil.copy2(spv, ctx.queen / "assets/shaders/compute/aos_load.spv")
        engine.log("[forge-clone] AMOURANTHRTX shader assets synced")

    run_inside(ctx, engine)
    return _ok(engine, "vendors") if ok else _fail(engine, "vendors", "clone failed")


# ── deps ──────────────────────────────────────────────────────────────────────

def _vendor_dep_ok(ctx: ForgeContext, name: str) -> bool:
    p = ctx.deps / name
    try:
        return p.exists() and (p.resolve() / "CMakeLists.txt").is_file()
    except OSError:
        return False


def check_deps(ctx: ForgeContext) -> bool:
    required = ("glm", "sdl3", "sdl3_image", "sdl3_mixer", "sdl3_ttf", "tinyobjloader")
    return all(_vendor_dep_ok(ctx, n) for n in required)


def run_deps(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:deps — stage inside vendor cache ===")
    ctx.deps.mkdir(parents=True, exist_ok=True)
    names = [
        ("sdl3", "sdl3-src"),
        ("sdl3_image", "sdl3_image-src"),
        ("sdl3_mixer", "sdl3_mixer-src"),
        ("sdl3_ttf", "sdl3_ttf-src"),
        ("glm", "glm-src"),
        ("tinyobjloader", "tinyobjloader-src"),
    ]
    staged = sum(1 for n, s in names if engine.symlink_dep(n, s))
    if staged == 0:
        engine.log("No cached _deps — rtx_fetch will populate on first configure.")
    engine.log(f"=== deps ready: {ctx.deps} ({staged} linked) ===")
    return _ok(engine, "deps")


# ── shaders ───────────────────────────────────────────────────────────────────

def check_shaders(ctx: ForgeContext) -> bool:
    for p in (
        ctx.queen / "assets/shaders/compute/QueenBoot.spv",
        ctx.rtx / "assets/shaders/compute/QueenBoot.spv",
    ):
        if p.is_file():
            return True
    return False


def run_shaders(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:shaders — QueenBoot SPIR-V ===")
    rtx = ctx.rtx
    shader_dir = rtx / "Navigator/shaders"
    queen_boot = ctx.queen / "shaders/compute/QueenBoot.comp"
    dst_comp = shader_dir / "compute/QueenBoot.comp"
    if queen_boot.is_file() and not dst_comp.is_file():
        dst_comp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(queen_boot, dst_comp)
        engine.log(f"copied QueenBoot.comp → {dst_comp}")

    if not engine.which("glslc"):
        engine.log("glslc missing — using prebuilt SPIR-V if present")
        return _ok(engine, "shaders", "prebuilt")

    makefile = shader_dir / "Makefile"
    if makefile.is_file():
        rc = engine.run_stream(
            ["make", "-C", str(shader_dir), f"-j{ctx.jobs}"],
            cwd=shader_dir,
        )
        if rc != 0:
            return _fail(engine, "shaders", "make failed", rc)
    elif dst_comp.is_file():
        out = rtx / "assets/shaders/compute/QueenBoot.spv"
        out.parent.mkdir(parents=True, exist_ok=True)
        rc = engine.run_stream([
            "glslc", "-I", str(shader_dir / "compute"),
            "-g", "-O", "--target-spv=spv1.6", "--target-env=vulkan1.4",
            "-fshader-stage=comp", str(dst_comp), "-o", str(out),
        ])
        if rc != 0:
            return _fail(engine, "shaders", "glslc failed", rc)
    engine.log("=== shaders ready ===")
    return _ok(engine, "shaders")


# ── rtx ───────────────────────────────────────────────────────────────────────

def check_rtx(ctx: ForgeContext) -> bool:
    return rtx_ready(ctx) and not _rtx_sources_stale(ctx)


_rtx_bin = rtx_bin


def run_rtx_fetch(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    if check_deps(ctx):
        engine.log("forge:rtx_fetch — vendor/deps staged, skip network fetch")
        return _ok(engine, "rtx_fetch", "skipped")
    if (ctx.build / "_deps/glm-src").is_dir():
        engine.log("forge:rtx_fetch — _deps cache present, skip fetch")
        return _ok(engine, "rtx_fetch", "skipped")
    engine.log("=== forge:rtx_fetch — one-time dep populate ===")
    if not ctx.preset.is_file():
        return _fail(engine, "rtx_fetch", f"missing preset {ctx.preset}")
    rc = engine.run_stream([
        "cmake", "-S", str(ctx.rtx), "-B", str(ctx.build),
        "-C", str(ctx.preset),
        "-DQUEEN_DEPS_INSIDE=OFF",
        "-DFETCH_SDL3_IMAGE=ON", "-DFETCH_SDL3_MIXER=ON", "-DFETCH_SDL3_TTF=ON",
        "-DFETCH_SDL3=ON", "-DQUEEN_USE_SYSTEM_SDL3=OFF",
    ])
    if rc != 0:
        return _fail(engine, "rtx_fetch", "cmake fetch failed", rc)
    _wipe_cmake_cache(ctx.build)
    engine.log("forge:rtx_fetch — cleared cmake cache (keep _deps; avoids compiler reconfigure loop)")
    run_deps(ctx, engine)
    return _ok(engine, "rtx_fetch")


def _rtx_configure_defines(ctx: ForgeContext | None = None) -> list[str]:
    """Command-line -D pins beat stale CMakeCache (avoids SDL FetchContent re-run loop)."""
    out = [
        "-DQUEEN_BROWSER_BUILD=ON",
        "-DQUEEN_DEPS_INSIDE=ON",
        "-DQUEEN_USE_SYSTEM_SDL3=OFF",
        "-DFETCH_SDL3=OFF",
        "-DFETCH_SDL3_IMAGE=OFF",
        "-DFETCH_SDL3_MIXER=OFF",
        "-DFETCH_SDL3_TTF=OFF",
    ]
    if ctx is not None:
        from forge.field_paths import kilroy_root, sg_root

        kr = kilroy_root(ctx.queen)
        if kr.is_dir():
            out.append(f"-DKILROY_ROOT={kr}")
    return out


def _cmake_stream_guard(engine: ForgeEngine, cmd: list[str], *, env: dict[str, str], timeout: int | None = 900) -> int:
    """Stream cmake; abort if SDL/compiler cache thrash loops."""
    engine.log(f"$ {' '.join(cmd)}")
    proc = subprocess.Popen(
        cmd,
        cwd=str(engine.ctx.queen),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    thrash = 0
    try:
        for line in proc.stdout:
            engine.log(line.rstrip("\n"))
            if "cache to be deleted" in line:
                thrash += 1
                if thrash >= 2:
                    proc.kill()
                    engine.log("forge:rtx_configure — aborted cmake cache thrash loop")
                    return 125
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        engine.log("TIMEOUT — cmake killed")
        return 124
    return proc.returncode or 0


def _rtx_sources_stale(ctx: ForgeContext) -> bool:
    """True when engine headers changed after queen-browser binary."""
    bin_path = _rtx_bin(ctx)
    if not bin_path or not bin_path.is_file():
        return True
    bin_mtime = bin_path.stat().st_mtime
    engine_dir = ctx.rtx / "Navigator/engine"
    if not engine_dir.is_dir():
        return False
    for path in engine_dir.rglob("*"):
        if path.suffix in {".hpp", ".cpp", ".h", ".c"} and path.stat().st_mtime > bin_mtime:
            return True
    queen_main = ctx.queen / "engine/queen-main.cpp"
    if queen_main.is_file() and queen_main.stat().st_mtime > bin_mtime:
        return True
    return False


def _rtx_configure_ok(ctx: ForgeContext) -> bool:
    cache = ctx.build / "CMakeCache.txt"
    if not cache.is_file():
        return False
    try:
        text = cache.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if "QUEEN_DEPS_INSIDE:BOOL=ON" not in text:
        return False
    if any(f"{k}:BOOL=ON" in text for k in ("FETCH_SDL3", "FETCH_SDL3_IMAGE", "FETCH_SDL3_MIXER", "FETCH_SDL3_TTF")):
        return False
    return (ctx.build / "Makefile").is_file() or (ctx.build / "build.ninja").is_file()


def _wipe_cmake_cache(build: Path, *, full: bool = False) -> None:
    """Remove cmake cache artifacts but keep populated _deps/ source trees."""
    for name in ("CMakeCache.txt", "cmake_install.cmake", "Makefile", "build.ninja"):
        p = build / name
        if p.is_file():
            p.unlink(missing_ok=True)
    cf = build / "CMakeFiles"
    if cf.is_dir():
        shutil.rmtree(cf, ignore_errors=True)
    deps_build = build / "_deps"
    if deps_build.is_dir():
        for sub in deps_build.iterdir():
            if sub.is_dir() and (sub.name.endswith("-build") or sub.name.endswith("-subbuild")):
                shutil.rmtree(sub, ignore_errors=True)
    if full:
        bin_dir = build / "bin"
        if bin_dir.is_dir():
            shutil.rmtree(bin_dir, ignore_errors=True)


def _rtx_build_stale(ctx: ForgeContext) -> bool:
    """True when a prior partial configure left a broken or looping cmake cache."""
    if rtx_ready(ctx):
        return False
    log = ctx.forge_log
    if log.is_file():
        tail = log.read_text(encoding="utf-8", errors="replace")[-120_000:]
        if tail.count("changed variables that require your cache to be deleted") >= 2:
            return True
    if ctx.deps.is_dir():
        for link in ctx.deps.iterdir():
            if link.is_symlink() and not link.resolve().is_dir():
                return True
    return False


def _field_cmake_available(ctx: ForgeContext) -> bool:
    return (
        field_cmake_script(ctx).is_file()
        and grok16_field_cmake_path(ctx).is_file()
        and queen_g16_bin(ctx) is not None
    )


def _rtx_needs_ninja_migrate(ctx: ForgeContext) -> bool:
    """True when field cmake is available but build dir still uses Unix Makefiles."""
    return _field_cmake_available(ctx) and not (ctx.build / "build.ninja").is_file()


def run_rtx_configure(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:rtx_configure (Grok16 field cmake) ===")
    if _field_cmake_available(ctx):
        script = field_cmake_script(ctx)
        if _rtx_configure_ok(ctx) and not _rtx_build_stale(ctx) and not _rtx_needs_ninja_migrate(ctx):
            engine.log("forge:rtx_configure — valid field cmake cache, skip")
            return _ok(engine, "rtx_configure", "cached")
        if _rtx_needs_ninja_migrate(ctx):
            engine.log("forge:rtx_configure — migrating Makefile cache → Ninja (field cmake)")
            _wipe_cmake_cache(ctx.build, full=False)
        env = {
            **ctx.env(),
            "GROK16_ROOT": str(grok16_root(ctx)),
            "QUEEN_ROOT": str(ctx.queen),
            "GROK16_FIELD_PROFILE": "queen_rtx",
            "GROK16_CMAKE_SOURCE": str(ctx.rtx),
            "GROK16_CMAKE_BUILD": str(ctx.build),
        }
        engine.log(f"forge:rtx_configure — delegating to {script}")
        rc = engine.run_stream(["bash", str(script), "configure"], env=env, timeout=900)
        if rc == 0 and _rtx_configure_ok(ctx):
            return _ok(engine, "rtx_configure", "field-cmake")
        return _fail(engine, "rtx_configure", "field-cmake.sh configure failed", rc, engine.tail_buffer())
    g16_script = ctx.queen / "scripts/g16-build.sh"
    if g16_script.is_file():
        env = {
            **ctx.env(),
            "GROK16_ROOT": str(grok16_root(ctx)),
            "QUEEN_ROOT": str(ctx.queen),
            "GROK16_CMAKE_SOURCE": str(ctx.rtx),
            "GROK16_CMAKE_BUILD": str(ctx.build),
        }
        engine.log(f"forge:rtx_configure — delegating to {g16_script} configure")
        rc = engine.run_stream(["bash", str(g16_script), "configure"], env=env, timeout=900)
        if rc == 0 and _rtx_configure_ok(ctx):
            return _ok(engine, "rtx_configure", "g16-build configure")
        return _fail(engine, "rtx_configure", "g16-build configure failed", rc, engine.tail_buffer())
    return _fail(engine, "rtx_configure", "field-cmake.sh unavailable — install Grok16")


def _combinatronics_compile_gate(ctx: ForgeContext, engine: ForgeEngine) -> dict:
    comb_py = grok16_root(ctx) / "lib" / "g16-compile-combinatronics.py"
    if not comb_py.is_file():
        return {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("g16_compile_combinatronics", comb_py)
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "compile_gate"):
            gate = mod.compile_gate(profile=os.environ.get("GROK16_FIELD_PROFILE"))
            engine.log(f"forge:combinatronics_gate profile={gate.get('profile')} ok={gate.get('ok')}")
            return gate
    except Exception as exc:
        engine.log(f"forge:combinatronics_gate warn — {exc}")
    return {}


def _stamp_compiled_binary(ctx: ForgeContext, engine: ForgeEngine, path: Path, gate: dict, meta: dict) -> None:
    comb_py = grok16_root(ctx) / "lib" / "g16-compile-combinatronics.py"
    if not comb_py.is_file() or not path.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("g16_compile_combinatronics", comb_py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "stamp_compiled_artifact"):
            stamp = mod.stamp_compiled_artifact(path, comb=gate.get("combinatronics"), compile_meta=meta)
            engine.log(f"forge:combinatronics_stamp ok={stamp.get('ok')} path={stamp.get('stamp')}")
    except Exception as exc:
        engine.log(f"forge:combinatronics_stamp warn — {exc}")


def run_rtx_build(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:rtx_build (g16 + Ninja — no cmake --build) ===")
    comb_gate = _combinatronics_compile_gate(ctx, engine)
    if comb_gate.get("profile"):
        os.environ["GROK16_FIELD_PROFILE"] = str(comb_gate["profile"])
    g16_bin = queen_g16_bin(ctx)
    if not g16_bin:
        return _fail(engine, "rtx_build", "g16 not ready — run scripts/g16-toolchain.sh install")
    if _field_cmake_available(ctx):
        script = field_cmake_script(ctx)
        env = {
            **ctx.env(),
            "GROK16_ROOT": str(grok16_root(ctx)),
            "G16_PREFIX": str(grok16_root(ctx)),
            "QUEEN_ROOT": str(ctx.queen),
            "GROK16_FIELD_PROFILE": "queen_rtx",
            "GROK16_CMAKE_SOURCE": str(ctx.rtx),
            "GROK16_CMAKE_BUILD": str(ctx.build),
            "GROK16_CMAKE_TARGET": "amouranth_engine",
            "GROK16_BUILD_JOBS": str(ctx.jobs),
            "CC": str(g16_bin),
            "CXX": str(g16_bin),
        }
        if not _rtx_configure_ok(ctx):
            r = run_rtx_configure(ctx, engine)
            if not r.ok:
                return r
        engine.log(f"forge:rtx_build — g16 ninja via {script}")
        rc = engine.run_stream(["bash", str(script), "g16-build"], env=env)
        if rc == 0:
            bin_path = _rtx_bin(ctx)
            if bin_path:
                bin_path.chmod(bin_path.stat().st_mode | 0o111)
                bindir = bin_path.parent
                for alias in ("queen-field-engine", "field-queen"):
                    link = bindir / alias
                    if link.exists() or link.is_symlink():
                        link.unlink()
                    link.symlink_to(bin_path.name)
                _stamp_compiled_binary(ctx, engine, bin_path, comb_gate, {"target": "queen-browser", "toolchain": "field-cmake"})
                engine.log(f"=== QUEEN BINARY READY: {bin_path} ===")
                return _ok(engine, "rtx_build", str(bin_path))
        return _fail(engine, "rtx_build", "g16 ninja build failed", rc, engine.tail_buffer())
    g16_script = ctx.queen / "scripts/g16-build.sh"
    if not g16_script.is_file():
        return _fail(engine, "rtx_build", "field-cmake.sh and g16-build.sh unavailable")
    env = {**ctx.env(), "GROK16_BUILD_JOBS": str(ctx.jobs), "QUEEN_BUILD_JOBS": str(ctx.jobs)}
    engine.log(f"forge:rtx_build — delegating to {g16_script}")
    rc = engine.run_stream(["bash", str(g16_script), "build"], env=env)
    if rc != 0:
        return _fail(engine, "rtx_build", "g16-build.sh failed", rc, engine.tail_buffer())
    bin_path = _rtx_bin(ctx)
    if not bin_path:
        return _fail(engine, "rtx_build", "no queen-browser binary after g16 build")
    bin_path.chmod(bin_path.stat().st_mode | 0o111)
    bindir = bin_path.parent
    for alias in ("queen-field-engine", "field-queen"):
        link = bindir / alias
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to(bin_path.name)
    _stamp_compiled_binary(ctx, engine, bin_path, comb_gate, {"target": "queen-browser", "toolchain": "g16-build"})
    engine.log(f"=== QUEEN BINARY READY: {bin_path} ===")
    return _ok(engine, "rtx_build", str(bin_path))


def run_rtx(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:rtx — full RTX pipeline ===")
    if not (ctx.rtx / "Navigator/shaders").is_dir():
        return _fail(engine, "rtx", f"AMOURANTHRTX missing at {ctx.rtx}")

    if not check_inside(ctx):
        run_inside(ctx, engine)

    run_shaders(ctx, engine)
    run_deps(ctx, engine)

    if check_deps(ctx):
        engine.log("forge:rtx — Queen/vendor/deps staged, skip rtx_fetch")
    elif not (ctx.build / "_deps/glm-src").is_dir():
        r = run_rtx_fetch(ctx, engine)
        if not r.ok:
            return r
        run_deps(ctx, engine)

    r = run_rtx_configure(ctx, engine)
    if not r.ok:
        return r
    return run_rtx_build(ctx, engine)


# ── media / engines ───────────────────────────────────────────────────────────

def check_ffmpeg(ctx: ForgeContext) -> bool:
    return (ctx.queen / "build/ffmpeg-prefix/lib/libavcodec.a").is_file()


def run_ffmpeg(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    ff = ctx.vendor / "ffmpeg"
    prefix = ctx.queen / "build/ffmpeg-prefix"
    if not (ff / ".git").is_dir():
        return _fail(engine, "ffmpeg", "run vendors first")
    engine.log("=== forge:ffmpeg ===")
    rc = engine.run_stream([
        str(ff / "configure"),
        f"--prefix={prefix}",
        "--enable-static", "--disable-shared", "--disable-doc", "--disable-programs",
        "--enable-gpl", "--enable-version3", "--enable-libmp3lame",
        "--enable-decoder=h264,hevc,aac,mp3,opus,vp8,vp9,av1",
        "--enable-demuxer=mov,mp4,m4v,matroska,webm,ogg,mpegts",
        "--enable-parser=h264,hevc,aac,mpegaudio,opus,vp9",
    ], cwd=ff)
    if rc != 0:
        return _fail(engine, "ffmpeg", "configure failed", rc)
    rc = engine.run_stream(["make", f"-j{ctx.jobs}"], cwd=ff)
    if rc != 0:
        return _fail(engine, "ffmpeg", "make failed", rc)
    rc = engine.run_stream(["make", "install"], cwd=ff)
    return _ok(engine, "ffmpeg", str(prefix)) if rc == 0 else _fail(engine, "ffmpeg", "install failed", rc)


def check_ladybird(ctx: ForgeContext) -> bool:
    lb = ctx.vendor / "ladybird"
    return lb.is_dir() and any(lb.rglob("Ladybird"))


def run_ladybird(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    lb = ctx.vendor / "ladybird"
    if not (lb / ".git").is_dir():
        return _fail(engine, "ladybird", "run vendors first")
    engine.log("=== forge:ladybird ===")
    meta = lb / "Meta/ladybird.py"
    if meta.is_file() and os.access(meta, os.X_OK):
        rc = engine.run_stream([str(meta), "build"], cwd=lb)
    elif (lb / "CMakeLists.txt").is_file():
        engine.run_stream(["cmake", "-B", "Build", "-DCMAKE_BUILD_TYPE=Release"], cwd=lb)
        rc = engine.run_stream(["cmake", "--build", "Build", f"-j{ctx.jobs}"], cwd=lb)
    else:
        return _fail(engine, "ladybird", "no build entry")
    return _ok(engine, "ladybird") if rc == 0 else _fail(engine, "ladybird", "build failed", rc)


def check_servo(ctx: ForgeContext) -> bool:
    return (ctx.queen / "build/servo/servo").is_file()


def run_servo(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    sv = ctx.vendor / "servo"
    out = ctx.queen / "build/servo"
    if not (sv / ".git").is_dir():
        return _fail(engine, "servo", "run vendors first")
    engine.log("=== forge:servo ===")
    rc = engine.run_stream(["./mach", "build", "--release"], cwd=sv)
    if rc != 0:
        return _fail(engine, "servo", "mach build failed", rc)
    out.mkdir(parents=True, exist_ok=True)
    built = sv / "target/release/servo"
    if built.is_file():
        shutil.copy2(built, out / "servo")
    return _ok(engine, "servo", str(out / "servo"))


# ── verify ────────────────────────────────────────────────────────────────────

def check_verify(ctx: ForgeContext) -> bool:
    return (ctx.queen / "gui/queen-theme-2026.json").is_file() and check_inside(ctx)


def run_verify(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log("=== forge:verify ===")
    root, nl = ctx.queen, ctx.nl
    checks: list[tuple[str, bool]] = []

    def req(path: Path, label: str) -> None:
        ok = path.is_file()
        checks.append((label, ok))
        engine.log(f"{'OK' if ok else 'FAIL'}: {label}")

    req(root / "gui/queen-theme-2026.json", "queen-theme-2026.json")
    req(root / "shaders/compute/QueenBoot.comp", "QueenBoot.comp")
    req(nl / "AMOURANTHRTX/Navigator/shaders/compute/QueenBoot.comp", "AMOURANTHRTX QueenBoot.comp")
    req(root / "data/queen-brain-manifest.json", "queen-brain-manifest.json")
    req(root / "lib/queen-hostess-brain.py", "queen-hostess-brain.py")
    try:
        brain_doc = json.loads((root / "data" / "queen-brain-manifest.json").read_text(encoding="utf-8"))
        checks.append(("hostess7_brain_ops", bool(brain_doc.get("hostess7_brain_ops"))))
        checks.append(("field_technology zac", bool(brain_doc.get("field_technology", {}).get("zac_monolith"))))
    except (OSError, json.JSONDecodeError):
        checks.append(("hostess7_brain_ops", False))
    req(root / "data/queen-forge-manifest.json", "queen-forge-manifest.json")
    req(root / "gui/queen-build-deck.html", "queen-build-deck.html")
    req(root / "lib/queen-forge.py", "queen-forge.py")
    req(root / "lib/queen-build.py", "queen-build.py")
    req(root / "data/grok-build-mandate.json", "grok-build-mandate.json")
    req(root / "data/field-rtx-sovereign.json", "field-rtx-sovereign.json")
    req(root / "data/queen-field-manifest.json", "queen-field-manifest.json")
    pkg = root / "field/sovereign/queen-sovereign-bundle.json"
    if pkg.is_file():
        engine.log("OK: sovereign field package sealed")
    else:
        engine.log("WARN: field package not sealed — pythong lib/queen-forge.py field")

    theme = json.loads((root / "gui/queen-theme-2026.json").read_text(encoding="utf-8"))
    checks.append(("theme web_boot", "browser.html" in json.dumps(theme.get("web_boot", ""))))
    checks.append(("theme aqua", '"aqua"' in json.dumps(theme)))

    try:
        proc = subprocess.run(
            ["pythong", str(nl / "lib/field-queen-browser.py"), "build"],
            capture_output=True, text=True, timeout=60, env=ctx.env(),
        )
        doc = json.loads(proc.stdout)
        checks.append(("QUEEN_READY", doc.get("queen_verdict") == "QUEEN_READY"))
        gates = doc.get("gates") or {}
        checks.append(("gates held", gates.get("all_held") and gates.get("held", 0) >= 37))
    except Exception as exc:
        checks.append(("panel doctrine", False))
        engine.log(f"panel check error: {exc}")

    try:
        proc = subprocess.run(
            ["pythong", str(root / "lib/queen-forge.py"), "json"],
            capture_output=True, text=True, timeout=30, cwd=str(root),
        )
        doc = json.loads(proc.stdout)
        checks.append(("forge json", doc.get("schema") == "queen-forge/v1"))
        checks.append(("forge tools", len(doc.get("tools", [])) >= 10))
    except Exception as exc:
        checks.append(("forge json", False))
        engine.log(f"forge check error: {exc}")

    bin_path = _rtx_bin(ctx)
    if bin_path and os.access(bin_path, os.X_OK):
        engine.log(f"smoke: {bin_path}")
        env = {**ctx.env(), "AMOURANTHRTX_HEADLESS": "1", "AMOURANTHRTX_MAX_FRAMES": "2"}
        try:
            proc = subprocess.run(
                [str(bin_path), "--sovereign", "--queen"],
                capture_output=True, text=True, timeout=120, env=env,
            )
            log = (proc.stdout or "") + (proc.stderr or "")
            smoke = any(k in log for k in ("FieldQueen", "Queen", "ANGEL", "QueenBoot", "navigator_main"))
            checks.append(("headless smoke", smoke))
            for line in log.splitlines()[-15:]:
                engine.log(line)
        except subprocess.TimeoutExpired:
            checks.append(("headless smoke", False))
    else:
        engine.log("SKIP: queen-browser not built")

    # Hostess + textbook + compiler matrix (best-effort before hard fail)
    try:
        from forge.hostess_tools import probe_compilers, run_forge_test
        comp = probe_compilers(ctx)
        checks.append(("compiler cmake+g++", comp.get("ready_rtx", False)))
        checks.append(("shader glslc|spv", comp.get("ready_shaders", False)))
        if (root / "lib" / "queen-hostess-brain.py").is_file():
            checks.append(("queen-hostess-brain", True))
        tb_zac = sg_root(ctx.queen) / "NewLatest" / "Textbook" / "field-technology-v5.zac"
        checks.append(("textbook zac", tb_zac.is_file()))
    except Exception as exc:
        engine.log(f"hostess probe warn: {exc}")

    failed = [c for c, ok in checks if not ok]
    if failed:
        return _fail(engine, "verify", f"failed: {', '.join(failed)}")
    engine.log("=== Queen verify PASSED ===")
    return _ok(engine, "verify")


# ── registry ──────────────────────────────────────────────────────────────────

TOOL_REGISTRY: dict[str, ForgeTool] = {
    "inside": ForgeTool("inside", "Install inside slice", "core", run_inside, check_inside,
                        replaces="scripts/install-inside.sh"),
    "vendors": ForgeTool("vendors", "Clone vendors (FFmpeg, Ladybird, Servo)", "core", run_vendors, check_vendors,
                         replaces="clone-all.sh"),
    "deps": ForgeTool("deps", "Stage inside deps (SDL, glm)", "core", run_deps, check_deps,
                      replaces="scripts/stage-deps-inside.sh"),
    "shaders": ForgeTool("shaders", "Compile QueenBoot SPIR-V", "core", run_shaders, check_shaders,
                         replaces="make Navigator/shaders"),
    "rtx_fetch": ForgeTool("rtx_fetch", "One-time RTX dep fetch", "core", run_rtx_fetch, check_deps,
                           kind="sub"),
    "rtx_configure": ForgeTool(
        "rtx_configure",
        "CMake configure RTX (Grok16 field cmake)",
        "core",
        run_rtx_configure,
        lambda c: _rtx_configure_ok(c) and not _rtx_needs_ninja_migrate(c),
        kind="sub",
    ),
    "rtx_build": ForgeTool("rtx_build", "Compile queen-browser", "core", run_rtx_build, check_rtx, kind="sub"),
    "rtx": ForgeTool("rtx", "Build queen-browser RTX exe", "core", run_rtx, check_rtx,
                     replaces="build.sh"),
    "ffmpeg": ForgeTool("ffmpeg", "Build FFmpeg static (MP4/H.264/AAC)", "media", run_ffmpeg, check_ffmpeg,
                        optional=True, replaces="build-ffmpeg.sh"),
    "ladybird": ForgeTool("ladybird", "Build Ladybird engine", "engine", run_ladybird, check_ladybird,
                          optional=True, replaces="build-ladybird.sh"),
    "servo": ForgeTool("servo", "Build Servo engine", "engine", run_servo, check_servo,
                       optional=True, replaces="build-servo.sh"),
    "verify": ForgeTool("verify", "Verify Queen doctrine + GUI", "core", run_verify, check_verify,
                        replaces="scripts/verify-queen.sh"),
}

for _fid, (_label, _track, _run, _check, _replaces) in FIELD_TOOLS.items():
    TOOL_REGISTRY[_fid] = ForgeTool(
        _fid, _label, _track, _run, _check,
        replaces=_replaces or "",
        kind="core" if _fid == "field" else ("sub" if _fid.startswith("field_") and _fid != "field_package" else "core"),
        optional=_fid in ("field_boot", "field_publish"),
    )

for _hid, (_label, _track, _run, _check, _replaces) in HOSTESS_TOOLS.items():
    TOOL_REGISTRY[_hid] = ForgeTool(
        _hid, _label, _track, _run, _check,
        replaces=_replaces or "",
        kind="core",
        optional=_hid in ("textbook_zac", "hostess_verify"),
    )

for _gid, (_label, _track, _run, _check, _replaces) in GCC_TOOLS.items():
    TOOL_REGISTRY[_gid] = ForgeTool(
        _gid, _label, _track, _run, _check,
        replaces=_replaces or "",
        kind="sub" if _gid != "gcc" else "core",
        optional=_gid not in ("gcc_fetch", "gcc_prereqs", "gcc_configure"),
    )

for _pid, (_label, _track, _run, _check, _replaces) in PYTHONG_TOOLS.items():
    TOOL_REGISTRY[_pid] = ForgeTool(
        _pid, _label, _track, _run, _check,
        replaces=_replaces or "",
        kind="sub" if _pid not in ("pythong", "grokpy") else "core",
        optional=_pid not in ("pythong", "pythong_probe", "grokpy", "grokpy_probe"),
    )

for _gid, (_label, _track, _run, _check, _replaces) in GROKPY_TOOLS.items():
    if _gid not in TOOL_REGISTRY:
        TOOL_REGISTRY[_gid] = ForgeTool(
            _gid, _label, _track, _run, _check,
            replaces=_replaces or "",
            kind="sub" if _gid != "grokpy" else "core",
            optional=_gid not in ("grokpy", "grokpy_probe"),
        )

for _bid, (_label, _track, _run, _check, _replaces) in BINUTILS_TOOLS.items():
    TOOL_REGISTRY[_bid] = ForgeTool(
        _bid, _label, _track, _run, _check,
        replaces=_replaces or "",
        kind="sub",
        optional=True,
    )

for _pid, (_label, _track, _run, _check, _replaces) in PROBE_TOOLS.items():
    TOOL_REGISTRY[_pid] = ForgeTool(
        _pid, _label, _track, _run, _check,
        replaces=_replaces or "",
        kind="core",
        optional=True,
    )

for _cid, (_run, _check) in FIELD_CMAKE_TOOLS.items():
    TOOL_REGISTRY[_cid] = ForgeTool(
        _cid,
        {
            "field_cmake_configure": "Field CMake configure (Grok16 queen-rtx)",
            "field_cmake_build": "Field CMake Ninja build",
            "field_cmake": "Field CMake full pipeline (g16)",
        }.get(_cid, _cid),
        "field-cmake",
        _run,
        _check,
        replaces="Grok16/scripts/field-cmake.sh",
        kind="sub" if _cid != "field_cmake" else "core",
    )

for _oid, (_label, _track, _run, _check, _replaces) in OPERATOR_TOOLS.items():
    TOOL_REGISTRY[_oid] = ForgeTool(
        _oid, _label, _track, _run, _check,
        replaces=_replaces or "",
        kind="core",
        optional=True,
    )

for _ftid, (_label, _track, _run, _check, _replaces) in FIELD_TECH_TOOLS.items():
    TOOL_REGISTRY[_ftid] = ForgeTool(
        _ftid, _label, _track, _run, _check,
        replaces=_replaces or "",
        kind="core",
    )

CORE_ORDER = FIELD_TECH_CORE_ORDER
HOSTESS_PIPELINE_ORDER = HOSTESS_ORDER
SOVEREIGN_FIELD_ORDER = ["inside"] + FIELD_ORDER + HOSTESS_PIPELINE_ORDER + ["verify"]