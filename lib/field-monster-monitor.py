#!/usr/bin/env python3
"""Monster — AmmoOS system monitor & rescue panel. Grok16 5.1.0 field stamp."""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-monster-monitor-doctrine.json"

_PROTECTED = (
    "threat-panel-http",
    "field-host-desktop",
    "queen-world",
    "field-monster-monitor",
    "ironclad-immediate",
    "nexus.sh",
    "start-field-stack",
)

_FIELD_SERVICES = (
    {"id": "nexus_panel", "name": "NEXUS Panel", "port": 9477, "path": "/api/field-host-desktop"},
    {"id": "queen_world", "name": "Queen World", "port": 9481, "path": "/api/queen-field-sanity"},
    {"id": "final_eye", "name": "Final Eye", "port": 9479, "path": "/ops"},
    {"id": "ammocode", "name": "AmmoCode", "port": 9478, "path": "/"},
)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _cpu_sample() -> dict[str, Any]:
    try:
        line = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0]
        parts = [int(x) for x in line.split()[1:]]
        idle = parts[3] + (parts[4] if len(parts) > 4 else 0)
        return {"idle": idle, "total": sum(parts), "cores": os.cpu_count() or 1}
    except (OSError, ValueError, IndexError):
        return {"idle": 0, "total": 1, "cores": 1}


_prev_cpu: dict[str, Any] | None = None


def _cpu_pct() -> float:
    global _prev_cpu
    cur = _cpu_sample()
    pct = 0.0
    if _prev_cpu and cur["total"] > _prev_cpu["total"]:
        dt = cur["total"] - _prev_cpu["total"]
        didle = cur["idle"] - _prev_cpu["idle"]
        pct = round(max(0.0, min(100.0, 100.0 * (1.0 - didle / dt))), 2)
    _prev_cpu = cur
    return pct


def _mem() -> dict[str, Any]:
    mem: dict[str, int] = {}
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            mem[k.strip()] = int(v.strip().split()[0])
    except OSError:
        pass
    total = mem.get("MemTotal", 0)
    avail = mem.get("MemAvailable", mem.get("MemFree", 0))
    used = max(0, total - avail) if total else 0
    swap_total = mem.get("SwapTotal", 0)
    swap_free = mem.get("SwapFree", 0)
    swap_used = max(0, swap_total - swap_free) if swap_total else 0
    return {
        "total_kb": total,
        "used_kb": used,
        "available_kb": avail,
        "used_pct": round(100.0 * used / total, 2) if total else 0.0,
        "swap_total_kb": swap_total,
        "swap_used_kb": swap_used,
        "swap_used_pct": round(100.0 * swap_used / swap_total, 2) if swap_total else 0.0,
    }


def _parse_ps_line(line: str) -> dict[str, Any] | None:
    line = line.strip()
    if not line:
        return None
    parts = line.split(None, 5)
    if len(parts) < 6:
        return None
    try:
        pid = int(parts[0])
    except ValueError:
        return None
    user, pcpu, pmem, etime, cmd = parts[1], parts[2], parts[3], parts[4], parts[5]
    name = Path(cmd.split()[0]).name if cmd else "?"
    protected = any(m in cmd for m in _PROTECTED)
    return {
        "pid": pid,
        "user": user,
        "cpu_pct": float(pcpu) if pcpu.replace(".", "", 1).isdigit() else 0.0,
        "mem_pct": float(pmem) if pmem.replace(".", "", 1).isdigit() else 0.0,
        "etime": etime,
        "cmd": cmd[:240],
        "name": name,
        "protected": protected,
    }


def list_processes(*, limit: int = 120) -> list[dict[str, Any]]:
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid,user,pcpu,pmem,etime,args", "--sort=-pcpu", "--no-headers"],
            capture_output=True,
            text=True,
            timeout=12,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    rows: list[dict[str, Any]] = []
    for line in (proc.stdout or "").splitlines():
        row = _parse_ps_line(line)
        if row:
            rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.35):
            return True
    except OSError:
        return False


def field_services() -> list[dict[str, Any]]:
    out = []
    for svc in _FIELD_SERVICES:
        up = _port_open(int(svc["port"]))
        out.append({**svc, "up": up, "status": "running" if up else "stopped"})
    return out


