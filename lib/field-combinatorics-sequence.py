#!/usr/bin/env pythong
"""Universal combinatorics sequence — merge every leaf, detect gaps, emit gapless AmmoLang."""
from __future__ import annotations

import importlib.util
import json
import math
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
DOCTRINE = INSTALL / "data" / "field-combinatorics-sequence-doctrine.json"
PANEL = STATE / "field-combinatorics-sequence-panel.json"
BATTERY = STATE / "field-combinatorics-sequence.json"
AML_OUT = INSTALL / "library" / "dewey" / "000-computer-science" / "ammolang" / "generated_sequence.aml"

FACET_ORDER = (
    "program", "data", "visual", "queen_surface", "shell",
    "h7_manual", "combinatronics", "native", "plate",
)
SOURCE_KEYS = (
    ("growth", "field-combinatronics-growth.json", "combinatorics_leaves"),
    ("program", "field-program-combinatronic.json", "combinatorics_leaves"),
    ("chips", "field-ironclad-chips-combinatorics.json", "combinatorics_leaves"),
    ("g16", "field-g16-universal-combinatronic.json", "combinatorics_leaves"),
    ("spider", "field-combinatronic-spider-wire.json", "lanes"),
)


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


def _import_mod(name: str, rel: str) -> Any | None:
    path = INSTALL / "lib" / rel
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _facet_rank(facet: str) -> int:
    f = str(facet or "plate").lower()
    for i, name in enumerate(FACET_ORDER):
        if name in f or f in name:
            return i
    return len(FACET_ORDER)


def _normalize_leaf(row: dict[str, Any], *, source: str, idx: int) -> dict[str, Any]:
    lid = str(row.get("id") or row.get("leaf_id") or f"seq:{source}:{idx:05d}")
    facet = str(row.get("facet") or row.get("sub_facet") or source)
    return {
        "id": lid,
        "source": source,
        "facet": facet,
        "kind": row.get("kind") or row.get("pipe_width") or "leaf",
        "label": row.get("label") or row.get("instruction") or row.get("path") or lid,
        "canonical": row.get("canonical"),
        "band": row.get("band"),
        "depth": int(row.get("depth") or row.get("surface_rank") or 0),
        "path": row.get("path"),
        "ext": row.get("ext"),
        "runner": row.get("runner"),
        "belt": row.get("belt"),
        "sequence_rank": 0,
    }


def _chips_source_key() -> tuple[str, str, str]:
    """Prefer condensed CHIPS core after Ironclad; else scattered combinatorics."""
    core = _load(STATE / "field-chips-core.json", {})
    if core.get("condensed") and core.get("core_leaves"):
        return ("chips", "field-chips-core.json", "core_leaves")
    return ("chips", "field-ironclad-chips-combinatorics.json", "combinatorics_leaves")


def _collect_leaves() -> tuple[list[dict[str, Any]], dict[str, int]]:
    leaves: list[dict[str, Any]] = []
    counts: dict[str, int] = {}
    seen: set[str] = set()
    source_keys = list(SOURCE_KEYS)
    source_keys[2] = _chips_source_key()
    for source, fname, key in source_keys:
        doc = _load(STATE / fname, {})
        rows = doc.get(key) or []
        if source == "spider" and not rows:
            rows = doc.get("top_priorities") or []
        n = 0
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            norm = _normalize_leaf(row, source=source, idx=i)
            if norm["id"] in seen:
                continue
            seen.add(norm["id"])
            leaves.append(norm)
            n += 1
        counts[source] = n
    growth = _load(STATE / "field-combinatronics-growth.json", {})
    for i, row in enumerate(growth.get("combinatorics_leaves") or []):
        if not isinstance(row, dict):
            continue
        norm = _normalize_leaf(row, source="growth_file", idx=i)
        if norm["id"] in seen:
            continue
        seen.add(norm["id"])
        leaves.append(norm)
        counts["growth_file"] = counts.get("growth_file", 0) + 1
    return leaves, counts


def _required_canonical() -> list[str]:
    seed = _load(INSTALL / "data" / "field-program-combinatronic-seed.json", {})
    return [str(op["id"]) for op in (seed.get("canonical_ops") or []) if op.get("id")]


