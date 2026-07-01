#!/usr/bin/env pythong
"""Shared OCR ingest/train/status pipeline for Hostess 7 vision chambers."""
from __future__ import annotations

import glob as globmod
import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

_INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
_STATE = Path(os.environ.get("NEXUS_STATE_DIR", _INSTALL / ".nexus-state"))
_LIB = _INSTALL / "lib"
_SG_ROOT = Path(os.environ.get("SG_ROOT", str(_INSTALL.parent)))
_HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(_INSTALL / "Hostess7")))

_EXTRACT_MOD: Any = None
_CLOCK_MOD: Any = None


def _load_extract() -> Any:
    global _EXTRACT_MOD
    if _EXTRACT_MOD is not None:
        return _EXTRACT_MOD
    py = _LIB / "hostess7-ocr-extract.py"
    spec = importlib.util.spec_from_file_location("hostess7_ocr_extract", py)
    if not spec or not spec.loader:
        raise ImportError("hostess7-ocr-extract.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _EXTRACT_MOD = mod
    return mod


def _now() -> str:
    global _CLOCK_MOD
    if _CLOCK_MOD is None:
        py = _LIB / "sovereign-clock.py"
        spec = importlib.util.spec_from_file_location("sovereign_clock_ocr_feed", py)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _CLOCK_MOD = mod
    if _CLOCK_MOD and hasattr(_CLOCK_MOD, "utc_z"):
        try:
            return _CLOCK_MOD.utc_z()
        except Exception:
            pass
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _final_eye_root() -> Path:
    try:
        import sys
        sys.path.insert(0, str(_LIB))
        from sg_paths import final_eye_root
        return final_eye_root()
    except Exception:
        env = os.environ.get("FINAL_EYE_ROOT", "").strip()
        if env:
            return Path(env).expanduser().resolve()
        return (_INSTALL / "Final_Eye").resolve()


def _grok16_root() -> Path:
    env = os.environ.get("GROK16_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    try:
        import sys
        sys.path.insert(0, str(_LIB))
        from sg_paths import grok16_root
        return grok16_root()
    except Exception:
        return (_INSTALL.parent / "Grok16").resolve()


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _resolve_source_path(spec: dict[str, Any]) -> Path | None:
    if spec.get("path_abs"):
        return Path(str(spec["path_abs"]))
    env = str(spec.get("path_env") or "")
    root = {
        "FINAL_EYE_ROOT": _final_eye_root(),
        "ZOCR_ROOT": _final_eye_root(),
        "ZNEWOCR_ROOT": _final_eye_root(),
        "HOSTESS7_ROOT": _HOSTESS7_ROOT,
        "NEXUS_INSTALL_ROOT": _INSTALL,
        "SG_ROOT": _SG_ROOT,
        "GROK16_ROOT": _grok16_root(),
    }.get(env, Path(os.environ.get(env, "")) if env else _SG_ROOT)
    rel = str(spec.get("path_rel") or "")
    if not rel:
        return None
    return Path(root) / rel


def _tail_jsonl(path: Path, *, limit: int = 500) -> list[dict[str, Any]]:
    if not path.is_file() or limit <= 0:
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows


def _ocr_core() -> Any | None:
    py = _LIB / "final-eye-ocr-core.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("final_eye_ocr_core_feed", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ocr_final_eye(path: Path) -> str:
    if not path.is_file():
        return ""
    core = _ocr_core()
    if core and hasattr(core, "ocr_image_text"):
        try:
            return str(core.ocr_image_text(path) or "").strip()
        except Exception:
            pass
    return ""


def _read_ocr_file(path: Path) -> str:
    core = _ocr_core()
    if core and hasattr(core, "read_ocr_text"):
        try:
            return str(core.read_ocr_text(path) or "")
        except Exception:
            pass
    if path.suffix.lower() == ".h7":
        h7_py = _LIB / "field-h7-format.py"
        if h7_py.is_file():
            try:
                spec = importlib.util.spec_from_file_location("field_h7_feed", h7_py)
                if spec and spec.loader:
                    h7 = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(h7)
                    if hasattr(h7, "open_any_h7_path"):
                        text, _ = h7.open_any_h7_path(path)
                        return str(text or "")
            except Exception:
                pass
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _text_chunks_from_row(row: dict[str, Any], spec: dict[str, Any], extract_mod: Any) -> list[str]:
    filter_key = str(spec.get("source_filter") or ("combat_motion" if spec.get("combat_filter") else ""))
    if filter_key and not extract_mod.row_passes_filter(row, filter_key):
        return []
    chunks: list[str] = []
    for field in spec.get("text_fields") or []:
        val = row.get(field)
        if isinstance(val, str) and val.strip():
            chunks.append(val)
    for field in (spec.get("ocr_file_field") or "ocr_file", "h7_file"):
        ocr_file = row.get(field)
        if ocr_file:
            fp = Path(str(ocr_file))
            if fp.is_file():
                text = _read_ocr_file(fp)
                if text.strip():
                    chunks.append(text)
                    break
    return chunks


def bind_chamber_ocr(
    chamber_id: str,
    *,
    install: Path | None = None,
    state: Path | None = None,
    doctrine_path: Path,
    corpus_path: Path,
    train_path: Path,
    ocr_ledger_path: Path,
    main_ledger_path: Path | None = None,
) -> dict[str, Callable[..., dict[str, Any]]]:
    """Return ingest_ocr_vision, train_ocr_vision, ocr_vision_status for a chamber."""
    install = install or _INSTALL
    state = state or _STATE
    extract_mod = _load_extract()

    def _append_ledger(row: dict[str, Any]) -> None:
        if not main_ledger_path:
            return
        try:
            with main_ledger_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def _ingest_text_blob(text: str, *, source_id: str, path: str, corpus: dict[str, Any], ocr_doc: dict[str, Any]) -> int:
        if not extract_mod.text_quality_ok(text):
            return 0
        max_c = int((ocr_doc.get("ingest") or {}).get("max_candidates_per_ingest") or 8000)
        if len(corpus.get("candidates") or []) >= max_c:
            return 0
        min_len = int((ocr_doc.get("train") or {}).get("min_candidate_len") or 8)
        added = 0
        known = corpus.setdefault("seen_hashes", [])
        seen_set = set(known[-50000:])
        for cand in extract_mod.extract_candidates(chamber_id, text, source_id=source_id, min_len=min_len):
            h = hashlib.sha256(f"{source_id}:{cand['text']}".encode()).hexdigest()[:24]
            if h in seen_set:
                continue
            seen_set.add(h)
            known.append(h)
            corpus["candidates"].append({
                **cand,
                "hash": h,
                "path": path,
                "ingested_at": _now(),
            })
            added += 1
            if len(corpus["candidates"]) >= max_c:
                break
        return added

    def ingest_ocr_vision(*, limit_per_source: int | None = None) -> dict[str, Any]:
        ocr_doc = _load(doctrine_path, {})
        ingest_cfg = ocr_doc.get("ingest") or {}
        max_files = limit_per_source or int(ingest_cfg.get("max_files_per_source") or 500)
        max_bytes = int(ingest_cfg.get("max_bytes_per_file") or 250000)

        corpus = _load(corpus_path, {
            "schema": f"hostess7-{chamber_id}-ocr-corpus/v1",
            "candidates": [],
            "seen_hashes": [],
            "sources": {},
        })
        corpus.setdefault("candidates", [])
        corpus.setdefault("seen_hashes", [])
        corpus.setdefault("sources", {})

        total_added = 0
        source_stats: dict[str, Any] = {}

        bundle_py = _INSTALL / "lib" / "field-h7s-desktop-bundle.py"
        if bundle_py.is_file():
            try:
                spec = importlib.util.spec_from_file_location("field_h7s_desktop_ocr_feed", bundle_py)
                if spec and spec.loader:
                    bmod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(bmod)
                    if hasattr(bmod, "ingest_ocr_feed"):
                        bundle_rows = bmod.ingest_ocr_feed(limit=max_files)
                        bundle_added = 0
                        for row in bundle_rows:
                            text = str(row.get("text") or "").strip()
                            if not text:
                                continue
                            bundle_added += _ingest_text_blob(
                                text,
                                source_id="desktop_h7s",
                                path=str(row.get("source") or "field-desktop.h7s"),
                                corpus=corpus,
                                ocr_doc=ocr_doc,
                            )
                        if bundle_added:
                            total_added += bundle_added
                            source_stats["desktop_h7s"] = {
                                "kind": "h7s_slice",
                                "rows": len(bundle_rows),
                                "added": bundle_added,
                            }
            except Exception:
                pass

        for spec in ocr_doc.get("feed_sources") or []:
            sid = str(spec.get("id") or "unknown")
            kind = str(spec.get("kind") or "jsonl")
            files_read = 0
            bytes_read = 0
            added = 0

            if kind == "jsonl":
                fp = _resolve_source_path(spec)
                if fp and fp.is_file():
                    for row in _tail_jsonl(fp, limit=max_files):
                        for chunk in _text_chunks_from_row(row, spec, extract_mod):
                            bytes_read += len(chunk)
                            added += _ingest_text_blob(chunk, source_id=sid, path=str(fp), corpus=corpus, ocr_doc=ocr_doc)
                        files_read += 1

            elif kind == "json":
                fp = _resolve_source_path(spec)
                if fp and fp.is_file():
                    try:
                        doc = json.loads(fp.read_text(encoding="utf-8", errors="replace")[:max_bytes])
                        nested = spec.get("nested")
                        rows = doc.get(nested) if nested else [doc]
                        for row in rows or []:
                            if isinstance(row, dict):
                                for chunk in _text_chunks_from_row(row, spec, extract_mod):
                                    bytes_read += len(chunk)
                                    added += _ingest_text_blob(chunk, source_id=sid, path=str(fp), corpus=corpus, ocr_doc=ocr_doc)
                        files_read = 1
                        bytes_read = fp.stat().st_size
                    except (OSError, json.JSONDecodeError):
                        pass

            elif kind == "glob":
                base = _resolve_source_path(spec)
                if spec.get("path_abs") and "*" in str(spec["path_abs"]):
                    paths = [Path(p) for p in globmod.glob(str(spec["path_abs"]))[:max_files]]
                elif base and "*" in base.name:
                    paths = sorted(base.parent.glob(base.name))[:max_files]
                elif base and base.suffix:
                    paths = sorted(base.parent.glob(base.name))[:max_files]
                else:
                    paths = []
                for fp in paths:
                    if not fp.is_file():
                        continue
                    try:
                        if spec.get("ocr_tesseract") or spec.get("ocr_final_eye"):
                            text = _ocr_final_eye(fp)
                        elif fp.suffix.lower() == ".h7":
                            text = _read_ocr_file(fp)[:max_bytes]
                        else:
                            text = fp.read_text(encoding="utf-8", errors="replace")[:max_bytes]
                        bytes_read += len(text)
                        added += _ingest_text_blob(text, source_id=sid, path=str(fp), corpus=corpus, ocr_doc=ocr_doc)
                        files_read += 1
                    except OSError:
                        continue

            total_added += added
            source_stats[sid] = {"files_read": files_read, "bytes_read": bytes_read, "candidates_added": added, "kind": kind}
            corpus["sources"][sid] = {**source_stats[sid], "updated": _now()}

        corpus["updated"] = _now()
        corpus["candidate_count"] = len(corpus.get("candidates") or [])
        corpus["ingest_total_added"] = int(corpus.get("ingest_total_added") or 0) + total_added
        _save(corpus_path, corpus)
        _append_ledger({"ts": _now(), "event": "ocr_ingest", "added": total_added, "sources": source_stats})
        try:
            with ocr_ledger_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "ts": _now(), "event": "ocr_ingest", "added": total_added, "sources": source_stats,
                }, ensure_ascii=False) + "\n")
        except OSError:
            pass
        return {"ok": True, "added": total_added, "candidate_count": corpus["candidate_count"], "sources": source_stats}

    def train_ocr_vision(*, verify: bool = True, limit: int = 500) -> dict[str, Any]:
        ocr_doc = _load(doctrine_path, {})
        train_cfg = ocr_doc.get("train") or {}
        corpus = _load(corpus_path, {"candidates": []})
        candidates = list(corpus.get("candidates") or [])
        if not candidates:
            ingest_ocr_vision()
            corpus = _load(corpus_path, {"candidates": []})
            candidates = list(corpus.get("candidates") or [])

        verified = 0
        attempts = 0
        samples: list[dict[str, Any]] = []
        for cand in candidates:
            if attempts >= limit:
                break
            text = str(cand.get("text") or "")
            if not text:
                continue
            attempts += 1
            ok = extract_mod.verify_candidate(chamber_id, text) if verify else False
            row = {**cand, "verified": ok}
            if ok:
                verified += 1
            samples.append(row)

        plausible_n = sum(
            1 for c in candidates
            if extract_mod.plausible_candidate(chamber_id, str(c.get("text") or ""))
        )
        total = len(candidates)
        rate = verified / max(plausible_n, 1)
        fluent_floor = int(train_cfg.get("fluent_samples_floor") or 40)
        master_floor = int(train_cfg.get("master_samples_floor") or 100)
        train_doc = {
            "schema": f"hostess7-{chamber_id}-ocr-train/v1",
            "updated": _now(),
            "candidate_count": total,
            "trained_count": attempts,
            "verified_count": verified,
            "verified_rate": round(rate, 4),
            "fluent": verified >= fluent_floor,
            "mastered": verified >= master_floor,
            "samples": samples[-24:],
            "sources": corpus.get("sources") or {},
        }
        _save(train_path, train_doc)
        _append_ledger({"ts": _now(), "event": "ocr_train", "verified": verified, "total": total, "rate": rate})
        return {"ok": True, **train_doc}

    def ocr_vision_status() -> dict[str, Any]:
        corpus = _load(corpus_path, {})
        train = _load(train_path, {})
        return {
            "schema": f"hostess7-{chamber_id}-ocr-status/v1",
            "updated": _now(),
            "corpus": {
                "candidate_count": len(corpus.get("candidates") or []),
                "ingest_total_added": corpus.get("ingest_total_added"),
                "sources": corpus.get("sources") or {},
            },
            "train": train,
        }

    return {
        "ingest_ocr_vision": ingest_ocr_vision,
        "train_ocr_vision": train_ocr_vision,
        "ocr_vision_status": ocr_vision_status,
    }


def handle_ocr_cli(
    cmd: str,
    *,
    ingest_fn: Callable[..., dict[str, Any]],
    train_fn: Callable[..., dict[str, Any]],
    status_fn: Callable[[], dict[str, Any]],
    usage: str,
) -> int | None:
    """Handle ocr-ingest|ocr-train|ocr-status CLI; return exit code or None if not matched."""
    import sys
    import json
    if cmd in ("ocr-ingest", "ocr_ingest", "ingest-ocr"):
        print(json.dumps(ingest_fn(), ensure_ascii=False))
        return 0
    if cmd in ("ocr-train", "ocr_train", "train-ocr"):
        lim = 500
        for arg in sys.argv[2:]:
            if arg.isdigit():
                lim = int(arg)
        print(json.dumps(train_fn(limit=lim), ensure_ascii=False))
        return 0
    if cmd in ("ocr-status", "ocr_status"):
        print(json.dumps(status_fn(), ensure_ascii=False))
        return 0
    if cmd in ("ocr-help",):
        print(json.dumps({"usage": usage}, ensure_ascii=False))
        return 0
    return None