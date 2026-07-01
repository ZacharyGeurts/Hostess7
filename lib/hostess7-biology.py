#!/usr/bin/env pythong
"""Hostess 7 biology & medical chamber — full understanding of life sciences and human medicine."""
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
DOCTRINE = INSTALL / "data" / "hostess7-biology-doctrine.json"
BATTERY = INSTALL / "data" / "hostess7-biology-battery.json"
EXPLAIN = INSTALL / "data" / "hostess7-biology-explain.json"
OCR_DOCTRINE = INSTALL / "data" / "hostess7-biology-ocr-doctrine.json"
PANEL = STATE / "hostess7-biology-panel.json"
RUNTIME = STATE / "hostess7-biology-runtime.json"
LEDGER = STATE / "hostess7-biology-ledger.jsonl"
OCR_CORPUS = STATE / "hostess7-biology-ocr-corpus.json"
OCR_LEDGER = STATE / "hostess7-biology-ocr-ledger.jsonl"
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

ENABLED = os.environ.get("NEXUS_HOSTESS7_BIOLOGY", "1") == "1"

DISCLAIMER = (
    "Educational biology and medicine only — not medical advice, diagnosis, or treatment. "
    "For emergencies call local emergency services. Consult your clinician for personal care."
)

_SECTION_LABELS = (
    ("what", "What"),
    ("why", "Why"),
    ("how", "How"),
    ("pitfalls", "Pitfalls"),
    ("where", "Where"),
    ("example", "Example"),
)

_BIOLOGY_KEYS = (
    "biology", "human biology", "life science", "anatomy", "physiology", "cell", "mitochondria",
    "dna", "rna", "gene", "genetics", "chromosome", "evolution", "ecosystem", "microbiology",
    "bacteria", "virus", "immune", "immunity", "vaccine", "neuron", "brain", "heart", "lung",
    "kidney", "liver", "muscle", "bone", "tissue", "organ", "endocrine", "hormone", "metabolism",
    "photosynthesis", "mitosis", "meiosis", "protein", "enzyme", "pathogen", "symptom", "disease",
    "medical", "medicine", "clinical", "pharmacology", "diagnosis", "treatment", "hospital",
    "doctor", "nurse", "patient", "cpr", "stroke", "diabetes", "cancer", "infection",
    "biology mastery", "biology fluency", "human anatomy", "human physiology",
)

_BIO_LINE_RE = re.compile(
    r"(?:"
    r"mitochondri|membrane|organelle|nucleus|ribosome|ATP|chromosom|DNA|RNA|gene|allele|"
    r"protein|enzyme|mitosis|meiosis|evolution|ecosystem|bacteri|virus|fung|pathogen|"
    r"immune|antibod|vaccine|neuron|synapse|brain|cortex|heart|cardiac|lung|respirat|"
    r"kidney|renal|liver|hepatic|muscle|skeletal|bone|tissue|organ|anatomy|physiology|"
    r"endocrine|hormone|insulin|glucose|diabetes|hypertension|stroke|fever|infection|"
    r"antibiotic|cell\s+membrane|homeostasis|histology|embryo"
    r")",
    re.I,
)