def intel_snapshot() -> dict[str, Any]:
    """Security hold posture, OCR brain witness, alt-tab yield readiness."""
    underlay = _load(INSTALL / "data" / "field-underlay-doctrine.json", {})
    host_desktop = _load(INSTALL / "data" / "field-host-desktop-doctrine.json", {})
    policy = host_desktop.get("policy") or {}
    protections = list((underlay.get("protections_envelope") or [])[:8])
    ocr_brain: dict[str, Any] = {}
    meld = INSTALL / "lib" / "field-sense-package-meld.py"
    if meld.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("meld_intel", meld)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "_witness_hostess7_ocr_brain"):
                    ocr_brain = mod._witness_hostess7_ocr_brain()
        except Exception:
            pass
    return {
        "schema": "field-monster-intel/v1",
        "ok": True,
        "updated": _now(),
        "security": {
            "security_hold": True,
            "freeze_underlying_os": False,
            "guest_os_passthrough": bool((underlay.get("policy") or {}).get("guest_os_passthrough")),
            "yield_to_host_ready": True,
            "alt_tab_sovereign_default": bool(policy.get("keyboard_sovereign", True)),
            "protections": protections,
            "motto": "Hold security — do not freeze the guest OS while AmmoOS runs.",
        },
        "ocr_brain": ocr_brain,
        "monster_tabs": (_load(DOCTRINE, {}).get("ui") or {}).get("tabs") or [],
    }


def snapshot() -> dict[str, Any]:
    perf_mod = INSTALL / "lib" / "field-performance-flyout.py"
    thermal: dict[str, Any] = {}
    if perf_mod.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("perf", perf_mod)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "sample"):
                    doc = mod.sample()
                    thermal = doc.get("thermal") or {}
        except Exception:
            pass
    try:
        loadavg = [round(float(x), 2) for x in os.getloadavg()]
    except OSError:
        loadavg = [0.0, 0.0, 0.0]
    return {
        "schema": "field-monster-monitor/v1",
        "ok": True,
        "title": "Monster",
        "motto": "Rescue system monitor — graphs, vision, security hold.",
        "updated": _now(),
        "cpu_pct": _cpu_pct(),
        "cpu_cores": _cpu_sample().get("cores", 1),
        "loadavg": loadavg,
        "memory": _mem(),
        "thermal": thermal,
        "process_count": len(list_processes(limit=500)),
        "services": field_services(),
        "uptime_sec": _uptime_sec(),
        "intel": intel_snapshot(),
    }


def _uptime_sec() -> float:
    try:
        return float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError, IndexError):
        return 0.0


def _is_protected(cmd: str) -> bool:
    return any(m in cmd for m in _PROTECTED)


def kill_process(pid: int, *, sig: int = 15, force: bool = False) -> dict[str, Any]:
    try:
        pid_i = int(pid)
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_pid"}
    if pid_i <= 1:
        return {"ok": False, "error": "protected_pid"}
    cmd = ""
    try:
        cmd = Path(f"/proc/{pid_i}/cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
    except OSError:
        return {"ok": False, "error": "process_not_found"}
    if _is_protected(cmd) and not force:
        return {"ok": False, "error": "protected_field_process", "cmd": cmd[:120]}
    try:
        os.kill(pid_i, sig)
        return {"ok": True, "pid": pid_i, "signal": sig, "terminated": sig in (signal.SIGKILL, signal.SIGTERM, 15, 9)}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "pid": pid_i}


def terminate_service(service_id: str) -> dict[str, Any]:
    """Best-effort terminate field service by id — sends SIGTERM to listener on port."""
    svc = next((s for s in _FIELD_SERVICES if s["id"] == service_id), None)
    if not svc:
        return {"ok": False, "error": "unknown_service"}
    port = int(svc["port"])
    pids: list[int] = []
    try:
        proc = subprocess.run(
            ["ss", "-ltnp", f"sport = :{port}"],
            capture_output=True,
            text=True,
            timeout=6,
        )
        for line in (proc.stdout or "").splitlines():
            if "pid=" not in line:
                continue
            chunk = line.split("pid=", 1)[1]
            pid_s = chunk.split(",", 1)[0]
            try:
                pids.append(int(pid_s))
            except ValueError:
                pass
    except (OSError, subprocess.TimeoutExpired):
        pass
    if not pids:
        return {"ok": False, "error": "no_listener", "service": service_id, "port": port}
    results = []
    for pid in pids:
        results.append(kill_process(pid, sig=15))
    return {"ok": any(r.get("ok") for r in results), "service": service_id, "results": results}


def handle_action(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "").lower()
    if action == "kill":
        sig = 9 if str(body.get("force") or body.get("kill")) in ("1", "true", "yes", "kill") else 15
        return kill_process(int(body.get("pid") or 0), sig=sig, force=bool(body.get("force_field")))
    if action == "terminate":
        return terminate_service(str(body.get("service") or ""))
    if action == "processes":
        return {"ok": True, "processes": list_processes(limit=int(body.get("limit") or 120))}
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    import sys
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "snapshot", "status"):
        print(json.dumps(snapshot(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "processes":
        print(json.dumps({"ok": True, "processes": list_processes()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "services":
        print(json.dumps({"ok": True, "services": field_services()}, ensure_ascii=False, indent=2))
        return 0
    if cmd == "intel":
        print(json.dumps(intel_snapshot(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "kill" and len(sys.argv) > 2:
        sig = 9 if "--force" in sys.argv else 15
        print(json.dumps(kill_process(int(sys.argv[2]), sig=sig), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["json", "processes", "services", "kill PID"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())