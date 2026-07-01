#!/usr/bin/env pythong
"""Combinatorics Studio — operator-driven plate tree, condense, and recombinatorics UI backend."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent if INSTALL.name == "nexus-shield" else INSTALL.parent)))
from sg_paths import grok16_root

GROK16 = grok16_root()


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = Path(__file__).resolve().parent / "sovereign-clock.py"
        _s = importlib.util.spec_from_file_location("sovereign_clock", _p)
        if not _s or not _s.loader:
            raise ImportError("sovereign-clock.py missing")
        _SOVEREIGN_CLOCK_MOD = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_SOVEREIGN_CLOCK_MOD)
    return _SOVEREIGN_CLOCK_MOD.utc_z()


_SOVEREIGN_CLOCK_MOD = None


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


def _import_combinatorics() -> Any | None:
    for path in (GROK16 / "lib" / "field_combinatorics.py"):
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("field_combinatorics", path)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _import_comb() -> Any | None:
    for path in (
        INSTALL / "lib" / "field-combinatorics-comb.py",
        Path(__file__).resolve().parent / "field-combinatorics-comb.py",
    ):
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("field_combinatorics_comb", path)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _import_orch() -> Any | None:
    path = INSTALL / "lib" / "field-plate-meld-orchestrator.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_plate_meld_orchestrator_studio", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _import_bridge() -> Any | None:
    path = INSTALL / "lib" / "field-plate-combinatorics-bridge.py"
    if not path.is_file():
        path = Path(__file__).resolve().parent / "field-plate-combinatorics-bridge.py"
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("field_plate_combinatorics_bridge", path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_truth_publish() -> dict[str, Any]:
    truth_py = GROK16 / "lib" / "field_truth_blocks.py"
    if not truth_py.is_file():
        return {"ok": False, "error": "truth_blocks_missing"}
    env = {**os.environ, "NEXUS_STATE_DIR": str(STATE), "GROK16_ROOT": str(GROK16), "SG_ROOT": str(SG)}
    proc = subprocess.run(
        [sys.executable, str(truth_py), "publish"],
        capture_output=True,
        text=True,
        timeout=90,
        env=env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": proc.returncode == 0, "stdout": (proc.stdout or "")[:400], "stderr": (proc.stderr or "")[:400]}


def _gather_metrics() -> dict[str, Any]:
    """All live plates the operator cares about — thermals, sense, bench, meld."""
    thermal = _load(STATE / "field-thermal-guard.json", {})
    advisory = _load(STATE / "thermal-advisory.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    gate = bridge.get("gate") or {}
    sense = _load(STATE / "g16-compiler-sense-plate.json", {})
    stack = _load(STATE / "nexus-g16-stack-panel.json", {})
    meld = _load(STATE / "field-plate-meld.json", {})
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    bench_ref = comb.get("bench_ref") or {}
    bus = _load(STATE / "field-unified-bus-runtime.json", {})
    bus_thermal = (bus.get("thermal") or {}) if isinstance(bus.get("thermal"), dict) else {}
    tests = _load(STATE / "field-plate-test-runner.json", {})
    headroom = float(gate.get("thermal_headroom_pct") or thermal.get("headroom_pct") or 100)
    level = str(gate.get("thermal_level") or advisory.get("level") or thermal.get("level") or "ok").lower()
    cap = comb.get("speed_cap") or {}
    native = cap.get("native_ceiling_ops_per_sec") or (cap.get("belt_2_0") or {}).get("estimated_cap_ops_per_sec")
    physics = _load(STATE / "field-physics-witness.json", {})
    if not physics.get("thermal"):
        pw_py = INSTALL / "lib" / "field-physics-witness.py"
        if pw_py.is_file():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("studio_physics", pw_py)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "witness"):
                        physics = mod.witness(sections=True)
            except Exception:
                pass
    sitrep = _load(STATE / "field-locational-sitrep-plate.json", {})
    if not sitrep.get("summary"):
        ls_py = INSTALL / "lib" / "field-locational-sitrep-plate.py"
        if ls_py.is_file():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("studio_sitrep", ls_py)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    if hasattr(mod, "build_plate"):
                        sitrep = mod.build_plate(write=False, refresh_spatial=False)
            except Exception:
                pass
    return {
        "physics_witness": physics,
        "we_all_know": physics.get("we_all_know") or {"thermals": True, "entropy": True, "isotope": True},
        "locational_sitrep": {
            "summary": sitrep.get("summary"),
            "verdict": sitrep.get("verdict"),
            "this_one": sitrep.get("this_one"),
            "movement": sitrep.get("movement"),
            "gps_ready": sitrep.get("gps_ready"),
            "spatial_pass_ok": sitrep.get("spatial_pass_ok"),
        },
        "thermal": {
            "headroom_pct": round(headroom, 1),
            "level": level,
            "advisory": advisory.get("message") or advisory.get("summary"),
            "temp_c": thermal.get("temp_c") or thermal.get("package_c"),
            "governor": thermal.get("governor") or advisory.get("governor"),
            "gate_ok": gate.get("ok"),
            "never_build_under_heat": gate.get("never_build_under_heat"),
            "entropy_ok": gate.get("entropy_ok"),
            "bus_entropy": bus_thermal.get("entropy"),
            "cool_ok": (physics.get("thermal") or {}).get("cool_ok"),
            "peak_c": (physics.get("thermal") or {}).get("peak_c"),
        },
        "entropy": physics.get("entropy") or {
            "entropy_ok": gate.get("entropy_ok"),
            "bus_entropy": bus_thermal.get("entropy"),
        },
        "isotope": physics.get("isotope") or {},
        "sense": {
            "profile": sense.get("effective_profile") or sense.get("profile"),
            "reason": sense.get("reason"),
            "score": sense.get("sense_score"),
            "eye_ok": sense.get("eye_ok"),
            "ear_ok": sense.get("ear_ok"),
            "mouth_ok": sense.get("mouth_ok"),
            "g16_ready": sense.get("g16_ready"),
            "meld_generation": sense.get("meld_generation"),
        },
        "stack": {
            "ok": stack.get("ok"),
            "ironclad_ok": (stack.get("ironclad_sanity") or {}).get("ok"),
            "rtx_satisfied": (stack.get("rtx_gate") or {}).get("satisfied"),
            "g16_ready": (stack.get("compile") or {}).get("probe", {}).get("g16_ready"),
            "optimized": stack.get("optimized"),
        },
        "meld": {
            "generation": meld.get("generation"),
            "plates_fused": meld.get("plates_fused") or meld.get("plate_count"),
            "chain_hash": (meld.get("chain_hash") or "")[:16],
        },
        "bench": {
            "host": bench_ref.get("host"),
            "bench_at": bench_ref.get("bench_at"),
            "native_ceiling_ops_per_sec": native,
            "belt_1_cap": (cap.get("belt_1_0") or {}).get("estimated_cap_ops_per_sec"),
            "belt_2_cap": (cap.get("belt_2_0") or {}).get("estimated_cap_ops_per_sec"),
        },
        "plate_tests": {
            "ok": tests.get("ok"),
            "battery": tests.get("battery") or tests.get("last_battery"),
            "passed": tests.get("passed"),
            "failed": tests.get("failed"),
        },
    }


def _fmt_ops(ops: float | int | None) -> str:
    v = float(ops or 0)
    if v <= 0:
        return "not measured yet"
    if v >= 1_000_000:
        return f"{v / 1_000_000:.1f} million ops per second"
    if v >= 1_000:
        return f"{v / 1_000:.0f} thousand ops per second"
    return f"{v:.0f} ops per second"


def _thermal_plain(m: dict[str, Any]) -> str:
    th = m.get("thermal") or {}
    hr = float(th.get("headroom_pct") or 0)
    level = str(th.get("level") or "ok")
    if not th.get("gate_ok"):
        return (
            f"Thermals are blocking heavy plate work right now — headroom is {hr:.0f}% "
            f"and the advisory level is {level}. Wait for the machine to cool, or run a lighter cycle."
        )
    if hr >= 60:
        return f"Thermals look comfortable — {hr:.0f}% headroom, level {level}. Safe to run a full combinatorics cycle."
    if hr >= 25:
        return f"Thermals are acceptable — {hr:.0f}% headroom, level {level}. Walk and condense are fine; full meld is OK with care."
    return f"Thermals are tight — only {hr:.0f}% headroom at level {level}. Prefer Walk or Recombine over Full cycle until headroom rises."


def evaluate(doc: dict[str, Any] | None = None) -> dict[str, Any]:
    """Plain-English readout + best compile verdict with reasons."""
    doc = doc or status()
    metrics = _gather_metrics()
    truth = doc.get("truth_blocks") or {}
    tree = doc.get("tree") or {}
    terminal = tree.get("terminal") or {}
    recomb = doc.get("recombinatorics") or {}
    posture = doc.get("exec_posture") or {}
    ideal = str(doc.get("ideal_profile") or recomb.get("ideal_profile") or "belt_2_0")
    sense_prof = (metrics.get("sense") or {}).get("profile") or "field_opt"
    candidates = recomb.get("candidates") or []
    ideal_row = next((c for c in candidates if c.get("profile") == ideal), candidates[0] if candidates else {})
    belt = str(terminal.get("belt_profile") or recomb.get("ideal_belt") or "belt_2_0")
    pattern = str(terminal.get("pattern_id") or posture.get("pattern_id") or "—")
    runner = str(terminal.get("runner") or posture.get("runner") or "native_bsp")
    die = int(terminal.get("die_slots") or posture.get("die_slots") or 512)
    native = (metrics.get("bench") or {}).get("native_ceiling_ops_per_sec")
    free_meld = bool(truth.get("free_meld"))
    leaves = tree.get("leaves_reached") or 0
    condensed = (doc.get("condense") or {}).get("group_count") or 0

    sections: list[dict[str, str]] = []

    sections.append({
        "id": "field_health",
        "title": "Field health",
        "text": _thermal_plain(metrics),
    })

    th = metrics.get("thermal") or {}
    entropy_bit = "Entropy discipline is clean." if th.get("entropy_ok") else "Entropy is on the trust layer — plate meld should stay light."
    sections.append({
        "id": "thermals_detail",
        "title": "Thermals & gates",
        "text": (
            f"Thermal headroom {th.get('headroom_pct', '—')}%, advisory {th.get('level', 'ok')}. "
            f"Bridge gate {'open' if th.get('gate_ok') else 'closed'}. {entropy_bit}"
        ),
    })

    sit = metrics.get("locational_sitrep") or {}
    sections.append({
        "id": "locational_sitrep",
        "title": "Locational sitrep",
        "text": sit.get("summary") or (
            f"Place {'witnessed' if sit.get('spatial_pass_ok') else 'watch'} — "
            f"GPS {'ready' if sit.get('gps_ready') else 'unset'}; "
            f"geometry {(sit.get('movement') or {}).get('geometry', 'stable')}."
        ),
    })

    sections.append({
        "id": "truth_tree",
        "title": "Truth & combinatoric tree",
        "text": (
            f"{truth.get('eligible_count', 0)} truth blocks eligible"
            f"{', free meld unlocked' if free_meld else ''}. "
            f"Tree reached {leaves} leaves"
            f"{' and is complete' if tree.get('complete') else ' — run Walk to finish'}. "
            f"{condensed} plate groups condensed. Terminal path: {pattern} on {belt} with {runner}."
        ),
    })

    bench = metrics.get("bench") or {}
    sections.append({
        "id": "speed",
        "title": "Speed ceiling",
        "text": (
            f"Local bench native ceiling is {_fmt_ops(native)}"
            f"{f' on {bench.get("host")}' if bench.get('host') else ''}. "
            f"Belt 2.0 cap estimate: {_fmt_ops(bench.get('belt_2_cap'))}."
        ),
    })

    sense = metrics.get("sense") or {}
    sections.append({
        "id": "sense",
        "title": "Compiler sense (Eye · Ear · Mouth)",
        "text": (
            f"Sense ladder currently at {sense_prof} ({sense.get('reason') or 'default'}). "
            f"Eye {'green' if sense.get('eye_ok') else 'watch'}, "
            f"Ear {'green' if sense.get('ear_ok') else 'watch'}, "
            f"Mouth {'green' if sense.get('mouth_ok') else 'watch'}. "
            f"G16 {'ready' if sense.get('g16_ready') else 'not ready'} · meld gen {sense.get('meld_generation') or 0}."
        ),
    })

    if candidates:
        top3 = ", ".join(
            f"{c.get('profile')} ({_fmt_ops(c.get('ops_per_sec'))}, {int(c.get('binary_bytes') or 0) // 1024} KB)"
            for c in candidates[:3]
        )
        sections.append({
            "id": "compile_race",
            "title": "Compile candidate race",
            "text": f"Recombinatorics scored {len(candidates)} profiles. Top three: {top3}.",
        })

    why_parts = [
        f"recombinatorics picked {ideal} for the best speed-to-size balance on your local bench",
        f"combinatoric terminal favors {belt} with {die} die slots",
        f"exec pattern {pattern} via {runner}",
    ]
    if ideal_row.get("belt_match"):
        why_parts.append("profile matches the tree's belt facet")
    if free_meld:
        why_parts.append("free meld is on so native BSP paths score higher")
    if sense_prof == ideal:
        why_parts.append("compiler sense plate agrees")
    elif sense.get("g16_ready"):
        why_parts.append(f"sense plate suggests {sense_prof} but recombinatorics overrides on bench evidence")

    verdict = {
        "best_profile": ideal,
        "best_belt": belt,
        "best_pattern": pattern,
        "best_runner": runner,
        "best_die_slots": die,
        "compiler_default": ideal,
        "sense_profile": sense_prof,
        "confidence": "high" if tree.get("complete") and recomb.get("ok") and th.get("gate_ok") else "medium",
        "why": " ".join(why_parts) + ".",
        "one_liner": (
            f"Best compile: **{ideal}** on **{belt}** ({die} die) — {pattern} / {runner}. "
            f"{why_parts[0].capitalize()}."
        ),
    }

    return {
        "schema": "field-combinatorics-evaluate/v1",
        "sections": sections,
        "verdict": verdict,
        "metrics": metrics,
    }


def _py_subjson(script: Path, args: list[str], *, timeout: int = 180) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": f"missing:{script.name}"}
    env = {**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL), "SG_ROOT": str(SG), "GROK16_ROOT": str(GROK16)}
    proc = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, timeout=timeout, env=env)
    try:
        out = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        out = {"ok": proc.returncode == 0, "stdout": (proc.stdout or "")[:300]}
    out.setdefault("ok", proc.returncode == 0)
    return out


def _run_plate_tests() -> dict[str, Any]:
    runner = INSTALL / "lib" / "field-plate-test-runner.py"
    if not runner.is_file():
        runner = Path(__file__).resolve().parent / "field-plate-test-runner.py"
    if not runner.is_file():
        return {"ok": False, "skipped": True, "reason": "plate_test_runner_missing"}
    env = {**os.environ, "NEXUS_STATE_DIR": str(STATE), "NEXUS_INSTALL_ROOT": str(INSTALL)}
    proc = subprocess.run(
        [sys.executable, str(runner), "smoke"],
        capture_output=True,
        text=True,
        timeout=180,
        env=env,
    )
    try:
        out = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        out = {"ok": proc.returncode == 0}
    out.setdefault("ok", proc.returncode == 0)
    return out


def status() -> dict[str, Any]:
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    ideal = _load(STATE / "g16-ideal-compile.json", {})
    truth = _load(STATE / "g16-truth-blocks-panel.json", {})
    walk = comb.get("tree_walk") or {}
    condense = comb.get("plate_condense") or {}
    recomb = comb.get("recombinatorics") or ideal
    terminal = walk.get("terminal_leaf") or {}
    base = {
        "schema": "field-combinatorics-studio/v2",
        "updated": _now(),
        "ok": bool(comb),
        "motto": "Walk the combinatoric tree yourself — condense plates, meld to perfection. Local only.",
        "truth_blocks": {
            "eligible_count": truth.get("eligible_count"),
            "free_meld": truth.get("free_meld"),
            "library_clear_sentences": truth.get("library_clear_sentences"),
        },
        "tree": {
            "complete": bool(walk.get("tree_complete")),
            "leaves_reached": walk.get("leaves_reached"),
            "top_leaves": walk.get("top_leaves") or [],
            "terminal": terminal,
        },
        "condense": {
            "ok": condense.get("ok"),
            "group_count": condense.get("group_count"),
            "groups": condense.get("groups") or [],
        },
        "recombinatorics": recomb,
        "ideal_profile": recomb.get("ideal_profile") or ideal.get("ideal_profile"),
        "bridge_ok": bridge.get("ok"),
        "exec_posture": bridge.get("exec_posture") or {},
        "speed_cap": comb.get("speed_cap") or {},
        "cardinality": (comb.get("combinatoric_space") or {}).get("cardinality_estimate"),
        "gate": bridge.get("gate") or {},
        "compiler_sense": _load(STATE / "g16-compiler-sense-plate.json", {}),
        "meld": _load(STATE / "field-plate-meld.json", {}),
    }
    ev = evaluate(base)
    base["metrics"] = ev.get("metrics")
    base["evaluate"] = {"sections": ev.get("sections"), "verdict": ev.get("verdict")}
    comb_mod = _import_comb()
    if comb_mod and hasattr(comb_mod, "comb_panel"):
        try:
            base["comb"] = comb_mod.comb_panel()
            base["poll_interval_sec"] = base["comb"].get("poll_interval_sec", 8)
        except Exception:
            base["comb"] = _load(STATE / "field-combinatorics-comb-panel.json", {})
    else:
        base["comb"] = _load(STATE / "field-combinatorics-comb-panel.json", {})
    return base


def run_action(action: str) -> dict[str, Any]:
    action = str(action or "status").strip().lower().replace("-", "_")
    mod = _import_combinatorics()
    if not mod:
        return {"ok": False, "error": "field_combinatorics_missing"}

    truth = _load(STATE / "g16-truth-blocks-panel.json", {})
    steps: list[dict[str, Any]] = []

    if action in ("truth", "truth_publish"):
        steps.append({"step": "truth_publish", **(_run_truth_publish())})
        truth = _load(STATE / "g16-truth-blocks-panel.json", {})
        return {**status(), "action": action, "steps": steps, "ok": all(s.get("ok", True) for s in steps)}

    if action in ("orchestrate", "orchestrator", "meld_orchestrator"):
        orch = _import_orch()
        if orch and hasattr(orch, "build_report"):
            mode = "full" if action == "orchestrate_full" else "cycle"
            doc = orch.build_report(run_steps=True, mode=mode)
            steps.append({
                "step": "plate_meld_orchestrator",
                "ok": doc.get("ok"),
                "improvements": (doc.get("improvement_summary") or {}).get("total"),
                "bottom_cpu": (doc.get("bottom_cpu") or {}).get("at_bottom"),
            })
            out = status()
            out["action"] = action
            out["steps"] = steps
            out["ok"] = doc.get("ok", True)
            out["orchestrator"] = {
                "improvements": doc.get("improvements"),
                "bottom_cpu": doc.get("bottom_cpu"),
                "posture": doc.get("posture"),
            }
            return out
        steps.append({"step": "plate_meld_orchestrator", "ok": False, "error": "orchestrator_missing"})
        return {**status(), "action": action, "steps": steps, "ok": False}

    walk: dict[str, Any] | None = None
    pipeline = {
        "tree": ("tree",),
        "walk": ("walk",),
        "condense": ("condense",),
        "recombine": ("recombine",),
        "publish": ("publish",),
        "bridge": ("bridge",),
        "fast": ("fast_cycle",),
        "fast_cycle": ("fast_cycle",),
        "cycle": ("walk", "recombine", "publish_light", "bridge"),
        "full": ("truth_publish", "walk", "condense", "recombine", "publish", "bridge", "plate_tests"),
        "rebalance": ("g16_rebalance",),
        "combine": ("g16_combine",),
        "connect": ("g16_connect",),
        "optimal": ("g16_optimal",),
    }
    for step in pipeline.get(action, ()):
        if step == "fast_cycle":
            if hasattr(mod, "fast_cycle"):
                fc = mod.fast_cycle(state_dir=STATE)
                steps.append({"step": "fast_cycle", **fc})
                walk = fc.get("walk")
            else:
                walk = mod.walk_tree_to_end(truth_panel=truth, free_meld=bool(truth.get("free_meld")))
                recomb = mod.recombinatorics_cycle(state_dir=STATE, truth_panel=truth, tree_walk=walk)
                pub = mod.publish_panel(state_dir=STATE, light=True) if hasattr(mod, "publish_panel") else {}
                steps.append({"step": "fast_cycle", "ok": True, "walk": walk, "recombinatorics": recomb, "publish": pub})
        elif step == "publish_light":
            pub = mod.publish_panel(state_dir=STATE, light=True)
            steps.append({"step": "publish_light", **pub})
        elif step == "tree":
            tree = mod.combinatoric_tree(truth_panel=truth)
            steps.append({"step": "tree", "ok": True, "leaf_count": tree.get("leaf_count")})
        elif step == "walk":
            walk = mod.walk_tree_to_end(truth_panel=truth, free_meld=bool(truth.get("free_meld")))
            steps.append({"step": "walk", "ok": bool(walk.get("tree_complete")), "terminal": walk.get("terminal_leaf")})
        elif step == "condense":
            meta = os.environ.get("G16_COMBO_CONDENSE", "meta").strip().lower() not in ("full", "0", "false")
            condense = mod.condense_plates(state_dir=STATE, truth_panel=truth, metadata_only=meta)
            steps.append({"step": "condense", **condense})
        elif step == "recombine":
            recomb = mod.recombinatorics_cycle(state_dir=STATE, truth_panel=truth, tree_walk=walk)
            steps.append({"step": "recombine", **recomb})
        elif step == "publish":
            pub = mod.publish_panel(state_dir=STATE, light=False)
            steps.append({"step": "publish", **pub})
        elif step == "truth_publish":
            steps.append({"step": "truth_publish", **(_run_truth_publish())})
            truth = _load(STATE / "g16-truth-blocks-panel.json", {})
        elif step == "plate_tests":
            steps.append({"step": "plate_tests", **_run_plate_tests()})
        elif step == "g16_rebalance":
            reb = INSTALL / "lib" / "g16-combinatronic-rebalance.py"
            steps.append({"step": "g16_rebalance", **_py_subjson(reb, ["rebalance"])})
        elif step == "g16_combine":
            reb = INSTALL / "lib" / "g16-combinatronic-rebalance.py"
            steps.append({"step": "g16_combine", **_py_subjson(reb, ["combine"])})
        elif step == "g16_connect":
            reb = INSTALL / "lib" / "g16-combinatronic-rebalance.py"
            steps.append({"step": "g16_connect", **_py_subjson(reb, ["connect"])})
        elif step == "g16_optimal":
            reb = INSTALL / "lib" / "g16-combinatronic-rebalance.py"
            full = os.environ.get("G16_COMBO_OPTIMAL_FULL", "0") == "1"
            args = ["optimal"] + (["--full"] if full else [])
            steps.append({"step": "g16_optimal", **_py_subjson(reb, args)})

    if action == "bridge":
        bridge_mod = _import_bridge()
        if bridge_mod and hasattr(bridge_mod, "build_bridge"):
            bridge = bridge_mod.build_bridge(write=True)
            steps.append({"step": "bridge", "ok": bridge.get("ok"), "pattern": (bridge.get("exec_posture") or {}).get("pattern_id")})
        else:
            steps.append({"step": "bridge", "ok": False, "error": "bridge_missing"})
    elif "bridge" in pipeline.get(action, ()) and action != "bridge":
        bridge_mod = _import_bridge()
        if bridge_mod and hasattr(bridge_mod, "build_bridge"):
            bridge = bridge_mod.build_bridge(write=True)
            steps.append({"step": "bridge", "ok": bridge.get("ok"), "pattern": (bridge.get("exec_posture") or {}).get("pattern_id")})

    if action == "plate_tests":
        steps.append({"step": "plate_tests", **_run_plate_tests()})

    if not steps and action == "status":
        return status()

    if not steps:
        return {"ok": False, "error": "unknown_action", "action": action}

    doc = status()
    doc["action"] = action
    doc["steps"] = steps
    doc["ok"] = all(s.get("ok", True) for s in steps)
    comb_mod = _import_comb()
    if comb_mod and hasattr(comb_mod, "record_comb_tick"):
        try:
            elapsed = next((s.get("elapsed_ms") for s in reversed(steps) if s.get("elapsed_ms")), None)
            comb_mod.record_comb_tick(action=action, source="combinatorics_studio", extra={"elapsed_ms": elapsed})
            doc["comb"] = comb_mod.comb_panel()
        except Exception:
            pass
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "evaluate":
        print(json.dumps(evaluate(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "run":
        action = sys.argv[2] if len(sys.argv) > 2 else "cycle"
        print(json.dumps(run_action(action), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("tree", "walk", "condense", "recombine", "publish", "cycle", "full", "bridge", "truth", "plate_tests", "rebalance", "combine", "connect", "optimal"):
        print(json.dumps(run_action(cmd), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["json", "status", "run <action>", "tree", "walk", "condense", "recombine", "publish", "cycle", "full", "bridge", "truth", "plate_tests"],
    }, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())