#!/usr/bin/env pythong
"""Hostess 7 infinite code drive — ISA opcodes + programming languages."""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_code_catalog import iter_all_entries  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BRAIN_CODE = ROOT / "cache" / "fieldstorage" / "brain" / "code"
INFINITE = BRAIN_CODE / "infinite"
SHARDS = INFINITE / "shards"
ARCHIVE = INFINITE / "archive"
STAGING = ROOT / "cache" / "fieldstorage" / "team_staging" / "code_bulk"
MANIFEST = INFINITE / "manifest.json"
INDEX = INFINITE / "search_index.jsonl"
INGEST_LOG = INFINITE / "ingest.jsonl"

INFINITE_VERSION = 1
SHARD_SIZE = 1500


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    for p in (INFINITE, SHARDS, ARCHIVE, STAGING):
        p.mkdir(parents=True, exist_ok=True)


def _entry_id(row: dict) -> str:
    return str(row.get("id") or hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16])


def _row_blob(row: dict) -> str:
    parts = [
        str(row.get("full_name") or row.get("name") or row.get("mnemonic") or ""),
        str(row.get("chip") or ""),
        str(row.get("opcode") or ""),
        str(row.get("operands") or ""),
        str(row.get("paradigm") or ""),
        str(row.get("typing") or ""),
        str(row.get("body", "")),
        " ".join(row.get("tags") or ()),
    ]
    return " ".join(parts).lower()


def load_manifest() -> dict[str, Any]:
    _ensure_dirs()
    if not MANIFEST.is_file():
        return {"version": INFINITE_VERSION, "shards": [], "entry_count": 0, "updated": _ts()}
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def save_manifest(manifest: dict[str, Any]) -> None:
    manifest["updated"] = _ts()
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def _archive_old(path: Path) -> Path | None:
    if not path.is_file():
        return None
    dest = ARCHIVE / f"{path.stem}_{int(time.time())}{path.suffix}"
    shutil.move(str(path), str(dest))
    return dest


def write_shards(rows: list[dict], *, label: str = "catalog") -> list[str]:
    _ensure_dirs()
    shard_names: list[str] = []
    for i in range(0, len(rows), SHARD_SIZE):
        chunk = rows[i : i + SHARD_SIZE]
        shard_id = f"{label}_{i // SHARD_SIZE:04d}"
        path = SHARDS / f"{shard_id}.jsonl"
        if path.is_file():
            _archive_old(path)
        with path.open("w", encoding="utf-8") as f:
            for row in chunk:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        shard_names.append(shard_id)
    return shard_names


def rebuild_index(rows: list[dict]) -> int:
    _ensure_dirs()
    if INDEX.is_file():
        _archive_old(INDEX)
    count = 0
    with INDEX.open("w", encoding="utf-8") as f:
        for row in rows:
            entry = {
                "id": _entry_id(row),
                "full_name": row.get("full_name") or row.get("name") or row.get("mnemonic", ""),
                "chip": row.get("chip", ""),
                "mnemonic": row.get("mnemonic", ""),
                "opcode": row.get("opcode", ""),
                "category": row.get("category", ""),
                "name": row.get("name", ""),
                "paradigm": row.get("paradigm", ""),
                "blob": _row_blob(row)[:4000],
                "body": str(row.get("body", ""))[:8000],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            count += 1
    return count


def ingest_catalog(*, vacuum: bool = True) -> dict[str, Any]:
    _ensure_dirs()
    rows = iter_all_entries()
    shards = write_shards(rows, label="code")
    indexed = rebuild_index(rows)
    opcodes = sum(1 for r in rows if r.get("category") == "isa_opcode")
    langs = sum(1 for r in rows if r.get("category") == "programming_language")
    manifest = {
        "version": INFINITE_VERSION,
        "source": "field_code_catalog",
        "shards": shards,
        "entry_count": len(rows),
        "opcode_count": opcodes,
        "language_count": langs,
        "indexed": indexed,
        "updated": _ts(),
    }
    save_manifest(manifest)
    with INGEST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _ts(), "action": "ingest_catalog", "count": len(rows)}) + "\n")
    if vacuum:
        vacuum_old_copies()
    return manifest


def ingest_bulk_dir(src: Path | None = None, *, vacuum: bool = True) -> dict[str, Any]:
    return ingest_catalog(vacuum=vacuum)


def vacuum_old_copies() -> int:
    _ensure_dirs()
    removed = 0
    excess = sorted(ARCHIVE.glob("*"), key=lambda p: p.stat().st_mtime)
    while len(excess) > 24:
        excess[0].unlink(missing_ok=True)
        removed += 1
        excess = excess[1:]
    return removed


def infinite_status() -> dict[str, Any]:
    _ensure_dirs()
    manifest = load_manifest()
    shard_bytes = sum(p.stat().st_size for p in SHARDS.glob("*.jsonl") if p.is_file())
    return {
        "indexed": manifest.get("indexed", manifest.get("entry_count", 0)),
        "entry_count": manifest.get("entry_count", 0),
        "opcode_count": manifest.get("opcode_count", 0),
        "language_count": manifest.get("language_count", 0),
        "shard_bytes": shard_bytes,
        "staging": str(STAGING),
    }


def search_infinite(query: str, *, limit: int = 10) -> list[dict]:
    if not INDEX.is_file():
        return []
    q = query.lower().strip()
    toks = [t for t in q.split() if len(t) > 1]
    scored: list[tuple[int, dict]] = []
    for line in INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        blob = str(row.get("blob", "")).lower()
        mnem = str(row.get("mnemonic", "")).lower()
        chip = str(row.get("chip", "")).lower()
        name = str(row.get("name", "")).lower()
        score = 0
        if q == mnem or q == name:
            score += 50
        if q == chip:
            score += 40
        for t in toks:
            if t == mnem or t == name or t == chip:
                score += 15
            elif t in blob:
                score += 4
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], x[1].get("full_name", "")))
    return [r for _, r in scored[:limit]]


def lookup_opcode(chip: str, mnemonic: str) -> list[dict]:
    c = chip.lower().strip()
    m = mnemonic.upper().strip()
    if not INDEX.is_file():
        return []
    out: list[dict] = []
    for line in INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("category") != "isa_opcode":
            continue
        if str(row.get("chip", "")).lower() == c and str(row.get("mnemonic", "")).upper() == m:
            out.append(row)
    return out


def lookup_language(name: str) -> dict | None:
    n = name.lower().strip()
    if not INDEX.is_file():
        return None
    for line in INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("category") != "programming_language":
            continue
        if str(row.get("name", "")).lower() == n or str(row.get("id", "")).lower() == f"lang_{n}":
            return row
    return None