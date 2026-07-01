#!/usr/bin/env pythong
"""Code bugfinder — knowledgebase retrieval + Ironclad truth compare at high rate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent if INSTALL.name == "NewLatest" else INSTALL.parent)))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")))
DOCTRINE = INSTALL / "data" / "field-code-bugfinder-doctrine.json"
REPORT_CACHE = STATE / "field-code-bugfinder-last.json"
PANEL = STATE / "field-code-bugfinder-panel.json"
FIX_QUEUE = STATE / "field-ironclad-bugfix-queue.json"
FIELD_RESEARCH = SG / "Field_Research" / "content" / "chapters"

IRONCLAD_PRIORITY_TARGETS: tuple[str, ...] = (
    "NewLatest/lib/field-wave-engine.py",
    "NewLatest/lib/field-popcorn-player.py",
    "NewLatest/lib/field-plate-combinatorics-bridge.py",
    "NewLatest/lib/field-plate-meld.py",
    "NewLatest/lib/field-code-bugfinder.py",
    "NewLatest/lib/field-g16-launch.py",
    "NewLatest/lib/field-shell-dock.py",
    "NewLatest/lib/field-c2-taskbar-plate.py",
    "NewLatest/lib/field-plate-meld-orchestrator.py",
    "Grok16/lib/field_combinatorics.py",
)

CODE_EXTS = frozenset({".py", ".pyw", ".gpy", ".js", ".ts", ".tsx", ".c", ".cpp", ".h", ".hpp", ".sh", ".rs", ".go"})

BUG_PATTERNS: tuple[dict[str, Any], ...] = (
    {"id": "eval_exec", "severity": "high", "re": r"\b(eval|exec)\s*\(", "kb": "code injection eval exec security"},
    {"id": "bare_except", "severity": "medium", "re": r"except\s*:", "kb": "python exception handling bare except"},
    {"id": "shell_true", "severity": "high", "re": r"subprocess\.(run|call|Popen)\([^)]*shell\s*=\s*True", "kb": "subprocess shell injection"},
    {"id": "pickle_untrusted", "severity": "high", "re": r"pickle\.loads?\s*\(", "kb": "pickle deserialization security"},
    {"id": "sql_concat", "severity": "high", "re": r"(execute|query)\s*\(\s*[f\"'].*(%s|\+|\.format)", "kb": "sql injection parameterized query"},
    {"id": "hardcoded_secret", "severity": "high", "re": r"(password|api_key|secret|token)\s*=\s*['\"][^'\"]{6,}['\"]", "kb": "hardcoded credentials secret management"},
    {"id": "mutable_default", "severity": "medium", "re": r"def\s+\w+\([^)]*=\s*(\[\]|\{\})", "kb": "python mutable default argument bug"},
    {"id": "assert_production", "severity": "low", "re": r"\bassert\s+", "kb": "assert optimization production python -O"},
    {"id": "todo_fixme", "severity": "info", "re": r"(TODO|FIXME|HACK|XXX|BUG)\b", "kb": "technical debt incomplete implementation"},
    {"id": "null_compare", "severity": "low", "re": r"==\s*None\b", "kb": "python is None identity compare"},
    {"id": "race_check_act", "severity": "medium", "re": r"if\s+not\s+os\.path\.(exists|isfile).*\n\s*(open|write|mkdir)", "kb": "race condition time of check time of use"},
    {"id": "no_context_manager", "severity": "low", "re": r"=\s*open\s*\([^)]+\)\s*$", "kb": "resource leak file handle context manager"},
)

CLAIM_RE = re.compile(
    r"(?:#\s*)?(?:must|never|always|shall|guarantee|ensure|only|forbidden)\b[^.\n]{8,120}",
    re.I,
)
DOCSTRING_RE = re.compile(r'"""(.*?)"""|\'\'\'(.*?)\'\'\'', re.S)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
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


def _load_mod(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _thermal_gate(*, ops: int = 1) -> dict[str, Any]:
    bridge = INSTALL / "lib" / "field-plate-combinatorics-bridge.py"
    mod = _load_mod(bridge, "comb_bridge")
    if mod and hasattr(mod, "thermal_entropy_gate"):
        return mod.thermal_entropy_gate(ops=ops)
    return {"ok": True, "skipped": "no_bridge"}


def _combinatorics_posture() -> dict[str, Any]:
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    posture = bridge.get("exec_posture") or {}
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    condense = comb.get("plate_condense") or {}
    iron_group = next((g for g in (condense.get("groups") or []) if g.get("group") == "iron_truth"), None)
    return {
        "bridge_ok": bridge.get("ok"),
        "pattern": posture.get("pattern_id"),
        "runner": posture.get("runner"),
        "thermal_ok": (bridge.get("gate") or {}).get("ok"),
        "iron_truth_condensed": bool(iron_group and iron_group.get("condensed")),
        "iron_truth_present": (iron_group or {}).get("present"),
        "tree_complete": (comb.get("tree_walk") or {}).get("tree_complete"),
    }


def _resolve_scan_path(rel: str) -> Path | None:
    candidates = [
        SG / rel,
        INSTALL / rel.replace("NewLatest/", ""),
        Path(rel).expanduser(),
    ]
    if INSTALL.name == "NewLatest":
        candidates.insert(0, INSTALL / rel.replace("NewLatest/", ""))
    for path in candidates:
        try:
            p = path.resolve()
            if p.is_file():
                return p
        except OSError:
            continue
    return None


def ironclad_scan_queue() -> list[dict[str, Any]]:
    """Combinatorics + iron_truth condense → prioritized bugfix scan targets."""
    queue: list[dict[str, Any]] = []
    seen: set[str] = set()
    iron_truth_boost = 0
    condensed = STATE / "condensed-iron_truth-plate.json"
    if condensed.is_file():
        doc = _load(condensed, {})
        iron_truth_boost = int(doc.get("present_count") or 0)

    for rel in IRONCLAD_PRIORITY_TARGETS:
        path = _resolve_scan_path(rel)
        if path and str(path) not in seen:
            seen.add(str(path))
            priority = 15 + min(iron_truth_boost, 6)
            if "field-wave-engine" in rel:
                priority += 5
            queue.append({
                "path": str(path),
                "source": "iron_truth_condense" if iron_truth_boost else "ironclad_priority",
                "priority": priority,
            })

    lib_dir = INSTALL if INSTALL.name == "NewLatest" else SG / "NewLatest"
    lib_root = lib_dir / "lib"
    if lib_root.is_dir():
        for py in sorted(lib_root.glob("field-*.py"))[:12]:
            if str(py.resolve()) in seen:
                continue
            seen.add(str(py.resolve()))
            queue.append({
                "path": str(py.resolve()),
                "source": "field_surface_sweep",
                "priority": 5,
            })
    queue.sort(key=lambda r: -int(r.get("priority") or 0))
    return queue


def ironclad_bugfix_cycle(*, max_compares_per_target: int = 64, max_targets: int = 8) -> dict[str, Any]:
    """Run Ironclad truth compares on combinatorics-prioritized code targets."""
    gate = _thermal_gate(ops=max(2, max_targets))
    if not gate.get("ok"):
        return {"ok": False, "error": "thermal_entropy_gate", "gate": gate}
    ic = _ironclad_slice()
    if not ic.get("ironclad_sealed") and str(ic.get("verdict") or "").upper() not in ("GREEN", "OK"):
        return {"ok": False, "error": "ironclad_not_sealed", "ironclad": ic}

    comb = _combinatorics_posture()
    queue = ironclad_scan_queue()[:max_targets]
    scans: list[dict[str, Any]] = []
    fix_queue: list[dict[str, Any]] = []

    for row in queue:
        report = find_bugs(row["path"], max_compares=max_compares_per_target)
        actionable = [
            b for b in (report.get("bugs") or [])
            if b.get("verdict") in ("bug", "heuristic", "suspect")
            and b.get("severity") in ("high", "medium", None)
        ]
        scans.append({
            "path": row["path"],
            "source": row.get("source"),
            "bug_count": report.get("bug_count"),
            "heuristic_actionable": report.get("heuristic_actionable"),
            "truth_suspect_count": report.get("truth_suspect_count"),
            "compares_per_sec": report.get("truth_compares_per_sec"),
        })
        for bug in actionable[:12]:
            fix_queue.append({
                **bug,
                "scan_path": row["path"],
                "ironclad_sealed": ic.get("ironclad_sealed"),
                "combinatorics_pattern": comb.get("pattern"),
            })

    doc = {
        "schema": "field-ironclad-bugfix-queue/v1",
        "updated": _now(),
        "ok": True,
        "ironclad": ic,
        "combinatorics": comb,
        "thermal_gate": gate,
        "targets_scanned": len(scans),
        "fix_count": len(fix_queue),
        "scans": scans,
        "fixes": fix_queue[:48],
        "motto": "Ironclad sealed + combinatorics posture → prioritized code truth compares → fix queue.",
    }
    FIX_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    tmp = FIX_QUEUE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(FIX_QUEUE)
    panel = build_panel(last_cycle=doc)
    return {**doc, "panel": panel.get("schema")}


def _ironclad_slice() -> dict[str, Any]:
    dc_path = HOSTESS7_ROOT / "scripts" / "field_detective_corpus.py"
    mod = _load_mod(dc_path, "field_detective_corpus")
    if mod and hasattr(mod, "ironclad_slice"):
        return mod.ironclad_slice()
    return {"ok": False, "verdict": "MISSING", "ironclad_sealed": False}


def _analyze_truth(text: str, *, ironclad: dict[str, Any], local_evidence: int = 0) -> dict[str, Any]:
    dc_path = HOSTESS7_ROOT / "scripts" / "field_detective_corpus.py"
    mod = _load_mod(dc_path, "field_detective_corpus")
    if mod and hasattr(mod, "analyze_truth"):
        return mod.analyze_truth(text, local_evidence=local_evidence, ironclad=ironclad)
    return {"truth_score": 0.0, "deception_risk": "high", "inconsistency_flags": []}


def _kb_passages(query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    atlas = _load_mod(INSTALL / "lib" / "h7-library-atlas.py", "h7_atlas")
    if atlas and hasattr(atlas, "search_passages"):
        return atlas.search_passages(query, limit=limit)
    return []


def _kb_detective(query: str, *, limit: int = 4) -> list[dict[str, Any]]:
    dc_path = HOSTESS7_ROOT / "scripts" / "field_detective_corpus.py"
    mod = _load_mod(dc_path, "field_detective_corpus")
    if mod and hasattr(mod, "search_detective"):
        return mod.search_detective(query, limit=limit)
    return []


def _kb_field_research(query: str, *, limit: int = 4) -> list[dict[str, Any]]:
    if not FIELD_RESEARCH.is_dir():
        return []
    toks = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
    if not toks:
        return []
    hits: list[tuple[int, dict[str, Any]]] = []
    for md in sorted(FIELD_RESEARCH.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        low = text.lower()
        score = sum(3 if t in low else 0 for t in toks)
        if score <= 0:
            continue
        excerpt = ""
        for line in text.splitlines():
            if any(t in line.lower() for t in toks):
                excerpt = line.strip()[:320]
                break
        hits.append((score, {
            "source": "field_research",
            "book_id": md.stem,
            "title": md.stem.replace("-", " "),
            "text": excerpt or text[:320],
            "score": score,
        }))
    hits.sort(key=lambda x: -x[0])
    return [r for _, r in hits[:limit]]


def kb_search(query: str, *, limit: int = 12) -> dict[str, Any]:
    passages = _kb_passages(query, limit=min(8, limit))
    detective = _kb_detective(query, limit=4)
    research = _kb_field_research(query, limit=4)
    return {
        "query": query,
        "passages": passages,
        "detective": detective,
        "field_research": research,
        "hit_count": len(passages) + len(detective) + len(research),
    }


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"\W+", text.lower()) if len(t) > 2}


def _contradiction_score(claim: str, evidence: str) -> float:
    """Fast lexical contradiction — high rate, no ML."""
    c_tok = _tokens(claim)
    e_tok = _tokens(evidence)
    if not c_tok or not e_tok:
        return 0.0
    overlap = len(c_tok & e_tok) / max(len(c_tok), 1)
    contra = 0.0
    cl, el = claim.lower(), evidence.lower()
    pairs = (
        ("always", "never"), ("must", "must not"), ("secure", "insecure"),
        ("encrypt", "plaintext"), ("validate", "skip"), ("immutable", "mutable"),
        ("thread safe", "race"), ("fail closed", "fail open"),
    )
    for a, b in pairs:
        if a in cl and b in el:
            contra += 0.35
        if b in cl and a in el:
            contra += 0.35
    if re.search(r"\bno\b", cl) and re.search(r"\b(yes|allow|enable)\b", el):
        contra += 0.2
    if overlap < 0.08 and len(claim) > 40 and len(evidence) > 40:
        contra += 0.15
    return min(1.0, contra + (1.0 - overlap) * 0.25)


def truth_compare_pair(
    code_claim: str,
    kb_text: str,
    *,
    ironclad: dict[str, Any],
    kb_source: str = "",
) -> dict[str, Any]:
    code_truth = _analyze_truth(code_claim, ironclad=ironclad, local_evidence=0)
    kb_truth = _analyze_truth(kb_text, ironclad=ironclad, local_evidence=2)
    contradiction = _contradiction_score(code_claim, kb_text)
    code_score = float(code_truth.get("truth_score") or 0)
    kb_score = float(kb_truth.get("truth_score") or 0)
    delta = round(code_score - kb_score, 1)
    if contradiction >= 0.55 and kb_score >= 45:
        verdict = "bug"
    elif contradiction >= 0.35 or (delta < -20 and kb_score >= 50):
        verdict = "suspect"
    elif kb_score >= 55 and contradiction < 0.2:
        verdict = "clear"
    else:
        verdict = "investigate"
    return {
        "code_claim": code_claim[:240],
        "kb_text": kb_text[:240],
        "kb_source": kb_source,
        "contradiction": round(contradiction, 3),
        "code_truth_score": code_score,
        "kb_truth_score": kb_score,
        "truth_delta": delta,
        "verdict": verdict,
        "code_flags": code_truth.get("inconsistency_flags") or [],
        "kb_flags": kb_truth.get("inconsistency_flags") or [],
        "ironclad_sealed": bool(ironclad.get("ironclad_sealed")),
    }


def truth_compare_high_rate(
    pairs: list[tuple[str, str, str]],
    *,
    ironclad: dict[str, Any] | None = None,
    max_compares: int = 256,
) -> dict[str, Any]:
    """Batch Ironclad truth compare — reports compares/sec."""
    ic = ironclad if ironclad is not None else _ironclad_slice()
    capped = pairs[:max_compares]
    t0 = time.perf_counter()
    rows: list[dict[str, Any]] = []
    counts = {"bug": 0, "suspect": 0, "clear": 0, "investigate": 0}
    for code_claim, kb_text, kb_source in capped:
        row = truth_compare_pair(code_claim, kb_text, ironclad=ic, kb_source=kb_source)
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        rows.append(row)
    elapsed = max(time.perf_counter() - t0, 1e-9)
    rate = round(len(rows) / elapsed, 1)
    return {
        "compares": len(rows),
        "elapsed_ms": round(elapsed * 1000, 2),
        "truth_compares_per_sec": rate,
        "counts": counts,
        "ironclad": {
            "sealed": ic.get("ironclad_sealed"),
            "verdict": ic.get("verdict"),
            "truth_percent": ic.get("truth_percent"),
            "citation": ic.get("citation", "ironclad:bugfinder"),
        },
        "rows": rows,
    }


def extract_claims(source: str, *, path: str = "") -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    lines = source.splitlines()
    for i, line in enumerate(lines, 1):
        for m in CLAIM_RE.finditer(line):
            claims.append({"line": i, "kind": "claim", "text": m.group(0).strip(), "path": path})
        for pat in BUG_PATTERNS:
            if pat["severity"] == "info" and pat["id"] != "todo_fixme":
                continue
            if re.search(pat["re"], line):
                claims.append({
                    "line": i,
                    "kind": "heuristic",
                    "pattern_id": pat["id"],
                    "severity": pat["severity"],
                    "text": line.strip()[:200],
                    "path": path,
                    "kb_query": pat["kb"],
                })
    for m in DOCSTRING_RE.finditer(source):
        body = (m.group(1) or m.group(2) or "").strip()
        if len(body) >= 24:
            first = body.split("\n\n")[0].replace("\n", " ")[:220]
            claims.append({"line": 0, "kind": "docstring", "text": first, "path": path})
    return claims


def scan_heuristics(source: str, *, path: str = "") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for i, line in enumerate(source.splitlines(), 1):
        for pat in BUG_PATTERNS:
            if re.search(pat["re"], line):
                findings.append({
                    "line": i,
                    "pattern_id": pat["id"],
                    "severity": pat["severity"],
                    "text": line.strip()[:200],
                    "path": path,
                    "kb_query": pat["kb"],
                })
    return findings


def _read_target(path: Path) -> tuple[str, list[Path]]:
    path = path.expanduser().resolve()
    if path.is_file():
        if path.suffix.lower() not in CODE_EXTS:
            return "", []
        try:
            return path.read_text(encoding="utf-8", errors="replace"), [path]
        except OSError:
            return "", []
    files: list[Path] = []
    texts: list[str] = []
    if not path.is_dir():
        return "", []
    for p in sorted(path.rglob("*")):
        if not p.is_file() or p.suffix.lower() not in CODE_EXTS:
            continue
        if any(part in p.parts for part in (".git", "node_modules", "build", "__pycache__", ".venv")):
            continue
        try:
            texts.append(p.read_text(encoding="utf-8", errors="replace"))
            files.append(p)
        except OSError:
            continue
        if len(files) >= 48:
            break
    return "\n\n".join(texts), files


def find_bugs(
    target: str | Path,
    *,
    max_compares: int = 256,
    source_text: str = "",
) -> dict[str, Any]:
    gate = _thermal_gate(ops=max(1, max_compares // 32))
    ic = _ironclad_slice()
    path = Path(target) if target else Path(".")
    text = source_text
    files: list[Path] = []
    if not text.strip():
        text, files = _read_target(path)
    if not text.strip():
        return {"ok": False, "error": "no_source", "path": str(path)}

    all_claims: list[dict[str, Any]] = []
    all_heuristics: list[dict[str, Any]] = []
    if files:
        for fp in files:
            try:
                src = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            rel = str(fp)
            all_claims.extend(extract_claims(src, path=rel))
            all_heuristics.extend(scan_heuristics(src, path=rel))
    else:
        all_claims = extract_claims(text, path=str(path))
        all_heuristics = scan_heuristics(text, path=str(path))

    pairs: list[tuple[str, str, str]] = []
    kb_cache: dict[str, dict[str, Any]] = {}
    for claim in all_claims:
        query = str(claim.get("kb_query") or claim.get("text") or "")[:120]
        if query not in kb_cache:
            kb_cache[query] = kb_search(query, limit=6)
        kb = kb_cache[query]
        for hit in (kb.get("passages") or [])[:2]:
            pairs.append((claim["text"], str(hit.get("text") or hit.get("excerpt") or ""), "atlas"))
        for hit in (kb.get("detective") or [])[:1]:
            pairs.append((claim["text"], str(hit.get("body") or "")[:240], "detective"))
        for hit in (kb.get("field_research") or [])[:1]:
            pairs.append((claim["text"], str(hit.get("text") or ""), "field_research"))

    compare_doc = truth_compare_high_rate(pairs, ironclad=ic, max_compares=max_compares)

    truth_bugs: list[dict[str, Any]] = []
    for row in compare_doc.get("rows") or []:
        if row.get("verdict") in ("bug", "suspect"):
            truth_bugs.append(row)
    heuristic_bugs: list[dict[str, Any]] = []
    for h in all_heuristics:
        if h.get("severity") in ("high", "medium"):
            heuristic_bugs.append({
                "verdict": "heuristic",
                "severity": h["severity"],
                "pattern_id": h["pattern_id"],
                "line": h["line"],
                "path": h["path"],
                "text": h["text"],
                "kb_query": h["kb_query"],
            })
    bugs = heuristic_bugs + truth_bugs

    report = {
        "ok": gate.get("ok", True),
        "schema": "field-code-bugfinder/v1",
        "updated": _now(),
        "path": str(path),
        "file_count": len(files) or (1 if text else 0),
        "claim_count": len(all_claims),
        "heuristic_count": len(all_heuristics),
        "heuristic_actionable": len(heuristic_bugs),
        "truth_suspect_count": len(truth_bugs),
        "bug_count": len(bugs),
        "truth_compares_per_sec": compare_doc.get("truth_compares_per_sec"),
        "compare_summary": {
            "compares": compare_doc.get("compares"),
            "elapsed_ms": compare_doc.get("elapsed_ms"),
            "counts": compare_doc.get("counts"),
        },
        "ironclad_landing": compare_doc.get("ironclad"),
        "thermal_gate": gate,
        "heuristics": heuristic_bugs,
        "truth_suspects": truth_bugs[:48],
        "bugs": (heuristic_bugs + truth_bugs)[:96],
        "doctrine": str(DOCTRINE),
    }
    try:
        _save_report(report)
    except OSError:
        pass
    return report


def _save_report(doc: dict[str, Any]) -> None:
    REPORT_CACHE.parent.mkdir(parents=True, exist_ok=True)
    tmp = REPORT_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(REPORT_CACHE)


def build_panel(*, last_cycle: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = _load(DOCTRINE, {"schema": "field-code-bugfinder/v1"})
    last = _load(REPORT_CACHE, {})
    ic = _ironclad_slice()
    cycle = last_cycle or _load(FIX_QUEUE, {})
    comb = _combinatorics_posture()
    panel = {
        "schema": "field-code-bugfinder-panel/v1",
        "updated": _now(),
        "ok": True,
        "doctrine": doc,
        "ironclad": ic,
        "combinatorics": comb,
        "last_scan": {
            "path": last.get("path"),
            "bug_count": last.get("bug_count"),
            "truth_compares_per_sec": last.get("truth_compares_per_sec"),
            "updated": last.get("updated"),
        },
        "ironclad_bugfix": {
            "fix_count": cycle.get("fix_count"),
            "targets_scanned": cycle.get("targets_scanned"),
            "updated": cycle.get("updated"),
            "queue_path": str(FIX_QUEUE),
        },
        "scan_queue_preview": ironclad_scan_queue()[:8],
        "routes": {
            "panel": "/api/bugfinder",
            "scan": "/api/bugfinder/scan",
            "ironclad_cycle": "pythong lib/field-code-bugfinder.py ironclad-cycle",
        },
        "posture": (
            f"Ironclad {ic.get('verdict', '?')} · "
            f"comb {comb.get('pattern') or 'pending'} · "
            f"fixes queued {cycle.get('fix_count', 0)}"
        ),
    }
    PANEL.parent.mkdir(parents=True, exist_ok=True)
    tmp = PANEL.with_suffix(".tmp")
    tmp.write_text(json.dumps(panel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL)
    return panel


def panel_json() -> dict[str, Any]:
    return build_panel()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "posture"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("ironclad-cycle", "ironclad_cycle", "cycle"):
        max_t = 8
        max_c = 64
        if "--max-targets" in sys.argv:
            idx = sys.argv.index("--max-targets")
            if idx + 1 < len(sys.argv):
                max_t = int(sys.argv[idx + 1])
        if "--max-compares" in sys.argv:
            idx = sys.argv.index("--max-compares")
            if idx + 1 < len(sys.argv):
                max_c = int(sys.argv[idx + 1])
        out = ironclad_bugfix_cycle(max_compares_per_target=max_c, max_targets=max_t)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "queue":
        print(json.dumps({"queue": ironclad_scan_queue(), "combinatorics": _combinatorics_posture()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan" and len(sys.argv) >= 3:
        max_c = 256
        if "--max" in sys.argv:
            idx = sys.argv.index("--max")
            if idx + 1 < len(sys.argv):
                max_c = int(sys.argv[idx + 1])
        path = Path(sys.argv[2]).expanduser()
        out = find_bugs(path, max_compares=max_c)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok", True) else 1
    if cmd == "compare" and len(sys.argv) >= 4:
        out = truth_compare_pair(sys.argv[2], sys.argv[3], ironclad=_ironclad_slice())
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd == "kb" and len(sys.argv) >= 3:
        print(json.dumps(kb_search(" ".join(sys.argv[2:])), ensure_ascii=False, indent=2))
        return 0
    if cmd == "text" and len(sys.argv) >= 3:
        text = " ".join(sys.argv[2:])
        out = find_bugs(Path("."), source_text=text, max_compares=64)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": [
            "json", "ironclad-cycle [--max-targets N] [--max-compares N]", "queue",
            "scan PATH [--max N]", "compare CLAIM EVIDENCE", "kb QUERY", "text SNIPPET",
        ],
    }, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())