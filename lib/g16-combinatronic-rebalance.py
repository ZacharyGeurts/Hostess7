#!/usr/bin/env pythong
"""G16 combinatronic rebalance — condense, combine, connect every chip and language optimally."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()


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


def _py_json(script: Path, args: list[str], *, timeout: int = 120) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": f"missing:{script.name}"}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "SG_ROOT": str(SG), "GROK16_ROOT": str(GROK16)}
    proc = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, timeout=timeout, env=env)
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": proc.returncode == 0, "stdout": (proc.stdout or "")[:300], "stderr": (proc.stderr or "")[:300]}


def _import_combinatorics() -> Any | None:
    for path in (GROK16 / "lib" / "field_combinatorics.py"):
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("field_combinatorics_rebal", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


def _balance_mod() -> Any | None:
    return _import_mod("comb_balance", "field-combinatronic-balance.py")


def rebalance(*, refresh: bool = True, force: bool = False) -> dict[str, Any]:
    """Refresh chip + program batteries, rebalance unified leaf ordering."""
    t0 = __import__("time").perf_counter()
    bal = _balance_mod()
    gate: dict[str, Any] = {}
    if bal and hasattr(bal, "gate_refresh"):
        gate = bal.gate_refresh(refresh, force=force)
        if gate.get("skip_reorganize") and not force:
            fp = bal.fast_path_response("universal") if hasattr(bal, "fast_path_response") else {}
            elapsed = round((__import__("time").perf_counter() - t0) * 1000, 3)
            if hasattr(bal, "record_cycle"):
                bal.record_cycle(reorganized=False, elapsed_ms=elapsed)
            return {
                "schema": "g16-combinatronic-rebalance/v1",
                "updated": _now(),
                "action": "rebalance",
                "ok": True,
                "skipped": True,
                "reason": gate.get("reason", "balanced_hold"),
                "balance_gate": gate,
                "fast_path": fp,
                "elapsed_ms": elapsed,
                "motto": "Balance hold — no reorganize unless new files or chips.",
            }
        refresh = bool(gate.get("effective_refresh", refresh))

    steps: list[dict[str, Any]] = []
    if gate:
        steps.append({"step": "balance_gate", **gate})
    if refresh:
        steps.append({"step": "ironclad_chips", **_py_json(INSTALL / "lib" / "field-ironclad-chips-combinatorics.py", ["publish"])})
        steps.append({"step": "chips_plate_stack", **_py_json(INSTALL / "lib" / "field-chips-plate-stack.py", ["publish", "--refresh"])})
        steps.append({"step": "program_combinatronic", **_py_json(INSTALL / "lib" / "field-program-combinatronic.py", ["combinatronic", "--refresh"])})
    uni = _import_mod("g16_uni", "field-g16-universal-combinatronic.py")
    if uni and hasattr(uni, "publish_panel"):
        pub = uni.publish_panel(refresh=refresh, write_battery=True)
        battery = _load(STATE / "field-g16-universal-combinatronic.json", {})
        steps.append({
            "step": "rebalance",
            "ok": pub.get("ok", True),
            "leaf_count": (pub.get("panel") or {}).get("leaf_count"),
            "top": ((battery.get("rebalance") or {}).get("top_leaves") or [])[:6],
        })
    else:
        steps.append({"step": "rebalance", "ok": False, "error": "universal_missing"})
    elapsed = round((__import__("time").perf_counter() - t0) * 1000, 3)
    out = {
        "schema": "g16-combinatronic-rebalance/v1",
        "updated": _now(),
        "action": "rebalance",
        "ok": all(s.get("ok", True) for s in steps),
        "steps": steps,
        "balance_gate": gate or None,
        "reorganized": True,
        "elapsed_ms": elapsed,
        "motto": "Every chip and every language — optimally reordered.",
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(reorganized=True, elapsed_ms=elapsed)
    return out


def dimensions_consolidate(*, metadata_only: bool = True) -> dict[str, Any]:
    """Configure plate width × length — fuse condense groups into fewer meta-plates."""
    dim = _import_mod("plate_dimensions", "field-plate-dimensions.py")
    if dim and hasattr(dim, "publish_panel"):
        pub = dim.publish_panel(write_battery=True, metadata_only=metadata_only)
        panel = pub.get("panel") or {}
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "dimensions",
            "ok": pub.get("ok", True),
            "group_count": panel.get("group_count"),
            "meta_plate_count": panel.get("meta_plate_count"),
            "dimensions": panel.get("dimensions"),
            "travel_reduction_pct": (panel.get("travel") or {}).get("reduction_pct"),
            "motto": "Width × length consolidation — fewer plates, same function, less travel.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "dimensions", "ok": False, "error": "plate_dimensions_missing"}


def condense(*, metadata_only: bool = True) -> dict[str, Any]:
    """Condense plate groups + universal bands."""
    steps: list[dict[str, Any]] = []
    mod = _import_combinatorics()
    truth = _load(STATE / "g16-truth-blocks-panel.json", {})
    if mod and hasattr(mod, "condense_plates"):
        condense_out = mod.condense_plates(state_dir=STATE, truth_panel=truth, metadata_only=metadata_only)
        steps.append({"step": "plate_condense", **condense_out})
    else:
        dim = _import_mod("plate_dimensions", "field-plate-dimensions.py")
        if dim and hasattr(dim, "condense_plates"):
            condense_out = dim.condense_plates(state_dir=STATE, truth_panel=truth, metadata_only=metadata_only)
            steps.append({"step": "plate_condense", **condense_out})
    steps.append({"step": "dimensions_consolidate", **dimensions_consolidate(metadata_only=metadata_only)})
    uni = _load(STATE / "field-g16-universal-combinatronic.json", {})
    if not uni.get("condense_bands"):
        rebalance(refresh=False)
        uni = _load(STATE / "field-g16-universal-combinatronic.json", {})
    steps.append({
        "step": "universal_bands",
        "ok": bool(uni.get("condense_bands")),
        "band_count": len(uni.get("condense_bands") or []),
        "bands": (uni.get("condense_bands") or [])[:12],
    })
    return {
        "schema": "g16-combinatronic-rebalance/v1",
        "updated": _now(),
        "action": "condense",
        "ok": all(s.get("ok", True) for s in steps),
        "steps": steps,
    }


def combine() -> dict[str, Any]:
    """Combine chips + programs into one universal panel and refresh combinatorics."""
    steps: list[dict[str, Any]] = []
    steps.append({"step": "rebalance", **rebalance(refresh=True)})
    mod = _import_combinatorics()
    if mod and hasattr(mod, "publish_panel"):
        pub = mod.publish_panel(state_dir=STATE, light=True)
        steps.append({"step": "combinatorics_publish", **pub})
    bridge = _import_mod("bridge", "field-plate-combinatorics-bridge.py")
    if bridge and hasattr(bridge, "build_bridge"):
        bdoc = bridge.build_bridge(write=True)
        steps.append({"step": "bridge", "ok": bdoc.get("ok"), "pattern": (bdoc.get("exec_posture") or {}).get("pattern_id")})
    uni = _load(STATE / "field-g16-universal-combinatronic-panel.json", {})
    return {
        "schema": "g16-combinatronic-rebalance/v1",
        "updated": _now(),
        "action": "combine",
        "ok": all(s.get("ok", True) for s in steps),
        "steps": steps,
        "universal": {
            "leaf_count": uni.get("leaf_count"),
            "counts": uni.get("counts"),
            "sub_facets": uni.get("sub_facets"),
        },
    }


def connect() -> dict[str, Any]:
    """Build chip ↔ language connection graph."""
    uni_mod = _import_mod("g16_uni", "field-g16-universal-combinatronic.py")
    if uni_mod and hasattr(uni_mod, "build_g16_universal"):
        doc = uni_mod.build_g16_universal(refresh=False)
        if uni_mod and hasattr(uni_mod, "publish_panel"):
            uni_mod.publish_panel(refresh=False, write_battery=True)
    else:
        doc = _load(STATE / "field-g16-universal-combinatronic.json", {})
    connections = doc.get("connections") or []
    by_isa: dict[str, int] = {}
    for edge in connections:
        isa = str(edge.get("isa") or "unknown")
        by_isa[isa] = by_isa.get(isa, 0) + 1
    return {
        "schema": "g16-combinatronic-rebalance/v1",
        "updated": _now(),
        "action": "connect",
        "ok": bool(connections),
        "connection_count": len(connections),
        "by_isa": by_isa,
        "sample": connections[:24],
        "motto": "Chip ISA ↔ language driver — optimal g16 edges.",
    }


def spider_wire(*, optimize: bool = True) -> dict[str, Any]:
    """Ironclad outward spider wire — neural lane priority, bottleneck elimination."""
    sw = _import_mod("spider_wire", "field-combinatronic-spider-wire.py")
    if sw and hasattr(sw, "publish_panel"):
        pub = sw.publish_panel(optimize=optimize)
        panel = pub.get("panel") or {}
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "spider_wire",
            "ok": pub.get("ok", True),
            "view": "ironclad_outward",
            "wire_count": panel.get("wire_count"),
            "lane_count": panel.get("lane_count"),
            "bottleneck_count": panel.get("bottleneck_count"),
            "optimized": panel.get("optimized"),
            "motto": "Ironclad on out — spider wire, cool lanes, zero bottlenecks.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "spider_wire", "ok": False, "error": "spider_wire_missing"}


def growth_scan() -> dict[str, Any]:
    """Whole-system file combinatorics — surface collapse + optimal width."""
    g = _import_mod("growth", "field-combinatronics-growth.py")
    if g and hasattr(g, "publish_panel"):
        pub = g.publish_panel()
        panel = pub.get("panel") or {}
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "growth",
            "ok": pub.get("ok", True),
            "file_count": panel.get("file_count"),
            "optimal_width": panel.get("optimal_width"),
            "best_surface_score": panel.get("best_surface_score"),
            "motto": "Scan every file — collapse to surface — optimal compute width.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "growth", "ok": False, "error": "growth_missing"}


def sequence_build(*, fill: bool = True) -> dict[str, Any]:
    """Universal combinatorics sequence — merge all leaves, fill gaps, emit AmmoLang."""
    seq = _import_mod("sequence", "field-combinatorics-sequence.py")
    if seq and hasattr(seq, "publish_panel"):
        pub = seq.publish_panel(fill=fill)
        panel = pub.get("panel") or {}
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "sequence",
            "ok": pub.get("ok", True),
            "gapless": panel.get("gapless"),
            "sequence_length": panel.get("sequence_length"),
            "gap_count": panel.get("gap_count"),
            "gap_fill_count": panel.get("gap_fill_count"),
            "ammolang_path": panel.get("ammolang_path"),
            "motto": "Everything is a sequence — massive coverage, zero code gaps.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "sequence", "ok": False, "error": "sequence_missing"}


def ammolang_panel(*, refresh: bool = False) -> dict[str, Any]:
    """AmmoLang — AI-native combinatorics language panel."""
    aml = _import_mod("ammolang", "field-ammolang.py")
    if aml and hasattr(aml, "publish_panel"):
        pub = aml.publish_panel(refresh=refresh)
        panel = pub.get("panel") or {}
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "ammolang",
            "ok": pub.get("ok", True),
            "version": panel.get("version"),
            "combinator_count": panel.get("combinator_count"),
            "example_count": panel.get("example_count"),
            "motto": "AmmoLang — pure combinatorics for AI operators.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "ammolang", "ok": False, "error": "ammolang_missing"}


def teach_universal_neural(*, force: bool = False) -> dict[str, Any]:
    """Teach combinamatrix — one neural builds whole Universal."""
    un = _import_mod("universal_neural", "field-universal-neural.py")
    if un and hasattr(un, "teach"):
        doc = un.teach(force=force)
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "teach_universal_neural",
            "ok": doc.get("ok", True) and not doc.get("quarantined"),
            "generation": doc.get("generation"),
            "neural_id": doc.get("neural_id"),
            "combinamatrix": doc.get("combinamatrix"),
            "universal_built": doc.get("universal_built"),
            "motto": "Teach combinamatrix — build whole Universal in one neural.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "teach_universal_neural", "ok": False, "error": "universal_neural_missing"}


def chips_core(*, refresh: bool = True) -> dict[str, Any]:
    cc = _import_mod("chips_core", "field-chips-core.py")
    if cc and hasattr(cc, "publish_panel"):
        pub = cc.publish_panel(refresh=refresh, write_core=True)
        panel = pub.get("panel") or {}
        core = pub.get("core") or {}
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "chips_core",
            "ok": pub.get("ok", True),
            "condensed": panel.get("condensed"),
            "pending": panel.get("pending"),
            "ironclad_sealed": panel.get("ironclad_sealed"),
            "core_module_count": (panel.get("counts") or {}).get("core_modules"),
            "chip_count": (panel.get("counts") or {}).get("chips"),
            "compression_ratio": (panel.get("counts") or {}).get("compression_ratio"),
            "posture": core.get("posture") or panel.get("posture"),
            "motto": "CHIPS core — condense scattered layers after Ironclad.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "chips_core", "ok": False, "error": "chips_core_missing"}


def chips_plate_stack(*, refresh: bool = True) -> dict[str, Any]:
    cps = _import_mod("chips_plate_stack", "field-chips-plate-stack.py")
    if cps and hasattr(cps, "publish_panel"):
        pub = cps.publish_panel(refresh=refresh, write_battery=True)
        panel = pub.get("panel") or {}
        battery = pub.get("battery") or {}
        deriv = battery.get("plate_rebalance_derivatives") or panel.get("plate_rebalance_derivatives") or {}
        deriv_meta = deriv.get("meta") or {}
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "chips_plate_stack",
            "ok": pub.get("ok", True),
            "module_count": (panel.get("counts") or {}).get("modules"),
            "sovereign_time_only": (panel.get("connection_policy") or {}).get("sovereign_time_only"),
            "derivatives": {
                "ok": deriv.get("ok"),
                "super_quick": deriv.get("super_quick") or deriv_meta.get("fast_path"),
                "elapsed_ms": deriv_meta.get("elapsed_ms_total") or deriv_meta.get("elapsed_ms"),
                "organize_gain_derivative": deriv.get("organize_gain_derivative"),
                "method": deriv_meta.get("method"),
                "top_marginal": deriv_meta.get("top_marginal"),
            },
            "ironclad": (battery.get("ironclad_chain") or {}),
            "motto": "CHIPS Iron + Steel plate — THE sort + Ironclad truth throughout.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "chips_plate_stack", "ok": False, "error": "chips_plate_stack_missing"}


def plate_rebalance_derivatives() -> dict[str, Any]:
    deriv = _import_mod("plate_deriv", "field-plate-rebalance-derivatives.py")
    stack = _load(STATE / "field-chips-plate-stack.json", {})
    modules = list(stack.get("modules") or [])
    if deriv and hasattr(deriv, "rebalance_plate_stack") and modules:
        doc = deriv.rebalance_plate_stack(
            modules,
            iron_meta=(stack.get("layers") or {}).get("iron_plate"),
            truth_percent=float((stack.get("layers") or {}).get("ironclad", {}).get("truth_percent") or 0),
        )
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "plate_rebalance_derivatives",
            **doc,
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "plate_rebalance_derivatives", "ok": False, "error": "derivatives_missing"}


def steel_neural_plates(*, refresh: bool = True) -> dict[str, Any]:
    snp = _import_mod("steel_plates", "field-steel-neural-plates.py")
    if snp and hasattr(snp, "publish_panel"):
        pub = snp.publish_panel(refresh=refresh, write_battery=True)
        panel = pub.get("panel") or {}
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "steel_neural_plates",
            "ok": pub.get("ok", True),
            "plate_count": panel.get("plate_count"),
            "connection_depth": panel.get("connection_depth"),
            "wires": panel.get("wires"),
            "motto": "Steel Neural Plates — deep combinatoric connection management.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "steel_neural_plates", "ok": False, "error": "steel_neural_plates_missing"}


def combinamatrix_build(*, refresh: bool = True) -> dict[str, Any]:
    cm = _import_mod("combinamatrix", "field-combinamatrix.py")
    if cm and hasattr(cm, "publish_panel"):
        pub = cm.publish_panel(refresh=refresh, write_battery=True)
        panel = pub.get("panel") or {}
        return {
            "schema": "g16-combinatronic-rebalance/v1",
            "updated": _now(),
            "action": "combinamatrix",
            "ok": pub.get("ok", True),
            "dimensions": panel.get("dimensions"),
            "cell_count": panel.get("cell_count"),
            "motto": "Combinamatrix — width × length leaf pack.",
        }
    return {"schema": "g16-combinatronic-rebalance/v1", "action": "combinamatrix", "ok": False, "error": "combinamatrix_missing"}


def optimal(*, full: bool = False) -> dict[str, Any]:
    """Full optimal cycle: growth → sequence → ammolang → rebalance → … → spider_wire → studio."""
    steps: list[dict[str, Any]] = []
    steps.append(growth_scan())
    steps.append(dimensions_consolidate(metadata_only=not full))
    steps.append(combinamatrix_build(refresh=True))
    steps.append(steel_neural_plates(refresh=True))
    steps.append(chips_plate_stack(refresh=True))
    steps.append(chips_core(refresh=True))
    steps.append(teach_universal_neural(force=full))
    steps.append(sequence_build(fill=True))
    steps.append(ammolang_panel(refresh=True))
    steps.append(rebalance(refresh=True))
    steps.append(condense(metadata_only=not full))
    steps.append(combine())
    steps.append(connect())
    steps.append(spider_wire(optimize=True))
    studio = _import_mod("studio", "field-combinatorics-studio.py")
    if studio and hasattr(studio, "run_action"):
        action = "full" if full else "cycle"
        sc = studio.run_action(action)
        steps.append({"step": f"studio_{action}", "ok": sc.get("ok"), "action": action})
    return {
        "schema": "g16-combinatronic-optimal/v1",
        "updated": _now(),
        "action": "optimal",
        "full": full,
        "ok": all(s.get("ok", True) for s in steps),
        "steps": steps,
        "motto": "Rebalance · condense · combine · connect — the amazing optimal g16 fashion.",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "optimal").strip().lower()
    full = "--full" in sys.argv[2:]
    refresh = "--refresh" in sys.argv[2:] or cmd in ("rebalance", "optimal", "combine")
    handlers = {
        "rebalance": lambda: rebalance(refresh=refresh),
        "condense": lambda: condense(metadata_only=not full),
        "combine": combine,
        "connect": connect,
        "spider_wire": lambda: spider_wire(optimize="--no-optimize" not in sys.argv),
        "growth": growth_scan,
        "dimensions": lambda: dimensions_consolidate(metadata_only=not full),
        "combinamatrix": lambda: combinamatrix_build(refresh=refresh),
        "steel_plates": lambda: steel_neural_plates(refresh=refresh),
        "steel_neural_plates": lambda: steel_neural_plates(refresh=refresh),
        "chips_plate_stack": lambda: chips_plate_stack(refresh=refresh),
        "chips_iron_steel": lambda: chips_plate_stack(refresh=refresh),
        "chips_core": lambda: chips_core(refresh=refresh),
        "plate_derivatives": plate_rebalance_derivatives,
        "derivatives": plate_rebalance_derivatives,
        "teach_neural": lambda: teach_universal_neural(force=full),
        "universal_neural": lambda: teach_universal_neural(force=full),
        "sequence": lambda: sequence_build(fill="--no-fill" not in sys.argv),
        "ammolang": lambda: ammolang_panel(refresh=refresh),
        "optimal": lambda: optimal(full=full),
        "all": lambda: optimal(full=full),
    }
    fn = handlers.get(cmd)
    if not fn:
        print(json.dumps({
            "error": "usage",
            "cmds": list(handlers.keys()),
            "flags": ["--refresh", "--full"],
        }, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(fn(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())