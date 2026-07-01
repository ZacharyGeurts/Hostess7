#!/usr/bin/env pythong
"""Hostess 7 combat chamber — educational martial arts and defense doctrine."""
from __future__ import annotations

import hashlib
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
DOCTRINE = INSTALL / "data" / "hostess7-combat-doctrine.json"
BATTERY = INSTALL / "data" / "hostess7-combat-battery.json"
EXPLAIN = INSTALL / "data" / "hostess7-combat-explain.json"
OCR_DOCTRINE = INSTALL / "data" / "hostess7-combat-ocr-doctrine.json"
PANEL = STATE / "hostess7-combat-panel.json"
RUNTIME = STATE / "hostess7-combat-runtime.json"
LEDGER = STATE / "hostess7-combat-ledger.jsonl"
OCR_CORPUS = STATE / "hostess7-combat-ocr-corpus.json"
OCR_LEDGER = STATE / "hostess7-combat-ocr-ledger.jsonl"
MOTION_PANEL = STATE / "humanoid-motion-panel.json"
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

ENABLED = os.environ.get("NEXUS_HOSTESS7_COMBAT", "1") == "1"

DISCLAIMER = (
    "Educational martial arts and defense doctrine only — not instructions to harm. "
    "Lawful self-defense where permitted by jurisdiction; de-escalation and retreat when possible. "
    "Not military operational orders."
)

_SECTION_LABELS = (
    ("what", "What"),
    ("why", "Why"),
    ("how", "How"),
    ("pitfalls", "Pitfalls"),
    ("where", "Where"),
    ("example", "Example"),
)

_COMBAT_KEYS = (
    "combat", "martial arts", "martial art", "fighting", "self defense", "self-defense",
    "striking", "boxing", "kickboxing", "grappling", "bjj", "jiu jitsu", "wrestling", "mma",
    "kung fu", "wing chun", "karate", "muay thai", "judo", "takedown", "submission", "guard",
    "stance", "footwork", "sparring", "dojo", "conditioning", "tactical", "awareness", "ooda",
    "de-escalation", "less lethal", "less-lethal", "pepper spray", "taser", "stun gun",
    "combat mastery", "combat fluency", "defense doctrine",
)

_COMBAT_LINE_RE = re.compile(
    r"(?:"
    r"martial|combat|strike|striking|punch|jab|cross|hook|uppercut|kick|roundhouse|elbow|knee|"
    r"boxing|kickbox|muay\s+thai|grappl|bjj|jiu[\s-]?jitsu|guard|armbar|triangle|choke|submission|"
    r"wrestl|takedown|sprawl|double\s+leg|single\s+leg|mma|clinch|cage|kung\s+fu|wing\s+chun|"
    r"shaolin|karate|judo|self[\s-]?defen|de[\s-]?escalat|awareness|ooda|tactical|footwork|"
    r"stance|sparring|dojo|conditioning|cardio|flexibility|pepper\s+spray|taser|stun\s+gun|"
    r"less[\s-]?lethal|cover|concealment|egress|surveillance"
    r")",
    re.I,
)

