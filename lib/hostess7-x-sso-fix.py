#!/usr/bin/env python3
"""X Jetfuel SSO fix — dismiss stuck empty modal divs; keep Google SSO lanes open."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "hostess7-x-sso-fix-doctrine.json"
PANEL = STATE / "hostess7-x-sso-fix-panel.json"
HONOR_SEED = INSTALL / "data" / "honorability-seed.json"
DOCS_API = INSTALL / "Hostess7" / "docs" / "api"

SSO_HOST_PATCHES: dict[str, dict[str, Any]] = {
    "accounts.google.com": {
        "stars": 5,
        "category": "sso",
        "note": "Google Sign-In for X Jetfuel SSO — never block during login",
    },
    "googleapis.com": {
        "stars": 5,
        "category": "sso_api",
        "note": "GSI client + OAuth token exchange for X SSO",
    },
    "ssl.gstatic.com": {
        "stars": 5,
        "category": "cdn",
        "note": "Google Sign-In static assets",
    },
    "www.gstatic.com": {
        "stars": 5,
        "category": "cdn",
        "note": "Google Sign-In button assets",
    },
}

CLIENT_CSS = """
/* hostess7-x-sso-fix — stuck X Jetfuel empty modal */
html[data-x-sso-repaired="1"] [data-testid="mask"],
html[data-x-sso-repaired="1"] [role="dialog"][aria-modal="true"]:has(.jetfuel-style-root:not(:has(button, iframe, input, form, a[href]))) {
  display: none !important;
  pointer-events: none !important;
  opacity: 0 !important;
}
html[data-x-sso-repaired="1"] body {
  overflow: auto !important;
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
    doc["x_sso_fix"] = _now()
    _save(HONOR_SEED, doc)
    return {"ok": True, "patched": changed}


def _is_stuck_sso_url(url: str) -> bool:
    u = (url or "").lower()
    return "/i/jf/onboarding/web/sso" in u or ("x.com" in u and "provider=google" in u and "sso" in u)


def repair(*, export_api: bool = True) -> dict[str, Any]:
    doc = doctrine()
    honor = _patch_honorability()
    out = {
        "ok": True,
        "schema": "hostess7-x-sso-fix/v1",
        "updated": _now(),
        "attribution": doc.get("attribution"),
        "motto": doc.get("motto"),
        "broken_pattern": doc.get("broken_pattern"),
        "sso_allow": doc.get("sso_allow") or [],
        "never_block_during_sso": doc.get("never_block_during_sso") or [],
        "honorability": honor,
        "client_repair": {
            **(doc.get("client_repair") or {}),
            "css": CLIENT_CSS,
            "detect": {
                "mask": '[data-testid="mask"]',
                "dialog": '[role="dialog"][aria-modal="true"]',
                "empty_jetfuel": ".jetfuel-style-root:not(:has(button, iframe, input, form, a[href]))",
            },
            "fallback_login": (doc.get("client_repair") or {}).get("fallback_login") or "/i/flow/login",
        },
        "witness": {"ok": True, "detail": "X Jetfuel SSO lanes open; empty modal repair armed"},
        "api": "/api/hostess7-x-sso-fix",
    }
    _save(PANEL, out)
    if export_api and DOCS_API.is_dir():
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
        "schema": "hostess7-x-sso-fix-panel/v1",
        "pending": "run repair",
        "motto": doctrine().get("motto"),
        "api": "/api/hostess7-x-sso-fix",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("repair", "fix", "run", "kill-div-bullshit"):
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
    print(
        json.dumps(
            {
                "usage": "hostess7-x-sso-fix.py [repair|json|explain|css]",
                "motto": doctrine().get("motto"),
                "api": "/api/hostess7-x-sso-fix",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())