#!/usr/bin/env pythong
"""Hostess7 internet — truth-filtered fetch, cache, connectivity (HOSTESS7_INTERNET=1)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from field_paths import ROOT

INTERNET_DIR = ROOT / "cache" / "fieldstorage" / "brain" / "internet"
FETCH_LOG = INTERNET_DIR / "fetch_log.jsonl"
CACHE_DIR = INTERNET_DIR / "cache"
STATUS_FILE = INTERNET_DIR / "status.json"

NOISE_RATIO = 0.94
TRUTH_RATIO = 0.06
MAX_BYTES = int(os.environ.get("HOSTESS7_FETCH_MAX_BYTES", str(2 * 1024 * 1024)))
TIMEOUT = int(os.environ.get("HOSTESS7_FETCH_TIMEOUT", "30"))
USER_AGENT = "Hostess7-SuperIntelligence/1.0 (+offline-first; truth-filtered)"

_BLOCKED_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0", "::1"})
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env_on(key: str, *, default: str = "") -> bool:
    return os.environ.get(key, default).strip().lower() in ("1", "true", "yes", "on")


def internet_enabled() -> bool:
    """Open when Hostess 7 wants the internet — explicit off wins; else mandate/autonomous defaults."""
    raw = os.environ.get("HOSTESS7_INTERNET", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    if _env_on("NEXUS_HOSTESS7_INTERNET", default="1"):
        return True
    if _env_on("HOSTESS7_ANGEL_MANDATE"):
        return True
    if _env_on("NEXUS_HOSTESS7_AUTONOMOUS"):
        return True
    return False


def _ensure_layout() -> None:
    INTERNET_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _url_allowed(url: str) -> tuple[bool, str]:
    try:
        parsed = urlparse(url)
    except ValueError as exc:
        return False, str(exc)
    if parsed.scheme not in ("http", "https"):
        return False, f"scheme not allowed: {parsed.scheme}"
    host = (parsed.hostname or "").lower()
    if not host:
        return False, "missing host"
    if host in _BLOCKED_HOSTS or host.endswith(".local"):
        return False, f"host blocked: {host}"
    return True, host


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def html_to_text(raw: str) -> str:
    text = unescape(_TAG_RE.sub(" ", raw))
    return _WS_RE.sub(" ", text).strip()


def truth_score_text(text: str) -> float:
    """Rough signal score — longer substantive text scores higher."""
    if not text:
        return TRUTH_RATIO * 100
    words = [w for w in re.split(r"\W+", text) if len(w) > 2]
    unique = len(set(words))
    score = TRUTH_RATIO * 100 + min(40, unique / 50) + min(30, len(text) / 2000)
    return min(100.0, round(score, 1))


def fetch_url(url: str, *, force: bool = False) -> dict[str, Any]:
    """Fetch URL — cached losslessly under brain/internet/cache/."""
    _ensure_layout()
    record: dict[str, Any] = {
        "ts": _ts(),
        "url": url,
        "ok": False,
        "cached": False,
        "bytes": 0,
        "content_type": "",
        "truth_score": 0.0,
        "text_preview": "",
        "error": "",
    }
    if not internet_enabled():
        record["error"] = "internet gate CLOSED — run ./Hostess7.sh on or HOSTESS7_INTERNET=1"
        _log_fetch(record)
        return record

    ok, detail = _url_allowed(url)
    if not ok:
        record["error"] = detail
        _log_fetch(record)
        return record

    key = _cache_key(url)
    cache_path = CACHE_DIR / f"{key}.bin"
    meta_path = CACHE_DIR / f"{key}.json"

    if not force and meta_path.is_file() and cache_path.is_file():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            body = cache_path.read_bytes()
            text = html_to_text(body.decode("utf-8", errors="replace")) if "html" in meta.get("content_type", "") else body.decode("utf-8", errors="replace")
            record.update({
                "ok": True,
                "cached": True,
                "bytes": len(body),
                "content_type": meta.get("content_type", ""),
                "truth_score": truth_score_text(text),
                "text_preview": text[:1200],
            })
            _log_fetch(record)
            return record
        except (OSError, json.JSONDecodeError):
            pass

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                body = body[:MAX_BYTES]
                record["truncated"] = True
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        record["error"] = str(exc)
        _log_fetch(record)
        return record

    text = html_to_text(body.decode("utf-8", errors="replace")) if "html" in content_type.lower() else body.decode("utf-8", errors="replace")
    meta = {"url": url, "fetched": _ts(), "content_type": content_type, "bytes": len(body)}
    cache_path.write_bytes(body)
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    record.update({
        "ok": True,
        "bytes": len(body),
        "content_type": content_type,
        "truth_score": truth_score_text(text),
        "text_preview": text[:1200],
    })
    _log_fetch(record)
    return record


def _log_fetch(record: dict[str, Any]) -> None:
    _ensure_layout()
    with FETCH_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({k: record[k] for k in record if k != "text_preview" or record.get("ok")}) + "\n")


def probe_connectivity() -> dict[str, Any]:
    """Lightweight connectivity probe."""
    probes = (
        "https://example.com/",
        "https://raw.githubusercontent.com/Alexir/CMUdict/master/cmudict-0.7b",
    )
    results: list[dict[str, Any]] = []
    for url in probes:
        if not internet_enabled():
            results.append({"url": url, "ok": False, "error": "internet disabled"})
            continue
        ok, _ = _url_allowed(url)
        if not ok:
            results.append({"url": url, "ok": False, "error": "blocked"})
            continue
        try:
            req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=10, context=ssl.create_default_context()) as resp:
                results.append({"url": url, "ok": True, "status": resp.status})
        except Exception:
            try:
                r = fetch_url(url, force=False)
                results.append({"url": url, "ok": r.get("ok", False), "cached": r.get("cached")})
            except Exception as exc:
                results.append({"url": url, "ok": False, "error": str(exc)})
    online = any(r.get("ok") for r in results)
    return {"updated": _ts(), "enabled": internet_enabled(), "online": online, "probes": results}


def save_status() -> Path:
    _ensure_layout()
    snap = probe_connectivity()
    snap["fetch_log"] = str(FETCH_LOG)
    snap["cache_dir"] = str(CACHE_DIR)
    snap["noise_ratio"] = NOISE_RATIO
    snap["truth_ratio"] = TRUTH_RATIO
    STATUS_FILE.write_text(json.dumps(snap, indent=2) + "\n", encoding="utf-8")
    return STATUS_FILE


def format_internet_report() -> str:
    snap = probe_connectivity()
    lines = [
        "=== Hostess 7 — Internet (truth-filtered) ===",
        f"Gate: {'OPEN' if snap.get('enabled') else 'CLOSED'} · online={'yes' if snap.get('online') else 'no'}",
        f"Philosophy: {int(NOISE_RATIO * 100)}% noise / {int(TRUTH_RATIO * 100)}% truth — cache then corroborate",
        "",
        "Probes:",
    ]
    for p in snap.get("probes") or []:
        status = "OK" if p.get("ok") else f"FAIL {p.get('error', '')}"
        lines.append(f"  • {p.get('url')}: {status}")
    lines.append("")
    if snap.get("enabled"):
        lines.append("Fetch: `./Hostess7.sh fetch <url>` · talk: `/fetch <url>`")
    else:
        lines.append("Enable: `./Hostess7.sh on` (starts 7 agents + internet)")
    return "\n".join(lines)


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s<>\"']+", text)


def internet_cmd(mode: str | None = None, arg: str | None = None) -> int:
    if mode in ("fetch", "get") and arg:
        rec = fetch_url(arg.strip())
        if rec.get("ok"):
            print(f"FETCH OK — {rec['bytes']} bytes · truth={rec['truth_score']}% · cached={rec.get('cached')}")
            if rec.get("text_preview"):
                print(rec["text_preview"][:2000])
            print(f"METRIC internet_truth={rec['truth_score']}")
            print("OK internet-fetch")
            return 0
        print(f"FETCH FAIL: {rec.get('error')}", file=sys.stderr)
        return 1
    save_status()
    print(format_internet_report())
    print(f"METRIC internet_enabled={1 if internet_enabled() else 0}")
    print(f"METRIC internet_online={1 if probe_connectivity().get('online') else 0}")
    print("OK internet")
    return 0


def main() -> int:
    if len(sys.argv) < 2:
        return internet_cmd()
    cmd = sys.argv[1]
    if cmd == "fetch" and len(sys.argv) >= 3:
        return internet_cmd("fetch", " ".join(sys.argv[2:]))
    if cmd == "status":
        return internet_cmd()
    return internet_cmd(cmd, sys.argv[2] if len(sys.argv) > 2 else None)


if __name__ == "__main__":
    raise SystemExit(main())