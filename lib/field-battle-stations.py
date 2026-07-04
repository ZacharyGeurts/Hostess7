#!/usr/bin/env pythong
"""Battle Stations — general quarters everywhere (Pages, panel, loopback)."""
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
DOCTRINE = INSTALL / "data" / "field-battle-stations-doctrine.json"
DESKTOP_DOCTRINE = INSTALL / "data" / "field-host-desktop-doctrine.json"
PANEL = STATE / "field-battle-stations-panel.json"
SIGNAL = STATE / "field-battle-stations.signal"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _env_on() -> bool | None:
    raw = os.environ.get("HOSTESS7_BATTLE_STATIONS", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if raw in ("1", "true", "yes", "on"):
        return True
    return None


def battle_stations_enabled() -> bool:
    env = _env_on()
    if env is not None:
        return env
    if SIGNAL.is_file():
        sig = _load(SIGNAL, {})
        if sig.get("enabled") is False:
            return False
        if sig.get("enabled") is True:
            return True
    doc = _load(DOCTRINE, {})
    return bool(doc.get("enabled", True))


def battle_stations_policy() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    base = dict(doc.get("policy") or {})
    if not battle_stations_enabled():
        return {"battle_stations": False, "six_tool_wall": False, "six_tool_wall_on_boot": False}
    base.setdefault("battle_stations", True)
    base.setdefault("six_tool_wall", True)
    base.setdefault("six_tool_wall_on_boot", True)
    return base


def merge_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    out = dict(policy or {})
    if battle_stations_enabled():
        out.update(battle_stations_policy())
    else:
        out["battle_stations"] = False
    return out


def _run_py(rel: str, *args: str, timeout: int = 120) -> dict[str, Any]:
    script = INSTALL / rel
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(rel)}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    doc = _load(DOCTRINE, {})
    for k, v in (doc.get("env") or {}).items():
        env.setdefault(str(k), str(v))
    env["HOSTESS7_BATTLE_STATIONS"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return {"ok": proc.returncode == 0, "stderr": proc.stderr[:400]}
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def stamp(*, reason: str = "battle_stations_on") -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    enabled = battle_stations_enabled()
    steps: dict[str, Any] = {}

    if enabled:
        steps["war_harden"] = _run_py("lib/field-war-hardening.py", "harden")
        alert = INSTALL / "Hostess7" / "scripts" / "field_alert_posture.py"
        if alert.is_file():
            steps["alert_posture"] = _run_py("Hostess7/scripts/field_alert_posture.py", "on")
        _save(SIGNAL, {"enabled": True, "ts": _utc(), "reason": reason})
    else:
        _save(SIGNAL, {"enabled": False, "ts": _utc(), "reason": reason})

    panel = {
        "ok": True,
        "schema": "field-battle-stations-panel/v1",
        "updated": _utc(),
        "enabled": enabled,
        "everywhere": bool(doc.get("everywhere", True)),
        "motto": doc.get("motto"),
        "policy": battle_stations_policy(),
        "reason": reason,
        "steps": steps,
        "posture": "battle-stations" if enabled else "stand-down",
    }
    _save(PANEL, panel)
    return panel


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "panel"):
        if not PANEL.is_file():
            print(json.dumps(stamp(reason="status_probe"), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(_load(PANEL, {}), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("on", "enable", "arm"):
        os.environ["HOSTESS7_BATTLE_STATIONS"] = "1"
        print(json.dumps(stamp(reason="battle_stations_on"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("off", "disable", "stand-down"):
        os.environ["HOSTESS7_BATTLE_STATIONS"] = "0"
        print(json.dumps(stamp(reason="battle_stations_off"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "stamp":
        print(json.dumps(stamp(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "policy":
        print(json.dumps(battle_stations_policy(), ensure_ascii=False, indent=2))
        return 0
    print("usage: field-battle-stations.py [on|off|json|stamp|policy]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())