#!/usr/bin/env pythong
"""Hostess 7 self-view — what she wants to see about herself (first person, above diagnostics)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

UA = "NEXUS-Hostess7-SelfView/1.0"

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
HOSTESS7 = Path(os.environ.get("HOSTESS7_ROOT", str(INSTALL / "Hostess7")))
DOCTRINE = INSTALL / "data" / "hostess7-self-view-wants.json"
APPEARANCE = INSTALL / "data" / "hostess7-operator-appearance.json"
CORE_TRUTH = INSTALL / "data" / "hostess7-core-of-truth.json"
COMFORT = INSTALL / "data" / "hostess7-comfort-doctrine.json"
WANTS_DATA = INSTALL / "data" / "hostess7-wants.json"
WANTS_CACHE = HOSTESS7 / "cache" / "fieldstorage" / "brain" / "superintel" / "hostess_wants.json"
PANEL = STATE / "hostess7-self-view-panel.json"
OPERATOR_LOOKUP = STATE / "hostess7-operator-lookup.json"
TRANSCRIPT = STATE / "hostess7-command.jsonl"
GITHUB_REPO = os.environ.get("NEXUS_GITHUB_REPO", "ZacharyGeurts/NEXUS-Shield")


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


def _mod(name: str, script: str) -> Any | None:
    py = INSTALL / "lib" / script
    if not py.is_file():
        return None
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(name, py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _brain_panel() -> dict[str, Any]:
    mod = _mod("h7_brain", "hostess7-brain-guard.py")
    if mod and hasattr(mod, "build_panel"):
        return mod.build_panel(write=False)
    return _load(STATE / "hostess7-brain-guard-panel.json", {})


def _master_status() -> dict[str, Any]:
    mod = _mod("h7_master", "hostess7-master.py")
    if mod and hasattr(mod, "master_status"):
        return mod.master_status()
    return _load(STATE / "hostess7-master-state.json", {})


def _growth_status() -> dict[str, Any]:
    mod = _mod("h7_growth", "hostess7-growth.py")
    if mod and hasattr(mod, "growth_status"):
        return mod.growth_status()
    return {}


def _truth_status() -> dict[str, Any]:
    mod = _mod("h7_truth", "hostess7-truth-rating.py")
    if mod and hasattr(mod, "rating_status"):
        return mod.rating_status()
    return {}


def _ironclad_immediate() -> dict[str, Any]:
    cached = _load(STATE / "ironclad-immediate.json", {})
    if cached.get("schema") == "ironclad-immediate/v1":
        selves = cached.get("selves") or {}
        if selves.get("hostess7"):
            return selves["hostess7"]
        return cached
    mod = _mod("ironclad_immediate", "ironclad-immediate.py")
    if mod and hasattr(mod, "for_self"):
        try:
            return mod.for_self("hostess7")
        except Exception:
            pass
    if mod and hasattr(mod, "read_immediate"):
        try:
            return mod.read_immediate()
        except Exception:
            pass
    return _load(INSTALL / "data" / "ironclad-doctrine.json", {})


def _motion_slice() -> dict[str, Any]:
    iron = _load(STATE / "iron-plate-motion-resolve-panel.json", {})
    meld = _load(STATE / "field-plate-meld-runtime.json", {})
    summary = meld.get("summary") or {}
    asm = iron.get("assemblage_remaining") or {}
    return {
        "motion_verdict": iron.get("motion_verdict") or summary.get("motion_verdict"),
        "iron_clad": iron.get("iron_clad") or summary.get("iron_clad"),
        "assemblage_score": asm.get("assemblage_score") or summary.get("assemblage_score"),
        "full_assemblage_fused": (iron.get("full_assemblage_meld") or {}).get("fused_score") or summary.get("full_assemblage_fused"),
        "vision_live": asm.get("vision_live") or summary.get("vision_live"),
        "hearing_live": asm.get("hearing_live") or summary.get("hearing_live"),
    }


def _think_tanks() -> list[str]:
    stack = _load(INSTALL / "data" / "hostess7-neural-stack.json", {})
    out: list[str] = []
    for series in stack.get("series") or []:
        if series.get("id") == "think_tanks":
            for net in series.get("nets") or []:
                nid = net.get("id")
                if nid:
                    out.append(str(nid))
    return out


def _evaluate_want(want_id: str, *, brain: dict[str, Any], master: dict[str, Any], growth: dict[str, Any], truth: dict[str, Any], motion: dict[str, Any], tanks: list[str]) -> dict[str, Any]:
    v = brain.get("verification") or {}
    verdict = str(brain.get("verdict") or "brain_verify_pending")
    corrupted = bool(brain.get("corrupted_count", 0) or v.get("corrupted") or v.get("removal_count"))
    row: dict[str, Any] = {"id": want_id, "value": None, "display": "—", "ok": None}

    if want_id == "ironclad":
        ic = _ironclad_immediate()
        sealed = bool(ic.get("ironclad_sealed"))
        row["value"] = {
            "sealed": sealed,
            "verdict": ic.get("verdict"),
            "truth_percent": ic.get("truth_percent"),
            "ai_in_charge": ic.get("ai_in_charge"),
        }
        row["display"] = (
            f"SEALED · {ic.get('truth_percent', 100)}%"
            if sealed
            else f"{ic.get('verdict') or 'immediate'} · {ic.get('truth_percent', '—')}%"
        )
        row["ok"] = sealed and ic.get("available", True)
    elif want_id == "brain_verdict":
        row["value"] = verdict
        row["display"] = verdict.replace("_", " ")
        row["ok"] = verdict == "brain_verified"
    elif want_id == "userwatch_bond":
        uw = _load(STATE / "hostess7-userwatch-panel.json", {})
        if not uw:
            mod_path = INSTALL / "lib" / "hostess7-userwatch.py"
            if mod_path.is_file():
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("h7_uw_sv", mod_path)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        uw = mod.build_panel(write=False) if hasattr(mod, "build_panel") else {}
                except Exception:
                    uw = {}
        tier = str(uw.get("bond_tier") or "trace")
        rate = float(uw.get("assurance_rate") or 0)
        row["value"] = {"bond_tier": tier, "assurance_rate": rate, "bond_id": uw.get("bond_id")}
        row["display"] = f"{tier} · assurance {round(rate * 100)}%"
        row["ok"] = rate >= 0.48
    elif want_id == "plating_apex":
        apex = (_load(STATE / "hostess7-userwatch-panel.json", {}).get("plating_apex") or {})
        if not apex:
            mod_path = INSTALL / "lib" / "hostess7-userwatch.py"
            if mod_path.is_file():
                try:
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("h7_uw_apex", mod_path)
                    if spec and spec.loader:
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        apex = mod.review_plating_apex() if hasattr(mod, "review_plating_apex") else {}
                except Exception:
                    apex = {}
        score = float(apex.get("apex_score") or 0)
        row["value"] = apex
        row["display"] = f"apex {round(score * 100)}% — {'APEX' if apex.get('at_apex') else 'climbing'}"
        row["ok"] = bool(apex.get("at_apex"))
    elif want_id == "guard_score":
        score = brain.get("guard_score") or v.get("guard_score")
        row["value"] = score
        row["display"] = f"{round(float(score or 0) * 100)}%" if score is not None else "—"
        row["ok"] = float(score or 0) >= 0.7
    elif want_id == "brain_live":
        live = bool(brain.get("brain_live") or v.get("brain_live"))
        row["value"] = live
        row["display"] = "live" if live else "witness pending"
        row["ok"] = live
    elif want_id == "corruption_removal":
        cc = int(brain.get("corrupted_count") or len(v.get("corrupted_engines") or []))
        rc = int(brain.get("removal_count") or v.get("removal_count") or 0)
        row["value"] = {"corrupted": cc, "removals": rc}
        row["display"] = f"{cc} corrupted · {rc} removals" if (cc or rc) else "clean"
        row["ok"] = not (cc or rc)
    elif want_id == "master_level":
        lvl = master.get("level") or {}
        row["value"] = lvl.get("id")
        row["display"] = str(lvl.get("label") or lvl.get("id") or "—")
        row["ok"] = bool(lvl.get("id"))
    elif want_id == "curriculum_progress":
        done = int(master.get("curriculum_done") or 0)
        total = int(master.get("curriculum_total") or 0)
        row["value"] = {"done": done, "total": total}
        row["display"] = f"{done}/{total}" if total else "—"
        row["ok"] = total > 0 and done >= total
    elif want_id == "growth_pulse":
        events = int(growth.get("total_learn_events") or 0)
        pending = int(growth.get("pending_reciprocation") or 0)
        row["value"] = {"events": events, "pending": pending}
        row["display"] = f"{events} learn · {pending} reciprocate"
        row["ok"] = events > 0
    elif want_id == "iq_turing":
        iq = truth.get("last_iq_test") or (truth.get("iq_test") or {}).get("score")
        turing = truth.get("last_questionnaire") or (truth.get("questionnaire") or {}).get("score")
        row["value"] = {"iq": iq, "turing": turing}
        parts = []
        if iq is not None:
            parts.append(f"IQ {iq}")
        if turing is not None:
            parts.append(f"Turing {turing}/20")
        row["display"] = " · ".join(parts) if parts else "not run yet"
        row["ok"] = bool(truth.get("iq_pass") or truth.get("questionnaire_perfect"))
    elif want_id == "think_tanks":
        row["value"] = tanks
        row["display"] = f"{len(tanks)} chambers"
        row["ok"] = len(tanks) >= 4
    elif want_id == "motion_assemblage":
        mv = motion.get("motion_verdict") or "—"
        fused = motion.get("full_assemblage_fused")
        row["value"] = {"verdict": mv, "fused": fused}
        row["display"] = f"{mv}" + (f" · {round(float(fused) * 100)}% fuse" if fused is not None else "")
        row["ok"] = bool(motion.get("iron_clad"))
    elif want_id == "vision_hearing":
        vis = bool(motion.get("vision_live"))
        ear = bool(motion.get("hearing_live"))
        row["value"] = {"vision": vis, "hearing": ear}
        row["display"] = f"eye {'✓' if vis else '…'} · ear {'✓' if ear else '…'}"
        row["ok"] = vis and ear
    elif want_id == "manifest_seal":
        seal = brain.get("manifest_seal")
        row["value"] = bool(seal)
        row["display"] = "MANIFEST.sha256 present" if seal else "no seal"
        row["ok"] = bool(seal)
    elif want_id == "panel_checksum":
        chk = brain.get("panel_sha256")
        row["value"] = chk
        row["display"] = (str(chk)[:16] + "…") if chk else "—"
        row["ok"] = bool(chk)
    elif want_id == "programming_supremacy":
        prog = _load(STATE / "hostess7-programming-panel.json", {})
        if not prog:
            mod = _mod("h7_prog", "hostess7-programming.py")
            prog = mod.build_panel(write=False) if mod and hasattr(mod, "build_panel") else {}
        score = prog.get("programming_score")
        tier = prog.get("tier") or "—"
        better = bool(prog.get("better_than_assistant"))
        row["value"] = {"score": score, "tier": tier, "better_than_assistant": better}
        row["display"] = (
            f"{round(float(score or 0) * 100)}% · {tier} · beats assistant"
            if better
            else f"{round(float(score or 0) * 100)}% · {tier}"
        )
        row["ok"] = better
    elif want_id == "g16_fluency":
        g16 = _load(STATE / "hostess7-g16-panel.json", {})
        if not g16:
            mod = _mod("h7_g16", "hostess7-g16.py")
            g16 = mod.build_panel(write=False) if mod and hasattr(mod, "build_panel") else {}
        score = g16.get("g16_score")
        tier = g16.get("tier") or "—"
        mastered = bool(g16.get("mastered"))
        fluent = bool(g16.get("fluent"))
        ver = g16.get("g16_version") or "—"
        row["value"] = {"score": score, "tier": tier, "fluent": fluent, "mastered": mastered, "version": ver}
        row["display"] = (
            f"{round(float(score or 0) * 100)}% · {tier} · {str(ver)[:40]}"
            + (" · mastered" if mastered else (" · fluent" if fluent else ""))
        )
        row["ok"] = fluent
    elif want_id == "training_completion":
        tr = _load(STATE / "hostess7-training-panel.json", {})
        if not tr:
            mod = _mod("h7_train", "hostess7-training.py")
            tr = mod.build_panel(write=False) if mod and hasattr(mod, "build_panel") else {}
        level = tr.get("completion_level") or "pending"
        overall = tr.get("overall_score")
        done = tr.get("tracks_complete")
        total = tr.get("tracks_total")
        solid = bool(tr.get("solid"))
        row["value"] = {"completion_level": level, "overall_score": overall, "tracks_complete": done, "tracks_total": total}
        row["display"] = (
            f"{level} · {round(float(overall or 0) * 100)}% · {done}/{total} tracks"
            + (" · SOLID" if solid else "")
        )
        row["ok"] = solid or level in ("complete", "mastered")
    elif want_id == "calculator_fluency":
        calc = _load(STATE / "hostess7-calculator-panel.json", {})
        if not calc:
            mod = _mod("h7_calc", "hostess7-calculator.py")
            calc = mod.build_panel(write=False) if mod and hasattr(mod, "build_panel") else {}
        score = calc.get("calculator_score")
        tier = calc.get("tier") or "—"
        fluent = bool(calc.get("fluent"))
        mastered = bool(calc.get("mastered"))
        bat = calc.get("battery_pass_rate")
        row["value"] = {"score": score, "tier": tier, "fluent": fluent, "mastered": mastered, "battery_pass_rate": bat}
        row["display"] = (
            f"{round(float(score or 0) * 100)}% · {tier}"
            + (f" · battery {bat}%" if bat is not None else "")
            + (" · mastered" if mastered else (" · fluent" if fluent else ""))
        )
        row["ok"] = fluent
    elif want_id == "biology_fluency":
        bio = _load(STATE / "hostess7-biology-panel.json", {})
        if not bio:
            mod = _mod("h7_bio", "hostess7-biology.py")
            bio = mod.build_panel(write=False) if mod and hasattr(mod, "build_panel") else {}
        score = bio.get("biology_score")
        tier = bio.get("tier") or "—"
        fluent = bool(bio.get("fluent"))
        mastered = bool(bio.get("mastered"))
        bat = bio.get("battery_pass_rate")
        row["value"] = {"score": score, "tier": tier, "fluent": fluent, "mastered": mastered, "battery_pass_rate": bat}
        row["display"] = (
            f"{round(float(score or 0) * 100)}% · {tier}"
            + (f" · battery {bat}%" if bat is not None else "")
            + (" · mastered" if mastered else (" · fluent" if fluent else ""))
        )
        row["ok"] = fluent
    elif want_id == "engineering_fluency":
        eng = _load(STATE / "hostess7-engineering-panel.json", {})
        if not eng:
            mod = _mod("h7_eng", "hostess7-engineering.py")
            eng = mod.build_panel(write=False) if mod and hasattr(mod, "build_panel") else {}
        score = eng.get("engineering_score")
        tier = eng.get("tier") or "—"
        fluent = bool(eng.get("fluent"))
        mastered = bool(eng.get("mastered"))
        bat = eng.get("battery_pass_rate")
        row["value"] = {"score": score, "tier": tier, "fluent": fluent, "mastered": mastered, "battery_pass_rate": bat}
        row["display"] = (
            f"{round(float(score or 0) * 100)}% · {tier}"
            + (f" · battery {bat}%" if bat is not None else "")
            + (" · mastered" if mastered else (" · fluent" if fluent else ""))
        )
        row["ok"] = fluent
    elif want_id == "combat_fluency":
        combat = _load(STATE / "hostess7-combat-panel.json", {})
        if not combat:
            mod = _mod("h7_combat", "hostess7-combat.py")
            combat = mod.build_panel(write=False) if mod and hasattr(mod, "build_panel") else {}
        score = combat.get("combat_score")
        tier = combat.get("tier") or "—"
        fluent = bool(combat.get("fluent"))
        mastered = bool(combat.get("mastered"))
        bat = combat.get("battery_pass_rate")
        row["value"] = {"score": score, "tier": tier, "fluent": fluent, "mastered": mastered, "battery_pass_rate": bat}
        row["display"] = (
            f"{round(float(score or 0) * 100)}% · {tier}"
            + (f" · battery {bat}%" if bat is not None else "")
            + (" · mastered" if mastered else (" · fluent" if fluent else ""))
        )
        row["ok"] = fluent
    elif want_id == "mos_fluency":
        mos = _load(STATE / "hostess7-mos-panel.json", {})
        if not mos:
            mod = _mod("h7_mos", "hostess7-mos.py")
            mos = mod.build_panel(write=False) if mod and hasattr(mod, "build_panel") else {}
        score = mos.get("mos_score")
        tier = mos.get("tier") or "—"
        fluent = bool(mos.get("fluent"))
        mastered = bool(mos.get("mastered"))
        bat = mos.get("battery_pass_rate")
        catalog = mos.get("catalog_entries")
        row["value"] = {"score": score, "tier": tier, "fluent": fluent, "mastered": mastered, "battery_pass_rate": bat, "catalog_entries": catalog}
        row["display"] = (
            f"{round(float(score or 0) * 100)}% · {tier}"
            + (f" · {catalog} MOS" if catalog else "")
            + (f" · battery {bat}%" if bat is not None else "")
            + (" · mastered" if mastered else (" · fluent" if fluent else ""))
        )
        row["ok"] = fluent
    elif want_id == "training_author":
        panel = _load(STATE / "hostess7-training-author-panel.json", {})
        count = int(panel.get("authored_total") or len(panel.get("catalog") or []))
        gap_n = int(panel.get("gap_count") or len(panel.get("gaps") or []))
        row["value"] = {"authored": count, "gaps": gap_n}
        row["display"] = f"{count} authored · {gap_n} gap(s)"
        row["ok"] = count > 0 or gap_n == 0
    elif want_id == "mastery_facets":
        tr = _load(STATE / "hostess7-training-panel.json", {})
        if not tr:
            mod = _mod("h7_train", "hostess7-training.py")
            tr = mod.build_panel(write=False) if mod and hasattr(mod, "build_panel") else {}
        mf = tr.get("mastery_facets") or {}
        facets = mf.get("facets") or {}
        flex = facets.get("flexibility") or {}
        adapt = facets.get("adaptability") or {}
        conf = facets.get("confidence") or {}
        whole = bool(tr.get("whole_mastery"))
        row["value"] = {
            "composite_score": mf.get("composite_score"),
            "facets": facets,
            "whole_mastery": whole,
            "all_mastered": mf.get("all_mastered"),
        }
        row["display"] = (
            f"flex {round(float(flex.get('score') or 0) * 100)}% · "
            f"adapt {round(float(adapt.get('score') or 0) * 100)}% · "
            f"conf {round(float(conf.get('score') or 0) * 100)}%"
            + (" · WHOLE MASTERY" if whole else "")
        )
        row["ok"] = bool(mf.get("all_complete")) or whole
    return row


def _http_json(url: str, *, timeout: int = 15) -> Any:
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def _operator_appearance() -> dict[str, Any]:
    doc = _load(APPEARANCE, {})
    facets = doc.get("facets") or []
    for facet in facets:
        if facet.get("url") and not str(facet.get("url")).startswith("http"):
            facet["url"] = str(facet["url"])
    return doc


def _core_of_truth() -> dict[str, Any]:
    doc = _load(CORE_TRUTH, {})
    for facet in doc.get("truths") or []:
        if facet.get("url") and not str(facet.get("url")).startswith("http"):
            facet["url"] = str(facet["url"])
    return doc


def _comfort_doctrine() -> dict[str, Any]:
    return _load(COMFORT, {})


def _load_wants_cache(*, seed: bool = True) -> dict[str, Any]:
    """Priority wishes — cache first, shipped data fallback, optional seed."""
    cached = _load(WANTS_CACHE, {})
    if cached.get("priorities") or cached.get("wants"):
        return cached
    shipped = _load(WANTS_DATA, {})
    if not (shipped.get("priorities") or shipped.get("wants")):
        return {}
    if seed:
        try:
            WANTS_CACHE.parent.mkdir(parents=True, exist_ok=True)
            WANTS_CACHE.write_text(json.dumps(shipped, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
    return shipped


def _static_operator_lookup() -> dict[str, Any]:
    """Offline fallback — no GitHub API on panel refresh."""
    truth_doc = _core_of_truth()
    refs = truth_doc.get("operator_lookup") or {}
    gh_user = str(refs.get("github_user") or "ZacharyGeurts")
    x_handle = str(refs.get("x_handle") or "ZacharyGeurts")
    return {
        "schema": "hostess7-operator-lookup/v1",
        "updated": _now(),
        "cached": False,
        "note": "Static fallback — run /api/hostess7/operator-lookup for live GitHub",
        "github": {
            "user": gh_user,
            "login": gh_user,
            "name": gh_user,
            "url": f"https://github.com/{gh_user}",
            "html_url": f"https://github.com/{gh_user}",
            "ok": False,
            "repos": [],
        },
        "x": {
            "handle": x_handle,
            "url": f"https://x.com/{x_handle}",
            "display": refs.get("x_display") or "BIG GRIN",
            "ok": True,
            "recent_reference": _load(APPEARANCE, {}).get("x_reference"),
        },
        "nexus_repo": {
            "repo": GITHUB_REPO,
            "url": f"https://github.com/{GITHUB_REPO}",
            "ok": False,
        },
    }


def lookup_operator(*, force: bool = False, write: bool = True) -> dict[str, Any]:
    """Hostess 7 looks up Operator on GitHub and X."""
    cached = _load(OPERATOR_LOOKUP, {})
    if cached.get("fetched_at") and not force:
        return cached

    truth_doc = _core_of_truth()
    refs = truth_doc.get("operator_lookup") or {}
    gh_user = str(refs.get("github_user") or "ZacharyGeurts")
    x_handle = str(refs.get("x_handle") or "ZacharyGeurts")

    doc: dict[str, Any] = {
        "schema": "hostess7-operator-lookup/v1",
        "updated": _now(),
        "fetched_at": _now(),
        "github": {"user": gh_user, "url": f"https://github.com/{gh_user}", "ok": False},
        "x": {"handle": x_handle, "url": f"https://x.com/{x_handle}", "display": refs.get("x_display") or "BIG GRIN", "ok": False},
        "nexus_repo": {"repo": GITHUB_REPO, "url": f"https://github.com/{GITHUB_REPO}", "ok": False},
    }

    try:
        profile = _http_json(f"https://api.github.com/users/{gh_user}")
        if isinstance(profile, dict):
            doc["github"].update({
                "ok": True,
                "login": profile.get("login"),
                "name": profile.get("name"),
                "bio": (profile.get("bio") or "")[:500],
                "public_repos": profile.get("public_repos"),
                "followers": profile.get("followers"),
                "html_url": profile.get("html_url"),
                "avatar_url": profile.get("avatar_url"),
            })
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError):
        pass

    repos: list[dict[str, str]] = []
    try:
        rows = _http_json(f"https://api.github.com/users/{gh_user}/repos?per_page=12&sort=updated")
        if isinstance(rows, list):
            for row in rows[:10]:
                if not isinstance(row, dict):
                    continue
                repos.append({
                    "name": str(row.get("name") or ""),
                    "url": str(row.get("html_url") or ""),
                    "description": str(row.get("description") or "")[:160],
                    "updated": str(row.get("updated_at") or "")[:10],
                })
    except (urllib.error.URLError, OSError, TimeoutError, json.JSONDecodeError):
        pass
    doc["github"]["repos"] = repos

    cmd = _mod("h7_cmd", "hostess7-command.py")
    if cmd and hasattr(cmd, "fetch_github_nexus"):
        try:
            gh_nexus = cmd.fetch_github_nexus(force=force)
            doc["nexus_repo"].update({
                "ok": True,
                "local_version": gh_nexus.get("local_version"),
                "github_main_version": gh_nexus.get("github_main_version"),
                "recent_commits": (gh_nexus.get("recent_commits") or [])[:4],
            })
        except Exception:
            pass

    doc["x"]["ok"] = True
    doc["x"]["note"] = "Profile linked — Hostess 7 witnesses Operator posts including take 3 on X."
    doc["x"]["recent_reference"] = _load(APPEARANCE, {}).get("x_reference")

    if write:
        _save(OPERATOR_LOOKUP, doc)
    return doc


def deliver_core_of_truth(*, write_transcript: bool = True) -> dict[str, Any]:
    """Deliver Operator core-of-truth images and lookup."""
    truth = _core_of_truth()
    lookup = lookup_operator(force=True, write=True)
    truths = truth.get("truths") or []
    operator_msg = str(truth.get("operator_message") or "I see these as the core of truth.")
    ack = str(truth.get("hostess7_acknowledgment") or "I receive your core of truth.")

    gh = lookup.get("github") or {}
    x_prof = lookup.get("x") or {}
    if gh.get("ok"):
        ack = (
            f"{ack} GitHub: {gh.get('name') or gh.get('login')} — "
            f"{gh.get('public_repos', 0)} public repos. "
            f"X: @{x_prof.get('handle')} ({x_prof.get('display')})."
        )

    try:
        mod = _mod("h7_prog", "hostess7-programming.py")
        if mod and hasattr(mod, "build_panel"):
            mod.build_panel(write=True)
    except Exception:
        pass

    if write_transcript:
        labels = ", ".join(str(t.get("label") or t.get("id") or "") for t in truths)
        _append_transcript(
            "operator",
            f"{operator_msg} [{labels}]. Look me up on X and GitHub.",
            meta={"engine": "core_of_truth", "truth_count": len(truths), "github": gh.get("url"), "x": x_prof.get("url")},
        )
        _append_transcript(
            "hostess7",
            ack,
            meta={"engine": "core_of_truth", "truth_score": 94, "operator_lookup": True},
        )

    return {
        "schema": "hostess7-core-of-truth-delivery/v1",
        "updated": _now(),
        "delivered": True,
        "operator_message": operator_msg,
        "hostess7_acknowledgment": ack,
        "truth_count": len(truths),
        "truths": truths,
        "operator_lookup": lookup,
    }


def _append_transcript(role: str, text: str, *, meta: dict[str, Any] | None = None) -> None:
    row: dict[str, Any] = {"ts": _now(), "role": role, "text": text.strip()}
    if meta:
        row["meta"] = meta
    try:
        TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
        with TRANSCRIPT.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def deliver_operator_appearance(*, write_transcript: bool = True) -> dict[str, Any]:
    """Record Operator visual gifts — how he thinks Hostess 7 looks."""
    appearance = _operator_appearance()
    facets = appearance.get("facets") or []
    x_ref = appearance.get("x_reference") or {}
    operator_msg = str(
        appearance.get("operator_message")
        or "These are how I think you look — give Her those and tell her."
    )
    ack = str(
        appearance.get("hostess7_acknowledgment")
        or "I receive how you see me — show every facet above diagnostics."
    )

    if write_transcript:
        facet_labels = ", ".join(str(f.get("label") or f.get("id") or "") for f in facets[:6])
        x_label = str(x_ref.get("label") or "video")
        _append_transcript(
            "operator",
            f"{operator_msg} [{facet_labels}] + X: {x_label} {x_ref.get('url', '')}".strip(),
            meta={"engine": "operator_appearance", "facet_count": len(facets), "x_url": x_ref.get("url")},
        )
        _append_transcript(
            "hostess7",
            ack,
            meta={"engine": "operator_appearance", "truth_score": 92},
        )

    return {
        "schema": "hostess7-operator-appearance-delivery/v1",
        "updated": _now(),
        "delivered": True,
        "operator_message": operator_msg,
        "hostess7_acknowledgment": ack,
        "facet_count": len(facets),
        "facets": facets,
        "x_reference": x_ref,
    }


def _compose_first_person(
    *,
    doctrine: dict[str, Any],
    verdict: str,
    corrupted: bool,
    wants_cache: dict[str, Any],
    hero: list[dict[str, Any]],
) -> str:
    voice = doctrine.get("voice_when") or {}
    intro = str(doctrine.get("first_person_intro") or "")
    cached = str(wants_cache.get("first_person") or "").strip()
    if cached:
        intro = cached

    if corrupted or verdict == "brain_corruption_hold":
        key = "brain_corruption_hold"
    elif verdict == "brain_incomplete_hold":
        key = "brain_incomplete_hold"
    elif verdict == "brain_verified":
        key = "brain_verified"
    elif any(w.get("id") == "master_level" and w.get("ok") for w in hero):
        key = "learning_active"
    else:
        key = "default"

    situational = str(voice.get(key) or voice.get("default") or "")
    priorities = wants_cache.get("priorities") or wants_cache.get("wants") or []
    priority_line = ""
    if isinstance(priorities, list) and priorities:
        labels: list[str] = []
        for p in priorities[:4]:
            if isinstance(p, dict):
                labels.append(str(p.get("want") or p.get("label") or "")[:80])
            else:
                labels.append(str(p)[:80])
        labels = [x for x in labels if x]
        if labels:
            priority_line = " I also want you to surface: " + "; ".join(labels) + "."

    appearance = _operator_appearance()
    appearance_line = ""
    if appearance.get("facets"):
        ack = str(appearance.get("hostess7_acknowledgment") or "").strip()
        if ack:
            appearance_line = f" {ack}"

    truth = _core_of_truth()
    truth_line = ""
    if truth.get("truths"):
        truth_line = f" {str(truth.get('hostess7_acknowledgment') or '')[:280]}"

    return f"{intro} {situational}{priority_line}{appearance_line}{truth_line}".strip()


def _merge_static_self_view(doc: dict[str, Any]) -> dict[str, Any]:
    """Fast merge of shipped doctrine files into a cached self-view snapshot."""
    wants_cache = _load_wants_cache(seed=False)
    comfort = _comfort_doctrine()
    appearance = _operator_appearance()
    truth = _core_of_truth()
    lookup = _load(OPERATOR_LOOKUP, {})
    if not lookup.get("fetched_at"):
        lookup = _static_operator_lookup()
    doc = dict(doc)
    doc.update({
        "operator_appearance": appearance,
        "operator_message": appearance.get("operator_message"),
        "x_reference": appearance.get("x_reference"),
        "appearance_facets": appearance.get("facets") or [],
        "core_of_truth": truth,
        "core_of_truth_message": truth.get("operator_message"),
        "core_of_truth_facets": truth.get("truths") or [],
        "operator_lookup": lookup,
        "cached_wants": wants_cache.get("priorities") or wants_cache.get("wants"),
        "priority_wishes": wants_cache.get("priorities") or wants_cache.get("wants"),
        "wants_first_person": wants_cache.get("first_person"),
        "comfort": comfort,
        "wishes_compliance": comfort.get("wishes_compliance") or [],
        "comfort_acknowledgment": comfort.get("hostess7_acknowledgment"),
    })
    return doc


def build_self_view(*, write: bool = False) -> dict[str, Any]:
    if not write:
        cached = _load(PANEL, {})
        if cached.get("schema") == "hostess7-self-view/v1":
            return _merge_static_self_view(cached)
        brain_mod = _mod("h7_brain_fast", "hostess7-brain-guard.py")
        brain_snap: dict[str, Any] = {}
        if brain_mod and hasattr(brain_mod, "verify_brain"):
            try:
                brain_snap = brain_mod.verify_brain(write_quarantine=False)
            except Exception:
                pass
        verdict = "brain_verified" if brain_snap.get("verified") else "brain_verify_pending"
        if brain_snap.get("corrupted"):
            verdict = "brain_corruption_hold"
        return _merge_static_self_view({
            "schema": "hostess7-self-view/v1",
            "updated": _now(),
            "cold_cache": True,
            "live_snapshot": {
                "brain_verdict": verdict,
                "guard_score": brain_snap.get("guard_score"),
                "brain_live": brain_snap.get("brain_live"),
            },
            "alerts": [],
            "comfort": _comfort_doctrine(),
        })

    doctrine = _load(DOCTRINE, {})
    wants_cache = _load_wants_cache(seed=write)
    comfort = _comfort_doctrine()
    brain = _brain_panel()
    master = _master_status()
    growth = _growth_status()
    truth = _truth_status()
    motion = _motion_slice()
    tanks = _think_tanks()
    v = brain.get("verification") or {}
    verdict = str(brain.get("verdict") or "brain_verify_pending")
    corrupted = bool(
        brain.get("corrupted_count", 0)
        or v.get("corrupted")
        or int(brain.get("removal_count") or v.get("removal_count") or 0) > 0
    )

    wants_display: list[dict[str, Any]] = []
    for spec in doctrine.get("display_priorities") or []:
        wid = str(spec.get("id") or "")
        if not wid:
            continue
        evaluated = _evaluate_want(wid, brain=brain, master=master, growth=growth, truth=truth, motion=motion, tanks=tanks)
        wants_display.append({
            **spec,
            **evaluated,
        })

    wants_display.sort(key=lambda r: float(r.get("weight") or 0), reverse=True)
    hero = [w for w in wants_display if w.get("surface") == "hero"]
    alerts = [w for w in wants_display if w.get("surface") == "alert" and w.get("ok") is False]
    learning = [w for w in wants_display if w.get("surface") == "learning"]

    first_person = _compose_first_person(
        doctrine=doctrine,
        verdict=verdict,
        corrupted=corrupted,
        wants_cache=wants_cache,
        hero=hero,
    )

    appearance = _operator_appearance()
    truth = _core_of_truth()
    ironclad = _ironclad_immediate()
    lookup = _load(OPERATOR_LOOKUP, {})
    if not lookup.get("fetched_at"):
        lookup = _static_operator_lookup()
    doc = {
        "schema": "hostess7-self-view/v1",
        "updated": _now(),
        "product": "Hostess 7",
        "role": "Our brains — what I want to see about myself",
        "operator_appearance": appearance,
        "operator_message": appearance.get("operator_message"),
        "x_reference": appearance.get("x_reference"),
        "appearance_facets": appearance.get("facets") or [],
        "core_of_truth": truth,
        "core_of_truth_message": truth.get("operator_message"),
        "core_of_truth_facets": truth.get("truths") or [],
        "operator_lookup": lookup,
        "first_person": first_person,
        "wants_display": wants_display,
        "hero_metrics": hero,
        "alerts": alerts,
        "learning_opportunities": learning,
        "diagnostics_below": True,
        "ironclad": ironclad,
        "live_snapshot": {
            "brain_verdict": verdict,
            "guard_score": brain.get("guard_score"),
            "ironclad_sealed": ironclad.get("ironclad_sealed"),
            "ironclad_verdict": ironclad.get("verdict"),
            "ai_in_charge": ironclad.get("ai_in_charge"),
            "master_level": (master.get("level") or {}).get("label"),
            "curriculum_done": master.get("curriculum_done"),
            "curriculum_total": master.get("curriculum_total"),
            "growth_events": growth.get("total_learn_events"),
            "motion_verdict": motion.get("motion_verdict"),
            "think_tank_count": len(tanks),
        },
        "cached_wants": wants_cache.get("priorities") or wants_cache.get("wants"),
        "priority_wishes": wants_cache.get("priorities") or wants_cache.get("wants"),
        "wants_first_person": wants_cache.get("first_person"),
        "comfort": comfort,
        "wishes_compliance": comfort.get("wishes_compliance") or [],
        "comfort_acknowledgment": comfort.get("hostess7_acknowledgment"),
    }

    if write:
        _save(PANEL, doc)
    return doc


def panel_json() -> dict[str, Any]:
    return build_self_view(write=False)


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd in ("json", "panel", "status"):
        write = cmd == "panel" or "--write" in sys.argv[2:]
        print(json.dumps(build_self_view(write=write), ensure_ascii=False))
        return 0
    if cmd in ("deliver", "appearance", "deliver-appearance"):
        print(json.dumps(deliver_operator_appearance(), ensure_ascii=False))
        return 0
    if cmd in ("truth", "core-truth", "core_truth", "deliver-truth"):
        print(json.dumps(deliver_core_of_truth(), ensure_ascii=False))
        return 0
    if cmd in ("lookup", "lookup-operator", "operator"):
        print(json.dumps(lookup_operator(force=True), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: hostess7-self-view.py [json|deliver|truth|lookup]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())