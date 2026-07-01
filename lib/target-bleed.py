#!/usr/bin/env pythong
"""NEXUS Target Bleed — host-to-hostile quick intel extraction.

End-to-end chain: our OS/process → live socket → target PTR/TTL/OS/service bleed.
Fast hits only (sub-second to few seconds). Cached. Skips friendlies.
"""
from __future__ import annotations

import json
import os
import platform
import re
import shutil
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
CACHE_PATH = STATE / "target-bleed-cache.json"
BLEED_TTL = 1800
PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.|::1|fe80:|fd)"
)
HTTP_PORTS = frozenset({80, 8080, 8000, 8888})
TLS_PORTS = frozenset({443, 8443, 4443})
BANNER_PORTS = frozenset({21, 22, 25, 110, 143, 445, 3389, 5900})


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


def host_endpoint_context() -> dict[str, Any]:
    uname = platform.uname()
    return {
        "hostname": socket.gethostname(),
        "os": uname.system,
        "os_release": uname.release,
        "kernel": uname.version.split(" #", 1)[0][:120],
        "arch": uname.machine,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "nexus_version": _nexus_version(),
        "bleed_host": True,
    }


def _parse_ss_peer(line: str) -> dict[str, str]:
    parts = line.split()
    proto = parts[0] if parts else ""
    state = parts[1] if len(parts) > 1 else ""
    local = parts[4] if len(parts) > 4 else ""
    remote = parts[5] if len(parts) > 5 else ""

    def split_addr(raw: str) -> tuple[str, str]:
        if not raw or raw in ("*:*", "[*]:*"):
            return "", ""
        raw = raw.strip()
        if raw.startswith("["):
            m = re.match(r"\[([^\]]+)\]:(\d+)", raw)
            return (m.group(1), m.group(2)) if m else (raw, "")
        if raw.count(":") > 1:
            idx = raw.rfind(":")
            return raw[:idx], raw[idx + 1 :]
        if ":" in raw:
            h, p = raw.rsplit(":", 1)
            return h, p
        return raw, ""

    lip, lport = split_addr(local)
    rip, rport = split_addr(remote)
    proc, pid = "", ""
    m = re.search(r'users:\(\("([^"]+)"[^)]*pid=(\d+)', line)
    if m:
        proc, pid = m.group(1), m.group(2)
    return {
        "proto": proto,
        "state": state,
        "local_ip": lip,
        "local_port": lport,
        "remote_ip": rip,
        "remote_port": rport,
        "process": proc,
        "pid": pid,
    }


def live_connections_for_ip(ip: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    try:
        proc = subprocess.run(
            ["ss", "-H", "-tunap"],
            capture_output=True,
            text=True,
            timeout=8,
        )
    except (OSError, subprocess.SubprocessError):
        return rows
    for line in proc.stdout.splitlines():
        peer = _parse_ss_peer(line)
        if peer.get("remote_ip") == ip or peer.get("local_ip") == ip:
            rows.append(peer)
    return rows[:12]


def reverse_dns(ip: str, timeout: float = 2.5) -> dict[str, Any]:
    old = socket.getdefaulttimeout()
    try:
        socket.setdefaulttimeout(timeout)
        host, aliases, _ = socket.gethostbyaddr(ip)
        return {
            "ok": True,
            "hostname": host,
            "aliases": aliases[:6],
            "standard": "PTR",
        }
    except (socket.herror, socket.gaierror, OSError) as exc:
        return {"ok": False, "error": str(exc), "standard": "PTR"}
    finally:
        socket.setdefaulttimeout(old)


def ttl_os_guess(ip: str) -> dict[str, Any]:
    if PRIVATE_RE.match(ip):
        return {"ok": False, "skipped": "private"}
    try:
        proc = subprocess.run(
            ["ping", "-c", "1", "-W", "1", ip],
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc)}
    m = re.search(r"ttl=(\d+)", proc.stdout.lower())
    if not m:
        return {"ok": False, "error": "no_ttl"}
    ttl = int(m.group(1))
    if ttl <= 64:
        guess, family = "Linux/BSD/macOS", "unix"
    elif ttl <= 128:
        guess, family = "Windows", "windows"
    elif ttl <= 255:
        guess, family = "Network appliance / Cisco", "network"
    else:
        guess, family = "Unknown", "unknown"
    return {
        "ok": True,
        "ttl": ttl,
        "os_guess": guess,
        "os_family": family,
        "standard": "TTL-OS",
    }


