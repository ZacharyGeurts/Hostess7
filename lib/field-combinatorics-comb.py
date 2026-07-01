#!/usr/bin/env pythong
"""Combinatorics comb telemetry — frequent charts, CPU catalog, plate meld design, brain speed routing."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from operator import itemgetter
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent if INSTALL.name == "nexus-shield" else INSTALL.parent)))
from sg_paths import grok16_root

GROK16 = grok16_root()
PANEL = STATE / "field-combinatorics-comb-panel.json"
LEDGER = STATE / "field-combinatorics-comb-ledger.jsonl"
LEDGER_MAX = 2000
CHART_TAIL = 120
POLL_INTERVAL_SEC = 5


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


def _save(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_ledger(row: dict[str, Any]) -> None:
    try:
        with LEDGER.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        if LEDGER.is_file():
            lines = LEDGER.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lines) > LEDGER_MAX:
                LEDGER.write_text("\n".join(lines[-LEDGER_MAX:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def _tail_ledger(limit: int = CHART_TAIL) -> list[dict[str, Any]]:
    if not LEDGER.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    except OSError:
        pass
    return rows


def _import_combinatorics() -> Any | None:
    for path in (GROK16 / "lib" / "field_combinatorics.py"):
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("field_combinatorics_comb", path)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _brain_core_paths() -> list[Path]:
    return [
        p for p in (
            SG / "Hostess7" / "scripts" / "field_brain_core.py",
            SG / "NewLatest" / "Hostess7" / "scripts" / "field_brain_core.py",
            INSTALL / "Hostess7" / "scripts" / "field_brain_core.py",
        )
        if p.is_file()
    ]


def _load_brain_module() -> Any | None:
    for brain_py in _brain_core_paths():
        try:
            mod_name = f"field_brain_core_comb_{brain_py.parent.parent.name}"
            spec = importlib.util.spec_from_file_location(mod_name, brain_py)
            if spec and spec.loader:
                bmod = importlib.util.module_from_spec(spec)
                sys.modules[mod_name] = bmod
                spec.loader.exec_module(bmod)
                return bmod
        except Exception:
            continue
    return None


def _brain_route(task: str, *, pattern_id: str = "", runner: str = "") -> dict[str, Any]:
    """Map combinatorics speed task → Hostess7 brain area + neural chamber."""
    route: dict[str, Any] = {
        "task": task,
        "pattern_id": pattern_id,
        "runner": runner,
        "brain_area": None,
        "neural_chamber": None,
        "why": "",
        "try_command": "",
    }
    task_l = task.lower()
    pat = pattern_id.lower()
    run = runner.lower()

    if "bench" in task_l or "speed" in task_l or "bsp" in pat or run in ("native_bsp", "iron_exec"):
        area_id, chamber = "broca", "g16_unified"
        intent = "code"
        why = "Broca routes shell/code/BSP hot paths; grok16_runtime chamber drives native bench."
    elif "emul" in task_l or "chips" in pat or "die" in task_l or run == "python":
        area_id, chamber = "temporal", "g16_unified"
        intent = "chips"
        why = "Temporal holds emulation pattern memory — try when Python/emu paths lag native BSP."
    elif "spatial" in pat or "lattice" in pat:
        area_id, chamber = "limbic", "g16_forever"
        intent = "field_drive"
        why = "Limbic field resonance for spatial lattice ticks — wave-optimized compile paths."
    elif "truth" in task_l or "condense" in task_l:
        area_id, chamber = "insula", "detective_truth"
        intent = "detective"
        why = "Insula detective hub corroborates truth before condense commits."
    else:
        area_id, chamber = "prefrontal", "g16_unified"
        intent = "release"
        why = "Prefrontal plans profile switches and release gates when headroom allows faster belt."

    route["brain_area"] = area_id
    route["neural_chamber"] = chamber
    route["why"] = why
    route["try_command"] = f"./Hostess7.sh brain route --intent={intent}"

    bmod = _load_brain_module()
    if bmod:
        try:
            if hasattr(bmod, "route_query"):
                q = f"combinatorics {task} {pattern_id} {runner}".strip()
                br = bmod.route_query(q, intent, workspace="bench")
                if hasattr(br, "_asdict"):
                    route["brain_route"] = br._asdict()
                elif isinstance(br, dict):
                    route["brain_route"] = br
                else:
                    route["brain_route"] = {
                        "primary_area": getattr(br, "primary_area", None),
                        "secondary_area": getattr(br, "secondary_area", None),
                        "cross_transfer": getattr(br, "cross_transfer", None),
                    }
            if hasattr(bmod, "brain_status"):
                route["brain_status"] = bmod.brain_status()
        except Exception as exc:
            route["brain_error"] = str(exc)

    stack = _load(SG / "Hostess7" / "data" / "hostess7-neural-stack.json", {})
    if not stack.get("series"):
        stack = _load(SG / "NewLatest" / "Hostess7" / "data" / "hostess7-neural-stack.json", stack)
    for series in stack.get("series") or []:
        if series.get("id") == "grok16_runtime":
            route["grok16_chambers"] = [n.get("id") for n in (series.get("nets") or []) if n.get("id")]
            break

    return route


def _ironclad_chips_architectures() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load Ironclad chip combinatorics for combinatorics CPU catalog."""
    for path in (
        INSTALL / "lib" / "field-ironclad-chips-combinatorics.py",
        Path(__file__).resolve().parent / "field-ironclad-chips-combinatorics.py",
    ):
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("field_ironclad_chips_comb", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "build_ironclad_chips_combinatorics"):
                    battery = mod.build_ironclad_chips_combinatorics()
                    archs: list[dict[str, Any]] = []
                    for chip in battery.get("chips") or []:
                        archs.append({
                            "kind": f"chip_{chip.get('kind') or 'battery'}",
                            "id": chip.get("id"),
                            "label": chip.get("label"),
                            "vendor": chip.get("vendor"),
                            "family": chip.get("family"),
                            "mame_device": chip.get("mame_device"),
                            "combinatorics_leaf": chip.get("combinatorics_leaf"),
                            "source": chip.get("source"),
                            "mhz": chip.get("mhz"),
                            "platforms": chip.get("platforms"),
                            "path_pct": chip.get("path_pct"),
                            "band": chip.get("band"),
                            "slot": chip.get("slot"),
                            "pipe_width": chip.get("pipe_width"),
                        })
                    pred = battery.get("code_path_prediction") or {}
                    return archs, {
                        **(battery.get("counts") or {}),
                        "path_prediction": {
                            "total_pct": pred.get("total_pct"),
                            "bands": len(pred.get("bands") or []),
                            "narrow_band_width": pred.get("narrow_band_width"),
                        },
                    }
        except Exception:
            continue
    return [], {}


