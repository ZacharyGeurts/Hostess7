#!/usr/bin/env pythong
"""Field device registry — never more active devices than exist; stale fakes evicted for AI."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
REGISTRY_PATH = STATE / "field-device-registry.json"
LAN_STABLE_PATH = STATE / "field-lan-device-stable.json"
EVICT_LEDGER_PATH = STATE / "field-device-evict.jsonl"
SEED_PATH = INSTALL / "data" / "field-device-registry-seed.json"

_DEFAULT_POLICY = {
    "never_exceed_existence": True,
    "ai_evict_stale": True,
    "stale_after_seconds": 86400,
    "lan_stale_after_seconds": 7200,
    "min_corroboration_sources": 1,
    "existence_floor": 1,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_seconds(raw: str | None, *, now: datetime | None = None) -> float | None:
    ts = _parse_ts(raw)
    if not ts:
        return None
    ref = now or datetime.now(timezone.utc)
    return max(0.0, (ref - ts).total_seconds())


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_evict(row: dict[str, Any]) -> None:
    try:
        EVICT_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EVICT_LEDGER_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _policy(doc: dict[str, Any] | None = None) -> dict[str, Any]:
    seed = _load(SEED_PATH, {})
    merged = dict(_DEFAULT_POLICY)
    merged.update((seed.get("policy") or {}))
    if doc:
        merged.update((doc.get("policy") or {}))
    return merged


def _host_id() -> str:
    return socket.gethostname().split(".")[0] or "local"


def _hardware_existence_count() -> int:
    """Ground-truth device slots: host + USB + net ifaces + audio + input."""
    count = 1  # this host always exists
    usb_base = Path("/sys/bus/usb/devices")
    if usb_base.is_dir():
        for dev in usb_base.iterdir():
            if dev.name.startswith("."):
                continue
            if (dev / "idVendor").is_file() and (dev / "idProduct").is_file():
                count += 1
    net_base = Path("/sys/class/net")
    if net_base.is_dir():
        count += sum(1 for iface in net_base.iterdir() if iface.name != "lo")
    asound = Path("/proc/asound/cards")
    if asound.is_file():
        count += sum(1 for line in asound.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip())
    input_devs = Path("/proc/bus/input/devices")
    if input_devs.is_file():
        count += sum(1 for line in input_devs.read_text(encoding="utf-8", errors="replace").splitlines() if line.startswith("H: Handlers="))
    return max(1, count)


def devices_in_existence(*, lan_corroborated: int = 0) -> dict[str, Any]:
    """Canonical ceiling — active registry must never exceed this."""
    hardware = _hardware_existence_count()
    policy = _policy()
    floor = int(policy.get("existence_floor") or 1)
    # LAN corroborated peers are real only when multi-sourced; hardware is local truth.
    ceiling = max(floor, hardware, int(lan_corroborated or 0))
    return {
        "count": ceiling,
        "hardware": hardware,
        "lan_corroborated": int(lan_corroborated or 0),
        "last_timestamp": _now(),
    }


def _device_key(dev: dict[str, Any]) -> str:
    raw = str(dev.get("id") or dev.get("ip") or dev.get("mac") or dev.get("hostname") or "").strip().lower()
    if raw:
        return raw
    blob = json.dumps(dev, sort_keys=True, ensure_ascii=False).encode()
    return "dev_" + hashlib.sha256(blob).hexdigest()[:16]


def _is_stale(dev: dict[str, Any], policy: dict[str, Any], *, lan: bool = False) -> bool:
    ttl = int(policy.get("lan_stale_after_seconds" if lan else "stale_after_seconds") or 86400)
    age = _age_seconds(dev.get("last_timestamp") or dev.get("last_seen"))
    if age is None:
        return False
    return age > ttl


def _corroboration_score(dev: dict[str, Any]) -> int:
    sources = dev.get("sources") or dev.get("tables") or []
    if isinstance(sources, list):
        return len(sources)
    return 1 if dev.get("self") else 0


def reconcile_devices(
    devices: list[dict[str, Any]],
    *,
    existence_cap: int | None = None,
    policy: dict[str, Any] | None = None,
    lan: bool = False,
    now: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Enforce existence cap and evict stale fakes.
    Returns (active_devices, evicted_devices).
    """
    pol = dict(_policy())
    if policy:
        pol.update(policy)
    stamp = now or _now()
    cap = existence_cap
    if cap is None:
        cap = devices_in_existence().get("count", 1)

    active: list[dict[str, Any]] = []
    evicted: list[dict[str, Any]] = []

    ranked = sorted(
        devices,
        key=lambda d: (
            -int(bool(d.get("self"))),
            -_corroboration_score(d),
            -float(d.get("existence_score") or 0),
            str(d.get("last_timestamp") or d.get("last_seen") or ""),
        ),
    )

    for dev in ranked:
        row = dict(dev)
        if not row.get("last_timestamp"):
            row["last_timestamp"] = row.get("last_seen") or stamp
        is_self = bool(row.get("self"))
        stale = bool(pol.get("ai_evict_stale")) and not is_self and _is_stale(row, pol, lan=lan)
        min_src = int(pol.get("min_corroboration_sources") or 1)
        under_corroborated = _corroboration_score(row) < min_src and not is_self
        over_cap = bool(pol.get("never_exceed_existence")) and not is_self and len(active) >= cap

        if stale or under_corroborated or over_cap:
            row["active"] = False
            row["fake"] = True
            row["evicted_at"] = stamp
            row["evict_reason"] = (
                "stale" if stale else "under_corroborated" if under_corroborated else "over_existence_cap"
            )
            evicted.append(row)
            _append_evict({
                "ts": stamp,
                "event": "evict_fake",
                "device_id": row.get("id") or _device_key(row),
                "reason": row["evict_reason"],
                "last_timestamp": row.get("last_timestamp"),
                "sources": row.get("sources") or row.get("tables") or [],
            })
            continue

        row["active"] = True
        row["fake"] = False
        active.append(row)

    return active, evicted


