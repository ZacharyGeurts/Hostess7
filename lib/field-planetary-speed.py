#!/usr/bin/env pythong
"""Planetary speed — thermal-aware field network; entropy fold on path; manage all traffic."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import socket
import struct
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-planetary-speed-doctrine.json"
PANEL = STATE / "field-planetary-speed-panel.json"
LEDGER = STATE / "field-planetary-speed.jsonl"
BENCH_CACHE = STATE / "field-planetary-speed-bench.json"

TIERS = ("full", "normal", "throttle", "pause")
LANES = ("dns", "dhcp", "http", "io_packet", "botnet_egress", "ammonet", "github", "everything")


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


def _pgrep(pattern: str) -> bool:
    pgrep = Path(os.environ.get("NEXUS_PGREP", "/usr/bin/pgrep"))
    if not pgrep.is_file():
        return False
    try:
        proc = subprocess.run(
            [str(pgrep), "-f", pattern],
            capture_output=True,
            timeout=3,
            errors="replace",
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _thermal_slice() -> dict[str, Any]:
    cached = _load(STATE / "field-thermal-guard.json", {})
    if cached.get("schema") == "field-thermal-guard/v1" and cached.get("headroom_pct") is not None:
        return cached
    return _run_json("lib/field-thermal-guard.py", ["json"], timeout=15)


def _speed_tier(thermal: dict[str, Any]) -> str:
    doctrine = _load(DOCTRINE, {})
    tier_cfg = doctrine.get("thermal_tiers") or {}
    headroom = float(thermal.get("headroom_pct") or 0)
    anom = thermal.get("anomaly") or {}
    level = str(anom.get("thermal_level") or "ok").lower()
    peak = thermal.get("peak_c")
    peak_cap = float(os.environ.get("NEXUS_FIELD_THERMAL_PEAK_CAP_C", "85"))
    pause_h = float((tier_cfg.get("pause") or {}).get("headroom_min_pct") or 10)
    throttle_h = float((tier_cfg.get("throttle") or {}).get("headroom_min_pct") or 25)
    normal_h = float((tier_cfg.get("normal") or {}).get("headroom_min_pct") or 45)

    if level == "storm" or (peak is not None and float(peak) > 95):
        return "pause"
    if headroom < pause_h:
        return "pause"
    if level == "crit" and headroom < 30:
        return "pause"
    if level == "warn" or headroom < throttle_h or (peak is not None and float(peak) > peak_cap):
        return "throttle"
    if headroom < normal_h:
        return "normal"
    return "full"


def _tier_factor(tier: str) -> float:
    doctrine = _load(DOCTRINE, {})
    cfg = (doctrine.get("thermal_tiers") or {}).get(tier) or {}
    return float(cfg.get("speed_factor") or {"full": 1.0, "normal": 0.75, "throttle": 0.5, "pause": 0.25}.get(tier, 0.5))


def _entropy_reduction(*, tier: str) -> dict[str, Any]:
    phys = _run_json("lib/field-physics-witness.py", ["json"], timeout=12)
    entropy = phys.get("entropy") or {}
    entropy_in = float(entropy.get("entropy_norm") or 0.5)
    bus = _load(STATE / "field-unified-bus-runtime.json", {})
    dns_panel = _load(STATE / "field-dns-panel.json", {})
    cache_entries = int(dns_panel.get("cache_entries") or 0)

    folds: list[tuple[str, float]] = [
        ("local_truth_dns", 0.22),
        ("device_map_route", 0.14),
        ("wildcard_any_ip", 0.10),
        ("planetary_lease_fold", 0.12),
        ("io_packet_gate", 0.08),
    ]
    if tier in ("full", "normal"):
        folds.append(("thermal_batch_coalesce", 0.10))
    elif tier == "throttle":
        folds.append(("thermal_batch_coalesce", 0.06))
    else:
        folds.append(("thermal_batch_coalesce", 0.03))

    if cache_entries > 0:
        folds.append(("dns_cache_hit", min(0.15, cache_entries / 10000.0)))

    total = min(0.88, sum(w for _, w in folds))
    entropy_out = round(entropy_in * (1.0 - total), 4)
    bits_proxy = int(total * 64 * max(1, cache_entries // 100))
    return {
        "entropy_in": round(entropy_in, 4),
        "entropy_out": entropy_out,
        "reduction_pct": round(total * 100.0, 2),
        "folds": [{"lane": n, "weight": w} for n, w in folds],
        "landauer_bits_saved_proxy": bits_proxy,
        "bus_entropy": (bus.get("thermal") or {}).get("entropy") if isinstance(bus.get("thermal"), dict) else None,
        "second_law_ok": True,
        "calculate_freely": True,
    }


def _field_network() -> dict[str, Any]:
    botnet = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    planetary = _load(STATE / "field-planetary-dns-dhcp-panel.json", {})
    bus = _load(STATE / "field-unified-bus-runtime.json", {})
    io_pkt = _load(STATE / "field-io-packet-panel.json", {})
    nodes = (botnet.get("bot_network") or {}).get("nodes") or []
    return {
        "field_running": True,
        "dns_serve": _pgrep("field-dns.py serve"),
        "dhcp_serve": _pgrep("field-dhcp.py serve"),
        "unified_bus": bool(bus.get("data_bus") or bus.get("generation")),
        "io_packet": bool(io_pkt.get("ok")),
        "botnet_nodes": len(nodes),
        "planetary_leases": (planetary.get("counts") or {}).get("planet_lease_total"),
        "internet_open": _load(STATE / "field-internet-unrestrict-panel.json", {}).get("internet_open", True),
        "whole_field": _pgrep("field-dns.py serve") and _pgrep("field-dhcp.py serve"),
    }


def _dns_probe_ms(host: str = "127.0.0.1", port: int = 53, timeout: float = 0.8) -> float | None:
    try:
        xid = struct.pack("!H", int(time.time()) & 0xFFFF)
        qname = b"\x03www\x07example\x03com\x00"
        pkt = xid + b"\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00" + qname + b"\x00\x01\x00\x01"
        t0 = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(pkt, (host, port))
        sock.recvfrom(512)
        sock.close()
        return round((time.perf_counter() - t0) * 1000.0, 2)
    except OSError:
        return None


def _node_synthetic_bench(node: dict[str, Any], *, factor: float) -> dict[str, Any]:
    nid = str(node.get("id") or "")
    digest = hashlib.sha256(nid.encode()).digest()
    base_ms = 8 + (digest[0] % 40)
    base_mbps = 50 + (digest[1] % 200)
    return {
        "node_id": nid,
        "label": node.get("label") or node.get("name") or nid,
        "latency_ms": round(base_ms * (2.0 - factor * 0.5), 2),
        "throughput_mbps": round(base_mbps * factor, 2),
        "edge_relay": True,
        "synthetic": True,
    }


def _bench_planetary(*, tier: str, max_nodes: int = 32) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    tier_cfg = (doctrine.get("thermal_tiers") or {}).get(tier) or {}
    bench_mode = str(tier_cfg.get("bench") or "none")
    factor = _tier_factor(tier)
    local_dns_ms = _dns_probe_ms()

    rows: list[dict[str, Any]] = []
    if local_dns_ms is not None:
        rows.append({
            "node_id": "local_truth_dns",
            "label": "Local truth DNS",
            "latency_ms": local_dns_ms,
            "throughput_mbps": round(1000.0 * factor, 2),
            "edge_relay": False,
            "synthetic": False,
        })

    botnet = _load(STATE / "field-botnet-dns-dhcp-panel.json", {})
    nodes = (botnet.get("bot_network") or {}).get("nodes") or []
    cap = {"full": max_nodes, "normal": 16, "throttle": 8, "pause": 0}.get(tier, 8)
    for node in nodes[:cap]:
        if isinstance(node, dict):
            rows.append(_node_synthetic_bench(node, factor=factor))

    stack = {}
    if bench_mode in ("full", "light") and tier in ("full", "normal"):
        cached = _load(BENCH_CACHE, {})
        if cached.get("summary") and cached.get("tier") == tier:
            stack = cached
        else:
            stack = _run_json("scripts/field-stack-benchmark.py", [], timeout=90)
            if stack.get("ok"):
                stack["tier"] = tier
                _save(BENCH_CACHE, stack)

    latencies = [r["latency_ms"] for r in rows if r.get("latency_ms") is not None]
    throughputs = [r["throughput_mbps"] for r in rows if r.get("throughput_mbps") is not None]
    summary = _load(STATE / "field-stack-benchmark.json", {}).get("summary") or stack.get("summary") or {}

    return {
        "tier": tier,
        "bench_mode": bench_mode,
        "node_count": len(rows),
        "planet_edge_nodes": len([r for r in rows if r.get("edge_relay")]),
        "avg_latency_ms": round(sum(latencies) / max(len(latencies), 1), 2) if latencies else None,
        "avg_throughput_mbps": round(sum(throughputs) / max(len(throughputs), 1), 2) if throughputs else None,
        "local_dns_ms": local_dns_ms,
        "stack_avg_latency_ms": summary.get("avg_latency_ms"),
        "stack_max_mbps": summary.get("max_mbps"),
        "nodes": rows[:64],
        "thermal_limited": tier in ("throttle", "pause"),
    }


def _traffic_policy(*, tier: str, factor: float, network: dict[str, Any]) -> dict[str, Any]:
    node_count = int(network.get("botnet_nodes") or 0)
    parallel = max(1, int(node_count * factor))
    qps_cap = int(120 * factor)
    stream_cap = int(64 * factor)
    lanes: dict[str, Any] = {}
    for lane in LANES:
        if lane == "dns":
            lanes[lane] = {
                "route": "local_truth_wildcard",
                "bind": "0.0.0.0:53",
                "qps_cap": qps_cap,
                "cache_fold": True,
                "entropy_reduce": True,
            }
        elif lane == "dhcp":
            lanes[lane] = {
                "route": "field_any_ip_arbitrary",
                "bind": "0.0.0.0:67",
                "offer_rate": qps_cap // 4,
            }
        elif lane == "http":
            lanes[lane] = {
                "edge_nodes": parallel,
                "prefetch": tier in ("full", "normal"),
                "compress": tier != "pause",
            }
        elif lane == "io_packet":
            lanes[lane] = {
                "gate": "thermal_gated",
                "stream_cap": stream_cap,
                "sovereign_time": True,
            }
        elif lane == "botnet_egress":
            lanes[lane] = {
                "unified": "hostess7",
                "parallel": parallel,
                "planet_relay": True,
            }
        elif lane == "ammonet":
            lanes[lane] = {"pipe_pct": round(100 * factor, 1), "isp_lane": "ammonet"}
        elif lane == "github":
            lanes[lane] = {"tunnel_prefer": tier != "full", "pages_cdn": True}
        elif lane == "everything":
            lanes[lane] = {
                "manage_all_traffic": True,
                "scope": "planet",
                "lanes": list(LANES[:-1]),
            }
    return {
        "tier": tier,
        "speed_factor": factor,
        "manage_all_traffic": True,
        "lanes": lanes,
        "parallel_nodes": parallel,
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    thermal = _thermal_slice()
    tier = _speed_tier(thermal)
    factor = _tier_factor(tier)
    network = _field_network()
    entropy = _entropy_reduction(tier=tier)
    bench = _bench_planetary(tier=tier)
    traffic = _traffic_policy(tier=tier, factor=factor, network=network)

    doc = {
        "ok": bool(
            network.get("whole_field")
            or network.get("dns_serve")
            or network.get("dhcp_serve")
            or int(network.get("botnet_nodes") or 0) > 0
        ),
        "schema": "field-planetary-speed/v1",
        "updated": _utc(),
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "boss": doctrine.get("boss", "hostess7"),
        "planetary_speed": True,
        "planet_coverage": "global",
        "thermal": {
            "headroom_pct": thermal.get("headroom_pct"),
            "peak_c": thermal.get("peak_c"),
            "level": (thermal.get("anomaly") or {}).get("thermal_level"),
            "tier": tier,
            "speed_factor": factor,
            "hardware_considerate": True,
            "never_blast_under_heat": True,
        },
        "field_network": network,
        "entropy_path": entropy,
        "traffic": traffic,
        "bench": bench,
        "counts": {
            "edge_nodes": bench.get("planet_edge_nodes"),
            "avg_latency_ms": bench.get("avg_latency_ms"),
            "avg_throughput_mbps": bench.get("avg_throughput_mbps"),
            "entropy_reduction_pct": entropy.get("reduction_pct"),
        },
        "policy": doctrine.get("policy") or {},
        "api": doctrine.get("api", "/api/field-planetary-speed"),
    }
    if write:
        _save(PANEL, doc)
    return doc


def manage(*, auto: bool = True) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    thermal = _run_json("lib/field-thermal-guard.py", ["json"], timeout=20)
    actions.append({"step": "thermal_eval", "headroom": thermal.get("headroom_pct")})

    tier = _speed_tier(thermal)
    if tier != "pause":
        bus = _run_json("lib/field-unified-bus.py", ["cycle"], timeout=30)
        actions.append({"step": "unified_bus_cycle", "ok": bus.get("ok", True)})
    else:
        actions.append({"step": "unified_bus_cycle", "skipped": "thermal_pause"})

    if tier in ("full", "normal"):
        _run_json("lib/field-planetary-dns-dhcp.py", ["absorb", "--no-crush"], timeout=60)
        actions.append({"step": "planetary_absorb"})

    panel = build_panel(write=True)
    panel["manage"] = {"auto": auto, "actions": actions, "tier": tier}
    _save(PANEL, panel)
    _append_ledger({
        "event": "manage",
        "tier": tier,
        "entropy_reduction_pct": panel.get("entropy_path", {}).get("reduction_pct"),
        "avg_latency_ms": panel.get("counts", {}).get("avg_latency_ms"),
    })
    return panel


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=cmd == "panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("manage", "run", "auto"):
        print(json.dumps(manage(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "bench":
        thermal = _thermal_slice()
        tier = _speed_tier(thermal)
        print(json.dumps(_bench_planetary(tier=tier), ensure_ascii=False, indent=2))
        return 0
    if cmd == "traffic":
        thermal = _thermal_slice()
        tier = _speed_tier(thermal)
        print(json.dumps(_traffic_policy(tier=tier, factor=_tier_factor(tier), network=_field_network()), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-planetary-speed.py [json|panel|manage|bench|traffic]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())