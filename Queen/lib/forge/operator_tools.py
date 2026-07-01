"""Field Technology operator tools — ZOCR + Final_Eye + Final_Ear sense watch + live build."""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from forge.common import fail_result, ok_result
from forge.engine import ForgeContext, ForgeEngine, ForgeResult
from forge.field_paths import sg_root

_HANGUP_OCR_RE = re.compile(
    r"(loading|booting|please\s+wait|not\s+responding|hang|stuck|spinning|"
    r"initializing|sealing|hydrat|connecting)",
    re.I,
)
_COMPLETE_RE = re.compile(
    r"QUEEN BINARY READY|FORGE END verify ok=True|FORGE END field_tech ok=True|"
    r"FORGE END live_build_field ok=True|FORGE END field_package ok=True|"
    r"FORGE END field ok=True",
)
_FAIL_RE = re.compile(r"FORGE END \w+ ok=False|compile failed|CMake Error")


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _zocr_root(ctx: ForgeContext) -> Path:
    env = os.environ.get("ZOCR_ROOT", "").strip()
    if env and Path(env).is_dir():
        return Path(env)
    sg = sg_root(ctx.queen)
    zocr = sg / "ZOCR"
    if (zocr / "zocr_product.py").is_file():
        return zocr
    return zocr


def _final_eye_root(ctx: ForgeContext) -> Path:
    env = os.environ.get("FINAL_EYE_ROOT", "").strip()
    if env and Path(env).is_dir():
        return Path(env)
    sg = sg_root(ctx.queen)
    fe = sg / "Final_Eye"
    if (fe / "zocr_product.py").is_file() or (fe / "VERSION").is_file():
        return fe
    zocr = _zocr_root(ctx)
    if (zocr / "zocr_product.py").is_file():
        return zocr
    return fe


def _final_ear_root(ctx: ForgeContext) -> Path:
    env = os.environ.get("FINAL_EAR_ROOT", "").strip()
    if env and Path(env).is_dir():
        return Path(env)
    sg = sg_root(ctx.queen)
    ear = sg / "Final_Ear"
    if (ear / "zocr_product.py").is_file():
        return ear
    return ear


def _sense_env(ctx: ForgeContext) -> dict[str, str]:
    sg = sg_root(ctx.queen)
    zocr = _zocr_root(ctx)
    eye = _final_eye_root(ctx)
    ear = _final_ear_root(ctx)
    py_parts = [str(p) for p in (zocr, eye, ear) if p.is_dir()]
    py = os.pathsep.join(py_parts)
    if os.environ.get("PYTHONPATH"):
        py = py + os.pathsep + os.environ["PYTHONPATH"]
    return {
        **os.environ,
        "PYTHONPATH": py,
        "ZOCR_ROOT": str(zocr),
        "FINAL_EYE_ROOT": str(eye),
        "FINAL_EAR_ROOT": str(ear),
        "QUEEN_ROOT": str(ctx.queen),
        "SG_ROOT": str(sg),
        "GROK16_ROOT": os.environ.get("GROK16_ROOT", str(sg / "Grok16")),
        "NEXUS_INSTALL_ROOT": str(ctx.install),
        "NEXUS_STATE_DIR": str(ctx.state),
    }


def _zocr_env(ctx: ForgeContext) -> dict[str, str]:
    return _sense_env(ctx)


def _sense_look(ctx: ForgeContext, root: Path, *, label: str = "forge_watch") -> dict:
    script = root / "queen_forge_watch.py"
    if not script.is_file():
        script = root / "zocr_watch.py"
    if not script.is_file():
        return {"ok": False, "error": "sense_watch_missing", "root": str(root)}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "once", label],
            capture_output=True,
            text=True,
            timeout=45,
            env=_sense_env(ctx),
            cwd=str(root),
        )
        raw = (proc.stdout or "").strip()
        if raw.startswith("{"):
            return json.loads(raw)
        return {"ok": False, "tail": raw[-1500:], "returncode": proc.returncode, "root": str(root)}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "sense_timeout", "root": str(root)}
    except json.JSONDecodeError:
        return {"ok": False, "error": "sense_bad_json", "tail": raw[-800:], "root": str(root)}


