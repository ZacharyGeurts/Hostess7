#!/usr/bin/env python3
"""AmmoCode network mesh — polite discovery, HTTP tunnel, friend/block, threat ratings."""
from __future__ import annotations

import ipaddress
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SG = ROOT.parent
NEWLATEST = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", NEWLATEST / ".nexus-state"))
LISTS_PATH = ROOT / "data" / "network-lists.json"
DOCTRINE_PATH = ROOT / "data" / "ammocode-network-doctrine.json"
PORT = int(os.environ.get("AMMOCODE_PORT", "9555"))

_SCAN_LOCK = threading.Lock()
_LAST_SCAN: dict[str, float] = {}
_HOST_CACHE: dict[str, Any] | None = None
_HOST_CACHE_AT = 0.0

_TUNNEL_QUEUES: dict[str, deque] = {}
_TUNNEL_SESSIONS: dict[str, dict[str, Any]] = {}
_TUNNEL_LOCK = threading.Lock()
_SERVER_TUNNEL_INBOX = secrets.token_hex(8)

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save_json(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _doctrine() -> dict[str, Any]:
    return _load_json(DOCTRINE_PATH, {})


def _lists() -> dict[str, Any]:
    doc = _load_json(LISTS_PATH, {"friends": [], "blocks": []})
    doc.setdefault("friends", [])
    doc.setdefault("blocks", [])
    return doc


def _save_lists(doc: dict[str, Any]) -> None:
    _save_json(LISTS_PATH, doc)


def _import_mod(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _local_ips() -> list[str]:
    ips: list[str] = []
    try:
        proc = subprocess.run(
            ["hostname", "-I"],
            capture_output=True, text=True, timeout=3,
        )
        ips.extend(proc.stdout.split())
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        proc = subprocess.run(
            ["ip", "-4", "addr", "show"],
            capture_output=True, text=True, timeout=4,
        )
        for line in proc.stdout.splitlines():
            m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
            if m:
                ips.append(m.group(1))
    except (OSError, subprocess.TimeoutExpired):
        pass
    out = []
    for ip in ips:
        if ip and ip not in out and not ip.startswith("127."):
            out.append(ip)
    if not out:
        out.append("127.0.0.1")
    return out


def _subnet_hosts(ip: str, limit: int = 24) -> list[str]:
    try:
        addr = ipaddress.ip_address(ip)
        if addr.is_loopback:
            return ["127.0.0.1"]
        if addr.is_private:
            net = ipaddress.ip_network(f"{ip}/24", strict=False)
            hosts = [str(h) for h in net.hosts()]
            return hosts[:limit]
    except ValueError:
        pass
    return []


def beacon(identity: dict[str, Any] | None = None) -> dict[str, Any]:
    ips = _local_ips()
    doc = {
        "ok": True,
        "schema": "ammocode-network-beacon/v1",
        "ammocode": True,
        "version": "4.9.0",
        "distro_version": "5.0.0",
        "service": "ammocode",
        "port": PORT,
        "ips": ips,
        "network": "local" if any(PRIVATE_RE.match(i) for i in ips) else "open",
        "http_tunnel": True,
        "tunnel_inbox": _SERVER_TUNNEL_INBOX,
        "ws_collab": int(os.environ.get("AMMOCODE_COLLAB_PORT", "9556")),
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if identity:
        doc.update(identity)
    return doc


def _probe_beacon(host: str, port: int, timeout: float) -> dict[str, Any] | None:
    url = f"http://{host}:{port}/api/ammocode"
    body = json.dumps({"action": "network_beacon"}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "AmmoCode-Discover/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def discover(client_ip: str = "", force: bool = False) -> dict[str, Any]:
    """Polite LAN discovery — rate-limited, capped host count, single port."""
    doc = _doctrine()
    disc = doc.get("discovery") or {}
    min_iv = float(disc.get("min_scan_interval_seconds", 120))
    max_hosts = int(disc.get("max_hosts_per_scan", 24))
    timeout = float(disc.get("probe_timeout_seconds", 1.5))
    delay = float(disc.get("inter_probe_delay_ms", 80)) / 1000.0
    ports = disc.get("ports") or [PORT]

    key = client_ip or "local"
    now = time.monotonic()
    with _SCAN_LOCK:
        last = _LAST_SCAN.get(key, 0.0)
        if not force and (now - last) < min_iv:
            wait = int(min_iv - (now - last))
            return {
                "ok": True,
                "throttled": True,
                "retry_after": wait,
                "hosts": [],
                "message": f"Discovery rate-limited — wait {wait}s (not spammy)",
            }
        _LAST_SCAN[key] = now

    local = _local_ips()
    candidates: list[str] = []
    seen: set[str] = set()
    for lip in local:
        for h in _subnet_hosts(lip, max_hosts):
            if h not in seen and h not in local:
                seen.add(h)
                candidates.append(h)
        if lip.startswith("127."):
            continue
        break
    candidates = candidates[:max_hosts]

    found: list[dict[str, Any]] = []
    for host in candidates:
        for port in ports:
            hit = _probe_beacon(host, int(port), timeout)
            if hit and hit.get("ammocode"):
                rated = rate_host(host, hit)
                found.append({
                    "host": host,
                    "port": port,
                    "network": rated.get("network", "local"),
                    "beacon": hit,
                    "threat": rated,
                })
                break
        time.sleep(delay)

    return {
        "ok": True,
        "throttled": False,
        "scanned": len(candidates),
        "found_count": len(found),
        "hosts": found,
        "local_ips": local,
        "polite": True,
    }


def _gk_connection_for_ip(ip: str) -> dict[str, Any] | None:
    gk_path = NEWLATEST / "lib" / "connection-gatekeeper.py"
    mod = _import_mod(gk_path, "connection_gatekeeper_ac")
    if not mod or not hasattr(mod, "analyze_connections"):
        return None
    try:
        proc = subprocess.run(
            ["ss", "-H", "-tunap"],
            capture_output=True, text=True, timeout=8,
        )
        out = mod.analyze_connections(proc.stdout.splitlines())
        for row in out.get("connections") or []:
            if row.get("peer_ip") == ip or row.get("remote_ip") == ip:
                return row
    except (OSError, subprocess.TimeoutExpired, Exception):
        pass
    return None


def _friendly_check(ip: str) -> dict[str, Any] | None:
    fg = NEWLATEST / "lib" / "friendly-guard.py"
    mod = _import_mod(fg, "friendly_guard_ac")
    if not mod or not hasattr(mod, "check_payload"):
        return None
    try:
        return mod.check_payload(ip)
    except Exception:
        return None


def rate_host(host: str, beacon: dict[str, Any] | None = None) -> dict[str, Any]:
    """Automated threat security rating 0–100 for a connection target."""
    lists = _lists()
    friends = {str(x).lower() for x in lists.get("friends") or []}
    blocks = {str(x).lower() for x in lists.get("blocks") or []}
    h = host.lower().strip()
    local_ips = {x.lower() for x in _local_ips()}

    if h in local_ips or h in ("127.0.0.1", "::1"):
        return {
            "rating": 98,
            "verdict": "SELF",
            "label": "this host",
            "sources": ["local_ips"],
            "permit": True,
            "network": "local",
        }

    if h in blocks:
        return {
            "rating": 0,
            "verdict": "BLOCKED",
            "label": "blocked",
            "sources": ["block_list"],
            "permit": False,
            "network": "denied",
        }

    if h in friends:
        return {
            "rating": 95,
            "verdict": "FRIEND",
            "label": "friend",
            "sources": ["friend_list"],
            "permit": True,
            "network": "local" if PRIVATE_RE.match(h) else "open",
        }

    sources: list[str] = ["heuristic"]
    rating = 50
    verdict = "UNKNOWN"
    is_local = bool(PRIVATE_RE.match(h))
    if is_local:
        rating = 65
        verdict = "LOCAL"
        sources.append("local_subnet")
    if beacon and beacon.get("ammocode"):
        rating = min(100, rating + 20)
        sources.append("ammocode_beacon")
        verdict = "AMMOCODE_PEER"

    gk = _gk_connection_for_ip(h)
    if gk:
        sources.append("connection_gatekeeper")
        tr = int(gk.get("trust_rank", 3))
        hostility = int(gk.get("hostility_score") or 0)
        if gk.get("block_recommended"):
            rating = max(0, 20 - hostility // 10)
            verdict = "HARM_CANDIDATE"
        else:
            rating = max(rating, 80 - tr * 15 - hostility // 5)
            verdict = str(gk.get("verdict") or verdict)

    fg = _friendly_check(h)
    if fg:
        sources.append("friendly_guard")
        if fg.get("refuse"):
            rating = min(rating, 30)
            verdict = "FRIENDLY_REFUSE"

    doc = _doctrine()
    thr = doc.get("threat_ratings") or {}
    block_thr = int(thr.get("block_threshold", 25))
    permit = rating >= block_thr and h not in blocks

    return {
        "rating": max(0, min(100, rating)),
        "verdict": verdict,
        "label": "trusted" if rating >= 85 else "caution" if rating >= 50 else "risk",
        "sources": sources,
        "permit": permit,
        "network": "local" if is_local else "open",
        "gatekeeper": gk,
    }


def evaluate_host(force: bool = False) -> dict[str, Any]:
    """Evaluate threats on the host AmmoCode currently resides on."""
    global _HOST_CACHE, _HOST_CACHE_AT
    now = time.monotonic()
    if not force and _HOST_CACHE and (now - _HOST_CACHE_AT) < 60.0:
        return _HOST_CACHE

    score = 100
    findings: list[dict[str, Any]] = []
    sources: list[str] = []

    gk_path = NEWLATEST / "lib" / "connection-gatekeeper.py"
    mod = _import_mod(gk_path, "connection_gatekeeper_host")
    if mod and hasattr(mod, "analyze_connections"):
        sources.append("connection_gatekeeper")
        try:
            proc = subprocess.run(["ss", "-H", "-tunap"], capture_output=True, text=True, timeout=10)
            gk_out = mod.analyze_connections(proc.stdout.splitlines())
            harm = int(gk_out.get("harm_candidates") or 0)
            peak = int(gk_out.get("peak_hostility_score") or 0)
            if harm:
                score -= min(40, harm * 8)
                findings.append({"id": "harm_candidates", "count": harm, "severity": "bad"})
            if peak > 50:
                score -= min(25, peak // 4)
                findings.append({"id": "peak_hostility", "value": peak, "severity": "warn"})
            hostile_conns = [
                c for c in (gk_out.get("connections") or [])
                if c.get("block_recommended")
            ][:5]
            for c in hostile_conns:
                findings.append({
                    "id": "connection",
                    "peer": c.get("peer_ip") or c.get("remote_ip"),
                    "verdict": c.get("verdict"),
                    "severity": "bad",
                })
        except (OSError, subprocess.TimeoutExpired, Exception) as exc:
            findings.append({"id": "gatekeeper_error", "message": str(exc), "severity": "info"})

    hostile_py = NEWLATEST / "lib" / "znetwork-hostile-threat.py"
    hmod = _import_mod(hostile_py, "znetwork_hostile_ac")
    if hmod and hasattr(hmod, "scan"):
        sources.append("znetwork_hostile")
        try:
            os.environ.setdefault("NEXUS_INSTALL_ROOT", str(NEWLATEST))
            os.environ.setdefault("NEXUS_STATE_DIR", str(STATE))
            hz = hmod.scan(publish=False)
            hc = int(hz.get("hostile_count") or hz.get("harm_candidates") or 0)
            if hc:
                score -= min(30, hc * 10)
                findings.append({"id": "znetwork_hostile", "count": hc, "severity": "bad"})
        except Exception:
            pass

    sources.append("local_heuristic")
    try:
        proc = subprocess.run(["ss", "-H", "-ltn"], capture_output=True, text=True, timeout=5)
        listeners = [ln for ln in proc.stdout.splitlines() if ln.strip()]
        risky_ports = sum(1 for ln in listeners if any(p in ln for p in (":4444 ", ":31337 ", ":6667 ")))
        if risky_ports:
            score -= 15
            findings.append({"id": "risky_listeners", "count": risky_ports, "severity": "warn"})
    except (OSError, subprocess.TimeoutExpired):
        pass

    score = max(0, min(100, score))
    doc = {
        "ok": True,
        "host_score": score,
        "host_label": "clean" if score >= 80 else "caution" if score >= 50 else "at_risk",
        "findings": findings,
        "sources": sources,
        "local_ips": _local_ips(),
        "hostname": socket.gethostname(),
        "evaluated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _HOST_CACHE = doc
    _HOST_CACHE_AT = now
    return doc


def list_manage(action: str, entry: str = "", list_name: str = "") -> dict[str, Any]:
    doc = _lists()
    key = "friends" if list_name in ("friend", "friends") else "blocks"
    entry = entry.strip().lower()
    if not entry and action != "get":
        return {"ok": False, "error": "entry_required"}
    items = [str(x).lower() for x in doc.get(key) or []]
    if action in ("add", "friend_add", "block_add"):
        if entry not in items:
            items.append(entry)
        other = "blocks" if key == "friends" else "friends"
        doc[other] = [x for x in doc.get(other, []) if str(x).lower() != entry]
    elif action in ("remove", "friend_remove", "block_remove"):
        items = [x for x in items if x != entry]
    doc[key] = items
    _save_lists(doc)
    return {"ok": True, "lists": doc}


def tunnel_register(peer_id: str = "") -> dict[str, Any]:
    pid = peer_id or _SERVER_TUNNEL_INBOX
    with _TUNNEL_LOCK:
        _TUNNEL_QUEUES.setdefault(pid, deque(maxlen=256))
    return {
        "ok": True,
        "tunnel_id": pid,
        "poll_action": "tunnel_poll",
        "send_action": "tunnel_send",
        "server_inbox": _SERVER_TUNNEL_INBOX,
    }


def _local_ip_set() -> set[str]:
    return {x.lower() for x in _local_ips()} | {"127.0.0.1", "localhost", "::1"}


def _parse_remote_tunnel_target(to_id: str) -> tuple[str, int] | None:
    if ":" not in to_id:
        return None
    host, _, port_s = to_id.rpartition(":")
    try:
        port = int(port_s)
    except ValueError:
        return None
    host = host.strip("[]").lower()
    if host in _local_ip_set():
        return None
    return host, port


def _http_tunnel_post(host: str, port: int, action: str, body: dict[str, Any], timeout: float = 3.0) -> dict[str, Any] | None:
    url = f"http://{host}:{port}/api/ammocode"
    payload = json.dumps({"action": action, **body}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "AmmoCode-Tunnel/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, TimeoutError, OSError):
        return None


def tunnel_deliver(from_id: str, tunnel_id: str, payload: Any) -> dict[str, Any]:
    """Enqueue a message delivered from a remote peer (HTTP tunnel relay)."""
    if not tunnel_id:
        return {"ok": False, "error": "tunnel_id_required"}
    sender_host = (from_id or "").split(":")[0].lower()
    if sender_host and sender_host not in _local_ip_set():
        rated = rate_host(sender_host)
        if not rated.get("permit"):
            return {"ok": False, "error": "threat_blocked", "threat": rated}
    msg = {"from": from_id, "to": tunnel_id, "payload": payload, "ts": time.time(), "relayed": True}
    with _TUNNEL_LOCK:
        _TUNNEL_QUEUES.setdefault(tunnel_id, deque(maxlen=256)).append(msg)
    return {"ok": True, "delivered": True}


def tunnel_poll(tunnel_id: str, timeout_ms: int = 2000) -> dict[str, Any]:
    deadline = time.monotonic() + max(0.2, timeout_ms / 1000.0)
    with _TUNNEL_LOCK:
        q = _TUNNEL_QUEUES.setdefault(tunnel_id, deque(maxlen=256))
        while time.monotonic() < deadline:
            if q:
                msgs = []
                while q and len(msgs) < 16:
                    msgs.append(q.popleft())
                return {"ok": True, "messages": msgs}
            time.sleep(0.05)
    return {"ok": True, "messages": []}


def tunnel_send(from_id: str, to_id: str, payload: Any) -> dict[str, Any]:
    if not to_id:
        return {"ok": False, "error": "to_id_required"}
    remote = _parse_remote_tunnel_target(to_id)
    rated = rate_host((remote[0] if remote else to_id.split(":")[0]).lower())
    if not rated.get("permit"):
        return {"ok": False, "error": "threat_blocked", "threat": rated}
    if remote:
        host, port = remote
        beacon_hit = _probe_beacon(host, port, 2.0) or {}
        inbox = str(beacon_hit.get("tunnel_inbox") or _SERVER_TUNNEL_INBOX)
        relay = _http_tunnel_post(host, port, "tunnel_deliver", {
            "from_id": from_id or _SERVER_TUNNEL_INBOX,
            "tunnel_id": inbox,
            "payload": payload,
        })
        if not relay or not relay.get("ok"):
            return {"ok": False, "error": "remote_deliver_failed", "threat": rated}
        return {"ok": True, "sent": True, "relayed": True, "remote_inbox": inbox, "threat": rated}
    msg = {"from": from_id, "to": to_id, "payload": payload, "ts": time.time()}
    with _TUNNEL_LOCK:
        _TUNNEL_QUEUES.setdefault(to_id, deque(maxlen=256)).append(msg)
    return {"ok": True, "sent": True, "threat": rated}


def tunnel_connect(local_id: str, remote_host: str, remote_port: int = 0) -> dict[str, Any]:
    port = remote_port or PORT
    rated = rate_host(remote_host)
    if not rated.get("permit"):
        return {"ok": False, "error": "threat_blocked", "threat": rated}
    remote_beacon = _probe_beacon(remote_host, port, 2.0)
    if not remote_beacon:
        return {"ok": False, "error": "beacon_unreachable", "threat": rated}
    mitm: dict[str, Any] = {"ok": True, "verdict": "SKIP"}
    try:
        import ammocode_security_manage as sec_mgr
        mitm = sec_mgr.verify_beacon(remote_host, remote_beacon)
        if not mitm.get("permit"):
            return {"ok": False, "error": "mitm_blocked", "mitm": mitm, "threat": rated}
    except ImportError:
        pass
    session = secrets.token_hex(10)
    with _TUNNEL_LOCK:
        _TUNNEL_SESSIONS[session] = {
            "local_id": local_id,
            "remote_host": remote_host,
            "remote_port": port,
            "created": time.time(),
            "threat": rated,
        }
    return {
        "ok": True,
        "session_id": session,
        "http_tunnel": True,
        "remote": remote_beacon,
        "threat": rated,
        "poll": {"action": "tunnel_poll", "tunnel_id": local_id},
        "remote_tunnel_inbox": remote_beacon.get("tunnel_inbox"),
        "mitm": mitm,
        "send": {"action": "tunnel_send", "to_id": f"{remote_host}:{port}"},
    }


def network_status() -> dict[str, Any]:
    return {
        "ok": True,
        "doctrine": _doctrine(),
        "lists": _lists(),
        "local_ips": _local_ips(),
        "host": evaluate_host(),
        "beacon": beacon(),
    }