#!/usr/bin/env pythong
"""NEXUS Vector Intelligence — classify every peer and process; never leave unknown.

When internet is available, enriches IPs via PTR + ip-api.com (cached).
Offline: CDN heuristics, PTR, and inferred labels — always a named classification.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
CACHE_PATH = STATE / "vector-intel-cache.json"
SCOUR_PATH = STATE / "vector-scour.json"
THREATS_TSV = STATE / "threat-vectors.tsv"
TRUSTED_TSV = STATE / "firewall-trusted.tsv"

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)
STREAM_CDN_PREFIXES = (
    "104.18.", "104.16.", "172.64.", "172.66.", "140.82.", "185.199.",
    "34.107.", "64.233.", "151.101.", "23.", "34.120.", "13.32.", "13.33.", "13.35.",
)
SEARCH_CDN_PREFIXES = (
    "34.", "35.", "142.250.", "172.217.", "216.58.", "13.", "20.", "40.", "52.", "104.", "151.101.", "199.16.",
)
HARM_PORTS = frozenset({"4444", "5555", "1337", "31337", "6666", "9001", "9050", "1080", "3128"})
CDN_ORG_HINTS = (
    ("cloudflare", "stream_cdn", "Cloudflare CDN"),
    ("google", "search_cdn", "Google / Alphabet"),
    ("amazon", "cloud_aws", "Amazon Web Services"),
    ("microsoft", "cloud_azure", "Microsoft Azure"),
    ("akamai", "stream_cdn", "Akamai CDN"),
    ("fastly", "stream_cdn", "Fastly CDN"),
    ("github", "stream_cdn", "GitHub"),
    ("digitalocean", "hosting", "DigitalOcean hosting"),
    ("ovh", "hosting", "OVH hosting"),
    ("hetzner", "hosting", "Hetzner hosting"),
    ("linode", "hosting", "Linode / Akamai hosting"),
    ("cloudfront", "stream_cdn", "Amazon CloudFront"),
)

CACHE_TTL_ONLINE = 86400
CACHE_TTL_OFFLINE = 3600
ONLINE_PROBE_HOSTS = ("1.1.1.1", "8.8.8.8", "github.com")


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


def has_internet(timeout: float = 2.5) -> bool:
    for host in ONLINE_PROBE_HOSTS:
        try:
            with socket.create_connection((host, 443 if host != "1.1.1.1" else 53), timeout=timeout):
                return True
        except OSError:
            try:
                with socket.create_connection((host, 80), timeout=timeout):
                    return True
            except OSError:
                continue
    return False


def reverse_ptr(ip: str) -> str:
    if not ip or PRIVATE_RE.match(ip):
        return ""
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host or ""
    except OSError:
        return ""


def _prefix_class(ip: str) -> tuple[str, str]:
    if not ip:
        return "unresolved", "No remote address"
    if PRIVATE_RE.match(ip):
        if ip.startswith("127."):
            return "loopback", "Local machine (loopback)"
        return "private", "Private LAN address"
    for p in STREAM_CDN_PREFIXES:
        if ip.startswith(p):
            return "stream_cdn", "Major streaming / web CDN"
    for p in SEARCH_CDN_PREFIXES:
        if ip.startswith(p):
            return "search_cdn", "Search / social CDN"
    return "classified_remote", "Public internet peer"


def _org_class(org: str, asname: str = "") -> tuple[str, str]:
    blob = f"{org} {asname}".lower()
    for needle, ip_class, label in CDN_ORG_HINTS:
        if needle in blob:
            return ip_class, label
    if org:
        return "identified_org", org.strip()
    if asname:
        return "identified_org", asname.strip()
    return "classified_remote", "Public internet peer"


def lookup_ip_online(ip: str, timeout: float = 4.0) -> dict[str, Any]:
    url = (
        f"http://ip-api.com/json/{ip}"
        "?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,isp,org,as,asname,reverse,query"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "NEXUS-Shield/2.5 vector-intel"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}

    if data.get("status") != "success":
        return {"ok": False, "error": data.get("message", "lookup failed")}

    org = str(data.get("org") or data.get("isp") or "")
    asname = str(data.get("asname") or "")
    ip_class, label = _org_class(org, asname)
    hostname = str(data.get("reverse") or "")
    if not hostname:
        hostname = reverse_ptr(ip)
    if hostname and label == "Public internet peer":
        label = hostname
    country = str(data.get("countryCode") or "")
    if country and label and country not in label:
        label = f"{label} ({country})"

    lat = data.get("lat")
    lon = data.get("lon")
    return {
        "ok": True,
        "ip": ip,
        "ip_class": ip_class,
        "label": label,
        "org": org,
        "as": str(data.get("as") or ""),
        "asname": asname,
        "country": str(data.get("country") or ""),
        "country_code": str(data.get("countryCode") or ""),
        "region": str(data.get("regionName") or ""),
        "city": str(data.get("city") or ""),
        "zip": str(data.get("zip") or ""),
        "lat": lat if lat is not None else None,
        "lon": lon if lon is not None else None,
        "hostname": hostname,
        "confidence": "high",
        "source": "ip-api",
        "updated": _now(),
    }


def _addr_version(ip: str) -> str:
    try:
        return "ipv6" if isinstance(ipaddress.ip_address(ip.split("%")[0]), ipaddress.IPv6Address) else "ipv4"
    except ValueError:
        return "ipv6" if ":" in ip else "ipv4"


def classify_ip(ip: str, cache: dict[str, Any], online: bool | None = None) -> dict[str, Any]:
    if not ip:
        return {
            "ip": "",
            "ip_class": "unresolved",
            "label": "No remote address",
            "addr_version": "unknown",
            "confidence": "high",
            "source": "local",
            "updated": _now(),
        }

    ver = _addr_version(ip)
    cached = cache.get("ips", {}).get(ip)
    if cached:
        age = time.time() - float(cached.get("_ts", 0))
        ttl = CACHE_TTL_ONLINE if cached.get("source") == "ip-api" else CACHE_TTL_OFFLINE
        if age < ttl:
            return cached

    if ver == "ipv6":
        ip_class, label = "ipv6_global", "IPv6 global peer"
    else:
        ip_class, label = _prefix_class(ip)
    hostname = reverse_ptr(ip) if ver == "ipv4" else ""
    entry: dict[str, Any] = {
        "ip": ip,
        "ip_class": ip_class,
        "label": label,
        "addr_version": ver,
        "hostname": hostname,
        "org": "",
        "confidence": "inferred",
        "source": "heuristic",
        "updated": _now(),
    }

    if hostname and ip_class == "classified_remote":
        entry["label"] = hostname
        entry["confidence"] = "medium"
        entry["source"] = "ptr"

    if online is None:
        online = has_internet()

    if online and ip_class in ("classified_remote", "identified_org", "hosting", "cloud_aws", "cloud_azure"):
        remote = lookup_ip_online(ip)
        if remote.get("ok"):
            entry.update({
                k: remote[k]
                for k in (
                    "ip_class", "label", "org", "as", "asname", "country", "country_code",
                    "region", "city", "zip", "lat", "lon", "hostname", "confidence", "source",
                )
                if k in remote
            })
            entry["updated"] = remote["updated"]

    entry["_ts"] = time.time()
    cache.setdefault("ips", {})[ip] = entry
    return entry


def _read_proc(pid: int) -> dict[str, str]:
    base = Path(f"/proc/{pid}")
    out: dict[str, str] = {"pid": str(pid), "comm": "", "exe": "", "cmdline": ""}
    if not base.is_dir():
        return out
    try:
        out["comm"] = (base / "comm").read_text(encoding="utf-8", errors="replace").strip("\0")
    except OSError:
        pass
    try:
        out["exe"] = os.readlink(base / "exe")
    except OSError:
        pass
    try:
        raw = (base / "cmdline").read_bytes()
        out["cmdline"] = raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()[:240]
    except OSError:
        pass
    return out


def resolve_process_from_line(line: str) -> dict[str, Any]:
    proc = ""
    pid = 0
    m = re.search(r'users:\(\("([^"]+)"[^)]*pid=(\d+)', line)
    if m:
        proc = m.group(1).lower()
        if proc.endswith("-bin"):
            proc = proc[:-4]
        pid = int(m.group(2))
    else:
        m2 = re.search(r"pid=(\d+)", line)
        if m2:
            pid = int(m2.group(1))

    intel: dict[str, Any] = {"proc": proc or f"pid-{pid}" if pid else "background-peer", "pid": pid}
    if pid:
        pinfo = _read_proc(pid)
        if pinfo["comm"]:
            intel["comm"] = pinfo["comm"]
            if not proc or proc.startswith("pid"):
                intel["proc"] = pinfo["comm"]
        if pinfo["exe"]:
            intel["exe"] = pinfo["exe"]
            intel["label"] = Path(pinfo["exe"]).name
            if "/tmp/" in pinfo["exe"] or "/dev/shm/" in pinfo["exe"]:
                intel["risk"] = "temp_binary"
                intel["label"] = f"Temp binary: {intel['label']}"
            else:
                intel["risk"] = "identified"
        else:
            intel["label"] = intel.get("comm") or intel["proc"]
            intel["risk"] = "identified"
        if pinfo["cmdline"]:
            intel["cmdline"] = pinfo["cmdline"]
    else:
        intel["label"] = proc or "kernel-network-peer"
        intel["risk"] = "inferred"
        intel["confidence"] = "medium"

    intel.setdefault("label", intel.get("proc", "network-peer"))
    intel.setdefault("confidence", "high" if pid else "inferred")
    return intel


def _snapshot_connections() -> list[str]:
    try:
        proc = subprocess.run(
            ["ss", "-H", "-tunap"],
            capture_output=True,
            text=True,
            timeout=12,
        )
        return [ln for ln in proc.stdout.splitlines() if ln.strip()]
    except (subprocess.SubprocessError, OSError):
        return []


def _load_threats(limit: int = 120) -> list[dict[str, str]]:
    if not THREATS_TSV.is_file():
        return []
    rows: list[dict[str, str]] = []
    lines = THREATS_TSV.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in lines[-limit:]:
        if line.startswith("ts\t"):
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        rows.append({"ts": parts[0], "vector": parts[1], "severity": parts[2], "detail": parts[3]})
    return rows


def _extract_ips(text: str) -> list[str]:
    found = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    found += [x for x in re.findall(r"(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F]{0,4}", text) if x not in ("::", "::1")]
    return found


def scour_active_vectors(max_online_lookups: int = 12) -> dict[str, Any]:
    online = has_internet()
    cache_doc = _load_json(CACHE_PATH, {"ips": {}, "updated": ""})
    lines = _snapshot_connections()
    threats = _load_threats()
    threat_ips: dict[str, list[str]] = {}
    for t in threats:
        for ip in _extract_ips(t["detail"]):
            if PRIVATE_RE.match(ip):
                continue
            threat_ips.setdefault(ip, []).append(t["vector"])

    active: list[dict[str, Any]] = []
    seen_peers: set[str] = set()
    lookups = 0

    for line in lines:
        if "ESTAB" not in line and "ESTABLISHED" not in line:
            continue
        proc_intel = resolve_process_from_line(line)
        parts = line.split()
        remote_idx = 5
        if parts and parts[0] in ("tcp", "udp", "tcp6", "udp6"):
            remote_idx = 5
        elif len(parts) > 4:
            remote_idx = 4
        remote = parts[remote_idx] if len(parts) > remote_idx else ""
        rip, rport = "", ""
        if remote.startswith("["):
            m6 = re.match(r"\[([^\]]+)\]:(\d+)", remote)
            if m6:
                rip, rport = m6.group(1), m6.group(2)
        elif remote.count(":") > 1:
            idx = remote.rfind(":")
            rip, rport = remote[:idx], remote[idx + 1 :]
        else:
            rip_m = re.match(r"(\d{1,3}(?:\.\d{1,3}){3}):(\d+)", remote)
            if rip_m:
                rip, rport = rip_m.group(1), rip_m.group(2)
        if not rip:
            continue
        if PRIVATE_RE.match(rip) or rip in seen_peers:
            continue
        seen_peers.add(rip)

        if online and lookups < max_online_lookups:
            ip_intel = classify_ip(rip, cache_doc, online=True)
            lookups += 1
        else:
            ip_intel = classify_ip(rip, cache_doc, online=False)

        vectors = threat_ips.get(rip, [])
        pest_score = 0
        if proc_intel.get("risk") == "temp_binary":
            pest_score += 8
        if rport in HARM_PORTS:
            pest_score += 10
        if vectors:
            pest_score += min(10, 2 + len(vectors))
        if ip_intel.get("ip_class") == "classified_remote":
            pest_score += 2

        arsenal = []
        if rip:
            arsenal.append({"action": "block_forever", "target": rip, "label": "Firewall block peer"})
        if proc_intel.get("pid"):
            arsenal.append({"action": "kill_process", "target": str(proc_intel["pid"]), "label": "Stop process"})
        if proc_intel.get("exe") and ("/tmp/" in proc_intel["exe"] or "/dev/shm/" in proc_intel["exe"]):
            arsenal.append({"action": "quarantine_file", "target": proc_intel["exe"], "label": "Quarantine temp binary"})

        direction = "from_us"
        if "LISTEN" in line:
            direction = "at_us"
        elif "SYN-RECV" in line:
            direction = "at_us"

        active.append({
            "remote_ip": rip,
            "remote_port": rport,
            "addr_version": _addr_version(rip),
            "direction": direction,
            "direction_label": "At us" if direction == "at_us" else "From us",
            "process": proc_intel.get("proc", "network-peer"),
            "process_intel": proc_intel,
            "ip_intel": {k: v for k, v in ip_intel.items() if k != "_ts"},
            "threat_vectors": vectors,
            "pest_score": pest_score,
            "is_pest": pest_score >= 8,
            "arsenal": arsenal,
            "line": line[:200],
        })

    # enrich threat-only IPs not in active connections
    for ip, vecs in threat_ips.items():
        if ip in seen_peers:
            continue
        if online and lookups < max_online_lookups:
            ip_intel = classify_ip(ip, cache_doc, online=True)
            lookups += 1
        else:
            ip_intel = classify_ip(ip, cache_doc, online=False)
        active.append({
            "remote_ip": ip,
            "remote_port": "",
            "process": "threat-linked-peer",
            "process_intel": {"label": "Threat diary peer", "confidence": "inferred"},
            "ip_intel": {k: v for k, v in ip_intel.items() if k != "_ts"},
            "threat_vectors": vecs,
            "pest_score": min(12, 4 + len(vecs)),
            "is_pest": len(vecs) >= 2,
            "arsenal": [{"action": "block_forever", "target": ip, "label": "Firewall block peer"}],
            "line": "",
        })

    active.sort(key=lambda x: (-x.get("pest_score", 0), x.get("remote_ip", "")))
    pests = [a for a in active if a.get("is_pest")]

    cache_doc["updated"] = _now()
    cache_doc["online"] = online
    _save_json(CACHE_PATH, cache_doc)

    out = {
        "updated": _now(),
        "online": online,
        "lookups": lookups,
        "active_count": len(active),
        "pest_count": len(pests),
        "active_vectors": active[:80],
        "pests": pests[:30],
        "arsenal_catalog": [
            {"id": "block_forever", "label": "Block peer forever", "safe": True},
            {"id": "block_day", "label": "Block peer 1 day", "safe": True},
            {"id": "kill_process", "label": "Stop host process", "safe": False},
            {"id": "quarantine_file", "label": "Quarantine temp binary", "safe": False},
            {"id": "eradicate", "label": "Full eradicate (block + stop + quarantine)", "safe": False},
        ],
        "never_unknown": True,
    }
    _save_json(SCOUR_PATH, out)
    return out


def get_cache() -> dict[str, Any]:
    return _load_json(CACHE_PATH, {"ips": {}, "updated": ""})


def lookup_one(ip: str) -> dict[str, Any]:
    cache_doc = _load_json(CACHE_PATH, {"ips": {}, "updated": ""})
    entry = classify_ip(ip, cache_doc, online=has_internet())
    cache_doc["updated"] = _now()
    _save_json(CACHE_PATH, cache_doc)
    return {k: v for k, v in entry.items() if k != "_ts"}


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: vector-intel.py [scour|lookup <ip>|cache]", file=sys.stderr)
        return 1
    cmd = sys.argv[1]
    if cmd == "scour":
        json.dump(scour_active_vectors(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if cmd == "cache":
        json.dump(get_cache(), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if cmd == "lookup" and len(sys.argv) >= 3:
        json.dump(lookup_one(sys.argv[2]), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    print("usage: vector-intel.py [scour|lookup <ip>|cache]", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())