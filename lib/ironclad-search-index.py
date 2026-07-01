#!/usr/bin/env python3
"""Ironclad search index — fast token lookup + best-sort; assists every search/sort lane."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
INDEX_PATH = STATE / "ironclad-search-index.json"
FILE_INDEX_PATH = STATE / "ironclad-file-search-index.json"
REGISTRY_INDEX_PATH = STATE / "ironclad-registry-token-index.json"

_TOKEN_RE = re.compile(r"[a-z0-9_./-]+", re.I)
_BLOCKED = frozenset({".git", "__pycache__", ".venv-browser", "node_modules"})


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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
    tmp.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _tokenize(*parts: str) -> list[str]:
    blob = " ".join(p for p in parts if p).lower()
    return [t for t in _TOKEN_RE.findall(blob) if len(t) >= 2]


def _row_fingerprint(row: dict[str, Any]) -> str:
    key = json.dumps(
        {k: row.get(k) for k in ("id", "path", "title", "label", "name", "collection", "kind")},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def ironclad_sort(
    rows: list[dict[str, Any]],
    *,
    context: str = "registry_index",
    n: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Sort through Ironclad secure API → field-best-sort."""
    api = _import_mod("ironclad_api_idx", "ironclad-secure-api.py")
    if api:
        try:
            inst = api.IroncladSecureAPI.instance()
            return inst.sort_index(rows, context=context, n=n or len(rows))
        except Exception:
            pass
    best = _import_mod("field_best_sort_idx", "field-best-sort.py")
    if best and hasattr(best, "apply_best"):
        try:
            return best.apply_best(rows, context=context, n=n or len(rows))
        except Exception:
            pass
    return sorted(rows, key=lambda r: str(r.get("label") or r.get("title") or r.get("name") or "").lower()), {
        "algorithm": "fallback_label",
        "context": context,
    }


def build_token_index(
    rows: list[dict[str, Any]],
    *,
    id_key: str = "id",
    text_keys: tuple[str, ...] = ("title", "label", "name", "path", "collection", "kind", "id"),
) -> dict[str, Any]:
    """Inverted token index — O(tokens) lookup instead of full-json scan."""
    postings: dict[str, list[str]] = {}
    catalog: dict[str, dict[str, Any]] = {}
    for row in rows:
        rid = str(row.get(id_key) or row.get("path") or _row_fingerprint(row))
        catalog[rid] = row
        seen: set[str] = set()
        for key in text_keys:
            for tok in _tokenize(str(row.get(key) or "")):
                if tok in seen:
                    continue
                seen.add(tok)
                postings.setdefault(tok, []).append(rid)
    return {
        "schema": "ironclad-token-index/v1",
        "updated": _now(),
        "entry_count": len(catalog),
        "token_count": len(postings),
        "postings": postings,
        "catalog": catalog,
    }


def search_token_index(
    index: dict[str, Any],
    query: str,
    *,
    limit: int = 48,
) -> list[dict[str, Any]]:
    q = query.lower().strip()
    if not q:
        catalog = index.get("catalog") or {}
        return list(catalog.values())[:limit]
    tokens = _tokenize(q)
    if not tokens:
        return []
    postings: dict[str, list[str]] = index.get("postings") or {}
    catalog: dict[str, dict[str, Any]] = index.get("catalog") or {}
    scores: dict[str, int] = {}
    for tok in tokens:
        for rid in postings.get(tok, []):
            scores[rid] = scores.get(rid, 0) + 4
        for ptok, rids in postings.items():
            if tok in ptok and ptok != tok:
                for rid in rids:
                    scores[rid] = scores.get(rid, 0) + 1
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    hits = [catalog[rid] for rid, _ in ranked if rid in catalog]
    return hits[:limit]


def build_registry_index(*, refresh: bool = False) -> dict[str, Any]:
    if REGISTRY_INDEX_PATH.is_file() and not refresh:
        cached = _load(REGISTRY_INDEX_PATH, {})
        if cached.get("schema") == "ironclad-token-index/v1" and cached.get("catalog"):
            return cached
    reg = _import_mod("lib_reg_idx", "field-library-registry.py")
    rows: list[dict[str, Any]] = []
    if reg and hasattr(reg, "registry_entries"):
        try:
            rows = list(reg.registry_entries())
        except Exception:
            pass
    idx = build_token_index(rows, id_key="id")
    idx["source"] = "field-library-registry"
    _save(REGISTRY_INDEX_PATH, idx)
    return idx


def search_registry_fast(query: str, *, limit: int = 48) -> list[dict[str, Any]]:
    idx = build_registry_index()
    hits = search_token_index(idx, query, limit=limit * 2)
    sorted_hits, _ = ironclad_sort(hits, context="registry_index", n=limit)
    return sorted_hits[:limit]


def _walk_files(
    root: Path,
    *,
    depth: int,
    on_row: Callable[[dict[str, Any]], None],
    remaining: list[int],
) -> None:
    if depth <= 0 or remaining[0] <= 0:
        return
    try:
        children = list(root.iterdir())
    except OSError:
        return
    children.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
    for child in children:
        if remaining[0] <= 0:
            return
        if child.name in _BLOCKED or child.name.startswith("."):
            continue
        row = {
            "path": str(child.resolve()),
            "name": child.name,
            "label": child.name,
            "kind": "dir" if child.is_dir() else "file",
            "family": "executable" if child.suffix.lower() in (".sh", ".exe", ".bin") else "data",
        }
        on_row(row)
        remaining[0] -= 1
        if child.is_dir():
            _walk_files(child, depth=depth - 1, on_row=on_row, remaining=remaining)


