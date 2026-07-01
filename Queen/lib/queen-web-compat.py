#!/usr/bin/env pythong
"""Queen Web Compat — full HTML/JS/CSS spectrum, pre-1.0 through future drafts.

Auto modes secure legacy code: isolate old JS from OS/memory while preserving surface behavior.
Engine targets (Queen Browser, Ladybird, Servo) honor these profiles at render time.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

QUEEN = Path(__file__).resolve().parents[1]

# Eras: nothing omitted — gates held per layer, not amputated.
ERAS: list[dict[str, Any]] = [
    {
        "id": "html_pre1",
        "label": "HTML pre-1.0 / Netscape 1",
        "year": 1993,
        "js": "none",
        "quirks": "netscape1",
        "plugins": ["surrogate"],
    },
    {
        "id": "html2",
        "label": "HTML 2.0 / early tables",
        "year": 1995,
        "js": "es1",
        "quirks": "nav4",
        "plugins": ["surrogate"],
    },
    {
        "id": "html3",
        "label": "HTML 3.2 / CSS1",
        "year": 1997,
        "js": "es3",
        "quirks": "ie5",
        "plugins": ["surrogate", "java_applet_wasm"],
    },
    {
        "id": "html4",
        "label": "HTML 4.01 / XHTML 1",
        "year": 1999,
        "js": "es5",
        "quirks": "ie7",
        "plugins": ["surrogate", "flash_wasm", "silverlight_wasm"],
    },
    {
        "id": "html5",
        "label": "HTML5 living / ES5+",
        "year": 2012,
        "js": "es5",
        "quirks": "almost-standards",
        "plugins": ["surrogate"],
    },
    {
        "id": "es2015",
        "label": "ES2015 modules",
        "year": 2015,
        "js": "es2015",
        "quirks": "no-quirks",
        "plugins": [],
    },
    {
        "id": "es2020",
        "label": "ES2020 + WASM mature",
        "year": 2020,
        "js": "es2020",
        "quirks": "no-quirks",
        "plugins": [],
    },
    {
        "id": "es2026",
        "label": "ES2026 ship-now",
        "year": 2026,
        "js": "es2026",
        "quirks": "no-quirks",
        "plugins": [],
    },
    {
        "id": "future_draft",
        "label": "Future drafts / WICG incubating",
        "year": 2030,
        "js": "esnext",
        "quirks": "no-quirks",
        "plugins": [],
        "experimental": True,
    },
]

MODES: dict[str, dict[str, Any]] = {
    "auto": {
        "label": "Auto — detect era, secure legacy",
        "detect": True,
        "default_era": "es2026",
    },
    "modern": {
        "label": "Modern — full surface, gates held",
        "era": "es2026",
        "sandbox": "allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-presentation",
        "legacy_isolate": False,
    },
    "legacy_secure": {
        "label": "Legacy secure — quirks + WASM surrogates, OS isolated",
        "era": "html4",
        "sandbox": "allow-scripts allow-same-origin allow-forms allow-popups",
        "legacy_isolate": True,
        "block_top_navigation": True,
        "plugin_surrogate": True,
        "no_shared_array_buffer": True,
    },
    "archaeology": {
        "label": "Archaeology — pre-HTML5, maximum compat cage",
        "era": "html2",
        "sandbox": "allow-scripts allow-same-origin allow-forms",
        "legacy_isolate": True,
        "plugin_surrogate": True,
        "document_write": True,
        "frameset": True,
    },
    "future": {
        "label": "Future — experimental APIs enabled",
        "era": "future_draft",
        "sandbox": "allow-scripts allow-same-origin allow-forms allow-popups allow-modals allow-downloads allow-presentation",
        "experimental": True,
    },
}

_LEGACY_HOST_RE = re.compile(
    r"(geocities|angelfire|tripod|fortunecity|xoom|homestead|"
    r"archive\.org|web\.archive|wayback|neocities|"
    r"\.htm$|\.shtml$|frameset|marquee)",
    re.I,
)
_LEGACY_PATH_RE = re.compile(r"/(old|legacy|retro|v1|classic|ie\d|ns\d)/", re.I)


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _era_by_id(era_id: str) -> dict[str, Any]:
    for e in ERAS:
        if e["id"] == era_id:
            return e
    return ERAS[-2]


def detect_era(url: str, hints: dict[str, Any] | None = None) -> dict[str, Any]:
    hints = hints or {}
    u = (url or "").strip().lower()
    parsed = urlparse(u if "://" in u else f"http://{u}")
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()

    if hints.get("era"):
        era = _era_by_id(str(hints["era"]))
        return {"era": era, "confidence": 1.0, "reason": "operator_hint"}

    if u.startswith("queen://") or host in ("127.0.0.1", "localhost"):
        return {"era": _era_by_id("es2026"), "confidence": 0.95, "reason": "queen_internal"}

    if _LEGACY_HOST_RE.search(host) or _LEGACY_PATH_RE.search(path):
        return {"era": _era_by_id("html4"), "confidence": 0.85, "reason": "legacy_host_or_path"}

    if parsed.scheme == "http" and not host.endswith(".onion"):
        return {"era": _era_by_id("html5"), "confidence": 0.6, "reason": "cleartext_http"}

    if hints.get("frameset") or hints.get("document_write"):
        return {"era": _era_by_id("html3"), "confidence": 0.75, "reason": "legacy_dom_signals"}

    if hints.get("flash") or hints.get("applet") or hints.get("silverlight"):
        return {"era": _era_by_id("html4"), "confidence": 0.9, "reason": "plugin_surrogate"}

    return {"era": _era_by_id("es2026"), "confidence": 0.5, "reason": "default_modern"}


def _queen_user_agent(*, era: dict[str, Any], mode_key: str) -> str:
    ua_era = era["id"]
    engine_rev = "128.0"
    if era["year"] < 1998:
        return f"Mozilla/4.0 (compatible; QueenBrowser/2026; AmmoOS; Legacy/{ua_era})"
    return (
        f"Mozilla/5.0 (X11; Linux x86_64; rv:{engine_rev}) "
        f"QueenBrowser/2026 AmmoOS/1.0 compat/{ua_era} mode/{mode_key} "
        f"Gecko/20100101 QueenFieldEngine/{engine_rev}"
    )


def resolve_profile(
    url: str,
    *,
    mode: str = "auto",
    hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    mode_key = (mode or "auto").strip().lower().replace("-", "_")
    if mode_key not in MODES:
        mode_key = "auto"
    mode_doc = MODES[mode_key]

    if mode_key == "auto":
        detected = detect_era(url, hints)
        era = detected["era"]
        if era["year"] < 2005:
            effective_mode = "legacy_secure"
        elif era["year"] < 2012:
            effective_mode = "archaeology" if era["year"] < 1998 else "legacy_secure"
        else:
            effective_mode = "modern"
        mode_doc = {**MODES[effective_mode], "auto_selected": effective_mode}
        detect_meta = detected
    else:
        era = _era_by_id(str(mode_doc.get("era") or "es2026"))
        detect_meta = {"era": era, "confidence": 1.0, "reason": f"mode:{mode_key}"}

    user_agent = _queen_user_agent(era=era, mode_key=mode_key)

    return {
        "schema": "queen-web-compat/v1",
        "updated": _ts(),
        "url": url,
        "mode": mode_key,
        "effective_mode": mode_doc.get("auto_selected") or mode_key,
        "era": era,
        "detect": detect_meta,
        "sandbox": mode_doc.get("sandbox") or MODES["modern"]["sandbox"],
        "legacy_isolate": bool(mode_doc.get("legacy_isolate")),
        "plugin_surrogate": bool(mode_doc.get("plugin_surrogate") or era.get("plugins")),
        "experimental": bool(mode_doc.get("experimental") or era.get("experimental")),
        "quirks": era.get("quirks"),
        "js_target": era.get("js"),
        "user_agent": user_agent,
        "capabilities": {
            "html_dom": True,
            "javascript": True,
            "wasm": era["year"] >= 2015,
            "service_workers": era["year"] >= 2012,
            "webgl": era["year"] >= 2011,
            "webgpu": era["year"] >= 2024,
            "mse_mp4": era["year"] >= 2010,
            "webrtc": era["year"] >= 2012,
            "legacy_plugins_surrogate": bool(era.get("plugins")),
            "document_write": bool(mode_doc.get("document_write") or era["year"] < 2005),
            "frameset": bool(mode_doc.get("frameset") or era["year"] < 2000),
        },
        "security": {
            "isolate_from_os": bool(mode_doc.get("legacy_isolate")),
            "block_top_navigation": bool(mode_doc.get("block_top_navigation")),
            "no_shared_array_buffer": bool(mode_doc.get("no_shared_array_buffer")),
            "gate_nav_required": True,
            "serve_and_listen": True,
        },
        "motto": "THE web browser — every era, every gate held, legacy caged not amputated",
    }


def compat_status() -> dict[str, Any]:
    return {
        "schema": "queen-web-compat/v1",
        "updated": _ts(),
        "motto": "Full gamut: pre-1.0 HTML through future drafts. Auto modes secure old code.",
        "modes": {k: {"label": v["label"]} for k, v in MODES.items()},
        "eras": ERAS,
        "engine_targets": ["queen-browser", "queen-field-engine", "queen-shell+proxy", "ladybird", "servo"],
        "doctrine": {
            "omit_capabilities": False,
            "hold_all_gates": True,
            "legacy_strategy": "wasm_surrogate_plus_sandbox",
        },
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "eras"):
        return {"ok": True, **compat_status()}
    if action in ("resolve", "profile", "detect"):
        url = str(body.get("url") or "")
        profile = resolve_profile(
            url,
            mode=str(body.get("mode") or "auto"),
            hints=body.get("hints") if isinstance(body.get("hints"), dict) else None,
        )
        return {"ok": True, **profile}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(compat_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())