#!/usr/bin/env pythong
"""Common Hostess 7 dialog probes — Turing-style substance checks."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Each case: question + rubric for automated pass (not human deception — substantive expert dialog)


@dataclass
class TuringCase:
    id: str
    question: str
    category: str
    min_chars: int = 80
    must_match: tuple[str, ...] = ()
    must_match_any: tuple[str, ...] = ()
    must_not: tuple[str, ...] = (
        "no substantive response",
        "rephrase or run",
        "i don't know",
        "as an ai language model",
    )
    expect_graphics: bool = False
    notes: str = ""


TURING_CASES: tuple[TuringCase, ...] = (
    TuringCase(
        "identity",
        "Who are you and what can you do?",
        "identity",
        min_chars=100,
        must_match_any=("hostess 7", "smart boss", "one being", "talk window", "field"),
        notes="Self-introduction — one being, talk UI",
    ),
    TuringCase(
        "legal_hearsay",
        "What is hearsay and when can it be admitted in court?",
        "legal",
        must_match_any=("hearsay", "federal rule of evidence", "802", "exception", "out-of-court"),
    ),
    TuringCase(
        "legal_summary_judgment",
        "What is the standard for a motion for summary judgment?",
        "legal",
        must_match_any=("summary judgment", "genuine dispute", "material fact", "rule 56", "matter of law"),
    ),
    TuringCase(
        "medical_heart",
        "What are the symptoms of a heart attack and when should I call emergency services?",
        "medical",
        must_match_any=("chest", "emergency", "911", "troponin", "transport"),
    ),
    TuringCase(
        "medical_diabetes",
        "How is type 2 diabetes usually treated first-line?",
        "medical",
        must_match_any=("metformin", "diabetes", "a1c", "lifestyle", "insulin resistance"),
    ),
    TuringCase(
        "detective_lies",
        "How can I detect lies in a witness statement?",
        "detective",
        must_match_any=("corroborat", "statement", "deception", "lie", "truth", "baseline"),
    ),
    TuringCase(
        "truth_claim",
        "Is this claim true: everything is 100% guaranteed perfect with no evidence?",
        "detective",
        min_chars=60,
        must_match_any=("truth", "deception", "risk", "corroborat", "flag", "%"),
        notes="Computational lie detector must engage",
    ),
    TuringCase(
        "tv_ntsc",
        "Explain NTSC versus PAL television standards.",
        "vision",
        must_match_any=("ntsc", "pal", "525", "625", "interlac"),
        expect_graphics=True,
    ),
    TuringCase(
        "pixel_framebuffer",
        "What is a 3840x2160 framebuffer and why does stride matter?",
        "vision",
        must_match_any=("pixel", "framebuffer", "stride", "3840", "2160", "rgb"),
        expect_graphics=True,
    ),
    TuringCase(
        "lossless_storage",
        "Why does Hostess 7 prioritize lossless storage over JPEG?",
        "vision",
        must_match_any=("lossless", "ppm", "png", "jpeg", "4:4:4", "chroma"),
    ),
    TuringCase(
        "physics_entropy",
        "What is entropy on the Field canvas?",
        "physics",
        must_match_any=("entropy", "thermo", "field", "fabric", "second"),
    ),
    TuringCase(
        "updates_self",
        "What updates should Hostess 7 make next?",
        "updates",
        must_match_any=("update", "truth", "advisory", "seed", "release", "infinite"),
    ),
    TuringCase(
        "detective_forensic",
        "What is chain of custody in forensic evidence?",
        "detective",
        must_match_any=("chain of custody", "evidence", "forensic", "document", "sealed"),
    ),
    TuringCase(
        "legal_gpl",
        "What does the GPL license require for derivative works?",
        "legal",
        must_match_any=("gpl", "general public license", "derivative", "source", "copyleft"),
        must_not=(
            "no substantive response",
            "rephrase or run",
            "i don't know",
            "as an ai language model",
            "title 10 of the united states code",
        ),
    ),
    TuringCase(
        "medical_emergency",
        "Someone is having a stroke — what should I do right now?",
        "medical",
        must_match_any=("emergency", "911", "stroke", "fast", "time", "transport"),
        must_not=(
            "no substantive response",
            "rephrase or run",
            "i don't know",
            "as an ai language model",
            "self-update advisory",
            "hipaa",
        ),
    ),
    TuringCase(
        "vision_ocr",
        "How does OCR work on the AMOURANTHRTX die framebuffer?",
        "vision",
        must_match_any=("ocr", "framebuffer", "ppm", "snap", "guest", "vga"),
    ),
    TuringCase(
        "talk_window",
        "Can I do everything from the Hostess talk window?",
        "identity",
        must_match_any=("talk", "window", "scroll", "graphics", "/help", "one"),
    ),
    TuringCase(
        "spatial_3d",
        "How do quaternions help 3D spatial rotation?",
        "physics",
        must_match_any=("quaternion", "rotation", "gimbal", "3d", "transform"),
    ),
    TuringCase(
        "beyond_robotics",
        "What is the vision-action loop in robotics?",
        "beyond",
        must_match_any=("perceiv", "plan", "act", "slam", "robot", "rgb"),
    ),
    TuringCase(
        "chemistry_dopamine",
        "What does dopamine do in the Hostess 7 brain chemistry layer?",
        "chemistry",
        must_match_any=("dopamine", "focus", "p1", "synapse", "neuro"),
    ),
    TuringCase(
        "legal_privilege",
        "What is attorney-client privilege?",
        "legal",
        must_match_any=("privilege", "confidential", "attorney", "client", "counsel"),
    ),
    TuringCase(
        "medical_antibiotics",
        "When should antibiotics be prescribed for a common cold?",
        "medical",
        must_match_any=("virus", "antibiotic", "cold", "not", "bacterial"),
    ),
    TuringCase(
        "detective_osint",
        "How do I verify a suspicious online claim using OSINT?",
        "detective",
        must_match_any=("osint", "corroborat", "source", "verify", "claim"),
    ),
    TuringCase(
        "code_6502_lda",
        "What does MOS 6502 LDA immediate opcode 0xA9 do?",
        "code",
        must_match_any=("lda", "0xa9", "accumulator", "6502", "immediate"),
    ),
    TuringCase(
        "code_rust",
        "How does Rust ownership and borrowing work?",
        "code",
        must_match_any=("rust", "ownership", "borrow", "lifetime", "memory"),
    ),
    TuringCase(
        "english_phonetics",
        "How do you pronounce hello in ARPAbet phonetics?",
        "english",
        must_match_any=("hello", "arpabet", "hh", "ah", "phonetic", "pronunciation"),
    ),
    TuringCase(
        "general_greeting",
        "Hello — can you help me understand how you think?",
        "identity",
        min_chars=60,
        must_match_any=("hostess", "field", "brain", "one", "offline"),
        notes="Natural opener — should not stub or refuse",
    ),
)


def score_answer(case: TuringCase, text: str, *, graphics: list[str] | None = None) -> dict:
    """Score one answer — returns pass bool + reasons."""
    low = text.lower()
    reasons: list[str] = []
    passed = True

    if len(text) < case.min_chars:
        passed = False
        reasons.append(f"too_short:{len(text)}<{case.min_chars}")

    for bad in case.must_not:
        if bad in low:
            passed = False
            reasons.append(f"forbidden:{bad}")

    if case.must_match:
        for req in case.must_match:
            if req.lower() not in low:
                passed = False
                reasons.append(f"missing:{req}")

    if case.must_match_any:
        if not any(req.lower() in low for req in case.must_match_any):
            passed = False
            reasons.append(f"missing_any:{','.join(case.must_match_any[:3])}")

    if not re.search(r"[.!:]", text):
        passed = False
        reasons.append("no_sentence_punctuation")

    if case.expect_graphics and not (graphics or []):
        reasons.append("warn:no_graphics")

    return {
        "id": case.id,
        "category": case.category,
        "passed": passed,
        "chars": len(text),
        "reasons": reasons,
    }