#!/usr/bin/env pythong
"""Singular field plane — chamber → depth-0 fields, trim excess, auto-convert, run on belt."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
DOCTRINE = QUEEN / "data" / "queen-launch-singular-field.json"
PLANE_ROOT = STATE / "launch-singular-plane"
SCHEMA = "queen-singular-field/v1"

NATIVE_EXTS = (".cpp", ".cxx", ".cc", ".c", ".comp")
CXX_FLAGS = ("-std=gnu++23", "-O2", "-march=native", "-fPIE", "-pie")
C_FLAGS = ("-std=gnu17", "-O2", "-march=native", "-fPIE", "-pie", "-lm")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _grok16_root() -> Path:
    _SG_PATHS_LIB = Path(__file__).resolve().parents[2] / "lib"
    if str(_SG_PATHS_LIB) not in sys.path:
        sys.path.insert(0, str(_SG_PATHS_LIB))
    from sg_paths import grok16_root
    return grok16_root()


def _g16_bin() -> Path | None:
    p = _grok16_root() / "bin" / "g16"
    return p if p.is_file() else None


def _compile_combinatronics_mod() -> Any | None:
    comb_py = _grok16_root() / "lib" / "g16-compile-combinatronics.py"
    if not comb_py.is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("g16_compile_combinatronics", comb_py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _host_gxx() -> str:
    from shutil import which
    for c in ("g++", "g++-13", "g++-12", "/usr/bin/g++"):
        if c.startswith("/") and Path(c).is_file():
            return c
        w = which(c)
        if w:
            return w
    return "g++"


def _host_gcc() -> str:
    from shutil import which
    for c in ("gcc", "gcc-13", "gcc-12", "/usr/bin/gcc"):
        if c.startswith("/") and Path(c).is_file():
            return c
        w = which(c)
        if w:
            return w
    return "gcc"


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {"schema": SCHEMA, "policy": {"field_depth": 0}})


def compile_mode_enabled() -> bool:
    return os.environ.get("QUEEN_LAUNCH_COMPILE", "").strip().lower() in (
        "1", "true", "yes", "on",
    ) or os.environ.get("G16_FORCE_COMPILE", "").strip().lower() in (
        "1", "true", "yes", "on",
    )


def _chamber_mod():
    import importlib.util
    spec = importlib.util.spec_from_file_location("qlc", QUEEN / "lib" / "queen-launch-chamber.py")
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _walk_rels(root: Path) -> list[str]:
    ch = _chamber_mod()
    if ch:
        rels, _ = ch._walk_chamber(root)
        return rels
    return []


def _trim_verdict(rel: str, entry: str, doc: dict[str, Any]) -> str:
    trim = doc.get("trim") or {}
    name = Path(rel).name
    suffix = Path(rel).suffix.lower()
    if rel == entry or rel.replace("\\", "/") == entry.replace("\\", "/"):
        return "KEEP_ENTRY"
    if name in set(trim.get("strip_names") or []):
        return "STRIP"
    if suffix in set(trim.get("strip_suffixes") or []):
        return "STRIP"
    if name in set(trim.get("keep_names") or []):
        return "KEEP"
    if suffix in set(trim.get("keep_suffixes") or []):
        return "KEEP"
    if suffix in (".launch",):
        return "STRIP_META"
    return "STRIP_EXCESS"


def project_singular_fields(
    root: Path,
    *,
    entry: str,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map chamber files → depth-0 fields on the singular plane."""
    root = root.resolve()
    doc = _doctrine()
    rels = _walk_rels(root)
    fields: list[dict[str, Any]] = []
    stripped = 0
    for rel in rels:
        verdict = _trim_verdict(rel, entry, doc)
        if verdict.startswith("STRIP"):
            stripped += 1
            continue
        role = "plane_entry" if rel == entry else "support"
        if Path(rel).suffix.lower() in NATIVE_EXTS and Path(entry).stem == Path(rel).stem:
            role = "native_sibling"
        fields.append({
            "path": rel,
            "depth": 0,
            "field_depth": 0,
            "role": role,
            "verdict": verdict,
        })
    fields.sort(key=lambda f: f["path"])
    return {
        "schema": SCHEMA,
        "field_depth": 0,
        "single_plane": True,
        "chamber_root": str(root),
        "entry": entry,
        "fields": fields,
        "field_count": len(fields),
        "stripped_excess": stripped,
        "total_seen": len(rels),
        "updated": _ts(),
        "manifest": manifest or {},
    }