def _program_combinatronic_counts() -> dict[str, Any]:
    for path in (
        INSTALL / "lib" / "field-program-combinatronic.py",
        Path(__file__).resolve().parent / "field-program-combinatronic.py",
    ):
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("field_program_combinatronic_comb", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "program_combinatronic_slice"):
                    sl = mod.program_combinatronic_slice(state_dir=STATE)
                    counts = sl.get("counts") or {}
                    return {
                        "languages": counts.get("languages"),
                        "commands": counts.get("commands"),
                        "leaves": sl.get("leaf_count"),
                        "boil_pct": sl.get("boil_pct"),
                        "boil_complete": sl.get("boil_complete"),
                    }
        except Exception:
            continue
    return {}


def cpu_architecture_catalog() -> dict[str, Any]:
    """Total architecture map — guest CPUs, host CPUs, G16 exec patterns, CHIPS hot paths."""
    game = _load(SG / "NewLatest" / "Queen" / "data" / "queen-game-room.json", {})
    if not game.get("systems"):
        game = _load(INSTALL / "Queen" / "data" / "queen-game-room.json", game)
    chips = _load(SG / "NewLatest" / "Queen" / "data" / "chips-g16-manifest.json", {})
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    posture = bridge.get("exec_posture") or {}

    guest: list[dict[str, Any]] = []
    cpus_seen: dict[str, int] = {}
    for sys_row in game.get("systems") or []:
        cpu = str(sys_row.get("cpu") or "—")
        cpus_seen[cpu] = cpus_seen.get(cpu, 0) + 1
        guest.append({
            "id": sys_row.get("id"),
            "label": sys_row.get("label"),
            "cpu": cpu,
            "era": sys_row.get("era"),
            "status": sys_row.get("status"),
            "chips": sys_row.get("chips"),
            "ratio": sys_row.get("ratio"),
        })

    host_cpus = list(game.get("host_cpus") or [])
    patterns = comb.get("common_usage") or []
    if not patterns:
        doctrine = _load(GROK16 / "data" / "g16-field-combinatorics-doctrine.json", {})
        for pid in doctrine.get("common_usage_ids") or []:
            patterns.append({"id": pid})

    x86_die = (comb.get("hard_limits") or {}).get("fieldx86") or {}
    exec_stack = bridge.get("emulator_stack") or {}

    architectures: list[dict[str, Any]] = []
    for cpu, count in sorted(cpus_seen.items(), key=lambda x: (-x[1], x[0])):
        if cpu in ("—", ""):
            continue
        architectures.append({
            "kind": "guest_cpu",
            "id": cpu.lower().replace("/", "_").replace(" ", "_"),
            "label": cpu,
            "system_count": count,
            "exec_runner": posture.get("runner"),
            "exec_emulator": posture.get("emulator") or exec_stack.get("primary"),
        })

    for hc in host_cpus:
        architectures.append({
            "kind": "host_cpu",
            "id": hc.get("id"),
            "label": hc.get("label"),
            "vendor": hc.get("vendor"),
            "mhz": hc.get("mhz"),
            "note": hc.get("note"),
        })

    for pat in patterns:
        pid = pat.get("id") or pat.get("pattern_id")
        if not pid:
            continue
        facets = pat.get("facets") or {}
        architectures.append({
            "kind": "g16_pattern",
            "id": pid,
            "label": pat.get("label") or pid,
            "runner": facets.get("runner") or pat.get("runner"),
            "belt": facets.get("profile") or facets.get("belt"),
            "die": facets.get("die"),
            "headroom_ratio": pat.get("headroom_ratio"),
            "ops_per_sec": pat.get("current_ops_per_sec") or pat.get("native_ceiling_ops_per_sec"),
            "active": pid == posture.get("pattern_id"),
        })

    architectures.append({
        "kind": "fieldx86_die",
        "id": "FieldX86Die",
        "label": "FieldX86 die (native BSP)",
        "wave_bands": x86_die.get("wave_bands"),
        "frames_per_epoch": x86_die.get("frames_per_epoch"),
        "belt_1_slots": (x86_die.get("belt_1_0") or {}).get("die_slots"),
        "belt_2_slots": (x86_die.get("belt_2_0") or {}).get("die_slots"),
        "active": (posture.get("emulator") or exec_stack.get("primary")) == "FieldX86Die",
    })

    hot_chips = (chips.get("hot_paths") or chips.get("cores") or chips.get("headers") or [])
    if isinstance(hot_chips, list):
        for chip in hot_chips[:24]:
            if isinstance(chip, str):
                architectures.append({"kind": "chips_hot", "id": chip, "label": chip})
            elif isinstance(chip, dict):
                architectures.append({"kind": "chips_hot", **chip})

    battery_archs, battery_counts = _ironclad_chips_architectures()
    prog_counts = _program_combinatronic_counts()
    seen_ids = {str(a.get("id")) for a in architectures}
    for arch in battery_archs:
        if str(arch.get("id")) in seen_ids:
            continue
        architectures.append(arch)
        seen_ids.add(str(arch.get("id")))

    return {
        "schema": "field-combinatorics-cpu-catalog/v2",
        "updated": _now(),
        "total_architectures": len(architectures),
        "guest_systems": len(guest),
        "host_cpus": len(host_cpus),
        "g16_patterns": sum(1 for a in architectures if a.get("kind") == "g16_pattern"),
        "ironclad_chips_total": battery_counts.get("total") or len(battery_archs),
        "ironclad_chips_counts": battery_counts,
        "program_combinatronic_total": prog_counts.get("commands"),
        "program_combinatronic_languages": prog_counts.get("languages"),
        "program_boil_pct": prog_counts.get("boil_pct"),
        "code_path_prediction": battery_counts.get("path_prediction") or {},
        "active_posture": posture,
        "architectures": architectures,
        "guest_systems_detail": guest,
        "motto": "Every chip ever indexed — Cyrix, CoCo, MAME, CHIPS — all combinatorics leaves.",
    }


