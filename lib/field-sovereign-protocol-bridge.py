#!/usr/bin/env pythong
"""Sovereign protocol bridge — NEXUS-managed wire with legacy HTTP/DNS/TCP compat ears."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-drop-in-doctrine.json"
PANEL = STATE / "field-sovereign-protocol-bridge.json"

MANAGED = (
    {"id": "field_net", "role": "primary", "module": "connection-gatekeeper.py", "port": None},
    {"id": "znetwork_shadow", "role": "shadow_wire", "module": "znetwork-field.sh", "port": None},
    {"id": "sovereign_sync", "role": "time_truth", "module": "field-sovereign-sync.py", "port": None},
    {"id": "truth_dns", "role": "dns_authority", "module": "field-dns.py", "port": 53},
    {"id": "field_dhcp", "role": "dhcp_authority", "module": "field-dhcp.py", "port": 67},
)

LEGACY_SHIMS = (
    {"id": "http", "compat": "HTTP/1.1", "bridge": "gatekeeper_egress", "managed_by": "field_net"},
    {"id": "https", "compat": "TLS/HTTP2", "bridge": "gatekeeper_egress", "managed_by": "field_net"},
    {"id": "dns", "compat": "UDP/53", "bridge": "truth_dns_shim", "managed_by": "truth_dns"},
    {"id": "tcp", "compat": "TCP/IPv4+IPv6", "bridge": "gatekeeper_socket", "managed_by": "field_net"},
    {"id": "tls", "compat": "TLS1.2+", "bridge": "gatekeeper_egress", "managed_by": "field_net"},
    {"id": "websocket", "compat": "WS/WSS", "bridge": "gatekeeper_egress", "managed_by": "field_net"},
)


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


def _run_py(script: str, *args: str, timeout: int = 60) -> dict[str, Any]:
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
        raw = proc.stdout or "{}"
        return json.loads(raw) if raw.strip().startswith("{") else {"ok": proc.returncode == 0, "raw": raw[:300]}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc), "script": script}


def _gatekeeper_json() -> dict[str, Any]:
    py = INSTALL / "lib" / "connection-gatekeeper.py"
    if not py.is_file():
        return {"ok": False, "error": "gatekeeper_missing"}
    cached = STATE / "connection-gatekeeper-panel.json"
    if cached.is_file():
        doc = _load(cached, {})
        if doc:
            doc.setdefault("ok", True)
            return doc
    return _run_py("connection-gatekeeper.py", timeout=25)


def _port_listening(port: int, host: str = "127.0.0.1") -> bool:
    if port <= 0:
        return False
    try:
        with socket.create_connection((host, port), timeout=0.4):
            return True
    except OSError:
        return False


def _module_present(rel: str) -> bool:
    return (INSTALL / "lib" / rel).is_file()


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    gatekeeper = _gatekeeper_json()
    sovereign_sync = _run_py("field-sovereign-sync.py", "json", timeout=15) if _module_present("field-sovereign-sync.py") else {}
    znet_status = _load(STATE / "znetwork-status.json", {})
    znet_op = _load(STATE / "znetwork-operator.json", {})
    dns_live = _port_listening(53) or _load(STATE / "field-dns-panel.json", {}).get("running")
    dhcp_live = _port_listening(67) or _load(STATE / "field-dhcp-panel.json", {}).get("running")

    managed: list[dict[str, Any]] = []
    for proto in MANAGED:
        present = _module_present(proto["module"])
        live = present
        if proto["id"] == "field_net":
            live = bool(present and (gatekeeper.get("ok", True) or gatekeeper.get("connections") is not None or gatekeeper.get("schema")))
        elif proto["id"] == "znetwork_shadow":
            live = znet_op.get("choice") == "yes" or bool(znet_status)
        elif proto["id"] == "sovereign_sync":
            live = bool(sovereign_sync.get("ok") or sovereign_sync.get("sections"))
        elif proto["id"] == "truth_dns":
            live = bool(dns_live)
        elif proto["id"] == "field_dhcp":
            live = bool(dhcp_live)
        managed.append({**proto, "present": present, "live": live})

    legacy: list[dict[str, Any]] = []
    for shim in LEGACY_SHIMS:
        mgr = next((m for m in managed if m["id"] == shim["managed_by"]), None)
        legacy.append({
            **shim,
            "shim_live": bool(mgr and mgr.get("live")),
            "compat_ok": bool(mgr and mgr.get("present")),
        })

    managed_live = sum(1 for m in managed if m.get("live"))
    legacy_live = sum(1 for l in legacy if l.get("shim_live"))
    secured = managed_live >= 2 and legacy_live >= 2 and _module_present("connection-gatekeeper.py")

    return {
        "schema": "field-sovereign-protocol-bridge/v1",
        "ts": _now(),
        "title": "Sovereign protocol bridge",
        "motto": "Own wire first. Legacy ears open through gatekeeper — never raw guest egress.",
        "managed_protocols": managed,
        "legacy_compat": legacy,
        "gatekeeper": gatekeeper,
        "sovereign_sync": sovereign_sync,
        "znetwork": {"operator": znet_op, "status": znet_status},
        "managed_live": managed_live,
        "legacy_shims_live": legacy_live,
        "secured": secured,
        "policy": doctrine.get("protocols", {}),
        "api": "/api/sovereign-protocol",
    }


def activate() -> dict[str, Any]:
    """Bring managed protocols aboard and wire legacy shims through gatekeeper."""
    steps: list[dict[str, Any]] = []
    gk = _gatekeeper_json()
    steps.append({"step": "gatekeeper_live", "ok": gk.get("ok", True), "detail": gk})
    redata = _run_py("field-global-redata.py", "incremental", timeout=45)
    steps.append({"step": "global_redata", "ok": redata.get("ok", True), "detail": redata})
    if _module_present("field-sovereign-sync.py"):
        sync = _run_py("field-sovereign-sync.py", "json", timeout=20)
        steps.append({"step": "sovereign_sync", "ok": sync.get("ok", True), "detail": sync})
    doc = posture()
    doc["activated"] = True
    doc["activated_at"] = _now()
    doc["steps"] = steps
    doc["ok"] = bool(doc.get("secured"))
    _write_atomic(PANEL, doc)
    return doc


def main() -> int:
    mode = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if mode == "activate":
        result = activate()
    else:
        result = posture()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) or result.get("secured") else 1


if __name__ == "__main__":
    raise SystemExit(main())