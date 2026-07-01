#!/usr/bin/env pythong
"""QA: Full English lexicon — dictionaries, phonetics, spell export."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_english_infinite import WORDS_SORTED, lookup_word  # noqa: E402
from field_english_lexicon import corpus_stats, ensure_corpus, search_english, synthesize_english_paragraphs  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    stats = corpus_stats()

    if stats["word_count"] < 100_000:
        return fail(f"expected 100k+ words, got {stats['word_count']}")
    if stats["phonetic_count"] < 50_000:
        return fail(f"expected 50k+ phonetic entries, got {stats['phonetic_count']}")
    if stats["spell_words"] < 100_000:
        return fail(f"expected 100k+ spell words, got {stats['spell_words']}")
    if not WORDS_SORTED.is_file():
        return fail(f"spell word list missing: {WORDS_SORTED}")

    hello = lookup_word("hello")
    if not hello or "HH" not in str(hello.get("phonetic_arpabet", "")):
        return fail("hello pronunciation missing ARPAbet")

    world = lookup_word("world")
    if not world or not world.get("phonetic_arpabet"):
        return fail("world pronunciation missing")

    for probe in ("beautiful", "through", "jurisdiction"):
        if not lookup_word(probe):
            return fail(f"common dictionary word not indexed: {probe}")

    paras = synthesize_english_paragraphs("How do you pronounce hello in ARPAbet?")
    text = " ".join(paras).lower()
    if "arpabet" not in text and "hh" not in text:
        return fail("phonetics synthesis missing ARPAbet")

    ortho = synthesize_english_paragraphs("English orthography and spellcheck dictionary")
    if len(" ".join(ortho)) < 120:
        return fail("orthography synthesis too short")

    print(f"OK english lexicon words={stats['word_count']} phonetic={stats['phonetic_count']}")
    print(f"METRIC english_words={stats['word_count']}")
    print(f"METRIC english_phonetic={stats['phonetic_count']}")
    print(f"METRIC english_spell_words={stats['spell_words']}")
    print(f"METRIC english_spell_path={WORDS_SORTED}")
    print("METRIC qa_english_lexicon=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())