def plate_meld_design() -> dict[str, Any]:
    """Brilliant plate meld architecture — layers, combinatorics hooks, fusion chain."""
    meld = _load(STATE / "field-plate-meld.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    layers_doc = _load(STATE / "field-compatibility-layers-panel.json", {})

    plate_sources: list[dict[str, Any]] = []
    try:
        meld_candidates = (
            INSTALL / "lib" / "field-plate-meld.py",
            Path(__file__).resolve().parent / "field-plate-meld.py",
        )
        for meld_py in meld_candidates:
            if not meld_py.is_file():
                continue
            spec = importlib.util.spec_from_file_location("field_plate_meld_comb", meld_py)
            if not spec or not spec.loader:
                continue
            mmod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mmod)
            for sid, fname in getattr(mmod, "PLATE_SOURCES", ()):
                path = STATE / fname
                combinatorics_ids = {
                    "field_combinatorics",
                    "combinatorics_bridge",
                    "ironclad_chips",
                    "truth_blocks",
                    "code_bugfinder",
                    "c2_taskbar",
                    "shell_dock",
                    "field_popcorn",
                    "field_g16_launch",
                    "field_gpu",
                    "field_audio",
                    "field_broadcaster",
                    "field_lock",
                }
                plate_sources.append({
                    "id": sid,
                    "file": fname,
                    "present": path.is_file(),
                    "bytes": path.stat().st_size if path.is_file() else 0,
                    "combinatorics": sid in combinatorics_ids,
                    "operator_surface": sid in (
                        "c2_taskbar",
                        "shell_dock",
                        "field_popcorn",
                        "field_g16_launch",
                        "field_gpu",
                        "field_audio",
                        "field_broadcaster",
                        "field_lock",
                    ),
                })
            break
    except Exception:
        plate_sources = []

    layers = []
    for layer in (layers_doc.get("layers") or []):
        layers.append({
            "id": layer.get("id"),
            "label": layer.get("label"),
            "glyph": layer.get("glyph"),
            "color": layer.get("color"),
            "live": layer.get("live"),
            "role": layer.get("role"),
        })

    comb_hook = {
        "combinatorics_panel": bool(comb),
        "tree_complete": (comb.get("tree_walk") or {}).get("tree_complete"),
        "leaves_reached": (comb.get("tree_walk") or {}).get("leaves_reached"),
        "condensed_groups": (comb.get("plate_condense") or {}).get("group_count"),
        "bridge_ok": bridge.get("ok"),
        "exec_pattern": (bridge.get("exec_posture") or {}).get("pattern_id"),
        "thermal_gate": (bridge.get("gate") or {}).get("ok"),
    }

    return {
        "schema": "field-plate-meld-design/v1",
        "updated": _now(),
        "motto": "Plate meld fuses truth → combinatorics → bridge → exec — one unbreakable chain.",
        "generation": meld.get("generation"),
        "plates_fused": meld.get("plates_fused") or meld.get("plate_count"),
        "chain_hash": (meld.get("chain_hash") or "")[:24],
        "chain": [
            {"step": "truth_blocks", "panel": "g16-truth-blocks-panel.json", "role": "Ironclad sentences"},
            {"step": "combinatorics", "panel": "g16-field-combinatorics-panel.json", "role": "Facet tree + speed cap"},
            {"step": "recombinatorics", "panel": "g16-ideal-compile.json", "role": "Ideal profile race"},
            {"step": "bridge", "panel": "field-plate-combinatorics-bridge.json", "role": "Exec posture + thermal gate"},
            {"step": "c2_taskbar", "panel": "condensed-c2_taskbar-plate.json", "role": "Start · Files · Terminal · Broadcaster · Lock"},
            {"step": "operator_surfaces", "panel": "condensed-operator_surfaces-plate.json", "role": "Dock · Popcorn · Launch · GPU · Audio · Lock"},
            {"step": "meld", "panel": "field-plate-meld.json", "role": "Flock fuse all plates"},
            {"step": "compiler_sense", "panel": "g16-compiler-sense-plate.json", "role": "Eye·Ear·Mouth ladder"},
        ],
        "compatibility_layers": layers,
        "plate_sources": plate_sources,
        "combinatorics_hook": comb_hook,
        "fusion_arc": [
            {
                "step": s["step"],
                "role": s["role"],
                "panel": s["panel"],
                "present": (STATE / s["panel"]).is_file(),
                "combinatorics_core": s["step"] in ("combinatorics", "recombinatorics", "bridge", "c2_taskbar", "operator_surfaces"),
            }
            for s in [
                {"step": "truth_blocks", "panel": "g16-truth-blocks-panel.json", "role": "Ironclad sentences"},
                {"step": "combinatorics", "panel": "g16-field-combinatorics-panel.json", "role": "Facet tree + speed cap"},
                {"step": "recombinatorics", "panel": "g16-ideal-compile.json", "role": "Ideal profile race"},
                {"step": "bridge", "panel": "field-plate-combinatorics-bridge.json", "role": "Exec posture + thermal gate"},
                {"step": "c2_taskbar", "panel": "condensed-c2_taskbar-plate.json", "role": "Start · Files · Terminal · Broadcaster · Lock"},
                {"step": "operator_surfaces", "panel": "condensed-operator_surfaces-plate.json", "role": "Dock · Popcorn · Launch · GPU · Audio · Lock"},
                {"step": "meld", "panel": "field-plate-meld.json", "role": "Flock fuse all plates"},
                {"step": "compiler_sense", "panel": "g16-compiler-sense-plate.json", "role": "Eye·Ear·Mouth ladder"},
            ]
        ],
        "field_surfaces": (bridge.get("field_surfaces") or {}),
        "design_notes": [
            "Truth collected → condense groups → walk tree to terminal leaf.",
            "Recombinatorics scores belt profiles on local bench only.",
            "Bridge picks runner/emulator/die without operator combinatorics crank.",
            "C2 taskbar quint condenses into c2_taskbar plate — Ironclad witness + BSP reuse.",
            "Operator surfaces condense into operator_surfaces plate when truths land.",
            "Meld generation must advance before secured .launch refresh.",
        ],
    }


