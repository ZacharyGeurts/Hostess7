#!/usr/bin/env pythong
"""NEXUS Angel Dossier — full attack-path chains, research tables, IPv4/IPv6.

They look at us or from us — we look back HARD.
Builds dossiers tracing vectors → peers → processes → MAC → CVE/exploit intel.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
DATA = INSTALL / "data"
DOSSIER_PATH = STATE / "angel-dossiers.json"
RESEARCH_PATH = STATE / "angel-research.json"
INTEL_CACHE = STATE / "vector-intel-cache.json"
SCOUR_PATH = STATE / "vector-scour.json"
THREATS_TSV = STATE / "threat-vectors.tsv"
ARP_SNAPSHOT = STATE / "arp.snapshot"
CONN_INTENT = STATE / "connection-intent.json"

IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IPV6_RE = re.compile(
    r"\b(?:[0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}\b|"
    r"\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b"
)


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
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _is_private_addr(addr: str) -> bool:
    if not addr:
        return True
    try:
        ip = ipaddress.ip_address(addr.split("%")[0])
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return True


def _parse_ss_peer(line: str) -> dict[str, str]:
    parts = line.split()
    proto = parts[0] if parts else ""
    state = parts[1] if len(parts) > 1 else ""
    local_idx, remote_idx = 4, 5
    if proto in ("tcp", "udp", "tcp6", "udp6"):
        state = parts[1] if len(parts) > 1 else state
        local_idx, remote_idx = 4, 5
    local = parts[local_idx] if len(parts) > local_idx else ""
    remote = parts[remote_idx] if len(parts) > remote_idx else ""

    def split_addr(raw: str) -> tuple[str, str, str]:
        if not raw or raw in ("*:*", "[*]:*"):
            return "", "", "unknown"
        raw = raw.strip()
        if raw.startswith("["):
            m = re.match(r"\[([^\]]+)\]:(\d+)", raw)
            if m:
                return m.group(1), m.group(2), "ipv6"
            return raw.strip("[]"), "", "ipv6"
        if raw.count(":") > 1:
            idx = raw.rfind(":")
            return raw[:idx], raw[idx + 1 :], "ipv6"
        if ":" in raw:
            h, p = raw.rsplit(":", 1)
            return h, p, "ipv4"
        return raw, "", "unknown"

    lip, lport, lver = split_addr(local)
    rip, rport, rver = split_addr(remote)
    proc = ""
    pid = ""
    m = re.search(r'users:\(\("([^"]+)"[^)]*pid=(\d+)', line)
    if m:
        proc = m.group(1).lower()
        pid = m.group(2)

    direction = "from_us"
    direction_label = "From us → them"
    if state in ("LISTEN", "LISTENING"):
        direction = "at_us"
        direction_label = "At us — listening for them"
    elif state in ("SYN-RECV", "SYN_RECV"):
        direction = "at_us"
        direction_label = "At us — inbound attempt"
    elif state in ("ESTAB", "ESTABLISHED"):
        direction = "from_us"
        direction_label = "From us → outbound session"

    addr_ver = rver if rip else lver
    peer = rip or lip
    return {
        "proto": proto,
        "state": state,
        "local_ip": lip,
        "local_port": lport,
        "remote_ip": rip,
        "remote_port": rport,
        "peer": peer,
        "addr_version": addr_ver if addr_ver != "unknown" else ("ipv6" if ":" in peer else "ipv4"),
        "process": proc,
        "pid": pid,
        "direction": direction,
        "direction_label": direction_label,
        "line": line[:240],
    }


def _load_oui_table() -> dict[str, dict[str, str]]:
    path = DATA / "oui-vendors.tsv"
    out: dict[str, dict[str, str]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        prefix, vendor, category = parts[0].upper(), parts[1], parts[2]
        out[prefix.replace("-", ":")] = {"vendor": vendor, "category": category}
    return out


def _normalize_mac(mac: str) -> str:
    mac = mac.upper().replace("-", ":")
    parts = mac.split(":")
    if len(parts) >= 3:
        return ":".join(parts[:3])
    return mac


def lookup_mac_vendor(mac: str, oui_db: dict[str, dict[str, str]], online: bool) -> dict[str, Any]:
    prefix = _normalize_mac(mac)
    entry = oui_db.get(prefix)
    if entry:
        return {
            "mac": mac,
            "oui": prefix,
            "vendor": entry["vendor"],
            "category": entry["category"],
            "source": "oui-table",
            "confidence": "high",
        }
    if online and mac:
        try:
            url = f"https://api.macvendors.com/{urllib.parse.quote(mac)}"
            req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Shield/2.6 angel-dossier"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                vendor = resp.read().decode("utf-8", errors="replace").strip()
            if vendor and "errors" not in vendor.lower():
                return {
                    "mac": mac,
                    "oui": prefix,
                    "vendor": vendor,
                    "category": "lookup",
                    "source": "macvendors-api",
                    "confidence": "medium",
                }
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
    return {
        "mac": mac,
        "oui": prefix,
        "vendor": f"OUI {prefix} (unlisted)",
        "category": "unlisted",
        "source": "inferred",
        "confidence": "inferred",
    }


def _load_cve_map() -> dict[str, Any]:
    return _load_json(DATA / "cve-vector-map.json", {"vectors": {}, "exploit_classes": {}})


def _vector_exploit_intel(vector: str, cve_map: dict[str, Any]) -> dict[str, Any]:
    info = (cve_map.get("vectors") or {}).get(vector, {})
    if not info:
        return {
            "vector": vector,
            "mitre": [],
            "cves": [],
            "exploit_class": "unmapped",
            "summary": "Vector recorded — mapping pending in research tables.",
        }
    return {
        "vector": vector,
        "mitre": info.get("mitre", []),
        "cves": info.get("cves", []),
        "exploit_class": info.get("exploit_class", "mixed"),
        "exploit_class_label": (cve_map.get("exploit_classes") or {}).get(
            info.get("exploit_class", ""), ""
        ),
        "summary": info.get("summary", ""),
    }


def _load_arp_table() -> dict[str, str]:
    """ip -> mac from neigh snapshot."""
    out: dict[str, str] = {}
    if not ARP_SNAPSHOT.is_file():
        return out
    for line in ARP_SNAPSHOT.read_text(encoding="utf-8", errors="replace").splitlines():
        # ip neigh: 192.168.1.1 dev wlan0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
        m = re.search(
            r"([0-9a-fA-F:.]+)\s+dev\s+\S+\s+lladdr\s+([0-9a-fA-F:]{11,17})",
            line,
        )
        if m:
            out[m.group(1)] = m.group(2)
        else:
            # proc arp format
            parts = line.split()
            if len(parts) >= 4 and parts[3] != "00:00:00:00:00:00":
                out[parts[0]] = parts[3]
    return out


def _extract_addrs(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for ip in IPV4_RE.findall(text):
        found.append((ip, "ipv4"))
    for ip in IPV6_RE.findall(text):
        if ip not in ("::", "::1"):
            found.append((ip, "ipv6"))
    return found


def _intel_for_peer(peer: str, addr_ver: str, cache: dict[str, Any]) -> dict[str, Any]:
    entry = (cache.get("ips") or {}).get(peer)
    if entry:
        return {k: v for k, v in entry.items() if k != "_ts"}
    label = "IPv6 global peer" if addr_ver == "ipv6" else "Classified remote peer"
    ip_class = "ipv6_global" if addr_ver == "ipv6" else "classified_remote"
    return {
        "ip": peer,
        "ip_class": ip_class,
        "label": label,
        "addr_version": addr_ver,
        "confidence": "inferred",
        "source": "dossier",
    }


def _build_attack_path(
    vector: str,
    peer: str,
    proc: str,
    mac_info: dict[str, Any],
    ip_intel: dict[str, Any],
    exploit: dict[str, Any],
    direction: str,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    n = 1
    steps.append({
        "step": n,
        "node": vector,
        "type": "vector",
        "label": exploit.get("summary") or vector,
        "direction": direction,
    })
    n += 1
    if peer:
        steps.append({
            "step": n,
            "node": peer,
            "type": "peer",
            "label": ip_intel.get("label") or peer,
            "addr_version": ip_intel.get("addr_version", "ipv4"),
            "direction": direction,
        })
        n += 1
    if proc:
        steps.append({
            "step": n,
            "node": proc,
            "type": "process",
            "label": proc,
            "direction": direction,
        })
        n += 1
    if mac_info.get("mac"):
        steps.append({
            "step": n,
            "node": mac_info["mac"],
            "type": "mac",
            "label": mac_info.get("vendor", "MAC vendor"),
            "direction": "at_us" if direction == "at_us" else "adjacent",
        })
        n += 1
    for cve in (exploit.get("cves") or [])[:3]:
        steps.append({
            "step": n,
            "node": cve,
            "type": "cve",
            "label": f"{cve} — {(exploit.get('exploit_class_label') or exploit.get('exploit_class', ''))}",
            "exploit_class": exploit.get("exploit_class"),
        })
        n += 1
    for tid in (exploit.get("mitre") or [])[:2]:
        steps.append({
            "step": n,
            "node": tid,
            "type": "mitre",
            "label": f"MITRE ATT&CK {tid}",
        })
        n += 1
    return steps


def build_dossiers(online: bool = False) -> dict[str, Any]:
    cve_map = _load_cve_map()
    oui_db = _load_oui_table()
    arp = _load_arp_table()
    cache = _load_json(INTEL_CACHE, {"ips": {}})
    scour = _load_json(SCOUR_PATH, {})
    conn_data = _load_json(CONN_INTENT, {})
    threats: list[dict[str, str]] = []
    if THREATS_TSV.is_file():
        for line in THREATS_TSV.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("ts\t"):
                continue
            parts = line.split("\t")
            if len(parts) >= 4:
                threats.append({
                    "ts": parts[0],
                    "vector": parts[1],
                    "severity": parts[2],
                    "detail": parts[3],
                })

    # Index scour by peer
    scour_by_peer: dict[str, dict[str, Any]] = {}
    for av in scour.get("active_vectors") or []:
        p = av.get("remote_ip") or av.get("peer")
        if p:
            scour_by_peer[p] = av

    conn_by_peer: dict[str, dict[str, Any]] = {}
    for c in conn_data.get("connections") or []:
        p = c.get("remote_ip")
        if p:
            conn_by_peer[p] = c

    dossiers: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_dossier(
        vector: str,
        peer: str,
        addr_ver: str,
        proc: str,
        pid: str,
        direction: str,
        direction_label: str,
        severity: str,
        detail: str,
        ts: str,
    ) -> None:
        key = f"{vector}:{peer}:{direction}:{proc}"
        if key in seen:
            return
        seen.add(key)

        ip_intel = _intel_for_peer(peer, addr_ver, cache)
        if peer in scour_by_peer:
            si = scour_by_peer[peer].get("ip_intel") or {}
            ip_intel.update({k: v for k, v in si.items() if k != "_ts"})

        mac = arp.get(peer, "")
        if not mac and peer:
            # gateway / neighbor heuristic for IPv4 LAN peers
            for ip_key, mac_val in arp.items():
                if ip_key.startswith(peer.rsplit(".", 1)[0] + ".") if "." in peer else False:
                    mac = mac_val
                    break
        mac_info = lookup_mac_vendor(mac, oui_db, online) if mac else {"mac": "", "vendor": "No ARP entry", "source": "none"}

        exploit = _vector_exploit_intel(vector, cve_map)
        path = _build_attack_path(vector, peer, proc, mac_info, ip_intel, exploit, direction)

        lookback = "We look back HARD — dossier links vector to peer, process, MAC, and CVE chain."
        if direction == "at_us":
            lookback = "They looked at us — dossier traces inbound path with MAC + exploit cross-ref."

        dossiers.append({
            "id": f"dossier-{len(dossiers)+1}",
            "ts": ts or _now(),
            "vector": vector,
            "severity": severity,
            "detail": detail[:200],
            "peer": peer,
            "addr_version": addr_ver,
            "direction": direction,
            "direction_label": direction_label,
            "process": proc,
            "pid": pid,
            "ip_intel": ip_intel,
            "mac_intel": mac_info,
            "exploit_intel": exploit,
            "attack_path": path,
            "lookback": lookback,
            "gatekeeper": conn_by_peer.get(peer, {}),
        })

    # Threat diary → dossiers
    for t in threats[-60:]:
        vector = t["vector"]
        detail = t["detail"]
        for peer, ver in _extract_addrs(detail):
            if _is_private_addr(peer):
                continue
            add_dossier(
                vector, peer, ver, "", "", "from_us",
                "From us / threat-linked egress", t["severity"], detail, t["ts"],
            )

    # Live connections → dossiers for suspicious+
    try:
        proc = subprocess.run(["ss", "-H", "-tunap"], capture_output=True, text=True, timeout=12)
        ss_lines = proc.stdout.splitlines()
    except (subprocess.SubprocessError, OSError):
        ss_lines = []

    for line in ss_lines:
        p = _parse_ss_peer(line)
        peer = p.get("remote_ip") or p.get("local_ip")
        if not peer or _is_private_addr(peer):
            continue
        addr_ver = p.get("addr_version", "ipv4")
        gk = conn_by_peer.get(peer, {})
        verdict = gk.get("verdict", "MONITOR")
        vectors = []
        if peer in scour_by_peer:
            vectors = scour_by_peer[peer].get("threat_vectors") or []
        vector = vectors[0] if vectors else (
            "EGRESS_BEACON" if verdict in ("SUSPICIOUS", "HARM_CANDIDATE") else "CONN_OBSERVED"
        )
        if verdict in ("MONITOR", "USER_OK", "EPHEMERAL") and not vectors:
            continue
        add_dossier(
            vector, peer, addr_ver, p.get("process", ""), p.get("pid", ""),
            p.get("direction", "from_us"), p.get("direction_label", ""),
            "medium" if verdict == "SUSPICIOUS" else "high",
            p.get("line", ""), _now(),
        )

    dossiers.sort(key=lambda d: (
        0 if d.get("severity") == "critical" else 1 if d.get("severity") == "high" else 2,
        0 if d.get("direction") == "at_us" else 1,
        -len(d.get("attack_path") or []),
    ))

    out = {
        "updated": _now(),
        "motto": "Let's Be Angels — we look back HARD.",
        "online": online,
        "dossier_count": len(dossiers),
        "at_us_count": sum(1 for d in dossiers if d.get("direction") == "at_us"),
        "from_us_count": sum(1 for d in dossiers if d.get("direction") == "from_us"),
        "ipv4_count": sum(1 for d in dossiers if d.get("addr_version") == "ipv4"),
        "ipv6_count": sum(1 for d in dossiers if d.get("addr_version") == "ipv6"),
        "dossiers": dossiers[:50],
    }
    _save_json(DOSSIER_PATH, out)
    return out


def build_research_tables(online: bool = False) -> dict[str, Any]:
    cve_map = _load_cve_map()
    oui_db = _load_oui_table()
    arp = _load_arp_table()
    cache = _load_json(INTEL_CACHE, {"ips": {}})
    dossier_data = _load_json(DOSSIER_PATH, {"dossiers": []})

    mac_table: list[dict[str, Any]] = []
    seen_mac: set[str] = set()
    for ip, mac in sorted(arp.items()):
        if mac in seen_mac:
            continue
        seen_mac.add(mac)
        mac_table.append({
            "ip": ip,
            "addr_version": "ipv6" if ":" in ip else "ipv4",
            **lookup_mac_vendor(mac, oui_db, online),
        })

    ip_table: list[dict[str, Any]] = []
    for ip, entry in sorted((cache.get("ips") or {}).items()):
        ip_table.append({
            "ip": ip,
            "addr_version": "ipv6" if ":" in ip else "ipv4",
            "label": entry.get("label", ""),
            "org": entry.get("org", ""),
            "ip_class": entry.get("ip_class", ""),
            "source": entry.get("source", ""),
        })

    exploit_table: list[dict[str, Any]] = []
    for vector, info in sorted((cve_map.get("vectors") or {}).items()):
        exploit_table.append({
            "vector": vector,
            "mitre": info.get("mitre", []),
            "cves": info.get("cves", []),
            "exploit_class": info.get("exploit_class", ""),
            "class_label": (cve_map.get("exploit_classes") or {}).get(info.get("exploit_class", ""), ""),
            "summary": info.get("summary", ""),
        })

    path_table: list[dict[str, Any]] = []
    for d in dossier_data.get("dossiers") or []:
        path_table.append({
            "dossier_id": d.get("id"),
            "vector": d.get("vector"),
            "peer": d.get("peer"),
            "direction": d.get("direction"),
            "addr_version": d.get("addr_version"),
            "steps": len(d.get("attack_path") or []),
            "attack_path": d.get("attack_path"),
        })

    out = {
        "updated": _now(),
        "motto": "Let's Be Angels — research tables, zero unknowns.",
        "online": online,
        "tables": {
            "mac_vendors": mac_table[:40],
            "ip_intel": ip_table[:40],
            "exploit_cve_map": exploit_table,
            "attack_paths": path_table[:30],
            "oui_entries_loaded": len(oui_db),
            "cve_vectors_mapped": len(exploit_table),
        },
    }
    _save_json(RESEARCH_PATH, out)
    return out


def build_all(online: bool = False) -> dict[str, Any]:
    if not online:
        # quick probe
        try:
            import socket
            with socket.create_connection(("1.1.1.1", 443), timeout=2):
                online = True
        except OSError:
            online = False
    dossiers = build_dossiers(online=online)
    research = build_research_tables(online=online)
    return {
        "updated": _now(),
        "motto": "Let's Be Angels",
        "dossiers": dossiers,
        "research": research,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: angel-dossier.py [build|dossiers|research]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    online = "--online" in sys.argv
    if cmd == "build":
        json.dump(build_all(online=online), sys.stdout, indent=2)
    elif cmd == "dossiers":
        json.dump(build_dossiers(online=online), sys.stdout, indent=2)
    elif cmd == "research":
        json.dump(build_research_tables(online=online), sys.stdout, indent=2)
    else:
        print("usage: angel-dossier.py [build|dossiers|research]", file=sys.stderr)
        return 1
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())