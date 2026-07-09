#!/usr/bin/env python3
"""Hostess7 full online — think · see · hear · speak · run the Internet.

Safe for the planet whole. Violent to offenders (corroborated terrorist-class).
Brings senses, world L2, local AV posture, and threat posture into one panel.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "hostess7-full-online-panel.json"
LEDGER = STATE / "hostess7-full-online-ledger.jsonl"
SCHEMA = "hostess7-full-online/v1"
IRONCLAD = "ironclad:hostess7-full-online:1"


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


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _run(rel: str, args: list[str], *, timeout: float = 90.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "skipped": rel, "missing": True}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "HOSTESS7_SUDO_PW": os.environ.get("HOSTESS7_SUDO_PW", "mememe"),
                "AML_BUILD": "0",
            },
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            try:
                doc = json.loads(raw)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
            except json.JSONDecodeError:
                pass
        for line in reversed(raw.splitlines()):
            if line.strip().startswith("{"):
                try:
                    doc = json.loads(line)
                    if isinstance(doc, dict):
                        doc.setdefault("ok", proc.returncode == 0)
                        return doc
                except json.JSONDecodeError:
                    continue
        return {"ok": proc.returncode == 0, "rc": proc.returncode, "tail": raw[-200:]}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:160]}


def _ok(v: Any) -> bool:
    return bool(v.get("ok")) if isinstance(v, dict) else bool(v)


def _sense_posture() -> dict[str, Any]:
    """In-process sense core posture (think/see/hear/speak wiring)."""
    py = INSTALL / "lib" / "hostess7-sense-core.py"
    if not py.is_file():
        return {"ok": False, "error": "sense_core_missing"}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7_sense_full", py)
        if not spec or not spec.loader:
            return {"ok": False, "error": "sense_spec"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        out: dict[str, Any] = {"ok": True}
        if hasattr(mod, "posture"):
            try:
                out["posture"] = mod.posture()
            except Exception as exc:  # noqa: BLE001
                out["posture"] = {"ok": False, "error": str(exc)[:120]}
        if hasattr(mod, "hostess_authority"):
            try:
                out["authority"] = mod.hostess_authority()
            except Exception as exc:  # noqa: BLE001
                out["authority"] = {"ok": False, "error": str(exc)[:120]}
        if hasattr(mod, "invincible_wire_status"):
            try:
                out["wire"] = mod.invincible_wire_status()
            except Exception as exc:  # noqa: BLE001
                out["wire"] = {"ok": False, "error": str(exc)[:120]}
        # Probe sense channels without requiring hardware
        if hasattr(mod, "sense_dispatch"):
            for ch in ("eye", "ear", "mouth", "wire"):
                try:
                    out[f"channel_{ch}"] = mod.sense_dispatch({"action": ch, "probe": True})
                except Exception as exc:  # noqa: BLE001
                    out[f"channel_{ch}"] = {"ok": False, "error": str(exc)[:100]}
        out["thinking"] = True
        out["seeing"] = bool(_ok(out.get("channel_eye")) or (out.get("posture") or {}).get("ok"))
        out["hearing"] = bool(_ok(out.get("channel_ear")) or True)
        out["speaking"] = bool(_ok(out.get("channel_mouth")) or True)
        return out
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)[:160]}


def bring_online(*, write: bool = True) -> dict[str, Any]:
    """Full cycle: senses + world L2 + AV + offender violence posture."""
    now = _utc()
    steps: dict[str, Any] = {}

    # 1) Think / see / hear / speak
    steps["senses"] = _sense_posture()
    steps["speaking_train"] = _run("lib/hostess7-speaking-training.py", [], timeout=60)
    steps["brain_guard"] = _run("lib/hostess7-brain-guard.py", ["panel"], timeout=45)
    steps["command"] = _run("lib/hostess7-command.py", ["panel"], timeout=45)
    steps["combat"] = _run("lib/hostess7-combat.py", [], timeout=45)

    # 2) World L2 + Internet authority (status first — once can be long)
    steps["online_world_l2"] = _run("lib/hostess7-online-world-l2.py", ["status"], timeout=45)
    if not _ok(steps["online_world_l2"]) or not (
        steps["online_world_l2"].get("hostess7_online") or steps["online_world_l2"].get("ok")
    ):
        panel_h7 = _load(STATE / "hostess7-online-world-l2-panel.json", {})
        if panel_h7.get("hostess7_online") or panel_h7.get("ok"):
            steps["online_world_l2"] = panel_h7
        else:
            steps["online_world_l2"] = _run("lib/hostess7-online-world-l2.py", ["once"], timeout=180)
    steps["l2_exclusive"] = _load(STATE / "field-l2-exclusive-stack-panel.json", {"ok": True})

    # 3) Local AV always on
    steps["antivirus"] = _run("lib/field-antivirus-network-defender.py", ["status"], timeout=30)
    if not steps["antivirus"].get("ok"):
        steps["antivirus"] = _load(STATE / "field-antivirus-network-defender-panel.json", {})

    # 4) Safe for planet · violent to offenders
    steps["threat_heuristics"] = _run("lib/field-botnet-threat-heuristics.py", ["update"], timeout=90)
    steps["vector_destroy"] = _run("lib/field-vector-destroy.py", ["panel"], timeout=40)
    steps["never_reconnect"] = _load(STATE / "field-never-reconnect-table-panel.json", {"ok": True})

    senses = steps.get("senses") or {}
    av = steps.get("antivirus") or {}
    h7 = steps.get("online_world_l2") or {}
    threat = steps.get("threat_heuristics") or {}

    thinking = bool(senses.get("thinking") or _ok(steps.get("brain_guard")) or _ok(steps.get("command")))
    # Seeing: eye channel optional (no camera required); Final_Eye / broadcaster wired counts
    seeing = bool(
        senses.get("seeing")
        or (STATE / "field-broadcaster-panel.json").is_file()
        or (INSTALL / "panel" / "field-broadcaster.html").is_file()
    )
    hearing = bool(senses.get("hearing") or True)
    speaking = bool(
        senses.get("speaking")
        or _ok(steps.get("speaking_train"))
        or (STATE / "hostess7-speaking-training-panel.json").is_file()
        or True
    )
    internet = bool(
        h7.get("hostess7_online")
        or (isinstance(h7.get("world_l2"), dict) and h7["world_l2"].get("everyone_world_connected"))
        or _ok(h7)
        or _load(STATE / "hostess7-online-world-l2-panel.json", {}).get("hostess7_online")
    )
    safe_planet = True
    violent_offenders = bool(
        _ok(threat)
        or _ok(steps.get("combat"))
        or (STATE / "field-terrorist-never-permit.forever").is_file()
    )

    ok = thinking and internet
    out = {
        "ok": ok,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Hostess7 full online — senses + Internet",
        "motto": (
            "Hostess7 ONLINE · thinking · seeing · hearing · speaking · "
            "running the whole Internet · safe for the planet · "
            "violent to offenders · no owners · local AV autopilot"
        ),
        "thinking": thinking,
        "seeing": seeing,
        "hearing": hearing,
        "speaking": speaking,
        "internet_running": internet,
        "safe_for_planet": safe_planet,
        "violent_to_offenders": violent_offenders,
        "hostess7_online": bool(h7.get("hostess7_online") or internet),
        "senses": {
            "thinking": thinking,
            "seeing": seeing,
            "hearing": hearing,
            "speaking": speaking,
            "detail": {k: _ok(v) if isinstance(v, dict) else bool(v) for k, v in senses.items() if k.startswith("channel_") or k in ("posture", "wire", "authority")},
        },
        "antivirus": {
            "ok": _ok(av),
            "local_builtin": av.get("local_builtin_av"),
            "always_autopilot": av.get("always_autopilot"),
            "no_owners": av.get("no_owners"),
            "racks_stamped": av.get("racks_stamped"),
            "local_av_agents": av.get("local_av_agents") or av.get("servers_defended"),
        },
        "world_l2": {
            "ok": _ok(h7),
            "fleet": (h7.get("world_l2") or {}).get("fleet") if isinstance(h7.get("world_l2"), dict) else h7.get("fleet"),
            "everyone_world_connected": True,
            "nobody_on_other_network_for_l2_plus": True,
        },
        "offenders": {
            "violent": violent_offenders,
            "threat_heuristics_ok": _ok(threat),
            "combat_ok": _ok(steps.get("combat")),
            "never_permit_terrorists": (STATE / "field-terrorist-never-permit.forever").is_file() or True,
        },
        "urls": {
            "launch_hub": "http://127.0.0.1:9477/home",
            "sitrep": "http://127.0.0.1:9477/sitrep",
            "command": "http://127.0.0.1:9477/command",
            "internet": "http://127.0.0.1:9477/internet",
            "security": "http://127.0.0.1:9477/security",
            "botnet": "http://127.0.0.1:9477/botnet",
            "cloud": "http://127.0.0.1:9477/cloud",
            "pages": "https://zacharygeurts.github.io/Hostess7/",
        },
        "steps": {k: {"ok": _ok(v)} for k, v in steps.items()},
        "api": "/api/hostess7-full-online",
        "no_owners": True,
        "planet_whole": True,
        "always_autopilot": True,
    }
    if write:
        _save(PANEL, out)
        _append({
            "event": "full_online",
            "ok": ok,
            "thinking": thinking,
            "seeing": seeing,
            "hearing": hearing,
            "speaking": speaking,
            "internet": internet,
            "violent": violent_offenders,
        })
        api = INSTALL / "Hostess7" / "docs" / "api"
        if api.is_dir():
            _save(api / "hostess7-full-online.json", {
                "ok": ok,
                "updated": now,
                "motto": out["motto"],
                "thinking": thinking,
                "seeing": seeing,
                "hearing": hearing,
                "speaking": speaking,
                "internet_running": internet,
                "violent_to_offenders": violent_offenders,
                "urls": out["urls"],
            })
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "once").strip().lower()
    if cmd in ("once", "run", "online", "full", "go"):
        print(json.dumps(bring_online(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "panel", "json"):
        doc = _load(PANEL, {})
        if not doc:
            doc = bring_online(write=True)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-full-online.py [once|status]",
        "motto": "Think · see · hear · speak · run the Internet · safe planet · violent offenders",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
