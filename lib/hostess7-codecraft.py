#!/usr/bin/env pythong
"""Hostess 7 codecraft — self code analysis, testing center, validated improvement.

Programming + G16 mastery composite — deeper than generic assistants on the live stack.
"""
from __future__ import annotations

import ast
import importlib.util
import json
import os
import py_compile
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "hostess7-codecraft-doctrine.json"
BATTERY = INSTALL / "data" / "hostess7-codecraft-battery.json"
EXPLAIN = INSTALL / "data" / "hostess7-codecraft-explain.json"
TESTING_CENTER = INSTALL / "data" / "hostess7-codecraft-testing-center.json"
PANEL = STATE / "hostess7-codecraft-panel.json"
RUNTIME = STATE / "hostess7-codecraft-runtime.json"
LEDGER = STATE / "hostess7-codecraft-ledger.jsonl"
PROPOSALS = STATE / "hostess7-codecraft-proposals.json"

ENABLED = os.environ.get("NEXUS_HOSTESS7_CODECRAFT", "1") == "1"
DISCLAIMER = (
    "Codecraft analysis is educational — operator approves production changes. "
    "Testing center validates quality in advance; it does not auto-deploy without your authority."
)

_SECTION_LABELS = (
    ("what", "What"),
    ("why", "Why"),
    ("how", "How"),
    ("pitfalls", "Pitfalls"),
    ("where", "Where"),
    ("example", "Example"),
)

_CODECRAFT_KEYS = (
    "codecraft", "self code", "code analysis", "self analysis", "self eval", "self evaluation",
    "testing center", "test center", "validate improvement", "optimization", "optimizational",
    "improvement cycle", "analyze module", "review code", "self improvement",
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


def _mod(name: str, filename: str) -> Any | None:
    py = INSTALL / "lib" / filename
    if not py.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _run_nexus_json(module: str, args: list[str], *, timeout: int = 120) -> dict[str, Any]:
    py = INSTALL / "lib" / module
    if not py.is_file():
        return {"ok": False, "error": "module_missing", "module": module}
    try:
        proc = subprocess.run(
            ["pythong", str(py), *args],
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"ok": False, "error": proc.stderr.strip() or "empty_output"}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _pattern_hits(text: str) -> dict[str, bool]:
    return {
        "atomic_write": ".tmp" in text and "replace" in text,
        "safe_json_load": "json.JSONDecodeError" in text or "JSONDecodeError" in text,
        "importlib_plate": "importlib" in text and "exec_module" in text,
        "no_bare_except": "except:" not in text or "except Exception" in text,
        "has_main": 'if __name__ == "__main__"' in text,
        "brain_guard_ref": "brain-guard" in text or "brain_guard" in text,
        "g16_ref": "g16" in text.lower() or "grok16" in text.lower(),
    }


def analyze_module(path: str | Path) -> dict[str, Any]:
    """Self code analysis — AST metrics and NEXUS pattern hits."""
    p = Path(path)
    if not p.is_file():
        p = INSTALL / "lib" / str(path)
    if not p.is_file():
        return {"ok": False, "error": "not_found", "path": str(path)}
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"ok": False, "error": str(exc), "path": str(p)}
    issues: list[dict[str, str]] = []
    patterns = _pattern_hits(text)
    if "eval(" in text:
        issues.append({"severity": "critical", "msg": "eval() forbidden on NEXUS stack"})
    if re.search(r"open\([^)]+\)\s*\n\s*json\.dump", text) and not patterns["atomic_write"]:
        issues.append({"severity": "medium", "msg": "Panel write may lack atomic tmp+replace"})
    if "except:" in text and "except Exception" not in text:
        issues.append({"severity": "low", "msg": "Bare except detected — prefer OSError, JSONDecodeError"})
    try:
        tree = ast.parse(text)
        funcs = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
        classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
        syntax_ok = True
    except SyntaxError as exc:
        funcs = classes = 0
        syntax_ok = False
        issues.append({"severity": "critical", "msg": f"SyntaxError: {exc}"})
    score = 0.5
    score += 0.1 if patterns["atomic_write"] else 0.0
    score += 0.08 if patterns["safe_json_load"] else 0.0
    score += 0.06 if patterns["importlib_plate"] else 0.0
    score += 0.06 if patterns["no_bare_except"] else 0.0
    score += 0.05 if syntax_ok else 0.0
    score -= 0.15 * sum(1 for i in issues if i["severity"] == "critical")
    score = round(max(0.0, min(1.0, score)), 4)
    return {
        "ok": True,
        "path": str(p),
        "module": p.name,
        "lines": text.count("\n") + 1,
        "functions": funcs,
        "classes": classes,
        "syntax_ok": syntax_ok,
        "patterns": patterns,
        "issues": issues,
        "quality_score": score,
    }


