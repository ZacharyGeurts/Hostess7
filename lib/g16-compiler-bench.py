#!/usr/bin/env python3
"""G16 compiler & interpreter benchmark — every driver, every language, timed numbers."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
GROK16 = Path(os.environ.get("GROK16_ROOT", INSTALL / "Grok16"))
EXAMPLES = GROK16 / "examples" / "languages"
OUT_JSON = STATE / "g16-compiler-bench.json"
OUT_JSONL = STATE / "g16-compiler-bench.jsonl"

_COMPILER_DRIVERS = frozenset({
    "g16-cc", "g16-cxx", "g16-as", "g16-gfortran", "g16-rust", "g16-go", "g16-zig",
    "g16-gdc", "g16-gnat", "g16-objc", "g16-qbasic", "g16-fpc", "g16-aml",
})
_INTERP_DRIVERS = frozenset({"g16-interp", "gpy-16"})


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
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


def _import_mod(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _append_jsonl(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with OUT_JSONL.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def discover_bench_matrix() -> list[dict[str, Any]]:
    doc = _load(GROK16 / "data" / "grok16-languages.json", {})
    langs = doc.get("languages") or {}
    rows: list[dict[str, Any]] = []
    for lang_id in sorted(langs.keys()):
        row = langs[lang_id]
        driver = str(row.get("driver") or "g16-interp")
        folder = EXAMPLES / lang_id
        hello: Path | None = None
        if folder.is_dir():
            launch = folder / f"{lang_id}.launch"
            if launch.is_file():
                manifest = _load(launch, {})
                entry = manifest.get("entry")
                if entry and (folder / str(entry)).is_file():
                    hello = folder / str(entry)
            if not hello:
                for p in sorted(folder.glob("hello.*")):
                    if p.is_file():
                        hello = p
                        break
        rows.append({
            "lang": lang_id,
            "driver": driver,
            "runtime": row.get("runtime"),
            "uncompiled": bool(row.get("uncompiled", True)),
            "secure_chamber": row.get("secure_chamber", True),
            "sample": str(hello) if hello else None,
            "has_sample": bool(hello),
            "bench_compile": True,
            "bench_interp": driver in _INTERP_DRIVERS or lang_id in ("java", "kotlin", "javascript", "typescript"),
        })
    return rows


def _bench_compile(lang: str, sample: Path, *, native: Any) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        body = sample.read_text(encoding="utf-8")
        rep = native.compile_source(body, lang=lang, out_name=f"bench_{lang}")
        ms = int((time.perf_counter() - t0) * 1000)
        return {
            "ok": bool(rep.get("ok")),
            "ms": rep.get("compile_ms") or ms,
            "driver": rep.get("driver") or "g16",
            "lane": rep.get("lane"),
            "compiler": rep.get("compiler", "g16"),
            "binary": rep.get("binary"),
            "error": rep.get("error"),
        }
    except Exception as exc:
        return {"ok": False, "ms": int((time.perf_counter() - t0) * 1000), "error": type(exc).__name__}


def _bench_run_binary(binary: str | None) -> dict[str, Any]:
    if not binary or not Path(binary).is_file():
        return {"ok": False, "ms": 0, "error": "no_binary"}
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [binary], capture_output=True, text=True, timeout=30,
            env={**os.environ, "GROK16_ROOT": str(GROK16)},
        )
        return {
            "ok": proc.returncode == 0,
            "ms": int((time.perf_counter() - t0) * 1000),
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[:200],
            "stderr": (proc.stderr or "")[:400],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "ms": int((time.perf_counter() - t0) * 1000), "error": "timeout"}
    except OSError as exc:
        return {"ok": False, "ms": int((time.perf_counter() - t0) * 1000), "error": str(exc)}


def _field_python() -> str:
    """Prefer working python3 over a broken pythong shim on PATH."""
    gpy = shutil.which("pythong")
    if gpy:
        try:
            probe = subprocess.run([gpy, "-c", "pass"], capture_output=True, timeout=5)
            if probe.returncode == 0:
                return gpy
        except (OSError, subprocess.TimeoutExpired):
            pass
    return sys.executable


def _bench_gpy16(sample: Path) -> dict[str, Any]:
    gpy = GROK16 / "bin" / "gpy-16"
    py = _field_python()
    runner = str(gpy) if gpy.is_file() else py
    argv = [runner, str(sample)] if gpy.is_file() else [py, str(sample)]
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60, cwd=str(sample.parent))
        return {
            "ok": proc.returncode == 0,
            "ms": int((time.perf_counter() - t0) * 1000),
            "driver": "gpy-16",
            "returncode": proc.returncode,
            "stdout": (proc.stdout or "")[:200],
            "stderr": (proc.stderr or "")[:400],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "ms": int((time.perf_counter() - t0) * 1000), "driver": "gpy-16", "error": "timeout"}


def _bench_interp_native(lang: str, sample: Path) -> dict[str, Any]:
    native_py = GROK16 / "lib" / "g16-native-compile.py"
    py = sys.executable
    env = {**os.environ, "GROK16_ROOT": str(GROK16), "G16_PREFIX": str(GROK16)}
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [py, str(native_py), "run", str(sample), "--lang", lang],
            capture_output=True, text=True, timeout=180, env=env,
        )
        ms = int((time.perf_counter() - t0) * 1000)
        if proc.stdout.strip():
            try:
                doc = json.loads(proc.stdout)
                return {
                    "ok": bool(doc.get("ok")),
                    "ms": doc.get("interp_ms") or ms,
                    "compile_ms": doc.get("compile_ms"),
                    "run_ms": doc.get("run_ms"),
                    "driver": "g16-interp",
                    "stdout": (doc.get("stdout") or "")[:200],
                    "stderr": (doc.get("stderr") or "")[:400],
                }
            except json.JSONDecodeError:
                pass
        return {
            "ok": proc.returncode == 0,
            "ms": ms,
            "driver": "g16-interp",
            "stderr": (proc.stderr or "")[:400],
            "error": "interp_failed" if proc.returncode != 0 else None,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "ms": int((time.perf_counter() - t0) * 1000), "driver": "g16-interp", "error": "timeout"}


def _bench_special_interp(lang: str, sample: Path) -> dict[str, Any]:
    py = _field_python()
    t0 = time.perf_counter()
    if lang == "ammolang":
        script = INSTALL / "lib" / "field-ammolang.py"
        argv = [py, str(script), "run", str(sample), "--live"]
    elif lang == "field":
        script = INSTALL / "lib" / "field-plate-field.py"
        argv = [py, str(script), "json"]
    else:
        return {"ok": False, "ms": 0, "error": "unknown_special"}
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
        return {
            "ok": proc.returncode == 0,
            "ms": int((time.perf_counter() - t0) * 1000),
            "driver": "g16-interp",
            "stdout": (proc.stdout or "")[:200],
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "ms": int((time.perf_counter() - t0) * 1000), "driver": "g16-interp", "error": "timeout"}


def bench_language(row: dict[str, Any], *, native: Any) -> dict[str, Any]:
    lang = row["lang"]
    sample_s = row.get("sample")
    driver = row.get("driver")
    result: dict[str, Any] = {
        "lang": lang,
        "driver": driver,
        "sample": sample_s,
        "ok": False,
        "compile": None,
        "run": None,
        "interp": None,
    }
    if not sample_s:
        result["error"] = "no_sample"
        return result

    sample = Path(sample_s)
    content = sample.read_text(encoding="utf-8", errors="replace")

    compile_bench = _bench_compile(lang, sample, native=native)
    result["compile"] = compile_bench

    if compile_bench.get("binary"):
        result["run"] = _bench_run_binary(str(compile_bench["binary"]))

    if driver == "gpy-16" or lang == "python":
        result["interp"] = _bench_gpy16(sample)
    elif lang in ("ammolang", "field"):
        result["interp"] = _bench_special_interp(lang, sample)
    elif row.get("bench_interp") or driver == "g16-interp":
        result["interp"] = _bench_interp_native(lang, sample)
    elif compile_bench.get("ok") and result.get("run"):
        c_ms = int(compile_bench.get("ms") or 0)
        r_ms = int((result["run"] or {}).get("ms") or 0)
        result["interp"] = {
            "ok": bool((result["run"] or {}).get("ok")),
            "ms": c_ms + r_ms,
            "compile_ms": c_ms,
            "run_ms": r_ms,
            "driver": driver,
            "note": "compile+run (compiler driver)",
        }

    _gate_only = frozenset({
        "shell", "plaintext", "sql", "verilog", "linux", "economics",
        "html", "css", "json", "yaml", "markdown", "toml", "xml",
        "dockerfile", "makefile", "cmake", "glsl", "graphql", "ini",
        "log", "diff", "scss", "powershell", "vbscript", "cobol_copy",
        "wat", "wasm",
    })
    run_ok = bool((result.get("run") or {}).get("ok")) or bool((result.get("run") or {}).get("gate_only"))
    result["ok"] = bool(
        compile_bench.get("ok")
        and (
            (result.get("interp") or {}).get("ok")
            or run_ok
            or lang in _gate_only
        )
    )
    return result


def _aggregate_by_driver(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_driver: dict[str, dict[str, Any]] = {}
    for r in results:
        driver = str(r.get("driver") or "unknown")
        bucket = by_driver.setdefault(driver, {
            "driver": driver,
            "languages": [],
            "compile_ok": 0,
            "compile_fail": 0,
            "interp_ok": 0,
            "interp_fail": 0,
            "interp_na": 0,
            "compile_ms_total": 0,
            "compile_ms_min": None,
            "compile_ms_max": 0,
            "interp_ms_total": 0,
            "interp_ms_min": None,
            "interp_ms_max": 0,
        })
        bucket["languages"].append(r["lang"])
        comp = r.get("compile") or {}
        if comp.get("ok"):
            bucket["compile_ok"] += 1
            ms = int(comp.get("ms") or 0)
            bucket["compile_ms_total"] += ms
            bucket["compile_ms_min"] = ms if bucket["compile_ms_min"] is None else min(bucket["compile_ms_min"], ms)
            bucket["compile_ms_max"] = max(bucket["compile_ms_max"], ms)
        elif comp:
            bucket["compile_fail"] += 1
        interp = r.get("interp")
        if interp is None:
            bucket["interp_na"] += 1
        elif interp.get("ok"):
            bucket["interp_ok"] += 1
            ims = int(interp.get("ms") or 0)
            bucket["interp_ms_total"] += ims
            bucket["interp_ms_min"] = ims if bucket["interp_ms_min"] is None else min(bucket["interp_ms_min"], ims)
            bucket["interp_ms_max"] = max(bucket["interp_ms_max"], ims)
        else:
            bucket["interp_fail"] += 1
    for bucket in by_driver.values():
        n = bucket["compile_ok"] or 1
        bucket["compile_ms_avg"] = int(bucket["compile_ms_total"] / n)
        ni = bucket["interp_ok"] or 1
        bucket["interp_ms_avg"] = int(bucket["interp_ms_total"] / ni) if bucket["interp_ok"] else 0
    return by_driver


def run_bench(
    *,
    langs: list[str] | None = None,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    native = _import_mod(GROK16 / "lib" / "g16-native-compile.py", "g16_bench_native")
    if not native:
        return {"ok": False, "error": "g16_native_compile_missing"}

    if OUT_JSONL.is_file():
        OUT_JSONL.unlink()

    matrix = discover_bench_matrix()
    if langs:
        want = {x.lower() for x in langs}
        matrix = [r for r in matrix if r["lang"] in want]

    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    compile_pass = compile_fail = interp_pass = interp_fail = 0

    for i, row in enumerate(matrix, 1):
        if not row.get("has_sample"):
            rep = {"lang": row["lang"], "driver": row["driver"], "ok": False, "error": "no_sample"}
            results.append(rep)
            _append_jsonl({"ts": _now(), "event": "skip", **rep})
            continue

        rep = bench_language(row, native=native)
        results.append(rep)
        if (rep.get("compile") or {}).get("ok"):
            compile_pass += 1
        else:
            compile_fail += 1
        interp = rep.get("interp")
        if interp is not None:
            if interp.get("ok"):
                interp_pass += 1
            else:
                interp_fail += 1
        _append_jsonl({
            "ts": _now(),
            "event": "bench",
            "index": i,
            "total": len(matrix),
            **{k: v for k, v in rep.items()},
        })
        if on_progress:
            on_progress({"done": i, "total": len(matrix), "lang": row["lang"], "result": rep})

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    by_driver = _aggregate_by_driver(results)
    doc = {
        "schema": "g16-compiler-bench/v1",
        "updated": _now(),
        "ok": compile_fail == 0 and interp_fail == 0,
        "grok16_root": str(GROK16),
        "host_toolchain": False,
        "elapsed_ms": elapsed_ms,
        "totals": {
            "languages": len(matrix),
            "with_sample": sum(1 for r in matrix if r.get("has_sample")),
            "compile_pass": compile_pass,
            "compile_fail": compile_fail,
            "interp_pass": interp_pass,
            "interp_fail": interp_fail,
        },
        "by_driver": by_driver,
        "results": results,
    }
    STATE.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="G16 compiler & interpreter benchmark")
    ap.add_argument("--lang", action="append", help="Bench only these languages (repeatable)")
    ap.add_argument("--json", action="store_true", help="Print full JSON to stdout")
    ap.add_argument("--quick", action="store_true", help="First 8 languages with samples only")
    args = ap.parse_args()

    langs = args.lang
    if args.quick:
        matrix = discover_bench_matrix()
        langs = [r["lang"] for r in matrix if r.get("has_sample")][:8]

    doc = run_bench(langs=langs)
    if args.json:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        t = doc.get("totals") or {}
        print(f"g16-compiler-bench: compile {t.get('compile_pass')}/{t.get('with_sample')} "
              f"interp {t.get('interp_pass')} pass · {doc.get('elapsed_ms')}ms")
        print(f"written: {OUT_JSON}")
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())