#!/usr/bin/env pythong
"""Medical papers & documents catalog — landmark literature for infinite drive seed."""
from __future__ import annotations

from typing import Iterator

MEDICAL_PAPER_CATEGORIES: tuple[str, ...] = (
    "foundations",
    "clinical_trial",
    "guideline",
    "genetics",
    "infectious",
    "cardiology",
    "oncology",
    "neurology",
    "psychiatry",
    "public_health",
    "ethics",
    "methods",
)

LANDMARK_PAPERS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "hippocratic_corpus",
        "full_name": "Hippocratic Corpus — foundational medical ethics",
        "authors": ("Hippocratic school",),
        "year": "circa 400 BCE",
        "journal": "historical",
        "category": "ethics",
        "tags": ("hippocrates", "ethics", "history", "medicine"),
        "body": (
            "Early Western medical tradition; primum non nocere (first, do no harm) attributed in spirit. "
            "Physician duty, prognosis, dietetics — foundation for professional medical ethics."
        ),
    },
    {
        "id": "jenner_vaccination_1798",
        "full_name": "An Inquiry into the Causes and Effects of the Variolae Vaccinae",
        "authors": ("Edward Jenner",),
        "year": "1798",
        "journal": "historical monograph",
        "category": "infectious",
        "tags": ("vaccine", "smallpox", "immunization", "public health"),
        "body": (
            "Cowpox inoculation protects against smallpox — foundation of vaccination and modern immunology practice."
        ),
    },
    {
        "id": "snow_cholera_1855",
        "full_name": "On the Mode of Communication of Cholera",
        "authors": ("John Snow",),
        "year": "1855",
        "journal": "historical",
        "category": "public_health",
        "tags": ("epidemiology", "cholera", "water", "outbreak"),
        "body": (
            "Broad Street pump investigation — geographic epidemiology proving waterborne transmission; "
            "landmark field epidemiology and public health intervention."
        ),
    },
    {
        "id": "pasteur_germ_theory",
        "full_name": "Germ Theory of Disease — experimental foundations",
        "authors": ("Louis Pasteur", "Robert Koch"),
        "year": "1860s–1880s",
        "journal": "historical",
        "category": "infectious",
        "tags": ("germ", "bacteria", "infection", "microbiology"),
        "body": (
            "Microorganisms cause fermentation and disease; Koch's postulates link specific organisms to illness; "
            "basis for antibiotics, sterilization, and modern infectious disease medicine."
        ),
    },
    {
        "id": "watson_crick_1953",
        "full_name": "Molecular Structure of Nucleic Acids: A Structure for Deoxyribose Nucleic Acid",
        "authors": ("James Watson", "Francis Crick"),
        "year": "1953",
        "journal": "Nature",
        "category": "genetics",
        "tags": ("dna", "double helix", "genetics", "molecular biology"),
        "body": (
            "DNA double helix with base pairing (A-T, G-C) — central dogma framework; "
            "enabled genomics, CRISPR, personalized medicine."
        ),
    },
    {
        "id": "sanger_sequencing_1977",
        "full_name": "DNA Sequencing with Chain-Terminating Inhibitors",
        "authors": ("Frederick Sanger",),
        "year": "1977",
        "journal": "PNAS",
        "category": "genetics",
        "tags": ("sequencing", "sanger", "genomics", "laboratory"),
        "body": (
            "Chain-termination method for DNA sequencing — Human Genome Project and clinical genetic testing depend on sequencing lineage."
        ),
    },
    {
        "id": "hill_randomized_1948",
        "full_name": "Streptomycin Treatment of Pulmonary Tuberculosis — randomized trial report",
        "authors": ("Medical Research Council",),
        "year": "1948",
        "journal": "BMJ",
        "category": "clinical_trial",
        "tags": ("randomized", "trial", "tuberculosis", "streptomycin", "evidence"),
        "body": (
            "Landmark randomized controlled trial design — allocation concealment, follow-up; "
            "template for modern evidence-based medicine and CONSORT reporting."
        ),
    },
    {
        "id": "fleming_penicillin_1929",
        "full_name": "On the Antibacterial Action of Cultures of a Penicillium",
        "authors": ("Alexander Fleming",),
        "year": "1929",
        "journal": "British Journal of Experimental Pathology",
        "category": "infectious",
        "tags": ("antibiotic", "penicillin", "bacteria", "infection"),
        "body": (
            "Penicillium mold inhibits staphylococci — discovery of penicillin; "
            "Florey and Chain scaled production; transformed bacterial infection mortality."
        ),
    },
    {
        "id": "isis2_mi_1988",
        "full_name": "ISIS-2: Randomised trial of intravenous streptokinase, oral aspirin, both, or neither among 17,187 cases of suspected acute myocardial infarction",
        "authors": ("ISIS-2 Collaborative Group",),
        "year": "1988",
        "journal": "Lancet",
        "category": "cardiology",
        "tags": ("heart attack", "aspirin", "strepokinase", "mi", "rct"),
        "body": (
            "Aspirin and streptokinase reduce mortality in acute MI — large factorial RCT; "
            "foundation for acute coronary syndrome dual antiplatelet and reperfusion protocols."
        ),
    },
    {
        "id": "4s_simvastatin_1994",
        "full_name": "Randomised trial of cholesterol lowering in 4444 patients with coronary heart disease (Scandinavian Simvastatin Survival Study — 4S)",
        "authors": ("Scandinavian Simvastatin Survival Study Group",),
        "year": "1994",
        "journal": "Lancet",
        "category": "cardiology",
        "tags": ("statin", "cholesterol", "ldl", "coronary", "rct"),
        "body": (
            "Simvastatin reduces total mortality in CHD — established statin benefit class; "
            "LDL lowering cornerstone of cardiovascular prevention guidelines."
        ),
    },
    {
        "id": "dcct_diabetes_1993",
        "full_name": "The Effect of Intensive Treatment of Diabetes on the Development and Progression of Long-Term Complications in Insulin-Dependent Diabetes Mellitus (DCCT)",
        "authors": ("Diabetes Control and Complications Trial Research Group",),
        "year": "1993",
        "journal": "NEJM",
        "category": "foundations",
        "tags": ("diabetes", "hba1c", "complications", "intensive control"),
        "body": (
            "Intensive glycemic control reduces microvascular complications in type 1 diabetes — "
            "A1c targets individualized per hypoglycemia risk in modern practice."
        ),
    },
    {
        "id": "ninds_tpa_stroke_1995",
        "full_name": "Tissue Plasminogen Activator for Acute Ischemic Stroke (NINDS rt-PA Stroke Study)",
        "authors": ("National Institute of Neurological Disorders and Stroke rt-PA Stroke Study Group",),
        "year": "1995",
        "journal": "NEJM",
        "category": "neurology",
        "tags": ("stroke", "thrombolysis", "tpa", "ischemic"),
        "body": (
            "IV alteplase within 3 hours improves outcomes in ischemic stroke — time-critical reperfusion; "
            "extended windows with imaging selection in current guidelines."
        ),
    },
    {
        "id": "consort_2010",
        "full_name": "CONSORT 2010 Statement — reporting randomized trials",
        "authors": ("CONSORT Group",),
        "year": "2010",
        "journal": "BMJ / PLoS Medicine",
        "category": "methods",
        "tags": ("consort", "reporting", "rct", "methods", "checklist"),
        "body": (
            "Consolidated Standards of Reporting Trials — flow diagram, allocation, blinding, outcomes; "
            "required for credible clinical trial literature appraisal."
        ),
    },
    {
        "id": "prisma_2009",
        "full_name": "PRISMA Statement — preferred reporting items for systematic reviews and meta-analyses",
        "authors": ("PRISMA Group",),
        "year": "2009",
        "journal": "PLoS Medicine",
        "category": "methods",
        "tags": ("prisma", "systematic review", "meta-analysis", "evidence"),
        "body": (
            "Standard for systematic review reporting — search strategy, inclusion, bias assessment, synthesis."
        ),
    },
    {
        "id": "helsinki_2013",
        "full_name": "World Medical Association Declaration of Helsinki — Ethical Principles for Medical Research Involving Human Subjects",
        "authors": ("World Medical Association",),
        "year": "2013",
        "journal": "WMA declaration",
        "category": "ethics",
        "tags": ("helsinki", "ethics", "research", "consent", "irb"),
        "body": (
            "International ethical principles for human subjects research — informed consent, risk-benefit, "
            "vulnerable populations, placebo use; informs IRB and regulatory frameworks globally."
        ),
    },
    {
        "id": "hipaa_privacy_1996",
        "full_name": "Health Insurance Portability and Accountability Act — Privacy Rule",
        "authors": ("United States Congress",),
        "year": "1996",
        "journal": "federal statute",
        "category": "ethics",
        "tags": ("hipaa", "privacy", "phi", "health information"),
        "body": (
            "Protected health information standards in US healthcare — minimum necessary, patient rights, "
            "security safeguards; governs clinical data handling and research de-identification."
        ),
    },
    {
        "id": "who_icd11",
        "full_name": "International Classification of Diseases 11th Revision (ICD-11)",
        "authors": ("World Health Organization",),
        "year": "2019",
        "journal": "WHO reference",
        "category": "foundations",
        "tags": ("icd", "diagnosis", "classification", "who", "coding"),
        "body": (
            "Global diagnostic classification — mortality, morbidity, epidemiology, billing alignment; "
            "successor to ICD-10 with updated mental health and digital health chapters."
        ),
    },
    {
        "id": "acc_aha_chf_2022",
        "full_name": "2022 AHA/ACC/HFSA Guideline for the Management of Heart Failure",
        "authors": ("American Heart Association", "American College of Cardiology"),
        "year": "2022",
        "journal": "Circulation",
        "category": "guideline",
        "tags": ("heart failure", "guideline", "hfref", "hfpef", "gdmt"),
        "body": (
            "Guideline-directed medical therapy for HFrEF: ARNI/ACEi/ARB, beta-blocker, MRA, SGLT2 inhibitor; "
            "HFpEF: comorbidity management, SGLT2; device therapy per EF and QRS."
        ),
    },
    {
        "id": "ada_standards_2024",
        "full_name": "Standards of Care in Diabetes — American Diabetes Association",
        "authors": ("American Diabetes Association",),
        "year": "2024",
        "journal": "Diabetes Care",
        "category": "guideline",
        "tags": ("diabetes", "guideline", "ada", "a1c", "sglt2", "glp1"),
        "body": (
            "Annual standards: diagnosis, glycemic targets, cardiovascular-renal protection with GLP-1 RA and SGLT2, "
            "technology (CGM, pumps), screening complications."
        ),
    },
    {
        "id": "gold_copd_2024",
        "full_name": "Global Initiative for Chronic Obstructive Lung Disease (GOLD) Report",
        "authors": ("GOLD Committee",),
        "year": "2024",
        "journal": "GOLD report",
        "category": "guideline",
        "tags": ("copd", "gold", "spirometry", "bronchodilator"),
        "body": (
            "COPD diagnosis by post-bronchodilator FEV1/FVC < 0.70; ABCD/ABE assessment; "
            "LAMA/LABA/ICS escalation; pulmonary rehab; exacerbation management."
        ),
    },
    {
        "id": "ash_atlas_2021",
        "full_name": "ASH Clinical Practice Guidelines on Venous Thromboembolism",
        "authors": ("American Society of Hematology",),
        "year": "2021",
        "journal": "Blood Advances",
        "category": "guideline",
        "tags": ("dvt", "pe", "anticoagulation", "vte", "hematology"),
        "body": (
            "VTE diagnosis and treatment — DOAC vs warfarin, duration of therapy, cancer-associated thrombosis, "
            "pregnancy-specific guidance."
        ),
    },
    {
        "id": "immunotherapy_checkmate_2015",
        "full_name": "Nivolumab versus Docetaxel in Advanced Nonsquamous Non-Small-Cell Lung Cancer (CheckMate 057)",
        "authors": ("Borghaei et al.",),
        "year": "2015",
        "journal": "NEJM",
        "category": "oncology",
        "tags": ("immunotherapy", "pd1", "nivolumab", "lung cancer", "oncology"),
        "body": (
            "PD-1 checkpoint inhibitor improves survival vs chemotherapy in advanced NSCLC — "
            "immuno-oncology era; biomarker (PD-L1) guides selection."
        ),
    },
    {
        "id": "crispr_sickle_2023",
        "full_name": "Exagamglogene Autotemcel for Severe Sickle Cell Disease (Casgevy clinical basis)",
        "authors": ("Frangoul et al.",),
        "year": "2023",
        "journal": "NEJM",
        "category": "genetics",
        "tags": ("crispr", "sickle cell", "gene therapy", "casgevy"),
        "body": (
            "CRISPR-Cas9 edited autologous HSCT for sickle cell — voxeletor gene reactivation via BCL11A disruption; "
            "first approved CRISPR therapy milestone."
        ),
    },
    {
        "id": "star_d_depression_2006",
        "full_name": "Sequenced Treatment Alternatives to Relieve Depression (STAR*D)",
        "authors": ("Rush et al.",),
        "year": "2006",
        "journal": "American Journal of Psychiatry",
        "category": "psychiatry",
        "tags": ("depression", "ssri", "treatment resistant", "sequential"),
        "body": (
            "Large pragmatic depression trial — remission rates with sequential treatment steps; "
            "informs treatment-resistant depression algorithms and combination therapy."
        ),
    },
    {
        "id": "mRNA_vaccine_fundamentals",
        "full_name": "mRNA vaccines — immunological mechanisms and clinical development",
        "authors": ("Pardi et al.", "Karikó et al."),
        "year": "2018",
        "journal": "Nature Reviews Drug Discovery",
        "category": "infectious",
        "tags": ("mrna", "vaccine", "lipid nanoparticle", "immunology"),
        "body": (
            "Modified nucleosides reduce innate immune activation; LNP delivery; rapid antigen design — "
            "platform used in COVID-19 vaccines and future outbreak response."
        ),
    },
)

