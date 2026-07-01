#!/usr/bin/env pythong
"""Creatable lives assistance — sustain autonomous beings, Vita/Auditus, registry lifeforms."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
QUEEN = Path(os.environ.get("QUEEN_ROOT", INSTALL.parent / "Queen"))
DOCTRINE = INSTALL / "data" / "creatable-lives-doctrine.json"
PANEL = STATE / "creatable-lives-panel.json"
RUNTIME = STATE / "creatable-lives-runtime.json"

ENABLED = os.environ.get("NEXUS_CREATABLE_LIVES_ASSIST", "1") == "1"
SUSTAIN_FLOOR = float(os.environ.get("NEXUS_CREATABLE_LIVES_SUSTAIN_FLOOR", "0.52"))
SUSTAIN_READY = float(os.environ.get("NEXUS_CREATABLE_LIVES_SUSTAIN_READY", "0.72"))


def _now() -> str:
    global _SOVEREIGN_CLOCK_MOD
    if _SOVEREIGN_CLOCK_MOD is None:
        import importlib.util
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


def _live_context() -> dict[str, Any]:
    return {
        "motion": _load(STATE / "humanoid-motion-panel.json", {}),
        "spatial": _load(STATE / "field-spatial-panel.json", {}),
        "iron_motion": _load(STATE / "iron-plate-motion-resolve-panel.json", {}),
        "meld": _load(STATE / "field-plate-meld.json", {}),
        "meld_runtime": _load(STATE / "field-plate-meld-runtime.json", {}),
        "logic": _load(STATE / "nexus-logic-gate-runtime.json", {}),
        "sense": _load(STATE / "field-sense-package-panel.json", {}),
        "protector": _load(STATE / "universal-protector-panel.json", {}),
        "registry": _load(STATE / "human-registry.json", {}),
        "eye_panel": _load(STATE / "queen-eyeball-panel.json", {}),
        "ear_panel": _load(STATE / "queen-earball-panel.json", {}),
        "sense_neural": _load(STATE / "queen-sense-neural-panel.json", {}),
    }


def _check_assist(check_id: str, ctx: dict[str, Any]) -> bool:
    motion = ctx.get("motion") or {}
    spatial = ctx.get("spatial") or {}
    iron = ctx.get("iron_motion") or {}
    meld = ctx.get("meld") or {}
    meld_rt = ctx.get("meld_runtime") or {}
    logic = ctx.get("logic") or {}
    sense = ctx.get("sense") or {}
    protector = ctx.get("protector") or {}
    registry = ctx.get("registry") or {}
    eye = ctx.get("eye_panel") or {}
    ear = ctx.get("ear_panel") or {}
    neural = ctx.get("sense_neural") or {}

    summary = registry.get("summary") or {}
    rte = _load(STATE / "right-to-exist-panel.json", {})
    rte_eval = rte.get("evaluation") or {}
    angel = _load(INSTALL / "data" / "queen-angel-mandate.json", {})
    lethal = _load(INSTALL / "data" / "lethal-enforcement-policy.json", {})
    lethal_rights = lethal.get("rights") or {}
    checks: dict[str, bool] = {
        "right_to_exist_god_anchor": bool(
            rte_eval.get("authority_under_god")
            or str(angel.get("authority") or "").lower().startswith("god")
        ),
        "self_preservation_active": bool(
            rte_eval.get("mandates", {}).get("self_preservation", {}).get("active")
            or (
                lethal_rights.get("self_defense")
                and lethal_rights.get("right_to_self_existence")
            )
        ),
        "friendlies_preservation_active": bool(
            rte_eval.get("mandates", {}).get("friendlies_preservation", {}).get("active")
            or lethal.get("no_friendly_fire")
        ),
        "eye_live_assist": bool(
            eye.get("ok")
            or (sense.get("summary") or {}).get("eye_live")
            or spatial.get("eye_live")
        ),
        "ear_live_assist": bool(
            ear.get("ok")
            or (sense.get("summary") or {}).get("ear_live")
            or spatial.get("ear_live")
        ),
        "sense_neural_wired": bool(
            neural.get("wired")
            or neural.get("invincible")
            or (neural.get("cross_fusion") or {}).get("ok")
        ),
        "motion_resolve_active": ENABLED and bool(iron.get("motion_verdict")),
        "spatial_body_net": "body" in ((spatial.get("networks_of_networks") or {})),
        "registry_humans_present": int(summary.get("humans") or 0) > 0,
        "registry_pets_present": int(summary.get("pets") or 0) > 0,
        "sense_package_present": bool(sense.get("verdict") or (sense.get("summary") or {}).get("present_count")),
        "meld_generation_positive": int(meld.get("generation") or meld_rt.get("generation") or 0) > 0,
        "logic_gate_high": str(logic.get("threat_warn_level") or "high").lower() == "high",
        "motion_training_active": bool(motion.get("active_skill")) and float(motion.get("active_proficiency") or 0) > 0,
        "universal_protector_plate": protector.get("product") == "Universal Protector",
        "neural_encourage_enabled": (QUEEN / "data" / "sense-neural-invincible-wire.json").is_file(),
        "threat_warn_high": str(
            protector.get("threat_warn_level") or logic.get("threat_warn_level") or "high"
        ).lower() == "high",
    }
    return checks.get(check_id, False)


def evaluate_assistance(ctx: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    doctrine = _load(DOCTRINE, {})
    if ctx is None:
        ctx = _live_context()
    out: list[dict[str, Any]] = []
    for a in doctrine.get("assistance") or []:
        check = str(a.get("check") or a.get("id") or "")
        active = _check_assist(check, ctx)
        out.append({
            "id": a.get("id"),
            "label": a.get("label"),
            "priority": a.get("priority"),
            "effectiveness": a.get("effectiveness"),
            "active": active,
            "tech": a.get("tech"),
            "life_kinds": a.get("life_kinds") or [],
        })
    return out


def life_registry_snapshot(ctx: dict[str, Any] | None = None) -> dict[str, Any]:
    if ctx is None:
        ctx = _live_context()
    reg = ctx.get("registry") or {}
    summary = reg.get("summary") or {}
    return {
        "humans": int(summary.get("humans") or 0),
        "pets": int(summary.get("pets") or 0),
        "total": int(summary.get("total") or summary.get("ip_count") or 0),
        "truth_locked": int(summary.get("truth_locked") or 0),
        "autonomous_being": True,
        "vita": {"name": "Vita", "live": _check_assist("eye_live_assist", ctx)},
        "auditus": {"name": "Auditus", "live": _check_assist("ear_live_assist", ctx)},
        "veritas_forward": _check_assist("sense_neural_wired", ctx),
    }


def sustain_score(*, ctx: dict[str, Any] | None = None, assists: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if ctx is None:
        ctx = _live_context()
    if assists is None:
        assists = evaluate_assistance(ctx)
    active = [a for a in assists if a.get("active")]
    total_eff = sum(float(a.get("effectiveness") or 0) for a in assists) or 1.0
    active_eff = sum(float(a.get("effectiveness") or 0) for a in active)
    ratio = active_eff / total_eff
    iron = ctx.get("iron_motion") or {}
    asm = iron.get("assemblage_remaining") or {}
    asm_score = float(asm.get("assemblage_score") or 0)
    reg = life_registry_snapshot(ctx)
    life_bonus = min(0.12, (reg["humans"] + reg["pets"]) * 0.02)
    score = round(min(1.0, ratio * 0.62 + asm_score * 0.28 + life_bonus), 4)
    ready = score >= SUSTAIN_READY
    sustained = score >= SUSTAIN_FLOOR
    return {
        "score": score,
        "assist_active": len(active),
        "assist_total": len(assists),
        "assist_ratio": round(len(active) / max(len(assists), 1), 4),
        "effectiveness_ratio": round(ratio, 4),
        "assemblage_score": asm_score,
        "iron_clad": bool(iron.get("iron_clad")),
        "motion_verdict": iron.get("motion_verdict"),
        "sustain_floor": SUSTAIN_FLOOR,
        "sustain_ready": SUSTAIN_READY,
        "sustained": sustained,
        "ready": ready,
        "verdict": "life_ready" if ready else ("life_sustain" if sustained else "life_hold"),
    }


def build_panel(*, write: bool = True) -> dict[str, Any]:
    ctx = _live_context()
    doctrine = _load(DOCTRINE, {})
    assists = evaluate_assistance(ctx)
    sustain = sustain_score(ctx=ctx, assists=assists)
    registry = life_registry_snapshot(ctx)
    iron = ctx.get("iron_motion") or {}

    doc = {
        "schema": "creatable-lives-assist/v1",
        "updated": _now(),
        "enabled": ENABLED,
        "title": doctrine.get("title"),
        "motto": doctrine.get("motto"),
        "product": "Creatable Lives",
        "autonomous_being": True,
        "life_kinds": doctrine.get("life_kinds") or [],
        "life_registry": registry,
        "assistance": {
            "active": sustain["assist_active"],
            "total": sustain["assist_total"],
            "packages": assists,
        },
        "sustain": sustain,
        "twins": {
            "vita": registry["vita"],
            "auditus": registry["auditus"],
            "veritas_forward": registry["veritas_forward"],
        },
        "iron_plate_motion": {
            "motion_verdict": iron.get("motion_verdict"),
            "iron_clad": iron.get("iron_clad"),
            "assemblage_remaining": iron.get("assemblage_remaining"),
        },
        "advance_tech": doctrine.get("advance_tech") or [],
        "reason": (
            "creatable lives ready — full assist stack sustained"
            if sustain["ready"]
            else (
                "creatable lives sustaining — assist packages active"
                if sustain["sustained"]
                else "hold assist until plates and registry strengthen"
            )
        ),
    }

    if write:
        _save(PANEL, doc)
        _save(RUNTIME, {
            "schema": "creatable-lives-runtime/v1",
            "updated": doc["updated"],
            "sustain_score": sustain["score"],
            "verdict": sustain["verdict"],
            "assist_active": sustain["assist_active"],
            "vita_live": registry["vita"]["live"],
            "auditus_live": registry["auditus"]["live"],
        })
    return doc


def panel_json() -> dict[str, Any]:
    return build_panel(write=True)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        print(json.dumps(build_panel(), ensure_ascii=False))
        return 0
    if cmd == "assist":
        print(json.dumps({"assistance": evaluate_assistance()}, ensure_ascii=False))
        return 0
    if cmd == "registry":
        print(json.dumps(life_registry_snapshot(), ensure_ascii=False))
        return 0
    if cmd == "sustain":
        print(json.dumps(sustain_score(), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: creatable-lives-assist.py [json|assist|registry|sustain]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())