def try_brain_speed(*, intent: str | None = None) -> dict[str, Any]:
    """Invoke Hostess7 brain routing when headroom allows a faster combinatorics path."""
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    posture = bridge.get("exec_posture") or {}
    gate = bridge.get("gate") or {}
    pattern_id = str(posture.get("pattern_id") or "")
    runner = str(posture.get("runner") or "")
    headroom = float(gate.get("thermal_headroom_pct") or 100)
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    cap = float((comb.get("speed_cap") or {}).get("native_ceiling_ops_per_sec") or 0)

    suggestion = speed_brain_suggestion(
        headroom=headroom,
        native_ops=cap,
        pattern_id=pattern_id,
        runner=runner,
    )
    primary = suggestion.get("primary_route") or {}
    use_intent = intent or {
        "broca": "code",
        "temporal": "chips",
        "limbic": "field_drive",
        "insula": "detective",
        "prefrontal": "release",
    }.get(str(primary.get("brain_area") or ""), "code")

    invoke: dict[str, Any] = {"intent": use_intent, "workspace": "bench"}
    bmod = _load_brain_module()
    if bmod:
        try:
            if hasattr(bmod, "set_active_workspace"):
                bmod.set_active_workspace("bench")
            q = f"combinatorics speed {pattern_id} {runner} native_bsp belt promote".strip()
            if hasattr(bmod, "route_query"):
                br = bmod.route_query(q, use_intent, workspace="bench")
                invoke["route"] = br._asdict() if hasattr(br, "_asdict") else {
                    "primary_area": getattr(br, "primary_area", None),
                    "workspace": getattr(br, "workspace", None),
                    "cross_transfer": getattr(br, "cross_transfer", None),
                }
            if hasattr(bmod, "format_route_line") and invoke.get("route"):
                from types import SimpleNamespace
                r = invoke["route"]
                fake = SimpleNamespace(
                    primary_area=r.get("primary_area"),
                    primary_hemisphere=r.get("primary_hemisphere", "both"),
                    workspace=r.get("workspace", "bench"),
                    cross_transfer=r.get("cross_transfer", False),
                )
                invoke["route_line"] = bmod.format_route_line(fake)
            if hasattr(bmod, "brain_status"):
                invoke["brain_status"] = bmod.brain_status()
        except Exception as exc:
            invoke["error"] = str(exc)
    else:
        invoke["error"] = "field_brain_core_missing"

    tick = record_comb_tick(
        action="brain_try",
        source="combinatorics_comb",
        extra={
            "brain_area": primary.get("brain_area"),
            "intent": use_intent,
            "can_try_faster": suggestion.get("can_try_faster"),
        },
    )
    return {
        "ok": not invoke.get("error"),
        "brain_speed": suggestion,
        "brain_invoke": invoke,
        "comb": comb_panel(latest_tick=tick.get("tick")),
        "motto": "Brain area engaged — route recorded on comb ledger for chart continuity.",
    }


