#!/usr/bin/env pythong
"""Hostess 7 control balancer — thermals, bandwidth, disk I/O, compute; mission-primary."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", INSTALL / "Hostess7"))
DOCTRINE = INSTALL / "data" / "hostess7-control-balancer-doctrine.json"
CONFIG = STATE / "hostess7-control-balancer.json"
PANEL = STATE / "hostess7-control-balancer-panel.json"
POLICY_ENV = STATE / "hostess7-control-balancer-policy.env"
LEDGER = STATE / "hostess7-control-balancer-ledger.jsonl"

VALID_MODES = frozenset({"balanced", "mission", "connectionless"})


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _append(row: dict[str, Any]) -> None:
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({**row, "ts": _now()}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _mod(name: str, rel: str) -> Any | None:
    path = INSTALL / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(f"{name}_{path.stem}", path)
    if not spec or not spec.loader:
        return None
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _default_lanes() -> dict[str, dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    out: dict[str, dict[str, Any]] = {}
    for lane in doc.get("lanes") or []:
        lid = str(lane.get("id") or "").strip()
        if not lid:
            continue
        out[lid] = {
            "id": lid,
            "label": lane.get("label") or lid,
            "enabled": bool(lane.get("enabled_default", True)),
            "weight": float(lane.get("weight_default", 1.0)),
            "luxury": bool(lane.get("luxury", False)),
        }
    return out


def load_config() -> dict[str, Any]:
    doc = _load(CONFIG, {})
    doctrine = _load(DOCTRINE, {})
    defaults = _default_lanes()
    lanes = dict(defaults)
    for lid, row in (doc.get("lanes") or {}).items():
        if lid in lanes:
            lanes[lid].update({k: v for k, v in row.items() if k in ("enabled", "weight", "label")})
    mode = str(doc.get("mode") or "balanced")
    if mode not in VALID_MODES:
        mode = "balanced"
    return {
        "schema": "hostess7-control-balancer-config/v1",
        "updated": doc.get("updated") or _now(),
        "mode": mode,
        "lanes": lanes,
        "connectionless": bool(doc.get("connectionless") or mode == "connectionless"),
        "internet_luxury": doc.get("internet_luxury", True),
        "motto": doctrine.get("motto"),
    }


def save_config(cfg: dict[str, Any]) -> None:
    cfg["updated"] = _now()
    _save(CONFIG, cfg)


def _disk_paths() -> list[Path]:
    paths = [INSTALL, STATE, HOSTESS7]
    brain = Path(os.environ.get("HOSTESS7_BRAIN_STATE", HOSTESS7 / "brain" / "state"))
    if brain not in paths:
        paths.append(brain)
    return paths


def _probe_thermal() -> dict[str, Any]:
    panel = _load(STATE / "field-thermal-guard.json", {})
    if panel:
        return {
            "ok": True,
            "headroom_pct": panel.get("headroom_pct"),
            "peak_c": panel.get("peak_c"),
            "anomaly": (panel.get("anomaly") or {}).get("active"),
            "source": "panel",
        }
    tg = _mod("thermal", "lib/field-thermal-guard.py")
    if tg and hasattr(tg, "evaluate"):
        try:
            ev = tg.evaluate()
            return {
                "ok": True,
                "headroom_pct": ev.get("headroom_pct"),
                "peak_c": ev.get("peak_c"),
                "anomaly": (ev.get("anomaly") or {}).get("active"),
                "source": "evaluate",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
    return {"ok": False, "error": "thermal_guard_missing"}


def _probe_bandwidth() -> dict[str, Any]:
    hist = _load(STATE / "connection-history.json", {})
    peers = hist.get("peers") or {}
    conn_count = len(peers)
    harm = sum(1 for p in peers.values() if p.get("block_recommended"))
    return {
        "ok": True,
        "connection_count": conn_count,
        "harm_candidates": harm,
        "luxury": True,
        "source": "connection-history",
    }


def _probe_disk_io() -> dict[str, Any]:
    usage: list[dict[str, Any]] = []
    min_free_pct = 100.0
    for p in _disk_paths():
        try:
            if not p.exists():
                continue
            du = shutil.disk_usage(p)
            free_pct = round(100.0 * du.free / max(du.total, 1), 1)
            min_free_pct = min(min_free_pct, free_pct)
            rel = str(p.relative_to(INSTALL)) if p.is_relative_to(INSTALL) else str(p)
            usage.append({"path": rel, "free_pct": free_pct, "free_gb": round(du.free / (1024**3), 2)})
        except OSError:
            continue
    return {
        "ok": bool(usage),
        "free_pct": min_free_pct if usage else None,
        "paths": usage,
        "source": "disk_usage",
    }


def _probe_compute() -> dict[str, Any]:
    panel = _load(STATE / "hostess7-presume-panel.json", {})
    if panel:
        return {
            "ok": True,
            "drift_us": panel.get("drift_us") or panel.get("median_drift_us"),
            "resumed_on_point": panel.get("resumed_on_point"),
            "verdict": panel.get("verdict") or panel.get("timing_verdict"),
            "source": "presume_panel",
        }
    presume = _mod("presume", "lib/hostess7-presume.py")
    if presume and hasattr(presume, "presume"):
        try:
            pr = presume.presume(4000, label="balancer_probe", alternate_id="sovereign_know")
            return {
                "ok": True,
                "drift_us": pr.get("drift_us"),
                "resumed_on_point": pr.get("resumed_on_point"),
                "source": "presume_probe",
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:120]}
    return {"ok": False, "error": "presume_missing"}


def _probe_network() -> dict[str, Any]:
    bw = _probe_bandwidth()
    connectionless = os.environ.get("HOSTESS7_CONNECTIONLESS", "0") in ("1", "true", "yes")
    cfg = load_config()
    return {
        "ok": True,
        "external_enabled": not connectionless and cfg.get("mode") != "connectionless",
        "connection_count": bw.get("connection_count", 0),
        "luxury": True,
        "internet_mandate": False,
        "source": "config+history",
    }


PROBE_FNS = {
    "thermal": _probe_thermal,
    "bandwidth": _probe_bandwidth,
    "disk_io": _probe_disk_io,
    "compute": _probe_compute,
    "network": _probe_network,
}


def probe_lanes() -> dict[str, Any]:
    cfg = load_config()
    probes: dict[str, Any] = {}
    for lid, lane in cfg.get("lanes", {}).items():
        fn = PROBE_FNS.get(lid)
        if fn and lane.get("enabled", True):
            probes[lid] = fn()
        else:
            probes[lid] = {"ok": True, "disabled": True, "skipped": not lane.get("enabled", True)}
    return probes


def _sensitive_boost() -> list[dict[str, Any]]:
    doc = _load(DOCTRINE, {})
    supreme = _load(INSTALL / "data/hostess7-supreme-authority.json", {})
    if not supreme:
        supreme = _load(HOSTESS7 / "data/hostess7-supreme-authority.json", {})
    assumes = set(supreme.get("full_system_control", {}).get("assumes") or [])
    out: list[dict[str, Any]] = []
    for area in doc.get("sensitive_areas") or []:
        aid = str(area.get("id") or "")
        bind = str(area.get("assumes") or aid)
        out.append({
            "id": aid,
            "boost": float(area.get("boost", 1.0)),
            "assumes_bound": bind in assumes,
            "secured": bind in assumes,
        })
    return out


def allocate_resources(*, mode: str | None = None) -> dict[str, Any]:
    """Dynamic allocation — sensitive lanes get more when mission or connectionless."""
    cfg = load_config()
    active_mode = mode or str(cfg.get("mode") or "balanced")
    lanes = dict(cfg.get("lanes") or {})
    probes = probe_lanes()
    sensitive = _sensitive_boost()
    boost_factor = 1.0
    if active_mode == "mission":
        boost_factor = 1.25
    elif active_mode == "connectionless":
        boost_factor = 1.15

    total_weight = 0.0
    allocation: dict[str, Any] = {}
    for lid, lane in lanes.items():
        if not lane.get("enabled", True):
            allocation[lid] = {"share_pct": 0.0, "enabled": False, "weight": 0.0}
            continue
        w = float(lane.get("weight", 1.0))
        if active_mode == "connectionless" and lane.get("luxury"):
            allocation[lid] = {"share_pct": 0.0, "enabled": False, "weight": 0.0, "connectionless_off": True}
            continue
        if active_mode == "mission" and lid in ("compute", "disk_io", "thermal"):
            w *= boost_factor
        probe = probes.get(lid) or {}
        stress = 0.0
        if lid == "thermal" and probe.get("headroom_pct") is not None:
            stress = max(0.0, 1.0 - float(probe["headroom_pct"]) / 100.0)
        elif lid == "disk_io" and probe.get("free_pct") is not None:
            stress = max(0.0, 1.0 - float(probe["free_pct"]) / 100.0)
        elif lid == "compute" and probe.get("drift_us") is not None:
            stress = min(1.0, float(probe["drift_us"]) / 50000.0)
        adj = w * (1.0 + stress * 0.5)
        allocation[lid] = {"weight": round(adj, 3), "enabled": True, "stress": round(stress, 3)}
        total_weight += adj

    for lid, row in allocation.items():
        if row.get("enabled") and total_weight > 0:
            row["share_pct"] = round(100.0 * float(row["weight"]) / total_weight, 1)

    secured = [s for s in sensitive if s.get("secured")]
    return {
        "schema": "hostess7-control-balancer-allocation/v1",
        "mode": active_mode,
        "total_weight": round(total_weight, 3),
        "allocation": allocation,
        "sensitive_areas": sensitive,
        "sensitive_secured_count": len(secured),
        "internet_luxury_not_mandate": True,
        "probes": probes,
    }


def _write_policy_env(cfg: dict[str, Any], alloc: dict[str, Any]) -> None:
    doc = _load(DOCTRINE, {})
    connless = doc.get("connectionless") or {}
    env_map: dict[str, str] = {}
    if cfg.get("connectionless") or cfg.get("mode") == "connectionless":
        for k, v in (connless.get("env") or {}).items():
            env_map[str(k)] = str(v)
    else:
        env_map["HOSTESS7_CONNECTIONLESS"] = "0"
        env_map["HOSTESS7_INTERNET_LUXURY"] = "1" if cfg.get("internet_luxury", True) else "0"

    for lid, row in (alloc.get("allocation") or {}).items():
        key = f"HOSTESS7_BALANCER_{lid.upper()}_SHARE"
        env_map[key] = str(row.get("share_pct", 0))

    env_map["HOSTESS7_BALANCER_MODE"] = str(cfg.get("mode") or "balanced")
    env_map["HOSTESS7_BALANCER_UPDATED"] = _now()

    lines = [f"{k}={v}" for k, v in sorted(env_map.items())]
    POLICY_ENV.parent.mkdir(parents=True, exist_ok=True)
    POLICY_ENV.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for k, v in env_map.items():
        os.environ[k] = v


def apply_posture(*, reason: str = "balancer_apply") -> dict[str, Any]:
    cfg = load_config()
    alloc = allocate_resources(mode=str(cfg.get("mode")))
    _write_policy_env(cfg, alloc)

    if cfg.get("mode") == "connectionless" or cfg.get("connectionless"):
        tg = _mod("thermal", "lib/field-thermal-guard.py")
        if tg and hasattr(tg, "publish_policy") and hasattr(tg, "FieldThermalGuard"):
            try:
                guard = tg.FieldThermalGuard()
                tg.publish_policy(guard)
            except Exception:
                pass

    witness = _mod("change", "lib/hostess7-change-awareness.py")
    if witness and hasattr(witness, "witness_change"):
        try:
            witness.witness_change(
                source="control_balancer",
                label=f"posture:{cfg.get('mode')}",
                detail=f"Allocation applied — {reason}",
                meta={"mode": cfg.get("mode"), "connectionless": cfg.get("connectionless")},
                notify=True,
            )
        except Exception:
            pass

    row = {
        "event": "apply_posture",
        "ok": True,
        "mode": cfg.get("mode"),
        "connectionless": cfg.get("connectionless"),
        "reason": reason,
        "policy_env": str(POLICY_ENV),
    }
    _append(row)
    return {**row, "allocation": alloc}


def set_mode(mode: str, *, apply: bool = True) -> dict[str, Any]:
    mode = (mode or "balanced").strip().lower()
    if mode not in VALID_MODES:
        return {"ok": False, "error": "invalid_mode", "valid": sorted(VALID_MODES)}
    cfg = load_config()
    cfg["mode"] = mode
    cfg["connectionless"] = mode == "connectionless"
    if mode == "connectionless":
        cfg["internet_luxury"] = False
        doc = _load(DOCTRINE, {})
        for lid in (doc.get("connectionless") or {}).get("disable_lanes") or []:
            if lid in cfg.get("lanes", {}):
                cfg["lanes"][lid]["enabled"] = False
        for lid in (doc.get("connectionless") or {}).get("boost_lanes") or []:
            if lid in cfg.get("lanes", {}):
                cfg["lanes"][lid]["weight"] = max(
                    float(cfg["lanes"][lid].get("weight", 1.0)), 1.2
                )
    save_config(cfg)
    _append({"event": "set_mode", "mode": mode})
    out = {"ok": True, "mode": mode, "connectionless": mode == "connectionless", "config": cfg}
    if apply:
        out["apply"] = apply_posture(reason=f"set_mode:{mode}")
    return out


def set_lane(lane_id: str, enabled: str | bool, weight: str | float | None = None, *, apply: bool = True) -> dict[str, Any]:
    lid = (lane_id or "").strip().lower()
    cfg = load_config()
    lanes = cfg.get("lanes") or {}
    if lid not in lanes:
        return {"ok": False, "error": "unknown_lane", "lane": lid, "known": sorted(lanes)}
    if isinstance(enabled, str):
        en = enabled.strip().lower() in ("1", "true", "yes", "on", "enable", "enabled")
    else:
        en = bool(enabled)
    lanes[lid]["enabled"] = en
    if weight is not None:
        try:
            lanes[lid]["weight"] = float(weight)
        except (TypeError, ValueError):
            return {"ok": False, "error": "invalid_weight"}
    cfg["lanes"] = lanes
    save_config(cfg)
    _append({"event": "set_lane", "lane": lid, "enabled": en, "weight": lanes[lid].get("weight")})
    out = {"ok": True, "lane": lid, "enabled": en, "weight": lanes[lid].get("weight")}
    if apply:
        out["apply"] = apply_posture(reason=f"set_lane:{lid}")
    return out


def connectionless(*, apply: bool = True) -> dict[str, Any]:
    return set_mode("connectionless", apply=apply)


def balance(*, apply: bool = True) -> dict[str, Any]:
    alloc = allocate_resources()
    out = {"ok": True, "balanced": True, "allocation": alloc}
    if apply:
        out["apply"] = apply_posture(reason="balance")
    return out


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = _load(DOCTRINE, {})
    cfg = load_config()
    alloc = allocate_resources()
    rep = {
        "schema": "hostess7-control-balancer/v1",
        "updated": _now(),
        "motto": doc.get("motto"),
        "mission_primary": bool(doc.get("mission_primary")),
        "internet_luxury_not_mandate": bool(doc.get("internet_luxury_not_mandate")),
        "hostess7_adjustable": bool(doc.get("hostess7_adjustable")),
        "mode": cfg.get("mode"),
        "connectionless": cfg.get("connectionless"),
        "internet_luxury": cfg.get("internet_luxury", True),
        "lanes": cfg.get("lanes"),
        "allocation": alloc,
        "sensitive_areas": alloc.get("sensitive_areas"),
        "policy_env": str(POLICY_ENV) if POLICY_ENV.is_file() else None,
        "ok": True,
    }
    if write:
        _save(PANEL, rep)
    return rep


def explain_balancer(query: str = "") -> str:
    doc = _load(DOCTRINE, {})
    panel = build_panel(write=False)
    lines = [
        str(doc.get("motto") or "Mission-primary resource balancer."),
        "Hostess 7 adjusts lanes on the fly — thermal, bandwidth, disk I/O, compute, network.",
        "Any lane can be disabled. Connectionless mode uses internals solely; internet is a luxury.",
        f"Current mode: {panel.get('mode')}. Connectionless: {panel.get('connectionless')}.",
        "Commands: control-balancer status | balance | connectionless | set-mode mission | set-lane bandwidth off",
    ]
    low = (query or "").lower()
    if "connectionless" in low or "internet" in low:
        lines.append(
            str((doc.get("connectionless") or {}).get("motto")
                or "Internals solely — no mandate for internet on mission.")
        )
    return "\n".join(lines)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("balance", "rebalance"):
        print(json.dumps(balance(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("connectionless", "offline", "internals-only"):
        print(json.dumps(connectionless(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "set-mode" and len(sys.argv) > 2:
        print(json.dumps(set_mode(sys.argv[2]), ensure_ascii=False, indent=2))
        return 0
    if cmd == "set-lane" and len(sys.argv) > 3:
        w = sys.argv[4] if len(sys.argv) > 4 else None
        print(json.dumps(set_lane(sys.argv[2], sys.argv[3], w), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("apply", "propagate"):
        print(json.dumps(apply_posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "allocate":
        print(json.dumps(allocate_resources(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("explain", "teach"):
        q = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        print(explain_balancer(q))
        return 0
    print(
        json.dumps(
            {
                "error": "usage: hostess7-control-balancer.py "
                "[panel|balance|connectionless|set-mode MODE|set-lane ID on|off [weight]|apply|allocate|explain]"
            },
            ensure_ascii=False,
        )
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())