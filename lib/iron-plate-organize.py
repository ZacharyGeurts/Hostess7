#!/usr/bin/env pythong
"""Iron Plate organize — fuse Simple Iron Plate with BSP power sort and proven organize tools."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "iron-plate-organize-doctrine.json"
PANEL = STATE / "iron-plate-organize-panel.json"
RUNTIME = STATE / "iron-plate-organize-runtime.json"
ENABLED = os.environ.get("NEXUS_IRON_PLATE_ORGANIZE", "1") == "1"
LOW_POWER = os.environ.get("NEXUS_PLATE_SPOT_LOW_POWER", "1") == "1"


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        _p = INSTALL / "lib" / "sovereign-clock.py"
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
    pio_path = INSTALL / "lib" / "plate-sealed-io.py"
    if pio_path.is_file():
        import importlib.util
        spec = importlib.util.spec_from_file_location("plate_sealed_io_ipo", pio_path)
        if spec and spec.loader:
            pio = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pio)
            if hasattr(pio, "sealed_write_json"):
                pio.sealed_write_json(path, doc)
                return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _thermal_gate(*, ops: int = 2) -> dict[str, Any]:
    spot_py = INSTALL / "lib" / "iron-plate-spot-detector.py"
    mod = _import_py(spot_py, "iron_spot_gate") if spot_py.is_file() else None
    if mod and hasattr(mod, "thermal_gate"):
        try:
            return mod.thermal_gate(ops=ops)
        except Exception:
            pass
    bridge = INSTALL / "lib" / "field-plate-combinatorics-bridge.py"
    mod = _import_py(bridge, "comb_organize_gate")
    if mod and hasattr(mod, "thermal_entropy_gate"):
        try:
            return mod.thermal_entropy_gate(ops=max(1, ops if not LOW_POWER else min(ops, 2)))
        except Exception:
            pass
    return {"ok": True, "skipped": "no_gate", "low_power": LOW_POWER}


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


def _power_sort_mod() -> Any | None:
    for path in (GROK16 / "lib" / "field-power-sort.py", INSTALL / "Grok16" / "lib" / "field-power-sort.py"):
        mod = _import_py(path, "field_power_sort_organize")
        if mod:
            return mod
    return None


def _composite_bsp_sort(
    rows: list[dict[str, Any]],
    *,
    key: str = "priority",
    reverse: bool = True,
) -> list[dict[str, Any]]:
    """BSP median-partition sort — composite_bsp organize path."""
    if len(rows) <= 1:
        return list(rows)

    def score(row: dict[str, Any], idx: int) -> float:
        raw = row.get(key)
        if raw is None:
            raw = row.get("weight")
        if raw is None:
            raw = row.get("composite_score")
        if raw is None:
            raw = len(rows) - idx
        return float(raw)

    scored = [(score(r, i), r) for i, r in enumerate(rows)]
    scored.sort(key=lambda t: t[0], reverse=reverse)
    mid = len(scored) // 2
    left = _composite_bsp_sort([r for _, r in scored[:mid]], key=key, reverse=reverse)
    right = _composite_bsp_sort([r for _, r in scored[mid:]], key=key, reverse=reverse)
    return left + right


def _sort_rows(
    rows: list[dict[str, Any]],
    *,
    context: str,
    algorithm: str | None = None,
    n: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply power-sort or composite_bsp to organizational rows."""
    mod = _power_sort_mod()
    pick: dict[str, Any] = {}
    alg = algorithm or ""
    if mod and hasattr(mod, "select_sort"):
        try:
            pick = mod.select_sort(context, n=n or len(rows))
            alg = str(pick.get("algorithm") or alg or "dirs_first")
        except Exception:
            alg = alg or "dirs_first"
    elif context == "recombinatorics":
        alg = "composite_bsp"
    else:
        alg = alg or "dirs_first"

    acc = _import_py(INSTALL / "lib" / "ironclad-access.py", "iron_organize_acc")
    if acc and hasattr(acc, "sort_rows"):
        try:
            out, meta = acc.sort_rows(rows, context=context, n=n or len(rows))
            return out, meta
        except Exception:
            pass
    if alg == "composite_bsp":
        out = _composite_bsp_sort(rows)
        meta = {"algorithm": alg, "context": context, "power_sort": pick or None, "bsp_partitions": True}
        return out, meta

    if mod and hasattr(mod, "apply_sort") and rows and isinstance(rows[0], dict) and "name" in rows[0]:
        try:
            out = mod.apply_sort(rows, context=context, n=n or len(rows))
            return out, {"algorithm": alg, "context": context, "power_sort": pick}
        except Exception:
            pass

    if alg == "cool_sort":
        out = sorted(rows, key=lambda r: float(r.get("thermo_proxy") or r.get("priority") or 0))
        return out, {"algorithm": alg, "context": context, "power_sort": pick}

    out = sorted(rows, key=lambda r: str(r.get("name") or r.get("id") or r.get("title") or "").lower())
    return out, {"algorithm": alg or "dirs_first", "context": context, "power_sort": pick}


