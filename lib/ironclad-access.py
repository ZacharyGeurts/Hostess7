#!/usr/bin/env python3
"""Ironclad Access — fast on-metal search/sort/H7 tools; read-only, loopback-safe."""
from __future__ import annotations

import importlib.util
import json
import os
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "ironclad-access-doctrine.json"
PANEL = STATE / "ironclad-access-panel.json"

_READ_ACTIONS = frozenset({
    "posture", "tools", "search", "sort", "h7_catalog", "h7_resolve", "h7_search",
    "file_search", "registry_search", "federated_search",
})
_BUILD_ACTIONS = frozenset({"build_h7_index", "build_registry_index", "build_file_index"})


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
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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


def _secure_api() -> Any | None:
    return _import_mod("ironclad_api_acc", "ironclad-secure-api.py")


def _search_index() -> Any | None:
    return _import_mod("ironclad_idx_acc", "ironclad-search-index.py")


def _h7_access() -> Any | None:
    return _import_mod("ironclad_h7_acc", "ironclad-h7-access.py")


def tools_manifest() -> dict[str, Any]:
    return {
        "schema": "ironclad-access-tools/v1",
        "read_only": True,
        "no_body_reads": True,
        "loopback_policy": "ironclad-secure-api",
        "tools": {
            "search": {
                "action": "search",
                "module": "lib/ironclad-search-index.py",
                "contexts": ["all", "registry", "files", "h7", "routes", "chips"],
                "security": "metadata_only",
            },
            "federated_search": {
                "action": "federated_search",
                "module": "lib/ironclad-search-index.py",
                "security": "metadata_only",
            },
            "sort": {
                "action": "sort",
                "module": "lib/field-best-sort.py",
                "contexts": ["registry_index", "file_list", "chip_paths", "catalog_index"],
            },
            "h7_catalog": {
                "action": "h7_catalog",
                "module": "lib/ironclad-h7-access.py",
                "security": "book_json_and_headers_only",
            },
            "h7_resolve": {
                "action": "h7_resolve",
                "module": "lib/ironclad-h7-access.py",
                "security": "path_map_lookup",
            },
            "h7_search": {
                "action": "h7_search",
                "module": "lib/ironclad-h7-access.py",
                "security": "token_index",
            },
            "file_search": {
                "action": "file_search",
                "module": "lib/ironclad-search-index.py",
                "security": "cached_index",
            },
            "registry_search": {
                "action": "registry_search",
                "module": "lib/ironclad-search-index.py",
                "security": "token_index",
            },
        },
        "build_actions": sorted(_BUILD_ACTIONS),
        "motto": "Ironclad on the metal — fast indexes, no H7 body reads, loopback gate",
    }


