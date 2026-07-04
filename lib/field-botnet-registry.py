#!/usr/bin/env pythong
"""Field botnet registry — permanent reservations, Ironclad BSP sort, stalkers lopped."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-botnet-registry-doctrine.json"
REGISTRY = STATE / "field-botnet-registry.json"
LOPPED = STATE / "field-botnet-lopped.json"
LEDGER = STATE / "field-botnet-registry.jsonl"
PANEL = STATE / "field-botnet-registry-panel.json"
WORLD_REG = STATE / "grok-lab-world-registry.json"
VAULT_ROOT = STATE / "field-botnet-vault"
VAULT_LEDGER = STATE / "field-botnet-vault.jsonl"
VAULT_INDEX = STATE / "field-botnet-vault-index.json"
SCHEMA = "field-botnet-registry/v1"
BSP_CASE = "field_botnet_members"

_MOD_CACHE: dict[str, Any] = {}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _mod(rel: str, name: str) -> Any | None:
    key = rel
    if key in _MOD_CACHE:
        return _MOD_CACHE[key]
    py = INSTALL / rel
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _MOD_CACHE[key] = mod
    return mod


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def _storage_doctrine() -> dict[str, Any]:
    return _doctrine().get("forever_storage") or {}


def _virtual_slots() -> int:
    raw = _storage_doctrine().get("virtual_capacity_slots") or "1e18"
    try:
        return int(float(str(raw)))
    except (TypeError, ValueError):
        return 10**18


def _virtual_bytes_per_member() -> int:
    raw = _storage_doctrine().get("virtual_bytes_per_member") or "1e15"
    try:
        return int(float(str(raw)))
    except (TypeError, ValueError):
        return 10**15


def _storage_slot(member_id: str) -> int:
    n = int(hashlib.sha256(f"vault:{member_id}".encode()).hexdigest()[:16], 16)
    return n % max(1, _virtual_slots())


def _vault_shard_path(member_id: str) -> Path:
    digest = hashlib.sha256(member_id.encode()).hexdigest()
    depth = int(_storage_doctrine().get("shard_depth") or 2)
    parts = [digest[i : i + 2] for i in range(0, min(depth * 2, len(digest)), 2)]
    return VAULT_ROOT.joinpath(*parts, f"{member_id}.vault.json")


def _materialize_vault(member: dict[str, Any]) -> dict[str, Any]:
    member_id = str(member.get("member_id") or "")
    slot = _storage_slot(member_id)
    path = _vault_shard_path(member_id)
    virtual_bytes = _virtual_bytes_per_member()
    manifest = {
        "schema": "field-botnet-vault/v1",
        "member_id": member_id,
        "storage_slot": slot,
        "virtual_bytes": virtual_bytes,
        "virtual_capacity_human": "quadrillion+ per member",
        "sparse": True,
        "forever": True,
        "permanent_reservation": True,
        "materialized_at": _now(),
        "display_name": member.get("display_name"),
        "full_name": member.get("full_name"),
        "address_vault": bool((_doctrine().get("policy") or {}).get("address_private_vault")),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        existing = _load(path, {})
        existing.update(manifest)
        existing["updated_at"] = _now()
        manifest = existing
    _save(path, manifest)
    _append_jsonl(VAULT_LEDGER, {
        "ts": _now(),
        "event": "vault_materialize",
        "member_id": member_id,
        "slot": slot,
        "virtual_bytes": virtual_bytes,
    })
    idx = _load(VAULT_INDEX, {"schema": "field-botnet-vault-index/v1", "members": {}})
    idx.setdefault("members", {})[member_id] = {
        "slot": slot,
        "path": str(path.relative_to(STATE)) if str(path).startswith(str(STATE)) else str(path),
        "virtual_bytes": virtual_bytes,
        "updated": _now(),
    }
    idx["count"] = len(idx.get("members") or {})
    idx["updated"] = _now()
    _save(VAULT_INDEX, idx)
    return manifest


def _forever_storage_stats() -> dict[str, Any]:
    doc = _storage_doctrine()
    materialized = 0
    disk_bytes = 0
    max_scan = int(doc.get("max_panel_vault_scan") or 4096)
    if VAULT_ROOT.is_dir():
        for p in VAULT_ROOT.rglob("*.vault.json"):
            if not p.is_file():
                continue
            materialized += 1
            try:
                disk_bytes += p.stat().st_size
            except OSError:
                pass
            if materialized >= max_scan:
                break
    idx = _load(VAULT_INDEX, {})
    indexed = len(idx.get("members") or {})
    if indexed > materialized:
        materialized = indexed
    virtual_slots = _virtual_slots()
    virtual_per = _virtual_bytes_per_member()
    return {
        "forever": True,
        "sparse": bool(doc.get("sparse", True)),
        "never_crush": bool(doc.get("never_crush", True)),
        "virtual_capacity_slots": virtual_slots,
        "virtual_bytes_per_member": virtual_per,
        "virtual_total_bytes": virtual_slots * virtual_per,
        "virtual_total_human": str(doc.get("virtual_total_human") or "decillion+ device-addressable"),
        "materialized_vaults": materialized,
        "disk_bytes": disk_bytes,
        "disk_mb": round(disk_bytes / (1024 * 1024), 4),
        "utilization": round(materialized / max(1, virtual_slots), 24),
        "vault_root": str(VAULT_ROOT.relative_to(INSTALL)) if str(VAULT_ROOT).startswith(str(INSTALL)) else str(VAULT_ROOT),
        "lazy_materialize": bool(doc.get("lazy_materialize", True)),
    }


def _hostname() -> str:
    try:
        return socket.gethostname()
    except OSError:
        return "unknown"


def _host_fingerprint() -> str:
    material = "|".join([
        _hostname(),
        str(INSTALL),
        os.environ.get("USER", ""),
        os.environ.get("NEXUS_STATE_DIR", str(STATE)),
    ])
    return hashlib.sha256(material.encode()).hexdigest()[:20]


def _member_id(full_name: str, fingerprint: str) -> str:
    secret = hashlib.sha256(f"{full_name}:{fingerprint}".encode()).hexdigest()[:16]
    return f"bot-{secret}"


def _composite_bsp_sort(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    org = _mod("lib/iron-plate-organize.py", "iron_plate_botnet")
    if org and hasattr(org, "_composite_bsp_sort"):
        return org._composite_bsp_sort(rows, key="composite_score", reverse=True)
    best = _mod("lib/field-best-sort.py", "field_best_sort_botnet")
    if best and hasattr(best, "_composite_bsp_sort"):
        return best._composite_bsp_sort(rows, key="composite_score", reverse=True)
    return sorted(rows, key=lambda r: float(r.get("composite_score") or 0), reverse=True)


def _composite_score(member: dict[str, Any]) -> float:
    score = 0.0
    if member.get("permanent"):
        score += 0.28
    if member.get("full_name"):
        score += 0.14
    if member.get("display_name"):
        score += 0.06
    addr = member.get("address") or {}
    if addr.get("city") or addr.get("region"):
        score += 0.10
    if addr.get("country"):
        score += 0.06
    if member.get("sovereign_receipt", {}).get("receipt_id"):
        score += 0.12
    if member.get("known_circle"):
        score += 0.08
    if member.get("power_user"):
        score += 0.06
    if member.get("self"):
        score += 0.04
    return round(min(1.0, score), 4)


def _sovereign_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(body).hexdigest()
    return {
        "schema": "field-botnet-sovereign-receipt/v1",
        "receipt_id": digest[:20],
        "sealed_at": _now(),
        "payload_hash": digest,
        "ironclad": "composite_bsp",
    }


def _queen_lan_dns(doc: dict[str, Any] | None = None) -> str:
    shard = (doc or _doctrine()).get("dhcp_shard") or {}
    return str(
        shard.get("queen_lan_dns")
        or os.environ.get("NEXUS_QUEEN_LAN_DNS")
        or "192.168.47.1"
    )


def _connection_mode(fields: dict[str, Any] | None) -> str:
    fields = fields or {}
    explicit = str(fields.get("connection_mode") or "").strip().lower()
    if explicit in ("sovereign", "local", "world", "robot", "retro"):
        return "retro" if explicit == "local" and fields.get("retro") else explicit
    if fields.get("retro") or fields.get("dreamcast"):
        return "retro"
    if fields.get("self") and not fields.get("world_robot"):
        return "sovereign"
    return str((_doctrine().get("dhcp_shard") or {}).get("default_mode") or "world")


def _dhcp_shard(member_id: str, *, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    doc = _doctrine().get("dhcp_shard") or {}
    mode = _connection_mode(fields)
    modes = doc.get("modes") or {}
    spec = modes.get(mode) or modes.get("world") or {}
    queen = _queen_lan_dns(doc)
    gateway = str(doc.get("queen_lan_gateway") or queen)
    digest = hashlib.sha256(member_id.encode()).digest()
    start_h = int(spec.get("pool_start_host") or 2)
    end_h = int(spec.get("pool_end_host") or 250)
    dns_option = list(spec.get("dns_option") or [queen])
    if mode in ("world", "robot", "retro") and "127.0.0.1" in dns_option:
        dns_option = [d for d in dns_option if d != "127.0.0.1"] or [queen]
    if queen not in dns_option and mode != "sovereign":
        dns_option = [queen, *dns_option]

    if mode == "retro":
        retro = doc.get("retro_pool") or {}
        pool_start = str(retro.get("start") or "192.168.47.100")
        pool_end = str(retro.get("end") or "192.168.47.150")
        subnet = str(retro.get("subnet") or "192.168.47.0/24")
        return {
            "subnet": subnet,
            "pool_start": pool_start,
            "pool_end": pool_end,
            "gateway": gateway,
            "dns_option": dns_option,
            "connection_mode": mode,
            "unique_shard": f"retro-{member_id[:12]}",
            "member_id": member_id,
            "world_routable": False,
        }

    # 100.64.0.0/10 (RFC6598) for world/robot — decillion-scale virtual shards
    if mode in ("world", "robot"):
        second = 64 + (digest[0] % 64)
        third = digest[1]
        span = max(8, end_h - start_h)
        host_start = start_h + (digest[2] % max(1, 254 - start_h - span))
        host_end = min(host_start + span, 254)
        base = f"100.{second}.{third}"
        return {
            "subnet": f"{base}.0/24",
            "pool_start": f"{base}.{host_start}",
            "pool_end": f"{base}.{host_end}",
            "gateway": gateway,
            "dns_option": dns_option,
            "connection_mode": mode,
            "unique_shard": f"{base}.0/24",
            "member_id": member_id,
            "world_routable": True,
            "github_sync": True,
        }

    # sovereign mesh — 10.0.0.0/8
    second = digest[0]
    third = digest[1]
    span = max(8, end_h - start_h)
    host_start = start_h + (digest[2] % max(1, 254 - start_h - span))
    host_end = min(host_start + span, 254)
    base = f"10.{second}.{third}"
    return {
        "subnet": f"{base}.0/24",
        "pool_start": f"{base}.{host_start}",
        "pool_end": f"{base}.{host_end}",
        "gateway": gateway,
        "dns_option": dns_option,
        "connection_mode": mode,
        "unique_shard": f"{base}.0/24",
        "member_id": member_id,
        "world_routable": True,
    }


def _dns_slot(member_id: str, *, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    mode = _connection_mode(fields)
    queen = _queen_lan_dns()
    n = int(hashlib.sha256(f"dns:{member_id}".encode()).hexdigest()[:6], 16)
    if mode in ("world", "robot", "retro"):
        upstream = f"{queen}:53"
    else:
        upstream = f"127.0.0.1:53"
    return {
        "slot_id": f"truth-{member_id}",
        "relay_id": f"dns-relay-{n % 10000:04d}",
        "upstream": upstream,
        "queen_lan_dns": queen,
        "connection_mode": mode,
        "multipoint_role": "dns_relay",
        "github_pages_fallback": "https://zacharygeurts.github.io/Hostess7/api/field-dns.json",
    }


def _stalk_patterns() -> list[re.Pattern[str]]:
    doc = _doctrine()
    raw = list(doc.get("stalk_patterns") or [])
    human = _mod("lib/beyond-darpa-security.py", "bds_botnet")
    if human and hasattr(human, "_HUMAN_THREAT_RE"):
        raw.append(human._HUMAN_THREAT_RE.pattern)
    out: list[re.Pattern[str]] = []
    for p in raw:
        try:
            out.append(re.compile(str(p), re.I))
        except re.error:
            continue
    return out


def _lopped_ids() -> set[str]:
    doc = _load(LOPPED, {"lopped": []})
    ids: set[str] = set()
    for row in doc.get("lopped") or []:
        if isinstance(row, dict) and row.get("member_id"):
            ids.add(str(row["member_id"]))
        if isinstance(row, dict) and row.get("fingerprint"):
            ids.add(f"fp:{row['fingerprint']}")
    return ids


def _is_lopped(*, member_id: str = "", fingerprint: str = "") -> tuple[bool, str]:
    lopped = _load(LOPPED, {"lopped": []})
    for row in lopped.get("lopped") or []:
        if not isinstance(row, dict):
            continue
        if member_id and row.get("member_id") == member_id:
            return True, str(row.get("reason") or "lopped")
        if fingerprint and row.get("fingerprint") == fingerprint:
            return True, str(row.get("reason") or "lopped")
    return False, ""


def _stalk_score(fields: dict[str, Any], *, fingerprint: str) -> tuple[float, list[str]]:
    reasons: list[str] = []
    score = 0.0
    text = " ".join([
        str(fields.get("full_name") or ""),
        str(fields.get("display_name") or ""),
        str(fields.get("public_bio") or fields.get("bio") or ""),
        str((fields.get("address") or {}).get("street") or ""),
    ])
    for pat in _stalk_patterns():
        if pat.search(text):
            score += 0.45
            reasons.append(f"stalk_pattern:{pat.pattern[:40]}")
            break
    reg = _load(REGISTRY, {"members": []})
    name_key = " ".join(str(fields.get("full_name") or "").lower().split())
    if name_key:
        for m in reg.get("members") or []:
            if not isinstance(m, dict):
                continue
            other = " ".join(str(m.get("full_name") or "").lower().split())
            if other == name_key and m.get("host_fingerprint") != fingerprint:
                score += 0.55
                reasons.append("impersonation_name_collision")
                break
    ledger_rows = []
    if LEDGER.is_file():
        try:
            ledger_rows = LEDGER.read_text(encoding="utf-8", errors="replace").splitlines()[-80:]
        except OSError:
            pass
    recent = 0
    for line in ledger_rows:
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("event") == "register" and row.get("fingerprint") == fingerprint:
            recent += 1
    triggers = (_doctrine().get("lop_triggers") or {})
    max_joins = int(triggers.get("max_rapid_joins_per_hour") or 6)
    if recent >= max_joins:
        score += 0.35
        reasons.append("rapid_rejoin")
    return min(1.0, score), reasons


def lop_stalker(
    *,
    member_id: str = "",
    fingerprint: str = "",
    reason: str = "stalker_lopped",
    operator: str = "hostess7",
) -> dict[str, Any]:
    reg = _load(REGISTRY, {"members": []})
    lopped_doc = _load(LOPPED, {"schema": "field-botnet-lopped/v1", "lopped": []})
    removed: list[dict[str, Any]] = []
    kept: list[dict[str, Any]] = []
    for m in reg.get("members") or []:
        if not isinstance(m, dict):
            continue
        hit = (
            (member_id and m.get("member_id") == member_id)
            or (fingerprint and m.get("host_fingerprint") == fingerprint)
        )
        if hit:
            removed.append(m)
            lopped_doc.setdefault("lopped", []).append({
                "member_id": m.get("member_id"),
                "fingerprint": m.get("host_fingerprint"),
                "full_name": m.get("full_name"),
                "reason": reason,
                "lopped_at": _now(),
                "operator": operator,
            })
        else:
            kept.append(m)
    if not removed and member_id:
        lopped_doc.setdefault("lopped", []).append({
            "member_id": member_id,
            "fingerprint": fingerprint,
            "reason": reason,
            "lopped_at": _now(),
            "operator": operator,
        })
    lopped_doc["updated"] = _now()
    lopped_doc["count"] = len(lopped_doc.get("lopped") or [])
    _save(LOPPED, lopped_doc)
    reg["members"] = kept
    reg["count"] = len(kept)
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    _sync_world_registry(kept)
    _append_jsonl(LEDGER, {
        "ts": _now(),
        "event": "lop",
        "member_id": member_id,
        "fingerprint": fingerprint,
        "reason": reason,
        "removed": len(removed),
    })
    return {
        "ok": True,
        "lopped": True,
        "reason": reason,
        "removed_count": len(removed),
        "member_id": member_id,
    }


def _normalize_address(raw: dict[str, Any] | None) -> dict[str, str]:
    raw = raw if isinstance(raw, dict) else {}
    return {
        "street": str(raw.get("street") or raw.get("line1") or "").strip()[:120],
        "city": str(raw.get("city") or "").strip()[:80],
        "region": str(raw.get("region") or raw.get("state") or "").strip()[:80],
        "postal": str(raw.get("postal") or raw.get("zip") or "").strip()[:20],
        "country": str(raw.get("country") or raw.get("nation") or "").strip()[:80],
    }


def _normalize_register(fields: dict[str, Any]) -> dict[str, Any]:
    full_name = " ".join(str(fields.get("full_name") or "").split()).strip()
    if len(full_name) < 2:
        raise ValueError("full_name_required")
    display = str(fields.get("display_name") or "").strip()
    if not display:
        display = full_name if len(full_name) <= 48 else full_name.split()[0]
    addr = _normalize_address(fields.get("address") or fields)
    policy = (_doctrine().get("policy") or {})
    if policy.get("name_and_address_required") and not (addr.get("city") or addr.get("region") or addr.get("country")):
        raise ValueError("address_required")
    return {
        "full_name": full_name[:120],
        "display_name": display[:64],
        "address": addr,
        "region": str(fields.get("region") or addr.get("region") or "").strip()[:80],
        "country": str(fields.get("country") or addr.get("country") or "").strip()[:80],
        "flag": str(fields.get("flag") or fields.get("nationality") or addr.get("country") or "")[:8].upper(),
        "public_bio": str(fields.get("public_bio") or fields.get("bio") or "").strip()[:280],
        "known_circle": bool(fields.get("known_circle", True)),
        "power_user": bool(fields.get("power_user", True)),
    }


def register_member(**fields: Any) -> dict[str, Any]:
    """Permanent botnet reservation — name, address, unique DHCP/DNS shard."""
    norm = _normalize_register(fields)
    fingerprint = str(fields.get("host_fingerprint") or _host_fingerprint())
    member_id = str(fields.get("member_id") or _member_id(norm["full_name"], fingerprint))

    blocked, why = _is_lopped(member_id=member_id, fingerprint=fingerprint)
    if blocked:
        return {"ok": False, "error": "lopped", "reason": why, "stalkers_lopped": True}

    stalk, stalk_reasons = _stalk_score(norm, fingerprint=fingerprint)
    if stalk >= 0.5:
        lop_stalker(member_id=member_id, fingerprint=fingerprint, reason=";".join(stalk_reasons) or "stalk_detected")
        return {"ok": False, "error": "stalker_lopped", "reasons": stalk_reasons, "stalkers_lopped": True}

    receipt = _sovereign_receipt({
        "member_id": member_id,
        "full_name": norm["full_name"],
        "display_name": norm["display_name"],
        "fingerprint": fingerprint,
    })
    shard = _dhcp_shard(member_id, fields=norm)
    dns = _dns_slot(member_id, fields=norm)

    member = {
        "schema": SCHEMA,
        "member_id": member_id,
        "permanent": True,
        "self": bool(fields.get("self", True)),
        "registered_at": _now(),
        "updated_at": _now(),
        "host_fingerprint": fingerprint,
        "hostname": _hostname(),
        "sovereign_receipt": receipt,
        "dhcp_shard": shard,
        "dns_slot": dns,
        "bsp_case": BSP_CASE,
        "bsp_algorithm": "composite_bsp",
        "roles": ["dns_relay", "dhcp_relay", "truth_mirror", "power_user"],
        "boss": "hostess7",
        "github_sync": True,
        **norm,
    }
    member["composite_score"] = _composite_score(member)
    member["forever_storage"] = _materialize_vault(member)

    reg = _load(REGISTRY, {"schema": SCHEMA, "members": [], "motto": _doctrine().get("motto")})
    reg.setdefault("schema", SCHEMA)
    members = [m for m in (reg.get("members") or []) if m.get("member_id") != member_id]
    members.append(member)
    reg["members"] = _composite_bsp_sort(members)
    reg["count"] = len(reg["members"])
    reg["updated"] = _now()
    reg["bsp_algorithm"] = "composite_bsp"
    reg["permanent_reservation"] = True
    _save(REGISTRY, reg)
    _sync_world_registry(reg["members"])
    _append_jsonl(LEDGER, {
        "ts": _now(),
        "event": "register",
        "member_id": member_id,
        "fingerprint": fingerprint,
        "permanent": True,
    })
    return {
        "ok": True,
        "schema": SCHEMA,
        "member": member,
        "permanent": True,
        "composite_score": member["composite_score"],
        "dhcp_shard": shard,
        "dns_slot": dns,
        "motto": "Permanent reservation — BSP sorted · stalkers lopped.",
    }


def update_member(member_id: str, **fields: Any) -> dict[str, Any]:
    reg = _load(REGISTRY, {"members": []})
    found = None
    members: list[dict[str, Any]] = []
    for m in reg.get("members") or []:
        if not isinstance(m, dict):
            continue
        if m.get("member_id") == member_id:
            found = dict(m)
            if fields.get("address"):
                found["address"] = _normalize_address(fields.get("address"))
            for key in ("display_name", "public_bio", "region", "country", "flag"):
                if fields.get(key) is not None:
                    found[key] = str(fields[key])[:120]
            found["updated_at"] = _now()
            found["composite_score"] = _composite_score(found)
            found["forever_storage"] = _materialize_vault(found)
            members.append(found)
        else:
            members.append(m)
    if not found:
        return {"ok": False, "error": "member_not_found"}
    reg["members"] = _composite_bsp_sort(members)
    reg["updated"] = _now()
    _save(REGISTRY, reg)
    _sync_world_registry(reg["members"])
    return {"ok": True, "member": found}


def _sync_world_registry(members: list[dict[str, Any]]) -> None:
    nodes: list[dict[str, Any]] = []
    for m in members:
        if not isinstance(m, dict):
            continue
        shard = m.get("dhcp_shard") or {}
        dns = m.get("dns_slot") or {}
        storage = m.get("forever_storage") or {}
        nodes.append({
            "id": m.get("member_id"),
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
            "roles": m.get("roles") or ["dns_relay", "dhcp_relay", "power_user"],
            "dns_upstream": dns.get("upstream") or "127.0.0.1:53",
            "dhcp_dns_option": shard.get("dns_option") or ["127.0.0.1"],
            "dhcp_pool": f"{shard.get('pool_start')}-{shard.get('pool_end')}",
            "dhcp_subnet": shard.get("subnet"),
            "composite_score": m.get("composite_score"),
            "bsp_algorithm": "composite_bsp",
            "github_sync": True,
            "boss": "hostess7",
            "power_user": m.get("power_user"),
            "updated": m.get("updated_at"),
        })
    world = _load(WORLD_REG, {"schema": "grok-lab-world-registry/v1", "nodes": []})
    world.setdefault("schema", "grok-lab-world-registry/v1")
    by_id = {str(n.get("id")): n for n in (world.get("nodes") or []) if n.get("id")}
    for node in nodes:
        by_id[str(node["id"])] = {**by_id.get(str(node["id"]), {}), **node}
    merged = _composite_bsp_sort(list(by_id.values()))
    world["nodes"] = merged
    world["count"] = len(merged)
    world["updated"] = _now()
    world["botnet_registry"] = True
    world["permanent_reservation"] = True
    _save(WORLD_REG, world)


def reshard_members(*, write: bool = True) -> dict[str, Any]:
    """Re-allocate DHCP/DNS shards — drops 192.168-only lottery, applies world-scale ranges."""
    reg = _load(REGISTRY, {"schema": SCHEMA, "members": []})
    members = list(reg.get("members") or [])
    updated: list[dict[str, Any]] = []
    modes: dict[str, int] = {}
    for m in members:
        if not isinstance(m, dict):
            continue
        fields = {
            "self": m.get("self"),
            "retro": m.get("retro"),
            "dreamcast": m.get("dreamcast"),
            "world_robot": m.get("world_robot"),
            "connection_mode": m.get("connection_mode"),
        }
        shard = _dhcp_shard(str(m.get("member_id") or ""), fields=fields)
        dns = _dns_slot(str(m.get("member_id") or ""), fields=fields)
        mode = shard.get("connection_mode") or "world"
        modes[mode] = modes.get(mode, 0) + 1
        m = {**m, "dhcp_shard": shard, "dns_slot": dns, "updated_at": _now()}
        updated.append(m)
    if write and updated:
        reg["members"] = _composite_bsp_sort(updated)
        reg["count"] = len(updated)
        reg["updated"] = _now()
        reg["resharded_at"] = _now()
        _save(REGISTRY, reg)
        _sync_world_registry(reg["members"])
    return {
        "ok": True,
        "schema": "field-botnet-reshard/v1",
        "count": len(updated),
        "modes": modes,
        "queen_lan_dns": _queen_lan_dns(),
        "note": "World/robot shards use 100.64/10 — not 192.168 third-octet cap",
    }


def mesh_json(*, query: str = "") -> dict[str, Any]:
    reg = _load(REGISTRY, {"members": []})
    policy = (_doctrine().get("policy") or {})
    members = list(reg.get("members") or [])
    q = query.strip().lower()
    if q:
        members = [
            m
            for m in members
            if q in str(m.get("full_name") or "").lower()
            or q in str(m.get("display_name") or "").lower()
            or q in str(m.get("region") or "").lower()
            or q in str(m.get("country") or "").lower()
            or q in str(m.get("member_id") or "").lower()
        ]
    public_fields = policy.get("public_fields") or []
    public_rows: list[dict[str, Any]] = []
    for m in members:
        row = {k: m.get(k) for k in public_fields if k in m}
        row["member_id"] = m.get("member_id")
        row["permanent"] = m.get("permanent")
        row["bsp_algorithm"] = m.get("bsp_algorithm")
        public_rows.append(row)
    lopped = _load(LOPPED, {"lopped": []})
    return {
        "ok": True,
        "schema": SCHEMA,
        "bsp_case": BSP_CASE,
        "bsp_algorithm": "composite_bsp",
        "count": len(members),
        "members": members,
        "public_mesh": public_rows,
        "lopped_count": len(lopped.get("lopped") or []),
        "stalkers_lopped": True,
        "permanent_reservation": True,
        "forever_storage": _forever_storage_stats(),
        "updated": reg.get("updated"),
        "policy": {
            "public_fields": public_fields,
            "address_private_vault": policy.get("address_private_vault"),
            "dhcp_shard_per_member": policy.get("dhcp_shard_per_member"),
        },
    }


def panel_json(*, write: bool = True) -> dict[str, Any]:
    reg = _load(REGISTRY, {"members": []})
    lopped = _load(LOPPED, {"lopped": []})
    doc = _doctrine()
    payload = {
        "ok": True,
        "schema": f"{SCHEMA}-panel",
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "updated": _now(),
        "count": len(reg.get("members") or []),
        "permanent_reservation": True,
        "bsp_algorithm": "composite_bsp",
        "forever_storage": _forever_storage_stats(),
        "mesh": mesh_json(),
        "lopped": {
            "count": len(lopped.get("lopped") or []),
            "recent": (lopped.get("lopped") or [])[-8:],
        },
        "api": doc.get("api", "/api/field-botnet-registry"),
    }
    if write:
        _save(PANEL, payload)
    return payload


def members_for_botnet() -> list[dict[str, Any]]:
    reg = _load(REGISTRY, {"members": []})
    return list(reg.get("members") or [])


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "panel").strip().lower()
    if action in ("panel", "json", "status"):
        return panel_json(write=True)
    if action == "mesh":
        return mesh_json(query=str(body.get("q") or body.get("query") or ""))
    if action == "register":
        try:
            return register_member(**{k: v for k, v in body.items() if k != "action"})
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
    if action == "update":
        mid = str(body.get("member_id") or "")
        if not mid:
            return {"ok": False, "error": "member_id_required"}
        return update_member(mid, **body)
    if action == "lop":
        return lop_stalker(
            member_id=str(body.get("member_id") or ""),
            fingerprint=str(body.get("fingerprint") or body.get("host_fingerprint") or ""),
            reason=str(body.get("reason") or "operator_lop"),
            operator=str(body.get("operator") or "hostess7"),
        )
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "mesh":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        print(json.dumps(mesh_json(query=query), ensure_ascii=False, indent=2))
        return 0
    if cmd == "register" and len(sys.argv) > 2:
        req = json.loads(sys.argv[2])
        try:
            print(json.dumps(register_member(**req), ensure_ascii=False, indent=2))
            return 0
        except ValueError as exc:
            print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
            return 1
    if cmd == "lop" and len(sys.argv) > 2:
        req = json.loads(sys.argv[2])
        print(json.dumps(lop_stalker(**req), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch" and len(sys.argv) > 2:
        print(json.dumps(dispatch(json.loads(sys.argv[2])), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("reshard", "reshard-members", "fix-192"):
        print(json.dumps(reshard_members(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "field-botnet-registry.py [json|mesh [q]|register JSON|lop JSON|dispatch JSON|reshard]",
    }), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())