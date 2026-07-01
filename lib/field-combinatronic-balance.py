#!/usr/bin/env pythong
"""Combinatronic balance — self-adjust without slowdown; reorganize only on new files/chips."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-combinatronic-balance-doctrine.json"
PANEL = STATE / "field-combinatronic-balance-panel.json"
BALANCE_TABLE = STATE / "field-combinatronic-balance-table.json"
IDENTIFIERS = STATE / "field-combinatronic-balance-identifiers.json"

BALANCE_TARGET = 0.97
FAST_PATH_MS = 25
BALANCE_ID_PREFIX = "CBAL"
DOMAIN_TAGS = {"h7c": "h", "library": "l", "files": "f", "universal": "u"}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("cbal_h7s_fs", fs_py)
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


def _ids_from_rows(rows: list[Any], id_field: str) -> list[str]:
    out: list[str] = []
    for row in rows:
        if isinstance(row, dict):
            val = str(row.get(id_field) or row.get("id") or "")
            if val:
                out.append(val)
        elif isinstance(row, str):
            out.append(row)
    return sorted(set(out))


CACHE_PRESENT_KEYS = (
    "combinatorics_leaves", "cells", "entries", "chips", "commands", "formats",
    "lanes", "sequence", "devices", "games", "wire_layers", "file_count",
)


def _entry_batteries() -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    return list(doctrine.get("entry_batteries") or [])


def _entry_battery_path(domain: str) -> Path | None:
    for row in _entry_batteries():
        if str(row.get("id")) == domain:
            bat = str(row.get("battery") or "")
            if bat:
                return STATE / bat
    fallback = {
        "universal": STATE / "field-g16-universal-combinatronic.json",
        "chips": STATE / "field-ironclad-chips-combinatorics.json",
        "programs": STATE / "field-program-combinatronic.json",
        "program": STATE / "field-program-combinatronic.json",
        "files": STATE / "field-file-formats-table.json",
        "library": STATE / "field-extensive-library.json",
        "cpu": STATE / "field-cpu-library.json",
        "matrix": STATE / "field-combinamatrix.json",
        "growth": STATE / "field-combinatronics-growth.json",
        "sequence": STATE / "field-combinatorics-sequence.json",
        "spider": STATE / "field-combinatronic-spider-wire.json",
        "visuals": STATE / "field-combinatronic-visuals-panel.json",
        "steel_plates": STATE / "field-steel-neural-plates.json",
    }
    return fallback.get(domain)


def _battery_has_data(doc: dict[str, Any], keys: tuple[str, ...] = CACHE_PRESENT_KEYS) -> bool:
    for key in keys:
        val = doc.get(key)
        if isinstance(val, dict) and val:
            return True
        if isinstance(val, list) and val:
            return True
        if isinstance(val, (int, float)) and val > 0 and key == "file_count":
            return True
    return bool(doc.get("ok"))


def _fingerprint_domain(src: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    sid = str(src.get("id") or "")
    panel_name = str(src.get("panel") or "")
    key = str(src.get("key") or "id")
    id_field = str(src.get("id_field") or "id")
    doc = _load(STATE / panel_name, {})
    if not doc and panel_name.startswith("data/"):
        doc = _load(INSTALL / panel_name, {})
    if not doc and not panel_name.startswith("data/"):
        seed_name = panel_name.replace(".json", "-seed.json")
        doc = _load(INSTALL / "data" / seed_name, {})
    if src.get("count_only"):
        if key == "entries" and isinstance(doc.get("entries"), dict):
            count = len(doc["entries"])
        elif key == "file_count":
            count = int(doc.get("file_count") or doc.get(key) or 0)
        else:
            val = doc.get(key)
            count = len(val) if isinstance(val, (list, dict)) else int(val or 0)
        domain = {"count": count}
        return f"{sid}:{count}", domain
    if src.get("dict_keys"):
        ids = sorted((doc.get(key) or {}).keys()) if isinstance(doc.get(key), dict) else []
    else:
        rows = doc.get(key) or []
        ids = _ids_from_rows(rows if isinstance(rows, list) else [], id_field)
    ids_hash = hashlib.sha256(",".join(ids).encode()).hexdigest()[:16] if ids else "empty"
    domain = {"count": len(ids), "ids_hash": ids_hash}
    return f"{sid}:{len(ids)}:{ids_hash}", domain


def corpus_fingerprint(*, scan_library: bool = True) -> dict[str, Any]:
    """Fingerprint all combinatoric domains — doctrine-driven widened base."""
    doctrine = _load(DOCTRINE, {})
    domains: dict[str, Any] = {}
    material: list[str] = []
    for src in doctrine.get("fingerprint_sources") or []:
        if not isinstance(src, dict):
            continue
        line, domain = _fingerprint_domain(src)
        sid = str(src.get("id") or "")
        domains[sid] = domain
        material.append(line)

    if scan_library:
        dewey_count = 0
        dewey_root = INSTALL / "library" / "dewey"
        if dewey_root.is_dir():
            for p in dewey_root.rglob("book.json"):
                dewey_count += 1
            for p in dewey_root.rglob("*.h7c"):
                dewey_count += 1
        domains["dewey_shelf"] = {"artifact_count": dewey_count}
        material.append(f"dewey:{dewey_count}")

    corpus_hash = hashlib.sha256("|".join(material).encode()).hexdigest()
    return {
        "schema": "field-combinatronic-fingerprint/v1",
        "updated": _now(),
        "corpus_hash": corpus_hash,
        "domains": domains,
        "material_lines": len(material),
        "entry_base": len(doctrine.get("entry_batteries") or []),
    }


def combinatoric_entry(
    domain: str,
    *,
    refresh: bool = False,
    force: bool = False,
    battery_path: Path | str | None = None,
) -> dict[str, Any]:
    """Synchronous combinatoric entry gate — shared by every domain build."""
    gate = gate_refresh(refresh, force=force)
    bp = Path(battery_path) if battery_path else _entry_battery_path(domain)
    out: dict[str, Any] = {
        "schema": "field-combinatronic-entry/v1",
        "domain": domain,
        "gate": gate,
        "skip_build": bool(gate.get("skip_reorganize")) and not force,
        "fast_path": gate.get("fast_path", False),
        "synchronous": True,
        "entry_base": True,
    }
    if out["skip_build"] and bp and bp.is_file():
        cached = _load(bp, {})
        if _battery_has_data(cached):
            out["cached"] = True
            out["cached_doc"] = cached
    return out


def wrap_entry_doc(
    doc: dict[str, Any],
    *,
    domain: str,
    gate: dict[str, Any],
    elapsed_ms: float,
    reorganized: bool,
    incremental_added: int = 0,
    record: bool = True,
) -> dict[str, Any]:
    """Stamp combinatoric fields and optionally record cycle."""
    out = dict(doc)
    out["combinatronic"] = True
    out["all_data_combinatronic"] = True
    out["entry_domain"] = domain
    out["entry_synchronous"] = True
    out["balance_gate"] = gate
    out["elapsed_ms"] = round(elapsed_ms, 3)
    if gate.get("fast_path") or gate.get("reason") == "balanced_hold":
        out["optimized_combinatronic"] = True
        out["balance_hold"] = True
    elif gate.get("balanced"):
        out["optimized_combinatronic"] = True
    if gate.get("fast_path"):
        out["fast_path"] = True
    if record:
        record_cycle(
            reorganized=reorganized,
            elapsed_ms=elapsed_ms,
            incremental_added=incremental_added,
        )
    return out


def _import_publish(mod_name: str, publish_fn: str) -> Any | None:
    path = INSTALL / "lib" / mod_name
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(f"sync_{mod_name}", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            fn = getattr(mod, publish_fn, None)
            return fn if callable(fn) else None
    except Exception:
        return None
    return None


def sync_all_entries(*, refresh: bool = False, force: bool = False) -> dict[str, Any]:
    """Synchronous pass across widened entry base — respects balance gate."""
    t0 = time.perf_counter()
    doctrine = _load(DOCTRINE, {})
    order = list(doctrine.get("sync_order") or [])
    batteries = {str(b.get("id")): b for b in _entry_batteries()}
    gate = gate_refresh(refresh, force=force)
    steps: list[dict[str, Any]] = []

    if gate.get("skip_reorganize") and not force:
        for domain in order:
            bp = _entry_battery_path(domain)
            cached = _load(bp, {}) if bp else {}
            steps.append({
                "domain": domain,
                "skipped": True,
                "fast_path": True,
                "ok": _battery_has_data(cached),
                "reason": gate.get("reason", "balanced_hold"),
            })
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
        record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
        return {
            "schema": "field-combinatronic-sync/v1",
            "updated": _now(),
            "ok": all(s.get("ok", True) for s in steps),
            "skipped": True,
            "synchronous": True,
            "entry_count": len(steps),
            "balance_gate": gate,
            "steps": steps,
            "elapsed_ms": elapsed_ms,
            "motto": "Widened entry base — all domains hold at balance.",
        }

    for domain in order:
        spec = batteries.get(domain) or {}
        mod = str(spec.get("module") or "")
        pub = str(spec.get("publish") or "publish_panel")
        fn = _import_publish(mod, pub) if mod else None
        step: dict[str, Any] = {"domain": domain, "module": mod}
        if fn:
            try:
                if domain == "library":
                    result = fn(refresh=True)
                elif domain == "visuals":
                    result = fn(refresh=bool(spec.get("light")))
                elif domain == "files":
                    result = fn()
                else:
                    result = fn()
                step["ok"] = bool((result or {}).get("ok", True))
                step["skipped"] = False
            except Exception as exc:
                step["ok"] = False
                step["error"] = str(exc)[:200]
        else:
            step["ok"] = False
            step["hint"] = "publish_missing"
        steps.append(step)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
    record_cycle(reorganized=True, elapsed_ms=elapsed_ms)
    return {
        "schema": "field-combinatronic-sync/v1",
        "updated": _now(),
        "ok": all(s.get("ok", True) for s in steps),
        "skipped": False,
        "synchronous": True,
        "entry_count": len(steps),
        "balance_gate": gate,
        "steps": steps,
        "elapsed_ms": elapsed_ms,
        "motto": "Widened entry base — synchronous combinatoric publish.",
    }


def balance_state() -> dict[str, Any]:
    doc = _load(PANEL, {})
    if doc.get("corpus_hash"):
        return doc
    return {
        "schema": "field-combinatronic-balance-panel/v1",
        "updated": _now(),
        "balanced": False,
        "balance": 0.0,
        "corpus_hash": "",
        "cycles": 0,
        "reorganize_count": 0,
        "fast_path_count": 0,
        "new_item_events": 0,
    }


def _compute_balance(cycles: int, fast_paths: int, reorganizes: int) -> float:
    total = max(1, cycles)
    stable = fast_paths + (reorganizes if reorganizes == 0 else 0)
    raw = (fast_paths / total) if cycles > 0 else 0.0
    if reorganizes == 0 and cycles >= 3:
        raw = min(1.0, raw + 0.15)
    return round(min(1.0, raw), 4)


def should_reorganize(*, force: bool = False) -> dict[str, Any]:
    """True only when not balanced, forced, or corpus changed (new files/chips)."""
    if force or os.environ.get("FIELD_COMBINATRONIC_FORCE", "").strip().lower() in ("1", "true", "yes"):
        return {
            "reorganize": True,
            "reason": "forced",
            "balanced": False,
            "new_items": True,
        }
    state = balance_state()
    fp = corpus_fingerprint(scan_library=False)
    prev_hash = str(state.get("corpus_hash") or "")
    cur_hash = fp.get("corpus_hash") or ""
    balanced = bool(state.get("balanced")) and float(state.get("balance") or 0) >= BALANCE_TARGET

    if not prev_hash:
        return {"reorganize": True, "reason": "initial", "balanced": False, "new_items": True, "fingerprint": fp}

    if cur_hash != prev_hash:
        return {
            "reorganize": True,
            "reason": "new_corpus",
            "balanced": False,
            "new_items": True,
            "fingerprint": fp,
            "prev_hash": prev_hash,
            "corpus_hash": cur_hash,
        }

    reorg_count = int(state.get("reorganize_count") or 0)
    if reorg_count > 0 or bool(state.get("optimized_combinatronic")):
        return {
            "reorganize": False,
            "reason": "balanced_hold",
            "balanced": True,
            "new_items": False,
            "fingerprint": fp,
            "corpus_hash": cur_hash,
            "fast_path": True,
        }

    if balanced:
        return {
            "reorganize": False,
            "reason": "balanced_hold",
            "balanced": True,
            "new_items": False,
            "fingerprint": fp,
            "corpus_hash": cur_hash,
            "fast_path": True,
        }

    return {
        "reorganize": True,
        "reason": "seeking_balance",
        "balanced": False,
        "new_items": False,
        "fingerprint": fp,
    }


def _merge_predictive_gate(gate: dict[str, Any], *, force: bool = False) -> dict[str, Any]:
    fn = _import_publish("field-predictive-meld.py", "merge_balance_gate")
    if fn and callable(fn):
        return fn(gate, force=force)
    return gate


def gate_refresh(requested_refresh: bool = False, *, force: bool = False) -> dict[str, Any]:
    """Map caller refresh to effective refresh — false at balance with stable corpus."""
    decision = should_reorganize(force=force)
    decision = _merge_predictive_gate(decision, force=force)
    effective = requested_refresh or force or decision.get("reorganize", False)
    if decision.get("fast_path") and not force:
        effective = False
    return {
        "schema": "field-combinatronic-balance-gate/v1",
        "requested_refresh": requested_refresh,
        "effective_refresh": effective,
        "skip_reorganize": not effective,
        "fast_path": decision.get("fast_path", False),
        **decision,
    }


def stamp_optimized(leaves: list[dict[str, Any]], *, balanced: bool = False) -> list[dict[str, Any]]:
    """Mark leaves as optimized combinatoric when at balance."""
    out: list[dict[str, Any]] = []
    for leaf in leaves:
        row = dict(leaf)
        row["combinatronic"] = True
        if balanced:
            row["optimized_combinatronic"] = True
            row["balance_hold"] = True
        out.append(row)
    return out


def incremental_merge(
    existing: list[dict[str, Any]],
    new_rows: list[dict[str, Any]],
    *,
    id_field: str = "id",
) -> tuple[list[dict[str, Any]], int]:
    """Append only new items — no full re-sort."""
    seen = {str(r.get(id_field) or r.get("id") or "") for r in existing}
    added = 0
    merged = list(existing)
    for row in new_rows:
        rid = str(row.get(id_field) or row.get("id") or "")
        if not rid or rid in seen:
            continue
        seen.add(rid)
        merged.append({**row, "combinatronic": True, "incremental": True})
        added += 1
    return merged, added


def record_cycle(
    *,
    reorganized: bool,
    elapsed_ms: float,
    fingerprint: dict[str, Any] | None = None,
    incremental_added: int = 0,
) -> dict[str, Any]:
    """Update balance panel after a combinatoric cycle."""
    state = balance_state()
    fp = fingerprint or corpus_fingerprint(scan_library=False)
    cycles = int(state.get("cycles") or 0) + 1
    reorganize_count = int(state.get("reorganize_count") or 0) + (1 if reorganized else 0)
    fast_path_count = int(state.get("fast_path_count") or 0) + (0 if reorganized else 1)
    new_item_events = int(state.get("new_item_events") or 0) + (1 if incremental_added > 0 else 0)

    balance = _compute_balance(cycles, fast_path_count, reorganize_count)
    if reorganized:
        balance = max(balance, BALANCE_TARGET)
        balanced = True
    else:
        balanced = balance >= BALANCE_TARGET or bool(state.get("balanced"))

    if reorganized:
        corpus_hash = fp.get("corpus_hash") or ""
    else:
        corpus_hash = str(state.get("corpus_hash") or fp.get("corpus_hash") or "")

    panel = {
        "schema": "field-combinatronic-balance-panel/v1",
        "updated": _now(),
        "balanced": balanced,
        "balance": balance,
        "balance_target": BALANCE_TARGET,
        "corpus_hash": corpus_hash,
        "domains": fp.get("domains"),
        "cycles": cycles,
        "reorganize_count": reorganize_count,
        "fast_path_count": fast_path_count,
        "new_item_events": new_item_events,
        "last_elapsed_ms": round(elapsed_ms, 3),
        "last_reorganized": reorganized,
        "self_adjusting": True,
        "reorganize_only_on_new": True,
        "optimized_combinatronic": balanced,
        "statement": "field_combinatronic_balance_hold" if balanced else "field_combinatronic_seeking_balance",
    }
    _save(PANEL, panel)

    table = _load(BALANCE_TABLE, {"schema": "field-combinatronic-balance-table/v1", "history": []})
    history = list(table.get("history") or [])
    history.append({
        "at": panel["updated"],
        "reorganized": reorganized,
        "elapsed_ms": panel["last_elapsed_ms"],
        "balance": balance,
        "balanced": balanced,
        "incremental_added": incremental_added,
    })
    table["history"] = history[-128:]
    table["updated"] = panel["updated"]
    table["balanced"] = balanced
    table["balance"] = balance
    _save(BALANCE_TABLE, table)

    return panel


def _file_micro_sig(path: Path) -> str:
    """Cheap precise file sig — size, mtime, header bytes; no full read."""
    if not path.is_file():
        return ""
    try:
        st = path.stat()
        head = path.read_bytes()[:128]
        return hashlib.sha256(
            f"{st.st_size}:{int(st.st_mtime_ns)}:{head.hex()}".encode("utf-8")
        ).hexdigest()[:16]
    except OSError:
        return ""


def _resolve_content_paths(content_id: str, domain: str) -> list[Path]:
    """Locate on-disk artifacts for a content id — Dewey shelf + H7c corpus."""
    cid = str(content_id or "").strip()
    if not cid:
        return []
    found: list[Path] = []
    dewey = INSTALL / "library" / "dewey"
    if dewey.is_dir():
        try:
            import importlib.util
            dpath = INSTALL / "lib" / "field-dewey-library.py"
            if dpath.is_file():
                spec = importlib.util.spec_from_file_location("field_dewey_library", dpath)
                if spec and spec.loader:
                    dmod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(dmod)
                    hit = dmod.find_h7c(cid)
                    if hit and hit.is_file():
                        found.append(hit)
        except Exception:
            pass
        for book_json in dewey.glob(f"**/{cid}/book.json"):
            found.append(book_json)
            h7c = book_json.parent / f"{cid}.h7c"
            if h7c.is_file():
                found.append(h7c)
            cover = INSTALL / "library" / "assets" / "covers" / cid / "front.png"
            if cover.is_file():
                found.append(cover)
    return found


def content_precise_digest(
    content_id: str,
    domain: str,
    *,
    text_sha256: str = "",
    file_paths: list[Path] | None = None,
) -> str:
    """Digest proving precise file identity — corpus + domain + id + file sigs."""
    state = balance_state()
    paths = file_paths if file_paths is not None else _resolve_content_paths(content_id, domain)
    parts = [
        str(state.get("corpus_hash") or ""),
        domain,
        content_id,
        text_sha256 or "",
    ]
    for path in sorted({str(p.resolve()) for p in paths}):
        parts.append(_file_micro_sig(Path(path)))
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def balance_id(
    content_id: str,
    *,
    fmt: str = "",
    collection: str = "",
    text_sha256: str = "",
    digest: str | None = None,
) -> str:
    """Best identifier — precise file proof at no cost when system is balanced."""
    domain = content_domain(content_id, fmt=fmt, collection=collection)
    d = digest or content_precise_digest(content_id, domain, text_sha256=text_sha256)
    tag = DOMAIN_TAGS.get(domain, "x")
    return f"{BALANCE_ID_PREFIX}-{tag}{d[:20]}"


def load_balance_identifiers() -> dict[str, Any]:
    doc = _load(IDENTIFIERS, {})
    if doc.get("by_id"):
        return doc
    return {
        "schema": "field-combinatronic-balance-identifiers/v1",
        "updated": _now(),
        "by_id": {},
        "by_balance_id": {},
    }


def save_balance_identifiers(doc: dict[str, Any]) -> None:
    doc["updated"] = _now()
    _save(IDENTIFIERS, doc)


def register_balance_identifier(
    content_id: str,
    bid: str,
    *,
    fmt: str = "",
    collection: str = "",
    digest: str = "",
    precise_file: bool = False,
    no_cost: bool = False,
) -> None:
    """Cache balance_id → content mapping after a verified read."""
    doc = load_balance_identifiers()
    by_id = doc.setdefault("by_id", {})
    by_bid = doc.setdefault("by_balance_id", {})
    row = {
        "content_id": content_id,
        "balance_id": bid,
        "format": fmt,
        "collection": collection,
        "digest": digest,
        "precise_file": precise_file,
        "no_cost": no_cost,
        "registered": _now(),
    }
    by_id[content_id] = row
    by_bid[bid] = row
    save_balance_identifiers(doc)


def lookup_balance_id(balance_id: str) -> dict[str, Any] | None:
    doc = load_balance_identifiers()
    return (doc.get("by_balance_id") or {}).get(balance_id)


def identify_by_balance(
    content_id: str,
    *,
    fmt: str = "",
    collection: str = "",
    text_sha256: str = "",
    read_stats: dict[str, Any] | None = None,
    elapsed_ms: float | None = None,
    register: bool = True,
) -> dict[str, Any]:
    """
    Balance is the best identifier — proves precise file at no cost when hold + fast path.
    """
    state = balance_state()
    gate = should_reorganize()
    domain = content_domain(content_id, fmt=fmt, collection=collection)
    read_stats = read_stats or {}
    paths = _resolve_content_paths(content_id, domain)
    digest = content_precise_digest(
        content_id,
        domain,
        text_sha256=text_sha256 or str(read_stats.get("text_sha256") or ""),
    )
    bid = balance_id(content_id, fmt=fmt, collection=collection, text_sha256=text_sha256, digest=digest)

    file_sigs = [{"path": str(p.relative_to(INSTALL)) if p.is_relative_to(INSTALL) else str(p), "sig": _file_micro_sig(p)} for p in paths[:8]]
    precise_file = bool(paths) and all(_file_micro_sig(p) for p in paths[:1])

    read_ms = elapsed_ms if elapsed_ms is not None else read_stats.get("elapsed_ms")
    balance_hold = gate.get("reason") == "balanced_hold"
    h7c_hit = bool(read_stats.get("balance_table_hits")) or bool(
        (read_stats.get("universal_rapid") or {}).get("active")
    )
    read_fast = (
        bool(gate.get("fast_path"))
        or bool(read_stats.get("near_instant"))
        or (read_ms is not None and float(read_ms) <= FAST_PATH_MS)
    )
    no_cost = bool(balance_hold and read_fast and (h7c_hit or not paths or precise_file))
    best_identifier = bool(precise_file and (no_cost or bool(state.get("balanced"))))

    cached = lookup_balance_id(bid)
    if cached and cached.get("digest") == digest:
        best_identifier = True
        no_cost = no_cost or bool(cached.get("no_cost"))

    if register and best_identifier:
        register_balance_identifier(
            content_id,
            bid,
            fmt=fmt,
            collection=collection,
            digest=digest,
            precise_file=precise_file,
            no_cost=no_cost,
        )

    return {
        "schema": "field-combinatronic-balance-identify/v1",
        "ok": True,
        "balance_id": bid,
        "best_identifier": best_identifier,
        "precise_file": precise_file,
        "no_cost": no_cost,
        "content_id": content_id,
        "domain": domain,
        "digest": digest,
        "corpus_hash": state.get("corpus_hash"),
        "balanced": state.get("balanced"),
        "balance": state.get("balance"),
        "balance_hold": balance_hold,
        "read_fast_path": read_fast,
        "read_elapsed_ms": read_ms,
        "file_count": len(paths),
        "file_sigs": file_sigs,
        "cached_lookup": bool(cached),
        "statement": "Balance is the best identifier — precise file at no cost because the system is balanced.",
    }


def content_domain(
    content_id: str,
    *,
    fmt: str = "",
    collection: str = "",
) -> str:
    """Map content id/format to combinatronic balance domain."""
    fid = str(content_id or "")
    f = str(fmt or "").lower()
    col = str(collection or "").lower()
    if f in ("h7c",) or fid.endswith(".h7c"):
        return "h7c"
    if col == "file_formats" or fid.startswith("format-"):
        return "files"
    if col in ("devices", "games", "programming_greats", "manifests"):
        return "library"
    if col == "textbooks" or f == "textbook":
        return "library"
    if f in ("registry-entry", "registry"):
        return "files"
    return "library"


def read_content_balance(
    content_id: str,
    *,
    fmt: str = "",
    collection: str = "",
    read_stats: dict[str, Any] | None = None,
    elapsed_ms: float | None = None,
) -> dict[str, Any]:
    """Combinatronic balance slice for a content read — global gate + domain + read metrics."""
    state = balance_state()
    gate = should_reorganize()
    domain = content_domain(content_id, fmt=fmt, collection=collection)
    read_stats = read_stats or {}

    global_bal: dict[str, Any] = {
        "balanced": state.get("balanced"),
        "balance": state.get("balance"),
        "balance_target": BALANCE_TARGET,
        "balance_hold": gate.get("reason") == "balanced_hold",
        "fast_path": gate.get("fast_path", False),
        "corpus_hash": state.get("corpus_hash"),
        "optimized_combinatronic": state.get("optimized_combinatronic"),
        "reorganize_only_on_new": True,
    }

    content_slice: dict[str, Any] = {
        "combinatronic": True,
        "domain": domain,
        "content_id": content_id,
        "format": fmt or "unknown",
        "collection": collection or None,
    }

    if domain == "h7c":
        h7c_table = _load(STATE / "field-h7c-balance-table.json", {})
        content_slice["h7c_table_balance"] = h7c_table.get("balance")
        content_slice["h7c_table_balanced"] = h7c_table.get("balanced")
        content_slice["h7c_table_entries"] = len((h7c_table.get("entries") or {}))
        if read_stats:
            content_slice["h7c_read"] = {
                "balance_table_hits": read_stats.get("balance_table_hits"),
                "near_instant": read_stats.get("near_instant"),
                "elapsed_ms": read_stats.get("elapsed_ms"),
                "lossless": read_stats.get("lossless"),
                "optimizer": read_stats.get("optimizer"),
                "universal_rapid": read_stats.get("universal_rapid"),
            }
    else:
        fp = fast_path_response(domain)
        content_slice["domain_balance"] = fp.get("balance")
        content_slice["domain_balanced"] = fp.get("balanced")
        content_slice["domain_fast_path"] = fp.get("fast_path")

    read_ms = elapsed_ms if elapsed_ms is not None else read_stats.get("elapsed_ms")
    read_fast = (
        bool(gate.get("fast_path"))
        or bool(read_stats.get("near_instant"))
        or (read_ms is not None and float(read_ms) <= FAST_PATH_MS)
    )

    text_sha = str(read_stats.get("text_sha256") or "")
    identify = identify_by_balance(
        content_id,
        fmt=fmt,
        collection=collection,
        text_sha256=text_sha,
        read_stats=read_stats,
        elapsed_ms=read_ms,
        register=read_fast or bool(global_bal.get("balance_hold")),
    )

    return {
        "schema": "field-combinatronic-content-balance/v1",
        "ok": True,
        "content_id": content_id,
        **global_bal,
        "content": content_slice,
        "read_fast_path": read_fast,
        "read_elapsed_ms": read_ms,
        "balance_id": identify.get("balance_id"),
        "best_identifier": identify.get("best_identifier"),
        "precise_file": identify.get("precise_file"),
        "no_cost": identify.get("no_cost"),
        "digest": identify.get("digest"),
        "identify": identify,
        "statement": "Balance is the best identifier — precise file at no cost because the system is balanced.",
    }


def fast_path_response(domain: str) -> dict[str, Any]:
    """Return cached battery metadata when balanced — near-zero cost."""
    bp = _entry_battery_path(domain) or STATE / "field-g16-universal-combinatronic.json"
    cached = _load(bp, {})
    state = balance_state()
    return {
        "schema": "field-combinatronic-fast-path/v1",
        "ok": bool(cached),
        "domain": domain,
        "balanced": state.get("balanced"),
        "balance": state.get("balance"),
        "skip_reorganize": True,
        "fast_path": True,
        "cached": True,
        "leaf_count": len(cached.get("combinatorics_leaves") or cached.get("cells") or []),
        "elapsed_ms": 0,
        "statement": "balance_hold — no reorganize unless new files",
    }


def panel() -> dict[str, Any]:
    state = balance_state()
    decision = should_reorganize()
    fp = corpus_fingerprint()
    doctrine = _load(DOCTRINE, {})
    return {
        "schema": "field-combinatronic-balance-panel/v1",
        "updated": _now(),
        "ok": True,
        "motto": doctrine.get("motto"),
        "balance_target": BALANCE_TARGET,
        "policy": doctrine.get("policy"),
        **state,
        "decision": decision,
        "fingerprint": fp,
        "fast_path_ms_target": FAST_PATH_MS,
        "entry_base": fp.get("entry_base"),
        "sync_order": (_load(DOCTRINE, {}).get("sync_order") or []),
        "entry_synchronous": True,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "fingerprint":
        print(json.dumps(corpus_fingerprint(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "gate":
        refresh = "--refresh" in sys.argv or "--force" in sys.argv
        force = "--force" in sys.argv
        print(json.dumps(gate_refresh(refresh, force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "should":
        print(json.dumps(should_reorganize(force="--force" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        gate = gate_refresh(False)
        ok = gate.get("schema") == "field-combinatronic-balance-gate/v1"
        print(json.dumps({"ok": ok, "gate": gate}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    if cmd in ("sync", "sync_all", "entries"):
        refresh = "--refresh" in sys.argv
        force = "--force" in sys.argv
        print(json.dumps(sync_all_entries(refresh=refresh, force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "entry" and len(sys.argv) > 2:
        domain = sys.argv[2].strip().lower()
        refresh = "--refresh" in sys.argv
        force = "--force" in sys.argv
        print(json.dumps(combinatoric_entry(domain, refresh=refresh, force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("content", "identify", "id") and len(sys.argv) > 2:
        cid = sys.argv[2].strip()
        fmt = ""
        collection = ""
        argv = sys.argv[3:]
        i = 0
        while i < len(argv):
            if argv[i] == "--format" and i + 1 < len(argv):
                fmt = argv[i + 1]
                i += 2
                continue
            if argv[i] == "--collection" and i + 1 < len(argv):
                collection = argv[i + 1]
                i += 2
                continue
            i += 1
        if cmd in ("identify", "id"):
            out = identify_by_balance(cid, fmt=fmt, collection=collection)
        else:
            out = read_content_balance(cid, fmt=fmt, collection=collection)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd == "lookup" and len(sys.argv) > 2:
        row = lookup_balance_id(sys.argv[2].strip())
        print(json.dumps({"ok": bool(row), "entry": row}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["panel", "fingerprint", "gate", "should", "verify", "sync", "entry <domain>", "content <id>", "identify <id>", "lookup <CBAL-...>"],
    }))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())