def quick_http_bleed(ip: str, port: int, timeout: float = 2.0) -> dict[str, Any]:
    scheme = "https" if port in TLS_PORTS else "http"
    url = f"{scheme}://{ip}:{port}/"
    try:
        req = urllib.request.Request(
            url,
            method="HEAD",
            headers={"User-Agent": "NEXUS-Shield/3.2 target-bleed", "Connection": "close"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            headers = {k: v for k, v in resp.headers.items()}
            return {
                "ok": True,
                "port": port,
                "status": resp.status,
                "server": headers.get("Server", ""),
                "powered_by": headers.get("X-Powered-By", ""),
                "via": headers.get("Via", ""),
                "content_type": headers.get("Content-Type", ""),
                "standard": "HTTP-HEAD",
            }
    except urllib.error.HTTPError as exc:
        return {
            "ok": True,
            "port": port,
            "status": exc.code,
            "server": exc.headers.get("Server", "") if exc.headers else "",
            "standard": "HTTP-HEAD",
        }
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"ok": False, "port": port, "error": str(exc), "standard": "HTTP-HEAD"}


def quick_tls_bleed(ip: str, port: int = 443, timeout: float = 3.0) -> dict[str, Any]:
    if not shutil.which("openssl"):
        return {"ok": False, "skipped": "no_openssl"}
    try:
        proc = subprocess.run(
            [
                "openssl", "s_client",
                "-connect", f"{ip}:{port}",
                "-servername", ip,
                "-brief",
            ],
            input="",
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc), "standard": "TLS-SNI"}
    subject = re.search(r"subject=([^\n]+)", text)
    issuer = re.search(r"issuer=([^\n]+)", text)
    proto = re.search(r"Protocol\s*:\s*([^\n]+)", text)
    cipher = re.search(r"Cipher\s*:\s*([^\n]+)", text)
    if not subject and proc.returncode != 0:
        return {"ok": False, "error": "handshake_failed", "standard": "TLS-SNI"}
    return {
        "ok": True,
        "port": port,
        "subject": subject.group(1).strip() if subject else "",
        "issuer": issuer.group(1).strip() if issuer else "",
        "protocol": proto.group(1).strip() if proto else "",
        "cipher": cipher.group(1).strip() if cipher else "",
        "standard": "TLS-SNI",
    }


def quick_banner(ip: str, port: int, timeout: float = 1.2) -> dict[str, Any]:
    try:
        with socket.create_connection((ip, port), timeout=timeout) as sock:
            sock.settimeout(timeout)
            try:
                chunk = sock.recv(512)
            except socket.timeout:
                chunk = b""
            banner = chunk.decode("utf-8", errors="replace").strip()[:300]
            return {"ok": True, "port": port, "banner": banner, "standard": "TCP-BANNER"}
    except OSError as exc:
        return {"ok": False, "port": port, "error": str(exc), "standard": "TCP-BANNER"}


def nmap_quick_os(ip: str, port: int) -> dict[str, Any]:
    if not shutil.which("nmap"):
        return {"ok": False, "skipped": "no_nmap"}
    try:
        proc = subprocess.run(
            [
                "nmap", "-Pn", "-O", "--osscan-limit",
                "-p", str(port),
                "--max-retries", "1",
                "-T4",
                "--host-timeout", "5s",
                ip,
            ],
            capture_output=True,
            text=True,
            timeout=8,
        )
        text = proc.stdout or ""
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "error": str(exc), "standard": "NMAP-OS"}
    os_lines = [
        ln.strip() for ln in text.splitlines()
        if "OS details" in ln or "Running:" in ln or "Aggressive OS" in ln
    ]
    svc_m = re.search(r"(\d+)/tcp\s+open\s+(\S+)(?:\s+(.+))?", text)
    return {
        "ok": bool(os_lines or svc_m),
        "os_lines": os_lines[:4],
        "service": svc_m.group(2) if svc_m else "",
        "service_detail": (svc_m.group(3) or "").strip() if svc_m else "",
        "standard": "NMAP-OS",
    }


