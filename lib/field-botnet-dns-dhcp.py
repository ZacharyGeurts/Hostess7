#!/usr/bin/env pythong
"""Fielded bot network — secure stable DNS & DHCP for everyone · GitHub control plane · Hostess 7 boss."""
from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-botnet-dns-dhcp-doctrine.json"
PANEL = STATE / "field-botnet-dns-dhcp-panel.json"
LEDGER = STATE / "field-botnet-dns-dhcp.jsonl"
GITHUB_CACHE = STATE / "field-internet-github.json"


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


def _run_json(rel: str, args: list[str] | None = None, *, timeout: int = 90) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": f"missing {rel}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *(args or ["json"])],
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
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        pass
    return {"ok": False, "error": "script_failed", "script": rel}


def _probe_url(url: str, *, timeout: float = 3.5) -> dict[str, Any]:
    ctx = ssl.create_default_context()
    started = time.monotonic()
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "FieldBotnetDnsDhcp/1.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            return {"ok": True, "status": resp.status, "elapsed_ms": elapsed_ms, "url": url}
    except urllib.error.HTTPError as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return {"ok": exc.code < 500, "status": exc.code, "elapsed_ms": elapsed_ms, "url": url}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "error": str(exc)[:120], "url": url}


def _github_slice(doctrine: dict[str, Any], *, fast: bool) -> dict[str, Any]:
    gh_plane = doctrine.get("github_control_plane") or {}
    cached = _load(GITHUB_CACHE, {})
    if fast and cached.get("schema"):
        return {
            **gh_plane,
            "github_open": bool(cached.get("always_open") or cached.get("open_count", 0) > 0),
            "open_count": cached.get("open_count", 0),
            "pages_runtime": gh_plane.get("pages"),
            "cached": True,
        }
    pages = str(gh_plane.get("pages") or "").strip()
    hit = _probe_url(pages) if pages else {"ok": False}
    return {
        **gh_plane,
        "github_open": hit.get("ok"),
        "pages_probe": hit,
        "pages_runtime": pages,
        "cached": False,
    }


def _member_registry_nodes(doctrine: dict[str, Any], *, fast: bool = False) -> list[dict[str, Any]]:
    net = doctrine.get("bot_network") or {}
    if not net.get("prefer_member_registry", True):
        return []
    members: list[dict[str, Any]] = []
    if fast:
        reg_doc = _load(STATE / "field-botnet-registry.json", {})
        members = list(reg_doc.get("members") or [])
    else:
        mesh = _run_json("lib/field-botnet-registry.py", ["mesh"], timeout=20)
        members = list(mesh.get("members") or [])
    nodes: list[dict[str, Any]] = []
    for m in members:
        if not isinstance(m, dict):
            continue
        shard = m.get("dhcp_shard") or {}
        dns = m.get("dns_slot") or {}
        storage = m.get("forever_storage") or {}
        nodes.append({
            "id": str(m.get("member_id") or ""),
            "kind": "botnet_member",
            "name": m.get("display_name"),
            "full_name": m.get("full_name"),
            "region": m.get("region"),
            "country": m.get("country"),
            "flag": m.get("flag"),
            "permanent": True,
            "forever_storage": bool(storage.get("forever") or storage.get("sparse")),
            "storage_slot": storage.get("storage_slot"),
            "virtual_bytes": storage.get("virtual_bytes"),
            "roles": m.get("roles") or net.get("roles") or ["dns_relay", "dhcp_relay", "power_user"],
            "dns_upstream": dns.get("upstream") or "127.0.0.1:53",
            "dhcp_dns_option": shard.get("dns_option") or ["127.0.0.1"],
            "dhcp_pool": f"{shard.get('pool_start')}-{shard.get('pool_end')}",
            "dhcp_subnet": shard.get("subnet"),
            "composite_score": m.get("composite_score"),
            "bsp_algorithm": m.get("bsp_algorithm") or "composite_bsp",
            "github_sync": True,
            "boss": "hostess7",
            "power_user": m.get("power_user", True),
        })
    return [n for n in nodes if n.get("id")]


