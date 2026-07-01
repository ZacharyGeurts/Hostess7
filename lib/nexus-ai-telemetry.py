#!/usr/bin/env pythong
"""NEXUS AI telemetry posture — local secure channel ON by default; zero external release."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
OVERRIDE = STATE / "settings.override"

AI_KEYS = ("NEXUS_AI_SECURE_CHANNEL", "QUEEN_AI_TELEMETRY_OK")
ZERO_KEYS = ("NEXUS_ZERO_TELEMETRY", "QUEEN_ZERO_TELEMETRY")


def _truthy(val: str | None) -> bool:
    return str(val or "").strip().lower() in ("1", "true", "yes", "on")


def _read_override() -> dict[str, str]:
    out: dict[str, str] = {}
    if not OVERRIDE.is_file():
        return out
    try:
        for line in OVERRIDE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            out[key.strip()] = val.strip()
    except OSError:
        pass
    return out


def _effective_flag(key: str, *, default: str = "1") -> bool:
    override = _read_override()
    if key in override:
        return _truthy(override[key])
    env = os.environ.get(key, "")
    if env:
        return _truthy(env)
    return _truthy(default)


def zero_telemetry_active() -> bool:
    for key in ZERO_KEYS:
        if _effective_flag(key, default="1"):
            return True
    return _effective_flag("NEXUS_QUEEN_SOVEREIGN", default="1")


def ai_telemetry_on() -> bool:
    return all(_effective_flag(k, default="1") for k in AI_KEYS)


def posture() -> dict[str, Any]:
    on = ai_telemetry_on()
    zero = zero_telemetry_active()
    return {
        "schema": "nexus-ai-telemetry/v1",
        "ai_telemetry_on": on,
        "ai_secure_channel": _effective_flag("NEXUS_AI_SECURE_CHANNEL", default="1"),
        "queen_ai_telemetry_ok": _effective_flag("QUEEN_AI_TELEMETRY_OK", default="1"),
        "zero_telemetry": zero,
        "data_release": False,
        "local_only": True,
        "egress_policy": "loopback_secure_channel_only",
        "motto": "AI telemetry ON locally — zero phone-home; we never release your data.",
        "settings_keys": list(AI_KEYS),
    }


def apply_env(env: dict[str, str] | None = None) -> dict[str, str]:
    """Inject effective AI telemetry flags into a subprocess environment."""
    base = dict(env or os.environ)
    for key in AI_KEYS:
        base[key] = "1" if _effective_flag(key, default="1") else "0"
    for key in ZERO_KEYS:
        base[key] = "1" if _effective_flag(key, default="1") else "0"
    return base


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: nexus-ai-telemetry.py [json|status|posture]"}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())