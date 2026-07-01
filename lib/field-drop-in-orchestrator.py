#!/usr/bin/env pythong
"""Forceful drop-in orchestrator — defield gate → WRDT redata → secure network → F9 Queen browser."""
from __future__ import annotations

import json
import os
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-drop-in-doctrine.json"
PANEL = STATE / "field-drop-in-orchestrator.json"
LOCK = STATE / "field-underlay-lock.json"
PHASES = ("force_drop_in", "defield_gate", "redata", "secure_network", "ready")


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



def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _run_py(script: str, *args: str, timeout: int = 120) -> dict[str, Any]:
    py = INSTALL / "lib" / script
    if not py.is_file():
        return {"ok": False, "error": "missing", "script": script}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "SG_ROOT": str(SG)}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc), "script": script}


def _defield_gate(*, full: bool = True) -> dict[str, Any]:
    panel = _load(STATE / "field-drive-converter-panel.json", {})
    drop = _load(PANEL, {})
    cached = drop.get("defield_audit") or panel.get("defield_audit") or {}
    if drop.get("defield_ok") is not None:
        cached = {**cached, "defield_ok": drop.get("defield_ok")}
    if panel.get("defield_ok") is not None:
        cached = {**cached, "defield_ok": panel.get("defield_ok")}
    if not full:
        if cached.get("defield_ok") is not None:
            return {**cached, "ok": bool(cached.get("defield_ok")), "cached": True}
        if cached.get("ok") is not None:
            return {**cached, "ok": bool(cached.get("ok")), "cached": True}
        return {"ok": False, "cached": False, "error": "no_cached_defield"}
    return _run_py("field-non-fielded-safety.py", "gate-convert", timeout=300)


def _phase_from_panel(panel: dict[str, Any]) -> str:
    if panel.get("ready"):
        return "ready"
    if panel.get("secure_network"):
        return "secure_network"
    if panel.get("redata_complete") or panel.get("wrdt_scanned"):
        return "redata"
    if panel.get("defield_ok"):
        return "defield_gate"
    if panel.get("force_drop_in"):
        return "force_drop_in"
    return "force_drop_in"


def board_panel(**updates: Any) -> dict[str, Any]:
    doc = _load(PANEL, {"schema": "field-drop-in-orchestrator/v1"})
    doc.update(updates)
    doc["updated"] = _now()
    doc["phase"] = _phase_from_panel(doc)
    _write_atomic(PANEL, doc)
    return doc


def _host_id() -> str:
    return socket.gethostname().split(".")[0] or "local"


def _device_registry() -> dict[str, Any]:
    reg = STATE / "field-device-registry.json"
    seed = INSTALL / "data" / "field-device-registry-seed.json"
    doc = _load(reg, _load(seed, {"schema": "field-device-registry/v1", "devices": []}))
    devices = list(doc.get("devices") or [])
    host = _host_id()
    found = False
    for dev in devices:
        if dev.get("self") or dev.get("id") in (host, "local"):
            dev.update({
                "id": host,
                "hostname": socket.gethostname(),
                "machine": platform.machine(),
                "panel_port": int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")),
                "queen_port": int(os.environ.get("QUEEN_WORLD_PORT", "9481")),
                "self": True,
                "last_seen": _now(),
            })
            found = True
            break
    if not found:
        devices.insert(0, {
            "id": host,
            "role": "primary",
            "display_name": "This host",
            "kind": "workstation",
            "hostname": socket.gethostname(),
            "machine": platform.machine(),
            "panel_port": int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")),
            "queen_port": int(os.environ.get("QUEEN_WORLD_PORT", "9481")),
            "self": True,
            "display_open": True,
            "drop_in": True,
            "last_seen": _now(),
        })
    doc["devices"] = devices
    doc["ts"] = _now()
    _write_atomic(reg, doc)
    return doc


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    panel = _load(PANEL, {})
    lock = _load(LOCK, {})
    defield = _defield_gate(full=False)
    protocol = _run_py("field-sovereign-protocol-bridge.py", "json", timeout=30)
    underlay = _run_py("field-underlay-switch.py", "json", timeout=25)
    devices = _device_registry()
    phase = panel.get("phase") or _phase_from_panel(panel)
    f9_target = "queen_sovereign_browser"
    if not defield.get("ok") and not lock.get("committed"):
        f9_target = doctrine.get("policy", {}).get("hotkey_pre_defield", "tristate_installer")
    elif not panel.get("secure_network") and not lock.get("committed"):
        f9_target = doctrine.get("policy", {}).get("hotkey_pre_defield", "tristate_installer")
    else:
        f9_target = doctrine.get("policy", {}).get("hotkey_post_secure", "queen_sovereign_browser")

    return {
        "schema": "field-drop-in-orchestrator/v1",
        "ts": _now(),
        "title": doctrine.get("title", ""),
        "motto": doctrine.get("motto", ""),
        "phase": phase,
        "phases": list(PHASES),
        "policy": doctrine.get("policy", {}),
        "panel": panel,
        "defield_audit": defield,
        "defield_ok": bool(defield.get("ok")),
        "secondary_fields": not bool(defield.get("ok")),
        "redata": {
            "scanned": bool(panel.get("wrdt_scanned")),
            "applied": bool(panel.get("redata_complete")),
            "plan": _load(STATE / "field-underlay-wrdt-plan.json", {}),
        },
        "secure_network": protocol,
        "secure_network_ready": bool(protocol.get("secured") or panel.get("secure_network")),
        "committed": bool(lock.get("committed")),
        "f9_target": f9_target,
        "f9_hotkey": doctrine.get("policy", {}).get("hotkey", "F9"),
        "browser": doctrine.get("browser", {}),
        "devices": devices,
        "underlay_phase": underlay.get("phase"),
        "api": "/api/drop-in-orchestrator",
    }


