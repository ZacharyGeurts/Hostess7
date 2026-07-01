#!/usr/bin/env pythong
"""Queen settings surface — lock best-settings doctrine; expose minimal operator controls."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT)))
DOCTRINE = INSTALL / "data" / "queen-settings-surface-doctrine.json"


def _load() -> dict[str, Any]:
    candidates = (
        DOCTRINE,
        ROOT / "data" / "queen-settings-surface-doctrine.json",
        INSTALL.parent / "data" / "queen-settings-surface-doctrine.json",
        Path("/usr/local/lib/nexus-shield/data/queen-settings-surface-doctrine.json"),
    )
    for path in candidates:
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
    return {
        "schema": "queen-settings-surface/v1",
        "policy": {"surface_locked": True, "always_optimal": True},
        "operator_exposed": {"shell": ["ui_scale"], "audio": []},
        "locked_nexus_keys": [],
        "locked_shell_keys": [],
    }


def surface_locked() -> bool:
    if os.environ.get("QUEEN_SETTINGS_SURFACE_UNLOCK", "") in ("1", "true", "yes", "on"):
        return False
    doc = _load()
    return bool((doc.get("policy") or {}).get("surface_locked", True))


def locked_nexus_keys() -> frozenset[str]:
    doc = _load()
    return frozenset(doc.get("locked_nexus_keys") or [])


def locked_shell_keys() -> frozenset[str]:
    doc = _load()
    return frozenset(doc.get("locked_shell_keys") or [])


def operator_shell_keys() -> frozenset[str]:
    doc = _load()
    exposed = doc.get("operator_exposed") or {}
    return frozenset(exposed.get("shell") or ["ui_scale"])


def operator_audio_keys() -> frozenset[str]:
    doc = _load()
    exposed = doc.get("operator_exposed") or {}
    return frozenset(
        exposed.get("audio")
        or [
            "default_sink",
            "default_source",
            "sink_volume",
            "source_volume",
            "sink_muted",
            "source_muted",
        ]
    )


def nexus_key_allowed(key: str) -> bool:
    if not surface_locked():
        return True
    return str(key).strip() not in locked_nexus_keys()


def shell_patch_allowed(patch: dict[str, Any]) -> dict[str, Any]:
    if not surface_locked():
        return dict(patch or {})
    allowed = operator_shell_keys()
    return {k: v for k, v in (patch or {}).items() if k in allowed}


def audio_patch_allowed(patch: dict[str, Any]) -> dict[str, Any]:
    if not surface_locked():
        return dict(patch or {})
    allowed = operator_audio_keys()
    out = {k: v for k, v in (patch or {}).items() if k in allowed}
    if "advanced" in (patch or {}):
        out["advanced"] = False
    return out


def _sovereignty() -> dict[str, Any]:
    script = ROOT / "lib" / "queen-ammoos-sovereignty.py"
    if not script.is_file():
        return {"ok": False, "skipped": True}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("queen_ammoos_sov_settings", script)
        mod = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(mod)
        return mod.posture()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def posture() -> dict[str, Any]:
    doc = _load()
    policy = doc.get("policy") or {}
    sov = _sovereignty()
    return {
        "schema": "queen-settings-surface/v1",
        "ok": True,
        "surface_locked": surface_locked(),
        "always_optimal": bool(policy.get("always_optimal", True)),
        "best_settings": policy.get("best_settings") or "always_optimal",
        "operator_exposed": doc.get("operator_exposed") or {},
        "operator_panels": doc.get("operator_panels") or [],
        "locked_nexus_count": len(locked_nexus_keys()),
        "locked_shell_count": len(locked_shell_keys()),
        "sovereignty": sov,
        "loopback_authority": sov.get("loopback_authority") or "127.0.0.1",
        "internet_pipe_percent": sov.get("internet_pipe_percent", 0),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    print("usage: queen-settings-surface.py [json]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())