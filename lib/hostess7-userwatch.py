#!/usr/bin/env pythong
"""Hostess 7 Userwatch — operator bond, rhythm assurance, work-zone replate hold, task queues."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENABLED = os.environ.get("NEXUS_HOSTESS7_USERWATCH", "1") == "1"

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "hostess7-userwatch-doctrine.json"
STORE = STATE / "hostess7-userwatch.json"
PANEL = STATE / "hostess7-userwatch-panel.json"
RUNTIME = STATE / "hostess7-userwatch-runtime.json"
LEDGER = STATE / "hostess7-userwatch-ledger.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _h7s_read_json(path: Path, default: Any = None) -> Any:
    fs_py = INSTALL / "lib" / "field-h7s-fs.py"
    if path.suffix.lower() == ".json" and fs_py.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_h7s_fs_io", fs_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_json"):
                    return mod.read_json(path, default=default)
        except Exception:
            pass
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return default if default is not None else {}

def _load(path: Path, default: Any = None) -> Any:
    return _h7s_read_json(path, default=default)


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _doctrine() -> dict[str, Any]:
    return _load(DOCTRINE, {"bond_tiers": {}, "assurance_weights": {}})


def _import_mod(name: str, path: Path) -> Any | None:
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _operator_default() -> dict[str, Any]:
    mod = _import_mod("operator_default", INSTALL / "lib" / "operator-default.py")
    if mod and hasattr(mod, "load_default"):
        return mod.load_default()
    return {"display_name": "operator", "github": ""}


def operator_fingerprint() -> dict[str, Any]:
    """Stable operator bond id — behavioral, not biometric fingerprint tech."""
    op = _operator_default()
    machine = os.environ.get("NEXUS_MACHINE_ID", "").strip()
    if not machine:
        try:
            node = os.uname().nodename
        except AttributeError:
            node = "host"
        machine = hashlib.sha256(node.encode()).hexdigest()[:12]
    seed = "|".join([
        str(op.get("display_name") or "operator"),
        str(op.get("github") or ""),
        machine,
        str(INSTALL.resolve()),
    ])
    bond_id = hashlib.sha256(seed.encode()).hexdigest()[:24]
    return {
        "schema": "hostess7-operator-fingerprint/v1",
        "bond_id": bond_id,
        "display_name": op.get("display_name"),
        "method": "operator_bond_hash",
        "not_biometric": True,
        "machine_hint": machine[:8],
        "statement": "We always know the user — rhythm and bond, not fingerprint SDKs.",
    }


def load_store() -> dict[str, Any]:
    doc = _load(STORE, {})
    if doc.get("bond_id"):
        return doc
    fp = operator_fingerprint()
    return {
        "schema": "hostess7-userwatch/v1",
        "bond_id": fp["bond_id"],
        "created": _now(),
        "updated": _now(),
        "samples_total": 0,
        "keyboard": {"intervals": {}, "bursts": 0, "keys": 0, "wpm_ema": 0.0},
        "mouse": {"speeds": {}, "clicks": 0, "moves": 0, "avg_interval_ms": 0.0},
        "work_zones": [],
        "queues": {"desktop": [], "programming": []},
        "assurance_history": [],
        "bond_tier": "trace",
        "assurance_rate": 0.0,
        "infinite_smart": 0.0,
    }


def save_store(doc: dict[str, Any]) -> None:
    doc["schema"] = "hostess7-userwatch/v1"
    doc["updated"] = _now()
    _save(STORE, doc)


def _bucket(value: float, edges: list[float]) -> str:
    for i, edge in enumerate(edges):
        if value < edge:
            return f"b{i}"
    return f"b{len(edges)}"


def _touch_bucket(bucket: dict[str, int], key: str) -> None:
    bucket[key] = int(bucket.get(key) or 0) + 1


def _ema(prev: float, value: float, alpha: float = 0.12) -> float:
    if prev <= 0:
        return value
    return prev * (1 - alpha) + value * alpha


def ingest_sample(
    kind: str,
    *,
    dt_ms: float | None = None,
    speed: float | None = None,
    key: str = "",
    x: float | None = None,
    y: float | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ingest mouse/keyboard rhythm sample — builds assurance without biometric storage."""
    if not ENABLED:
        return {"ok": False, "error": "disabled"}
    kind = (kind or "").strip().lower()
    doc = load_store()
    kb = doc.setdefault("keyboard", {"intervals": {}, "bursts": 0, "keys": 0, "wpm_ema": 0.0})
    ms = doc.setdefault("mouse", {"speeds": {}, "clicks": 0, "moves": 0, "avg_interval_ms": 0.0})
    buckets = (_doctrine().get("input_buckets") or {})

    if kind in ("key", "keydown", "keyup", "keyboard"):
        if dt_ms is not None and dt_ms > 0:
            bk = _bucket(float(dt_ms), list(buckets.get("keyboard_interval_ms") or [80, 160, 320]))
            _touch_bucket(kb.setdefault("intervals", {}), bk)
            if dt_ms < 180:
                kb["bursts"] = int(kb.get("bursts") or 0) + 1
            cps = min(30.0, 1000.0 / max(dt_ms, 20.0))
            kb["wpm_ema"] = round(_ema(float(kb.get("wpm_ema") or 0), cps * 12.0), 2)
        if key:
            kb["keys"] = int(kb.get("keys") or 0) + 1
    elif kind in ("mouse_move", "mousemove", "move"):
        ms["moves"] = int(ms.get("moves") or 0) + 1
        if dt_ms is not None and dt_ms > 0:
            ms["avg_interval_ms"] = round(_ema(float(ms.get("avg_interval_ms") or 0), float(dt_ms)), 2)
        if speed is not None:
            sk = _bucket(float(speed), list(buckets.get("mouse_speed_px_per_s") or [100, 400, 1200]))
            _touch_bucket(ms.setdefault("speeds", {}), sk)
    elif kind in ("click", "mouse_click", "mousedown"):
        ms["clicks"] = int(ms.get("clicks") or 0) + 1

    doc["samples_total"] = int(doc.get("samples_total") or 0) + 1
    if meta:
        doc.setdefault("last_meta", {}).update(meta)
    _recompute_assurance(doc)
    save_store(doc)
    _append_ledger({"ts": _now(), "event": "sample", "kind": kind, "assurance": doc.get("assurance_rate")})
    return {
        "ok": True,
        "kind": kind,
        "assurance_rate": doc.get("assurance_rate"),
        "bond_tier": doc.get("bond_tier"),
        "samples_total": doc.get("samples_total"),
    }


