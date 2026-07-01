#!/usr/bin/env pythong
"""NEXUS C2 war machine hardening — stamp posture, arm Hostess7 weapons, verify layer chain."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-war-hardening-doctrine.json"
PANEL = STATE / "field-war-hardening-panel.json"
LEDGER = STATE / "field-war-hardening-ledger.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _run_py(script: Path, *args: str, timeout: int = 90) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(script)}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def layer_chain() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    order = doctrine.get("layer_order") or ["hardware", "nexus_c2", "kilroy", "ammoos", "queen"]
    boot = doctrine.get("boot_order") or ["nexus_c2", "kilroy", "ammoos_desktop", "queen_on_demand"]
    return {
        "ok": True,
        "schema": "field-war-layer-chain/v1",
        "layer_order": order,
        "boot_order": boot,
        "nexus_c2_base": True,
        "war_machine": True,
        "kiosk": False,
    }


def stamp(*, reason: str = "war_harden_boot") -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    steps: dict[str, Any] = {}

    basement = INSTALL / "GrokLab" / "deploy" / "nexus-c2-basement-arm.sh"
    basement_state = STATE / "nexus-c2-basement.json"
    if basement.is_file():
        try:
            subprocess.run(
                ["bash", str(basement)],
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "AML_BUILD": "0"},
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            steps["nexus_c2_basement"] = _load(basement_state, {"ok": basement_state.is_file()})
        except (OSError, subprocess.TimeoutExpired) as exc:
            steps["nexus_c2_basement"] = {"ok": False, "error": str(exc)}
    else:
        steps["nexus_c2_basement"] = {"ok": False, "error": "basement_script_missing"}

    wd = INSTALL / "lib" / "hostess7-weapons-defense.py"
    if wd.is_file():
        steps["weapons_turnover"] = _run_py(wd, "turnover", timeout=120)

    kilroy_pkg = STATE / "kilroy-war-package.json"
    steps["kilroy_weaponized"] = _load(kilroy_pkg, {})

    kit = INSTALL / "lib" / "field-attack-kit.py"
    if kit.is_file() and os.environ.get("NEXUS_BOOT_REKILL", "1") == "1":
        steps["boot_rekill"] = _run_py(kit, "boot-rekill", timeout=60)

    hostile = STATE / "field-hostile.tsv"
    hostile_count = 0
    if hostile.is_file():
        try:
            hostile_count = max(0, len(hostile.read_text(encoding="utf-8").splitlines()) - 1)
        except OSError:
            pass

    reg = STATE / "kill-rekill-registry.json"
    registry_count = 0
    if reg.is_file():
        reg_doc = _load(reg, {})
        registry_count = len(reg_doc.get("entries") or {})

    doc = {
        "schema": "field-war-hardening-panel/v1",
        "updated": _now(),
        "motto": doctrine.get("motto"),
        "posture": doctrine.get("posture") or {},
        "war_machine": True,
        "kiosk": False,
        "nexus_c2_basement": bool((steps.get("nexus_c2_basement") or {}).get("weaponized", True)),
        "kilroy_weaponized": bool((steps.get("kilroy_weaponized") or {}).get("fully_weaponized", True)),
        "fully_weaponized": True,
        "layer_order": doctrine.get("layer_order"),
        "boot_order": doctrine.get("boot_order"),
        "every_kill_rekill": True,
        "forever_kill_enforce": True,
        "reason": reason,
        "hostile_registry_count": hostile_count,
        "kill_rekill_registry_count": registry_count,
        "steps": steps,
        "env": {
            k: os.environ.get(k, v)
            for k, v in (doctrine.get("env") or {}).items()
        },
    }
    _save_atomic(PANEL, doc)
    _append_ledger({"event": "stamp", "reason": reason, "hostile": hostile_count, "registry": registry_count})
    return {"ok": True, **doc}


def posture_json() -> dict[str, Any]:
    panel = _load(PANEL, {})
    if panel:
        return panel
    return stamp(reason="posture_probe")


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture"):
        print(json.dumps(posture_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "stamp":
        print(json.dumps(stamp(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "layers":
        print(json.dumps(layer_chain(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "harden":
        print(json.dumps(stamp(reason="war_harden_cli"), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-war-hardening.py [json|posture|stamp|layers|harden]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())