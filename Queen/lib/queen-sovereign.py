#!/usr/bin/env pythong
"""Queen Sovereign Capsule — self-contained OS for Humans and AI.

Inside Queen: compile, rebuild, test, reboot. Nothing talks in or monitors without IFF inside.
Horizon 7 (Hostess 7) shares the compiler lane with Queen Forge.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUEEN = Path(__file__).resolve().parents[1]
SG = QUEEN.parent.parent
from sg_paths import grok16_root
_LIB = Path(__file__).resolve().parent
CAPSULE = QUEEN / "data" / "queen-sovereign-capsule.json"
STATE = Path(os.environ.get("NEXUS_STATE_DIR", QUEEN / ".nexus-state"))


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _run_json(script: Path, *args: str, body: dict | None = None, timeout: int = 120) -> dict[str, Any]:
    if not script.is_file():
        return {"ok": False, "error": "missing", "path": str(script)}
    cmd = [sys.executable, str(script), *args]
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(body) if body is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(QUEEN),
            env=_env(),
        )
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return {"ok": False, "tail": (proc.stdout or "")[-1500:] + (proc.stderr or "")[-1500:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}


def _env() -> dict[str, str]:
    return {
        **os.environ,
        "SG_ROOT": str(SG),
        "QUEEN_ROOT": str(QUEEN),
        "QUEEN_SOVEREIGN": "1",
        "QUEEN_INTERNAL_ONLY": "1",
        "NEXUS_INSTALL_ROOT": os.environ.get("NEXUS_INSTALL_ROOT", str(QUEEN)),
        "NEXUS_STATE_DIR": str(STATE),
        "GROK16_ROOT": str(grok16_root()),
        "PYTHONG_ROOT": os.environ.get("PYTHONG_ROOT", str(SG / "PythonG")),
        "HOSTESS7_ROOT": os.environ.get("HOSTESS7_ROOT", str(SG / "Hostess7")),
        "KILROY_ROOT": os.environ.get("KILROY_ROOT", str(SG / "KILROY")),
        "AMOURANTHRTX_ROOT": os.environ.get(
            "AMOURANTHRTX_ROOT", str(SG / "NewLatest" / "AMOURANTHRTX")
        ),
    }


def _g16_manifest() -> dict[str, Any]:
    return _load(QUEEN / "data" / "g16-toolchain.json")


def _g16_probe() -> dict[str, Any]:
    doc = _g16_manifest()
    tc = doc.get("toolchain") or {}
    found = doc.get("found") or {}
    g16_root = Path(tc.get("prefix") or tc.get("grok16_root") or _env()["GROK16_ROOT"])
    g16 = Path(found.get("g16") or g16_root / "bin" / "g16")
    gxx = Path(found.get("g++16") or g16_root / "bin" / "g++16")
    target = tc.get("g16_version") or "16.1.1"
    dump = tc.get("dumpversion") or ""
    runtime = doc.get("ready_g16_runtime", g16.is_file())
    version_ok = bool(doc.get("ready_g16")) or dump == target
    mandate = doc.get("field_mandate") or {}
    return {
        "ready": runtime and doc.get("ready_rtx", True),
        "ready_g16": doc.get("ready_g16", version_ok),
        "ready_g16_runtime": runtime,
        "version_ok": version_ok,
        "version_upgrade_pending": doc.get("version_upgrade_pending", dump != target and bool(dump)),
        "profile": tc.get("build_profile") or os.environ.get("QUEEN_GROK16_PROFILE", "field_opt"),
        "g16": str(g16) if g16.is_file() else None,
        "g++16": str(gxx) if gxx.is_file() else None,
        "dumpversion": dump,
        "target_version": target,
        "version": target,
        "field_mandate": mandate.get("id"),
        "inside_queen": (QUEEN / ".queen-inside").is_file(),
        "manifest": str(QUEEN / "data" / "g16-toolchain.json"),
    }


def _pythong_manifest() -> dict[str, Any]:
    return _load(QUEEN / "data" / "pythong-toolchain.json")


def _pythong_probe() -> dict[str, Any]:
    doc = _pythong_manifest()
    tc = doc.get("toolchain") or {}
    pg_root = Path(tc.get("pythong_root") or _env().get("PYTHONG_ROOT", str(SG / "PythonG")))
    driver = Path(tc.get("driver") or pg_root / "bin" / "pythong")
    return {
        "ready": doc.get("ready_runtime", driver.is_file()),
        "ready_pythong": doc.get("ready_pythong", False),
        "bootstrap": doc.get("bootstrap", True),
        "pythong_version": tc.get("pythong_version") or "3.12.8-g1",
        "cpython_version": tc.get("cpython_version"),
        "driver": str(driver) if driver.is_file() else None,
        "profile": tc.get("profile", "field_opt"),
        "hostess_lane": (doc.get("hostess7") or {}).get("lane"),
        "manifest": str(QUEEN / "data" / "pythong-toolchain.json"),
    }


def _compiler_shared() -> dict[str, Any]:
    doc = _g16_manifest()
    tc = doc.get("toolchain") or {}
    probe = _g16_probe()
    return {
        "active": bool(probe.get("ready")) and bool(doc.get("ready_rtx")),
        "prefix": tc.get("prefix"),
        "profile": probe.get("profile"),
        "dumpversion": probe.get("dumpversion"),
        "target_version": probe.get("target_version"),
        "version_ok": probe.get("version_ok"),
        "manifest": probe.get("manifest"),
        "lock_holder": "queen_forge",
        "field_mandate": probe.get("field_mandate"),
    }


def horizon7_status() -> dict[str, Any]:
    cap = _load(CAPSULE)
    h7 = Path(_env()["HOSTESS7_ROOT"])
    stack = _load(h7 / "data" / "hostess7-neural-stack.json")
    lanes = []
    for net in (stack.get("networks") or stack.get("nets") or []):
        if isinstance(net, dict):
            lanes.append(net)
    horizon_lane = None
    for item in stack.get("lanes") or []:
        if isinstance(item, dict) and item.get("lane") == "Horizon":
            horizon_lane = item
    for row in (stack.get("routing") or {}).get("lanes") or []:
        if isinstance(row, dict) and row.get("id") == "world":
            horizon_lane = horizon_lane or {"id": "world", "corpus": row.get("corpus"), "lane": "Horizon"}
    brain = _run_json(_LIB / "queen-hostess-brain.py", "json", timeout=60)
    return {
        "schema": "queen-horizon7/v1",
        "updated": _now(),
        "title": "Horizon 7 — inside Queen with Hostess 7",
        "hostess_root": str(h7),
        "present": h7.is_dir(),
        "lane": cap.get("horizon7", {}).get("lane") or "Horizon",
        "corpus": cap.get("horizon7", {}).get("corpus") or "field_world_corpus",
        "neural_stack": str(h7 / "data" / "hostess7-neural-stack.json"),
        "compiler_shared": _compiler_shared(),
        "g16": _g16_probe(),
        "pythong": _pythong_probe(),
        "hostess_brain": brain if brain.get("ok") is not False else {"live": bool(brain)},
        "horizon_lane": horizon_lane,
        "doctrine": "Horizon geography + people corpus — truth-filtered inside capsule; never external wire",
    }


def monitor_gate() -> dict[str, Any]:
    cap = _load(CAPSULE)
    policy = cap.get("ingress_policy") or {}
    field_net = _run_json(_LIB / "queen-field-net.py", "json", timeout=30)
    gates = _run_json(_LIB / "queen-gate.py", "json", timeout=30)
    return {
        "schema": "queen-monitor-gate/v1",
        "updated": _now(),
        "ingress_policy": policy,
        "internal_only": field_net.get("internal_only", True),
        "external_blocked": policy.get("external_http") == "BLOCK",
        "host_telemetry_blocked": policy.get("host_telemetry") == "BLOCK",
        "queen_verdict": gates.get("queen_verdict"),
        "gates_held": gates.get("gates", {}).get("all_held"),
        "packet_field": field_net.get("packet_field"),
        "note": "Nothing monitors Queen from outside — packet-field IFF tags only inside witnesses",
    }


def capsule_status() -> dict[str, Any]:
    cap = _load(CAPSULE)
    seal = _run_json(_LIB / "queen-secure-space.py", "json", timeout=45)
    forge = _run_json(_LIB / "queen-build.py", "json", timeout=45)
    field_net = _run_json(_LIB / "queen-field-net.py", "json", timeout=30)
    kilroy = _run_json(_LIB / "queen-kilroy.py", "json", timeout=45)
    rtx = Path(_env()["AMOURANTHRTX_ROOT"])
    bin_qb = rtx / "build" / "bin" / "Linux" / "queen-browser"
    if not bin_qb.is_file():
        bin_qb = QUEEN / "build" / "rtx" / "bin" / "Linux" / "queen-browser"
    layers = cap.get("layers") or []
    layer_ok = {
        "seal": bool(seal.get("sealed")),
        "gates": (field_net.get("internal_only") is True),
        "fieldnet": field_net.get("schema") == "queen-field-net/v1",
        "forge": forge.get("all_core_ready") or forge.get("core_ready", 0) > 0,
        "compiler": _g16_probe().get("ready") and _g16_probe().get("ready_g16_runtime"),
        "g16_version": _g16_probe().get("version_ok"),
        "runtime": _pythong_probe().get("ready"),
        "pythong": _pythong_probe().get("ready"),
        "horizon7": Path(_env()["HOSTESS7_ROOT"]).is_dir(),
        "test": (QUEEN / "tests" / "test_queen_browser.py").is_file(),
        "reboot": (QUEEN / "data" / "ammoos-boot-map.json").is_file(),
    }
    held = sum(1 for lid in layer_ok if layer_ok.get(lid))
    return {
        "schema": "queen-sovereign-capsule/v1",
        "updated": _now(),
        "title": cap.get("title"),
        "motto": cap.get("motto"),
        "doctrine": cap.get("doctrine"),
        "capsule_sealed": seal.get("sealed") and field_net.get("internal_only"),
        "never_leave": True,
        "operator_surface": cap.get("operator_entry", {}).get("surface"),
        "layers": layers,
        "layer_status": layer_ok,
        "layers_ready": f"{held}/{len(layer_ok)}",
        "compiler_lane": {**cap.get("compiler_lane", {}), "live": _g16_probe()},
        "runtime_lane": {**cap.get("runtime_lane", {}), "live": _pythong_probe()},
        "horizon7": horizon7_status(),
        "monitor_gate": monitor_gate(),
        "seal": seal,
        "forge": {
            "inside": forge.get("inside"),
            "core_ready": forge.get("core_ready"),
            "core_total": forge.get("core_total"),
            "binary_ready": forge.get("binary_ready"),
        },
        "rtx_binary": str(bin_qb) if bin_qb.is_file() else None,
        "kilroy_present": kilroy.get("kilroy_present"),
        "actions": ["rebuild", "test", "reboot", "compile", "seal", "horizon7"],
    }


def _spawn(cmd: list[str], *, log_name: str, timeout: int = 7200) -> dict[str, Any]:
    log = QUEEN / f".queen-{log_name}.log"
    try:
        with open(log, "a", encoding="utf-8") as fh:
            subprocess.Popen(
                cmd,
                cwd=str(QUEEN),
                env=_env(),
                stdout=fh,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        return {"ok": True, "started": True, "log": str(log), "cmd": " ".join(cmd)}
    except OSError as e:
        return {"ok": False, "error": "spawn_failed", "detail": str(e)}


def dispatch(body: dict[str, Any]) -> dict[str, Any]:
    action = str(body.get("action") or "status").strip().lower().replace("-", "_")

    if action in ("status", "json", "capsule"):
        return {"ok": True, **capsule_status()}

    if action in ("horizon7", "horizon", "hostess_horizon"):
        return {"ok": True, **horizon7_status()}

    if action in ("monitor", "monitor_gate", "gate"):
        return {"ok": True, **monitor_gate()}

    if action in ("compile", "compiler", "g16_probe"):
        probe_out = _run_json(_LIB / "queen-forge.py", "run", "compiler_probe", timeout=300)
        return {
            "ok": True,
            "compiler": _g16_probe(),
            "compiler_shared": _compiler_shared(),
            "probe": probe_out,
            "forge": _run_json(_LIB / "queen-forge.py", "json"),
        }

    if action in ("seal", "re_seal", "secure"):
        out = _run_json(_LIB / "queen-secure-space.py", "boot", timeout=90)
        return {"ok": True, "action": "seal", "seal": out, "capsule": capsule_status()}

    if action in ("reboot", "boot", "refresh"):
        seal = _run_json(_LIB / "queen-secure-space.py", "boot", timeout=90)
        boot = _load(QUEEN / "data" / "ammoos-boot-map.json")
        return {
            "ok": True,
            "action": "reboot",
            "seal": seal,
            "boot_map": boot.get("schema"),
            "phases": len(boot.get("phases") or []),
            "message": "Capsule reboot — seal refreshed, AmmoOS boot map live",
        }

    if action in ("rebuild", "build", "forge_rebuild"):
        target = str(body.get("target") or body.get("tool") or "rtx").strip()
        if body.get("background"):
            return _spawn(
                [sys.executable, str(_LIB / "queen-forge.py"), "run", target],
                log_name=f"rebuild-{target}",
            )
        out = _run_json(_LIB / "queen-build.py", "dispatch", body={"action": "run", "stage": target}, timeout=7200)
        return {"ok": out.get("ok", True), "action": "rebuild", "target": target, **out}

    if action in ("rebuild_all", "build_all"):
        if body.get("background"):
            return _spawn([sys.executable, str(_LIB / "queen-forge.py"), "run-all"], log_name="rebuild-all")
        out = _run_json(_LIB / "queen-build.py", "dispatch", body={"action": "run-all"}, timeout=7200)
        return {"ok": out.get("ok", True), "action": "rebuild_all", **out}

    if action in ("rebuild_pythong", "pythong", "pythong_rebuild"):
        if body.get("background"):
            return _spawn(
                [sys.executable, str(_LIB / "queen-forge.py"), "run", "pythong_rebuild"],
                log_name="pythong-rebuild",
            )
        out = _run_json(_LIB / "queen-forge.py", "run", "pythong_rebuild", timeout=14400)
        probe = _run_json(_LIB / "queen-forge.py", "run", "pythong_probe", timeout=300)
        return {
            "ok": out.get("ok", True),
            "action": "rebuild_pythong",
            "probe": probe,
            "pythong": _pythong_probe(),
            **out,
        }

    if action in ("pythong_probe", "runtime_probe"):
        probe = _run_json(_LIB / "queen-forge.py", "run", "pythong_probe", timeout=300)
        return {"ok": True, "action": "pythong_probe", "probe": probe, "pythong": _pythong_probe()}

    if action in ("rebuild_g16", "g16", "toolchain"):
        if body.get("background"):
            return _spawn(
                [sys.executable, str(_LIB / "queen-forge.py"), "run", "g16_toolchain"],
                log_name="g16-toolchain",
            )
        out = _run_json(_LIB / "queen-forge.py", "run", "g16_toolchain", timeout=7200)
        probe = _run_json(_LIB / "queen-forge.py", "run", "compiler_probe", timeout=300)
        return {
            "ok": out.get("ok", True),
            "action": "rebuild_g16",
            "probe": probe,
            "compiler": _g16_probe(),
            **out,
        }

    if action in ("rebuild_chips", "chips", "nes_qa"):
        rtx = Path(_env()["AMOURANTHRTX_ROOT"])
        script = rtx / "linux.sh"
        if body.get("background"):
            return _spawn(["bash", str(script), "nes-qa"], log_name="nes-qa")
        proc = subprocess.run(
            ["bash", str(script), "nes-qa"],
            cwd=str(rtx),
            capture_output=True,
            text=True,
            timeout=900,
            env=_env(),
        )
        return {
            "ok": proc.returncode == 0,
            "action": "rebuild_chips",
            "rc": proc.returncode,
            "tail": (proc.stdout or "")[-2000:] + (proc.stderr or "")[-2000:],
        }

    if action in ("test", "test_all", "forge_test"):
        out = _run_json(_LIB / "queen-build.py", "dispatch", body={"action": "forge-test"}, timeout=600)
        browser_test = QUEEN / "tests" / "test_queen_browser.py"
        bt: dict[str, Any] = {"skipped": True}
        if browser_test.is_file() and body.get("include_browser", True):
            proc = subprocess.run(
                [sys.executable, str(browser_test)],
                cwd=str(QUEEN),
                capture_output=True,
                text=True,
                timeout=180,
                env=_env(),
            )
            bt = {"ok": proc.returncode == 0, "rc": proc.returncode, "tail": (proc.stdout or "")[-1500:]}
        return {
            "ok": out.get("ok", False) and bt.get("ok", True),
            "action": "test",
            "forge_test": out,
            "browser_test": bt,
        }

    if action == "field_package":
        out = _run_json(_LIB / "queen-build.py", "dispatch", body={"action": "field"}, timeout=14400)
        return {"ok": out.get("ok", True), "action": "field_package", **out}

    return {
        "ok": False,
        "error": "unknown_action",
        "actions": [
            "status", "horizon7", "monitor_gate", "compile", "seal", "reboot",
            "rebuild", "rebuild_all", "rebuild_g16", "rebuild_pythong", "pythong_probe",
            "rebuild_chips", "test", "field_package",
        ],
    }


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "dispatch":
        try:
            body = json.loads(sys.stdin.read() or "{}")
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "bad_json"}))
            return 1
        print(json.dumps(dispatch(body), ensure_ascii=False))
        return 0
    if len(sys.argv) > 1 and sys.argv[1] == "horizon7":
        print(json.dumps(horizon7_status(), ensure_ascii=False))
        return 0
    print(json.dumps(capsule_status(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())