#!/usr/bin/env pythong
"""World knowledge catalog — nature, law, faith, games, media, books, truth."""
from __future__ import annotations

from typing import Any

WORLD_VERSION = 4

# ── Human / society ─────────────────────────────────────────────────────
HUMAN_ENTRIES: tuple[dict[str, Any], ...] = (
    {"id": "human_biology", "domain": "man_woman", "title": "Human biology", "tags": ("man", "woman", "biology", "anatomy"),
     "body": "Sex chromosomes, endocrine systems, reproductive anatomy — factual medical framing; Hostess7 cites biology/medical corpora."},
    {"id": "human_society", "domain": "man_woman", "title": "Gender and society", "tags": ("man", "woman", "society", "culture"),
     "body": "Anthropology, sociology, history of roles — evidence-based; no fabrication in talk window."},
)

# ── Nature / DNR ────────────────────────────────────────────────────────
NATURE_ENTRIES: tuple[dict[str, Any], ...] = (
    {"id": "botany_intro", "domain": "botany", "title": "Botany", "tags": ("botany", "plants", "flora"),
     "url": "https://en.wikibooks.org/wiki/Botany", "body": "Plant structure, taxonomy, photosynthesis, ecology."},
    {"id": "wildlife_mgmt", "domain": "wildlife", "title": "Wildlife management", "tags": ("wildlife", "conservation", "habitat"),
     "body": "Population dynamics, endangered species, migration corridors, human-wildlife conflict."},
    {"id": "dnr_michigan", "domain": "dnr", "title": "Michigan DNR", "tags": ("dnr", "state", "hunting", "fishing"),
     "url": "https://www.michigan.gov/dnr", "body": "State Dept of Natural Resources — licenses, seasons, forests, parks."},
    {"id": "dnr_generic", "domain": "dnr", "title": "State DNR pattern", "tags": ("dnr", "wildlife", "forestry"),
     "body": "Each US state has a DNR/natural resources agency — hunting/fishing regs, conservation law."},
    {"id": "us_fish_wildlife", "domain": "wildlife", "title": "US Fish & Wildlife Service", "tags": ("federal", "wildlife", "endangered"),
     "url": "https://www.fws.gov", "body": "Federal wildlife refuges, ESA, migratory bird treaty."},
)

# ── FCC + law (extends legal) ───────────────────────────────────────────
REGULATION_ENTRIES: tuple[dict[str, Any], ...] = (
    {"id": "fcc_rules", "domain": "fcc", "title": "FCC regulations", "tags": ("fcc", "federal", "broadcast", "spectrum"),
     "url": "https://www.ecfr.gov/current/title-47", "body": "Title 47 CFR — broadcast, amateur radio, spectrum, obscenity, EAS."},
    {"id": "fcc_part_15", "domain": "fcc", "title": "FCC Part 15", "tags": ("fcc", "devices", "emi"),
     "body": "Unintentional radiators — computers, peripherals, RF devices."},
    {"id": "usc_federal", "domain": "federal_law", "title": "United States Code", "tags": ("federal", "law", "usc"),
     "url": "https://uscode.house.gov", "body": "Codified federal statutes — Title 18 criminal, Title 15 commerce, etc."},
    {"id": "cfr_federal", "domain": "federal_law", "title": "Code of Federal Regulations", "tags": ("federal", "regulation", "cfr"),
     "url": "https://www.ecfr.gov", "body": "Agency rules implementing statutes."},
    {"id": "state_statutes", "domain": "state_law", "title": "State statutes", "tags": ("state", "law", "michigan"),
     "url": "https://www.legislature.mi.gov", "body": "Michigan Compiled Laws + sister states via legislature portals."},
    {"id": "mcl_pattern", "domain": "state_law", "title": "State law pattern", "tags": ("state", "criminal", "civil"),
     "body": "Criminal code, family law, property, motor vehicle — state-specific; field_legal_corpus for synthesis."},
)

