#!/usr/bin/env pythong
"""Unified Field Bus — data_bus[64] packed from all lanes; copilot hot route per lane.

Field Die discipline on host NEXUS: scan/pack once, arithmetic decode forever.
Compatible with FieldLayer::BusMap slot bases from AMOURANTHRTX.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-unified-bus-doctrine.json"
RUNTIME = STATE / "field-unified-bus-runtime.json"
PANEL = STATE / "field-unified-bus-panel.json"
BUS_SIZE = 64

LANE_SLOTS: dict[str, tuple[int, ...]] = {
    "operator": (2, 3, 4, 5, 6, 7),
    "kernel": (8, 9, 10, 11),
    "sense": (12, 13, 14, 15),
    "firmware": (56, 57, 58, 59),
    "net": (16, 17, 18, 19),
    "gatekeeper": (20, 21, 22, 23),
    "security": (24, 25, 26, 27),
    "deinterlace": (28, 29, 30, 31),
    "rf": (32, 33, 34, 35),
    "dns": (36, 37, 38, 39),
    "sovereign": (40, 41, 42, 43),
    "io_packet": (44, 45, 46, 47),
    "thermal": (48, 49, 50, 51),
    "copilot": (52, 53, 54, 55),
}

LANE_KEYS: dict[str, dict[str, int]] = {
    "operator": {"connections": 2, "direct": 3, "storm": 4, "irq": 5, "wires": 6, "iommu": 7},
    "kernel": {"live": 8, "bzimage": 9, "substrate": 10, "generation": 11},
    "sense": {"eye_live": 12, "ear_sealed": 13, "zocr_legacy": 14, "redata_ok": 15},
    "firmware": {"threats": 56, "removed": 57, "bios_manual": 58, "verdict": 59},
    "net": {"tx": 16, "rx": 17, "alerts": 18, "ports": 19},
    "gatekeeper": {"connections": 20, "harm": 21, "suspicious": 22, "permits": 23},
    "security": {"storm": 24, "red": 25, "wifi_hostile": 26, "heat_crush": 27},
    "deinterlace": {"processed": 28, "secure": 29, "quarantine": 30, "legal": 31},
    "rf": {"aps": 32, "hostile": 33, "pollution": 34, "signal": 35},
    "dns": {"truth": 36, "blocked": 37, "qps": 38, "services": 39},
    "sovereign": {"cycle": 40, "pulse": 41, "mirrors": 42, "seal": 43},
    "io_packet": {"gate_pass": 44, "sanity_ok": 45, "baselines_ok": 46, "stream_count": 47},
    "thermal": {"peak_c": 48, "level": 49, "entropy": 50, "quota": 51},
}

_BUS_COPILOT: "BusCopilot | None" = None
_RT_MEM: tuple[float, dict[str, Any]] | None = None
_GEN = 0


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


def _save_atomic(path: Path, doc: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    payload = (
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        if compact
        else json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    )
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def pack_word(*, magnitude: int, tier: int = 0, flags: int = 0, lane_id: int = 0) -> int:
    """uint32 bus word — hot-decode with AND/SHR on copilot path."""
    return (
        (magnitude & 0xFF)
        | ((tier & 0xFF) << 8)
        | ((flags & 0xFF) << 16)
        | ((lane_id & 0xFF) << 24)
    )


def decode_word(word: int) -> dict[str, int]:
    return {
        "magnitude": word & 0xFF,
        "tier": (word >> 8) & 0xFF,
        "flags": (word >> 16) & 0xFF,
        "lane_id": (word >> 24) & 0xFF,
        "raw": word,
    }


def _int_panel(path: Path, *keys: str, default: int = 0) -> int:
    doc = _load(path, {})
    for key in keys:
        val = doc
        for part in key.split("."):
            if isinstance(val, dict):
                val = val.get(part)
            else:
                val = None
                break
        if isinstance(val, bool):
            return 1 if val else 0
        if isinstance(val, (int, float)):
            return int(val)
    return default


def pack_bus() -> list[int]:
    """Pack data_bus[64] from cached subsystem panels — no subprocess on hot path."""
    global _GEN
    _GEN += 1
    bus = [0] * BUS_SIZE

    meld = _load(STATE / "field-plate-meld.json", {})
    snaps = meld.get("snapshots") if isinstance(meld.get("snapshots"), dict) else {}
    plate_rt = snaps.get("plate_runtime") if snaps else {}
    plate = snaps.get("iron_plate") if snaps else {}
    kern = snaps.get("kernel") if snaps else {}
    firm = snaps.get("firmware") if snaps else {}
    sense = snaps.get("sense_package") if snaps else {}
    if not plate_rt:
        plate_rt = _load(STATE / "field-operator-plate-runtime.json", {})
    if not plate:
        plate = _load(STATE / "field-operator-iron-plate.json", {})
    if not kern:
        kern = _load(STATE / "field-kernel-meld-panel.json", {})
    if not firm:
        firm = _load(STATE / "field-firmware-threat-panel.json", {})
    if not sense:
        sense = _load(STATE / "field-sense-package-panel.json", {})
    pkt = _load(STATE / "packet-field.json", {})
    gk = _load(STATE / "connection-intent.json", {})
    ddos = _load(STATE / "field-port-ddos-panel.json", {})
    deint = _load(STATE / "field-packet-deinterlace-panel.json", {})
    rf = _load(STATE / "field-rf-sentinel.json", {})
    dns = _load(STATE / "field-dns.json", {})
    sync = _load(STATE / "sovereign-sync-manifest.json", {})
    thermal = _load(STATE / "thermal-advisory.json", {})
    anchor = _load(STATE / "sovereign-time-anchor.json", {})

    bus[0] = pack_word(magnitude=_GEN & 0xFF, tier=1, flags=0xA5, lane_id=0)
    cycle = _int_panel(STATE / "sovereign-cycle-state.json", "cycle", default=0)
    bus[1] = pack_word(magnitude=min(cycle, 255), tier=1, lane_id=1)

    wires = len(plate_rt.get("route_words") or [])
    bus[2] = pack_word(magnitude=min(wires, 255), tier=2, lane_id=2)
    bus[3] = pack_word(magnitude=min(int(plate_rt.get("direct_count") or 0), 255), flags=0x01, lane_id=2)
    boot_vec = int(kern.get("boot_vector") or 0) if kern.get("bzimage_ready") else int(plate_rt.get("storm_count") or 0)
    bus[4] = pack_word(
        magnitude=min(boot_vec, 255),
        flags=0x02 | (0x04 if kern.get("kilroy_live") else 0),
        lane_id=2,
    )
    scan = plate.get("scan") or {}
    bus[5] = pack_word(magnitude=min(int(scan.get("irq_lines") or 0), 255), lane_id=2)
    bus[6] = pack_word(magnitude=min(wires, 255), lane_id=2)
    bus[7] = pack_word(magnitude=1 if plate_rt.get("iommu") else 0, flags=0x04 if plate_rt.get("iommu") else 0, lane_id=2)

    bus[8] = pack_word(magnitude=1 if kern.get("kilroy_live") else 0, flags=0xD1 if kern.get("config_rtx_field_die", {}).get("enabled") else 0, lane_id=8)
    bus[9] = pack_word(magnitude=min(int(kern.get("bzimage_hash_byte") or 0), 255), flags=0x01 if kern.get("bzimage_ready") else 0, lane_id=8)
    bus[10] = pack_word(magnitude=1 if kern.get("substrate_pinned") else 0, lane_id=8)
    bus[11] = pack_word(magnitude=min(int(kern.get("generation") or 0), 255), lane_id=8)

    sense_sum = sense.get("summary") or {}
    sense_bus = sense.get("bus_pack") or {}
    sense_verdict_map = {"GREEN": 0, "WATCH": 1, "WARN": 2, "PROTECT": 3}
    bus[12] = pack_word(
        magnitude=1 if sense_sum.get("eye_live") or sense_bus.get("eye_live") else 0,
        flags=0x01 if (sense.get("members") or {}).get("final_eye", {}).get("motion_track") else 0,
        lane_id=12,
    )
    bus[13] = pack_word(
        magnitude=1 if sense_sum.get("ear_sealed") or sense_bus.get("ear_sealed") else 0,
        lane_id=12,
    )
    bus[14] = pack_word(
        magnitude=1 if sense_sum.get("zocr_legacy") or sense_bus.get("zocr_legacy") else 0,
        lane_id=12,
    )
    hostess_tier = int(sense_sum.get("hostess_brain_score") or sense_bus.get("hostess_brain_tier") or 0)
    if hostess_tier > 255:
        hostess_tier = hostess_tier // 10
    bus[15] = pack_word(
        magnitude=sense_verdict_map.get(str(sense.get("verdict") or "WATCH"), 1),
        tier=min(hostess_tier, 255),
        flags=(
            (0x02 if sense_sum.get("redata_live") or sense_bus.get("redata_ok") else 0)
            | (0x04 if sense_sum.get("hostess_brain_live") or sense_bus.get("hostess_brain") else 0)
        ),
        lane_id=12,
    )

    verdict_map = {"GREEN": 0, "WATCH": 1, "WARN": 2, "BIOS_REQUIRED": 3}
    bus[56] = pack_word(magnitude=min(int(firm.get("threat_count") or 0), 255), lane_id=56)
    bus[57] = pack_word(magnitude=min(int(firm.get("removed_count") or 0), 255), flags=0x01, lane_id=56)
    bus[58] = pack_word(magnitude=min(int(firm.get("bios_manual_count") or 0), 255), lane_id=56)
    bus[59] = pack_word(
        magnitude=verdict_map.get(str(firm.get("verdict") or "GREEN"), 1),
        flags=0x02 if firm.get("safe") else 0,
        lane_id=56,
    )

    bus[16] = pack_word(magnitude=min(int(pkt.get("tx_count") or 0), 255), lane_id=16)
    bus[17] = pack_word(magnitude=min(int(pkt.get("rx_count") or 0), 255), lane_id=16)
    bus[18] = pack_word(magnitude=min(int(pkt.get("alert_count") or 0), 255), flags=0x08 if pkt.get("alert_count") else 0, lane_id=16)
    bus[19] = pack_word(magnitude=min(len(pkt.get("ports") or []), 255), lane_id=16)

    conns = gk.get("connections") or []
    bus[20] = pack_word(magnitude=min(len(conns), 255), lane_id=20)
    bus[21] = pack_word(magnitude=min(int(gk.get("harm_candidates") or 0), 255), flags=0x10, lane_id=20)
    bus[22] = pack_word(
        magnitude=min(sum(1 for c in conns if c.get("verdict") == "SUSPICIOUS"), 255),
        lane_id=20,
    )
    bus[23] = pack_word(
        magnitude=min(sum(1 for c in conns if c.get("verdict") in ("USER_OK", "EPHEMERAL", "MONITOR")), 255),
        flags=0x20,
        lane_id=20,
    )

    bus[24] = pack_word(magnitude=min(int((ddos.get("storm_edges") or 0) * 16), 255), lane_id=24)
    bus[25] = pack_word(magnitude=min(int(ddos.get("stats", {}).get("red", 0) if isinstance(ddos.get("stats"), dict) else ddos.get("red", 0) or 0), 255), flags=0x40, lane_id=24)
    wifi = ddos.get("wifi") or []
    hostile_wifi = sum(1 for w in wifi if w.get("verdict") == "RED")
    bus[26] = pack_word(magnitude=min(hostile_wifi, 255), lane_id=24)
    bus[27] = pack_word(magnitude=1 if ddos.get("verdict") == "RED" else 0, flags=0x80, lane_id=24)

    bus[28] = pack_word(magnitude=min(int(deint.get("processed") or 0), 255), lane_id=28)
    bus[29] = pack_word(magnitude=min(int(deint.get("secure") or 0), 255), flags=0x01, lane_id=28)
    bus[30] = pack_word(magnitude=min(int(deint.get("quarantined") or 0), 255), lane_id=28)
    bus[31] = pack_word(magnitude=min(int(deint.get("legal_violations") or 0), 255), lane_id=28)

    bus[32] = pack_word(magnitude=min(int(rf.get("ap_count") or len(rf.get("wifi_scan") or [])), 255), lane_id=32)
    bus[33] = pack_word(magnitude=min(int(rf.get("hostile_count") or rf.get("threat_count") or 0), 255), lane_id=32)
    bus[34] = pack_word(magnitude=min(int(rf.get("pollution_clusters") or 0), 255), lane_id=32)
    bus[35] = pack_word(magnitude=128, tier=0, lane_id=32)

    bus[36] = pack_word(magnitude=1 if dns.get("ok") is not False else 0, flags=0x01, lane_id=36)
    bus[37] = pack_word(magnitude=min(len(dns.get("blocked") or []), 255), lane_id=36)
    bus[38] = pack_word(magnitude=30, tier=1, lane_id=36)
    bus[39] = pack_word(magnitude=1, lane_id=36)

    bus[40] = pack_word(magnitude=min(cycle, 255), lane_id=40)
    bus[41] = pack_word(magnitude=min(int(anchor.get("pulse") or 0) % 256, 255), lane_id=40)
    bus[42] = pack_word(magnitude=min(int(sync.get("redundant_files") or 0), 255), lane_id=40)
    bus[43] = pack_word(magnitude=1 if sync.get("never_lose_cycle") else 0, flags=0x02, lane_id=40)

    io_panel = _load(STATE / "field-io-packet-panel.json", {})
    io_gate = io_panel.get("truth_gate") or {}
    io_stream = int((io_panel.get("conversation_stream") or {}).get("count") or 0)
    bus[44] = pack_word(magnitude=1 if io_gate.get("pass_ok") else 0, flags=0x01, lane_id=44)
    bus[45] = pack_word(magnitude=1 if (io_gate.get("field_sanity") or {}).get("ok") else 0, lane_id=44)
    bus[46] = pack_word(magnitude=1 if (io_gate.get("g1id_baselines") or {}).get("ok") else 0, lane_id=44)
    bus[47] = pack_word(magnitude=min(io_stream, 255), flags=0x02, lane_id=44)

    peak = thermal.get("peak_c")
    peak_byte = int(float(peak)) if isinstance(peak, (int, float)) else 0
    level_map = {"ok": 0, "warn": 1, "crit": 2, "unknown": 3}
    bus[48] = pack_word(magnitude=min(peak_byte, 255), lane_id=48)
    bus[49] = pack_word(magnitude=level_map.get(str(thermal.get("level") or "unknown"), 3), lane_id=48)
    bus[50] = pack_word(magnitude=0, lane_id=48)
    bus[51] = pack_word(magnitude=min(int(thermal.get("quota_pct") or 5), 255), lane_id=48)

    bus[60] = pack_word(magnitude=0x5A, flags=0xFF, lane_id=60)
    bus[63] = pack_word(magnitude=1 if os.environ.get("NEXUS_FIELD_MAX", "0") == "1" else 0, lane_id=63)

    checksum = sum(bus) & 0xFFFFFFFF
    bus[52] = pack_word(magnitude=checksum & 0xFF, tier=(checksum >> 8) & 0xFF, flags=(checksum >> 16) & 0xFF, lane_id=52)
    bus[53] = pack_word(magnitude=wires & 0xFF, lane_id=52)
    bus[54] = pack_word(magnitude=bus[18] & 0xFF, lane_id=52)
    bus[55] = pack_word(magnitude=bus[21] & 0xFF, lane_id=52)

    return bus


class BusCopilot:
    """Per-lane hot router on unified data_bus[64]."""

    __slots__ = ("_words", "_gen", "_keys", "_per_route_ns")

    def __init__(self) -> None:
        self._words: tuple[int, ...] = (0,) * BUS_SIZE
        self._gen = 0
        self._keys = LANE_KEYS
        self._per_route_ns = 0.0

    def absorb(self, rt: dict[str, Any]) -> None:
        words = rt.get("data_bus") or [0] * BUS_SIZE
        self._words = tuple(int(w) for w in words[:BUS_SIZE])
        while len(self._words) < BUS_SIZE:
            self._words = self._words + (0,)
        self._gen = int(rt.get("generation") or 0)

    @property
    def hot(self) -> bool:
        return bool(self._words) and self._words[0] != 0

    def word_at(self, slot: int) -> int:
        if 0 <= slot < len(self._words):
            return self._words[slot]
        return 0

    def route(self, lane: str, key: str) -> dict[str, Any]:
        t0 = time.perf_counter_ns()
        lane_l = lane.strip().lower()
        key_l = key.strip().lower()
        slot = (self._keys.get(lane_l) or {}).get(key_l)
        if slot is None:
            return {"ok": False, "error": "unknown_lane_key", "lane": lane_l, "key": key_l, "copilot": True}
        word = self.word_at(slot)
        decoded = decode_word(word)
        elapsed_ns = time.perf_counter_ns() - t0
        self._per_route_ns = float(elapsed_ns)
        return {
            "ok": True,
            "copilot": True,
            "lane": lane_l,
            "key": key_l,
            "slot": slot,
            "word": word,
            "decoded": decoded,
            "elapsed_ms": 0,
            "elapsed_ns": elapsed_ns,
            "generation": self._gen,
        }

    def route_batch(self, queries: list[tuple[str, str]]) -> dict[str, Any]:
        t0 = time.perf_counter_ns()
        hits = [self.route(lane, key) for lane, key in queries]
        total_ns = time.perf_counter_ns() - t0
        return {
            "ok": True,
            "copilot": True,
            "count": len(hits),
            "hits": hits,
            "elapsed_ms": round(total_ns / 1_000_000, 3),
            "per_route_ns": round(total_ns / max(len(queries), 1), 3),
        }

    def bench(self, *, samples: int = 50_000) -> dict[str, Any]:
        if not self.hot:
            return {"ok": False, "error": "bus_empty"}
        probe = ("operator", "connections")
        t0 = time.perf_counter_ns()
        acc = 0
        for _ in range(samples):
            slot = self._keys[probe[0]][probe[1]]
            acc += self.word_at(slot) & 0xFF
        route_ns = (time.perf_counter_ns() - t0) / samples
        t1 = time.perf_counter_ns()
        for _ in range(min(samples, 2000)):
            os.sched_getaffinity(0)
        cpu_ns = (time.perf_counter_ns() - t1) / min(samples, 2000)
        speedup = cpu_ns / route_ns if route_ns > 0 else 0
        return {
            "ok": True,
            "samples": samples,
            "per_route_ns": round(route_ns, 3),
            "routes_per_sec": int(1_000_000_000 / route_ns) if route_ns else 0,
            "cpu_affinity_ns": round(cpu_ns, 3),
            "faster_than_cpu": speedup > 1,
            "speedup_x": round(speedup, 1),
            "checksum": acc & 0xFFFF,
        }

    def lane_snapshot(self, lane: str) -> dict[str, Any]:
        lane_l = lane.strip().lower()
        keys = self._keys.get(lane_l) or {}
        return {
            "lane": lane_l,
            "slots": {k: {"slot": s, "decoded": decode_word(self.word_at(s))} for k, s in keys.items()},
        }


def bus_copilot(*, reload: bool = False) -> BusCopilot:
    global _BUS_COPILOT
    if _BUS_COPILOT is None:
        _BUS_COPILOT = BusCopilot()
    if reload or not _BUS_COPILOT.hot:
        _BUS_COPILOT.absorb(bus_runtime())
    return _BUS_COPILOT


def bus_route(lane: str, key: str) -> dict[str, Any]:
    return bus_copilot().route(lane, key)


def bus_runtime(*, rebuild: bool = False) -> dict[str, Any]:
    global _RT_MEM, _GEN
    try:
        mtime = RUNTIME.stat().st_mtime
    except OSError:
        mtime = 0.0
    if not rebuild and _RT_MEM and _RT_MEM[0] == mtime:
        return _RT_MEM[1]
    cached = _load(RUNTIME, {})
    if cached.get("data_bus") and not rebuild:
        _RT_MEM = (mtime, cached)
        return cached
    return build_runtime()


def build_runtime() -> dict[str, Any]:
    global _GEN, _RT_MEM
    bus = pack_bus()
    doctrine = _load(DOCTRINE, {})
    rt: dict[str, Any] = {
        "schema": "field-unified-bus-runtime/v1",
        "ts": _now(),
        "generation": _GEN,
        "bus_size": BUS_SIZE,
        "data_bus": bus,
        "die_compatible": True,
        "lanes": list(LANE_SLOTS.keys()),
        "checksum": sum(bus) & 0xFFFFFFFF,
    }
    _save_atomic(RUNTIME, rt, compact=True)
    try:
        _RT_MEM = (RUNTIME.stat().st_mtime, rt)
    except OSError:
        _RT_MEM = (time.time(), rt)
    bus_copilot(reload=True)
    return rt


def build_panel() -> dict[str, Any]:
    rt = build_runtime()
    cpu = bus_copilot()
    doc: dict[str, Any] = {
        "schema": "field-unified-bus/v1",
        "updated": _now(),
        "motto": doctrine_motto(),
        "generation": rt.get("generation"),
        "bus_size": BUS_SIZE,
        "checksum": rt.get("checksum"),
        "lanes": list(LANE_SLOTS.keys()),
        "data_bus": rt.get("data_bus"),
        "lane_snapshots": {lane: cpu.lane_snapshot(lane) for lane in LANE_SLOTS},
        "copilot": {
            "hot": cpu.hot,
            "policy": "data_bus[64] — pack once, route every lane at arithmetic rate",
        },
    }
    if cpu.hot:
        doc["copilot"]["bench"] = cpu.bench(samples=20_000)
    _save_atomic(PANEL, doc)
    return doc


def doctrine_motto() -> str:
    return str(_load(DOCTRINE, {}).get("motto") or "Unified field bus")


def panel_json() -> dict[str, Any]:
    if PANEL.is_file():
        cached = _load(PANEL, {})
        if cached.get("schema"):
            return cached
    return build_panel()


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("cycle", "build", "pack"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "route" and len(sys.argv) > 3:
        build_runtime()
        print(json.dumps(bus_route(sys.argv[2], sys.argv[3]), ensure_ascii=False))
        return 0
    if cmd == "copilot":
        build_runtime()
        print(json.dumps({
            "schema": "field-unified-bus-copilot/v1",
            "ts": _now(),
            **bus_copilot().bench(samples=20_000),
            "lanes": list(LANE_SLOTS.keys()),
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "snapshot" and len(sys.argv) > 2:
        build_runtime()
        print(json.dumps(bus_copilot().lane_snapshot(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-unified-bus.py [json|cycle|route <lane> <key>|copilot|snapshot <lane>]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())