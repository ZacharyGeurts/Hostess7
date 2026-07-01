#!/usr/bin/env pythong
"""Field host freeze — lock memory, freeze guest host, sovereign clock on resume.

Soft freeze uses cgroup v2 freezer on nexus-host-guest.slice while nexus-field.slice
keeps panel, daemon, and field draw paths alive. ACPI mem/disk paths seal state first.
"""
from __future__ import annotations

import ctypes
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

INSTALL = Path(os.environ.get("NEXUS_INSTALL_ROOT", "/usr/local/lib/nexus-shield"))
STATE = Path(os.environ.get("NEXUS_STATE_DIR", "/var/lib/nexus-shield"))
DOCTRINE = INSTALL / "data" / "field-host-freeze-doctrine.json"
FREEZE_STATE = STATE / "field-host-freeze.json"
FREEZE_LOG = STATE / "field-host-freeze.jsonl"
STAMP = STATE / "field-host-freeze.stamp"
CGROUP_ROOT = Path("/sys/fs/cgroup")

MCL_CURRENT = 1
MCL_FUTURE = 2
MCL_ONFAULT = 4


def _now() -> str:
    try:
        spec = importlib.util.spec_from_file_location(
            "sovereign_clock_freeze", INSTALL / "lib" / "sovereign-clock.py",
        )
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod.utc_z("host_freeze")
    except (ImportError, OSError, AttributeError):
        pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _save_atomic(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_log(row: dict[str, Any]) -> None:
    try:
        with FREEZE_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    except OSError:
        pass


def _sovereign_mod() -> Any:
    spec = importlib.util.spec_from_file_location("sovereign_time_freeze", INSTALL / "lib" / "sovereign-time.py")
    if not spec or not spec.loader:
        raise ImportError("sovereign-time.py missing")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _freeze_sh() -> Path:
    return INSTALL / "lib" / "field-host-freeze.sh"


def _virtual_mode() -> bool:
    return os.environ.get("NEXUS_VIRTUAL_FIELD", "").strip().lower() in ("1", "true", "yes")


def _is_root() -> bool:
    return os.geteuid() == 0 or os.environ.get("NEXUS_ELEVATED_ROOT", "0") == "1"


def _run_sh(cmd: str, *, timeout: int = 30) -> dict[str, Any]:
    sh = _freeze_sh()
    if not sh.is_file():
        return {"ok": False, "error": "field_host_freeze_sh_missing"}
    env = {**os.environ, "NEXUS_INSTALL_ROOT": str(INSTALL), "NEXUS_STATE_DIR": str(STATE)}
    try:
        proc = subprocess.run(
            ["bash", str(sh), cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return {
            "ok": proc.returncode == 0,
            "cmd": cmd,
            "rc": proc.returncode,
            "stderr": (proc.stderr or "")[:300],
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "error": str(exc), "cmd": cmd}


def _probe_acpi() -> dict[str, Any]:
    sleep_states: list[str] = []
    mem_sleep = Path("/sys/power/mem_sleep")
    state_path = Path("/sys/power/state")
    try:
        if mem_sleep.is_file():
            sleep_states = mem_sleep.read_text(encoding="utf-8", errors="replace").strip().split()
    except OSError:
        pass
    states: list[str] = []
    try:
        if state_path.is_file():
            states = state_path.read_text(encoding="utf-8", errors="replace").strip().split()
    except OSError:
        pass
    cgroup_v2 = (CGROUP_ROOT / "cgroup.controllers").is_file()
    field_slice = DOCTRINE_DEFAULT["cgroups"]["field_slice"]
    host_slice = DOCTRINE_DEFAULT["cgroups"]["host_slice"]
    host_frozen = None
    freeze_ctl = CGROUP_ROOT / host_slice / "cgroup.freeze"
    if freeze_ctl.is_file():
        try:
            host_frozen = freeze_ctl.read_text(encoding="utf-8").strip() == "1"
        except OSError:
            host_frozen = None
    return {
        "cgroup_v2": cgroup_v2,
        "mem_sleep_states": sleep_states,
        "power_states": states,
        "mem_available": "mem" in states or "freeze" in states,
        "disk_available": "disk" in states,
        "host_slice_frozen": host_frozen,
        "field_slice": field_slice,
        "host_slice": host_slice,
    }


DOCTRINE_DEFAULT = _load(DOCTRINE, {
    "schema": "field-host-freeze-doctrine/v1",
    "cgroups": {"field_slice": "nexus-field.slice", "host_slice": "nexus-host-guest.slice"},
    "modes": {},
})


def _current_state() -> dict[str, Any]:
    return _load(FREEZE_STATE, {
        "schema": "field-host-freeze-state/v1",
        "phase": "idle",
        "mode": None,
        "frozen": False,
    })


def lock_memory(*, state_files_only: bool = True) -> dict[str, Any]:
    """mlock field state — best effort; does not fail freeze on cap limits."""
    locked_pages = 0
    errors: list[str] = []
    mlockall_ok = False
    if platform.system().lower() == "linux" and not _virtual_mode():
        try:
            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            rc = libc.mlockall(MCL_CURRENT | MCL_FUTURE)
            mlockall_ok = rc == 0
            if rc != 0:
                err = ctypes.get_errno()
                errors.append(f"mlockall_errno_{err}")
        except OSError as exc:
            errors.append(f"mlockall:{exc}")

    doctrine = _load(DOCTRINE, DOCTRINE_DEFAULT)
    targets: list[Path] = [STATE / name for name in doctrine.get("state_files", [])]
    if not state_files_only:
        targets.append(STATE)
    for path in targets:
        if not path.exists():
            continue
        try:
            if path.is_file():
                data = path.read_bytes()
                buf = ctypes.create_string_buffer(data)
                libc = ctypes.CDLL("libc.so.6", use_errno=True)
                page = libc.sysconf(30)  # _SC_PAGESIZE
                length = max(len(data), page)
                if libc.mlock(ctypes.addressof(buf), length) == 0:
                    locked_pages += 1
        except OSError as exc:
            errors.append(f"{path.name}:{exc}")

    row = {
        "ts": _now(),
        "event": "memory_lock",
        "mlockall": mlockall_ok,
        "locked_files": locked_pages,
        "errors": errors,
    }
    _append_log(row)
    return {"ok": True, "memory_lock": row}


def prepare(*, mode: str = "soft") -> dict[str, Any]:
    mode = (mode or "soft").strip().lower()
    if mode not in ("soft", "mem", "disk"):
        return {"ok": False, "error": "invalid_mode", "allowed": ["soft", "mem", "disk"]}
    acpi = _probe_acpi()
    if mode == "soft" and not acpi.get("cgroup_v2"):
        return {"ok": False, "error": "cgroup_v2_unavailable"}
    if mode == "mem" and not acpi.get("mem_available"):
        return {"ok": False, "error": "acpi_mem_unavailable", "acpi": acpi}
    if mode == "disk" and not acpi.get("disk_available"):
        return {"ok": False, "error": "acpi_disk_unavailable", "acpi": acpi}

    lock = lock_memory()
    doc = {
        "schema": "field-host-freeze-state/v1",
        "phase": "prepared",
        "mode": mode,
        "frozen": False,
        "prepared_at": _now(),
        "mono_ns": time.monotonic_ns(),
        "linear_ns": _sovereign_linear_ns(),
        "wall_ns": time.time_ns(),
        "memory_lock": lock.get("memory_lock"),
        "field_draw_isolated": mode == "soft",
        "acpi": acpi,
    }
    _save_atomic(FREEZE_STATE, doc)
    STAMP.write_text(_now() + "\n", encoding="utf-8")
    _append_log({"ts": _now(), "event": "prepare", "mode": mode, "doc": {k: v for k, v in doc.items() if k != "memory_lock"}})
    if _is_root() and not _virtual_mode():
        _run_sh("ensure-slices")
    return {"ok": True, "prepared": True, "mode": mode, "state": doc}


def _sovereign_linear_ns() -> int:
    try:
        return int(_sovereign_mod().linear_time_ns())
    except (ImportError, AttributeError, OSError):
        return time.time_ns()


def freeze(*, mode: str = "soft", async_acpi: bool = True) -> dict[str, Any]:
    mode = (mode or "soft").strip().lower()
    prep = prepare(mode=mode)
    if not prep.get("ok"):
        return prep

    if _virtual_mode():
        doc = _current_state()
        doc.update({"phase": "frozen", "frozen": True, "frozen_at": _now(), "virtual": True})
        _save_atomic(FREEZE_STATE, doc)
        return {"ok": True, "frozen": True, "mode": mode, "virtual": True, "state": doc}

    if not _is_root():
        return {
            "ok": False,
            "error": "root_required",
            "hint": "POST /api/field-host-freeze/freeze with elevation or pkexec",
            "prepared": prep,
        }

    if mode == "soft":
        result = _run_sh("soft-freeze")
        if not result.get("ok"):
            return {"ok": False, "error": "soft_freeze_failed", "detail": result}
        doc = _current_state()
        doc.update({
            "phase": "frozen",
            "frozen": True,
            "frozen_at": _now(),
            "field_draw_isolated": True,
        })
        _save_atomic(FREEZE_STATE, doc)
        _append_log({"ts": _now(), "event": "soft_freeze", "host_slice": DOCTRINE_DEFAULT["cgroups"]["host_slice"]})
        return {"ok": True, "frozen": True, "mode": "soft", "field_draw_isolated": True, "state": doc}

    doc = _current_state()
    doc.update({"phase": "suspending", "frozen": True, "suspend_at": _now()})
    _save_atomic(FREEZE_STATE, doc)
    _append_log({"ts": _now(), "event": "acpi_suspend_begin", "mode": mode})

    async_cmd = "async-mem" if mode == "mem" else "async-disk"
    if async_acpi:
        _run_sh(async_cmd, timeout=5)
        return {
            "ok": True,
            "pending": True,
            "mode": mode,
            "message": "ACPI suspend scheduled — host will freeze; resume witness runs on wake",
            "state": doc,
        }

    sh_cmd = "acpi-mem" if mode == "mem" else "acpi-disk"
    result = _run_sh(sh_cmd, timeout=3600)
    resume = resume_witness()
    return {"ok": result.get("ok", False), "mode": mode, "acpi": result, "resume": resume}


def thaw() -> dict[str, Any]:
    cur = _current_state()
    mode = cur.get("mode") or "soft"
    if _virtual_mode():
        doc = {**cur, "phase": "idle", "frozen": False, "thawed_at": _now()}
        _save_atomic(FREEZE_STATE, doc)
        return {"ok": True, "thawed": True, "virtual": True, "state": doc}

    if mode != "soft" and cur.get("phase") not in ("frozen", "prepared", "resumed"):
        return {"ok": False, "error": "not_soft_frozen", "state": cur}

    if _is_root():
        _run_sh("thaw")
    doc = {**cur, "phase": "idle", "frozen": False, "thawed_at": _now()}
    _save_atomic(FREEZE_STATE, doc)
    _append_log({"ts": _now(), "event": "thaw"})
    return {"ok": True, "thawed": True, "state": doc}


def close(*, mode: str = "disk") -> dict[str, Any]:
    """Seal host and ACPI-close — disk hibernate or mem sleep."""
    return freeze(mode=mode, async_acpi=True)


def resume_witness() -> dict[str, Any]:
    """On wake — witness suspend gap, update sovereign clock story, thaw soft if needed."""
    cur = _current_state()
    phase = cur.get("phase") or "idle"
    if phase == "idle" and not cur.get("frozen"):
        return {"ok": True, "witness": "idle", "skipped": True}

    now_mono = time.monotonic_ns()
    now_wall = time.time_ns()
    prep_mono = int(cur.get("mono_ns") or 0)
    prep_wall = int(cur.get("wall_ns") or 0)
    prep_linear = int(cur.get("linear_ns") or 0)
    suspend_s: float | None = None
    if prep_mono > 0:
        suspend_s = max(0.0, (now_mono - prep_mono) / 1_000_000_000.0)

    gap: dict[str, Any] | None = None
    red_flag: dict[str, Any] | None = None
    try:
        st = _sovereign_mod()
        if suspend_s and suspend_s > 0.05:
            gap = st.take_time_out(
                kind="gap",
                reason="host_freeze_resume",
                evidence={
                    "suspend_s": suspend_s,
                    "mode": cur.get("mode"),
                    "prep_wall_ns": prep_wall,
                    "resume_wall_ns": now_wall,
                    "prep_linear_ns": prep_linear,
                },
            )
        sample = {"mono_ns": now_mono, "wall_ns": now_wall}
        if hasattr(st, "_check_linear_gap"):
            red_flag = st._check_linear_gap(sample)
        if hasattr(st, "pulse"):
            st.pulse()
    except (ImportError, AttributeError, OSError) as exc:
        gap = {"ok": False, "error": str(exc)}

    clock_bump = {
        "resume_at": _now(),
        "suspend_s": suspend_s,
        "wall_delta_s": (now_wall - prep_wall) / 1_000_000_000.0 if prep_wall else None,
        "linear_ns": _sovereign_linear_ns(),
        "immutable_rule": "Linear time never pauses — gap witnessed on resume",
    }

    if _is_root() and cur.get("mode") == "soft":
        _run_sh("thaw")

    doc = {
        **cur,
        "phase": "resumed",
        "frozen": False,
        "resumed_at": _now(),
        "resume_witness": clock_bump,
        "gap_flag": gap,
        "linear_check": red_flag,
    }
    _save_atomic(FREEZE_STATE, doc)
    _append_log({"ts": _now(), "event": "resume_witness", "clock_bump": clock_bump, "gap": gap is not None})
    STAMP.write_text(_now() + "\n", encoding="utf-8")

    return {
        "ok": True,
        "witness": "resume",
        "clock_bump": clock_bump,
        "gap_flag": gap,
        "linear_check": red_flag,
        "state": doc,
    }


def posture() -> dict[str, Any]:
    doctrine = _load(DOCTRINE, DOCTRINE_DEFAULT)
    cur = _current_state()
    acpi = _probe_acpi()
    root = _is_root()
    return {
        "schema": "field-host-freeze/v1",
        "ts": _now(),
        "ok": True,
        "doctrine": doctrine.get("title", "field-host-freeze"),
        "phase": cur.get("phase", "idle"),
        "frozen": bool(cur.get("frozen")),
        "mode": cur.get("mode"),
        "field_draw_isolated": cur.get("field_draw_isolated", acpi.get("host_slice_frozen") is False),
        "root": root,
        "virtual": _virtual_mode(),
        "acpi": acpi,
        "memory_lock_policy": doctrine.get("policy", {}).get("memory_lock_before_freeze", True),
        "modes": doctrine.get("modes", {}),
        "state": cur,
        "posture": "Host guest freezable — field slice keeps draw; sovereign gap on ACPI resume",
    }


def main() -> int:
    cmd = (sys.argv[1] if len(sys.argv) > 1 else "json").strip().lower()
    elevated = "--elevated" in sys.argv or os.environ.get("NEXUS_ELEVATED_ROOT", "0") == "1"
    if elevated:
        os.environ["NEXUS_ELEVATED_ROOT"] = "1"

    if cmd in ("json", "status", "posture"):
        print(json.dumps(posture(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "prepare":
        mode = sys.argv[2] if len(sys.argv) > 2 else "soft"
        print(json.dumps(prepare(mode=mode), ensure_ascii=False, indent=2))
        return 0
    if cmd == "lock-memory":
        print(json.dumps(lock_memory(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "freeze":
        mode = sys.argv[2] if len(sys.argv) > 2 else "soft"
        print(json.dumps(freeze(mode=mode), ensure_ascii=False, indent=2))
        return 0
    if cmd == "thaw":
        print(json.dumps(thaw(), ensure_ascii=False, indent=2))
        return 0
    if cmd == "close":
        mode = sys.argv[2] if len(sys.argv) > 2 else "disk"
        print(json.dumps(close(mode=mode), ensure_ascii=False, indent=2))
        return 0
    if cmd in ("resume-witness", "resume", "wake"):
        print(json.dumps(resume_witness(), ensure_ascii=False, indent=2))
        return 0

    print(
        "usage: field-host-freeze.py [json|prepare MODE|lock-memory|freeze MODE|thaw|close MODE|resume-witness]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())