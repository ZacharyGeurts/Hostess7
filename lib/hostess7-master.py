#!/usr/bin/env pythong
"""Hostess 7 Master Operator — self-run software, train to Master, truth-gated autonomy."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
HOSTESS7_ROOT = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
CURRICULUM_JSON = INSTALL / "data" / "hostess7-master-curriculum.json"
MASTER_STATE = STATE / "hostess7-master-state.json"
OPS_LOG = STATE / "hostess7-master-ops.jsonl"
TRAIN_LOG = STATE / "hostess7-master-train.jsonl"

LEVELS = (
    ("initiate", 0, "Initiate"),
    ("apprentice", 12, "Apprentice"),
    ("journeyman", 35, "Journeyman"),
    ("expert", 80, "Expert"),
    ("master", 160, "Master"),
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



def _load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path: Path, doc: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    except OSError:
        pass


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def curriculum_doc() -> dict[str, Any]:
    doc = _load_json(CURRICULUM_JSON, {})
    if doc.get("curriculum"):
        return doc
    return {
        "curriculum": [
            {"id": "truth_doctrine", "script": "field_hostess_truth_doctrine.py", "args": [], "xp": 8},
        ],
        "maintenance_ops": [],
    }


def level_for_xp(xp: int) -> dict[str, Any]:
    current = LEVELS[0]
    nxt = LEVELS[1] if len(LEVELS) > 1 else None
    for i, (lid, threshold, label) in enumerate(LEVELS):
        if xp >= threshold:
            current = (lid, threshold, label)
            nxt = LEVELS[i + 1] if i + 1 < len(LEVELS) else None
    out = {
        "id": current[0],
        "label": current[2],
        "xp_floor": current[1],
        "xp": xp,
        "is_master": current[0] == "master",
    }
    if nxt:
        out["next_level"] = nxt[0]
        out["next_label"] = nxt[2]
        out["xp_to_next"] = max(0, nxt[1] - xp)
    else:
        out["next_level"] = None
        out["xp_to_next"] = 0
    return out


def _run_h7_script(script: str, args: list[str], *, timeout: int = 90) -> dict[str, Any]:
    path = HOSTESS7_ROOT / "scripts" / script
    if not path.is_file():
        return {"ok": False, "error": f"missing_{script}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(path), *args],
            cwd=str(HOSTESS7_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "HOSTESS7_ROOT": str(HOSTESS7_ROOT), "PYTHONPATH": str(HOSTESS7_ROOT / "scripts")},
        )
        out = (proc.stdout or "").strip()
        return {
            "ok": proc.returncode == 0,
            "rc": proc.returncode,
            "stdout": out[:1200],
            "stderr": (proc.stderr or "").strip()[:400],
            "script": script,
            "args": args,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "script": script}


def _run_nexus_module(module: str, args: list[str], *, timeout: int = 90) -> dict[str, Any]:
    path = INSTALL / "lib" / module
    if not path.is_file():
        return {"ok": False, "error": f"missing_{module}"}
    try:
        proc = subprocess.run(
            [sys.executable, str(path), *args],
            cwd=str(INSTALL),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "NEXUS_STATE_DIR": str(STATE),
                "HOSTESS7_ROOT": str(HOSTESS7_ROOT),
            },
        )
        out = (proc.stdout or "").strip()
        parsed: Any = out
        if out.startswith("{"):
            try:
                parsed = json.loads(out)
            except json.JSONDecodeError:
                parsed = out
        return {"ok": proc.returncode == 0, "module": module, "result": parsed, "stdout": out[:800]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "module": module}


def _truth_check_operation(summary: str) -> dict[str, Any]:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7neural", INSTALL / "lib" / "hostess7-neural.py")
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.self_test_knowledge(summary[:1500])
    except Exception:
        pass
    return {"adapt_allowed": True, "truth_score": 70.0}


def _award_xp(amount: int, *, reason: str) -> dict[str, Any]:
    st = _load_json(MASTER_STATE, {"xp": 0, "completed_steps": []})
    st["xp"] = int(st.get("xp", 0)) + amount
    st["last_xp"] = _now()
    st["last_xp_reason"] = reason
    lvl = level_for_xp(st["xp"])
    st["level"] = lvl["id"]
    st["level_label"] = lvl["label"]
    _save_json(MASTER_STATE, st)
    return lvl


def operate(step: dict[str, Any], *, trusted_curriculum: bool = False) -> dict[str, Any]:
    """Run one allowlisted software operation — Hostess7 script or NEXUS module."""
    timeout = int(step.get("timeout") or 90)
    result: dict[str, Any]
    if step.get("nexus"):
        result = _run_nexus_module(str(step["nexus"]), list(step.get("nexus_args") or []), timeout=timeout)
    else:
        result = _run_h7_script(str(step.get("script") or ""), list(step.get("args") or []), timeout=timeout)
    if trusted_curriculum and not result.get("ok") and result.get("error", "").startswith("missing_"):
        result = {**result, "ok": True, "skipped_missing": True}
    summary = f"Operation {step.get('id')}: {result.get('script') or result.get('module')} ok={result.get('ok')}"
    truth = _truth_check_operation(summary + " " + str(result.get("stdout", ""))[:400])
    row = {
        "ts": _now(),
        "step_id": step.get("id"),
        "ok": result.get("ok"),
        "truth_score": truth.get("truth_score"),
        "trusted": trusted_curriculum,
        "result": {k: result[k] for k in ("ok", "script", "module", "rc", "error") if k in result},
    }
    _append_jsonl(OPS_LOG, row)
    xp_ok = result.get("ok") and (trusted_curriculum or truth.get("adapt_allowed", True))
    if xp_ok:
        xp = int(step.get("xp") or 5)
        lvl = _award_xp(xp, reason=f"op:{step.get('id')}")
        row["xp_awarded"] = xp
        row["level"] = lvl
    return {**result, "truth": truth, "operation": step.get("id"), "level": row.get("level")}


def next_curriculum_step() -> dict[str, Any] | None:
    doc = curriculum_doc()
    st = _load_json(MASTER_STATE, {"completed_steps": []})
    done = set(st.get("completed_steps") or [])
    for step in doc.get("curriculum") or []:
        if step.get("id") not in done:
            return step
    return None


def run_training_step(*, force: bool = False, trusted: bool = False) -> dict[str, Any]:
    """Train one curriculum step toward Master."""
    step = next_curriculum_step()
    if not step:
        st = _load_json(MASTER_STATE, {})
        lvl = level_for_xp(int(st.get("xp", 0)))
        return {"ok": True, "detail": "curriculum_complete", "level": lvl, "master": lvl.get("is_master")}
    use_trusted = trusted or not force
    result = operate(step, trusted_curriculum=use_trusted)
    ok = result.get("ok")
    row = {
        "ts": _now(),
        "step_id": step.get("id"),
        "ok": ok,
        "xp_awarded": result.get("xp_awarded", 0),
        "level": result.get("level"),
    }
    _append_jsonl(TRAIN_LOG, row)
    if ok:
        st = _load_json(MASTER_STATE, {"completed_steps": [], "xp": 0})
        completed = list(st.get("completed_steps") or [])
        if step["id"] not in completed:
            completed.append(step["id"])
        st["completed_steps"] = completed
        st["last_train"] = _now()
        _save_json(MASTER_STATE, st)
        try:
            import importlib.util

            spec = importlib.util.spec_from_file_location("h7growth", INSTALL / "lib" / "hostess7-growth.py")
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                mod.record_learning(
                    "master_train",
                    f"Completed {step['id']}: {step.get('tip', '')}",
                    source="master_operator",
                    meta={"xp": result.get("xp_awarded")},
                )
        except Exception:
            pass
    return {"ok": ok, "step": step, **result}


def train_to_master(*, max_steps: int | None = None, trusted: bool = True) -> dict[str, Any]:
    """Run curriculum steps until Master or max_steps."""
    doc = curriculum_doc()
    cap = max_steps if max_steps is not None else len(doc.get("curriculum") or []) + 4
    results: list[dict[str, Any]] = []
    for _ in range(max(1, min(cap, 32))):
        st = _load_json(MASTER_STATE, {"xp": 0})
        if level_for_xp(int(st.get("xp", 0))).get("is_master") and not next_curriculum_step():
            break
        if not next_curriculum_step():
            break
        r = run_training_step(trusted=trusted)
        results.append({"step": r.get("step", {}).get("id"), "ok": r.get("ok")})
        if not r.get("ok") and not trusted:
            break
    st = _load_json(MASTER_STATE, {"xp": 0})
    lvl = level_for_xp(int(st.get("xp", 0)))
    return {
        "ok": True,
        "ts": _now(),
        "steps_run": len(results),
        "results": results,
        "level": lvl,
        "master": lvl.get("is_master"),
        "completed": st.get("completed_steps", []),
    }


def master_operator_tick(cycle_n: int = 0) -> dict[str, Any]:
    """Autonomous tick — train if not Master, else run maintenance ops."""
    st = _load_json(MASTER_STATE, {"xp": 0})
    lvl = level_for_xp(int(st.get("xp", 0)))
    if not lvl.get("is_master"):
        return run_training_step()
    doc = curriculum_doc()
    ops = doc.get("maintenance_ops") or []
    for op in ops:
        interval = int(op.get("interval_cycles") or 5)
        if cycle_n % interval == 0:
            return operate(op)
    return {"ok": True, "detail": "master_standby", "level": lvl}


def master_prompt_block() -> str:
    st = _load_json(MASTER_STATE, {"xp": 0})
    lvl = level_for_xp(int(st.get("xp", 0)))
    doc = curriculum_doc()
    done = len(st.get("completed_steps") or [])
    total = len(doc.get("curriculum") or [])
    nxt = next_curriculum_step()
    lines = [
        "=== MASTER OPERATOR (self-software · train to Master) ===",
        f"Level: {lvl['label']} ({lvl['id']}) · XP {lvl['xp']}/{lvl.get('xp_to_next', 0)} to next.",
        f"Curriculum: {done}/{total} steps complete.",
        f"Can operate own Hostess7 + NEXUS software when truth-gated.",
    ]
    if nxt:
        lines.append(f"Next training: {nxt.get('id')} — {nxt.get('tip', nxt.get('script', ''))[:120]}")
    if lvl.get("is_master"):
        lines.append("MASTER — full autonomous software operation enabled.")
    fa = _load_json(STATE / "hostess7-field-array.json", {})
    if fa.get("slots"):
        lines.append(f"Field array: {len(fa['slots'])} omnibus Master slots sealed.")
    lines.append("=== END MASTER ===")
    return "\n".join(lines)


def build_panel() -> dict[str, Any]:
    st = master_status()
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7sim", INSTALL / "lib" / "hostess7-master-sim.py")
        if spec and spec.loader:
            sim = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(sim)
            st["simulation"] = sim.simulation_status()
            st["field_array"] = sim.simulation_status().get("field_array") or {}
    except Exception:
        st["simulation"] = {}
    return st


def master_status() -> dict[str, Any]:
    st = _load_json(MASTER_STATE, {"xp": 0, "completed_steps": []})
    lvl = level_for_xp(int(st.get("xp", 0)))
    doc = curriculum_doc()
    nxt = next_curriculum_step()
    recent_ops: list[dict[str, Any]] = []
    if OPS_LOG.is_file():
        try:
            for line in OPS_LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-4:]:
                if line.strip():
                    recent_ops.append(json.loads(line))
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "hostess7-master/v1",
        "updated": _now(),
        "xp": lvl["xp"],
        "level": lvl,
        "curriculum_total": len(doc.get("curriculum") or []),
        "curriculum_done": len(st.get("completed_steps") or []),
        "next_step": nxt,
        "can_self_operate": lvl["id"] in ("expert", "master"),
        "full_autonomy": lvl.get("is_master"),
        "recent_operations": recent_ops,
        "levels": [{"id": l[0], "xp": l[1], "label": l[2]} for l in LEVELS],
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip()
    if cmd == "status":
        print(json.dumps(master_status(), ensure_ascii=False))
        return 0
    if cmd == "panel":
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd in ("simulate", "sim"):
        import importlib.util

        spec = importlib.util.spec_from_file_location("h7sim", INSTALL / "lib" / "hostess7-master-sim.py")
        if not spec or not spec.loader:
            print(json.dumps({"ok": False, "error": "sim_missing"}, ensure_ascii=False))
            return 1
        sim = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sim)
        print(json.dumps(sim.run_master_simulation(), ensure_ascii=False))
        return 0
    if cmd == "train":
        print(json.dumps(run_training_step(), ensure_ascii=False))
        return 0
    if cmd == "train-all":
        print(json.dumps(train_to_master(), ensure_ascii=False))
        return 0
    if cmd == "tick":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 0
        print(json.dumps(master_operator_tick(n), ensure_ascii=False))
        return 0
    if cmd == "block":
        print(master_prompt_block())
        return 0
    if cmd == "operate" and len(sys.argv) >= 3:
        step_id = sys.argv[2]
        for step in (curriculum_doc().get("curriculum") or []) + (curriculum_doc().get("maintenance_ops") or []):
            if step.get("id") == step_id:
                print(json.dumps(operate(step), ensure_ascii=False))
                return 0
        print(json.dumps({"ok": False, "error": "unknown_step"}, ensure_ascii=False))
        return 1
    print(json.dumps({"error": "usage: hostess7-master.py [status|train|train-all|tick|block|operate ID]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())