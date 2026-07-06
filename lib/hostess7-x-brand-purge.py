#!/usr/bin/env python3
"""X brand purge — blow dangerous Twitter legacy; Producer is X brand not Twitter."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-x-brand-purge-doctrine.json"
PANEL = STATE / "hostess7-x-brand-purge-panel.json"
BROADCASTER = INSTALL / "data" / "field-broadcaster-platforms.json"
HONOR_SEED = INSTALL / "data" / "honorability-seed.json"
X_CACHE = STATE / "operator-x-comments-cache.json"
TCO_CACHE = STATE / "operator-tco-kill-cache.json"

TWITTER_URL_RE = re.compile(r"https?://(?:www\.)?twitter\.com", re.I)
TWITTER_HOST_RE = re.compile(r"\btwitter\.com\b", re.I)


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


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _witness_purge(*, detail: str) -> dict[str, Any]:
    py = INSTALL / "lib" / "hostess7-truth-lie-threat.py"
    if not py.is_file():
        return {"ok": True}
    try:
        spec = importlib.util.spec_from_file_location("x_brand_witness", py)
        if not spec or not spec.loader:
            return {"ok": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "witness_delay_threat"):
            return mod.witness_delay_threat(
                signal="twitter_legacy_purge",
                detail=detail,
                elapsed_sec=0,
                meta={"module": "hostess7-x-brand-purge.py"},
            )
    except Exception:
        pass
    return {"ok": True}


def _rewrite_urls_in_obj(obj: Any) -> tuple[Any, int]:
    count = 0
    if isinstance(obj, str):
        new = TWITTER_URL_RE.sub("https://x.com", obj)
        new = TWITTER_HOST_RE.sub("x.com", new)
        if new != obj:
            count += 1
        return new, count
    if isinstance(obj, list):
        out: list[Any] = []
        for item in obj:
            fixed, n = _rewrite_urls_in_obj(item)
            count += n
            out.append(fixed)
        return out, count
    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            fixed, n = _rewrite_urls_in_obj(v)
            count += n
            out[k] = fixed
        return out, count
    return obj, 0


def _ensure_x_producer_platform(doc: dict[str, Any]) -> dict[str, Any]:
    brand = (doctrine().get("brand") or {})
    platforms = list(doc.get("platforms") or [])
    x_entry = {
        "id": "x",
        "label": "X Live",
        "brand": brand.get("producer_label") or "X Producer",
        "color": "#000000",
        "rtmp_url": "rtmps://live-api-s.twitter.com:443/live",
        "rtmp_url_note": "Legacy ingest hostname — canonical brand is X Producer (not Twitter)",
        "stream_key_hint": "X Producer → Go Live → Streaming software setup",
        "recommended": {"video": "h264", "audio": "aac", "container": "flv", "bitrate_kbps": 4500, "keyframe_sec": 2},
        "legacy_purged": brand.get("forbidden_labels") or [],
        "musk_doctrine": doctrine().get("attribution"),
        "canonical_brand": "X",
    }
    replaced = False
    for i, p in enumerate(platforms):
        if str(p.get("id") or "").lower() in ("x", "twitter", "x-live"):
            platforms[i] = {**p, **x_entry}
            replaced = True
            break
    if not replaced:
        platforms.insert(0, x_entry)
    doc["platforms"] = platforms
    doc["x_producer_default"] = True
    doc["twitter_legacy_removed"] = True
    doc["updated"] = _now()
    return doc


def _patch_honorability_seed() -> dict[str, Any]:
    doc = _load(HONOR_SEED, {"entries": []})
    entries = list(doc.get("entries") or [])
    by_dom = {str(e.get("domain") or ""): e for e in entries}
    patches = {
        "twitter.com": {"stars": 4, "category": "legacy_redirect", "note": "Legacy redirect only — canonical X brand is x.com"},
        "ads-twitter.com": {"stars": 1, "category": "dangerous_legacy", "note": "Blow — Twitter ad path; block egress"},
        "t.co": {"stars": 2, "category": "delay_shortener", "note": "Blow hop — unwrap via tco-kill"},
        "syndication.twimg.com": {"stars": 2, "category": "useless_legacy", "note": "Broken/empty syndication — drop lane"},
        "periscope.tv": {"stars": 1, "category": "dead_brand", "note": "Periscope purged — X brand only"},
        "vine.co": {"stars": 1, "category": "dead_brand", "note": "Vine purged"},
        "api.twitter.com": {"stars": 3, "category": "legacy_api", "note": "Use api.x.com — legacy hostname"},
    }
    changed: list[str] = []
    for dom, patch in patches.items():
        if dom in by_dom:
            by_dom[dom].update(patch)
        else:
            by_dom[dom] = {"domain": dom, **patch}
        changed.append(dom)
    doc["entries"] = list(by_dom.values())
    doc["x_brand_purge"] = _now()
    _save(HONOR_SEED, doc)
    return {"ok": True, "patched": changed}


def _run_tco_kill() -> dict[str, Any]:
    py = INSTALL / "lib" / "hostess7-tco-kill.py"
    if not py.is_file():
        return {"ok": True, "skipped": "tco_kill_missing"}
    try:
        spec = importlib.util.spec_from_file_location("tco_kill_purge", py)
        if not spec or not spec.loader:
            return {"ok": True, "skipped": "load"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "open_and_kill"):
            return mod.open_and_kill()
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160]}
    return {"ok": True, "skipped": "open_and_kill"}


def purge(*, write_broadcaster: bool = True, rewrite_caches: bool = True) -> dict[str, Any]:
    doc = doctrine()
    blown = list(doc.get("dangerous_blow") or [])
    useless = list(doc.get("useless_twitter_shit") or [])
    honor = _patch_honorability_seed()
    broadcaster_out: dict[str, Any] = {"ok": False, "skipped": True}
    if write_broadcaster and BROADCASTER.is_file():
        bdoc = _ensure_x_producer_platform(_load(BROADCASTER, {}))
        _save(BROADCASTER, bdoc)
        broadcaster_out = {
            "ok": True,
            "x_producer": next((p for p in bdoc.get("platforms") or [] if p.get("id") == "x"), {}),
        }
    rewrites = 0
    cache_paths = [X_CACHE, TCO_CACHE, STATE / "operator-censorship-exposure.json"]
    for path in cache_paths:
        if not rewrite_caches or not path.is_file():
            continue
        cached = _load(path, {})
        fixed, n = _rewrite_urls_in_obj(cached)
        if n:
            rewrites += n
            _save(path, fixed if isinstance(fixed, dict) else {"data": fixed})
    tco = _run_tco_kill()
    witness = _witness_purge(
        detail=f"blew {len(blown)} dangerous hosts; X Producer brand; {rewrites} twitter→x rewrites",
    )
    out = {
        "ok": True,
        "schema": "hostess7-x-brand-purge/v1",
        "updated": _now(),
        "attribution": doc.get("attribution"),
        "brand": doc.get("brand"),
        "dangerous_blown": blown,
        "useless_twitter_shit": useless,
        "honorability": honor,
        "broadcaster": broadcaster_out,
        "twitter_urls_rewritten": rewrites,
        "tco_kill": {"tco_found": tco.get("tco_found"), "tco_unwrapped": tco.get("tco_unwrapped")},
        "witness": witness,
        "producer": {
            "label": (doc.get("brand") or {}).get("producer_label") or "X Producer",
            "not": "Twitter Producer",
            "platform_id": "x",
        },
        "api": "/api/hostess7-x-brand-purge",
    }
    _save(PANEL, out)
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    return {
        "ok": True,
        "schema": "hostess7-x-brand-purge-panel/v1",
        "pending": "run purge",
        "brand": doctrine().get("brand"),
        "api": "/api/hostess7-x-brand-purge",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("purge", "blow", "run", "kill-twitter-shit"):
        print(json.dumps(purge(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "explain":
        print(json.dumps(doctrine(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-x-brand-purge.py [purge|json|explain]",
        "motto": doctrine().get("motto"),
        "api": "/api/hostess7-x-brand-purge",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())