#!/usr/bin/env pythong
"""Diagnostic mode — secure baseline only; lock systems away from fault; reorganize out."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-diagnostic-mode-doctrine.json"
PANEL_PATH = STATE / "field-diagnostic-mode-panel.json"
QUARANTINE_PATH = STATE / "field-diagnostic-quarantine.json"
LEDGER_PATH = STATE / "field-diagnostic-ledger.jsonl"
SCHEMA = "field-diagnostic-mode/v1"

SECURE_BASELINE_SCRIPTS = frozenset({
    "sovereign-clock.py",
    "g1id-baseline.py",
    "ironclad-field-sanity.py",
    "field-io-packet.py",
    "nexus-probe-guard.py",
    "field-diagnostic-mode.py",
    "connection-gatekeeper.py",
    "field-operator.py",
})

SECURE_BASELINE_SLICES = frozenset({
    "ironclad_field_sanity",
    "ironclad",
    "ironclad_immediate",
    "ironclad_reality_field",
    "logic_gate",
    "gatekeeper",
    "field_diagnostic",
})

SECURE_BASELINE_REFRESH = frozenset({
    "ironclad_field_sanity",
    "g1id_baselines",
    "field_io_packet",
    "gatekeeper",
    "logic_gate",
    "g1id",
    "diagnostic",
})


def _now() -> str:
    mod = _load_module("sovereign_clock", INSTALL / "lib" / "sovereign-clock.py")
    if mod and hasattr(mod, "utc_z"):
        return mod.utc_z("diagnostic")
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_module(name: str, path: Path) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _atomic_write(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    row.setdefault("sovereign_at", _now())
    with LEDGER_PATH.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(row, ensure_ascii=False) + "\n")


def _doctrine() -> dict[str, Any]:
    return _read_json(DOCTRINE, {})


def _panel_state() -> dict[str, Any]:
    return _read_json(PANEL_PATH, {})


def manual_override() -> bool | None:
    raw = os.environ.get("NEXUS_DIAGNOSTIC_MODE", "").strip().lower()
    if raw in ("1", "true", "yes", "on", "force"):
        return True
    if raw in ("0", "false", "no", "off"):
        return False
    return None


def detect_problems() -> dict[str, Any]:
    """Scan field panels for faults that should trigger diagnostic mode."""
    faults: list[dict[str, Any]] = []

    sanity = _read_json(STATE / "ironclad-field-sanity-panel.json", {})
    queen = sanity.get("queen") or {}
    if sanity and not sanity.get("ok", True):
        faults.append({"id": "ironclad_field_sanity", "severity": "high", "detail": sanity.get("error") or "sanity_not_ok"})
    elif int(queen.get("quarantined") or 0) > 0:
        faults.append({"id": "ironclad_field_sanity", "severity": "medium", "detail": f"quarantined={queen.get('quarantined')}"})
    elif queen.get("gate_ok") is False:
        faults.append({"id": "ironclad_field_sanity", "severity": "high", "detail": "gate_not_ok"})

    g1id = _read_json(STATE / "g1id-baseline-panel.json", {})
    if g1id and not g1id.get("required_ok", g1id.get("ok", True)):
        faults.append({"id": "g1id_baselines", "severity": "critical", "detail": "immoveable_baselines_broken"})

    io_pkt = _read_json(STATE / "field-io-packet-panel.json", {})
    if io_pkt and io_pkt.get("ok") is False:
        faults.append({"id": "field_io_packet", "severity": "critical", "detail": "truth_gate_failed"})

    fs_panel = _read_json(STATE / "field-filesystem-panel.json", {})
    if fs_panel.get("pressure_level") == "critical":
        faults.append({"id": "filesystem_critical", "severity": "high", "detail": fs_panel.get("message")})

    thermal = _read_json(STATE / "thermal-advisory.json", {})
    if str(thermal.get("level") or "").lower() in ("crit", "storm", "critical"):
        faults.append({"id": "thermal_crit", "severity": "high", "detail": thermal.get("message") or thermal.get("level")})

    brain = _read_json(STATE / "hostess7-brain-guard-panel.json", {})
    if brain.get("corruption_detected") or brain.get("hold_motion"):
        faults.append({"id": "brain_corruption", "severity": "critical", "detail": brain.get("verdict") or "brain_guard_hold"})

    compat = _read_json(STATE / "field-compatibility-layers-panel.json", {})
    if compat and compat.get("ok") is False and int(compat.get("live_layers") or 0) < 3:
        faults.append({"id": "compatibility_fault", "severity": "medium", "detail": "compatibility_stack_degraded"})
    combo_lock = _read_json(STATE / "field-combinatorics-engine-lock.json", {})
    comb_panel = _read_json(STATE / "g16-field-combinatorics-panel.json", {})
    lock_doc = comb_panel.get("combinatorics_lock") or combo_lock
    if lock_doc.get("locked"):
        grok16 = Path(os.environ.get("GROK16_ROOT", str(INSTALL.parent.parent / "Grok16")))
        combo_py = grok16 / "lib" / "field_combinatorics.py"
        try:
            if combo_py.is_file():
                spec = importlib.util.spec_from_file_location("diag_combo", combo_py)
                if spec and spec.loader:
                    cmod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(cmod)
                    if hasattr(cmod, "verify_combinatorics_lock"):
                        v = cmod.verify_combinatorics_lock(comb_panel if comb_panel else None)
                        if v.get("verified") and not v.get("ok"):
                            faults.append({
                                "id": "combinatorics_lock",
                                "severity": "critical",
                                "detail": v.get("reason") or "combinatorics_engine_or_panel_sha_mismatch",
                            })
        except Exception:
            if lock_doc.get("rebuild_required"):
                faults.append({"id": "combinatorics_lock", "severity": "high", "detail": "engine_rebuild_required"})

    bridge = _read_json(STATE / "field-plate-combinatorics-bridge.json", {})
    gate = bridge.get("gate") or {}
    if gate.get("ok") is False and gate.get("never_build_under_heat"):
        faults.append({"id": "combinatorics_gate", "severity": "medium", "detail": "thermal_entropy_gate_closed"})

    combo_threat = _read_json(STATE / "field-combinatorics-threat-panel.json", {})
    combo_runtime = combo_threat.get("runtime") or _read_json(STATE / "field-combinatorics-runtime.json", {})
    reject_stats = combo_threat.get("stats") or {}
    retaliate_level = str((combo_threat.get("last") or {}).get("retaliate_level") or combo_runtime.get("last_retaliate_level") or "")
    reject_count = int(reject_stats.get("rejections") or reject_stats.get("attempt_count") or 0)
    if bridge.get("combinatorics_rejected"):
        faults.append({
            "id": "combinatorics_reject",
            "severity": "medium",
            "detail": (bridge.get("combinatorics_reject") or {}).get("reason") or "mismatch_rejected_last_good_held",
            "reject_count": reject_count,
        })
    if retaliate_level in ("diagnostic", "host_attacks", "lethal") or combo_runtime.get("diagnostic_recommended"):
        faults.append({
            "id": "combinatorics_threat_retaliate",
            "severity": "critical" if retaliate_level == "lethal" else "high",
            "detail": retaliate_level or "diagnostic_recommended",
            "reject_count": reject_count,
        })

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    faults.sort(key=lambda f: severity_rank.get(str(f.get("severity")), 9))
    worst = faults[0]["severity"] if faults else None
    return {
        "ok": len(faults) == 0,
        "fault_count": len(faults),
        "faults": faults,
        "worst_severity": worst,
        "should_engage": len(faults) > 0,
    }


def active() -> bool:
    override = manual_override()
    if override is not None:
        return override
    panel = _panel_state()
    if panel.get("engaged"):
        return True
    if _doctrine().get("policy", {}).get("auto_engage_on_fault", True):
        return detect_problems().get("should_engage", False)
    return False


is_active = active


def script_allowed(script_name: str) -> bool:
    if not active():
        return True
    base = Path(script_name).name
    return base in SECURE_BASELINE_SCRIPTS


def slice_allowed(slice_key: str) -> bool:
    if not active():
        return True
    return slice_key in SECURE_BASELINE_SLICES or slice_key == "field_diagnostic"


def refresh_allowed(refresh_id: str) -> bool:
    if not active():
        return True
    rid = refresh_id.strip().lower().replace("-", "_")
    return rid in SECURE_BASELINE_REFRESH or any(rid.startswith(p) for p in SECURE_BASELINE_REFRESH)


def filter_field_slices(slices: dict[str, tuple[str, list[str]]]) -> dict[str, tuple[str, list[str]]]:
    if not active():
        return slices
    return {k: v for k, v in slices.items() if slice_allowed(k)}


def _parallel_slice_keys() -> list[str]:
    mod = _load_module("field_panel_parallel", INSTALL / "lib" / "field-panel-parallel.py")
    if mod and hasattr(mod, "FIELD_SLICES"):
        return list(mod.FIELD_SLICES.keys())
    return []


def reorganize_fault(faults: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Quarantine fault domains and run sanity reorganize pass."""
    faults = faults if faults is not None else (detect_problems().get("faults") or [])
    fault_ids = [str(f.get("id")) for f in faults if f.get("id")]
    locked_slices = [k for k in _parallel_slice_keys() if not slice_allowed(k)]

    reorganized: list[dict[str, Any]] = []
    sanity_out: dict[str, Any] = {}
    ic = _load_module("ironclad_field_sanity", INSTALL / "lib" / "ironclad-field-sanity.py")
    if ic and hasattr(ic, "field_sanity_operator"):
        body = {
            "layers": [
                {"id": f"fault-{fid}", "url": f"diagnostic://fault/{fid}", "depth": 0, "active": False}
                for fid in fault_ids
            ],
            "fielded": True,
            "diagnostic_reorganize": True,
        }
        try:
            sanity_out = ic.field_sanity_operator(body)
            reorganized = (sanity_out.get("queen") or {}).get("reorganized") or []
        except Exception as exc:
            sanity_out = {"ok": False, "error": str(exc)}

    quarantine = {
        "schema": "field-diagnostic-quarantine/v1",
        "updated": _now(),
        "fault_ids": fault_ids,
        "faults": faults,
        "locked_slices": locked_slices,
        "reorganized": reorganized,
        "sanity_ok": sanity_out.get("ok"),
    }
    _atomic_write(QUARANTINE_PATH, quarantine)
    _append_ledger({"event": "reorganize_fault", "fault_ids": fault_ids, "locked_count": len(locked_slices)})
    return {"ok": True, "quarantine": quarantine, "sanity": sanity_out}


