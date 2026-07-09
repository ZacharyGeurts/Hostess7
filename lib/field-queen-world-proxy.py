#!/usr/bin/env python3
"""Proxy Queen Browser :9481 APIs through AmmoOS :9477 — Queen Room, SAP, NES library."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


def queen_port() -> int:
    try:
        return int(os.environ.get("QUEEN_WORLD_PORT", os.environ.get("NEXUS_QUEEN_PORT", "9481")))
    except ValueError:
        return 9481


def queen_base() -> str:
    host = os.environ.get("QUEEN_WORLD_HOST", "127.0.0.1").strip() or "127.0.0.1"
    return f"http://{host}:{queen_port()}"


def proxy_request(
    method: str,
    path: str,
    *,
    query: str = "",
    body: bytes | None = None,
    content_type: str = "application/json",
    timeout: float = 120.0,
) -> tuple[int, bytes, str]:
    """Returns (status_code, body_bytes, content_type)."""
    base = queen_base()
    url = base + path
    if query:
        url += ("&" if "?" in url else "?") + query.lstrip("?")
    headers = {"Accept": "*/*", "User-Agent": "AmmoOS-Queen-Proxy/1.0", "X-Queen-Proxy": "1"}
    if body is not None:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "application/octet-stream")
            return int(resp.status), raw, ctype
    except urllib.error.HTTPError as exc:
        raw = exc.read() if exc.fp else b""
        ctype = exc.headers.get("Content-Type", "application/json") if exc.headers else "text/plain"
        return int(exc.code), raw or json.dumps({"ok": False, "error": "queen_proxy_http", "code": exc.code}).encode(), ctype
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        doc = {
            "ok": False,
            "error": "queen_browser_unreachable",
            "hint": "Boot Queen Browser — ./nexus.sh or Queen Browser on :9481",
            "queen_base": base,
            "detail": str(exc)[:200],
        }
        return 503, json.dumps(doc, ensure_ascii=False).encode(), "application/json"


def proxy_json_post(path: str, body: dict[str, Any], *, timeout: float = 120.0) -> dict[str, Any]:
    code, raw, _ = proxy_request(
        "POST",
        path,
        body=json.dumps(body, ensure_ascii=False).encode(),
        content_type="application/json",
        timeout=timeout,
    )
    try:
        doc = json.loads(raw.decode("utf-8", errors="replace"))
        doc.setdefault("proxy_status", code)
        return doc
    except json.JSONDecodeError:
        return {"ok": False, "error": "queen_proxy_bad_json", "proxy_status": code, "raw": raw[:300].decode(errors="replace")}


def proxy_get_json(path: str, *, query: str = "", timeout: float = 30.0) -> dict[str, Any]:
    code, raw, _ = proxy_request("GET", path, query=query, timeout=timeout)
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {"ok": False, "error": "queen_proxy_bad_json", "proxy_status": code}


def is_queen_api_path(path: str) -> bool:
    p = path.split("?", 1)[0].rstrip("/")
    return p in (
        "/api/game-room",
        "/api/sap",
        "/api/nes-library",
    ) or p.startswith("/api/game-room/")


def main() -> int:
    import sys

    if len(sys.argv) < 2:
        print(json.dumps({"usage": "field-queen-world-proxy.py [status|ping]"}, indent=2))
        return 2
    cmd = sys.argv[1].strip().lower()
    if cmd == "ping":
        code, _, _ = proxy_request("GET", "/api/sap", query="", timeout=3.0)
        print(json.dumps({"ok": 200 <= code < 400, "queen_base": queen_base(), "code": code}, indent=2))
        return 0 if 200 <= code < 400 else 1
    if cmd == "status":
        st = proxy_get_json("/api/game-room", timeout=5.0)
        sap = proxy_get_json("/api/sap", timeout=5.0)
        print(json.dumps({"ok": True, "queen_base": queen_base(), "game_room": st, "sap": sap}, indent=2))
        return 0
    print(json.dumps({"error": "unknown", "cmds": ["ping", "status"]}, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())