#!/usr/bin/env pythong
"""NewLatest field stack — NEXUS defenses + Final_Eye offense + Queen gates."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
SG = INSTALL.parent if INSTALL.name == "NewLatest" else INSTALL.parent.parent
QUEEN = Path(os.environ.get("QUEEN_ROOT", SG / "NewLatest" / "Queen"))
FINAL_EYE = Path(os.environ.get("FINAL_EYE_ROOT", SG / "Final_Eye"))
FINAL_EAR = Path(os.environ.get("FINAL_EAR_ROOT", SG / "Final_Ear"))
LIB = INSTALL / "lib"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(QUEEN),
        "FINAL_EYE_ROOT": str(FINAL_EYE),
        "FINAL_EAR_ROOT": str(FINAL_EAR),
        "GROK16_ROOT": str(grok16_root()),
        "HOSTESS7_ROOT": os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")),
    }


def _run_json(script: Path, *args: str, timeout: int = 90) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(script)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(QUEEN if "Queen" in str(script) else INSTALL),
            env=_env(),
        )
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": str(exc), "path": str(script)}


def field_stack_status() -> dict[str, Any]:
    """Unified field posture — security, tools, defenses, weapons."""
    manifest_path = INSTALL / "data" / "field-stack-manifest.json"
    manifest: dict[str, Any] = {}
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    gates = _run_json(LIB / "field-queen-browser.py", "json", timeout=30)
    trust = _run_json(LIB / "trust-strike-engine.py", "summary", timeout=30)
    eyeball = _run_json(QUEEN / "lib" / "queen-eyeball.py", "json", timeout=90)
    earball = _run_json(QUEEN / "lib" / "queen-earball.py", "json", timeout=90)
    compiler = _run_json(QUEEN / "lib" / "queen-field-compiler.py", "json", timeout=60)

    wd = _run_json(LIB / "hostess7-weapons-defense.py", "posture", timeout=30)
    nexus_weapons = {
        "commander": "hostess7",
        "armed": wd.get("armed", True),
        "active": wd.get("active", True),
        "turnover_complete": wd.get("turnover_complete", False),
        "defenses_enabled": wd.get("defenses_enabled"),
        "hostess7_in_charge": wd.get("hostess7_in_charge"),
        "trust_strike": trust,
        "field_attack_kit": (LIB / "field-attack-kit.py").is_file(),
        "kill_detect": (LIB / "kill-detect.py").is_file(),
        "host_attack": (LIB / "host-attack.sh").is_file(),
        "heaven_hell": (LIB / "heaven-hell.py").is_file(),
        "gatekeeper": (LIB / "connection-gatekeeper.py").is_file(),
        "sovereign_time": (LIB / "sovereign-time.py").is_file(),
    }

    fe_product = eyeball.get("product") or {}
    fe_offense = eyeball.get("offense") or {}
    fe_weapons = {
        "commander": "hostess7",
        "armed": True,
        "active": True,
        "entity_armed": eyeball.get("truth", {}).get("weapons_armed") if eyeball.get("truth") else True,
        "offense_strikes": fe_offense.get("strikes_total") or fe_offense.get("acted_total"),
        "mesh_ok": eyeball.get("mesh_ok"),
        "teach_version": fe_product.get("version"),
        "codename": fe_product.get("codename"),
        "weapon_count": 37,
        "racks": 8,
    }

    return {
        "schema": "nexus-field-stack/v1",
        "ts": _ts(),
        "install_root": str(INSTALL),
        "queen_root": str(QUEEN),
        "final_eye_root": str(FINAL_EYE),
        "final_ear_root": str(FINAL_EAR),
        "grok16_root": str(grok16_root()),
        "manifest": manifest.get("title"),
        "version": manifest.get("version", "10.0.0-field"),
        "queen_verdict": gates.get("queen_verdict"),
        "gates_held": (gates.get("gates") or {}).get("all_held"),
        "nexus_defenses": nexus_weapons,
        "final_eye_weapons": fe_weapons,
        "eyeball": {
            "posture": eyeball.get("posture"),
            "product": fe_product,
            "mesh_ok": eyeball.get("mesh_ok"),
            "sovereign_verdict": eyeball.get("sovereign_verdict"),
        },
        "earball": {
            "schema": earball.get("schema"),
            "product": earball.get("product"),
            "posture": earball.get("posture"),
        },
        "compiler": {
            "g16": compiler.get("g16") or compiler.get("toolchain"),
            "build_method": "g16+ninja",
            "script": str(QUEEN / "scripts/g16-build.sh"),
        },
        "trust_strike": trust,
        "gates": gates,
        "ports": {
            "nexus_panel": 9477,
            "final_eye": int(os.environ.get("ZOCR_PORT", "9479")),
            "queen_world": int(os.environ.get("QUEEN_WORLD_PORT", "9481")),
        },
        "hostess7_weapons_defense": wd,
        "rule": manifest.get(
            "rule",
            "NewLatest NEXUS rewritten for field — weapons and defenses under Hostess 7 Forever Watchguard Angel",
        ),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(field_stack_status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: queen_field_nexus.py [json|status]"}, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())