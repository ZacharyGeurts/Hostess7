#!/usr/bin/env pythong
"""NEXUS Field DHCP — issue leases only; DNS option 6 → Truth Resolver."""
from __future__ import annotations

import atexit
import fcntl
import json
import os
import socket
import struct
import subprocess
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
PANEL_CACHE = STATE / "field-dhcp-panel.json"
PID_FILE = STATE / "field-dhcp.pid"
LEASE_FILE = STATE / "field-dhcp-leases.json"
EVENTS_LOG = STATE / "field-dhcp-events.jsonl"
EVENTS_LOG_MAX = 2000
DHCP_LOCK = STATE / "field-dhcp.lock"
_SERVE_LOCK_HANDLE = None

PORT = 67
DISCOVER_RATE: dict[str, list[float]] = {}
DISCOVER_RATE_MAX = 12
DISCOVER_RATE_WINDOW = 60.0
def _dns_servers_v4() -> list[str]:
    raw = os.environ.get("NEXUS_FIELD_DHCP_DNS_IPV4", "127.0.0.1")
    hosts = [h.strip() for h in raw.split(",") if h.strip()]
    return hosts or ["127.0.0.1"]


def _dns_servers_v6() -> list[str]:
    raw = os.environ.get("NEXUS_FIELD_DHCP_DNS_IPV6", os.environ.get("NEXUS_FIELD_DNS_IPV6", "::1"))
    hosts = [h.strip() for h in raw.split(",") if h.strip()]
    return hosts or ["::1"]


DNS_SERVERS = _dns_servers_v4()
DNS_SERVERS_V6 = _dns_servers_v6()
LEASE_SEC = int(os.environ.get("NEXUS_FIELD_DHCP_LEASE", "3600"))
POOL_START = os.environ.get("NEXUS_FIELD_DHCP_POOL_START", "192.168.50.100")
POOL_END = os.environ.get("NEXUS_FIELD_DHCP_POOL_END", "192.168.50.200")
LEGACY_POOL_START = os.environ.get("NEXUS_FIELD_DHCP_LEGACY_POOL_START", "")
LEGACY_POOL_END = os.environ.get("NEXUS_FIELD_DHCP_LEGACY_POOL_END", "")
LEGACY_LEASE_SEC = int(os.environ.get("NEXUS_FIELD_DHCP_LEGACY_LEASE", "86400") or "86400")
LEGACY_OUI_PREFIXES = tuple(
    p.strip().lower()
    for p in os.environ.get(
        "NEXUS_FIELD_DHCP_LEGACY_OUI",
        "00:d0:f1,00:d0:0f,00:09:bf",
    ).split(",")
    if p.strip()
)


def _legacy_dns_servers_v4() -> list[str]:
    raw = os.environ.get("NEXUS_FIELD_DHCP_LEGACY_DNS_IPV4", "")
    hosts = [h.strip() for h in raw.split(",") if h.strip()]
    if hosts:
        return hosts
    doctrine = INSTALL / "data" / "field-legacy-connect-doctrine.json"
    try:
        doc = json.loads(doctrine.read_text(encoding="utf-8"))
        retro = (doc.get("dhcp_legacy") or {}).get("retro_pool") or {}
        queen = str(retro.get("gateway") or "192.168.47.1")
        return [queen]
    except (OSError, json.JSONDecodeError):
        return ["192.168.47.1"]


LEGACY_DNS_SERVERS = _legacy_dns_servers_v4()


def _bind_if() -> str:
    raw = os.environ.get("NEXUS_FIELD_DHCP_BIND", "").strip()
    if raw:
        return raw
    try:
        out = subprocess.run(
            ["ip", "-4", "addr", "show", "dev", "dummy-queen"],
            capture_output=True, text=True, timeout=2, errors="replace",
        )
        if "192.168.47.1" in (out.stdout or ""):
            return "192.168.47.1"
    except (OSError, subprocess.SubprocessError):
        pass
    return "0.0.0.0"


BIND_IF = _bind_if()


def _ammonet_dhcp() -> dict[str, Any]:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ammonet_dns_zones_dhcp", INSTALL / "lib" / "ammonet-dns-zones.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return {
                "domain": mod.dhcp_domain() if hasattr(mod, "dhcp_domain") else "ammonet.net",
                "search": mod.dhcp_search_domains() if hasattr(mod, "dhcp_search_domains") else ["ammonet.net"],
            }
    except Exception:
        pass
    return {"domain": "ammonet.net", "search": ["ammonet.net", "ammonet.com", "ammonet.org"]}