COMBAT_DOMAINS: tuple[dict[str, Any], ...] = (
    {
        "id": "foundations_combat",
        "title": "Combat foundations",
        "tags": ("foundations", "combat", "stance", "discipline", "respect", "ethics", "sportsmanship", "dojo"),
        "body": (
            "Combat foundations: balanced stance, guard, footwork base, breathing, and respect for training partners. "
            "Ethics: sport rules differ from street law; educational doctrine prioritizes discipline, humility, and "
            "lawful conduct. Warm-up, mobility, and progressive overload prevent injury. "
            "Hostess 7 teaches foundations before specialization — never glamorize violence."
        ),
    },
    {
        "id": "striking",
        "title": "Striking fundamentals",
        "tags": ("striking", "punch", "jab", "cross", "hook", "uppercut", "kick", "elbow", "knee", "muay thai", "guard"),
        "body": (
            "Striking: jab (lead hand probe), cross (rear straight), hook (arc to head/body), uppercut (vertical close range). "
            "Kicks: front kick (teep), roundhouse (hip rotation), low kick (calf/thigh). Elbows and knees in clinch range. "
            "Mechanics: hip rotation, chin tucked, hands return to guard, weight transfer. Training: pads, bag, controlled sparring — "
            "educational sport context only."
        ),
    },
    {
        "id": "boxing_kickboxing",
        "title": "Boxing & kickboxing",
        "tags": ("boxing", "kickboxing", "footwork", "combinations", "roundhouse", "teep", "low kick", "ring", "rounds"),
        "body": (
            "Boxing emphasizes hands, head movement, and footwork — angles, pivot, slip, roll. Combinations: jab-cross-hook, "
            "body-head patterns. Kickboxing adds legs: low kick, roundhouse, front kick (teep). "
            "Distance management: long (kicks), mid (punches), close (clinch). Rule sets vary by organization — "
            "educational overview, not competition coaching for harm."
        ),
    },
    {
        "id": "grappling_bjj",
        "title": "Grappling & Brazilian jiu-jitsu",
        "tags": ("grappling", "bjj", "jiu jitsu", "guard", "armbar", "triangle", "choke", "mount", "side control", "submission"),
        "body": (
            "Grappling and BJJ: positional hierarchy — mount, back control, side control, guard. Guard types: closed, open, half. "
            "Submissions: armbar, triangle choke, rear-naked choke (training tap discipline). "
            "Escapes and sweeps return to standing or dominant position. Sport BJJ differs from self-defense priorities — "
            "educational control and joint safety in training."
        ),
    },
    {
        "id": "wrestling",
        "title": "Wrestling",
        "tags": ("wrestling", "takedown", "double leg", "single leg", "sprawl", "mat return", "pin", "folkstyle", "freestyle"),
        "body": (
            "Wrestling: level change, penetration step, takedowns (double leg, single leg), sprawls defend shots. "
            "Mat returns and rides control grounded opponents in sport rules. "
            "Strength, balance, and grip fighting dominate. Educational sport wrestling — not street fighting instruction."
        ),
    },
    {
        "id": "mma_mixed",
        "title": "Mixed martial arts",
        "tags": ("mma", "mixed martial arts", "clinch", "cage", "ground pound", "unified rules", "ufc", "grappling", "striking"),
        "body": (
            "MMA integrates striking, clinch, and ground fighting under unified rules. Phases: distance striking, clinch knees/elbows, "
            "takedown, ground-and-pound, submissions. Cage awareness: cut angles, stand-up against fence. "
            "Educational rules overview — fouls include eye gouge, groin strikes, spine strikes. Not street combat advice."
        ),
    },
    {
        "id": "kung_fu",
        "title": "Kung fu & Chinese martial arts",
        "tags": ("kung fu", "kung_fu", "wing chun", "shaolin", "hung gar", "tai chi", "centerline", "forms", "chi sao"),
        "body": (
            "Kung fu encompasses diverse Chinese arts: Wing Chun (centerline, chain punch, chi sao), Shaolin (long fist, stances), "
            "Hung Gar (tiger crane), Tai Chi (soft internal). Forms (taolu) encode technique; application requires instructor guidance. "
            "Educational cultural and technical overview — motion bridge loads Matrix skills when available."
        ),
    },
    {
        "id": "self_defense",
        "title": "Lawful self-defense",
        "tags": ("self defense", "self-defense", "de-escalation", "escape", "lawful", "boundary", "awareness", "retreat", "proportional"),
        "body": (
            "Lawful self-defense education: avoid confrontation when possible; verbal boundaries; create distance; "
            "move toward exits and witnesses; report to authorities. Proportional response only where jurisdiction permits — "
            "not revenge or vigilantism. De-escalation beats technique when safe. Consult local law; this is not legal advice."
        ),
    },
    {
        "id": "tactical_awareness",
        "title": "Tactical awareness",
        "tags": ("tactical", "awareness", "ooda", "situational", "observe", "orient", "decide", "cover", "concealment", "egress"),
        "body": (
            "Tactical awareness: OODA loop (observe, orient, decide, act). Environmental scan — exits, cover vs concealment, "
            "lighting, crowd density. Baseline normal vs anomaly detection. Egress planning before crisis. "
            "Lawful reporting to authorities — not surveillance of individuals without cause. Paired with warfare corpus protective doctrine."
        ),
    },
    {
        "id": "fitness_conditioning",
        "title": "Fitness & conditioning for combat sports",
        "tags": ("fitness", "conditioning", "strength", "cardio", "flexibility", "mobility", "endurance", "recovery", "training"),
        "body": (
            "Combat conditioning: aerobic base (roadwork, bike), anaerobic intervals (rounds, sprints), strength (compound lifts, "
            "grip, neck care with caution), mobility and flexibility. Periodization prevents overtraining. "
            "Recovery: sleep, hydration, nutrition. Educational fitness — consult trainers for personal programming."
        ),
    },
    {
        "id": "weapons_education",
        "title": "Weapons education (less-lethal / educational)",
        "tags": ("weapons", "less lethal", "less-lethal", "pepper spray", "taser", "stun gun", "educational", "recognition", "misuse"),
        "body": (
            "Educational less-lethal recognition only — not tactical employment. Pepper spray (OC), conducted electrical weapons (Taser), "
            "stun guns: legal status varies by jurisdiction; misuse against non-threats may be criminal. "
            "Medical risks: respiratory distress, cardiac stress, falls. Recognize and report misuse; seek lawful authority. "
            "No instructions to arm or harm."
        ),
    },
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


def _warfare_module() -> Any | None:
    script = HOSTESS7_ROOT / "scripts" / "field_warfare_corpus.py"
    if not script.is_file():
        return None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_warfare_corpus", script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(script.parent))
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _motion_skills_loaded() -> list[dict[str, Any]]:
    panel = _load(MOTION_PANEL, {})
    skills = panel.get("skills_loaded") or panel.get("loaded_skills") or []
    if isinstance(skills, list):
        return [s for s in skills if isinstance(s, dict)]
    return []


def _score_combat_domains(query: str, domains: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for d in domains:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:1500]}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("foundation", "stance", "discipline", "ethics", "sportsmanship", "dojo")):
            if d.get("id") == "foundations_combat":
                score += 15
        if any(k in q for k in ("strike", "striking", "jab", "cross", "hook", "uppercut", "elbow", "knee", "muay")):
            if d.get("id") == "striking":
                score += 15
        if any(k in q for k in ("boxing", "kickboxing", "footwork", "combination", "roundhouse", "teep", "low kick")):
            if d.get("id") == "boxing_kickboxing":
                score += 15
        if any(k in q for k in ("bjj", "grappling", "guard", "armbar", "triangle", "choke", "mount", "jiu")):
            if d.get("id") == "grappling_bjj":
                score += 15
        if any(k in q for k in ("wrestling", "takedown", "double leg", "single leg", "sprawl", "mat return")):
            if d.get("id") == "wrestling":
                score += 15
        if any(k in q for k in ("mma", "mixed martial", "clinch", "cage", "ground pound", "unified rules")):
            if d.get("id") == "mma_mixed":
                score += 15
        if any(k in q for k in ("kung fu", "kung_fu", "wing chun", "shaolin", "centerline", "forms")):
            if d.get("id") == "kung_fu":
                score += 15
        if any(k in q for k in ("self defense", "self-defense", "de-escalation", "deescalat", "lawful", "boundary", "escape")):
            if d.get("id") == "self_defense":
                score += 15
        if any(k in q for k in ("tactical", "awareness", "ooda", "observe", "orient", "cover", "concealment", "egress", "situational")):
            if d.get("id") == "tactical_awareness":
                score += 15
        if any(k in q for k in ("conditioning", "fitness", "strength", "cardio", "flexibility", "mobility")):
            if d.get("id") == "fitness_conditioning":
                score += 15
        if any(k in q for k in ("less lethal", "less-lethal", "pepper spray", "taser", "stun gun", "stun", "weapons")):
            if d.get("id") == "weapons_education":
                score += 15
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return scored


