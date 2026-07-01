#!/usr/bin/env pythong
"""Parallel field slice publish — each tab's fields refresh symmetrically."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
PANEL_JSON = STATE / "threat-panel.json"


def _queen_root() -> Path:
    qr = os.environ.get("QUEEN_ROOT", "").strip()
    if qr:
        p = Path(qr)
        if p.is_dir():
            return p
    candidate = INSTALL.parent / "Queen"
    return candidate if candidate.is_dir() else INSTALL

# panel JSON key -> (script relative to lib/, cli args)
FIELD_SLICES: dict[str, tuple[str, list[str]]] = {
    "field_hardware": ("field-hardware-probe.py", ["json"]),
    "field_hazard_onset": ("field-hazard-onset.py", ["panel"]),
    "lethal_enforcement": ("lethal-enforcement.py", ["panel"]),
    "hostess7_lethal_insight": ("hostess7-lethal-insight.py", ["panel"]),
    "hostess7_command": ("hostess7-command.py", ["panel"]),
    "hostess7_system_control": ("hostess7-system-control.py", ["json"]),
    "hostess7_tasklist": ("hostess7-tasklist.py", ["json"]),
    "hostess7_missions": ("hostess7-missions.py", ["panel"]),
    "hostess7_ingress_egress_gate": ("hostess7-ingress-egress-gate.py", ["panel"]),
    "hostess7_positional_awareness": ("hostess7-positional-awareness.py", ["panel"]),
    "hostess7_brain_training": ("hostess7-brain-training-chamber.py", ["panel"]),
    "hostess7_fifth_amendment": ("hostess7-fifth-amendment.py", ["panel"]),
    "hostess7_curiosity_corpus": ("hostess7-curiosity-corpus.py", ["panel"]),
    "hostess7_human_comfort": ("hostess7-human-comfort-training.py", ["panel"]),
    "field_h7b_brain": ("field-h7b-brain-storage.py", ["panel"]),
    "hostess7_operator": ("hostess7-operator.py", ["json"]),
    "hostess7_virtual_workspace": ("hostess7-virtual-workspace.py", ["json"]),
    "hostess7_noti": ("hostess7-noti.py", ["json"]),
    "noti_field": ("noti.py", ["json"]),
    "hostess7_master": ("hostess7-master.py", ["panel"]),
    "signals_field": ("signals-field.py", ["json"]),
    "field_radio": ("field-radio-catcher.py", ["json"]),
    "field_dns": ("field-dns.py", ["json"]),
    "field_outside_talk": ("field-outside-talk.py", ["json"]),
    "field_drive": ("field-drive-system.py", ["json"]),
    "home_protector": ("home-protector.py", ["json"]),
    "local_services": ("local-services-audit.py", ["json"]),
    "audio_train": ("audio-train.py", ["json"]),
    "field_rf": ("field-rf-sentinel.py", ["json"]),

    "h7_library": ("h7-library-bridge.py", ["build"]),
    "h7_corpus_sync": ("field-h7-corpus-sync.py", ["sync"]),
    "combinatorics_bridge": ("field-plate-combinatorics-bridge.py", ["build"]),
    "plate_meld_orchestrator": ("field-plate-meld-orchestrator.py", ["json"]),
    "hostess7_userwatch": ("hostess7-userwatch.py", ["json"]),
    "compatibility_layers": ("field-compatibility-layers.py", ["json"]),
    "field_filesystem": ("field-filesystem-update.py", ["json"]),
    "always_files": ("field-always-files.py", ["json"]),
    "field_diagnostic": ("field-diagnostic-mode.py", ["json"]),
    "packet_field": ("packet-field.py", ["json"]),
    "host_attacks": ("host-attack-map.py", ["json-panel"]),
    "us_field": ("field-us-intel.py", ["json"]),
    "us_obs_field": ("field-obs.py", ["us"]),
    "field_broadcaster": ("field-broadcaster.py", ["json"]),
    "field_obs": ("field-obs.py", ["json"]),
    "field_gpu": ("field-gpu-control.py", ["json"]),
    "c2_taskbar": ("field-c2-taskbar-plate.py", ["json"]),
    "field_shell_dock": ("field-shell-dock.py", ["json"]),
    "field_popcorn": ("field-popcorn-player.py", ["json"]),
    "field_ellie_fier": ("field-ellie-fier.py", ["json"]),
    "field_g16_launch": ("field-g16-launch.py", ["json"]),
    "field_audio": ("field-audio-settings.py", ["json"]),
    "field_lock": ("field-keepass.py", ["json"]),
    "code_bugfinder": ("field-code-bugfinder.py", ["json"]),
    "field_voltage_regulation": ("field-voltage-regulation.py", ["json"]),
    "us_voltage_regulation": ("field-voltage-regulation.py", ["us"]),
    "field_clean_juice": ("field-clean-juice.py", ["json"]),
    "field_power_ledger": ("field-power-ledger.py", ["json"]),
    "field_command": ("field-command.py", ["json"]),
    "browser_awareness": ("browser-awareness.py", ["json"]),
    "field_queen_browser": ("field-queen-browser.py", ["json"]),
    "field_stack": ("queen_field_nexus.py", ["json"]),
    "field_stack_layer": ("field-stack-layer.py", ["json"]),
    "trust_strike": ("trust-strike-engine.py", ["summary"]),
    "police_agency": ("police-agency-db.py", ["json"]),
    "human_registry": ("human-registry.py", ["json"]),
    "gov_intel": ("gov-intel-db.py", ["json"]),
    "program_tags": ("program-tags-db.py", ["json"]),
    "census_field": ("census-field-populate.py", ["json"]),
    "existence_identity": ("existence-identity.py", ["json"]),
    "operator_location": ("operator-location.py", ["json"]),
    "field_fabric": ("field-fabric-bridge.py", ["panel"]),
    "thermal_governor": ("thermal-governor.py", ["panel"]),
    "field_thermal_guard": ("field-thermal-guard.py", ["json"]),
    "port_ddos_shield": ("field-port-ddos-shield.py", ["json"]),
    "packet_deinterlace": ("field-packet-deinterlace.py", ["json"]),
    "kernel_meld": ("field-kernel-meld.py", ["json"]),
    "firmware_threat": ("field-firmware-threat-removal.py", ["json"]),
    "sense_package": ("field-sense-package-meld.py", ["json"]),
    "obs_threat_posterity": ("obs-threat-posterity-bridge.py", ["json"]),
    "eye_ear_plate": ("eye-ear-plate.py", ["json"]),
    "g16_compiler_sense": ("g16-compiler-sense-plate.py", ["json"]),
    "plate_test_runner": ("field-plate-test-runner.py", ["json"]),
    "plate_compiler": ("plate-compiler.py", ["json"]),
    "field_bus": ("field-unified-bus.py", ["json"]),
    "logic_gate": ("nexus-logic-gate.py", ["json"]),
    "znetwork": ("znetwork-orchestrator.py", ["json"]),
    "spatial_field": ("field-spatial-cognition.py", ["json"]),
    "universal_protector": ("universal-protector.py", ["json"]),
    "humanoid_motion": ("humanoid-motion-training.py", ["json"]),
    "iron_plate_motion": ("iron-plate-motion-resolve.py", ["resolve"]),
    "iron_plate_organize": ("iron-plate-organize.py", ["json"]),
    "iron_plate_spot": ("iron-plate-spot-detector.py", ["json"]),
    "ironclad_chips": ("field-ironclad-chips-combinatorics.py", ["json"]),
    "chips_plate_stack": ("field-chips-plate-stack.py", ["json"]),
    "chips_core": ("field-chips-core.py", ["json"]),
    "chips_program_usage": ("field-chips-program-usage.py", ["json"]),
    "program_combinatronic": ("field-program-combinatronic.py", ["json"]),
    "g16_universal": ("field-g16-universal-combinatronic.py", ["json"]),
    "cpu_library": ("field-cpu-library.py", ["json"]),
    "extensive_library": ("field-extensive-library.py", ["panel"]),
    "library_registry": ("field-library-registry.py", ["panel"]),
    "dewey_library": ("field-dewey-library.py", ["panel"]),
    "h7c_compression": ("field-h7c-compression.py", ["panel"]),
    "file_formats": ("field-file-formats.py", ["panel"]),
    "field_best_sort": ("field-best-sort.py", ["panel"]),
    "combinatronic_balance": ("field-combinatronic-balance.py", ["panel"]),
    "steel_neural_plates": ("field-steel-neural-plates.py", ["panel"]),
    "field_font": ("field-font-kit.py", ["panel"]),
    "creatable_lives": ("creatable-lives-assist.py", ["json"]),
    "right_to_exist": ("right-to-exist-mandate.py", ["json"]),
    "hostess7_brain": ("hostess7-brain-guard.py", ["json"]),
    "ironclad": ("ironclad-plate.py", ["json"]),
    "ironclad_immediate": ("ironclad-immediate.py", ["json"]),
    "ironclad_secure_api": ("ironclad-secure-api.py", ["status"]),
    "compile_autocorrect": ("field-compile-autocorrect.py", ["json"]),

    "ironclad_reality_field": ("ironclad-reality-field.py", ["json"]),
    "ironclad_field_sanity": ("ironclad-field-sanity.py", ["json"]),
    "hostess7_programming": ("hostess7-programming.py", ["json"]),
    "hostess7_g16": ("hostess7-g16.py", ["json"]),
    "nexus_g16_stack": ("nexus-g16-bridge.py", ["json"]),
    "plate_compiler": ("plate-compiler.py", ["json"]),
    "hostess7_codecraft": ("hostess7-codecraft.py", ["json"]),
    "hostess7_training": ("hostess7-training.py", ["json"]),
    "hostess7_calculator": ("hostess7-calculator.py", ["json"]),
    "hostess7_biology": ("hostess7-biology.py", ["json"]),
    "hostess7_engineering": ("hostess7-engineering.py", ["json"]),
    "hostess7_combat": ("hostess7-combat.py", ["json"]),
    "hostess7_mos": ("hostess7-mos.py", ["json"]),
}

QUEEN_SLICES: dict[str, tuple[str, list[str]]] = {
    "field_eyeball": ("lib/queen-eyeball.py", ["json"]),
    "field_earball": ("lib/queen-earball.py", ["json"]),
    "field_mouthball": ("lib/queen-mouthball.py", ["json"]),
}

STATE_SLICES: dict[str, tuple[str, dict[str, Any]]] = {
    "gatekeeper": ("connection-intent.json", {"connections": [], "harm_candidates": 0}),
    "angel_dossiers": ("angel-dossiers.json", {"dossier_count": 0, "dossiers": []}),
    "angel_research": ("angel-research.json", {"tables": {}}),
    "human_dossier": ("human-dossier.json", {"ip_count": 0, "ips": []}),
    "terror_spiderweb": ("terror-spiderweb-panel.json", {"schema": "terror-spiderweb/v2", "mode": "idle", "nodes": [], "edges": []}),
    "precision_field": ("precision-field-panel.json", {"schema": "precision-field/v1", "mode": "idle", "entities": [], "edges": []}),
}


def _env(*, cwd: Path | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
    env["NEXUS_STATE_DIR"] = str(STATE)
    sg = INSTALL.parent if INSTALL.name == "NewLatest" else INSTALL.parent.parent
    env.setdefault("SG_ROOT", str(sg))
    env.setdefault("QUEEN_ROOT", str(_queen_root()))
    queen = _queen_root()
    env.setdefault("FINAL_EYE_ROOT", str(sg / "Final_Eye"))
    env.setdefault("FINAL_EAR_ROOT", str(sg / "Final_Ear"))
    env.setdefault("FINAL_MOUTH_ROOT", str(sg / "Final_Mouth"))
    py_parts = [
        str(queen / "lib"),
        str(sg / "Final_Eye"),
        str(sg / "Final_Ear"),
        str(sg / "Final_Mouth"),
    ]
    if env.get("PYTHONPATH"):
        py_parts.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(p for p in py_parts if p)
    try:
        import importlib.util

        sp_py = INSTALL / "lib" / "sg_paths.py"
        if sp_py.is_file():
            spec = importlib.util.spec_from_file_location("sg_paths", sp_py)
            if spec and spec.loader:
                sp = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(sp)
                env.setdefault("HOSTESS7_ROOT", str(sp.hostess7_root()))
                env.setdefault("HOSTESS7_TEAM_FIELD", str(sp.hostess7_team_field()))
    except Exception:
        pass
    if cwd is not None:
        env["QUEEN_ROOT"] = str(cwd)
    return env


def _read_state_slice(key: str, filename: str, default: dict[str, Any]) -> tuple[str, Any | None]:
    fp = STATE / filename
    if not fp.is_file():
        return key, dict(default)
    try:
        doc = json.loads(fp.read_text(encoding="utf-8"))
        return key, doc if isinstance(doc, (dict, list)) else dict(default)
    except (OSError, json.JSONDecodeError):
        return key, dict(default)


def _run_slice(
    key: str,
    script_rel: str,
    args: list[str],
    *,
    root: Path | None = None,
) -> tuple[str, Any | None]:
    base = root or INSTALL
    script = base / script_rel if root else INSTALL / "lib" / script_rel
    if not script.is_file():
        return key, None
    try:
        proc = subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(root or INSTALL),
            env=_env(cwd=root),
        )
        if proc.returncode != 0 or not (proc.stdout or "").strip():
            return key, None
        return key, json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return key, None


def _h7s_lane() -> Any | None:
    if os.environ.get("NEXUS_H7S_LANE", "1") != "1":
        return None
    try:
        import importlib.util
        lane_py = INSTALL / "lib" / "field-h7s-lane.py"
        if not lane_py.is_file():
            return None
        spec = importlib.util.spec_from_file_location("field_h7s_lane_panel", lane_py)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _load_panel() -> dict[str, Any]:
    lane = _h7s_lane()
    if lane and hasattr(lane, "load_json"):
        doc = lane.load_json(PANEL_JSON, default=None)
        if isinstance(doc, dict):
            return doc
    try:
        return json.loads(PANEL_JSON.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"field": True}


def _save_panel(doc: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    tmp = PANEL_JSON.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(PANEL_JSON)


def _maybe_auto_engage_diagnostic() -> dict[str, Any] | None:
    try:
        import importlib.util

        diag_py = INSTALL / "lib" / "field-diagnostic-mode.py"
        if not diag_py.is_file():
            return None
        spec = importlib.util.spec_from_file_location("field_diagnostic_mode_engage", diag_py)
        if not spec or not spec.loader:
            return None
        dmod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(dmod)
        if dmod.active():
            return dmod.status(write=False)
        prob = dmod.detect_problems()
        policy = (dmod._doctrine() if hasattr(dmod, "_doctrine") else {}).get("policy") or {}
        if prob.get("should_engage") and policy.get("auto_engage_on_fault", True):
            return dmod.engage()
    except Exception:
        pass
    return None


def _radio_audio_disabled_keys() -> set[str]:
    """Field antenna / OTA radio / audio train removed from this install profile."""
    keys: set[str] = {"field_antenna"}
    if os.environ.get("NEXUS_SIGNALS_FIELD", "1") == "0":
        keys.add("signals_field")
    if os.environ.get("NEXUS_FIELD_RADIO", "1") == "0":
        keys.add("field_radio")
    if os.environ.get("NEXUS_AUDIO_TRAIN", "1") == "0":
        keys.add("audio_train")
    if os.environ.get("NEXUS_FIELD_RF_SENTINEL", "1") == "0":
        keys.add("field_rf")
    if os.environ.get("NEXUS_FIELD_RADIO", "1") == "0":
        keys.add("field_audio")
        keys.add("field_broadcaster")
    return keys


def _apply_slice_toggles(slices: dict[str, tuple[str, list[str]]]) -> dict[str, tuple[str, list[str]]]:
    drop = _radio_audio_disabled_keys()
    if not drop:
        return slices
    return {k: v for k, v in slices.items() if k not in drop}


def _diagnostic_filter_slices() -> dict[str, tuple[str, list[str]]]:
    base = _apply_slice_toggles(FIELD_SLICES)
    try:
        import importlib.util

        diag_py = INSTALL / "lib" / "field-diagnostic-mode.py"
        if not diag_py.is_file():
            return base
        spec = importlib.util.spec_from_file_location("field_diagnostic_mode", diag_py)
        if not spec or not spec.loader:
            return base
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "filter_field_slices"):
            return _apply_slice_toggles(mod.filter_field_slices(base))
    except Exception:
        pass
    return base


def publish_parallel(*, max_workers: int | None = None) -> dict[str, Any]:
    if max_workers is None:
        max_workers = int(os.environ.get("NEXUS_PANEL_PARALLEL_WORKERS", "8"))
    doc = _load_panel()
    doc["field"] = True
    doc["parallel_load"] = True
    updated: list[str] = []
    failed: list[str] = []
    diag_status = _maybe_auto_engage_diagnostic()
    if diag_status:
        doc["diagnostic_mode"] = diag_status
    slices = _diagnostic_filter_slices()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures: dict[Any, str] = {
            pool.submit(_run_slice, key, script, args): key
            for key, (script, args) in slices.items()
        }
        queen = _queen_root()
        for key, (script, args) in QUEEN_SLICES.items():
            futures[pool.submit(_run_slice, key, script, args, root=queen)] = key
        for key, (filename, default) in STATE_SLICES.items():
            futures[pool.submit(_read_state_slice, key, filename, default)] = key
        for fut in as_completed(futures):
            key = futures[fut]
            try:
                k, val = fut.result()
            except Exception:
                failed.append(key)
                continue
            if val is None:
                failed.append(k)
                continue
            doc[k] = val
            updated.append(k)

    doc["field_slices_updated"] = updated
    doc["field_slices_failed"] = failed
    _save_panel(doc)
    lane = _h7s_lane()
    if lane and hasattr(lane, "after_json_publish"):
        lane.after_json_publish(PANEL_JSON)
    return {
        "ok": True,
        "updated": updated,
        "failed": failed,
        "slice_count": len(updated),
        "panel": doc,
    }


def stored_panel() -> dict[str, Any]:
    """Return published threat-panel.json — no slice rebuild."""
    doc = _load_panel()
    keys = [k for k in doc if not str(k).startswith("_") and k not in ("field", "parallel_load")]
    return {
        "ok": True,
        "stored": True,
        "panel": doc,
        "slice_count": len(keys),
        "field_slices_updated": keys,
        "field_slices_failed": [],
    }


def _delegate_field() -> Any:
    import importlib.util

    py = INSTALL / "lib" / "field-panel-field.py"
    spec = importlib.util.spec_from_file_location("field_panel_field", py)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("usage: field-panel-parallel.py [publish|json|stored]", file=sys.stderr)
        return 1
    use_field = os.environ.get("NEXUS_FIELD_PLATES", "1") == "1"
    field_mod = _delegate_field() if use_field else None
    cmd = sys.argv[1]
    if cmd == "publish":
        if field_mod:
            field_mod.publish_field()
        else:
            publish_parallel()
        return 0
    if cmd == "stored":
        if field_mod:
            print(json.dumps(field_mod.stored_panel(), ensure_ascii=False))
        else:
            print(json.dumps(stored_panel(), ensure_ascii=False))
        return 0
    if cmd == "json":
        if field_mod:
            print(json.dumps(field_mod.publish_field(), ensure_ascii=False))
        else:
            print(json.dumps(publish_parallel(), ensure_ascii=False))
        return 0
    print(json.dumps({"ok": False, "error": "unknown_command"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