def _encode_domain_name(domain: str) -> bytes:
    out = bytearray()
    for label in domain.strip().lower().rstrip(".").split("."):
        if not label or len(label) > 63:
            continue
        out.append(len(label))
        out.extend(label.encode("ascii", errors="ignore"))
    out.append(0)
    return bytes(out)

_stats = {
    "discover": 0,
    "offer": 0,
    "request": 0,
    "ack": 0,
    "rejected": 0,
    "threat_rejects": 0,
    "conflicts_detected": 0,
    "declines": 0,
    "started_at": "",
}
_threats: list[dict[str, Any]] = []


def _now() -> str:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sovereign_sync_dhcp", INSTALL / "lib" / "field-sovereign-sync.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc("dhcp")
    except (ImportError, OSError, AttributeError):
        pass
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sovereign_clock_dhcp", INSTALL / "lib" / "sovereign-clock.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc_z("dhcp")
    except (ImportError, OSError, AttributeError):
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _ip_to_int(ip: str) -> int:
    return struct.unpack("!I", socket.inet_aton(ip))[0]


def _int_to_ip(n: int) -> str:
    return socket.inet_ntoa(struct.pack("!I", n & 0xFFFFFFFF))


def _lease_expiry(leased_at: str) -> tuple[str, int]:
    try:
        dt = datetime.strptime(leased_at[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        dt = datetime.strptime(_now()[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    exp = dt + timedelta(seconds=LEASE_SEC)
    now_dt = datetime.strptime(_now()[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    remaining = max(0, int((exp - now_dt).total_seconds()))
    return exp.strftime("%Y-%m-%dT%H:%M:%SZ"), remaining


def _append_event(event: str, mac: str, ip: str = "", reason: str = "") -> None:
    row = {"ts": _now(), "event": event, "mac": mac, "ip": ip, "reason": reason}
    EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        with EVENTS_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        lines = EVENTS_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > EVENTS_LOG_MAX:
            EVENTS_LOG.write_text("\n".join(lines[-EVENTS_LOG_MAX:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def _record_threat(reason: str, ip: str, mac: str, action: str = "reject") -> None:
    _stats["threat_rejects"] = int(_stats.get("threat_rejects") or 0) + 1
    row = {"reason": reason, "ip": ip, "mac": mac, "action": action, "ts": _now()}
    _threats.append(row)
    if len(_threats) > 100:
        del _threats[:-100]
    _append_event("threat_reject", mac, ip, reason)


def _discover_rate_ok(mac: str) -> bool:
    now = time.time()
    hits = [t for t in DISCOVER_RATE.get(mac, []) if now - t <= DISCOVER_RATE_WINDOW]
    DISCOVER_RATE[mac] = hits
    if len(hits) >= DISCOVER_RATE_MAX:
        return False
    hits.append(now)
    DISCOVER_RATE[mac] = hits
    return True


def _pool_valid(ip: str, *, start: str = POOL_START, end: str = POOL_END) -> bool:
    try:
        n = _ip_to_int(ip)
        return _ip_to_int(start) <= n <= _ip_to_int(end)
    except OSError:
        return False


def _is_legacy_client(mac: str) -> bool:
    m = str(mac or "").lower().replace("-", ":")
    if not m:
        return False
    return any(m.startswith(prefix) for prefix in LEGACY_OUI_PREFIXES)


def _pool_for_mac(mac: str) -> tuple[str, str, int]:
    if LEGACY_POOL_START and LEGACY_POOL_END and _is_legacy_client(mac):
        return LEGACY_POOL_START, LEGACY_POOL_END, LEGACY_LEASE_SEC
    return POOL_START, POOL_END, LEASE_SEC


def _dns_for_mac(mac: str) -> list[str]:
    if _is_legacy_client(mac) and LEGACY_DNS_SERVERS:
        return LEGACY_DNS_SERVERS
    return DNS_SERVERS


def _ip_in_use(ip: str, timeout: float = 0.9) -> bool:
    """Ping probe before OFFER — prevent lease/IP collisions on the LAN."""
    if os.environ.get("NEXUS_FIELD_DHCP_PING_PROBE", "1") != "1":
        return False
    try:
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True,
            timeout=timeout,
            errors="replace",
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _next_lease(mac: str, *, renew: bool = False) -> str:
    leases = _load_json(LEASE_FILE, {"leases": {}})
    pool = leases.setdefault("leases", {})
    now = _now()
    if mac in pool:
        entry = pool[mac]
        entry["last_seen"] = now
        entry["renewals"] = int(entry.get("renewals") or 0) + (1 if renew else 0)
        exp, rem = _lease_expiry(str(entry.get("leased_at") or now))
        entry["expires_at"] = exp
        entry["remaining_seconds"] = rem
        pool_start, pool_end, lease_sec = _pool_for_mac(mac)
        entry["dns"] = _dns_for_mac(mac)
        entry["legacy"] = _is_legacy_client(mac)
        entry["lease_seconds"] = lease_sec
        _save_json(LEASE_FILE, leases)
        return str(entry.get("ip") or pool_start)
    pool_start, pool_end, lease_sec = _pool_for_mac(mac)
    start = _ip_to_int(pool_start)
    end = _ip_to_int(pool_end)
    used = {_ip_to_int(v["ip"]) for v in pool.values() if v.get("ip")}
    for n in range(start, end + 1):
        if n not in used:
            ip = _int_to_ip(n)
            if _ip_in_use(ip):
                _stats["conflicts_detected"] = int(_stats.get("conflicts_detected") or 0) + 1
                _append_event("pool_conflict", mac, ip, "ping_probe_in_use")
                continue
            exp, rem = _lease_expiry(now)
            pool[mac] = {
                "ip": ip,
                "leased_at": now,
                "expires_at": exp,
                "remaining_seconds": rem,
                "renewals": 0,
                "declines": 0,
                "last_seen": now,
                "dns": _dns_for_mac(mac),
                "legacy": _is_legacy_client(mac),
                "lease_seconds": lease_sec,
            }
            _save_json(LEASE_FILE, leases)
            return ip
    return pool_start


def _dhcp_options(data: bytes) -> dict[int, bytes]:
    opts: dict[int, bytes] = {}
    if len(data) < 240:
        return opts
    i = 240
    while i < len(data):
        code = data[i]
        if code == 255:
            break
        if code == 0:
            i += 1
            continue
        if i + 1 >= len(data):
            break
        ln = data[i + 1]
        i += 2
        opts[code] = data[i : i + ln]
        i += ln
    return opts


def _build_reply(
    msg_type: int,
    xid: bytes,
    yiaddr: str,
    chaddr: bytes,
    *,
    lease_sec: int = LEASE_SEC,
    dns_servers: list[str] | None = None,
) -> bytes:
    op = 2
    htype = 1
    hlen = 6
    hops = 0
    secs = 0
    flags = 0
    ciaddr = "0.0.0.0"
    siaddr = BIND_IF if BIND_IF != "0.0.0.0" else "127.0.0.1"
    giaddr = "0.0.0.0"
    sname = b"\x00" * 64
    file_ = b"\x00" * 128
    magic = b"\x63\x82\x53\x63"
    opts = bytearray()
    opts.extend(bytes([53, 1, msg_type]))
    opts.extend(bytes([54, 4]) + socket.inet_aton(siaddr))
    opts.extend(bytes([51, 4]) + struct.pack("!I", lease_sec))
    dns_list = dns_servers or DNS_SERVERS
    dns_blob = b"".join(socket.inet_aton(d) for d in dns_list)
    opts.extend(bytes([6, len(dns_blob)]) + dns_blob)
    ammonet = _ammonet_dhcp()
    domain_blob = _encode_domain_name(str(ammonet.get("domain") or "ammonet.net"))
    if domain_blob:
        opts.extend(bytes([15, len(domain_blob)]) + domain_blob)
    search_list = bytearray()
    for dom in list(ammonet.get("search") or [])[:5]:
        enc = _encode_domain_name(str(dom))
        if enc:
            search_list.extend(enc)
    if search_list:
        opts.extend(bytes([119, len(search_list)]) + search_list)
    opts.extend(bytes([1, 4]) + socket.inet_aton("255.255.255.0"))
    opts.append(255)
    header = struct.pack(
        "!BBBBI4s4s4s4s16s64s128s4s",
        op, htype, hlen, hops,
        struct.unpack("!I", xid)[0],
        socket.inet_aton(ciaddr),
        socket.inet_aton(yiaddr),
        socket.inet_aton(siaddr),
        socket.inet_aton(giaddr),
        chaddr[:16].ljust(16, b"\x00"),
        sname,
        file_,
        magic,
    )
    return header + bytes(opts)


def _guard_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("dns_threat_guard", INSTALL / "lib" / "dns-threat-guard.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _sovereign_gate() -> dict[str, Any]:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sovereign_gate_dhcp", INSTALL / "lib" / "field-sovereign-gate.py",
        )
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.gate(service="dhcp", action="packet")
    except Exception:
        return {}


def _handle(data: bytes, addr: tuple[str, int]) -> bytes | None:
    gate = _sovereign_gate()
    if len(data) < 240:
        _stats["rejected"] += 1
        return None
    client = f"{addr[0]}:{addr[1]}"
    try:
        mod = _guard_mod()
        if mod.is_permanently_blocked(client):
            _stats["rejected"] += 1
            _record_threat("permanent_block", addr[0], client, "reject")
            return None
        ok, reason = mod.listen_before_reject(client_key=client, packet_len=len(data))
        if not ok:
            _stats["rejected"] += 1
            _record_threat(reason or "flood", addr[0], client, "reject")
            mod.eradicate_threat(client_key=client, reason=reason, vector="DDOS_FLOOD")
            return None
    except Exception:
        pass
    opts = _dhcp_options(data)
    msg_type = opts.get(53, b"\x01")[0] if 53 in opts else 1
    xid = data[4:8]
    chaddr = data[28:44]
    mac = ":".join(f"{b:02x}" for b in chaddr[:6])
    if msg_type == 1:
        if not _discover_rate_ok(mac):
            _stats["rejected"] += 1
            _record_threat("discover_rate_limit", addr[0], mac, "reject")
            return None
        _stats["discover"] += 1
        pool_start, pool_end, lease_sec = _pool_for_mac(mac)
        ip = _next_lease(mac)
        if not _pool_valid(ip, start=pool_start, end=pool_end):
            _stats["rejected"] += 1
            _stats["conflicts_detected"] = int(_stats.get("conflicts_detected") or 0) + 1
            _append_event("pool_conflict", mac, ip, "invalid_pool_ip")
            return None
        _stats["offer"] += 1
        _append_event("offer", mac, ip)
        return _build_reply(2, xid, ip, chaddr, lease_sec=lease_sec, dns_servers=_dns_for_mac(mac))
    if msg_type == 3:
        _stats["request"] += 1
        pool_start, pool_end, lease_sec = _pool_for_mac(mac)
        ip = _next_lease(mac, renew=True)
        if not _pool_valid(ip, start=pool_start, end=pool_end):
            _stats["rejected"] += 1
            return None
        _stats["ack"] += 1
        _append_event("ack", mac, ip)
        return _build_reply(5, xid, ip, chaddr, lease_sec=lease_sec, dns_servers=_dns_for_mac(mac))
    if msg_type == 7:
        _stats["declines"] = int(_stats.get("declines") or 0) + 1
        _append_event("decline", mac, "", "client_decline")
    _stats["rejected"] += 1
    _append_event("reject", mac, "", f"msg_type_{msg_type}")
    return None


def _port_in_use(port: int = PORT) -> bool:
    try:
        out = subprocess.run(
            ["ss", "-H", "-u", "-l", "-n", f"sport = :{port}"],
            capture_output=True, text=True, timeout=3, errors="replace",
        )
        return bool((out.stdout or "").strip())
    except (OSError, subprocess.SubprocessError):
        return False


def _dhcp_probe_offer(host: str = "192.168.47.1", timeout: float = 1.5) -> bool:
    """Live DHCP OFFER proves field server is crushing leases."""
    try:
        xid = struct.pack("!I", int(time.time()) & 0xFFFFFFFF)
        mac = b"\x02\x00\x00\x00\x00\x01" + b"\x00" * 10
        pkt = b"\x01\x01\x06\x00" + xid + b"\x00" * 16 + mac + b"\x00" * 64 + b"\x00" * 128
        pkt += bytes([99, 130, 83, 99, 53, 1, 1, 255])
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if host not in ("0.0.0.0", "255.255.255.255"):
            try:
                sock.bind((host, 0))
            except OSError:
                pass
        sock.settimeout(timeout)
        sock.sendto(pkt, (host, PORT))
        data, _ = sock.recvfrom(2048)
        sock.close()
        return len(data) >= 240 and data[0] == 2
    except OSError:
        return False


def _dhcp_running() -> bool:
    if PID_FILE.is_file():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip().split()[0])
            os.kill(pid, 0)
            return True
        except PermissionError:
            pass
        except (OSError, ValueError):
            pass
    if _port_in_use(PORT):
        for host in (BIND_IF, "192.168.47.1", "127.0.0.1"):
            if host and _dhcp_probe_offer(host):
                return True
        return _may_serve_dhcp()
    return False


def _loop() -> None:
    bind = _bind_if()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((bind, PORT))
    while True:
        try:
            data, addr = sock.recvfrom(2048)
        except OSError:
            continue
        resp = _handle(data, addr)
        if resp:
            try:
                sock.sendto(resp, addr)
            except OSError:
                pass


def _takeover_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dns_service_takeover", INSTALL / "lib" / "dns-service-takeover.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _may_serve_dhcp() -> bool:
    try:
        return bool(_takeover_mod().can_serve_dhcp())
    except Exception:
        return True


def _release_serve_lock() -> None:
    global _SERVE_LOCK_HANDLE
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    if _SERVE_LOCK_HANDLE is not None:
        try:
            fcntl.flock(_SERVE_LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
            _SERVE_LOCK_HANDLE.close()
        except OSError:
            pass
        _SERVE_LOCK_HANDLE = None


def _acquire_serve_lock() -> bool:
    global _SERVE_LOCK_HANDLE
    DHCP_LOCK.parent.mkdir(parents=True, exist_ok=True)
    if PID_FILE.is_file():
        try:
            old = int(PID_FILE.read_text(encoding="utf-8").strip().split()[0])
            os.kill(old, 0)
            return False
        except (OSError, ValueError):
            PID_FILE.unlink(missing_ok=True)
    try:
        handle = open(DHCP_LOCK, "w", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    except OSError:
        return False
    handle.write(f"{os.getpid()}\n")
    handle.flush()
    _SERVE_LOCK_HANDLE = handle
    atexit.register(_release_serve_lock)
    return True


def serve() -> int:
    if not _may_serve_dhcp():
        build_panel()
        from nexus_await import await_seconds

        await_seconds(15, STATE)
        return 0
    if not _acquire_serve_lock():
        from nexus_await import await_seconds

        await_seconds(5, STATE)
        return 0
    _stats["started_at"] = _now()
    PID_FILE.write_text(f"{os.getpid()}\n", encoding="utf-8")
    _loop()
    return 0


def _lease_history(limit: int = 100) -> list[dict[str, Any]]:
    if not EVENTS_LOG.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in EVENTS_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return list(reversed(rows[-limit:]))


def _leases_detailed(raw: dict[str, Any], limit: int = 200) -> list[dict[str, Any]]:
    pool = raw.get("leases") or {}
    rows: list[dict[str, Any]] = []
    for mac, entry in pool.items():
        if not isinstance(entry, dict):
            continue
        leased_at = str(entry.get("leased_at") or "")
        exp, rem = _lease_expiry(leased_at) if leased_at else ("", 0)
        rows.append({
            "mac": mac,
            "ip": entry.get("ip"),
            "leased_at": leased_at,
            "expires_at": entry.get("expires_at") or exp,
            "remaining_seconds": entry.get("remaining_seconds", rem),
            "renewals": int(entry.get("renewals") or 0),
            "declines": int(entry.get("declines") or 0),
            "last_seen": entry.get("last_seen"),
            "dns": entry.get("dns") or DNS_SERVERS,
        })
    rows.sort(key=lambda r: int(r.get("remaining_seconds") or 0))
    return rows[:limit]


def build_panel() -> dict[str, Any]:
    leases = _load_json(LEASE_FILE, {"leases": {}})
    takeover: dict[str, Any] = {}
    try:
        takeover = _takeover_mod().panel_json()
    except Exception:
        takeover = {}
    may_serve = _may_serve_dhcp()
    running = _dhcp_running()
    bind = _bind_if()
    detailed = _leases_detailed(leases, 200)
    events = _lease_history(100)
    pool_count = len(leases.get("leases") or {})
    doc = {
        "schema": "field-dhcp/v2",
        "updated": _now(),
        "running": running,
        "may_serve": may_serve,
        "takeover": takeover,
        "takeover_phase": takeover.get("phase") or "observing",
        "security_model": "field-sovereign-gate",
        "never_lose_cycle": True,
        "motto": "We are every DHCP lease left on the planet — DNS option 6 → Truth Resolver; cycle never lost.",
        "bind": f"{bind}:{PORT}",
        "ok": running and may_serve,
        "crushing": running,
        "pool": {"start": POOL_START, "end": POOL_END},
        "legacy_pool": (
            {"start": LEGACY_POOL_START, "end": LEGACY_POOL_END, "lease_seconds": LEGACY_LEASE_SEC}
            if LEGACY_POOL_START and LEGACY_POOL_END
            else None
        ),
        "legacy_oui_prefixes": list(LEGACY_OUI_PREFIXES),
        "dns_option": DNS_SERVERS,
        "dns_option_v6": DNS_SERVERS_V6,
        "lease_seconds": LEASE_SEC,
        "stats": dict(_stats),
        "stats_extended": {
            "discovers": int(_stats.get("discover") or 0),
            "offers": int(_stats.get("offer") or 0),
            "acks": int(_stats.get("ack") or 0),
            "rejects": int(_stats.get("rejected") or 0),
            "threat_rejects": int(_stats.get("threat_rejects") or 0),
            "conflicts_detected": int(_stats.get("conflicts_detected") or 0),
            "declines": int(_stats.get("declines") or 0),
        },
        "leases": list(leases.get("leases", {}).items())[:200],
        "leases_detailed": detailed,
        "lease_history_events": events,
        "lease_count": pool_count,
        "total_leases": pool_count,
        "ipv6_skeleton": {
            "enabled": False,
            "pool": "fe80::/64",
            "dns_option_v6": DNS_SERVERS_V6,
            "note": "IPv4-first serve path — IPv6 lease schema reserved",
        },
        "threats": list(_threats)[-50:],
        "hostess7": {
            "inside": f"LAN DHCP → {', '.join(DNS_SERVERS)} DNS · IPv6 field {', '.join(DNS_SERVERS_V6)}",
            "outside": "No DHCP on WAN — DNS admin ports 7/77/777 read-only",
        },
        "planetary_authority": {
            "scope": "planet",
            "we_are_every_lease": True,
            "api": "/api/field-planetary-dns-dhcp",
        },
        "collision_guard": _collision_guard_slice(),
    }
    _save_json(PANEL_CACHE, doc)
    return doc


def _collision_guard_slice() -> dict[str, Any]:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "collision_guard_dhcp", INSTALL / "lib" / "field-dns-dhcp-collision-guard.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            doc = mod.detect_collisions()
            sole = doc.get("sole_authority") or {}
            return {
                "ok": bool(sole.get("ok")),
                "sole_authority": sole,
                "collision_count": doc.get("collision_count", 0),
                "api": "/api/field-dns-dhcp-collision-guard",
            }
    except Exception:
        pass
    cached = _load_json(STATE / "field-dns-dhcp-collision-guard-panel.json", {})
    if cached.get("sole_authority"):
        return {
            "ok": bool((cached.get("sole_authority") or {}).get("ok")),
            "sole_authority": cached.get("sole_authority"),
            "collision_count": cached.get("collision_count", 0),
            "api": "/api/field-dns-dhcp-collision-guard",
        }
    return {"api": "/api/field-dns-dhcp-collision-guard", "partial": True}


def _panel_json_stub() -> dict[str, Any]:
    return {
        "schema": "field-dhcp/v2",
        "updated": _now(),
        "running": False,
        "lease_count": 0,
        "leases_detailed": [],
        "lease_history_events": [],
        "stats_extended": {},
        "threats": [],
        "_partial": True,
    }


def panel_json() -> dict[str, Any]:
    return build_panel()


def crush_dhcp() -> dict[str, Any]:
    """Promote takeover, refresh Queen LAN, prove DHCP OFFER, publish panel."""
    root = INSTALL
    queen_lan = root / "scripts" / "queen-lan-up.sh"
    if queen_lan.is_file():
        try:
            subprocess.run(
                ["bash", str(queen_lan)],
                timeout=12,
                capture_output=True,
                errors="replace",
            )
        except (OSError, subprocess.SubprocessError):
            pass
    try:
        _takeover_mod().evaluate_takeover(persist=True)
    except Exception:
        pass
    panel = build_panel()
    panel["crush"] = {
        "queen_lan": "192.168.47.1",
        "offer_queen": _dhcp_probe_offer("192.168.47.1"),
        "offer_loopback": _dhcp_probe_offer("127.0.0.1"),
        "port_67": _port_in_use(PORT),
        "motto": "We are every DHCP lease on the planet — Truth DNS option 6 · Queen LAN crushing leases",
    }
    _save_json(PANEL_CACHE, panel)
    return panel


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "serve":
        serve()
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "crush":
        print(json.dumps(crush_dhcp(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-dhcp.py [serve|build|json|crush]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())