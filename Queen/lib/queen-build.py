#!/usr/bin/env pythong
"""Queen build orchestrator — delegates to Queen Forge (all tools native inside)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
_LIB = Path(__file__).resolve().parent
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from forge.engine import ForgeContext  # noqa: E402
from forge.tools import TOOL_REGISTRY  # noqa: E402

FORGE = _LIB / "queen-forge.py"
INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", QUEEN))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_brain_manifest() -> dict[str, Any]:
    path = QUEEN / "data" / "queen-brain-manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _hostess_brain_ops() -> dict[str, Any]:
    brain = _load_brain_manifest()
    ops = dict(brain.get("hostess7_brain_ops") or {})
    bridge = QUEEN / "lib" / "queen-hostess-brain.py"
    if bridge.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(bridge), "json"],
                cwd=str(QUEEN),
                capture_output=True,
                text=True,
                timeout=45,
            )
            if proc.returncode == 0:
                ops["live_status"] = json.loads(proc.stdout)
        except (json.JSONDecodeError, subprocess.TimeoutExpired):
            pass
    return ops


def _field_technology() -> dict[str, Any]:
    return _load_brain_manifest().get("field_technology") or {}


def _forge_json() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(FORGE), "json"],
        cwd=str(QUEEN),
        capture_output=True,
        text=True,
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
    )
    if proc.returncode != 0:
        return {"schema": "queen-build/v1", "error": "forge_unavailable", "stderr": proc.stderr[-500:]}
    return json.loads(proc.stdout)


def _forge_run(tool_id: str) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(FORGE), "run", tool_id],
        cwd=str(QUEEN),
        capture_output=True,
        text=True,
        timeout=7200,
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "tool": tool_id, "tail": (proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:]}


def _forge_run_all() -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, str(FORGE), "run-all"],
        cwd=str(QUEEN),
        capture_output=True,
        text=True,
        timeout=7200,
        env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-4000:]}


def build_status() -> dict[str, Any]:
    forge = _forge_json()
    forge_tools = {t["id"]: t for t in forge.get("tools", [])}
    stages = []
    for tid, t in TOOL_REGISTRY.items():
        if t.kind != "core":
            continue
        row = forge_tools.get(tid)
        stages.append({
            "id": tid,
            "label": t.label,
            "track": t.track,
            "ready": row["ready"] if row else t.check(ForgeContext.from_env()),
            "forge": "lib/queen-forge.py",
            "replaces": t.replaces,
            "optional": t.optional,
        })
    core = [s for s in stages if s["track"] == "core"]
    core_ready = sum(1 for s in core if s.get("ready"))
    field_tools: dict[str, Any] = {}
    ft_script = _LIB / "queen-field-tools.py"
    if ft_script.is_file():
        try:
            proc = subprocess.run(
                [sys.executable, str(ft_script), "json"],
                cwd=str(QUEEN),
                capture_output=True,
                text=True,
                timeout=45,
            )
            if proc.returncode == 0:
                field_tools = json.loads(proc.stdout)
        except (json.JSONDecodeError, subprocess.TimeoutExpired):
            pass
    return {
        "schema": "queen-build/v1",
        "updated": _now(),
        "queen_root": str(QUEEN),
        "install_root": str(INSTALL),
        "inside": forge.get("inside", False),
        "forge": "lib/queen-forge.py",
        "forge_schema": forge.get("schema"),
        "brain": forge.get("brain"),
        "brain_stack": forge.get("brain_stack", {}),
        "hostess7_sdf_storage": forge.get("hostess7_sdf_storage", {}),
        "hostess7_brain_ops": _hostess_brain_ops(),
        "field_technology": _field_technology(),
        "motto": forge.get("motto"),
        "core_ready": core_ready,
        "core_total": len(core),
        "all_core_ready": forge.get("all_core_ready", False),
        "binary": forge.get("binary"),
        "binary_ready": forge.get("binary_ready", False),
        "gui": {
            "theme": "gui/queen-theme-2026.json",
            "build_deck": "gui/queen-build-deck.html",
            "boot_surface": "/world/browser.html",
        },
        "stages": stages,
        "forge_status": forge,
        "field_tools": field_tools,
        "field_tools_api": "/api/field-tools",
    }


def run_stage(stage_id: str) -> dict[str, Any]:
    if stage_id not in TOOL_REGISTRY:
        return {"ok": False, "error": "unknown_stage", "stage": stage_id}
    out = _forge_run(stage_id)
    out["stage"] = stage_id
    out["status"] = build_status()
    return out


def run_all_core() -> dict[str, Any]:
    out = _forge_run_all()
    out["status"] = build_status()
    return out


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower()
    if action in ("status", "json"):
        return build_status()
    if action in ("run", "build"):
        return run_stage(str(body.get("stage") or body.get("tool") or "rtx"))
    if action in ("run-all", "run_all", "build-all", "build_all"):
        return run_all_core()
    if action in ("run-field", "run_field", "field", "sovereign-field"):
        proc = subprocess.run(
            [sys.executable, str(_LIB / "queen-forge.py"), "field"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=14400,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
        )
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            out = {"ok": False, "tail": (proc.stdout or "")[-4000:]}
        out["status"] = build_status()
        return out
    if action == "log":
        proc = subprocess.run(
            [sys.executable, str(FORGE), "log"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": True, "log": ""}
    if action == "forge":
        return _forge_json()
    if action in ("field-tools", "field_tools", "field-tools-probe"):
        bridge = _LIB / "queen-field-tools.py"
        sub = "probe" if "probe" in action else "json"
        proc = subprocess.run(
            [sys.executable, str(bridge), sub],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=120,
        )
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"ok": False, "tail": (proc.stdout or "")[-2000:]}
    if action in ("hostess-teach", "hostess_teach", "queen-teach-redata"):
        bridge = _LIB / "queen-hostess-brain.py"
        proc = subprocess.run(
            [sys.executable, str(bridge), "teach"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=180,
        )
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            out = {"ok": False, "tail": (proc.stdout or "")[-2000:]}
        out["status"] = build_status()
        return out
    if action in ("forge-test", "forge_test", "test-all"):
        proc = subprocess.run(
            [sys.executable, str(FORGE), "forge-test"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "SG_ROOT": str(QUEEN.parent.parent)},
        )
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            report = QUEEN / "data" / "forge-test-report.json"
            if report.is_file():
                try:
                    doc = json.loads(report.read_text(encoding="utf-8"))
                    out = {"ok": doc.get("ok", False), "report": doc, "report_path": str(report)}
                except (OSError, json.JSONDecodeError):
                    out = {"ok": False, "tail": (proc.stdout or "")[-2000:]}
            else:
                out = {"ok": False, "tail": (proc.stdout or "")[-2000:]}
        out["status"] = build_status()
        return out
    if action in ("run-hostess", "hostess-pipeline"):
        proc = subprocess.run(
            [sys.executable, str(FORGE), "run-hostess"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=900,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "SG_ROOT": str(QUEEN.parent.parent)},
        )
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            out = {"ok": False}
        out["status"] = build_status()
        return out
    if action in ("verify-redata", "sdf-verify-redata"):
        bridge = _LIB / "queen-hostess-brain.py"
        proc = subprocess.run(
            [sys.executable, str(bridge), "dispatch"],
            input=json.dumps({"action": "verify-redata"}),
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=120,
        )
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            out = {"ok": False}
        out["status"] = build_status()
        return out
    if action in ("zocr", "queen-zocr", "browser-smoke", "zocr-smoke"):
        zocr = _LIB / "queen-zocr.py"
        proc = subprocess.run(
            [sys.executable, str(zocr), "browser-smoke"],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=120,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "SG_ROOT": str(QUEEN.parent.parent),
                "FINAL_EYE_ROOT": os.environ.get("FINAL_EYE_ROOT", str(QUEEN.parent.parent / "Final_Eye")),
            },
        )
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            out = {"ok": False, "tail": (proc.stdout or "")[-2000:]}
        out["status"] = build_status()
        return out

    def _eyeball_cmd(*args: str, timeout: int = 180) -> dict[str, Any]:
        bridge = _LIB / "queen-eyeball.py"
        proc = subprocess.run(
            [sys.executable, str(bridge), *args],
            cwd=str(QUEEN),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={
                **os.environ,
                "NEXUS_INSTALL_ROOT": str(INSTALL),
                "SG_ROOT": str(QUEEN.parent.parent),
                "FINAL_EYE_ROOT": os.environ.get("FINAL_EYE_ROOT", str(QUEEN.parent.parent / "Final_Eye")),
            },
        )
        try:
            out = json.loads(proc.stdout)
        except json.JSONDecodeError:
            out = {"ok": False, "tail": (proc.stdout or "")[-2000:]}
        out["status"] = build_status()
        return out

    if action in ("eyeball", "eyeball-status", "final-eye"):
        return _eyeball_cmd("json", timeout=60)
    if action in ("eyeball-verify", "verify-eyeball"):
        return _eyeball_cmd("verify")
    if action in ("eyeball-arm", "arm-dishes"):
        mode = str(body.get("mode") or "dishes")
        return _eyeball_cmd("arm", mode, timeout=60)
    if action in ("eyeball-weaponize", "weaponize-eyeball"):
        mode = str(body.get("mode") or "war")
        return _eyeball_cmd("weaponize", mode, timeout=90)
    if action in ("eyeball-bench", "bench-low-end"):
        return _eyeball_cmd("bench")
    return {"ok": False, "error": "unknown_action"}


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip()
    if cmd == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}, ensure_ascii=False))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if cmd == "json":
        print(json.dumps(build_status(), ensure_ascii=False))
        return 0
    if cmd == "run" and len(sys.argv) >= 3:
        print(json.dumps(run_stage(sys.argv[2]), ensure_ascii=False))
        return 0
    if cmd == "run-all":
        print(json.dumps(run_all_core(), ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: queen-build.py [json|run STAGE|run-all|dispatch]"}, ensure_ascii=False))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())