def debug_self() -> dict[str, Any]:
    """Run secure baseline verification chain only — debugging self."""
    steps: list[dict[str, Any]] = []
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}

    for script, args in (
        ("g1id-baseline.py", ["verify"]),
        ("ironclad-field-sanity.py", ["json"]),
        ("field-io-packet.py", ["gate"]),
        ("nexus-probe-guard.py", ["json"]),
    ):
        path = INSTALL / "lib" / script
        if not path.is_file():
            steps.append({"script": script, "ok": False, "error": "missing"})
            continue
        try:
            proc = subprocess.run(
                [sys.executable, str(path), *args],
                capture_output=True,
                text=True,
                timeout=90,
                env=env,
            )
            out = json.loads(proc.stdout or "{}")
            steps.append({"script": script, "ok": bool(out.get("ok", proc.returncode == 0)), "summary": out})
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as exc:
            steps.append({"script": script, "ok": False, "error": str(exc)})

    prob = detect_problems()
    reorganize = reorganize_fault(prob.get("faults") or []) if prob.get("faults") else {"ok": True, "skipped": True}
    all_ok = all(s.get("ok") for s in steps) and prob.get("ok")
    return {
        "ok": all_ok,
        "action": "debug_self",
        "steps": steps,
        "problems": prob,
        "reorganize": reorganize,
        "baseline_only": True,
        "message": "Self debug pass complete — baselines verified" if all_ok else "Self debug found faults — remain in diagnostic",
    }