def force_drop_in(*, elevated: bool = False) -> dict[str, Any]:
    """Board forceful drop-in — NEXUS protections aboard, underlay marked."""
    underlay = _run_py("field-underlay.py", "board", timeout=30)
    switch = _run_py("field-underlay-switch.py", "mark-nexus", timeout=20)
    devices = _device_registry()
    panel = board_panel(
        force_drop_in=True,
        force_drop_in_at=_now(),
        underlay_boarded=underlay.get("verdict") in ("GREEN", "PARTIAL") or underlay.get("ok"),
        nexus_installed=True,
    )
    out = posture()
    out["ok"] = True
    out["action"] = "force_drop_in"
    out["underlay"] = underlay
    out["switch"] = switch
    out["devices"] = devices
    out["panel"] = panel
    return out


def poll_defield(*, max_wait_sec: float = 0.0) -> dict[str, Any]:
    """Poll defield gate until clean or timeout."""
    deadline = time.monotonic() + max(0.0, max_wait_sec)
    last: dict[str, Any] = {"ok": False}
    while True:
        last = _defield_gate(full=True)
        board_panel(defield_ok=bool(last.get("ok")), defield_audit=last)
        if last.get("ok"):
            break
        if max_wait_sec <= 0 or time.monotonic() >= deadline:
            break
        time.sleep(min(2.0, max_wait_sec))
    out = posture()
    out["ok"] = bool(last.get("ok"))
    out["defield_audit"] = last
    if not last.get("ok"):
        out["error"] = "secondary_fields_remain"
        out["doctrine"] = "Defield all WRDT/WRZC/ZAC/H7 tails before redata and secure network"
    return out


def run_redata(*, scan_only: bool = True, confirm: bool = False, elevated: bool = False) -> dict[str, Any]:
    defield = _defield_gate(full=True)
    if not defield.get("ok") and os.environ.get("NEXUS_DRIVE_CONVERTER_FORCE") != "1":
        return {
            "ok": False,
            "error": "defield_required",
            "defield_audit": defield,
            "posture": posture(),
        }
    scan = _run_py("field-underlay-switch.py", "scan-wrdt", timeout=360)
    panel = board_panel(wrdt_scanned=bool(scan.get("ok")), wrdt_scan=scan.get("wrdt_scan"))
    apply_rep: dict[str, Any] | None = None
    if not scan_only and confirm:
        if os.geteuid() != 0 and not elevated:
            return {"ok": False, "error": "admin_required", "action": "com.nexus.field.underlay", "scan": scan}
        apply_rep = _run_py("field-underlay-switch.py", "wrdt-apply", "--confirm", timeout=900)
        board_panel(redata_complete=bool(apply_rep.get("ok")))
    global_redata = _run_py("field-global-redata.py", "incremental", timeout=60)
    out = posture()
    out["ok"] = bool(scan.get("ok"))
    out["scan"] = scan
    out["apply"] = apply_rep
    out["global_redata"] = global_redata
    out["panel"] = panel
    return out


