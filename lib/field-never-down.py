#!/usr/bin/env python3
"""Never go down — every server instantiates Field 1; always field-1 identity."""
from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "field-never-down-doctrine.json"
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-never-down-panel.json"
LEDGER = STATE / "field-never-down-ledger.jsonl"
PID_FILE = STATE / "field-never-down.pid"
INSTANT = STATE / "field-one-instantiate.json"
OP_LOCK = STATE / "field-never-down.lock"
DNS_HOST = os.environ.get("NEXUS_FIELD_DNS_IPV4", "127.0.0.1")
DNS_PORT = int(os.environ.get("NEXUS_FIELD_DNS_PORT", "53") or "53")


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


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


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


def _env(*, inline_never_down: bool = False) -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_FIELD_DNS": "1",
        "NEXUS_FIELD_DHCP": "1",
        "NEXUS_LEGACY_OPEN_SECURED": "1",
        "NEXUS_FIELD_DNS_LEGACY_COMPAT": "1",
        "NEXUS_FIELD_DHCP_BIND": os.environ.get("NEXUS_FIELD_DHCP_BIND", "192.168.47.1"),
        "NEXUS_NEVER_DOWN_INLINE": "1" if inline_never_down else "0",
    }


_OP_LOCK_HANDLE = None


def _release_op_lock() -> None:
    global _OP_LOCK_HANDLE
    if _OP_LOCK_HANDLE is not None:
        try:
            fcntl.flock(_OP_LOCK_HANDLE.fileno(), fcntl.LOCK_UN)
            _OP_LOCK_HANDLE.close()
        except OSError:
            pass
        _OP_LOCK_HANDLE = None


def _acquire_op_lock() -> bool:
    global _OP_LOCK_HANDLE
    OP_LOCK.parent.mkdir(parents=True, exist_ok=True)
    try:
        handle = open(OP_LOCK, "w", encoding="utf-8")
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    except OSError:
        return False
    handle.write(f"{os.getpid()}\n")
    handle.flush()
    _OP_LOCK_HANDLE = handle
    return True


def _dns_healthy() -> bool:
    qname = os.environ.get("NEXUS_DNS_TAKEOVER_HEALTH_QNAME", "example.com")
    txn = struct.pack("!H", int(time.time()) & 0xFFFF)
    header = txn + struct.pack("!HHHHH", 0x0100, 1, 0, 0, 0)
    out = bytearray()
    for label in qname.rstrip(".").split("."):
        raw = label.encode("ascii")[:63]
        out.append(len(raw))
        out.extend(raw)
    out.append(0)
    packet = header + bytes(out) + struct.pack("!HH", 1, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    try:
        sock.sendto(packet, (DNS_HOST, DNS_PORT))
        data, _ = sock.recvfrom(4096)
        return len(data) >= 12
    except OSError:
        return False
    finally:
        sock.close()


def _dhcp_port_up() -> bool:
    try:
        proc = subprocess.run(
            ["ss", "-H", "-l", "-n", "-u", "sport = :67"],
            capture_output=True,
            text=True,
            timeout=4,
        )
        return bool((proc.stdout or "").strip())
    except (OSError, subprocess.TimeoutExpired):
        return False


def _run_json(
    rel: str,
    args: list[str],
    *,
    timeout: float = 90.0,
    background: bool = False,
    inline_never_down: bool = False,
) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": "missing", "script": rel}
    if background:
        log_name = Path(rel).stem.replace(".py", "") + "-serve.log"
        log = STATE / log_name
        try:
            if _pgrep(f"{Path(rel).name} serve"):
                return {"ok": True, "already_running": True, "script": rel}
            with log.open("a", encoding="utf-8") as fh:
                proc = subprocess.Popen(
                    [sys.executable, str(py), "serve"],
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    env=_env(inline_never_down=inline_never_down),
                    start_new_session=True,
                    cwd=str(INSTALL),
                )
            time.sleep(0.5)
            return {"ok": True, "started": True, "pid": proc.pid, "log": str(log)}
        except OSError as exc:
            return {"ok": False, "error": str(exc)[:160]}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(inline_never_down=inline_never_down),
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


def _pgrep(pattern: str) -> bool:
    try:
        proc = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            timeout=3,
        )
        return proc.returncode == 0 and bool((proc.stdout or "").strip())
    except (OSError, subprocess.TimeoutExpired):
        return False