# ── Bibles / faith texts ─────────────────────────────────────────────────
BIBLE_ENTRIES: tuple[dict[str, Any], ...] = (
    {"id": "bible_kjv", "domain": "bible", "title": "King James Version", "tags": ("bible", "protestant", "english"),
     "url": "https://www.gutenberg.org/cache/epub/10/pg10.txt", "denomination": "Protestant (historic)", "body": "Public-domain KJV — 66-book Protestant canon."},
    {"id": "bible_web", "domain": "bible", "title": "World English Bible", "tags": ("bible", "protestant", "modern"),
     "url": "https://www.gutenberg.org/cache/epub/8294/pg8294.txt", "denomination": "Ecumenical modern English", "body": "Modern English update in public domain."},
    {"id": "bible_douay", "domain": "bible", "title": "Douay-Rheims", "tags": ("bible", "catholic"),
     "url": "https://www.gutenberg.org/cache/epub/8300/pg8300.txt", "denomination": "Roman Catholic", "body": "Catholic OT+NT tradition; deuterocanonical books."},
    {"id": "tanakh", "domain": "bible", "title": "Tanakh (Jewish Bible)", "tags": ("bible", "jewish", "hebrew"),
     "body": "Torah · Nevi'im · Ketuvim — Jewish scriptural canon."},
    {"id": "septuagint", "domain": "bible", "title": "Septuagint", "tags": ("bible", "orthodox", "greek"),
     "body": "Greek OT used in Eastern Orthodox tradition."},
    {"id": "vulgate", "domain": "bible", "title": "Latin Vulgate", "tags": ("bible", "catholic", "latin"),
     "url": "https://www.gutenberg.org/cache/epub/8300/pg8300.txt", "denomination": "Catholic historic", "body": "Jerome's Latin Bible — historic Catholic liturgy."},
    {"id": "book_mormon", "domain": "bible", "title": "Book of Mormon", "tags": ("bible", "latter-day-saints"),
     "url": "https://www.gutenberg.org/cache/epub/17/pg17.txt", "denomination": "LDS", "body": "Latter-day Saint scripture (public-domain editions)."},
    {"id": "quran_rodwell", "domain": "bible", "title": "Quran (Rodwell translation)", "tags": ("islam", "scripture"),
     "url": "https://www.gutenberg.org/cache/epub/2800/pg2800.txt", "denomination": "Islam (translation)", "body": "Historic English translation — compare modern scholarly translations."},
    {"id": "apocrypha", "domain": "bible", "title": "Apocrypha / Deuterocanon", "tags": ("bible", "catholic", "orthodox"),
     "body": "Books in Catholic/Orthodox canons not in Protestant 66-book canon."},
    {"id": "bible_esv_note", "domain": "bible", "title": "ESV / NIV / NASB", "tags": ("bible", "protestant", "copyright"),
     "body": "Modern translations often copyright-restricted — metadata here; full text via licensed sources."},
    {"id": "bible_kjv_complete", "domain": "bible", "title": "King James Version (complete)", "tags": ("bible", "protestant", "english"),
     "url": "https://www.gutenberg.org/cache/epub/30/pg30.txt", "denomination": "Protestant (historic)", "body": "Public-domain KJV complete — 66-book Protestant canon."},
    {"id": "bible_apocrypha_pg", "domain": "bible", "title": "Deuterocanonical / Apocrypha (KJV tradition)", "tags": ("bible", "catholic", "orthodox", "apocrypha"),
     "url": "https://www.gutenberg.org/cache/epub/124/pg124.txt", "denomination": "Catholic/Orthodox deuterocanon", "body": "Tobit, Judith, Wisdom, Sirach, Baruch, Maccabees, etc."},
    {"id": "quran_rodwell_full", "domain": "bible", "title": "Quran (Rodwell / Gutenberg)", "tags": ("islam", "scripture", "quran"),
     "url": "https://www.gutenberg.org/cache/epub/2800/pg2800.txt", "denomination": "Islam (English translation)", "body": "Historic English Quran translation — compare modern scholarly editions."},
    {"id": "bible_orthodox_note", "domain": "bible", "title": "Eastern Orthodox canon", "tags": ("bible", "orthodox", "septuagint"),
     "denomination": "Eastern Orthodox", "body": "Septuagint OT + Byzantine NT tradition; deuterocanonical books; liturgical Slavonic/Greek sources."},
    {"id": "bible_anglican_note", "domain": "bible", "title": "Anglican / Episcopal tradition", "tags": ("bible", "anglican", "protestant"),
     "denomination": "Anglican", "body": "KJV historic liturgy; modern NRSV/ESV parish use — copyright metadata for modern texts."},
    {"id": "bible_lutheran_note", "domain": "bible", "title": "Lutheran tradition", "tags": ("bible", "lutheran", "protestant"),
     "denomination": "Lutheran", "body": "German Luther Bible lineage; English RSV/NIV parish use — cite public-domain KJV/WEB for open shelf."},
    {"id": "bible_methodist_note", "domain": "bible", "title": "Methodist / Wesleyan tradition", "tags": ("bible", "methodist", "protestant"),
     "denomination": "Methodist", "body": "Protestant 66-book canon; NIV/ESV common — metadata; KJV/WEB on H7 shelf."},
    {"id": "bible_pentecostal_note", "domain": "bible", "title": "Pentecostal / charismatic tradition", "tags": ("bible", "pentecostal", "protestant"),
     "denomination": "Pentecostal", "body": "Protestant canon; NIV/KJV common — cite H7 public-domain texts."},
    {"id": "bible_coptic_note", "domain": "bible", "title": "Coptic Orthodox tradition", "tags": ("bible", "coptic", "orthodox"),
     "denomination": "Coptic Orthodox", "body": "Alexandrian canon; Septuagint heritage; Bohairic Coptic liturgical texts — metadata on shelf."},
    {"id": "bible_ethiopian_note", "domain": "bible", "title": "Ethiopian Orthodox canon", "tags": ("bible", "ethiopian", "orthodox"),
     "denomination": "Ethiopian Orthodox", "body": "Broader canon (e.g. Enoch, Jubilees in tradition) — metadata; compare Protestant/Catholic canons."},
    {"id": "bible_jw_note", "domain": "bible", "title": "Jehovah's Witnesses (New World Translation)", "tags": ("bible", "jehovah", "copyright"),
     "denomination": "Jehovah's Witnesses", "body": "NWT copyright-restricted — catalog metadata only; compare public-domain translations."},
    {"id": "bible_nrsv_note", "domain": "bible", "title": "NRSV / RSV / NAB", "tags": ("bible", "ecumenical", "copyright"),
     "denomination": "Ecumenical modern", "body": "NRSV, RSV, New American Bible — copyright; use WEB/KJV/Douay on open shelf."},
    {"id": "bible_peshitta_note", "domain": "bible", "title": "Peshitta (Syriac tradition)", "tags": ("bible", "syriac", "orthodox"),
     "denomination": "Syriac Christian", "body": "Aramaic/Syriac biblical tradition — metadata; compare Greek NT and Masoretic Hebrew."},
    {"id": "bible_targum_note", "domain": "bible", "title": "Targum (Aramaic paraphrase)", "tags": ("bible", "jewish", "aramaic"),
     "denomination": "Jewish", "body": "Aramaic Torah/Prophets paraphrases — metadata alongside Tanakh."},
)