def record_work_zone(
    cwd: str,
    *,
    command: str = "",
    pid: int | None = None,
    source: str = "program",
) -> dict[str, Any]:
    """Record where the operator runs — replate hold around active cwd."""
    if not ENABLED:
        return {"ok": False, "error": "disabled"}
    cwd = str(cwd or "").strip()
    if not cwd or cwd == ".":
        cwd = os.getcwd()
    try:
        path = str(Path(cwd).resolve())
    except OSError:
        path = cwd
    doc = load_store()
    ttl = int((_doctrine().get("work_zones") or {}).get("ttl_seconds") or 900)
    now_ts = time.time()
    zones = list(doc.get("work_zones") or [])
    zones = [z for z in zones if now_ts - float(z.get("ts_epoch") or 0) < ttl]
    zones.append({
        "path": path,
        "command": (command or "")[:240],
        "pid": pid,
        "source": source,
        "ts": _now(),
        "ts_epoch": now_ts,
    })
    # dedupe by path — keep latest
    seen: dict[str, dict[str, Any]] = {}
    for z in zones:
        seen[z["path"]] = z
    doc["work_zones"] = list(seen.values())[-12:]
    _recompute_assurance(doc)
    save_store(doc)
    _append_ledger({"ts": _now(), "event": "work_zone", "path": path, "command": command[:80]})
    return {"ok": True, "path": path, "zones_active": len(doc["work_zones"])}


def _path_overlap(target: str, zone_path: str, depth: int) -> bool:
    try:
        t = Path(target).resolve()
        z = Path(zone_path).resolve()
        if t == z:
            return True
        try:
            t.relative_to(z)
            return True
        except ValueError:
            pass
        # parent overlap within depth
        t_parts = t.parts
        z_parts = z.parts
        for i in range(1, min(len(t_parts), len(z_parts)) + 1):
            if t_parts[:i] == z_parts[:i] and i >= max(1, min(len(z_parts), depth)):
                return True
    except OSError:
        if target.startswith(zone_path) or zone_path.startswith(target):
            return True
    return False


