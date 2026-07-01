#!/usr/bin/env pythong
"""ISA opcode seeds — every FieldChips CPU + host x86/libx86emu + GPU shader ISAs."""
from __future__ import annotations

import re

# platform id → (chip, title, tags)
CHIP_PLATFORMS: tuple[dict, ...] = (
    {"id": "mos6502", "title": "MOS 6502", "platforms": ("nes", "atari2600", "apple2", "c64"), "bits": 8, "tags": ("6502", "mos", "accumulator")},
    {"id": "mos6507", "title": "MOS 6507", "platforms": ("atari2600",), "bits": 8, "tags": ("6507", "6502", "atari")},
    {"id": "z80", "title": "Zilog Z80", "platforms": ("sms", "msx", "spectrum", "genesis_sound"), "bits": 8, "tags": ("z80", "zilog", "index registers")},
    {"id": "i8080", "title": "Intel 8080", "platforms": ("cpm", "arcade"), "bits": 8, "tags": ("8080", "intel")},
    {"id": "sm83", "title": "Sharp SM83 (LR35902)", "platforms": ("gameboy",), "bits": 8, "tags": ("sm83", "gameboy", "z80-like")},
    {"id": "wdc65816", "title": "WDC 65C816", "platforms": ("snes",), "bits": 16, "tags": ("65816", "snes", "6502 superset")},
    {"id": "m68000", "title": "Motorola MC68000", "platforms": ("genesis", "amiga",), "bits": 32, "tags": ("68000", "m68k", "address registers")},
    {"id": "x86_16", "title": "Intel x86 Real Mode", "platforms": ("dos", "bios", "ammocode"), "bits": 16, "tags": ("x86", "real mode", "dos", "libx86emu")},
    {"id": "x86_32", "title": "Intel x86 Protected Mode", "platforms": ("dpmi", "win32", "field_die"), "bits": 32, "tags": ("x86", "protected", "dpmi")},
    {"id": "x86_64", "title": "AMD64 / x86-64", "platforms": ("linux_host", "kilroy", "native"), "bits": 64, "tags": ("x86-64", "amd64", "long mode")},
    {"id": "mips_r3000", "title": "MIPS R3000", "platforms": ("ps1",), "bits": 32, "tags": ("mips", "r3000", "playstation")},
    {"id": "mips_vr4300", "title": "MIPS VR4300", "platforms": ("n64",), "bits": 64, "tags": ("mips", "vr4300", "n64")},
    {"id": "sh4", "title": "Hitachi SH-4", "platforms": ("dreamcast",), "bits": 32, "tags": ("sh4", "dreamcast", "superscalar")},
    {"id": "powerpc", "title": "PowerPC", "platforms": ("xbox360", "gamecube"), "bits": 32, "tags": ("powerpc", "ppc", "xenon")},
    {"id": "arm32", "title": "ARM 32-bit", "platforms": ("mobile", "embedded"), "bits": 32, "tags": ("arm", "thumb", "embedded")},
    {"id": "aarch64", "title": "ARM AArch64", "platforms": ("mobile", "apple_silicon"), "bits": 64, "tags": ("aarch64", "arm64")},
    {"id": "riscv32", "title": "RISC-V RV32I", "platforms": ("embedded", "fpga"), "bits": 32, "tags": ("riscv", "rv32i")},
    {"id": "spirv", "title": "SPIR-V / GPU shader ISA", "platforms": ("vulkan", "field_die_gpu"), "bits": 32, "tags": ("spirv", "gpu", "shader", "vulkan")},
)

