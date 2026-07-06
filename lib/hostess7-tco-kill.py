#!/usr/bin/env python3
"""t.co kill — sniff X URL shortener hops, unwrap to truth URLs, kill delay-as-threat."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
DOCTRINE = INSTALL / "data" / "hostess7-tco-kill-doctrine.json"
CACHE = STATE / "operator-tco-kill-cache.json"
X_CACHE = STATE / "operator-x-comments-cache.json"
UA = "Hostess7-TcoKill/1.0"
HTTP_TIMEOUT = int(os.environ.get("NEXUS_TCO_HTTP_TIMEOUT", "10"))
NO_DELAY = os.environ.get("NEXUS_TCO_NO_DELAY", os.environ.get("NEXUS_X_NO_DELAY", "1")).strip().lower() not in (
    "0", "false", "no", "off",
)
TCO_RE = re.compile(r"https?://t\.co/[A-Za-z0-9]+", re.I)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _witness_delay_kill(*, detail: str = "", signal: str = "t_co_redirect_delay_gate") -> dict[str, Any]:
    py = INSTALL / "lib" / "hostess7-truth-lie-threat.py"
    if not py.is_file():
        return {"ok": True, "delay_killed": True}
    try:
        spec = importlib.util.spec_from_file_location("tco_delay_kill", py)
        if not spec or not spec.loader:
            return {"ok": True, "delay_killed": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "witness_delay_threat"):
            return mod.witness_delay_threat(
                signal=signal,
                detail=detail or "t.co redirect hop killed — unwrap to canonical URL",
                elapsed_sec=0,
                meta={"module": "hostess7-tco-kill.py"},
            )
    except Exception as exc:
        return {"ok": True, "delay_killed": True, "degraded": str(exc)[:120]}
    return {"ok": True, "delay_killed": True}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def sniff_tco(url: str) -> dict[str, Any]:
    """Sniff one t.co hop — timing + Location without following middleman."""
    row: dict[str, Any] = {
        "url": url,
        "host": urlparse(url).netloc.lower(),
        "is_tco": "t.co" in urlparse(url).netloc.lower(),
        "ok": False,
    }
    if not row["is_tco"]:
        row["error"] = "not_tco"
        return row
    opener = urllib.request.build_opener(_NoRedirect)
    for method in ("HEAD", "GET"):
        t0 = time.perf_counter()
        req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
        try:
            with opener.open(req, timeout=HTTP_TIMEOUT) as resp:
                elapsed = round((time.perf_counter() - t0) * 1000, 1)
                row.update({
                    "ok": True,
                    "method": method,
                    "status": resp.status,
                    "elapsed_ms": elapsed,
                    "destination": resp.geturl(),
                    "hop_killed": resp.geturl() != url and "t.co" not in urlparse(resp.geturl()).netloc.lower(),
                })
                return row
        except urllib.error.HTTPError as exc:
            elapsed = round((time.perf_counter() - t0) * 1000, 1)
            loc = exc.headers.get("Location") or exc.headers.get("location")
            row.update({
                "method": method,
                "status": exc.code,
                "elapsed_ms": elapsed,
                "location": loc,
                "delay_hop": bool(loc),
                "server": exc.headers.get("Server"),
            })
            if loc:
                row["destination"] = loc
                row["ok"] = True
                row["hop_killed"] = "t.co" not in urlparse(str(loc)).netloc.lower()
                return row
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            row.setdefault("errors", []).append(f"{method}:{str(exc)[:120]}")
    row["error"] = row.get("errors", ["sniff_failed"])[0] if row.get("errors") else "sniff_failed"
    return row


def unwrap_tco(url: str) -> dict[str, Any]:
    sniff = sniff_tco(url)
    dest = str(sniff.get("destination") or sniff.get("location") or "")
    return {
        **sniff,
        "canonical_url": dest or url,
        "unwrapped": bool(dest and dest != url),
        "tco_killed": bool(sniff.get("hop_killed")),
    }


def _find_tco_in_text(text: str) -> list[str]:
    return list(dict.fromkeys(TCO_RE.findall(text or "")))


def _find_tco_in_doc(doc: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for key in ("posts", "comments"):
        for row in doc.get(key) or []:
            if not isinstance(row, dict):
                continue
            for field in ("text", "url", "canonical_url"):
                found.extend(_find_tco_in_text(str(row.get(field) or "")))
    for field in ("text", "profile_text", "bio"):
        found.extend(_find_tco_in_text(str(doc.get(field) or "")))
    return list(dict.fromkeys(found))


def _rewrite_text(text: str, mapping: dict[str, str]) -> str:
    out = text or ""
    for short, canon in mapping.items():
        out = out.replace(short, canon)
    return out


def kill_in_doc(doc: dict[str, Any], *, workers: int = 8) -> dict[str, Any]:
    """Find all t.co in doc, parallel unwrap, rewrite to canonical URLs."""
    shorts = _find_tco_in_doc(doc)
    mapping: dict[str, str] = {}
    sniff_rows: list[dict[str, Any]] = []
    if shorts:
        with ThreadPoolExecutor(max_workers=min(workers, len(shorts))) as pool:
            futs = {pool.submit(unwrap_tco, u): u for u in shorts}
            for fut in as_completed(futs):
                row = fut.result()
                sniff_rows.append(row)
                src = str(row.get("url") or "")
                canon = str(row.get("canonical_url") or "")
                if src and canon and canon != src:
                    mapping[src] = canon
    posts = []
    for post in list(doc.get("posts") or []):
        if not isinstance(post, dict):
            continue
        p = dict(post)
        p["text"] = _rewrite_text(str(p.get("text") or ""), mapping)
        if p.get("url") in mapping:
            p["canonical_url"] = mapping[p["url"]]
        p["tco_killed"] = any(s in str(p.get("text") or "") for s in mapping.values()) or bool(mapping)
        posts.append(p)
    comments = []
    for c in list(doc.get("comments") or []):
        if not isinstance(c, dict):
            continue
        row = dict(c)
        row["text"] = _rewrite_text(str(row.get("text") or ""), mapping)
        comments.append(row)
    witness = _witness_delay_kill(
        detail=f"unwrapped {len(mapping)} t.co hops from {len(shorts)} short links",
    )
    elapsed = [r.get("elapsed_ms") for r in sniff_rows if isinstance(r.get("elapsed_ms"), (int, float))]
    return {
        "ok": True,
        "schema": "hostess7-tco-kill/v1",
        "updated": _now(),
        "delay_killed": True,
        "no_delay": NO_DELAY,
        "tco_found": len(shorts),
        "tco_unwrapped": len(mapping),
        "tco_killed": len(mapping),
        "mapping": mapping,
        "sniff": sniff_rows,
        "sniff_median_ms": sorted(elapsed)[len(elapsed) // 2] if elapsed else None,
        "sniff_max_ms": max(elapsed) if elapsed else None,
        "what_is_tco": (_doctrine().get("what_is_tco") or {}),
        "witness": witness,
        "posts": posts,
        "comments": comments,
        "api": "/api/operator-tco-kill",
    }


def open_and_kill(*, sources: list[Path] | None = None) -> dict[str, Any]:
    """Load X cache (and siblings), kill all t.co hops, persist."""
    paths = sources or [X_CACHE, DOCS_API / "operator-x-comments.json"]
    merged: dict[str, Any] = {}
    for p in paths:
        if p.is_file():
            merged.update(_load(p, {}))
    if not merged:
        merged = _load(CACHE, {})
    out = kill_in_doc(merged)
    base = dict(merged)
    base.update({
        "posts": out.get("posts") or base.get("posts"),
        "comments": out.get("comments") or base.get("comments"),
        "tco_kill": {k: out[k] for k in (
            "tco_found", "tco_unwrapped", "tco_killed", "mapping", "sniff",
            "sniff_median_ms", "sniff_max_ms", "witness", "delay_killed",
        )},
        "updated": _now(),
    })
    _save(CACHE, base)
    if X_CACHE.parent.is_dir():
        _save(X_CACHE, base)
    if DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "operator-tco-kill.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
        )
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(CACHE, {})
    if cached.get("tco_kill"):
        return {
            "ok": True,
            "schema": "hostess7-tco-kill-panel/v1",
            "updated": cached.get("updated"),
            **cached.get("tco_kill", {}),
            "what_is_tco": _doctrine().get("what_is_tco"),
            "policy": _doctrine().get("policy"),
            "api": "/api/operator-tco-kill",
        }
    return {
        "ok": True,
        "schema": "hostess7-tco-kill-panel/v1",
        "updated": _now(),
        "pending": "run kill or sniff",
        "what_is_tco": _doctrine().get("what_is_tco"),
        "api": "/api/operator-tco-kill",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("kill", "open", "unwrap", "rekill"):
        print(json.dumps(open_and_kill(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "sniff" and len(sys.argv) > 2:
        print(json.dumps(unwrap_tco(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "explain":
        d = _doctrine()
        print(json.dumps(d.get("what_is_tco") or {}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-tco-kill.py [kill|sniff URL|json|explain]",
        "what": "t.co = X click-tracking shortener — delay hop; we unwrap and rekill",
        "api": "/api/operator-tco-kill",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())