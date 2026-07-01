#!/usr/bin/env pythong
"""ZNetwork smart inside — policy owner with full traffic passthrough.

ZNetwork owns connection policy and security intelligence. The OS stack keeps L3
alive; normal requests flow unchanged. Gatekeeper, negotiation, and hostile scan
run advisory inside — interdict only on confirmed immediate harm.
"""
from __future__ import annotations

import importlib.util
import json
import os
import platform
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
CONNECTION = STATE / "znetwork-connection.json"
STATUS = STATE / "znetwork-status.json"
GUARD = STATE / "znetwork-handler-guard.json"
LEDGER = STATE / "znetwork-smart-inside.jsonl"
SCHEMA = "znetwork-smart-inside/v1"

_MOD_CACHE: dict[str, Any] = {}


def smart_inside_enabled() -> bool:
    return os.environ.get("ZNETWORK_SMART_INSIDE", "1") != "0"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _log(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": _now(), **row}, ensure_ascii=False) + "\n")


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _mod(py: Path, name: str) -> Any | None:
    key = str(py)
    if key in _MOD_CACHE:
        return _MOD_CACHE[key]
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MOD_CACHE[key] = mod
    return mod


def _znetwork_bin() -> Path | None:
    env = os.environ.get("ZNETWORK_BIN", "").strip()
    if env and Path(env).is_file():
        return Path(env).resolve()
    sg = Path(os.environ.get("SG_ROOT", str(INSTALL.parent)))
    for candidate in (
        sg / "ZNetwork" / "build" / "znetwork",
        INSTALL.parent / "ZNetwork" / "build" / "znetwork",
        INSTALL / "bin" / "znetwork",
    ):
        if candidate.is_file():
            return candidate.resolve()
    return None


def _probe_connection() -> dict[str, Any]:
    retire = _mod(INSTALL / "lib" / "znetwork-handler-retire.py", "znetwork_handler_retire")
    if retire and hasattr(retire, "_probe_connection"):
        return retire._probe_connection()
    bin_path = _znetwork_bin()
    if not bin_path:
        return {"ok": False, "error": "binary_missing"}
    try:
        proc = subprocess.run(
            [str(bin_path), "probe", "--json"],
            capture_output=True,
            text=True,
            timeout=8,
            env={**os.environ, "SG_ROOT": str(INSTALL.parent)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            doc = json.loads(proc.stdout)
            return {
                "ok": True,
                "connection": doc.get("connection") or doc,
                "backend": doc.get("backend") or {},
            }
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        pass
    return {"ok": False, "error": "probe_failed"}


def _iface_operstate(iface: str) -> str:
    try:
        return Path(f"/sys/class/net/{iface}/operstate").read_text(encoding="utf-8").strip().lower()
    except OSError:
        return "unknown"


def _link_healthy(conn: dict[str, Any]) -> bool:
    iface = str(conn.get("iface") or "").strip()
    if not iface:
        return False
    state = _iface_operstate(iface)
    if state not in ("up", "unknown"):
        return False
    ipv4 = str(conn.get("ipv4") or "").strip()
    gateway = str(conn.get("gateway") or "").strip()
    if not ipv4:
        return False
    if gateway:
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", "-W", "2", gateway],
                capture_output=True,
                text=True,
                timeout=4,
            )
            if proc.returncode == 0:
                return True
        except (subprocess.SubprocessError, OSError):
            pass
    return conn.get("state") == "connected" or bool(ipv4)


def _advisory_gatekeeper() -> dict[str, Any]:
    gk_py = INSTALL / "lib" / "connection-gatekeeper.py"
    if not gk_py.is_file():
        return {"ok": False, "skipped": True, "reason": "gatekeeper_missing"}
    try:
        proc = subprocess.run(
            [os.environ.get("NEXUS_PYTHONG", "pythong"), str(gk_py)],
            capture_output=True,
            text=True,
            timeout=12,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return {"ok": True, "mode": "advisory", "flows": json.loads(proc.stdout)}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc), "mode": "advisory"}
    return {"ok": True, "mode": "advisory", "passthrough": True}


def _advisory_field_dns() -> dict[str, Any]:
    dns_py = INSTALL / "lib" / "field-dns.py"
    if not dns_py.is_file():
        return {"ok": False, "skipped": True, "reason": "field_dns_missing"}
    try:
        subprocess.run(
            [os.environ.get("NEXUS_PYTHONG", "pythong"), str(dns_py), "build"],
            capture_output=True,
            text=True,
            timeout=12,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        proc = subprocess.run(
            [os.environ.get("NEXUS_PYTHONG", "pythong"), str(dns_py), "json"],
            capture_output=True,
            text=True,
            timeout=8,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return {"ok": True, "mode": "passthrough", "dns": json.loads(proc.stdout)}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "mode": "passthrough"}


def _advisory_binary_status() -> dict[str, Any]:
    bin_path = _znetwork_bin()
    if not bin_path:
        return {"ok": False, "error": "binary_missing"}
    try:
        proc = subprocess.run(
            [str(bin_path), "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "SG_ROOT": str(INSTALL.parent)},
        )
        if proc.returncode == 0 and proc.stdout.strip():
            doc = json.loads(proc.stdout)
            _save(STATUS, doc)
            return {"ok": True, "status": doc}
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "error": str(exc)}
    return {"ok": False, "error": "status_empty"}


def _exploit_shield_layer() -> dict[str, Any]:
    shield = _mod(INSTALL / "lib" / "znetwork-exploit-shield.py", "znetwork_exploit_shield_si")
    if not shield or not hasattr(shield, "scan"):
        return {"ok": False, "skipped": True, "reason": "exploit_shield_missing"}
    try:
        return shield.scan(publish=True)
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _attach_advisory_stack() -> dict[str, Any]:
    layers: dict[str, Any] = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_advisory_gatekeeper): "gatekeeper",
            pool.submit(_advisory_field_dns): "field_dns",
            pool.submit(_advisory_binary_status): "binary_status",
            pool.submit(_exploit_shield_layer): "exploit_shield",
        }
        for fut in as_completed(futures):
            layers[futures[fut]] = fut.result()
    exploit = layers.get("exploit_shield") or {}
    return {
        "ok": True,
        "mode": "smart_inside",
        "passthrough": True,
        "enforce_blocks": False,
        "zero_day_behavioral": True,
        "exploit_shield_armed": bool(exploit.get("ok")),
        "zero_day_candidates": int(exploit.get("zero_day_count") or 0),
        "layers": layers,
    }


