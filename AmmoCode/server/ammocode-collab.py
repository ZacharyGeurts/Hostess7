#!/usr/bin/env python3
"""AmmoCode 2027 collab hub — invite-only WebSocket, IP friends, voice signaling."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import secrets
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "server"))

from ddos_guard import DdosGuard  # noqa: E402

try:
    import ammocode_security_manage as sec_mgr  # noqa: E402
except ImportError:
    sec_mgr = None  # type: ignore

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    print("pip install websockets", file=sys.stderr)
    raise

COLLAB_PORT = int(os.environ.get("AMMOCODE_COLLAB_PORT", "9556"))
COLLAB_HOST = os.environ.get("AMMOCODE_COLLAB_HOST", "127.0.0.1")
MAX_GUESTS = 8


def _load_doctrine() -> dict[str, Any]:
    path = ROOT / "data" / "ammocode-2027-doctrine.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"collaboration": {"invite_only": True, "max_guests": MAX_GUESTS}}


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass
class Peer:
    ws: WebSocketServerProtocol
    peer_id: str
    name: str
    ip: str
    cursor_id: str = "arrow_emerald"
    is_host: bool = False
    muted: bool = False
    volume: float = 1.0


@dataclass
class Room:
    room_id: str
    invite_hash: str
    host_id: str
    room_secret: str = ""
    friend_ips: set[str] = field(default_factory=set)
    peers: dict[str, Peer] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    chat_log: list[dict[str, Any]] = field(default_factory=list)
    screen_share_grants: set[str] = field(default_factory=set)
    screen_share_active: str | None = None


class CollabHub:
    def __init__(self) -> None:
        self.guard = DdosGuard()
        self.rooms: dict[str, Room] = {}
        self.invite_index: dict[str, str] = {}
        self.peer_room: dict[str, str] = {}

    def create_invite(self, host_ip: str, friend_ips: list[str] | None = None) -> dict[str, Any]:
        token = secrets.token_urlsafe(24)
        room_id = secrets.token_hex(8)
        ih = _token_hash(token)
        secret = sec_mgr.room_secret() if sec_mgr else secrets.token_hex(16)
        room = Room(
            room_id=room_id,
            invite_hash=ih,
            host_id="",
            room_secret=secret,
            friend_ips=set(friend_ips or []),
        )
        if host_ip:
            room.friend_ips.add(host_ip)
        self.rooms[room_id] = room
        self.invite_index[ih] = room_id
        return {
            "ok": True,
            "room_id": room_id,
            "invite": token,
            "invite_url": f"?collab=1&invite={token}",
            "ws": f"ws://{COLLAB_HOST}:{COLLAB_PORT}",
            "friend_ips": sorted(room.friend_ips),
            "invite_only": True,
        }

    def validate_invite(self, token: str) -> Room | None:
        if not token:
            return None
        room_id = self.invite_index.get(_token_hash(token))
        if not room_id:
            return None
        return self.rooms.get(room_id)

    def _peer_list(self, room: Room) -> list[dict[str, Any]]:
        return [
            {
                "peer_id": p.peer_id,
                "name": p.name,
                "ip": p.ip,
                "cursor_id": p.cursor_id,
                "is_host": p.is_host,
                "muted": p.muted,
                "volume": p.volume,
            }
            for p in room.peers.values()
        ]

    async def broadcast(self, room: Room, msg: dict[str, Any], skip: str | None = None) -> None:
        dead: list[str] = []
        payload = json.dumps(msg, ensure_ascii=False)
        for pid, peer in room.peers.items():
            if pid == skip:
                continue
            try:
                await peer.ws.send(payload)
            except Exception:
                dead.append(pid)
        for pid in dead:
            await self._disconnect_peer(room, pid)

    async def _disconnect_peer(self, room: Room, peer_id: str) -> None:
        peer = room.peers.pop(peer_id, None)
        self.peer_room.pop(peer_id, None)
        if peer:
            self.guard.connection_close(peer.ip)
            try:
                await peer.ws.close()
            except Exception:
                pass
        if peer_id == room.host_id and room.peers:
            next_host = next(iter(room.peers))
            room.peers[next_host].is_host = True
            room.host_id = next_host
        await self.broadcast(room, {"type": "presence", "peers": self._peer_list(room)})

    async def handle(self, ws: WebSocketServerProtocol, path: str) -> None:
        ip = ws.remote_address[0] if ws.remote_address else "unknown"
        chk = self.guard.connection_open(ip)
        if not chk.get("ok"):
            await ws.close(1008, chk.get("error", "blocked"))
            return

        peer_id: str | None = None
        room: Room | None = None
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
            hello = json.loads(raw)
            if hello.get("type") != "join":
                await ws.send(json.dumps({"type": "error", "error": "invite_required",
                                          "message": "No connection without invite"}))
                await ws.close(1008, "invite_required")
                return

            token = str(hello.get("invite") or "")
            room = self.validate_invite(token)
            if not room:
                await ws.send(json.dumps({"type": "error", "error": "invalid_invite",
                                          "message": "Invalid or expired invite token"}))
                await ws.close(1008, "invalid_invite")
                return

            doc = _load_doctrine()
            max_g = int((doc.get("collaboration") or {}).get("max_guests", MAX_GUESTS))
            if len(room.peers) >= max_g:
                await ws.send(json.dumps({"type": "error", "error": "room_full"}))
                await ws.close(1008, "room_full")
                return

            if room.friend_ips and ip not in room.friend_ips:
                await ws.send(json.dumps({"type": "error", "error": "ip_not_friend",
                                          "message": f"IP {ip} not on host friend list"}))
                await ws.close(1008, "ip_not_friend")
                return

            peer_id = secrets.token_hex(6)
            name = str(hello.get("name") or f"guest-{peer_id[:4]}")[:32]
            cursor_id = str(hello.get("cursor_id") or "arrow_emerald")[:32]
            is_host = not room.host_id
            peer = Peer(ws=ws, peer_id=peer_id, name=name, ip=ip,
                        cursor_id=cursor_id, is_host=is_host)
            if is_host:
                room.host_id = peer_id
            room.peers[peer_id] = peer
            self.peer_room[peer_id] = room.room_id

            proof = ""
            if sec_mgr and room.room_secret:
                proof = sec_mgr.session_proof(room.room_secret, peer_id, room.invite_hash)
            await ws.send(json.dumps({
                "type": "joined",
                "peer_id": peer_id,
                "room_id": room.room_id,
                "is_host": is_host,
                "peers": self._peer_list(room),
                "chat_log": room.chat_log[-50:],
                "invite_only": True,
                "session_proof": proof,
                "screenshare_policy": "host_permit_gui_only",
            }))
            await self.broadcast(room, {"type": "peer_joined", "peer": self._peer_list(room)[-1]}, skip=peer_id)
            await self.broadcast(room, {"type": "presence", "peers": self._peer_list(room)}, skip=peer_id)

            async for message in ws:
                if len(message) > 65536:
                    continue
                try:
                    msg = json.loads(message)
                except json.JSONDecodeError:
                    continue
                await self._route(room, peer_id, msg)
        except asyncio.TimeoutError:
            try:
                await ws.send(json.dumps({"type": "error", "error": "join_timeout"}))
            except Exception:
                pass
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if room and peer_id and peer_id in room.peers:
                await self._disconnect_peer(room, peer_id)
            elif peer_id is None:
                self.guard.connection_close(ip)

    async def _route(self, room: Room, peer_id: str, msg: dict[str, Any]) -> None:
        mtype = str(msg.get("type") or "")
        peer = room.peers.get(peer_id)
        if not peer:
            return

        if mtype == "cursor":
            await self.broadcast(room, {
                "type": "cursor",
                "peer_id": peer_id,
                "line": msg.get("line"),
                "col": msg.get("col"),
                "x": msg.get("x"),
                "y": msg.get("y"),
                "cursor_id": peer.cursor_id,
            }, skip=peer_id)
            return

        if mtype == "chat":
            text = str(msg.get("text") or "").strip()[:2000]
            if not text:
                return
            entry = {"peer_id": peer_id, "name": peer.name, "text": text, "ts": time.time()}
            room.chat_log.append(entry)
            if len(room.chat_log) > 200:
                room.chat_log = room.chat_log[-200:]
            await self.broadcast(room, {"type": "chat", **entry})
            return

        if mtype == "voice_signal":
            target = str(msg.get("to") or "")
            payload = {
                "type": "voice_signal",
                "from": peer_id,
                "signal": msg.get("signal"),
                "sdp": msg.get("sdp"),
                "candidate": msg.get("candidate"),
            }
            if target and target in room.peers:
                try:
                    await room.peers[target].ws.send(json.dumps(payload))
                except Exception:
                    pass
            else:
                await self.broadcast(room, payload, skip=peer_id)
            return

        if mtype == "voice_state":
            peer.muted = bool(msg.get("muted"))
            peer.volume = max(0.0, min(1.0, float(msg.get("volume", peer.volume))))
            await self.broadcast(room, {
                "type": "voice_state",
                "peer_id": peer_id,
                "muted": peer.muted,
                "volume": peer.volume,
            })
            return

        if mtype == "set_cursor":
            cid = str(msg.get("cursor_id") or peer.cursor_id)[:32]
            peer.cursor_id = cid
            await self.broadcast(room, {"type": "cursor_persona", "peer_id": peer_id, "cursor_id": cid})
            return

        if mtype == "add_friend_ip" and peer.is_host:
            friend = str(msg.get("ip") or "").strip()
            if friend:
                room.friend_ips.add(friend)
                await ws_send(peer, {"type": "friend_ips", "ips": sorted(room.friend_ips)})
            return

        if mtype == "screen_share_grant" and peer.is_host:
            target = str(msg.get("to") or msg.get("peer_id") or "")
            if target in room.peers:
                room.screen_share_grants.add(target)
                room.screen_share_active = target
                await self.broadcast(room, {
                    "type": "screen_share_granted",
                    "from": peer_id,
                    "to": target,
                    "active": target,
                })
            return

        if mtype == "screen_share_revoke" and peer.is_host:
            target = str(msg.get("to") or msg.get("peer_id") or room.screen_share_active or "")
            room.screen_share_grants.discard(target)
            if room.screen_share_active == target:
                room.screen_share_active = None
            await self.broadcast(room, {"type": "screen_share_revoked", "from": peer_id, "to": target})
            return

        if mtype == "screen_share_request":
            host_peer = room.peers.get(room.host_id)
            if host_peer:
                await ws_send(host_peer, {
                    "type": "screen_share_request",
                    "from": peer_id,
                    "name": peer.name,
                })
            return

        if mtype == "screen_share_frame":
            frame_id = str(msg.get("frame_id") or "")
            mac = str(msg.get("mac") or "")
            if peer_id not in room.screen_share_grants and peer_id != room.host_id:
                return
            if sec_mgr and room.room_secret and frame_id:
                proof = sec_mgr.session_proof(room.room_secret, peer_id, room.invite_hash)
                if not sec_mgr.verify_frame_mac_peer(proof, frame_id, mac):
                    return
            payload = msg.get("data") or msg.get("frame")
            if not payload or len(str(payload)) > 280000:
                return
            await self.broadcast(room, {
                "type": "screen_share_frame",
                "from": peer_id,
                "frame_id": frame_id,
                "data": payload,
            }, skip=peer_id)
            return

        if mtype == "ping":
            await ws_send(peer, {"type": "pong", "ts": time.time()})


async def ws_send(peer: Peer, doc: dict[str, Any]) -> None:
    try:
        await peer.ws.send(json.dumps(doc))
    except Exception:
        pass


HUB = CollabHub()


async def ws_handler(ws: WebSocketServerProtocol, path: str = "") -> None:
    await HUB.handle(ws, path)


def create_invite_api(friend_ips: list[str] | None = None, host_ip: str = "127.0.0.1") -> dict[str, Any]:
    return HUB.create_invite(host_ip, friend_ips)


async def main_async() -> None:
    print(f"AmmoCode collab ws://{COLLAB_HOST}:{COLLAB_PORT} (invite-only)", flush=True)
    async with websockets.serve(ws_handler, COLLAB_HOST, COLLAB_PORT, max_size=65536):
        await asyncio.Future()


def main() -> int:
    parser = argparse.ArgumentParser(description="AmmoCode collab hub")
    parser.add_argument("--invite", action="store_true", help="Print a one-shot invite JSON and exit")
    parser.add_argument("--friend-ip", action="append", default=[], dest="friend_ips")
    args = parser.parse_args()
    if args.invite:
        print(json.dumps(HUB.create_invite("127.0.0.1", args.friend_ips), indent=2))
        return 0
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())