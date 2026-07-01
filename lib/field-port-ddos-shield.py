#!/usr/bin/env pythong
"""Port & WiFi DDoS shield — wave view thermals + entropy at the network edge.

AMOURANTHRTX FieldFabric parallel lanes at every port and WiFi connection:
  lead_in (ingress storm) · core (thermo load) · lead_out (egress boundary) · entropy fold

Zero-cost when calm (94/6). Heat crush at threshold before link saturation.
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-port-ddos-doctrine.json"
PANEL = STATE / "field-port-ddos-panel.json"
LEDGER = STATE / "field-port-ddos-ledger.jsonl"
RING = STATE / "packet-field.ring.jsonl"
PACKET_PANEL = STATE / "packet-field.json"
THERMAL = STATE / "thermal-advisory.json"
RF_PANEL = STATE / "field-rf-sentinel.json"

HEAT_CRUSH = float(os.environ.get("NEXUS_HEAT_CRUSH_THRESHOLD", "0.7"))
MAX_INGRESS_PPS = int(os.environ.get("NEXUS_PORT_MAX_INGRESS_PPS", "400"))
MAX_SYN_RATIO = float(os.environ.get("NEXUS_PORT_MAX_SYN_RATIO", "0.82"))
ENTROPY_STORM = float(os.environ.get("NEXUS_PORT_ENTROPY_STORM", "7.0"))
WINDOW_SEC = float(os.environ.get("NEXUS_PORT_DDOS_WINDOW", "3.0"))
BASELINE_CORE = float(os.environ.get("NEXUS_PORT_CALM_CORE", "12.0"))

PRIVATE_RE = re.compile(
    r"^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.|169\.254\.)"
)
SS_LINE = re.compile(
    r"^(?P<proto>tcp|udp|tcp6|udp6)\s+(?P<state>\S+)\s+\S+\s+\S+\s+"
    r"(?P<local>\S+)\s+(?P<remote>\S+)"
)


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None



def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_atomic(path: Path, doc: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _shannon_entropy(values: list[int]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    h = 0.0
    for c in counts.values():
        p = c / total
        h -= p * math.log2(p)
    return h


def _split_endpoint(ep: str) -> tuple[str, str]:
    if not ep or ep == "*":
        return "", ""
    if ep.startswith("["):
        host, _, port = ep[1:].partition("]:")
        return host, port
    if ":" in ep:
        host, port = ep.rsplit(":", 1)
        return host, port
    return ep, ""


def wave_view(
    *,
    ingress_pps: float,
    egress_pps: float,
    syn_ratio: float,
    entropy_h: float,
) -> dict[str, Any]:
    """FieldFabric parallel peaks — zero-cost math, no allocations on hot path."""
    syn_ratio = max(0.0, min(1.0, syn_ratio))
    lead_in = ingress_pps * syn_ratio * 1.15
    core = (ingress_pps + egress_pps) * 0.5
    lead_out = egress_pps * (1.0 - syn_ratio) * 0.87
    entropy_fold = entropy_h * 0.31 + syn_ratio * 0.19 + min(ingress_pps, 1.0) * 0.08
    thermo = abs(core) * 0.04 + entropy_fold
    calm = core < BASELINE_CORE and entropy_h < 5.5 and syn_ratio < 0.35
    return {
        "lead_in": round(lead_in, 3),
        "core": round(core, 3),
        "lead_out": round(lead_out, 3),
        "entropy_fold": round(entropy_fold, 3),
        "thermo": round(thermo, 3),
        "pad_field": [round(lead_in, 4), round(lead_out, 4), round(syn_ratio, 4), round(entropy_fold, 4)],
        "zero_cost_calm": calm,
    }


def _thermal_doc() -> dict[str, Any]:
    doc = _load(THERMAL, {})
    if doc:
        return doc
    try:
        proc = subprocess.run(
            [sys.executable, str(INSTALL / "lib" / "thermal-governor.py"), "panel"],
            capture_output=True,
            text=True,
            timeout=8,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return {}


def _thermal_coupling(thermal: dict[str, Any], wave_core: float) -> dict[str, Any]:
    peak_c = thermal.get("peak_c")
    level = str(thermal.get("level") or "unknown")
    norm_core = min(1.0, wave_core / max(BASELINE_CORE * 8, 1.0))
    thermo_boost = 0.0
    if isinstance(peak_c, (int, float)):
        if peak_c >= float(thermal.get("crit_c") or 88):
            thermo_boost = 0.35
        elif peak_c >= float(thermal.get("warn_c") or 78):
            thermo_boost = 0.18
    if level == "crit":
        thermo_boost = max(thermo_boost, 0.4)
    elif level == "warn":
        thermo_boost = max(thermo_boost, 0.2)
    score = min(1.0, norm_core + thermo_boost)
    return {
        "peak_c": peak_c,
        "level": level,
        "coupling_score": round(score, 3),
        "heat_crush_ready": score >= HEAT_CRUSH,
    }


def _ring_events(limit: int = 200) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if not RING.is_file():
        panel = _load(PACKET_PANEL, {})
        return list(panel.get("recent") or [])[-limit:]
    try:
        for line in RING.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            if line.strip():
                events.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        pass
    return events


def _port_edge_stats(events: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    now = time.time()
    edges: dict[int, dict[str, Any]] = defaultdict(
        lambda: {
            "ingress": 0,
            "egress": 0,
            "syn": 0,
            "total": 0,
            "lengths": [],
            "sources": Counter(),
        }
    )
    for ev in events:
        ts = ev.get("epoch") or ev.get("ts")
        if isinstance(ts, str):
            try:
                epoch = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
            except ValueError:
                epoch = now
        elif isinstance(ts, (int, float)):
            epoch = float(ts)
        else:
            epoch = now
        if now - epoch > WINDOW_SEC and isinstance(ts, (str, int, float)):
            continue
        direction = ev.get("direction", "")
        dport = int(ev.get("dst_port") or 0)
        sport = int(ev.get("src_port") or 0)
        length = int(ev.get("length") or 0)
        flags = str(ev.get("flags") or "")
        src_ip = str(ev.get("src_ip") or "")
        if direction == "RX" and dport:
            port = dport
            edges[port]["ingress"] += 1
            if "S" in flags and "A" not in flags:
                edges[port]["syn"] += 1
            if src_ip and not PRIVATE_RE.match(src_ip):
                edges[port]["sources"][src_ip] += 1
        elif direction == "TX" and sport:
            port = sport
            edges[port]["egress"] += 1
        else:
            port = dport or sport
            if not port:
                continue
        edges[port]["total"] += 1
        if length:
            edges[port]["lengths"].append(length)
    return edges


def _ss_syn_witness() -> dict[int, dict[str, int]]:
    """Live SYN-RECV / SYN-SENT counts per local port from ss."""
    out: dict[int, dict[str, int]] = defaultdict(lambda: {"syn_recv": 0, "syn_sent": 0, "estab": 0})
    try:
        proc = subprocess.run(["ss", "-H", "-tun"], capture_output=True, text=True, timeout=8)
    except (OSError, subprocess.TimeoutExpired):
        return out
    for line in (proc.stdout or "").splitlines():
        m = SS_LINE.match(line.strip())
        if not m:
            continue
        _, port = _split_endpoint(m.group("local"))
        if not port or not port.isdigit():
            continue
        p = int(port)
        state = m.group("state")
        if state in ("SYN-RECV", "SYN_RECV"):
            out[p]["syn_recv"] += 1
        elif state in ("SYN-SENT", "SYN_SENT"):
            out[p]["syn_sent"] += 1
        elif state in ("ESTAB", "ESTABLISHED"):
            out[p]["estab"] += 1
    return out


def _score_edge(
    port: int,
    stats: dict[str, Any],
    syn_witness: dict[str, int],
    thermal: dict[str, Any],
) -> dict[str, Any]:
    ingress = int(stats.get("ingress") or 0)
    egress = int(stats.get("egress") or 0)
    syn_flags = int(stats.get("syn") or 0)
    syn_recv = int(syn_witness.get("syn_recv") or 0)
    window = max(WINDOW_SEC, 0.1)
    ingress_pps = ingress / window
    egress_pps = egress / window
    syn_ratio = max(syn_flags, syn_recv) / max(ingress, 1)
    entropy_h = _shannon_entropy(list(stats.get("lengths") or [])[-64:])
    wave = wave_view(
        ingress_pps=ingress_pps,
        egress_pps=egress_pps,
        syn_ratio=syn_ratio,
        entropy_h=entropy_h,
    )
    thermo = _thermal_coupling(thermal, wave["core"])
    storm_score = min(
        1.0,
        (wave["core"] / max(BASELINE_CORE * 6, 1.0)) * 0.45
        + wave["entropy_fold"] * 0.25
        + syn_ratio * 0.2
        + thermo["coupling_score"] * 0.1,
    )
    verdict = "GREEN"
    vector = None
    if storm_score >= HEAT_CRUSH or ingress_pps >= MAX_INGRESS_PPS or (
        syn_ratio >= MAX_SYN_RATIO and ingress_pps >= BASELINE_CORE
    ):
        verdict = "RED"
        vector = "SYN_FLOOD" if syn_ratio >= MAX_SYN_RATIO else "DDOS_FLOOD"
    elif storm_score >= HEAT_CRUSH * 0.55 or entropy_h >= ENTROPY_STORM:
        verdict = "YELLOW"
        vector = "ENTROPY_STORM" if entropy_h >= ENTROPY_STORM else "DDOS_FLOOD"
    top_sources = [
        {"ip": ip, "hits": n}
        for ip, n in (stats.get("sources") or Counter()).most_common(5)
    ]
    return {
        "port": port,
        "verdict": verdict,
        "vector": vector,
        "storm_score": round(storm_score, 3),
        "ingress_pps": round(ingress_pps, 2),
        "egress_pps": round(egress_pps, 2),
        "syn_ratio": round(syn_ratio, 3),
        "entropy_h": round(entropy_h, 3),
        "wave_view": wave,
        "thermal": thermo,
        "syn_witness": syn_witness,
        "top_sources": top_sources,
        "heat_crush": verdict == "RED" and storm_score >= HEAT_CRUSH,
    }


def _wifi_edges(thermal: dict[str, Any]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    rf = _load(RF_PANEL, {})
    wifi_rows = [
        r for r in (rf.get("wifi_scan") or rf.get("devices") or [])
        if isinstance(r, dict)
    ]
    if not wifi_rows:
        try:
            proc = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "dev", "status"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            for line in (proc.stdout or "").splitlines():
                parts = line.split(":")
                if len(parts) >= 3 and parts[1] == "wifi":
                    wifi_rows.append({"device": parts[0], "state": parts[2]})
        except (OSError, subprocess.TimeoutExpired):
            pass

    ap_count = len(rf.get("access_points") or rf.get("wifi_aps") or [])
    hostile = int(rf.get("hostile_count") or rf.get("threat_count") or 0)
    pollution = int(rf.get("pollution_clusters") or 0)
    for row in wifi_rows[:4]:
        dev = str(row.get("device") or row.get("iface") or "wlan0")
        signal = int(row.get("signal") or row.get("strength") or -60)
        ingress_proxy = max(0, ap_count - 3) + hostile * 2 + pollution
        egress_proxy = 1 if str(row.get("state") or "").lower() == "connected" else 0
        syn_proxy = min(1.0, hostile / max(ap_count, 1))
        entropy_h = _shannon_entropy([signal + i for i in range(min(ap_count, 32))])
        wave = wave_view(
            ingress_pps=float(ingress_proxy),
            egress_pps=float(egress_proxy),
            syn_ratio=syn_proxy,
            entropy_h=entropy_h,
        )
        thermo = _thermal_coupling(thermal, wave["core"])
        storm_score = min(1.0, wave["entropy_fold"] * 0.4 + syn_proxy * 0.35 + thermo["coupling_score"] * 0.25)
        verdict = "GREEN"
        vector = None
        if hostile >= 2 or storm_score >= HEAT_CRUSH:
            verdict = "RED"
            vector = "WIFI_POLLUTION"
        elif ap_count >= 25 or storm_score >= HEAT_CRUSH * 0.55:
            verdict = "YELLOW"
            vector = "WIFI_POLLUTION"
        edges.append({
            "device": dev,
            "kind": "wifi",
            "verdict": verdict,
            "vector": vector,
            "storm_score": round(storm_score, 3),
            "ap_count": ap_count,
            "hostile_aps": hostile,
            "signal_dbm": signal,
            "wave_view": wave,
            "thermal": thermo,
            "heat_crush": verdict == "RED",
        })
    if not edges:
        edges.append({
            "device": "wifi",
            "kind": "wifi",
            "verdict": "GREEN",
            "storm_score": 0.0,
            "wave_view": wave_view(ingress_pps=0, egress_pps=0, syn_ratio=0, entropy_h=0),
            "thermal": _thermal_coupling(thermal, 0),
            "note": "no_wifi_iface",
        })
    return edges


def _firewall_block(ip: str, reason: str) -> bool:
    if not ip or PRIVATE_RE.match(ip):
        return False
    script = INSTALL / "lib" / "firewall-sentinel.sh"
    if not script.is_file():
        return False
    timeout = os.environ.get("NEXUS_FIREWALL_BLOCK_DURATION", "86400")
    cmd = (
        f'source "{script}" && nexus_firewall_block_ip both "{ip}" "{timeout}" "{reason}"'
    )
    try:
        proc = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
            timeout=12,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        return proc.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _enforce(edges: list[dict[str, Any]], *, apply: bool) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for edge in edges:
        if not edge.get("heat_crush"):
            continue
        sources = edge.get("top_sources") or []
        for src in sources[:3]:
            ip = str(src.get("ip") or "")
            if not ip:
                continue
            action = {
                "ts": _now(),
                "ip": ip,
                "port": edge.get("port"),
                "device": edge.get("device"),
                "vector": edge.get("vector") or "DDOS_FLOOD",
                "storm_score": edge.get("storm_score"),
                "action": "heat_crush_block",
                "applied": False,
            }
            if apply and os.environ.get("NEXUS_PORT_DDOS_ENFORCE", "1") == "1":
                action["applied"] = _firewall_block(ip, f"port_ddos_{edge.get('vector')}")
            actions.append(action)
            _append_ledger(action)
    return actions


def analyze(*, enforce: bool = False) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    thermal = _thermal_doc()
    events = _ring_events()
    port_stats = _port_edge_stats(events)
    syn_map = _ss_syn_witness()

    port_edges: list[dict[str, Any]] = []
    for port, stats in sorted(port_stats.items(), key=lambda kv: -kv[1]["ingress"])[:48]:
        port_edges.append(_score_edge(port, stats, syn_map.get(port, {}), thermal))

    for port, syn_w in syn_map.items():
        if port in port_stats or syn_w.get("syn_recv", 0) < 3:
            continue
        port_edges.append(
            _score_edge(
                port,
                {"ingress": syn_w["syn_recv"], "egress": 0, "syn": syn_w["syn_recv"], "lengths": [], "sources": Counter()},
                syn_w,
                thermal,
            )
        )

    wifi_edges = _wifi_edges(thermal)
    all_edges = port_edges + wifi_edges
    red = sum(1 for e in all_edges if e.get("verdict") == "RED")
    yellow = sum(1 for e in all_edges if e.get("verdict") == "YELLOW")
    calm = sum(1 for e in all_edges if (e.get("wave_view") or {}).get("zero_cost_calm"))
    overall = "GREEN"
    if red:
        overall = "RED"
    elif yellow:
        overall = "YELLOW"

    enforce_targets = [e for e in port_edges if e.get("heat_crush")]
    actions = _enforce(enforce_targets, apply=enforce)

    doc = {
        "schema": "field-port-ddos/v1",
        "updated": _now(),
        "motto": doctrine.get("motto", "Wave view at the wire — thermals + entropy before saturation"),
        "verdict": overall,
        "heat_crush_threshold": HEAT_CRUSH,
        "zero_cost_calm_edges": calm,
        "storm_edges": red + yellow,
        "policy": doctrine.get("policy") or {},
        "thermal": thermal,
        "ports": port_edges[:32],
        "wifi": wifi_edges,
        "actions": actions[-16:],
        "stats": {
            "port_edges": len(port_edges),
            "wifi_edges": len(wifi_edges),
            "red": red,
            "yellow": yellow,
            "packet_window_sec": WINDOW_SEC,
            "events_sampled": len(events),
        },
        "amouranthrtx": "FieldFabric.dispatchExtended",
    }
    return doc


def build_panel(*, enforce: bool = False) -> dict[str, Any]:
    doc = analyze(enforce=enforce)
    _save_atomic(PANEL, doc)
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL.is_file():
        cached = _load(PANEL, {})
        if cached.get("schema"):
            return cached
    return build_panel(enforce=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("cycle", "build"):
        enforce = os.environ.get("NEXUS_PORT_DDOS_ENFORCE", "1") == "1"
        print(json.dumps(build_panel(enforce=enforce), ensure_ascii=False, indent=2))
        return 0
    if cmd == "analyze":
        print(json.dumps(analyze(enforce=False), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-port-ddos-shield.py [json|cycle|build|analyze]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())