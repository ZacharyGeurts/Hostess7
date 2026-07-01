#!/usr/bin/env pythong
"""Universal program combinatronic — every language command boils to single g16 facet."""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", Path(__file__).resolve().parents[1]))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", INSTALL / ".nexus-state"))
SG = Path(os.environ.get("SG_ROOT", INSTALL.parent.parent))
from sg_paths import grok16_root

GROK16 = grok16_root()
DOCTRINE = INSTALL / "data" / "field-program-combinatronic-doctrine.json"
SEED = INSTALL / "data" / "field-program-combinatronic-seed.json"
PANEL = STATE / "field-program-combinatronic-panel.json"
BATTERY = STATE / "field-program-combinatronic.json"
LEAF_PREFIX = "prog"


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


def _balance_mod() -> Any | None:
    path = INSTALL / "lib" / "field-combinatronic-balance.py"
    if not path.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location("fpc_balance", path)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    except Exception:
        pass
    return None


def _norm_cmd(cmd: str) -> str:
    return re.sub(r"\s+", " ", str(cmd or "").strip().lower())


def _heuristic_boil(cmd: str, heuristics: dict[str, list[str]]) -> str:
    key = _norm_cmd(cmd)
    if not key:
        return "exec"
    for canonical, keywords in heuristics.items():
        for kw in keywords:
            kw_l = kw.lower()
            if key == kw_l or key.startswith(kw_l) or kw_l in key:
                return canonical
    if any(ch in key for ch in ("+", "-", "*", "/", "%")):
        return "math"
    if key in ("true", "false", "null", "nil", "none", "undefined"):
        return "declare"
    return "exec"


def _grok16_languages() -> dict[str, Any]:
    for path in (
        GROK16 / "data" / "grok16-languages.json",
        INSTALL / "Grok16" / "data" / "grok16-languages.json",
        SG / "Grok16" / "data" / "grok16-languages.json",
    ):
        doc = _load(path, {})
        if doc.get("languages"):
            return doc
    return {}


def _queen_languages() -> dict[str, str]:
    for path in (INSTALL / "Queen" / "data" / "queen-code-languages.json", SG / "NewLatest" / "Queen" / "data" / "queen-code-languages.json"):
        doc = _load(path, {})
        ext = doc.get("extensions") or {}
        if ext:
            return {str(k).lower(): str(v).lower() for k, v in ext.items()}
    return {}


def _language_registry(seed: dict[str, Any], grok: dict[str, Any], queen_ext: dict[str, str]) -> dict[str, dict[str, Any]]:
    packs = dict(seed.get("language_packs") or {})
    registry: dict[str, dict[str, Any]] = {}
    for lang_id, meta in (grok.get("languages") or {}).items():
        lid = str(lang_id).lower()
        registry.setdefault(lid, {
            "id": lid,
            "driver": meta.get("driver"),
            "memory": meta.get("memory"),
            "extensions": meta.get("extensions") or [],
            "belt": meta.get("belt"),
            "dialect": meta.get("dialect"),
            "source": "grok16_languages",
        })
        if meta.get("extends"):
            registry[lid]["extends"] = str(meta["extends"]).lower()
    ext_langs = sorted({v for v in queen_ext.values()})
    for lid in ext_langs:
        registry.setdefault(lid, {"id": lid, "source": "queen_code_languages"})
    for lid, pack in packs.items():
        row = registry.setdefault(str(lid).lower(), {"id": str(lid).lower(), "source": "seed"})
        if pack.get("extends"):
            row["extends"] = str(pack["extends"]).lower()
        row["pack_source"] = "seed"
    for lid in registry:
        if lid not in packs and registry[lid].get("source") != "seed":
            registry[lid]["inferred"] = True
    return registry


def _resolve_pack_commands(lang_id: str, packs: dict[str, Any]) -> dict[str, str]:
    pack = packs.get(lang_id) or {}
    commands = dict(pack.get("commands") or {})
    parent = str(pack.get("extends") or "").lower()
    if parent and parent in packs:
        merged = dict(_resolve_pack_commands(parent, packs))
        merged.update(commands)
        return merged
    return commands


def _canonical_index(seed: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(op["id"]): op for op in (seed.get("canonical_ops") or []) if op.get("id")}


def _combinatorics_leaf(lang: str, command: str, canonical: str) -> str:
    safe_cmd = re.sub(r"[^a-z0-9_]+", "_", _norm_cmd(command))[:48] or "cmd"
    return f"{LEAF_PREFIX}:{lang}:{safe_cmd}:{canonical}"


