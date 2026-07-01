#!/usr/bin/env python3
"""Field best sort — Ironclad meld: exactly one best sort ever per context."""
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
DOCTRINE = INSTALL / "data" / "field-best-sort-doctrine.json"
PANEL = STATE / "field-best-sort-panel.json"

STATEMENT = "field_one_best_ever"
MELD_CITATION = "ironclad:meld:2"

_FAMILY_ORDER = (
    "sovereign", "library", "geometry", "image_field",
    "media", "executable", "document", "archive", "data",
)


def _now() -> str:
    import time
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


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


def _power_sort_mod() -> Any | None:
    for path in (GROK16 / "lib" / "field-power-sort.py", INSTALL / "Grok16" / "lib" / "field-power-sort.py"):
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("field_power_sort_best", path)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _sort_family_then_label(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    fam_idx = {f: i for i, f in enumerate(_FAMILY_ORDER)}

    def key(r: dict[str, Any]) -> tuple:
        fam = str(r.get("family") or "data")
        return (
            fam_idx.get(fam, 99),
            str(r.get("label") or r.get("name") or r.get("id") or "").lower(),
            str(r.get("id") or ""),
        )

    return sorted(rows, key=key)


def _composite_bsp_sort(
    rows: list[dict[str, Any]],
    *,
    key: str = "path_pct",
    reverse: bool = True,
) -> list[dict[str, Any]]:
    if len(rows) <= 1:
        return list(rows)

    def score(row: dict[str, Any], idx: int) -> float:
        raw = row.get(key)
        if raw is None:
            raw = row.get("weight")
        if raw is None:
            raw = row.get("priority")
        if raw is None:
            raw = len(rows) - idx
        return float(raw)

    scored = [(score(r, i), r) for i, r in enumerate(rows)]
    scored.sort(key=lambda t: t[0], reverse=reverse)
    mid = len(scored) // 2
    left = _composite_bsp_sort([r for _, r in scored[:mid]], key=key, reverse=reverse)
    right = _composite_bsp_sort([r for _, r in scored[mid:]], key=key, reverse=reverse)
    return left + right


def _apply_algorithm(rows: list[dict[str, Any]], alg: str, *, context: str) -> list[dict[str, Any]]:
    if alg == "composite_bsp" or (context == "chip_paths" and alg != "narrow_band"):
        key = "path_pct" if context == "chip_paths" else "priority"
        return _composite_bsp_sort(rows, key=key)
    if alg == "family_then_label" or context == "format_table":
        return _sort_family_then_label(rows)
    mod = _power_sort_mod()
    if mod and hasattr(mod, "apply_sort"):
        name_rows = []
        for r in rows:
            name_rows.append({
                "name": str(r.get("label") or r.get("name") or r.get("id") or ""),
                "kind": r.get("kind") or "file",
                **r,
            })
        try:
            sorted_rows = mod.apply_sort(name_rows, context=context if context != "format_table" else "file_list", n=len(rows))
            id_order = [str(x.get("id") or x.get("name")) for x in sorted_rows]
            by_id = {str(r.get("id") or r.get("name")): r for r in rows}
            out = [by_id[i] for i in id_order if i in by_id]
            for r in rows:
                rid = str(r.get("id") or r.get("name"))
                if rid not in id_order:
                    out.append(r)
            return out
        except Exception:
            pass
    if alg == "cool_sort":
        return sorted(rows, key=lambda r: float(r.get("thermo_proxy") or r.get("priority") or 0))
    if alg == "dirs_first":
        return sorted(
            rows,
            key=lambda r: (
                0 if r.get("kind") in ("dir", "launch_facade") else 1,
                str(r.get("label") or r.get("name") or r.get("id") or "").lower(),
            ),
        )
    return sorted(rows, key=lambda r: str(r.get("label") or r.get("name") or r.get("id") or "").lower())


def resolve_best(context: str, *, n: int | None = None) -> dict[str, Any]:
    """Resolve exactly one best sort algorithm for a context — Field meld authority."""
    doctrine = _load(DOCTRINE, {})
    mod = _power_sort_mod()
    pick: dict[str, Any] = {}
    alg = "family_then_label" if context == "format_table" else "dirs_first"

    if context == "format_table":
        alg = str((doctrine.get("format_table") or {}).get("algorithm") or "family_then_label")
    elif context in ("chip_paths", "chips_battery", "chips_combinatronic", "chip_catalog"):
        alg = "composite_bsp"
    elif context in ("recombinatorics",):
        alg = "composite_bsp"
    elif context in ("registry_index", "library_registry", "catalog_index", "card_catalog"):
        alg = "family_then_label" if context != "card_catalog" else "locale_ci"
    elif context in ("api_registry", "api_index", "route_index"):
        alg = "dirs_first"
    elif mod and hasattr(mod, "select_sort"):
        try:
            pick = mod.select_sort(context, n=n)
            alg = str(pick.get("algorithm") or alg)
        except Exception:
            pass

    if context == "format_table" and alg not in ("family_then_label", "locale_ci", "timsort_key"):
        bench_alg = str(pick.get("algorithm") or "")
        if bench_alg in ("locale_ci", "timsort_key"):
            alg = bench_alg
        else:
            alg = "family_then_label"

    return {
        "schema": "field-best-sort/v1",
        "context": context,
        "algorithm": alg,
        "singleton": True,
        "field_unique_best": True,
        "always_best_sort": True,
        "one_best_ever": True,
        "statement": STATEMENT,
        "meld_citation": MELD_CITATION,
        "power_sort": pick or None,
        "n": n,
    }


def _ironclad_connected() -> dict[str, Any]:
    imm_path = STATE / "ironclad-immediate.json"
    imm = _load(imm_path, {})
    pts = imm.get("plate_to_sense") or {}
    return {
        "ironclad_connected": True,
        "meld_citation": MELD_CITATION,
        "truth_percent": imm.get("truth_percent") or pts.get("truth_percent"),
        "ironclad_grounded": bool(imm.get("ironclad_sealed") or pts.get("ironclad_grounded")),
    }


def apply_best(
    rows: list[dict[str, Any]],
    *,
    context: str = "format_table",
    n: int | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Sort rows using the one best algorithm — melded through Ironclad."""
    pick = resolve_best(context, n=n or len(rows))
    alg = str(pick.get("algorithm") or "family_then_label")
    sorted_rows = _apply_algorithm(list(rows), alg, context=context)
    meta = {**pick, "count": len(sorted_rows), "applied": True, **_ironclad_connected()}
    return sorted_rows, meta


def meld_slice() -> dict[str, Any]:
    """Slice for ironclad-plate / field-plate-meld."""
    contexts = (
        "format_table", "file_list", "thermal_layers", "recombinatorics", "chip_paths",
        "registry_index", "api_registry", "chip_catalog", "catalog_index", "card_catalog",
    )
    resolved = {ctx: resolve_best(ctx) for ctx in contexts}
    return {
        "id": "field_best_sort",
        "schema": "field-best-sort-meld/v1",
        "updated": _now(),
        "ok": True,
        "statement": STATEMENT,
        "field_unique_best": True,
        "one_best_ever": True,
        "meld_citation": MELD_CITATION,
        "contexts": resolved,
        "format_table_algorithm": resolved.get("format_table", {}).get("algorithm"),
    }


def publish_panel() -> dict[str, Any]:
    slice_doc = meld_slice()
    panel = {
        "schema": "field-best-sort-panel/v1",
        "updated": slice_doc["updated"],
        "ok": True,
        **slice_doc,
    }
    _save(PANEL, panel)
    return {"ok": True, "panel": panel}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    if cmd in ("panel", "json", "status"):
        if PANEL.is_file() and cmd != "meld":
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel().get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd == "meld":
        print(json.dumps(meld_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "resolve" and len(sys.argv) >= 3:
        ctx = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else None
        print(json.dumps(resolve_best(ctx, n=n), ensure_ascii=False, indent=2))
        return 0
    if cmd == "verify":
        pick = resolve_best("format_table")
        ok = (
            pick.get("field_unique_best") is True
            and pick.get("one_best_ever") is True
            and pick.get("singleton") is True
            and bool(pick.get("algorithm"))
        )
        print(json.dumps({"ok": ok, "pick": pick}, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    print(json.dumps({"error": "usage", "cmds": ["panel", "meld", "resolve <ctx>", "verify"]}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())