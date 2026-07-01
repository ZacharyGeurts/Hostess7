#!/usr/bin/env python3
"""G16 stack numbers — plate/meld posture + language matrix (Grok16-only, no host JDK)."""
from __future__ import annotations

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
GROK16 = Path(os.environ.get("GROK16_ROOT", INSTALL / "Grok16"))
OUT = STATE / "g16-stack-numbers.json"


def _import(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _g16_version() -> str:
    g16 = GROK16 / "bin" / "g16"
    if not g16.is_file():
        return "missing"
    try:
        proc = subprocess.run([str(g16), "-dumpversion"], capture_output=True, text=True, timeout=8)
        return (proc.stdout or proc.stderr or "").strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired):
        return "unknown"


def _bench_java() -> dict[str, Any]:
    sample = GROK16 / "examples" / "languages" / "java" / "hello.java"
    jmod = _import(GROK16 / "lib" / "g16-java-compile.py", "nums_java")
    if not jmod or not sample.is_file():
        return {"ok": False, "error": "java_lane_missing"}
    body = sample.read_text(encoding="utf-8")
    comp = jmod.compile_source(body, lang="java")
    run: dict[str, Any] = {"ok": False}
    sec = _import(INSTALL / "lib" / "g16-secure-chamber.py", "nums_sec")
    if sec and hasattr(sec, "run_path"):
        t0 = time.perf_counter()
        run = sec.run_path(str(sample), lang="java")
        run["run_ms"] = int((time.perf_counter() - t0) * 1000)
    return {
        "ok": bool(comp.get("ok") and run.get("ok")),
        "compiler": "g16",
        "host_jdk": False,
        "compile_ms": comp.get("compile_ms"),
        "lane": comp.get("lane"),
        "stdout": (run.get("stdout") or "")[:200],
        "compile": {k: comp.get(k) for k in ("ok", "compiler", "compile_ms", "lane")},
        "run": {k: run.get(k) for k in ("ok", "runner", "run_ms", "returncode")},
    }


def _plate_meld_numbers() -> dict[str, Any]:
    meld = _import(INSTALL / "lib" / "field-plate-meld.py", "nums_meld")
    orch = _import(INSTALL / "lib" / "field-plate-meld-orchestrator.py", "nums_orch")
    out: dict[str, Any] = {}
    if meld and hasattr(meld, "posture"):
        t0 = time.perf_counter()
        doc = meld.posture()
        out["meld_ms"] = int((time.perf_counter() - t0) * 1000)
        out["plate_count"] = len(doc.get("plates") or doc.get("sources") or [])
        out["chain_hash"] = (doc.get("chain") or {}).get("hash", "")[:16]
        out["generation"] = doc.get("generation")
    if orch and hasattr(orch, "posture"):
        t0 = time.perf_counter()
        odoc = orch.posture()
        out["orchestrator_ms"] = int((time.perf_counter() - t0) * 1000)
        out["surface_count"] = len(odoc.get("surfaces") or [])
        out["bottom_cpu"] = odoc.get("bottom_cpu")
    return out


def _compiler_bench_sample() -> dict[str, Any]:
    bench = _import(INSTALL / "lib" / "g16-compiler-bench.py", "nums_bench")
    path = STATE / "g16-compiler-bench.json"
    if path.is_file():
        doc = json.loads(path.read_text(encoding="utf-8"))
        return {
            "ok": doc.get("ok"),
            "elapsed_ms": doc.get("elapsed_ms"),
            "totals": doc.get("totals"),
            "by_driver": {
                k: {"compile_ok": v.get("compile_ok"), "interp_ok": v.get("interp_ok"),
                    "compile_ms_avg": v.get("compile_ms_avg"), "interp_ms_avg": v.get("interp_ms_avg")}
                for k, v in (doc.get("by_driver") or {}).items()
            },
            "path": str(path),
            "cached": True,
            "hint": "Run: scripts/g16-compiler-bench.py for full 57-language suite",
        }
    return {
        "ok": False,
        "error": "bench_not_run",
        "hint": "Run: python3 scripts/g16-compiler-bench.py",
        "path": str(path),
    }


def _language_matrix_sample() -> dict[str, Any]:
    matrix = _import(INSTALL / "lib" / "g16-language-test-matrix.py", "nums_matrix")
    if not matrix or not hasattr(matrix, "discover_matrix"):
        return {"ok": False, "error": "matrix_missing"}
    rows = matrix.discover_matrix()
    with_sample = sum(1 for r in rows if r.get("has_sample"))
    return {
        "languages": len(rows),
        "with_sample": with_sample,
        "java_row": next((r for r in rows if r.get("lang") == "java"), None),
    }


def build_numbers() -> dict[str, Any]:
    doc = {
        "schema": "g16-stack-numbers/v1",
        "updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ok": True,
        "consolidated": {
            "canonical_root": "NewLatest",
            "retired": ["ZOCR", "ZNEWOCR", "znetwork", "host_jdk"],
        },
        "grok16": {
            "version": _g16_version(),
            "root": str(GROK16),
            "g16_binary": str(GROK16 / "bin" / "g16"),
            "host_jdk": False,
        },
        "java_lane": _bench_java(),
        "plate_meld": _plate_meld_numbers(),
        "language_matrix": _language_matrix_sample(),
        "compiler_bench": _compiler_bench_sample(),
    }
    doc["ok"] = bool(doc["java_lane"].get("ok")) and GROK16.joinpath("bin/g16").is_file()
    return doc


def main() -> int:
    doc = build_numbers()
    STATE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False, indent=2))
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())