def sort_rows(
    rows: list[dict[str, Any]],
    *,
    context: str = "registry_index",
    n: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    idx = _search_index()
    if idx and hasattr(idx, "ironclad_sort"):
        return idx.ironclad_sort(rows, context=context, n=n or len(rows))
    api = _secure_api()
    if api:
        return api.ironclad_secure_api().sort_index(rows, context=context, n=n)
    return sorted(rows, key=lambda r: str(r.get("label") or r.get("title") or "")), {"algorithm": "fallback"}


def search(
    query: str,
    *,
    context: str = "all",
    limit: int = 48,
    file_roots: list[str] | None = None,
) -> dict[str, Any]:
    idx = _search_index()
    if idx and hasattr(idx, "federated_search"):
        return idx.federated_search(query, context=context, limit=limit, file_roots=file_roots)
    api = _secure_api()
    if api:
        return api.ironclad_secure_api().search_index(query, context=context, limit=limit)
    return {"ok": False, "error": "search_unavailable", "query": query}


def h7_catalog(*, refresh: bool = False) -> list[dict[str, Any]]:
    h7 = _h7_access()
    if not h7:
        return []
    if refresh and os.environ.get("IRONCLAD_ACCESS_BUILD", "").strip().lower() in ("1", "true", "yes"):
        h7.build_index(refresh=True)
    return h7.catalog_entries()


def h7_resolve(book_id: str) -> dict[str, Any]:
    h7 = _h7_access()
    if not h7:
        return {"ok": False, "error": "h7_access_missing", "book_id": book_id}
    path = h7.resolve_h7c_path(book_id)
    return {
        "ok": bool(path),
        "book_id": book_id,
        "h7c": str(path) if path else None,
        "no_body_read": True,
    }


def h7_search(query: str, *, limit: int = 24) -> list[dict[str, Any]]:
    h7 = _h7_access()
    if not h7:
        return []
    return h7.search_books(query, limit=limit)


def dispatch(action: str, *, body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read-only Ironclad tool dispatch — safe for loopback API."""
    act = str(action or "posture").strip().lower()
    body = body or {}
    if act in _BUILD_ACTIONS:
        if os.environ.get("IRONCLAD_ACCESS_BUILD", "").strip().lower() not in ("1", "true", "yes"):
            return {"ok": False, "error": "build_disabled", "hint": "set IRONCLAD_ACCESS_BUILD=1 to rebuild indexes"}
        if act == "build_h7_index":
            h7 = _h7_access()
            if h7:
                return {"ok": True, "built": h7.build_index(refresh=True)}
        if act == "build_registry_index":
            idx = _search_index()
            if idx:
                return {"ok": True, "built": idx.build_registry_index(refresh=True)}
        if act == "build_file_index":
            idx = _search_index()
            if idx:
                sg = str(Path(os.environ.get("SG_ROOT", INSTALL.parent)))
                return {"ok": True, "built": idx.build_file_index([sg, str(INSTALL)], refresh=True)}
        return {"ok": False, "error": "build_failed"}

    if act not in _READ_ACTIONS:
        return {"ok": False, "error": "action_denied", "allowed": sorted(_READ_ACTIONS)}

    if act in ("posture", "tools"):
        return {"ok": True, **posture()}

    if act == "search" or act == "federated_search":
        return search(
            str(body.get("query") or body.get("q") or ""),
            context=str(body.get("context") or "all"),
            limit=int(body.get("limit") or 48),
            file_roots=body.get("file_roots"),
        )

    if act == "sort":
        rows = list(body.get("entries") or body.get("rows") or [])
        sorted_rows, meta = sort_rows(rows, context=str(body.get("context") or "registry_index"))
        return {"ok": True, "entries": sorted_rows, "sort": meta}

    if act == "h7_catalog":
        return {"ok": True, "books": h7_catalog(refresh=bool(body.get("refresh")))}

    if act == "h7_resolve":
        return h7_resolve(str(body.get("book_id") or body.get("id") or ""))

    if act == "h7_search":
        return {"ok": True, "hits": h7_search(str(body.get("query") or body.get("q") or ""), limit=int(body.get("limit") or 24))}

    if act == "file_search":
        idx = _search_index()
        if idx and hasattr(idx, "search_files_fast"):
            roots = body.get("file_roots")
            hits = idx.search_files_fast(str(body.get("query") or ""), roots=roots, limit=int(body.get("limit") or 200))
            return {"ok": True, "hits": hits, "count": len(hits)}
        return {"ok": False, "error": "file_search_unavailable"}

    if act == "registry_search":
        idx = _search_index()
        if idx and hasattr(idx, "search_registry_fast"):
            hits = idx.search_registry_fast(str(body.get("query") or ""), limit=int(body.get("limit") or 48))
            return {"ok": True, "hits": hits, "count": len(hits)}
        return {"ok": False, "error": "registry_search_unavailable"}

    return posture()


def posture() -> dict[str, Any]:
    h7 = _h7_access()
    idx = _search_index()
    api = _secure_api()
    h7_posture = h7.posture() if h7 and hasattr(h7, "posture") else {}
    idx_posture = idx.posture() if idx and hasattr(idx, "posture") else {}
    grounded = False
    if api:
        try:
            grounded = bool(api.ironclad_secure_api().ironclad_grounded())
        except Exception:
            pass
    return {
        "schema": "ironclad-access/v1",
        "updated": _now(),
        "ok": True,
        "read_only": True,
        "no_body_reads": True,
        "ironclad_grounded": grounded,
        "tools": tools_manifest(),
        "h7": h7_posture,
        "search_index": idx_posture,
        "api_uri": "/api/ironclad/access",
        "secure_api_uri": "/api/ironclad/secure-api",
    }


def publish_panel() -> dict[str, Any]:
    doc = posture()
    _save(PANEL, doc)
    return {"ok": True, "panel": doc}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Ironclad Access")
    ap.add_argument("cmd", nargs="?", default="posture")
    ap.add_argument("--action", default="")
    ap.add_argument("--query", default="")
    ap.add_argument("--book", default="")
    ap.add_argument("--context", default="all")
    ap.add_argument("--limit", type=int, default=48)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    cmd = args.cmd.strip().lower()
    if cmd in ("posture", "json", "tools"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "search":
        print(json.dumps(search(args.query, context=args.context, limit=args.limit), ensure_ascii=False, indent=2))
        return 0
    if cmd == "h7-resolve":
        print(json.dumps(h7_resolve(args.book), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        rep = dispatch(args.action or "posture", body={
            "query": args.query, "q": args.query, "book_id": args.book,
            "context": args.context, "limit": args.limit,
        })
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0 if rep.get("ok", True) else 1
    print(json.dumps({"error": "usage", "cmds": ["posture", "search", "h7-resolve", "dispatch"]}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())