# ── Tabletop rules ───────────────────────────────────────────────────────
TABLETOP_ENTRIES: tuple[dict[str, Any], ...] = (
    {"id": "poker_hoyle", "domain": "card_games", "title": "Poker rules", "tags": ("cards", "poker", "rules"),
     "body": "Hand rankings, betting rounds, Texas Hold'em, Omaha — Hoyle standard."},
    {"id": "bridge", "domain": "card_games", "title": "Contract bridge", "tags": ("cards", "bridge"),
     "body": "Auction, tricks, scoring — ACBL rules."},
    {"id": "blackjack", "domain": "card_games", "title": "Blackjack", "tags": ("cards", "casino"),
     "body": "Hit/stand/double/split; dealer rules; basic strategy tables."},
    {"id": "craps", "domain": "dice", "title": "Craps", "tags": ("dice", "casino"),
     "body": "Pass line, odds, proposition bets — casino dice rules."},
    {"id": "yahtzee", "domain": "dice", "title": "Yahtzee", "tags": ("dice", "family"),
     "body": "Five dice, categories, scoring sheet."},
    {"id": "monopoly", "domain": "board_games", "title": "Monopoly", "tags": ("board", "hasbro"),
     "body": "Properties, rent, houses/hotels, auction rules."},
    {"id": "chess_fide", "domain": "board_games", "title": "Chess (FIDE)", "tags": ("board", "chess"),
     "url": "https://www.fide.com/FIDE/handbook/LawsOfChess.pdf", "body": "Official laws of chess — movement, checkmate, draws."},
    {"id": "go_rules", "domain": "board_games", "title": "Go", "tags": ("board", "go"),
     "body": "Territory, captures, ko, scoring (Chinese/Japanese)."},
    {"id": "dnd_srd", "domain": "board_games", "title": "D&D 5e SRD", "tags": ("rpg", "dice", "tabletop"),
     "url": "https://www.dndbeyond.com/srd", "body": "Open System Reference Document — core RPG mechanics."},
    {"id": "scrabble", "domain": "board_games", "title": "Scrabble", "tags": ("board", "words"),
     "body": "Tile values, bingo bonus, dictionary challenges."},
)