def is_replate_safe(path: str | Path | None = None) -> dict[str, Any]:
    """True when plating automation may touch path — false when operator is working there."""
    doc = load_store()
    zones = list(doc.get("work_zones") or [])
    ttl = int((_doctrine().get("work_zones") or {}).get("ttl_seconds") or 900)
    now_ts = time.time()
    active = [z for z in zones if now_ts - float(z.get("ts_epoch") or 0) < ttl]
    if not active:
        return {"ok": True, "safe": True, "reason": "no_active_work_zones", "zones": []}
    if path is None:
        hold = bool((_doctrine().get("work_zones") or {}).get("replate_hold_when_active"))
        return {
            "ok": True,
            "safe": not hold,
            "reason": "active_zones_present" if hold else "hold_disabled",
            "zones": active,
        }
    target = str(path)
    depth = int((_doctrine().get("work_zones") or {}).get("path_radius_depth") or 3)
    for z in active:
        if _path_overlap(target, str(z.get("path") or ""), depth):
            return {
                "ok": True,
                "safe": False,
                "reason": "operator_work_zone",
                "zone": z,
                "zones": active,
            }
    return {"ok": True, "safe": True, "reason": "outside_work_zones", "zones": active}


def gate_replate(replate_recommended: bool, *, target_path: str | None = None) -> dict[str, Any]:
    """Apply userwatch hold on iron-plate-organize replate recommendation."""
    safe_doc = is_replate_safe(target_path)
    if replate_recommended and not safe_doc.get("safe"):
        return {
            "replate_recommended": False,
            "replate_held": True,
            "replate_raw": True,
            "hold_reason": safe_doc.get("reason"),
            "work_zones": safe_doc.get("zones") or [],
            "statement": "Replate held — operator active in this zone.",
        }
    return {
        "replate_recommended": bool(replate_recommended),
        "replate_held": False,
        "replate_raw": bool(replate_recommended),
        "hold_reason": None,
        "work_zones": safe_doc.get("zones") or [],
    }


def _muscle_overlap() -> float:
    mod = _import_mod("h7_muscle", INSTALL / "lib" / "hostess7-muscle-memory.py")
    if not mod or not hasattr(mod, "load_store"):
        return 0.0
    try:
        store = mod.load_store()
        patterns = store.get("patterns") or {}
        if not patterns:
            return 0.0
        strengths = [float(p.get("strength") or 0) for p in patterns.values()]
        habits = sum(1 for p in patterns.values() if str(p.get("tier") or "") in ("habit", "reflex"))
        avg = sum(strengths) / max(len(strengths), 1)
        return min(1.0, avg * 0.7 + min(habits, 12) / 12.0 * 0.3)
    except Exception:
        return 0.0


def _keyboard_rhythm_score(kb: dict[str, Any]) -> float:
    intervals = kb.get("intervals") or {}
    total = sum(int(v) for v in intervals.values()) or 1
    keys = int(kb.get("keys") or 0)
    bursts = int(kb.get("bursts") or 0)
    diversity = len(intervals) / 6.0
    burst_ratio = min(1.0, bursts / max(keys, 1))
    volume = min(1.0, math.log1p(keys) / math.log1p(400))
    return min(1.0, diversity * 0.35 + burst_ratio * 0.25 + volume * 0.4)


def _mouse_rhythm_score(ms: dict[str, Any]) -> float:
    speeds = ms.get("speeds") or {}
    moves = int(ms.get("moves") or 0)
    clicks = int(ms.get("clicks") or 0)
    diversity = len(speeds) / 5.0
    volume = min(1.0, math.log1p(moves + clicks) / math.log1p(300))
    return min(1.0, diversity * 0.45 + volume * 0.55)


def _work_zone_score(zones: list[dict[str, Any]]) -> float:
    if not zones:
        return 0.0
    ttl = int((_doctrine().get("work_zones") or {}).get("ttl_seconds") or 900)
    now_ts = time.time()
    active = [z for z in zones if now_ts - float(z.get("ts_epoch") or 0) < ttl]
    return min(1.0, len(active) / 4.0)