def _pid_alive(name: str) -> bool:
    path = STATE / name
    if not path.is_file():
        return False
    try:
        pid = int(path.read_text(encoding="utf-8").strip().split()[0])
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def local_node() -> dict[str, Any]:
    host = socket.gethostname()
    return {
        "node_id": f"field-1-{host.replace('.', '-')}",
        "kind": "field_one_local",
        "field_id": "field-1",
        "hostname": host,
        "always_field_one": True,
        "source": "instantiate",
    }


def field_one_identity() -> dict[str, Any]:
    doc = doctrine()
    hub = dict(doc.get("field_one_hub") or {})
    one = _mod("lib/field-one.py", "field_one")
    if one and hasattr(one, "field_one_hub"):
        try:
            hub = {**hub, **one.field_one_hub()}
        except Exception:
            pass
    hub["id"] = "field-1"
    return {
        "schema": "field-one-identity/v1",
        "updated": _utc(),
        "never_go_down": True,
        "always_field_one": True,
        "every_server_instantiates": True,
        "hub": hub,
        "node": local_node(),
    }


def _stamp_local_h7r() -> dict[str, Any]:
    h7r = _mod("lib/field-h7r-stack.py", "h7r")
    if not h7r:
        return {"ok": False, "skipped": "h7r_missing"}
    node = local_node()
    if hasattr(h7r, "rapid_distribute"):
        try:
            return h7r.rapid_distribute(fast_panels=True, batch_size=1, workers=1)
        except TypeError:
            pass
    if hasattr(h7r, "_live_panels") and hasattr(h7r, "_stamp_one"):
        try:
            panels = h7r._live_panels(fast=True)
            racks = h7r._rack_paths() if hasattr(h7r, "_rack_paths") else []
            return h7r._stamp_one(node, panels, racks)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:160]}
    return _run_json("lib/field-h7r-stack.py", ["json"], timeout=30)


def service_status() -> dict[str, Any]:
    dns_proc = _pid_alive("field-dns.pid") or _pgrep("field-dns.py serve")
    dhcp_proc = _pid_alive("field-dhcp.pid") or _pgrep("field-dhcp.py serve")
    watch = _pid_alive("field-watch-dhcp.pid") or _pgrep("field-watch-dhcp.py serve")
    return {
        "dns_running": bool(dns_proc and _dns_healthy()),
        "dhcp_running": bool(dhcp_proc and _dhcp_port_up()),
        "dhcp_watch_running": watch,
        "dns_process": dns_proc,
        "dhcp_process": dhcp_proc,
        "field_one": True,
        "hub_id": "field-1",
    }


def instantiate(*, write: bool = True) -> dict[str, Any]:
    """Bootstrap this host as Field 1 — DNS, DHCP, watch, H7r, fleet."""
    if not _acquire_op_lock():
        cached = _load(INSTANT, {})
        if cached:
            cached["services"] = service_status()
            cached["ok"] = bool(cached["services"].get("dns_running"))
            return cached
        return {
            "ok": False,
            "schema": "field-never-down-instantiate/v1",
            "error": "busy",
            "motto": doctrine().get("motto"),
        }
    try:
        return _instantiate_locked(write=write)
    finally:
        _release_op_lock()