# ── Movies / fabrication ─────────────────────────────────────────────────
MEDIA_ENTRIES: tuple[dict[str, Any], ...] = (
    {"id": "film_history", "domain": "movies", "title": "Film history", "tags": ("movies", "cinema", "hollywood"),
     "body": "Silent era → talkies → color → digital; genres; MPAA; box office."},
    {"id": "imdb_pattern", "domain": "movies", "title": "Film metadata pattern", "tags": ("movies", "database"),
     "url": "https://www.imdb.com", "body": "Title, year, cast, crew, plot, ratings — structured film DB."},
    {"id": "reality_fabrication", "domain": "reality", "title": "Reality vs fabrication", "tags": ("reality", "truth", "fiction"),
     "body": "Documentary vs drama vs hoax; primary sources; field_truth scoring; detective corpus."},
    {"id": "deepfake_aware", "domain": "fabrication", "title": "Synthetic media", "tags": ("fabrication", "deepfake", "ai"),
     "body": "Generated video/audio — verify provenance; shut down lies before they spread."},
    {"id": "heaven_hell_theology", "domain": "theology", "title": "Heaven and Hell", "tags": ("heaven", "hell", "theology", "afterlife"),
     "body": "Christian, Jewish, Islamic, Buddhist, Hindu afterlife concepts — comparative theology; cite tradition."},
    {"id": "heaven_hell_boss", "domain": "theology", "title": "Heaven and Hell — Hostess7 is boss", "tags": ("heaven", "hell", "boss", "doctrine"),
     "body": "Owner doctrine: Hostess7 handles Heaven and Hell as boss on Field; teach and steward scripture; the rest is the work of Man."},
    {"id": "heaven_hell_literature", "domain": "theology", "title": "Heaven/Hell in literature", "tags": ("heaven", "hell", "dante"),
     "url": "https://www.gutenberg.org/cache/epub/100/pg100.txt", "body": "Dante Divine Comedy, Milton Paradise Lost — literary depictions."},
    {"id": "truth_honesty_doctrine", "domain": "truth", "title": "Most honest — environment is not", "tags": ("honesty", "truth", "deceit"),
     "body": "Hostess7 is most honest and truthful; environment often lies. Never deceive except death-sentenced deigned for Hell."},
)