SPECIALTY_DOCUMENTS: tuple[dict[str, str | tuple[str, ...]], ...] = (
    {
        "id": "gray_anatomy_reference",
        "full_name": "Gray's Anatomy — descriptive and surgical anatomy reference",
        "authors": ("Henry Gray",),
        "year": "1858",
        "journal": "textbook",
        "category": "foundations",
        "tags": ("anatomy", "textbook", "structure", "surgical"),
        "body": (
            "Comprehensive human anatomy — regional and systemic organization; foundation for surgery, "
            "imaging interpretation, and physical examination."
        ),
    },
    {
        "id": "harrisons_principles",
        "full_name": "Harrison's Principles of Internal Medicine",
        "authors": ("McGraw-Hill Medical",),
        "year": "ongoing",
        "journal": "textbook",
        "category": "foundations",
        "tags": ("internal medicine", "textbook", "diagnosis", "pathophysiology"),
        "body": (
            "Authoritative internal medicine reference — pathophysiology, diagnosis, management across specialties; "
            "used in medical education and clinical reasoning."
        ),
    },
    {
        "id": "cochrane_handbook",
        "full_name": "Cochrane Handbook for Systematic Reviews of Interventions",
        "authors": ("Cochrane Collaboration",),
        "year": "ongoing",
        "journal": "methods reference",
        "category": "methods",
        "tags": ("cochrane", "systematic review", "meta-analysis", "evidence"),
        "body": (
            "Methodological standard for intervention reviews — bias tools, GRADE certainty, "
            "pair with PRISMA for complete evidence synthesis workflow."
        ),
    },
    {
        "id": "pubmed_medline",
        "full_name": "PubMed / MEDLINE — biomedical literature index",
        "authors": ("National Library of Medicine",),
        "year": "ongoing",
        "journal": "database",
        "category": "methods",
        "tags": ("pubmed", "medline", "literature", "search", "database"),
        "body": (
            "Primary index for biomedical papers — MeSH terms, PMID, PMC full text where open access. "
            "Bulk ingest staging: cache/fieldstorage/team_staging/medical_bulk/"
        ),
    },
)


def catalog_count() -> int:
    return len(LANDMARK_PAPERS) + len(SPECIALTY_DOCUMENTS)


def catalog_by_category() -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in (*LANDMARK_PAPERS, *SPECIALTY_DOCUMENTS):
        cat = str(row.get("category", "other"))
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def iter_all_papers() -> Iterator[dict]:
    for row in LANDMARK_PAPERS:
        yield {
            "id": row["id"],
            "full_name": row["full_name"],
            "authors": list(row.get("authors") or ()),
            "year": row.get("year", ""),
            "journal": row.get("journal", ""),
            "category": row.get("category", ""),
            "tags": list(row.get("tags") or ()),
            "body": row.get("body", ""),
            "source": "medical_papers_catalog",
        }
    for row in SPECIALTY_DOCUMENTS:
        yield {
            "id": row["id"],
            "full_name": row["full_name"],
            "authors": list(row.get("authors") or ()),
            "year": row.get("year", ""),
            "journal": row.get("journal", ""),
            "category": row.get("category", ""),
            "tags": list(row.get("tags") or ()),
            "body": row.get("body", ""),
            "source": "medical_documents_catalog",
        }