#!/usr/bin/env pythong
"""Sovereign Truth DNS resolution — loopback @127.0.0.1 primary, dig+trace fallback."""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
TRUTH_HOST = os.environ.get("NEXUS_FIELD_DNS_IPV4", "127.0.0.1")
TRUTH_PORT = int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53"))
STUB_WITNESS = os.environ.get("NEXUS_FIELD_DNS_STUB_WITNESS", "127.0.0.53")


def _looks_ipv4(s: str) -> bool:
    try:
        ipaddress.IPv4Address(str(s).split()[0])
        return True
    except ValueError:
        return False


def _parse_dig_answer(stdout: str, qtype: str = "A") -> list[str]:
    out: list[str] = []
    for line in (stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[3] == qtype and _looks_ipv4(parts[4]):
            ip = parts[4].split()[0]
            if ip not in out:
                out.append(ip)
    return out[:24]


def _dig(
    host: str,
    *,
    server: str | None = None,
    qtype: str = "A",
    trace: bool = False,
    timeout: float = 6.0,
) -> list[str]:
    cmd: list[str]
    if trace:
        cmd = ["dig", "+trace", f"+time={int(timeout)}", "+tries=1", "+noall", "+answer", host, qtype]
    elif server:
        cmd = ["dig", f"@{server}", f"+time={int(timeout)}", "+tries=1", "+noall", "+answer", host, qtype]
    else:
        cmd = ["dig", f"+time={int(timeout)}", "+tries=1", "+noall", "+answer", host, qtype]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 4, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0 and not (proc.stdout or "").strip():
        return []
    return _parse_dig_answer(proc.stdout or "", qtype)


def truth_resolver_up(*, probe_host: str = "github.com") -> bool:
    if os.environ.get("NEXUS_FIELD_DNS_TRUTH_SKIP_PROBE", "").strip().lower() in ("1", "yes", "on"):
        return True
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.2)
        sock.connect((TRUTH_HOST, TRUTH_PORT))
        sock.close()
    except OSError:
        return False
    ips = _dig(probe_host, server=TRUTH_HOST, timeout=3.0)
    return bool(ips)


def resolve_a(host: str) -> dict[str, Any]:
    """Resolve A records via Truth DNS first; dig+trace fallback; stub witness last."""
    truth_up = truth_resolver_up(probe_host=host)
    truth_ips: list[str] = []
    if truth_up:
        truth_ips = _dig(host, server=TRUTH_HOST)
    trace_ips: list[str] = []
    if not truth_ips:
        trace_ips = _dig(host, trace=True, timeout=10.0)
    stub_ips: list[str] = []
    if STUB_WITNESS and STUB_WITNESS != TRUTH_HOST:
        stub_ips = _dig(host, server=STUB_WITNESS, timeout=3.0)
    system_ips: list[str] = []
    try:
        for info in socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM):
            ip = info[4][0]
            if ip not in system_ips:
                system_ips.append(ip)
    except OSError:
        pass

    if truth_ips:
        source = "truth_dns"
        ips = truth_ips
    elif trace_ips:
        source = "dig_trace"
        ips = trace_ips
    elif stub_ips:
        source = "stub_witness"
        ips = stub_ips
    elif system_ips:
        source = "system"
        ips = system_ips
    else:
        source = "none"
        ips = []

    return {
        "host": host,
        "ips": ips,
        "source": source,
        "ok": bool(ips),
        "truth_up": truth_up,
        "truth": truth_ips,
        "trace": trace_ips,
        "stub": stub_ips,
        "system": system_ips,
        "resolver": f"{TRUTH_HOST}:{TRUTH_PORT}",
    }


def resolve_a_list(host: str) -> list[str]:
    return list(resolve_a(host).get("ips") or [])


def _recover_hung_dns() -> dict[str, Any] | None:
    if os.environ.get("NEXUS_DNS_FIX_ACTIVE", "").strip() == "1":
        return None
    fix_py = INSTALL / "lib" / "field-dns-dhcp-fix.py"
    if not fix_py.is_file():
        return None
    py = os.environ.get("PYTHON", "python3")
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    try:
        proc = subprocess.run(
            [py, str(fix_py), "dns"],
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
            env=env,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        pass
    return None


def ensure_truth_dns() -> dict[str, Any]:
    """Publish Truth DNS panels and start serve loop if resolver is down."""
    applied: list[str] = []
    dns_py = INSTALL / "lib" / "field-dns.py"
    takeover_py = INSTALL / "lib" / "dns-service-takeover.py"
    py = os.environ.get("PYTHON", "python3")
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}

    if not truth_resolver_up():
        recovered = _recover_hung_dns()
        if recovered:
            applied.append("field-dns-dhcp-fix.dns")
            if recovered.get("healthy"):
                return {
                    "schema": "field-dns-resolve/v1",
                    "truth_up": True,
                    "resolver": f"{TRUTH_HOST}:{TRUTH_PORT}",
                    "applied": applied,
                    "ok": True,
                    "recovered": recovered,
                }

    if dns_py.is_file():
        try:
            subprocess.run([py, str(dns_py), "build"], capture_output=True, timeout=30, check=False, env=env)
            applied.append("field-dns.build")
        except (OSError, subprocess.TimeoutExpired):
            pass
    if takeover_py.is_file():
        try:
            subprocess.run([py, str(takeover_py), "evaluate"], capture_output=True, timeout=20, check=False, env=env)
            applied.append("dns-service-takeover.evaluate")
        except (OSError, subprocess.TimeoutExpired):
            pass

    if not truth_resolver_up():
        serve_log = STATE / "field-dns-serve.log"
        serve_log.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(
                [py, str(dns_py), "serve"],
                stdout=serve_log.open("a", encoding="utf-8"),
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
            applied.append("field-dns.serve")
            for _ in range(12):
                time.sleep(0.5)
                if truth_resolver_up():
                    break
        except OSError:
            pass

    up = truth_resolver_up()
    return {
        "schema": "field-dns-resolve/v1",
        "truth_up": up,
        "resolver": f"{TRUTH_HOST}:{TRUTH_PORT}",
        "applied": applied,
        "ok": up,
    }


def status() -> dict[str, Any]:
    up = truth_resolver_up()
    probe = resolve_a("github.com") if up else {"host": "github.com", "ips": [], "source": "none", "ok": False}
    return {
        "schema": "field-dns-resolve/v1",
        "truth_up": up,
        "resolver": f"{TRUTH_HOST}:{TRUTH_PORT}",
        "stub_witness": STUB_WITNESS,
        "probe": probe,
    }


def main() -> int:
    import sys

    args = sys.argv[1:]
    if not args:
        print(json.dumps({"usage": "field-dns-resolve.py [resolve|ensure|status] [host]"}, ensure_ascii=False))
        return 1
    cmd = args[0]
    if cmd == "resolve":
        host = args[1] if len(args) > 1 else "github.com"
        print(json.dumps(resolve_a(host), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ensure":
        print(json.dumps(ensure_truth_dns(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-dns-resolve.py [resolve|ensure|status] [host]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())