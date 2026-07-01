#!/usr/bin/env pythong
"""Hostess 7 engineering chamber — full understanding of applied engineering and NEXUS field systems."""
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
DOCTRINE = INSTALL / "data" / "hostess7-engineering-doctrine.json"
BATTERY = INSTALL / "data" / "hostess7-engineering-battery.json"
EXPLAIN = INSTALL / "data" / "hostess7-engineering-explain.json"
OCR_DOCTRINE = INSTALL / "data" / "hostess7-engineering-ocr-doctrine.json"
PANEL = STATE / "hostess7-engineering-panel.json"
RUNTIME = STATE / "hostess7-engineering-runtime.json"
LEDGER = STATE / "hostess7-engineering-ledger.jsonl"
OCR_CORPUS = STATE / "hostess7-engineering-ocr-corpus.json"
OCR_LEDGER = STATE / "hostess7-engineering-ocr-ledger.jsonl"
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

ENABLED = os.environ.get("NEXUS_HOSTESS7_ENGINEERING", "1") == "1"

DISCLAIMER = (
    "Educational engineering only — not licensed professional engineer (PE) sign-off, stamped drawings, "
    "or jurisdiction-specific code compliance. Consult a qualified engineer for design approval and construction."
)

_SECTION_LABELS = (
    ("what", "What"),
    ("why", "Why"),
    ("how", "How"),
    ("pitfalls", "Pitfalls"),
    ("where", "Where"),
    ("example", "Example"),
)

_ENGINEERING_KEYS = (
    "engineering", "mechanical", "electrical", "civil", "structural", "materials", "thermodynamics",
    "hvac", "fluid", "robotics", "control", "manufacturing", "cnc", "machining", "software", "embedded",
    "firmware", "circuit", "voltage", "current", "resistance", "beam", "concrete", "foundation", "steel",
    "aluminum", "fatigue", "stress", "strain", "torque", "gear", "bearing", "motor", "transformer",
    "pid", "feedback", "actuator", "sensor", "plc", "scada", "pipeline", "commissioning", "field stack",
    "nexus", "hostess7", "tolerance", "machining", "welding", "composite", "polymer", "heat pump", "duct",
    "ventilation", "load", "moment", "shear", "truss", "bridge", "soil", "bearing capacity", "rtos",
    "engineering mastery", "engineering fluency", "field engineering",
)

_ENG_LINE_RE = re.compile(
    r"(?:"
    r"engineer|mechanical|electrical|civil|structural|material|thermodynamic|hvac|fluid|robot|control|"
    r"manufactur|cnc|machin|embedded|firmware|circuit|voltage|current|resistance|ohm|beam|concrete|"
    r"foundation|steel|aluminum|fatigue|stress|strain|torque|gear|bearing|motor|transformer|pid|feedback|"
    r"actuator|sensor|plc|scada|pipeline|commission|field\s+stack|nexus|hostess7|tolerance|welding|"
    r"composite|polymer|heat\s+pump|duct|ventilation|load|moment|shear|truss|soil|rtos|navier|bernoulli|"
    r"newton|kinematic|corrosion|oxidation"
    r")",
    re.I,
)