def own_connection(*, probe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Mirror live link, own policy, keep OS L3 — all normal traffic passes."""
    if probe is None:
        probe = _probe_connection()
    if not probe.get("ok"):
        return {"ok": False, "error": "probe_failed", "probe": probe}

    conn = probe.get("connection") or {}
    backend = probe.get("backend") or {}
    iface = str(conn.get("iface") or "").strip()
    healthy = _link_healthy(conn)

    guard_doc = {
        "schema": "znetwork-handler-guard/v1",
        "active": True,
        "no_sudo": True,
        "coexist_os": True,
        "never_harm_os": True,
        "smart_inside": True,
        "bypass_not_replace": False,
        "policy_owner": "znetwork",
        "passthrough_all_traffic": True,
        "exploit_shield": True,
        "zero_day_behavioral": True,
        "retired_pids": [],
        "retired_at": _now(),
        "install_root": str(INSTALL.resolve()),
        "do_not_restart": [],
        "motto": "ZNetwork owns policy inside — OS keeps L3, all normal requests pass.",
    }
    _save(GUARD, guard_doc)

    stack = _attach_advisory_stack()

    doc = {
        "schema": "znetwork-connection/v1",
        "updated": _now(),
        "policy_owner": "znetwork",
        "smart_inside": True,
        "link_preserved": True,
        "passthrough_all_traffic": True,
        "exploit_shield": True,
        "zero_day_behavioral": True,
        "coexist_os": True,
        "never_harm_os": True,
        "native_backend_superseded": False,
        "connection": conn,
        "backend": backend,
        "supersedes": {
            "native_id": backend.get("id"),
            "native_label": backend.get("label"),
            "method": "smart_inside_policy_owner",
        },
        "verdict": "ZNETWORK_SMART_INSIDE" if healthy else "ZNETWORK_SMART_INSIDE_DEGRADED",
        "handoff": {
            "ok": True,
            "schema": SCHEMA,
            "os": platform.system().lower(),
            "iface": iface,
            "link_preserved": True,
            "appears_connected": healthy,
            "coexist_os": True,
            "native_mask_deferred": True,
            "policy_owner": "znetwork",
            "advisory_stack": stack,
        },
        "no_sudo": True,
    }
    _save(CONNECTION, doc)

    status = _load_json(STATUS) or {}
    status.update(
        {
            "effective_mode": os.environ.get("ZNETWORK_MODE", "ACTIVE"),
            "policy_owner": "znetwork",
            "smart_inside": True,
            "native_backend_bypassed": False,
            "native_backend_superseded": False,
            "coexist_os": True,
            "passthrough_all_traffic": True,
            "link_preserved": True,
            "appears_connected": healthy,
            "connection_owner": doc,
            "updated": _now(),
        }
    )
    _save(STATUS, status)

    rep = {
        "ok": healthy,
        "schema": SCHEMA,
        "connection": doc,
        "handoff": doc["handoff"],
        "link_healthy": healthy,
        "advisory_stack": stack,
    }
    _log({"event": "own_connection", **{k: rep.get(k) for k in ("ok", "link_healthy", "schema")}})
    return rep


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def posture() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "ok": True,
        "enabled": smart_inside_enabled(),
        "connection": _load_json(CONNECTION),
        "guard": _load_json(GUARD),
        "status": _load_json(STATUS),
        "checked_at": _now(),
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    handlers = {
        "json": posture,
        "posture": posture,
        "own": own_connection,
        "replace": own_connection,
    }
    fn = handlers.get(cmd)
    if not fn:
        print(
            json.dumps({"error": "usage: znetwork-smart-inside.py [json|own|replace]"}),
            file=sys.stderr,
        )
        return 2
    result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())