def _power_sort_plate() -> dict[str, Any]:
    for path in (STATE / "g16-power-sort-plate.json", GROK16 / "data" / "g16-power-sort-panel.json"):
        doc = _load(path, {})
        if doc.get("sections") or doc.get("selection"):
            sel = doc.get("selection") or {}
            return {
                "ok": bool(doc.get("ok") or doc.get("plated")),
                "recombinatorics_algorithm": sel.get("recombinatorics_algorithm")
                or (sel.get("selections") or {}).get("recombinatorics", {}).get("algorithm")
                or "composite_bsp",
                "file_list_mode": sel.get("file_list_mode") or "dirs_first",
                "sections": doc.get("sections") or {},
                "source": path.name,
            }
    return {"ok": False, "recombinatorics_algorithm": "composite_bsp", "sections": {}, "source": "missing"}


def _c2_bsp() -> dict[str, Any]:
    mod = _import_py(INSTALL / "lib" / "field-c2-taskbar-plate.py", "c2_taskbar_bsp")
    if mod and hasattr(mod, "_bsp_stage"):
        try:
            return mod._bsp_stage()
        except Exception:
            pass
    cached = _load(STATE / "field-c2-taskbar-panel.json", {})
    return cached.get("bsp") or {"ok": False, "skipped": "c2_taskbar_missing"}


def _combinatorics_bridge() -> dict[str, Any]:
    cached = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    if cached.get("ok") is not None or cached.get("exec_posture"):
        return cached
    if LOW_POWER:
        return cached
    mod = _import_py(INSTALL / "lib" / "field-plate-combinatorics-bridge.py", "comb_bridge_organize")
    if mod and hasattr(mod, "build_bridge"):
        try:
            return mod.build_bridge(write=False)
        except Exception:
            pass
    return cached


def _ironclad_immediate() -> dict[str, Any]:
    cached = _load(STATE / "ironclad-immediate.json", {})
    if cached.get("schema"):
        if LOW_POWER:
            return cached
    if not LOW_POWER:
        mod = _import_py(INSTALL / "lib" / "ironclad-immediate.py", "ironclad_immediate_organize")
        if mod and hasattr(mod, "immediate_slice"):
            try:
                return mod.immediate_slice()
            except Exception:
                pass
    return cached if cached.get("schema") else {}


