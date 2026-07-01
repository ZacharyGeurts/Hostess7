#!/usr/bin/env pythong
"""Plate combinatorics bridge — CPU-efficient exec posture from meld + thermals + entropy."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent if INSTALL.name == "NewLatest" else INSTALL.parent)))
from sg_paths import grok16_root

GROK16 = grok16_root()
PANEL = STATE / "field-plate-combinatorics-bridge.json"


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


def _import_combinatorics() -> Any | None:
    for path in (
        GROK16 / "lib" / "field_combinatorics.py",
        INSTALL.parent.parent / "Grok16" / "lib" / "field_combinatorics.py",
    ):
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("field_combinatorics", path)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def combinatorics_panel(*, allow_stale: bool = True) -> dict[str, Any]:
    """Return combinatorics panel — mismatch rejects and records; last-good panel never breaks meld."""
    mod = _import_combinatorics()
    cached = _load(STATE / "g16-field-combinatorics-panel.json", {})
    cached_verify: dict[str, Any] = {}
    if cached and mod and hasattr(mod, "verify_combinatorics_lock"):
        cached_verify = mod.verify_combinatorics_lock(cached, state_dir=STATE)

    if mod and hasattr(mod, "read_last_good_panel"):
        last_good = mod.read_last_good_panel(state_dir=STATE)
        if last_good:
            verify = last_good.get("combinatorics_lock_verify") or (
                mod.verify_combinatorics_lock(last_good, state_dir=STATE)
                if hasattr(mod, "verify_combinatorics_lock")
                else {}
            )
            last_good["combinatorics_lock_verify"] = verify
            last_good.setdefault("ok", True)
            if cached_verify and not cached_verify.get("ok") and hasattr(mod, "reject_attempt"):
                reject = mod.reject_attempt(
                    action="combinatorics_panel",
                    reason=str(cached_verify.get("reason") or "lock_mismatch"),
                    caller="combinatorics_bridge",
                    verify=cached_verify,
                    state_dir=STATE,
                )
                last_good["rejected"] = True
                last_good["combinatorics_rejected"] = True
                last_good["reject"] = {
                    "reason": reject.get("reason") or cached_verify.get("reason"),
                    "retaliate": reject.get("retaliate"),
                    "recorded": reject.get("recorded"),
                    "using_last_good": True,
                }
                last_good["needs_rebuild"] = cached_verify.get("needs_rebuild")
                last_good["hint"] = reject.get("hint")
            return last_good
    if cached and cached_verify:
        verify = cached_verify
        if verify.get("ok"):
            cached["combinatorics_lock_verify"] = verify
            cached.setdefault("ok", True)
            return cached
        reject = (
            mod.reject_attempt(
                action="combinatorics_panel",
                reason=str(verify.get("reason") or "lock_mismatch"),
                caller="combinatorics_bridge",
                verify=verify,
                state_dir=STATE,
            )
            if hasattr(mod, "reject_attempt")
            else {}
        )
        panel = reject.get("panel") or cached
        if panel:
            panel = {
                **panel,
                "ok": True,
                "rejected": True,
                "combinatorics_rejected": True,
                "combinatorics_lock_verify": verify,
                "lock_fault": verify,
                "reject": {
                    "reason": reject.get("reason") or verify.get("reason"),
                    "retaliate": reject.get("retaliate"),
                    "recorded": reject.get("recorded"),
                    "using_last_good": reject.get("using_last_good"),
                },
                "needs_rebuild": verify.get("needs_rebuild"),
                "hint": reject.get("hint")
                or "Run compatibility full refresh or Grok16 field_combinatorics.py rebuild",
            }
            return panel

    if mod and hasattr(mod, "operator_running") and mod.operator_running(state_dir=STATE).get("running"):
        last_good = mod.read_last_good_panel(state_dir=STATE) if hasattr(mod, "read_last_good_panel") else cached
        if last_good:
            last_good.setdefault("ok", True)
            last_good["combinatorics_deferred"] = True
            last_good["hint"] = "Operator running — combinatorics held at last-good panel"
            return last_good

    if mod and hasattr(mod, "refresh_allowed"):
        allowed, reason = mod.refresh_allowed(rebuild=False, state_dir=STATE)
        if allowed and hasattr(mod, "publish_panel"):
            try:
                pub = mod.publish_panel(state_dir=STATE, light=True)
                if pub.get("ok") and not pub.get("rejected"):
                    fresh = _load(STATE / "g16-field-combinatorics-panel.json", {})
                    if fresh:
                        fresh.setdefault("ok", True)
                        return fresh
            except Exception:
                pass
        elif not allowed and hasattr(mod, "reject_attempt"):
            verify = (
                mod.verify_combinatorics_lock(state_dir=STATE)
                if hasattr(mod, "verify_combinatorics_lock")
                else {"reason": reason}
            )
            reject = mod.reject_attempt(
                action="combinatorics_panel_refresh",
                reason=reason,
                caller="combinatorics_bridge",
                verify=verify if isinstance(verify, dict) else None,
                state_dir=STATE,
            )
            panel = reject.get("panel") or cached
            if panel:
                panel.setdefault("ok", True)
                panel["rejected"] = True
                panel["combinatorics_rejected"] = True
                panel["reject"] = reject
                return panel

    cached.setdefault("ok", bool(cached))
    return cached


def _locational_sitrep() -> dict[str, Any]:
    path = INSTALL / "lib" / "field-locational-sitrep-plate.py"
    if path.is_file():
        try:
            spec = importlib.util.spec_from_file_location("fpw_sitrep", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "build_plate"):
                    return mod.build_plate(write=False, refresh_spatial=False)
        except Exception:
            pass
    return _load(STATE / "field-locational-sitrep-plate.json", {})


def _physics_witness() -> dict[str, Any]:
    path = INSTALL / "lib" / "field-physics-witness.py"
    if not path.is_file():
        return _load(STATE / "field-physics-witness.json", {})
    try:
        spec = importlib.util.spec_from_file_location("fpw_bridge", path)
        if not spec or not spec.loader:
            return _load(STATE / "field-physics-witness.json", {})
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "witness"):
            return mod.witness(sections=True)
    except Exception:
        pass
    return _load(STATE / "field-physics-witness.json", {})


def _power_sort_plate() -> dict[str, Any]:
    for path in (STATE / "g16-power-sort-plate.json", GROK16 / "data" / "g16-power-sort-panel.json"):
        doc = _load(path, {})
        if doc.get("sections") or doc.get("selection"):
            thermal = doc.get("thermal") or {}
            sections = doc.get("sections") or {}
            return {
                "ok": bool(doc.get("ok") or doc.get("plated")),
                "sections": sections,
                "thermal": thermal,
                "cool_ok": bool(thermal.get("cool_ok", not thermal.get("hot"))),
                "sections_cool": sum(1 for s in sections.values() if s.get("cool")),
                "sections_live": sum(1 for s in sections.values() if s.get("available")),
                "recombinatorics_algorithm": (doc.get("selection") or {}).get("recombinatorics_algorithm")
                or ((doc.get("selection") or {}).get("selections") or {}).get("recombinatorics", {}).get("algorithm"),
                "source": path.name,
            }
    return {"ok": False, "sections": {}, "cool_ok": True, "sections_live": 0, "source": "missing"}


def thermal_entropy_gate(*, ops: int = 1) -> dict[str, Any]:
    """Gate plate/library work on thermal headroom, field sanity, entropy discipline."""
    thermal = _load(STATE / "field-thermal-guard.json", {})
    advisory = _load(STATE / "thermal-advisory.json", {})
    sanity = _load(STATE / "ironclad-field-sanity-panel.json", {})
    voltage = _load(STATE / "field-voltage-regulation-panel.json", {})
    bus = _load(STATE / "field-unified-bus-runtime.json", {})

    headroom = float(thermal.get("headroom_pct") or 100)
    level = str(advisory.get("level") or thermal.get("level") or "ok").lower()
    allow_thermal = headroom >= 15 and level not in ("crit", "storm")
    guard = None
    try:
        tg = importlib.util.spec_from_file_location("ftg", INSTALL / "lib" / "field-thermal-guard.py")
        if tg and tg.loader:
            mod = importlib.util.module_from_spec(tg)
            tg.loader.exec_module(mod)
            guard = mod.FieldThermalGuard()
            allow_thermal = allow_thermal and guard.allow_update(max(1, ops))
    except Exception:
        pass

    sanity_ok = bool(sanity.get("operator_ok", sanity.get("ok", True)))
    never_heat = bool(sanity.get("never_build_under_heat", True))
    entropy_on_trust = bool((voltage.get("entropy_on_trust_layer") or voltage.get("policy", {}).get("entropy_on_trust_layer")))
    bus_entropy = None
    if isinstance(bus.get("thermal"), dict):
        bus_entropy = bus["thermal"].get("entropy")
    entropy_ok = not entropy_on_trust

    ok = allow_thermal and sanity_ok and entropy_ok and never_heat
    return {
        "ok": ok,
        "allow_plate_work": ok,
        "thermal_headroom_pct": headroom,
        "thermal_level": level,
        "field_sanity_ok": sanity_ok,
        "never_build_under_heat": never_heat,
        "entropy_on_trust_layer": entropy_on_trust,
        "entropy_ok": entropy_ok,
        "bus_entropy": bus_entropy,
        "ops_requested": ops,
        "doctrine": "Thermals + entropy checked before plate meld and library truth passes.",
    }


def _combinatorics_mod() -> Any | None:
    return _import_combinatorics()


def _consolidated_plate_condense(comb: dict[str, Any]) -> dict[str, Any]:
    """Prefer width×length consolidated condense when dimensions panel is live."""
    for path in (
        INSTALL / "lib" / "field-plate-dimensions.py",
        SG / "NewLatest" / "lib" / "field-plate-dimensions.py",
    ):
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("fpw_plate_dim", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "read_consolidated_condense"):
                    consolidated = mod.read_consolidated_condense()
                    if consolidated.get("groups"):
                        base = comb.get("plate_condense") or {}
                        return {**base, **consolidated, "consolidated_dimensions": True}
        except Exception:
            continue
    cached = _load(STATE / "field-plate-condense-consolidated.json", {})
    if cached.get("groups"):
        base = comb.get("plate_condense") or {}
        return {**base, **cached, "consolidated_dimensions": True}
    return comb.get("plate_condense") or {}


RETRO_PLATFORMS = frozenset({
    "nes", "snes", "genesis", "sms", "a2600", "gameboy", "gamegear", "n64", "pce",
    "neogeo", "msx", "spectrum", "c64", "apple2", "amiga", "dreamcast", "saturn",
    "3do", "jaguar", "coco", "coco2", "coco3", "ps1", "dos",
})


def _ironclad_chips_retro_hint() -> dict[str, Any] | None:
    """Top Ironclad CHIPS combinatorics leaf — prefer FieldChips for retro platforms."""
    for path in (
        INSTALL / "lib" / "field-ironclad-chips-combinatorics.py",
        SG / "NewLatest" / "lib" / "field-ironclad-chips-combinatorics.py",
    ):
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("fpw_ironclad_chips", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "combinatronic_panel"):
                    panel = mod.combinatronic_panel()
                    leaves = panel.get("leaves") or panel.get("combinatorics_leaves") or []
                    for leaf in leaves:
                        if str(leaf.get("emulator") or "") != "FieldChips":
                            continue
                        chip_id = str(leaf.get("chip_id") or leaf.get("id") or "")
                        platforms = leaf.get("platforms") or []
                        if chip_id.startswith("system_"):
                            plat = chip_id.replace("system_", "", 1)
                            if plat in RETRO_PLATFORMS:
                                return {
                                    "emulator": "FieldChips",
                                    "runner": "emulator",
                                    "launch_surface": "queen_game_room",
                                    "system": plat,
                                    "chip_id": chip_id,
                                    "source": "ironclad_chips",
                                }
                        if any(str(p) in RETRO_PLATFORMS for p in platforms):
                            plat = next((str(p) for p in platforms if str(p) in RETRO_PLATFORMS), "nes")
                            return {
                                "emulator": "FieldChips",
                                "runner": "emulator",
                                "launch_surface": "queen_game_room",
                                "system": plat,
                                "chip_id": chip_id,
                                "source": "ironclad_chips",
                            }
                    for leaf in leaves:
                        if str(leaf.get("runner") or "") == "emulator":
                            return {
                                "emulator": str(leaf.get("emulator") or "FieldChips"),
                                "runner": "emulator",
                                "launch_surface": "queen_game_room",
                                "chip_id": leaf.get("chip_id"),
                                "source": "ironclad_chips_runner",
                            }
        except Exception:
            continue
    return None


def _retro_chips_posture(terminal: dict[str, Any], pattern: dict[str, Any], comb: dict[str, Any]) -> dict[str, Any] | None:
    facets = pattern.get("facets") or {}
    chip_em = str(terminal.get("emulator") or facets.get("emulator") or "")
    runner = str(terminal.get("runner") or facets.get("runner") or "")
    facet = str(terminal.get("facet") or facets.get("facet") or "")
    chip_id = str(terminal.get("chip_id") or "")
    platforms = terminal.get("platforms") or facets.get("platforms") or []

    if chip_em == "FieldChips" or runner == "emulator":
        plat = "nes"
        if chip_id.startswith("system_"):
            plat = chip_id.replace("system_", "", 1)
        elif platforms:
            plat = str(platforms[0])
        return {
            "emulator": "FieldChips",
            "runner": "emulator",
            "launch_surface": "queen_game_room",
            "system": plat if plat in RETRO_PLATFORMS else "nes",
            "source": "terminal_leaf",
        }
    if facet in ("ironclad_chips", "chips_battery", "retro_nes") or "nes" in chip_id or "chips" in chip_id.lower():
        return {
            "emulator": "FieldChips",
            "runner": "emulator",
            "launch_surface": "queen_game_room",
            "system": "nes",
            "source": "facet",
        }
    g16u = comb.get("g16_universal") or {}
    for leaf in (g16u.get("leaves") or [])[:32]:
        if str(leaf.get("sub_facet") or "") in ("ironclad_chips", "chips_battery"):
            return {
                "emulator": "FieldChips",
                "runner": "emulator",
                "launch_surface": "queen_game_room",
                "system": "nes",
                "source": "g16_universal",
            }
    return _ironclad_chips_retro_hint()


def _tree_terminal(
    *,
    comb: dict[str, Any],
    truth_blocks: dict[str, Any],
    gate: dict[str, Any],
    free_meld: bool,
) -> dict[str, Any]:
    walk = comb.get("tree_walk") or {}
    if walk.get("terminal_leaf"):
        return walk["terminal_leaf"]
    mod = _combinatorics_mod()
    if mod and hasattr(mod, "walk_tree_to_end"):
        try:
            walk = mod.walk_tree_to_end(
                truth_panel=truth_blocks,
                gate_ok=bool(gate.get("ok")),
                free_meld=free_meld,
            )
            return walk.get("terminal_leaf") or {}
        except Exception:
            pass
    return {}


def select_exec_posture(
    *,
    free_meld: bool = False,
    combinatorics: dict[str, Any] | None = None,
    gate: dict[str, Any] | None = None,
    truth_blocks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Pick CPU-efficient runner + emulator die from combinatoric tree terminal leaf."""
    comb = combinatorics or combinatorics_panel()
    g = gate or thermal_entropy_gate(ops=4)
    patterns = comb.get("common_usage") or []
    tb = truth_blocks if truth_blocks is not None else _load(STATE / "g16-truth-blocks-panel.json", {})
    fm = free_meld or bool(tb.get("free_meld"))
    terminal = _tree_terminal(comb=comb, truth_blocks=tb, gate=g, free_meld=fm)

    chosen_id = str(terminal.get("pattern_id") or "")
    if not chosen_id:
        chosen_id = "dev_organized_iron_exec" if fm and g.get("ok") else "dev_organized_python"
        if g.get("ok") and not fm and (comb.get("speed_cap") or {}).get("estimated_cap_ops_per_sec"):
            chosen_id = "singular_native_bsp"

    pattern = next((p for p in patterns if p.get("id") == chosen_id), patterns[0] if patterns else {})
    kernel = comb.get("kernel_default") or {}
    profile = str(
        terminal.get("belt_profile")
        or (pattern.get("facets") or {}).get("profile")
        or kernel.get("profile")
        or "belt_1_0"
    )
    die_slots = int(
        terminal.get("die_slots")
        or (pattern.get("facets") or {}).get("die")
        or kernel.get("die_slots")
        or 256
    )
    runner = str(
        terminal.get("runner")
        or (pattern.get("facets") or {}).get("runner")
        or ("native_bsp" if fm else "python")
    )

    retro = _retro_chips_posture(terminal, pattern, comb)
    if retro:
        runner = str(retro.get("runner") or "emulator")
        emulator = str(retro.get("emulator") or "FieldChips")
    else:
        emulator = str(terminal.get("emulator") or "FieldX86Die")
        if runner == "python" and not fm:
            emulator = "FieldX86Emu"
        elif runner in ("native_bsp", "iron_exec"):
            emulator = "FieldX86Die"

    condense = comb.get("plate_condense") or {}
    larger_plate = bool(condense.get("condensed")) and die_slots < 512 and fm
    if larger_plate and profile == "belt_1_0":
        profile = "belt_2_0"
        die_slots = 512

    recomb = comb.get("recombinatorics") or _load(STATE / "g16-ideal-compile.json", {})
    ideal_profile = str(recomb.get("ideal_profile") or "")
    ideal_map = {
        "belt_2_0": ("belt_2_0", 512),
        "expert": ("belt_2_0", 512),
        "heavy": ("belt_2_0", 512),
        "forever": ("belt_2_0", 512),
        "belt_1_0": ("belt_1_0", 256),
        "field_opt": ("belt_1_0", 256),
    }
    if ideal_profile in ideal_map:
        iprof, islots = ideal_map[ideal_profile]
        if iprof == "belt_2_0" or profile != "belt_2_0":
            profile = iprof
            die_slots = islots

    power_sort = _power_sort_plate()
    thermal_cool = float(g.get("thermal_headroom_pct") or 100) >= 15 and str(
        g.get("thermal_level") or "ok"
    ).lower() not in ("crit", "storm")
    sections = power_sort.get("sections") or {}
    sections_cool = all(
        s.get("cool", True) for s in sections.values() if s.get("available", True)
    ) if sections else True
    runs_cool = thermal_cool and bool(power_sort.get("cool_ok", True)) and sections_cool
    recomb_section = sections.get("recombinatorics") or {}
    if recomb_section.get("available") is False:
        runs_cool = False
    if not runs_cool:
        if runner in ("native_bsp", "iron_exec"):
            runner = "python"
            emulator = "FieldX86Emu"
        if profile == "belt_2_0" and not fm:
            profile = "belt_1_0"
            die_slots = min(die_slots, 256)

    launch_surface = retro.get("launch_surface") if retro else None
    launch_system = retro.get("system") if retro else None

    return {
        "pattern_id": pattern.get("id", chosen_id),
        "label": pattern.get("label", ""),
        "runner": runner,
        "emulator": emulator,
        "launch_surface": launch_surface,
        "launch_system": launch_system,
        "retro_chips": bool(retro),
        "retro_source": (retro or {}).get("source"),
        "free_meld": fm,
        "belt_profile": profile,
        "die_slots": die_slots,
        "ideal_profile": ideal_profile or profile,
        "wave_bands": int(kernel.get("wave_bands") or 16),
        "native_ceiling_ops_per_sec": (comb.get("speed_cap") or {}).get("estimated_cap_ops_per_sec"),
        "headroom_ratio": terminal.get("headroom_ratio") or pattern.get("headroom_ratio"),
        "optimize": pattern.get("optimize", ""),
        "full_emulator_via_meld": True,
        "gate_ok": g.get("ok"),
        "iron_exec_recommended": runner in ("native_bsp", "iron_exec") or fm,
        "queen_launch_iron_exec": fm and g.get("ok"),
        "tree_terminal": terminal,
        "truth_tier": terminal.get("truth_tier"),
        "larger_plate": larger_plate,
        "runs_cool": runs_cool,
        "power_sort_cool_ok": power_sort.get("cool_ok"),
        "power_sort_sections_live": power_sort.get("sections_live"),
    }


