#!/usr/bin/env pythong
"""Legacy open + secured connect — primary DNS/DHCP with Dreamcast modem and retro gear."""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-legacy-connect-doctrine.json"
PANEL = STATE / "field-legacy-connect-panel.json"
PPP_PEER = STATE / "dreamcast-modem.peer"
SCHEMA = "field-legacy-connect/v1"


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


def _env() -> dict[str, str]:
    return {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}


def _py(script: str, *args: str, timeout: int = 45) -> dict[str, Any]:
    path = INSTALL / "lib" / script
    if not path.is_file():
        return {"ok": False, "error": "missing", "script": script}
    py = os.environ.get("PYTHON", "python3")
    try:
        proc = subprocess.run(
            [py, str(path), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
            check=False,
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            out = json.loads(raw)
            out.setdefault("ok", proc.returncode == 0)
            return out
        return {"ok": proc.returncode == 0, "raw": raw[:400], "rc": proc.returncode}
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "script": script}


def doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def legacy_open_secured() -> bool:
    doc = doctrine()
    pol = doc.get("policy") or {}
    return bool(pol.get("legacy_open_secured", True))


def _serial_devices() -> list[dict[str, Any]]:
    doc = doctrine()
    dc = doc.get("dreamcast_modem") or {}
    dial = dc.get("dialup") or {}
    candidates = list(dial.get("serial_devices") or [])
    rows: list[dict[str, Any]] = []
    for dev in candidates:
        p = Path(dev)
        rows.append({"device": dev, "present": p.exists()})
    devroot = Path("/dev")
    for pat in ("ttyUSB*", "ttyACM*", "ttyS*"):
        for p in sorted(devroot.glob(pat)):
            if any(r["device"] == str(p) for r in rows):
                continue
            rows.append({"device": str(p), "present": True})
    return rows[:24]


def _write_ppp_peer() -> Path:
    doc = doctrine()
    dc = doc.get("dreamcast_modem") or {}
    dial = dc.get("dialup") or {}
    name = str(dial.get("pppd_peer") or "dreamcast-modem")
    serial = ""
    for row in _serial_devices():
        if row.get("present"):
            serial = str(row["device"])
            break
    retro = (doc.get("dhcp_legacy") or {}).get("retro_pool") or {}
    gateway = str(retro.get("gateway") or "192.168.47.1")
    text = (
        f"# {name} — Sega Dreamcast dial-up PPP peer (queen side)\n"
        f"# Connect null-modem or USB voice modem on {serial or '/dev/ttyUSB0'}\n"
        f"{serial or '/dev/ttyUSB0'}\n"
        "115200\n"
        "local\n"
        "noauth\n"
        "proxyarp\n"
        f"ms-dns {gateway}\n"
        "lcp-echo-interval 30\n"
        "lcp-echo-failure 4\n"
        "# NEXUS_FIELD_LEGACY_CONNECT=1\n"
    )
    PPP_PEER.write_text(text, encoding="utf-8")
    return PPP_PEER


def _takeover_phase() -> str:
    st = _load(STATE / "dns-takeover-state.json", {})
    return str(st.get("phase") or "observing")


def _apply_legacy_env() -> list[str]:
    doc = doctrine()
    applied: list[str] = []
    os.environ["NEXUS_FIELD_DNS_LEGACY_COMPAT"] = "1"
    os.environ["NEXUS_LEGACY_OPEN_SECURED"] = "1"
    applied.append("NEXUS_FIELD_DNS_LEGACY_COMPAT=1")
    applied.append("NEXUS_LEGACY_OPEN_SECURED=1")
    retro = (doc.get("dhcp_legacy") or {}).get("retro_pool") or {}
    if retro.get("start") and retro.get("end"):
        os.environ["NEXUS_FIELD_DHCP_LEGACY_POOL_START"] = str(retro["start"])
        os.environ["NEXUS_FIELD_DHCP_LEGACY_POOL_END"] = str(retro["end"])
        lease = int(retro.get("lease_seconds") or 86400)
        os.environ["NEXUS_FIELD_DHCP_LEGACY_LEASE"] = str(lease)
        applied.append(f"retro_pool={retro['start']}-{retro['end']}")
    gateway = str(retro.get("gateway") or "192.168.47.1")
    if gateway:
        os.environ["NEXUS_FIELD_DHCP_LEGACY_DNS_IPV4"] = gateway
        binds = os.environ.get("NEXUS_FIELD_DNS_BINDS_IPV4", "127.0.0.1")
        if gateway not in binds.split(","):
            os.environ["NEXUS_FIELD_DNS_BINDS_IPV4"] = f"{binds},{gateway}".strip(",")
        applied.append(f"legacy_lan_dns={gateway}")
    return applied


def ensure_primary(*, max_wait_sec: int = 90) -> dict[str, Any]:
    """Start Truth DNS + Field DHCP and promote takeover to primary."""
    doc = doctrine()
    steps: list[dict[str, Any]] = []
    env_applied = _apply_legacy_env()
    steps.append({"step": "legacy_env", "ok": True, "applied": env_applied})

    dns = _py("field-dns-resolve.py", "ensure", timeout=60)
    steps.append({"step": "truth_dns", "ok": bool(dns.get("truth_up") or dns.get("ok")), "detail": dns})

    dhcp_py = INSTALL / "lib" / "field-dhcp.py"
    if dhcp_py.is_file() and not _load(STATE / "field-dhcp.pid", ""):
        log = STATE / "field-dhcp-serve.log"
        try:
            with log.open("a", encoding="utf-8") as fh:
                subprocess.Popen(
                    [os.environ.get("PYTHON", "python3"), str(dhcp_py), "serve"],
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    env=_env(),
                    start_new_session=True,
                )
            steps.append({"step": "dhcp_serve", "ok": True})
        except OSError as exc:
            steps.append({"step": "dhcp_serve", "ok": False, "error": str(exc)})
    else:
        steps.append({"step": "dhcp_serve", "ok": True, "skipped": "already_running"})

    phase = _takeover_phase()
    deadline = time.monotonic() + max_wait_sec
    evals = 0
    while time.monotonic() < deadline:
        ev = _py("dns-service-takeover.py", "evaluate", timeout=25)
        evals += 1
        phase = str(ev.get("phase") or _takeover_phase())
        if phase == "primary":
            break
        time.sleep(2)

    if phase == "primary":
        _py("field-local-dns-connect.py", "connect", timeout=20)
        sh = INSTALL / "lib" / "field-dns.sh"
        if sh.is_file():
            try:
                subprocess.run(
                    ["bash", "-c", f'source "{sh}" && nexus_field_dns_enforce_resolv'],
                    timeout=15,
                    env=_env(),
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                pass

    peer = _write_ppp_peer()
    truth = _py("field-dns-resolve.py", "status", timeout=15)
    servers = _py("field-dns-drift-threat.py", "servers", timeout=30)
    bridge = _py("field-sovereign-protocol-bridge.py", "json", timeout=25)
    github_legacy = _py("field-github-legacy.py", "json", timeout=25)

    out = {
        "schema": SCHEMA,
        "ts": _utc(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "legacy_open_secured": legacy_open_secured(),
        "phase": phase,
        "primary": phase == "primary",
        "truth_up": bool(truth.get("truth_up")),
        "steps": steps,
        "takeover_evals": evals,
        "dreamcast_modem": {
            **(doc.get("dreamcast_modem") or {}),
            "serial_devices": _serial_devices(),
            "pppd_peer_path": str(peer),
        },
        "servers_updated": servers,
        "protocol_bridge": {
            "secured": bridge.get("secured"),
            "legacy_shims_live": bridge.get("legacy_shims_live"),
        },
        "github_legacy_open": github_legacy.get("github_open"),
        "ok": phase == "primary" and bool(truth.get("truth_up")),
        "api": doc.get("api") or "/api/field-legacy-connect",
    }
    _save(PANEL, out)
    return out


def panel(*, write: bool = True) -> dict[str, Any]:
    doc = doctrine()
    truth = _py("field-dns-resolve.py", "status", timeout=12)
    takeover = _py("dns-service-takeover.py", "json", timeout=12)
    dhcp = _load(STATE / "field-dhcp-panel.json", {})
    bridge = _py("field-sovereign-protocol-bridge.py", "json", timeout=20)
    out = {
        "schema": SCHEMA,
        "ts": _utc(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "legacy_open_secured": legacy_open_secured(),
        "policy": doc.get("policy") or {},
        "phase": takeover.get("phase") or _takeover_phase(),
        "primary": (takeover.get("phase") or "") == "primary",
        "truth_up": bool(truth.get("truth_up")),
        "dns_legacy": doc.get("dns_legacy") or {},
        "dhcp_legacy": doc.get("dhcp_legacy") or {},
        "dreamcast_modem": {
            **(doc.get("dreamcast_modem") or {}),
            "serial_devices": _serial_devices(),
            "pppd_peer_path": str(PPP_PEER) if PPP_PEER.is_file() else None,
        },
        "retro_ports": doc.get("retro_ports") or {},
        "dhcp_running": bool(dhcp.get("running")),
        "dhcp_may_serve": bool(dhcp.get("may_serve")),
        "protocol_bridge": bridge,
        "ok": legacy_open_secured() and bool(truth.get("truth_up") or bridge.get("secured")),
        "api": doc.get("api") or "/api/field-legacy-connect",
    }
    if write:
        _save(PANEL, out)
    return out


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ensure-primary":
        print(json.dumps(ensure_primary(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "legacy-open":
        print("1" if legacy_open_secured() else "0")
        return 0
    print(json.dumps({"error": "usage: field-legacy-connect.py [json|panel|ensure-primary|legacy-open]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())