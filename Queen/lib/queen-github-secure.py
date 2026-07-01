#!/usr/bin/env pythong
"""Queen Browser — pinned GitHub connect (DNS + SSH keys, anti-MITM/redirect)."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

QUEEN = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(QUEEN.parent)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
CACHE = STATE / "queen-github-secure-cache.json"
OWNER = os.environ.get("HOSTESS7_GITHUB_OWNER", "ZacharyGeurts").lower()
CACHE_TTL = int(os.environ.get("QUEEN_GITHUB_SECURE_CACHE_SEC", "120"))

_GITHUB_HOSTS = frozenset({
    "github.com",
    "api.github.com",
    "gist.github.com",
    "ssh.github.com",
    "raw.githubusercontent.com",
    "codeload.github.com",
})


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _secure_git_mod() -> Any | None:
    for script in (
        INSTALL / "Hostess7" / "scripts" / "hostess7_secure_git.py",
        QUEEN.parent / "Hostess7" / "scripts" / "hostess7_secure_git.py",
    ):
        if not script.is_file():
            continue
        spec = importlib.util.spec_from_file_location("hostess7_secure_git", script)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def is_github_host(host: str) -> bool:
    h = (host or "").lower().strip(".")
    if not h:
        return False
    if h in _GITHUB_HOSTS:
        return True
    return h.endswith(".github.io") or h.endswith(".githubusercontent.com")


def is_github_url(url: str) -> bool:
    try:
        return is_github_host(urlparse(url).hostname or "")
    except Exception:
        return False


def _owner_path(url: str) -> bool:
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()
        if host == f"{OWNER}.github.io":
            return True
        if "github.com" in host and path.startswith(f"/{OWNER}/"):
            return True
        if host == "gist.github.com" and f"/{OWNER}/" in path:
            return True
    except Exception:
        pass
    return False


def _read_cache() -> dict[str, Any] | None:
    if not CACHE.is_file():
        return None
    try:
        doc = json.loads(CACHE.read_text(encoding="utf-8"))
        ts = float(doc.get("cached_at") or 0)
        if time.time() - ts > CACHE_TTL:
            return None
        return doc.get("verify")
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _write_cache(verify: dict[str, Any]) -> None:
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps({"cached_at": time.time(), "verify": verify}, indent=2) + "\n",
        encoding="utf-8",
    )
    CACHE.chmod(0o600)


def verify_connect(*, refresh: bool = False) -> dict[str, Any]:
    if not refresh:
        cached = _read_cache()
        if cached is not None:
            return {**cached, "cached": True}
    mod = _secure_git_mod()
    if mod is None:
        return {"ok": False, "error": "hostess7_secure_git missing"}
    doc = mod.verify()
    _write_cache(doc)
    return doc


def classify_github_url(url: str, *, allow_external: bool | None = None) -> dict[str, Any] | None:
    """Return classification overlay for GitHub hosts, or None if not GitHub."""
    u = (url or "").strip()
    if not is_github_url(u):
        return None
    host = (urlparse(u).hostname or "").lower()
    owner_ok = _owner_path(u)
    ext = allow_external
    if ext is None:
        ext = os.environ.get("QUEEN_ALLOW_EXTERNAL_URLS", "") in ("1", "true", "yes")
    v = verify_connect()
    base = {
        "url": u,
        "host": host,
        "github": True,
        "owner_repo": owner_ok,
        "secure_connect": {
            "ok": v.get("ok"),
            "route": v.get("route"),
            "dns_pin": (v.get("dns_pin") or {}).get("ok"),
            "ssh_key_match": (v.get("ssh_key_match") or {}).get("ok"),
            "anti_hook": (v.get("anti_hook") or {}).get("git_config", {}).get("ok"),
            "cached": v.get("cached"),
        },
    }
    if not v.get("ok"):
        return {
            **base,
            "verdict": "BLOCK_MITM",
            "iff": "HOSTILE",
            "internal": False,
            "presume_hostile": True,
            "reason": "github_secure_connect_failed — DNS/SSH pin or anti-hook audit",
            "hint": f"https://{OWNER}.github.io/Hostess7/",
        }
    if owner_ok:
        return {
            **base,
            "verdict": "ALLOW_SECURE_GITHUB",
            "iff": "KNOWN_OWNER",
            "internal": False,
            "presume_hostile": True,
            "github_pinned": True,
            "layer": "secure_github",
        }
    if ext:
        return {
            **base,
            "verdict": "ALLOW_PINNED_GITHUB",
            "iff": "PINNED_DNS",
            "internal": False,
            "presume_hostile": True,
            "github_pinned": True,
            "layer": "secure_github",
        }
    return {
        **base,
        "verdict": "BLOCK_EXTERNAL",
        "iff": "HOSTILE",
        "internal": False,
        "presume_hostile": True,
        "reason": "queen_internal_only — non-owner GitHub blocked",
        "hint": f"https://{OWNER}.github.io/Hostess7/",
    }


def panel_json() -> dict[str, Any]:
    v = verify_connect()
    mod = _secure_git_mod()
    doctrine = str(getattr(mod, "DOCTRINE", "")) if mod else ""
    return {
        "schema": "queen-github-secure/v1",
        "updated": _now(),
        "owner": OWNER,
        "verify": v,
        "doctrine": doctrine,
        "policy": "Pinned GitHub DNS + SSH keys — no MITM, redirect, or credential hooks",
        "browser": "Queen",
        "legacy_engine_label": "legacy_gecko",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(panel_json(), indent=2))
        return 0 if panel_json().get("verify", {}).get("ok") else 1
    if cmd == "verify":
        refresh = "--refresh" in sys.argv
        doc = verify_connect(refresh=refresh)
        print(json.dumps(doc, indent=2))
        return 0 if doc.get("ok") else 1
    if cmd == "classify" and len(sys.argv) > 2:
        doc = classify_github_url(sys.argv[2]) or {"verdict": "NOT_GITHUB"}
        print(json.dumps(doc, indent=2))
        return 0
    print(json.dumps({"error": "usage: queen-github-secure.py [json|verify|classify URL]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())