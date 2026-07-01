#!/usr/bin/env pythong
"""DNS/DHCP graceful takeover — observe incumbents, never interrupt on arrival."""
from __future__ import annotations

import json
import os
import re
import socket
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE_FILE = STATE / "dns-takeover-state.json"
PANEL_CACHE = STATE / "dns-takeover-panel.json"

DNS_PORT = int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53"))
DHCP_PORT = 67
HEALTH_HOST = os.environ.get("NEXUS_FIELD_DNS_IPV4", "127.0.0.1")
READY_CHECKS = int(os.environ.get("NEXUS_DNS_TAKEOVER_READY_CHECKS", "2"))
HEALTH_QUERY = os.environ.get("NEXUS_DNS_TAKEOVER_HEALTH_QNAME", "example.com")

PHASES = ("observing", "ready", "primary")


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



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


def _run(cmd: list[str], timeout: int = 6) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
        return (proc.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _port_in_use(port: int, proto: str = "udp") -> bool:
    flag = "-u" if proto == "udp" else "-t"
    out = _run(["ss", "-H", "-l", "-n", flag, f"sport = :{port}"])
    if out:
        return True
    out = _run(["ss", "-H", "-l", "-n", flag, f"dport = :{port}"])
    if out:
        return True
    try:
        fam = socket.AF_INET if proto == "udp" else socket.SOCK_STREAM
        typ = socket.SOCK_DGRAM if proto == "udp" else socket.SOCK_STREAM
        sock = socket.socket(fam, typ)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", port))
        sock.close()
        return False
    except OSError:
        return True


def _listener_rows(port: int, proto: str = "udp") -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    flag = "-u" if proto == "udp" else "-t"
    for filt in (f"sport = :{port}", f"dport = :{port}"):
        out = _run(["ss", "-H", "-l", "-n", flag, filt])
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            addr = parts[3] if len(parts) > 3 else ""
            proc = parts[-1] if "users:" in line else ""
            rows.append({"proto": proto, "port": port, "bind": addr, "raw": line, "process_hint": proc})
    return rows


def _systemd_resolved_active() -> bool:
    if Path("/run/systemd/resolve/stub-resolv.conf").is_file():
        return True
    out = _run(["systemctl", "is-active", "systemd-resolved"])
    return out.strip() == "active"


def _read_resolv() -> dict[str, Any]:
    path = Path("/etc/resolv.conf")
    doc: dict[str, Any] = {
        "path": str(path),
        "is_symlink": path.is_symlink(),
        "nameservers": [],
        "search_domains": [],
        "nexus_truth_enforced": False,
    }
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return doc
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("nameserver"):
            ns = line.split()[1] if len(line.split()) > 1 else ""
            if ns:
                doc["nameservers"].append(ns)
        elif line.startswith("search"):
            doc["search_domains"] = line.split()[1:]
        elif "NEXUS Truth DNS" in line or "NEXUS_FIELD_DNS" in line:
            doc["nexus_truth_enforced"] = True
    if not doc["nexus_truth_enforced"]:
        doc["nexus_truth_enforced"] = (
            "127.0.0.1" in doc["nameservers"] and ("::1" in doc["nameservers"] or len(doc["nameservers"]) == 1)
        )
    return doc


def _nexus_dns_running() -> bool:
    pid_file = STATE / "field-dns.pid"
    if not pid_file.is_file():
        return False
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip().split()[0])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _nexus_dhcp_running() -> bool:
    pid_file = STATE / "field-dhcp.pid"
    if not pid_file.is_file():
        return False
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip().split()[0])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _encode_name(name: str) -> bytes:
    out = bytearray()
    for label in name.rstrip(".").split("."):
        raw = label.encode("ascii")[:63]
        out.append(len(raw))
        out.extend(raw)
    out.append(0)
    return bytes(out)


