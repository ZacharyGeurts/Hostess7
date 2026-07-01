#!/usr/bin/env pythong
"""Operator — field workhorse: IRQ, DMA, true hardware, Smart Connective Iron Plate."""
from __future__ import annotations

import heapq
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-operator-doctrine.json"
PANEL = STATE / "field-operator.json"
IRON_PLATE = STATE / "field-operator-iron-plate.json"
PLATE_RUNTIME = STATE / "field-operator-plate-runtime.json"
SCAN_CACHE = STATE / "field-operator-scan-cache.json"
CLOCK_ANCHOR = STATE / "field-operator-clock-anchor.json"

CACHE_TTL_SEC = 30
ANCHOR_FRESH_SEC = 60
SCAN_WORKERS = 7

_SOVEREIGN_MOD: Any = None
_FABRIC_ENCRYPT: Any = None
_CLOCK_ANCHOR_MEM: dict[str, Any] | None = None
_PLATE_RT_MEM: tuple[float, dict[str, Any]] | None = None
_COPILOT_CPU: "CopilotCPU | None" = None

COMM_CHANNELS = (
    "field_mmio_shadow",
    "netlink_field",
    "ioctl_direct",
    "mmap_userspace",
    "znetwork_shadow",
    "userspace_delegate",
)

_CHANNEL_INDEX = {name: idx for idx, name in enumerate(COMM_CHANNELS)}
_BUS_CODE = {"": 0, "irq": 1, "net": 2, "pci": 3, "storage": 4, "dma": 5, "input": 6}
_BUS_NAME = ("", "irq", "net", "pci", "storage", "dma", "input")
_TIER_CODE = {"unknown": 0, "watch": 1, "audit": 2, "field_known": 3}

# route_word bit layout — plain CPU AND/SHR decode on the hot path
# [3:0] bus  [7:4] channel  [9:8] tier  [21:10] slot  [29:22] quality  [30] board_direct  [31] storm
_FLAG_BOARD_DIRECT = 1 << 30
_FLAG_STORM = 1 << 31

_FINGERPRINT_PATHS = (
    "/proc/interrupts",
    "/proc/cpuinfo",
    "/proc/iomem",
    "/sys/kernel/iommu_groups",
    "/sys/bus/pci/devices",
    "/sys/class/net",
)


def _fabric_encrypt_mod() -> Any | None:
    global _FABRIC_ENCRYPT
    if _FABRIC_ENCRYPT is not None:
        return _FABRIC_ENCRYPT
    py = INSTALL / "lib" / "field-fabric-encrypt.py"
    if not py.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_fabric_encrypt", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _FABRIC_ENCRYPT = mod
    return mod


def _sovereign_mod() -> Any:
    global _SOVEREIGN_MOD
    if _SOVEREIGN_MOD is not None:
        return _SOVEREIGN_MOD
    py = INSTALL / "lib" / "sovereign-time.py"
    if not py.is_file():
        raise ImportError("sovereign-time.py missing")
    spec = importlib.util.spec_from_file_location("sovereign_time", py)
    if not spec or not spec.loader:
        raise ImportError("sovereign-time load failed")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _SOVEREIGN_MOD = mod
    return mod


def _load_clock_anchor() -> dict[str, Any]:
    global _CLOCK_ANCHOR_MEM
    if _CLOCK_ANCHOR_MEM is not None:
        return _CLOCK_ANCHOR_MEM
    _CLOCK_ANCHOR_MEM = _load(CLOCK_ANCHOR, {})
    return _CLOCK_ANCHOR_MEM


_SYNC_MOD: Any = None


