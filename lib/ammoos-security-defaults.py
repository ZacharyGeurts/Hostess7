#!/usr/bin/env pythong
"""AmmoOS security defaults — theme changes cannot weaken field posture."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "ammoos-security-defaults-doctrine.json"


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def posture() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    policy = doc.get("policy") or {}
    guards = doc.get("theme_guards") or {}
    return {
        "ok": True,
        "schema": doc.get("schema") or "ammoos-security-defaults/v1",
        "policy": policy,
        "theme_guards": guards,
        "motto": doc.get("motto") or "Operator customizes look · system holds security",
    }


def theme_patch_allowed(patch: dict[str, Any]) -> dict[str, Any]:
    """Strip keys that could weaken security via theme UI."""
    doc = _load(DOCTRINE, {})
    allowed = set((doc.get("theme_guards") or {}).get("allowed_shell_keys") or [])
    if not allowed:
        return dict(patch or {})
    return {k: v for k, v in (patch or {}).items() if k in allowed}


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    print("usage: ammoos-security-defaults.py [json|posture]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())