def build_file_index(
    roots: list[str],
    *,
    depth: int = 5,
    max_entries: int = 8000,
    refresh: bool = False,
) -> dict[str, Any]:
    sig = hashlib.sha256(json.dumps(sorted(roots)).encode()).hexdigest()[:12]
    if FILE_INDEX_PATH.is_file() and not refresh:
        cached = _load(FILE_INDEX_PATH, {})
        if (
            cached.get("schema") == "ironclad-token-index/v1"
            and cached.get("roots_sig") == sig
            and cached.get("catalog")
        ):
            return cached
    rows: list[dict[str, Any]] = []
    budget = [max_entries]

    def collect(row: dict[str, Any]) -> None:
        rows.append(row)

    for root_s in roots:
        root = Path(root_s).expanduser().resolve()
        if root.is_dir():
            _walk_files(root, depth=depth, on_row=collect, remaining=budget)
    idx = build_token_index(rows, id_key="path")
    idx["roots_sig"] = sig
    idx["roots"] = roots
    idx["source"] = "queen_file_browser"
    idx["max_depth"] = depth
    _save(FILE_INDEX_PATH, idx)
    return idx


def search_files_fast(
    query: str,
    *,
    roots: list[str] | None = None,
    limit: int = 200,
    depth: int = 5,
) -> list[dict[str, Any]]:
    if not roots:
        sg = Path(os.environ.get("SG_ROOT", INSTALL.parent))
        roots = [str(sg), str(INSTALL)]
    idx = build_file_index(roots, depth=depth)
    hits = search_token_index(idx, query, limit=limit * 2)
    sorted_hits, _ = ironclad_sort(hits, context="file_list", n=limit)
    return sorted_hits[:limit]


def federated_search(
    query: str,
    *,
    context: str = "all",
    limit: int = 48,
    file_roots: list[str] | None = None,
) -> dict[str, Any]:
    """Ironclad federated search — registry, files, routes; sorted hits."""
    q = str(query or "").strip()
    ctx = str(context or "all").lower()
    lim = max(1, min(int(limit or 48), 500))
    pools: list[dict[str, Any]] = []

    if ctx in ("all", "registry", "registry_index", "library"):
        pools.extend(search_registry_fast(q, limit=lim))

    if ctx in ("all", "h7", "h7_books", "catalog_index", "library_books"):
        h7 = _import_mod("ironclad_h7_fed", "ironclad-h7-access.py")
        if h7 and hasattr(h7, "search_books"):
            try:
                for row in h7.search_books(q, limit=lim):
                    hit = dict(row)
                    hit.setdefault("source", "ironclad-h7-access")
                    hit.setdefault("kind", "book")
                    pools.append(hit)
            except Exception:
                pass

    if ctx in ("all", "files", "file_list", "queen_files"):
        pools.extend(search_files_fast(q, roots=file_roots, limit=lim))

    if ctx in ("all", "routes", "api_registry", "api"):
        api = _import_mod("ironclad_api_fed", "ironclad-secure-api.py")
        if api:
            try:
                inst = api.IroncladSecureAPI.instance()
                rep = inst.search_index(q, context="routes", limit=lim)
                pools.extend(rep.get("hits") or [])
            except Exception:
                pass

    # Dedupe by path/id
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in pools:
        key = str(row.get("path") or row.get("id") or _row_fingerprint(row))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    sort_ctx = "file_list" if ctx in ("files", "file_list", "queen_files") else "registry_index"
    sorted_hits, sort_meta = ironclad_sort(unique, context=sort_ctx, n=lim)
    return {
        "ok": True,
        "schema": "ironclad-federated-search/v1",
        "query": q,
        "context": ctx,
        "count": len(sorted_hits[:lim]),
        "hits": sorted_hits[:lim],
        "sort": sort_meta,
        "ironclad_index": True,
        "updated": _now(),
    }


def posture() -> dict[str, Any]:
    reg = _load(REGISTRY_INDEX_PATH, {})
    files = _load(FILE_INDEX_PATH, {})
    return {
        "schema": "ironclad-search-index/v1",
        "updated": _now(),
        "ok": True,
        "registry_tokens": reg.get("token_count", 0),
        "registry_entries": reg.get("entry_count", 0),
        "file_tokens": files.get("token_count", 0),
        "file_entries": files.get("entry_count", 0),
        "paths": {
            "registry": str(REGISTRY_INDEX_PATH),
            "files": str(FILE_INDEX_PATH),
        },
        "motto": "Ironclad token index — search fast, sort once best ever",
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Ironclad search index")
    ap.add_argument("cmd", nargs="?", default="posture")
    ap.add_argument("arg", nargs="?", default="")
    ap.add_argument("--limit", type=int, default=48)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    cmd = args.cmd.strip().lower()
    if cmd in ("posture", "json", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "build-registry":
        print(json.dumps(build_registry_index(refresh=True), ensure_ascii=False)[:2000])
        return 0
    if cmd == "build-files":
        sg = str(Path(os.environ.get("SG_ROOT", INSTALL.parent)))
        print(json.dumps(build_file_index([sg, str(INSTALL)], refresh=args.refresh), ensure_ascii=False)[:2000])
        return 0
    if cmd == "search":
        print(json.dumps(federated_search(args.arg, limit=args.limit), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["posture", "build-registry", "build-files", "search QUERY"]}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())