def _dns_query(host: str, qname: str, port: int = DNS_PORT, timeout: float = 2.5) -> tuple[bool, bytes]:
    txn = struct.pack("!H", int(time.time()) & 0xFFFF)
    header = txn + struct.pack("!HHHHH", 0x0100, 1, 0, 0, 0)
    packet = header + _encode_name(qname) + struct.pack("!HH", 1, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(packet, (host, port))
        data, _ = sock.recvfrom(4096)
        return len(data) >= 12, data
    except OSError:
        return False, b""
    finally:
        sock.close()


def _resolver_health() -> dict[str, Any]:
    running = _nexus_dns_running()
    ok, payload = _dns_query(HEALTH_HOST, HEALTH_QUERY) if running else (False, b"")
    rcode = (payload[3] & 0xF) if len(payload) >= 4 else -1
    healthy = running and ok and rcode in (0, 3)
    return {
        "running": running,
        "probe_ok": ok,
        "rcode": rcode,
        "healthy": healthy,
        "host": HEALTH_HOST,
        "port": DNS_PORT,
        "qname": HEALTH_QUERY,
    }


def detect_incumbents() -> dict[str, Any]:
    dns_udp = _listener_rows(DNS_PORT, "udp")
    dns_tcp = _listener_rows(DNS_PORT, "tcp")
    dhcp_udp = _listener_rows(DHCP_PORT, "udp")
    dns_busy = _port_in_use(DNS_PORT, "udp") or _port_in_use(DNS_PORT, "tcp")
    dhcp_busy = _port_in_use(DHCP_PORT, "udp")
    resolved = _systemd_resolved_active()
    resolv = _read_resolv()
    foreign_ns = [n for n in resolv.get("nameservers") or [] if n not in ("127.0.0.1", "::1", "127.0.0.53")]
    return {
        "dns_port_busy": dns_busy,
        "dhcp_port_busy": dhcp_busy,
        "dns_listeners": dns_udp + dns_tcp,
        "dhcp_listeners": dhcp_udp,
        "systemd_resolved": resolved,
        "resolv": resolv,
        "foreign_nameservers": foreign_ns,
        "incumbent_dns": dns_busy or resolved or bool(foreign_ns),
        "incumbent_dhcp": dhcp_busy,
        "nexus_dns_running": _nexus_dns_running(),
        "nexus_dhcp_running": _nexus_dhcp_running(),
    }


def _advance_phase(
    prev_phase: str,
    streak: int,
    health: dict[str, Any],
    inc: dict[str, Any],
) -> str:
    phase = prev_phase or "observing"

    if phase == "observing":
        if health.get("healthy") and streak >= 1:
            return "ready"
        return "observing"

    if phase == "ready":
        if not health.get("healthy"):
            return "observing"
        if streak >= READY_CHECKS:
            vacant = not inc.get("incumbent_dhcp") and (
                not inc.get("incumbent_dns") or inc.get("nexus_dns_running")
            )
            if vacant or streak >= READY_CHECKS + 1:
                return "primary"
        return "ready"

    if phase == "primary":
        if not health.get("healthy"):
            return "ready"
        return "primary"

    return "observing"


def evaluate_takeover(*, persist: bool = True) -> dict[str, Any]:
    prev = _load_json(STATE_FILE, {})
    inc = detect_incumbents()
    health = _resolver_health()
    prev_streak = int(prev.get("healthy_streak") or 0)
    streak = prev_streak + 1 if health.get("healthy") else 0
    phase = _advance_phase(str(prev.get("phase") or "observing"), streak, health, inc)

    can_enforce_resolv = phase == "primary"
    can_serve_dhcp = phase == "primary" and not inc.get("incumbent_dhcp")
    can_capture_egress = phase == "primary"

    doc: dict[str, Any] = {
        "schema": "dns-takeover/v1",
        "updated": _now(),
        "phase": phase,
        "healthy_streak": streak,
        "motto": "Listen and learn first — takeover only when NEXUS resolver is healthy.",
        "policy": {
            "never_interrupt_on_arrival": True,
            "listen_before_reject": True,
            "dhcp_dns_only": True,
            "no_lateral_movement": True,
        },
        "health": health,
        "incumbents": inc,
        "permissions": {
            "enforce_resolv": can_enforce_resolv,
            "serve_dhcp": can_serve_dhcp,
            "local_capture": can_capture_egress,
            "break_resolv_symlink": can_enforce_resolv,
        },
        "hostess7": {
            "inside": {
                "dns": "Truth Resolver loopback — primary after graceful takeover",
                "dhcp": "LAN pool when port 67 vacant",
                "movement": "none",
            },
            "outside": {
                "dns_admin": "ports 7 · 77 · 777 read-only",
                "dhcp": "disabled on WAN",
                "movement": "none",
            },
        },
        "phase_history": (prev.get("phase_history") or [])[-12:],
    }
    if phase != prev.get("phase"):
        doc["phase_history"] = (doc["phase_history"] or []) + [{
            "ts": _now(),
            "from": prev.get("phase") or "observing",
            "to": phase,
            "healthy": health.get("healthy"),
        }]
    if persist:
        _save_json(STATE_FILE, doc)
        _save_json(PANEL_CACHE, doc)
    return doc


def current_phase() -> str:
    doc = _load_json(STATE_FILE, {})
    if doc.get("phase"):
        return str(doc["phase"])
    return evaluate_takeover(persist=True).get("phase", "observing")


def can_enforce_resolv() -> bool:
    return evaluate_takeover(persist=False).get("permissions", {}).get("enforce_resolv", False)


def can_serve_dhcp() -> bool:
    return evaluate_takeover(persist=False).get("permissions", {}).get("serve_dhcp", False)


def build_panel() -> dict[str, Any]:
    return evaluate_takeover(persist=True)


def panel_json() -> dict[str, Any]:
    cached = _load_json(PANEL_CACHE, {})
    if cached.get("updated"):
        return cached
    return build_panel()


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False))
        return 0
    if cmd == "build":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "phase":
        print(current_phase())
        return 0
    if cmd == "evaluate":
        print(json.dumps(evaluate_takeover(persist=True), ensure_ascii=False))
        return 0
    if cmd == "can-enforce-resolv":
        print("1" if can_enforce_resolv() else "0")
        return 0
    if cmd == "can-serve-dhcp":
        print("1" if can_serve_dhcp() else "0")
        return 0
    print(json.dumps({"error": "usage: dns-service-takeover.py [json|build|phase|evaluate|can-enforce-resolv|can-serve-dhcp]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())