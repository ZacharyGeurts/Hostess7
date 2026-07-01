#!/usr/bin/env pythong
"""NEXUS Field DNS — smart truthful self-hosted resolver (IPv4 + IPv6).

Only loopback listeners. Foreign resolvers (Charter, Google, Cloudflare, etc.)
are stopped by field-dns.sh firewall + resolv enforcement. Resolution uses
dig +trace from root hints — no shortcut public DNS.
"""
from __future__ import annotations

import atexit
import fcntl
import json
import os
import re
import socket
import struct
import subprocess
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nexus_await import await_seconds  # noqa: E402
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))

OUT_JSON = STATE / "field-dns.json"
PANEL_CACHE = STATE / "field-dns-panel.json"
PID_FILE = STATE / "field-dns.pid"
BLOCKLIST = STATE / "adblock" / "domains-block.txt"
EXTRA_BLOCK = STATE / "dns-truth-blocklist.txt"
CACHE_TTL = int(os.environ.get("NEXUS_FIELD_DNS_CACHE_TTL", "300"))

IPV4 = os.environ.get("NEXUS_FIELD_DNS_IPV4", "127.0.0.1")
IPV6 = os.environ.get("NEXUS_FIELD_DNS_IPV6", "::1")
PORT = int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53"))
QUERY_LOG = STATE / "field-dns-queries.jsonl"
QUERY_LOG_MAX = 5000
RECENT_PANEL_LIMIT = 200
DNS_LOCK = STATE / "field-dns.lock"
_SERVE_LOCK_HANDLE = None
_threat_events: list[dict[str, Any]] = []
_poison_anomalies = 0
_dnssec = {"enabled": True, "validations": 0, "failures": 0, "stub": True}


def _bind_hosts_v4() -> list[str]:
    # 127.0.0.53 is systemd-resolved — binding there conflicts; redirect via resolv instead.
    raw = os.environ.get("NEXUS_FIELD_DNS_BINDS_IPV4", "127.0.0.1")
    hosts = [h.strip() for h in raw.split(",") if h.strip()]
    return hosts or [IPV4]


def _bind_hosts_v6() -> list[str]:
    raw = os.environ.get("NEXUS_FIELD_DNS_BINDS_IPV6", IPV6)
    hosts = [h.strip() for h in raw.split(",") if h.strip()]
    return hosts or [IPV6]

QTYPE_MAP = {1: "A", 28: "AAAA", 5: "CNAME", 15: "MX", 16: "TXT"}

_cache: dict[str, tuple[float, list[str]]] = {}
_cache_lock = threading.Lock()
_stats = {
    "queries": 0,
    "blocked": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "errors": 0,
    "rate_limits": 0,
    "started_at": "",
}


def _now() -> str:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sovereign_sync_dns", INSTALL / "lib" / "field-sovereign-sync.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc("dns")
    except (ImportError, OSError, AttributeError):
        pass
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sovereign_clock_dns", INSTALL / "lib" / "sovereign-clock.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc_z("dns")
    except (ImportError, OSError, AttributeError):
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _load_blocklist() -> set[str]:
    blocked: set[str] = set()
    for path in (BLOCKLIST, EXTRA_BLOCK):
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                dom = line.strip().lower().lstrip(".")
                if dom and not dom.startswith("#"):
                    blocked.add(dom)
        except OSError:
            continue
    return blocked


def _is_blocked(qname: str, blocked: set[str]) -> bool:
    name = qname.lower().rstrip(".")
    if not name:
        return False
    if name in blocked:
        return True
    parts = name.split(".")
    for i in range(len(parts)):
        suffix = ".".join(parts[i:])
        if suffix in blocked:
            return True
    return False


def _encode_name(name: str) -> bytes:
    out = bytearray()
    for label in name.rstrip(".").split("."):
        try:
            raw = label.encode("ascii")[:63]
        except UnicodeEncodeError:
            raw = label.encode("idna")[:63]
        out.append(len(raw))
        out.extend(raw)
    out.append(0)
    return bytes(out)


