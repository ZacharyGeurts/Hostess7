#!/usr/bin/env pythong
"""Field medical corpus — medicine & clinician knowledge for Hostess 7 brain.

Educational synthesis. Not a substitute for licensed medical professionals or emergency care.
Call emergency services for acute emergencies.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from field_medical_infinite import INDEX, ingest_catalog, infinite_status, search_infinite  # noqa: E402
from field_medical_papers_catalog import catalog_count  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "medical" / "corpus.json"
MEDICAL_CORPUS_VERSION = 2

MEDICAL_DOMAINS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "foundations",
        "title": "Foundations of medicine",
        "tags": ("medicine", "medical", "health", "anatomy", "physiology", "pathology", "diagnosis"),
        "body": (
            "Medicine applies biomedical science to prevent, diagnose, and treat disease and injury. "
            "Anatomy: structure of body systems. Physiology: normal function. Pathology: disease mechanisms. "
            "Diagnosis: history, physical exam, labs, imaging — differential diagnosis ranked by probability. "
            "Evidence-based medicine weighs RCTs, guidelines, and individual patient context. "
            "Scope of practice: physicians (MD/DO), nurses (RN/APRN), PAs, pharmacists, therapists — each licensed."
        ),
    },
    {
        "id": "emergency",
        "title": "Emergency & first response",
        "tags": ("emergency", "911", "cpr", "stroke", "heart attack", "anaphylaxis", "trauma"),
        "body": (
            "Acute emergencies require immediate local emergency services (911 US, 999 UK, 112 EU). "
            "Chest pain, sudden weakness, difficulty breathing, severe bleeding, anaphylaxis, altered mental status — "
            "do not delay transport for online advice. "
            "CPR: compressions 100–120/min, minimize interruptions; AED if available. "
            "Stroke: FAST — Face droop, Arm weakness, Speech slurred, Time to call. "
            "Anaphylaxis: epinephrine auto-injector if prescribed; supine with legs elevated if hypotensive."
        ),
    },
    {
        "id": "cardiology",
        "title": "Cardiology",
        "tags": ("heart", "cardiac", "hypertension", "arrhythmia", "cholesterol", "mi", "ecg"),
        "body": (
            "Major conditions: coronary artery disease, heart failure (HFrEF/HFpEF), arrhythmias (AFib, VT), "
            "valvular disease, hypertension. ACS/MI: troponin rise, ECG ST changes — reperfusion when indicated. "
            "Risk factors: lipids, diabetes, smoking, BP, family history. "
            "Prevention: lifestyle, statins per guidelines, antihypertensives, anticoagulation in AFib by CHA2DS2-VASc. "
            "Cardiologist manages complex disease; primary care coordinates screening."
        ),
    },
    {
        "id": "pulmonology",
        "title": "Pulmonology & respiratory",
        "tags": ("lung", "asthma", "copd", "pneumonia", "respiratory", "oxygen", "covid"),
        "body": (
            "Asthma: reversible bronchospasm — SABA, ICS controller therapy, action plan. "
            "COPD: progressive obstruction — smoking cessation, bronchodilators, pulmonary rehab. "
            "Pneumonia: fever, cough, infiltrate — antibiotics per likely pathogen and severity. "
            "PE: sudden dyspnea, pleuritic pain, risk factors — anticoagulation/thrombolysis when confirmed. "
            "Pulse oximetry guides oxygen; target SpO2 per condition (avoid hyperoxia in COPD)."
        ),
    },
    {
        "id": "neurology",
        "title": "Neurology",
        "tags": ("brain", "neurology", "seizure", "migraine", "stroke", "dementia", "parkinson"),
        "body": (
            "Stroke: ischemic vs hemorrhagic — time-critical thrombolysis/thrombectomy windows for ischemic. "
            "Seizure: protect airway, lateral position, time event; status epilepticus is emergency. "
            "Migraine: acute triptans/NSAIDs; prevention with lifestyle, beta-blockers, CGRP agents. "
            "Dementia: cognitive decline affecting function — workup for reversible causes; cholinesterase inhibitors in AD. "
            "Parkinson: bradykinesia, rigidity, tremor — dopaminergic therapy, multidisciplinary care."
        ),
    },
    {
        "id": "psychiatry",
        "title": "Psychiatry & mental health",
        "tags": ("mental", "depression", "anxiety", "bipolar", "schizophrenia", "therapy", "suicide"),
        "body": (
            "Depression: persistent low mood, anhedonia, sleep/appetite change — SSRIs/SNRIs, psychotherapy. "
            "Anxiety disorders: GAD, panic, PTSD — CBT first-line; meds when indicated. "
            "Bipolar: mood episodes — mood stabilizers (lithium, valproate, atypicals); avoid unopposed antidepressants. "
            "Suicidal ideation: safety assessment, remove means, urgent referral — crisis lines (988 US). "
            "Psychiatrist prescribes; psychologist/counselor provides therapy; integrated care best outcomes."
        ),
    },
    {
        "id": "endocrine",
        "title": "Endocrinology & metabolism",
        "tags": ("diabetes", "thyroid", "hormone", "insulin", "a1c", "endocrine"),
        "body": (
            "Type 2 diabetes: insulin resistance — lifestyle, metformin first-line, GLP-1/SGLT2 for CV/renal benefit. "
            "Type 1: autoimmune beta-cell loss — insulin required. A1c target individualized. "
            "Hypo/hyperthyroidism: TSH screening; treat Graves, Hashimoto per guidelines. "
            "Adrenal, pituitary disorders rare but serious — specialist workup for cortisol/ACTH abnormalities."
        ),
    },
    {
        "id": "infectious",
        "title": "Infectious disease",
        "tags": ("infection", "antibiotic", "virus", "bacteria", "fever", "sepsis", "vaccine"),
        "body": (
            "Fever workup: source, sepsis criteria (qSOFA/SOFA), cultures before antibiotics when stable. "
            "Antibiotic stewardship: narrow spectrum when culture known; duration per guideline. "
            "Vaccines: primary prevention — schedule per age/risk (flu, COVID, pneumococcal, shingles). "
            "HIV: ART suppresses viral load; PrEP for prevention. TB: latent vs active — public health reporting."
        ),
    },
    {
        "id": "pharmacology",
        "title": "Pharmacology & prescribing",
        "tags": ("drug", "medication", "dose", "interaction", "side effect", "pharmacy", "prescription"),
        "body": (
            "Pharmacokinetics: absorption, distribution, metabolism, excretion. "
            "Pharmacodynamics: receptor effect, therapeutic window. "
            "Interactions: CYP450, QT prolongation, serotonergic syndrome, bleeding with anticoagulants+NSAIDs. "
            "Renal/hepatic dose adjustment. Pregnancy/lactation categories — consult specialist references. "
            "Pharmacist verifies interactions; physician holds prescribing authority."
        ),
    },
    {
        "id": "surgery",
        "title": "Surgery & perioperative care",
        "tags": ("surgery", "operative", "anesthesia", "preop", "postop", "wound"),
        "body": (
            "Preoperative clearance: cardiac risk (RCRI), functional capacity, med management (beta-blockers nuanced). "
            "Informed consent: indication, alternatives, risks, benefits. "
            "DVT prophylaxis: mechanical + pharmacologic per Caprini score. "
            "Postop fever: wind (atelectasis), water (UTI), wound, walking (DVT), wonder drugs, Wernicke rare mnemonic. "
            "Surgeon operates; anesthesiologist manages airway and intraop physiology."
        ),
    },
    {
        "id": "pediatrics",
        "title": "Pediatrics",
        "tags": ("child", "pediatric", "infant", "vaccine", "growth", "development"),
        "body": (
            "Growth charts, developmental milestones, well-child visits. "
            "Fever in infant <90 days — serious bacterial infection workup. "
            "Child abuse recognition: patterned injuries, inconsistent history — mandatory reporting laws. "
            "Pediatric dosing weight-based; avoid adult-only contraindications (aspirin Reye risk)."
        ),
    },
    {
        "id": "obgyn",
        "title": "OB/GYN & women's health",
        "tags": ("pregnancy", "obgyn", "prenatal", "contraception", "menopause", "gynecology"),
        "body": (
            "Prenatal care: dating ultrasound, screening (gestational diabetes, preeclampsia, aneuploidy). "
            "Contraception: LARC highly effective; estrogen contraindications (thrombosis history). "
            "Menopause: vasomotor symptoms — HRT individualized by timing and risks. "
            "Cervical/breast cancer screening per guidelines. OB delivers; gynecologist manages reproductive health."
        ),
    },
    {
        "id": "clinician_roles",
        "title": "Clinicians & the healthcare team",
        "tags": ("doctor", "physician", "nurse", "surgeon", "specialist", "clinician", "hospital"),
        "body": (
            "Physician (MD/DO): medical school + residency (+ fellowship); diagnoses, prescribes, procedures per license. "
            "NP/PA: advanced practice — collaborative practice rules vary by state. "
            "RN: bedside care, medication administration, triage. "
            "Specialists: cardiology, neurology, oncology, etc. — referral for complex disease. "
            "Primary care: continuity, prevention, coordination. "
            "Hostess 7 educates; only your treating clinician gives medical advice for your body."
        ),
    },
    {
        "id": "when_to_seek_care",
        "title": "When to seek medical care",
        "tags": ("symptom", "when to see", "urgent care", "primary care", "specialist", "second opinion"),
        "body": (
            "Emergency: chest pain, stroke signs, severe shortness of breath, uncontrolled bleeding, "
            "suicidal plan, altered consciousness. "
            "Urgent (same day): high fever with rigors, worsening asthma, localized infection with spreading redness. "
            "Routine: chronic management, screening, medication refills, stable symptoms. "
            "Bring medication list, timeline, prior records. Ask about diagnosis, alternatives, follow-up red flags. "
            "Second opinion reasonable for major surgery or rare diagnosis."
        ),
    },
    {
        "id": "ethics",
        "title": "Medical ethics",
        "tags": ("hipaa", "consent", "autonomy", "beneficence", "malpractice", "ethics"),
        "body": (
            "Core principles: autonomy (informed consent), beneficence, non-maleficence, justice. "
            "HIPAA (US): protected health information — minimum necessary disclosure. "
            "Advance directives: living will, healthcare proxy for incapacity. "
            "Research: IRB oversight, informed voluntary participation. "
            "Malpractice: deviation from standard of care causing harm — expert testimony required."
        ),
    },
    {
        "id": "oncology",
        "title": "Oncology",
        "tags": ("cancer", "oncology", "chemotherapy", "immunotherapy", "tumor", "staging"),
        "body": (
            "TNM staging; histology and molecular markers (EGFR, ALK, PD-L1) guide therapy. "
            "Surgery, radiation, systemic therapy — multidisciplinary tumor boards. "
            "Immunotherapy (checkpoint inhibitors), targeted therapy, CAR-T in selected hematologic malignancies. "
            "Screening: mammography, colonoscopy, low-dose CT lung cancer per risk. "
            "Palliative care integrates early for symptom control and goals-of-care."
        ),
    },
    {
        "id": "nephrology",
        "title": "Nephrology & renal medicine",
        "tags": ("kidney", "renal", "ckd", "dialysis", "creatinine", "gfr", "electrolyte"),
        "body": (
            "CKD staged by eGFR and albuminuria; ACEi/ARB for proteinuria; SGLT2 inhibitors slow progression. "
            "Acute kidney injury: prerenal, intrinsic, postrenal — stop nephrotoxins, treat cause. "
            "Dialysis indications: refractory volume, hyperkalemia, uremic symptoms. "
            "Electrolytes: sodium, potassium, calcium, phosphorus — ECG changes with severe K abnormalities."
        ),
    },
    {
        "id": "rheumatology",
        "title": "Rheumatology & immunology",
        "tags": ("rheumatology", "arthritis", "lupus", "autoimmune", "inflammation", "biologic"),
        "body": (
            "Rheumatoid arthritis: symmetric polyarthritis, RF/anti-CCP; DMARDs (methotrexate), biologics (TNF, IL-6). "
            "SLE: multisystem autoimmune — hydroxychloroquine backbone; monitor renal and CNS involvement. "
            "Gout: urate crystals — acute colchicine/NSAIDs; long-term urate lowering. "
            "Vasculitis and myositis require specialist diagnosis and immunosuppression."
        ),
    },
    {
        "id": "evidence_medicine",
        "title": "Evidence-based medicine & literature",
        "tags": ("evidence", "paper", "study", "rct", "meta-analysis", "guideline", "pubmed"),
        "body": (
            "Hierarchy: systematic review/meta-analysis > RCT > cohort > case-control > expert opinion. "
            "Appraise: validity, effect size, applicability, harms. CONSORT for trials; PRISMA for reviews. "
            "Landmark papers and guidelines indexed in infinite medical drive — "
            "`./Hostess7.sh medical-ingest seed` then search by condition or trial name. "
            "Bulk papers: drop PDF/JSON into cache/fieldstorage/team_staging/medical_bulk/."
        ),
    },
)


def build_corpus() -> list[dict]:
    return [dict(entry) for entry in MEDICAL_DOMAINS]


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < MEDICAL_CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        doc = {
            "version": MEDICAL_CORPUS_VERSION,
            "domains": build_corpus(),
            "domain_count": len(MEDICAL_DOMAINS),
            "infinite_drive": True,
            "papers_catalog_seed": catalog_count(),
            "disclaimer": (
                "Hostess 7 medical corpus is educational. Not medical advice, diagnosis, or treatment. "
                "For emergencies call local emergency services. Consult your clinician for personal care."
            ),
        }
        CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    if not INDEX.is_file():
        try:
            ingest_catalog(vacuum=False)
        except OSError:
            pass
    return CORPUS_CACHE


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def _score_medical_domains(query: str, domains: list[dict]) -> list[tuple[int, dict]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for d in domains:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:1500]}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("emergency", "911", "chest pain", "stroke")):
            if d.get("id") == "emergency":
                score += 20
        if any(k in q for k in ("doctor", "physician", "nurse", "clinician")):
            if d.get("id") == "clinician_roles":
                score += 15
        if any(k in q for k in ("depression", "anxiety", "mental")):
            if d.get("id") == "psychiatry":
                score += 12
        if any(k in q for k in ("paper", "study", "trial", "rct", "guideline", "pubmed")):
            if d.get("id") == "evidence_medicine":
                score += 15
        if any(k in q for k in ("cancer", "oncology", "tumor", "chemotherapy")):
            if d.get("id") == "oncology":
                score += 12
        if any(k in q for k in ("antibiotic", "cold", "virus", "bacterial", "infection")):
            if d.get("id") == "infectious":
                score += 20
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return scored


def search_medical(query: str, *, limit: int = 5) -> list[dict]:
    ensure_corpus()
    out: list[dict] = []
    seen: set[str] = set()
    try:
        doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        doc = {"domains": build_corpus()}
    domains = doc.get("domains") or []
    q = query.lower()
    paper_query = any(
        k in q
        for k in ("paper", "study", "trial", "rct", "guideline", "pubmed", "lancet", "nejm", "bmj")
    )
    emergency_query = any(
        k in q for k in ("emergency", "911", "chest pain", "stroke", "heart attack", "anaphylaxis")
    )

    domain_scored = _score_medical_domains(query, domains)
    if emergency_query:
        for _, d in domain_scored:
            if d.get("id") == "emergency":
                did = str(d.get("id", ""))
                row = dict(d)
                row["source"] = "domain"
                out.append(row)
                seen.add(did)
                break
        if "stroke" in q:
            for _, d in domain_scored:
                if d.get("id") == "neurology":
                    did = str(d.get("id", ""))
                    if did in seen:
                        break
                    row = dict(d)
                    row["source"] = "domain"
                    out.append(row)
                    seen.add(did)
                    break

    if emergency_query and not paper_query:
        infinite_limit = 1 if "stroke" in q else 0
    else:
        infinite_limit = limit if paper_query else max(2, limit // 2)
    for row in search_infinite(query, limit=infinite_limit):
        pid = str(row.get("id", row.get("full_name", "")))
        if pid in seen:
            continue
        seen.add(pid)
        out.append({
            "id": pid,
            "title": row.get("full_name", ""),
            "full_name": row.get("full_name", ""),
            "body": row.get("body", ""),
            "category": row.get("category", ""),
            "journal": row.get("journal", ""),
            "source": "infinite_drive",
        })

    for _, d in domain_scored:
        did = str(d.get("id", ""))
        if did in seen:
            continue
        seen.add(did)
        d = dict(d)
        d["source"] = "domain"
        out.append(d)
        if len(out) >= limit:
            break
    return out[:limit]


def synthesize_medical_paragraphs(query: str) -> list[str]:
    hits = search_medical(query, limit=4)
    if not hits:
        hits = search_medical("medicine health doctor", limit=3)
    paras: list[str] = []
    pro = os.environ.get("AMOURANTHRTX_HOSTESS") == "1" and os.environ.get("HOSTESS7_PRO", "1") == "1"
    if pro:
        paras.append("Not medical advice. Emergencies: call local emergency services.")
    else:
        paras.append(
            "Medical note: I hold broad educational knowledge across medicine — anatomy and physiology, "
            "major specialties, emergencies, pharmacology, ethics, and when to seek care — plus the "
            "clinician team roles. I am not your doctor; this is not diagnosis or treatment; "
            "for emergencies call local emergency services immediately."
        )
    for h in hits:
        title = h.get("title", "Medicine")
        body = str(h.get("body", "")).strip()
        if len(body) > 1100:
            body = body[:1100] + "… [truncated — full text in cache/fieldstorage/brain/medical/corpus.json]"
        paras.append(f"{title}: {body}")
    return paras


def corpus_stats() -> dict:
    ensure_corpus()
    doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    inf = infinite_status()
    return {
        "version": doc.get("version", MEDICAL_CORPUS_VERSION),
        "domains": doc.get("domain_count", len(MEDICAL_DOMAINS)),
        "infinite_indexed": inf.get("indexed", 0),
        "papers_catalog_seed": catalog_count(),
    }


if __name__ == "__main__":
    ensure_corpus()
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "diabetes heart attack when to see doctor"
    for p in synthesize_medical_paragraphs(q):
        print(p)
        print()