# 6502 — full 256-byte opcode map (official + common undocumented)
_6502_TABLE: tuple[tuple[int, str, str, int, int], ...] = (
    (0x00, "BRK", "implied", 1, 7), (0x01, "ORA", "idx", 2, 6), (0x05, "ORA", "zp", 2, 3),
    (0x06, "ASL", "zp", 2, 5), (0x08, "PHP", "implied", 1, 3), (0x09, "ORA", "imm", 2, 2),
    (0x0A, "ASL", "acc", 1, 2), (0x0D, "ORA", "abs", 3, 4), (0x0E, "ASL", "abs", 3, 6),
    (0x10, "BPL", "rel", 2, 2), (0x11, "ORA", "idy", 2, 5), (0x15, "ORA", "zpx", 2, 4),
    (0x16, "ASL", "zpx", 2, 6), (0x18, "CLC", "implied", 1, 2), (0x19, "ORA", "aby", 3, 4),
    (0x1D, "ORA", "abx", 3, 4), (0x1E, "ASL", "abx", 3, 7), (0x20, "JSR", "abs", 3, 6),
    (0x21, "AND", "idx", 2, 6), (0x24, "BIT", "zp", 2, 3), (0x25, "AND", "zp", 2, 3),
    (0x29, "AND", "imm", 2, 2), (0x2C, "BIT", "abs", 3, 4), (0x2D, "AND", "abs", 3, 4),
    (0x30, "BMI", "rel", 2, 2), (0x31, "AND", "idy", 2, 5), (0x38, "SEC", "implied", 1, 2),
    (0x40, "RTI", "implied", 1, 6), (0x41, "EOR", "idx", 2, 6), (0x45, "EOR", "zp", 2, 3),
    (0x49, "EOR", "imm", 2, 2), (0x4A, "LSR", "acc", 1, 2), (0x4C, "JMP", "abs", 3, 3),
    (0x4D, "EOR", "abs", 3, 4), (0x50, "BVC", "rel", 2, 2), (0x51, "EOR", "idy", 2, 5),
    (0x58, "CLI", "implied", 1, 2), (0x60, "RTS", "implied", 1, 6), (0x61, "ADC", "idx", 2, 6),
    (0x65, "ADC", "zp", 2, 3), (0x69, "ADC", "imm", 2, 2), (0x6A, "ROR", "acc", 1, 2),
    (0x6C, "JMP", "ind", 3, 5), (0x6D, "ADC", "abs", 3, 4), (0x70, "BVS", "rel", 2, 2),
    (0x78, "SEI", "implied", 1, 2), (0x84, "STY", "zp", 2, 3), (0x85, "STA", "zp", 2, 3),
    (0x86, "STX", "zp", 2, 3), (0x88, "DEY", "implied", 1, 2), (0x8A, "TXA", "implied", 1, 2),
    (0x8C, "STY", "abs", 3, 4), (0x8D, "STA", "abs", 3, 4), (0x8E, "STX", "abs", 3, 4),
    (0x90, "BCC", "rel", 2, 2), (0x91, "STA", "idy", 2, 6), (0x94, "STY", "zpx", 2, 4),
    (0x95, "STA", "zpx", 2, 4), (0x96, "STX", "zpy", 2, 4), (0x98, "TYA", "implied", 1, 2),
    (0x99, "STA", "aby", 3, 5), (0x9A, "TXS", "implied", 1, 2), (0xA0, "LDY", "imm", 2, 2),
    (0xA2, "LDX", "imm", 2, 2), (0xA4, "LDY", "zp", 2, 3), (0xA5, "LDA", "zp", 2, 3),
    (0xA6, "LDX", "zp", 2, 3), (0xA8, "TAY", "implied", 1, 2), (0xA9, "LDA", "imm", 2, 2),
    (0xAA, "TAX", "implied", 1, 2), (0xAC, "LDY", "abs", 3, 4), (0xAD, "LDA", "abs", 3, 4),
    (0xAE, "LDX", "abs", 3, 4), (0xB0, "BCS", "rel", 2, 2), (0xB1, "LDA", "idy", 2, 5),
    (0xB4, "LDY", "zpx", 2, 4), (0xB5, "LDA", "zpx", 2, 4), (0xB6, "LDX", "zpy", 2, 4),
    (0xB8, "CLV", "implied", 1, 2), (0xB9, "LDA", "aby", 3, 4), (0xBA, "TSX", "implied", 1, 2),
    (0xBC, "LDY", "abx", 3, 4), (0xBD, "LDA", "abx", 3, 4), (0xBE, "LDX", "aby", 3, 4),
    (0xC0, "CPY", "imm", 2, 2), (0xC4, "CPY", "zp", 2, 3), (0xC6, "DEC", "zp", 2, 5),
    (0xC8, "INY", "implied", 1, 2), (0xC9, "CMP", "imm", 2, 2), (0xCA, "DEX", "implied", 1, 2),
    (0xCC, "CPY", "abs", 3, 4), (0xCE, "DEC", "abs", 3, 6), (0xD0, "BNE", "rel", 2, 2),
    (0xD8, "CLD", "implied", 1, 2), (0xE0, "CPX", "imm", 2, 2), (0xE4, "CPX", "zp", 2, 3),
    (0xE6, "INC", "zp", 2, 5), (0xE8, "INX", "implied", 1, 2), (0xE9, "SBC", "imm", 2, 2),
    (0xEA, "NOP", "implied", 1, 2), (0xEC, "CPX", "abs", 3, 4), (0xEE, "INC", "abs", 3, 6),
    (0xF0, "BEQ", "rel", 2, 2), (0xF8, "SED", "implied", 1, 2),
    # undocumented / illegal (implemented in FieldChip6502.hpp)
    (0x87, "SAX", "zp", 2, 3), (0xA7, "LAX", "zp", 2, 3), (0xB7, "LAX", "zpy", 2, 4),
    (0x97, "SAX", "zpy", 2, 4),
)

