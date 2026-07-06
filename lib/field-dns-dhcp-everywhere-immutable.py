#!/usr/bin/env pythong
"""DNS and DHCP everywhere immutable — seal Truth DNS + Field DHCP always on."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-dns-dhcp-everywhere-immutable-doctrine.json"
PANEL = STATE / "field-dns-dhcp-everywhere-immutable-panel.json"
SIGNAL = STATE / "field-dns-dhcp-everywhere-immutable.signal.json"


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


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def field_one_hub() -> dict[str, Any]:
    doc = doctrine()
    hub = dict(doc.get("field_one_hub") or {})
    one_doc = _load(INSTALL / "data" / "field-one-doctrine.json", {})
    if not hub and one_doc.get("hub"):
        hub = dict(one_doc["hub"])
    hub.setdefault("id", "field-1")
    hub.setdefault("label", "Field One")
    hub.setdefault("dns", ["127.0.0.1", "192.168.47.1"])
    hub.setdefault("dhcp", ["192.168.47.1", "0.0.0.0"])
    hub.setdefault("truth", "127.0.0.1")
    hub.setdefault("loopback", "127.0.0.1")
    hub.setdefault("queen_lan", "192.168.47.1")
    return hub


def _run_py(rel: str, args: list[str], *, timeout: float = 45.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "skipped": rel}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
    except Exception:
        pass
    return {"ok": False, "script": rel}


def env_lock() -> dict[str, str]:
    doc = doctrine()
    lock = dict((doc.get("env_lock") or {}))
    lock.setdefault("NEXUS_FIELD_DNS", "1")
    lock.setdefault("NEXUS_FIELD_DHCP", "1")
    lock.setdefault("NEXUS_FIELD_LOCAL_DNS_CONNECT", "1")
    lock.setdefault("NEXUS_LEGACY_OPEN_SECURED", "1")
    lock.setdefault("NEXUS_ALWAYS_FIELD_ONE", "1")
    lock.setdefault("NEXUS_NEVER_DOWN", "1")
    return {str(k): str(v) for k, v in lock.items()}


def sealed() -> bool:
    sig = _load(SIGNAL, {})
    if sig.get("immutable_everywhere") is True:
        return True
    policy = doctrine().get("policy") or {}
    return bool(policy.get("immutable_everywhere", True))


def apply_env_lock() -> dict[str, str]:
    """Force immutable DNS/DHCP env in-process — ignores disable attempts."""
    applied: dict[str, str] = {}
    for key, value in env_lock().items():
        os.environ[key] = value
        applied[key] = value
    return applied


def seal(*, write: bool = True) -> dict[str, Any]:
    """Seal DNS + DHCP everywhere immutable — always Field One hub + env lock."""
    doc = doctrine()
    policy = doc.get("policy") or {}
    applied = apply_env_lock()
    hub = field_one_hub()
    fast = os.environ.get("NEXUS_DNS_DHCP_SEAL_FAST", "0").strip().lower() in ("1", "true", "yes", "on")
    absorb_timeout = 8.0 if fast else 60.0
    never_timeout = 6.0 if fast else 45.0
    field_one_absorb = _run_py("lib/field-one.py", ["absorb"], timeout=absorb_timeout)
    never_down = _run_py("lib/field-never-down.py", ["ensure"], timeout=never_timeout)
    out = {
        "ok": True,
        "schema": "field-dns-dhcp-everywhere-immutable/v1",
        "updated": _utc(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "immutable_everywhere": True,
        "always_field_one": True,
        "field_one": True,
        "field_one_hub": hub,
        "field_one_sink": policy.get("field_one_sink", "field-1"),
        "dns_always_on": bool(policy.get("dns_always_on", True)),
        "dhcp_always_on": bool(policy.get("dhcp_always_on", True)),
        "route_all_dns_to_field_one": bool(policy.get("route_all_dns_to_field_one", True)),
        "route_all_dhcp_to_field_one": bool(policy.get("route_all_dhcp_to_field_one", True)),
        "env_applied": applied,
        "field_one_absorb": {
            "ok": bool(field_one_absorb.get("ok")),
            "outside_network_absorbed": field_one_absorb.get("outside_network_absorbed"),
            "connected_devices": field_one_absorb.get("connected_devices"),
            "field_one_sink": field_one_absorb.get("field_one_sink", "field-1"),
        },
        "never_down": {
            "ok": bool(never_down.get("ok")),
            "always_field_one": never_down.get("always_field_one", True),
            "instantiated": never_down.get("instantiated"),
        },
        "api": doc.get("api", "/api/field-dns-dhcp-everywhere-immutable"),
        "pages_api": doc.get("pages_api", "/api/field-dns-dhcp-everywhere-immutable.json"),
    }
    if write:
        stamp = {**out, "sealed": True, "signal": "always_field_one_immutable_dns_dhcp"}
        _save(SIGNAL, stamp)
        _save(PANEL, out)
        api = INSTALL / "Hostess7" / "docs" / "api" / "field-dns-dhcp-everywhere-immutable.json"
        if api.parent.is_dir():
            _save(api, out)
    return out


def panel(*, write: bool = False) -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "field-dns-dhcp-everywhere-immutable/v1":
        cached["updated"] = _utc()
        cached["immutable_everywhere"] = True
        if write:
            _save(PANEL, cached)
        return cached
    return seal(write=write)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("seal", "lock", "enforce"):
        print(json.dumps(seal(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "apply-env":
        print(json.dumps({"ok": True, "env_applied": apply_env_lock()}, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-dns-dhcp-everywhere-immutable.py [seal|json|panel|apply-env]",
        "motto": "DNS and DHCP everywhere immutable",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())