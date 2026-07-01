#!/usr/bin/env pythong
"""Plate meld — uninterruptable fused state across all plates.

flock + fsync + chain-hash + triple mirror. Plates always share actual
generation-linked truth; copilot/bus read meld first.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-plate-meld-doctrine.json"
MELD = STATE / "field-plate-meld.json"
MELD_RUNTIME = STATE / "field-plate-meld-runtime.json"
LEDGER = STATE / "field-plate-meld-ledger.jsonl"
LOCK = STATE / "field-plate-meld.lock"
REDUNDANT = STATE / "plate-meld-redundant"

PLATE_SOURCES: tuple[tuple[str, str], ...] = (
    ("iron_plate", "field-operator-iron-plate.json"),
    ("plate_runtime", "field-operator-plate-runtime.json"),
    ("field_plate", "field-plate-field-runtime.json"),
    ("unified_bus", "field-unified-bus-runtime.json"),
    ("sense_package", "field-sense-package-panel.json"),
    ("kernel", "field-kernel-meld-panel.json"),
    ("firmware", "field-firmware-threat-panel.json"),
    ("port_ddos", "field-port-ddos-panel.json"),
    ("deinterlace", "field-packet-deinterlace-panel.json"),
    ("sovereign_sync", "sovereign-sync-manifest.json"),
    ("packet_field", "packet-field.json"),
    ("gatekeeper", "connection-intent.json"),
    ("znetwork", "znetwork-status.json"),
    ("spatial_field", "field-spatial-panel.json"),
    ("logic_gate", "nexus-logic-gate-runtime.json"),
    ("universal_protector", "universal-protector-panel.json"),
    ("humanoid_motion", "humanoid-motion-panel.json"),
    ("iron_plate_motion", "iron-plate-motion-resolve-panel.json"),
    ("iron_plate_organize", "iron-plate-organize-panel.json"),
    ("iron_plate_spot", "iron-plate-spot-panel.json"),
    ("creatable_lives", "creatable-lives-panel.json"),
    ("right_to_exist", "right-to-exist-panel.json"),
    ("hostess7_brain", "hostess7-brain-guard-panel.json"),
    ("ironclad", "ironclad-plate.json"),
    ("ironclad_reality_field", "ironclad-reality-field-panel.json"),
    ("ironclad_field_sanity", "ironclad-field-sanity-panel.json"),
    ("eye_ear_plate", "eye-ear-plate.json"),
    ("plate_compiler", "plate-compiler-panel.json"),
    ("g16_stack", "nexus-g16-stack-panel.json"),
    ("g16_compiler_sense", "g16-compiler-sense-plate.json"),
    ("plate_test_runner", "field-plate-test-runner.json"),
    ("g1id_baselines", "g1id-baseline-panel.json"),
    ("field_io_packet", "field-io-packet-panel.json"),
    ("truth_blocks", "g16-truth-blocks-panel.json"),
    ("field_combinatorics", "g16-field-combinatorics-panel.json"),
    ("combinatorics_bridge", "field-plate-combinatorics-bridge.json"),
    ("ironclad_chips", "field-ironclad-chips-combinatorics-panel.json"),
    ("chips_plate_stack", "field-chips-plate-stack-panel.json"),
    ("chips_core", "field-chips-core-panel.json"),
    ("program_combinatronic", "field-program-combinatronic-panel.json"),
    ("g16_universal", "field-g16-universal-combinatronic-panel.json"),
    ("cpu_library", "field-cpu-library-panel.json"),
    ("field_font", "field-font-panel.json"),
    ("g16_power_sort", "g16-power-sort-plate.json"),
    ("file_formats", "field-file-formats-panel.json"),
    ("field_best_sort", "field-best-sort-panel.json"),
    ("physics_witness", "field-physics-witness.json"),
    ("locational_sitrep", "field-locational-sitrep-plate.json"),
    ("c2_taskbar", "field-c2-taskbar-panel.json"),
    ("shell_dock", "field-shell-dock-panel.json"),
    ("field_popcorn", "field-popcorn-panel.json"),
    ("field_ellie_fier", "field-ellie-fier-panel.json"),
    ("field_g16_launch", "field-g16-launch-panel.json"),
    ("field_gpu", "field-gpu-control-panel.json"),
    ("field_audio", "field-audio-settings-panel.json"),
    ("field_storage", "field-storage-panel.json"),
    ("field_display", "field-display-settings-panel.json"),
    ("ammoos_blocks", "field-ammoos-blocks-panel.json"),
    ("thermal_manager_block", "field-thermal-manager-block-panel.json"),
    ("rtx_canvas_block", "field-rtx-canvas-block-panel.json"),
    ("final_ear_block", "field-final-ear-block-panel.json"),
    ("final_mouth_block", "field-final-mouth-block-panel.json"),
    ("field_broadcaster", "field-broadcaster-panel.json"),
    ("field_lock", "field-keepass-panel.json"),
    ("field_host_desktop", "field-host-desktop.json"),
    ("sovereign_stack", "field-sovereign-stack-meld-panel.json"),
    ("code_bugfinder", "field-code-bugfinder-panel.json"),
)

_GEN = 0
_LAST_CHAIN = ""


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



def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _fsync_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def _append_ledger(row: dict[str, Any]) -> None:
    line = json.dumps(row, ensure_ascii=False) + "\n"
    with LEDGER.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass


def _mirror_meld(doc: dict[str, Any]) -> None:
    REDUNDANT.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    for name in ("field-plate-meld.json", "field-plate-meld-runtime.json"):
        for suffix in ("", ".bak"):
            target = REDUNDANT / f"{name}{suffix}"
            target.write_text(payload, encoding="utf-8")


def _collect_plates() -> dict[str, Any]:
    plates: dict[str, Any] = {}
    for key, fname in PLATE_SOURCES:
        path = STATE / fname
        if path.is_file():
            plates[key] = _load(path, {})
        else:
            plates[key] = {"missing": True, "path": str(path)}
    return plates


def _digest(plates: dict[str, Any], prev_chain: str) -> str:
    material = json.dumps(plates, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(f"{prev_chain}|{material}".encode()).hexdigest()


def _meld_lock() -> int:
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    stale_sec = int(os.environ.get("NEXUS_PLATE_MELD_LOCK_STALE_SEC", "300") or "300")
    if LOCK.is_file() and stale_sec > 0:
        try:
            if time.time() - LOCK.stat().st_mtime > stale_sec:
                LOCK.unlink(missing_ok=True)
        except OSError:
            pass
    fd = os.open(str(LOCK), os.O_CREAT | os.O_RDWR, 0o644)
    deadline = time.time() + min(30, max(5, stale_sec // 10))
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            if time.time() >= deadline:
                try:
                    LOCK.unlink(missing_ok=True)
                except OSError:
                    pass
                fcntl.flock(fd, fcntl.LOCK_EX)
                return fd
            time.sleep(0.25)


def _meld_unlock(fd: int) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    except OSError:
        pass


def _import_call(script: Path, mod_name: str, fn: str, *args: Any, **kwargs: Any) -> Any:
    if not script.is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(mod_name, script)
        if not spec or not spec.loader:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        call = getattr(mod, fn, None)
        if not callable(call):
            return None
        return call(*args, **kwargs)
    except Exception:
        return None


def _iron_plate_fresh(max_age: int) -> bool:
    if max_age <= 0:
        return False
    for fname in ("field-operator-iron-plate.json", "field-operator-plate-runtime.json"):
        path = STATE / fname
        if not path.is_file():
            continue
        try:
            age = time.time() - path.stat().st_mtime
            if age >= max_age:
                continue
            cached = _load(path, {})
            if int(cached.get("connection_count") or 0) > 0:
                return True
            if len(cached.get("route_words") or []) > 0:
                return True
        except OSError:
            continue
    return False


_DIAG_MOD: Any = None
_PREDICTIVE_MELD_MOD: Any = False


def _predictive_meld_mod() -> Any:
    global _PREDICTIVE_MELD_MOD
    if _PREDICTIVE_MELD_MOD is not False:
        return _PREDICTIVE_MELD_MOD or None
    try:
        import importlib.util

        py = INSTALL / "lib" / "field-predictive-meld.py"
        if not py.is_file():
            _PREDICTIVE_MELD_MOD = None
            return None
        spec = importlib.util.spec_from_file_location("field_predictive_meld", py)
        if not spec or not spec.loader:
            _PREDICTIVE_MELD_MOD = None
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _PREDICTIVE_MELD_MOD = mod
    except Exception:
        _PREDICTIVE_MELD_MOD = None
    return _PREDICTIVE_MELD_MOD


def _predictive_skip_refresh(*, force: bool = False) -> dict[str, Any]:
    mod = _predictive_meld_mod()
    if mod and hasattr(mod, "predictive_meld"):
        return mod.predictive_meld(force=force)
    return {"skip_refresh": False}


_DIAG_MOD: Any = None


def _diagnostic_mod() -> Any:
    global _DIAG_MOD
    if _DIAG_MOD is not None:
        return _DIAG_MOD
    try:
        import importlib.util

        py = INSTALL / "lib" / "field-diagnostic-mode.py"
        if not py.is_file():
            _DIAG_MOD = False
            return _DIAG_MOD
        spec = importlib.util.spec_from_file_location("field_diagnostic_mode", py)
        if not spec or not spec.loader:
            _DIAG_MOD = False
            return _DIAG_MOD
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _DIAG_MOD = mod
    except Exception:
        _DIAG_MOD = False
    return _DIAG_MOD


def _diagnostic_active() -> bool:
    mod = _diagnostic_mod()
    return bool(mod and hasattr(mod, "active") and mod.active())


def _refresh_if_allowed(refresh_id: str, fn: Any) -> None:
    mod = _diagnostic_mod()
    if mod and hasattr(mod, "active") and mod.active() and hasattr(mod, "refresh_allowed"):
        if not mod.refresh_allowed(refresh_id):
            return
    fn()


def _refresh_iron_plate() -> None:
    if os.environ.get("NEXUS_IRON_PLATE_MELD_REFRESH", "1") != "1":
        return
    max_age = int(os.environ.get("NEXUS_IRON_PLATE_MELD_MAX_AGE_SEC", "60") or "60")
    if _iron_plate_fresh(max_age):
        return
    fast: dict[str, Any] | None = None
    scan_cache = STATE / "field-operator-scan-cache.json"
    if scan_cache.is_file():
        cached = _load(scan_cache, {})
        if cached.get("profiles"):
            fast = cached
    _import_call(
        INSTALL / "lib" / "field-operator.py",
        "field_operator",
        "build_iron_plate",
        fast=fast,
    )


def _refresh_gatekeeper() -> None:
    if os.environ.get("NEXUS_CONNECTION_GATEKEEPER", "1") != "1":
        return
    if os.environ.get("NEXUS_NETWORK_STACK_MELD", "1") != "1":
        return
    py = INSTALL / "lib" / "connection-gatekeeper.py"
    if not py.is_file():
        return
    try:
        import subprocess
        snap = STATE / "packet.snapshot"
        if snap.is_file() and snap.stat().st_size > 0:
            with snap.open("r", encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        else:
            proc = subprocess.run(
                ["ss", "-H", "-tunap"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = proc.stdout.splitlines()
        if not lines:
            return
        env = os.environ.copy()
        env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
        env["NEXUS_STATE_DIR"] = str(STATE)
        proc = subprocess.run(
            [sys.executable, str(py), "--stdin"],
            input="\n".join(lines) + "\n",
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        if proc.returncode != 0 or not (proc.stdout or "").strip():
            return
        payload = proc.stdout if proc.stdout.endswith("\n") else proc.stdout + "\n"
        _fsync_write(STATE / "connection-intent.json", payload)
    except Exception:
        pass


def _refresh_logic_gate() -> None:
    if os.environ.get("NEXUS_LOGIC_GATE", "1") != "1":
        return
    if os.environ.get("NEXUS_NETWORK_STACK_MELD", "1") != "1":
        return
    doc = _import_call(INSTALL / "lib" / "nexus-logic-gate.py", "nexus_logic_gate", "status_json")
    if isinstance(doc, dict) and doc.get("schema"):
        _fsync_write(
            STATE / "nexus-logic-gate-runtime.json",
            json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
        )


def _refresh_port_ddos() -> None:
    if os.environ.get("NEXUS_NETWORK_STACK_MELD", "1") != "1":
        return
    _import_call(
        INSTALL / "lib" / "field-port-ddos-shield.py",
        "field_port_ddos",
        "build_panel",
        enforce=os.environ.get("NEXUS_PORT_DDOS_ENFORCE", "1") == "1",
    )


def _refresh_packet_deinterlace() -> None:
    if os.environ.get("NEXUS_NETWORK_STACK_MELD", "1") != "1":
        return
    _import_call(INSTALL / "lib" / "field-packet-deinterlace.py", "field_packet_deinterlace", "build_panel")


def _znetwork_relayer_active() -> bool:
    marker = STATE / "znetwork-relayer.json"
    if not marker.is_file():
        return False
    try:
        doc = json.loads(marker.read_text(encoding="utf-8"))
        return bool(doc.get("active"))
    except (OSError, json.JSONDecodeError):
        return False


def _refresh_znetwork_status() -> None:
    if os.environ.get("NEXUS_ZNETWORK", "1") != "1":
        return
    if os.environ.get("NEXUS_NETWORK_STACK_MELD", "1") != "1":
        return
    out = STATE / "znetwork-status.json"
    relayer_mode = (
        os.environ.get("ZNETWORK_RELAYER", "1") != "0"
        and os.environ.get("ZNETWORK_UNDERHOOK", "0") != "1"
    )
    if relayer_mode and _znetwork_relayer_active():
        if out.is_file() and out.stat().st_size > 32:
            return
        relayer = INSTALL / "lib" / "znetwork-relayer.py"
        sh = INSTALL / "lib" / "znetwork-field.sh"
        try:
            import subprocess

            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
            env["NEXUS_STATE_DIR"] = str(STATE)
            env["ZNETWORK_PUBLISH_QUIET"] = "1"
            if sh.is_file():
                subprocess.run(
                    ["bash", "-c", f'source "{INSTALL}/lib/nexus-common.sh" && source "{sh}" && nexus_znetwork_publish_quiet'],
                    timeout=20,
                    env=env,
                    capture_output=True,
                    text=True,
                )
            elif relayer.is_file():
                subprocess.run(
                    [sys.executable, str(relayer), "posture"],
                    timeout=15,
                    env=env,
                    capture_output=True,
                    text=True,
                )
            if out.is_file() and out.stat().st_size > 32:
                return
        except Exception:
            pass
        return
    if out.is_file() and out.stat().st_size > 32:
        return
    orch = INSTALL / "lib" / "znetwork-orchestrator.py"
    if orch.is_file():
        try:
            import subprocess

            env = os.environ.copy()
            env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
            env["NEXUS_STATE_DIR"] = str(STATE)
            subprocess.run(
                [sys.executable, str(orch), "triple-check"],
                timeout=45,
                env=env,
                capture_output=True,
                text=True,
            )
            if out.is_file() and out.stat().st_size > 32:
                return
        except Exception:
            pass
    sh = INSTALL / "lib" / "znetwork-field.sh"
    if not sh.is_file():
        return
    try:
        import subprocess

        env = os.environ.copy()
        env["NEXUS_INSTALL_ROOT"] = str(INSTALL)
        env["NEXUS_STATE_DIR"] = str(STATE)
        env["ZNETWORK_PUBLISH_QUIET"] = "1"
        subprocess.run(
            ["bash", "-c", f'source "{INSTALL}/lib/nexus-common.sh" && source "{sh}" && nexus_znetwork_publish'],
            timeout=45,
            env=env,
            capture_output=True,
            text=True,
        )
    except Exception:
        pass


def _net_stack_summary(plates: dict[str, Any]) -> dict[str, Any]:
    iron = plates.get("iron_plate") or {}
    gk = plates.get("gatekeeper") or {}
    logic = plates.get("logic_gate") or {}
    znet = plates.get("znetwork") or {}
    ddos = plates.get("port_ddos") or {}
    deint = plates.get("deinterlace") or {}
    kernel = plates.get("kernel") or {}
    rt = plates.get("plate_runtime") or {}
    net_conns = [
        c for c in (iron.get("connections") or [])
        if str(c.get("bus") or "").lower() == "net"
    ]
    iron_total = int(
        iron.get("connection_count")
        or rt.get("connection_count")
        or len(rt.get("route_words") or [])
        or 0
    )
    return {
        "iron_plate_connections": iron_total,
        "net_iface_count": len(net_conns),
        "route_words": len((plates.get("plate_runtime") or {}).get("route_words") or []),
        "direct_routes": int(
            (iron.get("arithmetic") or {}).get("direct_count")
            or rt.get("direct_count")
            or 0
        ),
        "gatekeeper_connections": int(gk.get("connection_count") or len(gk.get("connections") or [])),
        "gatekeeper_harm_candidates": int(gk.get("harm_candidates") or 0),
        "gatekeeper_updated": bool(gk.get("updated")),
        "logic_gate_high": str(logic.get("threat_warn_level") or "high").lower() == "high",
        "logic_gate_ok": logic.get("ok") is not False and not logic.get("missing"),
        "znetwork_present": not znet.get("missing") and bool(znet),
        "znetwork_mode": znet.get("mode") or os.environ.get("ZNETWORK_MODE", "REVIEW_ONLY"),
        "kernel_meld_live": bool(kernel.get("kilroy_live")),
        "port_ddos_shield": ddos.get("schema") or (None if ddos.get("missing") else "present"),
        "packet_deinterlace": deint.get("schema") or (None if deint.get("missing") else "present"),
        "network_stack_melded": (
            iron_total > 0
            and bool(gk.get("updated") or gk.get("connections"))
            and (logic.get("ok") is not False)
        ),
    }


def _refresh_firmware_threats() -> None:
    py = INSTALL / "lib" / "field-firmware-threat-removal.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_firmware_threat", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.cycle()
    except Exception:
        pass


def _refresh_kernel_meld() -> None:
    py = INSTALL / "lib" / "field-kernel-meld.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_kernel_meld", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.meld(link_plates=True)
    except Exception:
        pass


def _meld_light() -> bool:
    return os.environ.get("NEXUS_PLATE_MELD_LIGHT", "1") == "1"


def _field_plate_fresh(max_age: int) -> bool:
    if max_age <= 0:
        return False
    path = STATE / "field-plate-field-runtime.json"
    if not path.is_file():
        return False
    try:
        age = time.time() - path.stat().st_mtime
        if age >= max_age:
            return False
        cached = _load(path, {})
        return bool(cached.get("schema")) and (
            cached.get("field_energy") is not None
            or cached.get("dimension_count") is not None
            or cached.get("peak_amplitude") is not None
        )
    except OSError:
        return False


def _refresh_field_plate() -> None:
    max_age = int(os.environ.get("NEXUS_FIELD_PLATE_MELD_MAX_AGE_SEC", "120") or "120")
    if _field_plate_fresh(max_age):
        return
    py = INSTALL / "lib" / "field-panel-field.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_panel_field", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.publish_field()
    except Exception:
        pass


def _refresh_spatial() -> None:
    py = INSTALL / "lib" / "field-spatial-cognition.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_spatial", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_spatial(write=True)
    except Exception:
        pass


def _refresh_hostess7_brain() -> None:
    py = INSTALL / "lib" / "hostess7-brain-guard.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_brain", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_hostess7_programming() -> None:
    py = INSTALL / "lib" / "hostess7-programming.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_programming", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_g16_stack() -> None:
    py = INSTALL / "lib" / "nexus-g16-bridge.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("nexus_g16_bridge", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_g16_compiler_sense() -> None:
    if os.environ.get("NEXUS_G16_COMPILER_SENSE", "1") != "1":
        return
    _import_call(
        INSTALL / "lib" / "g16-compiler-sense-plate.py",
        "g16_compiler_sense",
        "cycle",
    )


def _refresh_physics_witness() -> None:
    _import_call(INSTALL / "lib" / "field-physics-witness.py", "field_physics_witness", "publish")


def _refresh_locational_sitrep() -> None:
    if os.environ.get("NEXUS_LOCATIONAL_SITREP", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-locational-sitrep-plate.py", "locational_sitrep", "cycle")


def _refresh_g16_power_sort() -> None:
    if os.environ.get("G16_POWER_SORT", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    sg = Path(os.environ.get("GROK16_ROOT", str(INSTALL.parent.parent / "Grok16")))
    plate_py = sg / "lib" / "g16-power-sort-plate.py"
    if not plate_py.is_file():
        plate_py = INSTALL.parent.parent / "Grok16" / "lib" / "g16-power-sort-plate.py"
    _import_call(plate_py, "g16_power_sort_plate", "cycle")


def _refresh_truth_blocks() -> None:
    if os.environ.get("NEXUS_TRUTH_BLOCKS", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    sg = Path(os.environ.get("GROK16_ROOT", str(INSTALL.parent.parent / "Grok16")))
    tb_py = sg / "lib" / "field_truth_blocks.py"
    if not tb_py.is_file():
        tb_py = INSTALL.parent.parent / "Grok16" / "lib" / "field_truth_blocks.py"
    _import_call(tb_py, "field_truth_blocks", "publish_panel", state_dir=STATE)


def _combinatorics_operator_running() -> bool:
    sg = Path(os.environ.get("GROK16_ROOT", str(INSTALL.parent.parent / "Grok16")))
    comb_py = sg / "lib" / "field_combinatorics.py"
    if not comb_py.is_file():
        comb_py = INSTALL.parent.parent / "Grok16" / "lib" / "field_combinatorics.py"
    if not comb_py.is_file():
        return False
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location("meld_combo_op", comb_py)
        if not spec or not spec.loader:
            return False
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "operator_running"):
            return bool(mod.operator_running(state_dir=STATE).get("running"))
    except Exception:
        pass
    return False


def _refresh_field_combinatorics() -> None:
    if os.environ.get("NEXUS_FIELD_COMBINATORICS", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    if _combinatorics_operator_running():
        return
    sg = Path(os.environ.get("GROK16_ROOT", str(INSTALL.parent.parent / "Grok16")))
    comb_py = sg / "lib" / "field_combinatorics.py"
    if not comb_py.is_file():
        comb_py = INSTALL.parent.parent / "Grok16" / "lib" / "field_combinatorics.py"
    _import_call(comb_py, "field_combinatorics", "publish_panel", state_dir=STATE)


def _refresh_combinatorics_bridge() -> None:
    if os.environ.get("NEXUS_PLATE_COMBINATORICS_BRIDGE", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    if _combinatorics_operator_running():
        return
    _import_call(INSTALL / "lib" / "field-plate-combinatorics-bridge.py", "field_plate_combinatorics_bridge", "build_bridge", write=True)


def _refresh_c2_taskbar() -> None:
    if os.environ.get("NEXUS_C2_TASKBAR_PLATE", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-c2-taskbar-plate.py", "field_c2_taskbar_plate", "posture")


def _refresh_field_host_desktop() -> None:
    if os.environ.get("NEXUS_HOST_DESKTOP_PLATE", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-host-desktop.py", "field_host_desktop", "posture")


def _refresh_field_lock() -> None:
    if os.environ.get("NEXUS_FIELD_LOCK", os.environ.get("NEXUS_FIELD_KEEPASS", "1")).strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-keepass.py", "field_keepass", "posture")


def _refresh_shell_dock() -> None:
    if os.environ.get("NEXUS_FIELD_SHELL_DOCK", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-shell-dock.py", "field_shell_dock", "posture")


def _refresh_field_popcorn() -> None:
    if os.environ.get("NEXUS_FIELD_POPCORN", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-popcorn-player.py", "field_popcorn_player", "posture", rescan=False)


def _refresh_field_ellie_fier() -> None:
    if os.environ.get("NEXUS_FIELD_ELLIE_FIER", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-ellie-fier.py", "field_ellie_fier", "posture", scan=False)


def _refresh_field_g16_launch() -> None:
    if os.environ.get("NEXUS_FIELD_G16_LAUNCH", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-g16-launch.py", "field_g16_launch", "posture", rescan=False)


def _refresh_field_gpu() -> None:
    if os.environ.get("NEXUS_FIELD_GPU", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-gpu-control.py", "field_gpu_control", "posture")


def _refresh_field_audio() -> None:
    if os.environ.get("NEXUS_FIELD_AUDIO", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-audio-settings.py", "field_audio_settings", "posture")


def _refresh_field_storage() -> None:
    if os.environ.get("NEXUS_FIELD_STORAGE", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-storage.py", "field_storage", "scan")


def _refresh_field_display() -> None:
    if os.environ.get("NEXUS_FIELD_DISPLAY", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-display-settings.py", "field_display_settings", "posture")


def _refresh_ammoos_blocks() -> None:
    if os.environ.get("NEXUS_AMMOOS_BLOCKS", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-ammoos-blocks.py", "field_ammoos_blocks", "publish_panel")


def _refresh_sovereign_stack() -> None:
    if os.environ.get("FIELD_SOVEREIGN_STACK_MELD", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-sovereign-stack-meld.py", "field_sovereign_stack_meld", "publish_panel")


def _refresh_thermal_manager_block() -> None:
    if os.environ.get("NEXUS_THERMAL_MANAGER_BLOCK", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-thermal-manager-block.py", "field_thermal_manager_block", "publish_panel")


def _refresh_rtx_canvas_block() -> None:
    if os.environ.get("NEXUS_RTX_CANVAS_BLOCK", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-rtx-canvas-block.py", "field_rtx_canvas_block", "publish_panel")


def _refresh_final_ear_block() -> None:
    if os.environ.get("NEXUS_FINAL_EAR_BLOCK", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-final-ear-block.py", "field_final_ear_block", "publish_panel")


def _refresh_final_mouth_block() -> None:
    if os.environ.get("NEXUS_FINAL_MOUTH_BLOCK", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-final-mouth-block.py", "field_final_mouth_block", "publish_panel")


def _refresh_field_broadcaster() -> None:
    if os.environ.get("NEXUS_FIELD_BROADCASTER", os.environ.get("NEXUS_FIELD_OBS", "1")).strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "field-broadcaster.py", "field_broadcaster", "posture")


def _refresh_code_bugfinder() -> None:
    if os.environ.get("NEXUS_CODE_BUGFINDER", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    if _combinatorics_operator_running():
        return
    _import_call(INSTALL / "lib" / "field-code-bugfinder.py", "field_code_bugfinder", "build_panel")


def _refresh_compatibility_layers() -> None:
    if os.environ.get("NEXUS_COMPATIBILITY_LAYERS", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    if _combinatorics_operator_running():
        return
    _import_call(INSTALL / "lib" / "field-compatibility-layers.py", "field_compatibility_layers", "refresh", deep=False)


def _refresh_g1id_baselines() -> None:
    if os.environ.get("NEXUS_G1ID_BASELINE", "1") != "1":
        return
    _import_call(INSTALL / "lib" / "g1id-baseline.py", "g1id_baseline", "build_panel", write=True)


def _refresh_field_io_packet() -> None:
    if os.environ.get("NEXUS_FIELD_IO_PACKET", "1") != "1":
        return
    _import_call(INSTALL / "lib" / "field-io-packet.py", "field_io_packet", "build_panel", write=True)


def _refresh_plate_tests() -> None:
    if os.environ.get("NEXUS_PLATE_TEST_RUN", "1") != "1":
        return
    py = INSTALL / "lib" / "field-plate-test-runner.py"
    if not py.is_file():
        return
    try:
        import subprocess
        subprocess.run(
            [sys.executable, str(py), "run"],
            capture_output=True,
            text=True,
            timeout=600,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
    except Exception:
        pass


def _refresh_drop_in() -> None:
    py = INSTALL / "lib" / "field-drop-in-orchestrator.py"
    if not py.is_file():
        return
    try:
        import subprocess
        subprocess.run(
            [sys.executable, str(py), "json"],
            capture_output=True,
            text=True,
            timeout=45,
            env={**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)},
            check=False,
        )
    except Exception:
        pass


def _refresh_hostess7_g16() -> None:
    py = INSTALL / "lib" / "hostess7-g16.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_g16", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_hostess7_calculator() -> None:
    py = INSTALL / "lib" / "hostess7-calculator.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_calculator", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_hostess7_biology() -> None:
    py = INSTALL / "lib" / "hostess7-biology.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_biology", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_hostess7_engineering() -> None:
    py = INSTALL / "lib" / "hostess7-engineering.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_engineering", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_hostess7_combat() -> None:
    py = INSTALL / "lib" / "hostess7-combat.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_combat", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_hostess7_mos() -> None:
    py = INSTALL / "lib" / "hostess7-mos.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_mos", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_hostess7_training() -> None:
    py = INSTALL / "lib" / "hostess7-training.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("hostess7_training", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_right_to_exist() -> None:
    py = INSTALL / "lib" / "right-to-exist-mandate.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("right_to_exist", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_creatable_lives() -> None:
    py = INSTALL / "lib" / "creatable-lives-assist.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("creatable_lives", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_iron_plate_motion() -> None:
    py = INSTALL / "lib" / "iron-plate-motion-resolve.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("iron_plate_motion", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.resolve_motion(write=True)
    except Exception:
        pass


def _refresh_iron_plate_organize() -> None:
    if os.environ.get("NEXUS_IRON_PLATE_ORGANIZE", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "iron-plate-organize.py", "iron_plate_organize", "build_panel", write=True)


def _refresh_iron_plate_spot() -> None:
    if os.environ.get("NEXUS_IRON_PLATE_SPOT", "1").strip().lower() in ("0", "false", "no", "off"):
        return
    _import_call(INSTALL / "lib" / "iron-plate-spot-detector.py", "iron_plate_spot", "build_panel", write=True)


def _refresh_humanoid_motion() -> None:
    py = INSTALL / "lib" / "humanoid-motion-training.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("humanoid_motion", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_panel(write=True)
    except Exception:
        pass


def _refresh_ironclad_reality_field() -> None:
    if os.environ.get("NEXUS_IRONCLAD_TRUTH_SERUM", "1") != "1":
        return
    _import_call(
        INSTALL / "lib" / "ironclad-reality-field.py",
        "ironclad_reality_field",
        "cycle",
    )


def _refresh_ironclad_field_sanity() -> None:
    if os.environ.get("NEXUS_IRONCLAD_FIELD_SANITY", "1") != "1":
        return
    _import_call(
        INSTALL / "lib" / "ironclad-field-sanity.py",
        "ironclad_field_sanity",
        "cycle",
    )


def _refresh_eye_ear_plate() -> None:
    if os.environ.get("NEXUS_EYE_EAR_PLATE", "1") != "1":
        return
    _import_call(
        INSTALL / "lib" / "eye-ear-plate.py",
        "eye_ear_plate",
        "cycle",
    )


def _refresh_plate_compiler() -> None:
    if os.environ.get("NEXUS_PLATE_COMPILER", "1") != "1":
        return
    _import_call(
        INSTALL / "lib" / "plate-compiler.py",
        "plate_compiler",
        "cycle",
    )


def _refresh_universal_protector() -> None:
    py = INSTALL / "lib" / "universal-protector.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("universal_protector", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_status(meld=False, write=True)
    except Exception:
        pass


def _refresh_sense_package() -> None:
    py = INSTALL / "lib" / "field-sense-package-meld.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_sense_package_meld", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.meld(link_plates=True)
    except Exception:
        pass


def fuse(*, refresh_bus: bool = False) -> dict[str, Any]:
    """Fast fuse — collect on-disk plates only, no refresh storm."""
    return meld(refresh_bus=refresh_bus, refresh_plates=False)


def meld(*, refresh_bus: bool = True, refresh_plates: bool = True) -> dict[str, Any]:
    """Fuse all plates under flock — uninterruptable chain generation."""
    global _GEN, _LAST_CHAIN
    fd = _meld_lock()
    t0 = time.perf_counter()
    meld_force = os.environ.get("NEXUS_PLATE_MELD_FORCE", "").strip().lower() in ("1", "true", "yes")
    predictive: dict[str, Any] = {}
    try:
        if refresh_plates and not meld_force:
            predictive = _predictive_skip_refresh(force=False)
            if predictive.get("skip_refresh"):
                refresh_plates = False
        if refresh_plates:
            _refresh_if_allowed("eye_ear_plate", _refresh_eye_ear_plate)
            _refresh_if_allowed("ironclad_field_sanity", _refresh_ironclad_field_sanity)
            _refresh_if_allowed("ironclad_reality_field", _refresh_ironclad_reality_field)
            _refresh_if_allowed("iron_plate", _refresh_iron_plate)
            _refresh_if_allowed("gatekeeper", _refresh_gatekeeper)
            _refresh_if_allowed("logic_gate", _refresh_logic_gate)
            _refresh_if_allowed("port_ddos", _refresh_port_ddos)
            _refresh_if_allowed("packet_deinterlace", _refresh_packet_deinterlace)
            _refresh_if_allowed("znetwork", _refresh_znetwork_status)
            _refresh_if_allowed("firmware", _refresh_firmware_threats)
            _refresh_if_allowed("kernel", _refresh_kernel_meld)
            _refresh_if_allowed("sense_package", _refresh_sense_package)
            _refresh_if_allowed("field_plate", _refresh_field_plate)
            _refresh_if_allowed("spatial", _refresh_spatial)
            _refresh_if_allowed("humanoid_motion", _refresh_humanoid_motion)
            _refresh_if_allowed("hostess7_brain", _refresh_hostess7_brain)
            if not _meld_light():
                _refresh_if_allowed("hostess7_programming", _refresh_hostess7_programming)
                _refresh_if_allowed("hostess7_g16", _refresh_hostess7_g16)
                _refresh_if_allowed("hostess7_calculator", _refresh_hostess7_calculator)
                _refresh_if_allowed("hostess7_biology", _refresh_hostess7_biology)
                _refresh_if_allowed("hostess7_engineering", _refresh_hostess7_engineering)
                _refresh_if_allowed("hostess7_combat", _refresh_hostess7_combat)
                _refresh_if_allowed("hostess7_mos", _refresh_hostess7_mos)
            _refresh_if_allowed("hostess7_training", _refresh_hostess7_training)
            _refresh_if_allowed("iron_plate_motion", _refresh_iron_plate_motion)
            _refresh_if_allowed("iron_plate_organize", _refresh_iron_plate_organize)
            _refresh_if_allowed("iron_plate_spot", _refresh_iron_plate_spot)
            _refresh_if_allowed("creatable_lives", _refresh_creatable_lives)
            _refresh_if_allowed("right_to_exist", _refresh_right_to_exist)
            _refresh_if_allowed("universal_protector", _refresh_universal_protector)
            _refresh_if_allowed("g16_stack", _refresh_g16_stack)
            _refresh_if_allowed("g16_compiler_sense", _refresh_g16_compiler_sense)
            _refresh_if_allowed("physics_witness", _refresh_physics_witness)
            _refresh_if_allowed("locational_sitrep", _refresh_locational_sitrep)
            _refresh_if_allowed("g16_power_sort", _refresh_g16_power_sort)
            _refresh_if_allowed("truth_blocks", _refresh_truth_blocks)
            _refresh_if_allowed("c2_taskbar", _refresh_c2_taskbar)
            _refresh_if_allowed("field_host_desktop", _refresh_field_host_desktop)
            _refresh_if_allowed("shell_dock", _refresh_shell_dock)
            _refresh_if_allowed("field_popcorn", _refresh_field_popcorn)
            _refresh_if_allowed("field_ellie_fier", _refresh_field_ellie_fier)
            _refresh_if_allowed("field_g16_launch", _refresh_field_g16_launch)
            _refresh_if_allowed("field_gpu", _refresh_field_gpu)
            _refresh_if_allowed("field_audio", _refresh_field_audio)
            _refresh_if_allowed("field_storage", _refresh_field_storage)
            _refresh_if_allowed("field_display", _refresh_field_display)
            _refresh_if_allowed("ammoos_blocks", _refresh_ammoos_blocks)
            _refresh_if_allowed("sovereign_stack", _refresh_sovereign_stack)
            _refresh_if_allowed("thermal_manager_block", _refresh_thermal_manager_block)
            _refresh_if_allowed("rtx_canvas_block", _refresh_rtx_canvas_block)
            _refresh_if_allowed("final_ear_block", _refresh_final_ear_block)
            _refresh_if_allowed("final_mouth_block", _refresh_final_mouth_block)
            _refresh_if_allowed("field_broadcaster", _refresh_field_broadcaster)
            _refresh_if_allowed("field_lock", _refresh_field_lock)
            _refresh_if_allowed("code_bugfinder", _refresh_code_bugfinder)
            _refresh_if_allowed("field_combinatorics", _refresh_field_combinatorics)
            _refresh_if_allowed("combinatorics_bridge", _refresh_combinatorics_bridge)
            _refresh_if_allowed("compatibility_layers", _refresh_compatibility_layers)
            _refresh_if_allowed("drop_in", _refresh_drop_in)
            tb_panel_path = STATE / "g16-truth-blocks-panel.json"
            skip_compiler = False
            if tb_panel_path.is_file():
                try:
                    tb_panel = json.loads(tb_panel_path.read_text(encoding="utf-8"))
                    skip_compiler = bool(tb_panel.get("free_meld")) and not bool(tb_panel.get("compile_gate"))
                except (OSError, json.JSONDecodeError):
                    skip_compiler = False
            if not skip_compiler:
                _refresh_if_allowed("plate_compiler", _refresh_plate_compiler)
            _refresh_if_allowed("g1id_baselines", _refresh_g1id_baselines)
            _refresh_if_allowed("field_io_packet", _refresh_field_io_packet)
            if not _meld_light():
                _refresh_if_allowed("plate_tests", _refresh_plate_tests)
        prev = _load(MELD_RUNTIME, {})
        prev_chain = str(prev.get("chain_hash") or "")
        prev_gen = int(prev.get("generation") or 0)
        _GEN = max(prev_gen + 1, _GEN + 1)

        plates = _collect_plates()
        chain = _digest(plates, prev_chain)
        _LAST_CHAIN = chain

        iron = plates.get("iron_plate") or {}
        rt = plates.get("plate_runtime") or {}
        bus = plates.get("unified_bus") or {}
        gk = plates.get("gatekeeper") or {}
        znet = plates.get("znetwork") or {}
        logic = plates.get("logic_gate") or {}
        kernel = plates.get("kernel") or {}
        net_stack = _net_stack_summary(plates)
        firmware = plates.get("firmware") or {}
        sense = plates.get("sense_package") or {}
        field_plate = plates.get("field_plate") or {}
        spatial = plates.get("spatial_field") or {}
        motion = plates.get("humanoid_motion") or {}
        iron_motion = plates.get("iron_plate_motion") or {}
        creatable = plates.get("creatable_lives") or {}
        right_exist = plates.get("right_to_exist") or {}
        h7_brain = plates.get("hostess7_brain") or {}
        protector = plates.get("universal_protector") or {}
        ironclad_rf = plates.get("ironclad_reality_field") or {}
        ironclad_plate = plates.get("ironclad") or {}
        ironclad_fs = plates.get("ironclad_field_sanity") or {}
        eye_ear = plates.get("eye_ear_plate") or {}
        plate_compiler = plates.get("plate_compiler") or {}
        g16_stack = plates.get("g16_stack") or {}
        g16_sense = plates.get("g16_compiler_sense") or {}
        g16_power_sort = plates.get("g16_power_sort") or {}
        physics_witness = plates.get("physics_witness") or {}
        locational_sitrep = plates.get("locational_sitrep") or {}
        plate_tests = plates.get("plate_test_runner") or {}
        truth_blocks = plates.get("truth_blocks") or {}
        combinatorics = plates.get("field_combinatorics") or {}
        comb_bridge = plates.get("combinatorics_bridge") or {}
        exec_posture = comb_bridge.get("exec_posture") or {}
        shell_dock = plates.get("shell_dock") or {}
        field_popcorn = plates.get("field_popcorn") or {}
        field_ellie_fier = plates.get("field_ellie_fier") or {}
        field_g16_launch = plates.get("field_g16_launch") or {}
        field_gpu = plates.get("field_gpu") or {}
        field_audio = plates.get("field_audio") or {}
        field_storage = plates.get("field_storage") or {}
        field_display = plates.get("field_display") or {}
        ammoos_blocks = plates.get("ammoos_blocks") or {}
        sovereign_stack = plates.get("sovereign_stack") or {}
        field_broadcaster_plate = plates.get("field_broadcaster") or {}
        c2_taskbar = plates.get("c2_taskbar") or {}
        field_lock_plate = plates.get("field_lock") or {}

        doc: dict[str, Any] = {
            "schema": "field-plate-meld/v1",
            "ts": _now(),
            "generation": _GEN,
            "chain_hash": chain,
            "prev_chain_hash": prev_chain or None,
            "uninterruptable": True,
            "never_lose_plate_truth": True,
            "plates": list(plates.keys()),
            "plate_count": sum(1 for p in plates.values() if not p.get("missing")),
            "summary": {
                "connections": iron.get("connection_count") or len(rt.get("route_words") or []),
                "route_words": len(rt.get("route_words") or []),
                "bus_checksum": bus.get("checksum"),
                "direct": rt.get("direct_count"),
                "storm": rt.get("storm_count"),
                "network_stack": net_stack,
                "gatekeeper_connections": net_stack.get("gatekeeper_connections"),
                "gatekeeper_harm_candidates": net_stack.get("gatekeeper_harm_candidates"),
                "net_iface_count": net_stack.get("net_iface_count"),
                "logic_gate_high": net_stack.get("logic_gate_high"),
                "znetwork_present": net_stack.get("znetwork_present"),
                "network_stack_melded": net_stack.get("network_stack_melded"),
                "kernel_live": kernel.get("kilroy_live"),
                "bzimage_ready": kernel.get("bzimage_ready"),
                "boot_vector": kernel.get("boot_vector"),
                "firmware_verdict": firmware.get("verdict"),
                "firmware_threats": firmware.get("threat_count"),
                "firmware_removed": firmware.get("removed_count"),
                "sense_verdict": sense.get("verdict"),
                "sense_present": (sense.get("summary") or {}).get("present_count"),
                "eye_live": (sense.get("summary") or {}).get("eye_live"),
                "field_infinite_dimension": field_plate.get("infinite_dimension"),
                "field_energy": field_plate.get("field_energy"),
                "field_peak_amplitude": field_plate.get("peak_amplitude"),
                "field_dimension_count": field_plate.get("dimension_count"),
                "field_amplitude_process": field_plate.get("amplitude_process"),
                "spatial_dimensions": spatial.get("dimensions"),
                "spatial_delta_t": spatial.get("delta_t"),
                "spatial_movement": (spatial.get("movement_vector") or {}).get("geometry"),
                "spatial_approach": (spatial.get("movement_vector") or {}).get("approach"),
                "humanoid_motion_skill": motion.get("active_label"),
                "humanoid_motion_proficiency": motion.get("active_proficiency"),
                "assemblage_remaining": (iron_motion.get("assemblage_remaining") or {}).get("remaining_slots"),
                "assemblage_score": (iron_motion.get("assemblage_remaining") or {}).get("assemblage_score"),
                "full_assemblage_fused": (iron_motion.get("full_assemblage_meld") or {}).get("fused_score"),
                "vision_live": (iron_motion.get("assemblage_remaining") or {}).get("vision_live"),
                "hearing_live": (iron_motion.get("assemblage_remaining") or {}).get("hearing_live"),
                "motion_verdict": iron_motion.get("motion_verdict"),
                "iron_clad": iron_motion.get("iron_clad"),
                "simple_iron_goals_met": (iron_motion.get("simple_iron_plate_goals") or {}).get("met"),
                "truth_block_count": truth_blocks.get("truth_block_count"),
                "truth_blocks_eligible": truth_blocks.get("eligible_count"),
                "truth_blocks_bytes": truth_blocks.get("total_bytes"),
                "free_meld": truth_blocks.get("free_meld"),
                "free_meld_compile_gate": truth_blocks.get("compile_gate"),
                "ammoos_block_count": ammoos_blocks.get("block_count"),
                "ammoos_stack_held": ammoos_blocks.get("stack_held"),
                "ammoos_thermal_safe": ammoos_blocks.get("thermal_safe"),
                "ammoos_chips_held": (ammoos_blocks.get("chips_block") or {}).get("held"),
                "ammoos_codecs_held": (ammoos_blocks.get("codecs_block") or {}).get("held"),
                "sovereign_stack_sealed": sovereign_stack.get("sealed"),
                "sovereign_stack_tight": sovereign_stack.get("stack_tight"),
                "sovereign_tier_order": sovereign_stack.get("tier_order"),
                "sovereign_gaps": sovereign_stack.get("gaps"),
                "sovereign_interlopers": sovereign_stack.get("interlopers"),
                "ammoos_display_profile": (ammoos_blocks.get("display_block") or {}).get("snapshot", {}).get("resolution_profile"),
                "combinatorics_native_ceiling": (combinatorics.get("speed_cap") or {}).get("native_ceiling_ops_per_sec"),
                "combinatorics_lattice_dots": ((combinatorics.get("hard_limits") or {}).get("boxes_of_boxes") or {}).get("total_lattice_dots"),
                "combinatorics_cardinality": (combinatorics.get("combinatoric_space") or {}).get("cardinality_estimate"),
                "combinatoric_tree_complete": comb_bridge.get("combinatoric_tree_complete")
                or (combinatorics.get("tree_walk") or {}).get("tree_complete"),
                "combinatoric_tree_leaves": (combinatorics.get("tree_walk") or {}).get("leaves_reached"),
                "condensed_plate_groups": comb_bridge.get("condensed_group_count")
                or (combinatorics.get("plate_condense") or {}).get("group_count"),
                "library_truth_clear": truth_blocks.get("library_clear_sentences"),
                "exec_runner": exec_posture.get("runner"),
                "exec_emulator": exec_posture.get("emulator"),
                "exec_die_slots": exec_posture.get("die_slots"),
                "exec_belt_profile": exec_posture.get("belt_profile"),
                "exec_iron_exec": exec_posture.get("iron_exec_recommended"),
                "exec_larger_plate": exec_posture.get("larger_plate"),
                "thermal_entropy_ok": (comb_bridge.get("gate") or {}).get("ok"),
                "creatable_lives_sustain": (creatable.get("sustain") or {}).get("score"),
                "creatable_lives_verdict": (creatable.get("sustain") or {}).get("verdict"),
                "creatable_lives_assist": (creatable.get("assistance") or {}).get("active"),
                "vita_live": (creatable.get("twins") or {}).get("vita", {}).get("live"),
                "auditus_live": (creatable.get("twins") or {}).get("auditus", {}).get("live"),
                "right_to_exist_sealed": right_exist.get("mandate_sealed"),
                "self_preservation_mandate": right_exist.get("self_preservation_mandate"),
                "friendlies_preservation_mandate": right_exist.get("friendlies_preservation_mandate"),
                "under_god": right_exist.get("under_god"),
                "hostess7_brain_verified": (h7_brain.get("verification") or {}).get("verified") or h7_brain.get("verified"),
                "hostess7_brain_verdict": h7_brain.get("verdict"),
                "hostess7_guard_score": h7_brain.get("guard_score"),
                "hostess7_brain_corrupted": (
                    h7_brain.get("corrupted_count", 0) > 0
                    or (h7_brain.get("verification") or {}).get("corrupted")
                    or int(h7_brain.get("removal_count") or 0) > 0
                ),
                "autonomous_being": spatial.get("autonomous_being") or protector.get("autonomous_being"),
                "universal_protector": protector.get("product"),
                "think_tanks": (protector.get("pillars") or {}).get("cognition", {}).get("think_tanks"),
                "ironclad_sealed": ironclad_rf.get("ironclad_sealed") or ironclad_plate.get("realized"),
                "truth_serum_verdict": ironclad_rf.get("verdict"),
                "truth_percent": (ironclad_rf.get("truth_serum") or {}).get("truth_percent"),
                "clean_voltage_ok": (ironclad_rf.get("clean_voltage") or {}).get("ok"),
                "voltage_is_voltage": (ironclad_rf.get("clean_voltage") or {}).get("voltage_is_voltage"),
                "smoothness_score": (ironclad_rf.get("smoothness") or {}).get("smoothness_score"),
                "smooth_operator": (ironclad_rf.get("smoothness") or {}).get("smooth_operator"),
                "ironclad_canonical_hash": ironclad_rf.get("canonical_hash") or ironclad_plate.get("canonical_hash"),
                "ai_in_charge": ironclad_rf.get("ai_in_charge"),
                "human_condition": (ironclad_rf.get("human_condition") or {}).get("human_condition"),
                "charge_holder": ironclad_rf.get("charge_holder"),
                "field_sanity_ok": ironclad_fs.get("operator_ok") or ironclad_fs.get("ok"),
                "field_sanity_citation": ironclad_fs.get("citation"),
                "field_sanity_heat_avoided": (ironclad_fs.get("queen") or {}).get("heat_avoided"),
                "field_sanity_layers_out": (ironclad_fs.get("queen") or {}).get("layers_out"),
                "eye_ear_plate_ok": eye_ear.get("plated") or eye_ear.get("ok"),
                "eye_ear_plate_verdict": eye_ear.get("verdict"),
                "eye_ear_chain_hash": eye_ear.get("chain_hash"),
                "plate_compiler_ok": plate_compiler.get("compiler_ok") or plate_compiler.get("ok"),
                "plate_compiler_destinations": len(plate_compiler.get("destinations") or []),
                "g16_stack_ok": g16_stack.get("optimized") or g16_stack.get("ok"),
                "g16_effective_profile": (g16_stack.get("compile") or {}).get("effective_profile"),
                "g16_linker_targets": (g16_stack.get("multi_os") or {}).get("targets"),
                "g16_os_families": (g16_stack.get("multi_os") or {}).get("os_families"),
                "rtx_gate_satisfied": (g16_stack.get("rtx_gate") or {}).get("satisfied"),
                "eye_ok": eye_ear.get("eye_ok"),
                "ear_ok": eye_ear.get("ear_ok"),
                "mouth_ok": eye_ear.get("mouth_ok"),
                "g16_compiler_sense_ok": g16_sense.get("plated") or g16_sense.get("ok"),
                "g16_sense_profile": g16_sense.get("effective_profile"),
                "g16_sense_score": g16_sense.get("sense_score"),
                "g16_power_sort_ok": g16_power_sort.get("plated") or g16_power_sort.get("ok"),
                "g16_power_sort_verdict": g16_power_sort.get("verdict"),
                "g16_power_sort_cool": (g16_power_sort.get("thermal") or {}).get("cool_ok"),
                "g16_power_sort_sections": sum(
                    1 for s in (g16_power_sort.get("sections") or {}).values() if s.get("available")
                ),
                "physics_witness_ok": physics_witness.get("ok"),
                "thermal_cool_ok": (physics_witness.get("thermal") or {}).get("cool_ok"),
                "entropy_ok": (physics_witness.get("entropy") or {}).get("entropy_ok"),
                "isotope_ok": (physics_witness.get("isotope") or {}).get("ok"),
                "locational_sitrep_ok": locational_sitrep.get("plated") or locational_sitrep.get("ok"),
                "locational_sitrep_verdict": locational_sitrep.get("verdict"),
                "gps_ready": locational_sitrep.get("gps_ready"),
                "spatial_pass_ok": locational_sitrep.get("spatial_pass_ok"),
                "sitrep_geometry": (locational_sitrep.get("movement") or {}).get("geometry"),
                "plate_tests_ran": plate_tests.get("ran"),
                "plate_tests_passed": plate_tests.get("passed"),
                "plate_tests_incomplete": plate_tests.get("incomplete"),
                "shell_dock_ok": shell_dock.get("ok"),
                "sovereign_synced": (shell_dock.get("sovereign") or {}).get("all_synced"),
                "session_drift_ns": (shell_dock.get("session") or {}).get("drift_since_session_ns"),
                "popcorn_count": (field_popcorn.get("library") or {}).get("count"),
                "popcorn_ok": field_popcorn.get("ok"),
                "ellie_fier_ok": field_ellie_fier.get("ok"),
                "ellie_fier_verdict": (field_ellie_fier.get("systemwide") or {}).get("verdict"),
                "ellie_fier_score": (field_ellie_fier.get("systemwide") or {}).get("score"),
                "g16_launch_count": (field_g16_launch.get("index") or {}).get("count"),
                "g16_launch_ready": (field_g16_launch.get("g16") or {}).get("ok"),
                "field_gpu_count": field_gpu.get("detected_count"),
                "field_gpu_ok": field_gpu.get("ok"),
                "field_audio_ok": field_audio.get("ok"),
                "field_audio_backend": field_audio.get("backend"),
                "field_storage_ok": field_storage.get("ok"),
                "field_storage_disks": field_storage.get("disk_count"),
                "field_storage_partitions": field_storage.get("partition_count"),
                "field_display_ok": field_display.get("ok"),
                "ammoos_blocks_ok": ammoos_blocks.get("ok"),
                "ammoos_thermal_safe": ammoos_blocks.get("thermal_safe"),
                "broadcaster_ok": field_broadcaster_plate.get("ok"),
                "broadcaster_streaming": field_broadcaster_plate.get("streaming"),
                "field_surfaces_live": comb_bridge.get("field_surfaces_live"),
                "operator_surfaces_condensed": comb_bridge.get("operator_surfaces_condensed"),
                "c2_taskbar_ok": c2_taskbar.get("ok"),
                "c2_quint_live": c2_taskbar.get("quint_live"),
                "c2_quint_total": c2_taskbar.get("quint_total"),
                "c2_bsp_hit": (c2_taskbar.get("bsp") or {}).get("bsp_hit"),
                "c2_taskbar_condensed": comb_bridge.get("c2_taskbar_condensed"),
                "field_lock_ok": field_lock_plate.get("ok"),
            },
            "snapshots": plates,
        }

        payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
        _fsync_write(MELD, payload)
        runtime = {
            "schema": "field-plate-meld-runtime/v1",
            "ts": doc["ts"],
            "generation": _GEN,
            "chain_hash": chain,
            "summary": doc["summary"],
            "uninterruptable": True,
        }
        _fsync_write(MELD_RUNTIME, json.dumps(runtime, ensure_ascii=False, indent=2) + "\n")
        _mirror_meld(doc)
        _append_ledger({
            "ts": doc["ts"],
            "generation": _GEN,
            "chain_hash": chain,
            "plates": doc["plate_count"],
        })

        if refresh_bus:
            _refresh_unified_bus()

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 3)
        if predictive:
            doc["predictive_meld"] = predictive
        doc["predictive_skip_refresh"] = bool(predictive.get("skip_refresh"))
        doc["refresh_plates"] = refresh_plates
        doc["elapsed_ms"] = elapsed_ms
        pm = _predictive_meld_mod()
        if pm and hasattr(pm, "record_meld_cycle"):
            pm.record_meld_cycle(
                refreshed_plates=refresh_plates,
                elapsed_ms=elapsed_ms,
                plate_hash=str(predictive.get("plate_hash") or ""),
                corpus_hash=str(predictive.get("corpus_hash") or ""),
            )

        return doc
    finally:
        _meld_unlock(fd)


def _refresh_unified_bus() -> None:
    py = INSTALL / "lib" / "field-unified-bus.py"
    if not py.is_file():
        return
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("field_unified_bus", py)
        if not spec or not spec.loader:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.build_runtime()
    except Exception:
        pass


def read_meld() -> dict[str, Any]:
    """Hot read — prefer runtime, recover from redundant mirror."""
    doc = _load(MELD, {})
    if doc.get("schema"):
        return doc
    for path in (REDUNDANT / "field-plate-meld.json", REDUNDANT / "field-plate-meld.json.bak"):
        if path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
    return {}


def panel_json() -> dict[str, Any]:
    doc = read_meld()
    if doc.get("schema"):
        return doc
    return {
        "schema": "field-plate-meld/v1",
        "ok": False,
        "error": "meld_not_published",
        "hint": "Run field-plate-meld.py meld or POST /api/plate-meld/cycle",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    if cmd == "json":
        print(json.dumps(panel_json(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("meld", "cycle", "build"):
        print(json.dumps(meld(), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("fuse", "fast"):
        print(json.dumps(fuse(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "recover":
        doc = read_meld()
        print(json.dumps({"recovered": bool(doc), "generation": doc.get("generation")}, ensure_ascii=False))
        return 0
    print(json.dumps({"error": "usage: field-plate-meld.py [json|meld|recover]"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())