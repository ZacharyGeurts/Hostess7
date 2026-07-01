#!/usr/bin/env pythong
"""Sweet Anita Protocol (SAP) — Queen Game Room ↔ Queen Game Room lockstep netplay over HTTP tunnel."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import socket
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
NEXUS = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN.parent))
NEXUS_STATE = Path(os.environ.get("NEXUS_STATE_DIR", NEXUS / ".nexus-state"))
DOCTRINE = QUEEN / "data" / "queen-sap-doctrine.json"
SESSIONS_PATH = NEXUS_STATE / "queen-sap-sessions.json"
INBOX_PATH = NEXUS_STATE / "queen-sap-inbox.jsonl"

_LOCK = threading.Lock()
_QUEUES: dict[str, deque[dict[str, Any]]] = {}
_SESSIONS: dict[str, dict[str, Any]] = {}


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _world_port() -> int:
    try:
        return int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    except ValueError:
        return 9481


def _local_ips() -> set[str]:
    out = {"127.0.0.1", "::1", "localhost"}
    try:
        out.add(socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        out.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return out


def _inbox_id() -> str:
    host = next(iter(_local_ips() - {"localhost", "::1"}), "127.0.0.1")
    return f"sap:{host}:{_world_port()}"


def doctrine() -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    doc.setdefault("schema", "queen-sweet-anita-protocol/v1")
    return doc


def sap_beacon() -> dict[str, Any]:
    """Beacon advertised only by Queen World — peers must match before tunnel."""
    return {
        "sap": True,
        "sap_version": 1,
        "protocol": "queen-sweet-anita-protocol/v1",
        "queen_game_room": True,
        "service": "queen-game-room",
        "world_port": _world_port(),
        "inbox": _inbox_id(),
        "transport": "http_tunnel",
        "lockstep": True,
        "pixel_perfect": True,
        "max_players": 4,
        "updated": _now(),
    }


def _persist_sessions() -> None:
    _save(SESSIONS_PATH, {"updated": _now(), "sessions": _SESSIONS})


def _load_sessions() -> None:
    global _SESSIONS
    doc = _load(SESSIONS_PATH, {})
    raw = doc.get("sessions") or {}
    if isinstance(raw, dict):
        _SESSIONS = {str(k): v for k, v in raw.items() if isinstance(v, dict)}


def _queue_push(tunnel_id: str, msg: dict[str, Any]) -> None:
    with _LOCK:
        q = _QUEUES.setdefault(tunnel_id, deque(maxlen=512))
        q.append(msg)
    try:
        INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
        with INBOX_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"tunnel": tunnel_id, **msg}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _queue_drain(tunnel_id: str, *, limit: int = 32) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with _LOCK:
        q = _QUEUES.get(tunnel_id)
        if not q:
            return out
        while q and len(out) < limit:
            out.append(q.popleft())
    return out


def _parse_remote(target: str) -> tuple[str, int] | None:
    raw = str(target or "").strip()
    if not raw:
        return None
    if "://" in raw:
        raw = raw.split("://", 1)[-1]
    if "/" in raw:
        raw = raw.split("/", 1)[0]
    host = raw
    port = _world_port()
    if ":" in raw:
        host, ps = raw.rsplit(":", 1)
        try:
            port = int(ps)
        except ValueError:
            return None
    host = host.strip("[]").lower()
    if host in _local_ips():
        return None
    return host, port


def _http_post(host: str, port: int, path: str, body: dict[str, Any], *, timeout: float = 4.0) -> dict[str, Any] | None:
    url = f"http://{host}:{port}{path}"
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Queen-SAP/1.0",
            "X-Queen-SAP": "1",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def _fetch_remote_beacon(host: str, port: int) -> dict[str, Any] | None:
    doc = _http_post(host, port, "/api/sap", {"action": "beacon"}, timeout=3.0)
    if not doc or not doc.get("ok"):
        return None
    beacon = doc.get("beacon") or doc
    if not beacon.get("sap") or not beacon.get("queen_game_room"):
        return None
    return beacon


def _validate_peer(beacon: dict[str, Any] | None) -> tuple[bool, str]:
    if not beacon:
        return False, "beacon_missing"
    if not beacon.get("sap"):
        return False, "not_sap_peer"
    if not beacon.get("queen_game_room"):
        return False, "not_queen_game_room"
    if str(beacon.get("service") or "") not in ("queen-game-room", ""):
        return False, "wrong_service"
    return True, "ok"


def sap_status() -> dict[str, Any]:
    _load_sessions()
    doc = doctrine()
    active = sum(1 for s in _SESSIONS.values() if s.get("status") == "open")
    return {
        "schema": "queen-sap-status/v1",
        "ok": True,
        "updated": _now(),
        "abbrev": "SAP",
        "name": doc.get("name") or "Sweet Anita Protocol",
        "motto": doc.get("motto"),
        "beacon": sap_beacon(),
        "inbox": _inbox_id(),
        "active_sessions": active,
        "session_count": len(_SESSIONS),
        "transport": (doc.get("transport") or {}).get("primary") or "http_tunnel",
        "queen_game_room_only": True,
        "pixel_perfect": True,
        "lockstep": True,
        "viewport_profiles": (doc.get("viewport") or {}).get("profiles") or ["mobile", "tablet", "desktop"],
        "api": doc.get("api") or {},
    }


def host_session(
    *,
    system: str = "nes",
    rom_id: str | None = None,
    rom_sha256: str | None = None,
    max_players: int = 4,
    viewport: str = "desktop",
) -> dict[str, Any]:
    _load_sessions()
    token = secrets.token_hex(12)
    session_id = f"sap_{token}"
    host_id = _inbox_id()
    sess = {
        "session_id": session_id,
        "token": token,
        "host_inbox": host_id,
        "status": "open",
        "created": _now(),
        "system": system,
        "rom_id": rom_id,
        "rom_sha256": rom_sha256,
        "frame": 0,
        "max_players": min(4, max(2, int(max_players))),
        "players": [{"id": "host", "inbox": host_id, "role": "host", "viewport": viewport}],
        "lockstep": True,
        "pixel_perfect": True,
    }
    with _LOCK:
        _SESSIONS[session_id] = sess
    _persist_sessions()
    return {
        "ok": True,
        "session_id": session_id,
        "token": token,
        "host_inbox": host_id,
        "invite": f"{host_id}?session={session_id}&token={token}",
        "system": system,
        "message": "SAP session hosted — share host:port + token with friends",
    }


def tunnel_connect(remote: str) -> dict[str, Any]:
    parsed = _parse_remote(remote)
    if not parsed:
        return {"ok": False, "error": "invalid_remote", "hint": "Use host:port of remote Queen World"}
    host, port = parsed
    beacon = _fetch_remote_beacon(host, port)
    ok, reason = _validate_peer(beacon)
    if not ok:
        return {"ok": False, "error": reason, "remote": f"{host}:{port}"}
    session = secrets.token_hex(8)
    return {
        "ok": True,
        "connected": True,
        "remote": f"{host}:{port}",
        "remote_inbox": beacon.get("inbox"),
        "beacon": beacon,
        "local_inbox": _inbox_id(),
        "tunnel_session": session,
        "poll": {"action": "poll", "tunnel_id": _inbox_id()},
        "send": {"action": "send", "to_id": beacon.get("inbox")},
    }


def join_session(
    *,
    remote: str,
    session_id: str,
    token: str,
    viewport: str = "desktop",
    player_name: str = "guest",
) -> dict[str, Any]:
    conn = tunnel_connect(remote)
    if not conn.get("ok"):
        return conn
    host, port = _parse_remote(remote) or ("", 0)
    join_body = {
        "action": "deliver",
        "tunnel_id": conn.get("remote_inbox"),
        "from_id": _inbox_id(),
        "payload": {
            "type": "sap_join",
            "session_id": session_id,
            "token": token,
            "player": {"name": player_name, "inbox": _inbox_id(), "viewport": viewport},
        },
    }
    relay = _http_post(host, port, "/api/sap", join_body)
    if not relay or not relay.get("ok"):
        return {"ok": False, "error": "join_relay_failed", "connect": conn}
    return {
        "ok": True,
        "joined": True,
        "session_id": session_id,
        "remote": f"{host}:{port}",
        "local_inbox": _inbox_id(),
        "connect": conn,
        "message": "Join request sent — host acknowledges on next lockstep frame",
    }


def deliver(from_id: str, tunnel_id: str, payload: Any) -> dict[str, Any]:
    if not tunnel_id:
        return {"ok": False, "error": "tunnel_id_required"}
    msg = {"from": from_id or _inbox_id(), "to": tunnel_id, "payload": payload, "ts": time.time(), "sap": True}
    _queue_push(tunnel_id, msg)
    if isinstance(payload, dict) and payload.get("type") == "sap_join":
        sid = str(payload.get("session_id") or "")
        tok = str(payload.get("token") or "")
        _load_sessions()
        sess = _SESSIONS.get(sid)
        if sess and sess.get("token") == tok and sess.get("status") == "open":
            players = list(sess.get("players") or [])
            if len(players) < int(sess.get("max_players") or 4):
                player = payload.get("player") or {}
                players.append({
                    "id": f"p{len(players)}",
                    "inbox": player.get("inbox"),
                    "name": player.get("name") or "guest",
                    "role": "guest",
                    "viewport": player.get("viewport") or "desktop",
                })
                sess["players"] = players
                _SESSIONS[sid] = sess
                _persist_sessions()
                if player.get("inbox"):
                    _queue_push(str(player["inbox"]), {
                        "from": _inbox_id(),
                        "to": player["inbox"],
                        "payload": {"type": "sap_join_ack", "session_id": sid, "frame": sess.get("frame", 0)},
                        "ts": time.time(),
                        "sap": True,
                    })
    return {"ok": True, "delivered": True}


def poll(tunnel_id: str | None = None, *, timeout_ms: int = 2000) -> dict[str, Any]:
    tid = tunnel_id or _inbox_id()
    deadline = time.monotonic() + max(0.15, timeout_ms / 1000.0)
    while time.monotonic() < deadline:
        msgs = _queue_drain(tid)
        if msgs:
            return {"ok": True, "tunnel_id": tid, "messages": msgs}
        time.sleep(0.05)
    return {"ok": True, "tunnel_id": tid, "messages": []}


def send(to_id: str, payload: Any, *, from_id: str | None = None) -> dict[str, Any]:
    if not to_id:
        return {"ok": False, "error": "to_id_required"}
    parsed = _parse_remote(to_id)
    if parsed:
        host, port = parsed
        beacon = _fetch_remote_beacon(host, port)
        ok, reason = _validate_peer(beacon)
        if not ok:
            return {"ok": False, "error": reason}
        inbox = beacon.get("inbox") or to_id
        relay = _http_post(host, port, "/api/sap", {
            "action": "deliver",
            "from_id": from_id or _inbox_id(),
            "tunnel_id": inbox,
            "payload": payload,
        })
        if not relay or not relay.get("ok"):
            return {"ok": False, "error": "remote_deliver_failed"}
        return {"ok": True, "sent": True, "relayed": True, "remote_inbox": inbox}
    _queue_push(to_id, {
        "from": from_id or _inbox_id(),
        "to": to_id,
        "payload": payload,
        "ts": time.time(),
        "sap": True,
    })
    return {"ok": True, "sent": True, "relayed": False}


def sync_frame(
    session_id: str,
    *,
    frame: int | None = None,
    inputs: dict[str, Any] | None = None,
    fb_hash: str | None = None,
) -> dict[str, Any]:
    _load_sessions()
    sess = _SESSIONS.get(session_id)
    if not sess:
        return {"ok": False, "error": "session_not_found"}
    cur = int(sess.get("frame") or 0)
    nxt = int(frame) if frame is not None else cur + 1
    sess["frame"] = nxt
    sess["updated"] = _now()
    if inputs:
        hist = sess.setdefault("input_history", {})
        hist[str(nxt)] = inputs
    if fb_hash:
        sess.setdefault("fb_hashes", {})[str(nxt)] = fb_hash
    _SESSIONS[session_id] = sess
    _persist_sessions()
    drift = False
    if fb_hash and sess.get("fb_hashes"):
        vals = list(sess["fb_hashes"].values())
        if len(vals) >= 2 and len(set(vals[-2:])) > 1:
            drift = True
    for p in sess.get("players") or []:
        inbox = p.get("inbox")
        if inbox and inbox != _inbox_id():
            _queue_push(str(inbox), {
                "from": _inbox_id(),
                "to": inbox,
                "payload": {
                    "type": "sap_frame",
                    "session_id": session_id,
                    "frame": nxt,
                    "inputs": inputs or {},
                    "fb_hash": fb_hash,
                    "pixel_perfect": True,
                },
                "ts": time.time(),
                "sap": True,
            })
    return {
        "ok": True,
        "session_id": session_id,
        "frame": nxt,
        "lockstep": True,
        "drift_detected": drift,
        "players": len(sess.get("players") or []),
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json", "beacon"):
        out = sap_status()
        if action == "beacon":
            return {"ok": True, "beacon": out["beacon"]}
        return out
    if action in ("host", "create"):
        return host_session(
            system=str(body.get("system") or "nes"),
            rom_id=body.get("rom_id") or body.get("nes_id"),
            rom_sha256=body.get("rom_sha256"),
            max_players=int(body.get("max_players") or 4),
            viewport=str(body.get("viewport") or "desktop"),
        )
    if action in ("connect", "tunnel_connect"):
        return tunnel_connect(str(body.get("remote") or body.get("host") or ""))
    if action == "join":
        return join_session(
            remote=str(body.get("remote") or body.get("host") or ""),
            session_id=str(body.get("session_id") or ""),
            token=str(body.get("token") or ""),
            viewport=str(body.get("viewport") or "desktop"),
            player_name=str(body.get("player_name") or body.get("name") or "guest"),
        )
    if action in ("deliver", "tunnel_deliver"):
        return deliver(
            str(body.get("from_id") or _inbox_id()),
            str(body.get("tunnel_id") or body.get("to_id") or ""),
            body.get("payload"),
        )
    if action == "poll":
        return poll(body.get("tunnel_id"), timeout_ms=int(body.get("timeout_ms") or 2000))
    if action == "send":
        return send(str(body.get("to_id") or ""), body.get("payload"), from_id=body.get("from_id"))
    if action in ("sync", "frame", "lockstep"):
        return sync_frame(
            str(body.get("session_id") or ""),
            frame=body.get("frame"),
            inputs=body.get("inputs"),
            fb_hash=body.get("fb_hash"),
        )
    return {"ok": False, "error": "unknown_action", "actions": ["status", "host", "join", "connect", "poll", "send", "sync", "deliver"]}


def main() -> int:
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps(sap_status(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())