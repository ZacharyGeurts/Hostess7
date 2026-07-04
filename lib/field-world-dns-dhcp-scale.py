#!/usr/bin/env python3
"""World DNS/DHCP scale — population growth forever, edge/host math, ping rescue."""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-world-dns-dhcp-scale-doctrine.json"
PANEL = STATE / "field-world-dns-dhcp-scale-panel.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}


def _population_at(year: float, base: float, rate: float, base_year: float) -> float:
    dt = year - base_year
    return base * math.pow(1.0 + rate, dt)


def _devices(population: float, dpc: float) -> float:
    return population * dpc


def build_scale(*, years_ahead: float | None = None) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    pop = doc.get("population") or {}
    ipv4 = doc.get("ipv4") or {}
    edge = doc.get("edge_model") or {}

    base_year = float(pop.get("base_year") or 2026)
    base_pop = float(pop.get("base_population") or 8_100_000_000)
    rate = float(pop.get("annual_growth_rate") or 0.009)
    dpc = float(pop.get("devices_per_capita") or 2.75)
    horizons = list(pop.get("horizon_years") or [10, 25, 50, 100, 500, 1000])

    usable_ipv4 = int(ipv4.get("usable") or (2**32 - int(ipv4.get("reserved_headroom") or 2**28)))
    hosts_per_edge = int(edge.get("hosts_per_edge_default") or 65536)

    now_year = datetime.now(timezone.utc).year + (datetime.now(timezone.utc).month - 1) / 12.0
    target_year = now_year + float(years_ahead if years_ahead is not None else 0)

    projections: list[dict[str, Any]] = []
    for h in horizons:
        y = now_year + float(h)
        p = _population_at(y, base_pop, rate, base_year)
        dev = _devices(p, dpc)
        edges_ipv4_shard = max(1, math.ceil(dev / usable_ipv4)) if usable_ipv4 else 1
        edges_host_cap = max(1, math.ceil(dev / hosts_per_edge))
        edges_needed = max(edges_ipv4_shard, edges_host_cap)
        projections.append({
            "years_ahead": h,
            "calendar_year": round(y),
            "population": int(p),
            "devices": int(dev),
            "ipv4_capacity": usable_ipv4,
            "beyond_ipv4": dev > usable_ipv4,
            "edge_hosts_min": edges_needed,
            "people_per_edge": int(p / edges_needed) if edges_needed else int(p),
            "leases_per_edge": int(dev / edges_needed) if edges_needed else int(dev),
        })

    current_pop = _population_at(target_year, base_pop, rate, base_year)
    current_dev = _devices(current_pop, dpc)
    edges_now = max(
        1,
        math.ceil(current_dev / usable_ipv4) if usable_ipv4 else 1,
        math.ceil(current_dev / hosts_per_edge),
    )

    ping_posture = _load(STATE / "field-ping-panel.json", {}).get("last_ping") or {}

    return {
        "ok": True,
        "schema": "field-world-dns-dhcp-scale/v1",
        "updated": _utc(),
        "motto": doc.get("motto"),
        "world_dns_dhcp": doc.get("world_dns_dhcp") or {},
        "ingress_policy": edge.get("ingress_policy") or "quarantine_not_kill",
        "current": {
            "calendar_year": round(target_year),
            "population": int(current_pop),
            "devices": int(current_dev),
            "ipv4_usable": usable_ipv4,
            "beyond_ipv4": current_dev > usable_ipv4,
            "edge_hosts_recommended": edges_now,
            "dhcp_leases_if_one_per_device": int(current_dev),
            "dns_records_if_one_per_device": int(current_dev),
        },
        "projections": projections,
        "ping_rescue": {
            "enabled": bool(edge.get("ping_rescue")),
            "module": edge.get("ping_module"),
            "last_probe": ping_posture.get("host"),
            "last_rtt_ms": (ping_posture.get("stats") or {}).get("avg_ms"),
        },
        "formula": {
            "population": "P(t) = P0 * (1+r)^(t-t0)",
            "devices": "D(t) = P(t) * devices_per_capita",
            "edges": "max(ceil(D/ipv4_usable), ceil(D/hosts_per_edge))",
        },
    }


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").lower()
    if cmd == "json":
        out = build_scale()
        PANEL.parent.mkdir(parents=True, exist_ok=True)
        PANEL.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"usage": "field-world-dns-dhcp-scale.py [json]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())