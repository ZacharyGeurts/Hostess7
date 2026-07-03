#!/usr/bin/env pythong
"""Distribute GitHub probe traffic across field botnet — thermal-settle style ~90% offload."""
from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-github-traffic-shard-doctrine.json"
PANEL = STATE / "field-github-traffic-shard-panel.json"
SHARD_DIR = STATE / "field-github-shard-probes"
ROTATION = STATE / "field-github-traffic-rotation.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(ts: str) -> float:
    try:
        return datetime.strptime(str(ts).strip(), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


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


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {})


def thermal_headroom() -> float:
    guard = _load(STATE / "field-thermal-guard.json", {})
    try:
        return float(guard.get("headroom_pct") or 100.0)
    except (TypeError, ValueError):
        return 100.0


def offload_pct(*, doctrine: dict[str, Any] | None = None) -> float:
    doc = doctrine or _doctrine()
    base = float(doc.get("offload_target_pct") or 90)
    tc = doc.get("thermal_coupling") or {}
    if not tc.get("enabled", True):
        return base
    headroom = thermal_headroom()
    throttle = float(tc.get("headroom_throttle_pct") or 50)
    if headroom < throttle:
        base = min(98.0, base + float(tc.get("offload_boost_crit") or 15))
    elif headroom < float(tc.get("headroom_full_pct") or 80):
        base = min(95.0, base + float(tc.get("offload_boost_hot") or 8))
    return base


def host_share_pct(*, doctrine: dict[str, Any] | None = None) -> float:
    doc = doctrine or _doctrine()
    off = offload_pct(doctrine=doc)
    host = max(float(doc.get("host_share_pct_min") or 5), 100.0 - off)
    return min(float(doc.get("host_share_pct_max") or 15), host)


def cache_ttl(*, fast: bool = True, doctrine: dict[str, Any] | None = None) -> int:
    doc = doctrine or _doctrine()
    key = "fast_cache_ttl_sec" if fast else "full_cache_ttl_sec"
    return int(doc.get(key) or (90 if fast else 300))


def cache_fresh(updated: str | None, *, fast: bool = True) -> bool:
    if not updated:
        return False
    age = time.time() - _parse_ts(str(updated))
    return age <= cache_ttl(fast=fast)


def field_nodes(*, doctrine: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    doc = doctrine or _doctrine()
    roles = {str(r) for r in (doc.get("shard_roles") or ["github_sync"])}
    nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    reg = _load(STATE / "field-botnet-registry.json", {})
    for m in reg.get("members") or []:
        if not isinstance(m, dict):
            continue
        mid = str(m.get("member_id") or "")
        if not mid or mid in seen:
            continue
        m_roles = {str(r) for r in (m.get("roles") or [])}
        if m.get("github_sync") is False:
            continue
        if roles & m_roles or m.get("github_sync"):
            nodes.append({"id": mid, "kind": "botnet_member", "roles": sorted(m_roles & roles or roles)})
            seen.add(mid)
    world_path = INSTALL / ".nexus-state/grok-lab-world-registry.json"
    world = _load(world_path if world_path.is_file() else STATE / "grok-lab-world-registry.json", {})
    for row in world.get("nodes") or []:
        if not isinstance(row, dict):
            continue
        nid = str(row.get("id") or "")
        if not nid or nid in seen:
            continue
        if row.get("github_sync") is False:
            continue
        row_roles = {str(r) for r in (row.get("roles") or [])}
        if roles & row_roles or row.get("github_sync"):
            nodes.append({"id": nid, "kind": str(row.get("kind") or "world"), "roles": sorted(row_roles & roles or roles)})
            seen.add(nid)
    if not nodes:
        primary = str(doc.get("primary_host_id") or "field-loopback")
        nodes = [{"id": primary, "kind": "sovereign", "roles": ["github_sync"]}]
    return nodes


def _shard_key(node_id: str) -> Path:
    digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:16]
    return SHARD_DIR / f"{digest}.json"


def _load_shard(node_id: str) -> dict[str, Any]:
    path = _shard_key(node_id)
    if not path.is_file():
        return {}
    doc = _load(path, {})
    return doc if isinstance(doc, dict) else {}


def _save_shard(node_id: str, rows: list[dict[str, Any]], *, probe_kind: str) -> None:
    doc = {
        "schema": "field-github-shard-probe/v1",
        "node_id": node_id,
        "updated": _utc(),
        "probe_kind": probe_kind,
        "rows": rows,
    }
    _save(_shard_key(node_id), doc)


