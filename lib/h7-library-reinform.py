#!/usr/bin/env pythong
"""Library reinformation — overlap eval, Ironclad/Hostess7 corrections ledger, Biggest Lies index."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DEWEY_ROOT = INSTALL / "library" / "dewey"
DOCTRINE = INSTALL / "data" / "h7-library-reinform-doctrine.json"
OVERLAP_PATH = STATE / "h7-library-overlap.json"
LIES_LEDGER = STATE / "h7-library-lies-index.jsonl"
PANEL_DIR = STATE / "h7-library-reinform"
BIGGEST_LIES_HDR = "## Deception Index (Ironclad — Autonomous Warfare)"
LEDGER_NAME = "corrections-ledger.jsonl"

_SHINGLE_RE = re.compile(r"[a-z0-9]{3,}")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(rel: str, name: str) -> Any | None:
    py = INSTALL / "lib" / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pagination() -> Any | None:
    return _import_mod("h7-library-pagination.py", "h7_pg_reinform")


def _dewey() -> Any | None:
    return _import_mod("field-dewey-library.py", "dewey_reinform")


def _truth() -> Any | None:
    return _import_mod("h7-library-truth.py", "truth_reinform")


def _correct() -> Any | None:
    return _import_mod("field-h7c-correct.py", "correct_reinform")


def _book_dir(book_id: str) -> Path | None:
    dewey = _dewey()
    if not dewey or not hasattr(dewey, "find_h7c"):
        return None
    hit = dewey.find_h7c(book_id, auto_convert=False)
    return hit.parent if hit and hit.is_file() else None


def _book_json_path(book_id: str) -> Path | None:
    d = _book_dir(book_id)
    return d / "book.json" if d else None


def _ledger_path(book_id: str) -> Path | None:
    d = _book_dir(book_id)
    return d / LEDGER_NAME if d else None


def _read_book(book_id: str) -> tuple[str, dict[str, Any], dict[str, Any]]:
    dewey = _dewey()
    if not dewey or not hasattr(dewey, "read_h7c_text"):
        return "", {}, {}
    text, header, stats = dewey.read_h7c_text(book_id)
    return text, header or {}, stats or {}


def _header_meta_fast(path: Path) -> dict[str, Any]:
    iron = _import_mod("ironclad-h7-access.py", "iron_reinform")
    if iron and hasattr(iron, "h7c_meta_fast"):
        try:
            row = iron.h7c_meta_fast(path)
            if row:
                return row
        except Exception:
            pass
    h7c = _import_mod("field-h7c-compression.py", "h7c_reinform")
    if h7c and hasattr(h7c, "read_h7c_header_file"):
        try:
            return h7c.read_h7c_header_file(path) or {}
        except Exception:
            pass
    return {"id": path.stem}


def _shingles(text: str, k: int = 32) -> set[str]:
    words = _SHINGLE_RE.findall(text.lower()[:4000])
    if len(words) < k:
        return {" ".join(words)} if words else set()
    return {" ".join(words[i : i + k]) for i in range(0, len(words) - k + 1, 8)}


def _lie_score(truth_score: float, flags: list[str]) -> float:
    return round((100.0 - truth_score) + 12.0 * len(flags), 1)


def evaluate_overlap(*, limit: int = 0, sample_near: bool = False) -> dict[str, Any]:
    """Scan library — exact sha256 groups + optional near-duplicate shingles. Never deletes books."""
    dewey = _dewey()
    paths: list[Path] = []
    if dewey and hasattr(dewey, "glob_h7c_files"):
        paths = dewey.glob_h7c_files()
    else:
        paths = sorted(DEWEY_ROOT.rglob("*.h7c"))
    if limit > 0:
        paths = paths[:limit]

    entries: list[dict[str, Any]] = []
    by_sha: dict[str, list[str]] = {}
    by_shelf: dict[str, list[dict[str, Any]]] = {}

    for path in paths:
        meta = _header_meta_fast(path)
        bid = str(meta.get("id") or path.stem)
        sha = str(meta.get("text_sha256") or "")
        shelf = str(meta.get("shelf") or path.parent.parent.name)
        row = {
            "id": bid,
            "title": str(meta.get("title") or bid),
            "shelf": shelf,
            "text_sha256": sha,
            "char_count": int(meta.get("char_count") or 0),
            "h7c": str(path.relative_to(INSTALL)) if path.is_relative_to(INSTALL) else str(path),
        }
        entries.append(row)
        if sha:
            by_sha.setdefault(sha, []).append(bid)
        by_shelf.setdefault(shelf, []).append(row)

    exact_groups = [
        {"text_sha256": sha, "book_ids": ids, "count": len(ids)}
        for sha, ids in by_sha.items()
        if len(ids) > 1
    ]

    near_pairs: list[dict[str, Any]] = []
    if sample_near:
        for shelf, rows in by_shelf.items():
            if len(rows) < 2 or len(rows) > 80:
                continue
            shingles_cache: dict[str, set[str]] = {}
            for i, a in enumerate(rows):
                if a["id"] not in shingles_cache:
                    try:
                        text, _, _ = _read_book(a["id"])
                        shingles_cache[a["id"]] = _shingles(text)
                    except Exception:
                        shingles_cache[a["id"]] = set()
                sa = shingles_cache[a["id"]]
                if not sa:
                    continue
                for b in rows[i + 1 : i + 12]:
                    if b["id"] not in shingles_cache:
                        try:
                            text, _, _ = _read_book(b["id"])
                            shingles_cache[b["id"]] = _shingles(text)
                        except Exception:
                            shingles_cache[b["id"]] = set()
                    sb = shingles_cache[b["id"]]
                    if not sb:
                        continue
                    inter = len(sa & sb)
                    union = len(sa | sb) or 1
                    jaccard = round(inter / union, 3)
                    if jaccard >= 0.55:
                        near_pairs.append({
                            "a": a["id"],
                            "b": b["id"],
                            "shelf": shelf,
                            "jaccard": jaccard,
                            "kind": "near_duplicate_sample",
                        })

    doc = {
        "schema": "h7-library-overlap/v1",
        "ok": True,
        "updated": _now(),
        "book_count": len(entries),
        "exact_duplicate_groups": exact_groups,
        "exact_duplicate_count": len(exact_groups),
        "near_duplicate_pairs": near_pairs[:500],
        "near_duplicate_count": len(near_pairs),
        "policy": "preserve_all_books_add_refs",
        "entries_sample": entries[:48],
    }
    _save(OVERLAP_PATH, doc)
    return doc


def _append_ledger(book_id: str, row: dict[str, Any]) -> None:
    lp = _ledger_path(book_id)
    if not lp:
        return
    lp.parent.mkdir(parents=True, exist_ok=True)
    with lp.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"book_id": book_id, **row}, ensure_ascii=False) + "\n")


def load_corrections(book_id: str, *, limit: int = 48) -> list[dict[str, Any]]:
    lp = _ledger_path(book_id)
    if not lp or not lp.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in lp.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def build_lies_index(book_id: str, *, max_entries: int = 24, max_sentences: int = 96) -> dict[str, Any]:
    """Rank questionable sentences; map to canonical page numbers."""
    text, header, _ = _read_book(book_id)
    if not text:
        return {"ok": False, "error": "empty_book", "book_id": book_id}

    pg = _pagination()
    truth = _truth()
    if not pg or not truth:
        return {"ok": False, "error": "modules_missing", "book_id": book_id}

    pmap = pg.page_map(text)
    locs = {r["index"]: r for r in pg.sentence_locations(text)}
    ic = truth._ironclad_slice() if hasattr(truth, "_ironclad_slice") else {}
    sentences = pg.split_sentences(text)[:max_sentences]
    candidates: list[dict[str, Any]] = []

    for i, sent in enumerate(sentences):
        row = truth.score_sentence(sent, book_id=book_id, index=i, ironclad=ic)
        verdict = str(row.get("verdict") or "")
        if verdict not in ("questionable", "unknown"):
            continue
        score = float(row.get("truth_score") or 0)
        flags = list(row.get("flags") or [])
        ls = _lie_score(score, flags)
        if ls < 40:
            continue
        loc = locs.get(i) or {}
        candidates.append({
            "rank": 0,
            "page": int(loc.get("page") or pg.locate_char(text, int(loc.get("char_start") or 0))),
            "sentence_index": i,
            "sentence_on_page": int(loc.get("sentence_on_page") or 1),
            "truth_score": score,
            "lie_score": ls,
            "verdict": verdict,
            "flags": flags,
            "excerpt": sent[:220],
            "readout": row.get("readout"),
        })

    candidates.sort(key=lambda r: (-r["lie_score"], r["page"], r["sentence_index"]))
    for rank, row in enumerate(candidates[:max_entries], start=1):
        row["rank"] = rank

    index_doc = {
        "schema": "h7-biggest-lies-index/v1",
        "book_id": book_id,
        "title": str(header.get("title") or book_id),
        "updated": _now(),
        "page_chars": pmap["page_chars"],
        "page_count": pmap["page_count"],
        "entries": candidates[:max_entries],
        "entry_count": len(candidates[:max_entries]),
        "scanned_sentences": len(sentences),
    }

    try:
        LIES_LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LIES_LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(index_doc, ensure_ascii=False) + "\n")
    except OSError:
        pass

    bjp = _book_json_path(book_id)
    if bjp and bjp.is_file():
        doc = _load(bjp, {})
        doc["lies_index"] = index_doc
        doc["reinform_updated"] = _now()
        _save(bjp, doc)

    return {"ok": True, **index_doc}


def _back_matter_block(entries: list[dict[str, Any]], *, page_chars: int) -> str:
    lines = [
        "\n---\n",
        BIGGEST_LIES_HDR,
        "",
        "Lie Librarian / Ironclad deception index — LIKELY_FALSE and UNVERIFIED claims. "
        f"Autonomous Warfare corpus gate. Canonical pages at {page_chars} characters per page. "
        "Verify before fielding.",
        "",
        "| Rank | Page | Score | Verdict | Claim |",
        "| ---: | ---: | ----: | :--- | :--- |",
    ]
    for row in entries:
        excerpt = str(row.get("excerpt") or "").replace("|", "/").replace("\n", " ")[:120]
        lines.append(
            f"| {row.get('rank')} | {row.get('page')} | {row.get('lie_score')} | "
            f"{row.get('verdict')} | {excerpt} |"
        )
    lines.append("")
    lines.append("*Reinformed — Hostess 7 / Ironclad corrections ledger on file. Autonomous Warfare corpus gate.*")
    lines.append("")
    return "\n".join(lines)


def reinform_book(
    book_id: str,
    *,
    apply: bool = False,
    correct: bool = True,
    build_lies: bool = True,
) -> dict[str, Any]:
    """Apply corrections, record ledger, attach Biggest Lies appendix — no information loss."""
    text, header, stats = _read_book(book_id)
    if not text:
        return {"ok": False, "error": "empty_book", "book_id": book_id}

    sha_before = str(header.get("text_sha256") or hashlib.sha256(text.encode()).hexdigest())
    corrections: list[str] = []
    correct_row: dict[str, Any] = {}

    if correct:
        corr = _correct()
        dewey = _dewey()
        path = dewey.find_h7c(book_id) if dewey and hasattr(dewey, "find_h7c") else None
        if corr and path and hasattr(corr, "correct_h7c_path"):
            try:
                correct_row = corr.correct_h7c_path(path, apply=apply)
                corrections = list(correct_row.get("corrections") or [])
                if apply and correct_row.get("changed"):
                    text, header, stats = _read_book(book_id)
            except Exception as exc:
                correct_row = {"ok": False, "error": str(exc)}

    lies_doc = build_lies_index(book_id) if build_lies else _load(_book_json_path(book_id) or Path(), {}).get("lies_index") or {}
    entries = list((lies_doc or {}).get("entries") or [])

    pg = _pagination()
    page_chars = int((pg.PAGE_CHARS if pg else 3200))
    new_text = text
    appendix_added = False
    if entries and BIGGEST_LIES_HDR not in text:
        new_text = text.rstrip() + _back_matter_block(entries, page_chars=page_chars)
        appendix_added = True

    sha_after = hashlib.sha256(new_text.encode()).hexdigest()
    changed = appendix_added or bool(correct_row.get("changed"))

    revision_row = {
        "schema": "h7-book-revision/v1",
        "revision_ts": _now(),
        "sources": ["ironclad", "hostess7", "field-h7c-correct"],
        "text_sha_before": sha_before,
        "text_sha_after": sha_after,
        "changed": changed,
        "applied": False,
        "corrections": corrections,
        "correct_row": {k: v for k, v in correct_row.items() if k not in ("path",)},
        "appendix_added": appendix_added,
        "lies_entry_count": len(entries),
    }

    if apply and appendix_added and changed:
        dewey = _dewey()
        h7c_mod = _import_mod("field-h7c-compression.py", "h7c_reinform_write")
        path = dewey.find_h7c(book_id) if dewey and hasattr(dewey, "find_h7c") else None
        if h7c_mod and path and path.is_file():
            meta = {
                k: v
                for k, v in header.items()
                if k in ("id", "title", "source", "dewey", "author", "category", "ironclad_citation", "hostess7_lane")
                and isinstance(v, (str, int, float, bool))
            }
            meta.setdefault("id", book_id)
            meta.setdefault("ironclad_citation", "ironclad:h7c:1")
            meta["reinformed_at"] = _now()
            meta["revision"] = int(meta.get("revision") or 0) + 1
            meta["field_layer"] = 1
            meta["block_wrapper"] = True
            try:
                packed = h7c_mod.pack_h7c(
                    new_text, meta, use_optimizer=True, format_version=2, update_balance_table=False,
                )
                packed = h7c_mod.wrap_h7c_block(packed, meta)
                _, round_text, _ = h7c_mod.decompress_h7c(
                    packed, verify=True, update_balance_table=False,
                )
                if round_text != new_text:
                    revision_row["apply_error"] = "roundtrip_mismatch"
                    revision_row["applied"] = False
                else:
                    snap = path.with_suffix(".h7c.reinform.tmp")
                    snap.write_bytes(packed)
                    snap.replace(path)
                    revision_row["applied"] = True
                    sha_after = hashlib.sha256(new_text.encode()).hexdigest()
                    revision_row["text_sha_after"] = sha_after
            except Exception as exc:
                revision_row["apply_error"] = str(exc)[:200]
                revision_row["applied"] = False

    _append_ledger(book_id, revision_row)

    bjp = _book_json_path(book_id)
    overlap_refs: list[str] = []
    if OVERLAP_PATH.is_file():
        ov = _load(OVERLAP_PATH, {})
        for grp in ov.get("exact_duplicate_groups") or []:
            ids = grp.get("book_ids") or []
            if book_id in ids:
                overlap_refs.extend([x for x in ids if x != book_id])
        for pair in ov.get("near_duplicate_pairs") or []:
            if pair.get("a") == book_id:
                overlap_refs.append(str(pair.get("b")))
            elif pair.get("b") == book_id:
                overlap_refs.append(str(pair.get("a")))

    if bjp:
        doc = _load(bjp, {}) if bjp.is_file() else {"id": book_id}
        doc["revision"] = int(doc.get("revision") or 0) + (1 if revision_row["applied"] else 0)
        doc["text_sha256"] = sha_after
        doc["reinform_updated"] = _now()
        doc["overlap_refs"] = sorted(set(overlap_refs))[:24]
        if lies_doc:
            doc["lies_index"] = lies_doc
        _save(bjp, doc)

    out = {
        "ok": True,
        "schema": "h7-library-reinform/v1",
        "book_id": book_id,
        "changed": changed,
        "applied": revision_row["applied"],
        "appendix_added": appendix_added,
        "lies_entries": len(entries),
        "corrections": corrections,
        "revision": revision_row,
        "overlap_refs": sorted(set(overlap_refs))[:24],
    }
    _save(PANEL_DIR / f"{book_id}.json", out)
    return out


def _harvest_indexed_ids() -> list[str]:
    found: list[str] = []
    for bj in DEWEY_ROOT.rglob("book.json"):
        try:
            doc = _load(bj, {})
        except Exception:
            continue
        bid = str(doc.get("id") or bj.parent.name)
        if doc.get("lies_index") or doc.get("all_lies_index"):
            found.append(bid)
    return found


def _order_book_ids(ids: list[str], *, priority: str = "", pattern: str = "") -> list[str]:
    pool = list(ids)
    if pattern:
        pool = [bid for bid in pool if pattern in bid or bid.startswith(pattern)]
    if priority != "beta4":
        return sorted(pool)
    combat = {
        "exploring_hand_to_hand_combat",
        "exploring_weaponized_combat",
        "exploring_combat",
    }
    anatomy = [bid for bid in pool if bid.startswith("exploring_the_")]
    combat_hits = [bid for bid in pool if bid in combat or "combat" in bid]
    indexed = _harvest_indexed_ids()
    exploring = [bid for bid in pool if bid.startswith("exploring_")]
    ordered: list[str] = []
    seen: set[str] = set()
    for group in (combat_hits, anatomy, indexed, exploring, pool):
        for bid in group:
            if bid in seen:
                continue
            seen.add(bid)
            ordered.append(bid)
    return ordered


def _h7c_has_appendix(path: Path) -> bool:
    try:
        blob = path.read_bytes()
    except OSError:
        return False
    return BIGGEST_LIES_HDR.encode("utf-8") in blob or b"Deception Index" in blob


def audit_status() -> dict[str, Any]:
    if not DEWEY_ROOT.is_dir():
        return {"ok": False, "error": "dewey_missing"}
    lies_index = appendix = ledger = 0
    sample_missing_appendix: list[str] = []
    total = 0
    hdr = BIGGEST_LIES_HDR.encode("utf-8")
    for book_json in DEWEY_ROOT.rglob("book.json"):
        bid = book_json.parent.name
        try:
            doc = _load(book_json, {})
        except Exception:
            doc = {}
        bid = str(doc.get("id") or bid)
        h7c = book_json.parent / f"{bid}.h7c"
        if not h7c.is_file():
            continue
        total += 1
        has_meta = bool(doc.get("lies_index") or doc.get("all_lies_index"))
        has_body = _h7c_has_appendix(h7c)
        if has_meta:
            lies_index += 1
            if not has_body and len(sample_missing_appendix) < 8:
                sample_missing_appendix.append(bid)
        if has_body:
            appendix += 1
        ledger_path = book_json.parent / LEDGER_NAME
        if ledger_path.is_file():
            ledger += 1
    return {
        "ok": True,
        "schema": "h7-library-reinform-audit/v1",
        "updated": _now(),
        "counts": {
            "h7c_books": total,
            "lies_index_metadata": lies_index,
            "deception_appendix_in_h7c": appendix,
            "corrections_ledger": ledger,
        },
        "completion_pct": {
            "lies_index": round(100.0 * lies_index / max(total, 1), 2),
            "appendix_in_body": round(100.0 * appendix / max(total, 1), 2),
            "corrections_ledger": round(100.0 * ledger / max(total, 1), 2),
        },
        "sample_missing_appendix": sample_missing_appendix,
    }


def reinform_all(
    *,
    limit: int = 0,
    apply: bool = False,
    lies_only: bool = True,
    pattern: str = "",
    priority: str = "",
) -> dict[str, Any]:
    dewey = _dewey()
    if not dewey or not hasattr(dewey, "glob_h7c_files"):
        return {"ok": False, "error": "dewey_missing"}
    ids = _order_book_ids([p.stem for p in dewey.glob_h7c_files()], priority=priority, pattern=pattern)
    if limit > 0:
        ids = ids[:limit]
    results: list[dict[str, Any]] = []
    changed = applied = errors = 0
    for bid in ids:
        try:
            row = reinform_book(
                bid,
                apply=apply,
                correct=not lies_only,
                build_lies=True,
            )
        except Exception as exc:
            row = {"ok": False, "book_id": bid, "error": str(exc)[:160]}
        results.append({
            "book_id": bid,
            "ok": row.get("ok"),
            "lies_entries": row.get("lies_entries"),
            "applied": row.get("applied"),
            "appendix_added": row.get("appendix_added"),
            "error": row.get("error"),
        })
        if not row.get("ok"):
            errors += 1
        if row.get("changed"):
            changed += 1
        if row.get("applied"):
            applied += 1
    return {
        "ok": errors == 0,
        "schema": "h7-library-reinform-batch/v1",
        "processed": len(results),
        "changed": changed,
        "applied": applied,
        "errors": errors,
        "lies_only": lies_only,
        "apply": apply,
        "pattern": pattern or None,
        "priority": priority or None,
        "results": results[:64],
    }


def panel_json(book_id: str) -> dict[str, Any]:
    text, header, _ = _read_book(book_id)
    pg = _pagination()
    bjp = _book_json_path(book_id)
    book_doc = _load(bjp, {}) if bjp and bjp.is_file() else {}
    pmap = pg.page_map(text) if pg and text else {}
    return {
        "ok": bool(text),
        "schema": "h7-library-reinform-panel/v1",
        "book_id": book_id,
        "title": str(header.get("title") or book_id),
        "page_chars": pmap.get("page_chars"),
        "page_count": pmap.get("page_count"),
        "pagination": pmap,
        "lies_index": book_doc.get("lies_index"),
        "overlap_refs": book_doc.get("overlap_refs") or [],
        "corrections": load_corrections(book_id),
        "revision": book_doc.get("revision"),
        "text_sha256": book_doc.get("text_sha256") or header.get("text_sha256"),
        "reinform_updated": book_doc.get("reinform_updated"),
        "appendix_page": pg.appendix_page(text) if pg and text else None,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd == "overlap":
        limit = 0
        sample_near = "--near" in sys.argv
        for arg in sys.argv[2:]:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
        print(json.dumps(evaluate_overlap(limit=limit, sample_near=sample_near), ensure_ascii=False, indent=2))
        return 0
    if cmd == "lies" and len(sys.argv) >= 3:
        out = build_lies_index(sys.argv[2])
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "reinform" and len(sys.argv) >= 3:
        apply = "--apply" in sys.argv
        out = reinform_book(sys.argv[2], apply=apply)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if out.get("ok") else 1
    if cmd == "audit":
        print(json.dumps(audit_status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "reinform-all":
        limit = 0
        apply = "--apply" in sys.argv
        lies_only = "--full" not in sys.argv
        priority = ""
        pattern = ""
        for arg in sys.argv[2:]:
            if arg.startswith("--limit="):
                limit = int(arg.split("=", 1)[1])
            elif arg.startswith("--priority="):
                priority = arg.split("=", 1)[1]
            elif arg.startswith("--pattern="):
                pattern = arg.split("=", 1)[1]
        print(json.dumps(
            reinform_all(limit=limit, apply=apply, lies_only=lies_only, priority=priority, pattern=pattern),
            ensure_ascii=False,
            indent=2,
        ))
        return 0
    if cmd == "corrections" and len(sys.argv) >= 3:
        print(json.dumps({"ok": True, "book_id": sys.argv[2], "corrections": load_corrections(sys.argv[2])}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("panel", "pagination") and len(sys.argv) >= 3:
        print(json.dumps(panel_json(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage: h7-library-reinform.py [overlap|lies|reinform|reinform-all|audit|corrections|panel] <book_id> [--apply] [--full] [--priority=beta4] [--pattern=exploring_the_] [--limit=N]",
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())