ENGINEERING_DOMAINS: tuple[dict[str, Any], ...] = (
    {
        "id": "foundations",
        "title": "Engineering foundations",
        "tags": ("engineering", "design", "analysis", "synthesis", "safety", "ethics", "units", "standards"),
        "body": (
            "Engineering applies science and math to design systems under constraints: safety, cost, schedule, "
            "environment, and maintainability. Design process: requirements → concept → analysis → prototype → "
            "verification/validation → deployment → lifecycle maintenance. SI units and dimensional consistency; "
            "factor of safety and risk assessment. Professional ethics: competence, disclosure, public welfare — "
            "educational synthesis is not PE sign-off or stamped drawings."
        ),
    },
    {
        "id": "mechanical",
        "title": "Mechanical engineering",
        "tags": ("mechanical", "gear", "torque", "stress", "strain", "beam", "bearing", "machine", "fatigue", "shaft"),
        "body": (
            "Mechanical engineering covers statics, dynamics, machine elements, and stress analysis. "
            "Hooke's law σ = Eε; bending stress σ = My/I; torsion τ = Tr/J. "
            "Gears: speed ratio, mechanical advantage, efficiency, backlash. "
            "Fatigue: S-N curves, stress concentration, endurance limit. "
            "Power transmission: belts, chains, couplings, lubrication. "
            "Machine design balances strength, stiffness, wear, and manufacturability."
        ),
    },
    {
        "id": "electrical",
        "title": "Electrical engineering",
        "tags": ("electrical", "circuit", "voltage", "current", "resistance", "ohm", "motor", "transformer", "power", "phase"),
        "body": (
            "Electrical engineering spans circuits, power, and electromagnetics. Ohm's law V = IR; Kirchhoff's laws. "
            "AC power: real/reactive/apparent power, power factor correction. "
            "Three-phase systems: line vs phase voltage, balanced loads, motor starting. "
            "Transformers, switchgear, protection (fuses, breakers, relays). "
            "Signal integrity and grounding for embedded and industrial controls."
        ),
    },
    {
        "id": "civil_structural",
        "title": "Civil & structural engineering",
        "tags": ("civil", "structural", "concrete", "beam", "foundation", "soil", "truss", "bridge", "load", "moment", "shear"),
        "body": (
            "Civil and structural engineering designs built infrastructure: buildings, bridges, foundations, earthworks. "
            "Loads: dead, live, wind, seismic, soil pressure. "
            "Concrete beam design: flexure, shear, deflection limits, reinforcement detailing — code-specific calcs "
            "require licensed review. Foundation bearing capacity and settlement depend on soil mechanics and "
            "water table. Truss analysis: method of joints/sections."
        ),
    },
    {
        "id": "materials",
        "title": "Materials science & selection",
        "tags": ("materials", "steel", "aluminum", "composite", "polymer", "fatigue", "fracture", "corrosion", "alloy"),
        "body": (
            "Materials science links composition, microstructure, and properties. "
            "Metals: yield strength, ductility, hardness, fatigue life. "
            "Aluminum alloys: lightweight structures; steel: high strength, weldability tradeoffs. "
            "Composites: anisotropic stiffness, layup design, moisture and UV aging. "
            "Failure modes: fracture toughness, creep, corrosion — select materials for environment and load cycle."
        ),
    },
    {
        "id": "thermodynamics_systems",
        "title": "Thermodynamics & energy systems",
        "tags": ("thermodynamics", "heat", "entropy", "heat pump", "cop", "energy", "exchanger", "building", "cycle"),
        "body": (
            "Thermodynamics for engineered systems: first law energy balance, second law entropy generation. "
            "Heat engines and refrigeration cycles; COP for heat pumps in building HVAC. "
            "Heat exchangers: LMTD, effectiveness-NTU method. "
            "Building energy: envelope losses, system efficiency, control strategies. "
            "Educational synthesis — jurisdiction energy codes require qualified review."
        ),
    },
    {
        "id": "fluids_hvac",
        "title": "Fluids & HVAC",
        "tags": ("fluid", "hvac", "duct", "airflow", "ventilation", "pressure", "pump", "fan", "pipe", "flow"),
        "body": (
            "Fluid engineering for HVAC and piping: continuity, Bernoulli, friction losses (Darcy-Weisbach). "
            "Duct sizing for target airflow and static pressure budget; ventilation rates for occupancy and comfort. "
            "Pumps and fans on system curves; cavitation and NPSH. "
            "HVAC psychrometrics: sensible/latent loads, dehumidification, VAV vs constant volume. "
            "Bridge to physics fluid continuum for Navier-Stokes educational depth."
        ),
    },
    {
        "id": "robotics_control",
        "title": "Robotics & control systems",
        "tags": ("robotics", "control", "pid", "feedback", "actuator", "sensor", "kinematics", "servo", "loop"),
        "body": (
            "Robotics and control: sensing, actuation, feedback loops, and motion planning. "
            "PID control: proportional, integral, derivative tuning; stability margins. "
            "Forward/inverse kinematics for manipulators; Jacobian for velocity mapping. "
            "State estimation, Kalman filters, sensor fusion. "
            "Safety: e-stops, torque limits, collaborative robot standards — educational, not certified integration."
        ),
    },
    {
        "id": "manufacturing",
        "title": "Manufacturing engineering",
        "tags": ("manufacturing", "cnc", "machining", "tolerance", "fixture", "welding", "assembly", "quality", "gd&t"),
        "body": (
            "Manufacturing translates design into physical parts. CNC machining: toolpaths, feeds/speeds, surface finish. "
            "Tolerance stack-up analysis across assemblies; GD&T for datums and feature control. "
            "Processes: casting, forging, molding, additive, welding — each with distortion and defect modes. "
            "Quality systems: SPC, Cpk, inspection metrology. "
            "Design for manufacturability reduces cost and field failure."
        ),
    },
    {
        "id": "software_systems",
        "title": "Software & embedded systems",
        "tags": ("software", "embedded", "firmware", "rtos", "scheduling", "driver", "bus", "api", "systems"),
        "body": (
            "Software systems engineering: requirements, architecture, implementation, test, deployment. "
            "Embedded firmware on microcontrollers: interrupts, timers, drivers, watchdogs. "
            "RTOS scheduling: preemptive tasks, priorities, mutexes, deadlock avoidance. "
            "Interfaces: CAN, SPI, I2C, Ethernet; protocol stacks and timing budgets. "
            "Reliability: logging, OTA updates, secure boot — field stack parallels in NEXUS Hostess7."
        ),
    },
    {
        "id": "field_engineering",
        "title": "NEXUS field engineering",
        "tags": ("field engineering", "nexus", "hostess7", "field stack", "pipeline", "commissioning", "deploy", "canvas", "dispatch"),
        "body": (
            "NEXUS field engineering covers Hostess7 field stack deployment, canvas dispatch integration, "
            "pipeline commissioning, and operator-facing systems on SG/AMOURANTHRTX. "
            "Paths: Hostess7/scripts, NewLatest lib modules, cache/fieldstorage brain corpora, ZOCR/Final_Eye vision feeds. "
            "Commissioning checklist: corpus refresh, battery verify, panel health, OCR ingest/train. "
            "Field canvas physics couples fabric dispatch, entropy fabric, and WM overlay — educational operator literacy."
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


def _physics_module() -> Any | None:
    script = HOSTESS7_ROOT / "scripts" / "field_physics_corpus.py"
    if not script.is_file():
        return None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_physics_corpus", script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(script.parent))
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _chemistry_module() -> Any | None:
    script = HOSTESS7_ROOT / "scripts" / "field_chemistry_corpus.py"
    if not script.is_file():
        return None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_chemistry_corpus", script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(script.parent))
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _score_engineering_domains(query: str, domains: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for d in domains:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:1500]}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("engineering", "design process", "foundations", "requirements")):
            if d.get("id") == "foundations":
                score += 15
        if any(k in q for k in ("mechanical", "gear", "torque", "stress", "strain", "beam bending")):
            if d.get("id") == "mechanical":
                score += 15
        if any(k in q for k in ("electrical", "ohm", "voltage", "current", "circuit", "three phase", "motor")):
            if d.get("id") == "electrical":
                score += 15
        if any(k in q for k in ("civil", "structural", "concrete", "foundation", "soil", "bearing")):
            if d.get("id") == "civil_structural":
                score += 15
        if any(k in q for k in ("material", "fatigue", "fracture", "steel", "aluminum", "composite")):
            if d.get("id") == "materials":
                score += 12
        if any(k in q for k in ("thermodynamic", "heat pump", "cop", "heat exchanger", "building energy")):
            if d.get("id") == "thermodynamics_systems":
                score += 15
        if any(k in q for k in ("hvac", "duct", "airflow", "ventilation")):
            if d.get("id") == "fluids_hvac":
                score += 15
        if any(k in q for k in ("robot", "pid", "feedback", "control loop", "actuator")):
            if d.get("id") == "robotics_control":
                score += 15
        if any(k in q for k in ("manufacturing", "cnc", "machining", "tolerance")):
            if d.get("id") == "manufacturing":
                score += 15
        if any(k in q for k in ("embedded", "firmware", "rtos", "software systems", "scheduling")):
            if d.get("id") == "software_systems":
                score += 15
        if any(k in q for k in ("field stack", "nexus", "hostess7", "commissioning", "field engineering", "canvas dispatch")):
            if d.get("id") == "field_engineering":
                score += 18
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return scored


def search_engineering(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Search engineering domains and physics/chemistry corpus bridges."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    q = query.lower()
    physics_q = any(
        k in q
        for k in (
            "newton", "kinematics", "dynamics", "lagrangian", "hamiltonian", "navier", "bernoulli",
            "maxwell", "schrodinger", "relativity", "lorentz", "projectile", "centripetal", "fluid continuum",
        )
    )
    chemistry_q = any(
        k in q
        for k in (
            "corrosion", "oxidation", "electrochemistry", "polymer", "stoichiometry", "acid base",
            "redox", "molecule", "bond chemistry", "neurotransmitter",
        )
    )

    phys_mod = _physics_module()
    if phys_mod and physics_q:
        try:
            phys_mod.ensure_corpus()
            for row in phys_mod.search_physics(query, limit=max(2, limit // 2 + 1)):
                pid = str(row.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)
                out.append({**row, "source": row.get("source") or "physics_corpus"})
        except Exception:
            pass

    chem_mod = _chemistry_module()
    if chem_mod and chemistry_q:
        try:
            chem_mod.ensure_corpus()
            chem_hits = chem_mod.search_chemistry(query, limit=max(2, limit // 2 + 1))
            if not chem_hits:
                chem_hits = chem_mod.search_chemistry("general chemistry redox bond reaction", limit=1)
            for row in chem_hits:
                pid = str(row.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)
                out.append({**row, "source": row.get("source") or "chemistry_corpus"})
        except Exception:
            pass

    domain_scored = _score_engineering_domains(query, [dict(d) for d in ENGINEERING_DOMAINS])
    for _, d in domain_scored:
        did = str(d.get("id", ""))
        if did in seen:
            continue
        seen.add(did)
        row = dict(d)
        row["source"] = "engineering_domain"
        out.append(row)
        if len(out) >= limit:
            break

    if not out and phys_mod:
        try:
            for row in phys_mod.search_physics(query, limit=limit):
                pid = str(row.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)
                out.append({**row, "source": "physics_corpus"})
        except Exception:
            pass

    if not out and chem_mod:
        try:
            for row in chem_mod.search_chemistry(query, limit=limit):
                pid = str(row.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)
                out.append({**row, "source": "chemistry_corpus"})
        except Exception:
            pass

    return out[:limit]


def synthesize_engineering_paragraphs(query: str) -> list[str]:
    hits = search_engineering(query, limit=4)
    if not hits:
        hits = search_engineering("engineering mechanical electrical field stack NEXUS", limit=3)
    paras: list[str] = [DISCLAIMER]
    for h in hits:
        title = h.get("title", "Engineering")
        body = str(h.get("body", "")).strip()
        if len(body) > 1100:
            body = body[:1100] + "… [truncated]"
        src = h.get("source", "")
        if src in ("physics_corpus", "chemistry_corpus"):
            paras.append(f"{title} ({src.replace('_', ' ')}): {body}")
        else:
            paras.append(f"{title}: {body}")
    return paras


def format_engineering_reply(query: str) -> str:
    paras = synthesize_engineering_paragraphs(query)
    if len(paras) <= 1:
        return (
            "I could not match that engineering query cleanly — try mechanical, electrical, civil, "
            f"robotics, or field engineering topics. {DISCLAIMER}"
        )
    return "\n\n".join(paras)


def _looks_like_engineering(text: str) -> bool:
    low = (text or "").lower()
    if any(k in low for k in _ENGINEERING_KEYS):
        return True
    if _ENG_LINE_RE.search(low):
        return True
    return False


def extract_engineering_query(text: str) -> str:
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
    hits = search_engineering(query, limit=6)
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
        "physics_corpus_available": _physics_module() is not None,
        "chemistry_corpus_available": _chemistry_module() is not None,
    }


def _text_quality_ok(text: str) -> bool:
    if not text:
        return False
    sample = text[:4000]
    if "\x00" in sample or "H7E" in sample[:8]:
        return False
    printable = sum(1 for c in sample if c.isprintable() or c in "\n\t")
    return printable / max(len(sample), 1) >= 0.85


def _plausible_engineering_candidate(text: str) -> bool:
    if not _looks_like_engineering(text):
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


def extract_engineering_candidates(text: str, *, source_id: str = "") -> list[dict[str, Any]]:
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

    for m in _ENG_LINE_RE.finditer(text):
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 80)
        add(text[start:end], "regex_context")

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < min_len:
            continue
        if _ENG_LINE_RE.search(line):
            add(line, "engineering_line")

    return out[:200]


def _ocr_tesseract(path: Path) -> str:
    core_py = INSTALL / "lib" / "final-eye-ocr-core.py"
    if not core_py.is_file():
        return ""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("final_eye_ocr_eng", core_py)
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
    if spec.get("engineering_filter"):
        bid = str(row.get("id", "")).lower()
        title = str(row.get("title", "")).lower()
        path_s = str(row.get("path", "")).lower()
        if not any(
            k in bid or k in title or k in path_s
            for k in (
                "physics", "chemistry", "engineering", "mechanical", "electrical", "civil",
                "dewey/620", "dewey/530", "dewey/540", "dewey/500",
            )
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
    for cand in extract_engineering_candidates(text, source_id=source_id):
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
    """Feed engineering think tank from OCR vision and corpus sources."""
    ocr_doc = _load(OCR_DOCTRINE, {})
    ingest_cfg = ocr_doc.get("ingest") or {}
    max_files = limit_per_source or int(ingest_cfg.get("max_files_per_source") or 500)
    max_bytes = int(ingest_cfg.get("max_bytes_per_file") or 250000)

    corpus = _load(OCR_CORPUS, {
        "schema": "hostess7-engineering-ocr-corpus/v1",
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


def _verify_engineering_candidate(text: str) -> bool:
    if not _plausible_engineering_candidate(text):
        return False
    scored = _score_engineering_domains(text, [dict(d) for d in ENGINEERING_DOMAINS])
    if scored and scored[0][0] >= 4:
        return True
    phys = _physics_module()
    if phys:
        try:
            phys.ensure_corpus()
            hits = phys.search_physics(text, limit=1)
            if hits:
                return True
        except Exception:
            pass
    chem = _chemistry_module()
    if chem:
        try:
            chem.ensure_corpus()
            hits = chem.search_chemistry(text, limit=1)
            if hits:
                return True
        except Exception:
            pass
    return len(_tokens(text)) >= 3 and _ENG_LINE_RE.search(text) is not None


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
        ok = _verify_engineering_candidate(text) if verify else False
        row = {**cand, "verified": ok}
        if ok:
            verified += 1
        samples.append(row)

    plausible_n = sum(1 for c in candidates if _plausible_engineering_candidate(str(c.get("text") or "")))
    total = len(candidates)
    rate = verified / max(plausible_n, 1)
    fluent_floor = int(train_cfg.get("fluent_samples_floor") or 40)
    master_floor = int(train_cfg.get("master_samples_floor") or 100)
    train_doc = {
        "schema": "hostess7-engineering-ocr-train/v1",
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
    _save(STATE / "hostess7-engineering-ocr-train.json", train_doc)
    _append_ledger({"ts": _now(), "event": "ocr_train", "verified": verified, "total": total, "rate": rate})
    return {"ok": True, **train_doc}


def ocr_vision_status() -> dict[str, Any]:
    corpus = _load(OCR_CORPUS, {})
    train = _load(STATE / "hostess7-engineering-ocr-train.json", {})
    return {
        "schema": "hostess7-engineering-ocr-status/v1",
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
    out: list[dict[str, Any]] = []
    for pat in doctrine.get("patterns") or []:
        pid = str(pat.get("id") or "")
        mastered = False
        if pid == "domain_corpus":
            mastered = len(ENGINEERING_DOMAINS) >= 10
        elif pid == "physics_bridge":
            mastered = bool(bat.get("physics_corpus_available"))
        elif pid == "chemistry_bridge":
            mastered = bool(bat.get("chemistry_corpus_available"))
        elif pid == "battery_verify":
            mastered = bool(bat.get("passed"))
        elif pid == "disclaimer_seal":
            mastered = DISCLAIMER in format_engineering_reply("mechanical gear design")
        elif pid == "textbook_manifest":
            mf = INSTALL / "data" / "field-brain" / "manifest.json"
            mastered = mf.is_file()
        elif pid == "natural_language":
            mastered = _looks_like_engineering("what is PID control in robotics")
        elif pid == "structured_explain":
            mastered = bool(_load(EXPLAIN, {}).get("topics"))
        elif pid == "ocr_vision_train":
            tr = _load(STATE / "hostess7-engineering-ocr-train.json", {})
            mastered = bool(tr.get("mastered") or tr.get("fluent"))
        out.append({"id": pid, "label": pat.get("label"), "mastered": mastered})
    return out


def engineering_score(*, battery: dict[str, Any] | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    bat = battery or _run_battery()
    patterns = _pattern_mastery()
    mastered = sum(1 for p in patterns if p.get("mastered"))
    rate = float(bat.get("pass_rate") or 0) / 100.0
    by_cat = bat.get("by_category") or {}
    cats_mastered = sum(1 for c in by_cat.values() if c.get("total") and c["passed"] >= c["total"])
    ocr_train = _load(STATE / "hostess7-engineering-ocr-train.json", {})
    ocr_corpus = _load(OCR_CORPUS, {})
    ocr_verified = int(ocr_train.get("verified_count") or 0)
    ocr_candidates = int(ocr_corpus.get("candidate_count") or len(ocr_corpus.get("candidates") or []))
    ocr_rate = float(ocr_train.get("verified_rate") or 0)

    score = 0.64
    score += 0.18 * rate
    score += 0.06 * min(1.0, mastered / max(len(patterns), 1))
    score += 0.04 * min(1.0, cats_mastered / 8.0)
    score += 0.04 * min(1.0, ocr_verified / 300.0)
    score += 0.02 * min(1.0, ocr_rate / 0.4)
    score += 0.01 if bat.get("physics_corpus_available") else 0.0
    score += 0.01 if bat.get("chemistry_corpus_available") else 0.0
    score = round(min(0.99, score), 4)

    fluent_floor = float(doctrine.get("fluent_floor_score") or 0.86)
    master_target = float(doctrine.get("master_engineering_score") or 0.95)
    tier = "assistant_guess"
    if score >= master_target and bat.get("passed") and cats_mastered >= 6:
        tier = "engineering_master"
    elif score >= fluent_floor and bat.get("passed"):
        tier = "engineering_fluent"
    elif rate >= 0.5:
        tier = "engineering_basic"

    return {
        "score": score,
        "engineering_score": score,
        "tier": tier,
        "fluent": tier in ("engineering_fluent", "engineering_master"),
        "mastered": tier == "engineering_master",
        "better_than_assistant": score >= fluent_floor and bat.get("passed"),
        "battery": bat,
        "patterns_mastered": mastered,
        "patterns_total": len(patterns),
        "categories_mastered": cats_mastered,
        "physics_corpus_available": bat.get("physics_corpus_available"),
        "chemistry_corpus_available": bat.get("chemistry_corpus_available"),
        "domain_count": len(ENGINEERING_DOMAINS),
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
            return mod.merge_explain_doc("engineering", base)
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


def explain_engineering_structured(query: str = "") -> dict[str, Any]:
    q = (query or "").strip()
    low = q.lower()
    doc = _load(EXPLAIN, {})
    intro = str(doc.get("introduction") or "").strip()
    fmt = doc.get("format") or [s[0] for s in _SECTION_LABELS]
    metrics = engineering_score()

    topic = _match_explain_topic(q)
    if not topic and any(k in low for k in ("engineering", "engineering mastery", "field engineering", "mechanical", "electrical")):
        doctrine = _load(DOCTRINE, {})
        sections = {
            "what": "Engineering mastery means I synthesize applied engineering from structured domains through mechanical, electrical, civil, robotics, and NEXUS field stack with physics/chemistry corpus bridges.",
            "why": str(doctrine.get("fluency_claim") or ""),
            "how": (
                f"Battery pass {metrics.get('battery', {}).get('pass_rate')}% · tier {metrics.get('tier')} · "
                f"score {round(float(metrics.get('score') or 0) * 100)}% · domains {metrics.get('domain_count')}"
            ),
            "pitfalls": "PE sign-off claims; omitting educational disclaimer; training on binary .h7 as text.",
            "where": "lib/hostess7-engineering.py, field_physics_corpus.py, field_chemistry_corpus.py, /api/hostess7/engineering",
            "example": "Ask: PID feedback control loop — robotics_control domain with disclaimer.",
        }
        topic = {"id": "engineering_fluency_live", **sections}

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
            "engineering_score": metrics.get("score"),
            "tier": metrics.get("tier"),
            "disclaimer": DISCLAIMER,
        }

    fallback = intro + " " + DISCLAIMER + " Ask me about mechanical, electrical, civil, robotics, manufacturing, or NEXUS field engineering."
    return {"ok": True, "query": q, "reply": fallback.strip(), "format": fmt, "disclaimer": DISCLAIMER}


def explain_engineering(query: str = "") -> str:
    return str(explain_engineering_structured(query).get("reply") or "")


def build_panel(*, write: bool = True) -> dict[str, Any]:
    metrics = engineering_score()
    doc = {
        "schema": "hostess7-engineering/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "engineering_score": metrics.get("score"),
        "tier": metrics.get("tier"),
        "fluent": metrics.get("fluent"),
        "mastered": metrics.get("mastered"),
        "better_than_assistant": metrics.get("better_than_assistant"),
        "battery_pass_rate": metrics.get("battery", {}).get("pass_rate"),
        "categories_mastered": metrics.get("categories_mastered"),
        "domain_count": metrics.get("domain_count"),
        "physics_corpus_available": metrics.get("physics_corpus_available"),
        "chemistry_corpus_available": metrics.get("chemistry_corpus_available"),
        "patterns_mastered": metrics.get("patterns_mastered"),
        "patterns_total": metrics.get("patterns_total"),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "disclaimer": DISCLAIMER,
        "ocr_vision": metrics.get("ocr_vision"),
    }
    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "hostess7-engineering-runtime/v1",
            "updated": doc["updated"],
            "tier": doc["tier"],
            "engineering_score": doc["engineering_score"],
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
        print(json.dumps(engineering_score(), ensure_ascii=False))
        return 0
    if cmd in ("search", "answer", "query"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "PID control robotics"
        print(json.dumps({"ok": True, "query": q, "hits": search_engineering(q), "reply": format_engineering_reply(q)}, ensure_ascii=False))
        return 0
    if cmd in ("teach", "explain"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "engineering fluency"
        doc = explain_engineering_structured(q)
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
        "error": "usage: hostess7-engineering.py [json|search|battery|teach|ocr-ingest|ocr-train|ocr-status]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())