def secure_network(*, activate: bool = True) -> dict[str, Any]:
    defield = _defield_gate(full=True)
    if not defield.get("ok") and os.environ.get("NEXUS_SOVEREIGN_PROTOCOL_FORCE") != "1":
        return {
            "ok": False,
            "error": "defield_required",
            "defield_audit": defield,
            "posture": posture(),
        }
    verb = "activate" if activate else "json"
    bridge = _run_py("field-sovereign-protocol-bridge.py", verb, timeout=90)
    panel = board_panel(secure_network=bool(bridge.get("secured") or bridge.get("ok")), protocol_bridge=bridge)
    if bridge.get("secured") or bridge.get("ok"):
        board_panel(ready=True, ready_at=_now())
    out = posture()
    out["ok"] = bool(bridge.get("ok"))
    out["bridge"] = bridge
    out["panel"] = panel
    return out


def run_pipeline(*, redata_apply: bool = False, elevated: bool = False) -> dict[str, Any]:
    """Full drop-in pipeline: force → defield poll → redata scan → secure network."""
    steps: list[dict[str, Any]] = []

    def _step(name: str, fn: Callable[[], dict[str, Any]]) -> bool:
        rep = fn()
        steps.append({"step": name, "ok": rep.get("ok", True), "summary": rep})
        return bool(rep.get("ok", True))

    ok = True
    ok = _step("force_drop_in", lambda: force_drop_in(elevated=elevated)) and ok
    ok = _step("defield_gate", lambda: poll_defield(max_wait_sec=0.0)) and ok
    if ok or os.environ.get("NEXUS_DROP_IN_FORCE_REDATA") == "1":
        ok = _step(
            "redata_scan",
            lambda: run_redata(scan_only=not redata_apply, confirm=redata_apply, elevated=elevated),
        ) and ok
    if ok or os.environ.get("NEXUS_DROP_IN_FORCE_NET") == "1":
        ok = _step("secure_network", lambda: secure_network(activate=True)) and ok
    report = {
        "schema": "field-drop-in-pipeline/v1",
        "ts": _now(),
        "ok": ok and (steps[-1]["summary"] if steps else {}).get("panel", {}).get("ready", False)
        or _load(PANEL, {}).get("ready", False),
        "steps": steps,
        "posture": posture(),
    }
    _write_atomic(STATE / "field-drop-in-pipeline.json", report)
    return report


def f9_ready() -> bool:
    lock = _load(LOCK, {})
    if lock.get("committed"):
        return True
    panel = _load(PANEL, {})
    if panel.get("ready"):
        return True
    defield = _defield_gate(full=False)
    proto = _load(STATE / "field-sovereign-protocol-bridge.json", {})
    if not defield.get("ok"):
        return False
    return bool(panel.get("secure_network") or proto.get("secured"))


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    elevated = "--elevated" in sys.argv or os.environ.get("NEXUS_ELEVATED_ROOT") == "1"
    confirm = "--confirm" in sys.argv
    handlers = {
        "json": posture,
        "status": posture,
        "force": lambda: force_drop_in(elevated=elevated),
        "defield": lambda: poll_defield(max_wait_sec=float(os.environ.get("NEXUS_DEFIELD_POLL_SEC", "0"))),
        "redata": lambda: run_redata(scan_only=not confirm, confirm=confirm, elevated=elevated),
        "secure-network": lambda: secure_network(activate=True),
        "pipeline": lambda: run_pipeline(redata_apply=confirm, elevated=elevated),
        "f9-ready": lambda: {
            "ok": True,
            "ready": f9_ready(),
            "f9_target": "queen_sovereign_browser" if f9_ready() else "tristate_installer",
            "committed": bool(_load(LOCK, {}).get("committed")),
            "defield_ok": bool(_defield_gate(full=False).get("ok")),
        },
        "devices": _device_registry,
    }
    fn = handlers.get(mode)
    if not fn:
        print(
            "usage: field-drop-in-orchestrator.py [json|force|defield|redata|secure-network|pipeline|f9-ready|devices]",
            file=sys.stderr,
        )
        return 2
    result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())