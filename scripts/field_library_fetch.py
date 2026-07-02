#!/usr/bin/env pythong
"""Fast library fetch — ≤3 MiB, ≥3 MiB/s (Hostess7 fast-connection policy)."""
from __future__ import annotations

import os
import ssl
import time
import urllib.error
import urllib.request
from typing import Any

from field_internet import USER_AGENT, _cache_key, internet_enabled  # noqa: E402
from field_paths import ROOT

INTERNET_CACHE = ROOT / "cache" / "fieldstorage" / "brain" / "internet" / "cache"

# Fast connections: only books ≤3 MiB (small = fast download on any link)
MAX_LIBRARY_BYTES = int(os.environ.get("HOSTESS7_LIBRARY_MAX_BYTES", str(3 * 1024 * 1024)))
# Optional throughput floor (0 = disabled). "3MB or faster" = file size cap, not MB/s.
MIN_LIBRARY_BPS = int(os.environ.get("HOSTESS7_LIBRARY_MIN_BPS", "0"))
LIBRARY_FETCH_TIMEOUT = int(os.environ.get("HOSTESS7_LIBRARY_TIMEOUT", "25"))


def _head_content_length(url: str) -> int | None:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=LIBRARY_FETCH_TIMEOUT, context=ssl.create_default_context()) as resp:
            cl = resp.headers.get("Content-Length")
            return int(cl) if cl and str(cl).isdigit() else None
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def fetch_library_fast(url: str, *, force: bool = False) -> dict[str, Any]:
    """Fetch only when fast: size ≤3 MiB and average speed ≥3 MiB/s."""
    rec: dict[str, Any] = {
        "url": url,
        "ok": False,
        "bytes": 0,
        "bps": 0.0,
        "text": "",
        "error": "",
        "fast_policy": {"max_bytes": MAX_LIBRARY_BYTES, "min_bps": MIN_LIBRARY_BPS},
    }
    if not internet_enabled():
        rec["error"] = "internet CLOSED"
        return rec

    cache_bin = INTERNET_CACHE / f"{_cache_key(url)}.bin"
    cache_meta = INTERNET_CACHE / f"{_cache_key(url)}.json"
    if not force and cache_bin.is_file():
        body = cache_bin.read_bytes()
        if len(body) <= MAX_LIBRARY_BYTES:
            rec.update({
                "ok": True,
                "bytes": len(body),
                "bps": float(MAX_LIBRARY_BYTES),
                "text": body.decode("utf-8", errors="replace"),
                "cached": True,
            })
            return rec
        rec["error"] = f"cached_too_large:{len(body)}>{MAX_LIBRARY_BYTES}"
        return rec

    cl = _head_content_length(url)
    if cl is not None and cl > MAX_LIBRARY_BYTES:
        rec["error"] = f"content_length_too_large:{cl}>{MAX_LIBRARY_BYTES}"
        return rec

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=LIBRARY_FETCH_TIMEOUT, context=ssl.create_default_context()) as resp:
            body = resp.read(MAX_LIBRARY_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        rec["error"] = str(exc)
        return rec

    elapsed = max(time.perf_counter() - t0, 0.001)
    bps = len(body) / elapsed
    rec["bytes"] = len(body)
    rec["bps"] = round(bps, 1)

    if len(body) > MAX_LIBRARY_BYTES:
        rec["error"] = f"download_too_large:{len(body)}>{MAX_LIBRARY_BYTES}"
        return rec
    if MIN_LIBRARY_BPS > 0 and bps < MIN_LIBRARY_BPS:
        rec["error"] = f"too_slow:{bps:.0f}bps<{MIN_LIBRARY_BPS}"
        return rec

    text = body.decode("utf-8", errors="replace")
    INTERNET_CACHE.mkdir(parents=True, exist_ok=True)
    cache_bin.write_bytes(body)
    cache_meta.write_text(
        __import__("json").dumps({
            "url": url,
            "bytes": len(body),
            "bps": rec["bps"],
            "fast_library": True,
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    rec.update({"ok": True, "text": text, "cached": False})
    return rec