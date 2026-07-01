#!/usr/bin/env pythong
"""Hostess 7 MOS assistance — fill in for or assist any military occupational specialty."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "hostess7-mos-doctrine.json"
CATALOG = INSTALL / "data" / "hostess7-mos-catalog.json"
BATTERY = INSTALL / "data" / "hostess7-mos-battery.json"
EXPLAIN = INSTALL / "data" / "hostess7-mos-explain.json"
OCR_DOCTRINE = INSTALL / "data" / "hostess7-mos-ocr-doctrine.json"
PANEL = STATE / "hostess7-mos-panel.json"
RUNTIME = STATE / "hostess7-mos-runtime.json"
LEDGER = STATE / "hostess7-mos-ledger.jsonl"
OCR_CORPUS = STATE / "hostess7-mos-ocr-corpus.json"
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

ENABLED = os.environ.get("NEXUS_HOSTESS7_MOS", "1") == "1"

DISCLAIMER = (
    "MOS assistance is educational role knowledge — not orders from your chain of command. "
    "Hostess 7 assists and fills in procedurally; final authority remains your commissioned officers and NCOs. "
    "Not operational tasking or classified material."
)

_SECTION_LABELS = (
    ("what", "What"),
    ("why", "Why"),
    ("how", "How"),
    ("pitfalls", "Pitfalls"),
    ("where", "Where"),
    ("example", "Example"),
)

_MOS_KEYS = (
    "mos", "military occupational", "occupational specialty", "fill in for", "fill-in for",
    "assist as", "assist me as", "act as", "cover down as", "stand in as", "cmf",
    "rating", "afsc", "11b", "68w", "0311", "boatswain", "infantryman", "combat medic",
    "corpsman", "military police", "fire support", "cavalry scout", "cyber operations",
    "supply specialist", "wheeled vehicle mechanic", "human resources", "intelligence analyst",
    "mos mastery", "mos fluency", "any mos", "every mos",
)

_MOS_CODE_RE = re.compile(
    r"\b(?:"
    r"\d{2}[A-Z]\d?"           # Army 11B, 68W
    r"|0\d{3}"                  # Marines 0311
    r"|CMF[_\s]?\d{2}"          # CMF 11
    r"|\d[A-Z]\dX?\d"           # AFSC 1N0X1
    r"|[A-Z]{2,3}(?:_CG)?"      # Navy BM, OS_CG
    r")\b",
    re.I,
)

_MOS_LINE_RE = re.compile(
    r"(?:mos|duty|duties|tccc|pmcs|convoy|patrol|call\s+for\s+fire|hand\s+receipt|"
    r"supply|maintenance|intel|cyber|signal|artillery|infantry|medic|corpsman|"
    r"boatswain|quartermaster|avionics|jag|loac|reconnaissance|decontamination)",
    re.I,
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


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def _catalog_entries() -> list[dict[str, Any]]:
    doc = _load(CATALOG, {})
    return list(doc.get("entries") or [])


def _normalize_mos_id(raw: str) -> str:
    s = (raw or "").strip().upper().replace(" ", "_")
    s = re.sub(r"CMF[_\s]*", "CMF_", s)
    return s


def _load_mod(name: str, filename: str) -> Any | None:
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


def _hostess7_script(name: str) -> Any | None:
    script = HOSTESS7_ROOT / "scripts" / name
    if not script.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name.replace(".py", ""), script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(script.parent))
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _bridge_hits(bridges: list[str], query: str, *, limit: int = 2) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bridge in bridges or []:
        if len(out) >= limit:
            break
        b = str(bridge).lower()
        try:
            if b == "combat":
                mod = _load_mod("h7combat", "hostess7-combat.py")
                rows = mod.search_combat(query, limit=2) if mod else []
            elif b == "warfare":
                mod = _hostess7_script("field_warfare_corpus.py")
                rows = mod.search_warfare(query, limit=2) if mod else []
            elif b in ("biology", "medical"):
                mod = _load_mod("h7bio", "hostess7-biology.py")
                rows = mod.search_biology(query, limit=2) if mod else []
            elif b == "engineering":
                mod = _load_mod("h7eng", "hostess7-engineering.py")
                rows = mod.search_engineering(query, limit=2) if mod else []
            elif b == "programming":
                mod = _load_mod("h7prog", "hostess7-programming.py")
                if mod:
                    text = mod.explain_programming(query)
                    rows = [{"id": "programming_bridge", "title": "Programming assist", "body": text[:900]}] if text else []
                else:
                    rows = []
            else:
                rows = []
            for row in rows or []:
                rid = str(row.get("id", ""))
                if rid in seen:
                    continue
                seen.add(rid)
                out.append({**row, "bridge": b})
        except Exception:
            continue
    return out[:limit]


def _score_mos_entry(query: str, entry: dict[str, Any]) -> int:
    toks = _tokens(query)
    q = query.lower()
    eid = _normalize_mos_id(str(entry.get("id") or ""))
    tags = " ".join(entry.get("tags") or []).lower()
    title = str(entry.get("title", "")).lower()
    duties = str(entry.get("duties", "")).lower()
    branch = str(entry.get("branch", "")).lower()
    blob = f"{eid} {title} {tags} {duties} {branch}"
    score = 0

    for m in _MOS_CODE_RE.finditer(query):
        code = _normalize_mos_id(m.group(0))
        if code == eid or code in eid or eid.startswith(code):
            score += 40
        if code.replace("X", "") in eid.replace("X", ""):
            score += 25

    score += sum(5 if t in tags else 3 if t in blob else 0 for t in toks)
    if eid.lower() in q.replace("-", "_"):
        score += 30
    if title and title in q:
        score += 22
    if any(k in q for k in ("fill in", "fill-in", "assist as", "assist me", "act as", "cover down")):
        score += 4
    if "army" in q and branch == "army":
        score += 6
    if "navy" in q and branch == "navy":
        score += 6
    if "marine" in q and branch == "marine corps":
        score += 6
    if "air force" in q and branch == "air force":
        score += 6
    if "coast guard" in q and branch == "coast guard":
        score += 6
    if "space force" in q and branch == "space force":
        score += 6
    return score


def resolve_mos(query: str) -> dict[str, Any] | None:
    """Resolve a query to the best MOS catalog entry."""
    entries = _catalog_entries()
    if not entries:
        return None
    scored = [( _score_mos_entry(query, e), e) for e in entries]
    scored = [(s, e) for s, e in scored if s > 0]
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    best_score, best = scored[0]
    if best_score < 4:
        return None
    return dict(best)


def search_mos(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Search MOS catalog entries by code, title, or duties."""
    entries = _catalog_entries()
    scored = [( _score_mos_entry(query, e), e) for e in entries]
    scored = [(s, e) for s, e in scored if s > 0]
    scored.sort(key=lambda x: -x[0])
    out: list[dict[str, Any]] = []
    for _, e in scored[:limit]:
        row = dict(e)
        row["source"] = "mos_catalog"
        out.append(row)
    return out