def _surface_posture(surface: dict[str, Any], panel_doc: dict[str, Any]) -> dict[str, Any]:
    sid = str(surface.get("id") or "")
    ok = bool(panel_doc.get("ok")) and not panel_doc.get("missing")
    row: dict[str, Any] = {
        "id": sid,
        "label": surface.get("label"),
        "plate_key": surface.get("plate_key"),
        "panel": surface.get("panel"),
        "route": surface.get("route") or surface.get("exec"),
        "exec": surface.get("exec"),
        "combinatorics_role": surface.get("combinatorics_role"),
        "ok": ok,
        "posture": panel_doc.get("posture") or panel_doc.get("title"),
    }
    if sid == "shell_dock":
        row["sovereign_synced"] = (panel_doc.get("sovereign") or {}).get("all_synced")
        row["session_drift_ns"] = (panel_doc.get("session") or {}).get("drift_since_session_ns")
        row["dock_icons"] = len(panel_doc.get("dock_icons") or [])
    elif sid == "field_popcorn":
        lib = panel_doc.get("library") or {}
        row["media_count"] = lib.get("count", 0)
        row["by_kind"] = lib.get("by_kind") or {}
        insp = panel_doc.get("inspector") or {}
        row["inspector_cached"] = (insp.get("summary") or {}).get("cached")
        row["ai_generated_count"] = (insp.get("summary") or {}).get("ai_generated_count")
    elif sid == "field_ellie_fier":
        sw = panel_doc.get("systemwide") or {}
        row["ellie_verdict"] = sw.get("verdict")
        row["ellie_score"] = sw.get("score")
        row["ironclad_sealed"] = sw.get("ironclad_sealed")
        row["flagged_count"] = len((sw.get("media_scan") or {}).get("flagged") or [])
    elif sid == "field_g16_launch":
        row["launch_count"] = (panel_doc.get("index") or {}).get("count", 0)
        row["g16_ready"] = (panel_doc.get("g16") or {}).get("ok")
        row["uncompiled"] = True
    elif sid == "field_gpu":
        row["gpu_count"] = panel_doc.get("detected_count", len(panel_doc.get("gpus") or []))
        row["active_gpu"] = (panel_doc.get("active_gpu") or {}).get("name")
    elif sid == "field_audio":
        row["backend"] = panel_doc.get("backend")
        row["sink_count"] = panel_doc.get("sink_count", 0)
    elif sid in ("field_broadcaster", "field_obs"):
        row["scenes"] = panel_doc.get("scenes") or len((panel_doc.get("engine") or {}).get("filters") or [])
        row["streaming"] = panel_doc.get("streaming")
        row["audio_chain"] = bool((panel_doc.get("audio") or {}).get("chain"))
    elif sid == "c2_taskbar":
        row["quint_live"] = panel_doc.get("quint_live")
        row["quint_total"] = panel_doc.get("quint_total")
        row["quint"] = panel_doc.get("quint") or []
        row["bsp_hit"] = bool((panel_doc.get("bsp") or {}).get("bsp_hit"))
        row["bsp_case_id"] = (panel_doc.get("bsp") or {}).get("case_id")
        row["ironclad_cite"] = (panel_doc.get("ironclad") or {}).get("meld_citation")
        row["condense_group"] = panel_doc.get("condense_group") or "c2_taskbar"
    elif sid == "field_lock":
        row["product"] = panel_doc.get("product") or "Lock"
        row["vault_ready"] = panel_doc.get("vault_ready")
        row["db_present"] = panel_doc.get("db_present")
    return row