def assign_shards(endpoints: list[dict[str, Any]], nodes: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    shards: dict[str, list[dict[str, Any]]] = {str(n["id"]): [] for n in nodes}
    if not nodes:
        return shards
    for i, ep in enumerate(endpoints):
        node = nodes[i % len(nodes)]
        shards[str(node["id"])].append(ep)
    return shards


def active_shard_id(nodes: list[dict[str, Any]], *, doctrine: dict[str, Any] | None = None) -> str:
    doc = doctrine or _doctrine()
    interval = max(30, int(doc.get("rotate_interval_sec") or 120))
    slot = int(time.time() // interval) % max(1, len(nodes))
    return str(nodes[slot]["id"])


def plan_probe_batch(
    endpoints: list[dict[str, Any]],
    *,
    fast: bool = False,
    probe_kind: str = "legacy",
) -> dict[str, Any]:
    doc = _doctrine()
    nodes = field_nodes(doctrine=doc)
    shards = assign_shards(endpoints, nodes)
    active = active_shard_id(nodes, doctrine=doc)
    active_eps = list(shards.get(active) or [])
    off = offload_pct(doctrine=doc)
    host_pct = host_share_pct(doctrine=doc)
    live_cap = max(1, round(len(endpoints) * host_pct / 100.0))
    if fast:
        live_cap = min(live_cap, 2)
    live_batch = active_eps[:live_cap]
    cached_rows: list[dict[str, Any]] = []
    stale_nodes: list[str] = []
    for node_id, eps in shards.items():
        if node_id == active:
            continue
        shard_doc = _load_shard(node_id)
        rows = list(shard_doc.get("rows") or [])
        if rows and cache_fresh(shard_doc.get("updated"), fast=fast):
            for row in rows:
                if isinstance(row, dict):
                    row = {**row, "shard": node_id, "from_cache": True}
                    cached_rows.append(row)
        else:
            stale_nodes.append(node_id)
    rotation = {
        "schema": "field-github-traffic-rotation/v1",
        "updated": _utc(),
        "active_shard": active,
        "field_nodes": len(nodes),
        "offload_pct": off,
        "host_share_pct": host_pct,
        "live_batch": len(live_batch),
        "cached_rows": len(cached_rows),
        "stale_shards": stale_nodes,
        "thermal_headroom": thermal_headroom(),
        "fast": fast,
        "probe_kind": probe_kind,
    }
    _save(ROTATION, rotation)
    return {
        **rotation,
        "live_batch_eps": live_batch,
        "cached_rows_data": cached_rows,
        "shards": {k: len(v) for k, v in shards.items()},
        "total_catalog": len(endpoints),
    }


def merge_probe_rows(
    live_rows: list[dict[str, Any]],
    cached_rows: list[dict[str, Any]],
    *,
    active_shard: str,
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in cached_rows:
        rid = str(row.get("id") or row.get("url") or "")
        if rid:
            by_id[rid] = row
    for row in live_rows:
        rid = str(row.get("id") or row.get("url") or "")
        if not rid:
            continue
        by_id[rid] = {**row, "shard": active_shard, "live": True}
    merged = list(by_id.values())
    merged.sort(key=lambda r: str(r.get("id") or r.get("url") or ""))
    if not merged and live_rows:
        merged = live_rows
    return merged


def record_live_shard(active_shard: str, live_rows: list[dict[str, Any]], *, probe_kind: str) -> None:
    if active_shard and live_rows:
        _save_shard(active_shard, live_rows, probe_kind=probe_kind)


def keepalive_allowed(*, min_interval: int | None = None) -> tuple[bool, float]:
    doc = _doctrine()
    gap = float(min_interval if min_interval is not None else int(doc.get("keepalive_min_interval_sec") or 90))
    stamp = STATE / "field-internet-unified.stamp"
    if not stamp.is_file():
        return True, 0.0
    try:
        raw = stamp.read_text(encoding="utf-8").strip().splitlines()[0]
        age = time.time() - _parse_ts(raw)
        return age >= gap, age
    except OSError:
        return True, 0.0


def panel() -> dict[str, Any]:
    doc = _doctrine()
    nodes = field_nodes(doctrine=doc)
    rotation = _load(ROTATION, {})
    out = {
        "schema": "field-github-traffic-shard-panel/v1",
        "updated": _utc(),
        "ok": True,
        "title": doc.get("title"),
        "motto": doc.get("motto"),
        "offload_target_pct": offload_pct(doctrine=doc),
        "host_share_pct": host_share_pct(doctrine=doc),
        "field_nodes": len(nodes),
        "nodes": nodes[:32],
        "rotation": rotation,
        "thermal_headroom": thermal_headroom(),
        "cache_ttl_fast_sec": cache_ttl(fast=True, doctrine=doc),
        "keepalive_min_interval_sec": int(doc.get("keepalive_min_interval_sec") or 90),
        "api": doc.get("api", "/api/field-github-traffic-shard"),
    }
    _save(PANEL, out)
    return out


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "plan" and len(sys.argv) > 2:
        eps = json.loads(sys.argv[2]) if sys.argv[2].startswith("[") else []
        print(json.dumps(plan_probe_batch(eps, fast="--fast" in sys.argv), ensure_ascii=False, indent=2))
        return 0
    if cmd == "keepalive-ok":
        ok, age = keepalive_allowed()
        print(json.dumps({"ok": ok, "age_sec": round(age, 1)}, ensure_ascii=False))
        return 0
    print(json.dumps({"usage": "field-github-traffic-shard.py [panel|plan JSON] [--fast]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())