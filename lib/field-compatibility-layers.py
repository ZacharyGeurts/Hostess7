#!/usr/bin/env pythong
"""Compatibility layers — efficient auto-stack replacing operator combinatorics."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
SG = Path(os.environ.get("SG_ROOT", str(INSTALL.parent.parent if INSTALL.name == "nexus-shield" else INSTALL.parent)))
from sg_paths import grok16_root

GROK16 = grok16_root()
QUEEN = Path(os.environ.get("QUEEN_ROOT", str(INSTALL.parent / "Queen" if (INSTALL.parent / "Queen").is_dir() else SG / "NewLatest" / "Queen")))
DOCTRINE = INSTALL / "data" / "field-compatibility-layers-doctrine.json"
PANEL = STATE / "field-compatibility-layers-panel.json"


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


def _run_script(rel: str, *args: str, timeout: int = 90) -> dict[str, Any]:
    for base in (INSTALL / "lib", QUEEN / "lib", Path(__file__).resolve().parent):
        path = base / rel if "/" not in rel else base.parent / rel
        if rel.startswith("Queen/"):
            path = SG / "NewLatest" / rel
        elif rel.startswith("Grok16/"):
            path = GROK16 / rel.split("/", 1)[1]
        else:
            path = base / rel
        if not path.is_file():
            continue
        env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "SG_ROOT": str(SG), "GROK16_ROOT": str(GROK16)}
        try:
            proc = subprocess.run(
                [sys.executable, str(path), *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            return json.loads(proc.stdout or "{}")
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            return {"ok": False, "error": "run_failed", "script": str(path)}
    return {"ok": False, "error": "script_missing", "script": rel}


def _import_mod(name: str, rel: str) -> Any | None:
    for base in (INSTALL / "lib", QUEEN / "lib", Path(__file__).resolve().parent):
        path = base / rel
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location(name, path)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _layer_status(*, live: bool, summary: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"live": live, "ok": live, "summary": summary, "detail": detail or {}}


def probe_substrate() -> dict[str, Any]:
    kilroy_proc = Path("/proc/kilroy_field").is_dir()
    kilroy_dev = Path("/dev/kilroy_field").exists()
    compat_make = (SG / "compat" / "linux-7.1.1" / "Makefile").is_file()
    legacy_make = (SG / "linux-kernel" / "linux-7.1.1" / "Makefile").is_file()
    underlay = _load(STATE / "field-underlay-panel.json", {})
    live = kilroy_proc or kilroy_dev or compat_make or legacy_make
    pin = "compat/linux-7.1.1" if compat_make else ("linux-kernel/linux-7.1.1" if legacy_make else "unpinned")
    return {
        "id": "substrate",
        "index": 0,
        "label": "Substrate",
        "glyph": "⬡",
        "color": "#64748b",
        **_layer_status(
            live=live,
            summary=f"{'Field die live' if kilroy_proc or kilroy_dev else 'Guest substrate'} · {pin}",
            detail={
                "kilroy_proc": kilroy_proc,
                "kilroy_dev": kilroy_dev,
                "compat_pin": pin,
                "underlay_verdict": underlay.get("verdict"),
            },
        ),
    }


def _always_optimal_panel() -> dict[str, Any]:
    for path in (GROK16 / "data" / "g16-always-optimal-panel.json", STATE / "g16-always-optimal-panel.json"):
        doc = _load(path, {})
        if doc.get("always_optimal"):
            return doc
    return _load(GROK16 / "data" / "g16-always-optimal-panel.json", {})


def _locational_sitrep_slice() -> dict[str, Any]:
    doc = _load(STATE / "field-locational-sitrep-plate.json", {})
    if doc.get("sitrep") or doc.get("sections"):
        return {
            "ok": bool(doc.get("ok") or doc.get("plated")),
            "verdict": doc.get("verdict"),
            "summary": doc.get("summary"),
            "sections": doc.get("sections") or {},
            "this_one": doc.get("this_one"),
            "movement": doc.get("movement"),
            "gps_ready": doc.get("gps_ready"),
            "spatial_pass_ok": doc.get("spatial_pass_ok"),
            "source": "field-locational-sitrep-plate.json",
        }
    ls_py = INSTALL / "lib" / "field-locational-sitrep-plate.py"
    if ls_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("compat_sitrep", ls_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "build_plate"):
                    plate = mod.build_plate(write=False, refresh_spatial=False)
                    return {
                        "ok": bool(plate.get("ok")),
                        "verdict": plate.get("verdict"),
                        "summary": plate.get("summary"),
                        "sections": plate.get("sections") or {},
                        "this_one": plate.get("this_one"),
                        "movement": plate.get("movement"),
                        "source": "field-locational-sitrep-plate.py",
                    }
        except Exception:
            pass
    return {"ok": False, "summary": "Locational sitrep not yet employed.", "source": "missing"}


def _physics_witness_slice() -> dict[str, Any]:
    doc = _load(STATE / "field-physics-witness.json", {})
    if doc.get("thermal") or doc.get("entropy"):
        return doc
    pw_py = INSTALL / "lib" / "field-physics-witness.py"
    if pw_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("compat_physics_witness", pw_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "witness"):
                    return mod.witness(sections=True)
        except Exception:
            pass
    return {"ok": False, "motto": "We all need to know thermals. We all know entropy and isotope."}


def _power_sort_slice() -> dict[str, Any]:
    for path in (STATE / "g16-power-sort-plate.json", GROK16 / "data" / "g16-power-sort-panel.json", STATE / "g16-power-sort-panel.json"):
        doc = _load(path, {})
        if doc.get("sections") or doc.get("selection"):
            return {
                "ok": bool(doc.get("ok") or doc.get("plated")),
                "verdict": doc.get("verdict"),
                "sections": doc.get("sections") or {},
                "selection": doc.get("selection") or {},
                "thermal": doc.get("thermal") or {},
                "always_best_sort": bool(doc.get("always_best_sort", True)),
                "source": path.name,
            }
    ps_py = GROK16 / "lib" / "field-power-sort.py"
    if ps_py.is_file():
        try:
            spec = importlib.util.spec_from_file_location("compat_power_sort", ps_py)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "compute_selections") and hasattr(mod, "compute_sections"):
                    sel = mod.compute_selections()
                    thermal = mod.thermal_context() if hasattr(mod, "thermal_context") else {}
                    iron = _load(STATE / "ironclad-plate.json", {})
                    sections = mod.compute_sections(sel, thermal=thermal, ironclad_ok=bool(iron.get("ok") or iron.get("plated")))
                    return {
                        "ok": True,
                        "sections": sections,
                        "selection": sel,
                        "thermal": thermal,
                        "always_best_sort": True,
                        "source": "field-power-sort.py",
                    }
        except Exception:
            pass
    return {"ok": False, "sections": {}, "always_best_sort": False, "source": "missing"}


def _run_always_optimal() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, _load(SG / "NewLatest" / "data" / "field-compatibility-layers-doctrine.json", {}))
    policy = (doctrine.get("policy") or {})
    if not policy.get("always_optimal"):
        return {"ok": True, "step": "always_optimal", "skipped": True}
    mod_rel = str(policy.get("always_optimal_module") or "Grok16/lib/field-always-optimal.py")
    out = _run_script(mod_rel, "apply", "--no-layers", timeout=90)
    out["step"] = "always_optimal"
    return out


def probe_exec() -> dict[str, Any]:
    bridge = _load(STATE / "field-plate-combinatorics-bridge.json", {})
    comb = _load(STATE / "g16-field-combinatorics-panel.json", {})
    ao = _always_optimal_panel()
    optimal = ao.get("optimal") or {}
    posture = bridge.get("exec_posture") or {}
    gate = bridge.get("gate") or {}
    tree_ok = bool(bridge.get("combinatoric_tree_complete") or (comb.get("tree_walk") or {}).get("tree_complete"))
    always_on = bool(ao.get("always_optimal"))
    profile = optimal.get("belt_profile") or posture.get("belt_profile") or "belt_1_0"
    runner = optimal.get("runner") or posture.get("runner") or "python"
    pattern = optimal.get("pattern_id") or posture.get("pattern_id") or "—"
    die = optimal.get("die_slots") or posture.get("die_slots") or 256
    gate_ok = gate.get("ok")
    exec_live = bool(bridge or always_on) and bool(pattern) and bool(gate_ok or (always_on and profile))
    degraded = bool(ao.get("degraded_gate")) and not gate_ok
    summary = f"{pattern} · {profile} · {die} die · {runner}"
    if always_on and degraded:
        summary += " · gate degraded"
    return {
        "id": "exec",
        "index": 1,
        "label": "Exec / BSP",
        "glyph": "⚙",
        "color": "#5eead4",
        **_layer_status(
            live=exec_live,
            summary=summary,
            detail={
                "pattern_id": pattern,
                "belt_profile": profile,
                "die_slots": die,
                "runner": runner,
                "emulator": posture.get("emulator"),
                "tree_complete": tree_ok,
                "gate_ok": gate_ok,
                "degraded_gate": degraded,
                "thermal_headroom_pct": gate.get("thermal_headroom_pct"),
                "ideal_profile": optimal.get("ideal_profile") or posture.get("ideal_profile") or (comb.get("recombinatorics") or {}).get("ideal_profile"),
                "always_optimal": always_on,
                "bench_best_g16_ops_per_sec": (optimal.get("bench_best_g16") or {}).get("ops_per_sec"),
                "native_ceiling_ops_per_sec": optimal.get("native_ceiling_ops_per_sec") or posture.get("native_ceiling_ops_per_sec"),
            },
        ),
    }


def probe_program() -> dict[str, Any]:
    jump = (QUEEN / "lib" / "queen-nexus-jump.py").is_file()
    pythong = (SG / "PythonG" / "bin" / "pythong").is_file() or shutil_which("pythong")
    g16_as = (GROK16 / "bin" / "as").is_file()
    stack = _load(STATE / "nexus-g16-stack-panel.json", {})
    g16_ready = bool((stack.get("compile") or {}).get("probe", {}).get("g16_ready"))
    live = jump and (pythong or g16_as)
    return {
        "id": "program",
        "index": 2,
        "label": "Program interop",
        "glyph": "◈",
        "color": "#38bdf8",
        **_layer_status(
            live=live,
            summary=f"Queen jump {'on' if jump else 'off'} · G16 {'ready' if g16_ready else 'probe'} · pythong {'yes' if pythong else 'path'}",
            detail={
                "queen_nexus_jump": jump,
                "pythong": bool(pythong),
                "g16_toolchain": g16_as,
                "g16_ready": g16_ready,
                "ironclad_ok": (stack.get("ironclad_sanity") or {}).get("ok"),
            },
        ),
    }


def shutil_which(cmd: str) -> str | None:
    for d in os.environ.get("PATH", "").split(os.pathsep):
        p = Path(d) / cmd
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    return None


def probe_web() -> dict[str, Any]:
    mod = _import_mod("queen_web_compat", "queen-web-compat.py")
    if mod and hasattr(mod, "compat_status"):
        doc = mod.compat_status()
    else:
        doc = _run_script("queen-web-compat.py", "json", timeout=30)
    eras = doc.get("eras") or []
    modes = doc.get("modes") or {}
    live = len(eras) >= 6 and bool(modes.get("auto"))
    return {
        "id": "web",
        "index": 3,
        "label": "Web compat",
        "glyph": "◎",
        "color": "#a78bfa",
        **_layer_status(
            live=live,
            summary=f"{len(eras)} eras · auto + legacy_secure + archaeology",
            detail={
                "era_count": len(eras),
                "modes": list(modes.keys()),
                "default_mode": "auto",
                "engine_targets": doc.get("engine_targets") or [],
                "motto": doc.get("motto"),
            },
        ),
    }


def probe_chips() -> dict[str, Any]:
    chips_root = SG / "AMOURANTHRTX" / "Navigator" / "engine" / "CHIPS"
    manifest = QUEEN / "data" / "chips-g16-manifest.json"
    queen_chips = (QUEEN / "lib" / "queen-chips.py").is_file()
    chip_count = len(list(chips_root.rglob("*.hpp"))) if chips_root.is_dir() else 0
    manifest_doc = _load(manifest, {})
    platforms = manifest_doc.get("platforms") or manifest_doc.get("chips") or []
    live = chip_count > 0 and queen_chips
    return {
        "id": "chips",
        "index": 4,
        "label": "CHIPS / emu",
        "glyph": "▣",
        "color": "#fcd34d",
        **_layer_status(
            live=live,
            summary=f"{chip_count} BSP headers · manifest {len(platforms) if isinstance(platforms, list) else '—'} platforms",
            detail={
                "chip_headers": chip_count,
                "chips_root": str(chips_root),
                "queen_chips_bridge": queen_chips,
                "manifest_present": manifest.is_file(),
            },
        ),
    }


def probe_surface() -> dict[str, Any]:
    doctrine_path = INSTALL / "data" / "field-host-desktop-doctrine.json"
    if not doctrine_path.is_file():
        doctrine_path = SG / "NewLatest" / "data" / "field-host-desktop-doctrine.json"
    doctrine = _load(doctrine_path, {})
    programs = doctrine.get("programs") or []
    shell_js = (INSTALL / "panel" / "assets" / "nexus-field-shell.js").is_file()
    if not shell_js:
        shell_js = SG / "NewLatest" / "panel" / "assets" / "nexus-field-shell.js"
        shell_js = shell_js.is_file()
    no_client = bool(doctrine.get("no_client_browser"))
    live = len(programs) >= 5 and shell_js
    return {
        "id": "surface",
        "index": 5,
        "label": "Field surface",
        "glyph": "◇",
        "color": "#4ade80",
        **_layer_status(
            live=live,
            summary=f"{len(programs)} shell programs · Queen-only browser {no_client}",
            detail={
                "program_count": len(programs),
                "no_client_browser": no_client,
                "boot_program": doctrine.get("boot_program"),
                "field_route": doctrine.get("field_route") or "/field",
                "shell_js": bool(shell_js),
            },
        ),
    }


LAYER_PROBES = [
    probe_substrate,
    probe_exec,
    probe_program,
    probe_web,
    probe_chips,
    probe_surface,
]


def _launch_seal(*, bump: bool = False) -> dict[str, Any]:
    """Seal token for .launch refresh — bumps on each compatibility sync."""
    cached = _load(PANEL, {})
    seal = dict(cached.get("launch_seal") or {})
    gen = int(seal.get("generation") or 0)
    if bump:
        gen = max(gen, 0) + 1
        seal = {
            "generation": gen,
            "updated": _now(),
            "motto": "Stable .launch builds unlock only after this sync",
        }
    elif not seal:
        seal = {
            "generation": 0,
            "updated": _now(),
            "motto": "Bootstrap — first sync enables secured .launch refresh",
        }
    return seal


def _import_combinatorics() -> Any | None:
    for path in (GROK16 / "lib" / "field_combinatorics.py"):
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("field_combinatorics_layers", path)
        if not spec or not spec.loader:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    return None


def _auto_combinatorics(*, deep: bool = False) -> dict[str, Any]:
    """Run combinatorics pipeline — direct import fast_cycle (no studio subprocess)."""
    import time

    t0 = time.perf_counter()
    mod = _import_combinatorics()
    if not mod:
        return {"ok": False, "error": "field_combinatorics_missing", "action": "fast_cycle"}
    try:
        if hasattr(mod, "operator_running"):
            op = mod.operator_running(state_dir=STATE)
            if op.get("running") and hasattr(mod, "defer_combinatorics_update"):
                out = mod.defer_combinatorics_update(
                    action="auto_combinatorics",
                    reason="operator_running_no_combinatorics_update",
                    caller="compatibility_layers",
                    state_dir=STATE,
                )
                out["action"] = "fast_cycle"
                out["auto"] = True
                out["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                return out
        if deep:
            studio = INSTALL / "lib" / "field-combinatorics-studio.py"
            env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE), "GROK16_ROOT": str(GROK16), "SG_ROOT": str(SG), "G16_COMBO_CONDENSE": "full"}
            if studio.is_file():
                proc = subprocess.run(
                    [sys.executable, str(studio), "run", "full"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=env,
                )
                try:
                    out = json.loads(proc.stdout or "{}")
                except json.JSONDecodeError:
                    out = {"ok": proc.returncode == 0}
            else:
                out = {"ok": False, "error": "combinatorics_studio_missing"}
            out["action"] = "full"
        elif hasattr(mod, "fast_cycle"):
            verify = mod.verify_combinatorics_lock(state_dir=STATE) if hasattr(mod, "verify_combinatorics_lock") else {}
            if deep and hasattr(mod, "rebuild_engine_lock"):
                out = mod.rebuild_engine_lock(state_dir=STATE, deep=True)
                out["action"] = "engine_rebuild_deep"
            elif verify.get("needs_rebuild") and hasattr(mod, "rebuild_engine_lock"):
                out = mod.rebuild_engine_lock(state_dir=STATE, deep=False)
                out["action"] = "engine_rebuild_auto"
            else:
                out = mod.fast_cycle(state_dir=STATE)
                out["action"] = "fast_cycle"
        else:
            out = mod.publish_panel(state_dir=STATE, light=True) if hasattr(mod, "publish_panel") else {"ok": False}
            out["action"] = "publish_light"
        if out.get("rejected"):
            out["combinatorics_rejected"] = True
            out.setdefault("ok", True)
            out["never_break"] = True
            if hasattr(mod, "threat_panel"):
                out["combinatorics_threat"] = mod.threat_panel(state_dir=STATE)
        elif out.get("deferred"):
            out["combinatorics_deferred"] = True
            out.setdefault("ok", True)
            out["never_break"] = True
        else:
            out.setdefault("ok", True)
        out["auto"] = True
        out["elapsed_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        if hasattr(mod, "usage_profile"):
            out["usage"] = mod.usage_profile()
        return out
    except Exception as exc:
        return {"ok": False, "error": str(exc), "action": "fast_cycle", "auto": True, "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2)}


def _build_bridge() -> dict[str, Any]:
    return _run_script("field-plate-combinatorics-bridge.py", "build", timeout=60)


def stack(*, write: bool = False) -> dict[str, Any]:
    layers = [probe() for probe in LAYER_PROBES]
    live_count = sum(1 for layer in layers if layer.get("live"))
    exec_layer = next((layer for layer in layers if layer["id"] == "exec"), {})
    posture = (exec_layer.get("detail") or {})
    ao = _always_optimal_panel()
    optimal = ao.get("optimal") or {}
    doctrine = _load(DOCTRINE, _load(SG / "NewLatest" / "data" / "field-compatibility-layers-doctrine.json", {}))
    launch_seal = _launch_seal(bump=False)
    doc = {
        "schema": "field-compatibility-layers/v1",
        "updated": _now(),
        "ok": live_count >= 4,
        "motto": doctrine.get("motto") or "Pre-baked profiles stack upward — combinatorics runs itself.",
        "operator_combinatorics": False,
        "always_optimal": bool(ao.get("always_optimal")),
        "launch_seal": launch_seal,
        "live_layers": live_count,
        "total_layers": len(layers),
        "layers": layers,
        "effective_profile": {
            "pattern_id": optimal.get("pattern_id") or posture.get("pattern_id"),
            "belt_profile": optimal.get("belt_profile") or posture.get("belt_profile"),
            "die_slots": optimal.get("die_slots") or posture.get("die_slots"),
            "runner": optimal.get("runner") or posture.get("runner"),
            "ideal_profile": optimal.get("ideal_profile") or posture.get("ideal_profile"),
            "always_optimal": bool(ao.get("always_optimal")),
            "degraded_gate": ao.get("degraded_gate"),
        },
        "power_sort": _power_sort_slice(),
        "power_sort_sections": optimal.get("power_sort_sections") or (_power_sort_slice().get("sections") or {}),
        "physics_witness": _physics_witness_slice(),
        "locational_sitrep": _locational_sitrep_slice(),
        "gates_held": all(
            layer.get("live") or layer["id"] in ("chips",)
            for layer in layers
            if layer["id"] != "chips"
        ),
    }
    if write:
        _save(PANEL, doc)
    return doc


def refresh(*, deep: bool = False) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    comb = _auto_combinatorics(deep=deep)
    steps.append({"step": "auto_combinatorics", **comb})
    bridge = _build_bridge()
    steps.append({"step": "exec_bridge", **bridge})
    ao = _run_always_optimal()
    steps.append(ao)
    doc = stack(write=True)
    doc["launch_seal"] = _launch_seal(bump=True)
    comb_panel = _load(STATE / "g16-field-combinatorics-panel.json", {})
    if comb_panel.get("combinatorics_lock"):
        doc["combinatorics_lock"] = comb_panel["combinatorics_lock"]
    if comb_panel.get("engine_fingerprint"):
        doc["engine_fingerprint"] = {
            "engine_sha256": (comb_panel.get("engine_fingerprint") or {}).get("engine_sha256"),
            "source_count": (comb_panel.get("engine_fingerprint") or {}).get("source_count"),
            "auto_detected": True,
        }
    comb_step = next((s for s in steps if s.get("step") == "auto_combinatorics"), {})
    rejections = [s for s in steps if s.get("rejected") or s.get("combinatorics_rejected")]
    threat_panel = _load(STATE / "field-combinatorics-threat-panel.json", {})
    if threat_panel:
        doc["combinatorics_threat"] = {
            "stats": threat_panel.get("stats"),
            "last": threat_panel.get("last"),
            "runtime": threat_panel.get("runtime"),
        }
    if rejections or comb_step.get("rejected"):
        doc["combinatorics_rejections"] = rejections or [comb_step]
    doc["refresh"] = {
        "ok": all(s.get("ok", True) for s in steps),
        "never_break_on_mismatch": True,
        "steps": steps,
        "deep": deep,
        "launch_seal_generation": doc["launch_seal"]["generation"],
    }
    _save(PANEL, doc)
    return doc


def status() -> dict[str, Any]:
    cached = _load(PANEL, {})
    if cached.get("layers"):
        cached["updated"] = cached.get("updated") or _now()
        return cached
    return stack(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "status", "panel"):
        print(json.dumps(status(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("stack", "probe"):
        print(json.dumps(stack(write=False), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("refresh", "sync", "build"):
        deep = "--deep" in sys.argv or cmd == "full"
        print(json.dumps(refresh(deep=deep), ensure_ascii=False, indent=2))
        return 0
    if cmd == "full":
        print(json.dumps(refresh(deep=True), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps({
        "error": "usage",
        "cmds": ["json", "status", "stack", "refresh", "full", "sync"],
    }, ensure_ascii=False))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())