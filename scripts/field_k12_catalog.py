#!/usr/bin/env pythong
"""K-12 textbook catalog — OER, public domain, CC-licensed sources for infinite drive."""
from __future__ import annotations

from typing import Any, Iterator

GRADE_BANDS: tuple[str, ...] = (
    "K", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12",
)

SUBJECTS: tuple[str, ...] = (
    "math", "english_ela", "science", "social_studies", "history", "civics",
    "geography", "art", "music", "health", "computer_science", "foreign_language",
)

# OpenStax, CK-12, Wikibooks, Gutenberg, LibreTexts — fetchable OER only (no pirated PDFs)
K12_TEXTBOOKS: tuple[dict[str, Any], ...] = (
    # ── Mathematics ─────────────────────────────────────────────────────
    {"id": "openstax_prealgebra", "title": "OpenStax Prealgebra 2e", "grade_band": "6-8", "subject": "math", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/prealgebra-2e/pages/1-introduction"},
    {"id": "openstax_elementary_algebra", "title": "OpenStax Elementary Algebra 2e", "grade_band": "9-10", "subject": "math", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/elementary-algebra-2e/pages/1-introduction"},
    {"id": "openstax_algebra", "title": "OpenStax Algebra and Trigonometry 2e", "grade_band": "10-12", "subject": "math", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/algebra-and-trigonometry-2e/pages/1-introduction-to-prerequisites"},
    {"id": "openstax_college_algebra", "title": "OpenStax College Algebra 2e", "grade_band": "11-12", "subject": "math", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/college-algebra-2e/pages/1-prerequisites"},
    {"id": "openstax_precalculus", "title": "OpenStax Precalculus 2e", "grade_band": "11-12", "subject": "math", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/precalculus-2e/pages/1-introduction-to-functions"},
    {"id": "openstax_calculus_vol1", "title": "OpenStax Calculus Volume 1", "grade_band": "12", "subject": "math", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/calculus-volume-1/pages/1-introduction"},
    {"id": "openstax_statistics", "title": "OpenStax Introductory Statistics 2e", "grade_band": "11-12", "subject": "math", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/introductory-statistics-2e/pages/1-sampling-and-data"},
    {"id": "wikibooks_hs_math", "title": "Wikibooks High School Mathematics Extensions", "grade_band": "9-12", "subject": "math", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/High_School_Mathematics_Extensions"},
    {"id": "wikibooks_basic_algebra", "title": "Wikibooks Basic Algebra", "grade_band": "7-9", "subject": "math", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Basic_Algebra"},
    {"id": "gutenberg_first_algebra", "title": "First Lessons in Algebra (Gutenberg)", "grade_band": "7-9", "subject": "math", "publisher": "Project Gutenberg", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/13309/pg13309.txt"},
    # ── Science ─────────────────────────────────────────────────────────
    {"id": "openstax_biology", "title": "OpenStax Biology 2e", "grade_band": "9-12", "subject": "science", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/biology-2e/pages/1-introduction"},
    {"id": "openstax_biology_ap", "title": "OpenStax Biology for AP Courses", "grade_band": "10-12", "subject": "science", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/biology-ap-courses/pages/1-introduction"},
    {"id": "openstax_chemistry", "title": "OpenStax Chemistry 2e", "grade_band": "10-12", "subject": "science", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/chemistry-2e/pages/1-essential-ideas"},
    {"id": "openstax_physics", "title": "OpenStax College Physics 2e", "grade_band": "10-12", "subject": "science", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/college-physics-2e/pages/1-introduction-to-science-and-the-realm-of-physics-physical-quantities-and-units"},
    {"id": "openstax_astronomy", "title": "OpenStax Astronomy 2e", "grade_band": "9-12", "subject": "science", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/astronomy-2e/pages/1-science-and-the-universe-a-brief-introduction"},
    {"id": "openstax_anatomy", "title": "OpenStax Anatomy and Physiology 2e", "grade_band": "11-12", "subject": "science", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/anatomy-and-physiology-2e/pages/1-an-introduction-to-the-human-body"},
    {"id": "openstax_microbiology", "title": "OpenStax Microbiology", "grade_band": "11-12", "subject": "science", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/microbiology/pages/1-introduction"},
    {"id": "wikibooks_hs_physics", "title": "Wikibooks High School Physics", "grade_band": "9-12", "subject": "science", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/High_School_Physics"},
    {"id": "wikibooks_hs_chemistry", "title": "Wikibooks High School Chemistry", "grade_band": "10-12", "subject": "science", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/High_School_Chemistry"},
    {"id": "gutenberg_geology_school", "title": "Text-Book of Geology (Gutenberg)", "grade_band": "9-12", "subject": "science", "publisher": "Project Gutenberg", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/14838/pg14838.txt"},
    # ── English / ELA ───────────────────────────────────────────────────
    {"id": "wikibooks_rhetoric", "title": "Wikibooks Rhetoric and Composition", "grade_band": "9-12", "subject": "english_ela", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Rhetoric_and_Composition"},
    {"id": "wikibooks_poetry", "title": "Wikibooks Poetry", "grade_band": "6-12", "subject": "english_ela", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Poetry"},
    {"id": "openstax_writing_guide", "title": "OpenStax Writing Guide with Handbook", "grade_band": "9-12", "subject": "english_ela", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/writing-guide/pages/1-introduction"},
    {"id": "gutenberg_grammar_land", "title": "Grammar-Land (Gutenberg children's grammar)", "grade_band": "3-6", "subject": "english_ela", "publisher": "Project Gutenberg", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/37134/pg37134.txt"},
    {"id": "gutenberg_mcgruffey_1", "title": "McGuffey's First Eclectic Reader", "grade_band": "K-2", "subject": "english_ela", "publisher": "Project Gutenberg", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/14880/pg14880.txt"},
    {"id": "gutenberg_mcgruffey_2", "title": "McGuffey's Second Eclectic Reader", "grade_band": "2-4", "subject": "english_ela", "publisher": "Project Gutenberg", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/14881/pg14881.txt"},
    # ── Social studies / History / Civics ───────────────────────────────
    {"id": "openstax_us_history", "title": "OpenStax U.S. History", "grade_band": "9-12", "subject": "history", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/us-history/pages/1-the-americas-europe-and-africa-before-1492"},
    {"id": "openstax_world_history_1", "title": "OpenStax World History Volume 1", "grade_band": "9-12", "subject": "history", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/world-history-volume-1/pages/1-introduction"},
    {"id": "openstax_world_history_2", "title": "OpenStax World History Volume 2", "grade_band": "10-12", "subject": "history", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/world-history-volume-2/pages/1-introduction"},
    {"id": "openstax_am_gov", "title": "OpenStax American Government 3e", "grade_band": "9-12", "subject": "civics", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/american-government-3e/pages/1-american-government-and-civic-engagement"},
    {"id": "wikibooks_us_history", "title": "Wikibooks US History", "grade_band": "6-12", "subject": "history", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/US_History"},
    {"id": "wikibooks_world_history", "title": "Wikibooks World History", "grade_band": "6-12", "subject": "history", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/World_History"},
    {"id": "gutenberg_civics_manual", "title": "Elementary Civics (Gutenberg)", "grade_band": "4-6", "subject": "civics", "publisher": "Project Gutenberg", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/31516/pg31516.txt"},
    # ── Geography ───────────────────────────────────────────────────────
    {"id": "wikibooks_world_geography", "title": "Wikibooks World Regional Geography", "grade_band": "6-12", "subject": "geography", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/World_Regional_Geography"},
    {"id": "gutenberg_physical_geo", "title": "Physical Geography (Gutenberg)", "grade_band": "9-12", "subject": "geography", "publisher": "Project Gutenberg", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/71806/pg71806.txt"},
    # ── Health ──────────────────────────────────────────────────────────
    {"id": "openstax_health", "title": "OpenStax Health", "grade_band": "9-12", "subject": "health", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/health/pages/1-introduction"},
    {"id": "wikibooks_sex_ed", "title": "Wikibooks Sexual Health", "grade_band": "9-12", "subject": "health", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Sexual_Health"},
    # ── Computer science ────────────────────────────────────────────────
    {"id": "openstax_cs", "title": "OpenStax Introduction to Computer Science", "grade_band": "9-12", "subject": "computer_science", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/introduction-computer-science/pages/1-introduction"},
    {"id": "wikibooks_python", "title": "Wikibooks Python Programming", "grade_band": "9-12", "subject": "computer_science", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Python_Programming"},
    {"id": "wikibooks_cs", "title": "Wikibooks Computer Science", "grade_band": "9-12", "subject": "computer_science", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Computer_Science"},
    # ── Art / Music ─────────────────────────────────────────────────────
    {"id": "wikibooks_art_history", "title": "Wikibooks Art History", "grade_band": "9-12", "subject": "art", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Art_History"},
    {"id": "wikibooks_music", "title": "Wikibooks Music Theory", "grade_band": "6-12", "subject": "music", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Music_Theory"},
    # ── Foreign language ────────────────────────────────────────────────
    {"id": "wikibooks_spanish", "title": "Wikibooks Spanish", "grade_band": "6-12", "subject": "foreign_language", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Spanish"},
    {"id": "wikibooks_french", "title": "Wikibooks French", "grade_band": "6-12", "subject": "foreign_language", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/French"},
    # ── Elementary cross-subject (CK-12 / Wikibooks) ────────────────────
    {"id": "wikibooks_elem_science", "title": "Wikibooks General Science", "grade_band": "K-5", "subject": "science", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/General_Science"},
    {"id": "wikibooks_elem_math", "title": "Wikibooks Mathematics K-12", "grade_band": "K-8", "subject": "math", "publisher": "Wikibooks", "license": "CC BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Mathematics"},
    {"id": "gutenberg_arithmetic", "title": "First Book in Arithmetic (Gutenberg)", "grade_band": "1-3", "subject": "math", "publisher": "Project Gutenberg", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/33106/pg33106.txt"},
    {"id": "openstax_psychology", "title": "OpenStax Psychology 2e", "grade_band": "11-12", "subject": "social_studies", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/psychology-2e/pages/1-introduction-to-psychology"},
    {"id": "openstax_sociology", "title": "OpenStax Introduction to Sociology 3e", "grade_band": "11-12", "subject": "social_studies", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/introduction-sociology-3e/pages/1-introduction-to-sociology"},
    {"id": "openstax_economics", "title": "OpenStax Principles of Economics 3e", "grade_band": "11-12", "subject": "social_studies", "publisher": "OpenStax", "license": "CC BY 4.0", "fetch_url": "https://openstax.org/books/principles-economics-3e/pages/1-welcome-to-economics"},
)


def _enrich(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    out.setdefault("full_name", row.get("title", ""))
    out.setdefault("tags", (row.get("subject", ""), row.get("grade_band", ""), "k12", "textbook", row.get("publisher", "").lower()))
    out.setdefault(
        "body",
        f"K-12 textbook — {row.get('title')} · grades {row.get('grade_band')} · {row.get('subject')} · "
        f"{row.get('publisher')} · {row.get('license', 'OER')}.",
    )
    out["source"] = "field_k12_catalog"
    out["journal"] = "textbook"
    out["category"] = row.get("subject", "general")
    return out


def iter_all_textbooks() -> Iterator[dict[str, Any]]:
    for row in K12_TEXTBOOKS:
        yield _enrich(row)


def catalog_count() -> int:
    return len(K12_TEXTBOOKS)


def catalog_by_grade() -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in K12_TEXTBOOKS:
        g = str(row.get("grade_band", "?"))
        counts[g] = counts.get(g, 0) + 1
    return counts


def catalog_by_subject() -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in K12_TEXTBOOKS:
        s = str(row.get("subject", "?"))
        counts[s] = counts.get(s, 0) + 1
    return counts


def textbooks_with_fetch_url() -> list[dict[str, Any]]:
    return [dict(r) for r in K12_TEXTBOOKS if r.get("fetch_url")]