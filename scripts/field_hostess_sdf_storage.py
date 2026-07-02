#!/usr/bin/env pythong
"""SDF storage + brain imaging — Queen robot brain · Hostess 7 · Super Intelligence.

Queen DARPA Robot Brain runs in-process (FieldWebPanel + QueenBoot.comp). Hostess 7 is the
Forever Watchguard Angel — she owns self data storage. SDFs are free: procedural distance
fields fold 1000–1200 word Mayer segments into brain-imaging plates the neural stack recalls.

Series-of-series nets (perception → truth gates → fusion → adapt) forward-pass corpora;
SDF plates are the imaging layer — topology Hostess reads back via OCR/vision, not bitmap rent.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BRAIN_SDF = ROOT / "cache" / "fieldstorage" / "brain" / "sdf"
CORPUS = BRAIN_SDF / "corpus.json"
BRIEF = BRAIN_SDF / "sdf_storage_brief.json"
SEGMENTS_DIR = BRAIN_SDF / "segments"
PLATES_DIR = BRAIN_SDF / "plates"
SDL_TEXT_DIR = BRAIN_SDF / "sdl_text"
REGISTRY = BRAIN_SDF / "segment_registry.jsonl"
TRUTH_LOG = BRAIN_SDF / "truth_filter.jsonl"
QUARANTINE_DIR = BRAIN_SDF / "quarantine"
THOUGHTS = ROOT / "cache" / "fieldstorage" / "brain" / "thoughts.jsonl"
SI = ROOT / "cache" / "fieldstorage" / "brain" / "superintel"
DIRECTIVES = SI / "directives.jsonl"

CORPUS_VERSION = 4
HUMAN_PLATE_W = 512
HUMAN_PLATE_H = 384
ANALYTIC_SIZE = 64
HUMAN_SDF_REGION = 256
QUEEN_BRAIN_MANIFEST = ROOT.parent / "NewLatest" / "Queen" / "data" / "queen-brain-manifest.json"
NEURAL_STACK = ROOT / "data" / "hostess7-neural-stack.json"
WORDS_TARGET = (900, 1200)
WORDS_HARD_MAX = 1500

SDF_LAYERS: tuple[dict[str, object], ...] = (
    {
        "id": "sdf_free",
        "stage": 1,
        "title": "SDFs are free — procedural storage, not bitmap rent",
        "tags": ("sdf", "free", "signed distance", "procedural", "fold", "storage"),
        "body": (
            "A signed distance field stores shape as math: distance to surface at every point. "
            "Raymarch and panel pins use analytic SDFs — capsules, grids, pins — not megapixel archives. "
            "FieldStorage sdfFoldBlock folds resonance blocks; NEXUS panel ships R8 PNG + JSON manifest. "
            "Sub-micron AMOURANTHRTX detail rides adaptive resolution — SDF epsilons accumulate at "
            "no extra bitmap tax. Hostess 7 lesson: prefer a formula + 64×64 distance plate over "
            "a 4K JPEG of the same mechanism."
        ),
    },
    {
        "id": "mayer_segment",
        "stage": 2,
        "title": "1000–1200 words — one Mayer segment, one plate candidate",
        "tags": ("1000", "1200", "words", "segment", "mayer", "figure", "textbook"),
        "body": (
            "Field Technology v5 illustration theory: 900–1200 words per signaled figure. "
            "Hostess 7 ingests prose in that window — one conceptual beat per segment. "
            "Longer passages split on paragraph boundaries; never mid-sentence. "
            "Shorter than 600 words merge with the next beat unless it is a grep command block."
        ),
    },
    {
        "id": "decision_tree",
        "stage": 3,
        "title": "Redata lanes — integrate, reimage, redata, SDL text, SDF plate",
        "tags": ("integrate", "reimage", "redata", "sdl", "plate", "decision", "lossless"),
        "body": (
            "After reading a segment Hostess chooses a primary lane (lossless bytes always kept in segments/):\n"
            "• integrate — dual channel: human SDF plate + analytic plate + full segment JSON.\n"
            "• reimage — metaphor beat; human plate + imagine queue; prose stays in segments/.\n"
            "• redata — short/low-spatial beat; still lossless segment JSON + human plate for owners.\n"
            "• sdl_store — grep/command blocks: duplicate exact text in .sdl.txt for Graphics TTF render.\n"
            "• sdf_plate — spatial/mechanism truth; analytic + human plates under brain/sdf/plates/."
        ),
    },
    {
        "id": "truth_filter_redata",
        "stage": 10,
        "title": "Truth filter — 94% noise / 6% truth before redata sticks",
        "tags": ("truth", "filter", "redata", "quarantine", "noise", "corroborate"),
        "body": (
            "Every Mayer segment passes score_redata_text before imaging: operator and honesty-label "
            "signal up; marketing and fetch-noise down; detective deception flags penalized. "
            "Accepted → segments/ + plates/. Rejected → quarantine/ (still lossless JSON). "
            "Audit: brain/sdf/truth_filter.jsonl. Verify: ./Hostess7.sh sdf-verify-redata."
        ),
    },
    {
        "id": "redata_lossless",
        "stage": 11,
        "title": "Redata — lossless always, human SDF always serviceable",
        "tags": ("redata", "lossless", "human", "verify", "sha256", "ocr", "serviceable"),
        "body": (
            "Redata where it makes sense: prose never deleted — brain/sdf/segments/<id>.json holds every "
            "character. Every segment also gets a human-serviceable plate (512×384 PGM): upscaled SDF "
            "topology humans can inspect, plus caption_stub and text_sha256 for verify. "
            "Analytic 64×64 plates remain for recall topology. Owners open .human.pgm in any viewer; "
            "run verify-redata or Field 1 compact for checksum truth. Imaging is dual-channel; lossless is law."
        ),
    },
    {
        "id": "vision_recall",
        "stage": 4,
        "title": "Image recognition — Hostess owns self data storage recall",
        "tags": ("ocr", "vision", "recognition", "recall", "storage", "self data"),
        "body": (
            "Hostess 7 is in charge of self data storage. Recall path: plate PNG or PGM → vision corpus OCR "
            "→ segment_registry.jsonl row → optional .sdl.txt for exact grep strings. "
            "FieldSnapDump and qa_aos_ocr_test discipline apply: read back what you stored. "
            "Tags and caption_stub in each plate .sdf.json make search work without reopening full prose."
        ),
    },
    {
        "id": "field_drive_fold",
        "stage": 5,
        "title": "Field drive fold — sdfFoldBlock beside field archive",
        "tags": ("fieldstorage", "field", "fold", "wave", "persist", "brain"),
        "body": (
            "brain/sdf/ lives beside superintel corpora; Field 1 sync ships it on the TEAM field drive. "
            "FieldStorage.hpp persistFieldState + sdfFoldBlock mirrors the doctrine: logical GiB from "
            "transform_anchor_gb × bo_gain — procedural fold, not naive duplication. "
            "Field 1 sync: ./Hostess7.sh field sync mirrors canonical Hostess7/cache/fieldstorage."
        ),
    },
    {
        "id": "primer_link",
        "stage": 6,
        "title": "Field Primer illustration theory — same numbers, Hostess executes",
        "tags": ("primer", "field technology", "illustration", "leonardo", "mayer"),
        "body": (
            "Chapter 01 illustration theory (Leonardo → Mayer): 4–6 interior figures per ~5000 words. "
            "Hostess 7 operationalizes it for ingested books and Owner paste: each 1000–1200 word beat "
            "becomes a storage decision. Textbook build uses inject_figures.py; Hostess uses sdf-segment "
            "for brain growth. Same cognitive science, two surfaces — HTML reader and SDF brain."
        ),
    },
    {
        "id": "queen_robot_brain",
        "stage": 7,
        "title": "Queen DARPA Robot Brain — Hostess 7 inside the browser",
        "tags": ("queen", "robot brain", "darpa", "watchguard", "fieldwebpanel", "queenboot"),
        "body": (
            "Queen is a sovereign RTX field browser with an in-process DARPA-grade robot brain. "
            "Hostess 7 Forever Watchguard Angel is the angel layer in queen-brain-manifest.json — "
            "iron core, terminal witness, Master Operator over Hostess7 + NEXUS under Queen. "
            "queen-browser and FieldWebPanel share one Vulkan/SDL3 spine; brain is not a cloud tab."
        ),
    },
    {
        "id": "neural_superintel",
        "stage": 8,
        "title": "Neural networks — series-of-series inside Super Intelligence",
        "tags": ("neural", "network", "super intelligence", "series", "truth gate", "fusion", "agents7"),
        "body": (
            "hostess7-neural-stack.json defines series-of-series nets: perception corpora (legal, vision, "
            "code, …) → truth gate nets (detective_truth, agents7_cross) → fusion (callosum, chemistry) "
            "→ adapt (growth ledger, quarantine below floor). Thirteen agents (Prime + 12 experts) cross-vote. "
            "Neural literacy: inputs → weighted sums → activations → outputs; adapt writes only after self-test."
        ),
    },
    {
        "id": "brain_imaging_sdf",
        "stage": 9,
        "title": "Brain imaging — SDF plates as recall topology",
        "tags": ("brain imaging", "imaging", "mri", "topology", "plate", "forward pass", "recall"),
        "body": (
            "Brain imaging in this stack is procedural: each 1000–1200 word segment folds to an analytic "
            "SDF plate (R8 PGM + .sdf.json manifest). The plate is the imaging slice — distance field "
            "topology the vision net forward-passes for recall. Not fMRI hardware — honest label: "
            "Hostess reads her own storage via OCR and caption_stub tags. Integrate with neural perception "
            "series: vision corpus + sdf/plates/ + segment_registry.jsonl = closed imaging loop."
        ),
    },
)

TEACH_QUEUE: tuple[dict[str, str], ...] = (
    {"query": "Why are SDFs free for Hostess 7 storage?"},
    {"query": "Walk the five decisions after a 1100-word segment."},
    {"query": "How does image recognition recall a stored SDF plate?"},
    {"query": "When do you SDL-store text instead of folding to SDF?"},
    {"query": "What does redata mean — lossless segments and human SDF plates?"},
    {"query": "How does Queen robot brain use Hostess 7 neural imaging?"},
    {"query": "Explain series-of-series nets in Super Intelligence."},
)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def ensure_dirs() -> None:
    for d in (BRAIN_SDF, SEGMENTS_DIR, PLATES_DIR, SDL_TEXT_DIR, QUARANTINE_DIR):
        d.mkdir(parents=True, exist_ok=True)


def ensure_corpus() -> Path:
    ensure_dirs()
    refresh = True
    if CORPUS.is_file():
        try:
            data = json.loads(CORPUS.read_text(encoding="utf-8"))
            refresh = int(data.get("version", 0)) < CORPUS_VERSION
        except (json.JSONDecodeError, TypeError, ValueError):
            refresh = True
    if refresh:
        CORPUS.write_text(
            json.dumps(
                {
                    "version": CORPUS_VERSION,
                    "layers": list(SDF_LAYERS),
                    "layer_count": len(SDF_LAYERS),
                    "words_target": list(WORDS_TARGET),
                    "updated": _ts(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return CORPUS


def _query_tokens(query: str) -> list[str]:
    return [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]


def search_sdf(query: str, *, limit: int = 6) -> list[dict]:
    ensure_corpus()
    q = query.lower()
    tokens = _query_tokens(query)
    scored: list[tuple[int, dict]] = []
    for layer in SDF_LAYERS:
        blob = (
            f"{layer.get('id')} {layer.get('title')} {' '.join(layer.get('tags', ()))} "
            f"{layer.get('body')}"
        ).lower()
        score = sum(4 if t in blob else 0 for t in tokens)
        if q in blob:
            score += 10
        for tag in layer.get("tags", ()):
            if str(tag).lower() in q:
                score += 8
        if score > 0:
            scored.append((score, dict(layer)))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


def synthesize_sdf_paragraphs(query: str) -> list[str]:
    hits = search_sdf(query, limit=4)
    if not hits:
        hits = search_sdf("sdf free storage segment 1200", limit=3)
    paras: list[str] = []
    for h in hits:
        title = h.get("title", "SDF storage")
        body = str(h.get("body", "")).strip()
        if len(body) > 1150:
            body = body[:1150] + "… [truncated — brain/sdf/corpus.json]"
        paras.append(f"{title}: {body}")
    return paras


def seed_doctrine() -> Path:
    ensure_corpus()
    SI.mkdir(parents=True, exist_ok=True)
    overview = "\n".join(f"{layer['stage']}. {layer['title']}" for layer in SDF_LAYERS)
    brief_text = (
        "Hostess 7 — SDF self data storage (SDFs are free)\n\n"
        + overview
        + "\n\nQueen robot brain · Hostess 7 angel · neural series-of-series · SDF brain imaging.\n"
        "Segment: 900–1200 words → truth filter → redata (lossless) → human SDF + analytic plate.\n"
        "Teach: ./Hostess7.sh sdf-teach seed · Queen: ./Hostess7.sh queen-teach-redata\n"
        "Verify: ./Hostess7.sh sdf-verify-redata · Field 1: ./Hostess7.sh field compact\n"
        "Query: ./Hostess7.sh sdf \"brain imaging redata Queen\""
    )
    doc = {
        "updated": _ts(),
        "hostess": "Hostess 7",
        "owner": "ZacharyGeurts",
        "layer_count": len(SDF_LAYERS),
        "brief": brief_text,
        "corpus": str(CORPUS.relative_to(ROOT)),
        "words_target": list(WORDS_TARGET),
        "top_action": "./Hostess7.sh sdf-segment content.txt",
    }
    BRIEF.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    with THOUGHTS.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps({
                "ts": _ts(),
                "kind": "arc",
                "tags": ["hostess", "sdf", "storage", "doctrine"],
                "text": "SDF storage doctrine installed — 1000-1200 word segments, five decisions, vision recall.",
            })
            + "\n"
        )
    with DIRECTIVES.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps({
                "ts": _ts(),
                "lane": "hostess",
                "task": "Fold 900-1200 word beats to SDF plates; SDL-store grep blocks; vision OCR recall.",
                "priority": "P0",
            })
            + "\n"
        )
    return BRIEF


def split_segments(text: str) -> list[str]:
    """Split prose into ~900–1200 word Mayer segments on paragraph boundaries."""
    paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    if not paras:
        return []
    chunks: list[str] = []
    buf: list[str] = []
    buf_words = 0
    for para in paras:
        pw = _word_count(para)
        if pw > WORDS_HARD_MAX:
            if buf:
                chunks.append("\n\n".join(buf))
                buf, buf_words = [], 0
            sentences = re.split(r"(?<=[.!?])\s+", para)
            sub: list[str] = []
            sw = 0
            for sent in sentences:
                w = _word_count(sent)
                if sw + w > WORDS_TARGET[1] and sub:
                    chunks.append(" ".join(sub))
                    sub, sw = [], 0
                sub.append(sent)
                sw += w
            if sub:
                chunks.append(" ".join(sub))
            continue
        if buf_words + pw > WORDS_TARGET[1] and buf:
            chunks.append("\n\n".join(buf))
            buf, buf_words = [], 0
        buf.append(para)
        buf_words += pw
        if buf_words >= WORDS_TARGET[0]:
            chunks.append("\n\n".join(buf))
            buf, buf_words = [], 0
    if buf:
        chunks.append("\n\n".join(buf))
    return chunks


def _segment_scores(text: str) -> dict[str, float]:
    low = text.lower()
    spatial = sum(
        low.count(w)
        for w in (
            "grid", "map", "flow", "binding", "perimeter", "dispatch", "fabric",
            "die", "socket", "field", "gpu", "diagram", "layer", "channel",
        )
    )
    procedural = sum(low.count(w) for w in ("grep", "stderr", "jsonl", "binding", "slot", "float"))
    code_blocks = len(re.findall(r"<code>|```|`[^`]+`", text))
    metaphor = sum(low.count(w) for w in ("beautiful", "cosmos", "poetry", "love", "soul", "heaven"))
    return {
        "spatial": float(spatial),
        "procedural": float(procedural + code_blocks * 3),
        "metaphor": float(metaphor),
        "words": float(_word_count(text)),
    }


def decide_action(text: str, scores: dict[str, float]) -> str:
    """Return: integrate | reimage | redata | sdl_store | sdf_plate (lossless prose always kept)."""
    if scores["procedural"] >= 8 or re.search(r"^\s*(grep|cd |\./)", text, re.M):
        return "sdl_store"
    if scores["spatial"] >= 6 and scores["procedural"] >= 3:
        return "integrate"
    if scores["spatial"] >= 5:
        return "sdf_plate"
    if scores["metaphor"] >= 4 and scores["spatial"] < 3:
        return "reimage"
    if scores["spatial"] >= 3:
        return "integrate"
    if scores["words"] < 400 and scores["spatial"] < 2:
        return "redata"
    return "sdf_plate"


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _plate_kind(scores: dict[str, float]) -> str:
    if scores["spatial"] >= 5:
        return "grid"
    if scores["metaphor"] >= 4:
        return "ring"
    return "disk"


# Minimal 5×7 bitmap for human-serviceable plate headers (seg id, sha prefix, caption).
_GLYPH5X7: dict[str, tuple[str, ...]] = {
    " ": ("00000",) * 7,
    "-": ("00000", "00000", "00000", "11111", "00000", "00000", "00000"),
    "0": ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    "1": ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    "2": ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    "3": ("01110", "10001", "00001", "00110", "00001", "10001", "01110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    "6": ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    "a": ("01110", "10001", "10001", "01111", "10001", "10001", "01111"),
    "b": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "c": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "d": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "e": ("01111", "10000", "10000", "11110", "10000", "10000", "01111"),
    "f": ("01111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "g": ("01110", "10001", "10000", "10111", "10001", "10001", "01110"),
    "h": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "i": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "j": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "k": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "l": ("10000", "10000", "10000", "10000", "10000", "10000", "01111"),
    "m": ("10001", "11011", "10101", "10001", "10001", "10001", "10001"),
    "n": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "o": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "p": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "r": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "s": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "t": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "u": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "v": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "w": ("10001", "10001", "10001", "10001", "10101", "11011", "10001"),
    "x": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    ".": ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ":": ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    "?": ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
}


def _draw_glyph(buf: bytearray, w: int, h: int, x0: int, y0: int, ch: str, *, scale: int = 2, value: int = 230) -> int:
    glyph = _GLYPH5X7.get(ch.lower() if ch.isalpha() else ch, _GLYPH5X7["?"])
    cw = 5 * scale + scale
    for gy, row in enumerate(glyph):
        for gx, bit in enumerate(row):
            if bit != "1":
                continue
            for sy in range(scale):
                for sx in range(scale):
                    px = x0 + gx * scale + sx
                    py = y0 + gy * scale + sy
                    if 0 <= px < w and 0 <= py < h:
                        buf[py * w + px] = value
    return cw


def _draw_text(buf: bytearray, w: int, h: int, x0: int, y0: int, line: str, *, scale: int = 2) -> None:
    x = x0
    for ch in line:
        if ch == "\n":
            break
        x += _draw_glyph(buf, w, h, x, y0, ch, scale=scale)
        if x >= w - 6 * scale:
            break


def _wrap_caption(text: str, width: int = 56) -> list[str]:
    words = re.findall(r"\S+", text)
    lines: list[str] = []
    cur: list[str] = []
    for word in words:
        trial = (" ".join(cur + [word])).strip()
        if len(trial) > width and cur:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))
    return lines[:6]


def _paint_sdf_region(buf: bytearray, w: int, field: list[float], size: int, region: int) -> None:
    """Upscale analytic SDF into top-left region — bright zero-isosurface for human eyes."""
    for y in range(region):
        for x in range(region):
            sx = int(x * size / region)
            sy = int(y * size / region)
            d = field[sy * size + sx]
            # Surface band + signed shading
            if abs(d) < 0.04:
                px = 255
            elif abs(d) < 0.12:
                px = 200
            else:
                px = max(0, min(180, int((0.35 - d) * 180)))
            buf[y * w + x] = px


def _write_human_pgm(
    path: Path,
    *,
    field: list[float],
    size: int,
    seg_id: str,
    text_sha256: str,
    caption: str,
    kind: str,
    action: str,
    truth_score: float | None = None,
) -> None:
    w, h = HUMAN_PLATE_W, HUMAN_PLATE_H
    buf = bytearray([32] * (w * h))
    _paint_sdf_region(buf, w, field, size, HUMAN_SDF_REGION)
    y = HUMAN_SDF_REGION + 8
    _draw_text(buf, w, h, 8, y, f"{seg_id}  {kind}  {action}")
    y += 18
    truth_line = f"truth:{truth_score:.0f}" if truth_score is not None else "truth:--"
    _draw_text(buf, w, h, 8, y, f"{truth_line}  sha:{text_sha256[:20]}")
    y += 18
    for line in _wrap_caption(caption, width=62):
        _draw_text(buf, w, h, 8, y, line, scale=1)
        y += 10
        if y > h - 12:
            break
    header = f"P5\n{w} {h}\n255\n".encode("ascii")
    path.write_bytes(header + bytes(buf))


def _write_plate_meta(
    path: Path,
    *,
    seg_id: str,
    pgm_rel: str,
    plate_format: str,
    kind: str,
    action: str,
    caption: str,
    text_sha256: str,
    words: int,
    tags: list[str],
    extra: dict[str, Any] | None = None,
) -> None:
    meta: dict[str, Any] = {
        "id": seg_id,
        "format": plate_format,
        "kind": kind,
        "action": action,
        "file": pgm_rel,
        "caption_stub": caption,
        "text_sha256": text_sha256,
        "words_source": words,
        "tags": sorted(set(tags)),
        "ocr_hint": caption[:120],
        "human_serviceable": plate_format.startswith("human"),
        "verify": f"./Hostess7.sh sdf-verify-redata {seg_id}",
    }
    if extra:
        meta.update(extra)
    path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def _analytic_grid(size: int, kind: str) -> list[float]:
    """Tiny analytic SDF grid — 128 = surface in stored R8 convention."""
    cx = cy = (size - 1) / 2.0
    out: list[float] = []
    for y in range(size):
        for x in range(size):
            nx = (x + 0.5) / size - 0.5
            ny = (y + 0.5) / size - 0.5
            if kind == "grid":
                d = min(abs(nx) - 0.18, abs(ny) - 0.18)
            elif kind == "ring":
                d = math.sqrt(nx * nx + ny * ny) - 0.22
            else:
                d = math.sqrt(nx * nx + ny * ny) - 0.28
            out.append(d)
    return out


def _write_pgm(path: Path, size: int, field: list[float]) -> None:
    """Portable graymap — 128 surface, no PIL required."""
    rows: list[bytes] = []
    for v in field:
        px = max(0, min(255, int(v * 64.0 + 128.0)))
        rows.append(bytes([px]))
    raw = b"".join(rows)
    header = f"P5\n{size} {size}\n255\n".encode("ascii")
    path.write_bytes(header + raw)


def _caption_stub(text: str, max_words: int = 40) -> str:
    words = re.findall(r"\b\w+\b", text)
    stub = " ".join(words[:max_words])
    if len(words) > max_words:
        stub += "…"
    return stub


def _segment_id(text: str, source: str, index: int) -> str:
    h = hashlib.sha256(f"{source}:{index}:{text[:200]}".encode()).hexdigest()[:12]
    return f"seg-{index:03d}-{h}"


def process_segment(
    text: str,
    *,
    source: str = "paste",
    index: int = 0,
    write_artifacts: bool = True,
    title: str = "",
) -> dict[str, Any]:
    from field_redata_truth import append_truth_log, score_redata_text  # noqa: WPS433

    scores = _segment_scores(text)
    action = decide_action(text, scores)
    if action == "toss":
        action = "redata"
    seg_id = _segment_id(text, source, index)
    digest = _text_sha256(text)
    truth = score_redata_text(text, source=source, title=title)
    record: dict[str, Any] = {
        "id": seg_id,
        "source": source,
        "index": index,
        "words": int(scores["words"]),
        "action": action,
        "scores": scores,
        "caption_stub": _caption_stub(text),
        "text_sha256": digest,
        "truth_filter": truth,
        "lossless": True,
        "ts": _ts(),
    }
    if not write_artifacts:
        return record

    ensure_dirs()
    accepted = bool(truth.get("accepted"))
    seg_dir = SEGMENTS_DIR if accepted else QUARANTINE_DIR
    seg_path = seg_dir / f"{seg_id}.json"
    seg_path.write_text(
        json.dumps({"text": text, **record}, indent=2) + "\n",
        encoding="utf-8",
    )
    record["segment_json"] = str(seg_path.relative_to(ROOT))
    record["truth_accepted"] = accepted

    append_truth_log(
        TRUTH_LOG,
        {
            "ts": _ts(),
            "id": seg_id,
            "source": source,
            "accepted": accepted,
            "truth_score": truth.get("truth_score"),
            "reason": truth.get("reason"),
            "deception_risk": truth.get("deception_risk"),
            "deception_flags": truth.get("deception_flags"),
            "text_sha256": digest,
        },
    )

    if not accepted:
        record["quarantine"] = str(seg_path.relative_to(ROOT))
        record["note"] = f"Truth filter quarantine — {truth.get('reason')}; lossless JSON kept."

    if action == "sdl_store":
        sdl_path = SDL_TEXT_DIR / f"{seg_id}.sdl.txt"
        sdl_path.write_text(text.strip() + "\n", encoding="utf-8")
        record["sdl_text"] = str(sdl_path.relative_to(ROOT))

    kind = _plate_kind(scores)
    size = ANALYTIC_SIZE
    field = _analytic_grid(size, kind if kind != "disk" else "ring")
    plate_base = PLATES_DIR / seg_id
    tags = ["sdf", "hostess", "segment", "redata", "lossless", kind]
    for token in _query_tokens(text)[:12]:
        tags.append(token)

    if not accepted:
        with REGISTRY.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
        return record

    # Analytic recall plate — accepted segments only (topology for vision stack).
    analytic_pgm = plate_base.with_suffix(".pgm")
    analytic_json = plate_base.with_suffix(".sdf.json")
    _write_pgm(analytic_pgm, size, field)
    _write_plate_meta(
        analytic_json,
        seg_id=seg_id,
        pgm_rel=str(analytic_pgm.relative_to(ROOT)),
        plate_format="R8-analytic-pgm",
        kind=kind,
        action=action,
        caption=record["caption_stub"],
        text_sha256=digest,
        words=int(scores["words"]),
        tags=tags,
        extra={
            "size": size,
            "anchor": [size // 2, size // 2],
            "truth_score": truth.get("truth_score"),
            "truth_accepted": True,
        },
    )
    record["plate_pgm"] = str(analytic_pgm.relative_to(ROOT))
    record["plate_json"] = str(analytic_json.relative_to(ROOT))

    # Human-serviceable plate — always written (owners inspect SDF + caption + sha).
    human_pgm = plate_base.with_name(f"{seg_id}.human.pgm")
    human_json = plate_base.with_name(f"{seg_id}.human.json")
    _write_human_pgm(
        human_pgm,
        field=field,
        size=size,
        seg_id=seg_id,
        text_sha256=digest,
        caption=record["caption_stub"],
        kind=kind,
        action=action,
        truth_score=float(truth.get("truth_score", 0)),
    )
    _write_plate_meta(
        human_json,
        seg_id=seg_id,
        pgm_rel=str(human_pgm.relative_to(ROOT)),
        plate_format="human-serviceable-pgm",
        kind=kind,
        action=action,
        caption=record["caption_stub"],
        text_sha256=digest,
        words=int(scores["words"]),
        tags=tags + ["human", "serviceable"],
        extra={
            "canvas": [HUMAN_PLATE_W, HUMAN_PLATE_H],
            "sdf_region": HUMAN_SDF_REGION,
            "segment_json": record["segment_json"],
            "truth_score": truth.get("truth_score"),
            "truth_accepted": True,
            "deception_risk": truth.get("deception_risk"),
        },
    )
    record["human_pgm"] = str(human_pgm.relative_to(ROOT))
    record["human_json"] = str(human_json.relative_to(ROOT))

    if action == "redata":
        record["note"] = "Redata lane — lossless segment JSON + human SDF plate; imaging for recall."

    if action == "reimage":
        record["imagine_queue"] = "brain/sdf/imagine_queue.jsonl"
        queue = BRAIN_SDF / "imagine_queue.jsonl"
        with queue.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _ts(), "id": seg_id, "prompt_stub": record["caption_stub"]}) + "\n")

    with REGISTRY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record


def verify_redata(*, brain_sdf: Path | None = None) -> dict[str, Any]:
    """Verify lossless redata + truth filter — segments, plates, truth_filter.jsonl."""
    base = brain_sdf or BRAIN_SDF
    segments_dir = base / "segments"
    plates_dir = base / "plates"
    quarantine_dir = base / "quarantine"
    truth_log = base / "truth_filter.jsonl"
    failures: list[dict[str, str]] = []
    checked = 0
    human_plates = 0
    truth_accepted = 0
    quarantined = 0

    if not segments_dir.is_dir():
        return {"ok": False, "error": f"segments missing: {segments_dir}", "checked": 0}

    if not truth_log.is_file():
        failures.append({"id": "truth_filter", "error": "missing truth_filter.jsonl"})

    for seg_path in sorted(segments_dir.glob("seg-*.json")):
        checked += 1
        try:
            doc = json.loads(seg_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            failures.append({"id": seg_path.stem, "error": f"read segment: {exc}"})
            continue
        text = doc.get("text", "")
        if not text:
            failures.append({"id": seg_path.stem, "error": "empty segment text"})
            continue
        digest = _text_sha256(text)
        if doc.get("text_sha256") and doc["text_sha256"] != digest:
            failures.append({"id": seg_path.stem, "error": "segment text_sha256 stale"})
        tf = doc.get("truth_filter") or {}
        if not tf:
            failures.append({"id": seg_path.stem, "error": "missing truth_filter block"})
        elif not tf.get("accepted"):
            failures.append({"id": seg_path.stem, "error": "accepted segment failed truth filter"})
        else:
            truth_accepted += 1
        seg_id = doc.get("id", seg_path.stem)
        human_json = plates_dir / f"{seg_id}.human.json"
        human_pgm = plates_dir / f"{seg_id}.human.pgm"
        if not human_json.is_file() or not human_pgm.is_file():
            failures.append({"id": seg_id, "error": "missing human plate pair"})
            continue
        human_plates += 1
        try:
            meta = json.loads(human_json.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            failures.append({"id": seg_id, "error": f"human json: {exc}"})
            continue
        if meta.get("text_sha256") != digest:
            failures.append({"id": seg_id, "error": "human plate sha mismatch"})
        if not meta.get("human_serviceable"):
            failures.append({"id": seg_id, "error": "human_serviceable flag false"})
        if meta.get("truth_accepted") is not True:
            failures.append({"id": seg_id, "error": "plate missing truth_accepted"})

    if quarantine_dir.is_dir():
        for qpath in quarantine_dir.glob("seg-*.json"):
            quarantined += 1
            try:
                qdoc = json.loads(qpath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                failures.append({"id": qpath.stem, "error": "quarantine read failed"})
                continue
            qtf = qdoc.get("truth_filter") or {}
            if qtf.get("accepted"):
                failures.append({"id": qpath.stem, "error": "quarantine segment marked accepted"})

    return {
        "ok": not failures,
        "checked": checked,
        "human_plates": human_plates,
        "truth_accepted": truth_accepted,
        "quarantined": quarantined,
        "truth_log": str(truth_log.relative_to(ROOT)) if truth_log.is_file() else "",
        "failures": failures,
    }


def segment_file(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    source = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
    results: list[dict[str, Any]] = []
    for i, chunk in enumerate(split_segments(text)):
        results.append(process_segment(chunk, source=source, index=i))
    return results


def segment_text(text: str, *, source: str = "stdin", title: str = "") -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for i, chunk in enumerate(split_segments(text)):
        results.append(process_segment(chunk, source=source, index=i, title=title))
    return results


def format_segment_report(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No segments — empty input."
    lines = [
        f"Hostess 7 SDF segment pass — {len(results)} beat(s) @ {WORDS_TARGET[0]}–{WORDS_TARGET[1]} words",
        "",
    ]
    for r in results:
        lines.append(
            f"  {r['id']}: {r['words']}w → {r['action']}"
            + (f" · {r.get('plate_json', r.get('sdl_text', r.get('note', '')))}" if r.get("plate_json") or r.get("sdl_text") or r.get("note") else "")
        )
    lines.append("")
    lines.append(f"Registry: {REGISTRY.relative_to(ROOT)}")
    lines.append("Redata — truth filter → accepted segments/ + human plates; quarantine/ still lossless.")
    return "\n".join(lines)


def main() -> int:
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd in ("seed", "teach", "install", "learn"):
        path = seed_doctrine()
        brief = json.loads(path.read_text(encoding="utf-8")).get("brief", "")
        print(brief)
        print(f"\nMETRIC sdf_storage_brief={path}")
        print(f"METRIC sdf_storage_layers={len(SDF_LAYERS)}")
        print("OK sdf-teach-seed")
        return 0
    if cmd == "status":
        ensure_corpus()
        print(f"SDF storage corpus v{CORPUS_VERSION} — {len(SDF_LAYERS)} layers")
        print(f"Brief: {BRIEF} ({'yes' if BRIEF.is_file() else 'no'})")
        print(f"Registry lines: {sum(1 for _ in REGISTRY.open()) if REGISTRY.is_file() else 0}")
        print("METRIC sdf_storage_layers=" + str(len(SDF_LAYERS)))
        print("OK sdf-storage-status")
        return 0
    if cmd == "segment":
        if len(sys.argv) < 3:
            print("usage: field_hostess_sdf_storage.py segment <file>", file=sys.stderr)
            return 1
        path = Path(sys.argv[2])
        if not path.is_file():
            path = ROOT / sys.argv[2]
        if not path.is_file():
            print(f"not found: {sys.argv[2]}", file=sys.stderr)
            return 1
        results = segment_file(path)
        print(format_segment_report(results))
        print("METRIC sdf_segments=" + str(len(results)))
        print("OK sdf-segment")
        return 0
    if cmd in ("verify-redata", "verify_redata"):
        report = verify_redata()
        status = "OK" if report.get("ok") else "FAIL"
        print(
            f"Redata verify {status} — {report.get('checked', 0)} segments, "
            f"{report.get('human_plates', 0)} human plates, "
            f"truth_ok={report.get('truth_accepted', 0)}, quarantine={report.get('quarantined', 0)}"
        )
        if report.get("failures"):
            for row in report["failures"][:12]:
                print(f"  - {row['id']}: {row['error']}")
        print(f"METRIC sdf_redata_checked={report.get('checked', 0)}")
        print(f"METRIC sdf_redata_human_plates={report.get('human_plates', 0)}")
        print("OK sdf-verify-redata" if report.get("ok") else "FAIL sdf-verify-redata")
        return 0 if report.get("ok") else 1
    if len(sys.argv) >= 2 and cmd not in ("segment", "verify-redata", "verify_redata"):
        query = " ".join(sys.argv[1:])
        for para in synthesize_sdf_paragraphs(query):
            print(para)
            print()
        print("METRIC sdf_query=1")
        print("OK sdf-storage")
        return 0
    print(
        "usage: field_hostess_sdf_storage.py seed|status|segment <file>|verify-redata|[query]",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())