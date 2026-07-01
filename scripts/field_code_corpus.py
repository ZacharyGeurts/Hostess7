#!/usr/bin/env pythong
"""Field code corpus — every chip ISA opcode + all programming languages."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from field_code_catalog import catalog_stats  # noqa: E402
from field_code_domains import CODE_CORPUS_VERSION, CODE_DOMAINS  # noqa: E402
from field_code_infinite import (  # noqa: E402
    INDEX,
    ingest_catalog,
    infinite_status,
    lookup_language,
    lookup_opcode,
    search_infinite,
)
from field_isa_data import CHIP_PLATFORMS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CORPUS_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "code" / "corpus.json"


def build_corpus() -> dict:
    st = catalog_stats()
    return {
        "version": CODE_CORPUS_VERSION,
        "domains": [dict(d) for d in CODE_DOMAINS],
        "domain_count": len(CODE_DOMAINS),
        "chips": [dict(c) for c in CHIP_PLATFORMS],
        "chip_count": st.get("chips", 0),
        "opcode_count": st.get("opcodes", 0),
        "language_count": st.get("languages", 0),
        "infinite_drive": True,
        "disclaimer": (
            "Hostess 7 code brain is educational synthesis — opcode tables aligned to FieldChips silicon "
            "and standard ISA references. Not a substitute for official vendor programmer manuals."
        ),
    }


def ensure_corpus() -> Path:
    CORPUS_CACHE.parent.mkdir(parents=True, exist_ok=True)
    refresh = True
    if CORPUS_CACHE.is_file():
        try:
            data = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < CODE_CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh or not INDEX.is_file():
        ingest_catalog(vacuum=True)
    doc = build_corpus()
    CORPUS_CACHE.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return CORPUS_CACHE


def _tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 1]


def _score_domains(query: str, domains: list[dict]) -> list[tuple[int, dict]]:
    toks = _tokens(query)
    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for d in domains:
        tags = " ".join(d.get("tags") or []).lower()
        body = str(d.get("body", "")).lower()
        title = str(d.get("title", "")).lower()
        blob = f"{title} {tags} {body[:1500]}"
        score = sum(4 if t in tags else 2 if t in blob else 0 for t in toks)
        if any(k in q for k in ("opcode", "instruction", "assembly", "asm", "mnemonic")):
            if d.get("id") in ("isa_policy", "field_chips", "x86_host"):
                score += 20
        if any(k in q for k in ("language", "python", "rust", "typescript", "compiler")):
            if d.get("id") == "lang_policy":
                score += 18
        if any(k in q for k in ("chips", "nes", "genesis", "platform")):
            if d.get("id") == "field_chips":
                score += 15
        if score > 0:
            scored.append((score, d))
    scored.sort(key=lambda x: -x[0])
    return scored


def search_code(query: str, *, limit: int = 8) -> list[dict]:
    ensure_corpus()
    out: list[dict] = []
    seen: set[str] = set()
    q = query.lower()

    # Opcode lookup: "6502 LDA", "x86 MOV", "what is MIPS ADD"
    chip_m = re.search(
        r"\b(6502|6507|z80|x86|mips|arm|m68k|68000|sm83|65816|sh4|powerpc|riscv|spirv)\b",
        q,
    )
    insn_m = re.search(
        r"\b(lda|mov|add|jmp|call|nop|ret|branch|load|store)\b",
        q,
    )
    hex_m = re.search(r"\b0x[0-9a-f]{2,4}\b", q)
    if hex_m:
        for row in search_infinite(hex_m.group(0), limit=4):
            rid = str(row.get("id", ""))
            if rid not in seen and row.get("category") == "isa_opcode":
                seen.add(rid)
                out.append({**row, "source": "opcode_hex"})

    if chip_m and insn_m:
        chip_map = {
            "6502": "mos6502", "6507": "mos6507", "z80": "z80", "x86": "x86_16",
            "mips": "mips_r3000", "arm": "arm32", "m68k": "m68000", "68000": "m68000",
            "sm83": "sm83", "65816": "wdc65816", "sh4": "sh4", "powerpc": "powerpc",
            "riscv": "riscv32", "spirv": "spirv",
        }
        chip = chip_map.get(chip_m.group(1), chip_m.group(1))
        for row in lookup_opcode(chip, insn_m.group(1)):
            rid = str(row.get("id", ""))
            if rid not in seen:
                seen.add(rid)
                out.append({**row, "source": "opcode_lookup"})

    # Language lookup
    for m in re.finditer(
        r"\b(python|rust|c\+\+|cpp|javascript|typescript|java|go|zig|haskell|kotlin|swift|ammoasm|c#|csharp)\b",
        q,
    ):
        lang = m.group(1).replace("c++", "cpp").replace("csharp", "c#")
        hit = lookup_language(lang)
        if hit:
            hid = str(hit.get("id", ""))
            if hid not in seen:
                seen.add(hid)
                out.append({**hit, "source": "lang_lookup"})

    for row in search_infinite(query, limit=limit):
        rid = str(row.get("id", ""))
        if rid in seen:
            continue
        seen.add(rid)
        out.append({**row, "source": "infinite_drive"})
        if len(out) >= limit:
            break

    try:
        doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        doc = build_corpus()
    for _, d in _score_domains(query, doc.get("domains") or []):
        did = str(d.get("id", ""))
        if did in seen:
            continue
        seen.add(did)
        out.append({**dict(d), "source": "domain"})
        if len(out) >= limit:
            break
    return out[:limit]


def synthesize_code_paragraphs(query: str) -> list[str]:
    hits = search_code(query, limit=6)
    if not hits:
        hits = search_code("assembly opcode programming language chips x86 6502", limit=4)
    paras: list[str] = []
    pro = os.environ.get("AMOURANTHRTX_HOSTESS") == "1" and os.environ.get("HOSTESS7_PRO", "1") == "1"
    st = infinite_status()
    if pro:
        paras.append(
            f"Code brain: {st.get('opcode_count', 0)} ISA opcodes across FieldChips dies, "
            f"{st.get('language_count', 0)} programming languages indexed."
        )
    else:
        paras.append(
            f"Code corpus: {st.get('opcode_count', 0)} assembly instructions, "
            f"{st.get('language_count', 0)} languages — cache/fieldstorage/brain/code/."
        )

    for h in hits:
        if h.get("source") == "domain":
            paras.append(f"{h.get('title', 'Code')}: {h.get('body', '')}")
        elif h.get("category") == "programming_language":
            name = h.get("name", h.get("full_name", ""))
            body = str(h.get("body", "")).strip()
            parad = h.get("paradigm", "")
            typing = h.get("typing", "")
            paras.append(f"{name} ({parad}, {typing}): {body}")
        elif h.get("category") == "isa_opcode" or h.get("mnemonic"):
            chip = h.get("chip", "")
            mnem = h.get("mnemonic", "")
            opc = h.get("opcode", "")
            body = str(h.get("body", "")).strip()[:600]
            paras.append(f"{chip} {mnem} [{opc}]: {body}")
        else:
            paras.append(str(h.get("body", h.get("blob", "")))[:500])
    return paras


def corpus_stats() -> dict:
    ensure_corpus()
    doc = json.loads(CORPUS_CACHE.read_text(encoding="utf-8"))
    inf = infinite_status()
    return {
        "version": doc.get("version", CODE_CORPUS_VERSION),
        "domains": doc.get("domain_count", len(CODE_DOMAINS)),
        "chips": doc.get("chip_count", 0),
        "opcodes": inf.get("opcode_count", 0),
        "languages": inf.get("language_count", 0),
        "infinite_indexed": inf.get("indexed", 0),
    }


if __name__ == "__main__":
    ensure_corpus()
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "6502 LDA opcode Rust ownership"
    for p in synthesize_code_paragraphs(q):
        print(p)
        print()