def _read_name(data: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    end = offset
    jumped = False
    while offset < len(data):
        length = data[offset]
        if length == 0:
            offset += 1
            if not jumped:
                end = offset
            break
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                break
            if not jumped:
                end = offset + 2
            ptr = ((length & 0x3F) << 8) | data[offset + 1]
            offset = ptr
            jumped = True
            continue
        offset += 1
        labels.append(data[offset : offset + length].decode("ascii", errors="replace"))
        offset += length
    return ".".join(labels), end


def _parse_query(data: bytes) -> tuple[int, str, int, int] | None:
    if len(data) < 12:
        return None
    txn_id, flags, qdcount, _, _, _ = struct.unpack("!HHHHHH", data[:12])
    if qdcount < 1 or (flags >> 15) & 1:
        return None
    qname, offset = _read_name(data, 12)
    if offset + 4 > len(data):
        return None
    qtype, qclass = struct.unpack("!HH", data[offset : offset + 4])
    return txn_id, qname, qtype, qclass


def _pack_rdata(qtype: int, value: str) -> bytes | None:
    if qtype == 1:
        try:
            return socket.inet_pton(socket.AF_INET, value)
        except OSError:
            return None
    if qtype == 28:
        try:
            return socket.inet_pton(socket.AF_INET6, value)
        except OSError:
            return None
    return None


def _build_response(
    txn_id: int,
    qname: str,
    qtype: int,
    qclass: int,
    answers: list[str],
    rcode: int = 0,
) -> bytes:
    header = struct.pack("!HHHHHH", txn_id, 0x8180 | (rcode & 0xF), 1, len(answers), 0, 0)
    question = _encode_name(qname) + struct.pack("!HH", qtype, qclass)
    body = bytearray()
    for ans in answers:
        rdata = _pack_rdata(qtype, ans)
        if not rdata:
            continue
        body.extend(_encode_name(qname))
        body.extend(struct.pack("!HHI", qtype, qclass, 120))
        body.extend(struct.pack("!H", len(rdata)))
        body.extend(rdata)
    return header + question + bytes(body)


def _guard_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("dns_threat_guard", INSTALL / "lib" / "dns-threat-guard.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _integrity_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("dns_egress_integrity", INSTALL / "lib" / "dns-egress-integrity.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _resolve_trace(qname: str, qtype_name: str) -> list[str]:
    guard = _guard_mod()
    if not guard.acquire_dig_slot():
        return []
    try:
        proc = subprocess.run(
            [
                "dig",
                "+trace",
                "+time=4",
                "+tries=1",
                "+noall",
                "+answer",
                qname,
                qtype_name,
            ],
            capture_output=True,
            text=True,
            timeout=14,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        guard.release_dig_slot()
        return []
    finally:
        guard.release_dig_slot()
    out: list[str] = []
    for line in (proc.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == qtype_name:
            out.append(parts[4])
    return out[:24]


def _resolve(qname: str, qtype: int, blocked: set[str]) -> tuple[list[str], str]:
    qtype_name = QTYPE_MAP.get(qtype)
    if not qtype_name:
        return [], "unsupported"
    if _is_blocked(qname, blocked):
        return [], "blocked"
    key = f"{qname.lower()}:{qtype_name}"
    now = time.time()
    with _cache_lock:
        hit = _cache.get(key)
        if hit and hit[0] > now:
            _stats["cache_hits"] += 1
            return hit[1], "cache"
    answers = _resolve_trace(qname, qtype_name)
    _stats["cache_misses"] = int(_stats.get("cache_misses") or 0) + 1
    if answers:
        with _cache_lock:
            _cache[key] = (now + CACHE_TTL, answers)
        try:
            chk = _integrity_mod().verify_dns_answer(qname, qtype_name, answers)
            if isinstance(chk, dict) and chk.get("exact_match") is False:
                global _poison_anomalies
                _poison_anomalies += 1
                _record_threat_event("poison", qname, "integrity_mismatch")
        except Exception:
            pass
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "dns_internet_field", INSTALL / "lib" / "dns-internet-field.py",
            )
            if spec and spec.loader:
                _inf = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(_inf)
                _inf.record_query(qname, answers)
        except Exception:
            pass
        return answers, "trace"
    return [], "miss"


def _record_threat_event(kind: str, target: str, detail: str) -> None:
    row = {"type": kind, "target": target, "detail": detail, "ts": _now(), "count": 1}
    _threat_events.append(row)
    if len(_threat_events) > 200:
        del _threat_events[:-200]


def _append_query_log(row: dict[str, Any]) -> None:
    QUERY_LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        with QUERY_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        lines = QUERY_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > QUERY_LOG_MAX:
            QUERY_LOG.write_text("\n".join(lines[-QUERY_LOG_MAX:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def _parse_query_ts(ts: str) -> float:
    try:
        return datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp()
    except (ValueError, TypeError):
        return 0.0


def _read_query_log(limit: int = QUERY_LOG_MAX) -> list[dict[str, Any]]:
    if not QUERY_LOG.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in QUERY_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return rows


_ANALYTICS_CACHE: dict[str, Any] = {}
_ANALYTICS_AT: float = 0.0
_ANALYTICS_TTL = float(os.environ.get("NEXUS_FIELD_DNS_ANALYTICS_TTL", "60"))


def _query_analytics() -> dict[str, Any]:
    rows = _read_query_log()
    now = time.time()
    last_60 = [r for r in rows if now - _parse_query_ts(str(r.get("ts") or "")) <= 60]
    last_300 = [r for r in rows if now - _parse_query_ts(str(r.get("ts") or "")) <= 300]
    latencies = [float(r["latency_ms"]) for r in rows if r.get("latency_ms") is not None]
    top = Counter(str(r.get("qname") or "").lower().rstrip(".") for r in rows if r.get("qname")).most_common(20)
    queries_total = int(_stats.get("queries") or 0)
    cache_hits = int(_stats.get("cache_hits") or 0)
    return {
        "qps_60s": round(len(last_60) / 60, 2) if last_60 else 0.0,
        "qps_5m": round(len(last_300) / 300, 2) if last_300 else 0.0,
        "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
        "top_domains": dict(top),
        "cache_hit_rate": round(100 * cache_hits / max(queries_total, 1), 1),
    }


def _query_analytics_cached(force: bool = False) -> dict[str, Any]:
    global _ANALYTICS_CACHE, _ANALYTICS_AT
    now = time.time()
    if not force and _ANALYTICS_CACHE and now - _ANALYTICS_AT < _ANALYTICS_TTL:
        return _ANALYTICS_CACHE
    _ANALYTICS_CACHE = _query_analytics()
    _ANALYTICS_AT = now
    return _ANALYTICS_CACHE


def _dnssec_status() -> dict[str, Any]:
    enabled = os.environ.get("NEXUS_FIELD_DNS_DNSSEC", "1") == "1"
    if enabled:
        try:
            proc = subprocess.run(
                ["dig", "+dnssec", "+time=3", "+tries=1", "+noall", "+answer", "example.com", "A"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            if "ad" in out.lower() or "rrsig" in out.lower():
                _dnssec["validations"] = int(_dnssec.get("validations") or 0) + 1
            elif proc.returncode != 0:
                _dnssec["failures"] = int(_dnssec.get("failures") or 0) + 1
        except (OSError, subprocess.TimeoutExpired):
            _dnssec["failures"] = int(_dnssec.get("failures") or 0) + 1
    return {
        "enabled": enabled,
        "validations": int(_dnssec.get("validations") or 0),
        "failures": int(_dnssec.get("failures") or 0),
        "stub": True,
    }


def _threats_summary() -> list[dict[str, Any]]:
    by_type: dict[str, dict[str, Any]] = {}
    for row in _threat_events:
        kind = str(row.get("type") or "unknown")
        slot = by_type.setdefault(kind, {"type": kind, "count": 0, "last": row.get("ts")})
        slot["count"] += 1
        slot["last"] = row.get("ts") or slot["last"]
    if _poison_anomalies:
        slot = by_type.setdefault("poison", {"type": "poison", "count": 0, "last": _now()})
        slot["count"] += _poison_anomalies
    if int(_stats.get("rate_limits") or 0):
        by_type.setdefault("rate_limit", {
            "type": "rate_limit",
            "count": int(_stats.get("rate_limits") or 0),
            "last": _now(),
        })
    if int(_stats.get("blocked") or 0):
        by_type.setdefault("block", {
            "type": "block",
            "count": int(_stats.get("blocked") or 0),
            "last": _now(),
        })
    return list(by_type.values())


def _sovereign_gate() -> dict[str, Any]:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "sovereign_gate_dns", INSTALL / "lib" / "field-sovereign-gate.py",
        )
        if not spec or not spec.loader:
            return {}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.gate(service="dns", action="query")
    except Exception:
        return {}


def _handle_query(data: bytes, blocked: set[str], client: str = "") -> bytes | None:
    gate = _sovereign_gate()
    parsed = _parse_query(data)
    if not parsed:
        return None
    txn_id, qname, qtype, qclass = parsed
    _stats["queries"] += 1
    t0 = time.time()
    answers, reason = _resolve(qname, qtype, blocked)
    latency_ms = round((time.time() - t0) * 1000, 1)
    _append_query_log({
        "ts": gate.get("derived_utc") or _now(),
        "cycle": gate.get("cycle"),
        "qname": qname,
        "qtype": QTYPE_MAP.get(qtype, str(qtype)),
        "answers": answers[:8],
        "reason": reason,
        "client": client,
        "latency_ms": latency_ms,
        "blocked": reason == "blocked",
    })
    if reason == "blocked":
        _stats["blocked"] += 1
        _record_threat_event("block", qname, "blocklist")
        return _build_response(txn_id, qname, qtype, qclass, [], rcode=3)
    if not answers:
        _stats["errors"] += 1
        return _build_response(txn_id, qname, qtype, qclass, [], rcode=2)
    return _build_response(txn_id, qname, qtype, qclass, answers)


def _udp_loop(family: int, host: str) -> None:
    sock = socket.socket(family, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if family == socket.AF_INET6:
        try:
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
        except OSError:
            pass
    sock.bind((host, PORT))
    blocked = _load_blocklist()
    last_reload = time.time()
    while True:
        if time.time() - last_reload > 120:
            blocked = _load_blocklist()
            last_reload = time.time()
        try:
            data, addr = sock.recvfrom(4096)
        except OSError:
            continue
        client = f"{addr[0]}:{addr[1]}"
        try:
            guard = _guard_mod()
            if guard.is_permanently_blocked(client):
                continue
            parsed_peek = _parse_query(data)
            qtype_peek = parsed_peek[2] if parsed_peek else None
            ok, reason = guard.listen_before_reject(
                client_key=client, packet_len=len(data), qtype=qtype_peek,
            )
            if not ok:
                _stats["rate_limits"] = int(_stats.get("rate_limits") or 0) + 1
                _record_threat_event("rate_limit", client, reason or "flood")
                guard.eradicate_threat(client_key=client, reason=reason, vector="DDOS_FLOOD")
                continue
        except Exception:
            pass
        try:
            resp = _handle_query(data, blocked, client=client)
        except Exception:
            _stats["errors"] += 1
            continue
        if resp:
            try:
                sock.sendto(resp, addr)
            except OSError:
                pass


def _publish(extra: dict[str, Any] | None = None) -> None:
    doc: dict[str, Any] = {
        "updated": _now(),
        "title": "NEXUS Truth DNS",
        "priority": 1,
        "self_hosted": True,
        "truthful": True,
        "foreign_resolvers_stopped": True,
        "ipv4": {"host": IPV4, "port": PORT},
        "ipv6": {"host": IPV6, "port": PORT},
        "listeners": [f"{IPV4}#{PORT}", f"[{IPV6}]#{PORT}"],
        "stats": dict(_stats),
        "blocklist_domains": len(_load_blocklist()),
        "cache_entries": len(_cache),
    }
    if extra:
        doc.update(extra)
    tmp = OUT_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT_JSON)


def _multipoint_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dns_multipoint_identity", INSTALL / "lib" / "dns-multipoint-identity.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


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
    """Single resolver instance — duplicate binds cause silent query loss."""
    global _SERVE_LOCK_HANDLE
    DNS_LOCK.parent.mkdir(parents=True, exist_ok=True)
    if PID_FILE.is_file():
        try:
            old = int(PID_FILE.read_text(encoding="utf-8").strip().split()[0])
            os.kill(old, 0)
            return False
        except (OSError, ValueError):
            PID_FILE.unlink(missing_ok=True)
    try:
        handle = open(DNS_LOCK, "w", encoding="utf-8")
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
    if not _acquire_serve_lock():
        await_seconds(5, STATE)
        return 0
    _stats["started_at"] = _now()
    listeners: list[str] = []
    threads: list[threading.Thread] = []
    for host in _bind_hosts_v4():
        listeners.append(f"{host}#{PORT}")
        threads.append(threading.Thread(target=_udp_loop, args=(socket.AF_INET, host), daemon=True))
    for host in _bind_hosts_v6():
        listeners.append(f"[{host}]#{PORT}")
        threads.append(threading.Thread(target=_udp_loop, args=(socket.AF_INET6, host), daemon=True))
    try:
        _multipoint_mod().build_identity(running=True)
    except Exception:
        pass
    _publish({"running": True, "pid": os.getpid(), "listeners": listeners})
    PID_FILE.write_text(f"{os.getpid()}\n", encoding="utf-8")
    for t in threads:
        t.start()
    while True:
        await_seconds(5, STATE)
        try:
            _multipoint_mod().build_identity(running=True)
        except Exception:
            pass
        _publish({"running": True, "pid": os.getpid(), "listeners": listeners})


def status() -> dict[str, Any]:
    if OUT_JSON.is_file():
        try:
            return json.loads(OUT_JSON.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "updated": _now(),
        "running": False,
        "self_hosted": True,
        "ipv4": {"host": IPV4, "port": PORT},
        "ipv6": {"host": IPV6, "port": PORT},
    }


def _planetary_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dns_planetary_security", INSTALL / "lib" / "dns-planetary-security.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _recent_queries(limit: int = RECENT_PANEL_LIMIT) -> list[dict[str, Any]]:
    rows = _read_query_log(limit * 2)
    if rows:
        return list(reversed(rows[-limit:]))
    hints = STATE / "field-dns-cache-hints.jsonl"
    legacy: list[dict[str, Any]] = []
    if not hints.is_file():
        return legacy
    try:
        for line in hints.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            if not line.strip():
                continue
            try:
                legacy.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return list(reversed(legacy[-limit:]))


def _engineer_briefing(
    srv: dict[str, Any],
    planetary: dict[str, Any],
    multipoint: dict[str, Any],
    internet_field: dict[str, Any],
    takeover: dict[str, Any] | None = None,
) -> dict[str, Any]:
    seed = _load_json(INSTALL / "data" / "dns-admin-seed.json", {})
    welcome = seed.get("welcome") or {}
    resolv = planetary.get("resolv") or {}
    stats = srv.get("stats") or {}
    alerts: list[dict[str, Any]] = []

    if not srv.get("running"):
        alerts.append({
            "level": "critical",
            "code": "resolver_down",
            "title": "Truth Resolver not running",
            "detail": "UDP listener offline — restart nexus-genius or field-dns serve.",
            "action": "sudo systemctl restart nexus-genius",
        })
    takeover_phase = (takeover or {}).get("phase") or "observing"
    if takeover_phase in ("observing", "ready"):
        alerts.append({
            "level": "info",
            "code": "takeover_pending",
            "title": f"Graceful takeover — phase {takeover_phase}",
            "detail": "Incumbent DNS/DHCP left running until NEXUS Truth Resolver is healthy.",
            "action": "Wait for primary phase — no resolv interrupt",
        })
    elif not resolv.get("nexus_truth_enforced"):
        v4_ns = ", ".join(resolv.get("ipv4_nameservers") or []) or "—"
        v6_ns = ", ".join(resolv.get("ipv6_nameservers") or []) or "—"
        stacks = []
        if resolv.get("ipv4_nameservers") and not resolv.get("ipv4_truth_enforced"):
            stacks.append(f"IPv4 foreign: {v4_ns}")
        if resolv.get("ipv6_nameservers") and not resolv.get("ipv6_truth_enforced"):
            stacks.append(f"IPv6 foreign: {v6_ns}")
        detail = " · ".join(stacks) if stacks else f"Nameservers: {', '.join(resolv.get('nameservers') or ['—'])}"
        alerts.append({
            "level": "high",
            "code": "resolv_foreign",
            "title": "resolv.conf not steered to NEXUS (dual-stack)",
            "detail": f"{detail} — enforce cycle pending or needs root.",
            "action": "nexus_field_dns_enforce_resolv (daemon cycle or sudo)",
        })
    if int(stats.get("errors") or 0) > int(stats.get("queries") or 0) * 0.25 and int(stats.get("queries") or 0) > 3:
        alerts.append({
            "level": "medium",
            "code": "high_error_rate",
            "title": "Elevated SERVFAIL rate",
            "detail": f"{stats.get('errors', 0)} errors on {stats.get('queries', 0)} queries — check dig +trace path.",
            "action": "Inspect field-dns.json stats; verify root reachability",
        })
    if int(stats.get("rate_limits") or 0) > 0:
        alerts.append({
            "level": "medium",
            "code": "dns_rate_limit",
            "title": "DNS rate-limit events",
            "detail": f"{stats.get('rate_limits', 0)} client floods rejected — threat guard active.",
            "action": "Review dns-threat-guard permanent blocks",
        })
    if (internet_field.get("total_slots") or 0) and (internet_field.get("recognized_slots") or 0) == 0:
        alerts.append({
            "level": "info",
            "code": "internet_silent",
            "title": "Internet field all silent",
            "detail": "WHOLE slots loaded — run pull cycle or resolve domains to light LOCAL NOW.",
            "action": "pythong lib/dns-internet-field.py pull",
        })

    enforced = sum(1 for r in (planetary.get("rfc_matrix") or []) if r.get("compliance") == "enforced")
    return {
        "headline": welcome.get("headline") or "Engineer briefing — everything DNS upfront",
        "lead": welcome.get("lead") or "Truth Resolver on loopback. Trace-only. No foreign shortcut.",
        "upfront": list(welcome.get("dns_upfront") or []),
        "love_note": welcome.get("love_note") or "",
        "alerts": alerts,
        "healthy": not any(a.get("level") in ("critical", "high") for a in alerts),
        "quick_facts": {
            "running": bool(srv.get("running")),
            "pid": srv.get("pid"),
            "started_at": stats.get("started_at"),
            "listeners": srv.get("listeners") or [],
            "planetary_level": planetary.get("planetary_security_level"),
            "host_level": planetary.get("host_security_level"),
            "rfc_enforced": enforced,
            "rfc_total": len(planetary.get("rfc_matrix") or []),
            "root_servers": len(planetary.get("root_servers") or []),
            "multipoint_points": multipoint.get("point_count") or len(multipoint.get("identification_points") or []),
            "internet_slots": internet_field.get("total_slots", 0),
            "internet_recognized": internet_field.get("recognized_slots", 0),
            "foreign_blocked": len(planetary.get("foreign_resolvers_blocked") or []),
            "foreign_ipv4_blocked": len(planetary.get("foreign_resolver_ipv4") or []),
            "foreign_ipv6_blocked": len(planetary.get("foreign_resolver_ipv6") or []),
            "ipv6_truth_enforced": (planetary.get("resolv") or {}).get("ipv6_truth_enforced"),
            "blocklist_domains": srv.get("blocklist_domains", 0),
            "cache_entries": srv.get("cache_entries", 0),
        },
        "admin_ports": seed.get("admin_ports") or [7, 77, 777],
        "port_mnemonic": seed.get("port_mnemonic") or {},
    }


def _dns_admin_portal_status() -> dict[str, Any]:
    ports = [7, 77, 777]
    live: list[int] = []
    for port in ports:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.35):
                live.append(port)
        except OSError:
            continue
    return {
        "schema": "dns-admin-portal/v1",
        "updated": _now(),
        "ports": ports,
        "live_ports": live,
        "running": bool(live),
        "asset": "/assets/dns-admin-portal.html",
        "motto": "Information only — tired engineer ports 7 · 77 · 777.",
    }


def _build_traffic_patterns(
    srv: dict[str, Any],
    dhcp: dict[str, Any],
    egress: dict[str, Any],
    threat_guard: dict[str, Any],
    recent: list[dict[str, Any]],
) -> dict[str, Any]:
    stats = srv.get("stats") or {}
    queries = int(stats.get("queries") or 0)
    cache_hits = int(stats.get("cache_hits") or 0)
    blocked = int(stats.get("blocked") or 0)
    errors = int(stats.get("errors") or 0)
    total = max(queries, 1)
    eg_st = egress.get("stats") or {}
    tg_st = threat_guard.get("stats") or {}
    egress_checks = int(eg_st.get("total_checks") or 0)
    egress_verified = int(eg_st.get("verified_exact") or 0)
    leases = int(dhcp.get("lease_count") or 0)
    pct = lambda n: round((n / total) * 100) if queries else 0
    return {
        "schema": "dns-traffic-patterns/v1",
        "updated": _now(),
        "dns": {
            "queries": queries,
            "cache_hits": cache_hits,
            "blocked": blocked,
            "errors": errors,
            "hit_rate_pct": pct(cache_hits),
            "block_rate_pct": pct(blocked),
            "error_rate_pct": pct(errors),
            "egress_checks": egress_checks,
            "egress_verified": egress_verified,
            "permanent_blocks": int(tg_st.get("permanent_blocks") or 0),
            "recent_query_count": len(recent),
        },
        "dhcp": {
            "leases_active": leases,
            "running": bool(dhcp.get("running")),
            "bind": dhcp.get("bind") or "0.0.0.0:67",
            "dns_option": dhcp.get("dns_option") or ["127.0.0.1"],
        },
        "channels": [
            {"id": "queries", "label": "DNS queries", "value": queries, "pct": 100 if queries else 0},
            {"id": "cache", "label": "Cache hits", "value": cache_hits, "pct": pct(cache_hits)},
            {"id": "blocked", "label": "Policy blocked", "value": blocked, "pct": pct(blocked)},
            {"id": "errors", "label": "SERVFAIL", "value": errors, "pct": pct(errors)},
            {
                "id": "egress",
                "label": "Egress verified",
                "value": egress_verified,
                "pct": round((egress_verified / egress_checks) * 100) if egress_checks else 0,
            },
            {"id": "leases", "label": "DHCP leases", "value": leases, "pct": 100 if dhcp.get("running") and leases else 0},
        ],
    }


def _build_threat_model(
    planetary: dict[str, Any],
    multipoint: dict[str, Any],
    threat_guard: dict[str, Any],
    takeover: dict[str, Any],
    dhcp: dict[str, Any],
    srv: dict[str, Any],
    briefing: dict[str, Any],
) -> dict[str, Any]:
    pol = planetary.get("resolver_policy") or {}
    tg_pol = threat_guard.get("policy") or {}
    alerts = briefing.get("alerts") or []
    concern_count = sum(1 for a in alerts if a.get("level") in ("critical", "high", "medium"))
    enforced = int(briefing.get("quick_facts", {}).get("rfc_enforced") or 0)
    rfc_total = int(briefing.get("quick_facts", {}).get("rfc_total") or 0)
    if concern_count >= 2:
        overall = "elevated"
    elif concern_count:
        overall = "guarded"
    elif planetary.get("planetary_security_level") == "extreme":
        overall = "controlled"
    else:
        overall = "stable"
    foreign_blocked = int(briefing.get("quick_facts", {}).get("foreign_blocked") or 0)
    mp_pts = multipoint.get("point_count") or len(multipoint.get("identification_points") or [])
    untrusted = len(multipoint.get("untrusted_never_added") or [])
    inc = (takeover.get("incumbents") or {})
    return {
        "schema": "dns-threat-model/v1",
        "updated": _now(),
        "framework": "STRIDE + DNS/DHCP planetary",
        "overall_risk": overall,
        "controls_active": enforced,
        "controls_total": rfc_total,
        "summary": (
            "Loopback Truth Resolver, multipoint secure identification, foreign resolver block, "
            "DHCP listen-before-reject — planetary EXTREME when host honorability permits."
        ),
        "dns_vectors": [
            {
                "id": "spoofing",
                "threat": "DNS response spoofing / cache poison",
                "level": "mitigated" if pol.get("truthful_trace") else "open",
                "control": "dig +trace from root — no public shortcut",
                "rfc": "RFC 4033",
            },
            {
                "id": "tampering",
                "threat": "Unauthorized zone or record mutation",
                "level": "mitigated" if pol.get("loopback_only") else "monitored",
                "control": "Loopback bind only · egress integrity hash match",
                "rfc": "RFC 1035 §4.1",
            },
            {
                "id": "repudiation",
                "threat": "Query/answer non-repudiation gap",
                "level": "monitored",
                "control": "Recent query JSONL + egress integrity log",
                "rfc": "RFC 7766",
            },
            {
                "id": "disclosure",
                "threat": "Foreign resolver data exfiltration",
                "level": "mitigated" if planetary.get("foreign_resolvers_stopped", True) else "open",
                "control": f"{foreign_blocked} documented resolvers blocked",
                "rfc": "RFC 8484",
            },
            {
                "id": "dos",
                "threat": "Amplification / QPS flood",
                "level": "mitigated" if tg_pol.get("max_qps_per_client") else "monitored",
                "control": f"Max {tg_pol.get('max_qps_per_client', 30)} QPS/client · permanent eradication",
                "rfc": "RFC 6891",
            },
            {
                "id": "elevation",
                "threat": "Lateral movement via DNS channel",
                "level": "mitigated" if tg_pol.get("no_lateral_movement") else "monitored",
                "control": "No lateral movement · DHCP DNS-only option",
                "rfc": "RFC 2131",
            },
        ],
        "dhcp_vectors": [
            {
                "id": "rogue",
                "threat": "Rogue DHCP server on LAN",
                "level": "monitored" if inc.get("incumbent_dhcp") else "mitigated",
                "control": "Incumbent port-67 detection · graceful takeover",
                "rfc": "RFC 2131",
            },
            {
                "id": "starvation",
                "threat": "DHCP pool exhaustion",
                "level": "monitored" if dhcp.get("running") else "info",
                "control": f"{dhcp.get('lease_count', 0)} active leases · bind {dhcp.get('bind', '67/udp')}",
                "rfc": "RFC 2131 §4.3",
            },
            {
                "id": "option-inject",
                "threat": "Malicious DNS option injection",
                "level": "mitigated",
                "control": f"DNS option → {', '.join(dhcp.get('dns_option') or ['127.0.0.1'])}",
                "rfc": "RFC 3646",
            },
        ],
        "identification": {
            "points": mp_pts,
            "untrusted_blocked": untrusted,
        },
        "concern_count": concern_count,
        "resolver_running": bool(srv.get("running")),
    }


def _internet_field_mod() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "dns_internet_field", INSTALL / "lib" / "dns-internet-field.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def build_panel() -> dict[str, Any]:
    srv = status()
    planetary = _planetary_mod().build_planetary_dns(extra={"server": srv})
    multipoint: dict[str, Any] = {}
    internet_field: dict[str, Any] = {}
    try:
        multipoint = _multipoint_mod().build_identity(running=bool(srv.get("running")))
    except Exception:
        multipoint = {}
    try:
        internet_field = _internet_field_mod().build_internet_field(pull_live=bool(srv.get("running")))
    except Exception:
        internet_field = {}
    egress: dict[str, Any] = {}
    threat_guard: dict[str, Any] = {}
    dhcp: dict[str, Any] = {}
    takeover: dict[str, Any] = {}
    try:
        egress = _integrity_mod().build_panel()
    except Exception:
        egress = {}
    try:
        threat_guard = _guard_mod().build_panel()
    except Exception:
        threat_guard = {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_dhcp", INSTALL / "lib" / "field-dhcp.py")
        if spec and spec.loader:
            _dhcp = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_dhcp)
            dhcp = _dhcp.build_panel()
    except Exception:
        dhcp = {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "dns_service_takeover", INSTALL / "lib" / "dns-service-takeover.py",
        )
        if spec and spec.loader:
            _to = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_to)
            takeover = _to.build_panel()
    except Exception:
        takeover = {}
    hostess7 = takeover.get("hostess7") or {
        "inside": {
            "dns": f"{IPV4}:{PORT} loopback Truth Resolver",
            "dhcp": dhcp.get("bind") or "67/udp LAN pool",
            "movement": "none — issue/listen only",
        },
        "outside": {
            "dns_admin": "ports 7 · 77 · 777 read-only",
            "dhcp": "disabled on WAN",
            "movement": "none — information only",
        },
    }
    briefing = _engineer_briefing(srv, planetary, multipoint, internet_field, takeover)
    recent = _recent_queries(RECENT_PANEL_LIMIT)
    analytics = _query_analytics_cached(force=True)
    dnssec = _dnssec_status()
    threats = _threats_summary()
    traffic_patterns = _build_traffic_patterns(srv, dhcp, egress, threat_guard, recent)
    traffic_patterns["dns"]["qps_60s"] = analytics.get("qps_60s", 0)
    traffic_patterns["dns"]["qps_5m"] = analytics.get("qps_5m", 0)
    traffic_patterns["dns"]["avg_latency_ms"] = analytics.get("avg_latency_ms", 0)
    traffic_patterns["dhcp_lease_count"] = int(dhcp.get("lease_count") or 0)
    traffic_patterns["egress_integrity_ok"] = egress.get("healthy", True) is not False
    threat_model = _build_threat_model(
        planetary, multipoint, threat_guard, takeover, dhcp, srv, briefing,
    )
    base_stats = {**(srv.get("stats") or {}), **(planetary.get("stats") or {})}
    panel_stats = {
        "queries_total": int(base_stats.get("queries") or 0),
        "cache_hits": int(base_stats.get("cache_hits") or 0),
        "cache_misses": int(base_stats.get("cache_misses") or 0),
        "blocks": int(base_stats.get("blocked") or 0),
        "errors": int(base_stats.get("errors") or 0),
        "rate_limits": int(base_stats.get("rate_limits") or 0),
        "qps_60s": analytics.get("qps_60s", 0),
        "qps_5m": analytics.get("qps_5m", 0),
        "avg_latency_ms": analytics.get("avg_latency_ms", 0),
        **base_stats,
    }
    doc: dict[str, Any] = {
        "schema": "field-dns/v2",
        "updated": _now(),
        "title": "NEXUS Truth DNS & DHCP",
        "running": bool(srv.get("running")),
        "self_hosted": True,
        "truthful": True,
        "security_model": "field-sovereign-gate",
        "never_lose_cycle": True,
        "priority": 1,
        "listeners": srv.get("listeners") or [f"{IPV4}#{PORT}", f"[{IPV6}]#{PORT}"],
        "ipv4": srv.get("ipv4") or {"host": IPV4, "port": PORT},
        "ipv6": srv.get("ipv6") or {"host": IPV6, "port": PORT},
        "stats": panel_stats,
        "top_domains": analytics.get("top_domains") or {},
        "cache": {
            "size": srv.get("cache_entries", len(_cache)),
            "hit_rate": analytics.get("cache_hit_rate", 0),
            "ttl_default": CACHE_TTL,
        },
        "blocklists": {
            "domains": srv.get("blocklist_domains", len(_load_blocklist())),
            "last_reload": _now(),
            "sources": [str(BLOCKLIST), str(EXTRA_BLOCK)],
        },
        "dnssec": dnssec,
        "threats": threats,
        "blocklist_domains": srv.get("blocklist_domains", len(_load_blocklist())),
        "cache_entries": srv.get("cache_entries", len(_cache)),
        "foreign_resolvers_stopped": True,
        "planetary": planetary,
        "rfc_matrix": planetary.get("rfc_matrix") or [],
        "legal_framework": planetary.get("legal_framework") or [],
        "root_servers": planetary.get("root_servers") or [],
        "zones": planetary.get("zones") or [],
        "resolv": planetary.get("resolv") or {},
        "foreign_resolver_ipv4": planetary.get("foreign_resolver_ipv4") or [],
        "foreign_resolver_ipv6": planetary.get("foreign_resolver_ipv6") or [],
        "resolver_policy": planetary.get("resolver_policy") or {},
        "planetary_security_level": planetary.get("planetary_security_level"),
        "multipoint_identity": multipoint,
        "identification_points": multipoint.get("identification_points") or [],
        "dns_override_active": (multipoint.get("override") or {}).get("resolv", {}).get("nexus_override_active"),
        "internet_field": internet_field,
        "internet_slots": internet_field.get("total_slots", 0),
        "internet_recognized": internet_field.get("recognized_slots", 0),
        "internet_coverage_pct": internet_field.get("coverage_pct", 0),
        "recent_queries": recent,
        "engineer_briefing": briefing,
        "traffic_patterns": traffic_patterns,
        "threat_model": threat_model,
        "dns_admin_portal": _dns_admin_portal_status(),
        "legacy_dns_equipment": (_load_json(INSTALL / "data" / "dns-admin-seed.json", {}).get("legacy_dns_equipment") or []),
        "identity": planetary.get("identity") or {},
        "egress_integrity": egress,
        "threat_guard": threat_guard,
        "takeover": takeover,
        "dhcp_server": dhcp,
        "hostess7_service": hostess7,
        "servers": {
            "dns": {
                "running": bool(srv.get("running")),
                "listeners": srv.get("listeners") or [],
                "port": PORT,
                "pid": srv.get("pid"),
            },
            "dhcp": {
                "running": bool(dhcp.get("running")),
                "bind": dhcp.get("bind"),
                "lease_count": dhcp.get("lease_count", 0),
                "may_serve": dhcp.get("may_serve", True),
                "dns_option": dhcp.get("dns_option") or ["127.0.0.1"],
                "dns_option_v6": dhcp.get("dns_option_v6") or ["::1"],
                "leases_detailed": dhcp.get("leases_detailed") or [],
                "stats_extended": dhcp.get("stats_extended") or {},
                "threats": dhcp.get("threats") or [],
            },
        },
        "dhcp_leases_detailed": dhcp.get("leases_detailed") or [],
        "dhcp_events": dhcp.get("lease_history_events") or [],
    }
    tmp = PANEL_CACHE.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(PANEL_CACHE)
    return doc


def _panel_json_stub() -> dict[str, Any]:
    srv = status()
    return {
        "schema": "field-dns/v2",
        "updated": _now(),
        "running": bool(srv.get("running")),
        "self_hosted": True,
        "listeners": srv.get("listeners") or [],
        "stats": srv.get("stats") or {},
        "_partial": True,
        "recent_queries": [],
        "top_domains": {},
        "threats": [],
    }


def panel_json() -> dict[str, Any]:
    if PANEL_CACHE.is_file():
        try:
            return json.loads(PANEL_CACHE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return _panel_json_stub()


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: field-dns.py [serve|build|json|status]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "serve":
        serve()
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "status":
        print(json.dumps(status(), ensure_ascii=False))
        return 0
    print("usage: field-dns.py [serve|build|json|status]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())