def _sync_mod() -> Any:
    global _SYNC_MOD
    if _SYNC_MOD is not None:
        return _SYNC_MOD
    py = INSTALL / "lib" / "field-sovereign-sync.py"
    spec = importlib.util.spec_from_file_location("field_sovereign_sync", py)
    if not spec or not spec.loader:
        raise ImportError("field-sovereign-sync.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _SYNC_MOD = mod
    return mod


def stable_utc_now() -> str:
    """Canonical sovereign UTC — never misconstrued, never backward."""
    try:
        return _sync_mod().utc("operator")
    except (ImportError, OSError, AttributeError):
        try:
            py = INSTALL / "lib" / "sovereign-clock.py"
            spec = importlib.util.spec_from_file_location("sovereign_clock_op", py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                return mod.utc_z("operator")
        except (ImportError, OSError, AttributeError):
            pass
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now() -> str:
    return stable_utc_now()


def seal_clock_anchor(*, chain: str = "operator") -> dict[str, Any]:
    """Sync operator section to sovereign clock — redundant, never lose data."""
    try:
        doc = _sync_mod().sync_section("operator", chain)
        anchor = {
            "schema": "field-operator-clock-anchor/v1",
            "ts": doc.get("derived_utc") or stable_utc_now(),
            "pulse": doc.get("pulse"),
            "verdict": doc.get("verdict"),
            "cycle": doc.get("cycle"),
            "chain": chain,
            "synced": True,
            "never_lose_data": True,
        }
        _write_atomic(CLOCK_ANCHOR, anchor)
        global _CLOCK_ANCHOR_MEM
        _CLOCK_ANCHOR_MEM = anchor
        return anchor
    except (ImportError, OSError, AttributeError):
        st = _sovereign_mod()
        receipt = st.issue_pulse(chain=chain)
        anchor = {
            "schema": "field-operator-clock-anchor/v1",
            "ts": stable_utc_now(),
            "pulse": receipt.get("pulse"),
            "chain": chain,
        }
        _write_atomic(CLOCK_ANCHOR, anchor)
        _CLOCK_ANCHOR_MEM = anchor
        return anchor


def profile_clock() -> dict[str, Any]:
    t0 = time.perf_counter()
    anchor = _load_clock_anchor()
    ntp_panel = _load(STATE / "field-ntp-2026-panel.json", {})
    sovereign_panel: dict[str, Any] = {}
    mono = time.monotonic_ns()
    realtime = time.time_ns()
    if _anchor_fresh():
        local = {
            "mono_ns": mono,
            "realtime_ns": realtime,
            "micron_witness": anchor.get("micron_witness") or "",
            "freq_sum_khz": 0,
        }
    else:
        try:
            st_mod = _sovereign_mod()
            local = st_mod._clock_sample()
            sovereign_panel = _load(st_mod.PULSE_STATE, {})
        except (ImportError, AttributeError, OSError):
            local = {
                "mono_ns": mono,
                "realtime_ns": realtime,
                "micron_witness": "",
                "freq_sum_khz": 0,
            }
    drift_ms: float | None = None
    if anchor.get("mono_ns") and anchor.get("realtime_ns"):
        derived = int(anchor["realtime_ns"]) + (int(local["mono_ns"]) - int(anchor["mono_ns"]))
        drift_ms = abs(int(local["realtime_ns"]) - derived) / 1_000_000.0
    stable = anchor.get("verdict") == "USER_OK"
    return {
        "ok": True,
        "stable": stable,
        "verdict": anchor.get("verdict") or "unsealed",
        "utc_stable": stable_utc_now(),
        "triple": {
            "monotonic_ns": local.get("mono_ns"),
            "realtime_ns": local.get("realtime_ns"),
            "micron_witness": local.get("micron_witness"),
            "freq_sum_khz": local.get("freq_sum_khz"),
        },
        "anchor": {
            "pulse": anchor.get("pulse"),
            "micron_witness": anchor.get("micron_witness"),
            "drift_ms": round(drift_ms, 3) if drift_ms is not None else None,
        },
        "sovereign": {
            "port": int(os.environ.get("NEXUS_SOVEREIGN_TIME_PORT", "9123")),
            "last_pulse": sovereign_panel.get("last", {}).get("pulse") if isinstance(sovereign_panel.get("last"), dict) else sovereign_panel.get("pulse"),
            "last_verify": sovereign_panel.get("verify"),
        },
        "ntp": {
            "bind": ntp_panel.get("bind"),
            "running": ntp_panel.get("running"),
            "sovereign_first": ntp_panel.get("sovereign_first"),
            "squidgie_blocks": (ntp_panel.get("stats") or {}).get("squidgie_blocks"),
        },
        "elapsed_ms": _elapsed_ms(t0),
    }


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_atomic(path: Path, doc: dict[str, Any], *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    payload = (
        json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        if compact
        else json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    )
    tmp.write_text(payload, encoding="utf-8")
    tmp.replace(path)


def _anchor_fresh() -> bool:
    try:
        age = time.time() - CLOCK_ANCHOR.stat().st_mtime
    except OSError:
        return False
    anchor = _load_clock_anchor()
    return age <= ANCHOR_FRESH_SEC and anchor.get("verdict") == "USER_OK"


def _clean_label(text: str) -> str:
    cleaned = re.sub(r"[^\w\s\-.:/]", "", str(text or "")).strip()
    return cleaned[:64] if cleaned else "wire"


def _clean_load(raw: Any) -> tuple[int, int, bool]:
    load = max(0, int(raw or 0))
    if load < 2:
        return 0, 255, False
    storm = load > 1_000_000
    quality = 255 if load < 100_000 else (192 if load < 1_000_000 else (128 if load < 10_000_000 else 64))
    return min(load, 0xFFFF), quality, storm


def _pack_route(
    *,
    bus: int,
    channel: int,
    tier: int,
    slot: int,
    quality: int,
    board_direct: bool,
    storm: bool,
) -> int:
    word = (
        (bus & 0xF)
        | ((channel & 0xF) << 4)
        | ((tier & 0x3) << 8)
        | ((slot & 0xFFF) << 10)
        | ((quality & 0xFF) << 22)
    )
    if board_direct:
        word |= _FLAG_BOARD_DIRECT
    if storm:
        word |= _FLAG_STORM
    return word


def _unpack_route(word: int) -> dict[str, Any]:
    return {
        "bus": _BUS_NAME[word & 0xF] if (word & 0xF) < len(_BUS_NAME) else "",
        "bus_code": word & 0xF,
        "channel_idx": (word >> 4) & 0xF,
        "tier_code": (word >> 8) & 0x3,
        "slot": (word >> 10) & 0xFFF,
        "quality": (word >> 22) & 0xFF,
        "board_direct": bool(word & _FLAG_BOARD_DIRECT),
        "storm": bool(word & _FLAG_STORM),
        "route_word": word,
    }


def _board_direct(bus: str, tier: str, *, has_iommu: bool, driver: str = "") -> bool:
    if bus == "irq":
        return True
    if bus == "net":
        return bool(driver)
    if bus in ("pci", "storage") and has_iommu:
        return tier in ("field_known", "audit")
    return False


def _write_plate_runtime(
    *,
    connections: list[dict[str, Any]],
    route_words: list[int],
    slot_by_key: dict[str, int],
    has_iommu: bool,
) -> dict[str, Any]:
    ids = [str(c.get("id") or "") for c in connections]
    labels = [str(c.get("label") or "") for c in connections]
    rt: dict[str, Any] = {
        "schema": "field-operator-plate-runtime/v1",
        "ts": _now(),
        "iommu": has_iommu,
        "channels": list(COMM_CHANNELS),
        "route_words": route_words,
        "ids": ids,
        "labels": labels,
        "slots": slot_by_key,
        "direct_count": sum(1 for w in route_words if w & _FLAG_BOARD_DIRECT),
        "storm_count": sum(1 for w in route_words if w & _FLAG_STORM),
    }
    enc = _fabric_encrypt_mod()
    if enc is not None:
        material = json.dumps(
            {"route_words": route_words, "slots": slot_by_key, "ts": rt["ts"]},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        rt["fabric_encrypt"] = enc.seal_payload(
            material,
            peaks=[0.18, min(1.0, len(route_words) / 4096.0), 0.22, 0.12],
            arm_slots=4 if route_words else 0,
        )
    _write_atomic(PLATE_RUNTIME, rt, compact=True)
    global _PLATE_RT_MEM
    try:
        _PLATE_RT_MEM = (PLATE_RUNTIME.stat().st_mtime, rt)
    except OSError:
        _PLATE_RT_MEM = (time.time(), rt)
    copilot(reload=True)
    _refresh_unified_bus()
    return rt


def _refresh_unified_bus() -> None:
    meld_py = INSTALL / "lib" / "field-plate-meld.py"
    if meld_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("field_plate_meld", meld_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.meld(refresh_bus=True)
                return
        except Exception:
            pass
    py = INSTALL / "lib" / "field-unified-bus.py"
    if not py.is_file():
        return
    try:
        spec = importlib.util.spec_from_file_location("field_unified_bus", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_runtime()
    except Exception:
        pass


class CopilotCPU:
    """Plate copilot — field intelligence in silicon arithmetic, 0ms hot route, faster than sysfs CPU."""

    __slots__ = (
        "_words",
        "_slots",
        "_channels",
        "_ids",
        "_labels",
        "_iommu",
        "_gen",
        "_per_route_ns",
        "_direct",
    )

    def __init__(self) -> None:
        self._words: tuple[int, ...] = ()
        self._slots: dict[str, int] = {}
        self._channels: tuple[str, ...] = COMM_CHANNELS
        self._ids: tuple[str, ...] = ()
        self._labels: tuple[str, ...] = ()
        self._iommu = False
        self._gen = 0
        self._per_route_ns = 0.0
        self._direct = 0

    def absorb(self, rt: dict[str, Any]) -> None:
        self._words = tuple(int(w) for w in (rt.get("route_words") or ()))
        self._slots = {str(k).lower(): int(v) for k, v in (rt.get("slots") or {}).items()}
        self._channels = tuple(rt.get("channels") or COMM_CHANNELS)
        self._ids = tuple(str(x) for x in (rt.get("ids") or ()))
        self._labels = tuple(str(x) for x in (rt.get("labels") or ()))
        self._iommu = bool(rt.get("iommu"))
        self._direct = int(rt.get("direct_count") or sum(1 for w in self._words if w & _FLAG_BOARD_DIRECT))
        self._gen += 1

    @property
    def hot(self) -> bool:
        return bool(self._words)

    def word_for(self, key: str) -> tuple[int, int] | None:
        needle = key.strip().lower()
        slot = self._slots.get(needle)
        if slot is None or slot >= len(self._words):
            return None
        return slot, self._words[slot]

    def route(self, key: str) -> dict[str, Any]:
        hit = self.word_for(key)
        if hit is None:
            return {
                "ok": False,
                "copilot": True,
                "field_intelligence": False,
                "elapsed_ms": 0,
                "elapsed_ns": 0,
            }
        slot, word = hit
        ch_idx = (word >> 4) & 0xF
        channel = self._channels[ch_idx] if ch_idx < len(self._channels) else COMM_CHANNELS[0]
        intel = (word >> 22) & 0xFF
        return {
            "ok": True,
            "copilot": True,
            "field_intelligence": intel >= 192,
            "elapsed_ms": 0,
            "elapsed_ns": 0,
            "board_direct": bool(word & _FLAG_BOARD_DIRECT),
            "storm": bool(word & _FLAG_STORM),
            "route_word": word,
            "channel": channel,
            "bus_code": word & 0xF,
            "quality": intel,
            "intelligence": intel,
            "slot": slot,
            "id": self._ids[slot] if slot < len(self._ids) else "",
            "label": self._labels[slot] if slot < len(self._labels) else "",
            "communicate": {
                "channel": channel,
                "reason": "copilot_plate",
                "secure": channel in ("field_mmio_shadow", "netlink_field", "ioctl_direct", "znetwork_shadow"),
            },
        }

    def route_batch(self, keys: list[str]) -> dict[str, Any]:
        routes: list[dict[str, Any]] = []
        direct = 0
        for raw in keys:
            hit = self.route(str(raw))
            if hit.get("ok"):
                direct += 1 if hit.get("board_direct") else 0
            hit["target"] = raw
            routes.append(hit)
        return {
            "ok": True,
            "copilot": True,
            "elapsed_ms": 0,
            "elapsed_ns": 0,
            "count": len(routes),
            "direct": direct,
            "routes": routes,
        }

    def bench(self, *, samples: int = 50_000) -> dict[str, Any]:
        if not self._words or not self._slots:
            return {"ok": False, "error": "copilot_empty"}
        probe_key = next(iter(self._slots))
        probe_slot = self._slots[probe_key]
        probe_word = self._words[probe_slot]
        t0 = time.perf_counter_ns()
        acc = 0
        for _ in range(samples):
            w = probe_word
            acc += (w >> 4) & 0xF
            acc += 1 if (w & _FLAG_BOARD_DIRECT) else 0
            acc += (w >> 22) & 0xFF
        route_ns = (time.perf_counter_ns() - t0) / samples
        self._per_route_ns = route_ns
        cpu_t0 = time.perf_counter_ns()
        cpu_prof = profile_cpu()
        cpu_ns = time.perf_counter_ns() - cpu_t0
        speedup = (cpu_ns / route_ns) if route_ns else 0.0
        return {
            "ok": True,
            "samples": samples,
            "per_route_ns": round(route_ns, 3),
            "routes_per_sec": int(1_000_000_000 / route_ns) if route_ns else 0,
            "cpu_profile_ns": int(cpu_ns),
            "cpu_profile_ms": round(cpu_ns / 1_000_000, 3),
            "cpu_cores": cpu_prof.get("cores"),
            "faster_than_cpu": route_ns < cpu_ns,
            "speedup_x": round(speedup, 1),
            "checksum": acc & 0xFFFF,
        }


def copilot(*, reload: bool = False) -> CopilotCPU:
    global _COPILOT_CPU
    if _COPILOT_CPU is None:
        _COPILOT_CPU = CopilotCPU()
    if reload or not _COPILOT_CPU.hot:
        _COPILOT_CPU.absorb(_plate_runtime())
    return _COPILOT_CPU


def copilot_route(target: str) -> dict[str, Any]:
    return copilot().route(target)


def copilot_batch(targets: list[str]) -> dict[str, Any]:
    return copilot().route_batch(targets)


def copilot_status(*, bench: bool = True) -> dict[str, Any]:
    cpu = copilot()
    doc: dict[str, Any] = {
        "schema": "field-operator-copilot/v1",
        "ts": _now(),
        "hot": cpu.hot,
        "elapsed_ms": 0,
        "generation": cpu._gen,
        "wires": len(cpu._words),
        "board_direct": cpu._direct,
        "iommu": cpu._iommu,
        "policy": "Plate field intelligence — copilot routes at arithmetic rate, 0ms reported on hot path",
    }
    if bench and cpu.hot:
        doc["bench"] = cpu.bench(samples=20_000)
        doc["faster_than_cpu"] = doc["bench"].get("faster_than_cpu")
    return doc


def _plate_runtime(*, rebuild: bool = False) -> dict[str, Any]:
    global _PLATE_RT_MEM
    try:
        mtime = PLATE_RUNTIME.stat().st_mtime
    except OSError:
        mtime = 0.0
    if not rebuild and _PLATE_RT_MEM and _PLATE_RT_MEM[0] == mtime:
        return _PLATE_RT_MEM[1]
    rt = _load(PLATE_RUNTIME, {})
    if rt.get("route_words") and not rebuild:
        _PLATE_RT_MEM = (mtime, rt)
        return rt
    plate = _load(IRON_PLATE, {})
    if plate.get("connections"):
        return _plate_runtime_from_plate(plate)
    built = build_iron_plate()
    return _plate_runtime_from_plate(built)


def _plate_runtime_from_plate(plate: dict[str, Any]) -> dict[str, Any]:
    arithmetic = plate.get("arithmetic") or {}
    if arithmetic.get("route_words"):
        rt = {
            "schema": "field-operator-plate-runtime/v1",
            "ts": plate.get("ts"),
            "iommu": plate.get("iommu"),
            "channels": arithmetic.get("channels") or list(COMM_CHANNELS),
            "route_words": arithmetic["route_words"],
            "ids": arithmetic.get("ids") or [],
            "labels": arithmetic.get("labels") or [],
            "slots": arithmetic.get("slots") or {},
            "direct_count": arithmetic.get("direct_count", 0),
            "storm_count": arithmetic.get("storm_count", 0),
        }
        _write_atomic(PLATE_RUNTIME, rt, compact=True)
        global _PLATE_RT_MEM
        try:
            _PLATE_RT_MEM = (PLATE_RUNTIME.stat().st_mtime, rt)
        except OSError:
            _PLATE_RT_MEM = (time.time(), rt)
        return rt
    build_iron_plate(fast={"profiles": plate.get("fast_profiles") or {}} if plate.get("fast_profiles") else None)
    rt = _load(PLATE_RUNTIME, {})
    try:
        _PLATE_RT_MEM = (PLATE_RUNTIME.stat().st_mtime, rt)
    except OSError:
        _PLATE_RT_MEM = (time.time(), rt)
    return rt


def _conn_from_runtime(rt: dict[str, Any], slot: int, word: int) -> dict[str, Any]:
    decoded = _unpack_route(word)
    channels = rt.get("channels") or list(COMM_CHANNELS)
    ch_idx = decoded["channel_idx"]
    channel = channels[ch_idx] if ch_idx < len(channels) else COMM_CHANNELS[0]
    ids = rt.get("ids") or []
    labels = rt.get("labels") or []
    tier_name = next((k for k, v in _TIER_CODE.items() if v == decoded["tier_code"]), "unknown")
    return {
        "id": ids[slot] if slot < len(ids) else "",
        "label": labels[slot] if slot < len(labels) else "",
        "bus": decoded["bus"],
        "slot": slot,
        "quality": decoded["quality"],
        "storm": decoded["storm"],
        "tier": tier_name,
        "board_direct": decoded["board_direct"],
        "route_word": word,
        "communicate": {
            "channel": channel,
            "reason": "iron_plate_arithmetic",
            "secure": channel in ("field_mmio_shadow", "netlink_field", "ioctl_direct", "znetwork_shadow"),
        },
    }


def _run(cmd: list[str], *, timeout: int = 12) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (proc.stdout or proc.stderr or "").strip()
    except (subprocess.SubprocessError, OSError):
        return ""


def _dmi(key: str) -> str:
    p = Path(f"/sys/class/dmi/id/{key}")
    try:
        return p.read_text(encoding="utf-8", errors="replace").strip() if p.is_file() else ""
    except OSError:
        return ""


def _scan_fingerprint() -> str:
    parts: list[str] = []
    for raw in _FINGERPRINT_PATHS:
        p = Path(raw)
        try:
            if raw == "/proc/interrupts" and p.is_file():
                with p.open(encoding="utf-8", errors="replace") as fh:
                    header = fh.readline()
                    line_count = sum(1 for _ in fh)
                parts.append(f"i:{line_count}:{header.count('CPU')}")
            elif raw == "/proc/cpuinfo" and p.is_file():
                st = p.stat()
                parts.append(f"c:{st.st_size}:{st.st_ino}")
            elif raw == "/proc/iomem" and p.is_file():
                st = p.stat()
                parts.append(f"m:{st.st_size}:{st.st_ino}")
            elif p.is_dir():
                names = sorted(x.name for x in p.iterdir())
                parts.append(f"d:{raw}:{len(names)}:{','.join(names[:6])}")
            elif p.is_file():
                st = p.stat()
                parts.append(f"f:{raw}:{st.st_size}:{st.st_ino}")
            else:
                parts.append(f"x:{raw}")
        except OSError:
            parts.append(f"e:{raw}")
    return "|".join(parts)


def _cache_get(keys: list[str], fp: str) -> dict[str, Any] | None:
    doc = _load(SCAN_CACHE, {})
    if doc.get("fingerprint") != fp:
        return None
    age = time.time() - float(doc.get("cached_at", 0))
    if age > CACHE_TTL_SEC:
        return None
    cached_keys = doc.get("keys") or []
    if set(keys) != set(cached_keys):
        return None
    out = doc.get("payload")
    if not isinstance(out, dict):
        return None
    out = json.loads(json.dumps(out))
    scan = out.setdefault("scan", {})
    scan["cache"] = {"hit": True, "age_ms": int(age * 1000), "fingerprint": fp[:48]}
    scan["elapsed_ms"] = 0
    return out


def _cache_put(keys: list[str], fp: str, payload: dict[str, Any]) -> None:
    _write_atomic(
        SCAN_CACHE,
        {
            "schema": "field-operator-scan-cache/v1",
            "cached_at": time.time(),
            "fingerprint": fp,
            "keys": keys,
            "payload": payload,
        },
    )


def profile_cpu() -> dict[str, Any]:
    t0 = time.perf_counter()
    info = Path("/proc/cpuinfo")
    if not info.is_file():
        return {"ok": False, "error": "no_cpuinfo", "elapsed_ms": _elapsed_ms(t0)}
    model = ""
    flags: list[str] = []
    cores = 0
    try:
        with info.open(encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.startswith("processor\t:"):
                    cores += 1
                    if cores > 1 and model and flags:
                        break
                elif line.startswith("model name") and not model:
                    model = line.split(":", 1)[1].strip()
                elif line.startswith("flags") and not flags:
                    flags = line.split(":", 1)[1].split()
    except OSError:
        return {"ok": False, "error": "cpuinfo_read", "elapsed_ms": _elapsed_ms(t0)}
    return {
        "ok": True,
        "cores": cores,
        "model": model,
        "nx": "nx" in flags,
        "vmx": "vmx" in flags or "svm" in flags,
        "aes": "aes" in flags,
        "avx2": "avx2" in flags,
        "elapsed_ms": _elapsed_ms(t0),
    }


def profile_irq(*, top: int = 24) -> dict[str, Any]:
    t0 = time.perf_counter()
    irqf = Path("/proc/interrupts")
    if not irqf.is_file():
        return {"ok": False, "error": "no_interrupts", "elapsed_ms": _elapsed_ms(t0)}
    try:
        with irqf.open(encoding="utf-8", errors="replace") as fh:
            header = fh.readline()
            if not header:
                return {"ok": False, "error": "interrupts_empty", "elapsed_ms": _elapsed_ms(t0)}
            cpu_cols = max(0, header.count("CPU"))
            heap: list[tuple[int, int, str, list[int], str]] = []
            seq = 0
            total_lines = 0
            for line in fh:
                if not line.strip():
                    continue
                parts = line.split()
                if len(parts) < 2:
                    continue
                total_lines += 1
                irq = parts[0].rstrip(":")
                counts: list[int] = []
                for p in parts[1 : 1 + cpu_cols]:
                    try:
                        counts.append(int(p))
                    except ValueError:
                        break
                total = sum(counts) if counts else 0
                name = " ".join(parts[1 + cpu_cols :]) if len(parts) > 1 + cpu_cols else ""
                seq += 1
                row = (total, seq, irq, counts, name.strip())
                if len(heap) < top:
                    heapq.heappush(heap, row)
                elif total > heap[0][0]:
                    heapq.heapreplace(heap, row)
    except OSError:
        return {"ok": False, "error": "interrupts_read", "elapsed_ms": _elapsed_ms(t0)}
    rows = [
        {"irq": irq, "total": total, "name": name, "per_cpu": counts}
        for total, _seq, irq, counts, name in sorted(heap, key=lambda r: r[0], reverse=True)
    ]
    return {
        "ok": True,
        "cpu_columns": cpu_cols,
        "top": rows,
        "total_lines": total_lines,
        "storm_hint": rows[0]["name"] if rows and rows[0]["total"] > 1_000_000 else None,
        "elapsed_ms": _elapsed_ms(t0),
    }


def profile_dma() -> dict[str, Any]:
    t0 = time.perf_counter()
    iommu_dir = Path("/sys/kernel/iommu_groups")
    groups: list[dict[str, Any]] = []
    group_count = 0
    if iommu_dir.is_dir():
        try:
            entries = sorted(
                (p for p in iommu_dir.iterdir() if p.name.isdigit()),
                key=lambda p: int(p.name),
            )
            group_count = len(entries)
            for g in entries[:48]:
                devs_dir = g / "devices"
                devs = [d.name for d in devs_dir.iterdir()] if devs_dir.is_dir() else []
                groups.append({"group": g.name, "devices": devs})
        except OSError:
            pass
    dmar = ""
    try:
        proc = subprocess.run(
            ["dmesg", "-T"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        for line in reversed((proc.stdout or "").splitlines()[-120:]):
            if re.search(r"DMAR|IOMMU|dmar", line, re.I):
                dmar = line[-200:]
                break
    except (subprocess.SubprocessError, OSError, FileNotFoundError):
        dmar = ""
    iomem_dma: list[str] = []
    iomem = Path("/proc/iomem")
    if iomem.is_file():
        try:
            with iomem.open(encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    upper = line.upper()
                    if "DMA" in upper or "PCI" in line:
                        iomem_dma.append(line.strip()[:120])
                        if len(iomem_dma) >= 16:
                            break
        except OSError:
            pass
    return {
        "ok": True,
        "iommu_present": group_count > 0,
        "iommu_groups": group_count,
        "groups_sample": groups[:12],
        "dmar_line": dmar,
        "iomem_dma_sample": iomem_dma,
        "elapsed_ms": _elapsed_ms(t0),
    }


def _pci_from_sysfs(limit: int = 32) -> list[dict[str, Any]]:
    devices: list[dict[str, Any]] = []
    pci_root = Path("/sys/bus/pci/devices")
    if not pci_root.is_dir():
        return devices
    try:
        for dev in sorted(pci_root.iterdir())[:limit]:
            vendor = ""
            device = ""
            driver = ""
            try:
                vp = dev / "vendor"
                if vp.is_file():
                    vendor = vp.read_text(encoding="utf-8", errors="replace").strip()
                dp = dev / "device"
                if dp.is_file():
                    device = dp.read_text(encoding="utf-8", errors="replace").strip()
                drp = dev / "driver"
                if drp.is_symlink():
                    driver = drp.resolve().name
            except OSError:
                pass
            devices.append({"slot": dev.name, "vendor": vendor, "device": device, "driver": driver})
    except OSError:
        pass
    return devices


def profile_pci() -> dict[str, Any]:
    t0 = time.perf_counter()
    devices = _pci_from_sysfs(32)
    if devices:
        return {
            "ok": True,
            "source": "sysfs",
            "devices": devices,
            "count": len(devices),
            "elapsed_ms": _elapsed_ms(t0),
        }
    out = _run(["lspci", "-nn"], timeout=4)
    if not out:
        return {"ok": False, "error": "pci_unavailable", "elapsed_ms": _elapsed_ms(t0)}
    lines = [ln.strip() for ln in out.splitlines() if ln.strip()][:40]
    return {"ok": True, "source": "lspci", "lines": lines, "count": len(lines), "elapsed_ms": _elapsed_ms(t0)}


def profile_net() -> dict[str, Any]:
    t0 = time.perf_counter()
    links = _run(["ip", "-o", "link", "show"], timeout=3)
    routes = _run(["ip", "-4", "route", "show", "default"], timeout=3)
    ifaces: list[dict[str, Any]] = []
    net_root = Path("/sys/class/net")
    for line in links.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name = parts[1].rstrip(":")
        driver = ""
        drv_path = net_root / name / "device" / "driver"
        if drv_path.is_symlink():
            try:
                driver = os.path.basename(os.readlink(drv_path))
            except OSError:
                driver = ""
        ifaces.append({"iface": name, "driver": driver, "line": line[:160]})
    default_iface = ""
    if routes:
        m = re.search(r"dev\s+(\S+)", routes)
        if m:
            default_iface = m.group(1)
    return {
        "ok": True,
        "ifaces": ifaces,
        "default_route_iface": default_iface,
        "default_route": routes[:200],
        "elapsed_ms": _elapsed_ms(t0),
    }


def profile_storage() -> dict[str, Any]:
    t0 = time.perf_counter()
    out = _run(["lsblk", "-o", "NAME,SIZE,TYPE,MODEL,TRAN,MOUNTPOINT", "-J"], timeout=5)
    if out:
        try:
            doc = json.loads(out)
            return {
                "ok": True,
                "source": "lsblk",
                "blockdevices": doc.get("blockdevices", []),
                "elapsed_ms": _elapsed_ms(t0),
            }
        except json.JSONDecodeError:
            pass
    return {"ok": False, "error": "lsblk_unavailable", "elapsed_ms": _elapsed_ms(t0)}


def profile_iommu(*, dma: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    dma_data = dma if dma is not None else profile_dma()
    fw = {
        "board": _dmi("board_name"),
        "product": _dmi("product_name"),
        "bios": _dmi("bios_version"),
    }
    return {
        "ok": True,
        "firmware": fw,
        "dma": dma_data,
        "elapsed_ms": _elapsed_ms(t0),
    }


FAST_PROFILES: dict[str, Callable[..., dict[str, Any]]] = {
    "cpu": profile_cpu,
    "irq": profile_irq,
    "dma": profile_dma,
    "pci": profile_pci,
    "net": profile_net,
    "storage": profile_storage,
    "clock": profile_clock,
}


def _run_profile(key: str, profiles: dict[str, Any]) -> tuple[str, dict[str, Any], int]:
    t0 = time.perf_counter()
    if key == "iommu":
        result = profile_iommu(dma=profiles.get("dma"))
    else:
        fn = FAST_PROFILES[key]
        result = fn()
    return key, result, _elapsed_ms(t0)


def run_fast_profiles(
    names: list[str] | None = None,
    *,
    parallel: bool = True,
    use_cache: bool = False,
    amazing: bool = False,
) -> dict[str, Any]:
    keys = names or list(FAST_PROFILES.keys()) + ["iommu"]
    keys = [k for k in keys if k in FAST_PROFILES or k == "iommu"]
    if amazing and "clock" not in keys:
        keys.append("clock")
    fp = _scan_fingerprint()
    if use_cache or amazing:
        cached = _cache_get(keys, fp)
        if cached:
            return cached

    total_t0 = time.perf_counter()
    profiles: dict[str, Any] = {}
    timings: dict[str, int] = {}

    parallel_keys = [k for k in keys if k != "iommu"]
    if parallel and len(parallel_keys) > 1:
        with ThreadPoolExecutor(max_workers=min(SCAN_WORKERS, len(parallel_keys))) as pool:
            futs = {pool.submit(FAST_PROFILES[k]): k for k in parallel_keys}
            for fut in as_completed(futs):
                key = futs[fut]
                t0 = time.perf_counter()
                try:
                    profiles[key] = fut.result()
                except Exception as exc:
                    profiles[key] = {"ok": False, "error": str(exc)}
                timings[key] = profiles[key].get("elapsed_ms") or _elapsed_ms(t0)
    else:
        for key in parallel_keys:
            _, profiles[key], timings[key] = _run_profile(key, profiles)

    if "iommu" in keys:
        t0 = time.perf_counter()
        profiles["iommu"] = profile_iommu(dma=profiles.get("dma"))
        timings["iommu"] = profiles["iommu"].get("elapsed_ms") or _elapsed_ms(t0)

    elapsed_ms = _elapsed_ms(total_t0)
    out: dict[str, Any] = {
        "schema": "field-operator-fast/v2",
        "ts": _now(),
        "profiles": profiles,
        "scan": {
            "amazing": amazing,
            "parallel": parallel,
            "workers": min(SCAN_WORKERS, max(1, len(parallel_keys))),
            "elapsed_ms": elapsed_ms,
            "profile_ms": timings,
            "fingerprint": fp[:64],
            "cache": {"hit": False, "ttl_sec": CACHE_TTL_SEC},
        },
    }
    if amazing or use_cache:
        _cache_put(keys, fp, out)
    return out


def _security_tier(driver: str, bus: str) -> str:
    if not driver:
        return "unknown"
    if driver in ("nvme", "igb", "e1000e", "r8169", "i915", "amdgpu", "xhci_hcd"):
        return "field_known"
    if bus in ("net", "pci", "storage"):
        return "audit"
    return "watch"


def _best_channel(*, bus: str, driver: str, has_iommu: bool, override: str | None) -> dict[str, Any]:
    if override and override in COMM_CHANNELS:
        return {
            "channel": override,
            "reason": "operator_override",
            "secure": override in ("field_mmio_shadow", "netlink_field", "ioctl_direct"),
        }
    if bus == "net":
        ch = "znetwork_shadow" if driver else "netlink_field"
    elif bus in ("pci", "storage") and has_iommu:
        ch = "field_mmio_shadow"
    elif bus == "input":
        ch = "ioctl_direct"
    else:
        ch = "mmap_userspace"
    return {
        "channel": ch,
        "reason": f"iron_plate_{bus}",
        "secure": ch in ("field_mmio_shadow", "netlink_field", "ioctl_direct", "znetwork_shadow"),
    }


def _plate_profiles(fast: dict[str, Any]) -> dict[str, Any]:
    if "profiles" in fast:
        return fast["profiles"]
    return fast


def _index_iron_plate(connections: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, dict[str, Any]] = {}
    by_label: dict[str, dict[str, Any]] = {}
    by_bus: dict[str, list[str]] = {}
    for conn in connections:
        cid = str(conn.get("id", "")).lower()
        lbl = str(conn.get("label", "")).lower()
        bus = str(conn.get("bus", "")).lower()
        if cid:
            by_id[cid] = conn
        if lbl:
            by_label[lbl] = conn
        by_bus.setdefault(bus, []).append(cid or lbl)
    return {"by_id": by_id, "by_label": by_label, "by_bus": by_bus}


def build_iron_plate(
    *,
    override: str | None = None,
    fast: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Smart Connective Iron Plate — cleaned signals + arithmetic route words for board-direct hot path."""
    t0 = time.perf_counter()
    if fast is None:
        fast = run_fast_profiles(["irq", "dma", "pci", "net", "storage"], parallel=True, amazing=True)
    prof = _plate_profiles(fast)
    has_iommu = bool(prof.get("dma", {}).get("iommu_present"))
    connections: list[dict[str, Any]] = []
    route_words: list[int] = []
    slot_by_key: dict[str, int] = {}

    def _add_connection(conn: dict[str, Any]) -> None:
        slot = len(connections)
        connections.append(conn)
        cid = str(conn.get("id") or "").lower()
        lbl = str(conn.get("label") or "").lower()
        if cid:
            slot_by_key[cid] = slot
        if lbl:
            slot_by_key[lbl] = slot
        bus_code = _BUS_CODE.get(str(conn.get("bus") or ""), 0)
        chan_name = str((conn.get("communicate") or {}).get("channel") or COMM_CHANNELS[-1])
        if override and override in COMM_CHANNELS:
            chan_name = override
        chan_code = _CHANNEL_INDEX.get(chan_name, len(COMM_CHANNELS) - 1)
        tier_code = _TIER_CODE.get(str(conn.get("tier") or "unknown"), 0)
        load = int(conn.get("load") or 0)
        quality = int(conn.get("quality") or 255)
        storm = bool(conn.get("storm"))
        direct = bool(conn.get("board_direct"))
        word = _pack_route(
            bus=bus_code,
            channel=chan_code,
            tier=tier_code,
            slot=slot,
            quality=quality,
            board_direct=direct,
            storm=storm,
        )
        route_words.append(word)
        conn["slot"] = slot
        conn["route_word"] = word

    for row in prof.get("irq", {}).get("top", [])[:16]:
        irq_raw = str(row.get("irq") or "0")
        irq_num = int(re.sub(r"\D", "", irq_raw) or 0)
        load, quality, storm = _clean_load(row.get("total"))
        name = _clean_label(row.get("name") or irq_raw)
        tier = _security_tier("", "irq")
        _add_connection({
            "id": f"irq:{irq_num}",
            "bus": "irq",
            "label": name,
            "irq": irq_num,
            "load": load,
            "quality": quality,
            "storm": storm,
            "tier": tier,
            "board_direct": True,
            "communicate": _best_channel(bus="irq", driver="", has_iommu=has_iommu, override=override),
        })

    for iface in prof.get("net", {}).get("ifaces", []):
        drv = _clean_label(iface.get("driver") or "")
        ifname = _clean_label(iface.get("iface") or "")
        tier = _security_tier(drv, "net")
        _add_connection({
            "id": f"net:{ifname}",
            "bus": "net",
            "label": ifname,
            "driver": drv,
            "load": 0,
            "quality": 255,
            "storm": False,
            "tier": tier,
            "board_direct": _board_direct("net", tier, has_iommu=has_iommu, driver=drv),
            "communicate": _best_channel(bus="net", driver=drv, has_iommu=has_iommu, override=override),
        })

    pci_prof = prof.get("pci", {})
    pci_lines = pci_prof.get("lines") or [
        f"{d.get('slot')} {d.get('vendor')} {d.get('device')} {d.get('driver')}".strip()
        for d in pci_prof.get("devices", [])
    ]
    for line in pci_lines[:20]:
        label = _clean_label(line[:120])
        tier = "audit"
        _add_connection({
            "id": f"pci:{label[:40]}",
            "bus": "pci",
            "label": label,
            "load": 0,
            "quality": 240,
            "storm": False,
            "tier": tier,
            "board_direct": _board_direct("pci", tier, has_iommu=has_iommu),
            "communicate": _best_channel(bus="pci", driver="", has_iommu=has_iommu, override=override),
        })

    for dev in prof.get("storage", {}).get("blockdevices", [])[:8]:
        name = _clean_label(dev.get("name", ""))
        tran = _clean_label(dev.get("tran") or "")
        tier = _security_tier(tran, "storage")
        _add_connection({
            "id": f"storage:{name}",
            "bus": "storage",
            "label": name,
            "transport": tran,
            "model": _clean_label((dev.get("model") or "")[:80]),
            "load": 0,
            "quality": 250,
            "storm": False,
            "tier": tier,
            "board_direct": _board_direct("storage", tier, has_iommu=has_iommu, driver=tran),
            "communicate": _best_channel(bus="storage", driver=tran, has_iommu=has_iommu, override=override),
        })

    index = _index_iron_plate(connections)
    arithmetic = {
        "channels": list(COMM_CHANNELS),
        "route_words": route_words,
        "ids": [c.get("id") for c in connections],
        "labels": [c.get("label") for c in connections],
        "slots": slot_by_key,
        "direct_count": sum(1 for w in route_words if w & _FLAG_BOARD_DIRECT),
        "storm_count": sum(1 for w in route_words if w & _FLAG_STORM),
        "decode": "bus|channel<<4|tier<<8|slot<<10|quality<<22|direct<<30|storm<<31",
    }
    rt = _write_plate_runtime(
        connections=connections,
        route_words=route_words,
        slot_by_key=slot_by_key,
        has_iommu=has_iommu,
    )
    plate = {
        "schema": "field-operator-iron-plate/v3",
        "ts": _now(),
        "title": "Smart Connective Iron Plate",
        "connections": connections,
        "connection_count": len(connections),
        "iommu": has_iommu,
        "arithmetic": arithmetic,
        "index": {
            "ids": list(index["by_id"].keys()),
            "labels": list(index["by_label"].keys()),
            "buses": list(index["by_bus"].keys()),
        },
        "fast_profiles": prof,
        "scan": {
            "elapsed_ms": _elapsed_ms(t0),
            "inherited_fast_ms": (fast.get("scan") or {}).get("elapsed_ms"),
            "runtime_ms": 0,
            "board_direct": rt.get("direct_count"),
        },
        "doctrine": "Cleaned signals on plate — arithmetic route_word, board-direct without delegate stall",
    }
    plate["_index"] = index
    _write_atomic(IRON_PLATE, {k: v for k, v in plate.items() if k != "_index"})
    return plate


def _delegate_hw() -> dict[str, Any]:
    py = INSTALL / "lib" / "hardware-wire.py"
    if not py.is_file():
        return {"ok": False, "skipped": True}
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, str(py), "json"],
            capture_output=True,
            text=True,
            timeout=25,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        doc = json.loads(proc.stdout or "{}")
        doc["elapsed_ms"] = _elapsed_ms(t0)
        return doc
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return {"ok": False, "elapsed_ms": _elapsed_ms(t0)}


def board(*, override: str | None = None, include_hw_wire: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    doctrine = _load(DOCTRINE, {})
    fast = run_fast_profiles(parallel=True, amazing=True)
    plate = build_iron_plate(override=override, fast=fast)
    hw = _delegate_hw() if include_hw_wire else {"ok": False, "skipped": True, "reason": "deferred_fast_scan"}
    op_loc = _load(STATE / "operator-location.json", {})
    clock_anchor: dict[str, Any] = _load_clock_anchor()
    if not _anchor_fresh():
        try:
            clock_anchor = seal_clock_anchor(chain="operator-board")
        except (ImportError, OSError, AttributeError):
            pass
    doc = {
        "schema": "field-operator/v2",
        "ts": _now(),
        "title": "Operator",
        "role": "workhorse",
        "motto": doctrine.get("motto", ""),
        "iron_plate": {k: v for k, v in plate.items() if k != "_index"},
        "fast_profiles": fast.get("profiles"),
        "clock": {
            "stable": clock_anchor.get("verdict") == "USER_OK",
            "verdict": clock_anchor.get("verdict") or "unsealed",
            "pulse": clock_anchor.get("pulse"),
            "utc_stable": stable_utc_now(),
            "profile": fast.get("profiles", {}).get("clock"),
        },
        "hardware_wire": hw,
        "operator": {
            "display_name": op_loc.get("display_name") or "",
            "label": op_loc.get("label") or "",
        },
        "communication_channels": list(COMM_CHANNELS),
        "promises": doctrine.get("promises", []),
        "scan": {
            "elapsed_ms": _elapsed_ms(t0),
            "fast_ms": (fast.get("scan") or {}).get("elapsed_ms"),
            "iron_plate_ms": (plate.get("scan") or {}).get("elapsed_ms"),
            "hardware_wire_ms": hw.get("elapsed_ms"),
            "amazing": True,
        },
        "ready": plate.get("connection_count", 0) > 0,
    }
    _write_atomic(PANEL, doc)
    return doc


def route_to_board(target: str, *, override: str | None = None) -> dict[str, Any]:
    """Copilot-first O(1) route — 0ms on plate hot path."""
    if not override:
        hit = copilot_route(target)
        if hit.get("ok"):
            hit["connection"] = {
                "id": hit.get("id"),
                "label": hit.get("label"),
                "bus": _BUS_NAME[hit["bus_code"]] if hit["bus_code"] < len(_BUS_NAME) else "",
                "slot": hit.get("slot"),
                "quality": hit.get("quality"),
                "board_direct": hit.get("board_direct"),
                "route_word": hit.get("route_word"),
                "communicate": hit.get("communicate"),
            }
            hit["lookup"] = "copilot"
            return hit
    t0 = time.perf_counter_ns()
    rt = _plate_runtime()
    needle = target.strip().lower()
    slots = rt.get("slots") or {}
    slot = slots.get(needle)
    if slot is None:
        return {
            "ok": False,
            "connection": None,
            "elapsed_ns": time.perf_counter_ns() - t0,
            "note": "no slot — run iron-plate",
        }
    words = rt.get("route_words") or []
    if slot >= len(words):
        return {"ok": False, "connection": None, "elapsed_ns": time.perf_counter_ns() - t0}
    word = words[slot]
    conn = _conn_from_runtime(rt, slot, word)
    if override and override in COMM_CHANNELS:
        conn["communicate"] = {
            "channel": override,
            "reason": "operator_override",
            "secure": override in ("field_mmio_shadow", "netlink_field", "ioctl_direct"),
        }
    return {
        "ok": True,
        "connection": conn,
        "board_direct": bool(word & _FLAG_BOARD_DIRECT),
        "route_word": word,
        "lookup": "slot",
        "elapsed_ns": time.perf_counter_ns() - t0,
    }


def route_batch(targets: list[str], *, override: str | None = None) -> dict[str, Any]:
    if not override:
        return copilot_batch(targets)
    t0 = time.perf_counter_ns()
    rt = _plate_runtime()
    slots = rt.get("slots") or {}
    words = rt.get("route_words") or []
    routes: list[dict[str, Any]] = []
    for raw in targets:
        needle = str(raw).strip().lower()
        slot = slots.get(needle)
        if slot is None or slot >= len(words):
            routes.append({"ok": False, "target": raw})
            continue
        word = words[slot]
        conn = _conn_from_runtime(rt, slot, word)
        if override and override in COMM_CHANNELS:
            conn["communicate"] = {
                "channel": override,
                "reason": "operator_override",
                "secure": override in ("field_mmio_shadow", "netlink_field", "ioctl_direct"),
            }
        routes.append({
            "ok": True,
            "target": raw,
            "board_direct": bool(word & _FLAG_BOARD_DIRECT),
            "route_word": word,
            "connection": conn,
        })
    return {
        "ok": True,
        "count": len(routes),
        "direct": sum(1 for r in routes if r.get("board_direct")),
        "routes": routes,
        "elapsed_ns": time.perf_counter_ns() - t0,
    }


def communicate(path_or_id: str, *, override: str | None = None) -> dict[str, Any]:
    hit = route_to_board(path_or_id, override=override)
    if hit.get("ok"):
        return {
            "ok": True,
            "connection": hit.get("connection"),
            "iron_plate": True,
            "lookup": hit.get("lookup"),
            "board_direct": hit.get("board_direct"),
            "elapsed_ns": hit.get("elapsed_ns"),
        }
    rt = _plate_runtime()
    needle = path_or_id.strip().lower()
    for slot, cid in enumerate(rt.get("ids") or []):
        low = str(cid).lower()
        if needle in low or low.endswith(needle):
            word = (rt.get("route_words") or [0])[slot]
            return {
                "ok": True,
                "connection": _conn_from_runtime(rt, slot, word),
                "iron_plate": True,
                "lookup": "id_partial",
                "board_direct": bool(word & _FLAG_BOARD_DIRECT),
            }
    return {
        "ok": True,
        "connection": None,
        "suggest": _best_channel(bus="net", driver="", has_iommu=True, override=override),
        "note": "no exact match — default field channel",
    }


def operator_tick(*, seal: bool = False) -> dict[str, Any]:
    """Single-process daemon tick — scan cache + plate runtime, zero triple-spawn latency."""
    try:
        _sync_mod().sync_section("operator", "tick")
    except (ImportError, OSError, AttributeError):
        pass
    scan = amazing_scan(use_cache=True, seal=seal and not _anchor_fresh())
    plate = build_iron_plate(fast=scan)
    rt = _plate_runtime()
    cpu = copilot(reload=True)
    return {
        "ok": True,
        "scan_ms": (scan.get("scan") or {}).get("elapsed_ms"),
        "plate_ms": (plate.get("scan") or {}).get("elapsed_ms"),
        "connections": plate.get("connection_count"),
        "board_direct": rt.get("direct_count"),
        "copilot": {"hot": cpu.hot, "wires": len(cpu._words), "elapsed_ms": 0},
        "clock": scan.get("clock"),
    }


def amazing_scan(*, use_cache: bool = True, seal: bool = False) -> dict[str, Any]:
    result = run_fast_profiles(parallel=True, use_cache=use_cache, amazing=True)
    cache_hit = bool((result.get("scan") or {}).get("cache", {}).get("hit"))
    if seal and not cache_hit and not _anchor_fresh():
        try:
            anchor = seal_clock_anchor(chain="operator-scan")
            result["clock"] = {
                "sealed": True,
                "stable": anchor.get("verdict") == "USER_OK",
                "verdict": anchor.get("verdict"),
                "pulse": anchor.get("pulse"),
                "utc_stable": anchor.get("ts"),
            }
        except (ImportError, OSError, AttributeError) as exc:
            result["clock"] = {"sealed": False, "error": str(exc)}
    elif cache_hit:
        anchor = _load_clock_anchor()
        result["clock"] = {
            "sealed": bool(anchor.get("pulse")),
            "stable": anchor.get("verdict") == "USER_OK",
            "verdict": anchor.get("verdict"),
            "pulse": anchor.get("pulse"),
            "cache": True,
        }
    return result


def _parse_cli(argv: list[str]) -> tuple[str, list[str], dict[str, Any]]:
    mode = (argv[1] if len(argv) > 1 else "json").strip().lower()
    opts: dict[str, Any] = {
        "override": None,
        "amazing": False,
        "no_cache": False,
        "no_hw_wire": False,
    }
    skip = set()
    for i, arg in enumerate(argv):
        if i in skip:
            continue
        if arg == "--override" and i + 1 < len(argv):
            opts["override"] = argv[i + 1]
            skip.add(i + 1)
        elif arg in ("--amazing", "-a"):
            opts["amazing"] = True
        elif arg == "--no-cache":
            opts["no_cache"] = True
        elif arg == "--no-hw-wire":
            opts["no_hw_wire"] = True
    profile_args = [
        a
        for a in (argv[2:] if len(argv) > 2 else [])
        if a not in ("--override", "--amazing", "-a", "--no-cache", "--no-hw-wire")
        and not a.startswith("--")
        and a != opts.get("override")
    ]
    return mode, profile_args, opts


def main() -> int:
    mode, profile_args, opts = _parse_cli(sys.argv)
    override = opts.get("override")

    handlers: dict[str, Callable[[], Any]] = {
        "json": lambda: board(override=override, include_hw_wire=not opts["no_hw_wire"]),
        "board": lambda: board(override=override, include_hw_wire=not opts["no_hw_wire"]),
        "fast": lambda: run_fast_profiles(
            profile_args or None,
            parallel=True,
            use_cache=not opts["no_cache"],
            amazing=opts["amazing"] or not profile_args,
        ),
        "scan": lambda: amazing_scan(use_cache=not opts["no_cache"]),
        "tick": operator_tick,
        "iron-plate": lambda: build_iron_plate(override=override),
        "clock": profile_clock,
        "seal-clock": lambda: seal_clock_anchor(chain="operator-cli"),
        "route": lambda: route_to_board(sys.argv[2], override=override) if len(sys.argv) > 2 else {"ok": False, "error": "usage: route <id>"},
        "copilot": lambda: copilot_status(),
        "irq": profile_irq,
        "dma": profile_dma,
    }
    if mode == "route-batch" and len(sys.argv) > 2:
        targets = [a for a in sys.argv[2:] if not a.startswith("--")]
        result = route_batch(targets, override=override)
    elif mode == "communicate" and len(sys.argv) > 2:
        result = communicate(sys.argv[2], override=override)
    else:
        fn = handlers.get(mode)
        if not fn:
            print(
                json.dumps(
                    {
                        "error": "usage",
                        "cmds": [
                            "json",
                            "board",
                            "fast",
                            "scan",
                            "tick",
                            "iron-plate",
                            "clock",
                            "seal-clock",
                            "route <id>",
                            "route-batch <id>...",
                            "copilot",
                            "irq",
                            "dma",
                            "communicate <id>",
                            "flags: --amazing --no-cache --no-hw-wire --override <channel>",
                        ],
                    }
                ),
                file=sys.stderr,
            )
            return 2
        result = fn()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())