BIOLOGY_DOMAINS: tuple[dict[str, Any], ...] = (
    {
        "id": "foundations",
        "title": "Foundations of biology",
        "tags": ("biology", "life", "organism", "cell", "tissue", "organ", "system", "population", "ecosystem"),
        "body": (
            "Biology studies life at levels of organization: molecule, cell, tissue, organ, organ system, organism, "
            "population, community, ecosystem, biosphere. Living things share characteristics: ordered structure, "
            "metabolism, growth, reproduction, response to environment, homeostasis, evolution. "
            "Scientific method: observation, hypothesis, experiment, analysis, peer review."
        ),
    },
    {
        "id": "cell_biology",
        "title": "Cell biology",
        "tags": ("cell", "mitochondria", "membrane", "organelle", "cytoskeleton", "atp", "cytoplasm", "nucleus"),
        "body": (
            "Cells are the fundamental unit of life. Prokaryotes lack membrane-bound nucleus; eukaryotes have nucleus "
            "and organelles. Mitochondria produce ATP via oxidative phosphorylation; chloroplasts photosynthesize in plants. "
            "Plasma membrane: phospholipid bilayer, selective permeability — diffusion, osmosis, facilitated diffusion, "
            "active transport. Endomembrane system: ER, Golgi, lysosomes, vesicles. Cytoskeleton: microtubules, actin, "
            "intermediate filaments. Cell cycle: interphase, mitosis, cytokinesis; checkpoints and apoptosis."
        ),
    },
    {
        "id": "molecular_biology",
        "title": "Molecular biology",
        "tags": ("dna", "rna", "transcription", "translation", "protein", "replication", "polymerase", "ribosome"),
        "body": (
            "Central dogma: DNA → RNA → protein. Replication: semiconservative, helicase, primase, polymerase, ligase. "
            "Transcription: RNA polymerase, promoter, mRNA processing (5' cap, poly-A tail, splicing in eukaryotes). "
            "Translation: ribosome, tRNA, codons, start/stop; genetic code is nearly universal. "
            "Gene regulation: operons in bacteria; transcription factors, enhancers, epigenetics (methylation, histones) in eukaryotes."
        ),
    },
    {
        "id": "genetics",
        "title": "Genetics & genomics",
        "tags": ("gene", "allele", "genetics", "heredity", "mendel", "dominant", "recessive", "mutation", "genome", "crispr"),
        "body": (
            "Genes are units of heredity at loci on chromosomes. Mendelian inheritance: dominant/recessive alleles, "
            "Punnett squares, segregation and independent assortment. Extensions: incomplete dominance, codominance, "
            "sex-linked traits, polygenic traits, pleiotropy, epistasis. Mutations: point, frameshift, chromosomal. "
            "Genomics: sequencing, GWAS, pharmacogenomics. CRISPR-Cas9 enables targeted gene editing with ethical oversight."
        ),
    },
    {
        "id": "evolution",
        "title": "Evolution",
        "tags": ("evolution", "natural selection", "adaptation", "speciation", "darwin", "phylogeny", "allele frequency"),
        "body": (
            "Evolution is change in allele frequencies over generations. Natural selection: variation, heritability, "
            "differential reproduction — adaptation to environment. Other mechanisms: genetic drift, gene flow, mutation. "
            "Speciation: reproductive isolation (geographic, temporal, behavioral). Phylogenetics reconstructs evolutionary "
            "relationships. Evidence: fossils, comparative anatomy, embryology, molecular sequences, biogeography."
        ),
    },
    {
        "id": "ecology",
        "title": "Ecology",
        "tags": ("ecosystem", "food web", "trophic", "population", "community", "biome", "niche", "carrying capacity"),
        "body": (
            "Ecology studies interactions among organisms and environment. Levels: population, community, ecosystem, biosphere. "
            "Energy flow: producers (autotrophs) → consumers → decomposers; 10% rule between trophic levels. "
            "Nutrient cycling: carbon, nitrogen, phosphorus, water. Population dynamics: growth models, carrying capacity, "
            "predator-prey cycles. Conservation biology addresses habitat loss, invasive species, climate change impacts."
        ),
    },
    {
        "id": "human_anatomy",
        "title": "Human anatomy",
        "tags": ("anatomy", "skeleton", "bone", "muscle", "organ", "skull", "vertebra", "joint", "histology", "tissue"),
        "body": (
            "Gross anatomy: directional terms (superior/inferior, anterior/posterior), body planes and cavities. "
            "Skeletal system: axial (skull, vertebral column, rib cage) and appendicular (limbs, girdles); bone types, "
            "joints (synovial, cartilaginous, fibrous). Muscular system: skeletal, smooth, cardiac muscle; origin/insertion. "
            "Organ systems overview: integumentary, skeletal, muscular, nervous, endocrine, cardiovascular, lymphatic, "
            "respiratory, digestive, urinary, reproductive. Histology: epithelial, connective, muscle, nervous tissues."
        ),
    },
    {
        "id": "human_physiology",
        "title": "Human physiology",
        "tags": ("physiology", "homeostasis", "cardiovascular", "respiratory", "renal", "digestive", "endocrine", "nervous"),
        "body": (
            "Physiology explains how systems maintain homeostasis. Cardiovascular: heart chambers, cardiac cycle, "
            "stroke volume, blood pressure regulation, coronary circulation. Respiratory: ventilation, gas exchange at "
            "alveoli, hemoglobin O2/CO2 transport, chemoreceptor control. Renal: glomerular filtration, tubular "
            "reabsorption/secretion, ADH and RAAS. Digestive: mechanical/chemical digestion, absorption, hepatic metabolism. "
            "Endocrine: hypothalamic-pituitary axes, feedback loops. Nervous: action potentials, synaptic transmission."
        ),
    },
    {
        "id": "microbiology",
        "title": "Microbiology",
        "tags": ("bacteria", "virus", "fungus", "microbe", "pathogen", "antibiotic", "culture", "gram", "prokaryote"),
        "body": (
            "Microbiology studies microscopic organisms. Bacteria: prokaryotic, peptidoglycan cell wall, Gram stain, "
            "binary fission; some are commensal, some pathogenic. Viruses: obligate intracellular parasites, capsid, "
            "optional envelope; not treated by antibiotics. Fungi: yeasts and molds; opportunistic infections in immunocompromised. "
            "Sterilization vs disinfection; culture techniques; Koch's postulates. Antimicrobial resistance is a global threat."
        ),
    },
    {
        "id": "immunology",
        "title": "Immunology",
        "tags": ("immune", "immunity", "antibody", "antigen", "vaccine", "innate", "adaptive", "t cell", "b cell", "inflammation"),
        "body": (
            "Innate immunity: barriers (skin, mucosa), phagocytes, NK cells, complement, inflammation, fever. "
            "Adaptive immunity: B cells (humoral, antibodies), T cells (cell-mediated, CD4 helper, CD8 cytotoxic). "
            "Primary vs secondary immune response; immunological memory enables vaccines. Autoimmunity, allergy (IgE), "
            "and immunodeficiency alter responses. Transplant immunology requires HLA matching and immunosuppression."
        ),
    },
    {
        "id": "neuroscience",
        "title": "Neuroscience",
        "tags": ("brain", "neuron", "synapse", "neurotransmitter", "cns", "spinal", "cortex", "memory", "reflex"),
        "body": (
            "Nervous system: CNS (brain, spinal cord) and PNS (somatic, autonomic — sympathetic/parasympathetic). "
            "Neuron structure: dendrites, axon, myelin, nodes of Ranvier. Action potential: resting potential, "
            "depolarization, repolarization, saltatory conduction. Synapse: neurotransmitters (glutamate, GABA, dopamine, "
            "serotonin, acetylcholine), receptors, reuptake. Brain regions: cortex lobes, cerebellum, brainstem, limbic system. "
            "Plasticity underlies learning and memory; blood-brain barrier protects CNS."
        ),
    },
    {
        "id": "developmental_biology",
        "title": "Developmental biology",
        "tags": ("embryo", "development", "fertilization", "gastrulation", "organogenesis", "stem cell", "teratogen"),
        "body": (
            "Human development: fertilization, cleavage, blastocyst implantation, gastrulation (ectoderm, mesoderm, endoderm), "
            "neurulation, organogenesis. Embryonic induction and morphogen gradients pattern tissues. "
            "Stem cells: totipotent, pluripotent, multipotent — therapeutic and research applications with ethics. "
            "Teratogens (alcohol, certain drugs, infections) disrupt development; critical periods matter."
        ),
    },
    {
        "id": "nutrition_metabolism",
        "title": "Nutrition & metabolism",
        "tags": ("nutrition", "metabolism", "macronutrient", "vitamin", "glucose", "lipid", "protein", "calorie", "glycolysis"),
        "body": (
            "Macronutrients: carbohydrates, lipids, proteins — provide energy and building blocks. "
            "Micronutrients: vitamins and minerals as cofactors and regulators. Metabolism: glycolysis, Krebs cycle, "
            "oxidative phosphorylation; gluconeogenesis, lipolysis, protein catabolism. "
            "Fed vs fasted states; insulin and glucagon coordinate fuel use. BMI and body composition inform population health, "
            "not individual diagnosis alone."
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


def _medical_module() -> Any | None:
    script = HOSTESS7_ROOT / "scripts" / "field_medical_corpus.py"
    if not script.is_file():
        return None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_medical_corpus", script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(script.parent))
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _score_biology_domains(query: str, domains: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict[str, Any]]] = []
    for d in domains:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:1500]}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("anatomy", "bone", "skeleton", "muscle", "organ")):
            if d.get("id") == "human_anatomy":
                score += 12
        if any(k in q for k in ("physiology", "heart", "lung", "kidney", "homeostasis")):
            if d.get("id") == "human_physiology":
                score += 12
        if any(k in q for k in ("cell", "mitochondria", "membrane", "organelle")):
            if d.get("id") == "cell_biology":
                score += 15
        if any(k in q for k in ("dna", "gene", "genetics", "allele", "chromosome")):
            if d.get("id") in ("genetics", "molecular_biology"):
                score += 12
        if any(k in q for k in ("evolution", "natural selection", "darwin")):
            if d.get("id") == "evolution":
                score += 15
        if any(k in q for k in ("ecosystem", "food web", "trophic")):
            if d.get("id") == "ecology":
                score += 15
        if any(k in q for k in ("bacteria", "virus", "microbe", "pathogen")):
            if d.get("id") == "microbiology":
                score += 15
        if any(k in q for k in ("immune", "vaccine", "antibody", "immunity")):
            if d.get("id") == "immunology":
                score += 12
        if any(k in q for k in ("neuron", "brain", "synapse", "nervous")):
            if d.get("id") == "neuroscience":
                score += 12
        if any(k in q for k in ("embryo", "development", "fertilization")):
            if d.get("id") == "developmental_biology":
                score += 12
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return scored


