#!/usr/bin/env pythong
"""Hearing + speech + listening corpus — science, textbooks, GitHub, Hostess7 audio path."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "hearing" / "corpus.json"
CORPUS_VERSION = 1

HEARING_WORKFLOW: tuple[dict[str, str], ...] = (
    {
        "id": "hearing_overview",
        "title": "Hearing in Hostess7",
        "body": (
            "Hearing = listen (STT) + understand (Wernicke) + speak (Broca/TTS). "
            "hostess7_voice.py: arecord + whisper listen; spd-say/edge-tts speak. "
            "CMUdict phonetics in english brain. HOSTESS7_VOICE=1 HOSTESS7_LISTEN=1."
        ),
    },
    {
        "id": "hearing_pipeline",
        "title": "Listen → think → speak pipeline",
        "body": (
            "Mic/text → whisper STT → Language Expert reply → TTS → optional lip-sync Graphics. "
            "Web: /api/listen /api/speak /api/ask. Hearing corpus + H7 library for acoustics/psych."
        ),
    },
    {
        "id": "hearing_lossless",
        "title": "Lossless audio-adjacent storage",
        "body": (
            "Brain JSON FLD1, books H7B, Field WRDT1 — all lossless round-trip. "
            "Phonetic lexicon and textbook text preserve every character on pack/unpack."
        ),
    },
    {
        "id": "hearing_gac1",
        "title": "GAC1 / ZOCRAM1 sovereign audio",
        "body": (
            "Final_Ear GAC1 inside ZOCRAM1 (.zocr) — predictive frames, sealed segments, sovereign time. "
            "Better than naked PCM: provenance weave, cochlear-safe profiles, Shannon entropy per segment. "
            "Queen POST /api/queen-earball action gac1|pack_audio|verify_audio. "
            "Hostess7 bridge: field_final_ear_bridge.py listen → eye_ear_fusion."
        ),
    },
    {
        "id": "hearing_secure_path",
        "title": "Secure neural path — Eye↔Ear",
        "body": (
            "Sovereign time seals every tick; eye↔ear sync never desync (SQUIDGIE on drift). "
            "Signal intel: encoded carriers, mixed interference, deceit composite. "
            "Queen /api/sense-neural analyze + /api/queen-earball secure_identify. "
            "HOSTESS7_FINAL_EAR=1 routes listen_once through secure identify."
        ),
    },
)

HEARING_ENTRIES: tuple[dict[str, Any], ...] = (
    {
        "id": "whisper",
        "title": "OpenAI Whisper",
        "type": "github",
        "tags": ("stt", "speech-recognition", "listen", "open-source"),
        "url": "https://github.com/openai/whisper",
        "paper": "https://arxiv.org/abs/2212.04356",
        "body": "Robust speech recognition — Hostess7 listen_once() via whisper CLI + arecord.",
    },
    {
        "id": "wav2vec2",
        "title": "wav2vec 2.0",
        "type": "paper",
        "tags": ("stt", "self-supervised", "speech"),
        "arxiv": "2006.11477",
        "paper": "https://arxiv.org/abs/2006.11477",
        "url": "https://github.com/facebookresearch/fairseq",
        "body": "Self-supervised speech representations — foundation for modern STT.",
    },
    {
        "id": "speechbrain",
        "title": "SpeechBrain",
        "type": "github",
        "tags": ("stt", "tts", "hearing", "toolkit"),
        "url": "https://github.com/speechbrain/speechbrain",
        "body": "All-in-one speech toolkit — ASR, speaker ID, enhancement, separation.",
    },
    {
        "id": "piper_tts",
        "title": "Piper TTS",
        "type": "github",
        "tags": ("tts", "speak", "fast", "offline"),
        "url": "https://github.com/rhasspy/piper",
        "body": "Fast local neural TTS — low-latency voice for Hostess7 replies.",
    },
    {
        "id": "edge_tts",
        "title": "edge-tts",
        "type": "github",
        "tags": ("tts", "speak", "free"),
        "url": "https://github.com/rany2/edge-tts",
        "body": "Microsoft Edge voices via Python — free high-quality TTS without API key.",
    },
    {
        "id": "kokoro_tts",
        "title": "Kokoro-82M",
        "type": "github",
        "tags": ("tts", "speak", "lightweight"),
        "url": "https://huggingface.co/hexgrad/Kokoro-82M",
        "body": "Compact TTS — used in FasterLivePortrait text-driven video; good Hostess voice.",
    },
    {
        "id": "cmudict",
        "title": "CMU Pronouncing Dictionary",
        "type": "dataset",
        "tags": ("phonetics", "pronunciation", "hearing", "arpabet"),
        "url": "https://github.com/cmusphinx/cmudict",
        "body": "ARPAbet phoneme labels — field_english_lexicon pronunciation lookup.",
    },
    {
        "id": "openstax_hearing_psych",
        "title": "OpenStax Psychology — Hearing",
        "type": "textbook",
        "tags": ("textbook", "free", "psychoacoustics", "ear"),
        "url": "https://openstax.org/books/psychology-2e/pages/5-4-hearing",
        "body": "Free OER — sound waves, ear anatomy, pitch, loudness, localization.",
    },
    {
        "id": "openstax_hearing_physics",
        "title": "OpenStax College Physics — Hearing",
        "type": "textbook",
        "tags": ("textbook", "free", "acoustics", "decibel"),
        "url": "https://openstax.org/books/college-physics-2e/pages/17-6-hearing",
        "body": "Free OER — intensity, decibels, hearing range, ultrasound/infrasound.",
    },
    {
        "id": "understanding_acoustics",
        "title": "Understanding Acoustics",
        "type": "textbook",
        "tags": ("textbook", "free", "acoustics", "oer"),
        "url": "https://library.oapen.org/bitstream/20.500.12657/42912/1/2020_Book_UnderstandingAcoustics.pdf",
        "body": "Open-access acoustics textbook — waves, resonance, rooms, perception.",
    },
    {
        "id": "psychoacoustics_springer",
        "title": "Psychoacoustics (Springer open)",
        "type": "textbook",
        "tags": ("textbook", "psychoacoustics", "perception"),
        "url": "https://link.springer.com/book/10.1007/978-3-030-44787-8",
        "body": "How the brain hears — masking, critical bands, spatial hearing.",
    },
    {
        "id": "webrtc_vad",
        "title": "WebRTC VAD",
        "type": "github",
        "tags": ("vad", "listen", "streaming", "real-time"),
        "url": "https://github.com/wiseman/py-webrtcvad",
        "body": "Voice activity detection — when Owner is speaking vs silence.",
    },
    {
        "id": "silero_vad",
        "title": "Silero VAD",
        "type": "github",
        "tags": ("vad", "listen", "onnx"),
        "url": "https://github.com/snakers4/silero-vad",
        "body": "Lightweight VAD — gate whisper STT to save CPU in live talk.",
    },
    {
        "id": "auditory_scene_analysis",
        "title": "Auditory Scene Analysis",
        "type": "book",
        "tags": ("perception", "cocktail-party", "hearing"),
        "body": "Bregman — how we separate voices in noise; cocktail-party problem for Hostess listen.",
    },
    {
        "id": "asha_hearing",
        "title": "ASHA Hearing & Speech",
        "type": "reference",
        "tags": ("clinical", "audiology", "speech"),
        "url": "https://www.asha.org/public/hearing/",
        "body": "American Speech-Language-Hearing Association — clinical hearing reference.",
    },
    {
        "id": "librosa",
        "title": "librosa",
        "type": "github",
        "tags": ("audio", "analysis", "spectrogram", "python"),
        "url": "https://github.com/librosa/librosa",
        "body": "Audio feature extraction — mel spectrograms for speech/hearing ML.",
    },
    {
        "id": "coqui_tts",
        "title": "Coqui TTS",
        "type": "github",
        "tags": ("tts", "speak", "neural"),
        "url": "https://github.com/coqui-ai/TTS",
        "body": "Neural TTS with voice cloning — optional Hostess custom voice.",
    },
    {
        "id": "gutenberg_sound_music",
        "title": "The Standard Operaglass (music & hearing)",
        "type": "textbook",
        "tags": ("textbook", "free", "music", "children-adjacent"),
        "url": "https://www.gutenberg.org/cache/epub/16225/pg16225.txt",
        "body": "Public-domain music reference — pitch, opera, ear training context for H7 shelf.",
    },
    {
        "id": "gutenberg_child_garden",
        "title": "The Secret Garden",
        "type": "textbook",
        "tags": ("children", "free", "literature", "read-aloud"),
        "url": "https://www.gutenberg.org/cache/epub/113/pg113.txt",
        "body": "Children's classic — read-aloud TTS practice, language + hearing together.",
    },
    {
        "id": "gutenberg_peter_pan",
        "title": "Peter Pan",
        "type": "textbook",
        "tags": ("children", "free", "literature"),
        "url": "https://www.gutenberg.org/cache/epub/16/pg16.txt",
        "body": "Children's classic for Hostess7 library — Owner read-aloud and STT drills.",
    },
    {
        "id": "gutenberg_pinocchio",
        "title": "Pinocchio",
        "type": "textbook",
        "tags": ("children", "free", "literature"),
        "url": "https://www.gutenberg.org/cache/epub/500/pg500.txt",
        "body": "Children's classic — short chapters good for listen/speak sessions.",
    },
    {
        "id": "gutenberg_wind_willows",
        "title": "The Wind in the Willows",
        "type": "textbook",
        "tags": ("children", "free", "literature"),
        "url": "https://www.gutenberg.org/cache/epub/289/pg289.txt",
        "body": "Beloved children's book — rhythm and prosody for TTS tuning.",
    },
    {
        "id": "wikibooks_music",
        "title": "Wikibooks Music",
        "type": "textbook",
        "tags": ("textbook", "free", "music", "hearing"),
        "url": "https://en.wikibooks.org/wiki/Music",
        "body": "Free music theory — ties pitch perception to hearing brain.",
    },
    {
        "id": "hearing_survey_2025",
        "title": "Audio-Driven Facial Animation Survey",
        "type": "survey",
        "tags": ("survey", "audio", "speech", "video"),
        "arxiv": "2403.06421",
        "paper": "https://arxiv.org/abs/2403.06421",
        "url": "https://github.com/zwx8981/ADTH-QA",
        "body": "Perceptual quality metrics for audio-driven video — bridges hearing + live video.",
    },
    {
        "id": "hostess7_listen_env",
        "title": "Hostess7 hearing env",
        "type": "pattern",
        "tags": ("listen", "tts", "hostess7"),
        "body": (
            "HOSTESS7_VOICE=1 speak replies · HOSTESS7_LISTEN=1 whisper capture · "
            "HOSTESS7_WEB=1 browser talk · ./Hostess7.sh hearing-learn"
        ),
    },
)

CURATED_FETCH: tuple[dict[str, str], ...] = (
    {"id": "openstax-hearing-psych", "lane": "hearing", "url": "https://openstax.org/books/psychology-2e/pages/5-4-hearing", "why": "Free hearing psychology"},
    {"id": "openstax-hearing-physics", "lane": "hearing", "url": "https://openstax.org/books/college-physics-2e/pages/17-6-hearing", "why": "Free hearing physics"},
    {"id": "whisper-readme", "lane": "hearing", "url": "https://raw.githubusercontent.com/openai/whisper/main/README.md", "why": "Whisper STT"},
    {"id": "piper-readme", "lane": "hearing", "url": "https://raw.githubusercontent.com/rhasspy/piper/master/README.md", "why": "Piper TTS"},
    {"id": "speechbrain-readme", "lane": "hearing", "url": "https://raw.githubusercontent.com/speechbrain/speechbrain/develop/README.md", "why": "Speech toolkit"},
    {"id": "cmudict-readme", "lane": "hearing", "url": "https://raw.githubusercontent.com/cmusphinx/cmudict/master/README", "why": "Pronunciation dict"},
    {"id": "edge-tts-readme", "lane": "hearing", "url": "https://raw.githubusercontent.com/rany2/edge-tts/master/README.md", "why": "Free TTS"},
    {"id": "arxiv-whisper", "lane": "hearing", "url": "https://arxiv.org/abs/2212.04356", "why": "Whisper paper"},
)


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        doc = {
            "version": CORPUS_VERSION,
            "hearing_workflow": list(HEARING_WORKFLOW),
            "hearing": list(HEARING_ENTRIES),
            "curated_fetch": list(CURATED_FETCH),
            "hostess7_integration": {
                "listen": "hostess7_voice.listen_once — arecord + whisper",
                "speak": "hostess7_voice.speak — spd-say / edge-tts",
                "phonetics": "field_english_lexicon — CMUdict ARPAbet",
                "library": "field_library — free hearing/music/children .H7 books",
                "final_ear_bridge": "field_final_ear_bridge.py — Queen earball + secure identify",
                "gac1": "ZOCRAM1/GAC1 via /api/queen-earball",
                "secure_identify": "eye_ear_fusion under sovereign time",
            },
        }
        CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return CORPUS_CACHE


def search_hearing(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    ensure_corpus()
    q = query.lower()
    tokens = [t for t in re.split(r"\W+", q) if len(t) > 2]
    want_listen = any(t in q for t in ("listen", "hear", "stt", "speech", "whisper", "microphone"))
    want_speak = any(t in q for t in ("speak", "tts", "voice", "talk"))
    scored: list[tuple[int, dict]] = []
    for item in list(HEARING_WORKFLOW) + list(HEARING_ENTRIES):
        tags = item.get("tags", ())
        blob = f"{item.get('title','')} {item.get('body','')} {' '.join(tags)}".lower()
        score = sum(5 if t in blob else 0 for t in tokens)
        if q in blob:
            score += 10
        if want_listen and any(x in tags for x in ("stt", "listen", "vad", "speech-recognition")):
            score += 12
        if want_speak and "tts" in tags:
            score += 12
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1].get("title", "")))
    return [x[1] for x in scored[:limit]]


def synthesize_hearing_paragraphs(query: str) -> list[str]:
    hits = search_hearing(query, limit=6)
    paras = [
        f"Hearing — {len(HEARING_ENTRIES)} sources indexed. "
        "Listen with whisper, speak with TTS, read free textbooks from the H7 shelf.",
    ]
    for h in hits:
        title = h.get("title", "")
        body = str(h.get("body", ""))[:300]
        url = h.get("url") or h.get("paper") or ""
        line = f"{title}: {body}"
        if url:
            line += f" · {url}"
        paras.append(line)
    return paras


def format_registry() -> str:
    lines = ["=== Hearing registry (listen + speak + textbooks) ===", ""]
    for e in HEARING_ENTRIES:
        tags = ", ".join(e.get("tags", ()))
        lines.append(f"· {e['title']} [{e.get('type','')}] — {tags}")
        if e.get("url"):
            lines.append(f"    {e['url']}")
        lines.append(f"    {str(e.get('body',''))[:180]}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ensure_corpus()
    print(format_registry())
    print(f"METRIC hearing_entries={len(HEARING_ENTRIES)}")
    print("OK hearing-corpus")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())