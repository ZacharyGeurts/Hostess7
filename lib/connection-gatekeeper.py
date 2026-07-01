#!/usr/bin/env pythong
"""NEXUS Connection Gatekeeper — 10-axis IFF per live connection.

Civilian contacts identified and permitted. Hostile contacts interdicted without
hesitation. Unknown contacts held for positive identification before permit expansion.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
HISTORY = STATE / "connection-history.json"
TRUSTED_TSV = STATE / "firewall-trusted.tsv"
THREATS_TSV = STATE / "threat-vectors.tsv"
INTEL_CACHE = STATE / "vector-intel-cache.json"

BROWSER_PROCS = frozenset({
    "fieldfox", "field-queen", "queen-browser",
    "firefox", "chrome", "chromium", "brave", "brave-browser", "vivaldi", "opera",
    "msedge", "waterfox", "librewolf", "floorp", "thorium",
    "google-chrome", "google-chrome-stable",
})
EMAIL_PROCS = frozenset({
    "thunderbird", "betterbird", "evolution", "geary", "mailspring", "kmail",
    "sylpheed", "claws-mail", "slack", "zoom", "zoomclient", "teams", "teams-for-linux",
})
MEDIA_PROCS = BROWSER_PROCS | EMAIL_PROCS | frozenset({
    "vlc", "mpv", "totem", "spotify", "discord", "obs", "ffmpeg",
    "youtube", "celluloid", "streamlink", "grok",
})
CONSUMER_PROCS = BROWSER_PROCS | EMAIL_PROCS | MEDIA_PROCS
SEARCH_CDN_PREFIXES = (
    "34.", "35.", "142.250.", "172.217.", "216.58.",  # Google
    "13.", "20.", "40.", "52.", "104.",  # Azure/CF misc
    "151.101.", "199.16.",  # Fastly
)
STREAM_CDN_PREFIXES = (
    "104.18.", "104.16.", "172.64.", "172.66.",  # Cloudflare
    "140.82.", "185.199.", "140.82.113.",  # GitHub
    "34.107.", "64.233.",  # Google CDN
    "151.101.", "23.", "34.120.",  # Akamai/Fastly
    "13.32.", "13.33.", "13.35.",  # CloudFront
)
HARM_PORTS = frozenset({
    "4444", "5555", "1337", "31337", "6666", "6667", "9001", "9050", "1080", "3128",
    "4443", "8080", "8443", "3004", "3005", "6006", "6606", "8808",
})
KILL_VECTORS = frozenset({
    "C2_BEACON", "PACKET_INJECTION", "DNS_TUNNEL", "DNS_POISON", "RAW_SOCKET_INJECTION",
    "RST_FLOOD", "EGRESS_BEACON", "CONN_HARM",
    "AI_BEACON_PRECISION", "AI_LOLBIN_CHAIN", "AI_ROGUE_INFRA", "AI_EXFIL_SHAPE",
    "AI_AUTOSCAN", "AI_ML_C2_STACK", "AI_DNS_TUNNEL",
})
PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)
TRUST_RANK = {
    "USER_OK": 0,
    "EPHEMERAL": 1,
    "MONITOR": 2,
    "SUSPICIOUS": 3,
    "HARM_CANDIDATE": 4,
}

# IFF — Identification Friend/Foe (civilian vs hostile, zero-hesitation interdict)
IFF_TABLE: dict[str, tuple[str, str, str]] = {
    "USER_OK": ("CIVILIAN", "AUTHORIZED", "PASS — operator-initiated egress confirmed"),
    "EPHEMERAL": ("CIVILIAN", "TRANSIENT", "PASS — short-cycle CDN, no hostile signature"),
    "MONITOR": ("CIVILIAN", "ROUTINE", "PASS — routine egress under continuous watch"),
    "SUSPICIOUS": ("UNKNOWN", "CONTACT", "HOLD — positive identification required before permit"),
    "HARM_CANDIDATE": ("HOSTILE", "CONFIRMED", "INTERDICT — block immediately, zero hesitation"),
}


def _iff_resolve(verdict: str, block_rec: bool = False) -> dict[str, str]:
    if verdict == "HARM_CANDIDATE" or block_rec:
        iff, iff_class, enforcement = IFF_TABLE["HARM_CANDIDATE"]
    else:
        iff, iff_class, enforcement = IFF_TABLE.get(
            verdict, ("UNKNOWN", "CONTACT", "HOLD — classify before permit expansion"),
        )
    return {
        "iff": iff,
        "iff_class": iff_class,
        "iff_label": f"{iff} · {iff_class}",
        "enforcement": enforcement,
    }
# v4.0 packet permission: ranks 0–2 (USER_OK, EPHEMERAL, MONITOR) auto-permit at zero nft cost.
MIN_ACCEPT_TRUST_RANK = 2

SITE_IP_HINTS = {
    "104.244.": "x.com",
    "199.16.": "x.com",
    "199.59.": "x.com",
    "192.133.": "x.com",
}
HOST_ALIASES = {
    "twitter.com": "x.com",
    "t.co": "x.com",
    "twimg.com": "x.com",
}
_honor_mod: Any = None


def _honor_module():
    global _honor_mod
    if _honor_mod is not None:
        return _honor_mod
    import importlib.util

    spec = importlib.util.spec_from_file_location("honorability_db", INSTALL / "lib" / "honorability-db.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    _honor_mod = mod
    return mod


def _infer_site_host(rip: str, intel: dict[str, Any]) -> str:
    label = intel.get("hostname") or intel.get("label") or ""
    host = ""
    if label and "." in str(label):
        host = str(label).split()[0].lower()
    for prefix, site in SITE_IP_HINTS.items():
        if rip.startswith(prefix):
            return site
    if host:
        return HOST_ALIASES.get(host, host)
    return ""


def _apply_honorability(
    proc: str,
    rip: str,
    intel: dict[str, Any],
    verdict: str,
    trust_rank: int,
    scores: dict[str, Any],
) -> tuple[str, int, dict[str, Any]]:
    if proc.lower() not in BROWSER_PROCS:
        return verdict, trust_rank, {}
    host = _infer_site_host(rip, intel)
    if not host:
        return verdict, trust_rank, {}
    try:
        info = _honor_module().lookup(host)
    except Exception:
        return verdict, trust_rank, {}
    meta = {
        "active_site": host,
        "honor_stars": info["stars"],
        "honor_gold": info["gold"],
        "honor_needs_acceptance": info["needs_acceptance"],
        "honor_label": info["stars_label"],
        "protection_level": info.get("protection_level") or "standard",
    }
    extreme_meta: dict[str, Any] = {}
    if int(info.get("stars") or 0) >= 4:
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location(
                "host_security_tier", INSTALL / "lib" / "host-security-tier.py",
            )
            if spec and spec.loader:
                tier_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(tier_mod)
                extreme_meta = tier_mod.endpoint_extreme_meta(int(info["stars"]))
        except Exception:
            extreme_meta = {
                "security_level": "extreme",
                "extreme_endpoint_protection": True,
                "extreme_watch": True,
            }
        meta.update(extreme_meta)
        scores["process_trust"] = max(int(scores.get("process_trust") or 0), 8)
        scores["operator_auth"] = max(int(scores.get("operator_auth") or 0), 6)
    if info["gold"]:
        scores["user_browser"] = max(int(scores.get("user_browser") or 0), 10)
        return "USER_OK", TRUST_RANK["USER_OK"], meta
    if info["stars"] >= 4 and not info["needs_acceptance"]:
        return verdict, min(trust_rank, TRUST_RANK["EPHEMERAL"]), meta
    if info["needs_acceptance"]:
        meta["honor_pending_accept"] = True
    return verdict, trust_rank, meta


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


def _heaven_hell_doctrine() -> dict[str, Any]:
    return _load_json(INSTALL / "data" / "heaven-hell-doctrine.json", {})


def _heaven_hell_motto() -> str:
    doc = _heaven_hell_doctrine()
    return str(
        doc.get("heaven_hell_motto")
        or "We know Heaven from Hell. To those who chose Hell, we also choose it for them. "
        "No mercy. No friendly fire. God Bless."
    )


def _know_doctrine() -> str:
    doc = _heaven_hell_doctrine()
    return str(
        doc.get("motto")
        or "Know that nothing is unseen and nothing is fully secure. "
        "We can't hide all the rocks, so send Hell to Hell."
    )


def _field_thermal_meta() -> dict[str, Any]:
    """NEXUS-Shield thermal guard — headroom + stealth rate limit for gatekeeper."""
    guard = _load_json(STATE / "field-thermal-guard.json", {})
    rate = _load_json(STATE / "field-thermal-rate-limit.json", {})
    metrics = _load_json(STATE / "field-thermal-metrics.json", {})
    active = bool(rate.get("active"))
    headroom = guard.get("headroom_pct")
    field_intensity = 1.0
    if headroom is not None and headroom < 80.0:
        field_intensity = max(0.2, float(headroom) / 100.0)
    if active:
        field_intensity = min(field_intensity, 0.75)
    return {
        "headroom_pct": headroom,
        "rate_limit_active": active,
        "max_joules_per_second": rate.get("max_joules_per_second") or guard.get("max_joules_per_second"),
        "incremental_only": guard.get("incremental_only", True),
        "monolithic_blast_forbidden": guard.get("monolithic_blast_forbidden", True),
        "certainty_score": metrics.get("certainty_score") or guard.get("certainty_score"),
        "field_intensity_scale": round(field_intensity, 3),
        "burst_derating_ratio": metrics.get("burst_derating_ratio"),
    }


def _save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _load_trusted() -> set[str]:
    ips: set[str] = set()
    if not TRUSTED_TSV.is_file():
        return ips
    for line in TRUSTED_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 3 and parts[2]:
            ips.add(parts[2])
    return ips


def _is_private_ip(addr: str) -> bool:
    if not addr:
        return True
    try:
        ip = ipaddress.ip_address(addr.split("%")[0])
        return ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
    except ValueError:
        return PRIVATE_RE.match(addr) is not None


def _addr_version(addr: str) -> str:
    if not addr:
        return "unknown"
    try:
        return "ipv6" if isinstance(ipaddress.ip_address(addr.split("%")[0]), ipaddress.IPv6Address) else "ipv4"
    except ValueError:
        return "ipv6" if ":" in addr else "ipv4"


def _connection_direction(state: str) -> tuple[str, str]:
    if state in ("LISTEN", "LISTENING"):
        return "at_us", "At us — listening"
    if state in ("SYN-RECV", "SYN_RECV"):
        return "at_us", "At us — inbound"
    return "from_us", "From us → outbound"


def _recent_threat_ips(limit: int = 80) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if not THREATS_TSV.is_file():
        return out
    lines = THREATS_TSV.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]
    for line in lines[1:] if len(lines) > 1 else lines:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        vector, detail = parts[1], parts[3]
        for key in ("dst=", "ip="):
            m = re.search(rf"{re.escape(key)}([^\s;]+)", detail)
            if m:
                ip = m.group(1).strip()
                if ip and not _is_private_ip(ip):
                    out.setdefault(ip, []).append(vector)
        for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", detail):
            if not _is_private_ip(ip):
                out.setdefault(ip, []).append(vector)
        for ip in re.findall(r"(?:[0-9a-fA-F]{0,4}:){2,}[0-9a-fA-F]{0,4}", detail):
            if ip not in ("::", "::1") and not _is_private_ip(ip):
                out.setdefault(ip, []).append(vector)
    return out


def _parse_addr(addr: str) -> tuple[str, str]:
    if not addr or addr in ("*:*", "[*]:*"):
        return "", ""
    host = addr.strip("[]")
    if host.count(":") > 1 and "]" not in addr:
        # bare IPv6 host:port
        idx = host.rfind(":")
        return host[:idx], host[idx + 1 :]
    if addr.startswith("["):
        m = re.match(r"\[([^\]]+)\]:(\d+)", addr)
        if m:
            return m.group(1), m.group(2)
    if ":" in host:
        h, p = host.rsplit(":", 1)
        return h, p
    return host, ""


def _load_intel_cache() -> dict[str, Any]:
    return _load_json(INTEL_CACHE, {"ips": {}})


def _resolve_proc_pid(line: str, proc: str) -> tuple[str, int]:
    pid = 0
    m = re.search(r'users:\(\("([^"]+)"[^)]*pid=(\d+)', line)
    if m:
        if not proc:
            proc = m.group(1).lower()
            if proc.endswith("-bin"):
                proc = proc[:-4]
        pid = int(m.group(2))
    else:
        m2 = re.search(r"pid=(\d+)", line)
        if m2:
            pid = int(m2.group(2))
    if (not proc or proc == "pid-unknown") and pid:
        comm_path = Path(f"/proc/{pid}/comm")
        try:
            comm = comm_path.read_text(encoding="utf-8", errors="replace").strip("\0")
            if comm:
                proc = comm.lower()
        except OSError:
            proc = f"pid-{pid}"
    if not proc:
        proc = "network-peer"
    return proc, pid


def _intel_for_ip(ip: str, cache: dict[str, Any]) -> dict[str, Any]:
    entry = (cache.get("ips") or {}).get(ip)
    if entry:
        return {
            "ip_class": entry.get("ip_class") or "classified_remote",
            "label": entry.get("label") or "Public internet peer",
            "org": entry.get("org") or "",
            "hostname": entry.get("hostname") or "",
            "confidence": entry.get("confidence") or "inferred",
            "source": entry.get("source") or "cache",
        }
    ip_class = _ip_class_legacy(ip)
    label = {
        "stream_cdn": "Major streaming / web CDN",
        "search_cdn": "Search / social CDN",
        "private": "Private LAN address",
        "classified_remote": "Public internet peer",
    }.get(ip_class, "Public internet peer")
    return {
        "ip_class": ip_class,
        "label": label,
        "org": "",
        "hostname": "",
        "confidence": "inferred",
        "source": "heuristic",
    }


def _parse_ss(line: str) -> dict[str, str]:
    parts = line.split()
    proc = ""
    pid = 0
    m = re.search(r'users:\(\("([^"]+)"', line)
    if m:
        proc = m.group(1).lower()
        if proc.endswith("-bin"):
            proc = proc[:-4]
    proc, pid = _resolve_proc_pid(line, proc)
    state = parts[0] if parts else ""
    local_idx, remote_idx = 3, 4
    if parts and parts[0] in ("tcp", "udp", "tcp6", "udp6"):
        state = parts[1] if len(parts) > 1 else state
        local_idx, remote_idx = 4, 5
    local = parts[local_idx] if len(parts) > local_idx else ""
    remote = parts[remote_idx] if len(parts) > remote_idx else ""
    lip, lport = _parse_addr(local)
    rip, rport = _parse_addr(remote)
    return {
        "state": state,
        "local": local,
        "remote": remote,
        "local_ip": lip,
        "local_port": lport,
        "remote_ip": rip,
        "remote_port": rport,
        "proc": proc,
        "pid": str(pid) if pid else "",
        "line": line,
    }


def _ip_class_legacy(ip: str) -> str:
    if not ip or PRIVATE_RE.match(ip):
        return "private"
    for p in STREAM_CDN_PREFIXES:
        if ip.startswith(p):
            return "stream_cdn"
    for p in SEARCH_CDN_PREFIXES:
        if ip.startswith(p):
            return "search_cdn"
    return "classified_remote"


def _axis_user_browser(proc: str) -> tuple[int, str]:
    if proc in BROWSER_PROCS:
        return 9, f"browser:{proc}"
    if proc in EMAIL_PROCS:
        return 8, f"email:{proc}"
    if proc in MEDIA_PROCS:
        return 7, f"media_app:{proc}"
    if proc in ("", "pid-unknown", "network-peer"):
        return 2, "unidentified_process"
    if "/tmp/" in proc or "/dev/shm/" in proc:
        return 0, f"tmp_binary:{proc}"
    return 4, f"daemon:{proc}"


def _axis_media_stream(proc: str, rport: str, ip_class: str) -> tuple[int, str]:
    score = 0
    notes = []
    if rport in ("443", "80", "8080", "8443") and ip_class in ("stream_cdn", "search_cdn"):
        score += 5
        notes.append("https_cdn")
    if proc in BROWSER_PROCS and rport == "443":
        score += 4
        notes.append("browser_https")
    if proc in ("vlc", "mpv", "totem", "spotify", "obs", "ffmpeg", "streamlink"):
        score += 8
        notes.append("media_client")
    if rport in ("1935", "554", "8554", "8081"):
        score += 9
        notes.append("raw_stream_port")
    return min(10, score), ",".join(notes) or "none"


def _axis_search_ephemeral(key: str, history: dict, ip_class: str) -> tuple[int, str]:
    h = history.get(key, {})
    seen = int(h.get("seen_count", 0))
    age = int(h.get("age_ticks", 0))
    if ip_class == "search_cdn":
        base = 7
    elif ip_class == "stream_cdn":
        base = 3
    else:
        base = 1
    if seen <= 2 and age <= 3:
        base += 3
        note = "ephemeral_search_tab"
    elif seen >= 8:
        base -= 2
        note = "stable_session"
    else:
        note = "normal_churn"
    return max(0, min(10, base)), note


def _axis_bandwidth_abuse(proc: str, ip_class: str, rport: str) -> tuple[int, str]:
    if proc in CONSUMER_PROCS:
        return 1, "user_app_expected"
    if ip_class == "classified_remote" and rport == "443":
        return 6, "remote_bulk_https"
    if ip_class in ("classified_remote", "hosting", "identified_org"):
        return 8, "non_cdn_egress"
    return 2, "cdn_normal"


def _axis_stream_theft(proc: str, rport: str, lip: str) -> tuple[int, str]:
    if proc in CONSUMER_PROCS:
        return 0, "user_media_path"
    if rport in ("1935", "554", "8554", "8081", "9000"):
        return 10, "non_browser_stream_port"
    if lip.endswith(":443") and rport not in ("443", "80"):
        return 7, "tls_downgrade_hint"
    if proc and proc not in MEDIA_PROCS and rport == "443":
        return 5, "daemon_https_possible_exfil"
    return 1, "low"


def _axis_beacon(proc: str, key: str, history: dict) -> tuple[int, str]:
    h = history.get(key, {})
    seen = int(h.get("seen_count", 0))
    if proc in BROWSER_PROCS:
        return 1, "browser_on_demand"
    if seen >= 20 and proc not in BROWSER_PROCS:
        return 7, "persistent_daemon_session"
    if seen >= 5:
        return 4, "recurring"
    return 2, "fresh"


def _axis_process_trust(proc: str) -> tuple[int, str]:
    if proc in BROWSER_PROCS:
        return 10, "signed_browser"
    if proc in EMAIL_PROCS:
        return 9, "known_email"
    if proc in MEDIA_PROCS:
        return 8, "known_media"
    if "/tmp/" in proc or "/dev/shm/" in proc or proc.startswith("."):
        return 0, "untrusted_path"
    if proc in ("", "pid-unknown", "network-peer"):
        return 3, "unidentified"
    return 5, "system_daemon"


def _axis_destination(ip_class: str, rport: str) -> tuple[int, str]:
    harm = 0
    if ip_class in ("classified_remote", "hosting", "identified_org", "cloud_aws", "cloud_azure"):
        harm = 7
    elif ip_class == "search_cdn":
        harm = 2
    elif ip_class == "stream_cdn":
        harm = 1
    elif ip_class == "private":
        harm = 0
    if rport in HARM_PORTS:
        harm = 10
    return harm, ip_class if rport not in HARM_PORTS else f"{ip_class}+bad_port"


def _axis_threat_linked(rip: str, threats: dict[str, list[str]]) -> tuple[int, str]:
    vecs = threats.get(rip, [])
    if not vecs:
        return 0, "clean"
    real = [v for v in vecs if v not in ("C2_CORRELATION", "RST_FLOOD")]
    if real:
        return min(10, 4 + len(real)), ",".join(real[:3])
    return min(6, len(vecs)), "meta_noise:" + ",".join(vecs[:2])


def _axis_auth(rip: str, trusted: set[str]) -> tuple[int, str]:
    if rip in trusted:
        return 10, "operator_authorized"
    return 0, "not_authorized"


def _build_suggestion(
    scores: dict[str, int],
    notes: dict[str, str],
    verdict: str,
    reason: str,
    proc: str,
    rip: str,
    rport: str,
    ip_class: str,
    harm_total: int,
    user_total: int,
    block_rec: bool,
) -> dict[str, Any]:
    friendly: list[str] = []
    unfriendly: list[str] = []
    proc_name = proc or "background app"

    ub = int(scores.get("user_browser", 0))
    if proc in EMAIL_PROCS:
        friendly.append(f"{proc_name} is a mail or chat app — everyday email and messaging ({ub}/10).")
    elif ub >= 7:
        friendly.append(f"{proc_name} looks like a browser or media app you opened ({ub}/10).")
    elif ub <= 3:
        unfriendly.append(
            f"{proc_name} is not a browser ({ub}/10) — background apps calling out deserve a closer look."
        )

    ms = int(scores.get("media_stream", 0))
    if ms >= 6:
        friendly.append(f"HTTPS/stream pattern matches normal video or web traffic ({ms}/10).")

    se = int(scores.get("search_ephemeral", 0))
    if se >= 6:
        friendly.append(f"Short-lived tab-style traffic to a search or social CDN ({se}/10).")

    ba = int(scores.get("bandwidth_abuse", 0))
    if ba >= 6:
        unfriendly.append(
            f"Unusual outbound data volume for this app type ({ba}/10: {notes.get('bandwidth_abuse', '')})."
        )
    elif ba <= 2:
        friendly.append(f"Data amount looks normal for this kind of connection ({ba}/10).")

    st = int(scores.get("stream_theft_risk", 0))
    if st >= 8:
        unfriendly.append(
            f"Non-browser path that could move video or large streams ({st}/10: {notes.get('stream_theft_risk', '')})."
        )
    elif st <= 1:
        friendly.append("Not using suspicious stream-theft style ports.")

    bp = int(scores.get("beacon_pattern", 0))
    if bp >= 6:
        unfriendly.append(
            f"Repeating check-ins to the same server ({bp}/10: {notes.get('beacon_pattern', '')})."
        )
    elif bp <= 2:
        friendly.append("On-demand egress — no persistent beacon signature.")

    pt = int(scores.get("process_trust", 0))
    if pt >= 8:
        friendly.append(f"Process on consumer whitelist — civilian classification corroborated ({pt}/10).")
    elif pt <= 3:
        unfriendly.append(
            f"Unidentified process or untrusted origin — hostile indicators elevated ({pt}/10)."
        )

    dc = int(scores.get("destination_class", 0))
    cdn_labels = {
        "stream_cdn": "Address is a major CDN (Cloudflare, GitHub, etc.) — everyday web traffic.",
        "search_cdn": "Address is a Google/search CDN — typical when browsing or searching.",
    }
    if ip_class in cdn_labels and dc <= 3:
        friendly.append(cdn_labels[ip_class])
    elif ip_class in ("classified_remote", "hosting", "identified_org") and dc >= 6:
        intel_label = notes.get("intel_label") or rip
        unfriendly.append(f"{intel_label} is not a well-known CDN — classified remote peer ({dc}/10).")
    if rport in HARM_PORTS:
        unfriendly.append(f"Port {rport} is commonly used by malware and remote-control tools.")

    tl = int(scores.get("threat_linked", 0))
    if tl >= 4:
        unfriendly.append(f"Same IP triggered other warnings recently ({notes.get('threat_linked', '')}).")
    elif tl == 0:
        friendly.append("No cross-correlation with other hostile indicators on this station.")

    if int(scores.get("operator_auth", 0)) >= 10:
        friendly.append("Operator authorized this peer — civilian trust locked.")

    actions = {
        "USER_OK": "No action — civilian egress confirmed. Maintain watch.",
        "EPHEMERAL": "No action — transient civilian CDN cycle. Trust peer if strict mode blocks recognized search/social.",
        "SUSPICIOUS": "Hold — identify process. Known launcher/updater: authorize. Unknown: deny permit expansion.",
        "HARM_CANDIDATE": "Interdict — block forever or remove pest. Zero delay on unrecognized hostile process.",
        "MONITOR": "Routine civilian egress — permitted under packet permission v4.0 at zero nft cost.",
    }
    summaries = {
        "USER_OK": "CIVILIAN · AUTHORIZED — operator-initiated browser or media egress.",
        "EPHEMERAL": "CIVILIAN · TRANSIENT — short-lived CDN tab, no hostile axis fired.",
        "SUSPICIOUS": "UNKNOWN · CONTACT — harm/trust divergence; hold for positive ID.",
        "HARM_CANDIDATE": "HOSTILE · CONFIRMED — interdict recommended, zero hesitation.",
        "MONITOR": "CIVILIAN · ROUTINE — no hostile axis; continuous watch only.",
    }
    iff_meta = _iff_resolve(verdict, block_rec)
    if block_rec:
        action = actions["HARM_CANDIDATE"]
        summary = summaries.get(verdict, reason) + f" {iff_meta['enforcement']}"
    else:
        action = actions.get(verdict, "Watch the connection list; click ? on any row for detail.")
        summary = summaries.get(verdict, reason)

    return {
        "summary": summary,
        "action": action,
        "iff": iff_meta["iff"],
        "iff_class": iff_meta["iff_class"],
        "iff_label": iff_meta["iff_label"],
        "enforcement": iff_meta["enforcement"],
        "friendly_signals": friendly[:6],
        "unfriendly_signals": unfriendly[:6],
        "civilian_indicators": friendly[:6],
        "hostile_indicators": unfriendly[:6],
        "trust_meter": min(100, user_total * 5),
        "concern_meter": min(100, harm_total * 4),
        "harm_total": harm_total,
        "trust_total": user_total,
    }


def _queen_sovereign_active() -> bool:
    for key in ("NEXUS_QUEEN_SOVEREIGN", "QUEEN_SOVEREIGN", "NEXUS_FIELD_BROWSER_QUEEN"):
        if os.environ.get(key, "") in ("1", "true", "yes", "on"):
            return True
    return False


def _zero_telemetry_active() -> bool:
    for key in ("NEXUS_ZERO_TELEMETRY", "QUEEN_ZERO_TELEMETRY"):
        v = os.environ.get(key, "")
        if v in ("1", "true", "yes", "on"):
            return True
    return _queen_sovereign_active()


def _settings_override_flag(key: str, *, default: str = "") -> str:
    override = STATE / "settings.override"
    if override.is_file():
        try:
            for line in override.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip()
        except OSError:
            pass
    return os.environ.get(key, default)


def _ai_secure_telemetry_ok(proc: str) -> bool:
    if not _zero_telemetry_active():
        return True
    if _settings_override_flag("NEXUS_AI_SECURE_CHANNEL", default="1") not in ("1", "true", "yes", "on"):
        return False
    if _settings_override_flag("QUEEN_AI_TELEMETRY_OK", default="1") not in ("1", "true", "yes", "on"):
        return False
    pl = (proc or "").lower()
    ai_procs = ("hostess7", "nexus-shield", "nexus-daemon", "field-command", "angel-research")
    if _env_on("QUEEN_GROK_BUILD_SECURE"):
        ai_procs = ai_procs + ("grok", "grok-build", "queen-browser", "field-queen", "fieldfox")
    return any(p in pl for p in ai_procs)


def _env_on(key: str) -> bool:
    return os.environ.get(key, "") in ("1", "true", "yes", "on")


def _grok_max_sockets() -> int:
    raw = os.environ.get("GROK_MAX_SOCKETS", "5").strip()
    try:
        return max(1, min(32, int(raw)))
    except ValueError:
        return 5


def _grok_secure_hosts() -> frozenset[str]:
    return frozenset({
        "x.ai", "api.x.ai", "grok.x.ai", "grok.com", "x.com", "api.x.com",
        "cloudflare.com", "cf.cloudflare.com",
        "127.0.0.1", "localhost",
    })


def _grok_process(proc: str) -> bool:
    return "grok" in (proc or "").lower()


def _grok_secure_channel_match(proc: str, rip: str, intel: dict[str, Any]) -> bool:
    if not _grok_process(proc):
        return False
    if rip in ("127.0.0.1", "::1"):
        return True
    host = str(intel.get("hostname") or intel.get("reverse_dns") or "").lower()
    host = HOST_ALIASES.get(host, host)
    org = str(intel.get("org") or intel.get("asn_name") or "").lower()
    blob = f"{host} {rip or ''} {org}".lower()
    if "cloudflare" in org or "x.ai" in org or "x corp" in org:
        return True
    if rip.startswith(("104.18.", "104.16.", "172.64.", "172.66.", "2606:4700:")):
        return True
    for allowed in _grok_secure_hosts():
        if allowed in blob or host == allowed or host.endswith("." + allowed):
            return True
    return False


def _apply_grok_secure_channel(
    proc: str, rip: str, intel: dict[str, Any], verdict: str, trust_rank: int, reason: str,
) -> tuple[str, int, str]:
    secure_env = _env_on("QUEEN_GROK_BUILD_SECURE") or _env_on("GROK_SECURE_CHANNEL")
    channel_env = _env_on("NEXUS_AI_SECURE_CHANNEL") or _env_on("GROK_SECURE_CHANNEL")
    if not secure_env or not channel_env:
        return verdict, trust_rank, reason
    if not _grok_process(proc) and not _ai_secure_telemetry_ok(proc):
        return verdict, trust_rank, reason
    if _grok_secure_channel_match(proc, rip, intel):
        return (
            "USER_OK",
            TRUST_RANK["USER_OK"],
            "CIVILIAN · Grok secure xAI channel (TLS CA-pinned, no injection)",
        )
    if _grok_process(proc):
        return (
            "SUSPICIOUS",
            TRUST_RANK["SUSPICIOUS"],
            "HOLD — Grok egress outside xAI/Cloudflare allowlist; MITM or injection risk",
        )
    return verdict, trust_rank, reason


def _apply_zero_telemetry(
    proc: str, rip: str, intel: dict[str, Any], verdict: str, trust_rank: int, reason: str,
) -> tuple[str, int, str]:
    if not _zero_telemetry_active() or _ai_secure_telemetry_ok(proc):
        return verdict, trust_rank, reason
    host_blob = " ".join(
        str(intel.get(k) or "")
        for k in ("hostname", "reverse_dns", "org", "label", "asn_name")
    ).lower()
    host_blob = f"{host_blob} {rip or ''}".lower()
    telemetry_markers = (
        "telemetry", "metrics", "google-analytics", "googletagmanager", "crashlytics",
        "sentry.io", "browser-intake", "incoming.telemetry", "data.microsoft.com",
        "firefox.com/phoenix", "ping-centre",
    )
    for marker in telemetry_markers:
        if marker in host_blob:
            return (
                "HARM_CANDIDATE",
                TRUST_RANK["HARM_CANDIDATE"],
                f"IFF HOSTILE — telemetry egress interdicted ({marker}); AI channel requires NEXUS_AI_SECURE_CHANNEL + QUEEN_AI_TELEMETRY_OK",
            )
    return verdict, trust_rank, reason


def _local_capture_grant_active() -> bool:
    state = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
    grant_path = state / "local-capture-grant.json"
    try:
        doc = json.loads(grant_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not doc.get("active") or doc.get("egress_allowed"):
        return False
    exp = doc.get("expires_at") or ""
    try:
        from datetime import datetime, timezone

        if exp and datetime.strptime(exp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            return False
    except ValueError:
        return False
    return bool(doc.get("loopback_only"))


def _apply_queen_sovereign(
    proc: str, verdict: str, trust_rank: int, reason: str,
) -> tuple[str, int, str]:
    if not _queen_sovereign_active():
        return verdict, trust_rank, reason
    pl = (proc or "").lower()
    grant = _local_capture_grant_active()
    obs_markers = ("obs", "obs-studio", "obs-ffmpeg-mux")
    capture_markers = (
        "wf-recorder", "gpu-screen-recorder",
        "simplescreenrecorder", "kooha", "grim", "slurp", "wayshot", "spectacle", "peek",
        "recordmydesktop",
    )
    hook_markers = (
        "wmctrl", "xdotool", "ydotool", "dotool", "xte", "xmacro", "xvkbd",
        "keylogger", "logkeys", "lkl", "xbindkeys", "xhotkey", "autokey", "showkey",
        "evtest", "intercept", "skey", "keysniffer", "pynput", "pykeylogger",
        "evemu-event", "libinput-debug-events", "xev", "vnc", "x11vnc", "teamviewer",
    )
    if grant and any(m in pl for m in obs_markers):
        return "USER_OK", TRUST_RANK.get("USER_OK", 8), "CIVILIAN — operator local OBS grant (loopback only)"
    if any(m in pl for m in obs_markers + capture_markers):
        return "HARM_CANDIDATE", TRUST_RANK["HARM_CANDIDATE"], "IFF HOSTILE — screen capture interdicted (in-engine surface only)"
    if any(m in pl for m in hook_markers):
        return "HARM_CANDIDATE", TRUST_RANK["HARM_CANDIDATE"], "IFF HOSTILE — keyboard middleman interdicted (smart wire)"
    if "ffmpeg" in pl and any(x in pl for x in ("x11grab", "gdigrab", "avfoundation", "dshow")):
        return "HARM_CANDIDATE", TRUST_RANK["HARM_CANDIDATE"], "IFF HOSTILE — display capture path interdicted"
    return verdict, trust_rank, reason


def _verdict(scores: dict[str, int], proc: str, ip_class: str) -> tuple[str, str, bool]:
    harm = (
        scores["stream_theft_risk"] * 2
        + scores["bandwidth_abuse"]
        + scores["destination_class"]
        + scores["threat_linked"]
        - scores["user_browser"]
        - scores["operator_auth"] // 2
        - scores["process_trust"] // 2
    )
    user_ok = (
        scores["user_browser"] >= 7
        and scores["stream_theft_risk"] <= 2
        and scores["bandwidth_abuse"] <= 3
    )
    ephemeral = scores["search_ephemeral"] >= 6 and scores["stream_theft_risk"] <= 3
    media_ok = scores["media_stream"] >= 6 and scores["user_browser"] >= 6
    if _queen_sovereign_active() and os.environ.get("NEXUS_MEDIA_EGRESS_LOCK", "1") not in ("0", "false", "no"):
        if not _local_capture_grant_active():
            media_ok = False

    if scores["operator_auth"] >= 10:
        return "USER_OK", "CIVILIAN — operator-authorized peer", False
    if user_ok and media_ok:
        return "USER_OK", "CIVILIAN — operator-initiated media egress", False
    if user_ok and ephemeral:
        return "EPHEMERAL", "CIVILIAN — transient search/social CDN cycle", False
    if user_ok:
        return "USER_OK", "CIVILIAN — operator-initiated browser egress", False
    if scores["stream_theft_risk"] >= 8:
        return "HARM_CANDIDATE", "HOSTILE — non-browser stream exfiltration signature", True
    if harm >= 14 and scores["process_trust"] <= 4:
        return "HARM_CANDIDATE", "HOSTILE — daemon egress to classified remote with harm axes", True
    if harm >= 10:
        return "SUSPICIOUS", "UNKNOWN — atypical egress, hold for identification", False
    if ephemeral:
        return "EPHEMERAL", "CIVILIAN — short-lived CDN egress", False
    if ip_class in ("stream_cdn", "search_cdn") and scores["process_trust"] >= 5:
        return "USER_OK", "CIVILIAN — known CDN with trusted process", False
    return "MONITOR", "CIVILIAN — routine egress under watch", False


def _touch_module() -> Any:
    import importlib.util

    spec = importlib.util.spec_from_file_location("safe_signal_touch", INSTALL / "lib" / "safe-signal-touch.py")
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _human_touch_policy(
    verdict: str,
    trust_rank: int,
    scores: dict[str, int],
    soul_side: str,
    kill_ok: bool,
    proc: str,
    ip_class: str,
    host: str = "",
) -> dict[str, Any]:
    return _touch_module().connection_touch(
        verdict, trust_rank, scores, soul_side, kill_ok, proc, ip_class,
        host=host, min_accept_trust_rank=MIN_ACCEPT_TRUST_RANK,
    )


def _soul_side(
    verdict: str,
    trust_rank: int,
    scores: dict[str, int],
    kill_ok: bool,
) -> tuple[str, bool]:
    if int(scores.get("operator_auth", 0)) >= 10:
        return "heaven", False
    if trust_rank <= MIN_ACCEPT_TRUST_RANK and verdict in ("USER_OK", "EPHEMERAL", "MONITOR"):
        return "heaven", False
    if kill_ok or verdict == "HARM_CANDIDATE":
        return "hell", True
    if verdict == "SUSPICIOUS" and int(scores.get("process_trust", 0)) <= 3 and kill_ok:
        return "hell", True
    return "limbo", False


def _kill_signal(
    verdict: str,
    block_rec: bool,
    scores: dict[str, int],
    rip: str,
    rport: str,
    proc: str,
    threats: dict[str, list[str]],
    peer_history: dict[str, Any],
    thermal_meta: dict[str, Any] | None = None,
) -> tuple[bool, str, str]:
    """Return kill_eligible, kill_reason, kill_tier (block|eradicate|strike)."""
    thermal = thermal_meta or _field_thermal_meta()
    if thermal.get("rate_limit_active"):
        vecs_hold = [v for v in threats.get(rip, []) if v in KILL_VECTORS]
        if not vecs_hold and verdict != "HARM_CANDIDATE":
            return False, "thermal_rate_limit_hold", "hold"
        if verdict == "HARM_CANDIDATE" and int(scores.get("threat_linked", 0)) < 6:
            return False, "thermal_rate_limit_hold", "hold"
    vecs = [v for v in threats.get(rip, []) if v in KILL_VECTORS]
    if vecs:
        return True, f"threat_vector:{vecs[0]}", "strike"
    if rport in HARM_PORTS and int(scores.get("process_trust", 0)) <= 3:
        tier = "eradicate" if proc not in BROWSER_PROCS else "block"
        return True, f"shell_port:{rport}", tier
    if verdict == "HARM_CANDIDATE" and block_rec:
        if int(scores.get("threat_linked", 0)) >= 6:
            return True, "threat_correlated_harm", "block"
        if int(scores.get("stream_theft_risk", 0)) >= 9:
            return True, "stream_theft_daemon", "eradicate"
        if int(scores.get("beacon_pattern", 0)) >= 7 and proc not in BROWSER_PROCS:
            return True, "persistent_beacon", "eradicate"
        return True, "harm_candidate", "strike"
    if verdict == "SUSPICIOUS" and rport in HARM_PORTS:
        return True, f"suspicious_shell:{rport}", "block"
    seen = int(peer_history.get("seen_count", 0))
    if seen >= 24 and rport in HARM_PORTS and proc not in CONSUMER_PROCS:
        return True, f"beacon_burst:{seen}", "eradicate"
    return False, "", "none"


def _flow_intent(proc: str, verdict: str, reason: str, intel: dict[str, Any], direction_label: str) -> dict[str, str]:
    return {
        "who": proc or "unknown process",
        "purpose": reason,
        "direction": direction_label,
        "org": intel.get("label") or intel.get("org") or "",
        "verdict": verdict,
    }


def _flow_policy(verdict: str, trust_rank: int, rip: str, rport: str, proc: str, direction: str) -> dict[str, Any]:
    flow_key = f"{rip}:{rport}:{proc}"
    if trust_rank <= MIN_ACCEPT_TRUST_RANK:
        return {
            "permit": True,
            "block_scope": "none",
            "block_direction": None,
            "flow_key": flow_key,
            "zero_cost": True,
        }
    if verdict == "SUSPICIOUS":
        block_dir = "in" if direction == "at_us" else "out"
        return {
            "permit": False,
            "block_scope": "segment",
            "block_direction": block_dir,
            "flow_key": flow_key,
            "zero_cost": False,
        }
    if verdict == "HARM_CANDIDATE":
        return {
            "permit": False,
            "block_scope": "ip",
            "block_direction": "both",
            "flow_key": flow_key,
            "zero_cost": False,
        }
    return {
        "permit": True,
        "block_scope": "none",
        "block_direction": None,
        "flow_key": flow_key,
        "zero_cost": True,
    }


def analyze_connections(lines: list[str]) -> dict[str, Any]:
    thermal_meta = _field_thermal_meta()
    trusted = _load_trusted()
    threats = _recent_threat_ips()
    intel_cache = _load_intel_cache()
    history: dict[str, Any] = _load_json(HISTORY, {"ticks": 0, "peers": {}})
    history["ticks"] = int(history.get("ticks", 0)) + 1
    peers: dict[str, Any] = history.get("peers", {})
    current_keys: set[str] = set()
    results: list[dict[str, Any]] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        p = _parse_ss(line)
        state = p["state"]
        if state not in ("ESTAB", "ESTABLISHED", "SYN-SENT", "SYN-RECV"):
            continue
        rip, rport = p["remote_ip"], p["remote_port"]
        if not rip or _is_private_ip(rip):
            continue
        proc = p["proc"]
        direction, direction_label = _connection_direction(state)
        intel = _intel_for_ip(rip, intel_cache)
        ip_class = intel["ip_class"]
        key = f"{rip}:{rport}:{proc}"
        current_keys.add(key)
        peer_hist = peers.get(key, {"seen_count": 0, "first_tick": history["ticks"]})
        peer_hist["seen_count"] = int(peer_hist.get("seen_count", 0)) + 1
        peer_hist["last_tick"] = history["ticks"]
        peer_hist["age_ticks"] = history["ticks"] - int(peer_hist.get("first_tick", history["ticks"]))
        peers[key] = peer_hist

        scores: dict[str, Any] = {}
        notes: dict[str, str] = {}

        s, n = _axis_user_browser(proc)
        scores["user_browser"] = s
        notes["user_browser"] = n

        s, n = _axis_media_stream(proc, rport, ip_class)
        scores["media_stream"] = s
        notes["media_stream"] = n

        s, n = _axis_search_ephemeral(key, peers, ip_class)
        scores["search_ephemeral"] = s
        notes["search_ephemeral"] = n

        s, n = _axis_bandwidth_abuse(proc, ip_class, rport)
        scores["bandwidth_abuse"] = s
        notes["bandwidth_abuse"] = n

        s, n = _axis_stream_theft(proc, rport, p["local"])
        scores["stream_theft_risk"] = s
        notes["stream_theft_risk"] = n

        s, n = _axis_beacon(proc, key, peers)
        scores["beacon_pattern"] = s
        notes["beacon_pattern"] = n

        s, n = _axis_process_trust(proc)
        scores["process_trust"] = s
        notes["process_trust"] = n

        s, n = _axis_destination(ip_class, rport)
        scores["destination_class"] = s
        notes["destination_class"] = n
        notes["intel_label"] = intel.get("label") or rip
        notes["intel_org"] = intel.get("org") or ""

        s, n = _axis_threat_linked(rip, threats)
        scores["threat_linked"] = s
        notes["threat_linked"] = n

        s, n = _axis_auth(rip, trusted)
        scores["operator_auth"] = s
        notes["operator_auth"] = n

        harm_total = sum(
            scores[k] for k in ("stream_theft_risk", "bandwidth_abuse", "destination_class", "threat_linked")
        )
        user_total = sum(scores[k] for k in ("user_browser", "media_stream", "operator_auth", "process_trust"))

        verdict, reason, block_rec = _verdict(scores, proc, ip_class)
        trust_rank_pre = TRUST_RANK.get(verdict, 5)
        verdict, trust_rank_pre, reason = _apply_queen_sovereign(proc, verdict, trust_rank_pre, reason)
        verdict, trust_rank_pre, reason = _apply_zero_telemetry(
            proc, rip, intel, verdict, trust_rank_pre, reason,
        )
        verdict, trust_rank_pre, reason = _apply_grok_secure_channel(
            proc, rip, intel, verdict, trust_rank_pre, reason,
        )
        if verdict == "HARM_CANDIDATE":
            block_rec = True
        suggestion = _build_suggestion(
            scores, notes, verdict, reason, proc, rip, rport, ip_class,
            harm_total, user_total, block_rec,
        )

        trust_rank = TRUST_RANK.get(verdict, 5)
        verdict, trust_rank, honor_meta = _apply_honorability(proc, rip, intel, verdict, trust_rank, scores)
        if honor_meta.get("honor_gold"):
            reason = f"Honorability 5★ — {honor_meta.get('active_site', 'trusted site')} browser session"
        flow_policy = _flow_policy(verdict, trust_rank, rip, rport, proc, direction)
        intent = _flow_intent(proc, verdict, reason, intel, direction_label)
        kill_ok, kill_reason, kill_tier = _kill_signal(
            verdict, block_rec, scores, rip, rport, proc, threats, peer_hist, thermal_meta,
        )
        soul_side, hell_chosen = _soul_side(verdict, trust_rank, scores, kill_ok)
        if hell_chosen:
            if verdict == "HARM_CANDIDATE" or int(scores.get("threat_linked", 0)) >= 6:
                kill_tier = "lethal"
            elif kill_tier == "block":
                kill_tier = "strike"
        site_host = _infer_site_host(rip, intel)
        touch = _human_touch_policy(
            verdict, trust_rank, scores, soul_side, kill_ok, proc, ip_class, host=site_host,
        )
        iff_meta = _iff_resolve(verdict, block_rec)
        results.append({
            "remote_ip": rip,
            "remote_port": rport,
            "process": proc,
            "pid": p.get("pid") or "",
            "state": state,
            "ip_class": ip_class,
            "intel": intel,
            "addr_version": _addr_version(rip),
            "traffic_direction": direction,
            "traffic_direction_label": direction_label,
            "line": line,
            "scores": scores,
            "notes": notes,
            "harm_total": harm_total,
            "user_total": user_total,
            "verdict": verdict,
            "iff": iff_meta["iff"],
            "iff_class": iff_meta["iff_class"],
            "iff_label": iff_meta["iff_label"],
            "enforcement": iff_meta["enforcement"],
            "reason": reason,
            "block_recommended": block_rec,
            "trust_rank": trust_rank,
            "requires_user_trust": trust_rank > MIN_ACCEPT_TRUST_RANK,
            "direction": "out",
            "suggestion": suggestion,
            "intent": intent,
            "flow_policy": flow_policy,
            "kill_eligible": kill_ok,
            "kill_reason": kill_reason,
            "kill_tier": kill_tier,
            "soul_side": soul_side,
            "hell_chosen": hell_chosen,
            **touch,
            **honor_meta,
        })

    # decay history
    stale = [k for k in peers if k not in current_keys]
    for k in stale:
        peers[k]["miss_ticks"] = int(peers[k].get("miss_ticks", 0)) + 1
        if peers[k]["miss_ticks"] > 30:
            del peers[k]
    for k in current_keys:
        if k in peers:
            peers[k]["miss_ticks"] = 0

    history["peers"] = peers
    history["updated"] = _now()
    _save_json(HISTORY, history)

    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "hostility_priority", INSTALL / "lib" / "hostility-priority.py",
        )
        hp = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(hp)
        for row in results:
            hp.enrich_connection(row)
        results = hp.sort_hell_first(results)
    except Exception:
        results.sort(
            key=lambda x: (
                x.get("trust_rank", 5),
                -(x.get("suggestion") or {}).get("trust_meter", 0),
                int(x.get("block_recommended", False)),
                -x.get("harm_total", 0),
            )
        )
    harm_candidates = [r for r in results if r["block_recommended"]]
    kill_targets = [r for r in results if r.get("kill_eligible")]
    hell_chosen = [r for r in results if r.get("hell_chosen")]
    heaven_flows = [r for r in results if r.get("soul_side") == "heaven"]
    packet_permission = (
        os.environ.get("NEXUS_PACKET_PERMISSION", "") == "1"
        or os.environ.get("NEXUS_GATEKEEPER_STRICT_TRUST", "1") == "1"
    )
    strict_trust = packet_permission
    pending_trust = [r for r in results if r.get("requires_user_trust")]
    permitted = [r for r in results if (r.get("flow_policy") or {}).get("permit")]
    segment_blocks = [r for r in results if (r.get("flow_policy") or {}).get("block_scope") == "segment"]
    if packet_permission:
        why_no_auto_block = (
            "Packet permission v4.0: DPI + gatekeeper know who and intent on every flow. "
            f"Good traffic ({len(permitted)} flow(s)) passes at zero nft cost. "
            "Only harmful sections get segment blocks; harm candidates get IP blocks."
        )
    else:
        why_no_auto_block = (
            "Advisory mode: NEXUS classifies all traffic but does not auto-block segments. "
            "Turn on Packet permission to block harmful sections only."
        )
    return {
        "updated": _now(),
        "field_thermal": thermal_meta,
        "touch_policy": _touch_module().aggregate_counts(results),
        "connection_count": len(results),
        "harm_candidates": len(harm_candidates),
        "kill_targets": len(kill_targets),
        "hell_chosen_count": len(hell_chosen),
        "hostility_priority": "hell_first",
        "peak_hostility_score": max((int(r.get("hostility_score") or 0) for r in results), default=0),
        "heaven_flow_count": len(heaven_flows),
        "heaven_hell_motto": _heaven_hell_motto(),
        "know_doctrine": _know_doctrine(),
        "pending_trust_count": len(pending_trust),
        "permitted_flow_count": len(permitted),
        "segment_block_count": len(segment_blocks),
        "strict_trust": strict_trust,
        "packet_permission": packet_permission,
        "min_accept_trust_rank": MIN_ACCEPT_TRUST_RANK,
        "why_no_auto_block": why_no_auto_block,
        "connections": results[:60],
    }


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--stdin":
        lines = sys.stdin.read().splitlines()
    else:
        import subprocess
        proc = subprocess.run(
            ["ss", "-H", "-tunap"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        lines = proc.stdout.splitlines()

    out = analyze_connections(lines)
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())