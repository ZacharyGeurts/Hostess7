#!/usr/bin/env pythong
"""Domain-specific OCR candidate extraction and verification for Hostess 7 chambers."""
from __future__ import annotations

import re
from typing import Any, Callable

_LINE_RE: dict[str, re.Pattern[str]] = {
    "programming": re.compile(
        r"(?:def\s+\w+|class\s+\w+|import\s+\w+|from\s+\w+\s+import|async\s+def|"
        r"function\s+\w+|const\s+\w+|let\s+\w+|var\s+\w+|return\s+|if\s*\(|for\s*\(|while\s*\(|"
        r"python|javascript|typescript|rust|golang|sql|api|endpoint|module|package|"
        r"hostess7|nexus|subprocess|json\.loads|pathlib)",
        re.I,
    ),
    "g16": re.compile(
        r"(?:g16|grok16|field_opt|field-opt|g16_field|compile|assembler|opcode|"
        r"bin/g16|g16-toolchain|mandate|ammo|launch\s+chamber|plane\s+convert|"
        r"5\.1\.0|compiler\s+fluency|stack_status)",
        re.I,
    ),
    "codecraft": re.compile(
        r"(?:refactor|lint|pattern|snippet|craft|review|ast\.|type\s+hint|"
        r"atomic\s+write|doctrine|battery|explain|codecraft|programming_tier|"
        r"hostess7-|nexus-|queen-)",
        re.I,
    ),
    "geography": re.compile(
        r"(?:capital|continent|latitude|longitude|postal|zip\s*code|address|"
        r"country|city|state|province|river|ocean|equator|hemisphere|"
        r"geography|map|coordinates|flat\s+earth|world\s+geography)",
        re.I,
    ),
    "music": re.compile(
        r"(?:note|chord|tempo|scale|clef|rhythm|pitch|interval|meter|key\s+signature|"
        r"treble|bass|allegro|andante|forte|piano|music\s+theory|notation|"
        r"sight[\s-]?read|ear\s+training|music_brain|music_eye)",
        re.I,
    ),
    "imaging": re.compile(
        r"(?:png|jpeg|jpg|webp|gif|pixel|pil|format|combinatronic|imagine|"
        r"icon|visual|render|canvas|resolution|4k|framebuffer|asset|repair|"
        r"field-imagine|nexus_teach|big_drive)",
        re.I,
    ),
    "sense": re.compile(
        r"(?:final_eye|final_ear|final_mouth|eyeball|earball|mouthball|"
        r"ocr|vision|audio|neural|plate\s+meld|sense\s+package|field\s+sense|"
        r"watch|look|poll|verify|queen-eyeball|queen-earball)",
        re.I,
    ),
    "reality_physics": re.compile(
        r"(?:gravity|entropy|thermodynamic|field\s+technology|physics|energy|"
        r"quantum|mechanics|spacetime|relativity|entropy|enthalpy|"
        r"reality_physics|field_technology|amplitude\s+chamber|lattice)",
        re.I,
    ),
}

_ROW_FILTERS: dict[str, Callable[[dict[str, Any]], bool]] = {
    "combat_motion": lambda row: any(
        k in str(row.get("id", "")).lower()
        or k in str(row.get("label", "")).lower()
        or k in str(row.get("family", "")).lower()
        for k in ("kung", "mma", "striking", "grappling", "defense", "wing", "shaolin", "wrestling", "boxing")
    ),
    "g16_toolchain": lambda row: "g16" in str(row.get("id", "")).lower() or "grok" in str(row.get("label", "")).lower(),
    "music_notation": lambda row: any(
        k in str(row.get("id", "")).lower() or k in str(row.get("label", "")).lower()
        for k in ("music", "note", "chord", "clef", "rhythm", "pitch")
    ),
    "imaging_format": lambda row: any(
        k in str(row.get("id", "")).lower() or k in str(row.get("format", "")).lower()
        for k in ("png", "jpeg", "webp", "gif", "icon", "visual", "format")
    ),
}


def text_quality_ok(text: str) -> bool:
    if not text:
        return False
    sample = text[:4000]
    if "\x00" in sample or "H7C" in sample[:8]:
        return False
    printable = sum(1 for c in sample if c.isprintable() or c in "\n\t")
    return printable / max(len(sample), 1) >= 0.85


def row_passes_filter(row: dict[str, Any], filter_key: str) -> bool:
    if not filter_key:
        return True
    fn = _ROW_FILTERS.get(filter_key)
    return fn(row) if fn else True


def extract_candidates(
    chamber_id: str,
    text: str,
    *,
    source_id: str = "",
    min_len: int = 8,
) -> list[dict[str, Any]]:
    if not text or len(text) < 3 or not text_quality_ok(text):
        return []
    pattern = _LINE_RE.get(chamber_id)
    if not pattern:
        return []
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    def add(raw: str, kind: str) -> None:
        cand = re.sub(r"\s+", " ", raw.strip())[:240]
        if len(cand) < min_len:
            return
        key = cand.lower()
        if key in seen:
            return
        seen.add(key)
        out.append({"text": cand, "kind": kind, "source_id": source_id})

    for m in pattern.finditer(text):
        start = max(0, m.start() - 40)
        end = min(len(text), m.end() + 80)
        add(text[start:end], "regex_context")

    for line in text.splitlines():
        line = line.strip()
        if not line or len(line) < min_len:
            continue
        if pattern.search(line):
            add(line, f"{chamber_id}_line")

    return out[:200]


def plausible_candidate(chamber_id: str, text: str) -> bool:
    pattern = _LINE_RE.get(chamber_id)
    if not pattern or not text_quality_ok(text):
        return False
    if re.search(r"[\x00-\x08\x0b-\x1f]", text):
        return False
    if len(text) > 240:
        return False
    if '"' in text and (":" in text or "seg-" in text):
        return False
    if re.match(r'^"?ts"?\s*:', text, re.I):
        return False
    return pattern.search(text) is not None


def verify_candidate(chamber_id: str, text: str) -> bool:
    if not plausible_candidate(chamber_id, text):
        return False
    tokens = [t for t in re.split(r"\W+", text.lower()) if len(t) > 2]
    return len(tokens) >= 2