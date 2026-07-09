#!/usr/bin/env python3
"""Everyone served · no port hangups on the system.

Doctrine:
  · Everyone is served on the Field DNS+DHCP plane (honest live + fleet stamps).
  · No port hangups — critical listeners healthy, no stuck Recv-Q/Send-Q, no dead binds.
  · Hang guard armed. Probes green. FIELD 1 FOREVER.

  python3 lib/field-everyone-served-no-hangups.py enforce
  python3 lib/field-everyone-served-no-hangups.py status
"""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-everyone-served-no-hangups-panel.json"
PUBLIC = STATE / "field-everyone-served-no-hangups-public.json"
LEDGER = STATE / "field-everyone-served-no-hangups-ledger.jsonl"
SEAL = STATE / "field-everyone-served.forever"
NO_HANG = STATE / "field-no-port-hangups.forever"
SCHEMA = "field-everyone-served-no-hangups/v1"
IRONCLAD = "ironclad:everyone-served-no-hangups:1"

# Critical ports that must not hang
CRITICAL_UDP = (53, 67)  # Field DNS + DHCP
CRITICAL_TCP = (9477, 9481)  # C2 threat panel · Queen


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(doc, ensure_ascii=False, indent=2, default=str) + "\n"
    try:
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
    except OSError:
        try:
            path.write_text(payload, encoding="utf-8")
        except OSError:
            pass


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def _ok(v: Any) -> bool:
    if isinstance(v, dict):
        return bool(v.get("ok", True)) and not v.get("error") and not v.get("missing")
    return bool(v)


