#!/usr/bin/env pythong
"""Queen FieldNet — internal-only routing, egress gate, packet field slice.

Queen takeover: no URLs outside Queen. Hostess 7 + loopback world is the wire.
AmmoOS INT 2A-2D → FieldQueenNet (g16/FIELDC build target).
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(SG / "NewLatest")))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
MANDATE = QUEEN / "data" / "queen-field-net.json"
WORLD_PORT = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
WORLD_HOST = os.environ.get("QUEEN_WORLD_HOST", "127.0.0.1")

INTERNAL_HOSTS = frozenset({
    "127.0.0.1", "localhost", "::1", "0.0.0.0",
    f"queen.local", f"hostess7.local",
})

QUEEN_SCHEME = "queen"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _mod(name: str, rel: str, install: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, install / "lib" / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def load_mandate() -> dict[str, Any]:
    return _load_json(MANDATE, {"schema": "queen-field-net/v1", "routes": []})


def internal_only() -> bool:
    if os.environ.get("QUEEN_ALLOW_EXTERNAL_URLS", "") in ("1", "true", "yes"):
        return False
    return os.environ.get("QUEEN_INTERNAL_ONLY", "1") == "1"


def world_base() -> str:
    return f"http://{WORLD_HOST}:{WORLD_PORT}"


def default_home() -> str:
    custom = os.environ.get("QUEEN_BROWSER_HOME", "").strip()
    if custom:
        return custom
    return f"{world_base()}/world/kilroy-home.html"


def internal_routes() -> list[dict[str, Any]]:
    m = load_mandate()
    routes = list(m.get("routes") or [])
    base = world_base()
    out = []
    for r in routes:
        path = r.get("path") or "/"
        out.append({**r, "url": base + path if path.startswith("/") else path})
    return out


def _resolve_queen_scheme(url: str) -> str:
    if not url.lower().startswith(f"{QUEEN_SCHEME}://"):
        return url
    rest = url.split("://", 1)[1]
    host = rest.split("/", 1)[0].lower()
    mapping = {
        "world": "/world/browser.html",
        "forge": "/gui/queen-build-deck.html",
        "hostess": "/api/field-brain",
        "brain": "/api/field-brain",
        "eye": "/api/queen-eyeball",
        "eyeball": "/api/queen-eyeball",
        "gates": "/api/queen-browser",
        "boot": "/api/queen-boot",
        "build": "/api/queen-build",
        "kilroy": "/api/kilroy",
        "field": "/api/kilroy",
        "rtx": "/world/queen-chips-cores.html",
        "amouranthrtx": "/world/queen-chips-cores.html",
        "engine": "/world/queen-chips-cores.html",
        "gameroom": "/world/queen-game-room.html",
        "game-room": "/world/queen-game-room.html",
        "chips": "/world/queen-chips-cores.html",
        "cores": "/world/queen-chips-cores.html",
        "cinema": "/world/queen-game-room.html",
        "terminal": "/world/?dock=terminal",
        "gnu-terminal": "/world/?dock=terminal",
        "shell": "/world/?dock=terminal",
        "start": f"http://127.0.0.1:{int(os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477'))}/field",
        "programs": f"http://127.0.0.1:{int(os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477'))}/field",
        "nexus": f"http://127.0.0.1:{int(os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477'))}/field",
        "nexus-field": f"http://127.0.0.1:{int(os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477'))}/field",
        "field": f"http://127.0.0.1:{int(os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477'))}/field",
        "c2": f"http://127.0.0.1:{int(os.environ.get('NEXUS_THREAT_PANEL_PORT', '9477'))}/field",
        "sovereign": "/api/sovereign",
        "capsule": "/api/sovereign",
        "horizon7": "/api/horizon7",
        "horizon-7": "/api/horizon7",
        "horizon": "/api/horizon7",
        "compiler": "/api/field/compiler",
        "g16": "/api/field/compiler",
        "field-compiler": "/api/field/compiler",
        "grokpy": "/api/grokpy",
        "pythong": "/api/pythong",
        "python": "/api/grokpy",
        "runtime": "/api/grokpy",
        "ear": "/api/queen-earball",
        "earball": "/api/queen-earball",
        "final-ear": "/api/final-ear",
        "field-manual": "/api/field-manual",
        "manual": "/api/field-manual",
        "nexus-jump": "/api/nexus-jump",
        "jump": "/api/nexus-jump",
        "external": "/api/external-wire",
        "external-wire": "/api/external-wire",
        "field-external": "/api/external-wire",
        "redata": "/api/world-redata",
        "world-redata": "/api/world-redata",
        "redata-forever": "/api/secure-channel",
        "secure-channel": "/api/secure-channel",
        "secure": "/api/secure-channel",
        "forever-secure": "/api/secure-channel",
        "repack": f"http://127.0.0.1:{int(os.environ.get('WORLD_REPACK_PORT', '9480'))}/",
        "world-repack": f"http://127.0.0.1:{int(os.environ.get('WORLD_REPACK_PORT', '9480'))}/",
        "contact-vector": "/api/contact-vector",
    }
    path = mapping.get(host, f"/world/?view={host}")
    return world_base() + path


def _single_field_depth_max() -> int:
    """Ironclad safety — one field, depth zero always (soft touch)."""
    if os.environ.get("NEXUS_SINGLE_FIELD_DEPTH", "1").strip().lower() in ("0", "false", "no", "off"):
        return 64
    return 0


def _field_depth_from_url(url: str) -> int:
    cap = _single_field_depth_max()
    if cap <= 0:
        return 0
    try:
        q = parse_qs(urlparse(url).query)
        d = int((q.get("field_depth") or ["0"])[0])
        return max(0, min(d, cap))
    except (ValueError, TypeError, IndexError):
        return 0


def _depth_singularizer_mod() -> Any | None:
    sing = INSTALL / "lib" / "field-depth-singularizer.py"
    if not sing.is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_depth_singularizer_net", sing)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _nested_field_meta(url: str, *, layer_depth: int | None = None) -> dict[str, Any]:
    cap = _single_field_depth_max()
    sing = _depth_singularizer_mod()
    if sing and hasattr(sing, "enforce_depth_field_impossible"):
        rec = sing.enforce_depth_field_impossible(url, layer_depth=layer_depth)
        depth = 0 if cap <= 0 else _field_depth_from_url(rec.get("url") or url)
        return {
            "field_depth": depth,
            "single_field_depth": cap <= 0,
            "max_field_depth": cap,
            "nested_field_safe": depth == 0,
            "field_on_field": False,
            "depth_field_requested": rec.get("depth_field_requested"),
            "depth_field_forbidden": rec.get("forbidden"),
            "depth_field_impossible": rec.get("depth_field_impossible"),
            "depth_fields_sealed_and_destroyed": rec.get("depth_fields_sealed_and_destroyed"),
            "depth_field_destroyed": rec.get("depth_field_destroyed"),
            "creation_forbidden": rec.get("creation_forbidden"),
            "depth_field_stripped": rec.get("depth_field_stripped"),
            "enforced_url": rec.get("url"),
            "rule": rec.get("rule") or ("single_field_depth_always" if cap <= 0 else "legacy_depth_cap"),
            "citation": rec.get("citation"),
        }
    depth = _field_depth_from_url(url)
    return {
        "field_depth": depth,
        "single_field_depth": cap <= 0,
        "max_field_depth": cap,
        "nested_field_safe": depth <= cap and depth == 0,
        "field_on_field": False if cap <= 0 else depth > 0,
        "rule": "single_field_depth_always" if cap <= 0 else "legacy_depth_cap",
    }


def classify_url(url: str) -> dict[str, Any]:
    """Classify contact — presume hostile; never presume correct contact without positive ID."""
    u = (url or "").strip()
    nested = _nested_field_meta(u)
    if not u or u == "about:blank":
        return {
            "url": u,
            "verdict": "ALLOW",
            "iff": "CONTACT_UNKNOWN",
            "layer": "blank",
            "internal": True,
            "presume_hostile": True,
            **nested,
        }
    if u.startswith("/"):
        u = world_base() + u
    if u.lower().startswith(f"{QUEEN_SCHEME}://"):
        resolved = _resolve_queen_scheme(u)
        return {
            "url": u,
            "resolved": resolved,
            "verdict": "ALLOW_INTERNAL",
            "iff": "CAPSULE_INTERNAL",
            "layer": "queen_scheme",
            "internal": True,
            "presume_hostile": True,
            **nested,
        }
    parsed = urlparse(u)
    host = (parsed.hostname or "").lower()
    if parsed.scheme in ("file", "data", "blob"):
        return {
            "url": u,
            "verdict": "ALLOW_LOCAL",
            "iff": "CAPSULE_INTERNAL",
            "layer": "local",
            "internal": True,
            "presume_hostile": True,
            **nested,
        }
    if host in INTERNAL_HOSTS or host.endswith(".local"):
        if parsed.port in (None, WORLD_PORT, 9479, 9477, 2419) or host in INTERNAL_HOSTS:
            return {
                "url": u,
                "verdict": "ALLOW_LOOPBACK",
                "iff": "CAPSULE_INTERNAL",
                "layer": "loopback",
                "internal": True,
                "presume_hostile": True,
                **nested,
            }
    if not internal_only():
        return {
            "url": u,
            "verdict": "ALLOW_LEGACY",
            "iff": "CONTACT_HOSTILE",
            "layer": "external",
            "internal": False,
            "presume_hostile": True,
            **nested,
        }
    return {
        "url": u,
        "verdict": "BLOCK_EXTERNAL",
        "iff": "HOSTILE",
        "layer": "external",
        "internal": False,
        "presume_hostile": True,
        "reason": "queen_internal_only — no URLs outside Queen",
        "hint": default_home(),
        **nested,
    }


def _packet_slice() -> dict[str, Any]:
    install = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN.parent))
    path = install / "lib" / "packet-field.py"
    if not path.is_file():
        path = SG / "NewLatest" / "lib" / "packet-field.py"
    if not path.is_file():
        return {"error": "packet-field missing"}
    try:
        return _mod("packet_field", "packet-field.py", path.parent.parent).panel_json()
    except Exception as exc:
        return {"error": str(exc)}


def _compiler_slice() -> dict[str, Any]:
    try:
        sys.path.insert(0, str(SG / "ZOCR"))
        from zocr_field_compiler import field_compiler_status  # type: ignore

        return field_compiler_status()
    except Exception as exc:
        return {"error": str(exc), "field_compiler": "Grok16", "note": "ZOCR bridge optional"}


def _queen_security() -> dict[str, Any]:
    try:
        return _mod("queen_security", "queen-security.py", QUEEN).security_status()
    except Exception as exc:
        return {"error": str(exc)}


def _external_wire_slice() -> dict[str, Any]:
    try:
        return _mod("queen_external_wire", "queen-external-wire.py", QUEEN).external_wire_status()
    except Exception as exc:
        return {"error": str(exc), "lane": "External"}


def _secure_channel_slice() -> dict[str, Any]:
    try:
        return _mod("queen_secure_channel", "queen-secure-channel.py", QUEEN).secure_channel_fast()
    except Exception as exc:
        return {"error": str(exc), "lane": "SecureChannel", "hydrate": "/api/secure-channel"}


def field_net_status() -> dict[str, Any]:
    m = load_mandate()
    sec = _queen_security()
    seal_ok = (sec.get("code_seal") or {}).get("ok")
    return {
        "schema": "queen-field-net/v1",
        "updated": _now(),
        "motto": m.get("motto"),
        "doctrine": m.get("doctrine") or {},
        "internal_only": internal_only(),
        "world_base": world_base(),
        "default_home": default_home(),
        "routes": internal_routes(),
        "fieldc_targets": m.get("fieldc_targets") or [],
        "phases": m.get("phases") or {},
        "packet_field": _packet_slice(),
        "external_wire": _external_wire_slice(),
        "secure_channel": _secure_channel_slice(),
        "field_compiler": _compiler_slice(),
        "queen_security": sec,
        "routes_secured": seal_ok is not False,
        "ammoos": {
            "ints": ["0x2A", "0x2C", "0x2D"],
            "handler": "FieldQueenNet.hpp",
            "status": "stub → FIELDC guest modules",
        },
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json"):
        return {"ok": True, **field_net_status()}
    if action == "classify":
        return {"ok": True, "classification": classify_url(str(body.get("url") or ""))}
    if action == "resolve":
        url = str(body.get("url") or "")
        try:
            gate = _mod("queen_security", "queen-security.py", QUEEN).mandate_enforce("field_route")
            if not gate.get("ok"):
                return {"ok": False, "error": "security_gate", **gate}
        except Exception:
            pass
        c = classify_url(url)
        if c.get("verdict") in ("BLOCK_EXTERNAL",):
            return {"ok": False, "error": "external_blocked", **c}
        resolved = c.get("resolved") or url
        if resolved.startswith("/"):
            resolved = world_base() + resolved
        return {"ok": True, "resolved": resolved, "classification": c}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(field_net_status(), ensure_ascii=False))
        return 0
    if cmd == "classify" and len(sys.argv) > 2:
        print(json.dumps(classify_url(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-field-net.py [json|classify <url>|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())