def comb_charts(*, tail: int = CHART_TAIL) -> dict[str, Any]:
    """Chart-ready timeseries — how combinatorics is combing along."""
    rows = _tail_ledger(tail)
    series: dict[str, list[Any]] = {
        "ts": [],
        "elapsed_ms": [],
        "leaves_reached": [],
        "tree_complete": [],
        "native_ops_per_sec": [],
        "headroom_pct": [],
        "condensed_groups": [],
        "composite_score": [],
        "meld_generation": [],
        "pattern_id": [],
        "action": [],
    }
    pattern_counts: dict[str, int] = {}
    action_counts: dict[str, int] = {}

    for row in rows:
        series["ts"].append(row.get("ts"))
        series["elapsed_ms"].append(row.get("elapsed_ms"))
        series["leaves_reached"].append(row.get("leaves_reached"))
        series["tree_complete"].append(1 if row.get("tree_complete") else 0)
        series["native_ops_per_sec"].append(row.get("native_ops_per_sec"))
        series["headroom_pct"].append(row.get("headroom_pct"))
        series["condensed_groups"].append(row.get("condensed_groups"))
        series["composite_score"].append(row.get("composite_score"))
        series["meld_generation"].append(row.get("meld_generation"))
        series["pattern_id"].append(row.get("pattern_id"))
        series["action"].append(row.get("action"))
        pid = str(row.get("pattern_id") or "")
        if pid:
            pattern_counts[pid] = pattern_counts.get(pid, 0) + 1
        act = str(row.get("action") or "")
        if act:
            action_counts[act] = action_counts.get(act, 0) + 1

    last = rows[-1] if rows else {}
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    cap = comb.get("speed_cap") or {}

    return {
        "schema": "field-combinatorics-charts/v1",
        "updated": _now(),
        "point_count": len(rows),
        "poll_interval_sec": POLL_INTERVAL_SEC,
        "series": series,
        "pattern_frequency": sorted(
            [{"pattern_id": k, "count": v} for k, v in pattern_counts.items()],
            key=itemgetter("count"),
            reverse=True,
        ),
        "action_frequency": sorted(
            [{"action": k, "count": v} for k, v in action_counts.items()],
            key=itemgetter("count"),
            reverse=True,
        ),
        "latest": last,
        "sparkline": {
            "elapsed_ms": [x for x in series["elapsed_ms"] if x is not None][-48:],
            "native_ops_per_sec": [x for x in series["native_ops_per_sec"] if x is not None][-48:],
            "leaves_reached": [x for x in series["leaves_reached"] if x is not None][-48:],
            "headroom_pct": [x for x in series["headroom_pct"] if x is not None][-48:],
        },
        "ceiling_ops_per_sec": cap.get("native_ceiling_ops_per_sec") or cap.get("estimated_cap_ops_per_sec"),
    }


