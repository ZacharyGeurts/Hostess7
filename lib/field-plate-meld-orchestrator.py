#!/usr/bin/env pythong
"""Plate meld orchestrator — automate fuse chain, audit connectivity, bottom-CPU combinatorics, redesign map."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
PANEL = STATE / "field-plate-meld-orchestrator-panel.json"

# Canonical meld → combinatorics → exec chain (bottom = FieldX86Die / native BSP)
PIPELINE_STEPS: tuple[dict[str, Any], ...] = (
    {"id": "truth_blocks", "label": "Truth blocks publish", "tier": "truth"},
    {"id": "surface_plates", "label": "Operator + C2 surface plates", "tier": "surfaces"},
    {"id": "combinatorics_walk", "label": "Walk combinatoric tree", "tier": "combinatorics"},
    {"id": "combinatorics_condense", "label": "Condense plate groups", "tier": "combinatorics"},
    {"id": "combinatorics_recombine", "label": "Recombinatorics ideal profile", "tier": "combinatorics"},
    {"id": "combinatorics_publish", "label": "Publish combinatorics panel", "tier": "combinatorics"},
    {"id": "combinatorics_bridge", "label": "Plate combinatorics bridge", "tier": "bridge"},
    {"id": "sovereign_stack_meld", "label": "Sovereign stack meld verify", "tier": "meld"},
    {"id": "plate_meld_fuse", "label": "Plate meld fuse", "tier": "meld"},
    {"id": "comb_record", "label": "Combinatorics comb telemetry", "tier": "telemetry"},
)

SURFACE_REFRESH_SCRIPTS: tuple[tuple[str, str, str], ...] = (
    ("c2_taskbar", "field-c2-taskbar-plate.py", "posture"),
    ("field_host_desktop", "field-host-desktop.py", "posture"),
    ("shell_dock", "field-shell-dock.py", "posture"),
    ("field_lock", "field-keepass.py", "posture"),
    ("field_broadcaster", "field-broadcaster.py", "posture"),
    ("field_popcorn", "field-popcorn-player.py", "posture"),
    ("field_g16_launch", "field-g16-launch.py", "posture"),
    ("field_gpu", "field-gpu-control.py", "posture"),
    ("field_audio", "field-audio-settings.py", "posture"),
)

BOTTOM_CPU_TARGETS = {
    "runner": ("native_bsp", "iron_exec"),
    "emulator": ("FieldX86Die",),
    "avoid_runner": ("python",),
    "avoid_emulator": ("FieldX86Emu",),
}


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


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _import_py(path: Path, name: str) -> Any | None:
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _import_meld() -> Any | None:
    return _import_py(INSTALL / "lib" / "field-plate-meld.py", "field_plate_meld_orch")


def _import_combinatorics() -> Any | None:
    for path in (
        GROK16 / "lib" / "field_combinatorics.py",
        INSTALL / "Grok16" / "lib" / "field_combinatorics.py",
    ):
        mod = _import_py(path, "field_combinatorics_orch")
        if mod:
            return mod
    return None


def _import_bridge() -> Any | None:
    return _import_py(INSTALL / "lib" / "field-plate-combinatorics-bridge.py", "field_plate_combinatorics_bridge_orch")


def _import_comb() -> Any | None:
    return _import_py(INSTALL / "lib" / "field-combinatorics-comb.py", "field_combinatorics_comb_orch")


def _import_studio() -> Any | None:
    return _import_py(INSTALL / "lib" / "field-combinatorics-studio.py", "field_combinatorics_studio_orch")


def _http_routes() -> set[str]:
    http_py = INSTALL / "lib" / "threat-panel-http.py"
    if not http_py.is_file():
        return set()
    try:
        text = http_py.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    routes: set[str] = set()
    for m in re.finditer(r'path\s*(?:==|in)\s*\(?\s*["\'](/api/[^"\']+)["\']', text):
        routes.add(m.group(1).split('"')[0].split("'")[0])
    for m in re.finditer(r'["\'](/api/[^"\']+)["\']', text):
        p = m.group(1)
        if p.startswith("/api/"):
            routes.add(p)
    return routes


def _parallel_slices() -> dict[str, Any]:
    par = _import_py(INSTALL / "lib" / "field-panel-parallel.py", "field_panel_parallel_orch")
    if not par:
        return {}
    return dict(getattr(par, "FIELD_SLICES", {}) or {})


def _condense_groups() -> dict[str, list[tuple[str, str]]]:
    comb = _import_combinatorics()
    if comb and hasattr(comb, "PLATE_CONDENSE_GROUPS"):
        return dict(comb.PLATE_CONDENSE_GROUPS)
    dim = _import_py(INSTALL / "lib" / "field-plate-dimensions.py", "plate_dim_orch")
    if dim and hasattr(dim, "PLATE_CONDENSE_GROUPS"):
        return dict(dim.PLATE_CONDENSE_GROUPS)
    return {}


def _plate_sources() -> list[tuple[str, str]]:
    meld = _import_meld()
    if meld and hasattr(meld, "PLATE_SOURCES"):
        return list(meld.PLATE_SOURCES)
    return []


def _meld_refresh_hooks() -> set[str]:
    meld = _import_meld()
    if not meld:
        return set()
    hooks: set[str] = set()
    for name in dir(meld):
        if name.startswith("_refresh_") and callable(getattr(meld, name)):
            hooks.add(name[len("_refresh_") :])
    return hooks


def _surfaces_doctrine() -> list[dict[str, Any]]:
    doc = _load(INSTALL / "data" / "field-field-surfaces-doctrine.json", {})
    return list(doc.get("surfaces") or [])


def _timed(step_id: str, fn: Callable[[], Any]) -> dict[str, Any]:
    t0 = time.perf_counter()
    try:
        out = fn()
        elapsed = int((time.perf_counter() - t0) * 1000)
        if isinstance(out, dict):
            return {"id": step_id, "ok": out.get("ok", True), "elapsed_ms": elapsed, **out}
        return {"id": step_id, "ok": True, "elapsed_ms": elapsed, "result": out}
    except Exception as exc:
        return {"id": step_id, "ok": False, "elapsed_ms": int((time.perf_counter() - t0) * 1000), "error": str(exc)[:200]}


def _refresh_surface_plates() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for plate_id, script_name, fn_name in SURFACE_REFRESH_SCRIPTS:
        script = INSTALL / "lib" / script_name
        mod = _import_py(script, script_name.replace("-", "_"))
        ok = False
        err = ""
        if mod and hasattr(mod, fn_name):
            try:
                getattr(mod, fn_name)()
                ok = True
            except Exception as exc:
                err = str(exc)[:120]
        else:
            err = "script_or_fn_missing"
        rows.append({"plate": plate_id, "script": script_name, "ok": ok, "error": err or None})
    live = sum(1 for r in rows if r.get("ok"))
    return {"ok": live > 0, "live": live, "total": len(rows), "surfaces": rows}


def bottom_cpu_posture() -> dict[str, Any]:
    """Evaluate how close exec posture is to bottom CPU (FieldX86Die / native BSP)."""
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    truth = _load(STATE / "g16-truth-blocks-panel.json", {})
    posture = bridge.get("exec_posture") or {}
    gate = bridge.get("gate") or {}
    stack = bridge.get("emulator_stack") or {}

    runner = str(posture.get("runner") or "")
    emulator = str(posture.get("emulator") or stack.get("primary") or "")
    runs_cool = bool(posture.get("runs_cool"))
    gate_ok = bool(gate.get("ok"))
    free_meld = bool(truth.get("free_meld"))
    iron_exec = bool(posture.get("iron_exec_recommended"))

    at_bottom = (
        runner in BOTTOM_CPU_TARGETS["runner"]
        and emulator in BOTTOM_CPU_TARGETS["emulator"]
    )
    blockers: list[dict[str, Any]] = []
    if runner in BOTTOM_CPU_TARGETS["avoid_runner"]:
        blockers.append({
            "id": "python_runner",
            "severity": "high",
            "fix": "Collect truth blocks / free_meld; rerun walk+bridge so terminal leaf picks native_bsp",
        })
    if emulator in BOTTOM_CPU_TARGETS["avoid_emulator"]:
        blockers.append({
            "id": "emu_fallback",
            "severity": "high",
            "fix": "Thermal gate or missing free_meld — cool_sort then bridge meld toward FieldX86Die",
        })
    if not gate_ok:
        blockers.append({
            "id": "thermal_entropy_gate",
            "severity": "medium",
            "fix": "Wait for thermal headroom or run light fuse; gate blocks native BSP under heat",
        })
    if not runs_cool:
        blockers.append({
            "id": "runs_not_cool",
            "severity": "medium",
            "fix": "Power sort sections hot — refresh physics witness and g16_power_sort before full meld",
        })
    if not free_meld and not iron_exec:
        blockers.append({
            "id": "no_free_meld",
            "severity": "low",
            "fix": "Publish more library clear sentences (≥12) or eligible truth blocks (≥2)",
        })

    fs = bridge.get("field_surfaces") or {}
    bsp_misses = [
        s.get("id") for s in (fs.get("surfaces") or [])
        if s.get("bsp_hit") is False or (s.get("id") == "c2_taskbar" and not s.get("bsp_hit"))
    ]
    if bsp_misses:
        blockers.append({
            "id": "bsp_cache_miss",
            "severity": "low",
            "plates": bsp_misses,
            "fix": "Run field-exec-full-bench or plate BSP staging (e.g. field-c2-taskbar-plate.py bsp)",
        })

    comb_mod = _import_comb()
    cpu_cat = comb_mod.cpu_architecture_catalog() if comb_mod and hasattr(comb_mod, "cpu_architecture_catalog") else {}
    die_active = any(
        a.get("kind") == "fieldx86_die" and a.get("active")
        for a in (cpu_cat.get("architectures") or [])
    )

    return {
        "schema": "field-plate-meld-bottom-cpu/v1",
        "at_bottom": at_bottom,
        "runner": runner,
        "emulator": emulator,
        "die_slots": posture.get("die_slots"),
        "belt_profile": posture.get("belt_profile"),
        "pattern_id": posture.get("pattern_id"),
        "gate_ok": gate_ok,
        "runs_cool": runs_cool,
        "free_meld": free_meld,
        "die_active_in_catalog": die_active,
        "native_ceiling_ops": (comb.get("speed_cap") or {}).get("native_ceiling_ops_per_sec"),
        "blockers": blockers,
        "recommendation": (
            "At bottom CPU — FieldX86Die native BSP"
            if at_bottom
            else f"Push toward native_bsp + FieldX86Die (now {runner}/{emulator})"
        ),
    }


def audit_connectivity() -> dict[str, Any]:
    """Cross-check plates, refresh hooks, parallel slices, API routes, condense groups."""
    sources = _plate_sources()
    hooks = _meld_refresh_hooks()
    parallel = _parallel_slices()
    routes = _http_routes()
    condense = _condense_groups()
    surfaces = _surfaces_doctrine()

    plate_rows: list[dict[str, Any]] = []
    missing_refresh: list[str] = []
    missing_panel: list[str] = []
    stale_panel: list[str] = []

    for key, fname in sources:
        panel_path = STATE / fname
        present = panel_path.is_file()
        stale = False
        if present:
            try:
                doc = _load(panel_path, {})
                stale = not bool(doc.get("ok", True)) and not doc.get("missing")
            except Exception:
                stale = True
        has_hook = key in hooks or key.replace("_", "") in {h.replace("_", "") for h in hooks}
        in_parallel = key in parallel or f"field_{key}" in parallel or key.replace("field_", "") in parallel
        plate_rows.append({
            "id": key,
            "panel": fname,
            "present": present,
            "ok": (_load(panel_path, {}).get("ok") if present else False),
            "has_refresh_hook": has_hook,
            "in_parallel": in_parallel,
        })
        if not has_hook and key not in ("iron_plate", "plate_runtime"):
            missing_refresh.append(key)
        if not present:
            missing_panel.append(key)

    surface_rows: list[dict[str, Any]] = []
    surface_gaps: list[dict[str, Any]] = []
    for surf in surfaces:
        sid = str(surf.get("id") or "")
        route = str(surf.get("route") or "")
        script = str(surf.get("script") or "")
        panel = str(surf.get("panel") or "")
        plate_key = str(surf.get("plate_key") or sid)
        script_path = INSTALL / "lib" / script if script else None
        panel_path = STATE / panel if panel else None
        in_sources = any(k == plate_key for k, _ in sources)
        in_parallel_key = plate_key in parallel or f"field_{plate_key}" in parallel or sid in parallel
        route_live = route in routes if route else False
        condense_group = surf.get("condense_group") or "operator_surfaces"
        in_condense = plate_key in {m[0] for m in condense.get(condense_group, [])} or plate_key in {
            m[0] for members in condense.values() for m in members
        }
        row = {
            "id": sid,
            "plate_key": plate_key,
            "script": script,
            "script_present": script_path.is_file() if script_path else False,
            "panel": panel,
            "panel_present": panel_path.is_file() if panel_path else False,
            "route": route,
            "route_wired": route_live,
            "in_plate_sources": in_sources,
            "in_parallel": in_parallel_key,
            "in_condense_group": in_condense,
            "condense_group": condense_group,
        }
        surface_rows.append(row)
        gaps: list[str] = []
        if script and not row["script_present"]:
            gaps.append("missing_script")
        if panel and not row["panel_present"]:
            gaps.append("missing_panel")
        if route and not row["route_wired"]:
            gaps.append("missing_api_route")
        if not row["in_plate_sources"]:
            gaps.append("not_in_plate_sources")
        if not row["in_parallel"]:
            gaps.append("not_in_parallel_slices")
        if not row["in_condense_group"]:
            gaps.append("not_in_condense_group")
        if gaps:
            surface_gaps.append({"surface": sid, "gaps": gaps, "fixes": _gap_fixes(gaps, surf)})

    condense_rows: list[dict[str, Any]] = []
    for group_id, members in condense.items():
        present = sum(1 for k, fn in members if (STATE / fn).is_file())
        condensed_path = STATE / f"condensed-{group_id}-plate.json"
        condense_rows.append({
            "group": group_id,
            "members": len(members),
            "present": present,
            "condensed_file": condensed_path.is_file(),
            "ready": present >= max(2, len(members) // 2),
        })

    expected_comb_ids = {
        "c2_taskbar", "shell_dock", "field_popcorn", "field_g16_launch", "field_gpu",
        "field_audio", "field_broadcaster", "field_lock", "combinatorics_bridge",
        "field_combinatorics", "truth_blocks", "code_bugfinder",
    }
    comb_ids: set[str] = set()
    comb_mod = _import_comb()
    if comb_mod and hasattr(comb_mod, "plate_meld_design"):
        try:
            design = comb_mod.plate_meld_design()
            for src in design.get("plate_sources") or []:
                if src.get("combinatorics"):
                    comb_ids.add(str(src.get("id") or ""))
        except Exception:
            pass
    combinatorics_gaps = sorted(expected_comb_ids - comb_ids)

    return {
        "schema": "field-plate-meld-connectivity-audit/v1",
        "plate_count": len(sources),
        "plates_present": sum(1 for r in plate_rows if r["present"]),
        "plates_with_refresh": sum(1 for r in plate_rows if r["has_refresh_hook"]),
        "surfaces": surface_rows,
        "surface_gaps": surface_gaps,
        "condense_groups": condense_rows,
        "missing_refresh_hooks": missing_refresh,
        "missing_panels": missing_panel,
        "combinatorics_comb_gaps": combinatorics_gaps,
        "parallel_slice_count": len(parallel),
        "api_route_count": len(routes),
    }


def _gap_fixes(gaps: list[str], surf: dict[str, Any]) -> list[str]:
    fixes: list[str] = []
    sid = surf.get("id", "")
    if "missing_api_route" in gaps:
        fixes.append(f"Add {surf.get('route')} handler in threat-panel-http.py → {surf.get('script')}")
    if "not_in_parallel_slices" in gaps:
        fixes.append(f"Add '{surf.get('plate_key') or sid}' to FIELD_SLICES in field-panel-parallel.py")
    if "not_in_plate_sources" in gaps:
        fixes.append(f"Add ('{surf.get('plate_key')}', '{surf.get('panel')}') to PLATE_SOURCES in field-plate-meld.py")
    if "not_in_condense_group" in gaps:
        fixes.append(f"Add member to PLATE_CONDENSE_GROUPS['{surf.get('condense_group', 'operator_surfaces')}'] in field_combinatorics.py")
    if "missing_script" in gaps:
        fixes.append(f"Implement lib/{surf.get('script')}")
    return fixes


def build_connection_graph() -> dict[str, Any]:
    """Redesign map — how programs should connect (truth → comb → bridge → meld → surfaces)."""
    nodes = [
        {"id": "truth_blocks", "module": "Grok16/lib/field_truth_blocks.py", "panel": "g16-truth-blocks-panel.json", "feeds": ["combinatorics", "condense"]},
        {"id": "combinatorics", "module": "Grok16/lib/field_combinatorics.py", "panel": "g16-field-combinatorics-panel.json", "feeds": ["bridge", "condense", "studio"]},
        {"id": "bridge", "module": "lib/field-plate-combinatorics-bridge.py", "panel": "field-plate-combinatorics-bridge.json", "feeds": ["meld", "comb", "studio"]},
        {"id": "meld", "module": "lib/field-plate-meld.py", "panel": "field-plate-meld.json", "feeds": ["bus", "copilot", "threat_panel"]},
        {"id": "surfaces", "module": "lib/field-field-surfaces-doctrine.json", "panel": "field-*-panel.json", "feeds": ["bridge", "meld", "condense"]},
        {"id": "c2_taskbar", "module": "lib/field-c2-taskbar-plate.py", "panel": "field-c2-taskbar-panel.json", "feeds": ["bridge", "meld", "bsp"]},
        {"id": "studio", "module": "lib/field-combinatorics-studio.py", "panel": "combinatorics API", "feeds": ["operator"]},
        {"id": "comb", "module": "lib/field-combinatorics-comb.py", "panel": "field-combinatorics-comb-panel.json", "feeds": ["studio", "charts"]},
        {"id": "parallel", "module": "lib/field-panel-parallel.py", "panel": "threat-panel.json slices", "feeds": ["meld", "ui_tabs"]},
        {"id": "bsp", "module": "Grok16/lib/field_exec_bsp.py", "panel": "data/bench/exec-plane/", "feeds": ["c2_taskbar", "g16_compile"]},
        {"id": "bottom_cpu", "module": "combinatorics terminal leaf", "panel": "exec_posture", "feeds": ["FieldX86Die", "native_bsp"]},
    ]
    edges = [
        {"from": "truth_blocks", "to": "combinatorics", "via": "publish_panel"},
        {"from": "combinatorics", "to": "condense", "via": "condense_plates()"},
        {"from": "combinatorics", "to": "bridge", "via": "combinatorics_panel() + select_exec_posture()"},
        {"from": "surfaces", "to": "bridge", "via": "field_surface_slices()"},
        {"from": "c2_taskbar", "to": "surfaces", "via": "field-field-surfaces-doctrine.json"},
        {"from": "c2_taskbar", "to": "bsp", "via": "bsp_try_reuse(c2_taskbar_plate)"},
        {"from": "bridge", "to": "meld", "via": "combinatorics_bridge plate in PLATE_SOURCES"},
        {"from": "meld", "to": "parallel", "via": "FIELD_SLICES refresh symmetric tabs"},
        {"from": "combinatorics", "to": "bottom_cpu", "via": "walk_tree_to_end → terminal_leaf"},
        {"from": "studio", "to": "combinatorics", "via": "run_action(cycle|full)"},
        {"from": "orchestrator", "to": "all", "via": "this module — single entry for audit + run"},
    ]
    return {
        "schema": "field-plate-meld-connection-graph/v1",
        "motto": "Truth → combinatorics → condense → bridge → meld → parallel UI. Bottom CPU = FieldX86Die.",
        "nodes": nodes,
        "edges": edges,
        "pipeline_order": [s["id"] for s in PIPELINE_STEPS],
    }


def collect_improvements(
    *,
    connectivity: dict[str, Any] | None = None,
    bottom: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Ranked improvement list — wiring gaps, CPU posture, condense, meld health."""
    connectivity = connectivity or audit_connectivity()
    bottom = bottom or bottom_cpu_posture()
    meld = _load(STATE / "field-plate-meld.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    improvements: list[dict[str, Any]] = []

    for gap in connectivity.get("surface_gaps") or []:
        improvements.append({
            "severity": "high" if "missing_api_route" in gap.get("gaps", []) else "medium",
            "category": "surface_wiring",
            "target": gap.get("surface"),
            "issue": ", ".join(gap.get("gaps") or []),
            "fixes": gap.get("fixes") or [],
        })

    for key in connectivity.get("missing_refresh_hooks") or []:
        if key in ("iron_plate", "plate_runtime", "sovereign_sync"):
            continue
        improvements.append({
            "severity": "medium",
            "category": "meld_refresh",
            "target": key,
            "issue": f"No _refresh_{key} in field-plate-meld.py",
            "fixes": [f"Add _refresh_{key}() and _refresh_if_allowed('{key}', ...) in fuse()"],
        })

    for grp in connectivity.get("condense_groups") or []:
        if grp.get("ready") and not grp.get("condensed_file"):
            improvements.append({
                "severity": "medium",
                "category": "condense",
                "target": grp.get("group"),
                "issue": "Members present but condensed plate not written",
                "fixes": ["Run combinatorics condense (full) after truth blocks land"],
            })

    if not (comb.get("tree_walk") or {}).get("tree_complete"):
        improvements.append({
            "severity": "high",
            "category": "combinatorics",
            "target": "tree_walk",
            "issue": "Combinatoric tree not complete",
            "fixes": ["field_combinatorics.py walk_tree_to_end or studio action 'walk'"],
        })

    if not bridge.get("ok"):
        improvements.append({
            "severity": "high",
            "category": "bridge",
            "target": "field-plate-combinatorics-bridge",
            "issue": "Bridge not OK",
            "fixes": ["field-plate-combinatorics-bridge.py build"],
        })

    summary = (meld.get("summary") or {}) if meld else {}
    if summary.get("c2_quint_live", 0) < 4:
        improvements.append({
            "severity": "medium",
            "category": "c2_taskbar",
            "target": "quint",
            "issue": f"C2 quint only {summary.get('c2_quint_live', 0)}/5 live",
            "fixes": ["field-c2-taskbar-plate.py json", "refresh queen-files/terminal routes"],
        })

    if not bottom.get("at_bottom"):
        for blocker in bottom.get("blockers") or []:
            improvements.append({
                "severity": blocker.get("severity", "medium"),
                "category": "bottom_cpu",
                "target": blocker.get("id"),
                "issue": blocker.get("fix", ""),
                "fixes": [blocker.get("fix", "")],
            })

    for cid in connectivity.get("combinatorics_comb_gaps") or []:
        improvements.append({
            "severity": "low",
            "category": "comb_design",
            "target": cid,
            "issue": "Missing from field-combinatorics-comb.py combinatorics_ids",
            "fixes": [f"Add '{cid}' to combinatorics_ids and operator_surface in plate_meld_design()"],
        })

    order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    improvements.sort(key=lambda r: (order.get(r.get("severity", "info"), 9), r.get("category", "")))
    return improvements


def run_pipeline(mode: str = "cycle") -> dict[str, Any]:
    """Automate meld chain. Modes: audit, cycle, full."""
    mode = str(mode or "cycle").strip().lower()
    if mode == "audit":
        return build_report(run_steps=False)

    comb = _import_combinatorics()
    meld = _import_meld()
    bridge = _import_bridge()
    comb_telemetry = _import_comb()
    studio = _import_studio()

    steps: list[dict[str, Any]] = []
    truth = _load(STATE / "g16-truth-blocks-panel.json", {})
    walk: dict[str, Any] | None = None

    def _want(step_id: str) -> bool:
        if mode == "full":
            return True
        if mode == "fast":
            return step_id in ("surface_plates", "combinatorics_bridge", "sovereign_stack_meld", "plate_meld_fuse")
        if mode == "cycle":
            return step_id in (
                "surface_plates", "combinatorics_walk", "combinatorics_condense",
                "combinatorics_recombine", "combinatorics_publish", "combinatorics_bridge",
                "sovereign_stack_meld", "plate_meld_fuse", "comb_record",
            )
        return step_id == "plate_meld_fuse"

    if _want("truth_blocks") and mode == "full":
        if studio and hasattr(studio, "_run_truth_publish"):
            steps.append(_timed("truth_blocks", studio._run_truth_publish))
            truth = _load(STATE / "g16-truth-blocks-panel.json", {})

    if _want("surface_plates"):
        steps.append(_timed("surface_plates", _refresh_surface_plates))

    if comb:
        if _want("combinatorics_walk"):
            def _walk() -> dict[str, Any]:
                nonlocal walk
                walk = comb.walk_tree_to_end(truth_panel=truth, free_meld=bool(truth.get("free_meld")))
                return {"ok": bool(walk.get("tree_complete")), "terminal": walk.get("terminal_leaf")}
            steps.append(_timed("combinatorics_walk", _walk))

        if _want("combinatorics_condense"):
            meta = os.environ.get("G16_COMBO_CONDENSE", "meta").strip().lower() not in ("full", "0", "false")
            steps.append(_timed(
                "combinatorics_condense",
                lambda: comb.condense_plates(state_dir=STATE, truth_panel=truth, metadata_only=meta),
            ))

        if _want("combinatorics_recombine"):
            steps.append(_timed(
                "combinatorics_recombine",
                lambda: comb.recombinatorics_cycle(state_dir=STATE, truth_panel=truth, tree_walk=walk),
            ))

        if _want("combinatorics_publish"):
            light = mode != "full"
            steps.append(_timed(
                "combinatorics_publish",
                lambda: comb.publish_panel(state_dir=STATE, light=light),
            ))

    if _want("combinatorics_bridge") and bridge and hasattr(bridge, "build_bridge"):
        steps.append(_timed("combinatorics_bridge", lambda: bridge.build_bridge(write=True)))

    if _want("sovereign_stack_meld"):
        ssm = _import_py(INSTALL / "lib" / "field-sovereign-stack-meld.py", "sov_stack_meld")
        if ssm and hasattr(ssm, "publish_panel"):
            steps.append(_timed("sovereign_stack_meld", ssm.publish_panel))

    if _want("plate_meld_fuse") and meld and hasattr(meld, "fuse"):
        steps.append(_timed("plate_meld_fuse", lambda: meld.fuse(refresh_bus=mode == "full")))

    if _want("comb_record") and comb_telemetry and hasattr(comb_telemetry, "record_comb_tick"):
        steps.append(_timed(
            "comb_record",
            lambda: comb_telemetry.record_comb_tick(action=f"orchestrator_{mode}", source="plate_meld_orchestrator"),
        ))

    return {
        "mode": mode,
        "steps": steps,
        "ok": all(s.get("ok", True) for s in steps),
        "elapsed_ms": sum(s.get("elapsed_ms", 0) for s in steps),
    }


def build_report(*, run_steps: bool = True, mode: str = "cycle") -> dict[str, Any]:
    pipeline_result = run_pipeline(mode) if run_steps else {"skipped": True, "mode": mode}
    connectivity = audit_connectivity()
    bottom = bottom_cpu_posture()
    improvements = collect_improvements(connectivity=connectivity, bottom=bottom)
    graph = build_connection_graph()
    meld = _load(STATE / "field-plate-meld.json", {})

    high = sum(1 for i in improvements if i.get("severity") == "high")
    medium = sum(1 for i in improvements if i.get("severity") == "medium")

    doc = {
        "schema": "field-plate-meld-orchestrator/v1",
        "ts": _now(),
        "ok": pipeline_result.get("ok", True) and high == 0,
        "product": "Plate Meld Orchestrator",
        "motto": "One entry — audit wiring, run the chain, push combinatorics to bottom CPU.",
        "mode": mode,
        "pipeline": pipeline_result,
        "connectivity": connectivity,
        "connection_graph": graph,
        "bottom_cpu": bottom,
        "improvements": improvements,
        "improvement_summary": {
            "total": len(improvements),
            "high": high,
            "medium": medium,
            "low": sum(1 for i in improvements if i.get("severity") == "low"),
        },
        "meld_generation": meld.get("generation"),
        "meld_summary": meld.get("summary"),
        "posture": (
            f"{'Bottom CPU' if bottom.get('at_bottom') else 'Not bottom CPU'} · "
            f"{bottom.get('runner')}/{bottom.get('emulator')} · "
            f"{len(improvements)} improvements ({high} high)"
        ),
    }
    _save_atomic(PANEL, doc)
    return doc


def human_report(doc: dict[str, Any]) -> str:
    lines = [
        f"Plate Meld Orchestrator — {doc.get('ts')}",
        doc.get("posture", ""),
        "",
        "Pipeline:",
    ]
    for step in (doc.get("pipeline") or {}).get("steps") or []:
        mark = "OK" if step.get("ok") else "FAIL"
        lines.append(f"  [{mark}] {step.get('id')} ({step.get('elapsed_ms', 0)} ms)")
    lines.extend(["", f"Improvements ({doc.get('improvement_summary', {}).get('total', 0)}):", ""])
    for imp in (doc.get("improvements") or [])[:24]:
        lines.append(f"  [{imp.get('severity', '?').upper()}] {imp.get('category')}/{imp.get('target')}: {imp.get('issue')}")
        for fix in (imp.get("fixes") or [])[:2]:
            lines.append(f"      → {fix}")
    bc = doc.get("bottom_cpu") or {}
    lines.extend([
        "",
        f"Bottom CPU: {bc.get('recommendation', '—')}",
        f"  runner={bc.get('runner')} emulator={bc.get('emulator')} gate_ok={bc.get('gate_ok')}",
    ])
    return "\n".join(lines)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    mode = (sys.argv[2] if len(sys.argv) > 2 else "cycle").strip().lower()

    if cmd in ("json", "status", "panel"):
        print(json.dumps(build_report(run_steps=False), ensure_ascii=False, indent=2))
        return 0
    if cmd == "audit":
        doc = build_report(run_steps=False)
        print(json.dumps({
            "connectivity": doc.get("connectivity"),
            "bottom_cpu": doc.get("bottom_cpu"),
            "improvements": doc.get("improvements"),
            "connection_graph": doc.get("connection_graph"),
        }, ensure_ascii=False, indent=2))
        return 0
    if cmd == "improve":
        doc = build_report(run_steps=False)
        print(json.dumps(doc.get("improvements") or [], ensure_ascii=False, indent=2))
        return 0
    if cmd == "connect":
        print(json.dumps(build_connection_graph(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "bottom":
        print(json.dumps(bottom_cpu_posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "report":
        doc = build_report(run_steps=cmd != "audit-only", mode=mode)
        print(human_report(doc))
        return 0 if doc.get("ok") else 1
    if cmd in ("run", "cycle", "full", "fast"):
        run_mode = cmd if cmd != "run" else mode
        doc = build_report(run_steps=True, mode=run_mode)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    print(
        "usage: field-plate-meld-orchestrator.py [json|audit|improve|connect|bottom|report|run|cycle|full|fast] [mode]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())