def engage(*, reason: str | None = None) -> dict[str, Any]:
    prob = detect_problems()
    faults = prob.get("faults") or []
    reorg = reorganize_fault(faults) if faults else {"ok": True, "skipped": True}
    doc = {
        "schema": SCHEMA,
        "updated": _now(),
        "engaged": True,
        "reason": reason or ("fault_detected" if faults else "manual"),
        "problems": prob,
        "quarantine_path": str(QUARANTINE_PATH),
        "secure_baseline_only": True,
        "locked_slice_count": len((reorg.get("quarantine") or {}).get("locked_slices") or []),
        "message": "Diagnostic mode — secure baseline only; non-baseline systems locked away from fault",
    }
    _atomic_write(PANEL_PATH, doc)
    _append_ledger({"event": "engage", "reason": doc["reason"], "fault_count": prob.get("fault_count")})
    return doc


def clear(*, force: bool = False) -> dict[str, Any]:
    if not force:
        dbg = debug_self()
        if not dbg.get("ok"):
            return {
                "ok": False,
                "error": "debug_self_failed",
                "debug_self": dbg,
                "message": "Clear diagnostic only after debug_self passes with zero faults",
            }
    doc = {
        "schema": SCHEMA,
        "updated": _now(),
        "engaged": False,
        "cleared": True,
        "message": "Diagnostic mode cleared — full field runtime restored",
    }
    _atomic_write(PANEL_PATH, doc)
    _append_ledger({"event": "clear", "force": force})
    return {"ok": True, **doc}


