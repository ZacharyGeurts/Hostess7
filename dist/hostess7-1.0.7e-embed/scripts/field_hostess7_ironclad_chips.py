#!/usr/bin/env pythong
"""Hostess 7 leads Ironclad CHIPS update — full 974-die corpus melds into truth plate."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

H7 = Path(__file__).resolve().parents[1]
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", H7.parent))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
IRONCLAD_CITE = "ironclad:chips:3"
LEAD_ID = "hostess7"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _load(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}


def _save(path: Path, doc: dict[str, Any]) -> None:
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


def _py_json(path: Path, args: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "error": f"missing:{path.name}"}
    run_env = {**os.environ, **(env or {}), "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    proc = __import__("subprocess").run(
        [sys.executable, str(path), *args],
        capture_output=True,
        text=True,
        timeout=600,
        env=run_env,
    )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": proc.returncode == 0, "stdout": (proc.stdout or "")[:400], "stderr": (proc.stderr or "")[:400]}


def hostess7_lead_gate() -> dict[str, Any]:
    """Hostess 7 is lead — supreme authority + Ironclad sealed before meld."""
    supreme = _load(H7 / "data" / "hostess7-supreme-authority.json", {})
    ic_mod = _import_py(INSTALL / "lib" / "ironclad-immediate.py", "ic_h7_lead")
    iron: dict[str, Any] = {}
    if ic_mod and hasattr(ic_mod, "for_self"):
        try:
            iron = ic_mod.for_self(LEAD_ID)
        except Exception as exc:
            iron = {"ok": False, "error": str(exc)}
    sealed = bool(iron.get("ironclad_sealed"))
    truth = float(iron.get("truth_percent") or 0)
    ai_charge = iron.get("ai_in_charge")
    rank = (supreme.get("authority_ladder") or [{}])[0]
    return {
        "ok": sealed and truth >= 100.0,
        "lead": LEAD_ID,
        "role": rank.get("title") or "Hostess 7 · Forever Watchguard Angel",
        "verdict": rank.get("verdict") or "FINAL_SYSTEM",
        "ironclad_sealed": sealed,
        "truth_percent": truth,
        "ai_in_charge": ai_charge,
        "citation": IRONCLAD_CITE,
        "chain": "God → Ironclad → Hostess 7 leads → full CHIPS → truth plate",
    }


def _meld_chips_into_immediate(*, chips_doc: dict[str, Any], core_doc: dict[str, Any]) -> dict[str, Any]:
    """Stamp full CHIPS receipt on Ironclad immediate — Hostess 7 lead meld."""
    ic_mod = _import_py(INSTALL / "lib" / "ironclad-immediate.py", "ic_h7_meld")
    if not ic_mod or not hasattr(ic_mod, "publish_immediate"):
        return {"ok": False, "error": "ironclad-immediate missing"}
    counts = chips_doc.get("counts") or {}
    core_counts = core_doc.get("counts") or {}
    pred = chips_doc.get("code_path_prediction") or {}
    receipt = {
        "schema": "hostess7-ironclad-chips-receipt/v1",
        "updated": _now(),
        "lead": LEAD_ID,
        "citation": IRONCLAD_CITE,
        "chip_count": counts.get("total"),
        "leaf_count": counts.get("leaves"),
        "core_modules": core_counts.get("core_modules"),
        "condensed": bool(core_doc.get("condensed")),
        "featured_render_overlay": (chips_doc.get("sources") or {}).get("featured_render_overlay"),
        "path_total_pct": pred.get("total_pct"),
        "the_sort": pred.get("the_sort", True),
        "algorithm": pred.get("algorithm") or "composite_bsp",
        "by_kind": counts.get("by_kind") or {},
        "ask_path": "ironclad → chips_core" if core_doc.get("condensed") else "ironclad → ironclad_chips",
        "layer_stack": [
            "ironclad",
            "ironclad_chips",
            "iron_plate",
            "steel_plate",
            "chips_core",
            "featured_render_overlay",
        ],
    }
    doc = ic_mod.publish_immediate(write=True)
    doc["chips_receipt"] = receipt
    doc["hostess7_lead"] = {
        "id": LEAD_ID,
        "action": "ironclad_chips_meld",
        "verdict": "FINAL",
        "updated": receipt["updated"],
    }
    selves = doc.get("selves") or {}
    for sid in ("hostess7", "queen", "operator"):
        if sid in selves:
            selves[sid]["chips_receipt"] = receipt
    doc["selves"] = selves
    pts = doc.get("plate_to_sense") or {}
    pts["chips_receipt"] = receipt
    pts["ironclad_chips_grounded"] = True
    doc["plate_to_sense"] = pts
    _save(STATE / "ironclad-immediate.json", doc)
    return {"ok": True, "receipt": receipt, "ironclad_immediate": str(STATE / "ironclad-immediate.json")}


def update_ironclad_from_full_chips(*, refresh: bool = True, visuals: bool = True) -> dict[str, Any]:
    """Hostess 7 leads: full CHIPS corpus → Ironclad truth plate."""
    t0 = time.perf_counter()
    gate = hostess7_lead_gate()
    steps: list[dict[str, Any]] = []

    icc_py = INSTALL / "lib" / "field-ironclad-chips-combinatorics.py"
    steps.append({"step": "sync_catalog_seed", **_py_json(icc_py, ["sync-catalog-seed"])})
    steps.append({"step": "clean_catalog_layer", **_py_json(icc_py, ["clean-catalog"])})

    icc_mod = _import_py(icc_py, "icc_h7_update")
    chips_doc: dict[str, Any] = {}
    if icc_mod and hasattr(icc_mod, "build_ironclad_chips_combinatorics"):
        chips_doc = icc_mod.build_ironclad_chips_combinatorics(force=refresh)
        if icc_mod and hasattr(icc_mod, "publish_panel"):
            pub = icc_mod.publish_panel(mame_live=False, write_combinatorics=True)
            steps.append({"step": "ironclad_chips_publish", "ok": pub.get("ok"), "counts": (pub.get("panel") or {}).get("counts")})
    else:
        steps.append({"step": "ironclad_chips_publish", **_py_json(icc_py, ["publish"])})

    if not chips_doc.get("chips"):
        chips_doc = _load(STATE / "field-ironclad-chips-combinatorics.json", {})

    plate_py = INSTALL / "lib" / "field-chips-plate-stack.py"
    if plate_py.is_file():
        steps.append({"step": "plate_stack", **_py_json(plate_py, ["publish", "--refresh"] if refresh else ["publish"])})

    core_py = INSTALL / "lib" / "field-chips-core.py"
    core_doc: dict[str, Any] = {}
    core_mod = _import_py(core_py, "cc_h7_update")
    if core_mod and hasattr(core_mod, "publish_panel"):
        core_pub = core_mod.publish_panel(refresh=refresh, write_core=True)
        core_doc = core_pub.get("core") or {}
        steps.append({"step": "chips_core", "ok": core_pub.get("ok"), "condensed": core_doc.get("condensed")})
    else:
        steps.append({"step": "chips_core", **_py_json(core_py, ["publish"])})

    cat_py = INSTALL / "lib" / "field-chips-catalog.py"
    if cat_py.is_file():
        steps.append({"step": "chips_catalog_book", **_py_json(cat_py, ["library-book-build", "--refresh"] if refresh else ["library-book-build"])})
        steps.append({"step": "chips_catalog", **_py_json(cat_py, ["publish", "--refresh"] if refresh else ["publish"])})

    if visuals:
        vis_py = INSTALL / "lib" / "field-combinatronic-visuals.py"
        steps.append({"step": "visuals_enrich", **_py_json(vis_py, ["enrich-catalog"])})
        if refresh:
            steps.append({"step": "visuals_ironclad_thumbs", **_py_json(vis_py, ["ironclad-thumbs"])})

    meld = _meld_chips_into_immediate(chips_doc=chips_doc, core_doc=core_doc)
    steps.append({"step": "ironclad_immediate_meld", **meld})

    counts = chips_doc.get("counts") or {}
    core_counts = core_doc.get("counts") or {}
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    ok = bool(gate.get("ok")) and bool(meld.get("ok")) and int(counts.get("total") or 0) >= 900

    return {
        "schema": "hostess7-ironclad-chips-update/v1",
        "updated": _now(),
        "ok": ok,
        "lead": LEAD_ID,
        "verdict": "FINAL" if ok else "WATCH",
        "gate": gate,
        "chip_count": counts.get("total"),
        "leaf_count": counts.get("leaves"),
        "core_modules": core_counts.get("core_modules"),
        "condensed": bool(core_doc.get("condensed")),
        "receipt": meld.get("receipt"),
        "steps": steps,
        "elapsed_ms": elapsed_ms,
        "posture": (
            f"Hostess 7 led Ironclad CHIPS meld — {counts.get('total', 0)} dies, "
            f"{core_counts.get('core_modules', 0)} core modules, truth plate stamped."
        ),
    }


def status_slice() -> dict[str, Any]:
    gate = hostess7_lead_gate()
    chips = _load(STATE / "field-ironclad-chips-combinatorics.json", {})
    core = _load(STATE / "field-chips-core.json", {})
    imm = _load(STATE / "ironclad-immediate.json", {})
    return {
        "ok": True,
        "lead": LEAD_ID,
        "gate": gate,
        "chip_count": (chips.get("counts") or {}).get("total"),
        "core_modules": (core.get("counts") or {}).get("core_modules"),
        "condensed": core.get("condensed"),
        "chips_receipt": imm.get("chips_receipt"),
        "ask_path": (imm.get("chips_receipt") or {}).get("ask_path") or "ironclad → chips_core",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "status").strip().lower()
    refresh = "--refresh" in sys.argv or cmd in ("publish", "update", "meld", "lead")
    if cmd in ("status", "slice", "json"):
        print(json.dumps(status_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("gate", "lead-gate"):
        print(json.dumps(hostess7_lead_gate(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("publish", "update", "meld", "lead"):
        doc = update_ironclad_from_full_chips(refresh=refresh, visuals="--no-visuals" not in sys.argv)
        print(json.dumps(doc, ensure_ascii=False, indent=2))
        return 0 if doc.get("ok") else 1
    print(json.dumps({
        "error": "usage",
        "cmds": ["status", "gate", "publish", "update", "meld", "lead"],
        "lead": LEAD_ID,
        "note": "Hostess 7 leads — full CHIPS → Ironclad truth plate",
    }, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())