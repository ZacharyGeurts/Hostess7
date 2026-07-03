#!/usr/bin/env python3
"""Arcade Battalion — botnet + QEMU little guys + SAP lobby + layer stack."""
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
DOCTRINE = INSTALL / "data" / "field-arcade-battalion-doctrine.json"
LAYER = INSTALL / "data" / "field-layer-stack-doctrine.json"
PANEL = STATE / "field-arcade-battalion-panel.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_py(rel: str, args: list[str], *, timeout: float = 25.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {}
    try:
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
    except Exception:
        pass
    return {}


def _import_proxy() -> Any | None:
    py = INSTALL / "lib" / "field-queen-world-proxy.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("fqp", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _qemu_witnesses(qemu: dict[str, Any]) -> list[dict[str, Any]]:
    slots = qemu.get("slots") or []
    if slots:
        out = []
        for s in slots:
            if not isinstance(s, dict):
                continue
            slot = int(s.get("slot") or 0)
            tunnel = int(s.get("tunnel") or (19477 + slot))
            out.append({
                "id": f"qemu-world-{slot}",
                "slot": slot,
                "tunnel_port": tunnel,
                "roles": ["sap_relay", "frame_witness"],
                "status": s.get("phase") or s.get("status") or "unknown",
            })
        return out
    target = int(qemu.get("target") or qemu.get("slots_total") or 6)
    completed = int(qemu.get("completed") or 0)
    n = max(target, completed, 1)
    n = min(n, 16)
    return [
        {
            "id": f"qemu-world-{i}",
            "slot": i,
            "tunnel_port": 19477 + i,
            "roles": ["sap_relay", "frame_witness"],
            "status": "active" if i < completed else "pipeline",
        }
        for i in range(n)
    ]


def _sap_sessions(proxy: Any) -> list[dict[str, Any]]:
    if not proxy:
        return []
    doc = proxy.proxy_json_post("/api/sap", {"action": "status"}, timeout=8.0)
    if not doc.get("ok"):
        return []
    out = []
    beacon = doc.get("beacon") or {}
    if beacon.get("sap"):
        out.append({
            "kind": "local_beacon",
            "inbox": doc.get("inbox") or beacon.get("inbox"),
            "world_port": beacon.get("world_port"),
            "active_sessions": doc.get("active_sessions", 0),
        })
    reg = _load(STATE / "field-botnet-registry.json", {})
    for m in reg.get("members") or []:
        g = m.get("gaming") or {}
        if g.get("sap_beacon"):
            out.append({
                "kind": "registry_beacon",
                "member_id": m.get("member_id"),
                "display_name": m.get("display_name"),
                "system": g.get("system"),
                "session_id": g.get("session_id"),
                "world_port": g.get("world_port"),
            })
    return out


def lobby_snapshot(*, write: bool = True) -> dict[str, Any]:
    proxy = _import_proxy()
    qemu = _run_py("lib/qemu-world-status.py", [], timeout=35.0)
    witnesses = _qemu_witnesses(qemu)
    sap_sessions = _sap_sessions(proxy)
    game_room = proxy.proxy_json_post("/api/game-room", {"action": "status"}, timeout=12.0) if proxy else {}
    layer = _load(LAYER, {})
    doctrine = _load(DOCTRINE, {})
    steam = _load(INSTALL / "data" / "field-steam-bridge-doctrine.json", {})

    doc = {
        "ok": True,
        "schema": "field-arcade-battalion/v1",
        "title": doctrine.get("title"),
        "updated": _utc(),
        "layer_stack": {
            "hostess7": (layer.get("hostess7") or {}),
            "layer_3_plus": (layer.get("layer_3_plus") or {}),
            "motto": layer.get("motto"),
        },
        "lobby": {
            "qemu_witnesses": len(witnesses),
            "sap_beacons": len(sap_sessions),
            "game_room_ok": bool(game_room.get("ok")),
            "pump_running": bool(game_room.get("pump_pid") or game_room.get("programs_canvas_ready")),
            "system": game_room.get("system") or game_room.get("system_id"),
        },
        "qemu_witnesses": witnesses,
        "sap_sessions": sap_sessions,
        "game_room": game_room,
        "steam_bridge": {
            "layer": steam.get("layer", 3),
            "enabled": True,
            "third_party": True,
            "motto": steam.get("motto"),
        },
        "hostess7_input": hostess7_input_lane(system=str(game_room.get("system") or "nes")),
        "api": {
            "lobby": "/api/field-arcade-battalion",
            "game_room": "/api/game-room",
            "sap": "/api/sap",
            "everyone": "/api/field-everyone-counter",
        },
    }
    if write:
        _save(PANEL, doc)
    return doc