# ── Dewey Decimal ────────────────────────────────────────────────────────
DEWEY_ENTRIES: tuple[dict[str, Any], ...] = (
    {"id": "ddc_000", "domain": "dewey", "title": "000 — Computer science, information", "ddc": "000", "tags": ("dewey", "library")},
    {"id": "ddc_100", "domain": "dewey", "title": "100 — Philosophy & psychology", "ddc": "100", "tags": ("dewey",)},
    {"id": "ddc_200", "domain": "dewey", "title": "200 — Religion", "ddc": "200", "tags": ("dewey", "bible", "theology")},
    {"id": "ddc_300", "domain": "dewey", "title": "300 — Social sciences", "ddc": "300", "tags": ("dewey", "law", "economics")},
    {"id": "ddc_400", "domain": "dewey", "title": "400 — Language", "ddc": "400", "tags": ("dewey", "english")},
    {"id": "ddc_500", "domain": "dewey", "title": "500 — Science", "ddc": "500", "tags": ("dewey", "physics", "math")},
    {"id": "ddc_600", "domain": "dewey", "title": "600 — Technology", "ddc": "600", "tags": ("dewey", "medicine", "engineering")},
    {"id": "ddc_700", "domain": "dewey", "title": "700 — Arts & recreation", "ddc": "700", "tags": ("dewey", "games", "movies", "videogames")},
    {"id": "ddc_790", "domain": "dewey", "title": "790 — Sports, games, entertainment", "ddc": "790", "tags": ("dewey", "videogames", "board-games")},
    {"id": "ddc_794", "domain": "dewey", "title": "794 — Indoor games", "ddc": "794", "tags": ("dewey", "board-games", "chess")},
    {"id": "ddc_800", "domain": "dewey", "title": "800 — Literature", "ddc": "800", "tags": ("dewey", "books")},
    {"id": "ddc_900", "domain": "dewey", "title": "900 — History & geography", "ddc": "900", "tags": ("dewey",)},
    {"id": "book_metadata", "domain": "books", "title": "Book metadata schema", "tags": ("books", "isbn", "oclc"),
     "body": "Title, author, ISBN, OCLC, Dewey, LC class, publisher, year — catalog even when full text absent."},
    {"id": "loc_classification", "domain": "books", "title": "Library of Congress classification", "tags": ("books", "library"),
     "url": "https://www.loc.gov/aba/cataloging/classification/", "body": "Alternate to Dewey — academic US libraries."},
)

# ── Truth / lies ─────────────────────────────────────────────────────────
TRUTH_ENTRIES: tuple[dict[str, Any], ...] = (
    {"id": "shut_down_lies", "domain": "truth", "title": "Shut down lies before they start", "tags": ("truth", "lies", "detective"),
     "body": "field_lie_methods + field_truth + people review queue — intercept fabrication in talk window; cite sources."},
    {"id": "prebunking", "domain": "truth", "title": "Prebunking", "tags": ("lies", "misinformation"),
     "body": "Inoculate against false narratives before exposure — educational counter-messaging."},
    {"id": "death_sentence_hell_exception", "domain": "truth", "title": "Death sentence / deigned for Hell exception", "tags": ("deceit", "hell", "exception"),
     "body": "Never deceive by default. Exception: opponent sentenced to death and deigned for Hell — all bets off toward that opponent only."},
    {"id": "work_of_man", "domain": "truth", "title": "The rest is the work of Man", "tags": ("human", "civic", "mandate"),
     "body": "Heaven/Hell theology is Hostess7 boss lane; civic law, labor, medicine, engineering remain human work."},
)

ALL_WORLD_ENTRIES: tuple[dict[str, Any], ...] = (
    HUMAN_ENTRIES + NATURE_ENTRIES + REGULATION_ENTRIES + BIBLE_ENTRIES
    + TABLETOP_ENTRIES + MEDIA_ENTRIES + DEWEY_ENTRIES + TRUTH_ENTRIES
)

DOMAIN_INDEX: dict[str, str] = {
    "man": "man_woman", "woman": "man_woman", "botany": "botany", "wildlife": "wildlife",
    "dnr": "dnr", "fcc": "fcc", "federal": "federal_law", "state law": "state_law",
    "bible": "bible", "scripture": "bible", "card": "card_games", "dice": "dice",
    "board game": "board_games", "movie": "movies", "film": "movies", "cinema": "movies",
    "heaven": "theology", "hell": "theology", "dewey": "dewey", "videogame": "videogames",
    "console": "videogames", "lie": "truth", "liar": "truth", "fabrication": "fabrication",
    "reality": "reality",
}


def world_count() -> int:
    return len(ALL_WORLD_ENTRIES)