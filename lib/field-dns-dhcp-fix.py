#!/usr/bin/env python3
"""Fix DNS and DHCP everywhere — prune pile-up, recover hung resolver, promote primary."""
from __future__ import annotations

import json
import os
import signal
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DNS_HOST = os.environ.get("NEXUS_FIELD_DNS_IPV4", "127.0.0.1")
DNS_PORT = int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53") or "53")
DHCP_PORT = 67
PROBE_QNAME = os.environ.get("NEXUS_DNS_TAKEOVER_HEALTH_QNAME", "example.com")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _env(*, recovery: bool = False) -> dict[str, str]:
    env = {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_FIELD_DNS": "1",
        "NEXUS_FIELD_DHCP": "1",
        "NEXUS_LEGACY_OPEN_SECURED": "1",
        "NEXUS_FIELD_DNS_LEGACY_COMPAT": "1",
        "NEXUS_NEVER_DOWN_INLINE": "0",
    }
    if recovery:
        env["NEXUS_FIELD_DNS_ANY_IP"] = "0"
        env["NEXUS_FIELD_DHCP_ANY_IP"] = "0"
        env["NEXUS_FIELD_DNS_BINDS_IPV4"] = "127.0.0.1"
        env["NEXUS_FIELD_DNS_BINDS_IPV6"] = "::1"
    return env


def _encode_name(name: str) -> bytes:
    out = bytearray()
    for label in name.rstrip(".").split("."):
        raw = label.encode("ascii")[:63]
        out.append(len(raw))
        out.extend(raw)
    out.append(0)
    return bytes(out)