def _bond_tier_for(assurance: float, samples: int) -> str:
    tiers = _doctrine().get("bond_tiers") or {}
    order = ("fused", "bonded", "habit", "forming", "trace")
    for tid in order:
        spec = tiers.get(tid) or {}
        if assurance >= float(spec.get("min_assurance") or 0) and samples >= int(spec.get("min_samples") or 0):
            return tid
    return "trace"


def _infinite_smart_score(samples: int, assurance: float) -> float:
    cfg = _doctrine().get("infinite_smart") or {}
    base = float(cfg.get("sample_growth_log_base") or 1.08)
    cap = float(cfg.get("cap") or 0.999)
    growth = 1.0 - math.exp(-math.log(base) * math.log1p(samples) / 12.0)
    return round(min(cap, assurance * 0.55 + growth * 0.45), 4)


def _recompute_assurance(doc: dict[str, Any]) -> None:
    weights = (_doctrine().get("assurance_weights") or {})
    kb_s = _keyboard_rhythm_score(doc.get("keyboard") or {})
    ms_s = _mouse_rhythm_score(doc.get("mouse") or {})
    wz_s = _work_zone_score(doc.get("work_zones") or [])
    mm_s = _muscle_overlap()
    rate = (
        kb_s * float(weights.get("keyboard_rhythm") or 0.34)
        + ms_s * float(weights.get("mouse_rhythm") or 0.28)
        + wz_s * float(weights.get("work_zone_stability") or 0.22)
        + mm_s * float(weights.get("muscle_memory_overlap") or 0.16)
    )
    samples = int(doc.get("samples_total") or 0)
    # volume gate — need honest samples before high assurance
    volume_gate = min(1.0, math.log1p(samples) / math.log1p(600))
    rate = round(min(0.999, rate * (0.35 + 0.65 * volume_gate)), 4)
    doc["assurance_rate"] = rate
    doc["bond_tier"] = _bond_tier_for(rate, samples)
    doc["infinite_smart"] = _infinite_smart_score(samples, rate)
    hist = list(doc.get("assurance_history") or [])
    hist.append({"ts": _now(), "rate": rate, "tier": doc["bond_tier"]})
    doc["assurance_history"] = hist[-64:]


def enqueue_task(
    queue: str,
    task: dict[str, Any],
    *,
    priority: int | None = None,
) -> dict[str, Any]:
    """Desktop or programming task queue — Hostess runs when bond sufficient."""
    if not ENABLED:
        return {"ok": False, "error": "disabled"}
    queue = (queue or "programming").strip().lower()
    if queue not in ("desktop", "programming"):
        return {"ok": False, "error": "invalid_queue"}
    cfg = (_doctrine().get("task_queues") or {}).get(queue) or {}
    max_pending = int(cfg.get("max_pending") or 32)
    doc = load_store()
    q = doc.setdefault("queues", {}).setdefault(queue, [])
    tier = str(doc.get("bond_tier") or "trace")
    min_bond = str(cfg.get("auto_run_min_bond") or "habit")
    tier_rank = {"trace": 0, "forming": 1, "habit": 2, "bonded": 3, "fused": 4}
    auto_ok = tier_rank.get(tier, 0) >= tier_rank.get(min_bond, 2)
    row = {
        "id": hashlib.sha256(f"{_now()}:{json.dumps(task, sort_keys=True)}".encode()).hexdigest()[:16],
        "task": task,
        "priority": priority if priority is not None else int(task.get("priority") or 5),
        "enqueued": _now(),
        "auto_eligible": auto_ok,
        "bond_tier_at_enqueue": tier,
        "status": "pending",
    }
    q.append(row)
    q.sort(key=lambda r: int(r.get("priority") or 5))
    doc["queues"][queue] = q[-max_pending:]
    save_store(doc)
    return {"ok": True, "queue": queue, "task": row, "pending": len(doc["queues"][queue])}


def list_queue(queue: str = "programming") -> list[dict[str, Any]]:
    doc = load_store()
    return list((doc.get("queues") or {}).get(queue) or [])