def _reuse_exec_plane_binary(source: Path) -> Path | None:
    """Reuse field-exec-stage plane when chamber matches a staged speed-demo."""
    if source.stem != "speed_demo":
        return None
    plane_dir = _grok16_root() / "data" / "bench" / "exec-plane"
    for name in ("cxx_host_o2", "cmake_host_o2", "c_host_o2", "cxx_g16_belt_2", "c_g16_belt_2"):
        candidate = plane_dir / name
        if not candidate.is_file():
            continue
        try:
            if candidate.stat().st_mtime >= source.stat().st_mtime:
                return candidate
        except OSError:
            continue
    return None


def _prefer_plane_source(root: Path, entry: str) -> tuple[Path, str]:
    """Pick native sibling for plane convert when present (amazing speedup path)."""
    stem = Path(entry).stem
    for ext in (".cpp", ".cxx", ".cc", ".c", ".comp"):
        sib = root / f"{stem}{ext}"
        if sib.is_file():
            kind = "cxx" if ext in (".cpp", ".cxx", ".cc", ".hpp", ".comp") else "c"
            return sib, kind
    ep = root / entry
    ext = ep.suffix.lower()
    if ext in (".cpp", ".cxx", ".cc", ".comp"):
        return ep, "cxx"
    if ext == ".c":
        return ep, "c"
    if ext in (".py", ".pyw", ".gpy"):
        return ep, "python"
    if ext in (".sh", ".bash"):
        return ep, "shell"
    return ep, "python"


def _chamber_fingerprint(root: Path, entry: str, fields: list[dict[str, Any]]) -> str:
    parts = [str(root), entry]
    for f in fields:
        rel = f["path"]
        p = root / rel
        try:
            st = p.stat()
            parts.append(f"{rel}:{st.st_mtime_ns}:{st.st_size}")
        except OSError:
            parts.append(f"{rel}:missing")
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:24]


def _parse_ops(stdout: str) -> float | None:
    for line in reversed(stdout.splitlines()):
        if line.startswith("speed_demo") and "ops_per_sec=" in line:
            m = re.search(r"ops_per_sec=([0-9.eE+-]+)", line)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    pass
    return None