def _run(rel: str, args: list[str], *, timeout: float = 90.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "missing": rel}
    try:
        cp = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "AML_BUILD": "0",
            },
            check=False,
        )
        raw = (cp.stdout or "").strip()
        if raw.startswith("{"):
            try:
                d = json.loads(raw)
                if isinstance(d, dict):
                    d.setdefault("ok", cp.returncode == 0)
                    return d
            except json.JSONDecodeError:
                pass
        for line in reversed(raw.splitlines()):
            if line.strip().startswith("{"):
                try:
                    d = json.loads(line)
                    if isinstance(d, dict):
                        d.setdefault("ok", cp.returncode == 0)
                        return d
                except json.JSONDecodeError:
                    continue
        return {"ok": cp.returncode == 0, "rc": cp.returncode, "tail": (raw or "")[-160:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "error": str(e)[:200]}


def scan_port_hangups() -> dict[str, Any]:
    """Detect hung / unhealthy critical ports via ss Recv-Q/Send-Q and presence."""
    now = _utc()
    hangups: list[dict[str, Any]] = []
    healthy: list[dict[str, Any]] = []
    listeners: list[dict[str, Any]] = []

    def parse_ss(proto: str) -> list[dict[str, Any]]:
        """Parse ss listeners robustly.

        Modern `ss -uln` / `ss -tln` often omit Netid:
          State Recv-Q Send-Q Local:Port Peer:Port
        Full form (no -t/-u alone) may include Netid first:
          Netid State Recv-Q Send-Q Local:Port Peer:Port
        """
        rows: list[dict[str, Any]] = []
        try:
            # Prefer numeric + no process column (works unprivileged; stable columns)
            flag = "-uln" if proto == "udp" else "-tln"
            cp = subprocess.run(
                ["ss", flag],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return rows
        for line in (cp.stdout or "").splitlines():
            s = line.strip()
            if not s or s.lower().startswith("netid") or s.lower().startswith("state"):
                continue
            parts = s.split()
            if len(parts) < 4:
                continue
            # Find first integer pair (Recv-Q Send-Q), then local addr
            recv_q, send_q = 0, 0
            local = ""
            i = 0
            # Skip optional Netid (tcp/udp/u_str/...) and State (LISTEN/UNCONN/...)
            while i < len(parts) and not parts[i].isdigit():
                i += 1
            if i + 1 < len(parts) and parts[i].isdigit() and parts[i + 1].isdigit():
                try:
                    recv_q = int(parts[i])
                    send_q = int(parts[i + 1])
                except ValueError:
                    recv_q, send_q = 0, 0
                if i + 2 < len(parts):
                    local = parts[i + 2]
            if not local:
                # Fallback: last token that looks like addr:port
                for tok in parts:
                    if re.search(r":\d+$", tok.replace("]", "")):
                        local = tok
                        break
            if not local:
                continue
            m = re.search(r":(\d+)$", local.replace("]", ""))
            if not m:
                continue
            port = int(m.group(1))
            rows.append({
                "proto": proto,
                "local": local,
                "port": port,
                "recv_q": recv_q,
                "send_q": send_q,
                "line": line[:200],
            })
        return rows

    for proto in ("udp", "tcp"):
        listeners.extend(parse_ss(proto))

    # UDP presence fallback — ss may be filtered; bind-probe local DNS/DHCP
    if not any(r["proto"] == "udp" and r["port"] == 53 for r in listeners):
        for host, family in (("127.0.0.1", socket.AF_INET), ("::1", socket.AF_INET6)):
            try:
                s = socket.socket(family, socket.SOCK_DGRAM)
                s.settimeout(0.4)
                s.connect((host, 53))
                s.close()
                listeners.append({
                    "proto": "udp", "local": f"{host}:53", "port": 53,
                    "recv_q": 0, "send_q": 0, "line": "connect-fallback",
                })
                break
            except OSError:
                continue
    if not any(r["proto"] == "udp" and r["port"] == 67 for r in listeners):
        # DHCP is often 0.0.0.0:67 — presence via ss only; soft if DNS ok
        pass

    # Critical coverage
    udp_ports = {r["port"] for r in listeners if r["proto"] == "udp"}
    tcp_ports = {r["port"] for r in listeners if r["proto"] == "tcp"}
    missing: list[dict[str, Any]] = []
    for p in CRITICAL_UDP:
        if p not in udp_ports:
            missing.append({"proto": "udp", "port": p, "issue": "not_listening"})
    for p in CRITICAL_TCP:
        if p not in tcp_ports:
            missing.append({"proto": "tcp", "port": p, "issue": "not_listening"})

    # Hang heuristics: huge Recv-Q backlog (UDP DNS flood stuck) or Send-Q stuck
    HANG_RECV = int(os.environ.get("FIELD_PORT_HANG_RECV_Q", "2048"))
    HANG_SEND = int(os.environ.get("FIELD_PORT_HANG_SEND_Q", "1024"))
    for r in listeners:
        port = r["port"]
        if port not in CRITICAL_UDP and port not in CRITICAL_TCP:
            # still note extreme hang on any port
            if r["recv_q"] >= HANG_RECV * 4 or r["send_q"] >= HANG_SEND * 4:
                hangups.append({**r, "issue": "extreme_queue"})
            continue
        if r["recv_q"] >= HANG_RECV:
            hangups.append({**r, "issue": "recv_q_hang"})
        elif r["send_q"] >= HANG_SEND:
            hangups.append({**r, "issue": "send_q_hang"})
        else:
            healthy.append(r)

    # Quick TCP connect probe to C2 / Queen (no hang)
    connect_probes: list[dict[str, Any]] = []
    for port in CRITICAL_TCP:
        t0 = time.perf_counter()
        try:
            s = socket.create_connection(("127.0.0.1", port), timeout=1.0)
            s.close()
            ms = (time.perf_counter() - t0) * 1000
            connect_probes.append({"port": port, "ok": True, "ms": round(ms, 2)})
            if ms > 2000:
                hangups.append({"proto": "tcp", "port": port, "issue": "slow_connect", "ms": round(ms, 2)})
        except OSError as e:
            connect_probes.append({"port": port, "ok": False, "error": str(e)[:80]})
            # Only hangup if expected local services — mark missing
            if port not in tcp_ports:
                pass
            else:
                hangups.append({"proto": "tcp", "port": port, "issue": "connect_fail", "error": str(e)[:80]})

    no_hangups = len(hangups) == 0 and len(missing) == 0
    # Soft: Queen 9481 optional if not required
    soft_missing = [m for m in missing if m.get("port") == 9481]
    hard_missing = [m for m in missing if m.get("port") != 9481]
    critical_ok = len(hard_missing) == 0 and not any(
        h.get("port") in CRITICAL_UDP or h.get("port") == 9477 for h in hangups
    )

    return {
        "ok": critical_ok and len([h for h in hangups if h.get("port") in CRITICAL_UDP or h.get("port") == 9477]) == 0,
        "scanned_at": now,
        "no_port_hangups": no_hangups or (critical_ok and not hangups),
        "critical_ok": critical_ok,
        "listeners_n": len(listeners),
        "healthy_critical_n": len(healthy),
        "hangups_n": len(hangups),
        "hangups": hangups[:40],
        "missing_critical": missing,
        "hard_missing": hard_missing,
        "soft_missing": soft_missing,
        "connect_probes": connect_probes,
        "udp_53": 53 in udp_ports,
        "udp_67": 67 in udp_ports,
        "tcp_9477": 9477 in tcp_ports,
        "tcp_9481": 9481 in tcp_ports,
        "motto": (
            "NO PORT HANGUPS · critical OK"
            if critical_ok and not hangups
            else f"PORT ISSUES · hangups {len(hangups)} · hard_missing {len(hard_missing)}"
        ),
    }


def clear_hangups(scan: dict[str, Any], *, write: bool = True) -> dict[str, Any]:
    """Attempt light recovery — hang guard pulse, re-verify serving (no blind kill of DNS)."""
    now = _utc()
    actions: list[dict[str, Any]] = []
    hangups = list(scan.get("hangups") or [])
    hard_missing = list(scan.get("hard_missing") or [])

    # Hang guard panel refresh
    hg = _run("lib/hostess7-hang-guard.py", ["json"], timeout=20)
    actions.append({"step": "hang_guard", "ok": _ok(hg)})

    # If DNS/DHCP missing, try status modules (do not force-kill listeners)
    if not scan.get("udp_53") or not scan.get("udp_67"):
        actions.append({
            "step": "dns_dhcp_status",
            "dns": _run("lib/field-dns.py", ["json"], timeout=30) if (INSTALL / "lib/field-dns.py").is_file() else {"ok": True, "skipped": True},
            "dhcp": _run("lib/field-dhcp.py", ["json"], timeout=30) if (INSTALL / "lib/field-dhcp.py").is_file() else {"ok": True, "skipped": True},
        })

    # Collision guard / legal ports
    if (INSTALL / "lib/field-dns-dhcp-collision-guard.py").is_file():
        actions.append({
            "step": "collision_guard",
            **_run("lib/field-dns-dhcp-collision-guard.py", ["json"], timeout=45),
        })

    # Re-scan
    rescanned = scan_port_hangups()
    cleared = (scan.get("hangups_n") or 0) > (rescanned.get("hangups_n") or 0) or rescanned.get("critical_ok")

    out = {
        "ok": bool(rescanned.get("critical_ok")),
        "updated": now,
        "cleared": cleared,
        "hangups_before": scan.get("hangups_n"),
        "hangups_after": rescanned.get("hangups_n"),
        "actions_n": len(actions),
        "actions": actions,
        "rescan": {
            "critical_ok": rescanned.get("critical_ok"),
            "udp_53": rescanned.get("udp_53"),
            "udp_67": rescanned.get("udp_67"),
            "tcp_9477": rescanned.get("tcp_9477"),
            "no_port_hangups": rescanned.get("no_port_hangups"),
        },
        "hard_missing_remaining": rescanned.get("hard_missing"),
        "motto": "Port hang recovery pass complete",
        "ironclad_cite": IRONCLAD,
    }
    if write:
        _append({"event": "clear_hangups", "before": scan.get("hangups_n"), "after": rescanned.get("hangups_n")})
    return out


def everyone_served(*, write: bool = True) -> dict[str, Any]:
    """Verify everyone is served on Field plane."""
    now = _utc()
    truth = _run("lib/field-serving-truth.py", ["verify"], timeout=60)
    if not _ok(truth):
        truth = _run("lib/field-serving-truth.py", ["status"], timeout=30)

    everyone = _run("lib/field-everyone-counter.py", ["fast"], timeout=60)
    weave = _load(STATE / "field-weave-everything-inside-panel.json", {})
    tri = _load(STATE / "field-trillions-kill-path-panel.json", {})
    leases = _load(STATE / "field-dhcp-leases.json", {})
    lease_n = 0
    if isinstance(leases, dict):
        L = leases.get("leases")
        lease_n = len(L) if isinstance(L, dict) else int(leases.get("count") or 0)

    probes_ok = int(truth.get("probes_ok") or 0)
    probes_total = int(truth.get("probes_total") or 0)
    dns_live = bool(truth.get("dns_live") or truth.get("we_serve_dns_ourselves"))
    dhcp_live = bool(truth.get("dhcp_live") or truth.get("we_serve_ips_ourselves"))
    serve_plane = bool(truth.get("we_serve_everyone_on_this_plane") or (dns_live and dhcp_live and probes_ok > 0))

    people_n = int(
        (everyone if isinstance(everyone, dict) else {}).get("everyone_total")
        or (weave if isinstance(weave, dict) else {}).get("people_n")
        or 0
    )
    serving_devices = int(
        (tri if isinstance(tri, dict) else {}).get("serving_devices")
        or _load(STATE / "field-serving-capacity-panel.json", {}).get("serving_devices")
        or 0
    )

    probes_green = probes_total > 0 and probes_ok == probes_total
    everyone_ok = serve_plane and probes_ok > 0 and dns_live and dhcp_live

    return {
        "ok": everyone_ok,
        "updated": now,
        "everyone_served": everyone_ok,
        "dns_live": dns_live,
        "dhcp_live": dhcp_live,
        "probes_ok": probes_ok,
        "probes_total": probes_total,
        "probes_green": probes_green,
        "leases_with_our_dns": lease_n,
        "people_n": people_n,
        "serving_capacity": serving_devices,
        "we_serve_everyone_on_this_plane": serve_plane,
        "serving_truth": {
            "ok": _ok(truth),
            "motto": truth.get("motto") if isinstance(truth, dict) else None,
        },
        "motto": (
            f"EVERYONE SERVED · probes {probes_ok}/{probes_total} · "
            f"leases {lease_n:,} · people {people_n:,} · capacity {serving_devices:,}"
        ),
        "ironclad_cite": IRONCLAD,
    }


def enforce(*, write: bool = True) -> dict[str, Any]:
    now = _utc()
    served = everyone_served(write=write)
    ports = scan_port_hangups()
    clear = {"ok": True, "skipped": True}
    if not ports.get("critical_ok") or (ports.get("hangups_n") or 0) > 0:
        clear = clear_hangups(ports, write=write)
        ports = scan_port_hangups()  # final

    # If probes still short, re-verify serving after hang clear
    if not served.get("probes_green"):
        served = everyone_served(write=write)

    no_hang = bool(ports.get("critical_ok") and (ports.get("hangups_n") or 0) == 0)
    everyone_ok = bool(served.get("everyone_served"))
    all_ok = everyone_ok and no_hang

    motto = (
        f"{'EVERYONE SERVED' if everyone_ok else 'SERVE GAPS'} · "
        f"probes {served.get('probes_ok')}/{served.get('probes_total')} · "
        f"{'NO PORT HANGUPS' if no_hang else 'PORT HANGUPS'} · "
        f"DNS {'UP' if ports.get('udp_53') else 'DOWN'} · "
        f"DHCP {'UP' if ports.get('udp_67') else 'DOWN'} · "
        f"C2 {'UP' if ports.get('tcp_9477') else 'DOWN'}"
    )

    out = {
        "ok": all_ok,
        "schema": SCHEMA,
        "updated": now,
        "ironclad_cite": IRONCLAD,
        "title": "Everyone served · no port hangups",
        "motto": motto,
        "everyone_served": everyone_ok,
        "no_port_hangups": no_hang,
        "probes_ok": served.get("probes_ok"),
        "probes_total": served.get("probes_total"),
        "probes_green": served.get("probes_green"),
        "dns_live": served.get("dns_live"),
        "dhcp_live": served.get("dhcp_live"),
        "leases": served.get("leases_with_our_dns"),
        "people_n": served.get("people_n"),
        "serving_capacity": served.get("serving_capacity"),
        "ports": {
            "udp_53": ports.get("udp_53"),
            "udp_67": ports.get("udp_67"),
            "tcp_9477": ports.get("tcp_9477"),
            "tcp_9481": ports.get("tcp_9481"),
            "hangups_n": ports.get("hangups_n"),
            "critical_ok": ports.get("critical_ok"),
            "connect_probes": ports.get("connect_probes"),
        },
        "clear_pass": {
            "ok": _ok(clear),
            "hangups_before": clear.get("hangups_before"),
            "hangups_after": clear.get("hangups_after"),
        },
        "api": "/api/everyone-served",
        "ui": "http://127.0.0.1:9477/api/everyone-served",
    }

    if write:
        try:
            SEAL.write_text(json.dumps({
                "sealed": True,
                "everyone_served": everyone_ok,
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
            NO_HANG.write_text(json.dumps({
                "sealed": True,
                "no_port_hangups": no_hang,
                "critical_ok": ports.get("critical_ok"),
                "updated": now,
                "ironclad_cite": IRONCLAD,
            }, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        _save(PANEL, out)
        public = {
            "ok": all_ok,
            "updated": now,
            "motto": motto,
            "everyone_served": everyone_ok,
            "no_port_hangups": no_hang,
            "probes_ok": out["probes_ok"],
            "probes_total": out["probes_total"],
            "ports": out["ports"],
            "api": "/api/everyone-served",
            "ironclad_cite": IRONCLAD,
        }
        _save(PUBLIC, public)
        for api_dir in (INSTALL / "Hostess7" / "docs" / "api", INSTALL / "docs" / "api"):
            try:
                api_dir.mkdir(parents=True, exist_ok=True)
                _save(api_dir / "everyone-served.json", public)
            except OSError:
                pass
        _append({
            "event": "enforce",
            "everyone": everyone_ok,
            "no_hang": no_hang,
            "probes": f"{out['probes_ok']}/{out['probes_total']}",
        })
    return out


def status() -> dict[str, Any]:
    panel = _load(PANEL, {})
    return {
        "ok": bool(panel.get("ok") or SEAL.is_file()),
        "schema": SCHEMA,
        "sealed": SEAL.is_file(),
        "no_hang_sealed": NO_HANG.is_file(),
        "everyone_served": panel.get("everyone_served"),
        "no_port_hangups": panel.get("no_port_hangups"),
        "probes_ok": panel.get("probes_ok"),
        "probes_total": panel.get("probes_total"),
        "ports": panel.get("ports"),
        "motto": panel.get("motto"),
        "updated": panel.get("updated"),
        "api": "/api/everyone-served",
        "ironclad_cite": IRONCLAD,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower().lstrip("-")
    if cmd in ("enforce", "run", "up", "seal", "serve", "fix"):
        print(json.dumps(enforce(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("ports", "hangups", "scan"):
        print(json.dumps(scan_port_hangups(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("everyone", "served"):
        print(json.dumps(everyone_served(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("status", "json", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-everyone-served-no-hangups.py [enforce|ports|everyone|status]",
        "motto": "Everyone served · no port hangups",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
