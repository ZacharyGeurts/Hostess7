"""Queen Forge — Grok16 unified compiler @ 16.1.1 (field_opt profile for RTX)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from forge.common import fail_result, ok_result
from forge.engine import ForgeContext, ForgeEngine, ForgeResult
from forge.field_paths import sg_root

G16_CC = "g16"
G16_CXX = "g++16"
GCC_REPO = os.environ.get("GROK16_GCC_REPO", os.environ.get("QUEEN_GCC_REPO", "https://gcc.gnu.org/git/gcc.git"))
GCC_BRANCH = os.environ.get("GROK16_GCC_BRANCH", os.environ.get("QUEEN_GCC_BRANCH", "releases/gcc-15"))
MANIFEST_NAME = "g16-toolchain.json"
CMAKE_FILE = "queen-g16-toolchain.cmake"
GROK16_PROFILE = os.environ.get("QUEEN_GROK16_PROFILE", "field_opt")


def _load_grok16_version() -> dict[str, Any]:
    roots: list[Path] = []
    if os.environ.get("GROK16_ROOT", "").strip():
        roots.append(Path(os.environ["GROK16_ROOT"]).resolve())
    queen = os.environ.get("QUEEN_ROOT", "").strip()
    if queen:
        roots.append(grok16_root_from_sg(sg_root(Path(queen))))
    roots.append(Path(__file__).resolve().parents[4] / "Grok16")
    for root in roots:
        path = root / "data/grok16-version.json"
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return {"g16_version": "16.1.1", "driver": "unified", "cxx_std_default": "gnu++26", "c_std_default": "gnu17"}


def grok16_root_from_sg(sg: Path) -> Path:
    env = os.environ.get("GROK16_ROOT", "").strip()
    return Path(env).resolve() if env else (sg / "Grok16").resolve()


def grok16_root(ctx: ForgeContext) -> Path:
    return grok16_root_from_sg(sg_root(ctx.queen))


_ver_meta = _load_grok16_version()
G16_VERSION = _ver_meta.get("g16_version", "16.1.1")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def gcc_src(ctx: ForgeContext) -> Path:
    override = os.environ.get("GROK16_GCC_SRC", "").strip()
    if override:
        return Path(override)
    grok = grok16_root(ctx) / "vendor/gcc"
    if (grok / ".git").is_dir():
        return grok
    return ctx.vendor / "gcc"


def gcc_build_dir(ctx: ForgeContext) -> Path:
    override = os.environ.get("GROK16_GCC_BUILD", "").strip()
    if override:
        return Path(override)
    grok = grok16_root(ctx) / "build/gcc"
    if (grok / "Makefile").is_file() or grok.is_dir():
        return grok
    return ctx.queen / "build/gcc"


def g16_prefix(ctx: ForgeContext) -> Path:
    env = os.environ.get("G16_PREFIX", "").strip()
    return Path(env) if env else grok16_root(ctx)


# Legacy alias — one prefix only (g16-prefix holds the real compiler)
def gcc_backend_prefix(ctx: ForgeContext) -> Path:
    return g16_prefix(ctx)


def g16_bin(ctx: ForgeContext, name: str) -> Path:
    return g16_prefix(ctx) / "bin" / name


def queen_g16_bin(ctx: ForgeContext) -> Path | None:
    p = g16_bin(ctx, G16_CC)
    return p if p.is_file() and os.access(p, os.X_OK) else None


def queen_gxx16_bin(ctx: ForgeContext) -> Path | None:
    p = g16_bin(ctx, G16_CXX)
    return p if p.is_file() and os.access(p, os.X_OK) else None


def queen_gcc_bin(ctx: ForgeContext) -> Path | None:
    return queen_g16_bin(ctx)


def g16_toolchain_script(ctx: ForgeContext) -> Path:
    grok = grok16_root(ctx) / "scripts/grok16-toolchain.sh"
    if grok.is_file():
        return grok
    return ctx.queen / "scripts/g16-toolchain.sh"


def grok16_profile_cmake(ctx: ForgeContext) -> Path | None:
    profile = os.environ.get("QUEEN_GROK16_PROFILE", GROK16_PROFILE).strip() or "field_opt"
    path = grok16_root(ctx) / "cmake" / f"grok16-profile-{profile.replace('_', '-')}.cmake"
    if profile == "field_opt":
        alt = grok16_root(ctx) / "cmake/grok16-profile-field-opt.cmake"
        return alt if alt.is_file() else (path if path.is_file() else None)
    return path if path.is_file() else None


def grok16_libexec(ctx: ForgeContext) -> Path:
    return g16_prefix(ctx) / "libexec" / "grok16"


def _is_real_compiler(bin_path: Path) -> bool:
    if not (bin_path.is_file() and os.access(bin_path, os.X_OK)):
        return False
    try:
        head = bin_path.read_bytes()[:2]
    except OSError:
        return False
    return head != b"#!"


def patch_gcc_field_version(ctx: ForgeContext, engine: ForgeEngine) -> None:
    base_ver = gcc_src(ctx) / "gcc/BASE-VER"
    if not base_ver.is_file():
        raise RuntimeError(f"missing {base_ver}")
    current = base_ver.read_text(encoding="utf-8").strip()
    if current != G16_VERSION:
        base_ver.write_text(G16_VERSION + "\n", encoding="utf-8")
        engine.log(f"gcc_field — patched BASE-VER {current} → {G16_VERSION}")


def _run_version(bin_path: Path, flag: str) -> str:
    try:
        return subprocess.check_output([str(bin_path), flag], text=True, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def selfhost_stamp(ctx: ForgeContext) -> Path:
    return gcc_backend_prefix(ctx) / "SELFHOST.json"


def read_selfhost_stamp(ctx: ForgeContext) -> dict[str, Any]:
    path = selfhost_stamp(ctx)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_selfhost_stamp(ctx: ForgeContext, *, bootstrap: bool) -> Path:
    g16 = queen_g16_bin(ctx)
    gxx = queen_gxx16_bin(ctx)
    doc = {
        "selfhosted": True,
        "bootstrap": bootstrap,
        "g16_version": G16_VERSION,
        "cc": str(g16) if g16 else "",
        "cxx": str(gxx) if gxx else "",
        "prefix": str(g16_prefix(ctx)),
        "pkgversion": _pkgversion(ctx),
        "engine_dumpversion": _run_version(gxx, "-dumpfullversion") if gxx else "",
        "updated": _ts(),
    }
    path = selfhost_stamp(ctx)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return path


def g16_status(ctx: ForgeContext) -> dict[str, Any]:
    src = gcc_src(ctx)
    backend = gcc_backend_prefix(ctx)
    prefix = g16_prefix(ctx)
    gxx = queen_gxx16_bin(ctx)
    g16 = queen_g16_bin(ctx)
    stamp = read_selfhost_stamp(ctx)
    probe = g16 or gxx
    libexec = grok16_libexec(ctx)
    unified = (libexec / "g16-cc").is_file() and (libexec / "g16-cxx").is_file()
    if g16 and gxx and gxx.is_symlink() and gxx.resolve() == g16.resolve():
        unified = True
    profile = grok16_profile_cmake(ctx)
    return {
        "product": "Grok16",
        "g16_version": G16_VERSION,
        "driver_mode": _ver_meta.get("driver", "unified"),
        "g16_cc": G16_CC,
        "g16_cxx": G16_CXX,
        "cxx_std_default": _ver_meta.get("cxx_std_default", "gnu++26"),
        "c_std_default": _ver_meta.get("c_std_default", "gnu17"),
        "build_profile": GROK16_PROFILE,
        "branch": GCC_BRANCH,
        "repo": GCC_REPO,
        "src": str(src),
        "src_ready": (src / ".git").is_dir(),
        "prereqs_ready": (src / "gmp").is_dir() and (src / "mpfr").is_dir(),
        "build_dir": str(gcc_build_dir(ctx)),
        "configured": (gcc_build_dir(ctx) / "Makefile").is_file(),
        "prefix": str(prefix),
        "grok16_root": str(grok16_root(ctx)),
        "engine_real": _is_real_compiler(g16) if g16 else False,
        "ready": gxx is not None and g16 is not None,
        "unified_driver": unified,
        "selfhosted": bool(stamp.get("selfhosted")),
        "bootstrap": stamp.get("bootstrap"),
        "selfhost_stamp": str(selfhost_stamp(ctx)) if stamp else "",
        "dumpversion": _run_version(probe, "-dumpversion") if probe else "",
        "version": _run_version(probe, "--version").splitlines()[0] if probe else "",
        "paths": {
            "g16": str(g16) if g16 else "",
            "g++16": str(gxx) if gxx else "",
            "backend_cc": str(libexec / "g16-cc") if (libexec / "g16-cc").is_file() else "",
            "backend_cxx": str(libexec / "g16-cxx") if (libexec / "g16-cxx").is_file() else "",
            "cmake": str(grok16_toolchain_path(ctx) or (ctx.queen / "cmake" / CMAKE_FILE)),
            "grok16_cmake": str(grok16_root(ctx) / "cmake/grok16-toolchain.cmake"),
            "field_cmake": str(grok16_field_cmake_path(ctx)),
            "field_cmake_script": str(field_cmake_script(ctx)),
            "g16_build_script": str(ctx.queen / "scripts/g16-build.sh"),
            "build_method": "g16+ninja",
            "profile_cmake": str(profile) if profile else "",
            "toolchain_sh": str(g16_toolchain_script(ctx)),
            "grok16_manifest": str(grok16_root(ctx) / "data/grok16-toolchain.json"),
        },
    }


def probe_host_tools(ctx: ForgeContext) -> dict[str, str]:
    found: dict[str, str] = {}
    for name in ("cmake", "make", "ninja", "glslc", "git", "pythong", "bash", "clang", "rustc", "cargo", "nasm", "ld"):
        path = shutil.which(name)
        if path:
            found[name] = path
    g16 = queen_g16_bin(ctx)
    gxx = queen_gxx16_bin(ctx)
    if g16 and gxx:
        found[G16_CC] = str(g16)
        found[G16_CXX] = str(gxx)
    return found


def probe_compilers(ctx: ForgeContext) -> dict[str, Any]:
    found = probe_host_tools(ctx)
    toolchain = g16_status(ctx)
    dump = toolchain.get("dumpversion", "")
    version_ok = dump == G16_VERSION
    runtime_ok = bool(toolchain.get("engine_real") and toolchain.get("ready"))
    return {
        "jobs": ctx.jobs,
        "cpu_count": os.cpu_count(),
        "found": found,
        "toolchain": toolchain,
        "ready_g16": version_ok,
        "ready_g16_runtime": runtime_ok,
        "version_upgrade_pending": runtime_ok and not version_ok,
        "ready_rtx": "cmake" in found and G16_CXX in found and runtime_ok,
        "ready_shaders": "glslc" in found or (ctx.queen / "assets/shaders/compute/QueenBoot.spv").is_file(),
        "ready_ffmpeg": "make" in found,
        "ready_servo": "cargo" in found and "rustc" in found,
    }


def write_manifest(ctx: ForgeContext) -> Path:
    doc = probe_compilers(ctx)
    doc["updated"] = _ts()
    if _ver_meta.get("distro_version"):
        doc["distro_version"] = _ver_meta["distro_version"]
    if _ver_meta.get("tag"):
        doc["release_tag"] = _ver_meta["tag"]
    doc["field_mandate"] = {
        "id": "G16_FIELD_SAFETY_MANDATE_v1",
        "cmake": str(g16_field_mandate_path(ctx)),
        "mandate_json": str(ctx.queen / "data/g16-field-mandate.json"),
    }
    out = ctx.queen / "data" / MANIFEST_NAME
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return out


def g16_field_mandate_path(ctx: ForgeContext) -> Path:
    canonical = grok16_root(ctx) / "cmake/g16-field-mandate.cmake"
    if canonical.is_file():
        return canonical
    return ctx.queen / "cmake/g16-field-mandate.cmake"


def grok16_field_cmake_path(ctx: ForgeContext) -> Path:
    return grok16_root(ctx) / "cmake/grok16-field.cmake"


def grok16_toolchain_path(ctx: ForgeContext) -> Path | None:
    path = grok16_root(ctx) / "cmake/grok16-toolchain.cmake"
    return path if path.is_file() else None


def field_cmake_script(ctx: ForgeContext) -> Path:
    return grok16_root(ctx) / "scripts/field-cmake.sh"


def write_cmake_toolchain(ctx: ForgeContext) -> Path | None:
    driver = g16_bin(ctx, G16_CC)
    if not driver.is_file():
        return None
    canonical = grok16_toolchain_path(ctx)
    if canonical:
        queen_tc = ctx.queen / "cmake" / CMAKE_FILE
        queen_tc.parent.mkdir(parents=True, exist_ok=True)
        if not queen_tc.exists() or queen_tc.is_symlink():
            if queen_tc.is_symlink() or queen_tc.exists():
                queen_tc.unlink(missing_ok=True)
            try:
                queen_tc.symlink_to(canonical)
            except OSError:
                queen_tc.write_text(f'include("{canonical}")\n', encoding="utf-8")
        return canonical
    path = ctx.queen / "cmake" / CMAKE_FILE
    prefix = g16_prefix(ctx)
    cxx_std = _ver_meta.get("cxx_std_default", "gnu++26")
    c_std = _ver_meta.get("c_std_default", "gnu17")
    path.write_text(
        "# Portable Grok16 toolchain — env GROK16_ROOT or relative from Queen/cmake\n"
        "if(DEFINED ENV{GROK16_ROOT})\n"
        "  set(_GROK16_PREFIX \"$ENV{GROK16_ROOT}\")\n"
        "else()\n"
        "  get_filename_component(_GROK16_PREFIX \"${CMAKE_CURRENT_LIST_DIR}/../../../Grok16\" ABSOLUTE)\n"
        "endif()\n"
        f'set(_G16_DRIVER "${{_GROK16_PREFIX}}/bin/{G16_CC}")\n'
        'set(CMAKE_C_COMPILER "${_G16_DRIVER}" CACHE FILEPATH "Grok16 g16 (C mode)" FORCE)\n'
        'set(CMAKE_CXX_COMPILER "${_G16_DRIVER}" CACHE FILEPATH "Grok16 g16 (C++ mode)" FORCE)\n'
        "unset(_G16_DRIVER)\n"
        f'set(WRDT_G16_VERSION "{G16_VERSION}" CACHE STRING "G16 version" FORCE)\n'
        'set(GROK16_PREFIX "${_GROK16_PREFIX}" CACHE PATH "Grok16 install prefix" FORCE)\n'
        f'set(GROK16_CXX_STD "{cxx_std}" CACHE STRING "Grok16 default C++ standard" FORCE)\n'
        f'set(GROK16_C_STD "{c_std}" CACHE STRING "Grok16 default C standard" FORCE)\n'
        "unset(_GROK16_PREFIX)\n",
        encoding="utf-8",
    )
    return path


def cmake_compiler_args(ctx: ForgeContext) -> list[str]:
    driver = g16_bin(ctx, G16_CC)
    if driver.is_file():
        return [f"-DCMAKE_C_COMPILER={driver}", f"-DCMAKE_CXX_COMPILER={driver}"]
    return []


def cmake_generator_args(ctx: ForgeContext) -> list[str]:
    if shutil.which("ninja"):
        return ["-G", "Ninja"]
    return []


def cmake_init_cache_args(ctx: ForgeContext, *, profile: str = "queen_rtx") -> tuple[list[str], dict[str, str]]:
    """Grok16 Field CMake — toolchain + grok16-field.cmake (g16 owns configure)."""
    args: list[str] = cmake_generator_args(ctx)
    env: dict[str, str] = {}
    tc = write_cmake_toolchain(ctx)
    if tc:
        args.append(f"-DCMAKE_TOOLCHAIN_FILE={tc}")
        driver = g16_bin(ctx, G16_CC)
        env["CC"] = str(driver)
        env["CXX"] = str(driver)
        env["WRDT_G16_PREFIX"] = str(g16_prefix(ctx))
        env["GROK16_ROOT"] = str(grok16_root(ctx))
        env["G16_PREFIX"] = str(g16_prefix(ctx))
        env["GROK16_FIELD_PROFILE"] = profile
    field_cmake = grok16_field_cmake_path(ctx)
    if field_cmake.is_file():
        args.append(f"-DCMAKE_PROJECT_INCLUDE={field_cmake}")
        args.append(f"-DGROK16_FIELD_PROFILE={profile}")
    else:
        profile_cmake = grok16_profile_cmake(ctx)
        if profile_cmake:
            args.append(f"-DCMAKE_PROJECT_INCLUDE={profile_cmake}")
        preset = ctx.queen / "cmake/queen-inside.cmake"
        if preset.is_file():
            args.extend(["-C", str(preset)])
    return args, env


def _sync_grok16_manifest(ctx: ForgeContext, engine: ForgeEngine | None = None) -> None:
    script = g16_toolchain_script(ctx)
    if script.is_file() and script.name == "grok16-toolchain.sh":
        env = {**os.environ, "GROK16_ROOT": str(grok16_root(ctx)), "G16_PREFIX": str(g16_prefix(ctx))}
        subprocess.run(["bash", str(script), "manifest"], env=env, capture_output=True, timeout=60, check=False)
        if engine:
            engine.log("g16: synced grok16-toolchain.json")


def verify_g16_install(ctx: ForgeContext, engine: ForgeEngine | None = None) -> bool:
    g16 = queen_g16_bin(ctx)
    gxx = queen_gxx16_bin(ctx)
    if not g16 or not gxx:
        if engine:
            engine.log("g16: missing g16/g++16 in prefix")
        return False
    gxx_ok = gxx.is_symlink() or _is_real_compiler(gxx)
    if not (_is_real_compiler(g16) and gxx_ok):
        if engine:
            engine.log("g16: refuse shell wrappers — run grok16-toolchain.sh rebuild")
        return False
    dv = _run_version(g16, "-dumpversion")
    if dv != G16_VERSION:
        if engine:
            engine.log(f"g16: -dumpversion={dv!r} expected {G16_VERSION}")
        return False
    prefix = g16_prefix(ctx)
    prefix.mkdir(parents=True, exist_ok=True)
    (prefix / "VERSION").write_text(
        f"GROK16={G16_VERSION}\nG16_FIELD_GCC={G16_VERSION}\nG16_DRIVER=unified\n"
        f"G16_CXX=g++16\nG16_CC=g16\nG16_PREFIX={prefix}\n"
        f"G16_C_STD={_ver_meta.get('c_std_default', 'gnu17')}\n"
        f"G16_CXX_STD={_ver_meta.get('cxx_std_default', 'gnu++26')}\n"
        f"PRODUCT=Grok16\nROOT={grok16_root(ctx)}\n",
        encoding="utf-8",
    )
    write_cmake_toolchain(ctx)
    _sync_grok16_manifest(ctx, engine)
    if engine:
        engine.log(f"g16: verified unified {g16} ({_run_version(g16, '--version').splitlines()[0]})")
    return True


install_g16 = verify_g16_install


# Legacy alias for field_tech_pipeline
gcc_status = g16_status


def check_gcc_fetch(ctx: ForgeContext) -> bool:
    return (gcc_src(ctx) / ".git").is_dir()


def run_gcc_fetch(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log(f"=== forge:gcc_fetch — {GCC_BRANCH} ===")
    dest = gcc_src(ctx)
    if (dest / ".git").is_dir():
        rc = engine.run_stream(["git", "-C", str(dest), "pull", "--ff-only"])
        if rc != 0:
            return fail_result(engine, "gcc_fetch", "pull failed", rc)
    else:
        ctx.vendor.mkdir(parents=True, exist_ok=True)
        depth = os.environ.get("QUEEN_CLONE_DEPTH", "1")
        rc = engine.run_stream([
            "git", "clone", f"--depth={depth}", "--branch", GCC_BRANCH, "--single-branch",
            GCC_REPO, str(dest),
        ])
        if rc != 0:
            return fail_result(engine, "gcc_fetch", "clone failed", rc)
    write_manifest(ctx)
    return ok_result(engine, "gcc_fetch", GCC_BRANCH)


def check_gcc_prereqs(ctx: ForgeContext) -> bool:
    src = gcc_src(ctx)
    return (src / "gmp").is_dir() and (src / "mpfr").is_dir() and (src / "mpc").is_dir()


def run_gcc_prereqs(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    src = gcc_src(ctx)
    if not (src / ".git").is_dir():
        return fail_result(engine, "gcc_prereqs", "run gcc_fetch first")
    script = src / "contrib/download_prerequisites"
    if not script.is_file():
        return fail_result(engine, "gcc_prereqs", "missing download_prerequisites")
    rc = engine.run_stream([str(script)], cwd=src, timeout=3600)
    return ok_result(engine, "gcc_prereqs") if rc == 0 else fail_result(engine, "gcc_prereqs", "failed", rc)


def check_gcc_configure(ctx: ForgeContext) -> bool:
    return (gcc_build_dir(ctx) / "Makefile").is_file()


G16_PROGRAM_TRANSFORM = "s/^gcc$/g16/; s/^g++$/g++16/; s/^gcc-/g16-/"


def _pkgversion(ctx: ForgeContext) -> str:
    override = os.environ.get("G16_PKGVERSION", "").strip()
    if override:
        return override
    if "Grok16" in str(g16_prefix(ctx)):
        return f"Grok16-{G16_VERSION}"
    return f"G16-Field-{G16_VERSION}"


def _gcc_configure_argv(ctx: ForgeContext, *, selfhost: bool) -> tuple[list[str], str]:
    argv = [
        str(gcc_src(ctx) / "configure"),
        f"--prefix={g16_prefix(ctx)}",
        "--disable-multilib",
        "--enable-languages=c,c++",
        f"--with-pkgversion={_pkgversion(ctx)}",
        f"--program-transform-name={G16_PROGRAM_TRANSFORM}",
    ]
    if selfhost:
        if os.environ.get("G16_DISABLE_BOOTSTRAP", "").strip() in ("1", "true", "yes"):
            argv.append("--disable-bootstrap")
            note = "bootstrap disabled (G16_DISABLE_BOOTSTRAP)"
        else:
            note = "bootstrap enabled (stage1→stage2→stage3)"
    else:
        argv.append("--disable-bootstrap")
        note = "host build, bootstrap disabled"
    return argv, note


def _compiler_for_selfhost(ctx: ForgeContext, name: str) -> Path:
    p = g16_bin(ctx, name)
    if p and _is_real_compiler(p):
        return p
    legacy = ctx.queen / "build/gcc-prefix/bin"
    leg = legacy / ("g++" if name == G16_CXX else "gcc")
    if leg.is_file():
        return leg
    if p and p.is_file():
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                if line.startswith('REAL="'):
                    real = Path(line.split('"')[1])
                    if real.is_file():
                        return real
        except OSError:
            pass
    raise RuntimeError(f"{name} not available for self-host (need prior build or legacy prefix)")


def _gcc_configure_env(ctx: ForgeContext, *, selfhost: bool) -> dict[str, str]:
    env = os.environ.copy()
    if selfhost:
        env["CC"] = str(_compiler_for_selfhost(ctx, G16_CC))
        env["CXX"] = str(_compiler_for_selfhost(ctx, G16_CXX))
    return env


def run_gcc_configure(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    if not check_gcc_prereqs(ctx):
        return fail_result(engine, "gcc_configure", "run gcc_prereqs first")
    patch_gcc_field_version(ctx, engine)
    bdir = gcc_build_dir(ctx)
    if (bdir / "Makefile").is_file():
        return ok_result(engine, "gcc_configure", "skipped")
    bdir.mkdir(parents=True, exist_ok=True)
    argv, note = _gcc_configure_argv(ctx, selfhost=False)
    engine.log(f"gcc_configure — {note}")
    rc = engine.run_stream(argv, cwd=bdir, env=_gcc_configure_env(ctx, selfhost=False))
    return ok_result(engine, "gcc_configure") if rc == 0 else fail_result(engine, "gcc_configure", "failed", rc)


def run_gcc_distclean(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    bdir = gcc_build_dir(ctx)
    if not bdir.exists():
        return ok_result(engine, "gcc_distclean", "no build tree")
    if (bdir / "Makefile").is_file():
        engine.log("gcc_distclean — make distclean")
        engine.run_stream(["make", "distclean"], cwd=bdir, timeout=600)
    engine.log(f"gcc_distclean — remove {bdir}")
    shutil.rmtree(bdir, ignore_errors=True)
    bdir.mkdir(parents=True, exist_ok=True)
    return ok_result(engine, "gcc_distclean")


def run_gcc_configure_selfhost(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    if not check_gcc_prereqs(ctx):
        return fail_result(engine, "gcc_configure_selfhost", "run gcc_prereqs first")
    patch_gcc_field_version(ctx, engine)
    try:
        cc = _compiler_for_selfhost(ctx, G16_CC)
        cxx = _compiler_for_selfhost(ctx, G16_CXX)
    except RuntimeError as exc:
        return fail_result(engine, "gcc_configure_selfhost", str(exc))
    bdir = gcc_build_dir(ctx)
    bdir.mkdir(parents=True, exist_ok=True)
    argv, note = _gcc_configure_argv(ctx, selfhost=True)
    engine.log(f"gcc_configure_selfhost — CC={cc} CXX={cxx} ({note})")
    rc = engine.run_stream(argv, cwd=bdir, env=_gcc_configure_env(ctx, selfhost=True))
    return ok_result(engine, "gcc_configure_selfhost") if rc == 0 else fail_result(engine, "gcc_configure_selfhost", "failed", rc)


def check_gcc_build(ctx: ForgeContext) -> bool:
    st = g16_status(ctx)
    return (
        st["ready"]
        and st["dumpversion"] == G16_VERSION
        and st.get("engine_real") is True
    )


def run_gcc_build(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    bdir = gcc_build_dir(ctx)
    if not (bdir / "Makefile").is_file():
        return fail_result(engine, "gcc_build", "run gcc_configure first")
    if engine.run_stream(["make", f"-j{ctx.jobs}"], cwd=bdir, timeout=None) != 0:
        return fail_result(engine, "gcc_build", "make failed")
    if engine.run_stream(["make", "install"], cwd=bdir, timeout=None) != 0:
        return fail_result(engine, "gcc_build", "install failed")
    if not install_g16(ctx, engine):
        if probe_compilers(ctx).get("version_upgrade_pending"):
            engine.log("gcc_build: version mismatch — escalating to gcc_rebuild @ Grok16")
            return run_gcc_rebuild(ctx, engine)
        return fail_result(engine, "gcc_build", "g16 install failed")
    write_cmake_toolchain(ctx)
    write_manifest(ctx)
    st = g16_status(ctx)
    engine.log(f"=== G16 READY {st.get('version')} ===")
    return ok_result(engine, "gcc_build", st.get("version", ""))


def run_g16_install(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    if not install_g16(ctx, engine):
        return fail_result(engine, "g16_install", "failed")
    write_cmake_toolchain(ctx)
    write_manifest(ctx)
    return ok_result(engine, "g16_install", g16_status(ctx).get("version", ""))


def check_gcc_rebuild(_ctx: ForgeContext) -> bool:
    return False


def run_gcc_rebuild(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    """Rebuild Grok16 unified compiler @ 16.1.1 with release/field_opt speedups."""
    grok_forge = grok16_root(ctx) / "forge" / "grok16-forge.py"
    if grok_forge.is_file():
        engine.log(f"=== forge:gcc_rebuild — Grok16 forge @ {G16_VERSION} ===")
        grok = grok16_root(ctx)
        env = {
            **os.environ,
            "GROK16_ROOT": str(grok),
            "G16_PREFIX": str(g16_prefix(ctx)),
            "GROK16_GCC_SRC": str(gcc_src(ctx)),
            "GROK16_GCC_BUILD": str(gcc_build_dir(ctx)),
            "GROK16_BUILD_JOBS": str(ctx.jobs),
            "QUEEN_ROOT": str(ctx.queen),
            "PYTHONPATH": str(grok / "forge")
            + (os.pathsep + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""),
        }
        env.setdefault("G16_RELEASE_PROFILE", "1")
        env.setdefault("G16_FIELD_SPEED", "1")
        if probe_compilers(ctx).get("version_upgrade_pending"):
            env["G16_FULL_REBUILD"] = "1"
            env["G16_FAST_REBUILD"] = "0"
            env.pop("G16_DISABLE_BOOTSTRAP", None)
            engine.log("gcc_rebuild: version upgrade pending — G16_FULL_REBUILD=1")
        rc = engine.run_stream([sys.executable, str(grok_forge), "run", "gcc_rebuild"], env=env, timeout=None)
        if rc != 0:
            return fail_result(engine, "gcc_rebuild", "grok16-forge gcc_rebuild failed", rc)
        if not install_g16(ctx, engine):
            return fail_result(engine, "gcc_rebuild", "g16 install verify failed")
        write_manifest(ctx)
        st = g16_status(ctx)
        engine.log(f"=== GROK16 READY {st.get('version')} profile={GROK16_PROFILE} ===")
        return ok_result(engine, "gcc_rebuild", st.get("version", ""))

    engine.log(f"=== forge:gcc_rebuild — Queen-local G16 @ {G16_VERSION} ===")
    try:
        _compiler_for_selfhost(ctx, G16_CC)
        _compiler_for_selfhost(ctx, G16_CXX)
    except RuntimeError as exc:
        return fail_result(engine, "gcc_rebuild", str(exc))
    bootstrap = os.environ.get("G16_DISABLE_BOOTSTRAP", "").strip() not in ("1", "true", "yes")
    build_env = _gcc_configure_env(ctx, selfhost=True)
    for step, run_fn in (
        ("gcc_distclean", run_gcc_distclean),
        ("gcc_configure_selfhost", run_gcc_configure_selfhost),
    ):
        r = run_fn(ctx, engine)
        if not r.ok:
            return fail_result(engine, "gcc_rebuild", f"{step} failed")
    bdir = gcc_build_dir(ctx)
    target = "bootstrap" if bootstrap else "all"
    engine.log(f"gcc_rebuild — make {target} -j{ctx.jobs} CC={build_env.get('CC')} CXX={build_env.get('CXX')}")
    if engine.run_stream(["make", target, f"-j{ctx.jobs}"], cwd=bdir, env=build_env, timeout=None) != 0:
        return fail_result(engine, "gcc_rebuild", f"make {target} failed")
    if engine.run_stream(["make", "install"], cwd=bdir, env=build_env, timeout=None) != 0:
        return fail_result(engine, "gcc_rebuild", "install failed")
    if not install_g16(ctx, engine):
        return fail_result(engine, "gcc_rebuild", "g16 install failed")
    stamp = write_selfhost_stamp(ctx, bootstrap=bootstrap)
    write_cmake_toolchain(ctx)
    write_manifest(ctx)
    st = g16_status(ctx)
    engine.log(f"=== G16 SELF-HOST READY {st.get('version')} stamp={stamp.name} ===")
    return ok_result(engine, "gcc_rebuild", st.get("version", ""))


def run_compiler_probe(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    engine.log(f"=== forge:compiler_probe (Grok16 unified @ {G16_VERSION}) ===")
    script = g16_toolchain_script(ctx)
    if script.is_file() and script.name == "grok16-toolchain.sh":
        env = {**os.environ, "GROK16_ROOT": str(grok16_root(ctx)), "G16_PREFIX": str(g16_prefix(ctx))}
        subprocess.run(["bash", str(script), "install"], env=env, capture_output=True, timeout=120, check=False)
    doc = probe_compilers(ctx)
    tc = doc.get("toolchain", {})
    engine.log(f"  profile: {tc.get('build_profile', GROK16_PROFILE)} unified={tc.get('unified_driver')}")
    for k, v in sorted(doc["found"].items()):
        engine.log(f"  {k}: {v}")
    out = write_manifest(ctx)
    engine.log(f"  wrote {out.name}")
    if not doc["ready_rtx"]:
        return fail_result(engine, "compiler_probe", "cmake + g16 required")
    if doc.get("version_upgrade_pending"):
        tc = doc.get("toolchain", {})
        engine.log(
            f"  WARN installed {tc.get('dumpversion')} → target {G16_VERSION}; "
            "run: G16_RELEASE_PROFILE=1 bash Grok16/scripts/grok16-toolchain.sh rebuild"
        )
    elif not doc.get("ready_g16"):
        return fail_result(engine, "compiler_probe", f"g16 -dumpversion must be {G16_VERSION}")
    return ok_result(engine, "compiler_probe", json.dumps(doc["found"]))


def check_compiler_probe(ctx: ForgeContext) -> bool:
    return probe_compilers(ctx)["ready_rtx"]


def run_gcc(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    for step, run_fn, check_fn in (
        ("gcc_fetch", run_gcc_fetch, check_gcc_fetch),
        ("gcc_prereqs", run_gcc_prereqs, check_gcc_prereqs),
        ("gcc_configure", run_gcc_configure, check_gcc_configure),
        ("gcc_build", run_gcc_build, check_gcc_build),
    ):
        if check_fn(ctx) and step != "gcc_build":
            continue
        r = run_fn(ctx, engine)
        if not r.ok:
            return r
    if not check_gcc_build(ctx):
        r = run_g16_install(ctx, engine)
        if not r.ok:
            return r
    return ok_result(engine, "gcc")


GCC_TOOLS: dict[str, tuple[str, str, object, object, str | None]] = {
    "gcc_fetch": ("Clone G16 source", "toolchain", run_gcc_fetch, check_gcc_fetch, None),
    "gcc_prereqs": ("G16 prerequisites", "toolchain", run_gcc_prereqs, check_gcc_prereqs, None),
    "gcc_configure": ("Configure G16 backend", "toolchain", run_gcc_configure, check_gcc_configure, None),
    "gcc_build": ("Build + install g16-prefix", "toolchain", run_gcc_build, check_gcc_build, None),
    "gcc_rebuild": ("Self-host G16 with g16/g++16", "toolchain", run_gcc_rebuild, check_gcc_rebuild, None),
    "g16_toolchain": ("G16 toolchain rebuild (alias)", "toolchain", run_gcc_rebuild, check_gcc_rebuild, "gcc_rebuild"),
    "g16_install": ("Verify g16/g++16 field install", "toolchain", run_g16_install, check_gcc_build, None),
    "gcc": ("Full G16 pipeline", "toolchain", run_gcc, check_gcc_build, None),
}

GCC_ORDER = ["gcc_fetch", "gcc_prereqs", "gcc_configure", "gcc_build", "g16_install"]