def _ironclad_chain_tree(
    *,
    bridge: dict[str, Any],
    bsp: dict[str, Any],
    power: dict[str, Any],
    iron: dict[str, Any],
) -> dict[str, Any]:
    """Replate Ironclad → organize → combinatorics → C2 — extension through equation."""
    doctrine = _load(DOCTRINE, {})
    chain_doc = doctrine.get("ironclad_chain") or {}
    imm = _ironclad_immediate()
    pts = imm.get("plate_to_sense") or {}
    truth = float(imm.get("truth_percent") or pts.get("truth_percent") or 0)
    grounded = bool(imm.get("ironclad_sealed") or pts.get("ironclad_grounded"))
    bridge_ok = bool(bridge.get("ok"))
    plate_condense = bridge.get("plate_condense") or {}
    condense_n = int(
        bridge.get("condensed_group_count")
        or plate_condense.get("meta_plate_count")
        or len(plate_condense.get("groups") or [])
    )
    travel_reduction = float(plate_condense.get("travel_reduction_pct") or 0) / 100.0
    bsp_hit = bool(bsp.get("bsp_hit") or bsp.get("ok"))
    alg = str(power.get("recombinatorics_algorithm") or "composite_bsp")
    bsp_weight = 1.0 if alg == "composite_bsp" and bsp_hit else 0.72 if bsp_hit else 0.5
    bridge_weight = min(1.0, 0.35 + condense_n * 0.08 + travel_reduction * 0.12) if bridge_ok else 0.25
    truth_norm = max(0.0, min(1.0, truth / 100.0))
    organize_gain = round(truth_norm * bsp_weight * bridge_weight, 4)
    connections = []
    for node in chain_doc.get("tree") or []:
        nid = str(node.get("id") or "")
        live = False
        mod_path = str(node.get("module") or "")
        if mod_path.startswith("Grok16/"):
            live = (GROK16 / mod_path.replace("Grok16/", "", 1)).is_file()
        elif mod_path:
            live = (INSTALL / mod_path).is_file()
        elif nid == "browser_display":
            live = bool(doctrine.get("sort_contexts"))
        if nid == "ironclad":
            live = live or bool(imm.get("schema"))
        if nid == "iron_plate":
            live = live or bool(iron.get("connection_count") or iron.get("ok"))
        if nid == "combinatorics_bridge":
            live = bridge_ok
        if nid == "c2_taskbar":
            live = bsp_hit
        connections.append({**node, "live": live})
    replate_raw = organize_gain >= 0.42 and grounded and bridge_ok and bsp_hit
    replate_gate: dict[str, Any] = {"replate_recommended": replate_raw, "replate_held": False}
    uw = _import_py(INSTALL / "lib" / "hostess7-userwatch.py", "iron_uw")
    if uw and hasattr(uw, "gate_replate"):
        try:
            replate_gate = uw.gate_replate(replate_raw)
        except Exception:
            replate_gate = {"replate_recommended": replate_raw, "replate_held": False}
    replate = bool(replate_gate.get("replate_recommended"))
    return {
        "schema": "ironclad-organize-chain/v1",
        "citation": chain_doc.get("citation") or "ironclad:neural:2",
        "equation": chain_doc.get("equation"),
        "ironclad_grounded": grounded,
        "truth_percent": truth,
        "recombinatorics_algorithm": alg,
        "composite_bsp_weight": bsp_weight,
        "bridge_condense": bridge_weight,
        "plate_dimensions": plate_condense.get("dimensions"),
        "travel_reduction_pct": plate_condense.get("travel_reduction_pct"),
        "meta_plate_count": plate_condense.get("meta_plate_count"),
        "organize_gain": organize_gain,
        "replate_recommended": replate,
        "replate_raw": replate_raw,
        "replate_held": bool(replate_gate.get("replate_held")),
        "replate_hold_reason": replate_gate.get("hold_reason"),
        "userwatch_zones": replate_gate.get("work_zones") or [],
        "connections": connections,
        "connections_live": sum(1 for c in connections if c.get("live")),
        "browser_in_c2": any(c.get("id") == "browser_display" for c in connections),
        "posture": (
            f"Ironclad chain · gain {organize_gain:.2f} · "
            f"{'replate held' if replate_gate.get('replate_held') else ('replate' if replate else 'hold')} · "
            f"{sum(1 for c in connections if c.get('live'))} nodes live"
        ),
    }


def _h7_organize_status() -> dict[str, Any]:
    lib_panel = _load(STATE / "hostess7-library-panel.json", {})
    bridge = _import_py(INSTALL / "lib" / "h7-library-bridge.py", "h7_lib_organize")
    available = bridge is not None
    return {
        "ok": available or bool(lib_panel),
        "library_panel": bool(lib_panel),
        "organize_command": "./Hostess7.sh library-organize",
        "dewey_profiles": bool(lib_panel.get("shelves") or lib_panel.get("library_profile")),
        "module": "h7-library-bridge.py",
    }