def _zocr_look(ctx: ForgeContext, *, label: str = "forge_watch") -> dict:
    return _sense_look(ctx, _zocr_root(ctx), label=label)


def _sense_watch_once(ctx: ForgeContext, *, label: str = "forge_watch") -> dict:
    zocr = _sense_look(ctx, _zocr_root(ctx), label=f"{label}_zocr")
    eye = _sense_look(ctx, _final_eye_root(ctx), label=f"{label}_eye")
    ear = _sense_look(ctx, _final_ear_root(ctx), label=f"{label}_ear")
    forge = (zocr.get("forge") or eye.get("forge") or ear.get("forge") or {})
    ok = bool(zocr.get("ok") or eye.get("ok") or ear.get("ok"))
    return {
        "ok": ok,
        "forge": forge,
        "zocr": zocr,
        "final_eye": eye,
        "final_ear": ear,
        "capture": zocr.get("capture") or eye.get("capture") or ear.get("capture") or {},
    }


def _sense_blob(look: dict) -> str:
    parts: list[str] = []
    cap = look.get("capture") or {}
    parts.extend([
        str(cap.get("ocr_text") or ""),
        str(look.get("ocr_text") or ""),
    ])
    forge = look.get("forge") or {}
    parts.append(str(forge.get("tail") or ""))
    for key in ("zocr", "final_eye", "final_ear"):
        sub = look.get(key) or {}
        scap = sub.get("capture") or {}
        parts.append(str(scap.get("ocr_text") or ""))
        sforge = sub.get("forge") or {}
        parts.append(str(sforge.get("tail") or ""))
        if key == "final_ear":
            parts.append(json.dumps(sub.get("tracker") or {}, default=str))
    return "\n".join(parts).lower()