def field_surface_slices(*, combinatorics: dict[str, Any] | None = None) -> dict[str, Any]:
    """Operator goodies — dock, popcorn, launch, GPU, audio, OBS — for bridge + combinatorics condense."""
    doctrine = _load(INSTALL / "data" / "field-field-surfaces-doctrine.json", {})
    surfaces_cfg = doctrine.get("surfaces") or []
    condense_group = str(doctrine.get("condense_group") or "operator_surfaces")
    comb = combinatorics or combinatorics_panel()
    condense = comb.get("plate_condense") or {}
    group_row = next(
        (g for g in (condense.get("groups") or []) if g.get("group") == condense_group),
        None,
    )
    c2_group_row = next(
        (g for g in (condense.get("groups") or []) if g.get("group") == "c2_taskbar"),
        None,
    )

    rows: list[dict[str, Any]] = []
    live = 0
    for surface in surfaces_cfg:
        panel_name = str(surface.get("panel") or "")
        panel_doc = _load(STATE / panel_name, {"missing": True}) if panel_name else {"missing": True}
        row = _surface_posture(surface, panel_doc)
        if row.get("ok"):
            live += 1
        rows.append(row)

    condensed = bool(group_row and group_row.get("condensed"))
    c2_condensed = bool(c2_group_row and c2_group_row.get("condensed"))
    c2_row = next((r for r in rows if r.get("id") == "c2_taskbar"), None)
    return {
        "schema": "field-surfaces-slice/v1",
        "updated": _now(),
        "ok": live > 0,
        "live_count": live,
        "total_count": len(rows),
        "condense_group": condense_group,
        "condensed": condensed,
        "condense_present": (group_row or {}).get("present"),
        "condense_total": (group_row or {}).get("total"),
        "c2_taskbar_condensed": c2_condensed,
        "c2_taskbar_condense_present": (c2_group_row or {}).get("present"),
        "c2_taskbar_condense_total": (c2_group_row or {}).get("total"),
        "c2_quint_live": (c2_row or {}).get("quint_live"),
        "c2_bsp_hit": (c2_row or {}).get("bsp_hit"),
        "surfaces": rows,
        "motto": doctrine.get("motto") or "Operator surfaces plated into meld and combinatorics condense.",
    }


