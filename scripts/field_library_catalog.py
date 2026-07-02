#!/usr/bin/env pythong
"""Free books catalog — OER textbooks + STEM/programming/medical for H7 library."""
from __future__ import annotations

from typing import Any, Iterator

from field_k12_catalog import K12_TEXTBOOKS, _enrich  # noqa: E402

FREE_CLASSICS: tuple[dict[str, Any], ...] = (
    {"id": "gutenberg_pride_prejudice", "title": "Pride and Prejudice", "author": "Jane Austen", "category": "literature", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/1342/pg1342.txt"},
    {"id": "gutenberg_alice", "title": "Alice's Adventures in Wonderland", "author": "Lewis Carroll", "category": "literature", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/11/pg11.txt"},
    {"id": "gutenberg_frankenstein", "title": "Frankenstein", "author": "Mary Shelley", "category": "literature", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/84/pg84.txt"},
    {"id": "gutenberg_sherlock_study", "title": "A Study in Scarlet", "author": "Arthur Conan Doyle", "category": "literature", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/244/pg244.txt"},
    {"id": "gutenberg_tom_sawyer", "title": "The Adventures of Tom Sawyer", "author": "Mark Twain", "category": "literature", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/74/pg74.txt"},
    {"id": "gutenberg_art_of_war", "title": "The Art of War", "author": "Sun Tzu", "category": "reference", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/132/pg132.txt"},
    {"id": "gutenberg_declaration", "title": "The Declaration of Independence", "author": "Continental Congress", "category": "civics", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/1/pg1.txt"},
    {"id": "gutenberg_wizard_oz", "title": "The Wonderful Wizard of Oz", "author": "L. Frank Baum", "category": "literature", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/55/pg55.txt"},
)

FREE_PROGRAMMING: tuple[dict[str, Any], ...] = (
    {"id": "gutenberg_flatland", "title": "Flatland", "author": "Edwin A. Abbott", "category": "programming", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/201/pg201.txt"},
    {"id": "gutenberg_symbolic_logic", "title": "Symbolic Logic", "author": "Lewis Carroll", "category": "programming", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/28663/pg28663.txt"},
    {"id": "gutenberg_babbage_economy", "title": "On the Economy of Machinery and Manufactures", "author": "Charles Babbage", "category": "programming", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/42312/pg42312.txt"},
    {"id": "gutenberg_lovelace_notes", "title": "Sketch of the Analytical Engine (Notes by Ada Lovelace)", "author": "Ada Lovelace", "category": "programming", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/3316/pg3316.txt"},
)

FREE_PHYSICS: tuple[dict[str, Any], ...] = (
    {"id": "gutenberg_einstein_relativity", "title": "Relativity: The Special and General Theory", "author": "Albert Einstein", "category": "physics", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/30114/pg30114.txt"},
    {"id": "gutenberg_huygens_light", "title": "Treatise on Light", "author": "Christiaan Huygens", "category": "physics", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/14725/pg14725.txt"},
    {"id": "gutenberg_faraday_candle", "title": "The Chemical History of a Candle", "author": "Michael Faraday", "category": "physics", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/67064/pg67064.txt"},
    {"id": "gutenberg_maxwell_matter", "title": "Matter and Motion", "author": "James Clerk Maxwell", "category": "physics", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/47364/pg47364.txt"},
    {"id": "gutenberg_physics_beginners", "title": "Physics for Beginners", "author": "Various (Gutenberg)", "category": "physics", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/11248/pg11248.txt"},
)

FREE_CHEMISTRY: tuple[dict[str, Any], ...] = (
    {"id": "gutenberg_lavoisier_elements", "title": "Elements of Chemistry", "author": "Antoine Lavoisier", "category": "chemistry", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/30725/pg30725.txt"},
    {"id": "gutenberg_elementary_chemistry", "title": "An Elementary Study of Chemistry", "author": "William G. Mixter", "category": "chemistry", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/28595/pg28595.txt"},
    {"id": "gutenberg_alchemy_chemistry", "title": "The Story of Alchemy and the Beginnings of Chemistry", "author": "M. M. Pattison Muir", "category": "chemistry", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/35692/pg35692.txt"},
    {"id": "gutenberg_chemical_lectures", "title": "Chemical Lectures (1809)", "author": "Humphry Davy", "category": "chemistry", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/71599/pg71599.txt"},
)

FREE_CHILDREN: tuple[dict[str, Any], ...] = (
    {"id": "gutenberg_child_garden", "title": "The Secret Garden", "author": "Frances Hodgson Burnett", "category": "children", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/113/pg113.txt"},
    {"id": "gutenberg_peter_pan", "title": "Peter Pan", "author": "J. M. Barrie", "category": "children", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/16/pg16.txt"},
    {"id": "gutenberg_pinocchio", "title": "The Adventures of Pinocchio", "author": "Carlo Collodi", "category": "children", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/500/pg500.txt"},
    {"id": "gutenberg_wind_willows", "title": "The Wind in the Willows", "author": "Kenneth Grahame", "category": "children", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/289/pg289.txt"},
    {"id": "gutenberg_little_women", "title": "Little Women", "author": "Louisa May Alcott", "category": "children", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/37106/pg37106.txt"},
    {"id": "gutenberg_treasure_island", "title": "Treasure Island", "author": "Robert Louis Stevenson", "category": "children", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/120/pg120.txt"},
)

FREE_BIBLES: tuple[dict[str, Any], ...] = (
    {"id": "gutenberg_bible_kjv", "title": "King James Bible", "author": "Various", "category": "bible", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/10/pg10.txt", "denomination": "Protestant (historic)"},
    {"id": "gutenberg_bible_kjv_complete", "title": "King James Bible (complete alt)", "author": "Various", "category": "bible", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/30/pg30.txt", "denomination": "Protestant (historic)"},
    {"id": "gutenberg_bible_web", "title": "World English Bible", "author": "Various", "category": "bible", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/8294/pg8294.txt", "denomination": "Ecumenical modern English"},
    {"id": "gutenberg_douay_rheims", "title": "Douay-Rheims Bible", "author": "Various", "category": "bible", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/8300/pg8300.txt", "denomination": "Roman Catholic"},
    {"id": "gutenberg_bible_apocrypha", "title": "Deuterocanonical Books (Apocrypha)", "author": "Various", "category": "bible", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/124/pg124.txt", "denomination": "Catholic/Orthodox deuterocanon"},
    {"id": "gutenberg_book_mormon", "title": "Book of Mormon", "author": "Joseph Smith", "category": "bible", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/17/pg17.txt", "denomination": "LDS"},
    {"id": "gutenberg_quran_rodwell", "title": "The Koran (Rodwell)", "author": "Various", "category": "bible", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/2800/pg2800.txt", "denomination": "Islam (translation)"},
    {"id": "gutenberg_paradise_lost", "title": "Paradise Lost", "author": "John Milton", "category": "theology", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/26/pg26.txt", "denomination": "Christian literature"},
    {"id": "gutenberg_divine_comedy", "title": "The Divine Comedy", "author": "Dante Alighieri", "category": "theology", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/100/pg100.txt", "denomination": "Christian literature"},
)

FREE_HEARING: tuple[dict[str, Any], ...] = (
    {"id": "gutenberg_sound_music", "title": "The Standard Operaglass", "author": "Charles Annesley", "category": "hearing", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/16225/pg16225.txt"},
    {"id": "gutenberg_story_of_siegfried", "title": "The Story of Siegfried", "author": "James Baldwin", "category": "children", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/54969/pg54969.txt"},
    {"id": "wikibooks_acoustics", "title": "Wikibooks Acoustics", "author": "Wikibooks contributors", "category": "hearing", "license": "CC-BY-SA", "fetch_url": "https://en.wikibooks.org/wiki/Acoustics"},
)

FREE_MEDICAL: tuple[dict[str, Any], ...] = (
    {"id": "gutenberg_nightingale_nursing", "title": "Notes on Nursing", "author": "Florence Nightingale", "category": "medical", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/1733/pg1733.txt"},
    {"id": "gutenberg_first_aid_manual", "title": "First Aid to the Injured", "author": "St. John Ambulance", "category": "medical", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/26654/pg26654.txt"},
    {"id": "gutenberg_forensic_medicine", "title": "Aids to Forensic Medicine and Toxicology", "author": "W. G. Aitchison Robertson", "category": "medical", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/12330/pg12330.txt"},
    {"id": "gutenberg_hygiene_brain", "title": "Hygiene of the Brain and Nerves", "author": "M. L. Holbrook", "category": "medical", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/44020/pg44020.txt"},
    {"id": "gutenberg_home_treatment", "title": "The Home Medical Library", "author": "Various", "category": "medical", "license": "Public Domain", "fetch_url": "https://www.gutenberg.org/cache/epub/28281/pg28281.txt"},
)

FREE_BOOK_SECTIONS: tuple[tuple[dict[str, Any], ...], ...] = (
    FREE_CLASSICS,
    FREE_CHILDREN,
    FREE_BIBLES,
    FREE_HEARING,
    FREE_PROGRAMMING,
    FREE_PHYSICS,
    FREE_CHEMISTRY,
    FREE_MEDICAL,
)

STEM_CATEGORIES = frozenset({
    "programming", "physics", "chemistry", "medical", "science",
    "computer_science", "math", "health",
})


def _enrich_lib(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("subject") and row.get("grade_band"):
        return _enrich(row)
    out = dict(row)
    out.setdefault("full_name", row.get("title", ""))
    out.setdefault("grade_band", "all")
    out.setdefault("subject", row.get("category", "literature"))
    out.setdefault("publisher", "Project Gutenberg")
    out.setdefault(
        "tags",
        (out.get("category", ""), "free", "h7", "fast", row.get("license", "Public Domain")),
    )
    out.setdefault(
        "body",
        f"Free book — {row.get('title')} · {row.get('author', '')} · {row.get('category', '')}",
    )
    out["source"] = "field_library_catalog"
    return out


def iter_all_library_books() -> Iterator[dict[str, Any]]:
    seen: set[str] = set()
    for row in K12_TEXTBOOKS:
        e = _enrich(row)
        bid = str(e["id"])
        if bid not in seen:
            seen.add(bid)
            yield e
    for section in FREE_BOOK_SECTIONS:
        for row in section:
            e = _enrich_lib(row)
            bid = str(e["id"])
            if bid not in seen:
                seen.add(bid)
                yield e


def iter_stem_books() -> Iterator[dict[str, Any]]:
    for book in iter_all_library_books():
        subj = str(book.get("subject", "")).lower()
        cat = str(book.get("category", "")).lower()
        if subj in STEM_CATEGORIES or cat in STEM_CATEGORIES:
            yield book


def library_count() -> int:
    return sum(1 for _ in iter_all_library_books())


def books_with_fetch_url(*, stem_only: bool = False) -> list[dict[str, Any]]:
    src = iter_stem_books if stem_only else iter_all_library_books
    return [dict(b) for b in src() if b.get("fetch_url")]