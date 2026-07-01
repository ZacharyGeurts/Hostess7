#!/usr/bin/env pythong
"""Grok16 script compile — g16-built executables that launch hot field scripts fast."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-g16-script-compile-doctrine.json"
MANIFEST = STATE / "g16-script-compile-manifest.json"
ENABLED = os.environ.get("G16_SCRIPT_EXEC", "1").strip().lower() not in ("0", "false", "no", "off")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def grok16_root() -> Path:
    try:
        sys.path.insert(0, str(INSTALL / "lib"))
        from sg_paths import grok16_root as _gr  # type: ignore

        return _gr()
    except Exception:
        pass
    for candidate in (INSTALL / "Grok16", SG / "Grok16", Path(os.environ.get("GROK16_ROOT", ""))):
        if candidate.is_dir() and (candidate / "bin" / "g16").is_file():
            return candidate
    return SG / "Grok16"


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def output_dir() -> Path:
    rel = str(_doctrine().get("output_dir") or "lib/bin")
    return INSTALL / rel


def _resolve_script(path: Path) -> Path | None:
    p = path
    if not p.is_absolute():
        p = INSTALL / p
    try:
        p = p.resolve()
    except OSError:
        return None
    if not p.is_file():
        return None
    try:
        p.relative_to(INSTALL.resolve())
    except ValueError:
        return None
    return p


def _python_driver() -> tuple[str, str]:
    g16 = grok16_root()
    for toolchain, candidate in (
        ("python_gpy", os.environ.get("GPY16_DRIVER")),
        ("python_gpy", str(g16 / "bin" / "gpy-16")),
        ("python_gpy", str(SG / "GrokPy" / "bin" / "gpy-16")),
        ("python_gpy", os.environ.get("NEXUS_PYTHONG")),
        ("python_gpy", str(SG / "PythonG" / "bin" / "pythong")),
        ("python_host", "pythong"),
        ("python_host", "python3"),
    ):
        if candidate:
            found = candidate if Path(candidate).is_file() else None
            if not found:
                from shutil import which
                found = which(str(candidate))
            if found and Path(found).is_file():
                return found, toolchain
    return sys.executable, "python_host"


def _escape_c(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _launcher_source(script: Path, *, kind: str) -> str:
    script_s = _escape_c(str(script))
    if kind == "python_launcher":
        driver, toolchain = _python_driver()
        driver_s = _escape_c(driver)
        return (
            "#include <stdio.h>\n"
            "#include <stdlib.h>\n"
            "#include <string.h>\n"
            "#include <unistd.h>\n"
            f"/* G16 script launcher — {toolchain} */\n"
            "static void run_script(int argc, char **argv) {\n"
            f'    const char *driver = "{driver_s}";\n'
            f'    const char *script = "{script_s}";\n'
            "    char **nargv = malloc((size_t)(argc + 2) * sizeof(char *));\n"
            "    if (!nargv) { perror(\"malloc\"); exit(127); }\n"
            "    nargv[0] = (char *)driver;\n"
            "    nargv[1] = (char *)script;\n"
            "    for (int i = 1; i < argc; i++) nargv[i + 1] = argv[i];\n"
            "    nargv[argc + 1] = NULL;\n"
            "    execv(driver, nargv);\n"
            "    perror(\"execv\");\n"
            "    free(nargv);\n"
            "    exit(127);\n"
            "}\n"
            "int main(int argc, char **argv) {\n"
            "    run_script(argc, argv);\n"
            "    return 127;\n"
            "}\n"
        )
    shell = _escape_c("/bin/bash")
    return (
        "#include <stdio.h>\n"
        "#include <stdlib.h>\n"
        "#include <string.h>\n"
        "#include <unistd.h>\n"
        "/* G16 shell launcher */\n"
        "static void run_script(int argc, char **argv) {\n"
        f'    const char *shell = "{shell}";\n'
        f'    const char *script = "{script_s}";\n'
        "    char **nargv = malloc((size_t)(argc + 3) * sizeof(char *));\n"
        "    if (!nargv) { perror(\"malloc\"); exit(127); }\n"
        "    nargv[0] = (char *)shell;\n"
        "    nargv[1] = (char *)script;\n"
        "    for (int i = 1; i < argc; i++) nargv[i + 1] = argv[i];\n"
        "    nargv[argc + 1] = NULL;\n"
        "    execv(shell, nargv);\n"
        "    perror(\"execv\");\n"
        "    free(nargv);\n"
        "    exit(127);\n"
        "}\n"
        "int main(int argc, char **argv) {\n"
        "    run_script(argc, argv);\n"
        "    return 127;\n"
        "}\n"
    )


def _source_fingerprint(script: Path, launcher_kind: str) -> str:
    try:
        st = script.stat()
        blob = f"{script}:{st.st_mtime_ns}:{st.st_size}:{launcher_kind}:{_python_driver()[0]}"
    except OSError:
        blob = f"{script}:missing:{launcher_kind}"
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def _g16_bin() -> Path | None:
    g16 = grok16_root() / "bin" / "g16"
    return g16 if g16.is_file() else None


_PIE_FLAGS = frozenset({"-fPIE", "-pie", "-fpie", "-fpic", "-fPIC", "-Wl,-pie"})


def _exec_link_fixup(flags: list[str]) -> list[str]:
    cleaned = [f for f in flags if f not in _PIE_FLAGS and not f.startswith("-Wl,-pie")]
    for req in ("-fno-pie", "-no-pie", "-static"):
        if req not in cleaned:
            cleaned.append(req)
    return cleaned


def _profile_flags(profile: str) -> list[str]:
    flags_py = grok16_root() / "scripts" / "grok16-profile-flags.py"
    if not flags_py.is_file():
        return _exec_link_fixup(["-std=gnu17", "-O3", "-march=native"])
    env = {**os.environ, "GROK16_ROOT": str(grok16_root()), "G16_PREFIX": str(grok16_root()), "G16_BENCH_PROFILE": profile}
    try:
        proc = subprocess.run(
            [sys.executable, str(flags_py), profile, "c"],
            capture_output=True, text=True, timeout=30, env=env, check=False,
        )
        if proc.stdout.strip():
            return _exec_link_fixup(proc.stdout.strip().split())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return _exec_link_fixup(["-std=gnu17", "-O3", "-march=native"])


def _comb_gate() -> dict[str, Any]:
    comb_py = grok16_root() / "lib" / "g16-compile-combinatronics.py"
    if not comb_py.is_file():
        return {}
    try:
        spec = importlib.util.spec_from_file_location("g16_compile_combinatronics", comb_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "compile_gate"):
                return mod.compile_gate(sustained=True) or {}
    except Exception:
        pass
    return {}


def compile_script(path: str | Path, *, force: bool = False) -> dict[str, Any]:
    """Compile a field script to a g16-built executable launcher."""
    t0 = time.perf_counter()
    if not ENABLED:
        return {"ok": False, "skipped": "disabled", "schema": "field-g16-script-compile/v1"}
    script = _resolve_script(Path(path))
    if not script:
        return {"ok": False, "error": "script_missing", "path": str(path)}
    ext = script.suffix.lower()
    exts = _doctrine().get("extensions") or {}
    kind = str(exts.get(ext) or "")
    if not kind:
        return {"ok": False, "error": "unsupported_extension", "path": str(script), "ext": ext}

    out_dir = output_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    binary = out_dir / script.stem
    fp = _source_fingerprint(script, kind)
    manifest = _load(MANIFEST, {"schema": "g16-script-compile-manifest/v1", "entries": {}})
    entries = manifest.setdefault("entries", {})
    prev = entries.get(script.stem) or {}
    if (
        not force
        and binary.is_file()
        and prev.get("fingerprint") == fp
        and prev.get("source_mtime_ns") == script.stat().st_mtime_ns
    ):
        return {
            "schema": "field-g16-script-compile/v1",
            "ok": True,
            "cached": True,
            "binary": str(binary),
            "script": str(script),
            "launcher_kind": kind,
            "fingerprint": fp,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
        }

    gate = _comb_gate()
    profile = str(
        _doctrine().get("profile_default")
        or os.environ.get("G16_AI_PROFILE")
        or gate.get("profile")
        or "ai_agent"
    )
    g16 = _g16_bin()
    if not g16:
        return {"ok": False, "error": "g16_missing", "grok16_root": str(grok16_root())}

    import tempfile
    with tempfile.TemporaryDirectory(prefix="g16-script-") as td:
        src_c = Path(td) / f"{script.stem}-launcher.c"
        src_c.write_text(_launcher_source(script, kind=kind), encoding="utf-8")
        flags = _profile_flags(profile)
        cmd = [str(g16), *flags, "-o", str(binary), str(src_c)]
        env = {
            **os.environ,
            "GROK16_ROOT": str(grok16_root()),
            "G16_PREFIX": str(grok16_root()),
            "G16_BENCH_PROFILE": profile,
        }
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, env=env, check=False)
        if proc.returncode != 0 or not binary.is_file():
            return {
                "schema": "field-g16-script-compile/v1",
                "ok": False,
                "error": "g16_compile_failed",
                "script": str(script),
                "stderr_tail": (proc.stderr or "")[-1200:],
                "profile": profile,
            }
        binary.chmod(binary.stat().st_mode | 0o111)

    stamp: dict[str, Any] = {}
    comb_py = grok16_root() / "lib" / "g16-compile-combinatronics.py"
    if comb_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("g16_compile_combinatronics", comb_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "stamp_compiled_artifact"):
                    stamp = mod.stamp_compiled_artifact(
                        binary,
                        comb=gate.get("combinatronics"),
                        compile_meta={"profile": profile, "launcher_kind": kind, "script": str(script)},
                    )
        except Exception:
            pass

    row = {
        "script": str(script),
        "binary": str(binary),
        "launcher_kind": kind,
        "fingerprint": fp,
        "profile": profile,
        "binary_bytes": binary.stat().st_size,
        "source_mtime_ns": script.stat().st_mtime_ns,
        "updated": _now(),
        "stamp": stamp,
    }
    entries[script.stem] = row
    manifest["updated"] = _now()
    _save(MANIFEST, manifest)

    return {
        "schema": "field-g16-script-compile/v1",
        "ok": True,
        "compiled": True,
        "binary": str(binary),
        "script": str(script),
        "launcher_kind": kind,
        "profile": profile,
        "binary_bytes": row["binary_bytes"],
        "combinatronics_gate": gate,
        "stamp": stamp,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def compile_batch(*, force: bool = False) -> dict[str, Any]:
    """Compile doctrine hot_scripts to lib/bin executables."""
    t0 = time.perf_counter()
    rows: list[dict[str, Any]] = []
    for rel in _doctrine().get("hot_scripts") or []:
        rows.append(compile_script(rel, force=force))
    ok = all(r.get("ok") or r.get("cached") for r in rows)
    return {
        "schema": "field-g16-script-compile-batch/v1",
        "updated": _now(),
        "ok": ok,
        "compiled": sum(1 for r in rows if r.get("compiled")),
        "cached": sum(1 for r in rows if r.get("cached")),
        "failed": sum(1 for r in rows if not r.get("ok")),
        "rows": rows,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
    }


def resolve_executable(script: str | Path) -> Path | None:
    """Return g16-compiled binary when fresh; else None."""
    if not ENABLED:
        return None
    src = _resolve_script(Path(script))
    if not src:
        return None
    binary = output_dir() / src.stem
    if not binary.is_file() or not os.access(binary, os.X_OK):
        return None
    manifest = _load(MANIFEST, {})
    row = (manifest.get("entries") or {}).get(src.stem) or {}
    kind = str(((_doctrine().get("extensions") or {}).get(src.suffix.lower()) or ""))
    fp = _source_fingerprint(src, kind)
    if row.get("fingerprint") != fp:
        return None
    try:
        if src.stat().st_mtime_ns > int(row.get("source_mtime_ns") or 0):
            return None
    except OSError:
        return None
    return binary


def resolve_argv(script: str | Path, args: list[str] | None = None) -> list[str]:
    """Command argv — prefer g16 executable launcher."""
    src = _resolve_script(Path(script))
    if not src:
        return [sys.executable, str(script), *(args or [])]
    exe = resolve_executable(src)
    if exe:
        return [str(exe), *(args or [])]
    if src.suffix.lower() in (".py", ".pyw"):
        driver, _ = _python_driver()
        return [driver, str(src), *(args or [])]
    if src.suffix.lower() in (".sh", ".bash"):
        return ["/bin/bash", str(src), *(args or [])]
    return [str(src), *(args or [])]


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    force = "--force" in sys.argv
    if cmd in ("json", "status", "panel"):
        doc = _load(MANIFEST, {"schema": "g16-script-compile-manifest/v1", "entries": {}})
        doc["g16"] = str(_g16_bin() or "")
        doc["enabled"] = ENABLED
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd == "compile" and len(sys.argv) > 2:
        doc = compile_script(sys.argv[2], force=force)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd in ("batch", "all", "hot"):
        doc = compile_batch(force=force)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "resolve" and len(sys.argv) > 2:
        print(json.dumps({"argv": resolve_argv(sys.argv[2], sys.argv[3:])}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["json", "compile PATH", "batch", "resolve PATH [args...]"],
        "flags": ["--force"],
    }, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())