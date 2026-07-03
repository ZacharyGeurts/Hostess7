#!/usr/bin/env pythong
"""GitHub path harden — presume MITM/hostile ISP; DNS cross-check, flap detect, tunnel-first."""
from __future__ import annotations

import ipaddress
import json
import os
import socket
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-github-path-harden-doctrine.json"
KNOWN = INSTALL / "Hostess7/data/github-known-hosts.json"
PANEL = STATE / "field-github-path-harden-panel.json"
ENV_FILE = Path.home() / ".config" / "ammo-shield" / "github-lane.env"


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _violation(msg: str) -> None:
    log_py = INSTALL / "lib" / "field-central-log.py"
    if not log_py.is_file():
        return
    try:
        subprocess.run(
            [os.environ.get("PYTHON", "python3"), str(log_py), "append", "warn", "github-path", msg],
            capture_output=True,
            timeout=8,
            check=False,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
    except (OSError, subprocess.TimeoutExpired):
        pass
    ammo_log = STATE / ".." / ".ammo-state-ci"
    violations = Path(os.environ.get("AMMO_STATE_DIR", str(STATE.parent / ".ammo-state-ci")))
    try:
        violations.mkdir(parents=True, exist_ok=True)
        with (violations / "violations.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{_utc()} VIOLATION {msg}\n")
    except OSError:
        pass


def _system_ips(host: str) -> list[str]:
    ips: list[str] = []
    try:
        for info in socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM):
            ip = info[4][0]
            if ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


def _doh_ips(host: str, url_tpl: str) -> list[str]:
    url = url_tpl.format(host=host)
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/dns-json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            doc = json.loads(resp.read().decode("utf-8"))
        out: list[str] = []
        for ans in doc.get("Answer") or doc.get("answers") or []:
            if isinstance(ans, dict):
                data = ans.get("data") or ans.get("Data")
                if data and _looks_ipv4(str(data)):
                    out.append(str(data).split()[0])
        return out
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        return []


def _looks_ipv4(s: str) -> bool:
    try:
        ipaddress.IPv4Address(s.split()[0])
        return True
    except ValueError:
        return False


def _ip_in_cidrs(ip: str, cidrs: list[str]) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


def _tcp_once(host: str, port: int, timeout: float, *, bind_ip: str | None = None) -> dict[str, Any]:
    t0 = time.monotonic()
    try:
        infos = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
    except OSError as exc:
        return {"ok": False, "error": str(exc), "ms": 0}
    last_err = ""
    for _, _, _, _, sockaddr in infos:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            if bind_ip:
                sock.bind((bind_ip, 0))
            sock.connect(sockaddr)
            sock.close()
            ms = round((time.monotonic() - t0) * 1000, 1)
            return {"ok": True, "ip": sockaddr[0], "ms": ms}
        except OSError as exc:
            last_err = str(exc)
            continue
    return {"ok": False, "error": last_err or "connect failed", "ms": round((time.monotonic() - t0) * 1000, 1)}


def _flap_probe(host: str, port: int, *, rounds: int = 3, interval: float = 1.5, timeout: float = 6.0) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for _ in range(max(1, rounds)):
        hits.append(_tcp_once(host, port, timeout))
        time.sleep(interval)
    oks = [h for h in hits if h.get("ok")]
    return {
        "host": host,
        "port": port,
        "rounds": rounds,
        "ok_count": len(oks),
        "flapping": 0 < len(oks) < rounds,
        "all_down": len(oks) == 0,
        "all_up": len(oks) == rounds,
        "hits": hits,
    }


def _tls_github(host: str = "api.github.com") -> dict[str, Any]:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert() or {}
        subj = dict(x[0] for x in cert.get("subject", ()))
        issuer = dict(x[0] for x in cert.get("issuer", ()))
        cn = subj.get("commonName", "")
        org = issuer.get("organizationName", "")
        ok = "github" in cn.lower() or "github" in org.lower() or "DigiCert" in org
        return {"ok": ok, "cn": cn, "issuer_org": org}
    except OSError as exc:
        return {"ok": False, "error": str(exc)[:160]}


