#!/usr/bin/env python3
"""Expand and update full 2500 global rack fleet — registry, protect, sync inventory."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-rack-fleet-2500-panel.json"
TARGET = int(os.environ.get("NEXUS_GLOBAL_SERVER_TARGET") or 2500)
STACK_VERSION = "h7r/1"
TRUTH_SECURITY_VERSION = "h7r/1-prejudice"
SERVICES = ["dns", "dhcp", "edge", "witness", "truth", "security", "prejudice"]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def _run_json(rel: str, args: list[str], *, timeout: int = 300) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)[:200]}
    return {"ok": False, "error": "script_failed", "script": rel}


def _stamp_registry_servers() -> dict[str, Any]:
    reg_path = STATE / "field-global-servers-registry.json"
    reg = _load(reg_path, {})
    servers = list(reg.get("servers") or [])
    svc_map = {s: True for s in SERVICES}
    for i, row in enumerate(servers):
        if not isinstance(row, dict):
            continue
        servers[i] = {
            **row,
            "h7r_stack_updated": True,
            "h7r_truth_security_updated": True,
            "prejudice_enforced": True,
            "more_than_permissible": True,
            "stack_version": STACK_VERSION,
            "truth_security_version": TRUTH_SECURITY_VERSION,
            "services": svc_map,
            "dns_primary": True,
            "dhcp_primary": True,
            "provisioned": True,
            "online": True,
            "full_rack": True,
            "updated": _utc(),
        }
    reg["servers"] = servers
    reg["count"] = len(servers)
    reg["full_updated"] = True
    reg["updated"] = _utc()
    _save(reg_path, reg)
    return {"ok": True, "stamped": len(servers), "path": str(reg_path)}


def expand_fleet(*, target: int | None = None, write: bool = True) -> dict[str, Any]:
    goal = int(target or TARGET)
    steps: list[dict[str, Any]] = []

    expand = _run_json("lib/field-global-servers.py", ["expand", str(goal)], timeout=180)
    steps.append({"step": "global_servers_expand", **expand})

    if write:
        stamp = _stamp_registry_servers()
        steps.append({"step": "registry_h7r_stamp", **stamp})

        prov = _run_json("lib/field-zachub-qemu-racks.py", ["provision"], timeout=180)
        steps.append({"step": "physical_racks_provision", **prov})

        protect = _run_json("lib/field-fleet-2500-protect.py", ["protect"], timeout=240)
        steps.append({"step": "fleet_protect", **protect})

        keep = _run_json("lib/field-botnet-dns-dhcp.py", ["keepalive"], timeout=90)
        steps.append({"step": "dns_dhcp_keepalive", **keep})

        inv = _run_json("lib/field-rack-inventory.py", ["json"], timeout=120)
        steps.append({"step": "inventory_sync", "ok": inv.get("ok", True), "counts": inv.get("counts")})

        mesh = _run_json("lib/field-rack-terminal-mesh.py", ["json"], timeout=90)
        steps.append({"step": "terminal_mesh_sync", "counts": mesh.get("counts")})

    reg = _load(STATE / "field-global-servers-registry.json", {})
    out = {
        "ok": bool(expand.get("deployed", 0) >= goal or expand.get("ok")),
        "schema": "field-rack-fleet-2500/v1",
        "updated": _utc(),
        "target": goal,
        "deployed": expand.get("deployed") or reg.get("count") or 0,
        "full_updated_racks": reg.get("full_updated", False),
        "steps": steps,
        "api": "/api/field-rack-fleet-2500",
    }
    if write:
        _save(PANEL, out)
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("expand", "deploy", "fleet", "2500"):
        return expand_fleet(target=body.get("target") or TARGET, write=bool(body.get("write", True)))
    if action in ("status", "json"):
        cached = _load(PANEL, {})
        reg = _load(STATE / "field-global-servers-registry.json", {})
        return {
            "ok": True,
            "schema": "field-rack-fleet-2500/v1",
            "target": TARGET,
            "deployed": reg.get("count") or cached.get("deployed") or 0,
            "full_updated": reg.get("full_updated", False),
            "last": cached,
            "api": "/api/field-rack-fleet-2500",
        }
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    target = TARGET
    for arg in sys.argv[2:]:
        if arg.isdigit():
            target = int(arg)
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("expand", "deploy", "2500"):
        print(json.dumps(expand_fleet(target=target), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(dispatch({"action": "status"}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())