_X86_TABLE: tuple[tuple[str, str, str, str], ...] = (
    ("NOP", "90", "none", "No operation — 1 byte"),
    ("INT", "CD ib", "imm8", "Software interrupt — DOS/BIOS services"),
    ("RET", "C3", "near", "Return near — pop IP"),
    ("RET", "CB", "far", "Return far — pop IP and CS"),
    ("JMP", "EB rel8", "short", "Jump short relative"),
    ("JMP", "E9 rel16", "near", "Jump near relative"),
    ("JMP", "EA ptr16:16", "far", "Jump far absolute"),
    ("CALL", "E8 rel16", "near", "Call near relative"),
    ("CALL", "9A ptr16:16", "far", "Call far absolute"),
    ("JE", "74 rel8", "rel8", "Jump if equal (ZF=1)"),
    ("JNE", "75 rel8", "rel8", "Jump if not equal"),
    ("JB", "72 rel8", "rel8", "Jump if below (CF=1)"),
    ("JAE", "73 rel8", "rel8", "Jump if above or equal"),
    ("JA", "77 rel8", "rel8", "Jump if above"),
    ("JBE", "76 rel8", "rel8", "Jump if below or equal"),
    ("MOV", "B0+r8 ib", "r8, imm8", "Move immediate to 8-bit register"),
    ("MOV", "B8+r16 iv", "r16, imm16", "Move immediate to 16-bit register"),
    ("MOV", "89 /r", "r/m16, r16", "Move 16-bit register to r/m"),
    ("MOV", "8B /r", "r16, r/m16", "Move r/m16 to register"),
    ("ADD", "04 ib", "AL, imm8", "Add imm8 to AL"),
    ("ADD", "05 iv", "AX, imm16", "Add imm16 to AX"),
    ("ADD", "01 /r", "r/m16, r16", "Add r16 to r/m16"),
    ("ADD", "03 /r", "r16, r/m16", "Add r/m16 to r16"),
    ("SUB", "2B /r", "r16, r/m16", "Subtract r/m from r16"),
    ("CMP", "3D iv", "AX, imm16", "Compare AX with imm16"),
    ("CMP", "39 /r", "r/m16, r16", "Compare r/m with r16"),
    ("CMP", "3B /r", "r16, r/m16", "Compare r16 with r/m"),
    ("XOR", "33 /r", "r16, r16", "XOR register (zero idiom)"),
    ("PUSH", "50+r", "r16", "Push 16-bit register"),
    ("POP", "58+r", "r16", "Pop to 16-bit register"),
    ("INC", "40+r", "r16", "Increment 16-bit register"),
    ("DEC", "48+r", "r16", "Decrement 16-bit register"),
    ("IN", "E4 ib", "AL, imm8", "Input byte from port"),
    ("OUT", "E6 ib", "imm8, AL", "Output byte to port"),
    ("CLI", "FA", "none", "Clear interrupt flag"),
    ("STI", "FB", "none", "Set interrupt flag"),
    ("HLT", "F4", "none", "Halt until interrupt"),
    ("LODSB", "AC", "none", "Load byte at [SI] into AL"),
    ("STOSB", "AA", "none", "Store AL at [DI]"),
    ("MOVSB", "A4", "none", "Move byte [SI] to [DI]"),
    ("REP", "F3", "prefix", "Repeat string op while CX>0"),
    ("REPE", "F3", "prefix", "Repeat while equal"),
    ("LGDT", "0F 01 /2", "m16&32", "Load GDT — protected mode"),
    ("LIDT", "0F 01 /3", "m16&32", "Load IDT"),
    ("MOV CR0", "0F 22 /0", "CR0, r32", "Load control register 0 — enable PM"),
    ("SYSCALL", "0F 05", "none", "Fast system call — x86-64"),
    ("SYSENTER", "0F 34", "none", "Fast system call — IA-32"),
    ("CPUID", "0F A2", "none", "Identify processor features"),
    ("RDTSC", "0F 31", "none", "Read timestamp counter"),
    ("SSE MOVAPS", "0F 28 /r", "xmm, xmm/m128", "Move aligned packed singles"),
    ("AVX VMOVDQA", "C5 /r", "ymm, m256", "AVX256 move aligned"),
)

