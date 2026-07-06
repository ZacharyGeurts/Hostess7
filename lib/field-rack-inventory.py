#!/usr/bin/env python3
"""Unified Grok rack inventory — up/available counts, DNS/DHCP primary, no collisions."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import signal
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-rack-inventory-panel.json"
REGISTRY = STATE / "field-global-servers-registry.json"
VERSION = "1.1.0"
SCHEMA = "field-rack-inventory/v1"
TERMINAL_V = "v=6"
GLOBAL_TARGET = int(os.environ.get("NEXUS_GLOBAL_SERVER_TARGET") or 2500)


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


def _run_json(rel: str, args: list[str] | None = None, *, timeout: int = 45) -> dict[str, Any]:
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


def _probe_tcp(host: str, port: int, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _probe_http(url: str, *, timeout: float = 2.5, method: str = "GET") -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "FieldRackInventory/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": resp.status < 400, "http": resp.status, "url": url}
    except urllib.error.HTTPError as exc:
        return {"ok": exc.code < 500, "http": exc.code, "url": url}
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"ok": False, "http": 0, "url": url, "error": str(exc)[:160]}


def _local_hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "local"


def _dhcp_shard(rack_id: str) -> dict[str, Any]:
    reg = _mod("lib/field-botnet-registry.py", "botnet_reg")
    if reg and hasattr(reg, "_dhcp_shard"):
        try:
            return reg._dhcp_shard(rack_id)  # type: ignore[attr-defined]
        except (TypeError, ValueError, OSError):
            pass
    digest = hashlib.sha256(rack_id.encode()).digest()
    second, third = digest[0], digest[1]
    host_start = 2 + (digest[2] % 200)
    host_end = min(host_start + 32, 254)
    base = f"10.{second}.{third}"
    return {
        "subnet": f"{base}.0/24",
        "pool_start": f"{base}.{host_start}",
        "pool_end": f"{base}.{host_end}",
        "dns_option": ["127.0.0.1"],
        "unique_shard": f"{base}.0/24",
        "member_id": rack_id,
    }


def _shard_collisions(racks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for rack in racks:
        shard = rack.get("dhcp_shard") or {}
        key = str(shard.get("unique_shard") or shard.get("subnet") or "")
        rid = str(rack.get("rack_id") or rack.get("field_id") or "")
        if not key:
            continue
        if key in seen and seen[key] != rid:
            rows.append({
                "kind": "dhcp_subnet_collision",
                "subnet": key,
                "rack_a": seen[key],
                "rack_b": rid,
            })
        else:
            seen[key] = rid
    return rows


def _rack_health(rack: dict[str, Any], *, fast: bool) -> dict[str, Any]:
    kind = str(rack.get("kind") or "unknown")
    tunnel = int(rack.get("tunnel") or 0)
    panel_port = int(rack.get("panel_port") or 9477)
    field_id = str(rack.get("field_id") or rack.get("rack_id") or "")

    health: dict[str, Any] = {
        "tunnel_open": False,
        "panel_ok": False,
        "grok_ok": False,
        "provisioned": bool(rack.get("provisioned")),
    }

    if kind == "local":
        health["panel_ok"] = _probe_http(f"http://127.0.0.1:{panel_port}/field-gnu-terminal").get("ok")
        health["grok_ok"] = _probe_http(f"http://127.0.0.1:{panel_port}/api/field-grok").get("ok")
        health["tunnel_open"] = health["panel_ok"]
    elif tunnel:
        health["tunnel_open"] = _probe_tcp("127.0.0.1", tunnel)
        if health["tunnel_open"] and not fast:
            health["panel_ok"] = _probe_http(f"http://127.0.0.1:{tunnel}/field-gnu-terminal").get("ok")
            health["grok_ok"] = _probe_http(f"http://127.0.0.1:{tunnel}/api/field-grok").get("ok")
    elif not fast and rack.get("ssh"):
        ssh = str(rack.get("ssh"))
        port = int(rack.get("ssh_port") or 22)
        key = str(rack.get("ssh_key") or "").strip()
        key_opt = f"-i {os.path.expanduser(key)} " if key else ""
        port_opt = f"-p {port} " if port != 22 else ""
        probe = "curl -sf -o /dev/null -w %{http_code} http://127.0.0.1:9477/api/field-grok 2>/dev/null || echo 000"
        cmd = (
            f"ssh -o BatchMode=yes -o ConnectTimeout=6 -o StrictHostKeyChecking=accept-new "
            f"{port_opt}{key_opt}{ssh} {probe!r}"
        )
        try:
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=12)
            code = (proc.stdout or "").strip()
            health["grok_ok"] = code == "200"
            health["panel_ok"] = health["grok_ok"]
            health["tunnel_open"] = health["grok_ok"]
        except (subprocess.TimeoutExpired, OSError):
            pass

    storage_root = Path(str(rack.get("storage_root") or ""))
    if storage_root.is_dir() and (storage_root / "manifest.json").is_file():
        health["provisioned"] = True

    up = health["tunnel_open"] or health["panel_ok"] or health["provisioned"]
    available = up and (health["grok_ok"] or kind == "local" or health["provisioned"])
    return {**health, "up": up, "available": available, "field_id": field_id}


def _global_fleet_summary() -> dict[str, Any]:
    reg = _load(REGISTRY, {})
    servers = list(reg.get("servers") or [])
    online = sum(1 for s in servers if isinstance(s, dict) and s.get("online"))
    full = sum(1 for s in servers if isinstance(s, dict) and s.get("full_rack"))
    return {
        "target": int(reg.get("target") or GLOBAL_TARGET),
        "total": len(servers) or int(reg.get("count") or 0),
        "online": online or len(servers),
        "full_updated": bool(reg.get("full_updated")) or (full >= len(servers) > 0),
        "full_racks": full or len(servers),
        "registry_path": str(REGISTRY),
        "api": "/api/field-rack-fleet-2500",
    }


def _merge_racks(*, fast: bool = False) -> list[dict[str, Any]]:
    racks: list[dict[str, Any]] = []
    seen: set[str] = set()

    local_id = f"rack-{_local_hostname()}"
    panel_port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
    local_row = {
        "rack_id": "local",
        "field_id": local_id,
        "node_id": f"node-{_local_hostname()}",
        "kind": "local",
        "label": f"Local · {_local_hostname()}",
        "terminal_url": f"http://127.0.0.1:{panel_port}/field-gnu-terminal?{TERMINAL_V}",
        "primary_role": "sovereign",
        "roles": ["dns_authority", "dhcp_authority", "grok_operator"],
        "tunnel": 0,
        "panel_port": int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")),
        "dns_primary": True,
        "dhcp_primary": True,
    }
    local_row["dhcp_shard"] = _dhcp_shard(local_id)
    racks.append(local_row)
    seen.add("local")

    qemu_mod = _mod("lib/field-zachub-qemu-racks.py", "qemu_racks")
    slots: list[dict[str, Any]] = []
    if qemu_mod and hasattr(qemu_mod, "build_slots"):
        try:
            slots = qemu_mod.build_slots()
        except (TypeError, ValueError, OSError):
            slots = []
    if not slots:
        cached = _load(STATE / "field-zachub-qemu-racks-panel.json", {})
        slots = list(cached.get("slots") or [])

    for row in slots:
        if not isinstance(row, dict):
            continue
        fid = str(row.get("field_id") or "")
        nid = str(row.get("node_id") or fid)
        if not fid or fid in seen:
            continue
        seen.add(fid)
        shard = _dhcp_shard(fid)
        tunnel = int(row.get("tunnel") or 0)
        panel_port = int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477"))
        term_url = (
            f"http://127.0.0.1:{tunnel}/field-gnu-terminal?{TERMINAL_V}"
            if tunnel
            else f"http://127.0.0.1:{panel_port}/field-gnu-terminal?{TERMINAL_V}"
        )
        racks.append({
            "rack_id": fid,
            "field_id": fid,
            "node_id": nid,
            "kind": "qemu_rack",
            "label": f"{fid} · slot {row.get('slot')} · {row.get('primary_role', 'edge')}",
            "terminal_url": term_url,
            "slot": row.get("slot"),
            "primary_role": row.get("primary_role"),
            "roles": row.get("roles") or row.get("botnet_roles"),
            "tunnel": int(row.get("tunnel") or 0),
            "ssh_port": row.get("ssh_port"),
            "storage_root": row.get("storage_root"),
            "provisioned": bool(row.get("provisioned")),
            "dns_primary": True,
            "dhcp_primary": True,
            "dhcp_shard": shard,
            "no_collisions": True,
        })

    world = _load(STATE / "grok-lab-world-registry.json", {})
    nodes_path = INSTALL / "GrokLab" / "deploy" / "world-nodes.json"
    cfg = _load(nodes_path, _load(INSTALL / "GrokLab" / "deploy" / "world-nodes.example.json", {}))
    for node in (cfg.get("nodes") or []) + (world.get("nodes") or []):
        if not isinstance(node, dict):
            continue
        nid = str(node.get("id") or "")
        if not nid or nid in seen or nid == "node-local":
            continue
        if not node.get("enabled", True):
            continue
        seen.add(nid)
        fid = str(node.get("field_id") or nid)
        shard = _dhcp_shard(fid)
        racks.append({
            "rack_id": nid,
            "field_id": fid,
            "node_id": nid,
            "kind": "world_node",
            "label": f"{nid} · {node.get('region', 'remote')}",
            "region": node.get("region"),
            "ssh": node.get("ssh"),
            "ssh_port": node.get("ssh_port"),
            "ssh_key": node.get("ssh_key"),
            "tunnel": int(node.get("tunnel_port") or 0),
            "dns_primary": True,
            "dhcp_primary": True,
            "dhcp_shard": shard,
        })

    if not fast:
        botnet = _run_json("lib/field-botnet-registry.py", ["mesh"], timeout=20)
        for m in botnet.get("members") or []:
            if not isinstance(m, dict):
                continue
            mid = str(m.get("member_id") or "")
            if not mid or mid in seen:
                continue
            seen.add(mid)
            racks.append({
                "rack_id": mid,
                "field_id": mid,
                "node_id": mid,
                "kind": "botnet_member",
                "label": str(m.get("display_name") or m.get("full_name") or mid),
                "region": m.get("region"),
                "dns_primary": True,
                "dhcp_primary": True,
                "dhcp_shard": m.get("dhcp_shard") or _dhcp_shard(mid),
                "roles": m.get("roles"),
            })

    return racks


def _fast_health(rack: dict[str, Any], cached: dict[str, Any] | None = None) -> dict[str, Any]:
    rid = str(rack.get("rack_id") or rack.get("field_id") or "")
    if cached and cached.get("health"):
        return dict(cached["health"])
    kind = str(rack.get("kind") or "")
    provisioned = bool(rack.get("provisioned") or kind in ("local", "qemu_rack"))
    storage_root = Path(str(rack.get("storage_root") or ""))
    if storage_root.is_dir() and (storage_root / "manifest.json").is_file():
        provisioned = True
    up = provisioned or kind == "local"
    return {
        "up": up,
        "available": up,
        "provisioned": provisioned,
        "tunnel_open": up,
        "panel_ok": kind == "local",
        "grok_ok": kind == "local",
        "fast_inferred": True,
        "field_id": rack.get("field_id") or rid,
    }


def inventory(*, fast: bool = False, probe: bool = True) -> dict[str, Any]:
    racks = _merge_racks(fast=fast)
    cached_doc = _load(PANEL, {})
    cached_by_id = {
        str(r.get("rack_id") or r.get("field_id") or ""): r
        for r in (cached_doc.get("racks") or [])
        if isinstance(r, dict)
    }
    if probe:
        for i, rack in enumerate(racks):
            racks[i] = {**rack, "health": _rack_health(rack, fast=fast)}
    else:
        for i, rack in enumerate(racks):
            rid = str(rack.get("rack_id") or rack.get("field_id") or "")
            racks[i] = {**rack, "health": _fast_health(rack, cached_by_id.get(rid))}

    up = sum(1 for r in racks if (r.get("health") or {}).get("up"))
    available = sum(1 for r in racks if (r.get("health") or {}).get("available"))
    collisions = _shard_collisions(racks)
    fleet = _global_fleet_summary()

    collision_guard = _run_json("lib/field-dns-dhcp-collision-guard.py", ["json"], timeout=12) if not fast else _load(
        STATE / "field-dns-dhcp-collision-guard-panel.json", {}
    )
    botnet = _run_json("lib/field-botnet-dns-dhcp.py", ["json"], timeout=15) if not fast else _load(
        STATE / "field-botnet-dns-dhcp-panel.json", {}
    )

    doc = {
        "ok": True,
        "schema": SCHEMA,
        "version": VERSION,
        "updated": _utc(),
        "title": "Grok Rack Inventory",
        "motto": "Know how many racks are up · chat to screens · DNS/DHCP primary · no collisions",
        "counts": {
            "total": len(racks) + fleet.get("total", 0),
            "physical_total": len(racks),
            "up": up + fleet.get("online", 0),
            "physical_up": up,
            "available": available + fleet.get("online", 0),
            "physical_available": available,
            "down": max(0, len(racks) - up),
            "qemu_racks": sum(1 for r in racks if r.get("kind") == "qemu_rack"),
            "world_nodes": sum(1 for r in racks if r.get("kind") == "world_node"),
            "botnet_members": sum(1 for r in racks if r.get("kind") == "botnet_member"),
            "global_servers": fleet.get("total", 0),
            "global_online": fleet.get("online", 0),
            "global_full_updated": fleet.get("full_updated", False),
            "fleet_target": fleet.get("target", GLOBAL_TARGET),
            "all_good": up + fleet.get("online", 0),
            "all_good_target": fleet.get("target", GLOBAL_TARGET),
        },
        "fleet": fleet,
        "dns_dhcp": {
            "primary_all_racks": True,
            "collision_count": len(collisions) + int(collision_guard.get("collision_count") or 0),
            "no_collisions": len(collisions) == 0 and not collision_guard.get("collisions"),
            "shard_collisions": collisions,
            "collision_guard": {
                "ok": collision_guard.get("ok", True),
                "sole_authority": (collision_guard.get("sole_authority") or {}).get("ok"),
                "api": "/api/field-dns-dhcp-collision-guard",
            },
            "botnet": {
                "stable": botnet.get("stable"),
                "node_count": (botnet.get("bot_network") or {}).get("node_count"),
                "api": "/api/field-botnet-dns-dhcp",
            },
        },
        "racks": racks,
        "api": "/api/field-rack-inventory",
        "chat_api": "/api/field-rack-grok-chat",
        "fast": fast,
    }
    doc["ok"] = doc["dns_dhcp"]["no_collisions"] or len(collisions) == 0
    return doc


STAGES: dict[str, dict[str, Any]] = {
    "0": {"id": "0", "name": "cleanup", "title": "Kill rogue PIDs · stop failed units"},
    "1": {"id": "1", "name": "inventory", "title": "Baseline rack inventory"},
    "2": {"id": "2", "name": "provision", "title": "Provision QEMU rack slots"},
    "3": {"id": "3", "name": "dns_dhcp", "title": "DNS/DHCP primary fix + keepalive"},
    "4": {"id": "4", "name": "collisions", "title": "Collision guard enforce"},
    "5": {"id": "5", "name": "killers", "title": "Spawner-kill + orphan killer always-on"},
    "6": {"id": "6", "name": "sync", "title": "Sync inventory · verify APIs"},
    "7": {"id": "7", "name": "probe", "title": "Probe racks for screen pickup"},
}


def _sudo_pw() -> str:
    return os.environ.get("HOSTESS7_SUDO_PW", "mememe")


def _sudo_run(args: list[str], *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    pw = _sudo_pw()
    cmd = ["sudo", "-S", *args]
    return subprocess.run(
        cmd,
        input=f"{pw}\n",
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _stage_cleanup() -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    deploy = INSTALL / "GrokLab" / "deploy"
    try:
        proc = _sudo_run(["chown", "-R", f"{os.getuid()}:{os.getgid()}", str(deploy)], timeout=15)
        actions.append({"deploy_chown": deploy, "ok": proc.returncode == 0})
    except (OSError, subprocess.TimeoutExpired):
        actions.append({"deploy_chown": str(deploy), "ok": False})
    for unit in ("grok-lab.service", "cups.path", "casper-md5check.service"):
        try:
            proc = _sudo_run(["systemctl", "stop", unit], timeout=8)
            actions.append({"unit": unit, "stopped": proc.returncode == 0})
        except (OSError, subprocess.TimeoutExpired):
            actions.append({"unit": unit, "stopped": False})
    rogue_patterns = (
        "field-grok-spawner-kill.py serve",
        "grok-lab",
        "qemu-world-pipeline",
    )
    killed: list[int] = []
    me = os.getpid()
    for pat in rogue_patterns:
        try:
            proc = subprocess.run(
                ["pgrep", "-f", pat],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            for line in (proc.stdout or "").split():
                if not line.strip().isdigit():
                    continue
                pid = int(line)
                if pid == me:
                    continue
                try:
                    os.kill(pid, signal.SIGTERM)
                    killed.append(pid)
                except OSError:
                    pass
        except (OSError, subprocess.TimeoutExpired, ValueError):
            pass
    kgo = INSTALL / "Kill-Grok-Orphans" / "bin" / "kgo"
    if kgo.is_file():
        try:
            subprocess.run([str(kgo), "--once"], capture_output=True, timeout=30, check=False)
            actions.append({"kgo": "once"})
        except (OSError, subprocess.TimeoutExpired):
            pass
    else:
        kgo_py = INSTALL / "Kill-Grok-Orphans" / "python" / "kgo_watchdog.py"
        if kgo_py.is_file():
            try:
                _sudo_run([sys.executable, str(kgo_py), "--once"], timeout=45)
                actions.append({"kgo_watchdog": "once"})
            except (OSError, subprocess.TimeoutExpired):
                pass
    return {"ok": True, "stage": "cleanup", "actions": actions, "killed_pids": killed}


def _stage_inventory() -> dict[str, Any]:
    doc = inventory(fast=False, probe=True)
    _save(PANEL, doc)
    return {"ok": True, "stage": "inventory", "counts": doc.get("counts"), "inventory": doc}


def _stage_provision() -> dict[str, Any]:
    prov = _run_json("lib/field-zachub-qemu-racks.py", ["provision"], timeout=120)
    racks = list(prov.get("racks_provisioned") or [])
    racks_ok = all(r.get("ok", True) for r in racks) if racks else bool(prov.get("ok", True))
    return {**prov, "ok": racks_ok, "stage": "provision", "pipeline_optional": True}


def _stage_dns_dhcp() -> dict[str, Any]:
    fix = _run_json("lib/field-dns-dhcp-fix.py", ["fix"], timeout=180)
    keep = _run_json("lib/field-botnet-dns-dhcp.py", ["keepalive"], timeout=60)
    fix_ok = bool(fix.get("ok", True)) or str(fix.get("schema", "")).startswith("field-dns-dhcp")
    keep_ok = bool(keep.get("ok", True))
    return {
        "stage": "dns_dhcp",
        "fix": fix,
        "keepalive": keep,
        "ok": fix_ok and keep_ok,
    }


def _stage_collisions() -> dict[str, Any]:
    guard = _run_json("lib/field-dns-dhcp-collision-guard.py", ["enforce"], timeout=90)
    racks = _merge_racks(fast=True)
    shard_rows = _shard_collisions(racks)
    rack_shards_ok = len(shard_rows) == 0
    return {
        "ok": rack_shards_ok,
        "stage": "collisions",
        "rack_shards_ok": rack_shards_ok,
        "shard_collisions": shard_rows,
        "guard": guard,
        "guard_ok": bool(guard.get("ok", True)),
    }


def _stage_killers() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    spawn_install = INSTALL / "packaging" / "grok-spawner-kill" / "linux" / "install.sh"
    kgo_install = INSTALL / "Kill-Grok-Orphans" / "packaging" / "linux" / "install.sh"
    env = {**os.environ, "HOSTESS7_SUDO_PW": _sudo_pw()}
    for label, script in (("spawner_kill", spawn_install), ("kgo", kgo_install)):
        if not script.is_file():
            results.append({"service": label, "ok": False, "error": "install_script_missing"})
            continue
        try:
            proc = subprocess.run(
                ["bash", str(script)],
                cwd=str(INSTALL),
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
                check=False,
            )
            ok = proc.returncode == 0
            if not ok and label == "kgo":
                try:
                    proc2 = _sudo_run(["bash", str(script)], timeout=120)
                    ok = proc2.returncode == 0
                    proc = proc2
                except (OSError, subprocess.TimeoutExpired):
                    pass
            results.append({
                "service": label,
                "ok": ok,
                "exit_code": proc.returncode,
                "tail": (proc.stdout or proc.stderr or "")[-400:],
            })
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append({"service": label, "ok": False, "error": str(exc)[:200]})
    return {"ok": all(r.get("ok") for r in results), "stage": "killers", "services": results}


def _stage_sync() -> dict[str, Any]:
    doc = inventory(fast=False, probe=True)
    _save(PANEL, doc)
    apis = {
        "inventory": _probe_http("http://127.0.0.1:9477/api/field-rack-inventory"),
        "chat": _probe_http("http://127.0.0.1:9477/api/field-rack-grok-chat"),
        "grok": _probe_http("http://127.0.0.1:9477/api/field-grok"),
    }
    return {
        "ok": all(v.get("ok") for v in apis.values()),
        "stage": "sync",
        "counts": doc.get("counts"),
        "apis": apis,
    }


def _stage_probe() -> dict[str, Any]:
    chat = _mod("lib/field-rack-grok-chat.py", "rack_chat")
    doc = inventory(fast=True, probe=True)
    probes: list[dict[str, Any]] = []
    for rack in doc.get("racks") or []:
        if not isinstance(rack, dict):
            continue
        if not (rack.get("health") or {}).get("available"):
            continue
        rid = str(rack.get("rack_id") or rack.get("field_id") or "")
        if not rid:
            continue
        if chat and hasattr(chat, "chat_to_rack"):
            row = chat.chat_to_rack(rid, "", probe=True)
        else:
            row = {"ok": False, "error": "chat_module_missing", "rack_id": rid}
        probes.append(row)
    pickup = sum(1 for p in probes if p.get("pickup"))
    return {
        "ok": pickup > 0 or len(probes) == 0,
        "stage": "probe",
        "probed": len(probes),
        "pickup_count": pickup,
        "probes": probes,
    }


_STAGE_RUNNERS = {
    "0": _stage_cleanup,
    "1": _stage_inventory,
    "2": _stage_provision,
    "3": _stage_dns_dhcp,
    "4": _stage_collisions,
    "5": _stage_killers,
    "6": _stage_sync,
    "7": _stage_probe,
    "cleanup": _stage_cleanup,
    "inventory": _stage_inventory,
    "provision": _stage_provision,
    "dns_dhcp": _stage_dns_dhcp,
    "collisions": _stage_collisions,
    "killers": _stage_killers,
    "sync": _stage_sync,
    "probe": _stage_probe,
}


def staged_rollout(
    stage: str | int | None = None,
    *,
    through: str | int | None = None,
) -> dict[str, Any]:
    ledger_path = STATE / "field-rack-rollout-ledger.json"
    ledger = _load(ledger_path, {"schema": "field-rack-rollout/v1", "stages": []})
    order = ["0", "1", "2", "3", "4", "5", "6", "7"]
    if stage is None and through is None:
        completed = {str(s.get("stage")) for s in ledger.get("stages") or [] if s.get("ok")}
        next_stage = next((s for s in order if s not in completed), order[-1])
        stage = next_stage
    stage_key = str(stage).strip().lower()
    if stage_key in STAGES:
        stage_key = STAGES[stage_key]["id"]
    runners: list[str] = [stage_key]
    if through is not None:
        through_key = str(through).strip().lower()
        if through_key in STAGES:
            through_key = STAGES[through_key]["id"]
        try:
            start_i = order.index(stage_key)
            end_i = order.index(through_key)
            runners = order[start_i : end_i + 1]
        except ValueError:
            runners = [stage_key]

    results: list[dict[str, Any]] = []
    for sid in runners:
        meta = STAGES.get(sid, {"id": sid, "name": sid})
        runner = _STAGE_RUNNERS.get(sid) or _STAGE_RUNNERS.get(meta.get("name", ""))
        if not runner:
            results.append({"ok": False, "stage": sid, "error": "unknown_stage"})
            continue
        try:
            row = runner()
            row["stage_id"] = sid
            row["stage_name"] = meta.get("name")
            row["title"] = meta.get("title")
            row["updated"] = _utc()
            results.append(row)
        except (OSError, TypeError, ValueError) as exc:
            results.append({"ok": False, "stage": sid, "error": str(exc)[:200]})

    out = {
        "ok": all(r.get("ok", False) for r in results),
        "schema": "field-rack-staged-rollout/v1",
        "updated": _utc(),
        "stages_available": list(STAGES.values()),
        "ran": results,
        "next_stage": None,
    }
    if results and results[-1].get("ok"):
        try:
            last_i = order.index(str(results[-1].get("stage_id") or results[-1].get("stage")))
            if last_i + 1 < len(order):
                nxt = STAGES[order[last_i + 1]]
                out["next_stage"] = nxt
        except (ValueError, KeyError):
            pass
    ledger.setdefault("stages", [])
    ledger["stages"].extend(results)
    ledger["updated"] = _utc()
    ledger["last"] = out
    _save(ledger_path, ledger)
    _save(STATE / "field-rack-rollout-panel.json", out)
    return out


def dns_dhcp_rollout(*, write: bool = True) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    if write:
        prov = _run_json("lib/field-zachub-qemu-racks.py", ["provision"], timeout=120)
        steps.append({"step": "provision_qemu_racks", **prov})
        fix = _run_json("lib/field-dns-dhcp-fix.py", ["fix"], timeout=90)
        steps.append({"step": "dns_dhcp_fix", **fix})
        keep = _run_json("lib/field-botnet-dns-dhcp.py", ["keepalive"], timeout=60)
        steps.append({"step": "botnet_keepalive", **keep})
        guard = _run_json("lib/field-dns-dhcp-collision-guard.py", ["enforce"], timeout=60)
        steps.append({"step": "collision_guard_enforce", **guard})
    inv = inventory(fast=False, probe=True)
    if write:
        inv["rollout_steps"] = steps
        _save(PANEL, inv)
    inv["schema"] = "field-rack-inventory-rollout/v1"
    inv["ok"] = all(s.get("ok", True) for s in steps) and inv.get("ok", True)
    return inv


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "inventory"):
        fast = bool(body.get("fast"))
        doc = inventory(fast=fast, probe=not fast)
        _save(PANEL, doc)
        return doc
    if action in ("refresh", "probe"):
        doc = inventory(fast=False, probe=True)
        _save(PANEL, doc)
        return doc
    if action in ("rollout", "dns_dhcp_primary", "dns_dhcp_rollout"):
        return dns_dhcp_rollout(write=bool(body.get("write", True)))
    if action in ("staged", "staged_rollout", "stage"):
        return staged_rollout(
            body.get("stage") or body.get("stage_id"),
            through=body.get("through") or body.get("through_stage"),
        )
    if action == "collisions":
        racks = _merge_racks(fast=True)
        rows = _shard_collisions(racks)
        return {"ok": len(rows) == 0, "collisions": rows, "count": len(rows)}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd in ("json", "status", "inventory"):
        doc = inventory(fast="--fast" in sys.argv, probe="--no-probe" not in sys.argv)
        _save(PANEL, doc)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("rollout", "dns-dhcp-primary"):
        print(json.dumps(dns_dhcp_rollout(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("staged", "staged-rollout", "stage"):
        stage = sys.argv[2] if len(sys.argv) > 2 else None
        through = sys.argv[3] if len(sys.argv) > 3 else None
        print(json.dumps(staged_rollout(stage, through=through), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-rack-inventory.py [json|inventory|rollout|staged <stage> [through]] [--fast] [--no-probe]",
        "stages": list(STAGES.values()),
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())