def publish_sap_beacon(
    *,
    session_id: str,
    token: str,
    system: str,
    display_name: str | None = None,
) -> dict[str, Any]:
    reg_py = INSTALL / "lib" / "field-botnet-registry.py"
    if not reg_py.is_file():
        return {"ok": False, "error": "registry_missing"}
    import subprocess
    body = {
        "action": "register",
        "display_name": display_name or "Arcade Host",
        "region": "local",
        "gaming": {
            "sap_beacon": True,
            "system": system,
            "session_id": session_id,
            "token_hint": token[:8] + "…" if token else None,
            "world_port": int(os.environ.get("QUEEN_WORLD_PORT", "9481")),
            "roles": ["sap_host", "game_room"],
        },
    }
    try:
        proc = subprocess.run(
            [sys.executable, str(reg_py), "dispatch"],
            input=json.dumps(body),
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        out = json.loads(proc.stdout or "{}")
        out["published"] = True
        return out
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}


def hostess7_input_lane(*, system: str = "nes") -> dict[str, Any]:
    """Hostess 7 input training + SAP relay witness for battalion lobby."""
    inp = INSTALL / "lib" / "hostess7-input-training.py"
    if not inp.is_file():
        return {"ok": False, "error": "input_training_missing"}
    try:
        proc = subprocess.run(
            [sys.executable, str(inp), "dispatch", json.dumps({"action": "panel"})],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        panel = json.loads(proc.stdout or "{}")
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:120]}
    relay: dict[str, Any] = {}
    try:
        proc2 = subprocess.run(
            [sys.executable, str(inp), "dispatch", json.dumps({"action": "sap_relay", "system": system})],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        relay = json.loads(proc2.stdout or "{}")
    except Exception:
        pass
    return {
        "ok": bool(panel.get("ok")),
        "hostess7": True,
        "play_ready": panel.get("play_ready"),
        "modalities": panel.get("modalities"),
        "sap_relay": relay,
        "system": system,
    }


def tournament_host(
    *,
    system: str = "nes",
    spawn_rtx: bool = True,
    max_players: int = 4,
) -> dict[str, Any]:
    proxy = _import_proxy()
    if not proxy:
        return {"ok": False, "error": "queen_proxy_missing"}
    launch = proxy.proxy_json_post(
        "/api/game-room",
        {"action": "launch", "system": system, "spawn_rtx": spawn_rtx},
        timeout=90.0,
    )
    host = proxy.proxy_json_post(
        "/api/sap",
        {"action": "host", "system": system, "max_players": max_players},
        timeout=15.0,
    )
    beacon = {}
    if host.get("ok"):
        beacon = publish_sap_beacon(
            session_id=str(host.get("session_id") or ""),
            token=str(host.get("token") or ""),
            system=system,
        )
    h7_lane = hostess7_input_lane(system=system)
    return {
        "ok": bool(launch.get("ok")) and bool(host.get("ok")),
        "tournament": True,
        "system": system,
        "launch": launch,
        "sap_host": host,
        "beacon": beacon,
        "hostess7_input": h7_lane,
        "lobby": lobby_snapshot(write=True).get("lobby"),
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "lobby").strip().lower()
    if action in ("lobby", "status", "json"):
        return lobby_snapshot(write=True)
    if action in ("publish_beacon", "beacon"):
        return publish_sap_beacon(
            session_id=str(body.get("session_id") or ""),
            token=str(body.get("token") or ""),
            system=str(body.get("system") or "nes"),
            display_name=body.get("display_name"),
        )
    if action in ("tournament", "tournament_host", "host_tournament"):
        return tournament_host(
            system=str(body.get("system") or "nes"),
            spawn_rtx=body.get("spawn_rtx", True) is not False,
            max_players=int(body.get("max_players") or 4),
        )
    return {"ok": False, "error": "unknown_action", "actions": ["lobby", "publish_beacon", "tournament"]}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "lobby").strip().lower()
    if cmd in ("lobby", "json", "status"):
        print(json.dumps(lobby_snapshot(), indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), indent=2))
        return 0
    print(json.dumps(dispatch({"action": cmd, **dict(os.environ)}), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())