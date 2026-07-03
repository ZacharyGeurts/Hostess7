#!/usr/bin/env pythong
"""DNS drift threat — Truth @127.0.0.1 authority; stub/trace/system drift = hostile."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-dns-drift-threat-doctrine.json"
PANEL = STATE / "field-dns-drift-threat-panel.json"


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


def _resolve_mod():
    path = INSTALL / "lib" / "field-dns-resolve.py"
    spec = importlib.util.spec_from_file_location("field_dns_resolve", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _violation(msg: str) -> None:
    log_py = INSTALL / "lib" / "field-central-log.py"
    if log_py.is_file():
        try:
            subprocess.run(
                [os.environ.get("PYTHON", "python3"), str(log_py), "append", "warn", "dns-drift", msg],
                capture_output=True,
                timeout=8,
                check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    ammo = Path(os.environ.get("AMMO_STATE_DIR", str(STATE.parent / ".ammo-state-ci")))
    try:
        ammo.mkdir(parents=True, exist_ok=True)
        with (ammo / "violations.log").open("a", encoding="utf-8") as fh:
            fh.write(f"{_utc()} VIOLATION {msg}\n")
    except OSError:
        pass


def _overlap(a: list[str], b: list[str]) -> bool:
    return bool(set(a) & set(b))


def _drift_row(host: str, resolved: dict[str, Any], *, doctrine: dict[str, Any]) -> dict[str, Any]:
    truth = list(resolved.get("truth") or [])
    stub = list(resolved.get("stub") or [])
    trace = list(resolved.get("trace") or [])
    system = list(resolved.get("system") or [])
    authority = truth or list(resolved.get("ips") or [])
    threats: list[str] = []
    level = "ok"
    if not resolved.get("truth_up") and doctrine.get("drift_as_threat", True):
        threats.append("TRUTH_DNS_DOWN")
        level = "high"
    if stub and authority and not _overlap(stub, authority) and doctrine.get("stub_drift_as_threat", True):
        threats.append("TRUTH_STUB_DRIFT")
        level = "critical"
    if trace and authority and not _overlap(trace, authority) and doctrine.get("trace_drift_as_threat", True):
        threats.append("TRUTH_TRACE_DRIFT")
        level = "critical" if level != "critical" else level
    if system and authority and not _overlap(system, authority):
        threats.append("TRUTH_SYSTEM_DRIFT")
        level = "high" if level == "ok" else level
    if authority and stub and _overlap(authority, stub) and authority != stub and doctrine.get("pool_drift_as_threat", True):
        if set(authority) != set(stub):
            threats.append("DNS_POOL_DRIFT")
            level = "medium" if level == "ok" else level
    return {
        "host": host,
        "truth": truth,
        "authority": authority,
        "stub": stub,
        "trace": trace,
        "system": system,
        "source": resolved.get("source"),
        "truth_up": resolved.get("truth_up"),
        "threats": threats,
        "threat_level": level,
        "drift": bool(threats),
    }


def scan(*, apply: bool = False) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    mod = _resolve_mod()
    hosts = list(doc.get("watch_hosts") or ["github.com", "api.github.com", "ssh.github.com"])
    rows: list[dict[str, Any]] = []
    max_level = "ok"
    level_rank = {"ok": 0, "medium": 1, "high": 2, "critical": 3}
    for host in hosts:
        resolved: dict[str, Any] = {}
        if mod is not None:
            try:
                resolved = mod.resolve_a(host)
            except (OSError, AttributeError):
                pass
        row = _drift_row(host, resolved, doctrine=doc)
        rows.append(row)
        if level_rank.get(row.get("threat_level", "ok"), 0) > level_rank.get(max_level, 0):
            max_level = str(row.get("threat_level"))
        if row.get("drift"):
            _violation(f"DNS drift threat {host}: {row.get('threats')}")

    applied: list[str] = []
    if apply and max_level in ("high", "critical"):
        guard_py = INSTALL / "lib" / "dns-threat-guard.py"
        if guard_py.is_file():
            try:
                spec = importlib.util.spec_from_file_location("dns_threat_guard", guard_py)
                if spec and spec.loader:
                    gmod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(gmod)
                    gmod.eradicate_threat(
                        client_key="dns-drift:stub",
                        reason=f"dns_drift level={max_level}",
                        vector=str((doc.get("mitigations") or {}).get("eradicate_vector") or "DNS_DRIFT"),
                    )
                    applied.append("dns-threat-guard.eradicate")
            except (OSError, AttributeError):
                pass
        if (doc.get("mitigations") or {}).get("enforce_resolv"):
            dns_sh = INSTALL / "lib" / "field-dns.sh"
            if dns_sh.is_file():
                try:
                    subprocess.run(
                        ["bash", "-c", f'source "{dns_sh}" && nexus_field_dns_enforce_cycle'],
                        capture_output=True,
                        timeout=20,
                        check=False,
                        env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
                    )
                    applied.append("field-dns.enforce_cycle")
                except (OSError, subprocess.TimeoutExpired):
                    pass

    out = {
        "schema": "field-dns-drift-threat/v1",
        "ts": _utc(),
        "ok": max_level in ("ok", "medium"),
        "threat": max_level not in ("ok",),
        "threat_level": max_level,
        "drift_as_threat": bool(doc.get("drift_as_threat", True)),
        "hosts": rows,
        "applied": applied,
    }
    _save(PANEL, out)
    return out


def servers_updated() -> dict[str, Any]:
    """Audit Truth DNS + Field DHCP across queen and botnet nodes."""
    doc = _load(DOCTRINE, {})
    req_dns = list(doc.get("dhcp_dns_require") or ["127.0.0.1"])
    req_upstream = str(doc.get("node_dns_upstream_require") or "127.0.0.1")

    dns_panel = _load(STATE / "field-dns-panel.json", {})
    dhcp_panel = _load(STATE / "field-dhcp-panel.json", {})
    takeover = _load(STATE / "dns-takeover-state.json", {})
    phase = str(takeover.get("phase") or "unknown")

    if not dns_panel.get("schema"):
        try:
            proc = subprocess.run(
                [os.environ.get("PYTHON", "python3"), str(INSTALL / "lib" / "field-dns.py"), "json"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            if proc.stdout.strip():
                dns_panel = json.loads(proc.stdout)
        except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass

    if not dhcp_panel.get("schema"):
        try:
            proc = subprocess.run(
                [os.environ.get("PYTHON", "python3"), str(INSTALL / "lib" / "field-dhcp.py"), "json"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
                env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            )
            if proc.stdout.strip():
                dhcp_panel = json.loads(proc.stdout)
        except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
            pass

    dhcp_dns = list(
        (dhcp_panel.get("dns_option") or dhcp_panel.get("servers", {}).get("dhcp", {}).get("dns_option") or req_dns)
    )
    queen_dns_ok = bool(dns_panel.get("running") or dns_panel.get("truthful"))
    queen_dhcp_ok = all(str(x) in dhcp_dns for x in req_dns)
    queen_updated = queen_dns_ok and queen_dhcp_ok and phase in ("ready", "primary")

    nodes: list[dict[str, Any]] = []
    stale = 0
    reg = _load(STATE / "field-botnet-registry.json", {})
    world = _load(STATE / "grok-lab-world-registry.json", {})
    if not world.get("nodes"):
        world = _load(INSTALL / ".nexus-state/grok-lab-world-registry.json", {})

    seen: set[str] = set()
    for m in reg.get("members") or []:
        if not isinstance(m, dict):
            continue
        mid = str(m.get("member_id") or "")
        if not mid:
            continue
        upstream = str((m.get("dns_slot") or {}).get("upstream") or "127.0.0.1:53")
        shard_dns = list((m.get("dhcp_shard") or {}).get("dns_option") or req_dns)
        up_ok = req_upstream in upstream
        dhcp_ok = all(str(x) in shard_dns for x in req_dns)
        ok = up_ok and dhcp_ok
        if not ok:
            stale += 1
        nodes.append({"id": mid, "kind": "botnet_member", "ok": ok, "dns_upstream": upstream, "dhcp_dns_option": shard_dns})
        seen.add(mid)

    for row in world.get("nodes") or []:
        if not isinstance(row, dict):
            continue
        nid = str(row.get("id") or "")
        if not nid or nid in seen:
            continue
        upstream = str(row.get("dns_upstream") or "127.0.0.1:53")
        shard_dns = list(row.get("dhcp_dns_option") or req_dns)
        up_ok = req_upstream in upstream
        dhcp_ok = all(str(x) in shard_dns for x in req_dns)
        ok = up_ok and dhcp_ok
        if not ok:
            stale += 1
        nodes.append({"id": nid, "kind": row.get("kind", "world"), "ok": ok, "dns_upstream": upstream, "dhcp_dns_option": shard_dns})
        seen.add(nid)

    mod = _resolve_mod()
    truth_up = bool(mod.truth_resolver_up()) if mod else False

    return {
        "schema": "field-dns-dhcp-servers-updated/v1",
        "ts": _utc(),
        "ok": queen_updated and stale == 0,
        "queen": {
            "dns_running": queen_dns_ok,
            "dhcp_dns_option": dhcp_dns,
            "takeover_phase": phase,
            "truth_resolver_up": truth_up,
            "updated": queen_updated,
        },
        "field_nodes": len(nodes),
        "stale_nodes": stale,
        "all_nodes_updated": stale == 0,
        "nodes_sample": nodes[:24],
        "required_dns": req_dns,
        "required_upstream": req_upstream,
    }


def panel(*, apply: bool = False) -> dict[str, Any]:
    drift = scan(apply=apply)
    servers = servers_updated()
    doc = _load(DOCTRINE, {})
    out = {
        "ok": drift.get("ok") and servers.get("ok"),
        "schema": "field-dns-drift-threat-panel/v1",
        "updated": _utc(),
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "drift": drift,
        "servers_updated": servers,
        "api": doc.get("api", "/api/field-dns-drift-threat"),
    }
    _save(PANEL, out)
    return out


def main() -> int:
    import sys

    args = sys.argv[1:]
    apply = "--apply" in args
    cmd = next((a for a in args if not a.startswith("-")), "panel")
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(apply=apply), ensure_ascii=False, indent=2))
        return 0
    if cmd == "scan":
        print(json.dumps(scan(apply=apply), ensure_ascii=False, indent=2))
        return 0
    if cmd == "servers":
        print(json.dumps(servers_updated(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-dns-drift-threat.py [panel|scan|servers] [--apply]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())