def auto_convert_plane(
    root: Path,
    source: Path,
    kind: str,
    cache_dir: Path,
    *,
    profile: str = "belt_2_0",
    allow_compile: bool = False,
) -> dict[str, Any]:
    """Wave-convert source to a plane runner binary (cached). Compile only when allowed."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    out_bin = cache_dir / f"plane-{source.stem}"
    t0 = time.perf_counter()

    if kind == "python":
        if allow_compile or compile_mode_enabled():
            nexus = _grok16_root().parent / "NewLatest"
            if not (nexus / "lib" / "field-g16-script-compile.py").is_file():
                nexus = Path(os.environ.get("NEXUS_INSTALL_ROOT", nexus))
            compile_py = nexus / "lib" / "field-g16-script-compile.py"
            if compile_py.is_file():
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("field_g16_script_compile", compile_py)
                    if spec and spec.loader:
                        sc = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(sc)
                        if hasattr(sc, "compile_script"):
                            rep = sc.compile_script(
                                source,
                                force=os.environ.get("G16_FORCE_COMPILE", "").strip().lower() in ("1", "true", "yes", "on"),
                            )
                            if rep.get("ok") and rep.get("binary"):
                                out_bin = Path(str(rep["binary"]))
                                if out_bin.is_file():
                                    convert_ms = round((time.perf_counter() - t0) * 1000, 2)
                                    return {
                                        "ok": True,
                                        "plane_kind": "binary",
                                        "runner": str(out_bin),
                                        "runtime": "g16_script_launcher",
                                        "toolchain": "g16_script_compile",
                                        "binary_bytes": out_bin.stat().st_size,
                                        "convert_ms": convert_ms,
                                        "source": str(source),
                                        "compile_report": rep,
                                    }
                except Exception:
                    pass
        return {
            "ok": True,
            "plane_kind": "interpreter",
            "runner": str(source),
            "runtime": "python",
            "convert_ms": 0,
            "message": "Python on gpy interpreter; enable Compile mode for g16 executable launcher",
        }

    if kind in ("cxx", "c"):
        bsp = None
        try:
            import importlib.util
            bsp_py = _grok16_root() / "lib" / "field_exec_bsp.py"
            if bsp_py.is_file():
                spec = importlib.util.spec_from_file_location("field_exec_bsp", bsp_py)
                if spec and spec.loader:
                    bsp = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(bsp)
        except Exception:
            bsp = None
        if bsp:
            plane = bsp.exec_plane(_grok16_root())
            for case_id in (
                "cxx_host_o2", "c_host_o2", "cmake_host_o2", "cxx_g16_belt_2", "c_g16_belt_2"
            ):
                hit, compile_ms, note = bsp.bsp_try_reuse(
                    plane,
                    case_id=case_id,
                    sources=[source],
                    profile=case_id,
                )
                if hit:
                    try:
                        import shutil
                        shutil.copy2(hit, out_bin)
                        out_bin.chmod(out_bin.stat().st_mode | 0o111)
                        convert_ms = round((time.perf_counter() - t0) * 1000, 2)
                        return {
                            "ok": True,
                            "plane_kind": "binary",
                            "runner": str(out_bin),
                            "runtime": "native",
                            "toolchain": case_id,
                            "binary_bytes": out_bin.stat().st_size,
                            "convert_ms": convert_ms,
                            "source": str(source),
                            "reused_exec_plane": str(hit),
                            "bsp_note": note,
                        }
                    except OSError:
                        pass

        reused = _reuse_exec_plane_binary(source)
        if reused:
            try:
                import shutil
                shutil.copy2(reused, out_bin)
                out_bin.chmod(out_bin.stat().st_mode | 0o111)
                convert_ms = round((time.perf_counter() - t0) * 1000, 2)
                return {
                    "ok": True,
                    "plane_kind": "binary",
                    "runner": str(out_bin),
                    "runtime": "native",
                    "toolchain": reused.name,
                    "binary_bytes": out_bin.stat().st_size,
                    "convert_ms": convert_ms,
                    "source": str(source),
                    "reused_exec_plane": str(reused),
                }
            except OSError:
                pass

        if not allow_compile and not compile_mode_enabled():
            return {
                "ok": False,
                "error": "compile_disabled",
                "message": "Organized field runs without compile; use Compile mode or exec-bsp-bench",
                "source": str(source),
            }

        comb_mod = _compile_combinatronics_mod()
        comb_gate: dict[str, Any] = {}
        if comb_mod and hasattr(comb_mod, "compile_gate"):
            try:
                comb_gate = comb_mod.compile_gate(profile=profile)
                if comb_gate.get("profile"):
                    profile = str(comb_gate["profile"])
            except Exception:
                comb_gate = {}

        g16 = _g16_bin()
        flags_py = _grok16_root() / "scripts" / "grok16-profile-flags.py"
        extra: list[str] = []
        if flags_py.is_file():
            try:
                proc = subprocess.run(
                    [sys.executable, str(flags_py), profile, kind],
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                    env={**os.environ, "GROK16_ROOT": str(_grok16_root()), "G16_PREFIX": str(_grok16_root())},
                )
                if proc.stdout.strip():
                    extra = proc.stdout.strip().split()
            except (OSError, subprocess.TimeoutExpired):
                pass

        tag = f"singular_{kind}"
        base_flags = list(CXX_FLAGS if kind == "cxx" else C_FLAGS)
        compilers: list[tuple[str, list[str]]] = []
        host = _host_gxx() if kind == "cxx" else _host_gcc()
        compilers.append(
            ("host_o2", [host, *base_flags, f'-DTOOLCHAIN_TAG="{tag}"', "-o", str(out_bin), str(source)]),
        )
        if g16:
            g16_flags = extra or (["-std=gnu++23", "-O3", "-march=native"] if kind == "cxx" else ["-std=gnu17", "-O3", "-march=native"])
            compilers.append(
                ("g16_belt_2", [str(g16), *g16_flags, f'-DTOOLCHAIN_TAG="{tag}"', "-o", str(out_bin), str(source)]),
            )

        last_err = ""
        for tag, cmd in compilers:
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, check=False, cwd=str(root))
            except (OSError, subprocess.TimeoutExpired) as exc:
                last_err = str(exc)
                continue
            if proc.returncode == 0 and out_bin.is_file():
                convert_ms = round((time.perf_counter() - t0) * 1000, 2)
                stamp: dict[str, Any] = {}
                if comb_mod and hasattr(comb_mod, "stamp_compiled_artifact"):
                    try:
                        stamp = comb_mod.stamp_compiled_artifact(
                            out_bin,
                            comb=comb_gate.get("combinatronics"),
                            compile_meta={
                                "profile": profile,
                                "toolchain": tag,
                                "convert_ms": convert_ms,
                                "source": str(source),
                            },
                        )
                    except Exception:
                        stamp = {}
                return {
                    "ok": True,
                    "plane_kind": "binary",
                    "runner": str(out_bin),
                    "runtime": "native",
                    "toolchain": tag,
                    "profile": profile,
                    "binary_bytes": out_bin.stat().st_size,
                    "convert_ms": convert_ms,
                    "source": str(source),
                    "combinatronics": {
                        "optimal_at_creation": True,
                        "ideal_profile": profile,
                        "gate": comb_gate or None,
                        "stamp": stamp or None,
                    },
                }
            last_err = (proc.stderr or proc.stdout or "")[-1500:]

        return {"ok": False, "error": "plane_convert_failed", "detail": last_err[:800]}

    return {"ok": False, "error": "unsupported_kind", "kind": kind}


def resolve_plane_runner(
    root: Path,
    entry: str,
    singular: dict[str, Any],
    *,
    profile: str = "belt_2_0",
    force_reconvert: bool = False,
    allow_compile: bool = False,
) -> dict[str, Any]:
    fp = _chamber_fingerprint(root, entry, singular.get("fields") or [])
    cache_dir = PLANE_ROOT / fp
    meta_path = cache_dir / "plane.json"
    source, kind = _prefer_plane_source(root, entry)

    if not force_reconvert and meta_path.is_file():
        meta = _load(meta_path, {})
        runner = Path(meta.get("runner") or "")
        if meta.get("ok") and runner.is_file():
            src = Path(meta.get("source") or source)
            try:
                if src.stat().st_mtime <= runner.stat().st_mtime:
                    meta["cache_hit"] = True
                    meta["fingerprint"] = fp
                    return meta
            except OSError:
                pass

    conv = auto_convert_plane(
        root, source, kind, cache_dir, profile=profile, allow_compile=allow_compile
    )
    doc = {
        **conv,
        "schema": SCHEMA,
        "fingerprint": fp,
        "field_depth": 0,
        "single_plane": True,
        "singular_field": singular,
        "cache_hit": False,
        "updated": _ts(),
    }
    if conv.get("ok"):
        meta_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def run_on_singular_plane(
    path: Path,
    *,
    timeout: int = 120,
    target_sec: int | None = None,
    allow_compile: bool | None = None,
) -> dict[str, Any]:
    """Project chamber → trim → auto-convert → execute on single plane."""
    ch = _chamber_mod()
    if not ch:
        return {"ok": False, "error": "chamber_unavailable"}

    if path.suffix.lower() == ".launch" and path.is_file():
        manifest = ch.load_launch_manifest(path)
        root = Path(manifest["_resolved_root"])
        entry = str(manifest.get("entry") or "")
    elif path.is_dir():
        manifest = ch.build_manifest(path)
        root = path
        entry = str(manifest.get("entry") or "")
    else:
        return {"ok": False, "error": "not_launch_or_folder"}

    if not entry:
        return {"ok": False, "error": "no_entry"}

    if allow_compile is None:
        allow_compile = compile_mode_enabled()
    singular = project_singular_fields(root, entry=entry, manifest=manifest)
    plane = resolve_plane_runner(root, entry, singular, allow_compile=allow_compile)
    if not plane.get("ok"):
        return {"ok": False, "error": plane.get("error"), "plane": plane, "singular_field": singular}

    target = target_sec or int(os.environ.get("SPEED_DEMO_TARGET_SEC", "10"))
    env = {
        **os.environ,
        "QUEEN_LAUNCH_SINGULAR_FIELD": "1",
        "NEXUS_SINGLE_FIELD_DEPTH": "1",
        "NEXUS_CHAMBER_ROOT": str(root),
        "QUEEN_SINGULAR_PLANE": "1",
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(QUEEN),
        "NEXUS_STATE_DIR": str(STATE),
        "SPEED_DEMO_TARGET_SEC": str(target),
        "TOOLCHAIN_TAG": str(plane.get("toolchain") or plane.get("runtime") or "singular_plane"),
    }

    if plane.get("plane_kind") == "binary":
        cmd = [str(plane["runner"])]
    elif plane.get("runtime") == "python":
        py = ch._resolve_pythong()
        cmd = [py, str(plane["runner"])]
    elif plane.get("runtime") == "shell":
        cmd = ["/bin/bash", str(plane["runner"])]
    else:
        cmd = [str(plane["runner"])]

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "singular_field": singular,
            "plane": plane,
        }

    wall_ms = round((time.perf_counter() - t0) * 1000, 2)
    stdout = proc.stdout or ""
    ops = _parse_ops(stdout)

    return {
        "ok": proc.returncode == 0,
        "singular_field": True,
        "field_depth": 0,
        "single_plane": True,
        "returncode": proc.returncode,
        "cmd": cmd,
        "cwd": str(root),
        "plane": plane,
        "singular": singular,
        "stdout_tail": stdout[-4000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
        "wall_ms": wall_ms,
        "ops_per_sec": ops,
        "trimmed_excess": singular.get("stripped_excess"),
        "field_count": singular.get("field_count"),
        "cache_hit": plane.get("cache_hit"),
        "convert_ms": plane.get("convert_ms"),
        "message": (
            f"Singular plane {'ok' if proc.returncode == 0 else 'fail'} · "
            f"{plane.get('toolchain') or plane.get('runtime')} · "
            f"{f'{ops:,.0f} ops/s' if ops else 'ops n/a'}"
            + (f" · cache hit" if plane.get("cache_hit") else f" · converted {plane.get('convert_ms')}ms")
        ),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Queen launch singular field plane")
    ap.add_argument("cmd", choices=["project", "plane", "run", "json"])
    ap.add_argument("path", nargs="?", default="")
    ap.add_argument("--timeout", type=int, default=120)
    args = ap.parse_args()
    path = Path(args.path).expanduser().resolve() if args.path else Path.cwd()

    if args.cmd == "project":
        ch = _chamber_mod()
        m = ch.build_manifest(path) if ch and path.is_dir() else {}
        out = project_singular_fields(path, entry=m.get("entry", ""), manifest=m)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "plane":
        ch = _chamber_mod()
        m = ch.build_manifest(path) if ch and path.is_dir() else {}
        s = project_singular_fields(path, entry=m.get("entry", ""), manifest=m)
        p = resolve_plane_runner(path, m.get("entry", ""), s)
        print(json.dumps({"singular": s, "plane": p}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd in ("run", "json"):
        out = run_on_singular_plane(path, timeout=args.timeout)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())