def build_bridge(*, write: bool = True) -> dict[str, Any]:
    gate = thermal_entropy_gate(ops=6)
    comb = combinatorics_panel()
    truth_blocks = _load(STATE / "g16-truth-blocks-panel.json", {})
    tree_walk = comb.get("tree_walk") or {}
    plate_condense = _consolidated_plate_condense(comb)
    posture = select_exec_posture(
        free_meld=bool(truth_blocks.get("free_meld")),
        combinatorics=comb,
        gate=gate,
        truth_blocks=truth_blocks,
    )
    g16_sense = _load(STATE / "g16-compiler-sense-plate.json", {})
    power_sort = _power_sort_plate()
    physics = _physics_witness()
    sitrep = _locational_sitrep()
    cmod = _combinatorics_mod()
    lock_verify = comb.get("combinatorics_lock_verify") or (
        cmod.verify_combinatorics_lock(comb)
        if comb and cmod and hasattr(cmod, "verify_combinatorics_lock")
        else {}
    )
    comb_rejected = bool(comb.get("rejected") or comb.get("combinatorics_rejected"))
    threat = _load(STATE / "field-combinatorics-threat-panel.json", {})
    sense_universal: dict[str, Any] = {}
    for path in (
        INSTALL / "lib" / "field-sense-package-meld.py",
        SG / "NewLatest" / "lib" / "field-sense-package-meld.py",
    ):
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("fpw_sense_universal", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "sense_universal_slice"):
                    sense_universal = mod.sense_universal_slice(state_dir=STATE)
                    break
        except Exception:
            continue
    if not sense_universal:
        sense_universal = comb.get("sense_universal") or {}
    program_combinatronic: dict[str, Any] = comb.get("program_combinatronic") or {}
    for path in (
        INSTALL / "lib" / "field-program-combinatronic.py",
        SG / "NewLatest" / "lib" / "field-program-combinatronic.py",
    ):
        if program_combinatronic.get("leaf_count"):
            break
        if not path.is_file():
            continue
        try:
            spec = importlib.util.spec_from_file_location("fpw_program_combinatronic", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "program_combinatronic_slice"):
                    program_combinatronic = mod.program_combinatronic_slice(state_dir=STATE)
                    break
        except Exception:
            continue
    field_surfaces = field_surface_slices(combinatorics=comb)
    surface_rows = field_surfaces.get("surfaces") or []
    c2_surface = next((r for r in surface_rows if r.get("id") == "c2_taskbar"), None)
    organize = _load(STATE / "iron-plate-organize-panel.json", {})
    chain = organize.get("ironclad_chain") or {}
    field_surfaces["exec_hook"] = {
        "queen_launch_iron_exec": posture.get("queen_launch_iron_exec"),
        "emulator_launch": {
            "surface": posture.get("launch_surface") or (
                "queen_game_room" if posture.get("emulator") == "FieldChips" else None
            ),
            "api": "/api/game-room",
            "action": "launch",
            "system": posture.get("launch_system"),
            "spawn_rtx": posture.get("emulator") == "FieldChips",
        } if posture.get("emulator") == "FieldChips" else None,
        "uncompiled_launch": any(
            r.get("id") == "field_g16_launch" and r.get("ok") for r in surface_rows
        ),
        "media_theatre": any(
            r.get("id") == "field_popcorn" and r.get("ok") for r in surface_rows
        ),
        "c2_taskbar_quint": bool(c2_surface and c2_surface.get("ok")),
        "c2_quint_live": (c2_surface or {}).get("quint_live"),
        "c2_bsp_hit": (c2_surface or {}).get("bsp_hit") or field_surfaces.get("c2_bsp_hit"),
        "c2_taskbar_condensed": field_surfaces.get("c2_taskbar_condensed"),
        "browser_in_c2": bool(chain.get("browser_in_c2")),
        "organize_gain": organize.get("organize_gain"),
        "replate_recommended": organize.get("replate_recommended"),
        "ironclad_chain_live": chain.get("connections_live"),
    }
    doc = {
        "schema": "field-plate-combinatorics-bridge/v2",
        "updated": _now(),
        "ok": bool(gate.get("ok")) and bool(comb),
        "combinatorics_ok": lock_verify.get("ok", True) and not comb_rejected,
        "combinatorics_rejected": comb_rejected,
        "combinatorics_lock": comb.get("combinatorics_lock"),
        "combinatorics_lock_verify": lock_verify,
        "combinatorics_threat": threat if threat else None,
        "combinatorics_reject": comb.get("reject"),
        "motto": "Truth-collected condensing — combinatoric tree walked to terminal leaf; larger plates when gated.",
        "gate": gate,
        "combinatorics_cardinality": (comb.get("combinatoric_space") or {}).get("cardinality_estimate"),
        "combinatoric_tree_complete": bool(tree_walk.get("tree_complete")),
        "tree_leaves_reached": tree_walk.get("leaves_reached"),
        "plate_condense": plate_condense,
        "condensed_group_count": plate_condense.get("group_count"),
        "library_clear_sentences": truth_blocks.get("library_clear_sentences"),
        "exec_posture": posture,
        "runs_cool": posture.get("runs_cool"),
        "power_sort": power_sort,
        "power_sort_sections": power_sort.get("sections") or {},
        "physics_witness": physics,
        "we_all_know": physics.get("we_all_know") or {"thermals": True, "entropy": True, "isotope": True},
        "locational_sitrep": sitrep,
        "field_surfaces": field_surfaces,
        "field_surfaces_live": field_surfaces.get("live_count"),
        "operator_surfaces_condensed": field_surfaces.get("condensed"),
        "c2_taskbar_condensed": field_surfaces.get("c2_taskbar_condensed"),
        "c2_quint_live": field_surfaces.get("c2_quint_live"),
        "c2_bsp_hit": field_surfaces.get("c2_bsp_hit"),
        "sitrep_summary": sitrep.get("summary"),
        "this_one": sitrep.get("this_one"),
        "movement": sitrep.get("movement"),
        "compiler_sense_profile": g16_sense.get("effective_profile"),
        "sense_universal": sense_universal,
        "sense_universal_lock": bool(sense_universal.get("universal_lock")),
        "sense_universal_leaves": sense_universal.get("leaf_count"),
        "program_combinatronic": program_combinatronic,
        "program_boil_pct": program_combinatronic.get("boil_pct"),
        "program_boil_complete": bool(program_combinatronic.get("boil_complete")),
        "program_combinatronic_leaves": program_combinatronic.get("leaf_count"),
        "g16_universal": comb.get("g16_universal") or {},
        "g16_universal_leaves": (comb.get("g16_universal") or {}).get("leaf_count"),
        "emulator_stack": {
            "primary": posture.get("emulator"),
            "die_slots": posture.get("die_slots"),
            "belt": posture.get("belt_profile"),
            "runner": posture.get("runner"),
            "free_with_plate_melds": posture.get("free_meld"),
            "larger_plate": posture.get("larger_plate"),
        },
        "doctrine": (
            "Plate meld + truth blocks + library clear sentences → condense groups into larger plates. "
            "Combinatoric tree walked to end; terminal leaf picks runner/emulator/die. "
            "FieldChips + queen_game_room for retro CHIPS leaves; FieldX86Die default otherwise."
        ),
    }
    if write:
        _save(PANEL, doc)
    return doc


