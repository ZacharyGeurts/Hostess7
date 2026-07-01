#!/usr/bin/env pythong
"""Queen KILROY + AMOURANTHRTX bridge — Field OS kernel, engine, FieldKilroy telemetry."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
AMOURANTHRTX_REPO = "https://github.com/ZacharyGeurts/AMOURANTHRTX"
ECOSYSTEM_REPOS = {
    "field_primer": {
        "name": "Field_Primer",
        "github": "https://github.com/ZacharyGeurts/Field_Primer",
        "path": "SG/Field_Primer",
        "role": "Field Technology v5 doctrine",
    },
    "final_eye": {
        "name": "Final_Eye",
        "github": "https://github.com/ZacharyGeurts/Final_Eye",
        "path": "SG/Final_Eye",
        "role": "Vision + stoard + field compiler bridge",
        "version_file": "VERSION",
    },
    "world_redata": {
        "name": "World_Redata",
        "github": "https://github.com/ZacharyGeurts/World_Redata",
        "path": "SG/World_Redata",
        "role": "WRDT1 lossless envelopes",
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_field_paths():
    spec = importlib.util.spec_from_file_location(
        "field_paths", QUEEN / "lib" / "forge" / "field_paths.py"
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _sg_root() -> Path:
    env = os.environ.get("SG_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return SG.resolve()


def kilroy_root() -> Path:
    env = os.environ.get("KILROY_ROOT", "").strip()
    if env:
        p = Path(env).expanduser().resolve()
        if (p / "scripts" / "build-kilroy.sh").is_file():
            return p
    sg = _sg_root()
    for candidate in (
        sg.parent / "KILROY",
        sg / "KILROY",
        Path.home() / "Desktop" / "KILROY",
        Path.home() / "KILROY",
    ):
        if (candidate / "scripts" / "build-kilroy.sh").is_file():
            return candidate.resolve()
    return sg / "KILROY"


def amouranthrtx_root() -> Path:
    env = os.environ.get("AMOURANTHRTX_ROOT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    for candidate in (
        QUEEN / "engine" / "AMOURANTHRTX",
        _sg_root() / "NewLatest" / "AMOURANTHRTX",
        _sg_root() / "AMOURANTHRTX",
    ):
        if candidate.is_dir() and (candidate / "CMakeLists.txt").is_file():
            return candidate.resolve()
    return (_sg_root() / "NewLatest" / "AMOURANTHRTX").resolve()


def _read_proc(rel: str, limit: int = 4000) -> str:
    try:
        return Path(rel).read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _kilroy_version_file(root: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    vf = root / "KILROY_VERSION"
    if not vf.is_file():
        return out
    for line in vf.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or "=" not in line:
            if line and "abi" not in out:
                out["product"] = line
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _git_head(repo: Path) -> dict[str, Any]:
    if not (repo / ".git").exists():
        return {"present": False}
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "log", "-1", "--format=%H %s"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return {"present": True, "error": proc.stderr[:200]}
        parts = (proc.stdout or "").strip().split(" ", 1)
        remote = subprocess.run(
            ["git", "-C", str(repo), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return {
            "present": True,
            "commit": parts[0] if parts else "",
            "subject": parts[1] if len(parts) > 1 else "",
            "remote": (remote.stdout or "").strip() or AMOURANTHRTX_REPO,
        }
    except (subprocess.TimeoutExpired, OSError) as exc:
        return {"present": True, "error": str(exc)}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _ecosystem_status() -> dict[str, Any]:
    sg = _sg_root()
    out: dict[str, Any] = {}
    for rid, meta in ECOSYSTEM_REPOS.items():
        path = sg / meta["path"].replace("SG/", "")
        entry: dict[str, Any] = {
            "id": rid,
            "name": meta["name"],
            "github": meta["github"],
            "path": str(path),
            "present": path.is_dir(),
            "role": meta["role"],
        }
        if path.is_dir():
            entry["git"] = _git_head(path)
        vf = meta.get("version_file")
        if vf and (path / vf).is_file():
            entry["version"] = (path / vf).read_text(encoding="utf-8").strip()
        out[rid] = entry
    return out


def _hostess_ai_wishes() -> dict[str, Any]:
    """Ask Hostess 7 what the AI kernel should honor (live via Queen bridge)."""
    bridge = QUEEN / "lib" / "queen-hostess-brain.py"
    if not bridge.is_file():
        return {"available": False}
    try:
        proc = subprocess.run(
            [sys.executable, str(bridge), "json"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=90,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return {"available": False, "error": "bridge_failed"}
        doc = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as e:
        return {"available": False, "error": str(e)}
    sdf = doc.get("sdf") or {}
    ops = doc.get("hostess7_brain_ops") or {}
    eye = (doc.get("final_eye_doctrine") or {}).get("eye_operations") or {}
    return {
        "available": True,
        "comfort": (doc.get("comfort") or {}).get("comfort") or ops.get("comfort"),
        "truth_filter": "94pct_noise_6pct_truth",
        "sdf_segments": sdf.get("segments"),
        "human_plates": sdf.get("human_plates"),
        "heaven": eye.get("heaven"),
        "hell": eye.get("hell"),
        "default_mode": "war",
        "war_mode": "war",
        "kernel_proc": "/proc/kilroy_field/ai",
        "wishes": [
            "sovereign_storage=cache/fieldstorage/brain/sdf/",
            "lossless_redata_is_law",
            "truth_filter_before_plates",
            "heaven_zero_cost_home",
            "hell_offense_when_corroborated",
        ],
    }


def _final_eye_brain_status(kr: Path) -> dict[str, Any]:
    """Grok OCR brain — Final Eye vision slice."""
    doctrine = _load_json(kr / "data" / "kilroy-final-eye-doctrine.json")
    eye_py = QUEEN.parent / "lib" / "kilroy-final-eye-brain.py"
    marker = _load_json(Path(os.environ.get("NEXUS_STATE_DIR", QUEEN.parent / ".nexus-state")) / "kilroy-final-eye-brain.json")
    proc_eye = _read_proc("/proc/kilroy_field/eye", 2500)
    board: dict[str, Any] = {}
    if eye_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(eye_py), "ocr-brain"],
                cwd=str(QUEEN.parent),
                capture_output=True,
                text=True,
                timeout=20,
                env={
                    **os.environ,
                    "NEXUS_INSTALL_ROOT": str(QUEEN.parent),
                    "KILROY_ROOT": str(kr),
                    "NEXUS_STATE_DIR": os.environ.get("NEXUS_STATE_DIR", str(QUEEN.parent / ".nexus-state")),
                },
            )
            if proc.returncode == 0 and proc.stdout.strip():
                board = json.loads(proc.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            board = {}
    return {
        "schema": doctrine.get("schema", "kilroy-final-eye-doctrine/v1"),
        "doctrine": doctrine,
        "proc": "/proc/kilroy_field/eye",
        "marker": marker or None,
        "ocr_brain": board or None,
        "proc_eye": proc_eye[:2500] if proc_eye else None,
        "module": str(eye_py) if eye_py.is_file() else None,
        "policy": doctrine.get("policy", "telemetry_only_no_recording"),
    }


def _field_brain_status(kr: Path) -> dict[str, Any]:
    """KILROY Field Brain — Hostess7 + Ironclad + Universal Protector stack board."""
    doctrine = _load_json(kr / "data" / "kilroy-field-brain-doctrine.json")
    brain_py = QUEEN.parent / "lib" / "kilroy-field-brain.py"
    marker = _load_json(Path(os.environ.get("NEXUS_STATE_DIR", QUEEN.parent / ".nexus-state")) / "kilroy-field-brain.json")
    proc_brain = _read_proc("/proc/kilroy_field/brain", 2500)
    board: dict[str, Any] = {}
    if brain_py.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(brain_py), "board"],
                cwd=str(QUEEN.parent),
                capture_output=True,
                text=True,
                timeout=12,
                env={
                    **os.environ,
                    "NEXUS_INSTALL_ROOT": str(QUEEN.parent),
                    "KILROY_ROOT": str(kr),
                    "NEXUS_STATE_DIR": os.environ.get("NEXUS_STATE_DIR", str(QUEEN.parent / ".nexus-state")),
                },
            )
            if proc.returncode == 0 and proc.stdout.strip():
                board = json.loads(proc.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
            board = {}
    return {
        "schema": doctrine.get("schema", "kilroy-field-brain/v1"),
        "doctrine": doctrine,
        "proc": "/proc/kilroy_field/brain",
        "marker": marker or None,
        "board": board or None,
        "proc_brain": proc_brain[:2500] if proc_brain else None,
        "stack_order": doctrine.get("stack_order") or [],
        "verdict_rule": doctrine.get("verdict_rule"),
        "module": str(brain_py) if brain_py.is_file() else None,
    }


def _field_stack_mandate(kr: Path) -> dict[str, Any]:
    doc = _load_json(kr / "data" / "field-stack-mandate.json")
    proc_stack = _read_proc("/proc/kilroy_field/stack", 3000)
    return {
        **doc,
        "proc_stack": proc_stack or None,
        "recompile": str(kr / "scripts" / "field-recompile.sh"),
        "check": str(kr / "scripts" / "check-field-stack.sh"),
        "fieldc_manifest": str(kr / "field" / "compiler" / "manifest.json"),
    }


def _queen_binary() -> Path | None:
    for p in (
        QUEEN / "build" / "rtx" / "bin" / "Linux" / "queen-browser",
        QUEEN / "field" / "sovereign" / "queen" / "bin" / "queen-browser",
    ):
        if p.is_file():
            return p.resolve()
    return None


def resolve_program_usage(program_id: str) -> dict[str, Any]:
    """CHIPs program usage lane — kilroy_integration via field-chips-program-usage."""
    install = Path(os.environ.get("NEXUS_INSTALL_ROOT", SG / "NewLatest"))
    script = install / "lib" / "field-chips-program-usage.py"
    if not script.is_file():
        return {"schema": "field-chips-program-usage/v1", "ok": False, "program_id": program_id}
    try:
        proc = subprocess.run(
            [sys.executable, str(script), "resolve", program_id],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(install)},
        )
        return json.loads(proc.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError):
        return {"schema": "field-chips-program-usage/v1", "ok": False, "program_id": program_id}


def kilroy_status() -> dict[str, Any]:
    fp = _load_field_paths()
    kr = kilroy_root()
    arts = fp.kernel_artifacts(QUEEN)
    runtime = fp.kernel_runtime()
    version = _kilroy_version_file(kr)
    proc_status = _read_proc("/proc/kilroy_field/status")
    proc_boot = _read_proc("/proc/kilroy_field/boot", 2000)
    proc_stack = _read_proc("/proc/kilroy_field/stack", 2500)
    proc_ai = _read_proc("/proc/kilroy_field/ai", 2000)
    proc_brain = _read_proc("/proc/kilroy_field/brain", 2500)
    config_die = False
    config_brain = False
    cfg = kr / "build" / "config"
    try:
        if cfg.is_file():
            cfg_text = cfg.read_text(encoding="utf-8", errors="replace")
            config_die = "CONFIG_RTX_FIELD_DIE=y" in cfg_text
            config_brain = "CONFIG_RTX_FIELD_BRAIN_STACK=y" in cfg_text
    except OSError:
        pass
    return {
        "schema": "queen-kilroy/v1",
        "updated": _now(),
        "product": version.get("product") or "KILROY Field OS",
        "abi": version.get("abi") or "kilroy-field-1.0",
        "layout": version.get("layout") or "9",
        "identity": version.get("identity") or "Field",
        "compatible": version.get("compatible") or "Linux-POSIX",
        "kilroy_root": str(kr),
        "kilroy_present": kr.is_dir(),
        "build_script": str(kr / "scripts" / "build-kilroy.sh") if (kr / "scripts" / "build-kilroy.sh").is_file() else None,
        "artifacts": {k: str(v) if v else None for k, v in arts.items()},
        "config_rtx_field_die": config_die,
        "config_rtx_field_brain": config_brain,
        "runtime": runtime,
        "proc": {
            "status": proc_status[:1200] if proc_status else None,
            "boot": proc_boot[:800] if proc_boot else None,
            "stack": proc_stack[:2500] if proc_stack else None,
            "ai": proc_ai[:2000] if proc_ai else None,
            "brain": proc_brain[:2500] if proc_brain else None,
            "eye": _read_proc("/proc/kilroy_field/eye", 2000) or None,
        },
        "ai_kernel": _load_json(kr / "data" / "kilroy-ai-mandate.json"),
        "perimeter_war": _load_json(kr / "data" / "kilroy-perimeter-war-doctrine.json"),
        "field_brain": _field_brain_status(kr),
        "final_eye_brain": _final_eye_brain_status(kr),
        "hostess7_comfort": _load_json(kr / "data" / "hostess7-comfort-package.json"),
        "hostess7_ai_wishes": _hostess_ai_wishes(),
        "field_stack": _field_stack_mandate(kr),
        "ecosystem": _ecosystem_status(),
        "rank": 1,
        "motto_stack": "Number one with KILROY",
        "telemetry": {
            "proc": "/proc/kilroy_field",
            "dev": "/dev/kilroy_field",
            "slots": ["TIME", "RAM", "THERMO", "CONTEXT", "CPU", "FLOW", "CACHE", "DIRECT"],
        },
        "forge_tools": ["field_substrate", "field_kernel", "field_boot", "field_rootfs", "field_package"],
        "chips_usage": resolve_program_usage("kilroy"),
        "grok16_bridge": _load_json(kr / "data" / "kilroy-grok16-bridge.json"),
        "grok16_pair": version.get("grok16_pair") or _load_json(kr / "data" / "kilroy-version.json").get("stack_pairing", {}).get("grok16"),
        "kernel_test": str(kr / "scripts" / "kilroy-kernel-test.sh") if (kr / "scripts" / "kilroy-kernel-test.sh").is_file() else None,
        "amouranthrtx": amouranthrtx_status(),
    }


def amouranthrtx_status() -> dict[str, Any]:
    rtx = amouranthrtx_root()
    git = _git_head(rtx)
    qa = rtx / "build-release" / "bin" / "Linux" / "qa_field_kilroy_test"
    if not qa.is_file():
        qa = rtx / "build" / "bin" / "Linux" / "qa_field_kilroy_test"
    zc = _load_json(QUEEN / "data" / "queen-zero-cost-4slot.json")
    install = _sg_root() / "AmmoOS"
    rtx_doc = _load_json(install / "data" / "field-rtx-display-doctrine.json")
    if not rtx_doc:
        rtx_doc = _load_json(_sg_root() / "AmmoOS" / "data" / "field-rtx-display-doctrine.json")
    os_shaders = [
        str(mod.get("id"))
        for mod in (rtx_doc.get("os_shaders") or {}).get("modules") or []
        if mod.get("id")
    ]
    shader_dir = rtx / "Navigator" / "shaders" / "compute"
    os_ok = all((shader_dir / f"{s}.comp").is_file() for s in os_shaders) if os_shaders else False
    canvas_mod = None
    canvas_path = QUEEN / "lib" / "queen-canvas-renderer.py"
    if canvas_path.is_file():
        try:
            spec = importlib.util.spec_from_file_location("queen_canvas_kilroy", canvas_path)
            if spec and spec.loader:
                cm = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(cm)
                if hasattr(cm, "posture"):
                    canvas_mod = cm.posture()
        except Exception:
            canvas_mod = None
    return {
        "schema": "queen-field-rtx/v1",
        "repo": AMOURANTHRTX_REPO,
        "root": str(rtx),
        "present": rtx.is_dir() and (rtx / "CMakeLists.txt").is_file(),
        "role": rtx_doc.get("role", "display_technology"),
        "is_gui": rtx_doc.get("is_gui", False),
        "stack_layer": (rtx_doc.get("stack_layer") or {}).get("id", "ammoos_desktop"),
        "default_canvas": (rtx_doc.get("os_shaders") or {}).get("default", "CANVAS"),
        "desktop_comp_shader": (rtx_doc.get("queen_backend") or {}).get("desktop_comp_shader", False),
        "os_shaders": os_shaders,
        "os_shaders_ok": os_ok,
        "demo_shaders_policy": "demos_only — set AMOURANTHRTX_DEMO=1",
        "engines": {
            "pipeline": (rtx / "Navigator" / "engine" / "Pipeline.hpp").is_file(),
            "field_fabric": (rtx / "Navigator" / "engine" / "FieldFabric.hpp").is_file(),
            "field_thermal_guard": (rtx / "Navigator" / "engine" / "FieldThermalGuard.hpp").is_file(),
            "field_gpu_launch": (rtx / "Navigator" / "engine" / "FieldGpuLaunch.hpp").is_file(),
            "field_rtx_drivers": (rtx / "Navigator" / "engine" / "FieldRtxDrivers.hpp").is_file(),
        },
        "zero_cost_4_slot": {
            "enabled": True,
            "runtime_tax": zc.get("runtime_tax", 0),
            "tamper_action": zc.get("tamper_action", "abort"),
            "slots": zc.get("slots") or [
                {"id": "TIME"}, {"id": "MEMORY"}, {"id": "THERMO"}, {"id": "CONTEXT"},
            ],
            "queen_exceeds": zc.get("queen_exceeds_rtx", True),
        },
        "field_kilroy": str(rtx / "FieldKilroy"),
        "field_kilroy_present": (rtx / "FieldKilroy" / "FieldKilroyCompat.hpp").is_file(),
        "canvas_renderer": canvas_mod,
        "kilroy_os_script": str(rtx / "scripts" / "build_kilroy_os.sh"),
        "git": git,
        "qa_field_kilroy": str(qa) if qa.is_file() else None,
        "build": {
            "canvas": "pythong Queen/lib/queen-canvas-renderer.py json",
            "kilroy_os": f"{rtx}/scripts/build_kilroy_os.sh all",
            "field_kilroy_qa": f"{rtx}/scripts/field_kilroy.sh qa",
        },
    }


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")
    if action in ("status", "json"):
        return {"ok": True, **kilroy_status()}
    if action in ("amouranthrtx", "rtx", "engine"):
        return {"ok": True, **amouranthrtx_status()}
    if action == "paths":
        fp = _load_field_paths()
        return {"ok": True, **fp.field_status(QUEEN)}
    if action in ("proc_status", "proc"):
        text = _read_proc("/proc/kilroy_field/status")
        return {"ok": bool(text), "status": text or None}
    if action in ("load_os", "load", "boot", "launch"):
        launch_py = _sg_root() / "NewLatest" / "lib" / "field-queen-browser-open.py"
        if not launch_py.is_file():
            launch_py = QUEEN.parent / "lib" / "field-queen-browser-open.py"
        if not launch_py.is_file():
            return {"ok": False, "error": "field-queen-browser-open.py missing"}
        try:
            spec = importlib.util.spec_from_file_location("field_queen_browser_open", launch_py)
            if not spec or not spec.loader:
                return {"ok": False, "error": "load_os_import_failed"}
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "launch_kilroy_stack"):
                out = mod.launch_kilroy_stack()
                return {"ok": bool(out.get("ok")), **out}
            if hasattr(mod, "launch_ammoos_desktop"):
                out = mod.launch_ammoos_desktop()
                return {"ok": bool(out.get("ok")), **out}
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:200]}
        return {"ok": False, "error": "load_os_unavailable"}
    return {"ok": False, "error": "unknown_action", "action": action}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(kilroy_status(), ensure_ascii=False))
        return 0
    if cmd == "amouranthrtx":
        print(json.dumps(amouranthrtx_status(), ensure_ascii=False))
        return 0
    if cmd == "dispatch":
        raw = sys.stdin.read()
        body = json.loads(raw) if raw.strip() else {}
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-kilroy.py [json|amouranthrtx|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())