def _canonical_leaves(canonical: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    leaves: list[dict[str, Any]] = []
    for cid, op in canonical.items():
        leaves.append({
            "id": f"{LEAF_PREFIX}:canonical:{cid}",
            "canonical": cid,
            "label": op.get("label") or cid,
            "kind": "single_combinatronic",
            "facet": "program_combinatronic",
            "runner": op.get("runner") or "native_bsp",
            "belt": op.get("belt") or "belt_2_0",
            "depth": 0,
            "boil_target": True,
        })
    return leaves


def boil_command(
    lang: str,
    command: str,
    *,
    seed: dict[str, Any] | None = None,
    packs: dict[str, Any] | None = None,
    heuristics: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Boil any language command to the single combinatronic canonical op."""
    seed = seed if seed is not None else _load(SEED, {})
    packs = packs if packs is not None else (seed.get("language_packs") or {})
    heuristics = heuristics if heuristics is not None else (seed.get("heuristic_keywords") or {})
    lid = str(lang or "unknown").lower()
    cmd = str(command or "")
    pack_cmds = _resolve_pack_commands(lid, packs)
    norm = _norm_cmd(cmd)
    canonical = (
        pack_cmds.get(cmd)
        or pack_cmds.get(norm)
        or pack_cmds.get(cmd.upper())
        or pack_cmds.get(cmd.lower())
        or pack_cmds.get(norm.upper())
    )
    method = "pack"
    if not canonical:
        canonical = _heuristic_boil(cmd, heuristics)
        method = "heuristic"
    return {
        "lang": lid,
        "command": cmd,
        "canonical": canonical,
        "leaf_id": _combinatorics_leaf(lid, cmd, canonical),
        "boil_method": method,
        "boiled": True,
    }


def build_program_combinatronic(*, force: bool = False) -> dict[str, Any]:
    """Index every language command — 100% boiled to single combinatronic canonical ops."""
    t0 = time.perf_counter()
    bal = _balance_mod()
    balance_gate: dict[str, Any] = {}
    if bal and hasattr(bal, "gate_refresh"):
        balance_gate = bal.gate_refresh(False, force=force)
        if balance_gate.get("skip_reorganize") and not force:
            cached = _load(BATTERY, {})
            if cached.get("commands"):
                elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
                if hasattr(bal, "record_cycle"):
                    bal.record_cycle(reorganized=False, elapsed_ms=elapsed_ms)
                out = dict(cached)
                out["balance_hold"] = True
                out["fast_path"] = True
                out["balance_gate"] = balance_gate
                out["elapsed_ms"] = elapsed_ms
                out["optimized_combinatronic"] = True
                out["combinatronic"] = True
                return out
    seed = _load(SEED, {})
    grok = _grok16_languages()
    queen_ext = _queen_languages()
    packs = seed.get("language_packs") or {}
    heuristics = seed.get("heuristic_keywords") or {}
    canonical = _canonical_index(seed)
    registry = _language_registry(seed, grok, queen_ext)

    command_rows: list[dict[str, Any]] = []
    sources_meta: dict[str, int] = {"seed_packs": len(packs), "grok16": len(grok.get("languages") or {}), "queen_ext": len(set(queen_ext.values()))}

    for lang_id in sorted(registry.keys()):
        pack_cmds = _resolve_pack_commands(lang_id, packs)
        meta = registry[lang_id]
        if pack_cmds:
            for cmd, can in sorted(pack_cmds.items()):
                command_rows.append({
                    "lang": lang_id,
                    "command": cmd,
                    "canonical": can,
                    "driver": meta.get("driver"),
                    "memory": meta.get("memory"),
                    "source": "language_pack",
                    "boil_method": "pack",
                    "combinatorics_leaf": _combinatorics_leaf(lang_id, cmd, can),
                })
        else:
            for cmd in sorted({kw for kws in heuristics.values() for kw in kws})[:24]:
                boiled = boil_command(lang_id, cmd, seed=seed, packs=packs, heuristics=heuristics)
                command_rows.append({
                    "lang": lang_id,
                    "command": cmd,
                    "canonical": boiled["canonical"],
                    "driver": meta.get("driver"),
                    "memory": meta.get("memory"),
                    "source": meta.get("source") or "inferred",
                    "boil_method": boiled["boil_method"],
                    "combinatorics_leaf": boiled["leaf_id"],
                })

    canonical_leaves = _canonical_leaves(canonical)
    command_leaves: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in command_rows:
        leaf_id = row["combinatorics_leaf"]
        if leaf_id in seen:
            continue
        seen.add(leaf_id)
        can = str(row.get("canonical") or "exec")
        cop = canonical.get(can) or {}
        command_leaves.append({
            "id": leaf_id,
            "lang": row.get("lang"),
            "command": row.get("command"),
            "canonical": can,
            "label": f"{row.get('lang')}:{row.get('command')} → {can}",
            "kind": "language_command",
            "facet": "program_combinatronic",
            "runner": cop.get("runner") or "native_bsp",
            "belt": cop.get("belt") or "belt_2_0",
            "boil_method": row.get("boil_method"),
            "depth": 1,
        })

    all_leaves = canonical_leaves + command_leaves
    cached = _load(BATTERY, {})
    incremental_added = 0
    if balance_gate.get("reason") == "new_corpus" and cached.get("combinatorics_leaves") and bal and hasattr(bal, "incremental_merge"):
        all_leaves, incremental_added = bal.incremental_merge(
            cached.get("combinatorics_leaves") or [], all_leaves, id_field="id"
        )
    if bal and hasattr(bal, "stamp_optimized"):
        at_balance = bool(balance_gate.get("balanced")) or balance_gate.get("reason") == "balanced_hold"
        all_leaves = bal.stamp_optimized(all_leaves, balanced=at_balance)
    by_lang: dict[str, int] = {}
    by_canonical: dict[str, int] = {}
    for row in command_rows:
        by_lang[row["lang"]] = by_lang.get(row["lang"], 0) + 1
        c = str(row.get("canonical") or "exec")
        by_canonical[c] = by_canonical.get(c, 0) + 1

    total_cmds = len(command_rows)
    boiled_cmds = sum(1 for r in command_rows if r.get("canonical"))
    boil_pct = round(100.0 * boiled_cmds / max(total_cmds, 1), 2)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
    result = {
        "schema": "field-program-combinatronic/v1",
        "updated": _now(),
        "motto": "Every programming command in every language — 100% boiled to single combinatronic.",
        "ok": True,
        "single_combinatronic": {
            "canonical_op_count": len(canonical),
            "canonical_ops": list(canonical.keys()),
            "terminal_runner": "native_bsp",
            "terminal_emulator": "FieldX86Die",
            "belt_profile": "belt_2_0",
            "boil_pct": boil_pct,
            "boil_complete": boil_pct >= 100.0,
        },
        "sources": sources_meta,
        "counts": {
            "languages": len(registry),
            "commands": total_cmds,
            "command_leaves": len(command_leaves),
            "canonical_leaves": len(canonical_leaves),
            "total_leaves": len(all_leaves),
            "by_lang": by_lang,
            "by_canonical": by_canonical,
        },
        "languages": registry,
        "commands": command_rows,
        "combinatorics_leaves": all_leaves,
        "elapsed_ms": elapsed_ms,
        "balance_gate": balance_gate or None,
        "optimized_combinatronic": bool(balance_gate.get("balanced")),
        "combinatronic": True,
        "all_data_combinatronic": True,
    }
    if bal and hasattr(bal, "record_cycle"):
        bal.record_cycle(
            reorganized=not balance_gate.get("skip_reorganize"),
            elapsed_ms=elapsed_ms,
            incremental_added=incremental_added,
        )
    return result


def publish_panel(*, write_battery: bool = True) -> dict[str, Any]:
    battery = build_program_combinatronic()
    single = battery.get("single_combinatronic") or {}
    panel = {
        "schema": "field-program-combinatronic-panel/v1",
        "updated": battery.get("updated"),
        "ok": battery.get("ok", True),
        "motto": battery.get("motto"),
        "counts": battery.get("counts"),
        "sources": battery.get("sources"),
        "combinatorics_facet": "program_combinatronic",
        "leaf_count": len(battery.get("combinatorics_leaves") or []),
        "sample_leaves": (battery.get("combinatorics_leaves") or [])[:16],
        "single_combinatronic": single,
        "boil_pct": single.get("boil_pct"),
        "boil_complete": single.get("boil_complete"),
        "canonical_ops": single.get("canonical_ops") or [],
        "elapsed_ms": battery.get("elapsed_ms"),
    }
    _save(PANEL, panel)
    if write_battery:
        _save(BATTERY, battery)
    return {"ok": True, "panel": panel, "battery_path": str(BATTERY), "panel_path": str(PANEL)}


def combinatronic_panel(*, refresh: bool = False, state_dir: Path | None = None, force: bool = False) -> dict[str, Any]:
    state = state_dir or STATE
    bal = _balance_mod()
    if refresh and bal and hasattr(bal, "gate_refresh"):
        gate = bal.gate_refresh(refresh, force=force)
        if gate.get("skip_reorganize") and not force:
            refresh = False
    battery = _load(state / "field-program-combinatronic.json", {})
    if refresh or not battery.get("commands"):
        old_state = STATE
        try:
            if state_dir:
                globals()["STATE"] = state  # noqa: PLW0603
            publish_panel(write_battery=True)
            battery = _load(state / "field-program-combinatronic.json", {}) or build_program_combinatronic()
        finally:
            globals()["STATE"] = old_state
    if not battery.get("commands"):
        battery = build_program_combinatronic()

    single = battery.get("single_combinatronic") or {}
    counts = battery.get("counts") or {}
    leaves = battery.get("combinatorics_leaves") or []
    by_lang = [
        {"lang": lang, "commands": n}
        for lang, n in sorted((counts.get("by_lang") or {}).items(), key=lambda x: (-x[1], x[0]))
    ]
    by_canonical = [
        {"canonical": can, "commands": n}
        for can, n in sorted((counts.get("by_canonical") or {}).items(), key=lambda x: (-x[1], x[0]))
    ]

    return {
        "schema": "field-program-combinatronic/v1",
        "updated": battery.get("updated"),
        "ok": True,
        "motto": "Universal Program Combinatronic — one canonical facet, all languages boiled.",
        "facet": "program_combinatronic",
        "combinatorics_facet": "program_combinatronic",
        "single_combinatronic": single,
        "boil_pct": single.get("boil_pct"),
        "boil_complete": single.get("boil_complete"),
        "counts": counts,
        "sources": battery.get("sources"),
        "languages_by_command_count": by_lang[:32],
        "canonical_distribution": by_canonical[:36],
        "combinatorics_leaves": leaves[:96],
        "leaf_count": len(leaves),
        "canonical_leaves": [l for l in leaves if l.get("kind") == "single_combinatronic"],
        "sample_boil": (battery.get("commands") or [])[:24],
        "elapsed_ms": battery.get("elapsed_ms"),
        "balance_gate": battery.get("balance_gate"),
        "optimized_combinatronic": battery.get("optimized_combinatronic"),
        "combinatronic": True,
        "fast_path": battery.get("fast_path", False),
    }


def program_combinatronic_slice(*, state_dir: Path | None = None) -> dict[str, Any]:
    """Light read for combinatorics engine — cache first."""
    state = state_dir or STATE
    cached = _load(state / "field-program-combinatronic.json", {})
    if cached.get("commands"):
        single = cached.get("single_combinatronic") or {}
        return {
            "schema": "field-program-combinatronic-slice/v1",
            "facet": "program_combinatronic",
            "counts": cached.get("counts"),
            "leaf_count": len(cached.get("combinatorics_leaves") or []),
            "combinatorics_leaves": (cached.get("combinatorics_leaves") or [])[:48],
            "single_combinatronic": single,
            "boil_pct": single.get("boil_pct"),
            "boil_complete": single.get("boil_complete"),
            "canonical_op_count": single.get("canonical_op_count"),
            "languages": (cached.get("counts") or {}).get("languages"),
            "cached": True,
        }
    pub = publish_panel(write_battery=True)
    panel = pub.get("panel") or {}
    return {
        "schema": "field-program-combinatronic-slice/v1",
        "facet": "program_combinatronic",
        "counts": panel.get("counts"),
        "leaf_count": panel.get("leaf_count"),
        "combinatorics_leaves": panel.get("sample_leaves") or [],
        "boil_pct": panel.get("boil_pct"),
        "boil_complete": panel.get("boil_complete"),
        "cached": False,
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        if PANEL.is_file():
            print(json.dumps(_load(PANEL), ensure_ascii=False, indent=2))
        else:
            print(json.dumps(publish_panel().get("panel"), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("build", "publish", "battery"):
        print(json.dumps(publish_panel(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("combinatronic", "combinatronics"):
        refresh = "--refresh" in sys.argv[2:]
        print(json.dumps(combinatronic_panel(refresh=refresh), ensure_ascii=False, indent=2))
        return 0
    if cmd == "slice":
        print(json.dumps(program_combinatronic_slice(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "boil":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "usage: boil <lang> <command>"}), ensure_ascii=False)
            return 1
        print(json.dumps(boil_command(sys.argv[2], sys.argv[3]), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({"error": "usage: field-program-combinatronic.py [json|build|combinatronic|slice|boil]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())