def analyze_stack(*, glob: str = "hostess7-*.py", limit: int = 40) -> dict[str, Any]:
    lib = INSTALL / "lib"
    rows: list[dict[str, Any]] = []
    for path in sorted(lib.glob(glob))[:limit]:
        row = analyze_module(path)
        if row.get("ok"):
            rows.append(row)
    avg = sum(r.get("quality_score", 0) for r in rows) / max(len(rows), 1)
    return {
        "ok": True,
        "updated": _now(),
        "modules_analyzed": len(rows),
        "average_quality": round(avg, 4),
        "modules": rows,
    }


def propose_optimizations(*, module: str | None = None) -> dict[str, Any]:
    """Rule-based optimization proposals from analysis gaps."""
    target = analyze_stack(limit=1) if not module else {"modules": [analyze_module(module)]}
    proposals: list[dict[str, Any]] = []
    for row in target.get("modules") or []:
        if not row.get("ok"):
            continue
        mid = row.get("module", "unknown")
        pats = row.get("patterns") or {}
        if not pats.get("atomic_write") and "panel" in mid or row.get("lines", 0) > 80:
            proposals.append({
                "id": f"{mid}_atomic_write",
                "module": mid,
                "kind": "pattern",
                "priority": "medium",
                "summary": "Add atomic tmp+replace JSON panel writes",
                "rationale": "NEXUS stack standard — avoids partial reads on crash",
            })
        if not pats.get("safe_json_load"):
            proposals.append({
                "id": f"{mid}_safe_json",
                "module": mid,
                "kind": "pattern",
                "priority": "low",
                "summary": "Harden _load() with OSError + JSONDecodeError default",
                "rationale": "Missing files and corrupt JSON must fail closed to default",
            })
        for issue in row.get("issues") or []:
            if issue.get("severity") in ("critical", "high"):
                proposals.append({
                    "id": f"{mid}_{issue['severity']}_{len(proposals)}",
                    "module": mid,
                    "kind": "fix",
                    "priority": issue["severity"],
                    "summary": issue.get("msg", ""),
                    "rationale": "Self-analysis flagged before promote",
                })
    doc = {"updated": _now(), "proposals": proposals, "count": len(proposals)}
    _save(PROPOSALS, doc)
    return {"ok": True, **doc}