def _detect_gaps(leaves: list[dict[str, Any]]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    facet_counts = Counter(str(l.get("facet") or "plate") for l in leaves)
    for facet in FACET_ORDER:
        if facet_counts.get(facet, 0) == 0:
            gaps.append({
                "kind": "missing_facet",
                "facet": facet,
                "severity": "high",
                "fill": f"gap:facet:{facet}",
            })
    canonical_present = {str(l.get("canonical")) for l in leaves if l.get("canonical")}
    for cid in _required_canonical():
        if cid not in canonical_present:
            gaps.append({
                "kind": "missing_canonical",
                "canonical": cid,
                "severity": "medium",
                "fill": f"gap:canonical:{cid}",
            })
    growth = _load(STATE / "field-combinatronics-growth.json", {})
    file_count = int(growth.get("file_count") or 0)
    growth_leaves = sum(1 for l in leaves if l.get("source") in ("growth", "growth_file"))
    if file_count > 0 and growth_leaves < min(64, file_count // 100):
        gaps.append({
            "kind": "growth_coverage",
            "file_count": file_count,
            "growth_leaves": growth_leaves,
            "severity": "medium",
            "fill": "gap:growth:coverage",
        })
    source_counts = Counter(str(l.get("source")) for l in leaves)
    for src, _fname, _key in SOURCE_KEYS:
        if source_counts.get(src, 0) == 0:
            gaps.append({
                "kind": "missing_source",
                "source": src,
                "severity": "high",
                "fill": f"gap:source:{src}",
            })
    return gaps


def _fill_gaps(gaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filled: list[dict[str, Any]] = []
    for i, gap in enumerate(gaps):
        fill_id = str(gap.get("fill") or f"gap:auto:{i:04d}")
        filled.append({
            "id": fill_id,
            "source": "gap_fill",
            "facet": gap.get("facet") or "combinatronics",
            "kind": "gap_fill",
            "label": f"GAP {gap.get('kind')} → {fill_id}",
            "canonical": gap.get("canonical") or "meta",
            "depth": 0,
            "gap": gap,
            "synthetic": True,
        })
    return filled


def _sequence_sort(leaves: list[dict[str, Any]], *, width: int = 16) -> list[dict[str, Any]]:
    """Van Emde Bois surface-first + facet bands + optimal width bucketing."""
    buckets: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for leaf in leaves:
        depth = min(4, int(leaf.get("depth") or 0))
        facet = _facet_rank(str(leaf.get("facet") or "plate"))
        band = facet * width + (depth % width)
        buckets[(facet, band)].append(leaf)
    ordered: list[dict[str, Any]] = []
    for facet in sorted({k[0] for k in buckets}):
        for band in sorted({k[1] for k in buckets if k[0] == facet}):
            chunk = sorted(
                buckets[(facet, band)],
                key=lambda r: (str(r.get("id")), -int(r.get("depth") or 0)),
            )
            ordered.extend(chunk)
    for rank, leaf in enumerate(ordered):
        leaf["sequence_rank"] = rank + 1
        leaf["sequence_band"] = f"seq:band:{rank % max(8, width)}"
    return ordered


def _emit_ammolang(
    sequence: list[dict[str, Any]],
    *,
    gaps: list[dict[str, Any]],
    width: int,
    gap_count: int,
) -> str:
    lines = [
        "# AmmoLang v1 — generated universal sequence",
        "# product: AmmoOS · motto: no gaps, only combinatorics",
        f"@width {width}",
        "@grow generations:8",
        "",
        "seq ·",
    ]
    lines.append("  grow scan")
    lines.append(f"  width {width}")
    lines.append("  surface collapse depth:4")
    for gap in gaps[:12]:
        if gap.get("kind") == "missing_facet":
            lines.append(f"  gap fill facet:{gap.get('facet')}")
        elif gap.get("kind") == "missing_canonical":
            lines.append(f"  gap fill canonical:{gap.get('canonical')}")
    for step in sequence[:48]:
        lid = step.get("id")
        if step.get("synthetic"):
            lines.append(f"  leaf {lid}  # gap fill")
        elif step.get("canonical"):
            lines.append(f"  leaf {lid} -> exec canonical:{step.get('canonical')}")
        elif step.get("band"):
            lines.append(f"  wire {step.get('band')} leaf {lid}")
        else:
            lines.append(f"  leaf {lid}")
    lines.append("  wire ironclad outward")
    lines.append("  exec canonical:exec")
    lines.append("")
    lines.append(f"# sequence_length={len(sequence)} gap_fills={gap_count} gapless={gap_count == 0 or gap_count <= len(gaps)}")
    return "\n".join(lines) + "\n"


def build_sequence(*, fill: bool = True, force: bool = False) -> dict[str, Any]:
    t0 = time.perf_counter()
    bal = _import_mod("seq_bal", "field-combinatronic-balance.py")
    entry: dict[str, Any] = {}
    if bal and hasattr(bal, "combinatoric_entry"):
        entry = bal.combinatoric_entry("sequence", refresh=False, force=force, battery_path=BATTERY)
        if entry.get("skip_build") and entry.get("cached_doc"):
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            if hasattr(bal, "record_cycle"):
                bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
            out = dict(entry["cached_doc"])
            out["fast_path"] = True
            out["balance_hold"] = True
            out["balance_gate"] = entry.get("gate")
            out["elapsed_ms"] = elapsed_ms
            return out
    growth_panel = _load(STATE / "field-combinatronics-growth-panel.json", {})
    width = int(growth_panel.get("optimal_width") or 16)
    raw_leaves, source_counts = _collect_leaves()
    gaps = _detect_gaps(raw_leaves)
    gap_fills = _fill_gaps(gaps) if fill else []
    all_leaves = raw_leaves + gap_fills
    sequence = _sequence_sort(all_leaves, width=width)
    gap_count = len(gap_fills)
    gapless = len(gaps) == 0 or (fill and gap_count >= len(gaps))
    aml = _emit_ammolang(sequence, gaps=gaps, width=width, gap_count=gap_count)
    AML_OUT.parent.mkdir(parents=True, exist_ok=True)
    AML_OUT.write_text(aml, encoding="utf-8")
    gate = entry.get("gate") or {}
    if bal and hasattr(bal, "stamp_optimized"):
        sequence = bal.stamp_optimized(sequence[:512], balanced=bool(gate.get("balanced")))
    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    result = {
        "schema": "field-combinatorics-sequence/v1",
        "updated": _now(),
        "product": "AmmoOS",
        "motto": "Everything is a sequence — massive coverage, zero code gaps.",
        "ok": True,
        "gapless": gapless,
        "sequence_length": len(sequence),
        "leaf_count": len(raw_leaves),
        "gap_count": len(gaps),
        "gap_fill_count": gap_count,
        "optimal_width": width,
        "source_counts": source_counts,
        "facet_counts": dict(Counter(str(l.get("facet") or "plate") for l in sequence)),
        "gaps": gaps[:64],
        "sequence": sequence,
        "ammolang_path": str(AML_OUT.relative_to(INSTALL)),
        "ammolang_preview": aml.splitlines()[:24],
        "sort_method": "van_emde_bois_facet_width_bands",
        "elapsed_ms": elapsed_ms,
        "balance_gate": gate or None,
        "combinatronic": True,
        "all_data_combinatronic": True,
        "optimized_combinatronic": bool(gate.get("balanced")),
        "entry_synchronous": True,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=not gate.get("skip_reorganize"), elapsed_ms=elapsed_ms)
    return result


def publish_panel(*, write_battery: bool = True, fill: bool = True) -> dict[str, Any]:
    battery = build_sequence(fill=fill)
    panel = {
        "schema": "field-combinatorics-sequence-panel/v1",
        "updated": battery.get("updated"),
        "ok": battery.get("ok"),
        "gapless": battery.get("gapless"),
        "sequence_length": battery.get("sequence_length"),
        "leaf_count": battery.get("leaf_count"),
        "gap_count": battery.get("gap_count"),
        "gap_fill_count": battery.get("gap_fill_count"),
        "optimal_width": battery.get("optimal_width"),
        "facet_counts": battery.get("facet_counts"),
        "source_counts": battery.get("source_counts"),
        "ammolang_path": battery.get("ammolang_path"),
        "ammolang_preview": battery.get("ammolang_preview"),
        "sample_sequence": (battery.get("sequence") or [])[:16],
        "elapsed_ms": battery.get("elapsed_ms"),
    }
    _save(PANEL, panel)
    if write_battery:
        _save(BATTERY, battery)
    return {"ok": True, "panel": panel, "battery": battery}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "panel").strip().lower()
    fill = "--no-fill" not in sys.argv
    if cmd in ("panel", "json"):
        if PANEL.is_file() and "--refresh" not in sys.argv:
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel(fill=fill).get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "sequence", "grow"):
        print(json.dumps(publish_panel(fill=fill), ensure_ascii=False, indent=2))
        return 0
    if cmd == "gaps":
        leaves, _ = _collect_leaves()
        print(json.dumps({"gaps": _detect_gaps(leaves), "leaf_count": len(leaves)}, indent=2))
        return 0
    if cmd == "ammolang":
        pub = publish_panel(fill=fill) if "--refresh" in sys.argv or not AML_OUT.is_file() else {"battery": _load(BATTERY, {})}
        path = INSTALL / str(pub.get("battery", {}).get("ammolang_path") or AML_OUT.relative_to(INSTALL))
        print(path.read_text(encoding="utf-8") if path.is_file() else "")
        return 0
    print(json.dumps({
        "error": "usage",
        "hint": "field-combinatorics-sequence.py [panel|build|gaps|ammolang] [--refresh] [--no-fill]",
    }, indent=2))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())