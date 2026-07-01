#!/usr/bin/env pythong
"""Exploring Speaking X — phonetics, dictionary, thesaurus, teaching for every language ever."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
LIBRARY = INSTALL / "library" / "dewey"
SHELF = LIBRARY / "400-education"
DOCTRINE = INSTALL / "data" / "exploring-speaking-doctrine.json"
CATALOG = INSTALL / "data" / "exploring-speaking-languages-catalog.json"
SEEDS = INSTALL / "data" / "exploring-speaking-seeds.json"
HIEROGLYPHICS = INSTALL / "data" / "exploring-speaking-hieroglyphics.json"
SKIP_COVER = os.environ.get("FIELD_SKIP_COVER", "1") == "1"
FAST_PACK = os.environ.get("FIELD_SPEAKING_FAST", "1") == "1"

FAMILY_HINTS: dict[str, str] = {
    "eng": "Indo-European · Germanic",
    "deu": "Indo-European · Germanic",
    "fra": "Indo-European · Romance",
    "spa": "Indo-European · Romance",
    "ita": "Indo-European · Romance",
    "por": "Indo-European · Romance",
    "rus": "Indo-European · Slavic",
    "pol": "Indo-European · Slavic",
    "hin": "Indo-European · Indo-Aryan",
    "san": "Indo-European · Indo-Aryan",
    "jpn": "Japonic",
    "kor": "Koreanic",
    "zho": "Sino-Tibetan · Sinitic",
    "ara": "Afro-Asiatic · Semitic",
    "heb": "Afro-Asiatic · Semitic",
    "swa": "Niger-Congo · Bantu",
    "yor": "Niger-Congo",
    "vie": "Austroasiatic",
    "tha": "Tai-Kadai",
    "fin": "Uralic",
    "hun": "Uralic",
    "tur": "Turkic",
    "mon": "Mongolic",
    "lat": "Indo-European · Italic (ancient)",
    "grc": "Indo-European · Hellenic (historical)",
    "sux": "Language isolate (ancient Mesopotamia)",
    "egy": "Afro-Asiatic · Egyptian (ancient)",
    "got": "Indo-European · Germanic (ancient)",
    "epo": "Constructed (Esperanto)",
}

SCRIPT_HINTS: dict[str, str] = {
    "ara": "Arabic",
    "heb": "Hebrew",
    "jpn": "Kanji + Hiragana + Katakana",
    "kor": "Hangul",
    "zho": "Han",
    "rus": "Cyrillic",
    "ukr": "Cyrillic",
    "bul": "Cyrillic",
    "ell": "Greek",
    "grc": "Greek",
    "hin": "Devanagari",
    "ben": "Bengali",
    "tam": "Tamil",
    "tha": "Thai",
    "kat": "Georgian",
    "arm": "Armenian",
    "sux": "Cuneiform",
    "egy": "Hieroglyphic / hieratic",
    "got": "Gothic",
    "lat": "Latin",
}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(INSTALL))
    except ValueError:
        return str(path)


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _import_h7c() -> Any:
    path = INSTALL / "lib" / "field-h7c-compression.py"
    spec = importlib.util.spec_from_file_location("field_h7c", path)
    if not spec or not spec.loader:
        raise ImportError("field-h7c-compression.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return s[:48] or "language"


def _table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(lines)


def _section(title: str, body: str) -> str:
    return f"\n## {title}\n\n{body.strip()}\n"


def _bullet(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items)


def _status_label(lang_type: str) -> str:
    return {
        "living": "Living",
        "extinct": "Extinct",
        "ancient": "Ancient",
        "historical": "Historical",
        "constructed": "Constructed",
        "special": "Special",
    }.get(lang_type, lang_type.title())


def _cefr_path(status: str) -> list[tuple[str, str]]:
    base = [
        ("A1", "Survival — greetings, yes/no, numbers, core nouns (water, person)"),
        ("A2", "Routine — family, food, directions, simple past/future"),
        ("B1", "Independent — opinions, work, school, narrate experiences"),
        ("B2", "Fluent argument — abstract topics, nuance, register switching"),
        ("C1", "Proficient — idioms, rhetoric, specialized domains"),
        ("C2", "Mastery — literary/historical texts, reconstruction (ancient/extinct)"),
    ]
    if status in ("ancient", "historical", "extinct"):
        return [
            ("A1", "Script awareness — alphabet/syllabary, sound inventory, hello/goodbye reconstructions"),
            ("A2", "Core lexicon — 200 high-frequency lemmas with IPA + gloss"),
            ("B1", "Grammar sketch — noun/verb classes, basic syntax, period context"),
            ("B2", "Primary texts — graded excerpts with interlinear gloss"),
            ("C1", "Philology — manuscripts, sound changes, cognate webs"),
            ("C2", "Scholarly fluency — edit texts, debate reconstructions, teach AI retrieval"),
        ]
    return base


def _fallback_lemmas(lang: dict[str, Any], seeds: dict[str, Any]) -> list[dict[str, Any]]:
    code = lang["iso6393"]
    native = lang["name"]
    rows: list[dict[str, Any]] = []
    for item in seeds.get("universal_lemmas") or []:
        en = item["lemma_en"]
        ipa = f"/{en}/"
        rows.append({
            "lemma": f"[{en}]",
            "ipa": ipa,
            "pos": item.get("pos", "—"),
            "gloss": item.get("gloss", en),
            "register": item.get("register", "neutral"),
            "note": f"Seed pending native form — gloss via English pivot for {native}",
        })
    if not rows:
        rows.append({
            "lemma": "(pending)",
            "ipa": "—",
            "pos": "—",
            "gloss": f"Core lexicon for {native}",
            "register": "neutral",
            "note": "Expand via field corpus",
        })
    return rows


def _lemma_rows(lemmas: list[dict[str, Any]]) -> list[list[str]]:
    rows: list[list[str]] = []
    for item in lemmas:
        row = [
            item.get("lemma", "—"),
            item.get("ipa", "—"),
            item.get("pos", "—"),
            item.get("gloss", "—"),
            item.get("register", "neutral"),
        ]
        if item.get("romanization"):
            row[0] = f"{row[0]} ({item['romanization']})"
        rows.append(row)
    return rows


def _hieroglyph_lang_codes(hiero: dict[str, Any]) -> frozenset[str]:
    return frozenset(hiero.get("hieroglyph_lang_codes") or ())


def _hieroglyph_translation_section(
    lang: dict[str, Any],
    *,
    seed_lang: dict[str, Any],
    hiero: dict[str, Any],
) -> str | None:
    code = lang["iso6393"]
    codes = _hieroglyph_lang_codes(hiero)
    script = str(seed_lang.get("script") or SCRIPT_HINTS.get(code, ""))
    logographic = (
        code in codes
        or "hieroglyph" in script.lower()
        or "cuneiform" in script.lower()
        or "anatolian hieroglyph" in script.lower()
    )
    if not logographic and lang.get("type") not in ("ancient", "historical", "extinct"):
        return None

    parts: list[str] = [
        "Glyph → transliteration → IPA → English gloss. One row per attested sign or word.",
        "AI keys: `glyph`, `gardiner`, `translit`, `ipa`, `gloss_en`, `period`, `register`.",
        "",
    ]

    if code == "egy" or "egyptian" in lang["name"].lower():
        parts.append("### Egyptian periods")
        parts.append(_table(
            ["Period", "Script"],
            [[p["label"], p["script"]] for p in (hiero.get("egyptian_periods") or [])],
        ))
        parts.append("")
        parts.append("### Uniliteral signs (phonetic values)")
        parts.append(_table(
            ["Glyph", "Gardiner", "Value", "IPA", "Gloss"],
            [[s["glyph"], s["gardiner"], s["value"], s["ipa"], s["gloss"]]
             for s in (hiero.get("unilateral_signs") or [])[:16]],
        ))
        parts.append("")
        parts.append("### Core word translations")
        parts.append(_table(
            ["Glyphs", "Transliteration", "IPA", "POS", "English"],
            [[w["glyphs"], w["translit"], w["ipa"], w["pos"], w["gloss"]]
             for w in (hiero.get("core_words") or [])],
        ))
    elif seed_lang.get("lemmas"):
        parts.append("### Attested signs / words")
        parts.append(_table(
            ["Glyph", "Transliteration", "IPA", "POS", "English"],
            [[x.get("lemma", "—"), x.get("romanization", "—"), x.get("ipa", "—"),
              x.get("pos", "—"), x.get("gloss", "—")]
             for x in seed_lang.get("lemmas") or []],
        ))
    else:
        parts.append(
            f"Logographic or ancient script attestation for **{lang['name']}** — "
            "populate from corpus; use interlinear glossing (IGT) standard."
        )

    parts.append("")
    parts.append("### Translation method")
    parts.append(_bullet(hiero.get("translation_method") or [
        "Segment signs; separate phonetic from determinative.",
        "Transliterate; reconstruct pronunciation where unwritten.",
        "Gloss to English; mark damaged/uncertain with […] and (?).",
    ]))
    return "\n".join(parts)


def _thesaurus_section(seed_lang: dict[str, Any] | None, status: str) -> str:
    clusters = (seed_lang or {}).get("thesaurus") or []
    if not clusters:
        return _bullet([
            "**Greeting** — formal / informal / archaic registers (populate from corpus)",
            "**Affirmation** — yes / certainly / yeah / archaic aye",
            "**Negation** — no / not / never / prohibitive particles",
            "**Size** — big / large / vast / diminutive",
            "**Motion** — go / come / arrive / depart / hasten",
            f"Status **{status}** — prefer literary attestations and cognate webs for extinct/ancient lanes.",
        ])
    parts: list[str] = []
    for cluster in clusters:
        sense = cluster.get("sense", "sense")
        lines = [f"### {sense.title()}"]
        for key in ("formal", "informal", "slang", "archaic", "literary"):
            vals = cluster.get(key)
            if vals:
                lines.append(f"- **{key}:** {', '.join(vals)}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def build_speaking_manual(
    lang: dict[str, Any],
    *,
    seeds: dict[str, Any] | None = None,
    hiero: dict[str, Any] | None = None,
) -> str:
    """One book per language: Exploring Speaking {name} — phonetics, dictionary, thesaurus, teaching."""
    seeds = seeds or _load(SEEDS, {})
    hiero = hiero or _load(HIEROGLYPHICS, {})
    code = lang["iso6393"]
    name = lang["name"]
    status = _status_label(lang.get("type", "living"))
    seed_lang = (seeds.get("languages") or {}).get(code) or {}
    family = seed_lang.get("family") or FAMILY_HINTS.get(code, "See comparative linguistics corpora")
    script = seed_lang.get("script") or SCRIPT_HINTS.get(code, "Latin (romanization default)")
    native = seed_lang.get("native", name)
    iso1 = lang.get("iso6391") or "—"
    iso2 = lang.get("iso6392B") or lang.get("iso6392T") or code

    lines = [
        f"# Exploring Speaking {name}",
        "",
        "![Cover](h7fig:cover)" if not SKIP_COVER else "",
        "",
        f"**Exploring Speaking {name}** — this language's own book (one per language, X = {name}).",
        f"Phonetics, dictionary, thesaurus, hieroglyphics/script translation, and teaching pedagogy",
        f"for **{name}** ({native}). Built for human learners and **AI retrieval** (lemma · ipa · pos · register).",
        "",
        f"- **Book id:** `exploring_speaking_{code}`",
        f"- **ISO 639-3:** `{code}` · **639-1:** `{iso1}` · **639-2:** `{iso2}`",
        f"- **Status:** {status}",
        f"- **Family:** {family}",
        f"- **Script:** {script}",
        f"- **Updated:** {_now()}",
        "",
    ]
    if seed_lang.get("status_note"):
        lines.append(f"- **Note:** {seed_lang['status_note']}")
        lines.append("")

    lines.extend(["---", ""])

    phonology = seed_lang.get("phonology") or (
        f"Inventory varies by dialect and period. For **{status.lower()}** languages, use reconstructed "
        f"phonology where attested; mark uncertain segments with (?) in IPA."
    )
    ipa_note = seed_lang.get("ipa_chart_note", "Use IPA (International Phonetic Alphabet) for all lemmas below.")
    lines.append(_section("1. Phonetics & pronunciation", "\n".join([
        _bullet([
            f"**Sound system:** {phonology}",
            f"**Notation:** {ipa_note}",
            "**Stress:** language-specific — mark primary stress with ˈ before the syllable.",
            "**Tone:** mark with Chao tone letters or diacritics where applicable.",
            "**AI key:** `phoneme`, `ipa`, `stress_pattern`, `romanization`, `script_glyph`",
        ]),
        "",
        "### IPA consonant & vowel reference (universal)",
        "",
        _table(
            ["Class", "IPA symbols", "Teaching hook"],
            [
                ["Plosives", "p b t d k ɡ", "Hold airflow, then release"],
                ["Fricatives", "f v s z ʃ ʒ h", "Continuous turbulence"],
                ["Nasals", "m n ŋ", "Air through nose"],
                ["Vowels", "i e ɛ a ɔ o u ə", "Tongue height + backness"],
            ],
        ),
    ])))

    lemmas = seed_lang.get("lemmas") or _fallback_lemmas(lang, seeds)
    lines.append(_section(
        "2. Dictionary — core lemmas",
        "\n".join([
            "High-frequency lemmas with IPA, part of speech, English gloss, and register.",
            "AI agents: index each row as `lemma` + `ipa` + `pos` + `register` + `gloss_en`.",
            "",
            _table(["Lemma", "IPA", "POS", "Gloss (EN)", "Register"], _lemma_rows(lemmas)),
            "",
            "### Lemma JSON (AI retrieval)",
            "",
            "```json",
            json.dumps([
                {
                    "lemma": x.get("lemma"),
                    "ipa": x.get("ipa"),
                    "pos": x.get("pos"),
                    "register": x.get("register"),
                    "gloss_en": x.get("gloss"),
                    "iso6393": code,
                    "status": lang.get("type"),
                }
                for x in lemmas[:12]
            ], ensure_ascii=False, indent=2),
            "```",
        ]),
    ))

    lines.append(_section("3. Thesaurus — register & synonyms", _thesaurus_section(seed_lang, status)))

    hiero_body = _hieroglyph_translation_section(lang, seed_lang=seed_lang, hiero=hiero)
    if hiero_body:
        lines.append(_section("4. Hieroglyphics & script translation", hiero_body))
        teach_num = 5
        ai_num = 6
        pair_num = 7
    else:
        teach_num = 4
        ai_num = 5
        pair_num = 6

    cefr = _cefr_path(lang.get("type", "living"))
    lines.append(_section(
        f"{teach_num}. Teaching languages — pedagogy",
        "\n".join([
            "CEFR-aligned path for operators and AI tutors. Pair with Hostess 7 hearing/speech lanes.",
            "",
            _table(["Level", "Competency"], list(cefr)),
            "",
            _bullet([
                "**Listen → repeat → contrast** — minimal pairs for phoneme discrimination",
                "**Glossed reading** — interlinear texts for ancient/extinct lanes",
                "**Register drills** — formal vs informal thesaurus clusters",
                "**Spaced retrieval** — dictionary lemmas recycled across sessions",
                f"**Status {status}** — adjust expectations: living = conversation; extinct/ancient = philology + reconstruction",
            ]),
        ]),
    ))

    lines.append(_section(
        f"{ai_num}. AI retrieval keys",
        _bullet([
            f"`book_id` = `exploring_speaking_{code}`",
            f"`title` = `Exploring Speaking {name}`",
            f"`iso6393` = `{code}`",
            f"`language_name` = `{name}`",
            f"`status` = `{lang.get('type', 'living')}`",
            f"`family` = `{family}`",
            f"`script` = `{script}`",
            "`lemma`, `ipa`, `pos`, `register`, `gloss_en` — per dictionary row",
            "`glyph`, `gardiner`, `translit` — per hieroglyphic row",
            "`thesaurus_sense`, `register_band` — per synonym cluster",
            "`cefr_level` — per teaching milestone",
            f"Shelf: `library/dewey/400-education/exploring_speaking_{code}/`",
            "Reader: `/field-lang-manuals` (Speaking tab)",
        ]),
    ))

    lines.append(_section(
        f"{pair_num}. Pair with other Exploring books",
        "\n".join([
            "- **Explaining** programming manuals — `000-computer-science/explaining_*` (code languages)",
            "- **Exploring** subject manuals — vehicles, biology, history, combat",
            f"- **This book** — natural/spoken language lane: **Exploring Speaking {name}**",
        ]),
    ))

    return "\n".join(line for line in lines if line is not None) + "\n"


def pack_speaking_h7(lang: dict[str, Any], text: str) -> Path:
    h7c = _import_h7c()
    code = lang["iso6393"]
    name = lang["name"]
    book_id = f"exploring_speaking_{code}"
    book_dir = SHELF / book_id
    book_dir.mkdir(parents=True, exist_ok=True)
    h7c_path = book_dir / f"{book_id}.h7c"
    meta = {
        "id": book_id,
        "title": f"Exploring Speaking {name}",
        "author": "AmmoOS Field Library",
        "license": "Field",
        "subject": "language — phonetics, dictionary, thesaurus, teaching",
        "category": "language",
        "dewey": "400",
        "iso6393": code,
        "language_status": lang.get("type", "living"),
        "book_kind": "exploring",
        "speaking_lane": True,
        "uploaded": _now(),
        "reader": "NEXUS_H7C",
    }
    figures: dict[str, Any] = {}
    if not SKIP_COVER:
        cover = INSTALL / "data" / "combinatronic-visuals" / "books" / f"{book_id}.png"
        if cover.is_file():
            figures["cover"] = {
                "path": cover,
                "alt": f"Exploring Speaking {name}",
                "mime": "image/png",
                "plate_key": "cover",
                "accent": (72, 130, 180),
            }
    packed = h7c.pack_h7c(text, meta, use_optimizer=not FAST_PACK, format_version=3, figures=figures or None)
    h7c_path.write_bytes(packed)
    ein = "H7C-SPEAK-" + hashlib.sha256(text.encode()).hexdigest()[:12]
    book_json = {
        "id": book_id,
        "title": f"Exploring Speaking {name}",
        "author": "AmmoOS Field Library",
        "dewey": "400",
        "dewey_label": "Language",
        "ein": ein,
        "format": "h7c",
        "format_version": 3,
        "book_kind": "exploring",
        "speaking_lane": True,
        "iso6393": code,
        "iso6391": lang.get("iso6391") or "",
        "language_name": name,
        "language_status": lang.get("type", "living"),
        "embedded_figures": ["cover"] if figures else [],
        "manual_reader": "/field-lang-manuals",
        "h7c": _rel(h7c_path),
        "field_path": _rel(h7c_path),
        "github_shelf": "400-education",
        "updated": _now(),
    }
    (book_dir / "book.json").write_text(json.dumps(book_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return h7c_path


def generate_speaking_book(lang: dict[str, Any], *, seeds: dict[str, Any] | None = None) -> dict[str, Any]:
    seeds = seeds or _load(SEEDS, {})
    text = build_speaking_manual(lang, seeds=seeds)
    h7c_path = pack_speaking_h7(lang, text)
    return {
        "ok": True,
        "iso6393": lang["iso6393"],
        "name": lang["name"],
        "book_id": f"exploring_speaking_{lang['iso6393']}",
        "title": f"Exploring Speaking {lang['name']}",
        "h7c_path": str(h7c_path),
        "char_count": len(text),
        "status": lang.get("type"),
    }


def _catalog_langs(*, include_special: bool = False) -> list[dict[str, Any]]:
    doc = _load(CATALOG, {})
    skip = set(_load(DOCTRINE, {}).get("skip_scope") or ["special"])
    langs = []
    for lang in doc.get("languages") or []:
        if not include_special and lang.get("scope") in skip:
            continue
        if not include_special and lang.get("type") in skip:
            continue
        langs.append(lang)
    return langs


def _rebuild_index() -> int:
    index_path = SHELF / "speaking-index.jsonl"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for book_json in sorted(SHELF.glob("exploring_speaking_*/book.json")):
        try:
            doc = json.loads(book_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        rows.append({
            "id": doc.get("id"),
            "title": doc.get("title"),
            "iso6393": doc.get("iso6393"),
            "status": doc.get("language_status"),
            "h7c": doc.get("h7c"),
            "updated": doc.get("updated"),
        })
    index_path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return len(rows)


def _update_shelf_summary(count: int) -> None:
    shelf_json = SHELF / "shelf.json"
    doc = _load(shelf_json, {})
    doc.update({
        "schema": "dewey-shelf/v1",
        "shelf": "400-education",
        "code": "400",
        "title": "Language",
        "updated": _now(),
        "format_primary": "h7c",
        "speaking_lane": True,
        "speaking_index": "library/dewey/400-education/speaking-index.jsonl",
        "exploring_speaking_count": count,
        "book_count": count + sum(
            1 for b in (doc.get("books") or []) if not str(b.get("id", "")).startswith("exploring_speaking_")
        ),
    })
    shelf_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ensure_speaking_books(
    *,
    limit: int | None = None,
    codes: list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    seeds = _load(SEEDS, {})
    langs = _catalog_langs()
    if codes:
        want = {c.lower() for c in codes}
        langs = [l for l in langs if l["iso6393"] in want]
    if limit:
        langs = langs[:limit]
    created: list[str] = []
    skipped: list[str] = []
    errors: list[dict[str, Any]] = []
    for lang in langs:
        code = lang["iso6393"]
        book_dir = SHELF / f"exploring_speaking_{code}"
        if not force and (book_dir / "book.json").is_file():
            skipped.append(code)
            continue
        try:
            rep = generate_speaking_book(lang, seeds=seeds)
            if rep.get("ok"):
                created.append(code)
            else:
                errors.append({"iso6393": code, "error": rep.get("error")})
        except Exception as exc:
            errors.append({"iso6393": code, "error": type(exc).__name__})
    total = _rebuild_index()
    _update_shelf_summary(total)
    try:
        import importlib.util
        panel_py = INSTALL / "lib" / "hostess7-library-panel.py"
        if panel_py.is_file():
            spec = importlib.util.spec_from_file_location("h7_lib_panel", panel_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "publish_panel"):
                    mod.publish_panel()
    except Exception:
        pass
    return {
        "ok": not errors,
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "created_count": len(created),
        "total_speaking_books": total,
        "catalog_count": len(langs),
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Exploring Speaking X — every language ever")
    ap.add_argument("cmd", nargs="?", default="ensure", choices=["ensure", "one", "preview", "count"])
    ap.add_argument("--code", action="append", help="ISO 639-3 code(s)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.cmd == "count":
        langs = _catalog_langs()
        rep = {
            "catalog": len(langs),
            "on_disk": len(list(SHELF.glob("exploring_speaking_*/book.json"))),
            "types": {},
        }
        for lang in langs:
            t = lang.get("type", "?")
            rep["types"][t] = rep["types"].get(t, 0) + 1
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "preview":
        langs = _catalog_langs()
        code = (args.code or ["eng"])[0].lower()
        hit = next((l for l in langs if l["iso6393"] == code), langs[0])
        print(build_speaking_manual(hit)[:6000])
        return 0

    if args.cmd == "one":
        langs = _catalog_langs()
        code = (args.code or ["eng"])[0].lower()
        hit = next((l for l in langs if l["iso6393"] == code), None)
        if not hit:
            print(json.dumps({"ok": False, "error": "code_not_in_catalog", "code": code}, indent=2))
            return 1
        rep = generate_speaking_book(hit)
        if args.json:
            print(json.dumps(rep, ensure_ascii=False, indent=2))
        else:
            print(f"Exploring Speaking {hit['name']}: {rep.get('h7c_path')}")
        return 0

    rep = ensure_speaking_books(limit=args.limit, codes=args.code, force=args.force)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(
            f"exploring-speaking: created={rep.get('created_count')} "
            f"skipped={len(rep.get('skipped') or [])} total={rep.get('total_speaking_books')}"
        )
    return 0 if rep.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())