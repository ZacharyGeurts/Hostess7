#!/usr/bin/env python3
"""Ironclad Secure API — singleton gate, registry index, Ironclad-grounded sort."""
from __future__ import annotations

import importlib.util
import ipaddress
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "ironclad-secure-api-doctrine.json"
PANEL = STATE / "ironclad-secure-api-panel.json"

_LOOPBACK = frozenset({"127.0.0.1", "::1", "::ffff:127.0.0.1"})
_BLOCKED_WRITE_ACTIONS = frozenset({
    "write_file", "save_file", "delete_file", "exec_shell", "exec", "eval",
    "overwrite", "patch_file", "rmtree", "unlink",
})
_API_PATH_RE = re.compile(r"^/api/[a-zA-Z0-9_./-]+$")


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = INSTALL / "lib" / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            import time
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None


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


def _is_loopback(peer: str) -> bool:
    if peer in _LOOPBACK:
        return True
    if str(peer).startswith("127."):
        return True
    try:
        ip = ipaddress.ip_address(peer)
        return ip.is_loopback
    except ValueError:
        return False


class IroncladSecureAPI:
    """Singleton — secure API gate, registry sort, route index for the whole stack."""

    _instance: IroncladSecureAPI | None = None

    def __init__(self) -> None:
        self._doctrine = _load(DOCTRINE, {})
        self._route_cache: list[dict[str, Any]] | None = None
        self._immediate_cache: dict[str, Any] | None = None

    @classmethod
    def instance(cls) -> IroncladSecureAPI:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def doctrine(self) -> dict[str, Any]:
        return dict(self._doctrine)

    def _immediate(self) -> dict[str, Any]:
        if self._immediate_cache is not None:
            return self._immediate_cache
        mod = _import_mod("ironclad_imm", "ironclad-immediate.py")
        if mod and hasattr(mod, "read_immediate"):
            try:
                self._immediate_cache = mod.read_immediate()
                return self._immediate_cache
            except Exception:
                pass
        self._immediate_cache = {"ironclad_sealed": False, "integrity_ok": False}
        return self._immediate_cache

    def ironclad_grounded(self) -> bool:
        imm = self._immediate()
        return bool(imm.get("ironclad_sealed") and imm.get("integrity_ok"))

    def security_headers(self) -> dict[str, str]:
        raw = (self._doctrine.get("security_headers") or {})
        out = {str(k): str(v) for k, v in raw.items()}
        out.setdefault("X-Ironclad-Secure-API", "singleton")
        out.setdefault("X-Ironclad-Citation", self._doctrine.get("ironclad_citation") or "ironclad:api:1")
        if self.ironclad_grounded():
            out["X-Ironclad-Grounded"] = "sealed"
        return out

    def gate(
        self,
        *,
        peer: str = "127.0.0.1",
        path: str = "",
        method: str = "GET",
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Admit or block an API request — loopback + Ironclad policy."""
        policy = self._doctrine.get("policy") or {}
        p = str(path or "").split("?", 1)[0]
        m = str(method or "GET").upper()

        if policy.get("loopback_only", True) and not _is_loopback(peer):
            return {
                "ok": False,
                "code": 403,
                "error": "loopback_only",
                "detail": "Ironclad Secure API — non-loopback peer rejected",
                "peer": peer,
                "ironclad_citation": self._doctrine.get("ironclad_citation"),
                "singleton": True,
            }

        if p and not _API_PATH_RE.match(p) and p.startswith("/api/"):
            return {
                "ok": False,
                "code": 400,
                "error": "api_path_invalid",
                "path": p,
                "singleton": True,
            }

        action = ""
        if isinstance(body, dict):
            action = str(body.get("action") or "").lower()
        if policy.get("destructive_blocked", True) and action in _BLOCKED_WRITE_ACTIONS:
            return {
                "ok": False,
                "code": 403,
                "error": "nondestructive_action_blocked",
                "action": action,
                "detail": "Destructive API actions blocked by Ironclad singleton",
                "singleton": True,
            }

        imm = self._immediate()
        grounded = self.ironclad_grounded()
        if policy.get("ironclad_grounding_required", True) and not grounded:
            if not p.startswith("/api/ironclad"):
                return {
                    "ok": False,
                    "code": 503,
                    "error": "ironclad_not_grounded",
                    "detail": "API withheld until Ironclad plate is sealed and integrity_ok",
                    "verdict": imm.get("verdict") or "WATCH",
                    "singleton": True,
                }

        hdrs = {k.lower(): v for k, v in (headers or {}).items()}
        if policy.get("human_integration_forbidden", True):
            if hdrs.get("x-human-integration") in ("1", "true", "yes"):
                return {
                    "ok": False,
                    "code": 403,
                    "error": "human_integration_forbidden",
                    "singleton": True,
                }

        return {
            "ok": True,
            "code": 200,
            "path": p,
            "method": m,
            "loopback": True,
            "ironclad_grounded": grounded,
            "ironclad_citation": self._doctrine.get("ironclad_citation"),
            "truth_percent": imm.get("truth_percent"),
            "singleton": True,
        }

    def _best_sort_mod(self) -> Any | None:
        return _import_mod("field_best_sort", "field-best-sort.py")

    def _normalize_sort_rows(self, rows: list[dict[str, Any]], *, context: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for row in rows:
            n = dict(row)
            if not n.get("label") and n.get("title"):
                n["label"] = n["title"]
            if context in ("registry_index", "library_registry", "catalog_index"):
                if not n.get("family"):
                    n["family"] = n.get("collection") or n.get("category") or "data"
            if context in ("api_registry", "api_index", "route_index"):
                if not n.get("kind"):
                    n["kind"] = n.get("layer") or "api"
            out.append(n)
        return out

    def sort_index(
        self,
        rows: list[dict[str, Any]],
        *,
        context: str = "registry_index",
        n: int | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Ironclad meld sort — one best algorithm per context."""
        prepared = self._normalize_sort_rows(list(rows), context=context)
        mod = self._best_sort_mod()
        if mod and hasattr(mod, "apply_best"):
            try:
                sorted_rows, meta = mod.apply_best(prepared, context=context, n=n or len(prepared))
                return sorted_rows, {**meta, "ironclad_secure_api": True, "singleton": True}
            except Exception:
                pass
        return sorted(prepared, key=lambda r: str(r.get("title") or r.get("label") or r.get("id") or "").lower()), {
            "context": context,
            "algorithm": "fallback_label",
            "singleton": True,
        }

    def _collect_routes_from_doc(self, doc: dict[str, Any], source: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []

        src = source

        def add(path: str, *, title: str = "", layer: str = "api", kind: str = "route") -> None:
            if not path or not str(path).startswith("/api/"):
                return
            out.append({
                "path": str(path),
                "title": title or path,
                "layer": layer,
                "kind": kind,
                "source": src,
            })

        api = doc.get("api")
        if isinstance(api, str):
            add(api, title=doc.get("title") or source)
        elif isinstance(api, dict):
            for key, val in api.items():
                if isinstance(val, str):
                    add(val, title=key, layer=key)
        elif isinstance(api, list):
            for item in api:
                if isinstance(item, str):
                    add(item, title=item)

        for row in doc.get("routes") or []:
            if isinstance(row, dict) and row.get("path"):
                add(str(row["path"]), title=str(row.get("title") or row["path"]),
                    layer=str(row.get("layer") or "api"))

        for row in (doc.get("wiring") or []):
            if isinstance(row, dict):
                for r in row.get("routes") or []:
                    add(str(r), title=row.get("role") or "", layer="wiring")

        net = doc.get("field_net") or doc.get("layers")
        if isinstance(net, list):
            for row in net:
                if isinstance(row, dict) and row.get("path"):
                    add(str(row["path"]), title=str(row.get("title") or ""), layer=str(row.get("layer") or "field"))

        return out

    def collect_routes(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        if self._route_cache is not None and not refresh:
            return list(self._route_cache)

        seen: set[str] = set()
        routes: list[dict[str, Any]] = []
        sources = list(self._doctrine.get("route_sources") or [])

        for rel in sources:
            doc = _load(INSTALL / rel, {})
            if not doc:
                continue
            for row in self._collect_routes_from_doc(doc, rel):
                p = row["path"]
                if p in seen:
                    continue
                seen.add(p)
                routes.append(row)

        api_doc = self._doctrine.get("api") or {}
        for key, val in api_doc.items():
            if isinstance(val, str) and val.startswith("/api/") and val not in seen:
                seen.add(val)
                routes.append({
                    "path": val,
                    "title": f"Ironclad secure API — {key}",
                    "layer": "ironclad",
                    "kind": "secure_api",
                    "source": "ironclad-secure-api-doctrine.json",
                })

        sorted_routes, sort_meta = self.sort_index(routes, context="api_registry")
        for i, row in enumerate(sorted_routes):
            row["index"] = i
        self._route_cache = sorted_routes
        self._last_sort_meta = sort_meta
        return list(sorted_routes)

    def registry_index(
        self,
        entries: list[dict[str, Any]] | None = None,
        *,
        context: str = "registry_index",
    ) -> dict[str, Any]:
        """Sort registry/catalog rows through Ironclad best-sort."""
        rows = list(entries or [])
        if not rows:
            reg = _import_mod("lib_reg", "field-library-registry.py")
            if reg and hasattr(reg, "registry_entries"):
                try:
                    rows = list(reg.registry_entries())
                except Exception:
                    rows = []
        sorted_rows, sort_meta = self.sort_index(rows, context=context)
        return {
            "ok": True,
            "schema": "ironclad-secure-api-registry-index/v1",
            "context": context,
            "count": len(sorted_rows),
            "entries": sorted_rows,
            "sort": sort_meta,
            "ironclad_grounded": self.ironclad_grounded(),
            "singleton": True,
            "updated": _now(),
        }

    def status(self) -> dict[str, Any]:
        imm = self._immediate()
        routes = self.collect_routes()
        return {
            "ok": True,
            "schema": "ironclad-secure-api/v1",
            "singleton": True,
            "title": self._doctrine.get("title"),
            "motto": self._doctrine.get("motto"),
            "ironclad_citation": self._doctrine.get("ironclad_citation"),
            "ironclad_grounded": self.ironclad_grounded(),
            "truth_percent": imm.get("truth_percent"),
            "verdict": imm.get("verdict"),
            "route_count": len(routes),
            "sort_contexts": list((self._doctrine.get("sort_contexts") or {}).keys()),
            "policy": self._doctrine.get("policy"),
            "api": self._doctrine.get("api"),
            "updated": _now(),
        }

    def publish_panel(self) -> dict[str, Any]:
        doc = self.status()
        doc["routes_sample"] = self.collect_routes()[:32]
        _save(PANEL, doc)
        return {"ok": True, "panel": doc, "panel_path": str(PANEL)}

    def search_index(
        self,
        query: str,
        *,
        context: str = "all",
        limit: int = 48,
    ) -> dict[str, Any]:
        """Federated Ironclad search — registry, catalog, routes, chips; sorted hits."""
        q = str(query or "").strip()
        ctx = str(context or "all").lower()
        lim = max(1, min(int(limit or 48), 200))

        idx = _import_mod("ironclad_search_api", "ironclad-search-index.py")
        if idx and hasattr(idx, "federated_search") and ctx in (
            "all", "registry", "registry_index", "library", "files", "file_list", "queen_files",
        ):
            try:
                rep = idx.federated_search(q, context=ctx, limit=lim)
                rep["ironclad_secure_api"] = True
                rep["singleton"] = True
                rep["ironclad_grounded"] = self.ironclad_grounded()
                return rep
            except Exception:
                pass

        pools: list[dict[str, Any]] = []

        if ctx in ("all", "registry", "registry_index", "library"):
            reg = _import_mod("lib_reg", "field-library-registry.py")
            if reg and hasattr(reg, "search_registry"):
                try:
                    for row in reg.search_registry(q, limit=lim):
                        hit = dict(row)
                        hit.setdefault("source", "registry")
                        hit.setdefault("kind", hit.get("collection") or "registry")
                        pools.append(hit)
                except Exception:
                    pass

        if ctx in ("all", "catalog", "catalog_index", "card_catalog"):
            cat = _import_mod("card_cat", "field-card-catalog.py")
            if cat and hasattr(cat, "search_cards"):
                try:
                    doc = cat.search_cards(q, limit=lim)
                    for row in doc.get("hits") or []:
                        hit = dict(row)
                        hit.setdefault("source", "card_catalog")
                        hit.setdefault("kind", "catalog")
                        pools.append(hit)
                except Exception:
                    pass

        if ctx in ("all", "chips", "chip_catalog"):
            chips = _import_mod("chips_cat", "field-chips-catalog.py")
            if chips and hasattr(chips, "search_autocomplete"):
                try:
                    for row in chips.search_autocomplete(q, limit=lim):
                        hit = dict(row)
                        hit.setdefault("source", "chips")
                        hit.setdefault("kind", "chip")
                        pools.append(hit)
                except Exception:
                    pass

        if ctx in ("all", "routes", "api_registry", "api"):
            routes = self.collect_routes()
            if q:
                ql = q.lower()
                for row in routes:
                    blob = json.dumps(row, ensure_ascii=False).lower()
                    if ql in blob:
                        hit = dict(row)
                        hit.setdefault("source", "api_routes")
                        hit.setdefault("kind", "route")
                        pools.append(hit)
            elif ctx in ("routes", "api_registry", "api"):
                for row in routes[:lim]:
                    hit = dict(row)
                    hit.setdefault("source", "api_routes")
                    hit.setdefault("kind", "route")
                    pools.append(hit)

        sort_ctx = "registry_index" if ctx in ("all", "registry", "catalog", "chips") else "api_registry"
        sorted_hits, sort_meta = self.sort_index(pools, context=sort_ctx, n=lim)
        return {
            "ok": True,
            "schema": "ironclad-secure-api-search/v1",
            "query": q,
            "context": ctx,
            "count": len(sorted_hits[:lim]),
            "hits": sorted_hits[:lim],
            "sort": sort_meta,
            "ironclad_grounded": self.ironclad_grounded(),
            "singleton": True,
            "updated": _now(),
        }

    def handle_api(self, path: str, *, query: dict[str, list[str]] | None = None) -> dict[str, Any]:
        """Dispatch Ironclad secure-api sub-routes."""
        p = path.rstrip("/")
        q = query or {}
        if p.endswith("/status") or p == "/api/ironclad/secure-api":
            return self.status()
        if p.endswith("/routes") or p.endswith("/route-index"):
            refresh = str((q.get("refresh") or ["0"])[0]).lower() in ("1", "true", "yes")
            routes = self.collect_routes(refresh=refresh)
            return {"ok": True, "routes": routes, "count": len(routes), "singleton": True}
        if p.endswith("/registry-index"):
            ctx = str((q.get("context") or ["registry_index"])[0])
            return self.registry_index(context=ctx)
        if p.endswith("/search"):
            query_str = str((q.get("q") or q.get("query") or [""])[0])
            ctx = str((q.get("context") or ["all"])[0])
            try:
                lim = int((q.get("limit") or ["48"])[0])
            except (TypeError, ValueError):
                lim = 48
            return self.search_index(query_str, context=ctx, limit=lim)
        if p.endswith("/sort"):
            ctx = str((q.get("context") or ["registry_index"])[0])
            bs = self._best_sort_mod()
            resolve = bs.resolve_best(ctx) if bs and hasattr(bs, "resolve_best") else {}
            return {
                "ok": True,
                "context": ctx,
                "hint": "POST JSON {entries:[...]} for live sort; GET returns resolve_best metadata",
                "resolve": resolve,
            }
        return self.status()


def ironclad_secure_api() -> IroncladSecureAPI:
    """Module-level singleton accessor."""
    return IroncladSecureAPI.instance()


def gate_request(**kwargs: Any) -> dict[str, Any]:
    return ironclad_secure_api().gate(**kwargs)


def sort_registry(rows: list[dict[str, Any]], *, context: str = "registry_index") -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return ironclad_secure_api().sort_index(rows, context=context)


def security_headers() -> dict[str, str]:
    return ironclad_secure_api().security_headers()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    api = ironclad_secure_api()
    if cmd in ("status", "panel", "json"):
        print(json.dumps(api.status(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("publish", "build"):
        print(json.dumps(api.publish_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "routes":
        print(json.dumps({"routes": api.collect_routes(refresh=True), "count": len(api.collect_routes())},
                         ensure_ascii=False, indent=2))
        return 0
    if cmd == "registry-index":
        print(json.dumps(api.registry_index(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "search":
        q = sys.argv[2] if len(sys.argv) > 2 else ""
        ctx = sys.argv[3] if len(sys.argv) > 3 else "all"
        print(json.dumps(api.search_index(q, context=ctx), ensure_ascii=False, indent=2))
        return 0
    if cmd == "gate" and len(sys.argv) > 2:
        verdict = api.gate(peer="127.0.0.1", path=sys.argv[2], method="GET")
        print(json.dumps(verdict, ensure_ascii=False, indent=2))
        return 0 if verdict.get("ok") else 1
    if cmd == "verify":
        st = api.status()
        routes = api.collect_routes(refresh=True)
        ok = st.get("singleton") is True and len(routes) >= 8 and api.ironclad_grounded()
        print(json.dumps({"ok": ok, "routes": len(routes), "grounded": api.ironclad_grounded()}, indent=2))
        return 0 if ok else 1
    print(json.dumps({"error": "usage", "cmds": ["status", "routes", "registry-index", "gate <path>", "verify", "publish"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())