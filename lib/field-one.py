#!/usr/bin/env pythong
"""Field 1 — everything on one field. Storage, sync, compaction, restore.

Single canonical surface for Hostess7, Queen, and NEXUS panel.
No Hostess7-local ZAC shards — World_Redata WRDT1/WRZC1 owns compaction.

  pythong lib/field-one.py json
  pythong lib/field-one.py sync
  pythong lib/field-one.py compact
  pythong lib/field-one.py restore [--apply] [--confirm]
  pythong lib/field-one.py convert [--apply] [--confirm]
"""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
DOCTRINE = INSTALL / "data" / "field-one-doctrine.json"
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-one-absorb-panel.json"
REGISTRY = STATE / "field-device-registry.json"
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))


def _import_py(name: str, path: Path) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sg_paths() -> Any | None:
    return _import_py("sg_paths", INSTALL / "lib" / "sg_paths.py")


def _converter() -> Any | None:
    return _import_py("field_drive_converter", INSTALL / "lib" / "field-drive-converter.py")


def _unified_device() -> Any | None:
    return _import_py("field_unified_device", INSTALL / "lib" / "field-unified-device.py")


def _hostess7_root() -> Path:
    sp = _sg_paths()
    if sp and hasattr(sp, "hostess7_root"):
        return sp.hostess7_root()
    env = os.environ.get("HOSTESS7_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    nested = INSTALL / "Hostess7"
    if nested.is_dir():
        return nested.resolve()
    legacy = SG / "Hostess7"
    return legacy.resolve() if legacy.is_dir() else nested.resolve()


def storage_root() -> Path:
    sp = _sg_paths()
    if sp and hasattr(sp, "hostess7_team_field"):
        return sp.hostess7_team_field()
    return _hostess7_root() / "cache" / "fieldstorage"


def _team_drive_script() -> Path:
    return _hostess7_root() / "scripts" / "field_team_drive.py"


def _run_team(cmd: str, *extra: str, timeout: int = 3600) -> dict[str, Any]:
    script = _team_drive_script()
    if not script.is_file():
        return {"ok": False, "error": "team_drive_missing", "path": str(script)}
    env = {**os.environ, "HOSTESS7_ROOT": str(_hostess7_root())}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), cmd, *extra],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=str(_hostess7_root()),
        )
        tail = ((proc.stdout or "") + (proc.stderr or ""))[-4000:]
        return {"ok": proc.returncode == 0, "returncode": proc.returncode, "tail": tail}
    except (subprocess.SubprocessError, OSError) as exc:
        return {"ok": False, "error": str(exc)}


def _converter_call(fn_name: str, **kwargs: Any) -> dict[str, Any]:
    conv = _converter()
    if not conv:
        return {"ok": False, "error": "field_drive_converter_missing"}
    fn = getattr(conv, fn_name, None)
    if not callable(fn):
        return {"ok": False, "error": f"converter_missing_{fn_name}"}
    try:
        out = fn(**kwargs)
        return out if isinstance(out, dict) else {"ok": True, "result": out}
    except (OSError, ValueError, TypeError) as exc:
        return {"ok": False, "error": str(exc)}


def sync(*, storage_only: bool = False) -> dict[str, Any]:
    args = ("--storage-only",) if storage_only else ()
    rep = _run_team("sync", *args)
    return {"action": "sync", "storage_root": str(storage_root()), **rep}


def compact() -> dict[str, Any]:
    rep = _converter_call("scan")
    return {"action": "compact", "alias": "scan", **rep}


def scan() -> dict[str, Any]:
    rep = _converter_call("scan")
    return {"action": "scan", **rep}


def restore(*, apply: bool = False, confirm: bool = False) -> dict[str, Any]:
    rep = _converter_call("restore_out", apply=apply, confirm=confirm)
    return {"action": "restore", "apply": apply, **rep}


def convert(*, apply: bool = False, confirm: bool = False) -> dict[str, Any]:
    rep = _converter_call("convert", apply=apply, confirm=confirm)
    return {"action": "convert", "apply": apply, **rep}


def defield() -> dict[str, Any]:
    rep = _converter_call("defield_audit")
    return {"action": "defield", **rep}


def refield() -> dict[str, Any]:
    rep = _converter_call("refield")
    return {"action": "refield", **rep}


def install_phase(*, apply: bool = False, confirm: bool = False) -> dict[str, Any]:
    rep = _converter_call("install_phase", apply=apply, confirm=confirm)
    return {"action": "install-phase", "apply": apply, **rep}


def team_status() -> dict[str, Any]:
    rep = _run_team("status", timeout=120)
    return {"action": "team-status", **rep}