def speed_brain_suggestion(*, headroom: float, native_ops: float, pattern_id: str, runner: str) -> dict[str, Any]:
    """If we can go faster, suggest a brain area + chamber to try."""
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    cap = float((comb.get("speed_cap") or {}).get("native_ceiling_ops_per_sec") or 0)
    ratio = (native_ops / cap) if cap > 0 and native_ops > 0 else 0.0
    can_try_faster = headroom >= 25 and (ratio < 0.85 or runner == "python")

    task = "speed_up_bsp" if can_try_faster and runner != "native_bsp" else "combinatorics_cycle"
    route = _brain_route(task, pattern_id=pattern_id, runner=runner)

    alternatives: list[dict[str, Any]] = []
    if can_try_faster:
        if runner == "python":
            alternatives.append({
                "suggestion": "Switch to native_bsp / FieldX86Die",
                "brain_area": "broca",
                "chamber": "g16_unified",
                "expected_gain": "bench-native path",
            })
        if "belt_1" in pattern_id or pattern_id == "dev_organized_python":
            alternatives.append({
                "suggestion": "Promote to belt_2_0 / singular_native_bsp",
                "brain_area": "prefrontal",
                "chamber": "g16_forever",
                "expected_gain": "512 die slots",
            })
        if ratio < 0.5 and cap > 0:
            alternatives.append({
                "suggestion": "Route through temporal emulation memory + CHIPS hot path",
                "brain_area": "temporal",
                "chamber": "g16_unified",
                "expected_gain": "pattern recall",
            })

    return {
        "can_try_faster": can_try_faster,
        "headroom_pct": headroom,
        "utilization_vs_ceiling": round(ratio, 3) if ratio else None,
        "primary_route": route,
        "alternatives": alternatives,
        "plain": (
            f"Headroom {headroom:.0f}% — try **{route.get('brain_area')}** ({route.get('neural_chamber')}) "
            f"via Hostess7 brain: {route.get('why')}"
            if can_try_faster
            else f"Hold current posture ({pattern_id}/{runner}) — headroom {headroom:.0f}% or at ceiling."
        ),
    }