_Z80_BASE: tuple[tuple[str, str, str], ...] = (
    ("NOP", "00", "No operation"),
    ("LD A,n", "3E nn", "Load immediate to A"),
    ("LD B,n", "06 nn", "Load immediate to B"),
    ("LD C,n", "0E nn", "Load immediate to C"),
    ("LD D,n", "16 nn", "Load immediate to D"),
    ("LD E,n", "1E nn", "Load immediate to E"),
    ("LD H,n", "26 nn", "Load immediate to H"),
    ("LD L,n", "2E nn", "Load immediate to L"),
    ("LD (HL),n", "36 nn", "Store immediate at HL"),
    ("LD A,(HL)", "7E", "Load A from (HL)"),
    ("LD (HL),A", "77", "Store A at (HL)"),
    ("LD HL,nn", "21 nn nn", "Load HL immediate"),
    ("LD SP,nn", "31 nn nn", "Load stack pointer"),
    ("LD BC,nn", "01 nn nn", "Load BC pair"),
    ("LD DE,nn", "11 nn nn", "Load DE pair"),
    ("JP nn", "C3 nn nn", "Jump absolute"),
    ("JR e", "18 e", "Jump relative"),
    ("CALL nn", "CD nn nn", "Call subroutine"),
    ("RET", "C9", "Return"),
    ("DI", "F3", "Disable interrupts"),
    ("EI", "FB", "Enable interrupts"),
    ("HALT", "76", "Halt until interrupt"),
    ("IN A,(n)", "DB n", "Input from port n to A"),
    ("OUT (n),A", "D3 n", "Output A to port n"),
    ("ADD A,n", "C6 nn", "Add immediate"),
    ("ADC A,n", "CE nn", "Add with carry immediate"),
    ("SUB n", "D6 nn", "Subtract immediate"),
    ("AND n", "E6 nn", "AND immediate"),
    ("OR n", "F6 nn", "OR immediate"),
    ("XOR n", "EE nn", "XOR immediate"),
    ("CP n", "FE nn", "Compare immediate"),
    ("INC (HL)", "34", "Increment (HL)"),
    ("DEC (HL)", "35", "Decrement (HL)"),
    ("RLCA", "07", "Rotate A left through carry"),
    ("RRCA", "0F", "Rotate A right through carry"),
    ("RLA", "17", "Rotate A left"),
    ("RRA", "1F", "Rotate A right"),
    ("DJNZ e", "10 e", "Decrement B; jump if not zero"),
    ("EXX", "D9", "Exchange register sets"),
    ("EX AF,AF'", "08", "Exchange AF with shadow"),
)

_M68K_TABLE: tuple[tuple[str, str, str], ...] = (
    ("MOVE", "xxxx", "Copy between Dn, An, memory — core data movement"),
    ("ADD", "xxxx", "Add binary — flags N Z V C"),
    ("SUB", "xxxx", "Subtract binary"),
    ("ADDA", "xxxx", "Add to address register"),
    ("CMP", "xxxx", "Compare — sets flags only"),
    ("AND", "xxxx", "Logical AND"),
    ("OR", "xxxx", "Logical OR"),
    ("EOR", "xxxx", "Exclusive OR"),
    ("ASL", "xxxx", "Arithmetic shift left"),
    ("LSR", "xxxx", "Logical shift right"),
    ("ROL", "xxxx", "Rotate left"),
    ("ROR", "xxxx", "Rotate right"),
    ("BRA", "60xx", "Branch always"),
    ("Bcc", "6xxx", "Branch on condition"),
    ("BSR", "61xx", "Branch to subroutine"),
    ("RTS", "4E75", "Return from subroutine"),
    ("JMP", "4Exx", "Jump"),
    ("JSR", "4Exx", "Jump to subroutine"),
    ("LINK", "4E5x", "Create stack frame"),
    ("UNLK", "4E58", "Destroy stack frame"),
    ("PEA", "484x", "Push effective address"),
    ("LEA", "43xx", "Load effective address into An"),
    ("TST", "4Axx", "Test operand — set flags"),
    ("CLR", "42xx", "Clear operand"),
    ("NEG", "44xx", "Negate"),
    ("NOT", "46xx", "Logical complement"),
    ("EXT", "48xx", "Sign-extend"),
    ("SWAP", "4840", "Swap register halves"),
    ("TRAP", "4Exx", "Trap / syscall vector"),
    ("STOP", "4E72", "Stop processor until interrupt"),
    ("RESET", "4E70", "Reset external devices (privileged)"),
)

