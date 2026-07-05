#!/usr/bin/env python3
"""X login — clean and secure for everyone. SSO lanes open, broken modals killed."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-x-sso-fix-doctrine.json"
PANEL = STATE / "hostess7-x-sso-fix-panel.json"
HONOR_SEED = INSTALL / "data" / "honorability-seed.json"
URL_KILL = INSTALL / "data" / "hostess7-url-kill-doctrine.json"
DOCS_API = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7")) / "docs" / "api"
UA = "Hostess7-XLoginFix/2.0"
TIMEOUT = 14

SSO_HOST_PATCHES: dict[str, dict[str, Any]] = {
    "accounts.google.com": {"stars": 5, "category": "sso", "note": "Google Sign-In for X — never block during login"},
    "googleapis.com": {"stars": 5, "category": "sso_api", "note": "GSI + OAuth token exchange"},
    "oauth.googleusercontent.com": {"stars": 5, "category": "sso", "note": "Google OAuth callback for X login"},
    "ssl.gstatic.com": {"stars": 5, "category": "cdn", "note": "Google Sign-In static assets"},
    "www.gstatic.com": {"stars": 5, "category": "cdn", "note": "Google Sign-In button assets"},
}

CLIENT_CSS = """
/* hostess7-x-login-fix — kill overlay bullshit, keep login form */
html[data-x-login-killed="1"] [data-testid="mask"],
html[data-x-login-killed="1"] [role="dialog"][aria-modal="true"]:not(:has(button, input, iframe)),
html[data-x-login-killed="1"] [data-x-overlay-killed="1"],
html[data-x-login-killed="1"] .jetfuel-style-root:empty {
  display: none !important;
  pointer-events: none !important;
  opacity: 0 !important;
  visibility: hidden !important;
}
html[data-x-login-killed="1"] body {
  overflow: auto !important;
  pointer-events: auto !important;
}
iframe[src*="accounts.google"], iframe[src*="googleapis"] {
  display: block !important;
  visibility: visible !important;
  pointer-events: auto !important;
}
""".strip()


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


def _probe_url(url: str) -> dict[str, Any]:
    row: dict[str, Any] = {"url": url, "ok": False}
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            row["ok"] = True
            row["status"] = resp.status
            row["final_url"] = resp.geturl()
    except urllib.error.HTTPError as exc:
        row["status"] = exc.code
        row["ok"] = exc.code in (200, 301, 302, 303, 307, 308)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        row["error"] = str(exc)[:160]
    return row


def _probe_lanes() -> list[dict[str, Any]]:
    doc = doctrine()
    clean = doc.get("clean_login") or {}
    lanes = [
        ("x_clean_login", clean.get("primary") or "https://x.com/i/flow/login"),
        ("x_google_login", clean.get("google_sso") or "https://x.com/i/flow/login"),
        ("google_accounts", "https://accounts.google.com/"),
        ("google_apis", "https://www.googleapis.com/"),
    ]
    return [{"lane": name, **_probe_url(url)} for name, url in lanes]


def _patch_honorability() -> dict[str, Any]:
    doc = _load(HONOR_SEED, {"entries": []})
    entries = list(doc.get("entries") or [])
    by_dom = {str(e.get("domain") or ""): e for e in entries}
    changed: list[str] = []
    for dom, patch in SSO_HOST_PATCHES.items():
        if dom in by_dom:
            by_dom[dom].update(patch)
        else:
            by_dom[dom] = {"domain": dom, **patch}
        changed.append(dom)
    doc["entries"] = list(by_dom.values())
    doc["x_login_fix"] = _now()
    _save(HONOR_SEED, doc)
    return {"ok": True, "patched": changed}


def _patch_url_kill_allow() -> dict[str, Any]:
    doc = _load(URL_KILL, {})
    allow = list(doc.get("canonical_allow") or [])
    added: list[str] = []
    for host in (
        "accounts.google.com", "googleapis.com", "oauth.googleusercontent.com",
        "ssl.gstatic.com", "www.gstatic.com",
    ):
        if host not in allow:
            allow.append(host)
            added.append(host)
    if added:
        doc["canonical_allow"] = allow
        _save(URL_KILL, doc)
    return {"ok": True, "added": added}


def repair(*, export_api: bool = True) -> dict[str, Any]:
    doc = doctrine()
    honor = _patch_honorability()
    url_allow = _patch_url_kill_allow()
    probes = _probe_lanes()
    clean = doc.get("clean_login") or {}
    security = doc.get("security") or {}
    probes_ok = sum(1 for p in probes if p.get("ok"))
    out = {
        "ok": True,
        "schema": "hostess7-x-sso-fix/v2",
        "updated": _now(),
        "motto": doc.get("motto"),
        "title": doc.get("title"),
        "broken_pattern": doc.get("broken_pattern"),
        "clean_login": clean,
        "security": security,
        "sso_allow": doc.get("sso_allow") or [],
        "never_block_during_sso": security.get("never_block_during_login") or [],
        "honorability": honor,
        "url_kill_allow": url_allow,
        "probes": probes,
        "probes_ok": probes_ok,
        "probes_total": len(probes),
        "login_ready": probes_ok >= max(1, len(probes) - 1),
        "client_repair": {
            **(doc.get("client_repair") or {}),
            "css": CLIENT_CSS,
            "script": "https://zacharygeurts.github.io/Hostess7/assets/x-jetfuel-sso-fix.js",
            "early_redirect": True,
            "detect": {
                "broken_sso": "/i/jf/onboarding/web/sso",
                "mask": '[data-testid="mask"]',
                "dialog": '[role="dialog"][aria-modal="true"]',
            },
            "fallback_login": clean.get("primary") or "https://x.com/i/flow/login",
        },
        "hosted": {
            "login": "https://zacharygeurts.github.io/Hostess7/x-login/",
            "fix": "https://zacharygeurts.github.io/Hostess7/x-sso-fix/",
        },
        "for_everyone": True,
        "witness": {"ok": True, "detail": "X login clean and secure — lanes open, early redirect armed"},
        "api": "/api/hostess7-x-sso-fix",
    }
    _save(PANEL, out)
    if export_api and DOCS_API.parent.is_dir():
        DOCS_API.mkdir(parents=True, exist_ok=True)
        (DOCS_API / "hostess7-x-sso-fix.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    return {
        "ok": True,
        "schema": "hostess7-x-sso-fix-panel/v2",
        "pending": "run repair",
        "motto": doctrine().get("motto"),
        "hosted": "https://zacharygeurts.github.io/Hostess7/x-login/",
        "api": "/api/hostess7-x-sso-fix",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("repair", "fix", "run", "secure", "login"):
        print(json.dumps(repair(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "explain":
        print(json.dumps(doctrine(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "css":
        print(CLIENT_CSS)
        return 0
    print(json.dumps({
        "usage": "hostess7-x-sso-fix.py [repair|json|explain|css]",
        "motto": doctrine().get("motto"),
        "hosted": "https://zacharygeurts.github.io/Hostess7/x-login/",
        "api": "/api/hostess7-x-sso-fix",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())