def search_combat(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Search combat domains and warfare corpus bridge."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    q = query.lower()
    tactical = any(
        k in q
        for k in (
            "tactical", "awareness", "surveillance", "counter-surveillance", "alert", "heightened",
            "protective measure", "countermeasure", "terror", "homeland", "loac", "geneva",
            "stun", "taser", "less-lethal", "less lethal", "rf", "jamming", "cover", "concealment",
            "egress", "soft target", "infrastructure",
        )
    )

    war_mod = _warfare_module()
    if war_mod and tactical:
        try:
            war_mod.ensure_corpus()
            for row in war_mod.search_warfare(query, limit=max(2, limit // 2 + 1)):
                pid = str(row.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)
                out.append({**row, "source": row.get("source") or "warfare_corpus"})
        except Exception:
            pass

    domain_scored = _score_combat_domains(query, [dict(d) for d in COMBAT_DOMAINS])
    for _, d in domain_scored:
        did = str(d.get("id", ""))
        if did in seen:
            continue
        seen.add(did)
        row = dict(d)
        row["source"] = "combat_domain"
        out.append(row)
        if len(out) >= limit:
            break

    if not out and war_mod:
        try:
            for row in war_mod.search_warfare(query, limit=limit):
                pid = str(row.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)
                out.append({**row, "source": "warfare_corpus"})
        except Exception:
            pass

    return out[:limit]


def synthesize_combat_paragraphs(query: str) -> list[str]:
    hits = search_combat(query, limit=4)
    if not hits:
        hits = search_combat("martial arts self defense tactical awareness", limit=3)
    paras: list[str] = [DISCLAIMER]
    for h in hits:
        title = h.get("title", "Combat")
        body = str(h.get("body", "")).strip()
        if len(body) > 1100:
            body = body[:1100] + "… [truncated]"
        src = h.get("source", "")
        if src == "warfare_corpus":
            paras.append(f"{title} (warfare corpus): {body}")
        else:
            paras.append(f"{title}: {body}")
    return paras


def format_combat_reply(query: str) -> str:
    paras = synthesize_combat_paragraphs(query)
    if len(paras) <= 1:
        return (
            "I could not match that combat query cleanly — try striking, grappling, self-defense, or tactical awareness. "
            f"{DISCLAIMER}"
        )
    return "\n\n".join(paras)


def _looks_like_combat(text: str) -> bool:
    low = (text or "").lower()
    if any(k in low for k in _COMBAT_KEYS):
        return True
    if _COMBAT_LINE_RE.search(low):
        return True
    return False


def extract_combat_query(text: str) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    low = raw.lower()
    for prefix in (
        r"^(?:please\s+)?(?:explain|describe|tell me about)\s+",
        r"^what(?:'s| is)\s+",
        r"^how does\s+",
        r"^how do\s+",
        r"^why does\s+",
        r"^define\s+",
    ):
        m = re.match(prefix, low, re.I)
        if m:
            return raw[m.end():].strip().rstrip("?.!")
    return raw


def _battery_hit(query: str, expected_domain: str) -> bool:
    hits = search_combat(query, limit=6)
    exp = expected_domain.lower()
    for h in hits:
        hid = str(h.get("id", "")).lower()
        if hid == exp:
            return True
        tags = " ".join(h.get("tags") or []).lower()
        if exp in tags or exp in hid:
            return True
        title = str(h.get("title", "")).lower()
        if exp.replace("_", " ") in title:
            return True
    return False


def _run_battery() -> dict[str, Any]:
    doc = _load(BATTERY, {})
    problems = doc.get("problems") or []
    results: list[dict[str, Any]] = []
    passed = 0
    by_cat: dict[str, dict[str, int]] = {}
    for prob in problems:
        query = str(prob.get("query") or "")
        expected = str(prob.get("expected_domain") or "")
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
            "expected_domain": expected,
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
        "warfare_corpus_available": _warfare_module() is not None,
    }


def _text_quality_ok(text: str) -> bool:
    if not text:
        return False
    sample = text[:4000]
    if "\x00" in sample or "H7C" in sample[:8]:
        return False
    printable = sum(1 for c in sample if c.isprintable() or c in "\n\t")
    return printable / max(len(sample), 1) >= 0.85


def _plausible_combat_candidate(text: str) -> bool:
    if not _looks_like_combat(text):
        return False
    if not _text_quality_ok(text):
        return False
    if re.search(r"[\x00-\x08\x0b-\x1f]", text):
        return False
    if len(text) > 240:
        return False
    if '"' in text and (":" in text or "seg-" in text):
        return False
    if re.match(r'^"?ts"?\s*:', text, re.I):
        return False
    return True


def extract_combat_candidates(text: str, *, source_id: str = "") -> list[dict[str, Any]]:
    if not text or len(text) < 3 or not _text_quality_ok(text):
        return []
    ocr_doc = _load(OCR_DOCTRINE, {})
    min_len = int((ocr_doc.get("train") or {}).get("min_candidate_len") or 8)
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
        out.append({"text": cand, "kind": kind, "source_id": source_id})

    for m in _COMBAT_LINE_RE.finditer(text):
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 80)
        add(text[start:end], "regex_context")

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < min_len:
            continue
        if _COMBAT_LINE_RE.search(line):
            add(line, "combat_line")

    return out[:200]


def _ocr_tesseract(path: Path) -> str:
    core_py = INSTALL / "lib" / "final-eye-ocr-core.py"
    if not core_py.is_file():
        return ""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("final_eye_ocr_combat", core_py)
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
    if spec.get("combat_filter"):
        sid = str(row.get("id", "")).lower()
        label = str(row.get("label", "")).lower()
        family = str(row.get("family", "")).lower()
        if not any(
            k in sid or k in label or k in family
            for k in ("kung", "mma", "striking", "grappling", "defense", "wing", "shaolin", "wrestling", "boxing")
        ):
            return []
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


def _ingest_text_blob(text: str, *, source_id: str, path: str, corpus: dict[str, Any]) -> int:
    if not _text_quality_ok(text):
        return 0
    max_c = int((_load(OCR_DOCTRINE, {}).get("ingest") or {}).get("max_candidates_per_ingest") or 8000)
    if len(corpus.get("candidates") or []) >= max_c:
        return 0
    added = 0
    known = corpus.setdefault("seen_hashes", [])
    seen_set = set(known[-50000:])
    for cand in extract_combat_candidates(text, source_id=source_id):
        h = hashlib.sha256(f"{source_id}:{cand['text']}".encode()).hexdigest()[:24]
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
    """Feed combat think tank from OCR vision and corpus sources."""
    ocr_doc = _load(OCR_DOCTRINE, {})
    ingest_cfg = ocr_doc.get("ingest") or {}
    max_files = limit_per_source or int(ingest_cfg.get("max_files_per_source") or 500)
    max_bytes = int(ingest_cfg.get("max_bytes_per_file") or 250000)

    corpus = _load(OCR_CORPUS, {
        "schema": "hostess7-combat-ocr-corpus/v1",
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
                            for chunk in _text_chunks_from_row(row, spec):
                                bytes_read += len(chunk)
                                added += _ingest_text_blob(chunk, source_id=sid, path=str(fp), corpus=corpus)
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


def _verify_combat_candidate(text: str) -> bool:
    if not _plausible_combat_candidate(text):
        return False
    scored = _score_combat_domains(text, [dict(d) for d in COMBAT_DOMAINS])
    if scored and scored[0][0] >= 4:
        return True
    war = _warfare_module()
    if war:
        try:
            war.ensure_corpus()
            hits = war.search_warfare(text, limit=1)
            if hits:
                return True
        except Exception:
            pass
    return len(_tokens(text)) >= 3 and _COMBAT_LINE_RE.search(text) is not None


def train_ocr_vision(*, verify: bool = True, limit: int = 500) -> dict[str, Any]:
    ocr_doc = _load(OCR_DOCTRINE, {})
    train_cfg = ocr_doc.get("train") or {}
    corpus = _load(OCR_CORPUS, {"candidates": []})
    candidates = list(corpus.get("candidates") or [])
    if not candidates:
        ingest_ocr_vision()
        corpus = _load(OCR_CORPUS, {"candidates": []})
        candidates = list(corpus.get("candidates") or [])

    verified = 0
    attempts = 0
    samples: list[dict[str, Any]] = []
    for cand in candidates:
        if attempts >= limit:
            break
        text = str(cand.get("text") or "")
        if not text:
            continue
        attempts += 1
        ok = _verify_combat_candidate(text) if verify else False
        row = {**cand, "verified": ok}
        if ok:
            verified += 1
        samples.append(row)

    plausible_n = sum(1 for c in candidates if _plausible_combat_candidate(str(c.get("text") or "")))
    total = len(candidates)
    rate = verified / max(plausible_n, 1)
    fluent_floor = int(train_cfg.get("fluent_samples_floor") or 40)
    master_floor = int(train_cfg.get("master_samples_floor") or 100)
    train_doc = {
        "schema": "hostess7-combat-ocr-train/v1",
        "updated": _now(),
        "candidate_count": total,
        "trained_count": attempts,
        "verified_count": verified,
        "verified_rate": round(rate, 4),
        "fluent": verified >= fluent_floor,
        "mastered": verified >= master_floor,
        "samples": samples[-24:],
        "sources": corpus.get("sources") or {},
    }
    _save(STATE / "hostess7-combat-ocr-train.json", train_doc)
    _append_ledger({"ts": _now(), "event": "ocr_train", "verified": verified, "total": total, "rate": rate})
    return {"ok": True, **train_doc}


def ocr_vision_status() -> dict[str, Any]:
    corpus = _load(OCR_CORPUS, {})
    train = _load(STATE / "hostess7-combat-ocr-train.json", {})
    return {
        "schema": "hostess7-combat-ocr-status/v1",
        "updated": _now(),
        "corpus": {
            "candidate_count": len(corpus.get("candidates") or []),
            "ingest_total_added": corpus.get("ingest_total_added"),
            "sources": corpus.get("sources") or {},
        },
        "train": train,
    }


def _pattern_mastery() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    bat = _run_battery()
    motion = _motion_skills_loaded()
    out: list[dict[str, Any]] = []
    for pat in doctrine.get("patterns") or []:
        pid = str(pat.get("id") or "")
        mastered = False
        if pid == "domain_corpus":
            mastered = len(COMBAT_DOMAINS) >= 10
        elif pid == "warfare_bridge":
            mastered = bool(bat.get("warfare_corpus_available"))
        elif pid == "motion_bridge":
            mastered = len(motion) > 0 or _load(MOTION_PANEL, {}).get("loaded_count", 0) > 0
        elif pid == "battery_verify":
            mastered = bool(bat.get("passed"))
        elif pid == "disclaimer_seal":
            mastered = DISCLAIMER in format_combat_reply("boxing footwork")
        elif pid == "natural_language":
            mastered = _looks_like_combat("what is wing chun centerline theory")
        elif pid == "structured_explain":
            mastered = bool(_load(EXPLAIN, {}).get("topics"))
        elif pid == "ocr_vision_train":
            tr = _load(STATE / "hostess7-combat-ocr-train.json", {})
            mastered = bool(tr.get("mastered") or tr.get("fluent"))
        out.append({"id": pid, "label": pat.get("label"), "mastered": mastered})
    return out


def combat_score(*, battery: dict[str, Any] | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    bat = battery or _run_battery()
    patterns = _pattern_mastery()
    mastered = sum(1 for p in patterns if p.get("mastered"))
    rate = float(bat.get("pass_rate") or 0) / 100.0
    by_cat = bat.get("by_category") or {}
    cats_mastered = sum(1 for c in by_cat.values() if c.get("total") and c["passed"] >= c["total"])
    ocr_train = _load(STATE / "hostess7-combat-ocr-train.json", {})
    ocr_corpus = _load(OCR_CORPUS, {})
    ocr_verified = int(ocr_train.get("verified_count") or 0)
    ocr_candidates = int(ocr_corpus.get("candidate_count") or len(ocr_corpus.get("candidates") or []))
    ocr_rate = float(ocr_train.get("verified_rate") or 0)
    motion_panel = _load(MOTION_PANEL, {})
    skills_loaded = _motion_skills_loaded()
    skills_count = len(skills_loaded) or int(motion_panel.get("loaded_count") or 0)

    score = 0.64
    score += 0.18 * rate
    score += 0.06 * min(1.0, mastered / max(len(patterns), 1))
    score += 0.04 * min(1.0, cats_mastered / 8.0)
    score += 0.04 * min(1.0, ocr_verified / 300.0)
    score += 0.02 * min(1.0, ocr_rate / 0.4)
    score += 0.02 if bat.get("warfare_corpus_available") else 0.0
    score += 0.02 * min(1.0, skills_count / 6.0)
    score = round(min(0.99, score), 4)

    fluent_floor = float(doctrine.get("fluent_floor_score") or 0.86)
    master_target = float(doctrine.get("master_combat_score") or 0.95)
    tier = "assistant_guess"
    if score >= master_target and bat.get("passed") and cats_mastered >= 6:
        tier = "combat_master"
    elif score >= fluent_floor and bat.get("passed"):
        tier = "combat_fluent"
    elif rate >= 0.5:
        tier = "combat_basic"

    return {
        "score": score,
        "combat_score": score,
        "tier": tier,
        "fluent": tier in ("combat_fluent", "combat_master"),
        "mastered": tier == "combat_master",
        "better_than_assistant": score >= fluent_floor and bat.get("passed"),
        "battery": bat,
        "patterns_mastered": mastered,
        "patterns_total": len(patterns),
        "categories_mastered": cats_mastered,
        "warfare_corpus_available": bat.get("warfare_corpus_available"),
        "domain_count": len(COMBAT_DOMAINS),
        "motion_bridge": {
            "skills_loaded": skills_loaded,
            "skills_loaded_count": skills_count,
            "active_skill": motion_panel.get("active_skill"),
            "families_loaded": motion_panel.get("families_loaded") or {},
        },
        "ocr_vision": {
            "candidate_count": ocr_candidates,
            "verified_count": ocr_verified,
            "verified_rate": ocr_rate,
            "fluent": bool(ocr_train.get("fluent")),
            "mastered": bool(ocr_train.get("mastered")),
        },
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
            return mod.merge_explain_doc("combat", base)
    except Exception:
        pass
    return base


def _match_explain_topic(query: str) -> dict[str, Any] | None:
    q = (query or "").lower()
    best: dict[str, Any] | None = None
    best_score = 0
    for topic in (_explain_doc().get("topics") or []):
        sc = _topic_match_score(topic, q)
        if sc > best_score:
            best_score = sc
            best = topic
    return best if best_score > 0 else None


def _format_topic_prose(topic: dict[str, Any], *, intro: str = "") -> str:
    parts: list[str] = []
    if intro.strip():
        parts.append(intro.strip())
    parts.append(DISCLAIMER)
    for key, label in _SECTION_LABELS:
        val = str(topic.get(key) or "").strip()
        if val:
            parts.append(f"{label}: {val}")
    return "\n\n".join(parts)


def explain_combat_structured(query: str = "") -> dict[str, Any]:
    q = (query or "").strip()
    low = q.lower()
    doc = _explain_doc()
    intro = str(doc.get("introduction") or "").strip()
    fmt = doc.get("format") or [s[0] for s in _SECTION_LABELS]
    metrics = combat_score()

    topic = _match_explain_topic(q)
    if not topic and any(k in low for k in ("combat", "martial arts", "self defense", "fighting", "defense doctrine")):
        doctrine = _load(DOCTRINE, {})
        sections = {
            "what": "Combat mastery means I synthesize martial arts education from structured domains through lawful self-defense, tactical awareness, and warfare corpus bridge.",
            "why": str(doctrine.get("fluency_claim") or ""),
            "how": (
                f"Battery pass {metrics.get('battery', {}).get('pass_rate')}% · tier {metrics.get('tier')} · "
                f"score {round(float(metrics.get('score') or 0) * 100)}% · domains {metrics.get('domain_count')} · "
                f"motion skills {metrics.get('motion_bridge', {}).get('skills_loaded_count', 0)}"
            ),
            "pitfalls": "Instructing harm; omitting lawful-self-defense disclaimer; treating sport rules as street law.",
            "where": "lib/hostess7-combat.py, field_warfare_corpus.py, humanoid-motion-panel.json, /api/hostess7/combat",
            "example": "Ask: lawful self-defense de-escalation — self_defense domain with disclaimer.",
        }
        topic = {"id": "combat_fluency_live", **sections}

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
            "combat_score": metrics.get("score"),
            "tier": metrics.get("tier"),
            "disclaimer": DISCLAIMER,
        }

    fallback = intro + " " + DISCLAIMER + " Ask me about striking, grappling, self-defense, tactical awareness, or conditioning."
    return {"ok": True, "query": q, "reply": fallback.strip(), "format": fmt, "disclaimer": DISCLAIMER}


def explain_combat(query: str = "") -> str:
    return str(explain_combat_structured(query).get("reply") or "")


def build_panel(*, write: bool = True) -> dict[str, Any]:
    metrics = combat_score()
    doc = {
        "schema": "hostess7-combat/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "combat_score": metrics.get("score"),
        "tier": metrics.get("tier"),
        "fluent": metrics.get("fluent"),
        "mastered": metrics.get("mastered"),
        "better_than_assistant": metrics.get("better_than_assistant"),
        "battery_pass_rate": metrics.get("battery", {}).get("pass_rate"),
        "categories_mastered": metrics.get("categories_mastered"),
        "domain_count": metrics.get("domain_count"),
        "warfare_corpus_available": metrics.get("warfare_corpus_available"),
        "patterns_mastered": metrics.get("patterns_mastered"),
        "patterns_total": metrics.get("patterns_total"),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "disclaimer": DISCLAIMER,
        "motion_bridge": metrics.get("motion_bridge"),
        "ocr_vision": metrics.get("ocr_vision"),
    }
    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "hostess7-combat-runtime/v1",
            "updated": doc["updated"],
            "tier": doc["tier"],
            "combat_score": doc["combat_score"],
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
        print(json.dumps(combat_score(), ensure_ascii=False))
        return 0
    if cmd in ("search", "answer", "query"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "boxing footwork combinations"
        print(json.dumps({"ok": True, "query": q, "hits": search_combat(q), "reply": format_combat_reply(q)}, ensure_ascii=False))
        return 0
    if cmd in ("teach", "explain"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "combat fluency"
        doc = explain_combat_structured(q)
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
        "error": "usage: hostess7-combat.py [json|search|battery|teach|ocr-ingest|ocr-train|ocr-status]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())