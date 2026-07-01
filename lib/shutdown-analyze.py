#!/usr/bin/env pythong
"""Shutdown forensics — local WAN IP, remote peers, killer attribution."""
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

PRIVATE4 = re.compile(r"^(127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2[0-9]|3[0-1])\.)")


def is_private(ip: str) -> bool:
    if not ip or ip in ("*", "0.0.0.0", "::1"):
        return True
    if ":" in ip:
        return ip.startswith("fe80:") or ip.startswith("fd") or ip == "::1"
    return bool(PRIVATE4.match(ip))


def parse_endpoint(field: str) -> tuple[str, str]:
    field = (field or "").strip()
    if not field:
        return "", ""
    if field.startswith("["):
        m = re.match(r"\[([^\]]+)\]:(\d+)", field)
        return (m.group(1), m.group(2)) if m else ("", "")
    if ":" in field:
        host, _, port = field.rpartition(":")
        if "%" in host:
            host = host.split("%", 1)[0]
        return host, port
    if "%" in field:
        field = field.split("%", 1)[0]
    return field, ""


def parse_conn(line: str) -> dict | None:
    parts = line.split()
    if len(parts) < 6:
        return None
    proto, state = parts[0], parts[1]
    local, remote = parts[4], parts[5]
    proc = ""
    m = re.search(r'users:\(\(\"([^\"]+)\"', line)
    if m:
        proc = m.group(1)
    else:
        m = re.search(r"pid=(\d+)", line)
        if m:
            proc = f"pid={m.group(1)}"
    lip, lport = parse_endpoint(local)
    rip, rport = parse_endpoint(remote)
    return {
        "proto": proto,
        "state": state,
        "local_ip": lip,
        "local_port": lport,
        "remote_ip": rip,
        "remote_port": rport,
        "proc": proc,
    }


def score_peer(ports: list[str], count: int) -> int:
    s = count * 2
    if any(p in ("4444", "5555", "1337", "31337", "6667", "9001", "9050") for p in ports):
        s += 40
    if any(p in ("80", "443") for p in ports):
        s += 2
    if len(ports) > 3:
        s += 5
    return s


def analyze(fore: dict, who: str, journal: str, signal: str) -> dict:
    peers: dict[str, dict] = {}
    listeners: list[dict] = []
    local_v4: Counter = Counter()
    local_v6: Counter = Counter()

    for raw in fore.get("connections", []):
        row = parse_conn(raw)
        if not row:
            continue
        lip = row["local_ip"]
        if lip and not is_private(lip):
            if ":" in lip:
                local_v6[lip] += 1
            else:
                local_v4[lip] += 1
        if row["state"] == "LISTEN":
            listeners.append({"bind": row["local_ip"] or "*", "port": row["local_port"], "proc": row["proc"]})
            continue
        if row["state"] not in ("ESTAB", "ESTABLISHED"):
            continue
        rip, rport = row["remote_ip"], row["remote_port"]
        if not rip or is_private(rip):
            continue
        ent = peers.setdefault(rip, {"ip": rip, "ports": set(), "count": 0, "procs": set()})
        ent["count"] += 1
        if rport:
            ent["ports"].add(rport)
        if row["proc"]:
            ent["procs"].add(row["proc"])

    ranked = []
    for ip, ent in peers.items():
        ports = sorted(ent["ports"], key=lambda x: int(x) if x.isdigit() else 0)
        procs = sorted(ent["procs"])
        ranked.append({
            "ip": ip,
            "score": score_peer(ports, ent["count"]),
            "connections": ent["count"],
            "ports": ports[:8],
            "procs": procs[:6],
        })
    ranked.sort(key=lambda x: (-x["score"], -x["connections"], x["ip"]))

    killer: dict = {"signal": signal or "", "source": "", "detail": ""}
    for key in ("ppid", "comm", "user", "exe"):
        m = re.search(rf"{key}=([^\s]+)", who)
        if m:
            killer["process" if key == "comm" else key] = m.group(1)
    if killer.get("ppid"):
        killer["source"] = "parent_process"
        killer["detail"] = who[:400]

    jm = re.search(r"Killing process ([0-9]+) \(([^)]+)\) with signal (\w+)", journal)
    if jm:
        killer.update({
            "source": "systemd",
            "pid": jm.group(1),
            "process": jm.group(2),
            "signal": jm.group(3),
            "detail": jm.group(0),
        })
    elif "SIGKILL" in journal or "status=9/KILL" in journal:
        killer.update({"source": "journal", "signal": "SIGKILL", "detail": "systemd forced SIGKILL after stop timeout"})
    elif "SIGTERM" in journal:
        killer.update({"source": "journal", "signal": "SIGTERM", "detail": "systemd stop / service restart"})

    local_wan_ip = fore.get("local_wan_ip") or (local_v4.most_common(1)[0][0] if local_v4 else "")
    local_ipv6 = local_v6.most_common(1)[0][0] if local_v6 else ""
    gateway_ip = ""
    for arp_line in fore.get("arp", []):
        gm = re.search(r"^([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)\s", arp_line)
        if gm:
            gateway_ip = gm.group(1)
            break

    primary = ranked[0]["ip"] if ranked else ""
    primary_v4 = next((r["ip"] for r in ranked if "." in r["ip"]), primary)
    confidence = "high" if primary and ranked[0]["score"] >= 10 else ("medium" if primary else "low")

    verdict_parts = []
    if local_wan_ip:
        verdict_parts.append(f"This machine (WAN): {local_wan_ip}")
    if killer.get("source"):
        verdict_parts.append(f"Killer: {killer['source']} / {killer.get('signal', '?')}")
    if primary_v4:
        conns = next(r["connections"] for r in ranked if r["ip"] == primary_v4)
        verdict_parts.append(f"Top remote peer: {primary_v4} ({conns} conns)")
    elif primary:
        verdict_parts.append(f"Top remote peer: {primary}")
    else:
        verdict_parts.append("No public remote peer — likely local kill (systemd/admin/OOM)")
    if signal == "UNCLEAN_RESTART":
        verdict_parts.append("Prior instance gone before clean stop")

    return {
        "primary_ip": primary_v4 or primary,
        "suspect_ips": [r["ip"] for r in ranked[:12]],
        "egress_peers": ranked[:12],
        "listeners": listeners[:10],
        "local_ip": local_wan_ip,
        "local_wan_ip": local_wan_ip,
        "local_ipv6": local_ipv6,
        "local_ips": [k for k, _ in (local_v4 + local_v6).most_common(4)],
        "gateway_ip": gateway_ip,
        "killer": killer,
        "confidence": confidence,
        "verdict": ". ".join(verdict_parts),
        "connection_count": len(fore.get("connections", [])),
        "public_peer_count": len(ranked),
    }


def main() -> None:
    fore_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path()
    who = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("SD_WHO", "")
    journal = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("SD_JOURNAL", "")
    signal = sys.argv[4] if len(sys.argv) > 4 else os.environ.get("SD_SIGNAL", "")

    fore: dict = {}
    if fore_path.is_file():
        try:
            fore = json.loads(fore_path.read_text())
        except json.JSONDecodeError:
            fore = {}

    print(json.dumps(analyze(fore, who, journal, signal)))


if __name__ == "__main__":
    main()