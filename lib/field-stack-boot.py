#!/usr/bin/env python3
"""Phased field stack boot — NEXUS C2 → KILROY → KILROY iPXE → AmmoOS → stop."""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-stack-boot-doctrine.json"
PANEL = STATE / "field-stack-boot-panel.json"
LEDGER = STATE / "field-stack-boot-ledger.jsonl"
LOOPBACK = os.environ.get("NEXUS_LOOPBACK", "127.0.0.1")
C2_PORT = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477") or "9477")


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
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": _utc(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _port_up(port: int) -> bool:
    try:
        with socket.create_connection((LOOPBACK, port), timeout=0.4):
            return True
    except OSError:
        return False


def _http_ok(url: str, timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return 200 <= resp.status < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _run_json(rel: str, args: list[str], *, timeout: int = 120) -> dict[str, Any]:
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
    return {"ok": proc.returncode == 0, "rc": proc.returncode}


def _run_bash(rel: str, fn: str, *, timeout: int = 60) -> dict[str, Any]:
    sh = INSTALL / rel
    if not sh.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    try:
        proc = subprocess.run(
            ["bash", "-c", f"source '{sh}' && {fn}"],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
        return {"ok": proc.returncode == 0, "rc": proc.returncode, "stderr": (proc.stderr or "")[:200]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)[:160]}


def _ensure_c2_panel() -> dict[str, Any]:
    if _port_up(C2_PORT) and _http_ok(f"http://{LOOPBACK}:{C2_PORT}/field"):
        return {"ok": True, "already_up": True, "port": C2_PORT}
    sk = INSTALL / "lib" / "field-grok-spawner-kill.py"
    if sk.is_file():
        out = _run_json("lib/field-grok-spawner-kill.py", ["stack"], timeout=90)
        if _port_up(C2_PORT):
            return {"ok": True, "via": "spawner_stack", "port": C2_PORT, "stack": out}
    panel_py = INSTALL / "lib" / "threat-panel-http.py"
    if panel_py.is_file():
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    str(panel_py),
                    str(C2_PORT),
                    str(INSTALL / "panel"),
                    str(STATE / "threat-panel.json"),
                ],
                cwd=str(INSTALL),
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except OSError as exc:
            return {"ok": False, "error": str(exc)[:160]}
        for _ in range(24):
            if _port_up(C2_PORT):
                return {"ok": True, "restarted": True, "port": C2_PORT}
    return {"ok": False, "error": "c2_unavailable", "port": C2_PORT}


def _stage_nexus_c2() -> dict[str, Any]:
    panel = _ensure_c2_panel()
    dns = _run_json("lib/field-dns-dhcp-fix.py", ["dns"], timeout=90)
    harden = _run_json("lib/field-war-hardening.py", ["stamp"], timeout=60)
    gate = _run_json("lib/connection-gatekeeper.py", ["json"], timeout=25)
    ok = bool(panel.get("ok")) and bool(dns.get("healthy") or dns.get("dns_healthy") or dns.get("ok"))
    return {
        "ok": ok,
        "stage": "nexus_c2",
        "panel": panel,
        "dns": dns,
        "hardening": harden,
        "gatekeeper": gate,
        "field_up": _http_ok(f"http://{LOOPBACK}:{C2_PORT}/field"),
    }


def _stage_kilroy() -> dict[str, Any]:
    core = _run_bash("lib/kilroy-core.sh", "nexus_kilroy_core_board", timeout=45)
    boot = _run_json("lib/kilroy-boot-services.py", ["boot"], timeout=90)
    marker = _load(STATE / "kilroy-core.json", {})
    ok = bool(core.get("ok")) or bool(marker) or bool(boot.get("ok"))
    return {"ok": ok, "stage": "kilroy", "core": core, "boot_services": boot, "marker": bool(marker)}


def _stage_kilroy_ipxe() -> dict[str, Any]:
    ping = _run_json("lib/field-ping.py", ["json"], timeout=30)
    lane = {
        "schema": "kilroy-ipxe-lane/v1",
        "updated": _utc(),
        "active": True,
        "lineage": "KILROY iPXE ping_cmd.c",
        "module": "lib/field-ping.py",
        "netboot_lane": True,
    }
    _save(STATE / "kilroy-ipxe-lane.json", lane)
    ok = bool(ping.get("ok", True)) or lane.get("active")
    return {"ok": ok, "stage": "kilroy_ipxe", "ping": ping, "lane": lane}


def _stage_ammoos() -> dict[str, Any]:
    desktop = _http_ok(f"http://{LOOPBACK}:{C2_PORT}/field")
    if not desktop:
        open_py = INSTALL / "lib" / "field-queen-browser-open.py"
        if open_py.is_file():
            _run_json("lib/field-queen-browser-open.py", ["desktop"], timeout=45)
        desktop = _http_ok(f"http://{LOOPBACK}:{C2_PORT}/field")
    never = _run_json("lib/field-never-down.py", ["ensure"], timeout=45)
    return {
        "ok": desktop,
        "stage": "ammoos_desktop",
        "desktop_up": desktop,
        "url": f"http://{LOOPBACK}:{C2_PORT}/field",
        "never_down": never,
        "stop": True,
    }


STAGES: list[tuple[str, Callable[[], dict[str, Any]]]] = [
    ("nexus_c2", _stage_nexus_c2),
    ("kilroy", _stage_kilroy),
    ("kilroy_ipxe", _stage_kilroy_ipxe),
    ("ammoos_desktop", _stage_ammoos),
]


def boot_stack(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    results: list[dict[str, Any]] = []
    stopped_at = ""
    all_ok = True
    for sid, fn in STAGES:
        row = fn()
        row["id"] = sid
        results.append(row)
        if not row.get("ok"):
            all_ok = False
        stopped_at = sid
        if row.get("stop"):
            break
    out = {
        "ok": all_ok,
        "schema": "field-stack-boot/v1",
        "updated": _utc(),
        "motto": doctrine.get("motto"),
        "boot_order": [s[0] for s in STAGES],
        "stopped_at": stopped_at,
        "queen_browser": "on_demand_window_icon",
        "stages": results,
        "surfaces": {
            "nexus_c2": f"http://{LOOPBACK}:{C2_PORT}/field",
            "queen_browser": f"http://{LOOPBACK}:9481/world/browser.html",
        },
        "api": "/api/field-stack-boot",
    }
    if write:
        _save(PANEL, out)
        _append_ledger({"event": "boot_stack", "stopped_at": stopped_at, "ok": all_ok})
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "boot").strip().lower().replace("-", "_")
    if action in ("boot", "stack", "run", "json", "status"):
        return boot_stack(write=bool(body.get("write", True)))
    if action == "stages":
        return {"ok": True, "stages": [s[0] for s in STAGES], "doctrine": _load(DOCTRINE, {})}
    return {"ok": False, "error": "unknown_action", "actions": ["boot", "stages", "status"]}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "boot").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("boot", "stack", "json"):
        print(json.dumps(boot_stack(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-stack-boot.py [boot|dispatch]"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())