def _bot_nodes(doctrine: dict[str, Any], *, fast: bool = False) -> list[dict[str, Any]]:
    net = doctrine.get("bot_network") or {}
    nodes: list[dict[str, Any]] = _member_registry_nodes(doctrine, fast=fast)
    seen = {str(n.get("id")) for n in nodes if n.get("id")}

    reg_rel = str(net.get("registry") or ".nexus-state/grok-lab-world-registry.json")
    reg_path = INSTALL / reg_rel if not reg_rel.startswith("/") else Path(reg_rel)
    reg = _load(reg_path if reg_path.is_file() else STATE / "grok-lab-world-registry.json", {})
    for row in reg.get("nodes") or []:
        if not isinstance(row, dict):
            continue
        nid = str(row.get("id") or row.get("name") or "")
        if nid in seen:
            continue
        seen.add(nid)
        nodes.append({
            **row,
            "id": nid or f"node-{len(nodes)}",
            "roles": net.get("roles") or ["dns_relay", "dhcp_relay"],
            "dns_upstream": row.get("dns_upstream") or "127.0.0.1:53",
            "dhcp_dns_option": row.get("dhcp_dns_option") or ["127.0.0.1"],
            "github_sync": True,
            "boss": "hostess7",
        })
    qemu: dict[str, Any] = {}
    if not fast:
        qemu = _run_json("lib/qemu-world-status.py", [], timeout=12)
    else:
        qemu = _load(STATE / "qemu-world-pipeline.json", {})
    target = int(qemu.get("target") or 0)
    completed = int(qemu.get("completed") or 0)
    qemu_cap = int(net.get("max_qemu_placeholder_nodes") or 64)
    qemu_total = min(max(target, completed, 0), qemu_cap if nodes else max(target, completed, 0))
    for i in range(qemu_total):
        wid = f"qemu-world-{i + 1}"
        if any(n.get("id") == wid for n in nodes):
            continue
        nodes.append({
            "id": wid,
            "kind": "qemu_world",
            "roles": ["dns_relay", "dhcp_relay", "truth_mirror"],
            "dns_upstream": "127.0.0.1:53",
            "dhcp_dns_option": ["127.0.0.1"],
            "github_sync": True,
            "boss": "hostess7",
            "pipeline": qemu.get("schema"),
        })
    if not nodes:
        nodes = [
            {
                "id": "field-loopback",
                "kind": "sovereign",
                "roles": ["dns_authority", "dhcp_authority", "github_sync"],
                "dns_upstream": "127.0.0.1:53",
                "dhcp_dns_option": ["127.0.0.1"],
                "github_sync": True,
                "boss": "hostess7",
                "note": "Primary truth resolver until registry populates",
            }
        ]
    return nodes


def _dns_dhcp_slice(*, fast: bool = False) -> dict[str, Any]:
    dns_panel = _load(STATE / "field-dns-panel.json", {})
    dhcp_panel = _load(STATE / "field-dhcp-panel.json", {})
    if not dns_panel.get("schema"):
        dns_panel = _run_json("lib/field-dns.py", ["json"], timeout=8 if fast else 20)
    if not dhcp_panel.get("schema"):
        dhcp_panel = _run_json("lib/field-dhcp.py", ["json"], timeout=8 if fast else 20)
    srv = dns_panel.get("servers") or {}
    dns_srv = srv.get("dns") or {}
    dhcp_srv = srv.get("dhcp") or dns_panel.get("dhcp_server") or dhcp_panel
    return {
        "dns": {
            "ok": bool(dns_panel.get("running") or dns_srv.get("running")),
            "running": bool(dns_panel.get("running") or dns_srv.get("running")),
            "self_hosted": dns_panel.get("self_hosted", True),
            "truthful": dns_panel.get("truthful", True),
            "listeners": dns_srv.get("listeners") or dns_panel.get("listeners") or ["127.0.0.1#53"],
            "schema": dns_panel.get("schema", "field-dns/v2"),
        },
        "dhcp": {
            "ok": bool(dhcp_srv.get("running") or dhcp_panel.get("running")),
            "running": bool(dhcp_srv.get("running") or dhcp_panel.get("running")),
            "bind": dhcp_srv.get("bind") or dhcp_panel.get("bind") or "0.0.0.0:67",
            "lease_count": int(dhcp_srv.get("lease_count") or dhcp_panel.get("lease_count") or 0),
            "dns_option": dhcp_srv.get("dns_option") or dhcp_panel.get("dns_option") or ["127.0.0.1"],
            "dns_option_v6": dhcp_srv.get("dns_option_v6") or dhcp_panel.get("dns_option_v6") or ["::1"],
            "schema": dhcp_panel.get("schema", "field-dhcp/v2"),
        },
        "combined": bool(dns_panel.get("running") or dhcp_srv.get("running")),
    }