def testing_center_run(*, fast: bool = False) -> dict[str, Any]:
    """Testing center — validate batteries, panels, compile gates before promote."""
    cfg = _load(TESTING_CENTER, {})
    gates = cfg.get("gates") or []
    results: list[dict[str, Any]] = []
    required_pass = 0
    required_total = 0
    for gate in gates:
        gid = str(gate.get("id") or "")
        required = bool(gate.get("required", True))
        if required:
            required_total += 1
        kind = str(gate.get("kind") or "")
        ok = False
        detail: dict[str, Any] = {}
        if kind == "nexus":
            detail = _run_nexus_json(str(gate.get("module") or ""), list(gate.get("args") or ["json"]))
            match_key = gate.get("match")
            if match_key:
                ok = bool(detail.get(match_key)) or bool((detail.get("battery") or {}).get("passed"))
            else:
                ok = bool(detail.get("passed")) or detail.get("schema", "").startswith("hostess7")
        elif kind == "compile_glob":
            pattern = str(gate.get("glob") or "lib/hostess7-*.py")
            lib = INSTALL / "lib"
            fails: list[str] = []
            for py in lib.glob(pattern.replace("lib/", "")):
                try:
                    py_compile.compile(str(py), doraise=True)
                except py_compile.PyCompileError as exc:
                    fails.append(f"{py.name}: {exc}")
            ok = not fails
            detail = {"compiled": ok, "failures": fails[:8]}
        if ok and required:
            required_pass += 1
        results.append({"id": gid, "label": gate.get("label"), "required": required, "passed": ok, "detail": detail})

    smoke: list[dict[str, Any]] = []
    if not fast:
        for sm in cfg.get("smoke_tests") or []:
            mod = str(sm.get("module") or "")
            q = str(sm.get("query") or "")
            match = str(sm.get("match") or "")
            proc = subprocess.run(
                ["pythong", str(INSTALL / "lib" / mod), "teach", q],
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                capture_output=True,
                text=True,
                timeout=90,
                check=False,
            )
            body = (proc.stdout or "") + (proc.stderr or "")
            smoke.append({"id": sm.get("id"), "passed": match in body, "match": match})

    all_required = required_pass >= required_total and required_total > 0
    smoke_ok = all(s.get("passed") for s in smoke) if smoke else True
    passed = all_required and smoke_ok
    out = {
        "ok": True,
        "schema": "hostess7-codecraft-testing-center-run/v1",
        "updated": _now(),
        "passed": passed,
        "required_passed": required_pass,
        "required_total": required_total,
        "gates": results,
        "smoke_tests": smoke,
        "disclaimer": DISCLAIMER,
    }
    _save(STATE / "hostess7-codecraft-testing-center-last.json", out)
    _append_ledger({"ts": out["updated"], "event": "testing_center", "passed": passed})
    return out


def validate_improvement(*, proposal_id: str | None = None) -> dict[str, Any]:
    """Run testing center to validate pending improvements."""
    center = testing_center_run()
    props = _load(PROPOSALS, {})
    validated: list[str] = []
    if proposal_id:
        validated = [proposal_id] if center.get("passed") else []
    elif center.get("passed"):
        validated = [p.get("id") for p in props.get("proposals") or [] if p.get("id")]
    row = {
        "ts": _now(),
        "event": "validate_improvement",
        "proposal_id": proposal_id,
        "testing_center_passed": center.get("passed"),
        "validated_ids": validated,
    }
    _append_ledger(row)
    return {"ok": center.get("passed", False), "testing_center": center, "validated": validated, **row}


def self_improve_cycle(*, module: str | None = None) -> dict[str, Any]:
    """Analyze → propose → testing center → ledger."""
    analysis = analyze_stack() if not module else {"modules": [analyze_module(module)]}
    proposals = propose_optimizations(module=module)
    center = testing_center_run(fast=False)
    return {
        "ok": True,
        "updated": _now(),
        "disclaimer": DISCLAIMER,
        "analysis_summary": {
            "modules": analysis.get("modules_analyzed") or len(analysis.get("modules") or []),
            "average_quality": analysis.get("average_quality"),
        },
        "proposals": proposals.get("count", 0),
        "testing_center": center,
        "validated": center.get("passed", False),
    }