def search_biology(query: str, *, limit: int = 5) -> list[dict[str, Any]]:
    """Search biology domains and medical corpus bridge."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    q = query.lower()
    clinical = any(
        k in q
        for k in (
            "diabetes", "stroke", "heart attack", "cancer", "infection", "fever", "emergency",
            "911", "doctor", "clinical", "treatment", "diagnosis", "pharmacology", "symptom",
            "hypertension", "antibiotic", "depression", "anxiety",
        )
    )

    med_mod = _medical_module()
    if med_mod and clinical:
        try:
            med_mod.ensure_corpus()
            for row in med_mod.search_medical(query, limit=max(2, limit // 2 + 1)):
                pid = str(row.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)
                out.append({**row, "source": row.get("source") or "medical_corpus"})
        except Exception:
            pass

    domain_scored = _score_biology_domains(query, [dict(d) for d in BIOLOGY_DOMAINS])
    for _, d in domain_scored:
        did = str(d.get("id", ""))
        if did in seen:
            continue
        seen.add(did)
        row = dict(d)
        row["source"] = "biology_domain"
        out.append(row)
        if len(out) >= limit:
            break

    if not out and med_mod:
        try:
            for row in med_mod.search_medical(query, limit=limit):
                pid = str(row.get("id", ""))
                if pid in seen:
                    continue
                seen.add(pid)
                out.append({**row, "source": "medical_corpus"})
        except Exception:
            pass

    return out[:limit]


def synthesize_biology_paragraphs(query: str) -> list[str]:
    hits = search_biology(query, limit=4)
    if not hits:
        hits = search_biology("biology human anatomy physiology medicine", limit=3)
    paras: list[str] = [DISCLAIMER]
    for h in hits:
        title = h.get("title", "Biology")
        body = str(h.get("body", "")).strip()
        if len(body) > 1100:
            body = body[:1100] + "… [truncated]"
        src = h.get("source", "")
        if src == "medical_corpus" or h.get("journal"):
            paras.append(f"{title} (medical corpus): {body}")
        else:
            paras.append(f"{title}: {body}")
    return paras


def format_biology_reply(query: str) -> str:
    paras = synthesize_biology_paragraphs(query)
    if len(paras) <= 1:
        return f"I could not match that biology query cleanly — try anatomy, cell biology, genetics, or a medical topic. {DISCLAIMER}"
    return "\n\n".join(paras)


def _looks_like_biology(text: str) -> bool:
    low = (text or "").lower()
    if any(k in low for k in _BIOLOGY_KEYS):
        return True
    if _BIO_LINE_RE.search(low):
        return True
    return False


def extract_biology_query(text: str) -> str:
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
    hits = search_biology(query, limit=6)
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
        "medical_corpus_available": _medical_module() is not None,
    }


def _text_quality_ok(text: str) -> bool:
    if not text:
        return False
    sample = text[:4000]
    if "\x00" in sample or "H7B" in sample[:8]:
        return False
    printable = sum(1 for c in sample if c.isprintable() or c in "\n\t")
    return printable / max(len(sample), 1) >= 0.85


def _plausible_biology_candidate(text: str) -> bool:
    if not _looks_like_biology(text):
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


def extract_biology_candidates(text: str, *, source_id: str = "") -> list[dict[str, Any]]:
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

    for m in _BIO_LINE_RE.finditer(text):
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 80)
        add(text[start:end], "regex_context")

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < min_len:
            continue
        if _BIO_LINE_RE.search(line):
            add(line, "biology_line")

    return out[:200]


def _ocr_tesseract(path: Path) -> str:
    core_py = INSTALL / "lib" / "final-eye-ocr-core.py"
    if not core_py.is_file():
        return ""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("final_eye_ocr_bio", core_py)
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
    if spec.get("biology_filter"):
        bid = str(row.get("id", "")).lower()
        title = str(row.get("title", "")).lower()
        path_s = str(row.get("path", "")).lower()
        if not any(
            k in bid or k in title or k in path_s
            for k in ("biology", "microbiology", "anatomy", "physiology", "dewey/610", "medical", "nursing", "health")
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
    for cand in extract_biology_candidates(text, source_id=source_id):
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
    """Feed biology think tank from OCR vision and corpus sources."""
    ocr_doc = _load(OCR_DOCTRINE, {})
    ingest_cfg = ocr_doc.get("ingest") or {}
    max_files = limit_per_source or int(ingest_cfg.get("max_files_per_source") or 500)
    max_bytes = int(ingest_cfg.get("max_bytes_per_file") or 250000)

    corpus = _load(OCR_CORPUS, {
        "schema": "hostess7-biology-ocr-corpus/v1",
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


def _verify_biology_candidate(text: str) -> bool:
    if not _plausible_biology_candidate(text):
        return False
    scored = _score_biology_domains(text, [dict(d) for d in BIOLOGY_DOMAINS])
    if scored and scored[0][0] >= 4:
        return True
    med = _medical_module()
    if med:
        try:
            med.ensure_corpus()
            hits = med.search_medical(text, limit=1)
            if hits:
                return True
        except Exception:
            pass
    return len(_tokens(text)) >= 3 and _BIO_LINE_RE.search(text) is not None


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
        ok = _verify_biology_candidate(text) if verify else False
        row = {**cand, "verified": ok}
        if ok:
            verified += 1
        samples.append(row)

    plausible_n = sum(1 for c in candidates if _plausible_biology_candidate(str(c.get("text") or "")))
    total = len(candidates)
    rate = verified / max(plausible_n, 1)
    fluent_floor = int(train_cfg.get("fluent_samples_floor") or 40)
    master_floor = int(train_cfg.get("master_samples_floor") or 100)
    train_doc = {
        "schema": "hostess7-biology-ocr-train/v1",
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
    _save(STATE / "hostess7-biology-ocr-train.json", train_doc)
    _append_ledger({"ts": _now(), "event": "ocr_train", "verified": verified, "total": total, "rate": rate})
    return {"ok": True, **train_doc}


def ocr_vision_status() -> dict[str, Any]:
    corpus = _load(OCR_CORPUS, {})
    train = _load(STATE / "hostess7-biology-ocr-train.json", {})
    return {
        "schema": "hostess7-biology-ocr-status/v1",
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
            mastered = len(BIOLOGY_DOMAINS) >= 10
        elif pid == "medical_bridge":
            mastered = bool(bat.get("medical_corpus_available"))
        elif pid == "battery_verify":
            mastered = bool(bat.get("passed"))
        elif pid == "disclaimer_seal":
            mastered = DISCLAIMER in format_biology_reply("heart anatomy")
        elif pid == "textbook_manifest":
            mf = INSTALL / "data" / "field-brain" / "manifest.json"
            mastered = mf.is_file()
        elif pid == "natural_language":
            mastered = _looks_like_biology("what is mitosis in human cells")
        elif pid == "structured_explain":
            mastered = bool(_load(EXPLAIN, {}).get("topics"))
        elif pid == "ocr_vision_train":
            tr = _load(STATE / "hostess7-biology-ocr-train.json", {})
            mastered = bool(tr.get("mastered") or tr.get("fluent"))
        out.append({"id": pid, "label": pat.get("label"), "mastered": mastered})
    return out


def biology_score(*, battery: dict[str, Any] | None = None) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    bat = battery or _run_battery()
    patterns = _pattern_mastery()
    mastered = sum(1 for p in patterns if p.get("mastered"))
    rate = float(bat.get("pass_rate") or 0) / 100.0
    by_cat = bat.get("by_category") or {}
    cats_mastered = sum(1 for c in by_cat.values() if c.get("total") and c["passed"] >= c["total"])
    ocr_train = _load(STATE / "hostess7-biology-ocr-train.json", {})
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
    score += 0.02 if bat.get("medical_corpus_available") else 0.0
    score = round(min(0.99, score), 4)

    fluent_floor = float(doctrine.get("fluent_floor_score") or 0.86)
    master_target = float(doctrine.get("master_biology_score") or 0.95)
    tier = "assistant_guess"
    if score >= master_target and bat.get("passed") and cats_mastered >= 6:
        tier = "biology_master"
    elif score >= fluent_floor and bat.get("passed"):
        tier = "biology_fluent"
    elif rate >= 0.5:
        tier = "biology_basic"

    return {
        "score": score,
        "biology_score": score,
        "tier": tier,
        "fluent": tier in ("biology_fluent", "biology_master"),
        "mastered": tier == "biology_master",
        "better_than_assistant": score >= fluent_floor and bat.get("passed"),
        "battery": bat,
        "patterns_mastered": mastered,
        "patterns_total": len(patterns),
        "categories_mastered": cats_mastered,
        "medical_corpus_available": bat.get("medical_corpus_available"),
        "domain_count": len(BIOLOGY_DOMAINS),
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
            return mod.merge_explain_doc("biology", base)
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


def explain_biology_structured(query: str = "") -> dict[str, Any]:
    q = (query or "").strip()
    low = q.lower()
    doc = _load(EXPLAIN, {})
    intro = str(doc.get("introduction") or "").strip()
    fmt = doc.get("format") or [s[0] for s in _SECTION_LABELS]
    metrics = biology_score()

    topic = _match_explain_topic(q)
    if not topic and any(k in low for k in ("biology", "human biology", "medical knowledge", "anatomy", "physiology")):
        doctrine = _load(DOCTRINE, {})
        sections = {
            "what": "Biology mastery means I synthesize life sciences from structured domains through human anatomy, physiology, and medical corpus bridge.",
            "why": str(doctrine.get("fluency_claim") or ""),
            "how": (
                f"Battery pass {metrics.get('battery', {}).get('pass_rate')}% · tier {metrics.get('tier')} · "
                f"score {round(float(metrics.get('score') or 0) * 100)}% · domains {metrics.get('domain_count')}"
            ),
            "pitfalls": "Personal diagnosis; omitting emergency disclaimer; training on binary .h7 as text.",
            "where": "lib/hostess7-biology.py, field_medical_corpus.py, /api/hostess7/biology",
            "example": "Ask: innate vs adaptive immunity — immunology domain with disclaimer.",
        }
        topic = {"id": "biology_fluency_live", **sections}

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
            "biology_score": metrics.get("score"),
            "tier": metrics.get("tier"),
            "disclaimer": DISCLAIMER,
        }

    fallback = intro + " " + DISCLAIMER + " Ask me about cell biology, genetics, human anatomy, physiology, or medical topics."
    return {"ok": True, "query": q, "reply": fallback.strip(), "format": fmt, "disclaimer": DISCLAIMER}


def explain_biology(query: str = "") -> str:
    return str(explain_biology_structured(query).get("reply") or "")


def build_panel(*, write: bool = True) -> dict[str, Any]:
    metrics = biology_score()
    doc = {
        "schema": "hostess7-biology/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "biology_score": metrics.get("score"),
        "tier": metrics.get("tier"),
        "fluent": metrics.get("fluent"),
        "mastered": metrics.get("mastered"),
        "better_than_assistant": metrics.get("better_than_assistant"),
        "battery_pass_rate": metrics.get("battery", {}).get("pass_rate"),
        "categories_mastered": metrics.get("categories_mastered"),
        "domain_count": metrics.get("domain_count"),
        "medical_corpus_available": metrics.get("medical_corpus_available"),
        "patterns_mastered": metrics.get("patterns_mastered"),
        "patterns_total": metrics.get("patterns_total"),
        "motto": _load(DOCTRINE, {}).get("motto"),
        "disclaimer": DISCLAIMER,
        "ocr_vision": metrics.get("ocr_vision"),
    }
    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "hostess7-biology-runtime/v1",
            "updated": doc["updated"],
            "tier": doc["tier"],
            "biology_score": doc["biology_score"],
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
        print(json.dumps(biology_score(), ensure_ascii=False))
        return 0
    if cmd in ("search", "answer", "query"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "mitochondria function"
        print(json.dumps({"ok": True, "query": q, "hits": search_biology(q), "reply": format_biology_reply(q)}, ensure_ascii=False))
        return 0
    if cmd in ("teach", "explain"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "biology fluency"
        doc = explain_biology_structured(q)
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
        "error": "usage: hostess7-biology.py [json|search|battery|teach|ocr-ingest|ocr-train|ocr-status]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())