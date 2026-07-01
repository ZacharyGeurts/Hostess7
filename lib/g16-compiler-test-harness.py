#!/usr/bin/env python3
"""G16 compiler test harness — halt/issue detection, CHIPs compatibility, every language."""
from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
GROK16 = Path(os.environ.get("GROK16_ROOT", INSTALL / "Grok16"))
DOCTRINE = INSTALL / "data" / "g16-compiler-test-doctrine.json"
CHIPS_MANIFEST = INSTALL / "Queen" / "data" / "chips-g16-manifest.json"
OUT_JSON = STATE / "g16-compiler-test.json"
OUT_JSONL = STATE / "g16-compiler-test.jsonl"
CHIPS_HEALTH = STATE / "g16-chips-lang-health.json"
LIBRARY = INSTALL / "library" / "dewey" / "000-computer-science"


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


def _import(path: Path, name: str) -> Any | None:
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


def _book_exists(prefix: str, lang: str) -> bool:
    book = LIBRARY / f"{prefix}_{lang}" / "book.json"
    h7c = LIBRARY / f"{prefix}_{lang}" / f"{prefix}_{lang}.h7c"
    return book.is_file() or h7c.is_file()


def _gate_only_langs(doctrine: dict[str, Any]) -> frozenset[str]:
    return frozenset(doctrine.get("gate_only_langs") or [])


def _compiler_drivers(doctrine: dict[str, Any]) -> frozenset[str]:
    return frozenset(doctrine.get("compiler_drivers") or [])


def _interp_only_langs(doctrine: dict[str, Any]) -> frozenset[str]:
    return frozenset(doctrine.get("interp_only_langs") or ("ammolang", "field"))


def _interp_required(rep: dict[str, Any], *, doctrine: dict[str, Any]) -> bool:
    lang = rep.get("lang", "")
    driver = str(rep.get("driver") or "")
    if lang in _gate_only_langs(doctrine):
        return False
    if lang in _interp_only_langs(doctrine):
        return True
    if driver in frozenset(doctrine.get("interp_required_drivers") or ("g16-interp", "gpy-16")):
        return True
    return lang == "python"


def _lane_ok(rep: dict[str, Any], *, doctrine: dict[str, Any]) -> tuple[bool, bool, bool]:
    comp = rep.get("compile") or {}
    run = rep.get("run") or {}
    interp = rep.get("interp") or {}
    compile_ok = bool(comp.get("ok"))
    run_ok = bool(run.get("ok")) or bool(run.get("gate_only"))
    interp_ok = bool(interp.get("ok")) if interp else False
    if rep.get("lang") in _gate_only_langs(doctrine) and compile_ok and run_ok:
        return compile_ok, True, True
    if rep.get("lang") in _interp_only_langs(doctrine) and interp_ok:
        return True, run_ok, interp_ok
    driver = str(rep.get("driver") or "")
    if driver in _compiler_drivers(doctrine) and compile_ok and run_ok:
        return compile_ok, run_ok, True
    return compile_ok, run_ok, interp_ok


