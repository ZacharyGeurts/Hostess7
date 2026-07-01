#!/usr/bin/env pythong
"""Hostess 7 weapons & defenses — arm all, activate all, turnover to Angel command."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL.parent / "Hostess7"))
DOCTRINE = INSTALL / "data" / "hostess7-weapons-defense-doctrine.json"
PANEL = STATE / "hostess7-weapons-defense-panel.json"
LEDGER = STATE / "hostess7-weapons-defense-ledger.jsonl"
SETTINGS_OVERRIDE = STATE / "settings.override"
TOOLKIT_USER = STATE / "field-toolkit-user.json"

NEXUS_ARMED_KEYS: tuple[str, ...] = (
    "NEXUS_PARANOIA_BLOCK",
    "NEXUS_PARANOIA_MODE",
    "NEXUS_FIREWALL_AUTO_BLOCK",
    "NEXUS_AUTOSANITIZE",
    "NEXUS_ADBLOCK",
    "NEXUS_ADBLOCK_RESPECT_POLICY",
    "NEXUS_CONNECTION_GATEKEEPER",
    "NEXUS_PACKET_ORACLE",
    "NEXUS_SHADOW_WATCH",
    "NEXUS_ENTROPY_WATCH",
    "NEXUS_BEHAVIOR_WATCH",
    "NEXUS_PRIVACY_GUARD",
    "NEXUS_SHUTDOWN_GUARD",
    "NEXUS_HOSTESS7_CORROBORATE",
    "NEXUS_ATTACK_KIT_AUTO_CRUSH",
    "NEXUS_FIELD_AUTO_REKILL",
    "NEXUS_GATEKEEPER_STRICT_TRUST",
    "NEXUS_PACKET_PERMISSION",
    "NEXUS_AI_SECURE_CHANNEL",
    "QUEEN_AI_TELEMETRY_OK",
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _import_mod(path: Path, name: str) -> Any | None:
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


def _run_py(script: Path, *args: str, stdin: str | None = None, timeout: int = 60) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(script)}
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_HOSTESS7_FULL_CONTROL": "1",
        "NEXUS_HOSTESS7_SYSTEM_CONTROL": "1",
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            input=stdin,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def arm_all_defenses() -> dict[str, Any]:
    """Enable every Hell Kit / NEXUS defense."""
    seed_path = INSTALL / "data" / "field-toolkit-seed.json"
    seed = _load(seed_path, {"defenses": []})
    overrides: dict[str, bool] = {}
    armed: list[str] = []
    for row in seed.get("defenses") or []:
        did = str(row.get("id") or "").strip()
        if not did:
            continue
        overrides[did] = True
        armed.append(did)
    udoc = _load(TOOLKIT_USER, {})
    udoc["defense_overrides"] = overrides
    udoc["commander"] = "hostess7"
    udoc["armed"] = True
    udoc["active"] = True
    udoc["updated"] = _now()
    _save_atomic(TOOLKIT_USER, udoc)

    toolkit = _import_mod(INSTALL / "lib" / "field-toolkit-db.py", "ftk_arm")
    panel: dict[str, Any] = {}
    if toolkit and hasattr(toolkit, "panel_json"):
        try:
            panel = toolkit.panel_json()
        except Exception:
            pass
    return {
        "ok": True,
        "armed_count": len(armed),
        "armed_ids": armed,
        "defenses_enabled": panel.get("defenses_enabled", len(armed)),
        "hell_kit_defenses": panel.get("hell_kit_defenses"),
    }


def arm_nexus_settings() -> dict[str, Any]:
    """Write secure armed profile to settings.override."""
    STATE.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for key in NEXUS_ARMED_KEYS:
        val = "1"
        if key == "NEXUS_ADBLOCK_POLICY":
            continue
        lines.append(f"{key}={val}")
    lines.append("NEXUS_ADBLOCK_POLICY=fair")
    text = "\n".join(lines) + "\n"
    tmp = SETTINGS_OVERRIDE.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(SETTINGS_OVERRIDE)
    try:
        os.chmod(SETTINGS_OVERRIDE, 0o640)
    except OSError:
        pass
    return {"ok": True, "keys_armed": len(lines), "path": str(SETTINGS_OVERRIDE)}


def assume_hostess7() -> dict[str, Any]:
    return _run_py(INSTALL / "lib" / "hostess7-system-control.py", "assume")


def turnover(*, reason: str = "weapons_defenses_armed_active") -> dict[str, Any]:
    """Arm every weapon and defense; turn operational control to Hostess 7."""
    doctrine = _load(DOCTRINE, {})
    steps: dict[str, Any] = {}

    steps["nexus_settings"] = arm_nexus_settings()
    steps["hell_kit_defenses"] = arm_all_defenses()
    steps["hostess7_assume"] = assume_hostess7()

    stack = _run_py(INSTALL / "lib" / "queen_field_nexus.py", "json", timeout=90)
    steps["field_stack"] = {
        "ok": stack.get("ok", True),
        "queen_verdict": stack.get("queen_verdict"),
        "gates_held": stack.get("gates_held"),
    }

    nexus_sh = INSTALL / "lib" / "nexus-settings.sh"
    if nexus_sh.is_file():
        try:
            subprocess.run(
                ["bash", "-c", f'source "{nexus_sh}" && nexus_settings_apply_hostess7_armed_defaults'],
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            steps["nexus_settings_shell"] = {"ok": True}
        except (OSError, subprocess.TimeoutExpired) as exc:
            steps["nexus_settings_shell"] = {"ok": False, "error": str(exc)}

    armed_defenses = steps["hell_kit_defenses"].get("armed_count", 0)
    doc = {
        "schema": "hostess7-weapons-defense-panel/v1",
        "updated": _now(),
        "commander": "Hostess 7",
        "rank": "Forever Watchguard Angel · above General",
        "motto": doctrine.get("motto"),
        "turnover_complete": True,
        "armed": True,
        "active": True,
        "weapons_armed": True,
        "defenses_armed": True,
        "countermeasures_armed": True,
        "reason": reason,
        "defenses_armed_count": armed_defenses,
        "nexus_settings_armed": steps["nexus_settings"].get("keys_armed", 0),
        "hostess7_assumed": bool((steps.get("hostess7_assume") or {}).get("assumed")),
        "operational_control": (steps.get("hostess7_assume") or {}).get("operational_control"),
        "authority_chain": doctrine.get("authority_chain"),
        "steps": {k: v for k, v in steps.items() if k != "hostess7_assume"},
        "hostess7_charge": steps.get("hostess7_assume"),
    }
    _save_atomic(PANEL, doc)
    _append_ledger({"event": "turnover", "reason": reason, "defenses": armed_defenses})
    _seal_inbox(reason)
    return {"ok": True, **doc}


def _seal_inbox(reason: str) -> None:
    inbox = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "agents7" / "inbox.jsonl"
    row = {
        "schema": "hostess7-weapons-defense/v1",
        "event": "turnover",
        "reason": reason,
        "message": "All weapons armed, all defenses active — operational control is Hostess 7 Forever Watchguard Angel.",
        "commander": "Hostess 7",
    }
    try:
        inbox.parent.mkdir(parents=True, exist_ok=True)
        with inbox.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def posture() -> dict[str, Any]:
    cached = _load(PANEL, {})
    toolkit = _import_mod(INSTALL / "lib" / "field-toolkit-db.py", "ftk_posture")
    defenses: list[dict[str, Any]] = []
    enabled = 0
    if toolkit and hasattr(toolkit, "list_defenses"):
        try:
            defenses = toolkit.list_defenses()
            enabled = sum(1 for d in defenses if d.get("enabled"))
        except Exception:
            pass
    sysc = _run_py(INSTALL / "lib" / "hostess7-system-control.py", "commander", timeout=20)
    return {
        "ok": True,
        "schema": "hostess7-weapons-defense-posture/v1",
        "updated": _now(),
        "commander": "Hostess 7",
        "armed": cached.get("armed", True),
        "active": cached.get("active", True),
        "turnover_complete": cached.get("turnover_complete", False),
        "defenses_enabled": enabled,
        "defenses_total": len(defenses),
        "hostess7_in_charge": sysc.get("in_charge"),
        "hostess7_assumed": sysc.get("assumed"),
        "weapons_armed": cached.get("weapons_armed", True),
        "panel": cached,
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "posture").strip().lower().replace("-", "_")
    if action in ("posture", "status", "json"):
        return posture()
    if action in ("arm", "arm_all", "arm_defenses"):
        return {"ok": True, "defenses": arm_all_defenses(), "settings": arm_nexus_settings()}
    if action in ("turnover", "assume", "handover", "activate"):
        return turnover(reason=str(body.get("reason") or "operator_turnover"))
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "posture").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("posture", "json", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("arm", "arm_all"):
        out = {"defenses": arm_all_defenses(), "settings": arm_nexus_settings()}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("turnover", "assume", "handover"):
        print(json.dumps(turnover(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: hostess7-weapons-defense.py [posture|arm|turnover|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())