def posture() -> dict[str, Any]:
    sp = _sg_paths()
    conv = _converter()
    board: dict[str, Any] = {}
    udev = _unified_device()
    if udev and hasattr(udev, "board"):
        try:
            board = udev.board()
        except (OSError, TypeError):
            board = {}
    converter_posture = conv.posture() if conv and hasattr(conv, "posture") else {}
    team = _run_team("status", timeout=60) if _team_drive_script().is_file() else {"skipped": True}
    doc = _load_json(DOCTRINE, {})
    absorb_panel = _load_json(PANEL, {})
    return {
        "schema": "field-one/v1",
        "title": "Field 1",
        "motto": doc.get("motto", "Everything on one field"),
        "field_one": True,
        "one_field_whole_device": True,
        "universal_ingress": bool(doc.get("universal_ingress", True)),
        "outside_network_absorbed": bool(doc.get("outside_network_absorbed", True)),
        "hub": field_one_hub(),
        "absorb": {
            "ok": absorb_panel.get("ok"),
            "connected_devices": absorb_panel.get("connected_devices"),
            "registry_devices": absorb_panel.get("registry_devices"),
            "outside_absorbed": absorb_panel.get("outside_absorbed"),
            "updated": absorb_panel.get("updated"),
            "api": "/api/field-one/absorb",
        },
        "storage_root": str(storage_root()),
        "hostess7_root": str(_hostess7_root()),
        "team_field": str(sp.hostess7_team_field()) if sp else str(storage_root()),
        "world_redata": str(sp.world_redata_root()) if sp else None,
        "converter": converter_posture,
        "team": team,
        "board": board,
        "commands": doc.get("commands", {}),
    }


def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "NEXUS_INSTALL_ROOT": str(INSTALL),
        "NEXUS_STATE_DIR": str(STATE),
        "NEXUS_FIELD_DNS_ANY_IP": "1",
        "NEXUS_FIELD_DHCP_ANY_IP": "1",
        "NEXUS_FIELD_COLLISION_SOFT_INGRESS": "1",
        "NEXUS_FIELD_DHCP_SOFT_INGRESS": "1",
        "NEXUS_FIELD_DHCP_FOREIGN_PROBE": "0",
        "NEXUS_FIELD_INTERNET_UNRESTRICT": "0",
        "NEXUS_TRUTH_KEEPALIVE_FAST": "1",
    }