def assist_mos(query: str, *, fill_in: bool = True) -> dict[str, Any]:
    """Assist or fill-in for a resolved MOS."""
    mos = resolve_mos(query) or (search_mos(query, limit=1)[0] if search_mos(query, limit=1) else None)
    if not mos:
        return {"ok": False, "error": "mos_not_resolved", "query": query}
    bridges = mos.get("bridges") or []
    bridge_rows = _bridge_hits(bridges, query, limit=2)
    mode = "fill_in" if fill_in or any(k in query.lower() for k in ("fill in", "fill-in", "cover down", "act as")) else "assist"
    return {
        "ok": True,
        "mode": mode,
        "mos_id": mos.get("id"),
        "branch": mos.get("branch"),
        "family": mos.get("family"),
        "title": mos.get("title"),
        "duties": mos.get("duties"),
        "assist": mos.get("assist"),
        "bridges": bridges,
        "bridge_hits": bridge_rows,
    }


def format_mos_reply(query: str) -> str:
    doc = assist_mos(query)
    if not doc.get("ok"):
        return (
            f"I could not resolve that MOS — try a code (11B, 68W, HM, 0311, 25B, 2A3X3) or title (infantryman, combat medic). "
            f"{DISCLAIMER}"
        )
    paras: list[str] = [DISCLAIMER]
    mode = doc.get("mode", "assist")
    title = doc.get("title", "MOS")
    branch = doc.get("branch", "")
    mos_id = doc.get("mos_id", "")
    paras.append(
        f"{'Fill-in' if mode == 'fill_in' else 'Assist'} — {branch} {mos_id} {title}: "
        f"{doc.get('duties', '')}"
    )
    paras.append(f"How I help: {doc.get('assist', '')}")
    for hit in doc.get("bridge_hits") or []:
        btitle = hit.get("title", "Bridge")
        body = str(hit.get("body", "")).strip()
        if len(body) > 800:
            body = body[:800] + "…"
        bridge = hit.get("bridge", "")
        paras.append(f"{btitle} ({bridge} bridge): {body}")
    return "\n\n".join(paras)