def _detect_issues(rep: dict[str, Any], *, doctrine: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    sev_map = doctrine.get("issue_severity") or {}
    slow_ms = int(doctrine.get("slow_compile_ms") or 30000)
    lang = rep.get("lang", "")

    if not rep.get("sample"):
        issues.append({"id": "missing_sample", "severity": "warn", "lang": lang})
    if not _book_exists("explaining", lang):
        issues.append({"id": "missing_explaining_book", "severity": "warn", "lang": lang})
    if not _book_exists("exploring", lang):
        issues.append({"id": "missing_exploring_book", "severity": "warn", "lang": lang})

    check = rep.get("check") or {}
    if check.get("blocked"):
        issues.append({
            "id": "security_block",
            "severity": "halt",
            "lang": lang,
            "detail": (check.get("security") or {}).get("findings", [])[:3],
        })

    comp = rep.get("compile") or {}
    interp_only = lang in _interp_only_langs(doctrine)
    if comp and not comp.get("ok") and not comp.get("interpreted"):
        if interp_only and bool((rep.get("interp") or {}).get("ok")):
            issues.append({
                "id": "compile_skip",
                "severity": "info",
                "lang": lang,
                "detail": "interp-only language — compile lane optional",
            })
        else:
            issues.append({
                "id": "compile_fail",
                "severity": "critical",
                "lang": lang,
                "error": comp.get("error") or comp.get("stderr"),
            })
    elif int(comp.get("compile_ms") or comp.get("ms") or 0) > slow_ms:
        issues.append({
            "id": "slow_compile",
            "severity": "warn",
            "lang": lang,
            "ms": comp.get("compile_ms") or comp.get("ms"),
        })

    compile_ok, run_ok, interp_ok = _lane_ok(rep, doctrine=doctrine)
    run = rep.get("run") or {}
    if run and not run_ok:
        if lang in _gate_only_langs(doctrine) and compile_ok:
            issues.append({"id": "gate_only", "severity": "info", "lang": lang, "detail": run.get("message")})
        elif lang in _interp_only_langs(doctrine) and interp_ok:
            issues.append({"id": "run_skip", "severity": "info", "lang": lang, "detail": "interp-only language"})
        else:
            issues.append({"id": "run_fail", "severity": "critical", "lang": lang, "error": run.get("error")})
    elif run.get("gate_only"):
        issues.append({"id": "gate_only", "severity": "info", "lang": lang, "detail": run.get("message")})

    interp = rep.get("interp") or {}
    if interp and not interp_ok:
        if _interp_required(rep, doctrine=doctrine) and not (compile_ok and run_ok and str(rep.get("driver") or "") in _compiler_drivers(doctrine)):
            issues.append({"id": "interp_fail", "severity": "critical", "lang": lang, "error": interp.get("error")})
        elif not _interp_required(rep, doctrine=doctrine):
            issues.append({"id": "interp_skip", "severity": "info", "lang": lang, "detail": "compiler lane satisfied"})

    chips = rep.get("chips") or {}
    if chips.get("required") and not chips.get("ok"):
        issues.append({"id": "chips_gate_fail", "severity": "halt", "lang": lang, "detail": chips.get("reason")})

    if not (GROK16 / "bin" / "g16").is_file():
        issues.append({"id": "g16_missing", "severity": "halt", "lang": lang})

    for issue in issues:
        for sev, ids in sev_map.items():
            if issue["id"] in ids:
                issue["severity"] = sev
                break
    return issues


def _should_halt(issues: list[dict[str, Any]], *, doctrine: dict[str, Any]) -> bool:
    if os.environ.get("G16_TEST_NO_HALT", "").strip().lower() in ("1", "true", "yes"):
        return False
    halt_ids = set(doctrine.get("halt_on") or [])
    return any(i.get("id") in halt_ids or i.get("severity") == "halt" for i in issues)


def chips_posture() -> dict[str, Any]:
    """CHIPs ↔ G16 language health — field_opt manifest + ironclad truth + compiler designs."""
    manifest = _load(CHIPS_MANIFEST, {})
    iron = _load(STATE / "field-ironclad-chips-combinatorics-panel.json", {})
    langs_doc = _load(GROK16 / "data" / "grok16-languages.json", {})
    languages = langs_doc.get("languages") or {}
    written = sum(1 for m in languages.values() if m.get("compiler_written"))
    designs = sum(
        1 for lid in languages
        if (GROK16 / "examples" / "languages" / lid / "compiler.design.json").is_file()
    )
    g16_ok = (GROK16 / "bin" / "g16").is_file()
    compilers_ok = written == len(languages) and designs == len(languages) if languages else False
    return {
        "schema": "g16-chips-lang-health/v1",
        "updated": _now(),
        "ok": g16_ok and bool(manifest.get("hot_paths")) and compilers_ok,
        "g16_binary": g16_ok,
        "chips_profile": manifest.get("profile", "field_opt"),
        "hot_path_count": len(manifest.get("hot_paths") or []),
        "compiler_written": written,
        "compiler_design_files": designs,
        "languages_total": len(languages),
        "chips_universal": bool(langs_doc.get("chips_universal")),
        "ironclad_chips_ok": bool(iron.get("ok") or iron.get("pass_ok")),
        "ironclad_truth": iron.get("truth_percent"),
        "compatible": g16_ok and compilers_ok,
        "manifest": str(CHIPS_MANIFEST.relative_to(INSTALL)) if CHIPS_MANIFEST.is_file() else None,
    }


def _chips_lang_check(lang: str, driver: str) -> dict[str, Any]:
    """Per-language CHIPs compatibility — native_bsp / g16 drivers share field_opt toolchain."""
    chips = chips_posture()
    native_drivers = {
        "g16-cc", "g16-cxx", "g16-as", "g16-gfortran", "g16-rust", "g16-go", "g16-zig",
        "g16-gdc", "g16-gnat", "g16-objc", "g16-qbasic", "g16-fpc", "g16-aml",
    }
    required = driver in native_drivers or lang in ("c", "cxx", "asm")
    return {
        "ok": chips.get("ok", False) if required else True,
        "required": required,
        "driver": driver,
        "profile": chips.get("chips_profile"),
        "reason": None if chips.get("ok") or not required else "chips_g16_gate",
        "runner": "native_bsp" if driver != "g16-interp" else "g16-interp",
    }


def test_language_full(lang_id: str, *, sample: str | None = None) -> dict[str, Any]:
    """Complete test: check → compile → run → interp → issues → CHIPs."""
    matrix = _import(INSTALL / "lib" / "g16-language-test-matrix.py", "harness_matrix")
    bench = _import(INSTALL / "lib" / "g16-compiler-bench.py", "harness_bench")
    doctrine = _load(DOCTRINE, {})

    row: dict[str, Any] = {"lang": lang_id, "ok": False, "issues": [], "halt": False}
    g16_doc = _load(GROK16 / "data" / "grok16-languages.json", {})
    meta = (g16_doc.get("languages") or {}).get(lang_id) or {}
    row["driver"] = meta.get("driver")
    row["sample"] = sample

    if matrix and hasattr(matrix, "test_language"):
        base = matrix.test_language(lang_id, sample=sample)
        row.update({k: base.get(k) for k in ("check", "compile", "run", "discerned", "log", "error")})
        row["sample"] = base.get("sample") or sample
        row["ok"] = bool(base.get("ok"))

    if bench and hasattr(bench, "bench_language") and row.get("sample"):
        brow = {
            "lang": lang_id,
            "driver": row.get("driver"),
            "sample": row["sample"],
            "has_sample": True,
            "bench_compile": True,
            "bench_interp": True,
        }
        brep = bench.bench_language(brow, native=_import(GROK16 / "lib" / "g16-native-compile.py", "hn"))
        row["bench"] = {
            "compile": brep.get("compile"),
            "run": brep.get("run"),
            "interp": brep.get("interp"),
        }
        if brep.get("compile"):
            row.setdefault("compile", brep["compile"])
        if brep.get("interp"):
            row["interp"] = brep["interp"]

    row["chips"] = _chips_lang_check(lang_id, str(row.get("driver") or ""))
    row["books"] = {
        "explaining": _book_exists("explaining", lang_id),
        "exploring": _book_exists("exploring", lang_id),
    }
    row["issues"] = _detect_issues(row, doctrine=doctrine)
    row["halt"] = _should_halt(row["issues"], doctrine=doctrine)
    row["issue_count"] = len(row["issues"])
    row["critical_count"] = sum(1 for i in row["issues"] if i.get("severity") in ("halt", "critical"))
    compile_ok, run_ok, interp_ok = _lane_ok(row, doctrine=doctrine)
    row["ok"] = compile_ok and (run_ok or interp_ok) and not row["halt"] and row["critical_count"] == 0
    return row


_MATRIX_CACHE: list[dict[str, Any]] | None = None


def discover_all(*, refresh: bool = False) -> list[dict[str, Any]]:
    global _MATRIX_CACHE
    if _MATRIX_CACHE is not None and not refresh:
        return list(_MATRIX_CACHE)
    matrix = _import(INSTALL / "lib" / "g16-language-test-matrix.py", "h_disc")
    if matrix and hasattr(matrix, "discover_matrix"):
        _MATRIX_CACHE = matrix.discover_matrix()
        return list(_MATRIX_CACHE)
    doc = _load(GROK16 / "data" / "grok16-languages.json", {})
    _MATRIX_CACHE = [{"lang": k, **v} for k, v in sorted((doc.get("languages") or {}).items())]
    return list(_MATRIX_CACHE)


def run_harness(
    *,
    langs: list[str] | None = None,
    halt: bool = True,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if OUT_JSONL.is_file():
        OUT_JSONL.unlink()

    matrix = discover_all()
    if langs:
        want = {x.lower() for x in langs}
        matrix = [r for r in matrix if r.get("lang") in want]

    chips_before = chips_posture()
    if not chips_before.get("ok"):
        _append_jsonl({"ts": _now(), "event": "chips_warn", "chips": chips_before})

    t0 = time.perf_counter()
    results: list[dict[str, Any]] = []
    halted = False
    halt_lang = ""
    passed = failed = halted_count = 0

    for i, row in enumerate(matrix, 1):
        lang = row["lang"]
        rep = test_language_full(lang, sample=row.get("sample"))
        results.append(rep)
        if rep.get("halt"):
            halted_count += 1
            if halt and not halted:
                halted = True
                halt_lang = lang
                _append_jsonl({"ts": _now(), "event": "halt", "lang": lang, "issues": rep.get("issues")})
        if rep.get("ok"):
            passed += 1
        else:
            failed += 1
        _append_jsonl({"ts": _now(), "event": "test", "index": i, "total": len(matrix), **rep})
        if on_progress:
            on_progress({"done": i, "total": len(matrix), "lang": lang, "result": rep, "halted": halted})
        if halted and halt:
            break

    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    chips_health = {
        **chips_posture(),
        "languages_tested": len(results),
        "languages_passed": passed,
        "languages_failed": failed,
        "halted": halted,
        "halt_lang": halt_lang or None,
    }
    STATE.mkdir(parents=True, exist_ok=True)
    CHIPS_HEALTH.write_text(json.dumps(chips_health, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    doc = {
        "schema": "g16-compiler-test/v1",
        "updated": _now(),
        "ok": failed == 0 and not halted,
        "elapsed_ms": elapsed_ms,
        "halted": halted,
        "halt_lang": halt_lang or None,
        "totals": {
            "languages": len(matrix),
            "tested": len(results),
            "passed": passed,
            "failed": failed,
            "halted_events": halted_count,
            "missing_exploring": sum(1 for r in results if not (r.get("books") or {}).get("exploring")),
        },
        "chips": chips_health,
        "results": results,
    }
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return doc


def ensure_exploring_books(*, langs: list[str] | None = None) -> dict[str, Any]:
    vis = _import(INSTALL / "lib" / "field-combinatronic-visuals.py", "harness_vis")
    if not vis or not hasattr(vis, "generate_exploring_book"):
        return {"ok": False, "error": "exploring_generator_missing"}
    matrix = discover_all()
    if langs:
        want = {x.lower() for x in langs}
        matrix = [r for r in matrix if r.get("lang") in want]
    created: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, Any]] = []
    for row in matrix:
        lang = row["lang"]
        if _book_exists("exploring", lang):
            skipped.append(lang)
            continue
        try:
            rep = vis.generate_exploring_book(lang)
            if rep.get("ok"):
                created.append(lang)
            else:
                errors.append({"lang": lang, "error": rep.get("error")})
        except Exception as exc:
            errors.append({"lang": lang, "error": type(exc).__name__})
    return {
        "ok": len(errors) == 0,
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "created_count": len(created),
    }


def _aml_harness_enabled() -> bool:
    return os.environ.get("AML_BUILD", "1").strip().lower() not in ("0", "false", "no", "off")


def _run_via_ammolang_harness(*, no_halt: bool) -> dict[str, Any] | None:
    if not _aml_harness_enabled():
        return None
    build_py = INSTALL / "lib" / "field-ammolang-build.py"
    if not build_py.is_file():
        return None
    mod = _import(build_py, "harness_aml")
    if not mod or not hasattr(mod, "execute_build_script"):
        return None
    script = INSTALL / "library/dewey/000-computer-science/ammolang/compiler_harness.aml"
    if not script.is_file():
        return None
    os.environ.setdefault("G16_TEST_NO_HALT", "1" if no_halt else "0")
    mod.execute_build_script(script, live=True)
    return _load(OUT_JSON, None)


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="G16 compiler test harness")
    ap.add_argument("--lang", action="append")
    ap.add_argument("--no-halt", action="store_true")
    ap.add_argument("--books", action="store_true", help="Generate missing Exploring books")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.books:
        rep = ensure_exploring_books(langs=args.lang)
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            print(f"exploring books: created={rep.get('created_count')} skipped={len(rep.get('skipped') or [])}")
        return 0 if rep.get("ok") else 1

    if not args.lang:
        aml_doc = _run_via_ammolang_harness(no_halt=args.no_halt)
        doc = aml_doc if aml_doc else run_harness(langs=None, halt=not args.no_halt)
    else:
        doc = run_harness(langs=args.lang, halt=not args.no_halt)
    if args.json:
        print(json.dumps(doc, ensure_ascii=False, indent=2))
    else:
        t = doc.get("totals") or {}
        print(f"g16-compiler-test: {t.get('passed')}/{t.get('tested')} pass "
              f"halt={doc.get('halted')} · {doc.get('elapsed_ms')}ms")
        print(f"chips: {CHIPS_HEALTH}")
        print(f"report: {OUT_JSON}")
    return 0 if doc.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())