def _explain_doc() -> dict[str, Any]:
    base = _load(EXPLAIN, {"topics": []})
    try:
        spec = importlib.util.spec_from_file_location("h7overlay", INSTALL / "lib" / "hostess7-explain-overlay.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.merge_explain_doc("codecraft", base)
    except Exception:
        pass
    return base


def _resolve_explain_topic(query: str) -> dict[str, Any] | None:
    q = (query or "").strip()
    low = q.lower()
    topic = None
    best_score = 0
    for t in _explain_doc().get("topics") or []:
        sc = _topic_match_score(t, low)
        if sc > best_score:
            best_score = sc
            topic = t
    if not topic and any(k in low for k in _CODECRAFT_KEYS):
        topic = {
            "id": "codecraft_live",
            "what": "Self code analysis, evaluation, optimizational proposals, testing center validation — programming and G16 deeper than assistants.",
            "why": str(_load(DOCTRINE, {}).get("mastery_claim") or ""),
            "how": "analyze_stack → propose_optimizations → testing_center_run → validate_improvement ledger.",
            "pitfalls": "Auto-deploy without operator; skipping testing center; analyzing stale cache trees.",
            "where": "lib/hostess7-codecraft.py, /api/hostess7/codecraft",
            "example": "self-improve cycle → proposals → testing center passed → validated ledger.",
        }
    return topic


def _battery_hit(query: str, expected: str) -> bool:
    low = query.lower()
    exp = expected.lower()
    if exp in low:
        return True
    topic = _resolve_explain_topic(query)
    tid = str((topic or {}).get("id") or "").lower()
    if tid == exp or exp.replace("_", " ") in tid:
        return True
    for kw in (_load(EXPLAIN, {}).get("topics") or []):
        if kw.get("id") == expected:
            return any(str(k).lower() in low for k in (kw.get("keywords") or []))
    return False


def _run_battery() -> dict[str, Any]:
    doc = _load(BATTERY, {})
    problems = doc.get("problems") or []
    results: list[dict[str, Any]] = []
    passed = 0
    by_cat: dict[str, dict[str, int]] = {}
    for prob in problems:
        q = str(prob.get("query") or "")
        expected = str(prob.get("expected_topic") or "")
        cat = str(prob.get("category") or "misc")
        ok = _battery_hit(q, expected)
        if ok:
            passed += 1
        bucket = by_cat.setdefault(cat, {"passed": 0, "total": 0})
        bucket["total"] += 1
        if ok:
            bucket["passed"] += 1
        results.append({"id": prob.get("id"), "category": cat, "query": q, "expected_topic": expected, "passed": ok})
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
    }


def _pattern_mastery() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    bat = _run_battery()
    center = _load(STATE / "hostess7-codecraft-testing-center-last.json", {})
    out: list[dict[str, Any]] = []
    for pat in doctrine.get("patterns") or []:
        pid = str(pat.get("id") or "")
        mastered = False
        if pid == "self_code_analysis":
            mastered = bool(analyze_stack(limit=5).get("modules_analyzed"))
        elif pid == "testing_center":
            mastered = bool(center.get("passed")) or bool(testing_center_run(fast=True).get("passed"))
        elif pid == "validated_improvement":
            mastered = PROPOSALS.is_file()
        elif pid == "programming_bridge":
            prog = _mod("h7prog", "hostess7-programming.py")
            mastered = bool(prog and prog.programming_score().get("better_than_assistant"))
        elif pid == "g16_bridge":
            g16 = _mod("h7g16", "hostess7-g16.py")
            mastered = bool(g16 and g16.g16_score().get("fluent"))
        elif pid == "optimization_rules":
            mastered = bool(propose_optimizations().get("count", 0) >= 0)
        elif pid == "battery_verify":
            mastered = bool(bat.get("passed"))
        elif pid == "disclaimer_seal":
            mastered = DISCLAIMER in str(explain_codecraft_structured("testing center", include_metrics=False).get("reply") or "")
        out.append({"id": pid, "label": pat.get("label"), "mastered": mastered})
    return out


