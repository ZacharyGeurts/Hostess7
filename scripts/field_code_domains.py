#!/usr/bin/env pythong
"""Code brain domains — assembly ISAs, programming languages, toolchain."""
from __future__ import annotations

CODE_CORPUS_VERSION = 1

CODE_DOMAINS: tuple[dict, ...] = (
    {
        "id": "isa_policy",
        "title": "ISA & opcode policy",
        "tags": ("isa", "opcode", "assembly", "instruction", "mnemonic", "chip"),
        "body": (
            "Hostess 7 indexes every assembly instruction per FieldChips CPU die — MOS 6502/6507, Z80, "
            "8080, SM83, WDC65816, MC68000, x86 real/protected/long mode, MIPS R3000/VR4300, SH-4, PowerPC, "
            "ARM/AArch64, RISC-V RV32I, SPIR-V GPU. Lossless jsonl shards: cache/fieldstorage/brain/code/infinite/. "
            "Ingest: ./Hostess7.sh code-ingest seed. Native silicon: Navigator/engine/CHIPS/."
        ),
    },
    {
        "id": "field_chips",
        "title": "FieldChips platform map",
        "tags": ("chips", "nes", "snes", "genesis", "amiga", "ps1", "n64", "dreamcast", "xbox360"),
        "body": (
            "FieldChips.hpp maps consoles to CPU dies: NES 6502+2A03+2C02, SMS/Genesis Z80+68000, "
            "SNES 65816, PS1 MIPS R3000, N64 VR4300, Dreamcast SH-4, Xbox360 PowerPC+Xenos GPU wave. "
            "Common/: FieldChip6502, FieldChipZ80, FieldChipM68000, FieldChipSm83, FieldChipWdc65816. "
            "bench_chips.py QA gates GPU wave per platform."
        ),
    },
    {
        "id": "x86_host",
        "title": "Host x86 / libx86emu / Field die",
        "tags": ("x86", "libx86emu", "dos", "dpmi", "ammocode", "ammoasm"),
        "body": (
            "AMOURANTHRTX runs DOS via libx86emu on Field canvas — real-mode INT 21h, DPMI PM32, "
            "FieldX86Native traps. AMMOASM (FieldAmmoAsm.hpp) assembles MASM subset to FieldAmmoObj. "
            "FieldPc.hpp documents undocumented opcode traps. Kilroy ELF64 loader for native guest programs."
        ),
    },
    {
        "id": "lang_policy",
        "title": "Programming languages policy",
        "tags": ("programming language", "paradigm", "typing", "compiler", "interpreter"),
        "body": (
            "Full language catalog: imperative, functional, logic, OOP, concurrent, GPU, HDL, markup, data. "
            "Each entry: paradigm, typing discipline, memory model, compilation target, AMOURANTHRTX relevance. "
            "Hostess routes code/language/asm queries to code brain — perfect understanding bar: "
            "opcode-level for silicon, semantic-level for languages."
        ),
    },
    {
        "id": "toolchain",
        "title": "AMOURANTHRTX toolchain",
        "tags": ("toolchain", "cmake", "linux.sh", "release", "qa", "hostess7.sh"),
        "body": (
            "Build: cmake --build build. Gates: ./linux.sh release-2.0. Brain: pythong field_superintelligence.py. "
            "Talk: ./Hostess7.sh. Lossless brain under cache/fieldstorage/brain/. "
            "Code corpus QA: qa_code_corpus_test.py."
        ),
    },
)