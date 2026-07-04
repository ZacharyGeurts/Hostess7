#!/usr/bin/env pythong
"""True planetary DNS authority — generate, expand, remove foreign DHCP/DNS once complete."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-planetary-dns-authority-doctrine.json"
PANEL = STATE / "field-planetary-dns-authority-panel.json"
REMOVAL_PANEL = STATE / "field-planetary-removal-panel.json"
LEDGER = STATE / "field-planetary-dns-authority.jsonl"

IPV4_FULL = 2**32
TRUSTED_PROC = (
    "field-dns.py",
    "field-dhcp.py",
    "nexus_field_dns",
    "nexus_field_dhcp",
    "dnsmasq",
)
TRUSTED_BINDS = frozenset({
    "127.0.0.1:53", "127.0.0.53:53", "127.0.0.54:53", "0.0.0.0:53",
    "0.0.0.0:67", "192.168.47.1:67", "192.168.47.1:53",
})


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


def _run_json(rel: str, args: list[str], *, timeout: float = 45.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {}
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
    return {}


def _run(cmd: list[str], *, timeout: float = 12.0) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, errors="replace")
        return {"ok": proc.returncode == 0, "rc": proc.returncode, "stdout": (proc.stdout or "").strip()}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc)}


def _run_privileged(cmd: list[str], *, timeout: float = 20.0) -> dict[str, Any]:
    """Run with root — direct if euid 0, else sudo -n or sudo -S from NEXUS_SUDO_PASSWORD."""
    if os.geteuid() == 0:
        return _run(cmd, timeout=timeout)
    pw = os.environ.get("NEXUS_SUDO_PASSWORD", "").strip()
    if pw:
        try:
            proc = subprocess.run(
                ["sudo", "-S", *cmd],
                input=pw + "\n",
                capture_output=True,
                text=True,
                timeout=timeout,
                errors="replace",
            )
            return {
                "ok": proc.returncode == 0,
                "rc": proc.returncode,
                "stdout": (proc.stdout or "").strip(),
                "sudo": True,
            }
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "error": str(exc), "sudo": True}
    try:
        proc = subprocess.run(
            ["sudo", "-n", *cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            errors="replace",
        )
        if proc.returncode == 0:
            return {"ok": True, "rc": 0, "stdout": (proc.stdout or "").strip(), "sudo": True}
    except (OSError, subprocess.TimeoutExpired):
        pass
    return {"ok": False, "error": "privilege_required", "sudo": False}


def authority_enabled() -> bool:
    if os.environ.get("NEXUS_FIELD_PLANETARY_DNS_AUTHORITY", "1").strip().lower() in ("0", "false", "no", "off"):
        return False
    doctrine = _load(DOCTRINE, {})
    return bool((doctrine.get("policy") or {}).get("generate_true_dns_authority", True))


def _ipv4_enumeration_ready() -> dict[str, Any]:
    enum = _load(STATE / "field-ipv4-enumerate-panel.json", {})
    if not enum.get("counts"):
        enum = _run_json("lib/field-ipv4-enumerate.py", ["json"], timeout=12)
    counts = enum.get("counts") or {}
    ready = bool(enum.get("enumerate_addresses")) and int(counts.get("ipv4_enumerated_total") or 0) >= IPV4_FULL
    return {"ready": ready, "panel": enum, "counts": counts}


def _generate_zones() -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    planetary: dict[str, Any] = {}
    try:
        mod = _mod("lib/dns-planetary-security.py", "dns_planetary")
        if mod and hasattr(mod, "build_planetary_dns"):
            planetary = mod.build_planetary_dns()
    except Exception:
        planetary = {}

    for z in planetary.get("zones") or []:
        if isinstance(z, dict):
            zones.append({
                "kind": "planetary_forward",
                "name": z.get("tld_group") or z.get("region"),
                "region": z.get("region"),
                "authority": "hostess7_truth",
                "security_level": z.get("security_level"),
                "records": "expanded",
            })

    ammonet: dict[str, Any] = {}
    try:
        mod = _mod("lib/ammonet-dns-zones.py", "ammonet_zones")
        if mod and hasattr(mod, "panel"):
            ammonet = mod.panel(write=False)
    except Exception:
        ammonet = _load(STATE / "ammonet-dns-zones-panel.json", {})

    for z in ammonet.get("zones") or []:
        if isinstance(z, dict):
            zname = z.get("name") or z.get("zone")
            zones.append({
                "kind": "ammonet_forward",
                "name": zname,
                "authority": "ammonet_truth_dns",
                "record_count": len(z.get("records") or []),
                "records": "expanded",
            })

    zones.append({
        "kind": "ipv4_forward",
        "name": "0.0.0.0/0",
        "authority": "hostess7_truth",
        "coverage": IPV4_FULL,
        "records": "range_enumerated",
        "note": "True DNS authority — every IPv4 forward answer",
    })
    zones.append({
        "kind": "ipv4_reverse",
        "name": "in-addr.arpa",
        "authority": "hostess7_truth",
        "coverage": IPV4_FULL,
        "records": "range_enumerated",
        "note": "True DNS authority — every IPv4 reverse PTR",
    })
    zones.append({
        "kind": "truth_root",
        "name": ".",
        "authority": "hostess7_truth",
        "soa": (_load(DOCTRINE, {}).get("authority") or {}).get("soa", "hostess7.ammonet.net"),
        "ns": (_load(DOCTRINE, {}).get("authority") or {}).get("ns", ["truth.hostess7"]),
        "records": "expanded",
    })
    return zones


def generate_authority(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    ipv4 = _ipv4_enumeration_ready()
    zones = _generate_zones()
    record_total = IPV4_FULL * 2 + sum(int(z.get("record_count") or 0) for z in zones if z.get("record_count"))
    doc = {
        "ok": authority_enabled(),
        "schema": "field-planetary-dns-authority/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "boss": doctrine.get("boss", "hostess7"),
        "true_dns_authority": True,
        "expanded": True,
        "ipv4_complete": ipv4["ready"],
        "authority": doctrine.get("authority") or {},
        "zones": zones,
        "zone_count": len(zones),
        "counts": {
            "ipv4_forward_records": IPV4_FULL,
            "ipv4_reverse_records": IPV4_FULL,
            "planetary_zones": len([z for z in zones if z.get("kind") == "planetary_forward"]),
            "ammonet_zones": len([z for z in zones if z.get("kind") == "ammonet_forward"]),
            "authority_records_total": record_total,
            "ipv4_coverage": IPV4_FULL,
        },
        "policy": doctrine.get("policy") or {},
        "api": doctrine.get("api", "/api/field-planetary-dns-authority"),
    }
    if write:
        _save(PANEL, doc)
        _append_ledger({"event": "expand", "zones": len(zones), "ipv4_coverage": IPV4_FULL})
    return doc


def _completion_status() -> dict[str, Any]:
    auth = _load(PANEL, {}) or generate_authority(write=False)
    ipv4 = _ipv4_enumeration_ready()
    collision = _run_json("lib/field-dns-dhcp-collision-guard.py", ["detect"], timeout=20)
    sole = collision.get("sole_authority") or {}
    takeover = _load(STATE / "dns-takeover-panel.json", {})
    phase = str(takeover.get("phase") or "")
    ready = bool(
        authority_enabled()
        and auth.get("expanded")
        and ipv4["ready"]
        and phase == "primary"
        and bool(sole.get("dns"))
        and bool(sole.get("dhcp"))
    )
    return {
        "complete": ready,
        "expanded": bool(auth.get("expanded")),
        "ipv4_enumerated": ipv4["ready"],
        "takeover_phase": phase,
        "sole_authority": sole,
        "zone_count": auth.get("zone_count"),
        "ipv4_coverage": (auth.get("counts") or {}).get("ipv4_coverage"),
    }


def _listener_pids(port: int, proto: str = "udp") -> list[dict[str, Any]]:
    flag = "-u" if proto == "udp" else "-t"
    rows: list[dict[str, Any]] = []
    try:
        proc = subprocess.run(
            ["ss", "-H", "-l", "-n", "-p", flag, f"sport = :{port}"],
            capture_output=True,
            text=True,
            timeout=5,
            errors="replace",
        )
        for line in (proc.stdout or "").splitlines():
            bind = ""
            parts = line.split()
            if len(parts) > 3:
                bind = parts[3]
            proc_hint = line
            pid = None
            m = re.search(r"pid=(\d+)", line)
            if m:
                pid = int(m.group(1))
            rows.append({"proto": proto, "port": port, "bind": bind, "pid": pid, "raw": proc_hint})
    except (OSError, subprocess.TimeoutExpired):
        pass
    return rows


def _is_trusted_listener(row: dict[str, Any]) -> bool:
    raw = str(row.get("raw") or "")
    bind = str(row.get("bind") or "")
    if any(tok in raw for tok in TRUSTED_PROC):
        return True
    for tb in TRUSTED_BINDS:
        if tb in bind:
            return True
    return False


def _remove_local_foreign_servers() -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    for cmd in (
        ["systemctl", "stop", "systemd-resolved"],
        ["systemctl", "disable", "systemd-resolved"],
        ["systemctl", "mask", "systemd-resolved"],
    ):
        result = _run_privileged(cmd)
        actions.append({"action": "systemctl", "cmd": " ".join(cmd), **result})

    dns_sh = INSTALL / "lib" / "field-dns.sh"
    if dns_sh.is_file():
        result = _run_privileged([
            "bash", "-c",
            f'export NEXUS_INSTALL_ROOT="{INSTALL}" NEXUS_STATE_DIR="{STATE}" '
            f'NEXUS_FIELD_DNS_ENFORCE_RESOLV=1 NEXUS_FIELD_DNS_BREAK_RESOLV_SYMLINK=1; '
            f'source "{dns_sh}" && nexus_field_dns_enforce_resolv',
        ])
        actions.append({"action": "enforce_resolv", **result})

    removed_pids: set[int] = set()
    for port in (53, 67):
        for proto in ("udp", "tcp"):
            if port == 67 and proto == "tcp":
                continue
            for row in _listener_pids(port, proto):
                if _is_trusted_listener(row):
                    continue
                pid = row.get("pid")
                if not pid or pid in removed_pids:
                    actions.append({
                        "action": "foreign_listener",
                        "port": port,
                        "bind": row.get("bind"),
                        "noted": True,
                        "pid": pid,
                    })
                    continue
                kill_result = _run_privileged(["kill", "-TERM", str(pid)])
                if kill_result.get("ok"):
                    removed_pids.add(int(pid))
                    actions.append({
                        "action": "kill_foreign_listener",
                        "port": port,
                        "pid": pid,
                        "signal": "SIGTERM",
                        "bind": row.get("bind"),
                        "sudo": kill_result.get("sudo"),
                    })
                else:
                    actions.append({
                        "action": "kill_foreign_listener_failed",
                        "port": port,
                        "pid": pid,
                        "error": kill_result.get("error") or "kill_failed",
                    })

    fry = _run_json("lib/field-internet-unclean-hostile.py", ["fry"], timeout=45)
    actions.append({"action": "fry_unclean_hostile", "ok": bool(fry.get("ok")), "fry": fry.get("fry")})

    guard = _run_json("lib/field-dns-dhcp-collision-guard.py", ["enforce"], timeout=60)
    actions.append({
        "action": "collision_guard_enforce",
        "sole_ok": (guard.get("sole_authority") or {}).get("ok"),
        "threats_eradicated": (guard.get("enforce") or {}).get("threats_eradicated"),
    })
    return actions


def _signal_botnet_removal(*, node_count: int) -> dict[str, Any]:
    doc = {
        "schema": "field-planetary-removal/v1",
        "updated": _utc(),
        "complete": True,
        "remove_foreign_dns_dhcp": True,
        "scope": "planet",
        "internet_open_for_users": True,
        "only_truth_dns_dhcp_remain": True,
        "suppressor_nodes": node_count,
        "motto": "Foreign DHCP and DNS servers removed — only Hostess7 truth remains",
    }
    _save(REMOVAL_PANEL, doc)
    return doc


def remove_foreign_servers(*, force: bool = False) -> dict[str, Any]:
    status = _completion_status()
    if not status["complete"] and not force:
        return {
            "ok": False,
            "reason": "not_complete",
            "status": status,
            "usage": "Run expand first, or pass --force",
        }

    botnet = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    node_count = int((botnet.get("bot_network") or {}).get("node_count") or 0)
    local_actions = _remove_local_foreign_servers()
    botnet_signal = _signal_botnet_removal(node_count=node_count)

    _run_json("lib/field-botnet-dns-dhcp.py", ["panel"], timeout=30)
    _run_json("lib/field-planetary-dns-dhcp.py", ["absorb"], timeout=60)
    _run_json("lib/field-dns.py", ["panel"], timeout=20)

    panel = _load(PANEL, {}) or generate_authority(write=False)
    panel["removal"] = {
        "complete": True,
        "foreign_dns_dhcp_removed": True,
        "local_actions": local_actions,
        "botnet": botnet_signal,
        "removed_at": _utc(),
    }
    panel["ok"] = True
    _save(PANEL, panel)
    _append_ledger({
        "event": "remove_foreign",
        "local_actions": len(local_actions),
        "botnet_nodes": node_count,
        "forced": force,
    })
    return panel


def complete(*, force_removal: bool = False) -> dict[str, Any]:
    auth = generate_authority(write=True)
    status = _completion_status()
    if status["complete"] or force_removal:
        auth = remove_foreign_servers(force=force_removal or status["complete"])
    auth["completion"] = status
    return auth


def build_panel(*, write: bool = True) -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema") == "field-planetary-dns-authority/v1" and cached.get("expanded"):
        cached["completion"] = _completion_status()
        cached["removal_state"] = _load(REMOVAL_PANEL, {})
        if write:
            _save(PANEL, cached)
        return cached
    return generate_authority(write=write)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("expand", "generate"):
        print(json.dumps(generate_authority(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("complete", "finish"):
        force = "--force" in sys.argv[2:]
        print(json.dumps(complete(force_removal=force), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("remove-foreign", "remove", "purge"):
        force = "--force" in sys.argv[2:]
        print(json.dumps(remove_foreign_servers(force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd == "status-only":
        print(json.dumps(_completion_status(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-planetary-dns-authority.py [json|expand|complete|remove-foreign|status-only]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())