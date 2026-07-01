#!/usr/bin/env pythong
"""Hostess 7 Book (.H7) — lossless compressed library format for H7 reading only."""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "scripts"))

from field_fly_codec import fly_pack, fly_unpack, is_fly  # noqa: E402

MAGIC = b"H7B\x01"
MAGIC_FLY = b"H7B\x02"
FORMAT_ID = "h7b/1"
FORMAT_ID_FLY = "h7b/2"


class H7Error(ValueError):
    pass


def _line_offsets(raw: bytes) -> list[int]:
    offsets = [0]
    for i, byte in enumerate(raw):
        if byte == ord("\n"):
            offsets.append(i + 1)
    return offsets


def pack_h7(text: str, meta: dict[str, Any], *, use_fly: bool = True) -> bytes:
    """Pack full UTF-8 text — every character and line preserved, zlib-compressed."""
    raw = text.encode("utf-8")
    offsets = _line_offsets(raw)
    text_blob = fly_pack(raw) if use_fly else raw
    fly_layer = is_fly(text_blob)
    compressed = zlib.compress(text_blob, level=1 if fly_layer else 9)
    idx_raw = struct.pack(f"<{len(offsets)}I", *offsets)
    idx_compressed = zlib.compress(idx_raw, level=9)

    header: dict[str, Any] = {
        "format": FORMAT_ID_FLY if fly_layer else FORMAT_ID,
        "char_count": len(text),
        "byte_count": len(raw),
        "line_count": len(offsets),
        "text_sha256": hashlib.sha256(raw).hexdigest(),
        "compression": "fld1+zlib-1" if fly_layer else "zlib-9",
        "fly_layer": fly_layer,
        "raw_bytes": len(raw),
        "packed_bytes": len(compressed),
        "line_index_packed_bytes": len(idx_compressed),
        **{k: v for k, v in meta.items() if k not in ("format",)},
    }
    header_json = json.dumps(header, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(header_json) > 65535:
        raise H7Error("H7 header too large")

    magic = MAGIC_FLY if fly_layer else MAGIC
    return (
        magic
        + struct.pack("<I", len(header_json))
        + header_json
        + compressed
        + idx_compressed
    )


def parse_h7(data: bytes) -> tuple[dict[str, Any], bytes, bytes]:
    if len(data) < 8 or data[:4] not in (MAGIC, MAGIC_FLY):
        raise H7Error("not a Hostess7 .H7 book (bad magic)")
    header_len = struct.unpack("<I", data[4:8])[0]
    start = 8
    end = start + header_len
    if end > len(data):
        raise H7Error("truncated H7 header")
    header = json.loads(data[start:end].decode("utf-8"))
    payload = data[end:]
    packed_len = int(header.get("packed_bytes", 0))
    idx_len = int(header.get("line_index_packed_bytes", 0))
    if packed_len + idx_len > len(payload):
        raise H7Error("truncated H7 payload")
    compressed = payload[:packed_len]
    idx_compressed = payload[packed_len : packed_len + idx_len]
    return header, compressed, idx_compressed


def _decompress_text_payload(header: dict[str, Any], compressed: bytes) -> bytes:
    blob = zlib.decompress(compressed)
    if header.get("fly_layer") or is_fly(blob):
        return fly_unpack(blob)
    return blob


def unpack_h7(data: bytes, *, verify: bool = True) -> tuple[dict[str, Any], str]:
    header, compressed, idx_compressed = parse_h7(data)
    raw = _decompress_text_payload(header, compressed)
    if verify:
        expect = header.get("text_sha256")
        if expect and hashlib.sha256(raw).hexdigest() != expect:
            raise H7Error("H7 integrity check failed (sha256)")
        if int(header.get("byte_count", -1)) != len(raw):
            raise H7Error("H7 byte_count mismatch")
    text = raw.decode("utf-8")
    if verify and len(text) != int(header.get("char_count", len(text))):
        raise H7Error("H7 char_count mismatch")
    return header, text


def _decompress_index(idx_compressed: bytes, line_count: int) -> list[int]:
    idx_raw = zlib.decompress(idx_compressed)
    need = line_count * 4
    if len(idx_raw) < need:
        raise H7Error("line index corrupt")
    return list(struct.unpack(f"<{line_count}I", idx_raw[:need]))


def read_h7_file(path: Path, *, line_start: int = 1, line_end: int | None = None) -> dict[str, Any]:
    """Read .H7 book — full text or line range (1-based inclusive)."""
    data = path.read_bytes()
    header, compressed, idx_compressed = parse_h7(data)
    raw = _decompress_text_payload(header, compressed)
    text = raw.decode("utf-8")
    line_count = int(header.get("line_count", 0))
    offsets = _decompress_index(idx_compressed, line_count) if idx_compressed else [0]

    if line_start <= 1 and (line_end is None or line_end >= line_count):
        return {**header, "path": str(path), "text": text, "lines": text.splitlines()}

    start_i = max(1, line_start) - 1
    end_i = line_count if line_end is None else min(line_count, line_end)
    if start_i >= line_count:
        return {**header, "path": str(path), "text": "", "lines": []}

    chunk_start = offsets[start_i]
    chunk_end = offsets[end_i] if end_i < line_count else len(raw)
    chunk = raw[chunk_start:chunk_end].decode("utf-8")
    return {
        **header,
        "path": str(path),
        "text": chunk,
        "lines": chunk.splitlines(),
        "line_start": start_i + 1,
        "line_end": end_i,
    }


def h7_stats(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    header, compressed, idx_compressed = parse_h7(data)
    raw_size = int(header.get("raw_bytes", 0))
    packed = len(compressed) + len(idx_compressed) + len(data) - raw_size
    ratio = round(raw_size / max(1, len(data)), 2)
    return {
        "path": str(path),
        "file_bytes": len(data),
        "raw_bytes": raw_size,
        "char_count": header.get("char_count"),
        "line_count": header.get("line_count"),
        "compression_ratio": ratio,
        "title": header.get("title"),
        "id": header.get("id"),
        "license": header.get("license"),
    }


def write_h7(path: Path, text: str, meta: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = pack_h7(text, meta)
    path.write_bytes(blob)
    return h7_stats(path)