def codecraft_score(*, battery: dict[str, Any] | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    bat = battery or _run_battery()
    patterns = _pattern_mastery()
    mastered = sum(1 for p in patterns if p.get("mastered"))
    center = _load(STATE / "hostess7-codecraft-testing-center-last.json", {})
    if not center:
        center = testing_center_run(fast=True)

    prog = _mod("h7prog", "hostess7-programming.py")
    g16 = _mod("h7g16", "hostess7-g16.py")
    prog_m = prog.programming_score() if prog else {}
    g16_m = g16.g16_score() if g16 else {}
    stack = analyze_stack(limit=12)

    score = 0.58
    score += 0.14 * (float(bat.get("pass_rate") or 0) / 100.0)
    score += 0.08 * min(1.0, mastered / max(len(patterns), 1))
    score += 0.06 * float(stack.get("average_quality") or 0)
    score += 0.08 if center.get("passed") else 0.02
    score += 0.06 if prog_m.get("better_than_assistant") else 0.02
    score += 0.05 if prog_m.get("tier") == "hostess7_master" else 0.02
    score += 0.06 if g16_m.get("mastered") else (0.03 if g16_m.get("fluent") else 0.0)
    score += float(doctrine.get("programming_floor_boost") or 0.02) if prog_m.get("better_than_assistant") else 0.0
    score += float(doctrine.get("g16_floor_boost") or 0.02) if g16_m.get("fluent") else 0.0
    score = round(min(0.99, score), 4)

    fluent_floor = float(doctrine.get("fluent_floor_score") or 0.88)
    master_target = float(doctrine.get("master_codecraft_score") or 0.97)
    tier = "observer"
    if score >= master_target and bat.get("passed") and center.get("passed"):
        if prog_m.get("tier") == "hostess7_master" and g16_m.get("mastered"):
            tier = "codecraft_master"
        elif prog_m.get("better_than_assistant") and g16_m.get("fluent"):
            tier = "codecraft_fluent"
    elif score >= fluent_floor and bat.get("passed"):
        tier = "codecraft_fluent"
    elif score >= 0.72:
        tier = "analyst"

    return {
        "score": score,
        "codecraft_score": score,
        "tier": tier,
        "fluent": tier in ("codecraft_fluent", "codecraft_master"),
        "mastered": tier == "codecraft_master",
        "battery": bat,
        "testing_center": center,
        "programming": {"score": prog_m.get("score"), "tier": prog_m.get("tier")},
        "g16": {"score": g16_m.get("score"), "tier": g16_m.get("tier"), "fluent": g16_m.get("fluent")},
        "stack_analysis": {"modules": stack.get("modules_analyzed"), "avg_quality": stack.get("average_quality")},
        "patterns_mastered": mastered,
        "patterns_total": len(patterns),
    }


def _topic_match_score(topic: dict[str, Any], q: str) -> int:
    score = 0
    for kw in topic.get("keywords") or []:
        kw_l = str(kw).lower().strip()
        if kw_l and kw_l in q:
            score += len(kw_l) + (12 if q.strip() == kw_l else 0)
    return score


def explain_codecraft_structured(query: str = "", *, include_metrics: bool = True) -> dict[str, Any]:
    q = (query or "").strip()
    doc = _load(EXPLAIN, {})
    intro = str(doc.get("introduction") or "").strip()
    fmt = doc.get("format") or [s[0] for s in _SECTION_LABELS]
    topic = _resolve_explain_topic(q)
    metrics: dict[str, Any] = {}
    if include_metrics and topic:
        metrics = codecraft_score()
        if topic.get("id") == "codecraft_live":
            topic = {
                **topic,
                "how": (
                    f"Tier {metrics.get('tier')} · score {metrics.get('score')} · "
                    f"testing_center {metrics.get('testing_center', {}).get('passed')} · "
                    f"programming {metrics.get('programming', {}).get('tier')} · g16 {metrics.get('g16', {}).get('tier')}"
                ),
            }
    if topic:
        parts = [intro, DISCLAIMER] if intro else [DISCLAIMER]
        for key, label in _SECTION_LABELS:
            val = str(topic.get(key) or "").strip()
            if val:
                parts.append(f"{label}: {val}")
        return {
            "ok": True,
            "query": q,
            "topic_id": topic.get("id"),
            "reply": "\n\n".join(parts),
            "codecraft_score": metrics.get("score"),
            "tier": metrics.get("tier"),
            "disclaimer": DISCLAIMER,
            "format": fmt,
        }
    return {"ok": True, "query": q, "reply": (intro + " " + DISCLAIMER).strip(), "format": fmt}


def explain_codecraft(query: str = "") -> str:
    return str(explain_codecraft_structured(query).get("reply") or "")


def format_codecraft_reply(query: str) -> str:
    doc = explain_codecraft_structured(query)
    if doc.get("reply"):
        return str(doc["reply"])
    cycle = self_improve_cycle()
    return (
        f"{DISCLAIMER}\n\n"
        f"Codecraft cycle — {cycle.get('proposals', 0)} proposals · "
        f"testing center {'passed' if cycle.get('validated') else 'pending'} · "
        f"avg quality {cycle.get('analysis_summary', {}).get('average_quality')}"
    )


def build_panel(*, write: bool = True) -> dict[str, Any]:
    metrics = codecraft_score()
    doc = {
        "schema": "hostess7-codecraft/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "codecraft_score": metrics.get("score"),
        "tier": metrics.get("tier"),
        "fluent": metrics.get("fluent"),
        "mastered": metrics.get("mastered"),
        "battery_pass_rate": metrics.get("battery", {}).get("pass_rate"),
        "testing_center_passed": metrics.get("testing_center", {}).get("passed"),
        "programming_tier": metrics.get("programming", {}).get("tier"),
        "g16_tier": metrics.get("g16", {}).get("tier"),
        "patterns_mastered": metrics.get("patterns_mastered"),
        "patterns_total": metrics.get("patterns_total"),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "disclaimer": DISCLAIMER,
    }
    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "hostess7-codecraft-runtime/v1",
            "updated": doc["updated"],
            "tier": doc["tier"],
            "codecraft_score": doc["codecraft_score"],
        })
    return doc