def review_plating_apex() -> dict[str, Any]:
    """Review plating automation apex — far more plate data since meld orchestrator."""
    orch = _load(STATE / "field-plate-meld-orchestrator-panel.json", {})
    organize = _load(STATE / "iron-plate-organize-panel.json", {})
    meld = _load(STATE / "field-plate-meld.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge-panel.json", {})
    connectivity = orch.get("connectivity") or {}
    bottom = orch.get("bottom_cpu") or {}
    improvements = orch.get("improvements") or []

    plates_in_meld = int(meld.get("plate_count") or len(meld.get("snapshots") or {}))
    gen = int(meld.get("generation") or 0)
    replate_raw = bool(organize.get("replate_recommended"))
    replate_gate = gate_replate(replate_raw)
    high_imp = sum(1 for i in improvements if i.get("severity") == "high")

    automation_steps = (orch.get("pipeline") or {}).get("steps") or []
    steps_ok = sum(1 for s in automation_steps if s.get("ok"))
    automation_cov = steps_ok / max(len(automation_steps), 1) if automation_steps else 0.5

    at_bottom = bool(bottom.get("at_bottom"))
    bridge_ok = bool(organize.get("combinatorics_bridge_ok") or bridge.get("ok"))
    replate_discipline = 1.0 if (not replate_raw or replate_gate.get("replate_held")) else 0.6
    if replate_raw and replate_gate.get("replate_held"):
        replate_discipline = 1.0

    dims = {
        "automation_coverage": round(automation_cov, 4),
        "bottom_cpu": 1.0 if at_bottom else 0.45,
        "replate_discipline": replate_discipline,
        "meld_generation": min(1.0, gen / 50.0) if gen else 0.3,
        "connectivity": min(1.0, int(connectivity.get("wired_count") or 0) / 40.0),
    }
    apex = round(sum(dims.values()) / max(len(dims), 1), 4)
    threshold = float((_doctrine().get("plating_apex") or {}).get("apex_threshold") or 0.92)
    at_apex = apex >= threshold and high_imp == 0 and bridge_ok

    gaps: list[str] = []
    if not at_bottom:
        gaps.append("bottom_cpu:not_native_bsp")
    if high_imp:
        gaps.append(f"orchestrator:{high_imp}_high_improvements")
    if not bridge_ok:
        gaps.append("combinatorics_bridge:incomplete")
    if replate_raw and not replate_gate.get("replate_held"):
        gaps.append("replate:ungated_active_zone")
    if plates_in_meld < 30:
        gaps.append(f"meld:plate_count_{plates_in_meld}")

    methods_review = {
        "orchestrator_modes": ["audit", "fast", "cycle", "full"],
        "surface_refresh": 12,
        "meld_fuse": bool(meld.get("schema")),
        "organize_gain": organize.get("organize_gain"),
        "replate_raw": replate_raw,
        "replate_effective": replate_gate.get("replate_recommended"),
        "userwatch_hold": replate_gate.get("replate_held"),
        "ac_modules": (_doctrine().get("plating_apex") or {}).get("review_modules") or [],
    }

    return {
        "schema": "hostess7-plating-apex-review/v1",
        "ts": _now(),
        "apex_score": apex,
        "at_apex": at_apex,
        "apex_threshold": threshold,
        "dimensions": dims,
        "gaps": gaps,
        "plate_data": {
            "meld_plates": plates_in_meld,
            "meld_generation": gen,
            "orchestrator_ok": orch.get("ok"),
            "organize_ok": organize.get("ok"),
            "improvements_total": len(improvements),
            "improvements_high": high_imp,
        },
        "methods_review": methods_review,
        "posture": (
            f"Plating apex {apex:.2f} — {'APEX' if at_apex else 'climbing'} · "
            f"{plates_in_meld} meld plates · replate "
            f"{'held' if replate_gate.get('replate_held') else ('go' if replate_gate.get('replate_recommended') else 'hold')}"
        ),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    doc = load_store()
    _recompute_assurance(doc)
    if write:
        save_store(doc)
    fp = operator_fingerprint()
    apex = review_plating_apex()
    safe_global = is_replate_safe()
    panel = {
        "schema": "hostess7-userwatch-panel/v1",
        "updated": _now(),
        "ok": ENABLED,
        "enabled": ENABLED,
        "fingerprint": fp,
        "bond_id": doc.get("bond_id"),
        "bond_tier": doc.get("bond_tier"),
        "assurance_rate": doc.get("assurance_rate"),
        "infinite_smart": doc.get("infinite_smart"),
        "samples_total": doc.get("samples_total"),
        "keyboard": doc.get("keyboard"),
        "mouse": doc.get("mouse"),
        "work_zones": doc.get("work_zones"),
        "work_zones_active": len(safe_global.get("zones") or []),
        "replate_safe_global": safe_global.get("safe"),
        "queues": {
            "desktop": list_queue("desktop"),
            "programming": list_queue("programming"),
        },
        "plating_apex": apex,
        "motto": (_doctrine().get("motto") or ""),
        "posture": (
            f"Userwatch · {fp.get('display_name')} · bond {doc.get('bond_tier')} "
            f"· assurance {float(doc.get('assurance_rate') or 0):.2f} · "
            f"smart {float(doc.get('infinite_smart') or 0):.2f}"
        ),
    }
    if write:
        _save(PANEL, panel)
        _save(RUNTIME, {
            "schema": "hostess7-userwatch-runtime/v1",
            "updated": panel["updated"],
            "bond_tier": panel["bond_tier"],
            "assurance_rate": panel["assurance_rate"],
            "replate_safe_global": panel["replate_safe_global"],
            "at_apex": apex.get("at_apex"),
        })
    return panel


def dispatch(body: dict[str, Any] | None = None) -> dict[str, Any]:
    body = body or {}
    action = str(body.get("action") or "panel").strip().lower()
    if action in ("panel", "status", "json"):
        return build_panel(write=True)
    if action == "ingest":
        return ingest_sample(
            str(body.get("kind") or ""),
            dt_ms=body.get("dt_ms"),
            speed=body.get("speed"),
            key=str(body.get("key") or ""),
            meta=body.get("meta"),
        )
    if action == "work_zone":
        return record_work_zone(
            str(body.get("cwd") or body.get("path") or ""),
            command=str(body.get("command") or ""),
            pid=body.get("pid"),
            source=str(body.get("source") or "program"),
        )
    if action == "replate_safe":
        return is_replate_safe(body.get("path"))
    if action == "enqueue":
        return enqueue_task(
            str(body.get("queue") or "programming"),
            body.get("task") or body,
            priority=body.get("priority"),
        )
    if action == "apex":
        return review_plating_apex()
    if action == "fingerprint":
        return operator_fingerprint()
    return {"ok": False, "error": "unknown_action", "actions": [
        "panel", "ingest", "work_zone", "replate_safe", "enqueue", "apex", "fingerprint",
    ]}


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps(build_panel(write=True), ensure_ascii=False, indent=2))
        return 0
    cmd = sys.argv[1].strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "apex":
        print(json.dumps(review_plating_apex(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "fingerprint":
        print(json.dumps(operator_fingerprint(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "ingest" and len(sys.argv) >= 3:
        kind = sys.argv[2]
        body: dict[str, Any] = {"kind": kind}
        if len(sys.argv) > 3:
            try:
                body.update(json.loads(sys.argv[3]))
            except json.JSONDecodeError:
                body["key"] = sys.argv[3]
        print(json.dumps(ingest_sample(**{k: body[k] for k in body if k != "kind"} | {"kind": kind}), ensure_ascii=False))
        return 0
    if cmd == "work_zone" and len(sys.argv) >= 3:
        print(json.dumps(record_work_zone(sys.argv[2], command=sys.argv[3] if len(sys.argv) > 3 else ""), ensure_ascii=False))
        return 0
    if cmd == "dispatch" and len(sys.argv) >= 3:
        try:
            body = json.loads(sys.argv[2])
        except json.JSONDecodeError:
            body = {"action": sys.argv[2]}
        print(json.dumps(dispatch(body), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "usage": "hostess7-userwatch.py [json|apex|fingerprint|ingest KIND [JSON]|work_zone PATH|dispatch JSON]",
    }, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())