def panel(*, write: bool = True, fast: bool = False) -> dict[str, Any]:
    if fast and PANEL.is_file():
        cached = _load(PANEL, {})
        if cached.get("schema") == "field-botnet-dns-dhcp-panel/v1":
            cached["updated"] = _utc()
            cached["fast"] = True
            return cached

    doctrine = _load(DOCTRINE, {})
    net = doctrine.get("bot_network") or {}
    gh_slice = _github_slice(doctrine, fast=fast)
    gh_open = gh_slice.get("github_open")
    nodes = _bot_nodes(doctrine, fast=fast)
    services = _dns_dhcp_slice(fast=fast)
    stable = bool(services["dns"].get("running") and services["dhcp"].get("dns_option"))
    secure = bool(doctrine.get("for_everyone", {}).get("secure", True))

    if fast:
        legal_ports = _load(STATE / "field-botnet-legal-ports-panel.json", {}) or {"api": "/api/field-botnet-legal-ports"}
        h7t_truth = _load(STATE / "field-h7t-truth-panel.json", {}) or {"api": "/api/field-h7t-truth"}
        github_res = _load(STATE / "field-github-resilience-panel.json", {}) or _load(STATE / "field-github-resilience-probe.json", {})
        github_everyone = _load(STATE / "field-github-everyone-panel.json", {})
        traffic = _load(STATE / "field-github-traffic-shard-panel.json", {})
        drift_threat = _load(STATE / "field-dns-drift-threat-panel.json", {})
    else:
        legal_ports = _run_json("lib/field-botnet-legal-ports.py", ["json"], timeout=8 if fast else 15)
        h7t_truth = _run_json("lib/field-h7t-truth.py", ["json"], timeout=8 if fast else 15)
        github_res = _run_json("lib/field-github-resilience.py", ["json"], timeout=8 if fast else 15)
        github_everyone = _run_json("lib/field-github-everyone.py", ["json"], timeout=8 if fast else 15)
        traffic = _run_json("lib/field-github-traffic-shard.py", ["json"], timeout=8)
        drift_threat = _run_json("lib/field-dns-drift-threat.py", ["panel"], timeout=12)
    doc = {
        "ok": True,
        "schema": "field-botnet-dns-dhcp-panel/v1",
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "updated": _utc(),
        "boss": "hostess7",
        "layer": doctrine.get("layer", -2),
        "fkey": doctrine.get("fkey", "F10"),
        "for_everyone": doctrine.get("for_everyone") or {},
        "github_control_plane": gh_slice,
        "bot_network": {
            "enabled": True,
            "node_count": len(nodes),
            "nodes": nodes,
            "member_registry": net.get("member_registry") or "lib/field-botnet-registry.py",
            "member_registry_api": "/api/field-botnet-registry",
            "prefer_member_registry": bool(net.get("prefer_member_registry", True)),
            "permanent_reservation": any(n.get("permanent") for n in nodes),
            "any_and_all": True,
            "unified_egress": "hostess7",
        },
        "dns_dhcp": services,
        "stable": stable,
        "secure": secure,
        "internet_unified": {
            "ok": bool(gh_open),
            "api": "/api/field-internet",
            "github_open": gh_open,
            "note": "GitHub control plane via Pages probe — no circular unified panel",
        },
        "api": "/api/field-botnet-dns-dhcp",
        "dns_api": "/api/field-dns",
        "wires": doctrine.get("wires") or [],
        "legal_ports": legal_ports if legal_ports.get("ok") else {"api": "/api/field-botnet-legal-ports"},
        "h7t_truth": h7t_truth if h7t_truth.get("ok") else {"api": "/api/field-h7t-truth"},
        "github_resilience": github_res if github_res.get("probe") else {"api": "/api/field-github-resilience"},
        "github_everyone": github_everyone if github_everyone.get("ok") else {"api": "/api/field-github-everyone"},
        "github_traffic_shard": traffic if traffic.get("schema") else {"api": "/api/field-github-traffic-shard"},
        "dns_drift_threat": drift_threat if drift_threat.get("schema") else {"api": "/api/field-dns-drift-threat"},
        "servers_updated": (drift_threat.get("servers_updated") if drift_threat.get("schema") else None),
        "fast": fast,
    }
    doc["ok"] = bool(stable or gh_open or len(nodes) > 0)
    if write:
        _save(PANEL, doc)
    return doc


def keepalive(*, write: bool = True) -> dict[str, Any]:
    doc = panel(write=write, fast=True)
    doc["schema"] = "field-botnet-dns-dhcp-keepalive/v1"
    if write:
        try:
            with LEDGER.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"event": "keepalive", "ts": _utc(), "ok": doc.get("ok"), "nodes": doc.get("bot_network", {}).get("node_count")}, ensure_ascii=False) + "\n")
        except OSError:
            pass
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(panel(write=False, fast=True), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("keepalive", "pulse", "fast"):
        print(json.dumps(keepalive(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "panel":
        print(json.dumps(panel(write=True, fast=False), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-botnet-dns-dhcp.py [panel|json|keepalive|fast]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())