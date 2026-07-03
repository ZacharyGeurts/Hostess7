#!/usr/bin/env pythong
"""GitHub legacy secure lane — stable open connection for canonical + old stack repos."""
from __future__ import annotations

import json
import os
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-github-legacy-doctrine.json"
PANEL = STATE / "field-github-legacy-panel.json"
CACHE = STATE / "field-github-legacy-probe.json"

UA_MODERN = "FieldInternetUnified/1.0"
UA_LEGACY = "Mozilla/5.0 (compatible; FieldGitHubLegacy/1.0; old-stack)"


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


def always_allow_domains() -> list[str]:
    doc = _load(DOCTRINE, {})
    return list(doc.get("always_allow_domains") or [
        "github.com", "api.github.com", "raw.githubusercontent.com", "github.io",
    ])


def is_github_host(host: str) -> bool:
    h = str(host or "").lower().strip(".")
    if not h:
        return False
    for dom in always_allow_domains():
        d = dom.lower().strip(".")
        if h == d or h.endswith("." + d):
            return True
    return h.endswith(".github.io") or h.endswith(".githubusercontent.com")


def is_github_domain(qname: str) -> bool:
    name = str(qname or "").lower().rstrip(".")
    if not name:
        return False
    return is_github_host(name)


def _hub_endpoints() -> list[dict[str, Any]]:
    eps: list[dict[str, Any]] = []
    seen: set[str] = set()
    hub = _load(INSTALL / "data" / "ammoos-pages-hub.json", {})
    for key, spec in (hub.get("repos") or {}).items():
        if not isinstance(spec, dict):
            continue
        for field, role in (("github", "stack_repo"), ("pages_url", "pages")):
            url = str(spec.get(field) or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            eps.append({
                "id": f"{key}_{role}".lower(),
                "url": url,
                "role": role,
                "legacy": key != "Hostess7",
                "title": spec.get("title") or key,
            })
    old = _load(INSTALL / "Hostess7/data/hostess7-old-projects.json", {})
    main = old.get("main_project") or {}
    for field in ("repo", "pages"):
        url = str(main.get(field) or "").strip()
        if url and url not in seen:
            seen.add(url)
            eps.append({"id": "hostess7_main", "url": url, "role": field, "legacy": False})
    for proj in old.get("old_projects") or []:
        if not isinstance(proj, dict):
            continue
        name = str(proj.get("name") or "legacy")
        for field in ("repo", "pages"):
            url = str(proj.get(field) or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            eps.append({
                "id": f"legacy_{name}".lower().replace(" ", "_"),
                "url": url,
                "role": field,
                "legacy": True,
                "title": name,
                "tag": proj.get("tag"),
            })
    return eps


def all_endpoints() -> list[dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    eps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in doc.get("canonical_endpoints") or []:
        url = str(row.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            eps.append({**row, "legacy": False})
    for row in _hub_endpoints():
        url = str(row.get("url") or "").strip()
        if url and url not in seen:
            seen.add(url)
            eps.append(row)
    return eps


def pages_fallback(repo_url: str) -> str | None:
    url = str(repo_url or "").strip().rstrip("/")
    if not url.startswith("https://github.com/"):
        return None
    parts = url.replace("https://github.com/", "").split("/")
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    return f"https://{owner.lower()}.github.io/{repo}/"


def _probe_once(url: str, *, method: str, timeout: float, ua: str) -> dict[str, Any]:
    ctx = ssl.create_default_context()
    started = time.monotonic()
    headers = {"User-Agent": ua}
    if method == "GET_RANGE":
        headers["Range"] = "bytes=0-0"
        method = "GET"
    try:
        req = urllib.request.Request(url, method=method, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            if method == "GET":
                try:
                    resp.read(512)
                except OSError:
                    pass
            elapsed_ms = int((time.monotonic() - started) * 1000)
            return {"ok": True, "status": resp.status, "elapsed_ms": elapsed_ms, "url": url, "method": method}
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        ok = exc.code < 500
        if exc.code == 403 and "api.github.com" in url:
            ok = True
        return {"ok": ok, "status": exc.code, "elapsed_ms": elapsed_ms, "url": url, "method": method}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)[:120], "url": url, "method": method}


def probe_url(url: str, *, timeout: float = 4.0, legacy_ua: bool = False) -> dict[str, Any]:
    ua = UA_LEGACY if legacy_ua else UA_MODERN
    for method in ("HEAD", "GET_RANGE", "GET"):
        hit = _probe_once(url, method=method, timeout=timeout, ua=ua)
        if hit.get("ok"):
            hit["probe_chain"] = method
            return hit
        if method == "GET":
            hit_legacy = _probe_once(url, method="GET", timeout=timeout, ua=UA_LEGACY)
            if hit_legacy.get("ok"):
                hit_legacy["probe_chain"] = "GET_legacy_ua"
                return hit_legacy
    return hit


def probe_all(*, write: bool = True, fast: bool = False) -> dict[str, Any]:
    if fast and CACHE.is_file():
        cached = _load(CACHE, {})
        if cached.get("schema"):
            cached["cached"] = True
            return cached

    eps = all_endpoints()
    canonical = [e for e in eps if not e.get("legacy")]
    legacy = [e for e in eps if e.get("legacy")]

    if fast:
        sample = canonical[:4] + legacy[: int((_load(DOCTRINE, {}).get("secure_legacy") or {}).get("fast_sample_legacy") or 5)]
        to_probe = sample
        full_total = len(eps)
    else:
        to_probe = eps
        full_total = len(eps)

    rows: list[dict[str, Any]] = []
    for ep in to_probe:
        url = str(ep.get("url") or "")
        if not url:
            continue
        hit = probe_url(url, timeout=2.8 if fast else 4.0, legacy_ua=bool(ep.get("legacy")))
        row = {**ep, **hit, "always_open": hit.get("ok")}
        if not hit.get("ok") and ep.get("role") in ("stack_repo", "repo") and "github.com" in url:
            fb = pages_fallback(url)
            if fb:
                fb_hit = probe_url(fb, timeout=2.5, legacy_ua=True)
                row["pages_fallback"] = fb
                row["pages_fallback_ok"] = fb_hit.get("ok")
                if fb_hit.get("ok"):
                    row["ok"] = True
                    row["always_open"] = True
                    row["via_pages_mirror"] = True
        rows.append(row)

    open_n = sum(1 for r in rows if r.get("ok"))
    canon_open = sum(1 for r in rows if r.get("ok") and not r.get("legacy"))
    legacy_open = sum(1 for r in rows if r.get("ok") and r.get("legacy"))
    legacy_total = len(legacy) if not fast else min(len(legacy), 5)

    doc = {
        "schema": "field-github-legacy-probe/v1",
        "updated": _utc(),
        "ok": open_n > 0,
        "stable": canon_open >= 2 and (legacy_open > 0 or open_n >= 3),
        "always_open": open_n >= max(2, len(rows) // 2),
        "open_count": open_n,
        "canonical_open": canon_open,
        "legacy_open": legacy_open,
        "legacy_total": legacy_total if fast else len(legacy),
        "total_probed": len(rows),
        "total_catalog": full_total,
        "fast": fast,
        "secure_legacy": (_load(DOCTRINE, {}).get("secure_legacy") or {}),
        "endpoints": rows,
        "always_allow_domains": always_allow_domains(),
    }
    if write:
        _save(CACHE, doc)
    return doc


def panel(*, write: bool = True, fast: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    live = probe_all(write=write, fast=fast)
    doc = {
        "ok": live.get("ok"),
        "schema": "field-github-legacy-panel/v1",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "updated": _utc(),
        "boss": "hostess7",
        "stable_connection": live.get("stable"),
        "github_always": live,
        "catalog_count": len(all_endpoints()),
        "always_allow_domains": always_allow_domains(),
        "api": "/api/field-github-legacy",
        "fast": fast,
    }
    if write:
        _save(PANEL, doc)
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(panel(write=False, fast=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("probe", "keepalive", "fast"):
        print(json.dumps(probe_all(fast=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "panel":
        print(json.dumps(panel(write=True, fast=False), ensure_ascii=False, indent=2))
        return 0
    if cmd == "allow" and len(sys.argv) > 2:
        print(json.dumps({"ok": is_github_domain(sys.argv[2])}, ensure_ascii=False))
        return 0
    print(json.dumps({"usage": "field-github-legacy.py [panel|json|probe|allow DOMAIN]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())