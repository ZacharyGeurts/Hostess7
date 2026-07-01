#!/usr/bin/env pythong
"""NEXUS Field US Intel — Page 1 dossier for THIS machine.

Sherlock-grade facts gleaned only from local field tools and state:
ss, ip, arp, proc, resolv.conf, NEXUS state files. No external APIs.
"""
from __future__ import annotations

import ipaddress
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PRIVATE_IP = re.compile(
    r"^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|169\.254\.)"
)

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
OUT = STATE / "us-field.json"


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



def _run(cmd: list[str], timeout: int = 8) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
        return (proc.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _nexus_version() -> str:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("nexus_version", INSTALL / "lib" / "nexus_version.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.read_version(str(INSTALL))
    except Exception:
        pass
    return "unknown"


def _read_file_tail(path: Path, limit: int = 4000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _uptime_sec() -> float | None:
    try:
        with open("/proc/uptime", encoding="utf-8") as fh:
            return float(fh.read().split()[0])
    except (OSError, ValueError, IndexError):
        return None


def _meminfo() -> dict[str, int]:
    out: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            num = re.search(r"(\d+)", v)
            if num:
                out[k.strip()] = int(num.group(1))
    except OSError:
        pass
    return out


def _cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8", errors="replace").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "unknown"


def _interfaces() -> list[dict[str, Any]]:
    raw = _run(["ip", "-j", "addr"])
    if raw:
        try:
            rows = json.loads(raw)
        except json.JSONDecodeError:
            rows = []
        out = []
        for iface in rows:
            name = iface.get("ifname", "")
            state = iface.get("operstate", "")
            addrs = []
            for ai in iface.get("addr_info") or []:
                addrs.append({
                    "family": ai.get("family"),
                    "local": ai.get("local"),
                    "prefixlen": ai.get("prefixlen"),
                    "scope": ai.get("scope"),
                })
            out.append({"name": name, "state": state, "addresses": addrs})
        return out
    text = _run(["ip", "addr"])
    return [{"raw": line} for line in text.splitlines()[:40] if line.strip()]


def _is_wireless_iface(iface: str) -> bool:
    if not iface:
        return False
    if iface.startswith(("wlan", "wlp", "wl")):
        return True
    return Path(f"/sys/class/net/{iface}/wireless").is_dir()


def _parse_route_line(line: str) -> dict[str, Any]:
    row: dict[str, Any] = {"raw": line.strip()}
    m = re.search(
        r"default via (\S+)(?: dev (\S+))?(?: proto (\S+))?(?: metric (\d+))?(?: src (\S+))?",
        line,
    )
    if m:
        row.update({
            "gateway": m.group(1),
            "device": m.group(2) or "",
            "proto": m.group(3) or "",
            "metric": int(m.group(4)) if m.group(4) else None,
            "src": m.group(5) or "",
        })
    m2 = re.search(r"default dev (\S+)(?: proto (\S+))?(?: metric (\d+))?", line)
    if m2 and not row.get("gateway"):
        row.update({
            "gateway": "",
            "device": m2.group(1),
            "proto": m2.group(2) or "",
            "metric": int(m2.group(3)) if m2.group(3) else None,
            "onlink": True,
        })
    flags = []
    for flag in ("onlink", "dhcp", "static", "ra"):
        if flag in line:
            flags.append(flag)
    if flags:
        row["flags"] = flags
    return row


def _default_routes(*, family: str = "-4") -> list[dict[str, Any]]:
    text = _run(["ip", family, "route", "show", "default"])
    if not text:
        return []
    return [_parse_route_line(line) for line in text.splitlines() if line.strip()]


def _route_get(target: str, *, family: str = "-4") -> dict[str, Any]:
    text = _run(["ip", family, "route", "get", target])
    if not text:
        return {}
    row: dict[str, Any] = {"raw": text.splitlines()[0], "target": target}
    parts = text.split()
    for key in ("via", "dev", "src", "mtu", "uid", "from", "prefsrc"):
        if key in parts:
            idx = parts.index(key)
            if idx + 1 < len(parts):
                row[key if key != "dev" else "device"] = parts[idx + 1]
    return row


def _link_detail(iface: str) -> dict[str, Any]:
    if not iface:
        return {}
    raw = _run(["ip", "-j", "link", "show", "dev", iface])
    if raw:
        try:
            rows = json.loads(raw)
            if rows:
                ent = rows[0]
                return {
                    "name": ent.get("ifname") or iface,
                    "operstate": ent.get("operstate") or "",
                    "mtu": ent.get("mtu"),
                    "mac": str(ent.get("address") or ""),
                    "wireless": _is_wireless_iface(iface),
                    "kind": "wireless" if _is_wireless_iface(iface) else "wired",
                }
        except json.JSONDecodeError:
            pass
    return {"name": iface, "wireless": _is_wireless_iface(iface)}


def _neighbor_for(ip: str) -> dict[str, Any]:
    if not ip:
        return {}
    raw = _run(["ip", "-j", "neigh", "show", ip])
    if raw:
        try:
            rows = json.loads(raw)
            if rows:
                ent = rows[0]
                return {
                    "ip": ip,
                    "mac": str(ent.get("lladdr") or ""),
                    "iface": str(ent.get("dev") or ""),
                    "state": str(ent.get("state") or ""),
                    "reachable": str(ent.get("state") or "") in ("REACHABLE", "STALE", "DELAY", "PROBE"),
                }
        except json.JSONDecodeError:
            pass
    text = _run(["ip", "neigh", "show", ip])
    if not text:
        return {"ip": ip}
    parts = text.split()
    mac = parts[4] if len(parts) > 5 and parts[3] == "lladdr" else ""
    return {
        "ip": ip,
        "mac": mac,
        "iface": parts[2] if len(parts) > 2 else "",
        "state": parts[-1] if parts else "",
        "raw": text.splitlines()[0],
    }


def _iface_host_addresses(iface: str, interfaces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    addrs: list[dict[str, Any]] = []
    for ent in interfaces:
        if ent.get("name") != iface:
            continue
        for ai in ent.get("addresses") or []:
            if ai.get("family") in ("inet", "inet6", None) or str(ai.get("family")) in ("inet", "inet6"):
                addrs.append(dict(ai))
    return addrs


def _subnet_for_ip(ip: str, interfaces: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return None
    for ent in interfaces:
        for ai in ent.get("addresses") or []:
            local = ai.get("local")
            plen = ai.get("prefixlen")
            if not local or plen is None:
                continue
            try:
                net = ipaddress.ip_network(f"{local}/{plen}", strict=False)
            except ValueError:
                continue
            if addr in net:
                return {
                    "iface": ent.get("name") or "",
                    "cidr": str(net),
                    "host_ip": local,
                    "gateway_in_subnet": True,
                }
    return None


def _lan_device_match(
    gw_ip: str,
    gw_mac: str,
    local_net: dict[str, Any],
) -> dict[str, Any] | None:
    mac_l = (gw_mac or "").lower()
    for dev in local_net.get("devices") or []:
        dip = str(dev.get("ip") or "")
        dmac = str(dev.get("mac") or "").lower()
        if (gw_ip and dip == gw_ip) or (mac_l and dmac and dmac == mac_l):
            return dev
    return None


def _gatekeeper_gateway_flows(gw_ip: str) -> list[dict[str, Any]]:
    if not gw_ip:
        return []
    doc = _load_json(STATE / "connection-intent.json", {})
    flows: list[dict[str, Any]] = []
    for conn in doc.get("connections") or []:
        rip = str(conn.get("remote_ip") or conn.get("remote") or "").split(":")[0].strip("[]")
        lip = str(conn.get("local_ip") or conn.get("local") or "").split(":")[0].strip("[]")
        if rip == gw_ip or lip == gw_ip:
            flows.append({
                "local": conn.get("local") or conn.get("local_ip"),
                "remote": conn.get("remote") or conn.get("remote_ip"),
                "process": conn.get("process"),
                "verdict": conn.get("verdict"),
                "direction": conn.get("direction"),
            })
    return flows[:16]


def _trust_posture_for_ip(ip: str) -> dict[str, Any]:
    trusted = blocked = False
    if not ip:
        return {"trusted": False, "blocked": False}
    trusted_path = STATE / "firewall-trusted.tsv"
    blocks_path = STATE / "firewall-blocks.tsv"
    for path, flag in ((trusted_path, "trusted"), (blocks_path, "blocked")):
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
            if ip in line.split("\t"):
                if flag == "trusted":
                    trusted = True
                else:
                    blocked = True
    return {"trusted": trusted, "blocked": blocked, "sacred": ip in _sacred_ips()}


def _sacred_ips() -> set[str]:
    sacred = {"1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9", "149.112.112.112"}
    probe = _route_get("1.1.1.1")
    if probe.get("src"):
        sacred.add(str(probe["src"]))
    for route in _default_routes():
        if route.get("gateway"):
            sacred.add(str(route["gateway"]))
    return sacred


def _gateway_threat_events(gw_ip: str, gw_mac: str) -> list[dict[str, Any]]:
    path = STATE / "threat-vectors.tsv"
    if not path.is_file():
        return []
    mac_l = (gw_mac or "").lower()
    hits: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        ts, vector, severity, detail = parts[0], parts[1], parts[2], parts[3]
        if vector not in ("GATEWAY_SHIFT", "ARP_SPOOF", "PACKET_INJECTION", "MITM_LISTENER", "CONN_HIJACK"):
            continue
        blob = f"{gw_ip} {mac_l} {detail}".lower()
        if (gw_ip and gw_ip in blob) or (mac_l and mac_l in blob) or vector == "GATEWAY_SHIFT":
            hits.append({
                "ts": ts,
                "vector": vector,
                "severity": severity,
                "detail": detail[:240],
            })
    return hits[-8:]


def _gateway_knowledge_points(profile: dict[str, Any]) -> list[dict[str, str]]:
    points: list[dict[str, str]] = []
    v4 = profile.get("ipv4") or {}
    gw = v4.get("gateway") or ""
    dev = v4.get("device") or ""
    wan = v4.get("wan_ip") or ""
    neigh = v4.get("neighbor") or {}
    link = v4.get("link") or {}
    subnet = v4.get("subnet") or {}
    dns = profile.get("dns") or {}
    trust = profile.get("trust") or {}
    dhcp = profile.get("dhcp") or {}
    flows = profile.get("gatekeeper_flows") or []
    threats = profile.get("threat_events") or []
    lan = profile.get("lan_device") or {}

    if gw:
        mac = neigh.get("mac") or "unknown MAC"
        state = neigh.get("state") or "unknown"
        kind = link.get("kind") or ("wireless" if link.get("wireless") else "wired")
        points.append({
            "key": "primary_path",
            "label": "Primary egress",
            "text": (
                f"IPv4 traffic exits via {gw} on {dev or '—'} ({kind}). "
                f"Your WAN-facing address on this path is {wan or '—'}."
            ),
        })
        points.append({
            "key": "neighbor",
            "label": "Layer-2 neighbor",
            "text": (
                f"ARP/neighbor table shows {gw} at {mac or '—'} "
                f"({state or '—'} on {neigh.get('iface') or dev or '—'})."
            ),
        })
    if subnet.get("cidr"):
        points.append({
            "key": "subnet",
            "label": "Subnet placement",
            "text": (
                f"Gateway sits in {subnet['cidr']} with this host at {subnet.get('host_ip') or wan or '—'}."
            ),
        })
    if dns.get("nameservers"):
        points.append({
            "key": "dns",
            "label": "DNS resolvers",
            "text": (
                f"resolv.conf nameservers: {', '.join(dns['nameservers'][:4])}. "
                f"{'Gateway also listed as resolver.' if dns.get('gateway_is_resolver') else 'Gateway is not a listed resolver.'}"
            ),
        })
    if dhcp.get("server_running"):
        points.append({
            "key": "dhcp",
            "label": "DHCP on LAN",
            "text": (
                f"NEXUS Field DHCP is active ({dhcp.get('lease_count', 0)} lease(s)). "
                f"Clients receive DNS {', '.join(dhcp.get('dns_servers') or ['127.0.0.1'])}."
            ),
        })
    if lan:
        srcs = ", ".join(lan.get("sources") or lan.get("tables") or [])
        points.append({
            "key": "lan_tables",
            "label": "Learned from LAN tables",
            "text": (
                f"Gateway appears in merged LAN inventory as {lan.get('role') or 'device'}"
                + (f" (sources: {srcs})" if srcs else "")
                + "."
            ),
        })
    if flows:
        points.append({
            "key": "gatekeeper",
            "label": "Live gatekeeper flows",
            "text": f"{len(flows)} active flow(s) involve the gateway IP right now.",
        })
    if trust.get("sacred"):
        points.append({
            "key": "sacred",
            "label": "Sacred address",
            "text": "Gateway/WAN path is treated as sacred — NEXUS will not auto-block this hop.",
        })
    if trust.get("blocked"):
        points.append({
            "key": "blocked",
            "label": "Firewall block",
            "text": "Gateway IP appears in active firewall blocks — review trust posture.",
        })
    if threats:
        recent = threats[-1]
        points.append({
            "key": "threats",
            "label": "Threat history",
            "text": (
                f"{len(threats)} recent gateway-related vector(s); "
                f"latest {recent.get('vector')} ({recent.get('severity')}) at {recent.get('ts')}."
            ),
        })
    v6 = profile.get("ipv6") or {}
    if v6.get("gateway") or v6.get("device"):
        points.append({
            "key": "ipv6",
            "label": "IPv6 default",
            "text": (
                f"IPv6 default via {v6.get('gateway') or 'on-link'} on {v6.get('device') or '—'}."
            ),
        })
    routes = profile.get("all_routes") or []
    if len(routes) > 1:
        metrics = ", ".join(
            f"{r.get('gateway') or 'on-link'}→{r.get('device') or '—'}(m={r.get('metric') or '—'})"
            for r in routes[:4]
        )
        points.append({
            "key": "multi_route",
            "label": "Multiple defaults",
            "text": f"{len(routes)} default routes installed: {metrics}.",
        })
    return points


def _build_gateway_profile(
    *,
    interfaces: list[dict[str, Any]],
    local_net: dict[str, Any],
) -> dict[str, Any]:
    routes_v4 = _default_routes(family="-4")
    routes_v6 = _default_routes(family="-6")
    primary = routes_v4[0] if routes_v4 else {}
    gw_ip = str(primary.get("gateway") or "")
    dev = str(primary.get("device") or "")
    egress4 = _route_get("1.1.1.1", family="-4")
    egress6 = _route_get("2001:4860:4860::8888", family="-6")
    neighbor = _neighbor_for(gw_ip)
    gw_mac = str(neighbor.get("mac") or "")
    link = _link_detail(dev)
    host_addrs = _iface_host_addresses(dev, interfaces)
    subnet = _subnet_for_ip(gw_ip, interfaces) if gw_ip else None
    dns = _dns_local()
    dns_servers = dns.get("nameservers") or []
    dhcp_panel = _load_json(STATE / "field-dhcp-panel.json", {})
    lan_match = _lan_device_match(gw_ip, gw_mac, local_net)
    flows = _gatekeeper_gateway_flows(gw_ip)
    trust = _trust_posture_for_ip(gw_ip)
    threats = _gateway_threat_events(gw_ip, gw_mac)

    wan_ip = str(egress4.get("src") or primary.get("src") or "")
    if not wan_ip and host_addrs:
        for ai in host_addrs:
            if ai.get("family") in ("inet", None) and ai.get("local"):
                wan_ip = str(ai["local"])
                break

    ipv4: dict[str, Any] = {
        "gateway": gw_ip,
        "device": dev,
        "metric": primary.get("metric"),
        "proto": primary.get("proto") or "",
        "flags": primary.get("flags") or [],
        "raw": primary.get("raw") or "",
        "wan_ip": wan_ip,
        "egress_probe": egress4,
        "neighbor": neighbor,
        "link": link,
        "host_addresses": host_addrs,
        "subnet": subnet,
        "is_private": bool(gw_ip and PRIVATE_IP.match(gw_ip)),
        "role": "router" if gw_ip and PRIVATE_IP.match(gw_ip) else ("upstream" if gw_ip else "unknown"),
    }

    v6_primary = routes_v6[0] if routes_v6 else {}
    ipv6: dict[str, Any] = {}
    if v6_primary:
        ipv6 = {
            "gateway": str(v6_primary.get("gateway") or ""),
            "device": str(v6_primary.get("device") or ""),
            "metric": v6_primary.get("metric"),
            "proto": v6_primary.get("proto") or "",
            "raw": v6_primary.get("raw") or "",
            "egress_probe": egress6,
            "onlink": bool(v6_primary.get("onlink")),
        }

    profile: dict[str, Any] = {
        "schema": "us-gateway/v1",
        "updated": _now(),
        "ipv4": ipv4,
        "ipv6": ipv6,
        "all_routes": routes_v4,
        "all_routes_v6": routes_v6,
        "dns": {
            **dns,
            "gateway_is_resolver": bool(gw_ip and gw_ip in dns_servers),
        },
        "dhcp": {
            "server_running": bool(dhcp_panel.get("running")),
            "bind": dhcp_panel.get("bind"),
            "lease_count": dhcp_panel.get("lease_count", 0),
            "dns_servers": (dhcp_panel.get("dns_servers") or ["127.0.0.1"]),
        },
        "lan_device": lan_match,
        "gatekeeper_flows": flows,
        "trust": trust,
        "threat_events": threats,
    }
    profile["knowledge_points"] = _gateway_knowledge_points(profile)
    return profile


def _default_route() -> dict[str, str]:
    routes = _default_routes(family="-4")
    if not routes:
        return {}
    primary = routes[0]
    return {
        "gateway": str(primary.get("gateway") or ""),
        "device": str(primary.get("device") or ""),
        "raw": str(primary.get("raw") or ""),
    }


def _dns_local() -> dict[str, Any]:
    resolv = Path("/etc/resolv.conf")
    servers: list[str] = []
    search: list[str] = []
    if resolv.is_file():
        for line in resolv.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("nameserver"):
                servers.append(line.split()[1])
            elif line.startswith("search"):
                search.extend(line.split()[1:])
    snap = STATE / "resolv.sha"
    dns_hash = ""
    if snap.is_file():
        dns_hash = snap.read_text(encoding="utf-8", errors="replace").strip()[:64]
    return {"nameservers": servers, "search_domains": search, "dns_hash": dns_hash}


def _ss_connections() -> list[dict[str, Any]]:
    """Every established socket from ss -ti — label + TX/RX byte counters, no cap."""
    text = _run(["ss", "-H", "-ti", "-n", "-p"], timeout=15)
    conns: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if parts and parts[0] in ("ESTAB", "ESTABLISHED"):
            if current:
                conns.append(current)
            local = parts[3] if len(parts) > 3 else ""
            remote = parts[4] if len(parts) > 4 else ""
            proc_m = re.search(r'users:\(\("([^"]+)"', line)
            proc = proc_m.group(1) if proc_m else ""
            current = {
                "state": parts[0],
                "local": local,
                "remote": remote,
                "process": proc,
                "tx_bytes": 0,
                "rx_bytes": 0,
            }
        elif current and "bytes_sent:" in line:
            sent_m = re.search(r"bytes_sent:(\d+)", line)
            recv_m = re.search(r"bytes_received:(\d+)", line)
            if sent_m:
                current["tx_bytes"] = int(sent_m.group(1))
            if recv_m:
                current["rx_bytes"] = int(recv_m.group(1))
    if current:
        conns.append(current)
    for c in conns:
        proc = c.get("process") or "unknown"
        c["label"] = f"{proc} · {c.get('local', '—')} → {c.get('remote', '—')}"
    return conns


def _ss_summary() -> dict[str, Any]:
    text = _run(["ss", "-H", "-tunap"], timeout=12)
    estab = listen = syn = 0
    procs: dict[str, int] = {}
    remotes: dict[str, int] = {}
    listeners: list[dict[str, str]] = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        st = parts[1]
        if st in ("ESTAB", "ESTABLISHED"):
            estab += 1
        elif st in ("LISTEN", "LISTENING"):
            listen += 1
            local = parts[4] if len(parts) > 4 else ""
            proc_m = re.search(r'users:\(\("([^"]+)"', line)
            listeners.append({
                "local": local,
                "process": proc_m.group(1) if proc_m else "",
            })
        elif st.startswith("SYN"):
            syn += 1
        proc_m = re.search(r'users:\(\("([^"]+)"', line)
        if proc_m:
            procs[proc_m.group(1)] = procs.get(proc_m.group(1), 0) + 1
        if st in ("ESTAB", "ESTABLISHED") and len(parts) > 5:
            remote = parts[5]
            rip = remote.rsplit(":", 1)[0].strip("[]")
            if rip and not rip.startswith("127."):
                remotes[rip] = remotes.get(rip, 0) + 1
    top_procs = sorted(procs.items(), key=lambda x: -x[1])[:12]
    top_remotes = sorted(remotes.items(), key=lambda x: -x[1])[:12]
    return {
        "established": estab,
        "listening": listen,
        "syn_state": syn,
        "top_processes": [{"process": p, "socket_count": c} for p, c in top_procs],
        "top_remote_peers": [{"ip": ip, "socket_count": c} for ip, c in top_remotes],
        "listeners": listeners[:24],
    }


def _arp_neighbors() -> list[dict[str, str]]:
    snap = STATE / "arp.snapshot"
    if snap.is_file():
        rows = []
        for line in snap.read_text(encoding="utf-8", errors="replace").splitlines()[:40]:
            if not line.strip():
                continue
            rows.append({"line": line.strip()})
        return rows
    text = _run(["ip", "neigh", "show"])
    return [{"line": ln} for ln in text.splitlines()[:40] if ln.strip()]


def _gatekeeper_slice() -> dict[str, Any]:
    doc = _load_json(STATE / "connection-intent.json", {})
    conns = doc.get("connections") or []
    by_verdict: dict[str, int] = {}
    pending = 0
    for c in conns:
        v = c.get("verdict") or "UNKNOWN"
        by_verdict[v] = by_verdict.get(v, 0) + 1
        if c.get("requires_user_trust"):
            pending += 1
    return {
        "updated": doc.get("updated"),
        "connection_count": doc.get("connection_count", len(conns)),
        "strict_trust": doc.get("strict_trust"),
        "packet_permission": doc.get("packet_permission"),
        "permitted_flow_count": doc.get("permitted_flow_count", 0),
        "segment_block_count": doc.get("segment_block_count", 0),
        "pending_trust_count": doc.get("pending_trust_count", pending),
        "verdict_histogram": by_verdict,
        "harm_candidates": doc.get("harm_candidates", 0),
    }


def _trust_posture() -> dict[str, Any]:
    trusted_path = STATE / "firewall-trusted.tsv"
    blocks_path = STATE / "firewall-blocks.tsv"
    trusted = 0
    blocked = 0
    if trusted_path.is_file():
        trusted = max(0, sum(1 for _ in trusted_path.read_text(encoding="utf-8", errors="replace").splitlines()) - 1)
    if blocks_path.is_file():
        blocked = max(0, sum(1 for _ in blocks_path.read_text(encoding="utf-8", errors="replace").splitlines()) - 1)
    settings = _load_json(STATE / "settings.override", {})
    if not settings:
        settings = {}
        for line in _read_file_tail(STATE / "settings.override").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                settings[k.strip()] = v.strip()
    return {
        "trusted_entries": trusted,
        "active_blocks": blocked,
        "lockdown_first_complete": (STATE / "lockdown-first.done").is_file(),
        "strict_trust_setting": settings.get("NEXUS_GATEKEEPER_STRICT_TRUST", "1"),
        "paranoia_block": settings.get("NEXUS_PARANOIA_BLOCK", "0"),
        "auto_crush": settings.get("NEXUS_ATTACK_KIT_AUTO_CRUSH", "1"),
    }


def _field_storage() -> dict[str, Any]:
    paths = [
        STATE / "packet-field.json",
        STATE / "packet-field.ring.jsonl",
        STATE / "human-dossier.json",
        STATE / "connection-intent.json",
        STATE / "host-attacks-panel.json",
        STATE / "threat-panel.json",
    ]
    catalog = []
    for p in paths:
        if p.is_file():
            catalog.append({"path": str(p), "size": p.stat().st_size, "exists": True})
        else:
            catalog.append({"path": str(p), "size": 0, "exists": False})
    ring_lines = 0
    ring = STATE / "packet-field.ring.jsonl"
    if ring.is_file():
        try:
            ring_lines = sum(1 for _ in ring.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            pass
    return {"artifacts": catalog, "packet_ring_lines": ring_lines}


def _vigil_mode() -> str:
    st = STATE / "vigil.state"
    if not st.is_file():
        return "unknown"
    for line in st.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("mode="):
            return line.split("=", 1)[1].strip()
    return "unknown"


def _observations(doc: dict[str, Any]) -> list[dict[str, str]]:
    """Plain-English rundown blocks — one headline per fact, readable at a glance."""
    blocks: list[dict[str, str]] = []
    ident = doc.get("identity") or {}
    net = doc.get("network") or {}
    sock = doc.get("sockets") or {}
    gk = doc.get("gatekeeper") or {}
    trust = doc.get("trust_posture") or {}

    host = ident.get("hostname") or "this machine"
    os_line = f"{ident.get('os') or 'Linux'} {ident.get('os_release') or ''}".strip()
    blocks.append({
        "label": "Who you are on this network",
        "text": (
            f"{host} is running {os_line} on {ident.get('arch') or 'unknown'} hardware. "
            f"Kernel: {(ident.get('kernel') or '—')[:80]}. "
            f"Uptime: {ident.get('uptime_human') or '—'}."
        ),
    })
    if ident.get("cpu_model"):
        mem = ident.get("memory") or {}
        ram = f"{mem['MemTotal_kB'] // 1024} MiB RAM" if mem.get("MemTotal_kB") else "RAM unknown"
        blocks.append({"label": "Hardware", "text": f"{ident['cpu_model']}. {ram}."})

    gw_prof = doc.get("gateway") or {}
    v4 = gw_prof.get("ipv4") or {}
    route = net.get("default_route") or {}
    gw_ip = v4.get("gateway") or route.get("gateway")
    if gw_ip:
        neigh = v4.get("neighbor") or {}
        link = v4.get("link") or {}
        wan = v4.get("wan_ip") or ""
        mac = neigh.get("mac") or "—"
        kind = link.get("kind") or "link"
        blocks.append({
            "label": "Default gateway",
            "text": (
                f"Traffic leaves through {gw_ip} ({mac}) on {v4.get('device') or route.get('device') or '—'} "
                f"via {kind}. WAN address {wan or '—'}."
            ),
        })
        for point in (gw_prof.get("knowledge_points") or [])[:4]:
            if point.get("label") and point.get("text"):
                blocks.append({"label": point["label"], "text": point["text"]})
    dns = net.get("dns") or {}
    if dns.get("nameservers"):
        blocks.append({
            "label": "DNS (local resolv.conf)",
            "text": f"Resolvers: {', '.join(dns['nameservers'][:4])}.",
        })

    lan = doc.get("local_network") or {}
    devices = lan.get("devices") or net.get("lan_devices") or []
    tables = lan.get("tables_learned") or net.get("tables_learned") or {}
    if devices or tables:
        table_bits = ", ".join(f"{k}: {v}" for k, v in sorted(tables.items()) if v)
        blocks.append({
            "label": "Local network (learned tables)",
            "text": (
                f"{len(devices)} device(s) on your LAN from existing NEXUS tables"
                + (f" ({table_bits})" if table_bits else "")
                + ". See Local network panel below."
            ),
        })
    subs = net.get("subnets") or lan.get("subnets") or []
    if subs:
        blocks.append({
            "label": "Your subnets",
            "text": ", ".join(s.get("cidr") or s.get("host_ip") or "—" for s in subs[:6]),
        })

    blocks.append({
        "label": "Live socket posture",
        "text": (
            f"{sock.get('established', 0)} established connections, "
            f"{sock.get('listening', 0)} listening ports, "
            f"{sock.get('syn_state', 0)} half-open (SYN) sockets."
        ),
    })

    hist = gk.get("verdict_histogram") or {}
    if hist:
        parts = [f"{k}: {v}" for k, v in sorted(hist.items())]
        blocks.append({
            "label": "Gatekeeper verdicts (right now)",
            "text": " · ".join(parts) + ".",
        })
    if gk.get("packet_permission") or gk.get("strict_trust"):
        blocks.append({
            "label": "Packet permission v4.0",
            "text": (
                f"{gk.get('permitted_flow_count', 0)} good flow(s) pass at zero nft cost. "
                f"{gk.get('segment_block_count', 0)} harmful segment hold(s). "
                f"{gk.get('pending_trust_count', 0)} connection(s) await your review."
            ),
        })

    blocks.append({
        "label": "Trust & blocks",
        "text": (
            f"{trust.get('trusted_entries', 0)} address(es) trusted forever. "
            f"{trust.get('active_blocks', 0)} active firewall block(s)."
        ),
    })
    blocks.append({
        "label": "NEXUS field status",
        "text": (
            f"Version {ident.get('nexus_version') or '—'}. "
            f"Vigil mode: {ident.get('vigil_mode') or '—'}. "
            f"Snapshot: {_now()}."
        ),
    })
    return blocks


def build_us_field() -> dict[str, Any]:
    uname = platform.uname()
    mem = _meminfo()
    uptime = _uptime_sec()
    uptime_human = ""
    if uptime is not None:
        hrs = int(uptime // 3600)
        mins = int((uptime % 3600) // 60)
        uptime_human = f"{hrs}h {mins}m"

    identity = {
        "hostname": socket.gethostname(),
        "fqdn": socket.getfqdn(),
        "os": uname.system,
        "os_release": uname.release,
        "kernel": uname.version.split(" #", 1)[0][:120],
        "arch": uname.machine,
        "platform": platform.platform(),
        "cpu_model": _cpu_model(),
        "cpu_count": os.cpu_count(),
        "python": platform.python_version(),
        "nexus_version": _nexus_version(),
        "vigil_mode": _vigil_mode(),
        "operator_user": os.environ.get("USER") or _run(["whoami"]) or "unknown",
        "operator_uid": os.getuid() if hasattr(os, "getuid") else None,
        "timezone": time.tzname[0] if time.tzname else "",
        "uptime_sec": uptime,
        "uptime_human": uptime_human,
        "memory": mem,
        "disk_root": {},
    }
    try:
        usage = shutil.disk_usage("/")
        identity["disk_root"] = {
            "total_gb": round(usage.total / (1024 ** 3), 2),
            "used_gb": round(usage.used / (1024 ** 3), 2),
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "pct_used": round(100 * usage.used / usage.total, 1) if usage.total else 0,
        }
    except OSError:
        pass

    ifaces = _interfaces()
    local_net: dict[str, Any] = {}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "us_local_network", INSTALL / "lib" / "us-local-network.py",
        )
        if spec and spec.loader:
            ln = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ln)
            local_net = ln.build_local_network(interfaces=ifaces)
    except Exception:
        local_net = {}

    gateway = _build_gateway_profile(interfaces=ifaces, local_net=local_net)
    doc: dict[str, Any] = {
        "page": 1,
        "title": "US",
        "subtitle": "This machine — field-gleaned forensic identity",
        "motto": "Sherlock on localhost. Every fact from ss, ip, proc, and NEXUS state on this box — no external guesswork.",
        "generated_at": _now(),
        "identity": identity,
        "local_network": local_net,
        "gateway": gateway,
        "network": {
            "interfaces": ifaces,
            "default_route": _default_route(),
            "gateway": gateway,
            "dns": _dns_local(),
            "arp_neighbors": _arp_neighbors(),
            "connections": _ss_connections(),
            "subnets": local_net.get("subnets") or [],
            "lan_devices": local_net.get("devices") or [],
            "tables_learned": local_net.get("tables_learned") or {},
        },
        "sockets": _ss_summary(),
        "gatekeeper": _gatekeeper_slice(),
        "trust_posture": _trust_posture(),
        "field_storage": _field_storage(),
        "protection": {
            "firewall_state": _read_file_tail(STATE / "firewall.state", 500).splitlines()[:6],
            "paranoia_state": _read_file_tail(STATE / "paranoia.state", 400).splitlines()[:6],
        },
    }
    doc["observations"] = _observations(doc)
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "hostess_profile", INSTALL / "lib" / "hostess-profile.py",
        )
        if spec and spec.loader:
            hp = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(hp)
            doc = hp.attach_to_us_field(doc)
    except Exception:
        pass
    return doc


def publish() -> Path:
    doc = build_us_field()
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(OUT)
    return OUT


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: field-us-intel.py [build|json]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "build":
        publish()
        return 0
    if cmd == "json":
        if OUT.is_file():
            print(OUT.read_text(encoding="utf-8"))
        else:
            print(json.dumps(build_us_field(), ensure_ascii=False))
        return 0
    print("usage: field-us-intel.py [build|json]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    import sys
    raise SystemExit(main())