def list_mos_catalog(*, branch: str | None = None, family: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for e in _catalog_entries():
        if branch and str(e.get("branch", "")).lower() != branch.lower():
            continue
        if family and str(e.get("family", "")).lower() != family.lower():
            continue
        out.append({
            "id": e.get("id"),
            "branch": e.get("branch"),
            "family": e.get("family"),
            "title": e.get("title"),
        })
    return out


def _looks_like_mos(text: str) -> bool:
    low = (text or "").lower()
    if any(k in low for k in _MOS_KEYS):
        return True
    if _MOS_CODE_RE.search(text or ""):
        return True
    if _MOS_LINE_RE.search(low):
        return True
    return False


def extract_mos_query(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    for prefix in (
        r"^(?:please\s+)?(?:assist(?:\s+me)?\s+as|fill\s+in\s+for|act\s+as|cover\s+down\s+as)\s+",
        r"^(?:please\s+)?(?:explain|describe)\s+",
        r"^what(?:'s| is| are)\s+",
        r"^how does\s+",
    ):
        m = re.match(prefix, low, re.I)
        if m:
            return raw[m.end():].strip().rstrip("?.!")
    return raw


def _battery_hit(query: str, expected_mos: str) -> bool:
    mos = resolve_mos(query)
    if mos and _normalize_mos_id(str(mos.get("id", ""))) == _normalize_mos_id(expected_mos):
        return True
    hits = search_mos(query, limit=4)
    exp = _normalize_mos_id(expected_mos)
    for h in hits:
        if _normalize_mos_id(str(h.get("id", ""))) == exp:
            return True
    return False


def _run_battery() -> dict[str, Any]:
    doc = _load(BATTERY, {})
    problems = doc.get("problems") or []
    results: list[dict[str, Any]] = []
    passed = 0
    by_cat: dict[str, dict[str, int]] = {}
    catalog_n = len(_catalog_entries())
    for prob in problems:
        query = str(prob.get("query") or "")
        expected = str(prob.get("expected_mos") or "")
        cat = str(prob.get("category") or "misc")
        ok = _battery_hit(query, expected)
        if ok:
            passed += 1
        bucket = by_cat.setdefault(cat, {"passed": 0, "total": 0})
        bucket["total"] += 1
        if ok:
            bucket["passed"] += 1
        results.append({
            "id": prob.get("id"),
            "category": cat,
            "query": query,
            "expected_mos": expected,
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
        "catalog_entries": catalog_n,
        "branches_covered": len({e.get("branch") for e in _catalog_entries()}),
    }


def _pattern_mastery() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    bat = _run_battery()
    out: list[dict[str, Any]] = []
    for pat in doctrine.get("patterns") or []:
        pid = str(pat.get("id") or "")
        mastered = False
        if pid == "mos_catalog":
            mastered = len(_catalog_entries()) >= 50
        elif pid == "mos_resolve":
            mastered = resolve_mos("assist 11B infantryman") is not None
        elif pid == "chamber_bridges":
            mastered = bool(_bridge_hits(["combat", "warfare"], "patrol measures", limit=1))
        elif pid == "battery_verify":
            mastered = bool(bat.get("passed"))
        elif pid == "disclaimer_seal":
            mastered = DISCLAIMER in format_mos_reply("assist 68W")
        elif pid == "fill_in_assist":
            mastered = assist_mos("fill in for 25B").get("ok")
        elif pid == "structured_explain":
            mastered = bool(_load(EXPLAIN, {}).get("topics"))
        elif pid == "ocr_vision_train":
            tr = _load(STATE / "hostess7-mos-ocr-train.json", {})
            mastered = bool(tr.get("fluent") or tr.get("mastered"))
        out.append({"id": pid, "label": pat.get("label"), "mastered": mastered})
    return out


def mos_score(*, battery: dict[str, Any] | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    bat = battery or _run_battery()
    patterns = _pattern_mastery()
    mastered = sum(1 for p in patterns if p.get("mastered"))
    rate = float(bat.get("pass_rate") or 0) / 100.0
    by_cat = bat.get("by_category") or {}
    cats_mastered = sum(1 for c in by_cat.values() if c.get("total") and c["passed"] >= c["total"])
    ocr_train = _load(STATE / "hostess7-mos-ocr-train.json", {})
    catalog_n = int(bat.get("catalog_entries") or len(_catalog_entries()))

    score = 0.64
    score += 0.18 * rate
    score += 0.06 * min(1.0, mastered / max(len(patterns), 1))
    score += 0.04 * min(1.0, cats_mastered / 10.0)
    score += 0.04 * min(1.0, catalog_n / 60.0)
    score += 0.02 * min(1.0, int(ocr_train.get("verified_count") or 0) / 200.0)
    score += 0.02 if bat.get("branches_covered", 0) >= 5 else 0.0
    score = round(min(0.99, score), 4)

    fluent_floor = float(doctrine.get("fluent_floor_score") or 0.86)
    master_target = float(doctrine.get("master_mos_score") or 0.95)
    tier = "assistant_guess"
    if score >= master_target and bat.get("passed") and cats_mastered >= 8:
        tier = "mos_master"
    elif score >= fluent_floor and bat.get("passed"):
        tier = "mos_fluent"
    elif rate >= 0.5:
        tier = "mos_basic"

    return {
        "score": score,
        "mos_score": score,
        "tier": tier,
        "fluent": tier in ("mos_fluent", "mos_master"),
        "mastered": tier == "mos_master",
        "better_than_assistant": score >= fluent_floor and bat.get("passed"),
        "battery": bat,
        "patterns_mastered": mastered,
        "patterns_total": len(patterns),
        "categories_mastered": cats_mastered,
        "catalog_entries": catalog_n,
        "branches_covered": bat.get("branches_covered"),
    }


def _topic_match_score(topic: dict[str, Any], q: str) -> int:
    score = 0
    for kw in topic.get("keywords") or []:
        kw_l = str(kw).lower().strip()
        if kw_l and kw_l in q:
            score += len(kw_l) + (12 if q.strip() == kw_l else 0)
    return score


def _explain_doc() -> dict[str, Any]:
    base = _load(EXPLAIN, {"topics": []})
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("h7overlay", INSTALL / "lib" / "hostess7-explain-overlay.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.merge_explain_doc("mos", base)
    except Exception:
        pass
    return base


def explain_mos_structured(query: str = "") -> dict[str, Any]:
    q = (query or "").strip()
    low = q.lower()
    doc = _explain_doc()
    intro = str(doc.get("introduction") or "").strip()
    fmt = doc.get("format") or [s[0] for s in _SECTION_LABELS]
    metrics = mos_score()
    topic = None
    best_score = 0
    for t in doc.get("topics") or []:
        sc = _topic_match_score(t, low)
        if sc > best_score:
            best_score = sc
            topic = t
    if not topic and any(k in low for k in ("mos", "fill in", "military occupational", "assist as")):
        doctrine = _load(DOCTRINE, {})
        topic = {
            "id": "mos_fluency_live",
            "what": "I fill in for or assist any military MOS across all branches with catalog resolution and chamber bridges.",
            "why": str(doctrine.get("fluency_claim") or ""),
            "how": (
                f"Battery {metrics.get('battery', {}).get('pass_rate')}% · tier {metrics.get('tier')} · "
                f"catalog {metrics.get('catalog_entries')} entries · {metrics.get('branches_covered')} branches"
            ),
            "pitfalls": "Chain-of-command bypass; classified ops; inventing MOS duties.",
            "where": "lib/hostess7-mos.py, data/hostess7-mos-catalog.json, /api/hostess7/mos",
            "example": "fill in for 68W — combat medic duties, TCCC, medical bridge.",
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
            "mos_score": metrics.get("score"),
            "tier": metrics.get("tier"),
            "disclaimer": DISCLAIMER,
            "format": fmt,
        }
    fallback = intro + " " + DISCLAIMER
    return {"ok": True, "query": q, "reply": fallback.strip(), "format": fmt, "disclaimer": DISCLAIMER}


def explain_mos(query: str = "") -> str:
    return str(explain_mos_structured(query).get("reply") or "")


def build_panel(*, write: bool = True) -> dict[str, Any]:
    metrics = mos_score()
    doc = {
        "schema": "hostess7-mos/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "mos_score": metrics.get("score"),
        "tier": metrics.get("tier"),
        "fluent": metrics.get("fluent"),
        "mastered": metrics.get("mastered"),
        "better_than_assistant": metrics.get("better_than_assistant"),
        "battery_pass_rate": metrics.get("battery", {}).get("pass_rate"),
        "catalog_entries": metrics.get("catalog_entries"),
        "branches_covered": metrics.get("branches_covered"),
        "categories_mastered": metrics.get("categories_mastered"),
        "patterns_mastered": metrics.get("patterns_mastered"),
        "patterns_total": metrics.get("patterns_total"),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "disclaimer": DISCLAIMER,
    }
    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "hostess7-mos-runtime/v1",
            "updated": doc["updated"],
            "tier": doc["tier"],
            "mos_score": doc["mos_score"],
        })
    return doc


def _text_quality_ok(text: str) -> bool:
    sample = (text or "")[:400]
    if len(sample.strip()) < 3:
        return False
    printable = sum(1 for c in sample if c.isprintable() or c in "\n\t")
    return printable / max(len(sample), 1) >= 0.85


def _ocr_tesseract(path: Path) -> str:
    core_py = INSTALL / "lib" / "final-eye-ocr-core.py"
    if not core_py.is_file():
        return ""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("final_eye_ocr_mos", core_py)
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


def _ingest_mos_text(text: str, *, source_id: str, path: str, corpus: dict[str, Any]) -> int:
    if not _text_quality_ok(text):
        return 0
    ocr_doc = _load(OCR_DOCTRINE, {})
    min_len = int((ocr_doc.get("train") or {}).get("min_candidate_len") or 10)
    max_c = int((ocr_doc.get("ingest") or {}).get("max_candidates_per_ingest") or 6000)
    if len(corpus.get("candidates") or []) >= max_c:
        return 0
    added = 0
    known = corpus.setdefault("seen_hashes", [])
    seen_set = set(known[-50000:])
    for line in re.split(r"[\n.;]+", text):
        cand = re.sub(r"\s+", " ", line.strip())[:500]
        if len(cand) < min_len:
            continue
        if not _looks_like_mos(cand):
            continue
        h = hashlib.sha256(f"{source_id}:{cand}".encode()).hexdigest()[:24]
        if h in seen_set:
            continue
        seen_set.add(h)
        known.append(h)
        corpus["candidates"].append({
            "text": cand,
            "source_id": source_id,
            "hash": h,
            "path": path,
            "ingested_at": _now(),
        })
        added += 1
        if len(corpus["candidates"]) >= max_c:
            break
    return added


def ingest_ocr_vision(*, limit_per_source: int | None = None) -> dict[str, Any]:
    """Feed MOS think tank from Final_Eye vision + Hostess7 brain corpora."""
    ocr_doc = _load(OCR_DOCTRINE, {})
    ingest_cfg = ocr_doc.get("ingest") or {}
    max_files = limit_per_source or int(ingest_cfg.get("max_files_per_source") or 400)
    max_bytes = int(ingest_cfg.get("max_bytes_per_file") or 250000)
    corpus = _load(OCR_CORPUS, {
        "schema": "hostess7-mos-ocr-corpus/v1",
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
                        added += _ingest_mos_text(chunk, source_id=sid, path=str(fp), corpus=corpus)
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
                            for chunk in _text_chunks_from_row(row, spec):
                                bytes_read += len(chunk)
                                added += _ingest_mos_text(chunk, source_id=sid, path=str(fp), corpus=corpus)
                    files_read = 1
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
                    text = _ocr_tesseract(fp) if spec.get("ocr_tesseract") else fp.read_text(encoding="utf-8", errors="replace")[:max_bytes]
                    bytes_read += len(text)
                    added += _ingest_mos_text(text, source_id=sid, path=str(fp), corpus=corpus)
                    files_read += 1
                except OSError:
                    continue
        total_added += added
        source_stats[sid] = {"files_read": files_read, "bytes_read": bytes_read, "candidates_added": added, "kind": kind}
        corpus["sources"][sid] = {**source_stats[sid], "updated": _now()}

    for entry in _catalog_entries():
        text = f"{entry.get('title')} {entry.get('duties')} {entry.get('assist')}"
        total_added += _ingest_mos_text(text, source_id="mos_catalog", path=str(CATALOG), corpus=corpus)

    corpus["updated"] = _now()
    corpus["candidate_count"] = len(corpus.get("candidates") or [])
    corpus["ingest_total_added"] = int(corpus.get("ingest_total_added") or 0) + total_added
    _save(OCR_CORPUS, corpus)
    return {"ok": True, "added": total_added, "candidate_count": corpus["candidate_count"], "sources": source_stats}


def train_ocr_vision(*, limit: int = 300) -> dict[str, Any]:
    corpus = _load(OCR_CORPUS, {"candidates": []})
    candidates = list(corpus.get("candidates") or [])
    verified = sum(1 for c in candidates[:limit] if resolve_mos(str(c.get("text") or "")))
    total = len(candidates)
    rate = verified / max(total, 1)
    train_doc = {
        "schema": "hostess7-mos-ocr-train/v1",
        "updated": _now(),
        "candidate_count": total,
        "verified_count": verified,
        "verified_rate": round(rate, 4),
        "fluent": verified >= 35,
        "mastered": verified >= 90,
    }
    _save(STATE / "hostess7-mos-ocr-train.json", train_doc)
    return {"ok": True, **train_doc}


def ocr_vision_status() -> dict[str, Any]:
    return {
        "schema": "hostess7-mos-ocr-status/v1",
        "updated": _now(),
        "corpus": _load(OCR_CORPUS, {}),
        "train": _load(STATE / "hostess7-mos-ocr-train.json", {}),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "battery":
        print(json.dumps(_run_battery(), ensure_ascii=False))
        return 0
    if cmd == "score":
        print(json.dumps(mos_score(), ensure_ascii=False))
        return 0
    if cmd in ("search", "resolve", "assist"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "assist 11B infantryman"
        if cmd == "resolve":
            print(json.dumps({"ok": True, "query": q, "mos": resolve_mos(q)}, ensure_ascii=False))
        elif cmd == "assist":
            print(json.dumps(assist_mos(q), ensure_ascii=False))
        else:
            print(json.dumps({"ok": True, "query": q, "hits": search_mos(q), "reply": format_mos_reply(q)}, ensure_ascii=False))
        return 0
    if cmd == "catalog":
        print(json.dumps({"entries": list_mos_catalog()}, ensure_ascii=False))
        return 0
    if cmd in ("teach", "explain"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "mos fluency"
        doc = explain_mos_structured(q)
        print(doc.get("reply") or "")
        return 0
    if cmd in ("ocr-ingest", "ocr-train", "ocr-status"):
        if cmd == "ocr-ingest":
            print(json.dumps(ingest_ocr_vision(), ensure_ascii=False))
        elif cmd == "ocr-train":
            print(json.dumps(train_ocr_vision(), ensure_ascii=False))
        else:
            print(json.dumps(ocr_vision_status(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-mos.py [json|assist|battery|catalog|teach|ocr-ingest]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())