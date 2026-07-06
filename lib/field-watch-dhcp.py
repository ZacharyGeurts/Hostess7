#!/usr/bin/env python3
"""Field watch DHCP — observe foreign/incumbent DHCP; never serve (not our DHCP)."""
from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import re
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
DOCTRINE = INSTALL / "data" / "field-watch-dhcp-doctrine.json"
PANEL = STATE / "field-watch-dhcp-panel.json"
EVENTS = STATE / "field-watch-dhcp-events.jsonl"
PID_FILE = STATE / "field-watch-dhcp.pid"
WATCH_LOCK = STATE / "field-watch-dhcp.lock"
DHCP_PORT = 67
PRIVATE_IP = re.compile(r"^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|169\.254\.)")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _append_event(row: dict[str, Any]) -> None:
    try:
        with EVENTS.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _poll_interval() -> float:
    pol = doctrine().get("policy") or {}
    return float(pol.get("poll_interval_sec") or 15)


def _mod(rel: str, name: str) -> Any | None:
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(cmd: list[str], *, timeout: float = 6.0) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
        return (proc.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _our_dhcp_running() -> bool:
    pid_path = STATE / "field-dhcp.pid"
    if pid_path.is_file():
        try:
            pid = int(pid_path.read_text(encoding="utf-8").strip().split()[0])
            os.kill(pid, 0)
            return True
        except (OSError, ValueError):
            pass
    for pat in doctrine().get("our_dhcp_markers") or ("field-dhcp.py serve",):
        try:
            proc = subprocess.run(
                ["pgrep", "-f", str(pat)],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if proc.returncode == 0 and (proc.stdout or "").strip():
                return True
        except (OSError, subprocess.TimeoutExpired):
            continue
    return False


def _watch_serve_running() -> bool:
    try:
        proc = subprocess.run(
            ["pgrep", "-f", "field-watch-dhcp.py serve"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return proc.returncode == 0 and bool((proc.stdout or "").strip())
    except (OSError, subprocess.TimeoutExpired):
        return False


def _watch_pid_alive() -> bool:
    if not PID_FILE.is_file():
        return False
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip().split()[0])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        try:
            PID_FILE.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def _dhcp_option(data: bytes, code: int) -> bytes | None:
    i = 240
    while i < len(data) - 1:
        opt = data[i]
        if opt == 255:
            break
        if opt == 0:
            i += 1
            continue
        if i + 1 >= len(data):
            break
        ln = data[i + 1]
        if i + 2 + ln > len(data):
            break
        if opt == code:
            return data[i + 2 : i + 2 + ln]
        i += 2 + ln
    return None


def _parse_offer(data: bytes) -> dict[str, Any] | None:
    if len(data) < 240 or data[0] != 2:
        return None
    yiaddr = socket.inet_ntoa(data[16:20])
    chaddr = data[28:34].hex(":")
    server_id = _dhcp_option(data, 54)
    dns = _dhcp_option(data, 6)
    lease = _dhcp_option(data, 51)
    sid = socket.inet_ntoa(server_id[:4]) if server_id and len(server_id) >= 4 else yiaddr
    dns_list = []
    if dns:
        for j in range(0, len(dns) - 3, 4):
            dns_list.append(socket.inet_ntoa(dns[j : j + 4]))
    return {
        "kind": "offer",
        "server_id": sid,
        "yiaddr": yiaddr,
        "client_mac": chaddr,
        "dns": dns_list,
        "lease_sec": struct.unpack("!I", lease[:4])[0] if lease and len(lease) >= 4 else None,
        "source": "dhcp_discover_probe",
        "authority": "foreign",
    }


def _probe_dhcp_offers(*, timeout: float = 2.0) -> list[dict[str, Any]]:
    """Send DISCOVER on ephemeral port — observe OFFERs; never bind :67."""
    pol = doctrine().get("policy") or {}
    if not pol.get("probe_discover", True):
        return []
    offers: list[dict[str, Any]] = []
    seen: set[str] = set()
    xid = struct.pack("!I", int(time.time()) & 0xFFFFFFFF)
    mac = b"\x02\x00\x00\x00\x00\xf7" + b"\x00" * 10
    pkt = b"\x01\x01\x06\x00" + xid + b"\x00" * 16 + mac + b"\x00" * 64 + b"\x00" * 128
    pkt += bytes([99, 130, 83, 99, 53, 1, 1, 255])
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    except OSError:
        pass
    sock.settimeout(timeout)
    try:
        sock.bind(("0.0.0.0", 0))
        sock.sendto(pkt, ("255.255.255.255", DHCP_PORT))
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(4096)
            except socket.timeout:
                break
            except OSError:
                break
            row = _parse_offer(data)
            if not row:
                continue
            key = f"{row.get('server_id')}|{row.get('yiaddr')}"
            if key in seen:
                continue
            seen.add(key)
            row["responder"] = addr[0]
            offers.append(row)
    except OSError:
        pass
    finally:
        sock.close()
    return offers


def _incumbent_listeners() -> list[dict[str, Any]]:
    takeover = _mod("lib/dns-service-takeover.py", "takeover")
    if not takeover or not hasattr(takeover, "detect_incumbents"):
        return []
    try:
        inc = takeover.detect_incumbents()
    except Exception:
        return []
    ours = _our_dhcp_running()
    rows: list[dict[str, Any]] = []
    for row in inc.get("dhcp_listeners") or []:
        if not isinstance(row, dict):
            continue
        bind = str(row.get("bind") or "")
        foreign = bool(inc.get("incumbent_dhcp")) and not ours
        if ours and "field-dhcp" in str(row.get("process_hint") or "").lower():
            continue
        rows.append({
            **row,
            "source": "port_listener",
            "authority": "foreign" if foreign else "incumbent_or_shared",
            "observe_only": True,
        })
    return rows


def _neigh_clients() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    text = _run(["ip", "-j", "neigh", "show"])
    if text:
        try:
            for ent in json.loads(text):
                ip = str(ent.get("dst") or "")
                if not ip or not PRIVATE_IP.match(ip):
                    continue
                rows.append({
                    "ip": ip,
                    "mac": str(ent.get("lladdr") or ""),
                    "iface": str(ent.get("dev") or ""),
                    "state": str(ent.get("state") or ""),
                    "source": "arp_neigh",
                    "authority": "observed_lan",
                })
        except json.JSONDecodeError:
            pass
    return rows


def _external_lease_files() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in doctrine().get("external_lease_paths") or []:
        pattern = str(raw)
        if "*" in pattern:
            for path in Path("/").glob(pattern.lstrip("/")):
                rows.extend(_parse_lease_file(path))
        else:
            rows.extend(_parse_lease_file(Path(pattern)))
    return rows


def _parse_lease_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    if "dnsmasq" in path.name or path.name == "dnsmasq.leases":
        for line in text.splitlines():
            parts = line.split()
            if len(parts) >= 4:
                rows.append({
                    "expires": parts[0],
                    "mac": parts[1],
                    "ip": parts[2],
                    "hostname": parts[3] if len(parts) > 3 else "",
                    "source": f"lease_file:{path}",
                    "authority": "foreign",
                })
        return rows
    mac = ""
    ip = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("lease "):
            ip = line.split()[1] if len(line.split()) > 1 else ""
        elif line.startswith("hardware ethernet "):
            mac = line.split()[2].rstrip(";") if len(line.split()) > 2 else ""
        elif line == "}" and ip and mac:
            rows.append({
                "ip": ip,
                "mac": mac,
                "source": f"lease_file:{path}",
                "authority": "foreign",
            })
            mac = ""
            ip = ""
    return rows


def observe_once() -> dict[str, Any]:
    doc = doctrine()
    pol = doc.get("policy") or {}
    listeners = _incumbent_listeners()
    offers = _probe_dhcp_offers()
    neigh = _neigh_clients()
    external = _external_lease_files()
    ours = _our_dhcp_running()
    foreign_servers = {str(o.get("server_id")) for o in offers if o.get("server_id")}
    for ln in listeners:
        bind = str(ln.get("bind") or "")
        if bind:
            foreign_servers.add(bind.split(":")[0].replace("*", "").strip())

    return {
        "ok": True,
        "schema": "field-watch-dhcp/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "observe_only": True,
        "not_our_dhcp": True,
        "our_dhcp_running": ours,
        "automated": _watch_pid_alive(),
        "policy": pol,
        "why_we_did": doc.get("why_we_did"),
        "counts": {
            "foreign_listeners": len(listeners),
            "dhcp_offers_seen": len(offers),
            "lan_neigh_hosts": len(neigh),
            "external_lease_rows": len(external),
            "foreign_servers": len(foreign_servers),
            "observed_clients": len({r.get("mac") or r.get("ip") for r in external + neigh if r.get("mac") or r.get("ip")}),
        },
        "foreign_listeners": listeners,
        "dhcp_offers": offers,
        "lan_neigh": neigh[:64],
        "external_leases": external[:128],
        "foreign_servers": sorted(foreign_servers),
        "api": doc.get("api") or "/api/field-watch-dhcp",
    }


def build_panel() -> dict[str, Any]:
    out = observe_once()
    _save(PANEL, out)
    _append_event({
        "event": "observe",
        "foreign_servers": out.get("counts", {}).get("foreign_servers"),
        "offers": out.get("counts", {}).get("dhcp_offers_seen"),
    })
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "field-watch-dhcp/v1":
        return cached
    return build_panel()


def _acquire_watch_lock() -> bool:
    WATCH_LOCK.parent.mkdir(parents=True, exist_ok=True)
    if _watch_serve_running():
        return False
    try:
        handle = open(WATCH_LOCK, "w", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    except OSError:
        return False
    handle.write(f"{os.getpid()}\n")
    handle.flush()
    return True


def _serve_loop() -> None:
    try:
        sg = importlib.util.spec_from_file_location(
            "field_pid_spawn_guard",
            INSTALL / "lib" / "field-pid-spawn-guard.py",
        )
        if sg and sg.loader:
            mod = importlib.util.module_from_spec(sg)
            sg.loader.exec_module(mod)
            mod.authorize_spawn_or_exit(service="dhcp_watch", action="serve")
    except SystemExit:
        raise
    except Exception:
        pass
    if not _acquire_watch_lock():
        return
    PID_FILE.write_text(f"{os.getpid()}\n", encoding="utf-8")

    def _stop(*_args: Any) -> None:
        try:
            PID_FILE.unlink(missing_ok=True)
        except OSError:
            pass
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    interval = min(_poll_interval(), 3)
    while True:
        try:
            build_panel()
        except Exception as exc:
            _append_event({"event": "error", "error": str(exc)[:200]})
        if interval > 0:
            time.sleep(interval)


def ensure_automated(*, start: bool = True) -> dict[str, Any]:
    """Turbo observe — inline poll only. Never spawn serve daemons from ensure."""
    pol = doctrine().get("policy") or {}
    if _watch_serve_running():
        return {"ok": True, "already_running": True, "turbo": True, "observe_only": True}
    if not start:
        return {"ok": False, "running": False, "reason": "not_started"}
    try:
        panel = build_panel()
        return {
            "ok": True,
            "turbo": True,
            "inline_poll": True,
            "observe_only": True,
            "not_our_dhcp": True,
            "spawn_forbidden": True,
            "cli_serve": "./Hostess7.sh field-watch-dhcp serve",
            "counts": panel.get("counts") or {},
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:160], "turbo": True}


def stop_watch() -> dict[str, Any]:
    if not PID_FILE.is_file():
        return {"ok": True, "stopped": False, "reason": "not_running"}
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip().split()[0])
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.3)
    except (OSError, ValueError):
        pass
    try:
        PID_FILE.unlink(missing_ok=True)
    except OSError:
        pass
    return {"ok": True, "stopped": True}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("once", "observe", "build"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "serve":
        _serve_loop()
        return 0
    if cmd in ("ensure", "auto", "start"):
        print(json.dumps(ensure_automated(start=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "stop":
        print(json.dumps(stop_watch(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "why":
        doc = doctrine()
        print(json.dumps(doc.get("why_we_did") or {}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-watch-dhcp.py [json|once|serve|ensure|stop|why]",
        "motto": doctrine().get("motto"),
        "observe_only": True,
        "api": doctrine().get("api"),
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())