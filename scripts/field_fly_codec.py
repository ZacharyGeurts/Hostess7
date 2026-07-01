#!/usr/bin/env pythong
"""FLD1 — Field Lexicon Delta. Lossless fly compression for brain JSON/text.

Invisible to users: readers detect FLD1 magic and decompress on read.
Optimized for corpus.json mold (repeated keys, long body strings) — not plain RLE.

  pythong scripts/field_fly_codec.py pack <file>
  pythong scripts/field_fly_codec.py unpack <file>
  pythong scripts/field_fly_codec.py bench <file>
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import time
import zlib
from pathlib import Path
from typing import Any

MAGIC = b"FLD1"
VERSION = 1
METHOD_ZLIB = 0
METHOD_JSON_LEX = 1

# Corpus / brain JSON repeats these constantly — single-byte token IDs (0x01–0x7F)
_JSON_LEXICON: tuple[bytes, ...] = (
    b'"id":',
    b'"title":',
    b'"tags":',
    b'"body":',
    b'"version":',
    b'"domains":',
    b'"category":',
    b'"summary":',
    b'"path":',
    b'"cmd":',
    b'"license":',
    b'"author":',
    b'"format":',
    b'"corpus_path":',
    b'"lane":',
    b'"intent":',
    b'"workspace":',
    b'"role":',
    b'"emoji":',
    b'"name":',
    b'"description":',
    b'"updated":',
    b'"created":',
    b'"compression":',
    b'"char_count":',
    b'"line_count":',
    b'"text_sha256":',
    b'"fetch_url":',
    b'"grade_band":',
    b'"subject":',
    b'"publisher":',
    b'"category_index":',
    b'"domain_count":',
    b'"corpus_rel":',
    b'"extra":',
    b'"dynamic":',
    b'"fields":',
    b'"pillars":',
    b'"lessons":',
    b'"lesson":',
    b'"registry":',
    b'"reality":',
    b'"warfare":',
    b'"medical":',
    b'"legal":',
    b'"physics":',
    b'"chemistry":',
    b'"english":',
    b'"detective":',
    b'"beyond":',
    b'"code":',
    b'"vision":',
    b'"k12":',
    b'"people":',
    b'"agents":',
    b'"internet":',
    b'"running":',
    b'"agent_count":',
    b'"Hostess7":',
    b'"Hostess 7":',
    b'"Field is THE thing":',
    b'"cache/fieldstorage":',
    b'"scripts/":',
    b'"brain/":',
    b'"superintel/":',
    b'"corpus.json":',
    b'"indent":',
    b'"tags": [',
    b'"domains": [',
    b'"categories": [',
    b'",\n',
    b'",\n      ',
    b'",\n    ',
    b'": [\n',
    b'": {\n',
    b'      "',
    b'    "',
    b'  "',
    b'"true"',
    b'"false"',
    b'"null"',
)

# Sort longest-first so greedy substitution is safe
_LEX_SORTED = sorted(_JSON_LEXICON, key=len, reverse=True)
_LEX_TO_ID = {tok: i + 1 for i, tok in enumerate(_LEX_SORTED)}
_ID_TO_LEX = {i + 1: tok for i, tok in enumerate(_LEX_SORTED)}
_ESC = b"\x1e"


def is_fly(data: bytes) -> bool:
    return len(data) >= 10 and data[:4] == MAGIC


def _lex_encode(raw: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        if raw[i] == 0x1E:
            out.append(0x1E)
            out.append(0x00)
            i += 1
            continue
        matched = False
        for tok in _LEX_SORTED:
            tl = len(tok)
            if i + tl <= n and raw[i : i + tl] == tok:
                tid = _LEX_TO_ID[tok]
                out.append(0x1E)
                out.extend(struct.pack("<H", tid))
                i += tl
                matched = True
                break
        if not matched:
            out.append(raw[i])
            i += 1
    return bytes(out)


def _lex_decode(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    n = len(data)
    while i < n:
        if data[i] != 0x1E:
            out.append(data[i])
            i += 1
            continue
        i += 1
        if i >= n:
            break
        if data[i] == 0x00:
            out.append(0x1E)
            i += 1
            continue
        if i + 1 >= n:
            break
        tid = struct.unpack("<H", data[i : i + 2])[0]
        i += 2
        tok = _ID_TO_LEX.get(tid)
        if tok:
            out.extend(tok)
        else:
            out.append(0x1E)
    return bytes(out)


def _wrap(method: int, raw: bytes, payload: bytes) -> bytes:
    return MAGIC + struct.pack("<BBII", VERSION, method, len(raw), len(payload)) + payload


def _unwrap(blob: bytes) -> tuple[int, bytes]:
    if not is_fly(blob):
        raise ValueError("not FLD1")
    ver, method, raw_len, pay_len = struct.unpack("<BBII", blob[4:14])
    if ver != VERSION:
        raise ValueError(f"unsupported FLD1 version {ver}")
    payload = blob[14 : 14 + pay_len]
    if len(payload) != pay_len:
        raise ValueError("truncated FLD1 payload")
    return method, payload


def fly_pack(raw: bytes, *, min_ratio: float = 1.02) -> bytes:
    """Compress if beneficial; otherwise return raw unchanged."""
    if is_fly(raw):
        return raw
    if len(raw) < 64:
        return raw

    candidates: list[tuple[int, bytes]] = []

    z1 = zlib.compress(raw, level=1)
    candidates.append((METHOD_ZLIB, z1))

    if raw[:1] in (b"{", b"[") or b'"domains"' in raw[:4096] or b'"body"' in raw[:8192]:
        lexed = _lex_encode(raw)
        zlex = zlib.compress(lexed, level=1)
        candidates.append((METHOD_JSON_LEX, zlex))

    best_method, best_payload = min(candidates, key=lambda x: len(x[1]))
    wrapped = _wrap(best_method, raw, best_payload)
    if len(wrapped) >= len(raw) * min_ratio:
        return raw
    return wrapped


def fly_unpack(data: bytes) -> bytes:
    """Transparent read — pass-through if not FLD1."""
    if not is_fly(data):
        return data
    method, payload = _unwrap(data)
    try:
        body = zlib.decompress(payload)
    except zlib.error as exc:
        raise ValueError(f"FLD1 zlib failed: {exc}") from exc
    if method == METHOD_JSON_LEX:
        body = _lex_decode(body)
    return body


def fly_read_bytes(path: Path) -> bytes:
    return fly_unpack(path.read_bytes())


def fly_read_text(path: Path, *, encoding: str = "utf-8") -> str:
    return fly_read_bytes(path).decode(encoding)


def fly_write_bytes(path: Path, raw: bytes) -> dict[str, Any]:
    packed = fly_pack(raw)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(packed)
    return {
        "path": str(path),
        "raw_bytes": len(raw),
        "stored_bytes": len(packed),
        "fly": is_fly(packed),
        "ratio": round(len(raw) / max(1, len(packed)), 3),
    }


def fly_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> dict[str, Any]:
    return fly_write_bytes(path, text.encode(encoding))


def fly_read_json(path: Path) -> Any:
    return json.loads(fly_read_text(path))


def fly_write_json(path: Path, obj: Any, *, indent: int | None = 2) -> dict[str, Any]:
    text = json.dumps(obj, indent=indent, ensure_ascii=False) + "\n"
    return fly_write_text(path, text)


def should_fly_path(path: Path) -> bool:
    """Brain field files that benefit from FLD1."""
    name = path.name.lower()
    if name.endswith(".h7"):
        return False  # H7B already compressed — keep readable after ZAC restore
    if name.endswith((".json", ".jsonl", ".corpus")):
        return True
    if "corpus" in name or "brain" in str(path):
        return True
    return False


def fly_pack_file(path: Path, *, in_place: bool = True) -> dict[str, Any]:
    raw = path.read_bytes()
    if is_fly(raw):
        return {"path": str(path), "skipped": True, "reason": "already FLD1"}
    packed = fly_pack(raw)
    if not is_fly(packed):
        return {"path": str(path), "skipped": True, "reason": "no gain"}
    if in_place:
        path.write_bytes(packed)
    return {
        "path": str(path),
        "raw_bytes": len(raw),
        "stored_bytes": len(packed),
        "ratio": round(len(raw) / len(packed), 3),
    }


def bench_fly(raw: bytes) -> dict[str, Any]:
    t0 = time.perf_counter()
    packed = fly_pack(raw)
    pack_ms = int((time.perf_counter() - t0) * 1000)
    t1 = time.perf_counter()
    restored = fly_unpack(packed if is_fly(packed) else raw)
    unpack_ms = int((time.perf_counter() - t1) * 1000)
    return {
        "raw_bytes": len(raw),
        "stored_bytes": len(packed),
        "fly": is_fly(packed),
        "lossless": restored == raw,
        "pack_ms": pack_ms,
        "unpack_ms": unpack_ms,
        "ratio": round(len(raw) / max(1, len(packed)), 3),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="FLD1 fly codec — lossless brain compression")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pack_p = sub.add_parser("pack", help="Compress file in place")
    pack_p.add_argument("path", type=Path)

    unpack_p = sub.add_parser("unpack", help="Decompress FLD1 file to stdout")
    unpack_p.add_argument("path", type=Path)

    bench_p = sub.add_parser("bench", help="Benchmark roundtrip")
    bench_p.add_argument("path", type=Path)

    args = parser.parse_args(argv)
    try:
        if args.cmd == "pack":
            rep = fly_pack_file(args.path)
            print(json.dumps(rep, indent=2))
        elif args.cmd == "unpack":
            sys.stdout.buffer.write(fly_read_bytes(args.path))
        elif args.cmd == "bench":
            raw = args.path.read_bytes()
            if is_fly(raw):
                raw = fly_unpack(raw)
            print(json.dumps(bench_fly(raw), indent=2))
    except (OSError, ValueError) as exc:
        print(f"FLD1 error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())