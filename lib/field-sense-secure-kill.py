#!/usr/bin/env pythong
"""Secure kill posture — prejudice policy for sense ironclad blocks (Eye · Ear · Mouth)."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def _import_py(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _py_json(script: Path, args: list[str], *, install: Path, sg: Path, timeout: int = 30) -> dict[str, Any]:
    if not script.is_file():
        return {}
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(install),
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(install), "SG_ROOT": str(sg)},
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return {}
    try:
        doc = json.loads(proc.stdout)
        return doc if isinstance(doc, dict) else {}
    except json.JSONDecodeError:
        return {}


def secure_kill_posture(install: Path, sg: Path | None = None) -> dict[str, Any]:
    sg = sg or install.parent
    law_path = install / "data" / "kill-immediate-law.json"
    war_path = install / "data" / "field-war-hardening-doctrine.json"
    law = {}
    war_doc = {}
    try:
        law = json.loads(law_path.read_text(encoding="utf-8")) if law_path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        pass
    try:
        war_doc = json.loads(war_path.read_text(encoding="utf-8")) if war_path.is_file() else {}
    except (OSError, json.JSONDecodeError):
        pass

    kill_policy = war_doc.get("kill_policy") or {}
    prejudice = os.environ.get("SG_ROOT_KILL_PREJUDICE", "1").strip().lower() not in ("0", "false", "no")
    sovereign_kill = os.environ.get("SG_ROOT_SOVEREIGN_KILL", "1").strip().lower() not in ("0", "false", "no")

    war = _py_json(install / "lib" / "field-war-hardening.py", ["json"], install=install, sg=sg, timeout=25)
    root = _py_json(
        install / "Queen" / "lib" / "queen-root-sovereign.py",
        ["json"],
        install=install,
        sg=sg,
        timeout=20,
    )
    if not root:
        root_mod = _import_py(install / "Queen" / "lib" / "queen-root-sovereign.py", "qrs_sense")
        if root_mod and hasattr(root_mod, "status"):
            try:
                root = root_mod.status()
            except Exception:
                root = {}

    root_policy = str(root.get("kill_policy") or "observe")
    war_posture = war.get("posture") or war.get("war_machine") or war.get("ok")
    immediate = str(law.get("law") or "immediate_is_best") == "immediate_is_best"
    rekill = bool(kill_policy.get("every_kill_rekill", war_doc.get("posture", {}).get("every_kill_rekill")))

    env_armed = prejudice and sovereign_kill and immediate and rekill
    policy_ok = root_policy == "prejudice" if root else env_armed
    war_ok = bool(war.get("ok")) or war_path.is_file()
    ok = env_armed and policy_ok and war_ok

    return {
        "schema": "field-sense-secure-kill/v1",
        "kill_policy": "prejudice" if prejudice else "observe",
        "root_sovereign_policy": root_policy,
        "immediate_kill_law": immediate,
        "every_kill_rekill": rekill,
        "war_hardened": bool(war.get("ok") or war_posture),
        "foreign_root_cleared": int((root.get("panel") or {}).get("killed_prejudice") or root.get("killed_prejudice") or 0),
        "motto": "Anyone in the way — secure kill with prejudice · RE-KILL forever",
        "ok": ok,
    }


def main() -> int:
    install = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
    sg = Path(os.environ.get("SG_ROOT", install.parent))
    print(json.dumps(secure_kill_posture(install, sg), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())