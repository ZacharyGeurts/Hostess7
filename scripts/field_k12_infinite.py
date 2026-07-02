#!/usr/bin/env pythong
"""Hostess 7 infinite K-12 textbook drive — OER fetch, truth filter, shard index."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from field_k12_catalog import catalog_by_grade, catalog_by_subject, catalog_count, iter_all_textbooks, textbooks_with_fetch_url  # noqa: E402
from field_k12_truth import score_k12_text  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BRAIN_K12 = ROOT / "cache" / "fieldstorage" / "brain" / "k12"
INFINITE = BRAIN_K12 / "infinite"
SHARDS = INFINITE / "shards"
ARCHIVE = INFINITE / "archive"
STAGING = ROOT / "cache" / "fieldstorage" / "team_staging" / "k12_bulk"
FETCH_CACHE = STAGING / "fetched"
MANIFEST = INFINITE / "manifest.json"
INDEX = INFINITE / "search_index.jsonl"
INGEST_LOG = INFINITE / "ingest.jsonl"
TRUTH_LOG = INFINITE / "truth_filter.jsonl"
TRUTH_REJECT = INFINITE / "truth_reject.jsonl"

INFINITE_VERSION = 1
SHARD_SIZE = 50


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    for p in (INFINITE, SHARDS, ARCHIVE, STAGING, FETCH_CACHE):
        p.mkdir(parents=True, exist_ok=True)


def _book_id(row: dict) -> str:
    return str(row.get("id") or hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()[:16])


def _row_blob(row: dict) -> str:
    name = str(row.get("full_name") or row.get("title", ""))
    body = str(row.get("body", ""))
    tags = " ".join(row.get("tags") or ())
    subj = str(row.get("subject", ""))
    grade = str(row.get("grade_band", ""))
    return f"{name} {subj} {grade} {body} {tags}".lower()


def _load_fetch_cache_state() -> dict[str, dict[str, Any]]:
    """Restore truth-accepted bodies from fetch cache + truth log (survives re-seed)."""
    state: dict[str, dict[str, Any]] = {}
    if FETCH_CACHE.is_dir():
        for path in FETCH_CACHE.glob("*.txt"):
            body = path.read_text(encoding="utf-8", errors="replace").strip()
            if len(body) < 100:
                continue
            state[path.stem] = {"body": body[:50000], "fetched": True}
    if TRUTH_LOG.is_file():
        for line in TRUTH_LOG.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not entry.get("accepted"):
                continue
            bid = str(entry.get("id", ""))
            if not bid:
                continue
            row = state.setdefault(bid, {})
            row.update({
                "fetched": True,
                "fetch_url": entry.get("url", ""),
                "truth_score": entry.get("truth_score"),
                "word_count": entry.get("word_count"),
                "edu_hits": entry.get("edu_hits"),
                "fetched_ts": entry.get("ts"),
            })
            if not row.get("body"):
                cache_file = FETCH_CACHE / f"{bid}.txt"
                if cache_file.is_file():
                    row["body"] = cache_file.read_text(encoding="utf-8", errors="replace")[:50000]
    return state


def _merge_fetched(rows: list[dict]) -> list[dict]:
    cache_state = _load_fetch_cache_state()
    if not cache_state:
        return rows
    merged: list[dict] = []
    for row in rows:
        out = dict(row)
        cached = cache_state.get(str(out.get("id", "")))
        if cached:
            out.update(cached)
        merged.append(out)
    return merged


def load_manifest() -> dict[str, Any]:
    _ensure_dirs()
    if not MANIFEST.is_file():
        return {"version": INFINITE_VERSION, "shards": [], "textbook_count": 0, "updated": _ts()}
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


def write_shards(rows: list[dict], *, label: str = "textbooks") -> list[str]:
    _ensure_dirs()
    shard_names: list[str] = []
    for i in range(0, max(len(rows), 1), SHARD_SIZE):
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
                "id": _book_id(row),
                "full_name": row.get("full_name") or row.get("title", ""),
                "title": row.get("title", ""),
                "grade_band": row.get("grade_band", ""),
                "subject": row.get("subject", ""),
                "publisher": row.get("publisher", ""),
                "license": row.get("license", ""),
                "truth_score": row.get("truth_score"),
                "fetched": row.get("fetched", False),
                "category": row.get("category", ""),
                "blob": _row_blob(row)[:4000],
                "body": str(row.get("body", ""))[:50000],
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            count += 1
    return count


def ingest_catalog(*, vacuum: bool = True) -> dict[str, Any]:
    """Seed infinite drive from K-12 catalog metadata (no network)."""
    _ensure_dirs()
    rows = _merge_fetched(list(iter_all_textbooks()))
    fetched_n = sum(1 for r in rows if r.get("fetched"))
    prev = load_manifest()
    shards = write_shards(rows, label="textbooks")
    indexed = rebuild_index(rows)
    manifest = {
        "version": INFINITE_VERSION,
        "source": "field_k12_catalog+truth_fetch" if fetched_n else "field_k12_catalog",
        "shards": shards,
        "textbook_count": len(rows),
        "indexed": indexed,
        "fetched_count": fetched_n,
        "by_grade": catalog_by_grade(),
        "by_subject": catalog_by_subject(),
        "truth_filter": True,
        "updated": _ts(),
    }
    if fetched_n:
        manifest["truth_accepted"] = prev.get("truth_accepted", fetched_n)
        manifest["truth_rejected"] = prev.get("truth_rejected")
    save_manifest(manifest)
    with INGEST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": _ts(), "action": "ingest_catalog", "count": len(rows)}) + "\n")
    return manifest


def _fetch_one(url: str) -> dict[str, Any]:
    os.environ.setdefault("HOSTESS7_INTERNET", "1")
    from field_internet import fetch_url  # noqa: WPS433

    return fetch_url(url, force=False)


def fetch_all_truth_filtered(*, force: bool = False, limit: int | None = None) -> dict[str, Any]:
    """Fetch ALL catalog URLs — truth-filter before merging into K-12 brain."""
    os.environ["HOSTESS7_INTERNET"] = "1"
    _ensure_dirs()

    from field_internet import internet_enabled  # noqa: WPS433

    if not internet_enabled():
        return {"error": "internet gate CLOSED — run ./Hostess7.sh on or HOSTESS7_INTERNET=1", "accepted": 0}

    catalog_rows = {r["id"]: dict(r) for r in iter_all_textbooks()}
    to_fetch = textbooks_with_fetch_url()
    if limit:
        to_fetch = to_fetch[:limit]

    accepted_n = 0
    rejected_n = 0
    fetch_ok = 0

    for book in to_fetch:
        bid = book["id"]
        url = str(book.get("fetch_url", ""))
        if "wikibooks.org" in url and "action=render" not in url:
            url += "&action=render" if "?" in url else "?action=render"
        row = catalog_rows.get(bid, dict(book))
        title = str(row.get("title", ""))
        publisher = str(row.get("publisher", ""))

        rec = _fetch_one(url)
        if not rec.get("ok"):
            rejected_n += 1
            with TRUTH_REJECT.open("a", encoding="utf-8") as f:
                f.write(json.dumps({
                    "ts": _ts(), "id": bid, "url": url, "reason": rec.get("error", "fetch fail"),
                    "truth_score": 0,
                }) + "\n")
            continue

        fetch_ok += 1
        text = str(rec.get("text_preview", ""))
        if rec.get("bytes", 0) > len(text):
            cache_key = __import__("hashlib").sha256(url.encode()).hexdigest()[:16]
            cache_path = ROOT / "cache" / "fieldstorage" / "brain" / "internet" / "cache" / f"{cache_key}.bin"
            if cache_path.is_file():
                raw = cache_path.read_bytes().decode("utf-8", errors="replace")
                text = raw[:50000]

        verdict = score_k12_text(text, title=title, publisher=publisher)
        log_entry = {
            "ts": _ts(),
            "id": bid,
            "url": url,
            "title": title,
            "bytes": rec.get("bytes", 0),
            "cached": rec.get("cached", False),
            **verdict,
        }
        with TRUTH_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")

        if verdict.get("accepted"):
            accepted_n += 1
            body = text[:50000].strip()
            row.update({
                "body": body,
                "fetched": True,
                "fetch_url": url,
                "truth_score": verdict.get("truth_score"),
                "word_count": verdict.get("word_count"),
                "edu_hits": verdict.get("edu_hits"),
                "fetched_ts": _ts(),
            })
            cache_file = FETCH_CACHE / f"{bid}.txt"
            cache_file.write_text(body, encoding="utf-8")
            catalog_rows[bid] = row
        else:
            rejected_n += 1
            with TRUTH_REJECT.open("a", encoding="utf-8") as f:
                f.write(json.dumps({**log_entry, "reason": verdict.get("reason")}) + "\n")

    merged = list(catalog_rows.values())
    shards = write_shards(merged, label="textbooks")
    indexed = rebuild_index(merged)
    manifest = {
        "version": INFINITE_VERSION,
        "source": "field_k12_catalog+truth_fetch",
        "shards": shards,
        "textbook_count": len(merged),
        "indexed": indexed,
        "fetched_count": sum(1 for r in merged if r.get("fetched")),
        "fetch_ok": fetch_ok,
        "truth_accepted": accepted_n,
        "truth_rejected": rejected_n,
        "by_grade": catalog_by_grade(),
        "by_subject": catalog_by_subject(),
        "truth_filter": True,
        "updated": _ts(),
    }
    save_manifest(manifest)
    with INGEST_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({
            "ts": _ts(),
            "action": "fetch_all_truth_filtered",
            "fetch_ok": fetch_ok,
            "accepted": accepted_n,
            "rejected": rejected_n,
        }) + "\n")
    return manifest


def infinite_status() -> dict[str, Any]:
    m = load_manifest()
    shard_bytes = sum(p.stat().st_size for p in SHARDS.glob("*.jsonl") if p.is_file())
    return {
        "version": m.get("version", INFINITE_VERSION),
        "textbook_count": m.get("textbook_count", catalog_count()),
        "indexed": m.get("indexed", 0),
        "fetched_count": m.get("fetched_count", 0),
        "truth_accepted": m.get("truth_accepted"),
        "truth_rejected": m.get("truth_rejected"),
        "by_grade": m.get("by_grade", catalog_by_grade()),
        "by_subject": m.get("by_subject", catalog_by_subject()),
        "shard_bytes": shard_bytes,
        "staging": str(STAGING),
        "truth_log": str(TRUTH_LOG),
    }


def restore_from_fetch_cache() -> dict[str, Any]:
    """Rebuild index/shards from on-disk truth-accepted fetch cache (no network)."""
    return ingest_catalog(vacuum=False)


def search_infinite(query: str, *, limit: int = 8) -> list[dict]:
    if not INDEX.is_file():
        ingest_catalog(vacuum=False)
    toks = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2]
    scored: list[tuple[int, dict]] = []
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        blob = str(row.get("blob", "")).lower()
        score = sum(4 if t in blob else 0 for t in toks)
        if score > 0:
            scored.append((score, row))
    scored.sort(key=lambda x: -x[0])
    return [r for _, r in scored[:limit]]


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd in ("seed", "catalog", "ingest"):
        m = ingest_catalog()
        print(f"OK k12 infinite seed textbooks={m.get('textbook_count')}")
        print(f"METRIC k12_textbooks={m.get('textbook_count')}")
        return 0
    if cmd in ("restore", "rebuild"):
        m = restore_from_fetch_cache()
        print(f"OK k12 restore fetched={m.get('fetched_count')}")
        print(f"METRIC k12_fetched={m.get('fetched_count')}")
        return 0
    if cmd in ("fetch", "fetch-all", "grab"):
        limit = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else None
        m = fetch_all_truth_filtered(limit=limit)
        if m.get("error"):
            print(f"BLOCKER: {m['error']}", file=sys.stderr)
            return 1
        print(f"OK k12 fetch truth-filtered accepted={m.get('truth_accepted')} rejected={m.get('truth_rejected')}")
        print(f"METRIC k12_fetched={m.get('fetched_count')}")
        print(f"METRIC k12_truth_accepted={m.get('truth_accepted')}")
        print(f"METRIC k12_truth_rejected={m.get('truth_rejected')}")
        return 0
    st = infinite_status()
    print(f"K-12 textbooks: {st.get('textbook_count')} indexed · fetched {st.get('fetched_count')}")
    print(f"METRIC k12_textbooks={st.get('textbook_count')}")
    print(f"METRIC k12_indexed={st.get('indexed')}")
    print("OK k12-status")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())