def _hangup_verdict(
    *,
    log_stall: int,
    stage_stall: int,
    stage: str,
    ocr_blob: str,
    running: bool,
    log_progress: bool,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if log_stall >= 2 and running and stage in ("compiling", "cmake_configure", "compiler_probe"):
        reasons.append(f"log_stall:{log_stall}")
    if stage_stall >= 3 and stage not in ("binary_ready", "idle", "failed", "rtx_done"):
        reasons.append(f"stage_stall:{stage}×{stage_stall}")
    if _HANGUP_OCR_RE.search(ocr_blob) and log_stall >= 1 and not log_progress:
        reasons.append("ocr_loading_pattern")
    if stage == "idle" and running and log_stall >= 2:
        reasons.append("idle_but_procs_running")
    return len(reasons) >= 1, reasons


def _log_snapshot(ctx: ForgeContext) -> dict:
    log = ctx.forge_log
    size = log.stat().st_size if log.is_file() else 0
    tail = ""
    if log.is_file():
        try:
            text = log.read_text(encoding="utf-8", errors="replace")
            tail = "\n".join(text.splitlines()[-24:])
        except OSError:
            pass
    complete = bool(log.is_file() and _COMPLETE_RE.search(tail))
    failed = bool(log.is_file() and _FAIL_RE.search(tail) and not complete)
    return {
        "updated": _ts(),
        "log": str(log),
        "bytes": size,
        "tail": tail,
        "complete": complete,
        "failed": failed,
        "progress": size > 0 and not complete and not failed,
    }


def _write_watch(ctx: ForgeContext, doc: dict) -> None:
    out = ctx.queen / "data" / "forge-watch.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _shutdown_final_eye(ctx: ForgeContext, engine: ForgeEngine) -> None:
    port = int(os.environ.get("FINAL_EYE_PORT", os.environ.get("ZOCR_PORT", "9479")))
    eye = _final_eye_root(ctx)
    pidfile = eye / "data" / "zocr-server.pid"
    engine.log(f"=== shutdown Final_Eye — :{port} ===")
    if (eye / "start.sh").is_file():
        try:
            subprocess.run(
                ["bash", str(eye / "start.sh"), "--stop"],
                capture_output=True,
                timeout=12,
                cwd=str(eye),
                env=_sense_env(ctx),
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    if pidfile.is_file():
        try:
            pid = int(pidfile.read_text(encoding="utf-8").strip())
            os.kill(pid, signal.SIGTERM)
        except (OSError, ValueError):
            pass
        pidfile.unlink(missing_ok=True)
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        pass


def _ensure_final_eye_assist(ctx: ForgeContext, engine: ForgeEngine) -> None:
    if os.environ.get("FINAL_EYE_ASSIST", "1").strip().lower() in ("0", "false", "no"):
        return
    port = int(os.environ.get("FINAL_EYE_PORT", os.environ.get("ZOCR_PORT", "9479")))
    eye = _final_eye_root(ctx)
    start = eye / "start.sh"
    if not start.is_file():
        engine.log(f"Final_Eye start.sh missing — skip assist ({eye})")
        return
    try:
        proc = subprocess.run(
            ["curl", "-sf", f"http://127.0.0.1:{port}/api/health"],
            capture_output=True,
            timeout=4,
        )
        if proc.returncode == 0:
            engine.log(f"Final_Eye already up :{port}")
            return
    except (OSError, subprocess.TimeoutExpired):
        pass
    engine.log(f"=== Final_Eye assist — {start} --no-open :{port} ===")
    try:
        subprocess.run(
            ["bash", str(start), "--no-open"],
            capture_output=True,
            text=True,
            timeout=45,
            cwd=str(eye),
            env=_sense_env(ctx),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        engine.log(f"Final_Eye assist warning: {exc}")


def _shutdown_old_queen(ctx: ForgeContext, engine: ForgeEngine) -> None:
    port = int(os.environ.get("QUEEN_WORLD_PORT", "9481"))
    engine.log(f"=== shutdown old Queen — :{port} + queen-browser ===")
    for pattern in (
        r"queen-browser.*--sovereign",
        r"lib/queen-world\.py",
        r"grokpy_driver\.py.*queen-world",
    ):
        try:
            subprocess.run(["pkill", "-f", pattern], capture_output=True, timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        pass
    _shutdown_final_eye(ctx, engine)
    time.sleep(0.4)
    engine.log("old Queen + Final_Eye processes stopped")


def run_forge_watch(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    interval = int(os.environ.get("QUEEN_WATCH_INTERVAL", "10"))
    ocr_on = os.environ.get("QUEEN_WATCH_OCR", "1").strip().lower() not in ("0", "false", "no")
    if "QUEEN_WATCH_LOOPS" in os.environ:
        loops = int(os.environ["QUEEN_WATCH_LOOPS"])
    elif os.environ.get("QUEEN_WATCH_LOOP", "").strip() in ("1", "true", "yes"):
        loops = 999999
    else:
        loops = 1
    if loops <= 0:
        loops = 999999
    zocr = _zocr_root(ctx)
    eye = _final_eye_root(ctx)
    ear = _final_ear_root(ctx)
    engine.log(
        f"=== forge:forge_watch — {ctx.forge_log} every {interval}s "
        f"ZOCR={zocr} Final_Eye={eye} Final_Ear={ear} sense={ocr_on} ==="
    )
    last_size = -1
    log_stall = 0
    last_stage = ""
    stage_stall = 0
    hangups = 0
    for i in range(loops):
        snap = _log_snapshot(ctx)
        delta = snap["bytes"] - last_size if last_size >= 0 else snap["bytes"]
        log_progress = delta > 0 or last_size < 0
        if snap["bytes"] == last_size and last_size >= 0:
            log_stall += 1
            status = f"LOG_STALL ({log_stall})"
        else:
            log_stall = 0
            status = "PROGRESS"

        look: dict = {}
        stage = "unknown"
        running = False
        if ocr_on:
            look = _sense_watch_once(ctx, label=f"forge_watch_{i + 1}")
            forge = look.get("forge") or {}
            stage = str(forge.get("stage") or "unknown")
            running = bool(forge.get("running"))
            if stage == last_stage and stage not in ("binary_ready", "rtx_done", "failed"):
                stage_stall += 1
            else:
                stage_stall = 0
                last_stage = stage
            hung, reasons = _hangup_verdict(
                log_stall=log_stall,
                stage_stall=stage_stall,
                stage=stage,
                ocr_blob=_sense_blob(look),
                running=running,
                log_progress=log_progress,
            )
            if hung:
                hangups += 1
                status = f"HANGUP ({'; '.join(reasons)})"
                engine.log(f"  ! HANGUP #{hangups}: {reasons}")

        engine.log(f"[{i + 1}] bytes={snap['bytes']} delta={delta} stage={stage} {status}")
        for ln in snap["tail"].splitlines()[-6:]:
            if ln.strip():
                engine.log(f"  | {ln[-120:]}")
        cap = look.get("capture") or {}
        if look.get("ok") and cap.get("ocr_file"):
            engine.log(f"  zocr: {cap['ocr_file']}")
        ear_tracks = ((look.get("final_ear") or {}).get("tracker") or {}).get("track_count")
        if ear_tracks is not None:
            engine.log(f"  ear: tracks={ear_tracks}")

        doc = {
            **snap,
            "stall_count": log_stall,
            "stage_stall": stage_stall,
            "stage": stage,
            "status": status,
            "hangup_count": hangups,
            "zocr_root": str(zocr),
            "final_eye_root": str(eye),
            "final_ear_root": str(ear),
            "sense": look if ocr_on else None,
            "ocr": look if ocr_on else None,
            "interval_seconds": interval,
        }
        _write_watch(ctx, doc)

        if snap["complete"]:
            engine.log("=== BUILD COMPLETE ===")
            return ok_result(engine, "forge_watch", "complete")
        if snap["failed"] and i > 0:
            engine.log("=== BUILD FAILED ===")
            return fail_result(engine, "forge_watch", "failed")
        last_size = snap["bytes"]
        if i + 1 < loops:
            time.sleep(interval)
    return ok_result(engine, "forge_watch", f"{loops} checks hangups={hangups}")


def live_build_plan(ctx: ForgeContext) -> list[str]:
    from forge.field_tech_pipeline import field_tech_plan, gcc_toolchain_step, should_run_gcc_build
    from forge.field_tools import FIELD_ORDER

    plan = list(field_tech_plan(ctx))
    if "compiler_probe" not in plan:
        plan.insert(1 if plan and plan[0] == "inside" else 0, "compiler_probe")
    if should_run_gcc_build(ctx):
        step = gcc_toolchain_step(ctx)
        for old in ("gcc_build", "gcc_rebuild", "g16_install"):
            while old in plan:
                plan.remove(old)
        rtx_i = plan.index("rtx") if "rtx" in plan else len(plan)
        plan.insert(rtx_i, step)
        plan.insert(rtx_i + 1, "g16_install")
    full = os.environ.get("QUEEN_FULL_FIELD", "1").strip().lower() not in ("0", "false", "no")
    if full:
        for step in FIELD_ORDER:
            if step == "rtx":
                continue
            if step not in plan:
                plan.append(step)
    verify_i = plan.index("verify") if "verify" in plan else len(plan)
    for step in ("queen_eyeball", "queen_earball"):
        if step not in plan:
            plan.insert(verify_i + 1, step)
            verify_i += 1
    return plan


def run_live_build_field(ctx: ForgeContext, engine: ForgeEngine) -> ForgeResult:
    """Shutdown old Queen → latest g16 → full native field-tech + ZOCR watch."""
    from forge.tools import TOOL_REGISTRY

    _shutdown_old_queen(ctx, engine)
    _ensure_final_eye_assist(ctx, engine)
    engine.clear_log()
    plan = live_build_plan(ctx)
    engine.log("=== forge:live_build_field — full native field + Grok16 g16 ===")
    engine.log(f"ZOCR_ROOT={_zocr_root(ctx)}")
    engine.log(f"FINAL_EYE_ROOT={_final_eye_root(ctx)}")
    engine.log(f"FINAL_EAR_ROOT={_final_ear_root(ctx)}")
    engine.log(f"plan: {' → '.join(plan)}")

    interval = int(os.environ.get("QUEEN_WATCH_INTERVAL", "10"))
    watch_proc: subprocess.Popen[str] | None = None
    if os.environ.get("QUEEN_WATCH_INLINE", "1").strip().lower() not in ("0", "false", "no"):
        watch_py = ctx.queen / "lib" / "queen-forge.py"
        watch_env = {
            **_sense_env(ctx),
            "QUEEN_WATCH_LOOP": "1",
            "QUEEN_WATCH_INTERVAL": str(interval),
            "QUEEN_WATCH_OCR": "1",
        }
        watch_proc = subprocess.Popen(
            [sys.executable, str(watch_py), "run", "forge_watch"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=watch_env,
            cwd=str(ctx.queen),
            start_new_session=True,
        )
        engine.log(f"sense forge_watch started pid={watch_proc.pid} every {interval}s")

    results: list[dict] = []
    force_probe = {"compiler_probe", "gcc_rebuild", "verify"}
    if "gcc_rebuild" not in plan and "gcc_build" not in plan:
        force_probe.add("g16_install")
    for tid in plan:
        tool = TOOL_REGISTRY.get(tid)
        if not tool:
            engine.log(f"SKIP unknown {tid}")
            continue
        if tool.check(ctx) and tid not in force_probe:
            engine.log(f"SKIP {tid} — ready")
            results.append({"tool": tid, "skipped": True, "ok": True})
            continue
        engine.log(f"FORGE START {tid}")
        r = tool.run(ctx, engine)
        row = r.to_dict()
        results.append(row)
        engine.log(f"FORGE END {tid} ok={r.ok}")
        if not r.ok and tid in (
            "inside", "deps", "shaders", "rtx", "compiler_probe", "g16_install", "gcc_rebuild",
            "field_kernel", "field_package",
        ):
            if tid == "g16_install" and row.get("skipped") is not True:
                engine.log("g16_install failed — attempting gcc_rebuild then retry g16_install")
                rb = TOOL_REGISTRY.get("gcc_rebuild")
                if rb:
                    rr = rb.run(ctx, engine)
                    results.append(rr.to_dict())
                    if rr.ok:
                        engine.log("FORGE RETRY g16_install")
                        r2 = tool.run(ctx, engine)
                        results.append(r2.to_dict())
                        engine.log(f"FORGE END g16_install ok={r2.ok}")
                        if r2.ok:
                            continue
            if watch_proc and watch_proc.poll() is None:
                watch_proc.send_signal(signal.SIGTERM)
            return ForgeResult(ok=False, tool="live_build_field", message=f"stopped at {tid}", tail=engine.tail_buffer())

    if watch_proc and watch_proc.poll() is None:
        watch_proc.send_signal(signal.SIGTERM)
        try:
            watch_proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            watch_proc.kill()

    ok = all(r.get("ok", r.get("skipped")) for r in results)
    engine.log(f"=== live_build_field {'OK' if ok else 'FAILED'} ===")
    return ForgeResult(
        ok=ok,
        tool="live_build_field",
        message=f"{len(plan)} steps",
        tail=engine.tail_buffer(),
    )


def check_forge_watch(ctx: ForgeContext) -> bool:
    return (ctx.queen / "data" / "forge-watch.json").is_file()


def check_live_build_field(ctx: ForgeContext) -> bool:
    snap = _log_snapshot(ctx)
    return bool(snap.get("complete"))


OPERATOR_TOOLS: dict[str, tuple[str, str, object, object, str | None]] = {
    "forge_watch": (
        "ZOCR + Final_Eye + Final_Ear poll .queen-forge.log — catch hangups ~10s",
        "operator",
        run_forge_watch,
        check_forge_watch,
        "scripts/watch-build.sh",
    ),
    "live_build_field": (
        "Shutdown old Queen → g16 field-tech + sovereign field + tri-sense watch",
        "operator",
        run_live_build_field,
        check_live_build_field,
        "scripts/live-build-field.sh",
    ),
}