def gate_meld_refresh() -> dict[str, Any]:
    """Called at meld entry — block refresh storm when hot or entropic."""
    gate = thermal_entropy_gate(ops=8)
    if not gate.get("ok"):
        return {**gate, "meld_refresh_allowed": False, "reason": "thermal_entropy_gate"}
    return {**gate, "meld_refresh_allowed": True}


def meld_summary_extensions(
    *,
    combinatorics: dict[str, Any] | None = None,
    truth_blocks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    bridge = build_bridge(write=True)
    p = bridge.get("exec_posture") or {}
    return {
        "exec_pattern": p.get("pattern_id"),
        "exec_runner": p.get("runner"),
        "exec_emulator": p.get("emulator"),
        "exec_die_slots": p.get("die_slots"),
        "exec_belt_profile": p.get("belt_profile"),
        "exec_iron_exec": p.get("iron_exec_recommended"),
        "exec_larger_plate": p.get("larger_plate"),
        "thermal_entropy_ok": (bridge.get("gate") or {}).get("ok"),
        "combinatorics_bridge_ok": bridge.get("ok"),
        "combinatoric_tree_complete": bridge.get("combinatoric_tree_complete"),
        "condensed_group_count": bridge.get("condensed_group_count"),
        "library_clear_sentences": bridge.get("library_clear_sentences"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_bridge(write=False), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "cycle", "refresh"):
        print(json.dumps(build_bridge(write=True), ensure_ascii=False, indent=2))
        return 0
    if cmd == "gate":
        print(json.dumps(gate_meld_refresh(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "posture":
        print(json.dumps(select_exec_posture(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-plate-combinatorics-bridge.py [json|build|gate|posture]"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())