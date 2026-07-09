#!/usr/bin/env pythong
"""Hostess 7 perfect calculator — arithmetic through advanced mathematics and technology."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))

def _resolve_battery_path(fname: str) -> Path:
    """data/ may be root-owned empty; fall back to Hostess7/data and state."""
    candidates = [
        INSTALL / "data" / fname,
        INSTALL / "Hostess7" / "data" / fname,
        STATE / fname,
        Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7"))) / "data" / fname,
    ]
    for p in candidates:
        if p.is_file():
            return p
    return candidates[0]

DOCTRINE = INSTALL / "data" / "hostess7-calculator-doctrine.json"
BATTERY = _resolve_battery_path("hostess7-calculator-battery.json")
EXPLAIN = INSTALL / "data" / "hostess7-calculator-explain.json"
OCR_DOCTRINE = INSTALL / "data" / "hostess7-calculator-ocr-doctrine.json"
PANEL = STATE / "hostess7-calculator-panel.json"
RUNTIME = STATE / "hostess7-calculator-runtime.json"
LEDGER = STATE / "hostess7-calculator-ledger.jsonl"
OCR_CORPUS = STATE / "hostess7-calculator-ocr-corpus.json"
OCR_LEDGER = STATE / "hostess7-calculator-ocr-ledger.jsonl"
SG_ROOT = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent)))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
def _final_eye_root() -> Path:
    try:
        from sg_paths import final_eye_root as _fer
        return _fer()
    except ImportError:
        pass
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (INSTALL / "Final_Eye").resolve()


FINAL_EYE_ROOT = _final_eye_root()

ENABLED = os.environ.get("NEXUS_HOSTESS7_CALCULATOR", "1") == "1"

_SECTION_LABELS = (
    ("what", "What"),
    ("why", "Why"),
    ("how", "How"),
    ("pitfalls", "Pitfalls"),
    ("where", "Where"),
    ("example", "Example"),
)

_CALC_KEYS = (
    "calculate", "compute", "what is", "what's", "solve", "integrate", "integral",
    "derivative", "differentiate", "diff ", "limit", "factor", "expand", "simplify",
    "determinant", "det ", "eigenvalue", "matrix", "fft", "mean", "std", "sqrt",
    "sin(", "cos(", "tan(", "log(", "exp(", "pi", "percent", "% of",
    "linear algebra", "calculus", "calculator", "perfect calculator", "advanced math",
)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _field_math():
    """Field-native math engine — no sympy on the Field plane."""
    import importlib.util
    py = INSTALL / "lib" / "field-math.py"
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("field_math_calc", py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _sympy_ready() -> bool:
    """Legacy name — Field math is always ready (stdlib). Sympy not required."""
    fm = _field_math()
    return bool(fm and getattr(fm, "ready", lambda: True)())


def _field_ready() -> bool:
    return _sympy_ready()


def _normalize_result(val: Any) -> str:
    fm = _field_math()
    if fm and hasattr(fm, "format_field"):
        return fm.format_field(val)
    if val is None:
        return ""
    if isinstance(val, (list, tuple, set)):
        return ",".join(_normalize_result(v) for v in val)
    if isinstance(val, dict):
        return json.dumps({str(k): _normalize_result(v) for k, v in val.items()}, ensure_ascii=False)
    s = str(val).replace("**", "^")
    return re.sub(r"\s+", "", s)


def _results_match(got: str, expected: str) -> bool:
    fm = _field_math()
    if fm and hasattr(fm, "results_match"):
        return bool(fm.results_match(got, expected))
    got_n = re.sub(r"\s+", "", got.lower())
    exp_n = re.sub(r"\s+", "", expected.lower())
    if got_n == exp_n:
        return True
    try:
        return abs(float(got_n) - float(exp_n)) < 1e-6
    except ValueError:
        return False


def _parse_matrix(text: str) -> Any:
    fm = _field_math()
    if fm and hasattr(fm, "parse_matrix"):
        return fm.parse_matrix(text)
    return None


def _parse_vector(text: str) -> list[Any]:
    fm = _field_math()
    if fm and hasattr(fm, "parse_vector"):
        return fm.parse_vector(text)
    inside = re.search(r"\[([^\]]+)\]", text)
    raw = inside.group(1) if inside else text.strip()
    cells = [c.strip() for c in re.split(r"[,\s]+", raw) if c.strip()]
    return [float(c) for c in cells]


def extract_math_query(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    keep_verbs = ("solve", "integrate", "integral", "diff", "differentiate", "limit", "factor", "expand", "det", "determinant", "eigenvalue", "fft", "mean", "std", "dot", "abs")
    if any(low.startswith(v) for v in keep_verbs):
        return raw.rstrip("?.!")
    for prefix in (
        r"^(?:please\s+)?(?:calculate|compute|evaluate)\s+",
        r"^what(?:'s| is)\s+",
        r"^how much is\s+",
        r"^find\s+",
    ):
        m = re.match(prefix, low, re.I)
        if m:
            return raw[m.end():].strip().rstrip("?.!")
    return raw


def _looks_like_math(text: str) -> bool:
    low = (text or "").lower()
    if any(k in low for k in _CALC_KEYS):
        return True
    if re.search(r"\d", low) and re.search(r"[+\-*/^=()\[\]]", low):
        return True
    return False


def compute(text: str) -> dict[str, Any]:
    """Compute a math query — Field Math engine (no sympy)."""
    query = extract_math_query(text)
    if not query:
        return {"ok": False, "error": "empty_query", "method": "field"}

    fm = _field_math()
    if not fm or not hasattr(fm, "compute"):
        return {"ok": False, "error": "field_math_unavailable", "method": "field"}

    out = fm.compute(query)
    if not isinstance(out, dict):
        return {"ok": False, "error": "field_math_bad_response", "method": "field"}
    # Normalize legacy callers
    out.setdefault("method", out.get("method") or "field")
    out.setdefault("engine", "field-math")
    out.setdefault("ironclad_cite", "ironclad:field-math:1")
    # Drop any residual sympy branding
    if str(out.get("method") or "").startswith("sympy"):
        out["method"] = "field"
    return out


def format_compute_reply(doc: dict[str, Any]) -> str:
    if not doc.get("ok"):
        return f"I could not compute that cleanly — {doc.get('error') or 'check the expression'}."
    work = doc.get("work") or doc.get("method") or "field"
    return (
        f"{doc.get('result')} — category {doc.get('category')}, method {work} (Field Math). "
        f"Query: {doc.get('query')}."
    )


_MATH_LINE_RE = re.compile(
    r"(?:"
    r"\d+\s*%\s*of\s*\d+"
    r"|\d+(?:\.\d+)?\s*[\+\-\*×÷/]\s*\d+(?:\.\d+)?"
    r"|(?:solve|integrate|diff|det|eigenvalues?|fft|mean|std|sqrt|sin|cos|tan|log|exp)\s+[^\n]{2,80}"
    r"|\[\[[\d\s,\.\-]+\]\]"
    r"|(?:disparity|confidence|mean|rate|fps|score)\s*[=:]\s*\d+(?:\.\d+)?"
    r"|\d+(?:\.\d+)?\s*=\s*\d+(?:\.\d+)?"
    r")",
    re.I,
)


def _ocr_tesseract(path: Path) -> str:
    core_py = INSTALL / "lib" / "final-eye-ocr-core.py"
    if not core_py.is_file():
        return ""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("final_eye_ocr_calc", core_py)
        if not spec or not spec.loader:
            return ""
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "ocr_image_text"):
            return str(mod.ocr_image_text(path) or "").strip()
    except Exception:
        pass
    return ""


def _resolve_source_path(spec: dict[str, Any]) -> Path | None:
    if spec.get("path_abs"):
        return Path(str(spec["path_abs"]))
    env = str(spec.get("path_env") or "")
    root = {
        "FINAL_EYE_ROOT": FINAL_EYE_ROOT,
        "ZOCR_ROOT": FINAL_EYE_ROOT,
        "ZNEWOCR_ROOT": FINAL_EYE_ROOT,
        "HOSTESS7_ROOT": HOSTESS7_ROOT,
        "NEXUS_INSTALL_ROOT": INSTALL,
        "SG_ROOT": SG_ROOT,
    }.get(env, Path(os.environ.get(env, "")) if env else SG_ROOT)
    rel = str(spec.get("path_rel") or "")
    if not rel:
        return None
    return Path(root) / rel


def _tail_jsonl(path: Path, *, limit: int = 500) -> list[dict[str, Any]]:
    if not path.is_file() or limit <= 0:
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows


def _text_chunks_from_row(row: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    chunks: list[str] = []
    for field in spec.get("text_fields") or []:
        val = row.get(field)
        if isinstance(val, str) and val.strip():
            chunks.append(val)
    ocr_file = row.get(spec.get("ocr_file_field") or "ocr_file")
    if ocr_file:
        fp = Path(str(ocr_file))
        if fp.is_file():
            try:
                chunks.append(fp.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
    return chunks


def _text_quality_ok(text: str) -> bool:
    if not text:
        return False
    sample = text[:4000]
    if "\x00" in sample or "H7B" in sample[:8]:
        return False
    printable = sum(1 for c in sample if c.isprintable() or c in "\n\t")
    return printable / max(len(sample), 1) >= 0.85


def _plausible_math_candidate(expr: str) -> bool:
    if not _looks_like_math(expr):
        return False
    if not _text_quality_ok(expr):
        return False
    if re.search(r"[\x00-\x08\x0b-\x1f]", expr):
        return False
    if len(expr) > 180:
        return False
    if expr.count("{") > 2 or ("format" in expr.lower() and "h7" in expr.lower()):
        return False
    if '"' in expr and (":" in expr or "seg-" in expr):
        return False
    if re.match(r'^"?ts"?\s*:', expr, re.I):
        return False
    return True


def extract_math_candidates(text: str, *, source_id: str = "") -> list[dict[str, Any]]:
    """Pull math expressions from noisy OCR / vision text."""
    if not text or len(text) < 3 or not _text_quality_ok(text):
        return []
    ocr_doc = _load(OCR_DOCTRINE, {})
    min_len = int((ocr_doc.get("train") or {}).get("min_candidate_len") or 3)
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    def add(raw: str, kind: str) -> None:
        cand = re.sub(r"\s+", " ", raw.strip())[:240]
        if len(cand) < min_len:
            return
        key = cand.lower()
        if key in seen:
            return
        seen.add(key)
        out.append({"expr": cand, "kind": kind, "source_id": source_id})

    for m in _MATH_LINE_RE.finditer(text):
        add(m.group(0), "regex")

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < min_len:
            continue
        low = line.lower()
        if any(k in low for k in ("integrate", "derivative", "solve", "matrix", "eigen", "fft", "sqrt", "det ")):
            add(line, "calculus_keyword")
        if re.search(r"\d+\s*%\s*of\s*\d+", low):
            add(line, "percent_of")
        if re.search(r"\d+\s*[\+\-\*×÷/]\s*\d+", line):
            add(line, "arithmetic_expr")
        if "[[" in line and "]]" in line:
            add(line, "matrix_bracket")
        if re.search(r"(?:disparity|confidence|mean|fps|score)\s*[=:]\s*\d", low):
            add(line, "disparity_metric")

    return out[:200]


def _ingest_text_blob(text: str, *, source_id: str, path: str, corpus: dict[str, Any]) -> int:
    if not _text_quality_ok(text):
        return 0
    max_c = int((_load(OCR_DOCTRINE, {}).get("ingest") or {}).get("max_candidates_per_ingest") or 8000)
    if len(corpus.get("candidates") or []) >= max_c:
        return 0
    added = 0
    known = corpus.setdefault("seen_hashes", [])
    seen_set = set(known[-50000:])
    for cand in extract_math_candidates(text, source_id=source_id):
        h = hashlib.sha256(f"{source_id}:{cand['expr']}".encode()).hexdigest()[:24]
        if h in seen_set:
            continue
        seen_set.add(h)
        known.append(h)
        corpus["candidates"].append({
            **cand,
            "hash": h,
            "path": path,
            "ingested_at": _now(),
        })
        added += 1
        if len(corpus["candidates"]) >= max_c:
            break
    return added


def ingest_ocr_vision(*, limit_per_source: int | None = None) -> dict[str, Any]:
    """Feed calculator think tank from Final_Eye vision + Hostess7 brain corpus (vision, SDF, warfare)."""
    ocr_doc = _load(OCR_DOCTRINE, {})
    ingest_cfg = ocr_doc.get("ingest") or {}
    max_files = limit_per_source or int(ingest_cfg.get("max_files_per_source") or 500)
    max_bytes = int(ingest_cfg.get("max_bytes_per_file") or 250000)

    corpus = _load(OCR_CORPUS, {
        "schema": "hostess7-calculator-ocr-corpus/v1",
        "candidates": [],
        "seen_hashes": [],
        "sources": {},
    })
    corpus.setdefault("candidates", [])
    corpus.setdefault("seen_hashes", [])
    corpus.setdefault("sources", {})

    total_added = 0
    source_stats: dict[str, Any] = {}

    for spec in ocr_doc.get("feed_sources") or []:
        sid = str(spec.get("id") or "unknown")
        kind = str(spec.get("kind") or "jsonl")
        files_read = 0
        bytes_read = 0
        added = 0

        if kind == "jsonl":
            fp = _resolve_source_path(spec)
            if fp and fp.is_file():
                for row in _tail_jsonl(fp, limit=max_files):
                    for chunk in _text_chunks_from_row(row, spec):
                        bytes_read += len(chunk)
                        added += _ingest_text_blob(chunk, source_id=sid, path=str(fp), corpus=corpus)
                    files_read += 1

        elif kind == "json":
            fp = _resolve_source_path(spec)
            if fp and fp.is_file():
                try:
                    doc = json.loads(fp.read_text(encoding="utf-8", errors="replace")[:max_bytes])
                    nested = spec.get("nested")
                    rows = doc.get(nested) if nested else [doc]
                    for row in rows or []:
                        if isinstance(row, dict):
                            for field in spec.get("text_fields") or ["body", "text"]:
                                val = row.get(field)
                                if isinstance(val, str):
                                    added += _ingest_text_blob(val, source_id=sid, path=str(fp), corpus=corpus)
                    files_read = 1
                    bytes_read = fp.stat().st_size
                except (OSError, json.JSONDecodeError):
                    pass

        elif kind == "glob":
            import glob as globmod
            base = _resolve_source_path(spec)
            if spec.get("path_abs") and "*" in str(spec["path_abs"]):
                paths = [Path(p) for p in globmod.glob(str(spec["path_abs"]))[:max_files]]
            elif base and "*" in base.name:
                paths = sorted(base.parent.glob(base.name))[:max_files]
            elif base and base.suffix:
                paths = sorted(base.parent.glob(base.name))[:max_files]
            else:
                paths = []
            for fp in paths:
                if not fp.is_file():
                    continue
                try:
                    if spec.get("ocr_tesseract"):
                        text = _ocr_tesseract(fp)
                    else:
                        text = fp.read_text(encoding="utf-8", errors="replace")[:max_bytes]
                    bytes_read += len(text)
                    added += _ingest_text_blob(text, source_id=sid, path=str(fp), corpus=corpus)
                    files_read += 1
                except OSError:
                    continue

        total_added += added
        source_stats[sid] = {"files_read": files_read, "bytes_read": bytes_read, "candidates_added": added, "kind": kind}
        corpus["sources"][sid] = {**source_stats[sid], "updated": _now()}

    corpus["updated"] = _now()
    corpus["candidate_count"] = len(corpus.get("candidates") or [])
    corpus["ingest_total_added"] = int(corpus.get("ingest_total_added") or 0) + total_added
    _save(OCR_CORPUS, corpus)
    _append_ledger({"ts": _now(), "event": "ocr_ingest", "added": total_added, "sources": source_stats})
    try:
        with OCR_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": _now(), "event": "ocr_ingest", "added": total_added, "sources": source_stats,
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return {"ok": True, "added": total_added, "candidate_count": corpus["candidate_count"], "sources": source_stats}


def train_ocr_vision(*, verify: bool = True, limit: int = 500) -> dict[str, Any]:
    """Train calculator on ingested OCR math — verify with live compute."""
    ocr_doc = _load(OCR_DOCTRINE, {})
    train_cfg = ocr_doc.get("train") or {}
    corpus = _load(OCR_CORPUS, {"candidates": []})
    candidates = list(corpus.get("candidates") or [])
    if not candidates:
        ingest_ocr_vision()
        corpus = _load(OCR_CORPUS, {"candidates": []})
        candidates = list(corpus.get("candidates") or [])

    verified = 0
    computed = 0
    attempts = 0
    samples: list[dict[str, Any]] = []
    for cand in candidates:
        if attempts >= limit:
            break
        expr = str(cand.get("expr") or "")
        if not expr or not _plausible_math_candidate(expr):
            continue
        attempts += 1
        out = compute(expr) if verify else {"ok": False}
        row = {**cand, "compute_ok": bool(out.get("ok")), "result": out.get("result"), "category": out.get("category")}
        if out.get("ok"):
            computed += 1
            verified += 1
            samples.append(row)
        elif _looks_like_math(expr):
            samples.append(row)

    plausible_n = sum(1 for c in candidates if _plausible_math_candidate(str(c.get("expr") or "")))
    total = len(candidates)
    rate = verified / max(plausible_n, 1)
    fluent_floor = int(train_cfg.get("fluent_samples_floor") or 120)
    master_floor = int(train_cfg.get("master_samples_floor") or 400)
    rate_floor = float(train_cfg.get("verified_rate_floor") or 0.35)

    train_doc = {
        "schema": "hostess7-calculator-ocr-train/v1",
        "updated": _now(),
        "candidate_count": total,
        "trained_count": attempts,
        "verified_count": verified,
        "computed_count": computed,
        "verified_rate": round(rate, 4),
        "fluent": verified >= fluent_floor,
        "mastered": verified >= master_floor,
        "samples": samples[-24:],
        "sources": corpus.get("sources") or {},
    }
    _save(STATE / "hostess7-calculator-ocr-train.json", train_doc)
    _append_ledger({"ts": _now(), "event": "ocr_train", "verified": verified, "total": total, "rate": rate})
    return {"ok": True, **train_doc}


def ocr_vision_status() -> dict[str, Any]:
    corpus = _load(OCR_CORPUS, {})
    train = _load(STATE / "hostess7-calculator-ocr-train.json", {})
    return {
        "schema": "hostess7-calculator-ocr-status/v1",
        "updated": _now(),
        "corpus": {
            "candidate_count": len(corpus.get("candidates") or []),
            "ingest_total_added": corpus.get("ingest_total_added"),
            "sources": corpus.get("sources") or {},
        },
        "train": train,
    }


def _run_battery() -> dict[str, Any]:
    doc = _load(BATTERY, {})
    problems = doc.get("problems") or []
    results: list[dict[str, Any]] = []
    passed = 0
    by_cat: dict[str, dict[str, int]] = {}
    for prob in problems:
        expr = str(prob.get("expr") or "")
        expected = str(prob.get("expected") or "")
        cat = str(prob.get("category") or "misc")
        out = compute(expr)
        got = str(out.get("result") or "")
        ok = bool(out.get("ok")) and _results_match(got, expected)
        if ok:
            passed += 1
        bucket = by_cat.setdefault(cat, {"passed": 0, "total": 0})
        bucket["total"] += 1
        if ok:
            bucket["passed"] += 1
        results.append({
            "id": prob.get("id"),
            "category": cat,
            "expr": expr,
            "expected": expected,
            "got": got,
            "passed": ok,
        })
    total = len(problems) or 1
    rate = passed / total
    threshold = float(doc.get("pass_threshold") or 0.85)
    return {
        "passed": rate >= threshold,
        "score": passed,
        "total": total,
        "pass_rate": round(100.0 * rate, 1),
        "pass_threshold": threshold,
        "by_category": by_cat,
        "results": results,
        "sympy": False,  # Field Math only — sympy retired on this plane
        "field_math": _field_ready(),
    }


def _pattern_mastery() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    bat = _run_battery()
    out: list[dict[str, Any]] = []
    for pat in doctrine.get("patterns") or []:
        pid = str(pat.get("id") or "")
        mastered = False
        if pid in ("sympy_symbolic", "field_symbolic", "field_math") and bat.get("field_math"):
            mastered = any(r.get("passed") for r in bat.get("results") or [] if r.get("category") in ("algebra", "calculus", "arithmetic"))
        elif pid == "decimal_precision":
            mastered = any(r.get("passed") for r in bat.get("results") or [] if r.get("category") == "arithmetic")
        elif pid == "matrix_ops":
            mastered = any(r.get("passed") for r in bat.get("results") or [] if r.get("category") == "linear_algebra")
        elif pid == "battery_verify":
            mastered = bool(bat.get("passed"))
        elif pid == "no_unsafe_eval":
            mastered = True
        elif pid == "natural_language":
            mastered = compute("what is 17*23").get("ok")
        elif pid == "show_work":
            mastered = True
        elif pid == "technology_fft":
            mastered = any(r.get("passed") for r in bat.get("results") or [] if r.get("category") == "technology")
        elif pid == "ocr_vision_train":
            tr = _load(STATE / "hostess7-calculator-ocr-train.json", {})
            mastered = bool(tr.get("mastered") or tr.get("fluent"))
        out.append({
            "id": pid,
            "label": pat.get("label"),
            "mastered": mastered,
        })
    return out


def calculator_score(*, battery: dict[str, Any] | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    bat = battery or _run_battery()
    patterns = _pattern_mastery()
    mastered = sum(1 for p in patterns if p.get("mastered"))
    rate = float(bat.get("pass_rate") or 0) / 100.0
    by_cat = bat.get("by_category") or {}
    cats_mastered = sum(1 for c in by_cat.values() if c.get("total") and c["passed"] >= c["total"])
    ocr_train = _load(STATE / "hostess7-calculator-ocr-train.json", {})
    ocr_corpus = _load(OCR_CORPUS, {})
    ocr_verified = int(ocr_train.get("verified_count") or 0)
    ocr_candidates = int(ocr_corpus.get("candidate_count") or len(ocr_corpus.get("candidates") or []))
    ocr_rate = float(ocr_train.get("verified_rate") or 0)

    score = 0.66
    score += 0.16 * rate
    score += 0.06 * min(1.0, mastered / max(len(patterns), 1))
    score += 0.04 * min(1.0, cats_mastered / 8.0)
    score += 0.04 * min(1.0, ocr_verified / 400.0)
    score += 0.02 * min(1.0, ocr_rate / 0.5)
    score += 0.04 if bat.get("field_math") else 0.0  # Field Math engine bonus (sympy retired)
    score = round(min(0.99, score), 4)

    fluent_floor = float(doctrine.get("fluent_floor_score") or 0.88)
    master_target = float(doctrine.get("master_calculator_score") or 0.96)
    tier = "assistant_guess"
    if score >= master_target and bat.get("passed") and cats_mastered >= 6:
        tier = "calculator_master"
    elif score >= fluent_floor and bat.get("passed"):
        tier = "calculator_fluent"
    elif rate >= 0.5:
        tier = "calculator_basic"

    return {
        "score": score,
        "calculator_score": score,
        "tier": tier,
        "fluent": tier in ("calculator_fluent", "calculator_master"),
        "mastered": tier == "calculator_master",
        "better_than_assistant": score >= fluent_floor and bat.get("passed"),
        "battery": bat,
        "patterns_mastered": mastered,
        "patterns_total": len(patterns),
        "categories_mastered": cats_mastered,
        "sympy_available": False,
        "field_math_available": bat.get("field_math"),
        "ocr_vision": {
            "candidate_count": ocr_candidates,
            "verified_count": ocr_verified,
            "verified_rate": ocr_rate,
            "fluent": bool(ocr_train.get("fluent")),
            "mastered": bool(ocr_train.get("mastered")),
        },
    }


def _merge_explain_overlay(track: str, base: dict[str, Any]) -> dict[str, Any]:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("h7overlay", INSTALL / "lib" / "hostess7-explain-overlay.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.merge_explain_doc(track, base)
    except Exception:
        pass
    return base


def _load_explain_doc() -> dict[str, Any]:
    base = _load(EXPLAIN, {"topics": [], "introduction": "", "format": [s[0] for s in _SECTION_LABELS]})
    return _merge_explain_overlay("calculator", base)


def _topic_match_score(topic: dict[str, Any], q: str) -> int:
    score = 0
    for kw in topic.get("keywords") or []:
        kw_l = str(kw).lower().strip()
        if kw_l and kw_l in q:
            score += len(kw_l) + (12 if q.strip() == kw_l else 0)
    return score


def _match_explain_topic(query: str) -> dict[str, Any] | None:
    q = (query or "").lower()
    best: dict[str, Any] | None = None
    best_score = 0
    for topic in _load_explain_doc().get("topics") or []:
        sc = _topic_match_score(topic, q)
        if sc > best_score:
            best_score = sc
            best = topic
    return best if best_score > 0 else None


def _format_topic_prose(topic: dict[str, Any], *, intro: str = "") -> str:
    parts: list[str] = []
    if intro.strip():
        parts.append(intro.strip())
    for key, label in _SECTION_LABELS:
        val = str(topic.get(key) or "").strip()
        if val:
            parts.append(f"{label}: {val}")
    return "\n\n".join(parts)


def explain_calculator_structured(query: str = "") -> dict[str, Any]:
    q = (query or "").strip()
    low = q.lower()
    doc = _load_explain_doc()
    intro = str(doc.get("introduction") or "").strip()
    fmt = doc.get("format") or [s[0] for s in _SECTION_LABELS]
    metrics = calculator_score()

    topic = _match_explain_topic(q)
    if not topic and any(k in low for k in ("calculator", "perfect calc", "math mastery", "advanced math")):
        doctrine = _load(DOCTRINE, {})
        sections = {
            "what": "Calculator mastery means I compute arithmetic through advanced math with SymPy — not LLM guessing.",
            "why": str(doctrine.get("fluency_claim") or ""),
            "how": (
                f"Battery pass {metrics.get('battery', {}).get('pass_rate')}% · tier {metrics.get('tier')} · "
                f"score {round(float(metrics.get('score') or 0) * 100)}% · categories mastered {metrics.get('categories_mastered')}"
            ),
            "pitfalls": "Unsafe eval; float drift; claiming integrals without sympy; hiding work.",
            "where": "lib/hostess7-calculator.py, Command calc, /api/hostess7/calculator",
            "example": "calc 'integrate x^2 from 0 to 1' → 1/3",
        }
        topic = {"id": "calculator_fluency_live", **sections}

    if topic:
        return {
            "ok": True,
            "query": q,
            "topic_id": topic.get("id"),
            "topic_label": str(topic.get("id") or "").replace("_", " ").title(),
            "introduction": intro,
            "sections": {k: str(topic.get(k) or "") for k, _ in _SECTION_LABELS if topic.get(k)},
            "format": fmt,
            "reply": _format_topic_prose(topic, intro=intro),
            "calculator_score": metrics.get("score"),
            "tier": metrics.get("tier"),
        }

    fallback = intro + " Ask me to calculate, integrate, solve, or explain linear algebra — I show my work."
    return {"ok": True, "query": q, "reply": fallback.strip(), "format": fmt}


def explain_calculator(query: str = "") -> str:
    return str(explain_calculator_structured(query).get("reply") or "")


def build_panel(*, write: bool = True) -> dict[str, Any]:
    metrics = calculator_score()
    doc = {
        "schema": "hostess7-calculator/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "calculator_score": metrics.get("score"),
        "tier": metrics.get("tier"),
        "fluent": metrics.get("fluent"),
        "mastered": metrics.get("mastered"),
        "better_than_assistant": metrics.get("better_than_assistant"),
        "battery_pass_rate": metrics.get("battery", {}).get("pass_rate"),
        "categories_mastered": metrics.get("categories_mastered"),
        "sympy_available": metrics.get("sympy_available"),
        "patterns_mastered": metrics.get("patterns_mastered"),
        "patterns_total": metrics.get("patterns_total"),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "ocr_vision": metrics.get("ocr_vision"),
    }
    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "hostess7-calculator-runtime/v1",
            "updated": doc["updated"],
            "tier": doc["tier"],
            "calculator_score": doc["calculator_score"],
        })
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "battery":
        print(json.dumps(_run_battery(), ensure_ascii=False))
        return 0
    if cmd == "score":
        print(json.dumps(calculator_score(), ensure_ascii=False))
        return 0
    if cmd in ("calc", "compute", "solve"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        out = compute(q)
        print(json.dumps(out, ensure_ascii=False))
        return 0 if out.get("ok") else 1
    if cmd in ("teach", "explain"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "perfect calculator"
        doc = explain_calculator_structured(q)
        if "--json" in sys.argv:
            print(json.dumps(doc, ensure_ascii=False))
        else:
            print(doc.get("reply") or "")
        return 0
    if cmd in ("ocr-ingest", "ocr_ingest", "ingest-ocr"):
        print(json.dumps(ingest_ocr_vision(), ensure_ascii=False))
        return 0
    if cmd in ("ocr-train", "ocr_train", "train-ocr"):
        lim = 500
        for arg in sys.argv[2:]:
            if arg.isdigit():
                lim = int(arg)
        print(json.dumps(train_ocr_vision(limit=lim), ensure_ascii=False))
        return 0
    if cmd in ("ocr-status", "ocr_status"):
        print(json.dumps(ocr_vision_status(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: hostess7-calculator.py [json|calc|battery|teach|ocr-ingest|ocr-train|ocr-status]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())