def _run_json(rel: str, args: list[str], *, timeout: float = 90.0) -> dict[str, Any]:
    py = INSTALL / rel
    if not py.is_file():
        return {"ok": False, "error": "missing", "script": rel}
    try:
        proc = subprocess.run(
            [sys.executable, str(py), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=_env(),
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            doc = json.loads(raw)
            if isinstance(doc, dict):
                doc.setdefault("ok", proc.returncode == 0)
                return doc
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{"):
                doc = json.loads(line)
                if isinstance(doc, dict):
                    doc.setdefault("ok", proc.returncode == 0)
                    return doc
        return {"ok": proc.returncode == 0, "stdout": raw[:300]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "script": rel}
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": str(exc), "script": rel}


def field_one_hub() -> dict[str, Any]:
    doc = _load_json(DOCTRINE, {})
    hub = dict(doc.get("hub") or {})
    hub.setdefault("id", "field-1")
    hub.setdefault("dns", ["127.0.0.1", "192.168.47.1"])
    hub.setdefault("dhcp", ["192.168.47.1", "0.0.0.0"])
    hub.setdefault("truth", "127.0.0.1")
    hub.setdefault("loopback", "127.0.0.1")
    hub.setdefault("field_lan", (hub.get("field_lan") or hub.get("queen_lan")) or "192.168.47.1")
    hub.setdefault("queen_lan", hub["field_lan"])  # compat alias
    hub.setdefault("wildcard", "0.0.0.0/0")
    return hub


def _absorb_outside_devices(*, write: bool = True) -> dict[str, Any]:
    """Register outside-network and planetary devices into Field 1 registry."""
    hub = field_one_hub()
    hub_dns = hub.get("dns") or ["127.0.0.1"]
    truth = str(hub.get("truth") or hub_dns[0])

    reg_doc = _load_json(REGISTRY, {"devices": [], "policy": {}})
    policy = dict(reg_doc.get("policy") or {})
    policy.update({
        "field_one_sink": True,
        "outside_network_absorbed": True,
        "never_evict_dhcp_sourced": True,
        "dhcp_lease_is_real": True,
        "ai_evict_stale": False,
    })
    reg_doc["policy"] = policy

    by_id: dict[str, dict[str, Any]] = {}
    for d in reg_doc.get("devices") or []:
        if isinstance(d, dict) and d.get("id"):
            row = dict(d)
            row["field_one_sink"] = True
            row.setdefault("route_to", "field-1")
            by_id[str(row["id"])] = row

    absorbed = 0
    sources_checked: list[str] = []

    edge_panel = _load_json(STATE / "field-edge-blast-panel.json", {})
    for edge in edge_panel.get("edge_hosts") or []:
        if not isinstance(edge, dict):
            continue
        eid = str(edge.get("edge_id") or "")
        if not eid:
            continue
        by_id[eid] = {
            "id": eid,
            "kind": "edge_host",
            "bind": edge.get("bind"),
            "outside_network": bool(edge.get("outside_network")),
            "field_one_sink": True,
            "route_to": "field-1",
            "dns": [truth],
            "dhcp": edge.get("dhcp_server") or hub.get("queen_lan"),
            "sources": ["field-rescue-ingress", "field-one-absorb"],
            "real": True,
            "fake": False,
            "active": True,
            "quarantine": bool(edge.get("outside_network")),
            "last_seen": _utc(),
            "last_timestamp": _utc(),
        }
        absorbed += 1
    if edge_panel:
        sources_checked.append("edge_blast")

    gh = _load_json(STATE / "field-github-planet-sweep-panel.json", {})
    gh_index = gh.get("github_index") or {}
    for row in (gh_index.get("dhcp_index") or [])[:500]:
        if not isinstance(row, dict):
            continue
        did = str(row.get("lease_id") or row.get("mac") or row.get("ip") or "")
        if not did:
            continue
        key = f"gh-dhcp-{did.replace(':', '')[:24]}"
        by_id[key] = {
            "id": key,
            "kind": "github_planet_dhcp",
            "ip": row.get("ip"),
            "mac": row.get("mac"),
            "hostname": row.get("hostname"),
            "repo_slug": row.get("repo_slug"),
            "outside_network": True,
            "field_one_sink": True,
            "route_to": "field-1",
            "dns": [truth],
            "sources": ["github-planet-sweep", "field-one-absorb"],
            "real": True,
            "fake": False,
            "active": True,
            "quarantine": bool(row.get("quarantine", True)),
            "last_seen": _utc(),
            "last_timestamp": _utc(),
        }
        absorbed += 1
    if gh:
        sources_checked.append("github_planet_sweep")

    census = _load_json(STATE / "census-field-panel.json", {})
    for rec in (census.get("records") or census.get("entries") or [])[:500]:
        if not isinstance(rec, dict):
            continue
        cid = str(rec.get("id") or rec.get("ip") or "")
        if not cid:
            continue
        key = f"census-{cid.replace('.', '-')[:32]}"
        by_id[key] = {
            "id": key,
            "kind": "census",
            "outside_network": True,
            "field_one_sink": True,
            "route_to": "field-1",
            "dns": [truth],
            "sources": ["census-field", "field-one-absorb"],
            "real": True,
            "fake": False,
            "active": True,
            "quarantine": True,
            "last_seen": _utc(),
            "last_timestamp": _utc(),
        }
        absorbed += 1
    if census:
        sources_checked.append("census")

    botnet = _load_json(STATE / "field-botnet-dns-dhcp-panel.json", {})
    for n in (botnet.get("bot_network") or {}).get("nodes") or []:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id") or "")
        if not nid:
            continue
        key = f"botnet-{nid}"
        by_id[key] = {
            "id": key,
            "kind": "botnet_node",
            "node_id": nid,
            "outside_network": True,
            "field_one_sink": True,
            "route_to": "field-1",
            "dns": [truth],
            "sources": ["field-botnet-dns-dhcp", "field-one-absorb"],
            "real": True,
            "fake": False,
            "active": True,
            "quarantine": True,
            "last_seen": _utc(),
            "last_timestamp": _utc(),
        }
        absorbed += 1
    if botnet:
        sources_checked.append("botnet")

    reg_doc["devices"] = list(by_id.values())
    reg_doc["device_count"] = len(reg_doc["devices"])
    reg_doc["field_one_absorbed"] = _utc()
    reg_doc["outside_network_absorbed"] = True
    if write:
        _save(REGISTRY, reg_doc)

    return {
        "ok": True,
        "absorbed": absorbed,
        "registry_devices": reg_doc["device_count"],
        "outside_network": True,
        "field_one_sink": True,
        "hub": hub,
        "sources_checked": sources_checked,
    }


def absorb(*, write: bool = True) -> dict[str, Any]:
    """Universal ingress — anything and everything routes to Field 1."""
    doc = _load_json(DOCTRINE, {})
    hub = field_one_hub()
    steps: list[dict[str, Any]] = []

    cleared = _run_json("lib/field-rescue-ingress.py", ["clear-fakes"], timeout=30)
    steps.append({"step": "clear_fakes", **cleared})
    pool = _run_json("lib/field-rescue-ingress.py", ["expand-pool"], timeout=15)
    steps.append({"step": "expand_pool", **pool})
    edges = _run_json("lib/field-rescue-ingress.py", ["blast-edges"], timeout=45)
    steps.append({"step": "blast_edges", **edges})
    rescue = {
        "ok": bool(cleared.get("ok")),
        "cleared_fakes": cleared,
        "dhcp_pool": pool,
        "edge_blast": edges,
    }

    any_ip = _run_json("lib/field-dns-dhcp-any-ip.py", ["panel"], timeout=20)
    steps.append({"step": "any_ip_wildcard", **any_ip})

    planetary = _load_json(STATE / "field-planetary-dns-dhcp-panel.json", {})
    if not planetary:
        planetary = _run_json("lib/field-planetary-dns-dhcp.py", ["panel"], timeout=45)
    steps.append({"step": "planetary_panel", "ok": bool(planetary), "cached": bool(planetary)})

    outside = _absorb_outside_devices(write=write)
    steps.append({"step": "absorb_outside_devices", **outside})

    device_map = _load_json(STATE / "field-device-map-panel.json", {})
    if not device_map.get("devices"):
        device_map = _run_json("lib/field-device-map.py", ["build"], timeout=45)
    steps.append({"step": "device_map", "ok": bool(device_map), "cached": bool(device_map)})

    collision = _run_json("lib/field-dns-dhcp-collision-guard.py", ["detect"], timeout=25)
    steps.append({"step": "collision_detect", **collision})

    takeover = _run_json("lib/dns-service-takeover.py", ["evaluate"], timeout=20)
    steps.append({"step": "dns_takeover", **takeover})

    dns_zones = _run_json("lib/ammonet-dns-zones.py", ["panel"], timeout=15)
    steps.append({"step": "ammonet_dns", **dns_zones})

    connected = int(
        (device_map.get("summary") or {}).get("connected")
        or outside.get("registry_devices")
        or (rescue.get("cleared_fakes") or {}).get("registry_devices")
        or 0
    )
    edges = edges if isinstance(edges, dict) else (rescue.get("edge_blast") or {})
    out = {
        "ok": bool(rescue.get("ok")),
        "schema": "field-one-absorb/v1",
        "updated": _utc(),
        "title": doc.get("title"),
        "motto": doc.get("motto", "Anything and everything comes to Field 1"),
        "field_one": True,
        "universal_ingress": True,
        "outside_network_absorbed": True,
        "ingress_policy": doc.get("ingress_policy", "quarantine_not_kill"),
        "hub": hub,
        "connected_devices": connected,
        "registry_devices": outside.get("registry_devices"),
        "outside_absorbed": outside.get("absorbed"),
        "wan_edges": edges.get("wan_edges_deployed"),
        "total_edges": edges.get("total_edges_deployed"),
        "sole_authority": collision.get("sole_authority") or {},
        "takeover_phase": takeover.get("phase") or collision.get("takeover_phase"),
        "steps": steps,
        "api": doc.get("api", "/api/field-one"),
    }
    if write:
        _save(PANEL, out)
    return out


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    apply = "--apply" in args
    confirm = "--confirm" in args
    storage_only = "--storage-only" in args
    args = [a for a in args if a not in ("--apply", "--confirm", "--storage-only")]

    mode = (args[0] if args else "json").strip().lower()
    handlers: dict[str, Callable[[], dict[str, Any]]] = {
        "json": posture,
        "status": posture,
        "posture": posture,
        "sync": lambda: sync(storage_only=storage_only),
        "compact": compact,
        "scan": scan,
        "restore": lambda: restore(apply=apply, confirm=confirm),
        "restore-out": lambda: restore(apply=apply, confirm=confirm),
        "convert": lambda: convert(apply=apply, confirm=confirm),
        "defield": defield,
        "defield-audit": defield,
        "refield": refield,
        "install-phase": lambda: install_phase(apply=apply, confirm=confirm),
        "team-status": team_status,
        "team": team_status,
        "absorb": absorb,
        "ingress": absorb,
        "universal-ingress": absorb,
    }
    fn = handlers.get(mode)
    if not fn:
        print(
            "usage: field-one.py [json|sync|compact|scan|restore|convert|defield|refield|install-phase|team-status|absorb] [--apply] [--confirm] [--storage-only]",
            file=sys.stderr,
        )
        return 2
    result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())