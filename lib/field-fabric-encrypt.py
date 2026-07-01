#!/usr/bin/env pythong
"""Zero-cost 4+ slot encryption — AMOURANTHRTX FieldFabric parallel lanes.

Parallel slot processors; zero-cost when lanes are not armed (no HMAC work).
Mirrors FieldFabric.hpp: leadIn / core / leadOut / entropy + optional extra slots.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
PANEL = STATE / "field-fabric-encrypt.json"

DEFAULT_SLOTS = max(4, int(os.environ.get("NEXUS_FABRIC_ENCRYPT_SLOTS", "4") or "4"))
_SEAL_KEY = os.environ.get("NEXUS_FIELD_SEAL_KEY", "sovereign-field-fabric")

SLOT_NAMES = ("lead_in", "core", "lead_out", "entropy")


class FabricEncrypt:
    """Parallel encryption lanes — idle = zero CPU cost."""

    __slots__ = ("slot_count", "armed", "lanes", "_key")

    def __init__(self, slot_count: int = DEFAULT_SLOTS, *, key: str = _SEAL_KEY) -> None:
        self.slot_count = max(4, slot_count)
        self.armed = 0
        self.lanes = [0.0] * self.slot_count
        self._key = key

    def arm(self, slot: int) -> None:
        if 0 <= slot < self.slot_count:
            self.armed |= 1 << slot

    def arm_default_four(self) -> None:
        for i in range(min(4, self.slot_count)):
            self.arm(i)

    def arm_all(self) -> None:
        self.armed = (1 << self.slot_count) - 1

    def zero_cost_idle(self) -> bool:
        return self.armed == 0

    @staticmethod
    def _lane_peak(slot: int, peak: float) -> float:
        if slot == 0:
            return peak * 1.15
        if slot == 2:
            return peak * 0.87
        if slot == 3:
            return peak * 0.31 + 0.19
        return peak

    def sample(self, slot: int, payload: bytes) -> str | None:
        if slot < 0 or slot >= self.slot_count:
            return None
        if not (self.armed & (1 << slot)):
            return None
        peak = self._lane_peak(slot, self.lanes[slot])
        material = f"{self._key}:{slot}:{peak:.6f}".encode()
        return hmac.new(material, payload, hashlib.sha256).hexdigest()[:16]

    def dispatch_extended(self, peaks: list[float], payload: bytes) -> dict[str, Any]:
        t0 = time.perf_counter_ns()
        seals: dict[str, str] = {}
        for slot in range(self.slot_count):
            peak = peaks[slot] if slot < len(peaks) else 0.0
            self.lanes[slot] = peak
            tag = self.sample(slot, payload)
            if tag is not None:
                name = SLOT_NAMES[slot] if slot < len(SLOT_NAMES) else f"slot_{slot}"
                seals[name] = tag
        elapsed_us = (time.perf_counter_ns() - t0) / 1000.0
        return {
            "seals": seals,
            "armed": self.armed,
            "slot_count": self.slot_count,
            "zero_cost_idle": self.zero_cost_idle(),
            "elapsed_us": round(elapsed_us, 3),
            "lanes_active": len(seals),
        }

    def pack_push_peaks(self, peaks: list[float]) -> list[float]:
        pad = [0.0, 0.0, 0.0, 0.0]
        if peaks:
            pad[0] = peaks[0]
        if len(peaks) > 1:
            pad[1] = peaks[1]
        if len(peaks) > 2:
            pad[2] = peaks[2]
        if len(peaks) > 3:
            pad[3] = peaks[3]
        return pad


def seal_payload(
    payload: bytes,
    *,
    peaks: list[float] | None = None,
    arm_slots: int | None = None,
    slot_count: int = DEFAULT_SLOTS,
) -> dict[str, Any]:
    fabric = FabricEncrypt(slot_count=slot_count)
    if arm_slots is None:
        fabric.arm_default_four()
    elif arm_slots <= 0:
        pass
    elif arm_slots >= fabric.slot_count:
        fabric.arm_all()
    else:
        for i in range(arm_slots):
            fabric.arm(i)
    peak_list = peaks or fabric.pack_push_peaks([0.18, 1.0, 0.22, 0.12])
    doc = fabric.dispatch_extended(peak_list, payload)
    doc["schema"] = "field-fabric-encrypt/v1"
    doc["cost"] = "zero" if doc["zero_cost_idle"] else "armed_only"
    return doc


def panel_json() -> dict[str, Any]:
    if PANEL.is_file():
        try:
            return json.loads(PANEL.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    idle = seal_payload(b"idle-probe", arm_slots=0)
    armed = seal_payload(b"armed-probe", arm_slots=4)
    return {
        "schema": "field-fabric-encrypt/v1",
        "slot_count": DEFAULT_SLOTS,
        "slot_names": list(SLOT_NAMES),
        "default_slots": 4,
        "zero_cost_when_idle": True,
        "amouranthrtx": "FieldFabric.dispatchExtended",
        "idle_probe": idle,
        "armed_probe": armed,
        "free": True,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "seal" and len(sys.argv) > 2:
        payload = sys.argv[2].encode()
        slots = int(sys.argv[3]) if len(sys.argv) > 3 else 4
        print(json.dumps(seal_payload(payload, arm_slots=slots), ensure_ascii=False))
        return 0
    if cmd == "idle":
        print(json.dumps(seal_payload(b"", arm_slots=0), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-fabric-encrypt.py [json|seal <text> [slots]|idle]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())