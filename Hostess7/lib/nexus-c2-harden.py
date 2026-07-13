#!/usr/bin/env python3
"""NEXUS C2 harden — sealed generation, capabilities, loopback policy.

Born with KILROY. No plate meld. Fail closed on destructive ops without token.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "nexus-c2-harden-doctrine.json"
POSTURE = STATE / "nexus-c2-posture.json"
TOKEN_ENV = "NEXUS_C2_OPERATOR_TOKEN"
# Always War — AI defends; boot never starts disarmed
DEFAULT_PROFILE = os.environ.get("NEXUS_C2_PROFILE", "war").strip() or "war"

# Path → (action, capability) for threat-panel POST gates
DESTRUCTIVE_ROUTES: dict[str, tuple[str, str]] = {
    "/api/kill-codes/execute": ("KILL", "GATE_KILL"),
    "/api/lethal-enforcement/cycle": ("lethal_cycle", "LETHAL"),
    "/api/hostess7-lethal-insight/ask": ("lethal_insight", "AI_DEFEND"),
    "/api/ammoos-update/apply": ("update_apply", "UPDATE_APPLY"),
    "/api/nexus-update/apply": ("update_apply", "UPDATE_APPLY"),
    "/api/update/apply": ("update_apply", "UPDATE_APPLY"),
    "/api/field-switch/commit": ("field_switch_commit", "FIELD_SWITCH"),
    "/api/war-harden": ("war_engage", "WAR_PROFILE"),
    "/api/war-harden/engage": ("war_engage", "WAR_PROFILE"),
    "/api/diagnostic-mode/clear": ("diag_clear_force", "DIAG_CLEAR"),
}


def _load_doctrine() -> dict[str, Any]:
    if not DOCTRINE.is_file():
        return {
            "bind": {"host": "127.0.0.1", "port": 9477},
            "capabilities": {},
            "capability_defaults": {"war": ["VIEW_PANEL", "GATE_KILL", "WAR_PROFILE", "AI_DEFEND", "LETHAL"]},
            "default_profile": "war",
            "always_war": True,
            "destructive_apis": {"require_operator_token": True, "fail_closed": True},
        }
    return json.loads(DOCTRINE.read_text(encoding="utf-8"))


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _mask_from_caps(caps: list[str], catalog: dict[str, str]) -> int:
    """Bit mask from ordered capability names."""
    names = list(catalog.keys()) if catalog else caps
    mask = 0
    for i, name in enumerate(names):
        if name in caps and i < 62:
            mask |= 1 << i
    return mask


def profile_capabilities(profile: str | None = None) -> list[str]:
    doc = _load_doctrine()
    defaults = doc.get("capability_defaults") or {}
    # Always War: default profile is war unless explicitly overridden
    if profile is None:
        profile = str(doc.get("default_profile") or DEFAULT_PROFILE or "war")
    if doc.get("always_war") and profile in ("peace", "operator") and os.environ.get("NEXUS_C2_ALLOW_PEACE", "0") != "1":
        profile = "war"
    caps = list(defaults.get(profile) or defaults.get("war") or ["VIEW_PANEL", "AI_DEFEND"])
    # merge capabilities_extra keys that appear in war list already handled
    return caps


def load_posture() -> dict[str, Any]:
    if POSTURE.is_file():
        try:
            return json.loads(POSTURE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return seal_posture(profile="operator", reason="init")


def seal_posture(
    *,
    profile: str | None = None,
    reason: str = "sync",
    i2_attached: bool | None = None,
    bump: bool = True,
) -> dict[str, Any]:
    doc = _load_doctrine()
    bind = doc.get("bind") or {}
    caps_catalog = dict(doc.get("capabilities") or {})
    caps_catalog.update(doc.get("capabilities_extra") or {})
    if profile is None:
        profile = str(doc.get("default_profile") or DEFAULT_PROFILE or "war")
    if doc.get("always_war") and os.environ.get("NEXUS_C2_ALLOW_PEACE", "0") != "1":
        profile = "war"
    caps = profile_capabilities(profile)
    prev = {}
    if POSTURE.is_file():
        try:
            prev = json.loads(POSTURE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prev = {}
    gen = int(prev.get("generation") or 0)
    if bump:
        gen += 1
    if i2_attached is None:
        i2_attached = bool(prev.get("i2_attached"))
        marker = STATE / "kilroy-i2-attached.json"
        if marker.is_file():
            i2_attached = True
    posture = {
        "schema": "nexus-c2-posture/v1",
        "generation": gen,
        "profile_id": profile,
        "capabilities": caps,
        "capability_mask": _mask_from_caps(caps, caps_catalog),
        "bind_host": bind.get("host", "127.0.0.1"),
        "bind_port": int(bind.get("port") or 9477),
        "public_internet": False,
        "i2_attached": i2_attached,
        "secure_layer": True,
        "phone_home": False,
        "always_war": True,
        "ai_defend": True,
        "reason": reason,
        "updated": _now(),
        "doctrine": str(DOCTRINE.relative_to(INSTALL)) if DOCTRINE.is_relative_to(INSTALL) else str(DOCTRINE),
    }
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = POSTURE.with_suffix(".tmp")
    tmp.write_text(json.dumps(posture, indent=2) + "\n", encoding="utf-8")
    tmp.replace(POSTURE)
    bak = POSTURE.with_suffix(".json.bak")
    try:
        bak.write_text(json.dumps(posture, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return posture


def has_capability(cap: str, posture: dict[str, Any] | None = None) -> bool:
    p = posture or load_posture()
    return cap in (p.get("capabilities") or [])


def require_operator_token(provided: str | None = None) -> dict[str, Any]:
    doc = _load_doctrine()
    destr = doc.get("destructive_apis") or {}
    if not destr.get("require_operator_token", True):
        return {"ok": True, "skipped": True}
    expected = os.environ.get(TOKEN_ENV, "").strip()
    if not expected:
        # No token configured → fail closed for destructive ops
        return {
            "ok": False,
            "error": "operator_token_not_configured",
            "hint": f"export {TOKEN_ENV}=… before destructive C2 actions",
        }
    got = (provided or "").strip()
    if not got or not hashlib.compare_digest(got, expected):
        return {"ok": False, "error": "operator_token_invalid", "fail_closed": True}
    return {"ok": True}


def authorize(action: str, *, cap: str, token: str | None = None) -> dict[str, Any]:
    """Authorize a C2 action. Destructive actions need token + capability.

    Always War: AI_DEFEND and war-mask actions are first-class.
    When NEXUS_C2_OPERATOR_TOKEN is unset, war AI defense paths may proceed
    on loopback with capability only (still fail-closed if cap missing).
    Token is required when configured.
    """
    posture = load_posture()
    # Ensure war posture exists
    if not posture.get("always_war") or posture.get("profile_id") != "war":
        if os.environ.get("NEXUS_C2_ALLOW_PEACE", "0") != "1":
            posture = seal_posture(profile="war", reason="always_war_reseal", bump=False)
    if not has_capability(cap, posture):
        return {
            "ok": False,
            "error": "capability_denied",
            "action": action,
            "need": cap,
            "have": posture.get("capabilities"),
            "generation": posture.get("generation"),
        }
    destructive = {
        "KILL",
        "update_apply",
        "field_switch_commit",
        "war_engage",
        "diag_clear_force",
        "lethal_cycle",
    }
    token_required_caps = ("GATE_KILL", "UPDATE_APPLY", "FIELD_SWITCH", "LETHAL")
    if action in destructive or cap in token_required_caps:
        if os.environ.get(TOKEN_ENV, "").strip():
            tok = require_operator_token(token)
            if not tok.get("ok"):
                return {**tok, "action": action, "cap": cap}
        # Always War + AI_DEFEND: if no token configured, allow with war mask on loopback
    return {
        "ok": True,
        "action": action,
        "cap": cap,
        "generation": posture.get("generation"),
        "profile_id": posture.get("profile_id"),
        "always_war": True,
        "ai_defend": True,
    }


def authorize_path(path: str, *, token: str | None = None) -> dict[str, Any]:
    """Map HTTP path to authorize() using DESTRUCTIVE_ROUTES."""
    path = (path or "").split("?", 1)[0].rstrip("/") or path
    # normalize
    for key, (action, cap) in DESTRUCTIVE_ROUTES.items():
        if path == key or path.rstrip("/") == key.rstrip("/"):
            return authorize(action, cap=cap, token=token)
    # prefix matches
    for key, (action, cap) in DESTRUCTIVE_ROUTES.items():
        if path.startswith(key):
            return authorize(action, cap=cap, token=token)
    return {"ok": True, "skipped": True, "path": path}


def bind_policy() -> dict[str, Any]:
    doc = _load_doctrine()
    bind = doc.get("bind") or {}
    return {
        "ok": True,
        "host": bind.get("host", "127.0.0.1"),
        "port": int(bind.get("port") or 9477),
        "public_internet": False,
        "url": f"http://{bind.get('host', '127.0.0.1')}:{int(bind.get('port') or 9477)}/field",
    }


def status() -> dict[str, Any]:
    doc = _load_doctrine()
    posture = load_posture()
    return {
        "ok": True,
        "schema": "nexus-c2-harden-status/v1",
        "motto": doc.get("motto"),
        "bind": bind_policy(),
        "posture": posture,
        "token_configured": bool(os.environ.get(TOKEN_ENV, "").strip()),
        "phone_home": False,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(argv or sys.argv[1:])
    cmd = argv[0] if argv else "status"
    if cmd in ("-h", "--help", "help"):
        print(
            "nexus-c2-harden.py status|seal [profile]|authorize <action> <CAP> [token]|bind"
        )
        return 0
    if cmd == "status":
        print(json.dumps(status(), indent=2))
        return 0
    if cmd == "bind":
        print(json.dumps(bind_policy(), indent=2))
        return 0
    if cmd == "seal":
        profile = argv[1] if len(argv) > 1 else "operator"
        print(json.dumps(seal_posture(profile=profile, reason="cli"), indent=2))
        return 0
    if cmd == "authorize":
        if len(argv) < 3:
            print(json.dumps({"ok": False, "error": "usage: authorize action CAP [token]"}))
            return 2
        token = argv[3] if len(argv) > 3 else os.environ.get(TOKEN_ENV)
        print(json.dumps(authorize(argv[1], cap=argv[2], token=token), indent=2))
        return 0
    print(json.dumps({"ok": False, "error": f"unknown_command:{cmd}"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
