#!/usr/bin/env pythong
"""English linguistics domains — orthography, phonetics, morphology, lexicon policy."""
from __future__ import annotations

ENGLISH_CORPUS_VERSION = 2

ENGLISH_DOMAINS: tuple[dict, ...] = (
    {
        "id": "orthography",
        "title": "English orthography & spelling",
        "tags": ("spelling", "orthography", "alphabet", "grapheme", "spellcheck", "dictionary"),
        "body": (
            "English orthography maps phonemes to graphemes with deep historical irregularity — "
            "same sound may spell differently (through, threw, true); same letter varies (rough, dough, through). "
            "Hostess 7 indexes full American and British word lists (~100k+ each) plus merged union for spellcheck. "
            "AmmoText spellcheck loads lossless words_sorted.txt from cache/fieldstorage/brain/english/spell/. "
            "Morphological variants: inflection, compounding, affixation expand recognition beyond bare lemmas."
        ),
    },
    {
        "id": "phonetics_arpabet",
        "title": "ARPAbet phonetics (CMUdict)",
        "tags": ("phonetics", "arpabet", "pronunciation", "cmudict", "phoneme", "stress"),
        "body": (
            "ARPAbet is ASCII phonetic notation used by CMU Pronouncing Dictionary — "
            "consonants (B CH D DH F G HH JH K L M N NG P R S SH T TH V W Y Z ZH) and "
            "vowels (AA AE AH AO AW AY EH ER EY IH IY OW OY UH UW) with stress digits 0/1/2 on vowels. "
            "Example: HELLO → HH AH0 L OW1. Hostess maps lookup queries to indexed pronunciations; "
            "homographs may carry multiple ARPAbet lines (variant numbers in CMUdict)."
        ),
    },
    {
        "id": "phonetics_ipa",
        "title": "IPA & prosody",
        "tags": ("ipa", "international phonetic alphabet", "prosody", "stress", "intonation", "syllable"),
        "body": (
            "International Phonetic Alphabet transcribes sounds across languages — "
            "broad vs narrow transcription, syllable boundaries, primary/secondary stress, tone. "
            "English stress often shifts meaning (REcord vs reCORD). "
            "ARPAbet entries in Hostess brain convert to IPA mentally for linguistics questions; "
            "full IPA tables live in beyond linguistics domain."
        ),
    },
    {
        "id": "morphology",
        "title": "Morphology & word formation",
        "tags": ("morphology", "prefix", "suffix", "lemma", "inflection", "compound", "etymology"),
        "body": (
            "Morphology studies smallest meaningful units: roots, affixes, inflection, derivation. "
            "English compounds (blackbird vs black bird), prefixes (un-, re-, pre-), suffixes (-tion, -ly, -ness). "
            "Lemmatization links inflected forms to dictionary headwords for search and spellcheck."
        ),
    },
    {
        "id": "lexicon_policy",
        "title": "Full English lexicon policy",
        "tags": ("lexicon", "dictionary", "lossless", "infinite", "english", "all words"),
        "body": (
            "Policy: lossless-first English lexicon — json/jsonl shards, search_index.jsonl, plain words_sorted.txt. "
            "Sources: American English, British English, CMUdict ARPAbet. "
            "Ingest: ./Hostess7.sh english-ingest seed · bulk from team_staging/english_bulk/. "
            "Brain path: cache/fieldstorage/brain/english/. "
            "Goal: ALL of English — union orthography + known phonetics; expand with Wiktionary IPA bulk later."
        ),
    },
    {
        "id": "rhetoric_training",
        "title": "Extensive English rhetoric training",
        "tags": ("rhetoric", "metaphor", "thesaurus", "synonym", "sentence", "flow", "prose", "eloquence"),
        "body": (
            "Hostess 7 trains on metaphors (conceptual, extended, simile, personification), "
            "thesaurus discipline (synonyms, antonyms, formal/informal register), "
            "sentence structures (simple, compound, complex, periodic vs loose, parallelism), "
            "and natural language flow (transitions, cohesion, given-new, cadence). "
            "Brain: cache/fieldstorage/brain/english/rhetoric.json · "
            "./Hostess7.sh english-rhetoric · ./Hostess7.sh english-train"
        ),
    },
)