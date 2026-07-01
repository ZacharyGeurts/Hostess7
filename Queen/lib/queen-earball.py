#!/usr/bin/env pythong
"""Queen → Final_Ear earball — assistive hearing tenant for Hostess 7."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from queen_final_ear import final_ear_env, final_ear_root, import_final_ear


def _ear_product_info() -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location(
        "final_ear_product", FINAL_EAR / "zocr_product.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod.product_info()

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
_LIB = Path(__file__).resolve().parent
FINAL_EAR = final_ear_root()
HOSTESS = Path(os.environ.get("HOSTESS7_ROOT", SG / "Hostess7"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _import_ear():
    import_final_ear()
    return final_ear_env(queen=QUEEN)


def earball_status() -> dict[str, Any]:
    _import_ear()
    from zocr_ear import ear_status, final_ear_status
    from zocr_entity_ear import twin_ear_status
    from zocr_ear_truth import truth_filter_status
    from zocr_ear_equipment import equipment_catalog
    final = final_ear_status()
    twins = twin_ear_status()
    from zocr_virtual_ear import virtual_ear_status

    virtual = virtual_ear_status()
    technology: dict[str, Any] = {}
    try:
        from zocr_zocram1_api import gac1_status
        technology["gac1"] = gac1_status()
    except ImportError:
        technology["gac1"] = {"ok": False, "error": "gac1_module_missing"}
    try:
        from zocr_sovereign_time import sovereign_time_status
        technology["sovereign_time"] = sovereign_time_status(seal=False)
    except ImportError:
        technology["sovereign_time"] = final.get("sovereign_time")
    technology["secure_path"] = {
        "schema": "queen-ear-secure-path/v1",
        "pipeline": "seal → sync → signal_intel → truth → ear_nn → eye_nn → quorum",
        "api_actions": [
            "secure_identify", "eye_ear_fusion", "identify", "signal_intel",
            "sovereign_time", "gac1", "pack_audio", "verify_audio",
            "sense_all", "desktop_audio", "sound_track", "sound_registry",
        ],
        "hostess_bridge": "Hostess7/scripts/field_final_ear_bridge.py",
    }
    try:
        from zocr_sound_tracker import tracker_status
        technology["sound_tracker"] = tracker_status()
    except ImportError:
        technology["sound_tracker"] = {"ok": True, "degraded": True, "never_fail": True}
    hostess7: dict[str, Any] = {"root": str(HOSTESS) if HOSTESS.is_dir() else None}
    bridge = HOSTESS / "scripts" / "field_final_ear_bridge.py"
    stack = HOSTESS / "data" / "hostess7-neural-stack.json"
    if bridge.is_file():
        hostess7["bridge"] = str(bridge)
        hostess7["bridge_cli"] = "pythong scripts/field_final_ear_bridge.py listen"
    if stack.is_file():
        try:
            hostess7["neural_stack"] = json.loads(stack.read_text(encoding="utf-8")).get("series", [])
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "schema": "queen-earball-hostess7/v1",
        "updated": _now(),
        "posture": "assistive",
        "rule": "We never presume hearing loss. Confidence always in Hearing.",
        "virtual_rule": virtual.get("rule"),
        "always": {"sovereign_time": True, "redundancy": True, "twins": True, "truth_forward": True},
        "twins": twins,
        "product": _ear_product_info(),
        "final_ear_root": str(FINAL_EAR),
        "hostess_root": str(HOSTESS) if HOSTESS.is_dir() else None,
        "hostess7": hostess7,
        "technology": technology,
        "final_ear": final,
        "ear": ear_status(),
        "virtual_ears": virtual,
        "truth_filters": truth_filter_status(),
        "equipment": equipment_catalog(),
        "redundancy": final.get("redundancy"),
        "sovereign_time": technology.get("sovereign_time") or final.get("sovereign_time"),
        "field_manual": {"sense": "audio", "api": "/api/field-manual?sense=audio"},
        "sense_neural_api": "/api/sense-neural",
    }


def earball_arm(mode: str = "dishes", *, start_stream: bool = False) -> dict[str, Any]:
    _import_ear()
    from zocr_entity_ear import make_living_live
    out = make_living_live(mode, start_stream=start_stream)
    out["schema"] = "queen-earball-arm/v1"
    out["posture"] = "assistive"
    return out


def earball_verify() -> dict[str, Any]:
    _import_ear()
    from zocr_ear_truth import apply_truth_filters
    from zocr_entity_ear import truth_forward

    status = earball_status()
    truth = apply_truth_filters()
    fwd = truth_forward(scan=False)
    sovereign = status.get("sovereign_time") or {}
    redundancy = status.get("redundancy") or {}
    ok = truth.get("ok") and redundancy.get("ok", True) and sovereign.get("ok", True)
    return {
        "ok": ok,
        "schema": "queen-earball-verify/v1",
        "truth_filter": truth,
        "truth_forward": fwd,
        "status": status,
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json"):
        return {"ok": True, **earball_status()}

    if action in ("arm", "final_mode", "mode"):
        return earball_arm(str(body.get("mode") or "dishes"), start_stream=bool(body.get("start_stream")))

    if action in ("verify", "verify_earball"):
        return earball_verify()

    if action in ("forward", "truth_forward"):
        _import_ear()
        from zocr_entity_ear import truth_forward
        return truth_forward(scan=body.get("scan", True) is not False)

    if action in ("truth_filter", "truth", "filter"):
        _import_ear()
        from zocr_ear_truth import apply_truth_filters
        return apply_truth_filters(
            evidence=body.get("evidence"),
            sources=body.get("sources"),
            peak_db=body.get("peak_db"),
            existence=body.get("existence"),
        )

    if action in ("localize", "bearing", "arrangement"):
        _import_ear()
        from zocr_ear_localize import localize_sources
        return localize_sources(
            channels=body.get("channels"),
            itd_us=body.get("itd_us"),
            level_db=body.get("level_db"),
            arrangement_hint=body.get("arrangement"),
        )

    if action in ("correlate", "existence", "correlate_existence"):
        _import_ear()
        from zocr_ear_localize import correlate_existence, localize_sources
        loc = body.get("localization") or localize_sources(
            itd_us=body.get("itd_us"),
            level_db=body.get("level_db"),
            arrangement_hint=body.get("arrangement"),
        )
        return correlate_existence(
            loc,
            sdf_entities=body.get("sdf_entities"),
            vision_bearings=body.get("vision_bearings"),
        )

    if action in ("equipment", "catalog"):
        _import_ear()
        from zocr_ear_equipment import equipment_catalog, equipment_resolve
        if body.get("profile"):
            return equipment_resolve(str(body["profile"]))
        return equipment_catalog(obscure_only=bool(body.get("obscure_only")))

    if action in ("listen", "living_live", "live"):
        return earball_arm(str(body.get("mode") or "dishes"), start_stream=True)

    if action in ("field_manual", "manual", "textbook"):
        _import_ear()
        from zocr_field_manual import field_manual_for_sense, field_manual_for_function
        if body.get("function"):
            return field_manual_for_function(str(body["function"]))
        sense = str(body.get("sense") or "audio")
        return field_manual_for_sense(sense)

    if action in ("twins", "entity"):
        _import_ear()
        from zocr_entity_ear import twin_ear_status
        return {"ok": True, **twin_ear_status()}

    if action in ("virtual", "virtual_status", "virtual_ears"):
        _import_ear()
        from zocr_virtual_ear import virtual_ear_status
        return {"ok": True, **virtual_ear_status()}

    if action in ("virtual_spawn", "spawn_virtual", "spawn_ear"):
        _import_ear()
        from zocr_virtual_ear import spawn_virtual_ear
        return spawn_virtual_ear(
            mechanism=str(body.get("mechanism") or "kinetic_eardrum"),
            point=body.get("point"),
            x_m=body.get("x_m"),
            y_m=body.get("y_m"),
            z_m=body.get("z_m"),
            bearing_deg=body.get("bearing_deg"),
            elevation_deg=body.get("elevation_deg"),
            distance_m=body.get("distance_m"),
            profile=body.get("profile"),
            label=body.get("label"),
            truth_bound=body.get("truth_bound", True) is not False,
        )

    if action in ("virtual_observe", "observe_virtual", "hear_point"):
        _import_ear()
        from zocr_virtual_ear import observe_virtual_ear
        eid = str(body.get("ear_id") or body.get("id") or "")
        if not eid:
            return {"ok": False, "error": "missing_ear_id"}
        return observe_virtual_ear(eid, existence=body.get("existence"))

    if action in ("virtual_remove", "remove_virtual"):
        _import_ear()
        from zocr_virtual_ear import remove_virtual_ear
        eid = str(body.get("ear_id") or body.get("id") or "")
        if not eid:
            return {"ok": False, "error": "missing_ear_id"}
        return remove_virtual_ear(eid)

    if action in ("virtual_grid", "spawn_ear_grid"):
        _import_ear()
        from zocr_virtual_ear import spawn_ear_grid
        return spawn_ear_grid(
            mechanism=str(body.get("mechanism") or "kinetic_eardrum"),
            count=int(body.get("count") or 4),
            radius_m=float(body.get("radius_m") or 2.0),
            height_m=float(body.get("height_m") or 1.5),
        )

    if action in ("neural", "neural_assist", "neural_analyze"):
        _import_ear()
        from zocr_neural_assist import analyze_audio, neural_assist_status
        if body.get("analyze"):
            return analyze_audio(context=body.get("context") or body)
        return {"ok": True, **neural_assist_status()}

    if action in ("encourage", "neural_encourage"):
        _import_ear()
        from zocr_neural_assist import encourage
        return encourage(label=str(body.get("label") or "clear_audio"), delta=float(body.get("delta") or 0.02), source=str(body.get("source") or "hostess7"))

    if action in ("offense", "countermeasure", "audio_offense"):
        _import_ear()
        from zocr_audio_offense import audio_offense_status, countermeasure_for
        if body.get("threat"):
            return countermeasure_for(str(body["threat"]), hostess_ok=True, eye_ear_quorum=body.get("eye_ear_quorum", True) is not False)
        return {"ok": True, **audio_offense_status()}

    if action in ("gac1", "zocram", "zocram1", "codec"):
        _import_ear()
        from zocr_zocram1_api import gac1_status
        return {"ok": True, **gac1_status()}

    if action in ("pack_audio", "pack_zocram", "encode_gac1"):
        _import_ear()
        from zocr_zocram1_api import pack_audio
        return pack_audio(
            pcm_path=body.get("pcm_path"),
            dest_path=body.get("dest_path") or body.get("path"),
            profile=str(body.get("profile") or "binaural_safe"),
            sample_rate=int(body.get("sample_rate") or 48000),
            channels=int(body.get("channels") or 2),
            pcm_hex=body.get("pcm_hex"),
        )

    if action in ("verify_audio", "verify_zocram", "verify_gac1"):
        _import_ear()
        from zocr_zocram1_api import verify_audio
        path = str(body.get("path") or body.get("zocram_path") or "")
        if not path:
            return {"ok": False, "error": "missing_path", "schema": "zocr-verify-audio/v1"}
        return verify_audio(path)

    if action in ("unpack_audio", "unpack_zocram", "decode_gac1"):
        _import_ear()
        from zocr_zocram1_api import unpack_audio
        path = str(body.get("path") or body.get("zocram_path") or "")
        if not path:
            return {"ok": False, "error": "missing_path", "schema": "zocr-unpack-audio/v1"}
        return unpack_audio(path, dest=body.get("dest_path"))

    if action in ("wire", "invincible_wire", "fused_analyze", "fused", "secure_path", "secure_identify"):
        import subprocess
        wire_action = "analyze" if action in ("fused_analyze", "fused", "secure_path", "secure_identify") else "status"
        proc = subprocess.run(
            [sys.executable, str(_LIB / "queen-sense-neural.py"), "dispatch"],
            input=json.dumps({**body, "action": wire_action, "secure_path": action in ("secure_path", "secure_identify") or body.get("secure_path", True)}),
            capture_output=True, text=True, timeout=120, cwd=str(QUEEN),
        )
        try:
            return json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return {"ok": False, "error": "wire_failed"}

    if action in ("identify", "signal_intel", "identify_sound"):
        _import_ear()
        from zocr_ear_signal_intel import identify_sound
        return identify_sound(
            evidence=body.get("evidence"),
            sources=body.get("sources"),
            existence=body.get("existence"),
            pcm_hex=body.get("pcm_hex"),
        )

    if action in ("sovereign_time", "seal_time", "time"):
        _import_ear()
        from zocr_sovereign_time import seal_ear_tick, sovereign_time_status, verify_eye_ear_sync, load_eye_sovereign_mono
        if body.get("verify_sync"):
            ear = seal_ear_tick(reason="sync_check")
            return verify_eye_ear_sync(eye_mono_ns=load_eye_sovereign_mono(), ear_mono_ns=ear.get("sealed_mono_ns"))
        if body.get("seal"):
            return seal_ear_tick(reason=str(body.get("reason") or "earball"))
        return sovereign_time_status(seal=body.get("seal", True) is not False)

    if action in ("eye_ear_fusion", "fusion"):
        _import_ear()
        from zocr_eye_ear_fusion import secure_neural_path
        return secure_neural_path(
            evidence=body.get("evidence"),
            sources=body.get("sources"),
            existence=body.get("existence"),
            localization=body.get("localization"),
            pcm_hex=body.get("pcm_hex"),
            image_path=body.get("image_path"),
            require_sync=body.get("require_sync", True) is not False,
        )

    if action in ("desktop_audio", "desktop", "desktop_harvest"):
        _import_ear()
        from zocr_desktop_audio import desktop_audio_status, follow_user_desktop, capture_monitor_chunk
        if body.get("capture"):
            return capture_monitor_chunk(seconds=float(body.get("seconds") or 2.0))
        if body.get("follow"):
            return follow_user_desktop(learn=body.get("learn", True) is not False)
        return desktop_audio_status()

    if action in ("sound_track", "track", "track_status", "sound_tracker"):
        _import_ear()
        from zocr_sound_tracker import tracker_status, tick_source, ingest_observations, set_pursuit_policy, sense_all
        if body.get("tick") or body.get("observation"):
            obs = body.get("observation") or body
            return tick_source(obs, learn=body.get("learn", True) is not False)
        if body.get("observations"):
            return ingest_observations(body["observations"], learn=body.get("learn", True) is not False)
        if body.get("policy") and body.get("sound_id"):
            return set_pursuit_policy(str(body["sound_id"]), str(body["policy"]))
        if body.get("sense_all") or action == "sense_all":
            return sense_all(learn=body.get("learn", True) is not False, include_desktop=body.get("include_desktop", True) is not False)
        return tracker_status()

    if action in ("sense_all", "hear_all", "all_lanes"):
        _import_ear()
        from zocr_sound_tracker import sense_all
        return sense_all(
            learn=body.get("learn", True) is not False,
            include_desktop=body.get("include_desktop", True) is not False,
        )

    if action in ("sound_registry", "registry", "permanent_id"):
        _import_ear()
        from zocr_sound_registry import registry_status, register_sound, resolve_sound
        if body.get("register") or body.get("observation"):
            return register_sound(body.get("observation") or body, neural_label=body.get("neural_label"))
        if body.get("sound_id"):
            return resolve_sound(str(body["sound_id"]))
        return registry_status()

    if action in ("sound_learn", "learn_sound"):
        _import_ear()
        from zocr_sound_learn import learn_from_observation, learn_status
        if body.get("track"):
            return learn_from_observation(body["track"], source=str(body.get("source") or "queen"))
        return learn_status()

    if action in ("spectrum", "spectrum_analyze", "auditory_spectrum"):
        _import_ear()
        from zocr_ear_spectrum import capture_and_analyze, spectrum_doctrine, analyze_pcm_spectrum
        if body.get("doctrine"):
            return {"ok": True, **spectrum_doctrine()}
        pcm_hex = body.get("pcm_hex")
        if pcm_hex:
            pcm = bytes.fromhex(str(pcm_hex))
            return analyze_pcm_spectrum(
                pcm,
                sample_rate=int(body.get("sample_rate_hz") or 48000),
                channels=int(body.get("channels") or 2),
                profile_id=body.get("profile"),
            )
        return capture_and_analyze(
            seconds=float(body.get("seconds") or 0.5),
            profile_id=body.get("profile"),
        )

    return {
        "ok": False,
        "error": "unknown_action",
        "actions": [
            "status", "arm", "verify", "forward", "truth_filter", "localize",
            "correlate", "equipment", "listen", "field_manual", "twins",
            "virtual", "virtual_spawn", "virtual_observe", "virtual_remove", "virtual_grid",
            "neural", "neural_analyze", "encourage", "offense", "countermeasure",
            "gac1", "zocram", "pack_audio", "verify_audio", "unpack_audio",
            "wire", "fused_analyze", "secure_path", "secure_identify", "eye_ear_fusion",
            "identify", "signal_intel", "sovereign_time",
            "desktop_audio", "sense_all", "sound_track", "sound_registry", "sound_learn",
            "spectrum", "spectrum_analyze", "auditory_spectrum",
        ],
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(earball_status(), ensure_ascii=False))
        return 0
    if cmd == "verify":
        print(json.dumps(earball_verify(), ensure_ascii=False))
        return 0
    if cmd == "arm":
        mode = sys.argv[2] if len(sys.argv) > 2 else "dishes"
        print(json.dumps(earball_arm(mode), ensure_ascii=False))
        return 0
    print(json.dumps({
        "error": "usage: queen-earball.py [json|verify|arm MODE|dispatch]",
    }, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())