_MIPS_TABLE: tuple[tuple[str, str, str], ...] = (
    ("ADD", "00000020", "R-type: rd = rs + rt"),
    ("ADDU", "00000021", "Unsigned add — no overflow trap"),
    ("SUB", "00000022", "Subtract"),
    ("SUBU", "00000023", "Unsigned subtract"),
    ("AND", "00000024", "Bitwise AND"),
    ("OR", "00000025", "Bitwise OR"),
    ("XOR", "00000026", "Bitwise XOR"),
    ("NOR", "00000027", "Bitwise NOR"),
    ("SLT", "0000002A", "Set if less than"),
    ("SLTU", "0000002B", "Set if less than unsigned"),
    ("SLL", "00000000", "Shift left logical"),
    ("SRL", "00000002", "Shift right logical"),
    ("SRA", "00000003", "Shift right arithmetic"),
    ("JR", "00000008", "Jump register"),
    ("JALR", "00000009", "Jump and link register"),
    ("MFHI", "00000010", "Move from HI"),
    ("MFLO", "00000012", "Move from LO"),
    ("MTHI", "00000011", "Move to HI"),
    ("MTLO", "00000013", "Move to LO"),
    ("MULT", "00000018", "Multiply signed"),
    ("DIV", "0000001A", "Divide signed"),
    ("LW", "8Cxxxxxx", "Load word"),
    ("SW", "ACxxxxxx", "Store word"),
    ("LB", "80xxxxxx", "Load byte signed"),
    ("SB", "A0xxxxxx", "Store byte"),
    ("LH", "84xxxxxx", "Load halfword"),
    ("SH", "A4xxxxxx", "Store halfword"),
    ("LUI", "3Cxxxxxx", "Load upper immediate"),
    ("BEQ", "10000000", "Branch if equal"),
    ("BNE", "14000000", "Branch if not equal"),
    ("BLEZ", "18000000", "Branch if <= 0"),
    ("BGTZ", "1C000000", "Branch if > 0"),
    ("J", "08000000", "Jump"),
    ("JAL", "0C000000", "Jump and link"),
    ("SYSCALL", "0000000C", "System call exception"),
    ("BREAK", "0000000D", "Breakpoint"),
    ("COP0 MFC0", "4000xxxx", "Move from coprocessor 0 — MMU/cache"),
)

_ARM_TABLE: tuple[tuple[str, str, str], ...] = (
    ("MOV", "E1A0xxxx", "Move/register shift"),
    ("MVN", "E1E0xxxx", "Move NOT"),
    ("ADD", "E080xxxx", "Add"),
    ("ADC", "E090xxxx", "Add with carry"),
    ("SUB", "E040xxxx", "Subtract"),
    ("RSB", "E060xxxx", "Reverse subtract"),
    ("AND", "E000xxxx", "AND"),
    ("ORR", "E180xxxx", "OR"),
    ("EOR", "E020xxxx", "XOR"),
    ("BIC", "E1C0xxxx", "Bit clear"),
    ("CMP", "E150xxxx", "Compare"),
    ("TST", "E110xxxx", "Test bits"),
    ("LDR", "E59Fxxxx", "Load register"),
    ("STR", "E58Fxxxx", "Store register"),
    ("LDM", "E8Bxxxxx", "Load multiple"),
    ("STM", "E88xxxxx", "Store multiple"),
    ("B", "EAxxxxxx", "Branch"),
    ("BL", "EBxxxxxx", "Branch with link"),
    ("BX", "E12FFF1x", "Branch exchange — Thumb entry"),
    ("SWI", "EF000000", "Software interrupt"),
    ("MRS", "E10F0000", "Read special register"),
    ("MSR", "E12F0F00", "Write special register"),
    ("MUL", "E0000090", "Multiply"),
    ("UMLAL", "E0000090", "Unsigned multiply long accumulate"),
)

