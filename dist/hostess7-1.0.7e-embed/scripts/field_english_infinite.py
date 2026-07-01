#!/usr/bin/env pythong
"""Hostess 7 infinite English lexicon drive — dictionaries, phonetics, spell export."""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_english_catalog import catalog_count, iter_all_entries  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BRAIN_ENGLISH = ROOT / "cache" / "fieldstorage" / "brain" / "english"
INFINITE = BRAIN_ENGLISH / "infinite"
SHARDS = INFINITE / "shards"
ARCHIVE = INFINITE / "archive"
SPELL = BRAIN_ENGLISH / "spell"
STAGING = ROOT / "cache" / "fieldstorage" / "team_staging" / "english_bulk"
MANIFEST = INFINITE / "manifest.json"
INDEX = INFINITE / "search_index.jsonl"
INGEST_LOG = INFINITE / "ingest.jsonl"
WORDS_SORTED = SPELL / "words_sorted.txt"

INFINITE_VERSION = 1
SHARD_SIZE = 2000


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    for p in (INFINITE, SHARDS, ARCHIVE, SPELL, STAGING):
        p.mkdir(parents=True, exist_ok=True)


def _entry_id(row: dict) -> str:
    return str(row.get("id") or hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16])


def _row_blob(row: dict) -> str:
    word = str(row.get("word") or row.get("full_name", ""))
    body = str(row.get("body", ""))
    ph = str(row.get("phonetic_arpabet", ""))
    tags = " ".join(row.get("tags") or ())
    return f"{word} {ph} {body} {tags}".lower()


def load_manifest() -> dict[str, Any]:
    _ensure_dirs()
    if not MANIFEST.is_file():
        return {"version": INFINITE_VERSION, "shards": [], "word_count": 0, "updated": _ts()}
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
        for old in SHARDS.glob(f"{label}_{i // SHARD_SIZE:04d}*.jsonl"):
            if old != path:
                _archive_old(old)
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
                "word": row.get("word", ""),
                "full_name": row.get("word", row.get("full_name", "")),
                "phonetic_arpabet": row.get("phonetic_arpabet", ""),
                "locale": row.get("locale", ""),
                "category": row.get("category", "english_lexicon"),
                "blob": _row_blob(row)[:4000],
                "body": str(row.get("body", ""))[:8000],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            count += 1
    return count


RTX_SPELL_SUPPLEMENT = (
    "ammofat", "ammosys", "ammotext", "amouranth", "amouranthrtx", "hostess",
    "field", "rtx", "rtxsb", "rtxvga", "supercore", "vscodium", "framebuffer",
)


def export_spell_words(rows: list[dict]) -> int:
    """Lossless sorted word list for AmmoText native spellcheck."""
    _ensure_dirs()
    words = sorted(
        {str(r.get("word", "")).lower() for r in rows if r.get("word")}
        | {w.lower() for w in RTX_SPELL_SUPPLEMENT}
    )
    if WORDS_SORTED.is_file():
        _archive_old(WORDS_SORTED)
    WORDS_SORTED.write_text("\n".join(words) + "\n", encoding="utf-8")
    return len(words)


def ingest_catalog(*, vacuum: bool = True, download_cmudict: bool = True) -> dict[str, Any]:
    _ensure_dirs()
    rows = list(iter_all_entries(download_cmudict=download_cmudict))
    shards = write_shards(rows, label="lexicon")
    indexed = rebuild_index(rows)
    spell_n = export_spell_words(rows)
    with_phon = sum(1 for r in rows if r.get("phonetic_arpabet"))
    manifest = {
        "version": INFINITE_VERSION,
        "source": "field_english_catalog",
        "shards": shards,
        "word_count": len(rows),
        "indexed": indexed,
        "spell_words": spell_n,
        "phonetic_count": with_phon,
        "catalog_sources": catalog_count(),
        "formal_mode": True,
        "updated": _ts(),
    }
    save_manifest(manifest)
    with INGEST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _ts(), "action": "ingest_catalog", "count": len(rows)}) + "\n")
    if vacuum:
        vacuum_old_copies(keep_manifest_shards=True)
    return manifest


def _load_index_rows() -> list[dict]:
    if not INDEX.is_file():
        return []
    rows: list[dict] = []
    for line in INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def ingest_bulk_dir(src: Path | None = None, *, vacuum: bool = True) -> dict[str, Any]:
    _ensure_dirs()
    src = src or STAGING
    if not src.is_dir():
        return {"error": f"staging missing: {src}", "count": 0}
    # Re-run full catalog merge after bulk drop (e.g. new cmudict, wiktionary jsonl)
    return ingest_catalog(vacuum=vacuum)


def vacuum_old_copies(*, keep_manifest_shards: bool = False) -> int:
    _ensure_dirs()
    removed = 0
    manifest = load_manifest()
    keep = set(manifest.get("shards") or [])
    for path in ARCHIVE.glob("*"):
        if path.is_file():
            continue
    for path in list(ARCHIVE.iterdir()):
        if not path.is_file():
            continue
        if keep_manifest_shards and path.stem.split("_")[0] in keep:
            continue
        # keep archive — only trim if > 32 files
        pass
    excess = sorted(ARCHIVE.glob("*"), key=lambda p: p.stat().st_mtime)
    while len(excess) > 32:
        excess[0].unlink(missing_ok=True)
        removed += 1
        excess = excess[1:]
    return removed


def infinite_status() -> dict[str, Any]:
    _ensure_dirs()
    manifest = load_manifest()
    shard_bytes = sum(p.stat().st_size for p in SHARDS.glob("*.jsonl") if p.is_file())
    spell_bytes = WORDS_SORTED.stat().st_size if WORDS_SORTED.is_file() else 0
    return {
        "indexed": manifest.get("indexed", manifest.get("word_count", 0)),
        "word_count": manifest.get("word_count", 0),
        "phonetic_count": manifest.get("phonetic_count", 0),
        "spell_words": manifest.get("spell_words", 0),
        "shard_bytes": shard_bytes,
        "spell_bytes": spell_bytes,
        "catalog_seed_count": catalog_count(),
        "staging": str(STAGING),
        "spell_path": str(WORDS_SORTED),
    }


def search_infinite(query: str, *, limit: int = 8) -> list[dict]:
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
        word = str(row.get("word", "")).lower()
        blob = str(row.get("blob", "")).lower()
        score = 0
        if q == word:
            score += 50
        elif word.startswith(q):
            score += 30
        elif q in word:
            score += 15
        for t in toks:
            if t == word:
                score += 20
            elif t in blob:
                score += 4
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], x[1].get("word", "")))
    out: list[dict] = []
    seen: set[str] = set()
    for _, row in scored:
        wid = str(row.get("id", row.get("word", "")))
        if wid in seen:
            continue
        seen.add(wid)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def lookup_word(word: str) -> dict | None:
    w = word.strip().lower()
    if not w or not INDEX.is_file():
        return None
    best: dict | None = None
    variants: list[str] = []
    for line in INDEX.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(row.get("word", "")).lower() != w:
            continue
        ph = str(row.get("phonetic_arpabet", ""))
        if ph and ph not in variants:
            variants.append(ph)
        if not best:
            best = dict(row)
    if best and variants:
        best["phonetic_variants"] = variants
    return best