#!/usr/bin/env pythong
"""Queen root-threats slice — fast status for modern UI (no publish storm)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))
_LIB = Path(__file__).resolve().parent
PANEL_PORT = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _count_tsv_rows(path: Path) -> int:
    if not path.is_file():
        return 0
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return max(0, len(lines) - 1)
    except OSError:
        return 0


def _root_sovereign_fast() -> dict[str, Any]:
    panel = _load(STATE / "root-sovereign-panel.json")
    covenant = _load(STATE / "root-sovereign-covenant.json")
    kills = 0
    kill_log = STATE / "root-sovereign-kills.jsonl"
    if kill_log.is_file():
        try:
            kills = sum(1 for _ in kill_log.open(encoding="utf-8", errors="replace"))
        except OSError:
            kills = 0
    guard_pid = STATE / "root-sovereign-guard.pid"
    guard_live = False
    if guard_pid.is_file():
        try:
            pid = int(guard_pid.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            guard_live = True
        except (OSError, ValueError):
            guard_live = False
    return {
        "schema": "root-sovereign-fast/v1",
        "guard_live": guard_live,
        "covenant_sealed": bool(covenant.get("sealed") or covenant.get("operator_uid")),
        "operator": covenant.get("operator") or panel.get("operator"),
        "kills_total": kills,
        "kill_policy": panel.get("kill_policy") or "prejudice",
        "last_audit": panel.get("updated") or panel.get("last_audit"),
        "verdict": "ARMED" if guard_live and covenant else "STANDBY",
    }


def _attack_kit_fast() -> dict[str, Any]:
    hostile = _count_tsv_rows(STATE / "field-hostile.tsv")
    nokill = _count_tsv_rows(STATE / "field-nokill.tsv")
    rekill = _load(STATE / "auto-rekill-log.json", {})
    host_attacks = _load(STATE / "host-attacks.json", {})
    points = host_attacks.get("points") or host_attacks.get("hosts") or []
    if isinstance(points, dict):
        points = list(points.values())
    return {
        "schema": "attack-kit-fast/v1",
        "hostile_disabled": hostile,
        "nokill_whitelist": nokill,
        "map_targets": len(points) if isinstance(points, list) else 0,
        "autokill_armed": True,
        "rekill_cycle": rekill.get("last_cycle") or rekill.get("updated"),
        "rekill_hits": rekill.get("hits") or rekill.get("count") or 0,
        "ops": ["AUTOKILL", "RE-KILL", "KILL", "NO-KILL", "CRUSH-HOT"],
    }


def _threat_vectors_fast() -> dict[str, Any]:
    tsv = STATE / "threat-vectors.tsv"
    count = _count_tsv_rows(tsv)
    recent: list[str] = []
    if tsv.is_file():
        try:
            for line in tsv.read_text(encoding="utf-8", errors="replace").splitlines()[1:6]:
                parts = line.split("\t")
                if parts:
                    recent.append(parts[0])
        except OSError:
            pass
    return {
        "schema": "threat-vectors-fast/v1",
        "catalog_size": count,
        "recent": recent,
    }


def _field_virus_fast() -> dict[str, Any]:
    panel = _load(STATE / "field-virus-panel.json")
    return {
        "schema": "field-virus-fast/v1",
        "verdict": panel.get("verdict") or "WATCH",
        "scanned": panel.get("scanned") or 0,
        "quarantine": panel.get("quarantine") or 0,
    }


def root_threats_status(*, full: bool = False) -> dict[str, Any]:
    doc = {
        "schema": "queen-root-threats/v1",
        "updated": _ts(),
        "ok": True,
        "nexus_panel": f"http://127.0.0.1:{PANEL_PORT}/field",
        "root_sovereign": _root_sovereign_fast(),
        "attack_kit": _attack_kit_fast(),
        "threat_vectors": _threat_vectors_fast(),
        "field_virus": _field_virus_fast(),
        "kill_chain": {
            "autokill": "armed",
            "rekill": "armed",
            "root_guard": _root_sovereign_fast().get("verdict", "STANDBY"),
        },
    }
    if full:
        try:
            proc = subprocess.run(
                [sys.executable, str(_LIB / "queen-root-sovereign.py"), "json"],
                capture_output=True, text=True, timeout=12,
                env={**os.environ, "QUEEN_ROOT": str(QUEEN), "NEXUS_STATE_DIR": str(STATE)},
            )
            if proc.returncode == 0 and proc.stdout.strip():
                doc["root_sovereign_full"] = json.loads(proc.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            pass
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        return {"ok": True, **root_threats_status(full=bool(body.get("full")))}
    if action == "audit_root":
        proc = subprocess.run(
            [sys.executable, str(_LIB / "queen-root-sovereign.py"), "audit"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "NEXUS_STATE_DIR": str(STATE)},
        )
        try:
            audit = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            audit = {"ok": False, "tail": (proc.stdout or "")[-800:]}
        return {"ok": proc.returncode == 0, "audit": audit, "updated": _ts()}
    if action == "rekill":
        kit = INSTALL / "lib" / "field-attack-kit.py"
        if not kit.is_file():
            kit = SG / "NewLatest" / "lib" / "field-attack-kit.py"
        proc = subprocess.run(
            [sys.executable, str(kit), "rekill"],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
        )
        try:
            out = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            out = {"ok": False, "tail": (proc.stdout or "")[-800:]}
        return {"ok": proc.returncode == 0, **out, "updated": _ts()}
    if action in ("crush_hot", "crushhot"):
        kit = INSTALL / "lib" / "field-attack-kit.py"
        if not kit.is_file():
            kit = SG / "NewLatest" / "lib" / "field-attack-kit.py"
        proc = subprocess.run(
            [sys.executable, str(kit), "crush-hot"],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)},
        )
        try:
            out = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            out = {"ok": False, "tail": (proc.stdout or "")[-800:]}
        return {"ok": proc.returncode == 0, **out, "updated": _ts()}
    return {"ok": False, "error": "unknown_action", "actions": ["status", "audit_root", "rekill", "crush_hot"]}


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] in ("json", "status"):
        print(json.dumps(root_threats_status(), ensure_ascii=False))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(root_threats_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())