#!/usr/bin/env pythong
"""Plate dimensions — configure width × length to consolidate condense groups into fewer meta-plates."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
DOCTRINE = INSTALL / "data" / "field-plate-dimensions-doctrine.json"
PANEL = STATE / "field-plate-dimensions-panel.json"
BATTERY = STATE / "field-plate-dimensions.json"
CONDENSE_OUT = STATE / "field-plate-condense-consolidated.json"
WIDTH_CANDIDATES = (8, 12, 16, 20, 24, 32, 48)

PLATE_CONDENSE_GROUPS: dict[str, list[tuple[str, str]]] = {
    "c2_taskbar": [
        ("c2_taskbar", "field-c2-taskbar-panel.json"),
    ],
    "operator_surfaces": [
        ("shell_dock", "field-shell-dock-panel.json"),
        ("field_popcorn", "field-popcorn-panel.json"),
        ("field_ellie_fier", "field-ellie-fier-panel.json"),
        ("field_g16_launch", "field-g16-launch-panel.json"),
        ("field_gpu", "field-gpu-control-panel.json"),
        ("field_audio", "field-audio-settings-panel.json"),
        ("field_broadcaster", "field-broadcaster-panel.json"),
        ("field_lock", "field-keepass-panel.json"),
    ],
    "universal_lock": [
        ("sense_package", "field-sense-package-panel.json"),
        ("eye_ear_plate", "eye-ear-plate.json"),
        ("universal_protector", "universal-protector-panel.json"),
    ],
    "sense_stack": [
        ("sense_package", "field-sense-package-panel.json"),
        ("eye_ear_plate", "eye-ear-plate.json"),
    ],
    "g16_universal": [
        ("g16_universal", "field-g16-universal-combinatronic-panel.json"),
        ("ironclad_chips", "field-ironclad-chips-combinatorics-panel.json"),
        ("program_combinatronic", "field-program-combinatronic-panel.json"),
    ],
    "chips_core": [
        ("ironclad_chips", "field-ironclad-chips-combinatorics-panel.json"),
        ("chips_plate_stack", "field-chips-plate-stack-panel.json"),
        ("chips_core", "field-chips-core-panel.json"),
    ],
    "iron_truth": [
        ("truth_blocks", "g16-truth-blocks-panel.json"),
        ("code_bugfinder", "field-code-bugfinder-panel.json"),
        ("field_combinatorics", "g16-field-combinatorics-panel.json"),
        ("combinatorics_bridge", "field-plate-combinatorics-bridge.json"),
    ],
}


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
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _clamp_width(w: int, *, lo: int = 8, hi: int = 48) -> int:
    w = max(lo, min(hi, int(w)))
    return min(WIDTH_CANDIDATES, key=lambda c: abs(c - w))


def _growth_width() -> int:
    growth = _load(STATE / "field-combinatronics-growth-panel.json", {})
    ow = growth.get("optimal_width")
    if isinstance(ow, dict):
        ow = ow.get("optimal_width")
    if ow:
        return _clamp_width(int(ow))
    doctrine = _load(DOCTRINE, {})
    dim = doctrine.get("dimensions") or {}
    return _clamp_width(int(dim.get("default_width") or 16))


def _config_overrides() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("PLATE_WIDTH", "PLATE_LENGTH", "PLATE_MERGE_POLICY"):
        val = os.environ.get(key, "").strip()
        if not val:
            continue
        if key == "PLATE_WIDTH":
            out["width"] = _clamp_width(int(val))
        elif key == "PLATE_LENGTH":
            out["length"] = max(1, int(val))
        else:
            out["merge_policy"] = val
    return out


def _collect_condense_rows() -> list[dict[str, Any]]:
    """Build condense group rows from PLATE_CONDENSE_GROUPS + live panels."""
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    existing = {
        str(g.get("group")): g
        for g in (comb.get("plate_condense") or bridge.get("plate_condense") or {}).get("groups") or []
    }
    rows: list[dict[str, Any]] = []
    for group_id, members in PLATE_CONDENSE_GROUPS.items():
        present = 0
        member_docs: list[dict[str, Any]] = []
        for plate_key, fname in members:
            doc = _load(STATE / fname, {})
            live = bool(doc) and not doc.get("missing") and doc.get("ok", True)
            if live:
                present += 1
            member_docs.append({
                "plate_key": plate_key,
                "panel": fname,
                "present": live,
                "ok": bool(doc.get("ok", True)) if doc else False,
            })
        prior = existing.get(group_id) or {}
        rows.append({
            "group": group_id,
            "present": int(prior.get("present") or present),
            "total": int(prior.get("total") or len(members)),
            "condensed": bool(prior.get("condensed")),
            "priority": float(prior.get("present") or present) + (0.5 if group_id == "c2_taskbar" else 0),
            "members": member_docs,
        })
    rows.sort(key=lambda r: (-float(r.get("priority") or 0), str(r.get("group") or "")))
    return rows


def _optimal_length(*, group_count: int, width: int, auto: bool) -> int:
    if group_count <= 0:
        return 1
    min_len = max(1, math.ceil(group_count / width))
    if not auto:
        doctrine = _load(DOCTRINE, {})
        dim = doctrine.get("dimensions") or {}
        explicit = int(dim.get("default_length") or 0)
        if explicit > 0:
            return max(1, explicit)
        return min_len
    best_len = min_len
    best_score = -1.0
    for length in range(min_len, min_len + 6):
        cells = width * length
        meta_rows = length if True else 1
        overflow = max(0, group_count - cells)
        travel_proxy = length * (width - 1) * 0.5
        score = (group_count / max(1, meta_rows)) - overflow * 2 - travel_proxy * 0.01
        if score > best_score:
            best_score = score
            best_len = length
    return best_len


def _grid_positions(n: int, width: int, length: int) -> list[tuple[int, int]]:
    positions: list[tuple[int, int]] = []
    for i in range(n):
        row = i // width
        col = i % width
        if row >= length:
            row = length - 1
            col = min(col, width - 1)
        positions.append((row, col))
    return positions


def _manhattan_travel(order: list[str], positions: dict[str, tuple[int, int]]) -> int:
    total = 0
    for i in range(1, len(order)):
        a = positions.get(order[i - 1], (0, 0))
        b = positions.get(order[i], (0, 0))
        total += abs(a[0] - b[0]) + abs(a[1] - b[1])
    return total


def _merge_meta_plates(
    rows: list[dict[str, Any]],
    *,
    width: int,
    length: int,
    merge_policy: str,
    row_consolidate: bool,
    metadata_only: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Pack sorted groups into W×L grid; fuse rows into meta-plates."""
    order = [str(r["group"]) for r in rows]
    pos_list = _grid_positions(len(rows), width, length)
    positions = {gid: pos_list[i] for i, gid in enumerate(order)}

    travel_before = _manhattan_travel(order, positions)

    by_row: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        gid = str(row["group"])
        r, c = positions[gid]
        by_row.setdefault(r, []).append({**row, "grid_row": r, "grid_col": c})

    meta_plates: list[dict[str, Any]] = []
    meta_order: list[str] = []
    for r in sorted(by_row.keys()):
        row_groups = sorted(by_row[r], key=lambda g: int(g.get("grid_col") or 0))
        if merge_policy == "row_adjacent" and row_consolidate:
            members = [str(g["group"]) for g in row_groups]
            present = sum(int(g.get("present") or 0) for g in row_groups)
            total = sum(int(g.get("total") or 0) for g in row_groups)
            meta_id = f"meta_r{r}"
            panel_name = f"condensed-{meta_id}-plate.json"
            fused: dict[str, Any] = {
                "schema": "condensed-plate/v1",
                "meta_plate": meta_id,
                "groups": members,
                "dimensions": {"width": width, "length": length, "row": r},
                "present": present,
                "total": total,
                "snapshots": {},
            }
            if not metadata_only:
                for g in row_groups:
                    for m in g.get("members") or []:
                        if m.get("present"):
                            doc = _load(STATE / str(m.get("panel") or ""), {})
                            if doc:
                                fused["snapshots"][m.get("plate_key")] = {
                                    "panel": m.get("panel"),
                                    "ok": doc.get("ok"),
                                    "posture": doc.get("posture") or doc.get("title"),
                                }
                _save(STATE / panel_name, fused)
            meta_plates.append({
                "id": meta_id,
                "row": r,
                "col_start": min(int(g.get("grid_col") or 0) for g in row_groups),
                "col_end": max(int(g.get("grid_col") or 0) for g in row_groups),
                "members": members,
                "present": present,
                "total": total,
                "condensed": present >= max(1, len(row_groups) // 2),
                "panel": panel_name,
                "grid": {"width": width, "length": length},
            })
            meta_order.append(meta_id)
        else:
            for g in row_groups:
                gid = str(g["group"])
                meta_plates.append({
                    "id": gid,
                    "row": int(g.get("grid_row") or 0),
                    "col_start": int(g.get("grid_col") or 0),
                    "col_end": int(g.get("grid_col") or 0),
                    "members": [gid],
                    "present": int(g.get("present") or 0),
                    "total": int(g.get("total") or 0),
                    "condensed": bool(g.get("condensed")),
                    "panel": f"condensed-{gid}-plate.json",
                    "grid": {"width": width, "length": length},
                })
                meta_order.append(gid)

    meta_positions = {m["id"]: (int(m["row"]), int(m["col_start"])) for m in meta_plates}
    travel_after = _manhattan_travel(meta_order, meta_positions)

    updated_groups: list[dict[str, Any]] = []
    meta_by_member: dict[str, str] = {}
    for mp in meta_plates:
        for mem in mp.get("members") or []:
            meta_by_member[str(mem)] = str(mp["id"])

    for row in rows:
        gid = str(row["group"])
        updated_groups.append({
            **row,
            "condensed": bool(row.get("present")),
            "meta_plate": meta_by_member.get(gid),
            "grid_row": positions[gid][0],
            "grid_col": positions[gid][1],
        })

    return meta_plates, {
        "groups": updated_groups,
        "meta_plates": meta_plates,
        "travel_before": travel_before,
        "travel_after": travel_after,
        "travel_reduction": max(0, travel_before - travel_after),
        "travel_reduction_pct": round(
            (max(0, travel_before - travel_after) / travel_before * 100) if travel_before else 0,
            2,
        ),
    }


def consolidate_dimensions(
    *,
    width: int | None = None,
    length: int | None = None,
    metadata_only: bool = True,
) -> dict[str, Any]:
    doctrine = _load(DOCTRINE, {})
    dim_cfg = doctrine.get("dimensions") or {}
    overrides = _config_overrides()

    if width is None:
        width = overrides.get("width")
    if width is None:
        width = _growth_width() if dim_cfg.get("width_from_growth", True) else int(dim_cfg.get("default_width") or 16)
    width = _clamp_width(
        int(width),
        lo=int(dim_cfg.get("min_width") or 8),
        hi=int(dim_cfg.get("max_width") or 48),
    )

    rows = _collect_condense_rows()
    group_count = len(rows)

    if length is None:
        length = overrides.get("length")
    if length is None:
        length = _optimal_length(
            group_count=group_count,
            width=width,
            auto=bool(dim_cfg.get("length_auto", True)),
        )
    length = max(1, int(length))

    merge_policy = str(overrides.get("merge_policy") or dim_cfg.get("merge_policy") or "row_adjacent")
    row_consolidate = bool(dim_cfg.get("row_consolidate", True))

    meta_plates, pack = _merge_meta_plates(
        rows,
        width=width,
        length=length,
        merge_policy=merge_policy,
        row_consolidate=row_consolidate,
        metadata_only=metadata_only,
    )

    meta_count = len(meta_plates)
    condensed = meta_count < group_count or any(m.get("condensed") for m in meta_plates)

    plate_condense = {
        "schema": "plate-condense-consolidated/v1",
        "condensed": condensed,
        "group_count": group_count,
        "meta_plate_count": meta_count,
        "dimensions": {"width": width, "length": length, "cells": width * length},
        "travel_before": pack["travel_before"],
        "travel_after": pack["travel_after"],
        "travel_reduction": pack["travel_reduction"],
        "travel_reduction_pct": pack["travel_reduction_pct"],
        "groups": pack["groups"],
        "meta_plates": pack["meta_plates"],
        "merge_policy": merge_policy,
        "width_source": "growth_optimal_width" if dim_cfg.get("width_from_growth") else "doctrine_default",
    }

    return {
        "schema": "field-plate-dimensions/v1",
        "updated": _now(),
        "product": "AmmoOS",
        "motto": "Width × length consolidation — fewer meta-plates, same function, less travel.",
        "ok": group_count > 0,
        "group_count": group_count,
        "meta_plate_count": meta_count,
        "fewer_plates": max(0, group_count - meta_count),
        "dimensions": plate_condense["dimensions"],
        "travel": {
            "before": pack["travel_before"],
            "after": pack["travel_after"],
            "reduction": pack["travel_reduction"],
            "reduction_pct": pack["travel_reduction_pct"],
        },
        "plate_condense": plate_condense,
        "condensed": condensed,
        "metadata_only": metadata_only,
        "optimal_width": width,
        "posture": (
            f"Plate grid {width}×{length} — {group_count} groups → {meta_count} meta-plates · "
            f"travel −{pack['travel_reduction_pct']}%"
        ),
    }


def condense_plates(
    *,
    state_dir: Path | None = None,
    truth_panel: dict[str, Any] | None = None,
    metadata_only: bool = True,
) -> dict[str, Any]:
    """Compat shim for g16-combinatronic-rebalance / field_combinatorics.condense_plates."""
    global STATE
    if state_dir is not None:
        STATE = Path(state_dir)
    doc = consolidate_dimensions(metadata_only=metadata_only)
    _save(CONDENSE_OUT, doc.get("plate_condense") or {})
    comb_path = STATE / "g16-field-combinatorics-panel.json"
    comb = _load(comb_path, {})
    if comb:
        comb["plate_condense"] = doc.get("plate_condense")
        comb["plate_dimensions"] = {
            "width": doc.get("dimensions", {}).get("width"),
            "length": doc.get("dimensions", {}).get("length"),
            "meta_plate_count": doc.get("meta_plate_count"),
            "travel_reduction_pct": doc.get("travel", {}).get("reduction_pct"),
        }
        _save(comb_path, comb)
    return {
        "ok": doc.get("ok"),
        "condensed": doc.get("condensed"),
        "group_count": doc.get("group_count"),
        "meta_plate_count": doc.get("meta_plate_count"),
        "dimensions": doc.get("dimensions"),
        "travel_reduction_pct": doc.get("travel", {}).get("reduction_pct"),
        "metadata_only": metadata_only,
        "source": "field-plate-dimensions",
    }


def read_consolidated_condense() -> dict[str, Any]:
    """Return consolidated plate_condense for bridge / organize consumers."""
    cached = _load(CONDENSE_OUT, {})
    if cached.get("groups"):
        return cached
    panel = _load(PANEL, {})
    return panel.get("plate_condense") or cached


def publish_panel(*, write_battery: bool = True, metadata_only: bool = True) -> dict[str, Any]:
    doc = consolidate_dimensions(metadata_only=metadata_only)
    panel = {
        "schema": "field-plate-dimensions-panel/v1",
        "updated": doc.get("updated"),
        "ok": doc.get("ok"),
        "group_count": doc.get("group_count"),
        "meta_plate_count": doc.get("meta_plate_count"),
        "fewer_plates": doc.get("fewer_plates"),
        "dimensions": doc.get("dimensions"),
        "travel": doc.get("travel"),
        "optimal_width": doc.get("optimal_width"),
        "condensed": doc.get("condensed"),
        "meta_plates": (doc.get("plate_condense") or {}).get("meta_plates"),
        "posture": doc.get("posture"),
    }
    _save(PANEL, panel)
    _save(CONDENSE_OUT, doc.get("plate_condense") or {})
    if write_battery:
        _save(BATTERY, doc)
    return {"ok": True, "panel": panel, "battery": doc}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    meta = os.environ.get("G16_COMBO_CONDENSE", "meta").strip().lower() not in ("full", "0", "false")
    if "--full" in sys.argv:
        meta = False

    if cmd in ("panel", "json", "status"):
        print(json.dumps(publish_panel(metadata_only=meta), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "consolidate", "cycle", "refresh"):
        print(json.dumps(publish_panel(write_battery=True, metadata_only=meta), ensure_ascii=False, indent=2))
        return 0
    if cmd == "condense":
        print(json.dumps(condense_plates(metadata_only=meta), ensure_ascii=False, indent=2))
        return 0
    if cmd == "read":
        print(json.dumps(read_consolidated_condense(), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["panel", "build", "consolidate", "condense", "read"],
        "flags": ["--full"],
    }, ensure_ascii=False, indent=2))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())