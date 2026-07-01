#!/usr/bin/env pythong
"""NEXUS Packet Field — tcpdump capture, TX/RX classification, field jsonl + realtime panel feed."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_dpi_spec = importlib.util.spec_from_file_location("packet_dpi", Path(__file__).with_name("packet-dpi.py"))
_dpi_mod = importlib.util.module_from_spec(_dpi_spec)
assert _dpi_spec and _dpi_spec.loader
_dpi_spec.loader.exec_module(_dpi_mod)
analyze_packet = _dpi_mod.analyze_packet
summarize_inspect = _dpi_mod.summarize_inspect

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
OUT_JSON = STATE / "packet-field.json"
RING_PATH = STATE / "packet-field.ring.jsonl"
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
HOSTESS7_TEAM_FIELD = Path(os.environ.get("HOSTESS7_TEAM_FIELD", "/media/default/HOSTESS7_TEAM/fieldstorage"))
PACKET_MEMORY_FILE = os.environ.get("NEXUS_PACKET_MEMORY_FILE", "nexus-packets.jsonl")
CAPTURE_COUNT = int(os.environ.get("NEXUS_PACKET_FIELD_CAPTURE", "32"))
RING_MAX = int(os.environ.get("NEXUS_PACKET_FIELD_RING", "400"))
CAPTURE_TIMEOUT = int(os.environ.get("NEXUS_PACKET_FIELD_TIMEOUT", "4"))

PORT_SERVICES: dict[int, str] = {
    20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "TELNET", 25: "SMTP", 53: "DNS",
    67: "DHCP", 68: "DHCP", 80: "HTTP", 110: "POP3", 123: "NTP", 143: "IMAP",
    161: "SNMP", 194: "IRC", 443: "HTTPS", 445: "SMB", 465: "SMTPS", 587: "SMTP",
    853: "DNS-TLS", 993: "IMAPS", 995: "POP3S", 1080: "SOCKS", 1194: "OpenVPN",
    1433: "MSSQL", 1723: "PPTP", 1883: "MQTT", 2049: "NFS", 3000: "Dev-HTTP",
    3128: "Proxy", 3306: "MySQL", 3389: "RDP", 4443: "HTTPS-Alt", 4444: "Metasploit",
    5000: "UPnP", 5432: "PostgreSQL", 5555: "ADB", 5900: "VNC", 6006: "X11",
    6379: "Redis", 6667: "IRC", 8000: "HTTP-Alt", 8080: "HTTP-Proxy", 8443: "HTTPS-Alt",
    8888: "HTTP-Alt", 9001: "Tor-OR", 9050: "Tor-SOCKS", 27017: "MongoDB",
}

IP4_PKT = re.compile(
    r"^(?P<epoch>\d+\.\d+)\s+(?:\S+\s+)?(?P<flow>In|Out)?\s*IP\s+"
    r"(?P<src>[\d.]+)\.(?P<sport>\d+)\s+>\s+"
    r"(?P<dst>[\d.]+)\.(?P<dport>\d+):\s+"
    r"(?P<rest>.+)$"
)
UDP_PKT = re.compile(
    r"^(?P<epoch>\d+\.\d+)\s+(?:\S+\s+)?(?P<flow>In|Out)?\s*IP\s+"
    r"(?P<src>[\d.]+)\.(?P<sport>\d+)\s+>\s+"
    r"(?P<dst>[\d.]+)\.(?P<dport>\d+):\s+UDP,\s+length\s+(?P<length>\d+)"
)
SS_LINE = re.compile(
    r"^(?P<proto>tcp|udp|tcp6|udp6)\s+(?P<state>\S+)\s+\S+\s+\S+\s+"
    r"(?P<local>\S+)\s+(?P<remote>\S+)"
)
SS_PROC = re.compile(r'users:\(\("([^"]+)"(?:,pid=(\d+))?')


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


def _field_paths() -> list[Path]:
    return [
        HOSTESS7_ROOT / "cache" / "fieldstorage" / "brain" / "security" / PACKET_MEMORY_FILE,
        HOSTESS7_TEAM_FIELD / "brain" / "security" / PACKET_MEMORY_FILE,
        STATE / "field-storage" / "brain" / "security" / PACKET_MEMORY_FILE,
        STATE / "field-storage" / PACKET_MEMORY_FILE,
    ]


def _local_addresses() -> set[str]:
    addrs: set[str] = {"127.0.0.1", "::1"}
    try:
        addrs.add(socket.gethostbyname(socket.gethostname()))
    except OSError:
        pass
    try:
        proc = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope", "global"], capture_output=True, text=True, timeout=5)
        for line in (proc.stdout or "").splitlines():
            parts = line.split()
            if len(parts) >= 4:
                addrs.add(parts[3].split("/")[0])
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        proc = subprocess.run(["ss", "-H", "-tunap"], capture_output=True, text=True, timeout=8)
        for line in (proc.stdout or "").splitlines():
            m = SS_LINE.match(line.strip())
            if not m:
                continue
            ep = m.group("local")
            host = ep.rsplit(":", 1)[0] if ep else ""
            if host and host not in ("*", "0.0.0.0", "[::]"):
                addrs.add(host.strip("[]"))
    except (OSError, subprocess.TimeoutExpired):
        pass
    return addrs


def _connection_index() -> dict[str, dict[str, Any]]:
    """Map 'local_ip:local_port|remote_ip:remote_port' -> process info."""
    index: dict[str, dict[str, Any]] = {}
    try:
        proc = subprocess.run(["ss", "-H", "-tunap"], capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return index
    for line in (proc.stdout or "").splitlines():
        stripped = line.strip()
        m = SS_LINE.match(stripped)
        if not m or m.group("state") not in ("ESTAB", "ESTABLISHED", "SYN-SENT", "SYN-RECV"):
            continue
        local, remote = m.group("local"), m.group("remote")
        pm = SS_PROC.search(stripped)
        proc_name = pm.group(1) if pm else ""
        pid = pm.group(2) if pm else ""
        entry = {"process": proc_name, "pid": pid, "proto": m.group("proto"), "state": m.group("state")}
        for key in (f"{local}|{remote}", f"{remote}|{local}"):
            index[key] = entry
        lip, lport = _split_endpoint(local)
        rip, rport = _split_endpoint(remote)
        if lip and lport:
            index[f"port:{lport}|{rip}:{rport}"] = entry
            index[f"port:{lport}|{rip}"] = entry
    return index


def _split_endpoint(ep: str) -> tuple[str, str]:
    if not ep or ep == "*":
        return "", ""
    if ep.startswith("["):
        host, _, port = ep[1:].partition("]:")
        return host, port
    if ":" in ep:
        host, port = ep.rsplit(":", 1)
        return host, port
    return ep, ""


def _port_service(port: int) -> str:
    return PORT_SERVICES.get(port, f"port-{port}")


def _classify_direction(src: str, dst: str, local_addrs: set[str], flow: str | None = None) -> str:
    src_local = src in local_addrs
    dst_local = dst in local_addrs
    if src_local and dst_local:
        return "LAN"
    if src_local:
        return "TX"
    if dst_local:
        return "RX"
    if flow == "Out":
        return "TX"
    if flow == "In":
        return "RX"
    return "TRANSIT"


def _parse_tcp_flags(rest: str) -> tuple[str, int]:
    flags = ""
    length = 0
    fm = re.search(r"Flags\s+\[([^\]]+)\]", rest)
    if fm:
        flags = fm.group(1)
    lm = re.search(r"length\s+(\d+)", rest)
    if lm:
        length = int(lm.group(1))
    return flags, length


def _lookup_process(src: str, sport: int, dst: str, dport: int, conn_idx: dict[str, dict[str, Any]]) -> dict[str, Any]:
    keys = [
        f"{src}:{sport}|{dst}:{dport}",
        f"{dst}:{dport}|{src}:{sport}",
        f"port:{sport}|{dst}:{dport}",
        f"port:{dport}|{src}:{sport}",
        f"port:{sport}|{dst}",
        f"port:{dport}|{src}",
    ]
    for key in keys:
        if key in conn_idx:
            return conn_idx[key]
    return {}


def _english_summary(pkt: dict[str, Any]) -> str:
    direction = pkt.get("direction", "?")
    proc = pkt.get("process") or "unknown app"
    proto = (pkt.get("protocol") or "ip").upper()
    sport = pkt.get("src_port")
    dport = pkt.get("dst_port")
    src = pkt.get("src_ip")
    dst = pkt.get("dst_ip")
    svc = pkt.get("port_service") or _port_service(int(dport or sport or 0))
    length = pkt.get("length") or 0
    flags = pkt.get("flags") or ""

    if direction == "TX":
        verb = "Your PC sent"
        path = f"{proc} :{sport} → {dst}:{dport} ({svc})"
    elif direction == "RX":
        verb = "Your PC received"
        path = f"{dst}:{dport} ← {src}:{sport} ({svc}) via {proc}"
    elif direction == "LAN":
        verb = "Local LAN traffic"
        path = f"{src}:{sport} ↔ {dst}:{dport} ({svc}) · {proc}"
    else:
        verb = "Transit (not local)"
        path = f"{src}:{sport} → {dst}:{dport}"

    detail = []
    if flags:
        detail.append(f"TCP [{flags}]")
    if length:
        detail.append(f"{length} bytes")
    detail_s = " · ".join(detail) if detail else proto
    return f"{direction} · {verb} — {path} · {detail_s}"


def parse_tcpdump_line(line: str, local_addrs: set[str], conn_idx: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    line = line.strip()
    if not line or line.startswith("tcpdump:"):
        return None

    m = UDP_PKT.match(line)
    if m:
        epoch = float(m.group("epoch"))
        src, sport = m.group("src"), int(m.group("sport"))
        dst, dport = m.group("dst"), int(m.group("dport"))
        length = int(m.group("length"))
        flow = m.group("flow")
        direction = _classify_direction(src, dst, local_addrs, flow)
        proc_info = _lookup_process(src, sport, dst, dport, conn_idx)
        remote_port = dport if direction == "TX" else sport
        record: dict[str, Any] = {
            "kind": "nexus_packet",
            "ts": datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "epoch": epoch,
            "direction": direction,
            "protocol": "udp",
            "src_ip": src,
            "src_port": sport,
            "dst_ip": dst,
            "dst_port": dport,
            "flags": "",
            "length": length,
            "process": proc_info.get("process", ""),
            "pid": proc_info.get("pid", ""),
            "port_service": _port_service(remote_port),
            "tcpdump_flow": flow or "",
            "raw": line[:500],
        }
        record["english"] = _english_summary(record)
        return _enrich_dpi(record)

    m = IP4_PKT.match(line)
    if not m:
        return None

    epoch = float(m.group("epoch"))
    src, sport = m.group("src"), int(m.group("sport"))
    dst, dport = m.group("dst"), int(m.group("dport"))
    rest = m.group("rest")
    flags, length = _parse_tcp_flags(rest)
    flow = m.group("flow")
    direction = _classify_direction(src, dst, local_addrs, flow)
    proc_info = _lookup_process(src, sport, dst, dport, conn_idx)
    remote_port = dport if direction == "TX" else sport
    proto = "tcp"
    if rest.startswith("UDP"):
        proto = "udp"

    record = {
        "kind": "nexus_packet",
        "ts": datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "epoch": epoch,
        "direction": direction,
        "protocol": proto,
        "src_ip": src,
        "src_port": sport,
        "dst_ip": dst,
        "dst_port": dport,
        "flags": flags,
        "length": length,
        "process": proc_info.get("process", ""),
        "pid": proc_info.get("pid", ""),
        "port_service": _port_service(remote_port),
        "tcpdump_flow": flow or "",
        "raw": line[:500],
    }
    record["english"] = _english_summary(record)
    return _enrich_dpi(record)


def _intent_index() -> dict[str, dict[str, Any]]:
    path = STATE / "connection-intent.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    idx: dict[str, dict[str, Any]] = {}
    for row in doc.get("connections") or []:
        rip = str(row.get("remote_ip") or "")
        rport = str(row.get("remote_port") or "")
        proc = str(row.get("process") or "")
        if not rip:
            continue
        for key in (f"{rip}:{rport}:{proc}", f"{rip}:{rport}:"):
            idx[key] = {
                "verdict": row.get("verdict"),
                "trust_rank": row.get("trust_rank"),
                "intent": row.get("intent") or {},
                "flow_policy": row.get("flow_policy") or {},
                "reason": row.get("reason"),
            }
    return idx


def _enrich_dpi(record: dict[str, Any]) -> dict[str, Any]:
    dpi = analyze_packet(record)
    record["dpi"] = dpi
    record["translation"] = dpi.get("translation") or record.get("english", "")
    if dpi.get("alert"):
        record["dpi_alert"] = True
    direction = record.get("direction", "")
    remote_ip = record.get("dst_ip") if direction == "TX" else record.get("src_ip")
    remote_port = str(record.get("dst_port") if direction == "TX" else record.get("src_port") or "")
    proc = record.get("process") or ""
    idx = _intent_index()
    flow = idx.get(f"{remote_ip}:{remote_port}:{proc}") or idx.get(f"{remote_ip}:{remote_port}:")
    if flow:
        record["flow_intent"] = flow.get("intent") or {}
        record["flow_policy"] = flow.get("flow_policy") or {}
        if not (dpi.get("intent") or {}).get("purpose") and flow.get("reason"):
            dpi.setdefault("intent", {})["purpose"] = flow["reason"]
    else:
        record["flow_intent"] = dpi.get("intent") or {}
        record["flow_policy"] = {"permit": dpi.get("permit_fast", False), "block_scope": "none"}
    record["permit"] = bool((record.get("flow_policy") or {}).get("permit") or dpi.get("permit_fast"))
    return record


def _enrich_batch(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_enrich_dpi(r) if "dpi" not in r else r for r in records]


def capture_packets(count: int = CAPTURE_COUNT) -> list[dict[str, Any]]:
    try:
        proc = subprocess.run(
            [
                "timeout", str(CAPTURE_TIMEOUT), "tcpdump", "-i", "any", "-nn", "-tt", "-l",
                "-c", str(count), "tcp or udp",
            ],
            capture_output=True,
            text=True,
            timeout=CAPTURE_TIMEOUT + 2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    local_addrs = _local_addresses()
    conn_idx = _connection_index()
    events: list[dict[str, Any]] = []
    for line in (proc.stdout or "").splitlines():
        rec = parse_tcpdump_line(line, local_addrs, conn_idx)
        if rec:
            events.append(rec)
    return _enrich_batch(events)


def _append_ring(records: list[dict[str, Any]]) -> None:
    RING_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing: list[str] = []
    if RING_PATH.is_file():
        try:
            existing = RING_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            existing = []
    for rec in records:
        existing.append(json.dumps(rec, ensure_ascii=False))
    existing = existing[-RING_MAX:]
    try:
        RING_PATH.write_text("\n".join(existing) + ("\n" if existing else ""), encoding="utf-8")
    except OSError:
        pass


def _write_field_jsonl(records: list[dict[str, Any]]) -> int:
    written = 0
    for path in _field_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                for rec in records:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            written += 1
        except OSError:
            continue
    return written


def _build_port_registry(events: list[dict[str, Any]], prev: dict[str, Any]) -> list[dict[str, Any]]:
    by_key: dict[str, dict[str, Any]] = {}
    for old in prev.get("ports") or []:
        key = f"{old.get('proto','tcp')}:{old.get('port',0)}"
        by_key[key] = dict(old)

    for ev in events:
        direction = ev.get("direction")
        proto = ev.get("protocol") or "tcp"
        length = int(ev.get("length") or 0)
        for port in (ev.get("src_port"), ev.get("dst_port")):
            if not port:
                continue
            key = f"{proto}:{port}"
            row = by_key.setdefault(key, {
                "port": port,
                "proto": proto,
                "service": _port_service(int(port)),
                "tx_bytes": 0,
                "rx_bytes": 0,
                "tx_packets": 0,
                "rx_packets": 0,
                "processes": [],
            })
            if direction == "TX" and ev.get("src_port") == port:
                row["tx_bytes"] += length
                row["tx_packets"] += 1
            elif direction == "RX" and ev.get("dst_port") == port:
                row["rx_bytes"] += length
                row["rx_packets"] += 1
            proc = ev.get("process")
            if proc and proc not in row["processes"]:
                row["processes"].append(proc)
                row["processes"] = row["processes"][:8]

    ports = sorted(by_key.values(), key=lambda r: (-(r["tx_packets"] + r["rx_packets"]), r["port"]))
    return ports[:120]


def publish(events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    prev = _load_json(OUT_JSON, {})
    if events is None:
        events = []
        if RING_PATH.is_file():
            for line in RING_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    recent = _enrich_batch(events[-80:] if events else list(prev.get("recent") or [])[-80:])
    inspect = summarize_inspect(recent)
    doc: dict[str, Any] = {
        "updated": _now(),
        "capture_count": len(events),
        "local_addresses": sorted(_local_addresses()),
        "ports": _build_port_registry(events, prev),
        "recent": recent,
        "inspect": inspect,
        "tx_count": sum(1 for e in recent if e.get("direction") == "TX"),
        "rx_count": sum(1 for e in recent if e.get("direction") == "RX"),
        "lan_count": sum(1 for e in recent if e.get("direction") == "LAN"),
        "alert_count": inspect.get("alert_count", 0),
        "modem": {
            "pwr": True,
            "tx": sum(1 for e in recent[-20:] if e.get("direction") == "TX") > 0,
            "rx": sum(1 for e in recent[-20:] if e.get("direction") == "RX") > 0,
            "lan": sum(1 for e in recent[-20:] if e.get("direction") == "LAN") > 0,
            "alert": inspect.get("alert_count", 0) > 0,
            "cd": len(recent) > 0,
        },
        "standards": ["tcpdump", "TX-RX-Field", "DPI-Heuristics", "IEEE-Port-Registry", "RFC793-TCP", "RFC768-UDP"],
        "motto": "Every packet — program record on field drive, English translation, TX/RX from our machine.",
    }
    try:
        OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
        OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return doc


def capture_cycle() -> dict[str, Any]:
    events = capture_packets()
    if events:
        _append_ring(events)
        _write_field_jsonl(events)
    ring_events: list[dict[str, Any]] = []
    if RING_PATH.is_file():
        for line in RING_PATH.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]:
            try:
                ring_events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    doc = publish(ring_events)
    doc["field_paths_written"] = len(_field_paths()) if events else 0
    doc["captured_this_cycle"] = len(events)
    try:
        OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass
    return doc


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "capture"
    if cmd == "capture":
        json.dump(capture_cycle(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if cmd == "json":
        json.dump(publish(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if cmd == "parse-line" and len(sys.argv) > 2:
        local = _local_addresses()
        idx = _connection_index()
        rec = parse_tcpdump_line(" ".join(sys.argv[2:]), local, idx)
        json.dump(rec or {}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    print("usage: packet-field.py [capture|json|parse-line <tcpdump line>]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())