def status(*, write: bool = False) -> dict[str, Any]:
    prob = detect_problems()
    engaged = active()
    panel = _panel_state()
    quarantine = _read_json(QUARANTINE_PATH, {})
    doc = {
        "schema": SCHEMA,
        "updated": _now(),
        "ok": not engaged or prob.get("ok"),
        "engaged": engaged,
        "motto": (_doctrine().get("motto") or "Secure baseline only while debugging self."),
        "problems": prob,
        "secure_baseline_scripts": sorted(SECURE_BASELINE_SCRIPTS),
        "secure_baseline_slices": sorted(SECURE_BASELINE_SLICES),
        "locked_slices": quarantine.get("locked_slices") or [],
        "reorganized": quarantine.get("reorganized") or [],
        "quarantine": quarantine if quarantine else None,
        "panel": panel,
        "message": (
            "Diagnostic mode ACTIVE — only secure baseline files run; fault isolated and reorganized out"
            if engaged
            else (
                prob.get("faults") and "Problems detected — will engage diagnostic on next publish"
                or "Field runtime normal"
            )
        ),
    }
    if write:
        _atomic_write(PANEL_PATH, {**panel, **doc})
    return doc


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json", "panel"):
        return status(write=True)
    if action == "detect":
        return detect_problems()
    if action == "engage":
        return engage(reason=body.get("reason"))
    if action == "clear":
        return clear(force=bool(body.get("force")))
    if action in ("debug_self", "debug", "self"):
        return debug_self()
    if action == "reorganize":
        return reorganize_fault()
    if action == "allowed":
        return {
            "ok": True,
            "active": active(),
            "script": script_allowed(str(body.get("script") or "")),
            "slice": slice_allowed(str(body.get("slice") or "")),
            "refresh": refresh_allowed(str(body.get("refresh") or "")),
        }
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "panel"):
        print(json.dumps(status(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "detect":
        print(json.dumps(detect_problems(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "engage":
        print(json.dumps(engage(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "clear":
        force = "--force" in sys.argv
        print(json.dumps(clear(force=force), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("debug_self", "debug"):
        print(json.dumps(debug_self(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["json", "detect", "engage", "clear", "debug_self", "dispatch"]}, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())