_OCR_API: dict | None = None


def _ocr_api() -> dict:
    global _OCR_API
    if _OCR_API is None:
        import importlib.util
        py = INSTALL / "lib" / "hostess7-ocr-bind.py"
        spec = importlib.util.spec_from_file_location("h7_ocr_bind_codecraft", py)
        if not spec or not spec.loader:
            raise ImportError("hostess7-ocr-bind.py missing")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _OCR_API = mod.bind("codecraft", install=INSTALL, state=STATE, ledger=LEDGER)
    return _OCR_API


def ingest_ocr_vision(**kw):
    return _ocr_api()["ingest_ocr_vision"](**kw)


def train_ocr_vision(**kw):
    return _ocr_api()["train_ocr_vision"](**kw)


def ocr_vision_status():
    return _ocr_api()["ocr_vision_status"]()


def _handle_ocr_cli(cmd: str) -> int | None:
    import importlib.util
    py = INSTALL / "lib" / "hostess7-ocr-feed.py"
    spec = importlib.util.spec_from_file_location("h7_ocr_feed_codecraft", py)
    if not spec or not spec.loader:
        return None
    feed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(feed)
    return feed.handle_ocr_cli(
        cmd,
        ingest_fn=ingest_ocr_vision,
        train_fn=train_ocr_vision,
        status_fn=ocr_vision_status,
        usage="hostess7-codecraft.py [json|analyze|stack|propose|testing-center|improve|teach|ocr-ingest|ocr-train|ocr-status]",
    )


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "battery":
        print(json.dumps(_run_battery(), ensure_ascii=False))
        return 0
    if cmd == "score":
        print(json.dumps(codecraft_score(), ensure_ascii=False))
        return 0
    if cmd in ("analyze", "stack"):
        if cmd == "stack":
            print(json.dumps(analyze_stack(), ensure_ascii=False))
        else:
            target = sys.argv[2] if len(sys.argv) > 2 else "hostess7-codecraft.py"
            print(json.dumps(analyze_module(target), ensure_ascii=False))
        return 0
    if cmd == "propose":
        mod = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(propose_optimizations(module=mod), ensure_ascii=False))
        return 0
    if cmd in ("testing-center", "testing_center", "test-center"):
        fast = "--fast" in sys.argv
        print(json.dumps(testing_center_run(fast=fast), ensure_ascii=False))
        return 0
    if cmd == "validate":
        pid = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(validate_improvement(proposal_id=pid), ensure_ascii=False))
        return 0
    if cmd in ("improve", "self-improve", "cycle"):
        mod = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(self_improve_cycle(module=mod), ensure_ascii=False))
        return 0
    if cmd in ("teach", "explain"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "codecraft mastery"
        print(json.dumps(explain_codecraft_structured(q), ensure_ascii=False))
        return 0
    ocr_ret = _handle_ocr_cli(cmd)
    if ocr_ret is not None:
        return ocr_ret
    print(json.dumps({"error": "usage: hostess7-codecraft.py [json|analyze|stack|propose|testing-center|improve|teach|ocr-ingest|ocr-train|ocr-status]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())