def dns_probe(host: str = DNS_HOST, qname: str = PROBE_QNAME, timeout: float = 2.0) -> bool:
    txn = struct.pack("!H", int(time.time()) & 0xFFFF)
    header = txn + struct.pack("!HHHHH", 0x0100, 1, 0, 0, 0)
    packet = header + _encode_name(qname) + struct.pack("!HH", 1, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(packet, (host, DNS_PORT))
        data, _ = sock.recvfrom(4096)
        return len(data) >= 12
    except OSError:
        return False
    finally:
        sock.close()


def _port_busy(port: int, proto: str = "udp") -> bool:
    flag = "-u" if proto == "udp" else "-t"
    try:
        proc = subprocess.run(
            ["ss", "-H", "-l", "-n", flag, f"sport = :{port}"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        return bool((proc.stdout or "").strip())
    except (OSError, subprocess.TimeoutExpired):
        return False


def _pids(pattern: str) -> list[int]:
    try:
        proc = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=4,
        )
        if proc.returncode != 0:
            return []
        me = os.getpid()
        out: list[int] = []
        for line in (proc.stdout or "").splitlines():
            try:
                pid = int(line.strip())
            except ValueError:
                continue
            if pid != me:
                out.append(pid)
        return out
    except (OSError, subprocess.TimeoutExpired):
        return []


def _kill_pid(pid: int) -> bool:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.kill(pid, sig)
            time.sleep(0.2)
            return True
        except PermissionError:
            try:
                subprocess.run(
                    ["sudo", "-n", "kill", "-9", str(pid)],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
                time.sleep(0.2)
                return True
            except (OSError, subprocess.TimeoutExpired):
                pass
        except ProcessLookupError:
            return True
        except OSError:
            pass
    return False


def _run_py(rel: str, *args: str, recovery: bool = False, timeout: float = 90.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": "missing", "script": rel}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(recovery=recovery),
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            doc = json.loads(raw)
            if isinstance(doc, dict):
                doc.setdefault("ok", proc.returncode == 0)
                return doc
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                doc = json.loads(line)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
        return {"ok": proc.returncode == 0, "stdout": raw[:400], "rc": proc.returncode}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "script": rel}
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc)[:160], "script": rel}


def _kill_all_dns() -> list[int]:
    killed: list[int] = []
    for pid in _pids("field-dns.py"):
        if _kill_pid(pid):
            killed.append(pid)
    for path in (STATE / "field-dns.pid", STATE / "field-dns.lock"):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
    time.sleep(0.5)
    return killed


def _sudo_action(action: str) -> dict[str, Any]:
    wrapper = INSTALL / "scripts" / "hostess7-field-sudo.sh"
    secure = INSTALL / "lib" / "hostess7-sudo-secure.py"
    if secure.is_file():
        return _run_py("lib/hostess7-sudo-secure.py", "run", action, timeout=120.0)
    if wrapper.is_file():
        try:
            proc = subprocess.run(
                ["bash", str(wrapper), "run", action],
                capture_output=True,
                text=True,
                timeout=120,
                env=_env(),
                check=False,
            )
            raw = (proc.stdout or "").strip()
            if raw.startswith("{"):
                return json.loads(raw)
            return {"ok": proc.returncode == 0, "stdout": raw[:400]}
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            return {"ok": False, "error": str(exc)[:160]}
    return {"ok": False, "skipped": True, "reason": "sudo_wrapper_missing"}


# Explicit unsafe units — direct systemd list, no glob discovery.
_DOGSHIT_DOC = INSTALL / "data" / "field-dogshit-purge.json"


def _dogshit_doc() -> dict[str, Any]:
    try:
        return json.loads(_DOGSHIT_DOC.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


UNSAFE_SYSTEMD_UNITS = tuple(
    _dogshit_doc().get("unsafe_systemd")
    or ("ModemManager.service", "touchegg.service", "kerneloops.service", "fwupd.service", "colord.service")
)

# Protected online + truth stack — never stop these units.
PROTECTED_SYSTEMD_UNITS = frozenset({
    "NetworkManager.service",
    "wpa_supplicant.service",
    "systemd-timesyncd.service",
    "systemd-resolved.service",
    "field-grok-spawner-kill.service",
    "nexus-field-early.service",
    "nexus-genius.service",
    "dbus.service",
})


def _sudo_pw() -> str:
    return os.environ.get("HOSTESS7_SUDO_PW", "mememe")


def _systemctl_sudo(*args: str, timeout: float = 15.0) -> bool:
    pw = _sudo_pw()
    cmd = ["systemctl", *args]
    for mode in (["sudo", "-n", *cmd], ["sudo", "-S", *cmd]):
        try:
            proc = subprocess.run(
                mode,
                input=(f"{pw}\n" if len(mode) > 1 and mode[1] == "-S" else None),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            if proc.returncode == 0:
                return True
        except (OSError, subprocess.TimeoutExpired):
            continue
    return False


def flatline_unsafe_systemd() -> dict[str, Any]:
    """Stop, disable, mask unsafe units — flatline respawns; keep DNS/DHCP lane online."""
    units = [u for u in UNSAFE_SYSTEMD_UNITS if u not in PROTECTED_SYSTEMD_UNITS]
    flatlined: list[dict[str, Any]] = []
    failed: list[str] = []
    if units:
        script = "\n".join(
            f'systemctl stop "{u}" 2>/dev/null; systemctl disable "{u}" 2>/dev/null; systemctl mask "{u}" 2>/dev/null'
            for u in units
        )
        try:
            subprocess.run(
                ["sudo", "-S", "bash", "-c", script],
                input=f"{_sudo_pw()}\n",
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
        for unit in units:
            try:
                proc = subprocess.run(
                    ["systemctl", "is-enabled", unit],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                state = (proc.stdout or proc.stderr or "").strip().lower()
            except (OSError, subprocess.TimeoutExpired):
                state = ""
            ok = state == "masked"
            if ok:
                flatlined.append({"unit": unit, "steps": ["stop", "disable", "mask"], "ok": True})
            else:
                failed.append(unit)
    return {
        "ok": not failed or bool(flatlined),
        "flatlined": flatlined,
        "failed": failed,
        "protected": sorted(PROTECTED_SYSTEMD_UNITS),
    }


def stop_unsafe_systemd() -> dict[str, Any]:
    """Flatline unsafe OS services; keep NetworkManager + DNS/DHCP lane online."""
    return flatline_unsafe_systemd()


def prune_unsafe_panels() -> dict[str, Any]:
    """Kill duplicate panel subprocess storms — explicit patterns only."""
    doc = _dogshit_doc()
    keep_n = 1
    storms = [(p, keep_n) for p in (doc.get("panel_storms") or (
        "hostess7-lab-sovereign.py panel",
        "field-internet-unified.py panel",
        "qemu-world-status.py json",
        "hostess7-g16-online.py panel",
        "connection-gatekeeper.py",
        "field-sovereign-protocol-bridge.py json",
        "ammonet-field.py panel",
        "znetwork-orchestrator.py status",
    ))]
    protected = (
        "field-dns.py",
        "field-dhcp.py",
        "field-grok-spawner-kill.py",
        "threat-panel-http.py",
        "nexus-daemon.sh",
    )
    killed: dict[str, list[int]] = {}
    for pattern, keep in storms:
        pids = _pids(pattern)
        victims: list[int] = []
        for pid in pids:
            try:
                cmd = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode("utf-8", "replace")
            except OSError:
                cmd = ""
            if any(p in cmd for p in protected):
                continue
            victims.append(pid)
        if len(victims) > keep:
            for pid in victims[:-keep]:
                if _kill_pid(pid):
                    killed.setdefault(pattern, []).append(pid)
    return {"ok": True, "killed": killed, "killed_total": sum(len(v) for v in killed.values())}


def prune_pileup() -> dict[str, Any]:
    """Stop duplicate ensure/watch/dig storms; keep one watch daemon."""
    killed: dict[str, list[int]] = {"ensure": [], "watch_extra": [], "dig": []}

    for pid in _pids("field-never-down.py ensure"):
        if _kill_pid(pid):
            killed["ensure"].append(pid)

    watch_pids = _pids("field-watch-dhcp.py serve")
    if len(watch_pids) > 1:
        for pid in watch_pids[1:]:
            if _kill_pid(pid):
                killed["watch_extra"].append(pid)

    for pid in _pids("dig @127.0.0.1"):
        if _kill_pid(pid):
            killed["dig"].append(pid)

    return {
        "ok": True,
        "killed": killed,
        "ensure_remaining": len(_pids("field-never-down.py ensure")),
        "watch_remaining": len(_pids("field-watch-dhcp.py serve")),
    }


def recover_dns(*, force: bool = False) -> dict[str, Any]:
    """Restart hung Truth DNS when :53 is busy but probes fail."""
    if os.environ.get("NEXUS_DNS_FIX_ACTIVE", "").strip() == "1":
        healthy = dns_probe()
        return {"ok": healthy, "healthy": healthy, "skipped": "fix_active"}
    os.environ["NEXUS_DNS_FIX_ACTIVE"] = "1"
    port_busy = _port_busy(DNS_PORT, "udp")
    healthy = dns_probe()
    if healthy and not force:
        return {"ok": True, "already_healthy": True, "port_busy": port_busy}

    steps: list[dict[str, Any]] = []
    steps.append({"step": "kill_all_dns", "killed": _kill_all_dns()})

    if not dns_probe():
        steps.append({"step": "sudo_truth_dns_serve", **_sudo_action("truth-dns-serve")})
        time.sleep(2)
    if not dns_probe():
        steps.append({"step": "sudo_nexus_genius", **_sudo_action("nexus-genius")})
        time.sleep(2)
    if not dns_probe():
        log = STATE / "field-dns-serve.log"
        try:
            with log.open("a", encoding="utf-8") as fh:
                subprocess.Popen(
                    [sys.executable, str(INSTALL / "lib" / "field-dns.py"), "serve"],
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    env=_env(recovery=True),
                    start_new_session=True,
                    cwd=str(INSTALL),
                )
            steps.append({"step": "field_dns_serve_bg_loopback", "ok": True})
        except OSError as exc:
            steps.append({"step": "field_dns_serve_bg_loopback", "ok": False, "error": str(exc)[:160]})

    for _ in range(16):
        if dns_probe():
            break
        time.sleep(0.5)

    up = dns_probe()
    return {
        "ok": up,
        "healthy": up,
        "port_busy": _port_busy(DNS_PORT, "udp"),
        "steps": steps,
    }


def recover_dhcp() -> dict[str, Any]:
    """Promote takeover primary and bind DHCP :67."""
    steps: list[dict[str, Any]] = []
    steps.append({"step": "takeover_evaluate", **_run_py("lib/dns-service-takeover.py", "evaluate", timeout=30)})

    if not dns_probe():
        steps.append({"step": "dns_recover_first", "detail": recover_dns()})

    steps.append({"step": "legacy_ensure_primary", **_run_py("lib/field-legacy-connect.py", "ensure-primary", timeout=120)})

    crush_sh = INSTALL / "scripts" / "dhcp-crush.sh"
    if crush_sh.is_file():
        try:
            proc = subprocess.run(
                ["bash", str(crush_sh)],
                cwd=str(INSTALL),
                capture_output=True,
                text=True,
                timeout=180,
                env=_env(),
                check=False,
            )
            steps.append({"step": "dhcp_crush", "ok": proc.returncode == 0, "rc": proc.returncode})
        except (OSError, subprocess.TimeoutExpired) as exc:
            steps.append({"step": "dhcp_crush", "ok": False, "error": str(exc)[:160]})
    else:
        steps.append({"step": "field_dhcp_crush", **_run_py("lib/field-dhcp.py", "crush", timeout=60)})

    if not _pids("field-dhcp.py serve"):
        log = STATE / "field-dhcp-serve.log"
        try:
            with log.open("a", encoding="utf-8") as fh:
                subprocess.Popen(
                    [sys.executable, str(INSTALL / "lib" / "field-dhcp.py"), "serve"],
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    env=_env(),
                    start_new_session=True,
                    cwd=str(INSTALL),
                )
            steps.append({"step": "dhcp_serve_bg", "ok": True})
        except OSError as exc:
            steps.append({"step": "dhcp_serve_bg", "ok": False, "error": str(exc)[:160]})

    dhcp_json = _run_py("lib/field-dhcp.py", "json", timeout=45)
    port_67 = _port_busy(DHCP_PORT, "udp")
    return {
        "ok": bool(dhcp_json.get("may_serve") or port_67),
        "port_67": port_67,
        "may_serve": bool(dhcp_json.get("may_serve")),
        "takeover_phase": dhcp_json.get("takeover_phase"),
        "steps": steps,
        "dhcp": dhcp_json,
    }


def fix_planetary() -> dict[str, Any]:
    """Refresh planetary DNS/DHCP panels and collision guard."""
    rows: dict[str, Any] = {}
    for rel, cmd, timeout in (
        ("lib/field-dns-dhcp-collision-guard.py", "enforce", 45.0),
        ("lib/field-planetary-dns-dhcp.py", "panel", 30.0),
        ("lib/field-world-dns-dhcp-scale.py", "json", 20.0),
    ):
        rows[Path(rel).stem] = _run_py(rel, cmd, timeout=timeout)
    ok = any(isinstance(v, dict) and v.get("ok") for v in rows.values())
    return {"ok": ok, "modules": rows}


def connect_local() -> dict[str, Any]:
    return _run_py("lib/field-local-dns-connect.py", "connect", timeout=30)


def fix_everywhere(*, write: bool = True) -> dict[str, Any]:
    """Full DNS/DHCP recovery — prune unsafe, keep truth resolver + DHCP online."""
    unsafe_units = stop_unsafe_systemd()
    unsafe_panels = prune_unsafe_panels()
    prune = prune_pileup()
    dns = recover_dns()
    dhcp = recover_dhcp()
    watch = _run_py("lib/field-watch-dhcp.py", "ensure", timeout=20)
    planetary = fix_planetary()
    connect = connect_local() if dns.get("healthy") else {"ok": False, "skipped": True}

    dns_status = _run_py("lib/field-dns.py", "status", timeout=15)
    out = {
        "ok": bool(dns.get("healthy")) and bool(dhcp.get("port_67") or dhcp.get("may_serve")),
        "schema": "field-dns-dhcp-fix/v1",
        "updated": _utc(),
        "motto": "Fix DNS and DHCP everywhere — prune pile-up, recover truth, promote primary.",
        "dns_healthy": bool(dns.get("healthy")),
        "dhcp_port_67": bool(dhcp.get("port_67")),
        "dhcp_may_serve": bool(dhcp.get("may_serve")),
        "takeover_phase": dhcp.get("takeover_phase"),
        "unsafe_units": unsafe_units,
        "unsafe_panels": unsafe_panels,
        "prune": prune,
        "dns": dns,
        "dhcp": dhcp,
        "watch": watch,
        "planetary": planetary,
        "connect": connect,
        "dns_status": dns_status,
        "api": "/api/field-dns-dhcp-fix",
    }
    if write:
        path = STATE / "field-dns-dhcp-fix.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    return out


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "fix").strip().lower()
    if cmd in ("fix", "everywhere", "fix-everywhere", "recover"):
        print(json.dumps(fix_everywhere(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "prune":
        print(json.dumps({
            "ok": True,
            "pileup": prune_pileup(),
            "unsafe_panels": prune_unsafe_panels(),
            "unsafe_units": stop_unsafe_systemd(),
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "unsafe":
        print(json.dumps({
            "ok": True,
            "unsafe_panels": prune_unsafe_panels(),
            "unsafe_units": stop_unsafe_systemd(),
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "dns":
        print(json.dumps(recover_dns(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dhcp":
        print(json.dumps(recover_dhcp(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "status"):
        path = STATE / "field-dns-dhcp-fix.json"
        try:
            print(path.read_text(encoding="utf-8"))
        except OSError:
            print(json.dumps(fix_everywhere(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-dns-dhcp-fix.py [fix|prune|dns|dhcp|json]",
        "motto": "Fix DNS and DHCP everywhere",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())