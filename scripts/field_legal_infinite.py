#!/usr/bin/env pythong
"""Hostess 7 infinite legal drive — bulk ingest, torrent staging, shard index, vacuum old copies."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_legal_catalog import catalog_by_category, catalog_count, iter_all_statutes  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BRAIN_LEGAL = ROOT / "cache" / "fieldstorage" / "brain" / "legal"
INFINITE = BRAIN_LEGAL / "infinite"
SHARDS = INFINITE / "shards"
ARCHIVE = INFINITE / "archive"
STAGING = ROOT / "cache" / "fieldstorage" / "team_staging" / "legal_bulk"
TORRENT_STAGING = STAGING / "torrents"
MANIFEST = INFINITE / "manifest.json"
INDEX = INFINITE / "search_index.jsonl"
INGEST_LOG = INFINITE / "ingest.jsonl"

INFINITE_VERSION = 1
SHARD_SIZE = 500  # statutes per shard file


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    for p in (INFINITE, SHARDS, ARCHIVE, STAGING, TORRENT_STAGING):
        p.mkdir(parents=True, exist_ok=True)


def _statute_id(row: dict) -> str:
    return str(row.get("id") or hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16])


def _row_blob(row: dict) -> str:
    name = str(row.get("full_name") or row.get("title", ""))
    body = str(row.get("body", ""))
    tags = " ".join(row.get("tags") or ())
    return f"{name} {body} {tags}".lower()


def load_manifest() -> dict[str, Any]:
    _ensure_dirs()
    if not MANIFEST.is_file():
        return {"version": INFINITE_VERSION, "shards": [], "statute_count": 0, "updated": _ts()}
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
    """Write statute rows to shards; archive superseded shard files."""
    _ensure_dirs()
    shard_names: list[str] = []
    for i in range(0, len(rows), SHARD_SIZE):
        chunk = rows[i : i + SHARD_SIZE]
        shard_id = f"{label}_{i // SHARD_SIZE:04d}"
        path = SHARDS / f"{shard_id}.jsonl"
        old_glob = list(SHARDS.glob(f"{label}_{i // SHARD_SIZE:04d}*.jsonl"))
        for old in old_glob:
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
    """Full-text search index — one line per statute."""
    _ensure_dirs()
    if INDEX.is_file():
        _archive_old(INDEX)
    count = 0
    with INDEX.open("w", encoding="utf-8") as f:
        for row in rows:
            entry = {
                "id": _statute_id(row),
                "full_name": row.get("full_name") or row.get("title", ""),
                "jurisdiction": row.get("jurisdiction", ""),
                "category": row.get("category", ""),
                "blob": _row_blob(row)[:4000],
                "body": str(row.get("body", ""))[:8000],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            count += 1
    return count


def ingest_catalog(*, vacuum: bool = True) -> dict[str, Any]:
    """Bake universal catalog into infinite drive shards."""
    _ensure_dirs()
    rows = list(iter_all_statutes())
    shards = write_shards(rows, label="catalog")
    indexed = rebuild_index(rows)
    manifest = {
        "version": INFINITE_VERSION,
        "source": "field_legal_catalog",
        "shards": shards,
        "statute_count": len(rows),
        "indexed": indexed,
        "categories": catalog_by_category(),
        "formal_mode": True,
        "updated": _ts(),
    }
    save_manifest(manifest)
    with INGEST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _ts(), "action": "ingest_catalog", "count": len(rows), "shards": len(shards)}) + "\n")
    if vacuum:
        vacuum_old_copies(keep_manifest_shards=True)
    return manifest


def _parse_bulk_file(path: Path) -> list[dict]:
    """Convert downloaded legal text/json/xml to statute rows."""
    rows: list[dict] = []
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        rows.append(item)
            elif isinstance(data, dict) and "domains" in data:
                rows.extend(data["domains"])
        elif suffix == ".jsonl":
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        elif suffix in (".txt", ".md", ".xml", ".html"):
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if len(text) < 40:
                return rows
            title = path.stem.replace("_", " ").replace("-", " ")
            rows.append({
                "id": f"bulk_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}",
                "full_name": title,
                "jurisdiction": "bulk_ingest",
                "category": "bulk",
                "body": text[:50000],
                "tags": (suffix.lstrip("."), "bulk"),
                "source_path": str(path),
            })
    except OSError:
        pass
    return rows


def ingest_bulk_dir(src: Path | None = None, *, vacuum: bool = True) -> dict[str, Any]:
    """Ingest all legal files from staging directory into infinite drive."""
    _ensure_dirs()
    src = src or STAGING
    if not src.is_dir():
        return {"error": f"staging missing: {src}", "count": 0}
    existing = _load_index_rows()
    existing_ids = {_statute_id(r) for r in existing}
    new_rows: list[dict] = []
    for path in sorted(src.rglob("*")):
        if path.is_file() and path.suffix.lower() in (".json", ".jsonl", ".txt", ".md", ".xml", ".html"):
            if "archive" in path.parts or path.name.startswith("."):
                continue
            for row in _parse_bulk_file(path):
                if _statute_id(row) not in existing_ids:
                    new_rows.append(row)
                    existing_ids.add(_statute_id(row))
    merged = existing + new_rows
    if new_rows:
        write_shards(merged, label="merged")
        rebuild_index(merged)
    manifest = load_manifest()
    manifest.update({
        "statute_count": len(merged),
        "bulk_added": len(new_rows),
        "source": str(src),
        "updated": _ts(),
    })
    save_manifest(manifest)
    with INGEST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _ts(), "action": "ingest_bulk", "new": len(new_rows), "total": len(merged)}) + "\n")
    if vacuum:
        vacuum_old_copies(keep_manifest_shards=True)
    return manifest


def ingest_torrent(torrent_path: Path, *, vacuum: bool = True) -> dict[str, Any]:
    """Bulk download via aria2c or transmission-cli into staging, then ingest."""
    _ensure_dirs()
    if not torrent_path.is_file():
        return {"error": f"torrent not found: {torrent_path}", "ok": False}
    dest = TORRENT_STAGING / torrent_path.stem
    dest.mkdir(parents=True, exist_ok=True)
    downloaded = False
    for cmd in (
        ["aria2c", "--dir", str(dest), "--seed-time=0", str(torrent_path)],
        ["transmission-cli", "-w", str(dest), str(torrent_path)],
    ):
        try:
            rc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=3600, check=False).returncode
            if rc == 0:
                downloaded = True
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    if not downloaded:
        return {
            "error": "no torrent client (install aria2 or transmission-cli) or download failed",
            "ok": False,
            "staging": str(dest),
        }
    result = ingest_bulk_dir(dest, vacuum=False)
    if vacuum:
        result["vacuum_removed"] = vacuum_old_copies(
            keep_manifest_shards=True,
            prune_staging=True,
        )
    result["torrent"] = str(torrent_path)
    result["ok"] = True
    with INGEST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _ts(), "action": "ingest_torrent", "torrent": str(torrent_path)}) + "\n")
    return result


def vacuum_old_copies(*, keep_manifest_shards: bool = True, prune_staging: bool = False) -> int:
    """Remove archived superseded copies older than retention; keep current shards only."""
    _ensure_dirs()
    manifest = load_manifest()
    active = set(manifest.get("shards", []))
    removed = 0
    # Remove orphan shards not in manifest
    if keep_manifest_shards:
        for path in SHARDS.glob("*.jsonl"):
            if path.stem not in active:
                _archive_old(path)
                removed += 1
    # Prune archive older than 7 days
    cutoff = time.time() - 7 * 86400
    for path in ARCHIVE.glob("*"):
        if path.stat().st_mtime < cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    # Remove stale corpus.json if infinite is authoritative
    stale = BRAIN_LEGAL / "corpus.json.bak"
    corpus = BRAIN_LEGAL / "corpus.json"
    if corpus.is_file() and manifest.get("statute_count", 0) > 100:
        if not stale.is_file():
            shutil.copy2(corpus, stale)
    if prune_staging:
        for root in (STAGING, TORRENT_STAGING):
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("*"), reverse=True):
                if path.is_file() and path.suffix.lower() in (
                    ".json", ".jsonl", ".txt", ".md", ".xml", ".html",
                ):
                    path.unlink(missing_ok=True)
                    removed += 1
                elif path.is_dir() and not any(path.iterdir()):
                    path.rmdir()
    return removed


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


def search_infinite(query: str, *, limit: int = 8) -> list[dict]:
    """Search infinite drive index — full formal names."""
    _ensure_dirs()
    if not INDEX.is_file():
        ingest_catalog(vacuum=False)
    toks = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
    q = query.lower()
    scored: list[tuple[int, dict]] = []
    for row in _load_index_rows():
        blob = f"{row.get('full_name', '')} {row.get('blob', '')} {row.get('body', '')}".lower()
        score = sum(5 if t in str(row.get("full_name", "")).lower() else 3 if t in blob else 0 for t in toks)
        if q in blob:
            score += 12
        if "united states code" in q and row.get("category") == "united_states_code":
            score += 8
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: (-x[0], x[1].get("full_name", "")))
    return [r for _, r in scored[:limit]]


def infinite_status() -> dict[str, Any]:
    _ensure_dirs()
    manifest = load_manifest()
    index_rows = len(_load_index_rows()) if INDEX.is_file() else 0
    shard_bytes = sum(p.stat().st_size for p in SHARDS.glob("*.jsonl") if p.is_file())
    archive_bytes = sum(p.stat().st_size for p in ARCHIVE.rglob("*") if p.is_file())
    return {
        "manifest": manifest,
        "catalog_seed_count": catalog_count(),
        "indexed": index_rows,
        "shard_bytes": shard_bytes,
        "archive_bytes": archive_bytes,
        "staging": str(STAGING),
        "torrent_staging": str(TORRENT_STAGING),
        "infinite_path": str(INFINITE),
    }


def fetch_usc_title_outline(title_num: int) -> dict[str, Any]:
    """Fetch public United States Code title outline from House OLRC (network optional)."""
    url = f"https://uscode.house.gov/view.xhtml?req=granuleid:USC-prelim-title{title_num}&num=0&edition=prelim"
    try:
        import urllib.request
        with urllib.request.urlopen(url, timeout=30) as resp:
            html = resp.read(50000).decode("utf-8", errors="replace")
        return {"title": title_num, "url": url, "bytes": len(html), "ok": True}
    except Exception as exc:
        return {"title": title_num, "url": url, "ok": False, "error": str(exc)}


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd in ("catalog", "seed"):
        m = ingest_catalog()
        print(f"OK legal infinite catalog ingested statutes={m.get('statute_count')}")
        print(f"METRIC legal_infinite_statutes={m.get('statute_count')}")
        return 0
    if cmd == "bulk":
        src = Path(sys.argv[2]) if len(sys.argv) > 2 else STAGING
        m = ingest_bulk_dir(src)
        print(f"OK legal infinite bulk added={m.get('bulk_added', 0)} total={m.get('statute_count')}")
        return 0
    if cmd == "torrent":
        if len(sys.argv) < 3:
            print("usage: field_legal_infinite.py torrent <file.torrent>", file=sys.stderr)
            return 1
        m = ingest_torrent(Path(sys.argv[2]))
        if not m.get("ok"):
            print(f"FAIL {m.get('error')}", file=sys.stderr)
            return 1
        print(f"OK legal infinite torrent total={m.get('statute_count')}")
        return 0
    if cmd == "vacuum":
        n = vacuum_old_copies()
        print(f"OK legal infinite vacuum removed={n}")
        return 0
    if cmd == "search" and len(sys.argv) > 2:
        q = " ".join(sys.argv[2:])
        for row in search_infinite(q, limit=5):
            print(row.get("full_name", ""))
        return 0
    st = infinite_status()
    print(json.dumps(st, indent=2))
    print(f"METRIC legal_infinite_indexed={st.get('indexed')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())