#!/usr/bin/env python3
"""Sovereign endpoint registry — witnessed from→to for DNS, IP, port, URL, Pages, loopback, API, and more."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-endpoint-registry-doctrine.json"
SEED = INSTALL / "data" / "field-endpoint-registry-seed.json"
PAGES_SEED = INSTALL / "data" / "field-pages-movement-registry-seed.json"
LEDGER = STATE / "field-endpoint-registry.jsonl"
ROUTES = STATE / "field-endpoint-registry-routes.json"
PANEL = STATE / "field-endpoint-registry-panel.json"
PUBLIC = INSTALL / "data" / "field-endpoint-registry-public.json"
GENESIS = "0" * 64
REPO_RE = re.compile(r"^https?://github\.com/([^/]+)/([^/?#]+)", re.I)
PAGES_RE = re.compile(r"^https?://([^.]+)\.github\.io/([^/?#]*)/?", re.I)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _norm_url(url: str | None) -> str | None:
    if not url:
        return None
    u = str(url).strip().rstrip("/")
    return u or None


def _entry_hash(prev: str, body: dict[str, Any]) -> str:
    payload = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(f"{prev}:{payload}".encode()).hexdigest()


def _read_ledger() -> list[dict[str, Any]]:
    if not LEDGER.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _last_hash(rows: list[dict[str, Any]]) -> str:
    return str(rows[-1].get("hash") or GENESIS) if rows else GENESIS


def _ledger_append(row: dict[str, Any]) -> dict[str, Any]:
    rows = _read_ledger()
    prev = _last_hash(rows)
    body = {k: v for k, v in row.items() if k not in ("prev_hash", "hash")}
    digest = _entry_hash(prev, body)
    out = {**body, "prev_hash": prev, "hash": digest}
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(out, ensure_ascii=False) + "\n")
    return out


def verify_chain() -> dict[str, Any]:
    rows = _read_ledger()
    prev = GENESIS
    broken: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        if row.get("prev_hash") != prev:
            broken.append({"index": i, "reason": "prev_hash_mismatch", "id": row.get("id")})
        body = {k: v for k, v in row.items() if k not in ("prev_hash", "hash")}
        expect = _entry_hash(prev, body)
        if row.get("hash") != expect:
            broken.append({"index": i, "reason": "hash_mismatch", "id": row.get("id")})
        prev = str(row.get("hash") or prev)
    return {
        "ok": not broken,
        "count": len(rows),
        "genesis": GENESIS,
        "head": prev if rows else GENESIS,
        "broken": broken,
    }


def _route_key(layer: str, entity_id: str) -> str:
    return f"{layer}:{entity_id}"


def _load_routes() -> dict[str, Any]:
    doc = _load(ROUTES, {"schema": "field-endpoint-registry-routes/v1", "routes": {}})
    doc.setdefault("routes", {})
    return doc


def _save_routes(doc: dict[str, Any]) -> None:
    doc["updated"] = _utc()
    _save(ROUTES, doc)


def _apply_route(layer: str, entity_id: str, to_val: str | None, *, mirrors: list[str] | None = None) -> None:
    doc = _load_routes()
    key = _route_key(layer, entity_id)
    routes = doc.setdefault("routes", {})
    cur = routes.get(key) or {"layer": layer, "id": entity_id}
    if to_val:
        cur["canonical"] = _norm_url(to_val) or to_val
    if mirrors:
        chain = list(cur.get("mirror_chain") or [])
        for m in mirrors:
            m = _norm_url(m)
            if m and m not in chain:
                chain.append(m)
        cur["mirror_chain"] = chain
    cur["updated"] = _utc()
    routes[key] = cur
    if layer == "mirror" and "/" in entity_id:
        pages_key = _route_key("pages", entity_id)
        pages = routes.get(pages_key) or {"layer": "pages", "id": entity_id}
        chain = list(pages.get("mirror_chain") or [])
        canon = pages.get("canonical") or cur.get("canonical")
        if canon:
            canon = _norm_url(canon)
            if canon and canon not in chain:
                chain.insert(0, canon)
        for m in cur.get("mirror_chain") or []:
            if m and m not in chain:
                chain.append(m)
        if to_val:
            tv = _norm_url(to_val)
            if tv and tv not in chain:
                chain.append(tv)
        pages["mirror_chain"] = chain
        pages["updated"] = _utc()
        routes[pages_key] = pages
    _save_routes(doc)


def record(
    *,
    layer: str,
    kind: str,
    entity_id: str,
    from_val: str | None = None,
    to_val: str | None = None,
    witness: str = "operator",
    reason: str = "",
    at: str | None = None,
    mirrors: list[str] | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry_id = f"{layer}:{entity_id}:{kind}:{at or _utc()}"
    row = {
        "schema": "field-endpoint-movement/v1",
        "id": entry_id,
        "at": at or _utc(),
        "layer": layer,
        "kind": kind,
        "entity_id": entity_id,
        "from": _norm_url(from_val) if from_val and "://" in str(from_val) else from_val,
        "to": _norm_url(to_val) if to_val and "://" in str(to_val) else to_val,
        "witness": witness,
        "reason": reason,
        "meta": meta or {},
    }
    out = _ledger_append(row)
    if to_val:
        _apply_route(layer, entity_id, str(to_val), mirrors=mirrors)
    elif mirrors:
        _apply_route(layer, entity_id, None, mirrors=mirrors)
    return out


def _seed_rows_from_file(path: Path) -> list[dict[str, Any]]:
    doc = _load(path, {})
    return list(doc.get("movements") or doc.get("entries") or [])


def _ingest_pages_hub(rows: list[dict[str, Any]], seen: set[str]) -> None:
    hub = _load(INSTALL / "data" / "ammoos-pages-hub.json", {})
    for key, spec in (hub.get("repos") or {}).items():
        if not isinstance(spec, dict):
            continue
        slug = f"ZacharyGeurts/{key}"
        git = str(spec.get("git_repo") or spec.get("github") or "").strip()
        pages = str(spec.get("pages_url") or spec.get("url") or "").strip()
        mirror = str(spec.get("pages_mirror") or "").strip()
        if pages:
            rid = f"pages:{slug}:canonical"
            if rid not in seen:
                seen.add(rid)
                rows.append({
                    "layer": "pages", "kind": "canonical", "entity_id": slug,
                    "from_url": git if git.startswith("https://github.com") else None,
                    "to_url": pages, "witness": "ammoos-pages-hub",
                    "reason": spec.get("title") or key, "at": "2026-03-01T00:00:00Z",
                })
        if mirror:
            rid = f"mirror:{slug}:{mirror}"
            if rid not in seen:
                seen.add(rid)
                rows.append({
                    "layer": "mirror", "kind": "mirror_add", "entity_id": slug,
                    "from_url": pages or None, "to_url": mirror,
                    "witness": "ammoos-pages-hub", "reason": "pages_mirror", "at": "2026-07-03T00:00:00Z",
                })


def _ingest_dns_roots(rows: list[dict[str, Any]], seen: set[str]) -> None:
    dns = _load(INSTALL / "data" / "dns-legal-rfc-seed.json", {})
    for root in dns.get("root_servers") or []:
        letter = str(root.get("letter") or "").lower()
        host = str(root.get("hostname") or "")
        if not host:
            continue
        rid = f"icann_dns:root-{letter}"
        if rid in seen:
            continue
        seen.add(rid)
        rows.append({
            "layer": "icann_dns", "kind": "delegate", "entity_id": f"root.{letter}",
            "from_url": None, "to_url": host,
            "witness": "dns-legal-rfc-seed", "reason": f"IANA root {letter} — {root.get('operator')}",
            "at": "1987-11-01T00:00:00Z",
            "meta": {"ipv4": root.get("ipv4"), "ipv6": root.get("ipv6"), "operator": root.get("operator")},
        })
        for fam, ip in (("ipv4", root.get("ipv4")), ("ipv6", root.get("ipv6"))):
            if not ip:
                continue
            iid = f"ip:root-{letter}-{fam}"
            if iid in seen:
                continue
            seen.add(iid)
            rows.append({
                "layer": "ip", "kind": "canonical", "entity_id": f"{host}/{fam}",
                "from_url": None, "to_url": ip,
                "witness": "dns-legal-rfc-seed", "reason": f"Root server {host}",
                "at": "1987-11-01T00:00:00Z",
            })


def _ingest_loopback(rows: list[dict[str, Any]], seen: set[str]) -> None:
    specs = [
        ("field-github-resilience-doctrine.json", "loopback_authority"),
        ("hostess7-supreme-authority.json", None),
    ]
    res = _load(INSTALL / "data" / "field-github-resilience-doctrine.json", {})
    lb = res.get("loopback_authority") or {}
    base = str(lb.get("base") or "http://127.0.0.1:9477")
    port = int(lb.get("port") or 9477)
    rid = "loopback:threat-panel"
    if rid not in seen:
        seen.add(rid)
        rows.append({
            "layer": "loopback", "kind": "canonical", "entity_id": "threat-panel",
            "from_url": None, "to_url": base,
            "witness": "field-github-resilience", "reason": "Sovereign threat panel authority",
            "at": "2026-01-01T00:00:00Z", "meta": {"port": port},
        })
    queen = "http://127.0.0.1:9481"
    rid = "loopback:queen-browser"
    if rid not in seen:
        seen.add(rid)
        rows.append({
            "layer": "loopback", "kind": "canonical", "entity_id": "queen-browser",
            "from_url": None, "to_url": queen,
            "witness": "hostess7-supreme-authority", "reason": "Queen secured shell",
            "at": "2026-01-01T00:00:00Z", "meta": {"port": 9481},
        })


def _ingest_ports(rows: list[dict[str, Any]], seen: set[str]) -> None:
    doc = _load(INSTALL / "data" / "field-botnet-legal-ports-doctrine.json", {})
    gh = doc.get("github_service_ports") or {}
    for p in gh.get("ports") or []:
        pid = f"port:github-service-{p}"
        if pid in seen:
            continue
        seen.add(pid)
        rows.append({
            "layer": "port", "kind": "port_reserve", "entity_id": f"github/{p}",
            "from_url": None, "to_url": str(p),
            "witness": "field-botnet-legal-ports", "reason": gh.get("note") or "GitHub service port",
            "at": "2026-02-01T00:00:00Z",
        })
    ctx = doc.get("context_ports") or {}
    for p in ctx.get("ports") or []:
        pid = f"port:context-{p}"
        if pid in seen:
            continue
        seen.add(pid)
        rows.append({
            "layer": "port", "kind": "port_reserve", "entity_id": f"context/{p}",
            "from_url": None, "to_url": str(p),
            "witness": "field-botnet-legal-ports", "reason": ctx.get("note") or "Field context port",
            "at": "2026-02-01T00:00:00Z",
        })


def _ingest_scripts(rows: list[dict[str, Any]], seen: set[str]) -> None:
    doc = _load(INSTALL / "data" / "field-scripts-registry.json", {})
    for name, path in (doc.get("canonical") or {}).items():
        sid = f"script:{name}"
        if sid in seen:
            continue
        seen.add(sid)
        rows.append({
            "layer": "script", "kind": "canonical", "entity_id": name,
            "from_url": None, "to_url": path,
            "witness": "field-scripts-registry", "reason": "Canonical script path",
            "at": "2026-06-29T00:00:00Z",
        })
    for old, new in (doc.get("merge_map") or {}).items():
        mid = f"script:merge:{old}"
        if mid in seen:
            continue
        seen.add(mid)
        rows.append({
            "layer": "script", "kind": "merge_map", "entity_id": old,
            "from_url": old, "to_url": new,
            "witness": "field-scripts-registry", "reason": "Deprecated → canonical",
            "at": "2026-06-29T00:00:00Z",
        })


def _ingest_github_everyone(rows: list[dict[str, Any]], seen: set[str]) -> None:
    doc = _load(INSTALL / "data" / "field-github-everyone-doctrine.json", {})
    for slug, chain in (doc.get("repo_mirrors") or {}).items():
        if not chain:
            continue
        rid = f"mirror:doctrine:{slug}"
        if rid in seen:
            continue
        seen.add(rid)
        rows.append({
            "layer": "mirror", "kind": "mirror_add", "entity_id": slug,
            "from_url": chain[0] if chain else None,
            "to_url": chain[-1] if len(chain) > 1 else chain[0],
            "witness": "field-github-everyone-doctrine",
            "reason": "repo_mirrors fallback chain",
            "at": "2026-07-03T00:00:00Z",
            "meta": {"chain": chain},
        })


def _ingest_stack_index(rows: list[dict[str, Any]], seen: set[str]) -> None:
    idx = _load(INSTALL / "H7updater/data/h7updater-stack-index.json", {})
    for ent in idx.get("entries") or []:
        if not isinstance(ent, dict):
            continue
        slug = str(ent.get("github") or "")
        pages = str(ent.get("pages_url") or "").strip()
        repo = str(ent.get("repo_url") or "").strip()
        if not slug:
            continue
        if pages:
            rid = f"pages:{slug}:stack-index"
            if rid not in seen:
                seen.add(rid)
                rows.append({
                    "layer": "pages", "kind": "canonical", "entity_id": slug,
                    "from_url": repo or None, "to_url": pages,
                    "witness": "h7updater-stack-index", "reason": ent.get("role") or ent.get("name"),
                    "at": str(idx.get("generated") or "2026-03-01T00:00:00Z"),
                })


def _ingest_folder_relocate(rows: list[dict[str, Any]], seen: set[str]) -> None:
    doc = _load(INSTALL / "data" / "folder-consolidation-manifest.json", {})
    for key, spec in (doc.get("relocate") or {}).items():
        if not isinstance(spec, dict):
            continue
        fid = f"file:relocate:{key}"
        if fid in seen:
            continue
        seen.add(fid)
        rows.append({
            "layer": "file", "kind": "relocate", "entity_id": key,
            "from_url": str(spec.get("from") or "."), "to_url": str(spec.get("to") or ""),
            "witness": "folder-consolidation-manifest",
            "reason": str(spec.get("glob") or key),
            "at": "2026-05-01T00:00:00Z",
        })


def seed_historic(*, force: bool = False) -> dict[str, Any]:
    existing = _read_ledger()
    if existing and not force:
        return {"ok": True, "seeded": 0, "skipped": True, "reason": "ledger_nonempty"}

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in (SEED, PAGES_SEED):
        if path.is_file():
            for raw in _seed_rows_from_file(path):
                layer = str(raw.get("layer") or "pages")
                eid = str(raw.get("entity_id") or raw.get("repo_slug") or raw.get("id") or "")
                kind = str(raw.get("kind") or "seed_historic")
                key = f"{layer}:{eid}:{kind}"
                if key in seen:
                    continue
                seen.add(key)
                rows.append({
                    "layer": layer,
                    "kind": kind,
                    "entity_id": eid,
                    "from_url": raw.get("from_url") or raw.get("from"),
                    "to_url": raw.get("to_url") or raw.get("to"),
                    "witness": raw.get("witness") or "seed",
                    "reason": raw.get("reason") or "",
                    "at": raw.get("at"),
                    "meta": raw.get("meta") or {},
                })

    _ingest_pages_hub(rows, seen)
    _ingest_dns_roots(rows, seen)
    _ingest_loopback(rows, seen)
    _ingest_ports(rows, seen)
    _ingest_scripts(rows, seen)
    _ingest_github_everyone(rows, seen)
    _ingest_stack_index(rows, seen)
    _ingest_folder_relocate(rows, seen)

    seeded = 0
    for raw in rows:
        mirrors = None
        meta = raw.get("meta") or {}
        if isinstance(meta.get("chain"), list):
            mirrors = meta["chain"]
        record(
            layer=str(raw["layer"]),
            kind=str(raw["kind"]),
            entity_id=str(raw["entity_id"]),
            from_val=raw.get("from_url"),
            to_val=raw.get("to_url"),
            witness=str(raw.get("witness") or "seed_historic"),
            reason=str(raw.get("reason") or ""),
            at=raw.get("at"),
            mirrors=mirrors,
            meta=meta,
        )
        seeded += 1

    export_public()
    return {"ok": True, "seeded": seeded, "verify": verify_chain()}


def resolve(identifier: str) -> dict[str, Any]:
    """Resolve URL, domain, api path, repo slug, or route key to canonical + chain + history."""
    ident = str(identifier or "").strip()
    routes_doc = _load_routes()
    routes = routes_doc.get("routes") or {}
    history: list[dict[str, Any]] = []

    def _hist(layer: str | None, eid: str | None) -> None:
        if not eid:
            return
        for row in _read_ledger():
            if row.get("entity_id") == eid and (not layer or row.get("layer") == layer):
                history.append(row)

    # Direct route key
    if ":" in ident and ident in routes:
        r = routes[ident]
        _hist(r.get("layer"), r.get("id"))
        return {"ok": True, "match": "route_key", "route": r, "history": history[-12:]}

    # API path
    if ident.startswith("/api/"):
        for key, r in routes.items():
            if r.get("layer") == "api" and r.get("canonical") == ident:
                _hist("api", r.get("id"))
                return {"ok": True, "match": "api", "route": r, "history": history[-12:]}
        return {"ok": False, "match": "api", "identifier": ident}

    # URL
    if "://" in ident or ident.startswith("github.com"):
        url = ident if "://" in ident else f"https://{ident}"
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()

        m = REPO_RE.match(url)
        if m:
            slug = f"{m.group(1)}/{m.group(2)}"
            key = _route_key("pages", slug)
            r = routes.get(key) or routes.get(_route_key("repo", slug))
            mr = routes.get(_route_key("mirror", slug))
            _hist("pages", slug)
            chain = list((r or {}).get("mirror_chain") or [])
            for u in (mr or {}).get("mirror_chain") or []:
                if u and u not in chain:
                    chain.append(u)
            canon = (r or {}).get("canonical") or f"https://{m.group(1).lower()}.github.io/{m.group(2)}/"
            canon = _norm_url(canon) or canon
            if canon and canon not in chain:
                chain.insert(0, canon)
            return {
                "ok": True, "match": "github_repo", "repo_slug": slug,
                "canonical": canon, "mirror_chain": chain, "history": history[-12:],
            }

        m = PAGES_RE.match(url)
        if m:
            slug = f"{m.group(1)}/{m.group(2) or m.group(1)}"
            key = _route_key("pages", slug)
            r = routes.get(key)
            _hist("pages", slug)
            return {
                "ok": True, "match": "github_pages", "repo_slug": slug,
                "canonical": (r or {}).get("canonical") or url,
                "mirror_chain": (r or {}).get("mirror_chain") or [],
                "history": history[-12:],
            }

        for key, r in routes.items():
            canon = str(r.get("canonical") or "")
            if canon and (url.rstrip("/") == canon.rstrip("/") or url.startswith(canon)):
                _hist(r.get("layer"), r.get("id"))
                return {"ok": True, "match": "url", "route": r, "history": history[-12:]}

        if host:
            key = _route_key("icann_dns", host)
            r = routes.get(key)
            if r:
                _hist("icann_dns", host)
                return {"ok": True, "match": "dns", "route": r, "history": history[-12:]}

    # repo slug
    if "/" in ident and " " not in ident and not ident.startswith("/"):
        key = _route_key("pages", ident)
        r = routes.get(key)
        if r:
            _hist("pages", ident)
            return {
                "ok": True, "match": "repo_slug", "repo_slug": ident,
                "canonical": r.get("canonical"), "mirror_chain": r.get("mirror_chain") or [],
                "history": history[-12:],
            }

    return {"ok": False, "identifier": ident, "routes_count": len(routes)}


def routes_panel(*, layer: str | None = None) -> dict[str, Any]:
    doc = _load_routes()
    routes = doc.get("routes") or {}
    if layer:
        routes = {k: v for k, v in routes.items() if v.get("layer") == layer}
    return {"schema": "field-endpoint-registry-routes/v1", "updated": doc.get("updated"), "count": len(routes), "routes": routes}


def export_public(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    verify = verify_chain()
    routes = routes_panel()
    ledger_rows = _read_ledger()
    doc = {
        "ok": verify.get("ok", True),
        "schema": "field-endpoint-registry-public/v1",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "owner": doctrine.get("owner"),
        "scope": doctrine.get("scope"),
        "updated": _utc(),
        "layers": doctrine.get("layers") or [],
        "beyond_icann": [x["id"] for x in (doctrine.get("layers") or []) if x.get("beyond_icann")],
        "verify": verify,
        "route_count": routes.get("count"),
        "movement_count": len(ledger_rows),
        "routes": routes.get("routes"),
        "recent_movements": ledger_rows[-48:],
        "public_surfaces": doctrine.get("public_surfaces") or {},
        "api": "/api/field-endpoint-registry",
    }
    if write:
        _save(PUBLIC, doc)
        _save(PANEL, {**doc, "schema": "field-endpoint-registry-panel/v1"})
    return doc


def panel(*, seed_if_empty: bool = True) -> dict[str, Any]:
    if seed_if_empty and not _read_ledger():
        seed_historic()
    return export_public()


def pages_panel() -> dict[str, Any]:
    full = panel(seed_if_empty=False)
    routes = {k: v for k, v in (full.get("routes") or {}).items() if v.get("layer") in ("pages", "mirror", "repo")}
    movements = [m for m in (full.get("recent_movements") or []) if m.get("layer") in ("pages", "mirror", "repo", "url")]
    return {
        "ok": full.get("ok"),
        "schema": "field-pages-movement-panel/v1",
        "alias_of": "field-endpoint-registry",
        "title": "Pages movement (subset of endpoint registry)",
        "updated": full.get("updated"),
        "routes": routes,
        "recent_movements": movements,
        "api": "/api/field-pages-movement",
    }


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    cmd = (args[0] if args else "json").lower()

    if cmd in ("json", "panel"):
        print(json.dumps(panel(), indent=2))
        return 0
    if cmd == "pages":
        print(json.dumps(pages_panel(), indent=2))
        return 0
    if cmd == "seed":
        force = "--force" in args
        print(json.dumps(seed_historic(force=force), indent=2))
        return 0
    if cmd == "verify":
        print(json.dumps(verify_chain(), indent=2))
        return 0 if verify_chain().get("ok") else 1
    if cmd == "routes":
        layer = None
        for a in args[1:]:
            if a.startswith("--layer="):
                layer = a.split("=", 1)[1]
        print(json.dumps(routes_panel(layer=layer), indent=2))
        return 0
    if cmd == "resolve" and len(args) > 1:
        print(json.dumps(resolve(args[1]), indent=2))
        return 0
    if cmd == "record" and len(args) >= 5:
        layer, kind, entity_id, to_val = args[1:5]
        witness, reason, from_val = "cli", "", None
        mirrors: list[str] | None = None
        for a in args[5:]:
            if a.startswith("--witness="):
                witness = a.split("=", 1)[1]
            elif a.startswith("--reason="):
                reason = a.split("=", 1)[1]
            elif a.startswith("--from="):
                from_val = a.split("=", 1)[1]
            elif a.startswith("--mirror="):
                mirrors = (mirrors or []) + [a.split("=", 1)[1]]
            elif witness == "cli":
                witness = a
            elif not reason:
                reason = a
            else:
                reason = f"{reason} {a}"
        print(json.dumps(record(
            layer=layer, kind=kind, entity_id=entity_id,
            from_val=from_val, to_val=to_val, witness=witness, reason=reason, mirrors=mirrors,
        ), indent=2))
        export_public()
        return 0
    if cmd == "export":
        print(json.dumps(export_public(), indent=2))
        return 0

    print(json.dumps({"ok": False, "error": "usage", "cmds": [
        "json", "pages", "seed [--force]", "verify", "routes [--layer=pages]",
        "resolve <id>", "record <layer> <kind> <entity_id> <to> [witness] [reason]",
        "export",
    ]}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())