def dns_crosscheck(doc: dict[str, Any]) -> dict[str, Any]:
    cfg = doc.get("dns_crosscheck") or {}
    hosts = cfg.get("hosts") or ["github.com", "api.github.com", "ssh.github.com"]
    known = _load(KNOWN, {})
    cidrs = (known.get("dns_allow") or {}).get("git_cidrs") or []
    pinned = doc.get("pinned_connect_ips") or {}
    rows: list[dict[str, Any]] = []
    suspect = False
    for host in hosts:
        sys_ips = _system_ips(host)
        doh_sets: dict[str, list[str]] = {}
        for spec in cfg.get("doh") or []:
            doh_sets[str(spec.get("id"))] = _doh_ips(host, str(spec.get("url")))
        pin = list(pinned.get(host) or [])
        bad_sys = [ip for ip in sys_ips if cidrs and not _ip_in_cidrs(ip, cidrs)]
        all_doh = {ip for ips in doh_sets.values() for ip in ips}
        bad_doh = [ip for ip in all_doh if cidrs and not _ip_in_cidrs(ip, cidrs)]
        mismatch = False
        if bad_sys or bad_doh:
            mismatch = True
            suspect = True
            _violation(f"DNS outside git CIDR {host}: system_bad={bad_sys} doh_bad={bad_doh}")
        elif all_doh and sys_ips and not (set(sys_ips) & all_doh):
            # GitHub rotates A records — warn only unless flap/TLS also bad
            mismatch = True
            _violation(f"DNS pool drift {host}: system={sys_ips} doh={sorted(all_doh)} (same CIDR — monitor)")
        rows.append({
            "host": host,
            "system": sys_ips,
            "doh": doh_sets,
            "pinned": pin,
            "bad_system": bad_sys,
            "mismatch": mismatch,
        })
    return {"ok": not suspect, "suspect": suspect, "hosts": rows}


def path_audit(*, apply: bool = False) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    flap_cfg = doc.get("flap_probe") or {}
    rounds = int(flap_cfg.get("rounds") or 3)
    interval = float(flap_cfg.get("interval_sec") or 1.5)
    timeout = float(flap_cfg.get("timeout_sec") or 6)

    dns = dns_crosscheck(doc)
    flaps = [
        _flap_probe("github.com", 22, rounds=rounds, interval=interval, timeout=timeout),
        _flap_probe("ssh.github.com", 443, rounds=rounds, interval=interval, timeout=timeout),
        _flap_probe("api.github.com", 443, rounds=rounds, interval=interval, timeout=timeout),
    ]
    tls = _tls_github()
    any_flap = any(f.get("flapping") for f in flaps)
    direct_down_tunnel_up = (
        flaps[0].get("all_down") and flaps[1].get("ok_count", 0) > 0
    ) or (
        flaps[0].get("flapping") and flaps[1].get("ok_count", 0) >= flaps[0].get("ok_count", 0)
    )

    verdict = "OK"
    if dns.get("suspect"):
        verdict = "MITM_DNS_SUSPECT"
    elif any_flap:
        verdict = "ISP_FLAP_SUSPECT"
    elif direct_down_tunnel_up:
        verdict = "ISP_PORT22_FILTER"
    elif not tls.get("ok"):
        verdict = "TLS_SUSPECT"
    elif dns.get("hosts") and any(h.get("mismatch") for h in dns["hosts"]):
        verdict = "DNS_POOL_DRIFT"

    mitigations = list(doc.get("mitigations") or {})
    applied: list[str] = []
    if apply and verdict not in ("OK", "DNS_POOL_DRIFT"):
        if doc.get("mitigations", {}).get("force_tunnel"):
            ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
            ENV_FILE.write_text(
                "# Hostess7 github lane — auto-applied hostile path mitigations\n"
                "export HOSTESS7_GIT_TUNNEL=tunnel\n"
                "export HOSTESS7_GIT_SKIP_API_TLS=1\n"
                "export HOSTESS7_PRESUME_HOSTILE=1\n"
                "export GIT_SSH_VARIANT=tunnel443\n",
                encoding="utf-8",
            )
            applied.extend(["github-lane.env", "HOSTESS7_GIT_TUNNEL=tunnel"])
        _violation(f"path audit verdict={verdict} applied={applied}")

    out = {
        "schema": "field-github-path-harden/v1",
        "ts": _utc(),
        "ok": verdict == "OK",
        "verdict": verdict,
        "presume_mitm": bool(doc.get("presume_mitm", True)),
        "dns": dns,
        "flaps": flaps,
        "tls": tls,
        "recommended_route": "tunnel" if verdict != "OK" or doc.get("default_route") == "tunnel" else "direct",
        "applied": applied,
        "env_file": str(ENV_FILE),
        "operator": {
            "probe": "./scripts/github-lanes.sh probe",
            "push": "HOSTESS7_GIT_TUNNEL=tunnel ./scripts/github-lanes.sh push main",
            "audit": "./scripts/github-unflake.sh audit --apply",
        },
    }
    _save(PANEL, out)
    return out


def main() -> int:
    import sys

    args = sys.argv[1:]
    apply = "--apply" in args
    cmd = next((a for a in args if not a.startswith("-")), "audit")
    if cmd in ("audit", "json", "panel", "status"):
        print(json.dumps(path_audit(apply=apply), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-github-path-harden.py [audit|panel] [--apply]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())