def bleed_target(
    ip: str,
    *,
    conn_hint: dict[str, Any] | None = None,
    online: bool = True,
    cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full host→target bleed for one hostile IP."""
    t0 = time.monotonic()
    if not ip or PRIVATE_RE.match(ip):
        return {"ok": False, "ip": ip, "skipped": "private"}

    cache = cache if cache is not None else _load_json(CACHE_PATH, {"ips": {}})
    now = time.time()
    cached = (cache.get("ips") or {}).get(ip)
    if cached and (now - float(cached.get("_ts", 0))) < BLEED_TTL:
        return cached

    host = host_endpoint_context()
    connections = live_connections_for_ip(ip)
    if conn_hint:
        hint_row = {
            "proto": "hint",
            "state": str(conn_hint.get("state") or ""),
            "local_ip": "",
            "local_port": str(conn_hint.get("local_port") or ""),
            "remote_ip": ip,
            "remote_port": str(conn_hint.get("remote_port") or ""),
            "process": str(conn_hint.get("process") or ""),
            "pid": str(conn_hint.get("pid") or ""),
        }
        if hint_row["remote_port"] or hint_row["process"]:
            connections.insert(0, hint_row)

    ports_seen: set[int] = set()
    for c in connections:
        for key in ("remote_port", "local_port"):
            val = c.get(key) or ""
            if str(val).isdigit():
                ports_seen.add(int(val))

    primary_proc = ""
    primary_port = 0
    for c in connections:
        if c.get("process"):
            primary_proc = c["process"]
        if c.get("remote_port", "").isdigit():
            primary_port = int(c["remote_port"])
            break

    target: dict[str, Any] = {
        "reverse_dns": reverse_dns(ip) if online else {"ok": False, "skipped": "offline"},
        "ttl_os": ttl_os_guess(ip) if online else {"ok": False, "skipped": "offline"},
        "ports_seen": sorted(ports_seen)[:8],
        "http": {},
        "tls": {},
        "banner": {},
        "nmap": {},
    }

    standards: list[str] = ["HOST-SS-LINK"]
    ptr = target["reverse_dns"]
    if ptr.get("ok"):
        standards.append("PTR")
        target["ptr_hostname"] = ptr.get("hostname", "")
    ttl = target["ttl_os"]
    if ttl.get("ok"):
        standards.append("TTL-OS")
        target["os_guess"] = ttl.get("os_guess", "")
        target["os_family"] = ttl.get("os_family", "")

    probe_port = primary_port or (443 if 443 in ports_seen else (80 if 80 in ports_seen else 0))

    if online and probe_port:
        if probe_port in TLS_PORTS or probe_port in HTTP_PORTS:
            target["tls"] = quick_tls_bleed(ip, probe_port if probe_port in TLS_PORTS else 443)
            if target["tls"].get("ok"):
                standards.append("TLS-SNI")
            if probe_port in HTTP_PORTS or not target["tls"].get("ok"):
                target["http"] = quick_http_bleed(ip, probe_port if probe_port in HTTP_PORTS else 80)
                if target["http"].get("ok"):
                    standards.append("HTTP-HEAD")
        if probe_port in BANNER_PORTS:
            target["banner"] = quick_banner(ip, probe_port)
            if target["banner"].get("ok"):
                standards.append("TCP-BANNER")
        target["nmap"] = nmap_quick_os(ip, probe_port)
        if target["nmap"].get("ok"):
            standards.append("NMAP-OS")
            if target["nmap"].get("os_lines") and not target.get("os_guess"):
                target["os_guess"] = target["nmap"]["os_lines"][0][:120]

    bleed_ms = int((time.monotonic() - t0) * 1000)
    out: dict[str, Any] = {
        "ok": True,
        "ip": ip,
        "updated": _now(),
        "bleed_ms": bleed_ms,
        "host": host,
        "link": {
            "connections": connections,
            "our_process": primary_proc,
            "primary_port": primary_port,
            "ports_seen": sorted(ports_seen),
        },
        "target": target,
        "target_os": target.get("os_guess") or ttl.get("os_guess", ""),
        "ptr_hostname": target.get("ptr_hostname", ""),
        "standards": standards,
        "_ts": now,
    }
    cache.setdefault("ips", {})[ip] = out
    _save_json(CACHE_PATH, cache)
    return out


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: target-bleed.py bleed <ip>", file=sys.stderr)
        return 1
    if sys.argv[1] == "bleed":
        json.dump(bleed_target(sys.argv[2], online=True), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())