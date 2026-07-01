#!/usr/bin/env pythong
"""QA: Code brain — ISA opcodes + programming languages."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from field_code_corpus import corpus_stats, ensure_corpus, search_code, synthesize_code_paragraphs  # noqa: E402
from field_code_infinite import lookup_language, lookup_opcode  # noqa: E402


def fail(msg: str) -> int:
    print(f"FAIL {msg}", file=sys.stderr)
    return 1


def main() -> int:
    ensure_corpus()
    stats = corpus_stats()

    if stats["opcodes"] < 800:
        return fail(f"expected 800+ opcodes, got {stats['opcodes']}")
    if stats["languages"] < 50:
        return fail(f"expected 50+ languages, got {stats['languages']}")
    if stats["chips"] < 15:
        return fail(f"expected 15+ chip ISAs, got {stats['chips']}")

    lda = lookup_opcode("mos6502", "LDA")
    if not lda or not any("0xA9" in str(r.get("opcode", "")) for r in lda):
        return fail("6502 LDA opcode missing")

    mov = lookup_opcode("x86_16", "MOV")
    if not mov:
        return fail("x86 MOV missing")

    rust = lookup_language("rust")
    if not rust or "ownership" not in str(rust.get("body", "")).lower():
        return fail("Rust language entry missing ownership")

    py = lookup_language("python")
    if not py:
        return fail("Python language entry missing")

    asm_para = synthesize_code_paragraphs("What does 6502 opcode LDA immediate do?")
    if "lda" not in " ".join(asm_para).lower():
        return fail("6502 synthesis missing LDA")

    lang_para = synthesize_code_paragraphs("Explain Rust ownership and borrowing")
    text = " ".join(lang_para).lower()
    if "rust" not in text or "borrow" not in text:
        return fail("Rust synthesis weak")

    chips_hits = search_code("MIPS ADD instruction PS1", limit=5)
    if not chips_hits:
        return fail("MIPS search empty")

    print(f"OK code corpus opcodes={stats['opcodes']} languages={stats['languages']} chips={stats['chips']}")
    print(f"METRIC code_opcodes={stats['opcodes']}")
    print(f"METRIC code_languages={stats['languages']}")
    print(f"METRIC code_chips={stats['chips']}")
    print(f"METRIC code_indexed={stats['infinite_indexed']}")
    print("METRIC qa_code_corpus=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())