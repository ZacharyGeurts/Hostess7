#!/usr/bin/env python3
"""Field rack terminal mesh — GNU terminal between all racks, Hostess7, and AmmoOS."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-rack-terminal-mesh-panel.json"
REGISTRY = STATE / "field-global-servers-registry.json"
SCHEMA = "field-rack-terminal-mesh/v1"
PANEL_PORT = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
TERMINAL_V = "v=6"
GLOBAL_TARGET = int(os.environ.get("NEXUS_GLOBAL_SERVER_TARGET") or 2500)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _local_json(rel: str, args: list[str], body: dict[str, Any] | None = None, *, timeout: int = 90) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    cmd = [sys.executable, str(py)]
    if body is not None:
        cmd.append("dispatch")
    else:
        cmd.extend(args)
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(body) if body is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(INSTALL),
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)[:200]}
    return {"ok": False, "error": "dispatch_failed", "script": rel}


def _http_post(url: str, body: dict[str, Any], *, timeout: float = 60.0) -> dict[str, Any]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "FieldRackTerminalMesh/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if raw.strip().startswith("{"):
                return json.loads(raw)
            return {"ok": True, "output": raw[:8000]}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"ok": False, "http": exc.code, "error": raw[:300]}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)[:200]}


def _base_origin(tunnel: int = 0) -> str:
    if tunnel:
        return f"http://127.0.0.1:{tunnel}"
    return f"http://127.0.0.1:{PANEL_PORT}"


def _fixed_peers() -> list[dict[str, Any]]:
    origin = _base_origin()
    pages_h7 = "https://zacharygeurts.github.io/Hostess7/gnueol-terminal/"
    pages_ammo = "https://zacharygeurts.github.io/GNUEOLTerminal/"
    return [
        {
            "peer_id": "hostess7-local",
            "lane": "hostess7",
            "label": "Hostess7 · local command",
            "terminal_url": f"{origin}/grok-lab",
            "terminal_api": f"{origin}/api/hostess7-command",
            "mesh_api": f"{origin}/api/field-rack-terminal-mesh",
            "product": "Hostess7",
            "online": True,
        },
        {
            "peer_id": "hostess7-pages",
            "lane": "hostess7",
            "label": "Hostess7 · GitHub Pages terminal",
            "terminal_url": pages_h7,
            "terminal_api": None,
            "product": "Hostess7",
            "online": True,
            "pages": True,
        },
        {
            "peer_id": "ammoos-local",
            "lane": "ammoos",
            "label": "AmmoOS · GNU EOL Terminal",
            "terminal_url": f"{origin}/field-gnu-terminal?{TERMINAL_V}",
            "terminal_api": f"{origin}/api/field-gnu-terminal",
            "mesh_api": f"{origin}/api/field-rack-terminal-mesh",
            "product": "AmmoOS",
            "online": True,
        },
        {
            "peer_id": "ammoos-pages",
            "lane": "ammoos",
            "label": "AmmoOS · GNUEOL Pages",
            "terminal_url": pages_ammo,
            "terminal_api": None,
            "product": "AmmoOS",
            "online": True,
            "pages": True,
        },
    ]


def _global_fleet_summary() -> dict[str, Any]:
    reg = _load(REGISTRY, {})
    servers = list(reg.get("servers") or [])
    online = sum(1 for s in servers if isinstance(s, dict) and s.get("online"))
    return {
        "target": int(reg.get("target") or GLOBAL_TARGET),
        "total": len(servers) or int(reg.get("count") or 0),
        "online": online or len(servers),
        "full_updated": bool(reg.get("full_updated")),
        "api": "/api/field-rack-fleet-2500",
    }


def _global_server_peer(row: dict[str, Any]) -> dict[str, Any]:
    sid = str(row.get("id") or "")
    fid = str(row.get("field_id") or sid)
    tunnel = int(row.get("tunnel") or 0)
    origin = _base_origin(tunnel)
    metro = str(row.get("metro_label") or row.get("metro_id") or "global")
    return {
        "peer_id": sid,
        "lane": "global",
        "field_id": fid,
        "label": f"{sid} · {metro} · {fid}",
        "metro_id": row.get("metro_id"),
        "metro_label": row.get("metro_label"),
        "region_id": row.get("region_id"),
        "terminal_url": f"{origin}/field-gnu-terminal?{TERMINAL_V}",
        "terminal_api": f"{origin}/api/field-gnu-terminal",
        "mesh_api": f"{origin}/api/field-rack-terminal-mesh",
        "chat_api": f"{origin}/api/field-rack-grok-chat",
        "tunnel": tunnel or None,
        "online": bool(row.get("online", True)),
        "full_rack": bool(row.get("full_rack", True)),
        "product": "GlobalRack",
    }


def peers_search(
    query: str = "",
    *,
    limit: int = 40,
    offset: int = 0,
    lane: str = "",
) -> dict[str, Any]:
    q = (query or "").strip().lower()
    lim = max(1, min(int(limit or 40), 120))
    off = max(0, int(offset or 0))
    lane_filter = (lane or "").strip().lower()
    reg = _load(REGISTRY, {})
    servers = [s for s in (reg.get("servers") or []) if isinstance(s, dict)]
    hits: list[dict[str, Any]] = []
    for row in servers:
        if lane_filter and lane_filter not in ("global", "all"):
            continue
        if q:
            blob = " ".join(
                str(row.get(k) or "")
                for k in ("id", "field_id", "metro_id", "metro_label", "region_id", "machine_profile", "host_id")
            ).lower()
            if q not in blob:
                continue
        hits.append(_global_server_peer(row))
    total = len(hits)
    page = hits[off : off + lim]
    return {
        "ok": True,
        "schema": SCHEMA,
        "action": "peers_search",
        "query": q,
        "offset": off,
        "limit": lim,
        "total": total,
        "peers": page,
        "fleet": _global_fleet_summary(),
    }


def _physical_peers(*, probe: bool = True) -> list[dict[str, Any]]:
    peers: list[dict[str, Any]] = []
    seen: set[str] = set()

    inv = _mod("lib/field-rack-inventory.py", "rack_inv")
    racks: list[dict[str, Any]] = []
    if inv and hasattr(inv, "inventory"):
        doc = inv.inventory(fast=not probe, probe=probe)
        racks = list(doc.get("racks") or [])
    else:
        racks = list(_load(STATE / "field-rack-inventory-panel.json", {}).get("racks") or [])

    for rack in racks:
        if not isinstance(rack, dict):
            continue
        pid = str(rack.get("rack_id") or rack.get("field_id") or "")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        tunnel = int(rack.get("tunnel") or 0)
        origin = _base_origin(tunnel)
        health = rack.get("health") or {}
        peers.append({
            "peer_id": pid,
            "lane": "rack",
            "field_id": rack.get("field_id"),
            "label": rack.get("label") or pid,
            "terminal_url": rack.get("terminal_url") or f"{origin}/field-gnu-terminal?{TERMINAL_V}",
            "terminal_api": f"{origin}/api/field-gnu-terminal",
            "mesh_api": f"{origin}/api/field-rack-terminal-mesh",
            "chat_api": f"{origin}/api/field-rack-grok-chat",
            "tunnel": tunnel or None,
            "online": bool(health.get("available") or health.get("up")),
            "product": "GrokRack",
        })

    for row in _fixed_peers():
        pid = str(row.get("peer_id") or "")
        if pid and pid not in seen:
            seen.add(pid)
            peers.append(row)

    return peers


def mesh_peers(*, probe: bool = True, include_global: bool = False) -> list[dict[str, Any]]:
    peers = _physical_peers(probe=probe)
    if include_global:
        reg = _load(REGISTRY, {})
        for row in reg.get("servers") or []:
            if isinstance(row, dict):
                peers.append(_global_server_peer(row))
    return peers


def _find_peer(peer_id: str) -> dict[str, Any] | None:
    pid = (peer_id or "local").strip().lower()
    if pid.startswith("global-"):
        reg = _load(REGISTRY, {})
        for row in reg.get("servers") or []:
            if isinstance(row, dict) and str(row.get("id") or "").lower() == pid:
                return _global_server_peer(row)
    for peer in mesh_peers(probe=False):
        keys = {
            str(peer.get("peer_id") or "").lower(),
            str(peer.get("field_id") or "").lower(),
        }
        if pid in keys or (pid == "local" and peer.get("peer_id") == "local"):
            return peer
    if pid in ("local", "ammoos-local", "ammoos"):
        for peer in mesh_peers(probe=False):
            if peer.get("peer_id") == "ammoos-local":
                return peer
    return None


def _run_on_peer(peer: dict[str, Any], command: str, *, cwd: str = "") -> dict[str, Any]:
    lane = str(peer.get("lane") or "rack")
    cmd = (command or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty_command"}

    if lane == "hostess7" and not peer.get("pages"):
        return _local_json(
            "lib/hostess7-command.py",
            [],
            {"action": "ask", "message": f"[mesh terminal] {cmd}", "source": "field-rack-terminal-mesh"},
            timeout=120,
        )

    api = str(peer.get("terminal_api") or "")
    if api.startswith("http"):
        return _http_post(api, {"action": "run", "command": cmd, "cwd": cwd or None})

    if lane in ("rack", "ammoos") or peer.get("peer_id") == "local":
        return _local_json(
            "lib/field-gnu-terminal.py",
            [],
            {"action": "run", "command": cmd, "cwd": cwd or None},
        )

    return {"ok": False, "error": "peer_not_runnable", "peer": peer.get("peer_id")}


def mesh_status(*, probe: bool = True) -> dict[str, Any]:
    peers = _physical_peers(probe=probe)
    online = [p for p in peers if p.get("online")]
    fleet = _global_fleet_summary()
    by_lane: dict[str, int] = {}
    for p in peers:
        lane = str(p.get("lane") or "unknown")
        by_lane[lane] = by_lane.get(lane, 0) + 1
    by_lane["global"] = fleet.get("total", 0)
    doc = {
        "ok": True,
        "schema": SCHEMA,
        "updated": _utc(),
        "title": "Rack Terminal Mesh",
        "motto": "One GNU terminal between every rack · Hostess7 · AmmoOS · 2500 global",
        "counts": {
            "total": len(peers) + fleet.get("total", 0),
            "online": len(online) + fleet.get("online", 0),
            "physical_total": len(peers),
            "physical_online": len(online),
            "racks": sum(1 for p in peers if p.get("lane") == "rack"),
            "hostess7": sum(1 for p in peers if p.get("lane") == "hostess7"),
            "ammoos": sum(1 for p in peers if p.get("lane") == "ammoos"),
            "global": fleet,
            "by_lane": by_lane,
        },
        "peers": peers,
        "peers_mode": "physical_only",
        "peers_search_api": {"action": "peers_search", "query": "", "limit": 40},
        "fleet": fleet,
        "hub_terminal": f"http://127.0.0.1:{PANEL_PORT}/field-gnu-terminal?{TERMINAL_V}",
        "api": "/api/field-rack-terminal-mesh",
    }
    _save(PANEL, doc)
    return doc


def mesh_broadcast(command: str, *, cwd: str = "") -> dict[str, Any]:
    cmd = (command or "").strip()
    if not cmd:
        return {"ok": False, "error": "empty_command"}
    results: list[dict[str, Any]] = []
    for peer in mesh_peers(probe=False):
        if not peer.get("online") or peer.get("pages"):
            continue
        pid = str(peer.get("peer_id") or "")
        row = _run_on_peer(peer, cmd, cwd=cwd)
        results.append({
            "peer_id": pid,
            "lane": peer.get("lane"),
            "ok": row.get("ok", False),
            "output": (row.get("output") or row.get("reply") or "")[:1200],
            "error": row.get("error"),
        })
    ok_count = sum(1 for r in results if r.get("ok"))
    return {
        "ok": ok_count > 0,
        "schema": SCHEMA,
        "command": cmd,
        "broadcast": True,
        "reached": len(results),
        "ok_count": ok_count,
        "results": results,
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "peers"):
        return mesh_status(probe=bool(body.get("probe", True)))
    if action in ("peers_search", "search", "find_peers"):
        return peers_search(
            str(body.get("query") or body.get("q") or ""),
            limit=int(body.get("limit") or 40),
            offset=int(body.get("offset") or 0),
            lane=str(body.get("lane") or ""),
        )
    if action in ("run", "command", "exec"):
        peer_id = str(body.get("peer_id") or body.get("peer") or body.get("rack_id") or "ammoos-local")
        peer = _find_peer(peer_id)
        if not peer:
            return {"ok": False, "error": "peer_not_found", "peer_id": peer_id}
        cmd = str(body.get("command") or body.get("cmd") or "")
        cwd = str(body.get("cwd") or "")
        result = _run_on_peer(peer, cmd, cwd=cwd)
        return {
            **result,
            "peer_id": peer.get("peer_id"),
            "lane": peer.get("lane"),
            "label": peer.get("label"),
            "terminal_url": peer.get("terminal_url"),
        }
    if action in ("broadcast", "mesh_all", "all"):
        return mesh_broadcast(str(body.get("command") or body.get("cmd") or ""), cwd=str(body.get("cwd") or ""))
    if action == "open":
        peer = _find_peer(str(body.get("peer_id") or body.get("peer") or "ammoos-local"))
        if not peer:
            return {"ok": False, "error": "peer_not_found"}
        return {"ok": True, "peer": peer, "terminal_url": peer.get("terminal_url")}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "status", "peers"):
        print(json.dumps(mesh_status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-rack-terminal-mesh.py [json|dispatch]", "api": "/api/field-rack-terminal-mesh"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())