def record_comb_tick(
    *,
    action: str = "cycle",
    source: str = "combinatorics",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record one combinatorics progress tick for charts."""
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    meld = _load(STATE / "field-plate-meld.json", {})
    recomb = _load(STATE / "g16-ideal-compile.json", {})
    walk = comb.get("tree_walk") or {}
    terminal = walk.get("terminal_leaf") or {}
    posture = bridge.get("exec_posture") or {}
    gate = bridge.get("gate") or {}
    cap = comb.get("speed_cap") or {}
    condense = comb.get("plate_condense") or {}
    ideal = (recomb.get("candidates") or [{}])[0] if recomb.get("candidates") else {}

    row = {
        "ts": _now(),
        "action": action,
        "source": source,
        "elapsed_ms": (extra or {}).get("elapsed_ms"),
        "leaves_reached": walk.get("leaves_reached"),
        "tree_complete": walk.get("tree_complete"),
        "pattern_id": terminal.get("pattern_id") or posture.get("pattern_id"),
        "runner": terminal.get("runner") or posture.get("runner"),
        "belt_profile": terminal.get("belt_profile") or posture.get("belt_profile"),
        "die_slots": terminal.get("die_slots") or posture.get("die_slots"),
        "native_ops_per_sec": cap.get("native_ceiling_ops_per_sec") or cap.get("estimated_cap_ops_per_sec"),
        "headroom_pct": gate.get("thermal_headroom_pct"),
        "condensed_groups": condense.get("group_count"),
        "composite_score": ideal.get("composite_score"),
        "meld_generation": meld.get("generation"),
        "deferred": (extra or {}).get("deferred"),
        "rejected": (extra or {}).get("rejected"),
    }
    if extra:
        row.update({k: v for k, v in extra.items() if k not in row})
    _append_ledger(row)

    charts = comb_charts()
    panel = comb_panel(charts=charts, latest_tick=row)
    _save(PANEL, panel)
    return {"recorded": True, "tick": row, "chart_points": charts.get("point_count")}


def comb_panel(
    *,
    charts: dict[str, Any] | None = None,
    latest_tick: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full comb dashboard — charts, CPUs, meld design, brain speed."""
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    posture = bridge.get("exec_posture") or {}
    gate = bridge.get("gate") or {}
    charts = charts or comb_charts()
    native = float(charts.get("ceiling_ops_per_sec") or 0)
    headroom = float(gate.get("thermal_headroom_pct") or 100)

    doc = {
        "schema": "field-combinatorics-comb/v1",
        "updated": _now(),
        "motto": "Watch combinatorics comb along — charts, every CPU, plate meld arc, brain speed paths.",
        "poll_interval_sec": POLL_INTERVAL_SEC,
        "charts": charts,
        "cpu_catalog": cpu_architecture_catalog(),
        "plate_meld_design": plate_meld_design(),
        "brain_speed": speed_brain_suggestion(
            headroom=headroom,
            native_ops=native,
            pattern_id=str(posture.get("pattern_id") or ""),
            runner=str(posture.get("runner") or ""),
        ),
        "latest_tick": latest_tick or (charts.get("latest") or {}),
        "exec_posture": posture,
        "gate": gate,
        "field_surfaces": bridge.get("field_surfaces") or {},
    }
    return doc


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(comb_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "charts":
        print(json.dumps(comb_charts(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "cpus":
        print(json.dumps(cpu_architecture_catalog(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "meld":
        print(json.dumps(plate_meld_design(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "record":
        action = sys.argv[2] if len(sys.argv) > 2 else "manual"
        print(json.dumps(record_comb_tick(action=action, source="cli"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "brain":
        task = sys.argv[2] if len(sys.argv) > 2 else "speed"
        print(json.dumps(_brain_route(task), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("try-brain", "brain-try", "try_brain"):
        intent = sys.argv[2] if len(sys.argv) > 2 else None
        print(json.dumps(try_brain_speed(intent=intent), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "cmds": ["json", "charts", "cpus", "meld", "record", "brain", "try-brain"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())