def _instantiate_locked(*, write: bool = True) -> dict[str, Any]:
    doc = doctrine()
    identity = field_one_identity()
    steps: list[dict[str, Any]] = []

    for lane in doc.get("instantiate_lanes") or []:
        if not isinstance(lane, dict):
            continue
        lid = str(lane.get("id") or "")
        mod = str(lane.get("module") or "")
        cmd = str(lane.get("cmd") or "json")
        bg = bool(lane.get("background"))
        if lid == "h7r_local":
            row = _stamp_local_h7r()
        elif bg:
            row = _run_json(mod, [cmd], background=True)
        else:
            timeout = 120.0 if cmd in ("ensure-primary", "ensure") else 60.0
            inline = lid != "local_connect"
            row = _run_json(mod, [cmd], timeout=timeout, inline_never_down=inline)
        steps.append({"lane": lid, "module": mod, "cmd": cmd, **row})

    status = service_status()
    fleet = next((s for s in steps if s.get("lane") == "fleet_protect"), {})
    primary = next((s for s in steps if s.get("lane") == "legacy_primary"), {})

    out = {
        "ok": True,
        "schema": "field-never-down-instantiate/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "never_go_down": True,
        "always_field_one": True,
        "every_server_instantiates": True,
        "identity": identity,
        "services": status,
        "primary": bool(primary.get("primary") or primary.get("ok")),
        "fleet": fleet,
        "steps": steps,
        "why_we_did": doc.get("why_we_did"),
        "api": doc.get("api") or "/api/field-never-down",
    }
    out["ok"] = bool(status.get("dns_running")) and (
        bool(status.get("dhcp_running")) or bool(primary.get("ok"))
    )
    if write:
        _save(INSTANT, out)
        _save(PANEL, {**out, "schema": "field-never-down/v1"})
        _append_ledger({"event": "instantiate", "dns": status.get("dns_running"), "dhcp": status.get("dhcp_running")})
    return out


def ensure_up(*, write: bool = True) -> dict[str, Any]:
    """Restart anything down — never go down."""
    if not _acquire_op_lock():
        status = service_status()
        return {
            "ok": bool(status.get("dns_running")),
            "schema": "field-never-down-ensure/v1",
            "updated": _utc(),
            "never_go_down": True,
            "skipped": "busy",
            "services": status,
            "identity": field_one_identity(),
        }
    try:
        return _ensure_up_locked(write=write)
    finally:
        _release_op_lock()


def _ensure_up_locked(*, write: bool = True) -> dict[str, Any]:
    status = service_status()
    restarted: list[str] = []
    if not status.get("dns_running"):
        fix = _run_json("lib/field-dns-dhcp-fix.py", ["dns"], timeout=90)
        if not fix.get("healthy"):
            r = _run_json("lib/field-dns-resolve.py", ["ensure"], timeout=60)
            if not r.get("truth_up"):
                _run_json("lib/field-dns.py", ["serve"], background=True)
        restarted.append("dns")
    if not status.get("dhcp_running"):
        _run_json("lib/field-legacy-connect.py", ["ensure-primary"], timeout=90)
        _run_json("lib/field-dhcp.py", ["serve"], background=True)
        restarted.append("dhcp")
    if not status.get("dhcp_watch_running"):
        _run_json("lib/field-watch-dhcp.py", ["once"], timeout=12)
        restarted.append("dhcp_watch_poll")
    status = service_status()
    out = {
        "ok": bool(status.get("dns_running")),
        "schema": "field-never-down-ensure/v1",
        "updated": _utc(),
        "never_go_down": True,
        "restarted": restarted,
        "services": status,
        "identity": field_one_identity(),
    }
    if write:
        _save(PANEL, {**out, "schema": "field-never-down/v1", "motto": doctrine().get("motto")})
    return out


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "field-never-down/v1":
        cached["services"] = service_status()
        return cached
    return ensure_up(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("instantiate", "boot", "field-1", "field1"):
        print(json.dumps(instantiate(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("ensure", "up", "never-down", "restart"):
        print(json.dumps(ensure_up(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("fix", "fix-everywhere", "fix-dns-dhcp"):
        print(json.dumps(_run_json("lib/field-dns-dhcp-fix.py", ["fix"], timeout=240), ensure_ascii=False, indent=2))
        return 0
    if cmd == "identity":
        print(json.dumps(field_one_identity(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "why":
        print(json.dumps(doctrine().get("why_we_did") or {}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-never-down.py [instantiate|ensure|identity|why|json]",
        "motto": doctrine().get("motto"),
        "api": doctrine().get("api"),
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())