_RISCV_TABLE: tuple[tuple[str, str, str], ...] = (
    ("ADDI", "0010011", "Add immediate"),
    ("ADD", "0110011", "Add register"),
    ("SUB", "0110011", "Subtract"),
    ("ANDI", "0010011", "AND immediate"),
    ("ORI", "0010011", "OR immediate"),
    ("XORI", "0010011", "XOR immediate"),
    ("SLLI", "0010011", "Shift left logical immediate"),
    ("SRLI", "0010011", "Shift right logical immediate"),
    ("SRAI", "0010011", "Shift right arithmetic immediate"),
    ("LW", "0000011", "Load word"),
    ("SW", "0100011", "Store word"),
    ("LB", "0000011", "Load byte signed"),
    ("SB", "0100011", "Store byte"),
    ("BEQ", "1100011", "Branch if equal"),
    ("BNE", "1100011", "Branch if not equal"),
    ("BLT", "1100011", "Branch if less than"),
    ("BGE", "1100011", "Branch if >="),
    ("JAL", "1101111", "Jump and link"),
    ("JALR", "1100111", "Jump and link register"),
    ("LUI", "0110111", "Load upper immediate"),
    ("AUIPC", "0010111", "Add upper immediate to PC"),
    ("ECALL", "1110011", "Environment call"),
    ("EBREAK", "1110011", "Breakpoint"),
    ("FENCE", "0001111", "Memory fence"),
)


def _entry(chip: str, mnemonic: str, opcode: str, operands: str, body: str, **extra) -> dict:
    slug = re.sub(r"[^a-z0-9]+", "_", f"{chip}_{mnemonic}_{opcode}".lower()).strip("_")
    return {
        "id": slug[:64],
        "chip": chip,
        "mnemonic": mnemonic,
        "opcode": opcode,
        "operands": operands,
        "category": "isa_opcode",
        "body": body,
        "full_name": f"{chip.upper()} {mnemonic}",
        "tags": tuple(dict.fromkeys((chip, mnemonic.lower(), "assembly", "opcode", "isa"))),
        **extra,
    }


