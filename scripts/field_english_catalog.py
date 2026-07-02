#!/usr/bin/env pythong
"""English lexicon catalog — dictionary sources, phonetics (ARPAbet), orthography seeds."""
from __future__ import annotations

import re
import urllib.request
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "cache" / "fieldstorage" / "team_staging" / "english_bulk"
CMUDICT_NAME = "cmudict-0.7b"
CMUDICT_URL = "https://raw.githubusercontent.com/Alexir/CMUdict/master/cmudict-0.7b"

# Lossless dictionary sources — system paths + staged bulk
DICTIONARY_SOURCES: tuple[dict, ...] = (
    {
        "id": "american_english",
        "title": "American English word list",
        "path": Path("/usr/share/dict/american-english"),
        "locale": "en_US",
        "kind": "orthography",
    },
    {
        "id": "british_english",
        "title": "British English word list",
        "path": Path("/usr/share/dict/british-english"),
        "locale": "en_GB",
        "kind": "orthography",
    },
    {
        "id": "cmudict",
        "title": "CMU Pronouncing Dictionary 0.7b",
        "path": STAGING / CMUDICT_NAME,
        "locale": "en_US",
        "kind": "phonetics_arpabet",
        "url": CMUDICT_URL,
    },
)

# ARPAbet consonants and vowels (CMUdict stress 0/1/2 on vowels)
ARPABET_CONSONANTS = (
    "B", "CH", "D", "DH", "F", "G", "HH", "JH", "K", "L", "M", "N", "NG",
    "P", "R", "S", "SH", "T", "TH", "V", "W", "Y", "Z", "ZH",
)
ARPABET_VOWELS = ("AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW")


def catalog_count() -> int:
    return len(DICTIONARY_SOURCES)


def ensure_cmudict(*, download: bool = True) -> Path | None:
    STAGING.mkdir(parents=True, exist_ok=True)
    dest = STAGING / CMUDICT_NAME
    if dest.is_file() and dest.stat().st_size > 1000:
        return dest
    if not download:
        return None
    try:
        urllib.request.urlretrieve(CMUDICT_URL, dest)
    except OSError:
        return None
    return dest if dest.is_file() else None


def _normalize_word(raw: str) -> str:
    w = raw.strip().lower()
    w = re.sub(r"\(\d+\)$", "", w)
    return w


def _valid_word(w: str) -> bool:
    return bool(w) and len(w) >= 2 and w.replace("'", "").isalpha()


def parse_wordlist(path: Path, *, locale: str, source_id: str) -> Iterator[dict]:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        w = _normalize_word(line)
        if not _valid_word(w):
            continue
        yield {
            "id": f"word_{w}",
            "word": w,
            "locale": locale,
            "source": source_id,
            "phonetic_arpabet": "",
            "tags": ("orthography", "spellcheck"),
        }


def parse_cmudict(path: Path) -> Iterator[dict]:
    if not path.is_file():
        return
    text = path.read_text(encoding="latin-1", errors="replace")
    for line in text.splitlines():
        if not line or line.startswith(";;;"):
            continue
        m = re.match(r"^([A-Za-z'().\d]+)\s+(.+)$", line)
        if not m:
            continue
        raw_word, phones = m.group(1), m.group(2).strip()
        w = _normalize_word(raw_word)
        if not _valid_word(w):
            continue
        variant = ""
        vm = re.search(r"\((\d+)\)$", raw_word)
        if vm:
            variant = vm.group(1)
        entry_id = f"word_{w}" if not variant else f"word_{w}_{variant}"
        yield {
            "id": entry_id,
            "word": w,
            "locale": "en_US",
            "source": "cmudict",
            "phonetic_arpabet": phones,
            "variant": variant,
            "tags": ("phonetics", "arpabet", "pronunciation"),
        }


def iter_all_entries(*, download_cmudict: bool = True) -> Iterator[dict]:
    """Merge dictionary sources — CMUdict phonetics overlay orthography lists."""
    by_word: dict[str, dict] = {}
    pronunciations: dict[str, list[str]] = {}

    cmudict_path = ensure_cmudict(download=download_cmudict)
    if cmudict_path:
        for row in parse_cmudict(cmudict_path):
            w = row["word"]
            ph = row.get("phonetic_arpabet", "")
            if ph:
                pronunciations.setdefault(w, [])
                if ph not in pronunciations[w]:
                    pronunciations[w].append(ph)
            if w not in by_word or ph:
                by_word[w] = {
                    "id": f"word_{w}",
                    "word": w,
                    "locale": row.get("locale", "en_US"),
                    "source": "cmudict",
                    "phonetic_arpabet": ph,
                    "phonetic_variants": pronunciations.get(w, []),
                    "tags": list(row.get("tags") or ()),
                }

    for src in DICTIONARY_SOURCES:
        if src["kind"] != "orthography":
            continue
        path = Path(src["path"])
        for row in parse_wordlist(path, locale=src["locale"], source_id=src["id"]):
            w = row["word"]
            if w in by_word:
                tags = set(by_word[w].get("tags") or ())
                tags.update(row.get("tags") or ())
                tags.add(src["locale"])
                by_word[w]["tags"] = sorted(tags)
                if not by_word[w].get("phonetic_arpabet") and pronunciations.get(w):
                    by_word[w]["phonetic_arpabet"] = pronunciations[w][0]
                    by_word[w]["phonetic_variants"] = pronunciations[w]
                continue
            ph_list = pronunciations.get(w, [])
            by_word[w] = {
                "id": f"word_{w}",
                "word": w,
                "locale": src["locale"],
                "source": src["id"],
                "phonetic_arpabet": ph_list[0] if ph_list else "",
                "phonetic_variants": ph_list,
                "tags": sorted(set(row.get("tags") or ()) | {src["locale"]}),
            }

    for w in sorted(by_word):
        row = by_word[w]
        if row.get("phonetic_variants"):
            row["body"] = (
                f"{w}: ARPAbet /{row['phonetic_arpabet']}/"
                + (
                    f" (alt: {'; '.join(row['phonetic_variants'][1:3])})"
                    if len(row["phonetic_variants"]) > 1
                    else ""
                )
            )
        else:
            row["body"] = f"{w}: orthography (no CMUdict pronunciation indexed)"
        row["full_name"] = w
        row["category"] = "english_lexicon"
        yield row


def catalog_stats() -> dict:
    paths = {str(s["path"]) for s in DICTIONARY_SOURCES}
    return {
        "sources": len(DICTIONARY_SOURCES),
        "paths": sorted(paths),
        "arpabet_consonants": len(ARPABET_CONSONANTS),
        "arpabet_vowels": len(ARPABET_VOWELS),
    }