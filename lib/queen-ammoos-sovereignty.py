#!/usr/bin/env pythong
"""AmmoOS sovereignty posture — Queen local control, ZNetwork 100% internet pipe, own drivers."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", str(ROOT)))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE_PATH = INSTALL / "data" / "queen-ammoos-sovereignty-doctrine.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _load_doctrine() -> dict[str, Any]:
    for path in (
        DOCTRINE_PATH,
        ROOT / "data" / "queen-ammoos-sovereignty-doctrine.json",
        INSTALL.parent / "data" / "queen-ammoos-sovereignty-doctrine.json",
    ):
        if path.is_file():
            doc = _load_json(path, {})
            if doc:
                return doc
    return {
        "schema": "queen-ammoos-sovereignty/v1",
        "product": "AmmoOS",
        "loopback_authority": "127.0.0.1",
        "policy": {"znetwork_internet_pipe_percent_target": 100},
    }


def _local_services_slice() -> dict[str, Any]:
    script = INSTALL / "lib" / "field-local-dns-connect.py"
    if not script.is_file():
        script = ROOT / "lib" / "field-local-dns-connect.py"
    if not script.is_file():
        return {"ok": False, "skipped": True}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_local_dns_connect_sov", script)
        if not spec or not spec.loader:
            return {"ok": False, "skipped": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "posture"):
            return mod.posture()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "skipped": True}


def _znetwork_slice() -> dict[str, Any]:
    op = _load_json(STATE / "znetwork-operator.json", {})
    status = _load_json(STATE / "znetwork-status.json", {})
    relayer = _load_json(STATE / "znetwork-relayer.json", {})
    choice = str(op.get("choice") or "").lower()
    mode = str(
        op.get("mode")
        or status.get("mode")
        or os.environ.get("ZNETWORK_MODE")
        or "ACTIVE"
    ).upper()
    relayer_on = (
        relayer.get("enabled") is True
        or relayer.get("active") is True
        or os.environ.get("ZNETWORK_RELAYER", "1") != "0"
    )
    protection_only = os.environ.get("ZNETWORK_PROTECTION_ONLY", "0") == "1"
    target = int(os.environ.get("ZNETWORK_INTERNET_PIPE_TARGET", "100") or "100")
    operator_yes = choice in ("", "yes") or choice != "skip"
    running = operator_yes and (
        op.get("running") is True
        or str(op.get("running", "")).lower() == "true"
        or (relayer_on and not protection_only)
    )
    if relayer_on and not protection_only:
        pipe = target
    else:
        pipe = 0
    return {
        "running": running,
        "mode": mode,
        "relayer_enabled": relayer_on,
        "internet_pipe_percent": min(100, max(0, pipe)),
        "internet_pipe_target": target,
        "sole_stack": True,
        "iface": status.get("iface") or status.get("interface") or "",
    }


def _stack_layers_slice() -> dict[str, Any]:
    # field-stack-layer imports this module for the ammoos layer — avoid reentrant deadlock.
    if os.environ.get("FIELD_STACK_LAYER_POSTURE") == "1":
        return {"ok": False, "skipped": True, "reason": "reentrant"}
    script = INSTALL / "lib" / "field-stack-layer.py"
    if not script.is_file():
        script = ROOT / "lib" / "field-stack-layer.py"
    if not script.is_file():
        return {"ok": False, "skipped": True}
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("field_stack_layer_sov", script)
        if not spec or not spec.loader:
            return {"ok": False, "skipped": True}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "posture"):
            return mod.posture()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "skipped": True}


def posture() -> dict[str, Any]:
    doc = _load_doctrine()
    policy = doc.get("policy") or {}
    zn = _znetwork_slice()
    target = int(policy.get("znetwork_internet_pipe_percent_target", 100) or 100)
    pipe = zn.get("internet_pipe_percent", 0)
    if policy.get("znetwork_always_full_pipe", True) and zn.get("relayer_enabled"):
        pipe = target
        zn["internet_pipe_percent"] = pipe
    stack = _stack_layers_slice()
    loopback = doc.get("loopback_authority") or "127.0.0.1"
    return {
        "schema": doc.get("schema") or "queen-ammoos-sovereignty/v2",
        "ok": True,
        "ts": _now(),
        "product": doc.get("product") or "AmmoOS",
        "container": doc.get("container") or "Queen Browser",
        "ammoos_inside_queen": bool(doc.get("ammoos_inside_queen", policy.get("ammoos_embedded_not_sibling", False))),
        "queen_standalone_browser": bool(doc.get("queen_standalone_browser", policy.get("queen_standalone_not_container", True))),
        "kilroy_znetwork_absorbed": bool(doc.get("kilroy_znetwork_absorbed", policy.get("znetwork_absorbed_in_kilroy", True))),
        "motto": doc.get("motto") or "",
        "loopback_authority": loopback,
        "layer_order": doc.get("layer_order") or ["hardware", "nexus_c2", "znetwork", "queen_canvas", "queen", "ammoos"],
        "local_only_control": bool(policy.get("queen_full_system_control_local", True)),
        "queen_underlying_browser": bool(policy.get("queen_underlying_browser", True)),
        "queen_defends_with_nexus": bool(policy.get("queen_defends_with_nexus", True)),
        "queen_defends_with_znetwork": bool(policy.get("queen_defends_with_znetwork", True)),
        "hardware_no_break": bool(policy.get("hardware_no_break", (doc.get("hardware") or {}).get("no_breaks", True))),
        "presume_sole_internet": bool(policy.get("presume_sole_internet", True)),
        "hardware_pipe_full": bool(policy.get("hardware_pipe_full", True)),
        "own_drivers": bool((doc.get("hardware") or {}).get("own_drivers", True)),
        "hardened_as_only_internet": bool(policy.get("hardened_as_only_internet", True)),
        "znetwork": zn,
        "local_services": _local_services_slice(),
        "stack_layers": stack,
        "internet_pipe_percent": pipe,
        "internet_pipe_target": target,
        "nexus_c2_url": (doc.get("nexus_c2") or {}).get("field") or f"http://{loopback}:9477/field",
        "c2_url": f"http://{loopback}:9477/field",
        "panel_url": f"http://{loopback}:9477/command",
        "queen_shell": (doc.get("queen") or {}).get("shell") or "/world/browser.html",
        "queen_url": f"http://{loopback}:9481/world/browser.html",
        "blessing": "God Bless",
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "posture", "status"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    print("usage: queen-ammoos-sovereignty.py [json]", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())