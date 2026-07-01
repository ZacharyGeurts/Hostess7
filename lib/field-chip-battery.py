#!/usr/bin/env pythong
"""Deprecated shim — chip combinatorics now roots on Ironclad via field-ironclad-chips-combinatorics.py."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
_IRONCLAD_MOD: Any = None


def _ironclad_mod() -> Any:
    global _IRONCLAD_MOD
    if _IRONCLAD_MOD is not None:
        return _IRONCLAD_MOD
    path = INSTALL / "lib" / "field-ironclad-chips-combinatorics.py"
    spec = importlib.util.spec_from_file_location("ironclad_chips_shim", path)
    if not spec or not spec.loader:
        raise ImportError("field-ironclad-chips-combinatorics.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _IRONCLAD_MOD = mod
    return mod


def build_chip_battery(*, mame_live: bool = False, force: bool = False) -> dict[str, Any]:
    doc = _ironclad_mod().build_ironclad_chips_combinatorics(mame_live=mame_live, force=force)
    return {**doc, "schema": "field-chip-battery/v1", "deprecated": True, "shim": "ironclad_chips"}


def publish_panel(*, mame_live: bool = False, write_battery: bool = True) -> dict[str, Any]:
    pub = _ironclad_mod().publish_panel(mame_live=mame_live, write_combinatorics=write_battery)
    panel = dict(pub.get("panel") or {})
    panel["schema"] = "field-chip-battery-panel/v1"
    panel["deprecated"] = True
    panel["shim"] = "ironclad_chips"
    panel["combinatorics_facet"] = "ironclad_chips"
    return {**pub, "panel": panel, "battery_path": pub.get("combinatorics_path")}


def combinatorics_leaves(chips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _ironclad_mod().combinatorics_leaves(chips)


def combinatorics_leaves_from_chips(chips: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return combinatorics_leaves(chips)


def predict_code_paths(chips: list[dict[str, Any]], *, skip_reorganize: bool = False) -> dict[str, Any]:
    return _ironclad_mod().predict_code_paths(chips, skip_reorganize=skip_reorganize)


def combinatronic_panel(*, refresh: bool = False, state_dir: Path | None = None, force: bool = False) -> dict[str, Any]:
    return _ironclad_mod().combinatronic_panel(refresh=refresh, state_dir=state_dir, force=force)


def chip_battery_slice(*, state_dir: Path | None = None) -> dict[str, Any]:
    slice_doc = _ironclad_mod().ironclad_chips_slice(state_dir=state_dir)
    return {
        **slice_doc,
        "schema": "field-chip-battery-slice/v1",
        "facet": "ironclad_chips",
        "deprecated": True,
        "shim": "ironclad_chips",
    }


def main() -> int:
    mod = _ironclad_mod()
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(publish_panel().get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish"):
        mame_live = "--mame-live" in sys.argv[2:]
        print(json.dumps(publish_panel(mame_live=mame_live), ensure_ascii=False, indent=2))
        return 0
    if cmd == "battery":
        mame_live = "--mame-live" in sys.argv[2:]
        print(json.dumps(build_chip_battery(mame_live=mame_live), ensure_ascii=False, indent=2))
        return 0
    if cmd == "slice":
        print(json.dumps(chip_battery_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("paths", "predict", "path-predict"):
        battery = build_chip_battery()
        pred = battery.get("code_path_prediction") or {}
        if not pred or pred.get("total_pct") is None:
            panel = publish_panel(write_battery=False).get("panel") or {}
            pred = panel.get("code_path_prediction") or pred
        if not pred or pred.get("total_pct") is None:
            chips = list(battery.get("chips") or [])
            if chips:
                pred = predict_code_paths(chips)
        print(json.dumps(pred or {}, ensure_ascii=False, indent=2))
        return 0
    if cmd in ("combinatronic", "combinatronics", "chips-combinatronic"):
        refresh = "--refresh" in sys.argv[2:]
        print(json.dumps(combinatronic_panel(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        pub = publish_panel()
        panel = pub.get("panel") or {}
        counts = panel.get("counts") or {}
        pred = panel.get("code_path_prediction") or {}
        ok = (
            counts.get("total", 0) >= 50
            and counts.get("cyrix", 0) >= 5
            and counts.get("coco", 0) >= 5
            and pred.get("total_pct") == 100.0
        )
        print(json.dumps({"ok": ok, "counts": counts, "facet": "ironclad_chips", "shim": True}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    if cmd == "mame-import":
        os.environ["NEXUS_IRONCLAD_CHIPS_MAME_LIVE"] = "1"
        print(json.dumps(publish_panel(mame_live=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage", "shim": "ironclad_chips", "delegate": "field-ironclad-chips-combinatorics.py"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())