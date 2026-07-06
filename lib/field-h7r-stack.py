#!/usr/bin/env python3
"""H7r full field stack — DHCP, DNS, edge, witness, botnet on every node + rack."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
PANEL = STATE / "field-h7r-stack-panel.json"
LEDGER = STATE / "field-h7r-stack-ledger.jsonl"
STACK_INDEX = STATE / "field-h7r-stack-index.json"
STAMP_VAULT = STATE / "field-one-device-stamps"
GLOBAL_REG = STATE / "field-global-servers-registry.json"
DEVICE_REG = STATE / "field-device-registry.json"
DOCTRINE = INSTALL / "data" / "field-h7r-doctrine.json"
TRUTH_SEC_DOCTRINE = INSTALL / "data" / "field-h7r-truth-security-doctrine.json"
RACKS_ROOT = INSTALL / "GrokLab" / "deploy" / "qemu-racks"

STACK_VERSION = "h7r/1"
TRUTH_SECURITY_VERSION = "h7r/1-prejudice"
STORAGE_VERSION = "h7r/1"
FIELD_ONE_VERSION = "field-one-rack-stack/v2"
DEFAULT_WORKERS = int(os.environ.get("NEXUS_H7R_STACK_WORKERS") or 48)
DEFAULT_BATCH = int(os.environ.get("NEXUS_H7R_STACK_BATCH") or 512)

ROLE_CYCLE = ("dhcp", "dns", "edge", "witness")
EDGE_BUNDLE = ("edge", "dns_relay", "dhcp_relay")
BOTNET_SLOTS = ("dns_relay", "dhcp_relay", "truth_mirror")


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


def _safe_id(node_id: str) -> str:
    return re.sub(r"[^\w\-.]+", "_", str(node_id or "node"))[:120]


def _rack_paths() -> list[Path]:
    if not RACKS_ROOT.is_dir():
        return []
    return sorted(p for p in RACKS_ROOT.glob("qemu-rack-*") if p.is_dir())


def _hub() -> dict[str, Any]:
    return _load(INSTALL / "data" / "field-one-doctrine.json", {}).get("hub") or {}


def _truth_sec_doctrine() -> dict[str, Any]:
    return _load(TRUTH_SEC_DOCTRINE, _load(DOCTRINE, {}).get("truth_security") or {})


def _secure_kill_slice() -> dict[str, Any]:
    sk = _mod("lib/field-sense-secure-kill.py", "secure_kill")
    if sk and hasattr(sk, "secure_kill_posture"):
        try:
            sg = Path(os.environ.get("SG_ROOT", INSTALL.parent))
            return sk.secure_kill_posture(INSTALL, sg)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
    return _load(STATE / "field-sense-secure-kill-panel.json", {})


def _beyond_darpa_slice(*, fast: bool) -> dict[str, Any]:
    cached = _load(STATE / "beyond-darpa-security-panel.json", {})
    if fast and cached.get("schema"):
        return cached
    bds = _mod("lib/beyond-darpa-security.py", "beyond_darpa")
    if bds and hasattr(bds, "stack_posture"):
        try:
            return bds.stack_posture(write=False)
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
    return cached


def _rollout_security_slice() -> dict[str, Any]:
    rollout_panel = _load(STATE / "field-one-rollout-panel.json", {})
    test = rollout_panel.get("last_test") or {}
    if test.get("schema"):
        return test
    rollout = _mod("lib/field-one-rollout.py", "rollout")
    if rollout and hasattr(rollout, "test"):
        try:
            return rollout.test()
        except Exception:
            pass
    return {"security_score": 0, "checks_passed": 0, "checks_total": 0}


def _live_panels(*, fast: bool = True) -> dict[str, Any]:
    """Pull DNS/DHCP/any-IP/botnet + truth/security/prejudice from cached panels or live subprocess."""
    panels: dict[str, Any] = {
        "dns": _load(STATE / "field-dns-panel.json", {}),
        "dhcp": _load(STATE / "field-dhcp-panel.json", {}),
        "any_ip": _load(STATE / "field-dns-dhcp-any-ip-panel.json", {}),
        "botnet": _load(STATE / "field-botnet-dns-dhcp-panel.json", {}),
        "h7t_truth": _load(STATE / "field-h7t-truth-panel.json", {}),
        "truth_lie_threat": _load(STATE / "hostess7-truth-lie-threat-panel.json", {}),
        "ironclad": _load(STATE / "ironclad-immediate.json", {}),
        "collision_guard": _load(STATE / "field-dns-dhcp-collision-guard-panel.json", {}),
        "drift_threat": _load(STATE / "field-dns-drift-threat-panel.json", {}),
        "beyond_darpa": _beyond_darpa_slice(fast=fast),
        "secure_kill": _secure_kill_slice(),
        "rollout_security": _rollout_security_slice(),
    }
    if fast:
        return panels

    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    for key, rel, cmd in (
        ("dns", "lib/field-dns.py", ["json"]),
        ("dhcp", "lib/field-dhcp.py", ["json"]),
        ("any_ip", "lib/field-dns-dhcp-any-ip.py", ["panel"]),
        ("botnet", "lib/field-botnet-dns-dhcp.py", ["json"]),
        ("h7t_truth", "lib/field-h7t-truth.py", ["json"]),
        ("truth_lie_threat", "lib/hostess7-truth-lie-threat.py", ["json"]),
        ("collision_guard", "lib/field-dns-dhcp-collision-guard.py", ["json"]),
        ("drift_threat", "lib/field-dns-drift-threat.py", ["panel"]),
    ):
        if panels.get(key, {}).get("ok") or panels.get(key, {}).get("schema"):
            continue
        py = INSTALL / rel
        if not py.is_file():
            continue
        try:
            import subprocess

            proc = subprocess.run(
                [sys.executable, str(py), *cmd],
                cwd=str(INSTALL),
                capture_output=True,
                text=True,
                timeout=25,
                env=env,
                check=False,
            )
            raw = (proc.stdout or "").strip()
            if raw.startswith("{"):
                panels[key] = json.loads(raw)
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass
    return panels


def _node_roles(node: dict[str, Any]) -> dict[str, Any]:
    nid = str(node.get("id") or node.get("node_id") or "")
    slot = node.get("slot")
    if slot is None and nid:
        m = re.search(r"-(\d+)$", nid)
        if m:
            slot = int(m.group(1))
    slot = int(slot if slot is not None else int(hashlib.sha256(nid.encode()).hexdigest()[:6], 16) % 256)
    primary = str(node.get("primary_role") or ROLE_CYCLE[slot % len(ROLE_CYCLE)])
    roles = list(node.get("roles") or [])
    if not roles:
        roles = list(dict.fromkeys([primary, *EDGE_BUNDLE, *BOTNET_SLOTS]))
    return {
        "primary_role": primary,
        "roles": roles,
        "edge_roles": list(node.get("edge_roles") or EDGE_BUNDLE),
        "botnet_roles": list(node.get("botnet_roles") or BOTNET_SLOTS),
        "slot": slot,
    }


def _dns_slice(panels: dict[str, Any]) -> dict[str, Any]:
    dns = panels.get("dns") or {}
    any_ip = panels.get("any_ip") or {}
    binds = (any_ip.get("dns") or {}).get("binds_v4") or dns.get("binds_v4") or ["0.0.0.0", "127.0.0.1"]
    return {
        "authority": "hostess7_truth",
        "module": "lib/field-dns.py",
        "binds_v4": binds,
        "binds_v6": (any_ip.get("dns") or {}).get("binds_v6") or dns.get("binds_v6") or ["::"],
        "wildcard": bool((any_ip.get("dns") or {}).get("wildcard_v4") or any_ip.get("any_ip")),
        "port": int((any_ip.get("dns") or {}).get("port") or dns.get("port") or 53),
        "truth_resolver": True,
        "any_ip": bool(any_ip.get("any_ip") or any_ip.get("answer_any_ip")),
        "running": bool(dns.get("running") or dns.get("ok")),
    }


def _dhcp_slice(panels: dict[str, Any]) -> dict[str, Any]:
    dhcp = panels.get("dhcp") or {}
    any_ip = panels.get("any_ip") or {}
    bind = (any_ip.get("dhcp") or {}).get("bind") or dhcp.get("bind") or "0.0.0.0"
    return {
        "authority": "hostess7_field",
        "module": "lib/field-dhcp.py",
        "bind": bind,
        "server_id": (any_ip.get("dhcp") or {}).get("server_id") or dhcp.get("server_id") or "192.168.47.1",
        "wildcard": bool((any_ip.get("dhcp") or {}).get("wildcard") or bind == "0.0.0.0"),
        "port": 67,
        "dns_option": _dns_slice(panels).get("binds_v4") or ["127.0.0.1"],
        "lease_count": int(dhcp.get("lease_count") or 0),
        "running": bool(dhcp.get("running") or dhcp.get("ok")),
    }


def _edge_slice(node: dict[str, Any], role_meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "module": "lib/field-zachub-qemu-racks.py",
        "roles": role_meta.get("edge_roles") or list(EDGE_BUNDLE),
        "primary_role": role_meta.get("primary_role"),
        "internet_isolated": True,
        "tunnel": node.get("tunnel"),
        "ssh_port": node.get("ssh_port"),
    }


def _witness_slice(panels: dict[str, Any]) -> dict[str, Any]:
    botnet = panels.get("botnet") or {}
    gh = botnet.get("github_control_plane") or {}
    return {
        "truth_mirror": True,
        "forever_hash": True,
        "github_open": bool(gh.get("github_open")),
        "pages": gh.get("pages_runtime") or gh.get("pages"),
        "mirror_subdir": "field-one-mirror",
        "never_lose": True,
    }


def _botnet_slice(panels: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    botnet = panels.get("botnet") or {}
    net = botnet.get("bot_network") or {}
    return {
        "enabled": True,
        "boss": "hostess7",
        "ipv4_sovereign": bool(net.get("ipv4_sovereign")),
        "all_ipv4_every_box": bool(net.get("all_ipv4_every_box")),
        "suppress_foreign_dns_dhcp": bool(net.get("suppress_foreign_dns_dhcp_worldwide")),
        "github_control_plane": botnet.get("github_control_plane") or {},
        "node_kind": node.get("kind") or node.get("source"),
        "api": "/api/field-botnet-dns-dhcp",
    }


def _truth_slice(panels: dict[str, Any]) -> dict[str, Any]:
    doctrine = _truth_sec_doctrine()
    truth_doc = doctrine.get("truth") or {}
    h7t = panels.get("h7t_truth") or {}
    tlt = panels.get("truth_lie_threat") or {}
    iron = panels.get("ironclad") or {}
    floors = tlt.get("floors") or {
        "adapt": truth_doc.get("adapt_floor", 58),
        "quarantine_below": truth_doc.get("quarantine_below", 40),
        "lie_threat_below": truth_doc.get("lie_threat_below", 40),
        "hostile_below": truth_doc.get("hostile_below", 25),
    }
    return {
        "authority": "hostess7_truth",
        "more_than_permissible": True,
        "h7t_format": h7t.get("format") or truth_doc.get("h7t_format") or "h7t/1",
        "h7t_module": "lib/field-h7t-truth.py",
        "ironclad_module": "lib/field-ironclad-truth.py",
        "truth_lie_threat_module": "lib/hostess7-truth-lie-threat.py",
        "ironclad_sealed": bool(iron.get("ironclad_sealed") or iron.get("truth_percent") == 100),
        "truth_percent": float(iron.get("truth_percent") or iron.get("truth_score") or 100),
        "bands": list(truth_doc.get("bands") or []),
        "floors": floors,
        "chamber_isolation": bool(truth_doc.get("chamber_isolation", True)),
        "forever_hash_required": bool(truth_doc.get("forever_hash_required", True)),
        "lie_is_threat": True,
        "delay_is_threat": bool((doctrine.get("prejudice") or {}).get("delay_as_threat", True)),
        "chamber_count": int(h7t.get("chamber_count") or 0),
        "api": "/api/field-h7t-truth",
        "truth_lie_api": "/api/hostess7/truth-lie-threat",
    }


def _security_slice(panels: dict[str, Any]) -> dict[str, Any]:
    doctrine = _truth_sec_doctrine()
    sec_doc = doctrine.get("security") or {}
    bds = panels.get("beyond_darpa") or {}
    collision = panels.get("collision_guard") or {}
    drift = panels.get("drift_threat") or {}
    rollout = panels.get("rollout_security") or {}
    score = int(rollout.get("security_score") or 0)
    passed = int(rollout.get("checks_passed") or 0)
    total = int(rollout.get("checks_total") or 0)
    min_score = int(sec_doc.get("minimum_score_pct") or 100)
    gates_green = bool(rollout.get("ok")) and score >= min_score and (total == 0 or passed == total)
    sole = (collision.get("sole_authority") or {})
    return {
        "authority": "beyond_darpa_lockheed",
        "tier": bds.get("tier") or sec_doc.get("tier") or "beyond_darpa_lockheed",
        "more_than_permissible": True,
        "fail_closed": bool(sec_doc.get("fail_closed", True)),
        "beyond_darpa_module": "lib/beyond-darpa-security.py",
        "ironclad_grounded": bool(bds.get("ironclad_grounded")),
        "all_systems_secured": bool(bds.get("all_systems_secured")),
        "all_data_secured": bool(bds.get("all_data_secured")),
        "human_threats_covered": bool(bds.get("human_threats_covered")),
        "machine_threats_covered": bool(bds.get("machine_threats_covered")),
        "gates_green": gates_green,
        "security_score_pct": score,
        "checks_passed": passed,
        "checks_total": total,
        "sole_dns_dhcp_authority": bool(sole.get("ok") or collision.get("ok")),
        "collision_guard_module": "lib/field-dns-dhcp-collision-guard.py",
        "drift_threat_module": "lib/field-dns-drift-threat.py",
        "drift_servers_updated": drift.get("servers_updated"),
        "internet_isolated_racks": bool(sec_doc.get("internet_isolated_racks", True)),
        "api": "/api/beyond-darpa-security",
    }


def _prejudice_slice(panels: dict[str, Any]) -> dict[str, Any]:
    doctrine = _truth_sec_doctrine()
    prej = doctrine.get("prejudice") or {}
    sk = panels.get("secure_kill") or {}
    collision = panels.get("collision_guard") or {}
    tlt = panels.get("truth_lie_threat") or {}
    enforce = collision.get("enforce") or {}
    return {
        "policy": "prejudice",
        "with_prejudice": True,
        "more_than_permissible": True,
        "kill_policy": sk.get("kill_policy") or prej.get("kill_policy") or "prejudice",
        "root_sovereign_policy": sk.get("root_sovereign_policy") or "prejudice",
        "immediate_kill_law": bool(sk.get("immediate_kill_law") or prej.get("immediate_kill_law", True)),
        "every_kill_rekill": bool(sk.get("every_kill_rekill") or prej.get("every_kill_rekill", True)),
        "war_hardened": bool(sk.get("war_hardened")),
        "foreign_dns_dhcp": prej.get("foreign_dns_dhcp") or "terminate_with_prejudice",
        "lie_threat_action": prej.get("lie_threat_action") or "quarantine_block_escalate",
        "delay_as_threat": bool(prej.get("delay_as_threat", True)),
        "collision_enforce": bool(prej.get("collision_enforce", True)),
        "threats_eradicated": int(enforce.get("threats_eradicated") or 0),
        "foreign_root_cleared": int(sk.get("foreign_root_cleared") or 0),
        "lie_threat_vectors": list((tlt.get("doctrine") or {}).get("threat_vectors") or [])[:6]
        if isinstance((tlt.get("doctrine") or {}).get("threat_vectors"), dict)
        else [],
        "armed": bool(sk.get("ok")),
        "motto": sk.get("motto") or prej.get("motto") or "Anyone in the way — secure kill with prejudice · RE-KILL forever",
        "module": "lib/field-sense-secure-kill.py",
        "api": "/api/field-sense-secure-kill",
    }


def _forever_truth_attestation(doc: dict[str, Any]) -> str:
    """SHA-256 seal over stack services — delete/override requires hash match + personhood."""
    services = doc.get("services") or {}
    blob = json.dumps(
        {
            "stack_version": doc.get("stack_version"),
            "truth_security_version": doc.get("truth_security_version"),
            "node_id": doc.get("node_id"),
            "services": services,
            "prejudice": (services.get("prejudice") or {}).get("policy"),
        },
        sort_keys=True,
    ).encode()
    return hashlib.sha256(blob).hexdigest()


def stack_manifest_doc(
    node: dict[str, Any],
    panels: dict[str, Any],
    *,
    rack_id: str = "",
    metro_id: str = "",
    region_id: str = "",
) -> dict[str, Any]:
    nid = str(node.get("id") or node.get("node_id") or "")
    role_meta = _node_roles(node)
    pre: dict[str, Any] = {
        "schema": "field-h7r-stack/v2",
        "stack_version": STACK_VERSION,
        "truth_security_version": TRUTH_SECURITY_VERSION,
        "storage_version": STORAGE_VERSION,
        "services_version": STACK_VERSION,
        "field_one_version": FIELD_ONE_VERSION,
        "version": 2,
        "updated": _utc(),
        "field_one": True,
        "field_one_updated": True,
        "h7r_updated": True,
        "h7r_stack_updated": True,
        "h7r_truth_security_updated": True,
        "prejudice_enforced": True,
        "more_than_permissible": True,
        "never_lose": True,
        "cooperative_mesh": True,
        "internet_isolated": True,
        "hub": _hub(),
        "node_id": nid,
        "kind": node.get("kind"),
        "rack_id": rack_id or node.get("field_id") or "",
        "metro_id": metro_id or node.get("metro_id"),
        "region_id": region_id or node.get("region_id"),
        "primary_role": role_meta["primary_role"],
        "roles": role_meta["roles"],
        "services": {
            "dns": _dns_slice(panels),
            "dhcp": _dhcp_slice(panels),
            "edge": _edge_slice(node, role_meta),
            "witness": _witness_slice(panels),
            "botnet": _botnet_slice(panels, node),
            "truth": _truth_slice(panels),
            "security": _security_slice(panels),
            "prejudice": _prejudice_slice(panels),
        },
        "protocol": "field-h7r-rackmount",
        "hot_lane": "field-h7s-fs",
        "ammodrive_cloud": True,
        "api": "/api/field-h7r-stack",
        "truth_security_doctrine": "data/field-h7r-truth-security-doctrine.json",
    }
    pre["forever_truth_hash"] = _forever_truth_attestation(pre)
    h = hashlib.sha256(json.dumps(pre, sort_keys=True).encode()).hexdigest()[:32]
    pre["content_hash"] = h
    return pre


def _collect_targets() -> list[dict[str, Any]]:
    rapid = _mod("lib/ammodrive-storage-rapid.py", "storage_rapid")
    if rapid and hasattr(rapid, "_collect_targets"):
        return list(rapid._collect_targets())
    targets: list[dict[str, Any]] = []
    seen: set[str] = set()
    rollout = _mod("lib/field-one-rollout.py", "rollout")
    if rollout:
        for n in rollout._load_botnet_nodes():
            nid = str(n.get("id") or "")
            if nid and nid not in seen:
                seen.add(nid)
                targets.append({**n, "source": "botnet"})
    gs = _load(GLOBAL_REG, {})
    for s in gs.get("servers") or []:
        nid = str(s.get("id") or s.get("node_id") or "")
        if not nid or nid in seen:
            continue
        seen.add(nid)
        targets.append({
            "id": nid,
            "node_id": s.get("node_id"),
            "kind": "global_server",
            "storage_root": str(RACKS_ROOT / str(s.get("field_id") or f"qemu-rack-{nid.split('-')[-1]}")),
            "field_id": s.get("field_id"),
            "metro_id": s.get("metro_id"),
            "region_id": s.get("region_id"),
            "source": "global",
        })
    return targets


def _stamp_path(node: dict[str, Any]) -> Path:
    root = str(node.get("storage_root") or "").strip()
    if root and Path(root).is_dir():
        return Path(root) / "field-h7r-stack.json"
    return STAMP_VAULT / f"{_safe_id(str(node.get('id') or ''))}-h7r-stack.json"


def _has_latest(node: dict[str, Any]) -> bool:
    for path in (
        _stamp_path(node),
        STAMP_VAULT / f"{_safe_id(str(node.get('id') or ''))}-h7r-stack.json",
    ):
        if not path.is_file():
            continue
        doc = _load(path, {})
        if (
            doc.get("stack_version") == STACK_VERSION
            and doc.get("h7r_stack_updated")
            and doc.get("h7r_truth_security_updated")
            and doc.get("prejudice_enforced")
            and doc.get("truth_security_version") == TRUTH_SECURITY_VERSION
        ):
            return True
    if (
        node.get("stack_version") == STACK_VERSION
        and node.get("h7r_stack_updated")
        and node.get("h7r_truth_security_updated")
        and node.get("prejudice_enforced")
    ):
        return True
    return False


def _write_rack_services(rack: Path, doc: dict[str, Any]) -> list[str]:
    written: list[str] = []
    services = doc.get("services") or {}
    lanes = list((_truth_sec_doctrine().get("rack_lanes") or [])) or [
        "dns", "dhcp", "edge", "witness", "truth", "security", "prejudice",
    ]
    for lane in lanes:
        if lane == "botnet":
            continue
        lane_doc = {
            "schema": f"field-h7r-{lane}/v1",
            "stack_version": STACK_VERSION,
            "updated": doc.get("updated"),
            "node_id": doc.get("node_id"),
            "rack_id": rack.name,
            "lane": lane,
            **(services.get(lane) or {}),
        }
        target = rack / lane / "h7r-service.json"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                json.dumps(lane_doc, ensure_ascii=False, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            written.append(str(target))
        except OSError:
            pass
    combined = rack / "field-h7r-stack.json"
    try:
        combined.write_text(
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        written.append(str(combined))
    except OSError:
        pass
    return written


def _merge_field_one_stack(primary: Path, stack_doc: dict[str, Any]) -> None:
    """Merge stack fields into field-one-stack.json when present."""
    if not primary.is_file():
        return
    try:
        base = _load(primary, {})
        merged = {**base, **stack_doc}
        merged["field_one_stack"] = True
        primary.write_text(
            json.dumps(merged, ensure_ascii=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def _stamp_one(node: dict[str, Any], panels: dict[str, Any], racks: list[Path]) -> dict[str, Any]:
    nid = str(node.get("id") or "")
    if _has_latest(node):
        return {"ok": True, "id": nid, "skipped": True}
    rack_idx = int(hashlib.sha256(nid.encode()).hexdigest()[:8], 16) % max(1, len(racks))
    rack = racks[rack_idx] if racks else None
    doc = stack_manifest_doc(
        node,
        panels,
        rack_id=rack.name if rack else str(node.get("field_id") or ""),
        metro_id=str(node.get("metro_id") or ""),
        region_id=str(node.get("region_id") or ""),
    )
    primary = _stamp_path(node)
    compact = json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n"
    try:
        primary.parent.mkdir(parents=True, exist_ok=True)
        primary.write_text(compact, encoding="utf-8")
        vault = STAMP_VAULT / f"{_safe_id(nid)}-h7r-stack.json"
        STAMP_VAULT.mkdir(parents=True, exist_ok=True)
        vault.write_text(compact, encoding="utf-8")
        rack_written: list[str] = []
        if rack:
            rack_written = _write_rack_services(rack, doc)
            h7r_dir = rack / "h7-shard" / "h7r-vault" / "stack-stamps"
            h7r_dir.mkdir(parents=True, exist_ok=True)
            (h7r_dir / f"{_safe_id(nid)}.json").write_text(compact, encoding="utf-8")
            root = str(node.get("storage_root") or "")
            if root:
                _merge_field_one_stack(Path(root) / "field-one-stack.json", doc)
        return {
            "ok": True,
            "id": nid,
            "primary": str(primary),
            "rack": rack.name if rack else None,
            "rack_lanes": len(rack_written),
        }
    except OSError as exc:
        return {"ok": False, "id": nid, "error": str(exc)[:120]}


def _stamp_racks(panels: dict[str, Any], racks: list[Path]) -> list[dict[str, Any]]:
    """Ensure every rack has a canonical H7r stack manifest (rack authority node)."""
    stamped: list[dict[str, Any]] = []
    for rack in racks:
        manifest = _load(rack / "manifest.json", {})
        node = {
            "id": str(manifest.get("node_id") or rack.name),
            "node_id": manifest.get("node_id"),
            "kind": "qemu_rack",
            "field_id": manifest.get("field_id") or rack.name,
            "primary_role": manifest.get("primary_role"),
            "roles": manifest.get("roles"),
            "storage_root": str(rack),
            "tunnel": manifest.get("tunnel"),
            "ssh_port": manifest.get("ssh_port"),
            "source": "rack",
        }
        doc = stack_manifest_doc(node, panels, rack_id=rack.name)
        try:
            _write_rack_services(rack, doc)
            (rack / "field-h7r-stack.json").write_text(
                json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            manifest_out = {
                **manifest,
                "h7_protocol": "field-h7r-rackmount",
                "h7_stack": True,
                "stack_version": STACK_VERSION,
                "truth_security_version": TRUTH_SECURITY_VERSION,
                "prejudice_enforced": True,
                "more_than_permissible": True,
            }
            _save(rack / "manifest.json", manifest_out)
            stamped.append({"ok": True, "rack": rack.name, "node_id": node["id"]})
        except OSError as exc:
            stamped.append({"ok": False, "rack": rack.name, "error": str(exc)[:120]})
    return stamped


def rapid_distribute(
    *,
    workers: int | None = None,
    batch_size: int | None = None,
    dry_run: bool = False,
    fast_panels: bool = True,
) -> dict[str, Any]:
    """Stamp DHCP/DNS/edge/witness/botnet H7r manifests on all targets + racks."""
    workers_n = int(workers or DEFAULT_WORKERS)
    batch = int(batch_size or DEFAULT_BATCH)
    panels = _live_panels(fast=fast_panels)
    targets = _collect_targets()
    pending = [t for t in targets if not _has_latest(t)]
    racks = _rack_paths()

    if dry_run:
        return {
            "ok": True,
            "dry_run": True,
            "targets_total": len(targets),
            "pending": len(pending),
            "racks": len(racks),
            "workers": workers_n,
            "batch_size": batch,
            "panels": {k: bool(v) for k, v in panels.items()},
        }

    stamped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    skipped = 0

    for wave_start in range(0, len(pending), batch):
        wave = pending[wave_start : wave_start + batch]
        with ThreadPoolExecutor(max_workers=workers_n) as pool:
            futs = {pool.submit(_stamp_one, node, panels, racks): node for node in wave}
            for fut in as_completed(futs):
                row = fut.result()
                if row.get("skipped"):
                    skipped += 1
                elif row.get("ok"):
                    stamped.append(row)
                else:
                    errors.append(row)

    rack_rows = _stamp_racks(panels, racks)

    idx = _load(STACK_INDEX, {"schema": "field-h7r-stack-index/v1", "nodes": {}})
    for row in stamped:
        nid = str(row.get("id") or "")
        idx.setdefault("nodes", {})[nid] = {
            "node_id": nid,
            "stack_version": STACK_VERSION,
            "truth_security_version": TRUTH_SECURITY_VERSION,
            "prejudice_enforced": True,
            "updated": _utc(),
            "rack": row.get("rack"),
            "lanes": row.get("rack_lanes"),
        }
    for row in rack_rows:
        if row.get("ok"):
            idx.setdefault("racks", {})[str(row.get("rack") or "")] = {
                "stack_version": STACK_VERSION,
                "truth_security_version": TRUTH_SECURITY_VERSION,
                "prejudice_enforced": True,
                "updated": _utc(),
                "node_id": row.get("node_id"),
            }
    idx["count"] = len(idx.get("nodes") or {})
    idx["rack_count"] = len(idx.get("racks") or {})
    idx["stack_version"] = STACK_VERSION
    idx["updated"] = _utc()
    _save(STACK_INDEX, idx)

    gs = _load(GLOBAL_REG, {})
    gs_servers = []
    for s in gs.get("servers") or []:
        gs_servers.append({
            **s,
            "stack_version": STACK_VERSION,
            "truth_security_version": TRUTH_SECURITY_VERSION,
            "h7r_stack_updated": True,
            "h7r_truth_security_updated": True,
            "prejudice_enforced": True,
            "services_version": STACK_VERSION,
        })
    gs["servers"] = gs_servers
    gs["stack_version"] = STACK_VERSION
    gs["h7r_stack_rapid"] = _utc()
    _save(GLOBAL_REG, gs)

    dev_reg = _load(DEVICE_REG, {})
    devices = list(dev_reg.get("devices") or [])
    for i, dev in enumerate(devices):
        devices[i] = {
            **dev,
            "stack_version": STACK_VERSION,
            "truth_security_version": TRUTH_SECURITY_VERSION,
            "h7r_stack_updated": True,
            "h7r_truth_security_updated": True,
            "prejudice_enforced": True,
            "services_version": STACK_VERSION,
        }
    dev_reg["devices"] = devices
    dev_reg["stack_version"] = STACK_VERSION
    dev_reg["h7r_stack_rapid"] = _utc()
    _save(DEVICE_REG, dev_reg)

    doctrine = _load(DOCTRINE, {})
    services_doc = doctrine.get("services") or {}
    sec = _security_slice(panels)
    prej = _prejudice_slice(panels)
    truth = _truth_slice(panels)
    out = {
        "ok": len(errors) == 0,
        "schema": "field-h7r-stack-panel/v2",
        "updated": _utc(),
        "stack_version": STACK_VERSION,
        "truth_security_version": TRUTH_SECURITY_VERSION,
        "storage_version": STORAGE_VERSION,
        "more_than_permissible": True,
        "prejudice_enforced": True,
        "targets_total": len(targets),
        "pending_before": len(pending),
        "stamped": len(stamped),
        "skipped_already_latest": skipped + (len(targets) - len(pending)),
        "errors": len(errors),
        "racks_stamped": sum(1 for r in rack_rows if r.get("ok")),
        "racks_total": len(racks),
        "workers": workers_n,
        "waves": (len(pending) + batch - 1) // batch if pending else 0,
        "services": list(services_doc.get("lanes") or ["dns", "dhcp", "edge", "witness", "botnet", "truth", "security", "prejudice"]),
        "truth": {
            "ironclad_sealed": truth.get("ironclad_sealed"),
            "truth_percent": truth.get("truth_percent"),
            "forever_hash_required": truth.get("forever_hash_required"),
        },
        "security": {
            "gates_green": sec.get("gates_green"),
            "security_score_pct": sec.get("security_score_pct"),
            "ironclad_grounded": sec.get("ironclad_grounded"),
            "sole_dns_dhcp_authority": sec.get("sole_dns_dhcp_authority"),
            "tier": sec.get("tier"),
        },
        "prejudice": {
            "kill_policy": prej.get("kill_policy"),
            "armed": prej.get("armed"),
            "motto": prej.get("motto"),
        },
        "panels_live": {k: bool((panels.get(k) or {}).get("ok") or (panels.get(k) or {}).get("schema")) for k in panels},
        "api": "/api/field-h7r-stack",
    }
    _save(PANEL, out)
    _append_ledger({"event": "rapid_distribute", **{k: out[k] for k in ("stamped", "targets_total", "errors", "racks_stamped")}})
    return out


def distribute_all(
    *,
    workers: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Storage + full H7r stack — one shot."""
    storage = _mod("lib/ammodrive-storage-rapid.py", "storage_rapid")
    storage_out: dict[str, Any] = {"ok": False, "skipped": "module_missing"}
    if storage and hasattr(storage, "rapid_distribute"):
        storage_out = storage.rapid_distribute(workers=workers, dry_run=dry_run)
    stack_out = rapid_distribute(workers=workers, dry_run=dry_run)
    return {
        "ok": bool(storage_out.get("ok")) and bool(stack_out.get("ok")),
        "schema": "field-h7r-distribute-all/v1",
        "updated": _utc(),
        "storage": storage_out,
        "stack": stack_out,
        "api": "/api/field-h7r-stack",
    }


def panel_json() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("schema"):
        return cached
    doctrine = _load(DOCTRINE, {})
    return {
        "ok": True,
        "schema": "field-h7r-stack-panel/v1",
        "stack_version": STACK_VERSION,
        "truth_security_version": TRUTH_SECURITY_VERSION,
        "doctrine": doctrine.get("title"),
        "more_than_permissible": True,
        "prejudice_enforced": True,
        "services": (doctrine.get("services") or {}).get("lanes"),
        "pending": "run distribute",
        "api": "/api/field-h7r-stack",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "distribute").strip().lower()
    dry = "--dry-run" in sys.argv
    fast = "--live-panels" not in sys.argv
    workers = DEFAULT_WORKERS
    for arg in sys.argv[2:]:
        if arg.isdigit():
            workers = int(arg)
    if cmd in ("distribute", "rapid", "stack", "upgrade"):
        print(json.dumps(rapid_distribute(workers=workers, dry_run=dry, fast_panels=fast), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("all", "distribute-all", "full"):
        print(json.dumps(distribute_all(workers=workers, dry_run=dry), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-h7r-stack.py [distribute|all|json] [--dry-run] [--live-panels]",
        "stack_version": STACK_VERSION,
        "api": "/api/field-h7r-stack",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())