def _iron_plate_snapshot() -> dict[str, Any]:
    meld = _load(STATE / "field-plate-meld.json", {})
    snaps = meld.get("snapshots") if isinstance(meld.get("snapshots"), dict) else {}
    return snaps.get("iron_plate") or _load(STATE / "field-operator-iron-plate.json", {})


def organize_categories(
    categories: dict[str, list[dict[str, Any]]],
    *,
    category_order: list[str] | None = None,
) -> tuple[list[str], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """BSP-sort category keys; power-sort apps within each category."""
    doctrine = _load(DOCTRINE, {})
    ctx_meta = (doctrine.get("sort_contexts") or {}).get("start_menu_categories") or {}
    pri_map = {cat: float(len(category_order or []) - i) for i, cat in enumerate(category_order or [])}
    cat_rows = [{"id": k, "name": k, "priority": pri_map.get(k, 0)} for k in categories]
    ordered_keys, cat_sort_meta = _sort_rows(cat_rows, context=str(ctx_meta.get("context") or "recombinatorics"))
    ordered_cat_names = [str(r.get("id") or r.get("name")) for r in ordered_keys]
    for k in sorted(categories.keys()):
        if k not in ordered_cat_names:
            ordered_cat_names.append(k)

    out_cats: dict[str, list[dict[str, Any]]] = {}
    app_ctx = (doctrine.get("sort_contexts") or {}).get("start_menu_apps") or {}
    for cat in ordered_cat_names:
        apps = list(categories.get(cat) or [])
        app_rows = [{"name": a.get("name"), "kind": "dir" if a.get("pinned") else "file", **a} for a in apps]
        sorted_apps, _ = _sort_rows(app_rows, context=str(app_ctx.get("context") or "file_list"))
        out_cats[cat] = sorted_apps

    return ordered_cat_names, out_cats, {"categories": cat_sort_meta, "apps_context": app_ctx.get("context")}


def organize_tray_icons(icons: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = [{"name": i.get("name") or i.get("id"), **i} for i in icons]
    return _sort_rows(rows, context="file_list")


def organize_format_table(formats: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Ironclad format table — field_unique_best, one best sort ever."""
    if formats is None:
        mod = _import_py(INSTALL / "lib" / "field-file-formats.py", "fmt_organize")
        if mod and hasattr(mod, "build_table"):
            try:
                table = mod.build_table()
                formats = list(table.get("formats") or [])
            except Exception:
                formats = []
        else:
            formats = []
    best = _import_py(INSTALL / "lib" / "field-best-sort.py", "best_sort_organize")
    if best and hasattr(best, "apply_best"):
        try:
            return best.apply_best(formats, context="format_table")
        except Exception:
            pass
    return _sort_rows(
        [{"name": f.get("label") or f.get("id"), **f} for f in formats],
        context="format_table",
        algorithm="family_then_label",
    )


def organize_condense_groups(bridge: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    condense = bridge.get("plate_condense") or {}
    groups = list(condense.get("groups") or [])
    rows = [
        {
            "id": g.get("group"),
            "name": g.get("group"),
            "priority": float(g.get("present") or 0),
            "condensed": g.get("condensed"),
            "total": g.get("total"),
        }
        for g in groups
    ]
    return _sort_rows(rows, context="recombinatorics", algorithm="composite_bsp")


def apply_to_desktop(
    *,
    menu: dict[str, Any],
    tray_icons: list[dict[str, Any]] | None = None,
    monitor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply iron-plate organize to AmmoOS desktop slices (Start menu + tray)."""
    del monitor  # drop-wall monitor retired — desktop uses icons + task manager
    categories = dict(menu.get("categories") or {})
    host_cats = dict(menu.get("host_categories") or {})
    all_cats = {**categories, **host_cats}
    order, sorted_cats, cat_meta = organize_categories(all_cats, category_order=menu.get("category_order"))
    field_cats = {k: v for k, v in sorted_cats.items() if str(k).startswith("NEXUS")}
    host_sorted = {k: v for k, v in sorted_cats.items() if str(k).startswith("Host")}

    tray_out: list[dict[str, Any]] = []
    tray_meta: dict[str, Any] = {}
    if tray_icons:
        tray_out, tray_meta = organize_tray_icons(tray_icons)

    return {
        "menu": {
            **menu,
            "categories": field_cats,
            "host_categories": host_sorted,
            "category_order": order,
            "iron_plate_sorted": True,
        },
        "tray_icons": tray_out or tray_icons,
        "sort_meta": {
            "start_menu": cat_meta,
            "tray_icons": tray_meta,
        },
    }


def organize_chip_paths(*, limit: int = 48) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Iron Plate chip_paths — THE sort (composite_bsp) from CHIPS core, plate stack, or Ironclad chips."""
    core = _load(STATE / "field-chips-core.json", {})
    if core.get("condensed") and core.get("core_modules"):
        rows = [
            {
                "id": m.get("core_id") or m.get("id"),
                "name": m.get("label"),
                "family": m.get("family"),
                "path_pct": m.get("path_pct"),
                "slot": m.get("slot"),
                "chip_count": m.get("chip_count"),
            }
            for m in (core.get("core_modules") or [])[:limit]
        ]
        return rows, {
            "source": "chips_core",
            "count": len(rows),
            "the_sort": True,
            "condensed": True,
            "ironclad_grounded": bool(core.get("ironclad_sealed")),
            "ironclad_citation": core.get("ironclad_citation") or "ironclad:chips:core",
        }

    stack = _load(STATE / "field-chips-plate-stack.json", {})
    if stack.get("modules"):
        rows = [
            {
                "id": m.get("chip_id"),
                "name": m.get("label"),
                "family": m.get("family"),
                "band": m.get("band"),
                "path_pct": m.get("path_pct"),
                "iron_slot": m.get("iron_slot"),
                "bsp_model": m.get("bsp_model"),
            }
            for m in (stack.get("modules") or [])[:limit]
        ]
        meta = (stack.get("layers") or {}).get("iron_plate") or {}
        return rows, {**meta, "source": "chips_plate_stack", "count": len(rows)}

    combinatorics = _load(STATE / "field-ironclad-chips-combinatorics.json", {})
    chips = list(combinatorics.get("chips") or [])
    rows = [
        {
            "id": c.get("id"),
            "name": c.get("label"),
            "family": c.get("family"),
            "band": c.get("band"),
            "path_pct": c.get("path_pct"),
            "slot": c.get("slot"),
        }
        for c in chips[:limit]
    ]
    sorted_rows, meta = _sort_rows(rows, context="chip_paths", algorithm="composite_bsp", n=len(rows))
    imm = _ironclad_immediate()
    return sorted_rows, {
        **meta,
        "source": "ironclad_chips",
        "count": len(sorted_rows),
        "the_sort": True,
        "ironclad_grounded": bool(imm.get("ironclad_sealed") or (imm.get("plate_to_sense") or {}).get("ironclad_grounded")),
        "ironclad_citation": "ironclad:neural:2",
    }


def _plate_spots() -> dict[str, Any]:
    spot_py = INSTALL / "lib" / "iron-plate-spot-detector.py"
    mod = _import_py(spot_py, "iron_spot_organize")
    if mod and hasattr(mod, "slice_for_organize"):
        try:
            return mod.slice_for_organize()
        except Exception:
            pass
    if mod and hasattr(mod, "find_spots"):
        try:
            doc = mod.find_spots(allow_stale=True)
            return {
                "ok": doc.get("ok"),
                "spot_count": doc.get("spot_count"),
                "spots_live": doc.get("spots_live"),
                "top_spots": doc.get("top_spots"),
                "coolest_spot": doc.get("coolest_spot"),
                "low_power": doc.get("low_power"),
            }
        except Exception:
            pass
    return {}


def build_panel(*, write: bool = True) -> dict[str, Any]:
    gate = _thermal_gate(ops=2 if LOW_POWER else 6)
    cached = _load(PANEL, {})
    if not gate.get("ok") and cached:
        cached["thermal_deferred"] = True
        cached["thermal_gate"] = gate
        cached["posture"] = (
            f"Organize held — thermal gate · serving last-good panel · low_power={LOW_POWER}"
        )
        if write:
            _save(RUNTIME, {
                "schema": "iron-plate-organize-runtime/v1",
                "updated": cached.get("updated"),
                "ok": cached.get("ok"),
                "thermal_deferred": True,
                "low_power": LOW_POWER,
            })
        return cached

    doctrine = _load(DOCTRINE, {})
    iron = _iron_plate_snapshot()
    power = _power_sort_plate()
    bsp = _c2_bsp()
    bridge = _combinatorics_bridge()
    h7 = _h7_organize_status()
    desktop = _load(STATE / "field-host-desktop.json", {})

    menu = desktop.get("menu") or {}
    tray = desktop.get("startbar", {}).get("tray_icons") or _load(INSTALL / "data" / "field-host-desktop-doctrine.json", {}).get("tray_icons") or []

    organized = apply_to_desktop(menu=menu, tray_icons=list(tray))
    chip_path_rows, chip_path_meta = organize_chip_paths()
    format_rows, format_sort = organize_format_table()
    condense_rows, condense_meta = organize_condense_groups(bridge)
    posture = bridge.get("exec_posture") or {}
    ironclad_chain = _ironclad_chain_tree(bridge=bridge, bsp=bsp, power=power, iron=iron)
    plate_spots = _plate_spots()

    tools_live = 0
    for t in (doctrine.get("organizational_tools") or []):
        mod_path = str(t.get("module") or "")
        if mod_path.startswith("Grok16/"):
            if (GROK16 / mod_path.replace("Grok16/", "", 1)).is_file():
                tools_live += 1
        elif (INSTALL / mod_path).is_file():
            tools_live += 1

    bsp_ok = bool(bsp.get("bsp_hit") or bsp.get("ok"))
    power_ok = bool(power.get("ok"))
    bridge_ok = bool(bridge.get("ok"))
    iron_ok = bool(iron.get("connection_count") or iron.get("ok") or iron.get("plated"))
    organize_ok = ENABLED and tools_live >= 3 and (power_ok or bsp_ok or bridge_ok or iron_ok)

    stack_witness: dict[str, Any] = {}
    pio_path = INSTALL / "lib" / "plate-sealed-io.py"
    if pio_path.is_file():
        import importlib.util
        spec = importlib.util.spec_from_file_location("plate_sealed_io_ipo2", pio_path)
        if spec and spec.loader:
            pio = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(pio)
            if hasattr(pio, "stack_fabric_witness"):
                stack_witness = pio.stack_fabric_witness()

    doc = {
        "schema": "iron-plate-organize/v1",
        "updated": _now(),
        "stack_fabric": stack_witness,
        "meld_citation": "ironclad:meld:2",
        "enabled": ENABLED,
        "product": doctrine.get("iron_plate_product") or "Simple Iron Plate",
        "motto": doctrine.get("motto"),
        "ok": organize_ok,
        "iron_plate": {
            "connection_count": iron.get("connection_count"),
            "direct_routes": (iron.get("arithmetic") or {}).get("direct_count"),
            "plated": bool(iron.get("ok") or iron.get("plated")),
        },
        "power_sort": {
            "ok": power.get("ok"),
            "recombinatorics_algorithm": power.get("recombinatorics_algorithm"),
            "file_list_mode": power.get("file_list_mode"),
            "sections_live": sum(1 for s in (power.get("sections") or {}).values() if s.get("available")),
            "source": power.get("source"),
            "always_best_sort": True,
            "field_unique_best": True,
        },
        "chip_paths": {
            "count": len(chip_path_rows),
            "sort": chip_path_meta,
            "algorithm": chip_path_meta.get("algorithm") or "composite_bsp",
            "source": chip_path_meta.get("source"),
            "sample": chip_path_rows[:12],
        },
        "format_table": {
            "count": len(format_rows),
            "sort": format_sort,
            "field_unique_best": bool(format_sort.get("field_unique_best")),
            "one_best_ever": bool(format_sort.get("one_best_ever")),
            "algorithm": format_sort.get("algorithm"),
            "sample": format_rows[:8],
        },
        "recombinatorics_algorithm": power.get("recombinatorics_algorithm") or "composite_bsp",
        "bsp": bsp,
        "c2_bsp_hit": bool(bsp.get("bsp_hit")),
        "combinatorics_bridge_ok": bridge_ok,
        "exec_runner": posture.get("runner"),
        "exec_pattern": posture.get("pattern_id"),
        "condense_groups": condense_rows,
        "condense_sort": condense_meta,
        "ironclad_chain": ironclad_chain,
        "plate_spots": plate_spots,
        "organize_gain": ironclad_chain.get("organize_gain"),
        "replate_recommended": ironclad_chain.get("replate_recommended"),
        "low_power": LOW_POWER,
        "thermal_gate": gate,
        "h7_library": h7,
        "organizational_tools": [
            {
                "id": t.get("id"),
                "role": t.get("role"),
                "module": t.get("module"),
                "live": (
                    (GROK16 / str(t.get("module", "")).replace("Grok16/", "", 1)).is_file()
                    if str(t.get("module", "")).startswith("Grok16/")
                    else (INSTALL / str(t.get("module", ""))).is_file()
                ),
            }
            for t in (doctrine.get("organizational_tools") or [])
        ],
        "tools_live": tools_live,
        "surfaces": {
            "start_menu": {
                "iron_plate_sorted": (organized.get("menu") or {}).get("iron_plate_sorted"),
                "category_order": (organized.get("menu") or {}).get("category_order"),
                "category_count": len((organized.get("menu") or {}).get("categories") or {}),
            },
            "task_manager": {
                "mount": "fsb-task-manager",
                "registry": "data/system/field-desktop-registry.json",
            },
            "tray_icon_ids": [t.get("id") for t in (organized.get("tray_icons") or [])],
        },
        "sort_meta": organized.get("sort_meta"),
        "posture": (
            f"Iron plate → composite_bsp + power sort — "
            f"BSP {'hit' if bsp_ok else 'stage'} · "
            f"{tools_live} organize tools live · "
            f"{ironclad_chain.get('posture', 'ironclad chain pending')}"
        ),
    }

    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "iron-plate-organize-runtime/v1",
            "updated": doc["updated"],
            "ok": organize_ok,
            "recombinatorics_algorithm": doc["recombinatorics_algorithm"],
            "c2_bsp_hit": doc["c2_bsp_hit"],
            "combinatorics_bridge_ok": bridge_ok,
            "tools_live": tools_live,
        })
    return doc


def organize_ok(ctx: dict[str, Any] | None = None) -> bool:
    if not ENABLED:
        return False
    if ctx and ctx.get("iron_plate_organize"):
        return bool((ctx.get("iron_plate_organize") or {}).get("ok"))
    doc = _load(PANEL, {})
    if doc:
        return bool(doc.get("ok"))
    return bool(build_panel(write=True).get("ok"))


def slice_for_motion() -> dict[str, Any]:
    doc = _load(PANEL, {}) or build_panel(write=False)
    chain = doc.get("ironclad_chain") or {}
    return {
        "ok": doc.get("ok"),
        "recombinatorics_algorithm": doc.get("recombinatorics_algorithm"),
        "c2_bsp_hit": doc.get("c2_bsp_hit"),
        "combinatorics_bridge_ok": doc.get("combinatorics_bridge_ok"),
        "tools_live": doc.get("tools_live"),
        "exec_runner": doc.get("exec_runner"),
        "organize_gain": doc.get("organize_gain"),
        "replate_recommended": doc.get("replate_recommended"),
        "ironclad_grounded": chain.get("ironclad_grounded"),
        "browser_in_c2": chain.get("browser_in_c2"),
        "posture": doc.get("posture"),
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(write=True), ensure_ascii=False))
        return 0
    if cmd in ("build", "cycle", "refresh"):
        print(json.dumps(build_panel(write=True), ensure_ascii=False))
        return 0
    if cmd == "apply-desktop":
        desktop = _load(STATE / "field-host-desktop.json", {})
        out = apply_to_desktop(
            menu=desktop.get("menu") or {},
            tray_icons=(desktop.get("startbar") or {}).get("tray_icons"),
        )
        print(json.dumps(out, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: iron-plate-organize.py [json|build|apply-desktop]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())