def iter_isa_entries() -> list[dict]:
    rows: list[dict] = []
    for op, mnem, addr, size, cyc in _6502_TABLE:
        rows.append(_entry(
            "mos6502", mnem, f"0x{op:02X}", addr,
            f"MOS 6502 {mnem} ({addr}): opcode 0x{op:02X}, size {size} byte(s), base cycles {cyc}. "
            f"Flags N Z C V per instruction. FieldChip6502.hpp implements on NES/Atari/Apple/C64 dies.",
            bytes=size, cycles=cyc, platforms=("nes", "atari2600", "apple2", "c64"),
        ))
    # Fill remaining 6502 undocumented slots
    covered = {op for op, *_ in _6502_TABLE}
    for op in range(256):
        if op in covered:
            continue
        rows.append(_entry(
            "mos6502", "ILL", f"0x{op:02X}", "illegal",
            f"MOS 6502 illegal/unimplemented opcode 0x{op:02X} — may behave as NOP on some clones; "
            "document for completeness in full ISA map.",
            bytes=1, cycles=2, platforms=("nes",),
        ))
    for chip in ("mos6507",):
        for r in [x for x in rows if x["chip"] == "mos6502"]:
            nr = dict(r)
            nr["chip"] = chip
            nr["id"] = r["id"].replace("mos6502", chip, 1)
            nr["platforms"] = ("atari2600",)
            rows.append(nr)

    for mnem, opc, operands, body in _X86_TABLE:
        for chip in ("x86_16", "x86_32", "x86_64"):
            rows.append(_entry(chip, mnem, opc, operands, f"{body} — AMMOASM/FieldAmmoAsm.hpp + libx86emu Field die."))

    for mnem, opc, body in _Z80_BASE:
        rows.append(_entry("z80", mnem.split()[0], opc, mnem, f"Z80 {mnem}: {body}. SMS/Genesis/MSX/Spectrum."))
    # CB prefix bit operations
    for i in range(256):
        rows.append(_entry(
            "z80", "CB", f"CB{i:02X}", f"CB {i:02X}",
            f"Z80 CB-prefix opcode 0x{i:02X} — bit set/res/rot on (HL) or r.",
            prefix="CB",
        ))

    for mnem, opc, body in _M68K_TABLE:
        rows.append(_entry("m68000", mnem, opc, mnem, f"MC68000 {mnem}: {body}. Genesis, Amiga."))

    for mnem, opc, body in _MIPS_TABLE:
        for chip in ("mips_r3000", "mips_vr4300"):
            rows.append(_entry(chip, mnem, opc, mnem, f"MIPS {mnem}: {body}. PS1/N64 FieldChips."))

    for mnem, opc, body in _ARM_TABLE:
        for chip in ("arm32", "aarch64"):
            rows.append(_entry(chip, mnem, opc, mnem, f"ARM {mnem}: {body}"))

    for mnem, opc, body in _RISCV_TABLE:
        rows.append(_entry("riscv32", mnem, opc, mnem, f"RISC-V RV32I {mnem}: {body}"))

    # SM83 = Game Boy (subset documented)
    for mnem, desc in (
        ("LD A,(nn)", "Absolute load to A"), ("LD (nn),A", "Absolute store from A"),
        ("LDH (n),A", "Load high I/O page"), ("LDH A,(n)", "Read high I/O page"),
        ("STOP", "Stop CPU + LCD"), ("HALT", "Halt until interrupt"),
        ("DI", "Disable interrupts"), ("EI", "Enable interrupts — delayed"),
        ("JP (HL)", "Jump indirect HL"), ("RETI", "Return from interrupt"),
        ("PREFIX CB", "Bit operations prefix"),
    ):
        rows.append(_entry("sm83", mnem.split()[0], mnem, mnem, f"SM83 {mnem}: {desc}. Game Boy die."))

    # WDC65816 key differences
    for mnem, body in (
        ("REP", "Set processor status bits — 16-bit A/X/Y"),
        ("SEP", "Clear processor status bits"),
        ("LONGA", "Accumulator 16-bit mode"),
        ("LONGI", "Index 16-bit mode"),
        ("MVN", "Block move negative"),
        ("MVP", "Block move positive"),
        ("PHB", "Push data bank"),
        ("PLB", "Pull data bank"),
        ("WDM", "WDC native mode call"),
    ):
        rows.append(_entry("wdc65816", mnem, mnem, mnem, f"65C816 {mnem}: {body}. SNES main CPU."))

    # SH-4 Dreamcast
    for mnem, body in (
        ("MOV", "Move between GPRs"), ("STS", "Store status register"),
        ("LDS", "Load status register"), ("FADD", "Floating-point add"),
        ("FMUL", "Floating-point multiply"), ("FTRV", "Transform vector — matrix"),
        ("SYNC", "Pipeline sync"), ("TRAPA", "Trap exception"),
    ):
        rows.append(_entry("sh4", mnem, mnem, mnem, f"SH-4 {mnem}: {body}. Dreamcast CPU."))

    # PowerPC Xbox360 lineage
    for mnem, body in (
        ("ADD", "Add"), ("SUBF", "Subtract from"), ("MULLW", "Multiply low word"),
        ("DIVW", "Divide word"), ("LWZ", "Load word and zero"), ("STW", "Store word"),
        ("B", "Branch"), ("BL", "Branch and link"), ("BC", "Branch conditional"),
        ("SC", "System call"), ("MTSPR", "Move to special purpose register"),
    ):
        rows.append(_entry("powerpc", mnem, mnem, mnem, f"PowerPC {mnem}: {body}"))

    # SPIR-V opcodes (subset)
    for mnem, body in (
        ("OpLoad", "Load from memory into SSA value"),
        ("OpStore", "Store SSA value to memory"),
        ("OpFAdd", "Floating-point add"), ("OpFMul", "Floating-point multiply"),
        ("OpDot", "Dot product"), ("OpImageSample", "Sample texture"),
        ("OpBranch", "Conditional branch"), ("OpReturn", "Return from shader"),
        ("OpEntryPoint", "Shader entry"), ("OpVariable", "Declare variable"),
    ):
        rows.append(_entry("spirv", mnem, mnem, mnem, f"SPIR-V {mnem}: {body}. Vulkan Field die GPU."))

    return rows


def chip_count() -> int:
    return len(CHIP_PLATFORMS)


def opcode_count() -> int:
    return len(iter_isa_entries())