def touch_device(dev: dict[str, Any], *, now: str | None = None) -> dict[str, Any]:
    row = dict(dev)
    stamp = now or _now()
    row["last_seen"] = stamp
    row["last_timestamp"] = stamp
    return row


def merge_sightings(
    prev_devices: list[dict[str, Any]],
    sightings: list[dict[str, Any]],
    *,
    now: str | None = None,
) -> list[dict[str, Any]]:
    """Merge new sightings into stable registry, refreshing last_timestamp."""
    stamp = now or _now()
    by_key: dict[str, dict[str, Any]] = {}
    for dev in prev_devices:
        key = _device_key(dev)
        by_key[key] = dict(dev)

    for sight in sightings:
        key = _device_key(sight)
        prev = by_key.get(key, {})
        merged = {**prev, **sight}
        merged["id"] = merged.get("id") or key
        merged = touch_device(merged, now=stamp)
        merged["sightings"] = int(prev.get("sightings") or 0) + 1
        merged.setdefault("first_timestamp", prev.get("first_timestamp") or stamp)
        by_key[key] = merged

    return list(by_key.values())


def build_registry(*, refresh_self: bool = True) -> dict[str, Any]:
    seed = _load(SEED_PATH, {"schema": "field-device-registry/v1", "devices": []})
    doc = _load(REGISTRY_PATH, seed)
    policy = _policy(doc)
    host = _host_id()
    devices = list(doc.get("devices") or seed.get("devices") or [])
    stamp = _now()

    if refresh_self:
        found = False
        for idx, dev in enumerate(devices):
            if dev.get("self") or dev.get("id") in (host, "local"):
                dev.update({
                    "id": host,
                    "hostname": socket.gethostname(),
                    "machine": platform.machine(),
                    "panel_port": int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")),
                    "queen_port": int(os.environ.get("QUEEN_WORLD_PORT", "9481")),
                    "self": True,
                    "role": dev.get("role") or "primary",
                })
                devices[idx] = touch_device(dev, now=stamp)
                found = True
                break
        if not found:
            devices.insert(0, touch_device({
                "id": host,
                "role": "primary",
                "display_name": "This host",
                "kind": "workstation",
                "hostname": socket.gethostname(),
                "machine": platform.machine(),
                "panel_port": int(os.environ.get("NEXUS_THREAT_PANEL_PORT", "9477")),
                "queen_port": int(os.environ.get("QUEEN_WORLD_PORT", "9481")),
                "self": True,
                "display_open": True,
                "drop_in": True,
            }, now=stamp))

    existence = devices_in_existence()
    active, evicted = reconcile_devices(devices, existence_cap=existence["count"], policy=policy)

    out = {
        **doc,
        "schema": "field-device-registry/v1",
        "ts": stamp,
        "policy": policy,
        "devices_in_existence": existence,
        "devices": active,
        "device_count": len(active),
        "evicted": evicted,
        "evicted_count": len(evicted),
        "ai_note": (
            "Active devices never exceed devices_in_existence.count. "
            "Entries without fresh last_timestamp are marked fake and evicted."
        ),
    }
    _save_atomic(REGISTRY_PATH, out)
    return out


def build_lan_stable(
    sightings: list[dict[str, Any]],
    *,
    policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """LAN device stable — corroboration + existence cap + stale eviction."""
    pol = _policy()
    if policy:
        pol.update(policy)
    stamp = _now()
    prev = _load(LAN_STABLE_PATH, {"devices": []})
    merged = merge_sightings(prev.get("devices") or [], sightings, now=stamp)

    corroborated = sum(1 for d in merged if _corroboration_score(d) >= int(pol.get("min_corroboration_sources") or 1))
    existence = devices_in_existence(lan_corroborated=corroborated)
    # LAN registry cannot exceed corroborated existence (never phantom inflation).
    lan_cap = min(existence["count"], max(corroborated, int(pol.get("existence_floor") or 1)))

    active, evicted = reconcile_devices(merged, existence_cap=lan_cap, policy=pol, lan=True)

    doc = {
        "schema": "field-lan-device-stable/v1",
        "updated": stamp,
        "devices_in_existence": existence,
        "lan_existence_cap": lan_cap,
        "policy": pol,
        "devices": active,
        "device_count": len(active),
        "evicted": evicted,
        "evicted_count": len(evicted),
        "ai_note": (
            "LAN stable never lists more devices than corroborated existence. "
            "Stale last_timestamp → fake → evicted for AI discard."
        ),
    }
    _save_atomic(LAN_STABLE_PATH, doc)
    return doc


def main() -> int:
    import sys

    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(build_registry(), ensure_ascii=False))
        return 0
    if cmd == "existence":
        print(json.dumps(devices_in_existence(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-device-registry.py [json|existence]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())